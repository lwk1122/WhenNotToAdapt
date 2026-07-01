from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from statistics import NormalDist

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class PairedScenario:
    name: str
    reference_success_rate: float
    target_minus_reference: float
    discordance_rate: float


DEFAULT_SCENARIOS = [
    PairedScenario("equal_success_low_discordance", 0.35, 0.00, 0.18),
    PairedScenario("equal_success_mid_discordance", 0.45, 0.00, 0.25),
    PairedScenario("equal_success_high_discordance", 0.55, 0.00, 0.32),
    PairedScenario("target_loss_2pp_mid_discordance", 0.45, -0.02, 0.25),
    PairedScenario("target_gain_2pp_mid_discordance", 0.45, 0.02, 0.25),
    PairedScenario("target_loss_2pp_high_discordance", 0.55, -0.02, 0.32),
]


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def scenario_probabilities(scenario: PairedScenario) -> dict[str, float]:
    q = scenario.discordance_rate
    diff = scenario.target_minus_reference
    p10 = (q + diff) / 2.0
    p01 = (q - diff) / 2.0
    p11 = scenario.reference_success_rate - p01
    p00 = 1.0 - p11 - p10 - p01
    probabilities = {
        "both_success": p11,
        "target_only_success": p10,
        "reference_only_success": p01,
        "both_fail": p00,
    }
    if any(value < -1e-9 for value in probabilities.values()):
        raise ValueError(f"Invalid scenario probabilities for {scenario}: {probabilities}")
    total = sum(probabilities.values())
    if abs(total - 1.0) > 1e-9:
        raise ValueError(f"Scenario probabilities do not sum to one for {scenario}: {probabilities}")
    return {key: max(0.0, float(value)) for key, value in probabilities.items()}


def paired_diff_ci_lower(diff_values: np.ndarray, z_value: float) -> float:
    n = len(diff_values)
    mean = float(np.mean(diff_values))
    if n <= 1:
        return mean
    se = float(np.std(diff_values, ddof=1) / np.sqrt(n))
    return mean - z_value * se


def simulate_power(
    scenario: PairedScenario,
    sample_size: int,
    margin: float,
    z_value: float,
    simulations: int,
    rng: np.random.Generator,
) -> dict[str, float]:
    probabilities = scenario_probabilities(scenario)
    probs = np.array(
        [
            probabilities["both_success"],
            probabilities["target_only_success"],
            probabilities["reference_only_success"],
            probabilities["both_fail"],
        ],
        dtype=float,
    )
    values = np.array([0.0, 1.0, -1.0, 0.0], dtype=float)
    lower_bounds = np.empty(simulations, dtype=float)
    mean_diffs = np.empty(simulations, dtype=float)
    for idx in range(simulations):
        draws = rng.choice(values, size=sample_size, replace=True, p=probs)
        mean_diffs[idx] = float(np.mean(draws))
        lower_bounds[idx] = paired_diff_ci_lower(draws, z_value)
    return {
        "estimated_power": float(np.mean(lower_bounds > -margin)),
        "mean_estimated_diff": float(np.mean(mean_diffs)),
        "mean_ci_lower": float(np.mean(lower_bounds)),
        "p10_target_only": probabilities["target_only_success"],
        "p01_reference_only": probabilities["reference_only_success"],
        "p11_both_success": probabilities["both_success"],
        "p00_both_fail": probabilities["both_fail"],
    }


def scenario_rows(
    scenarios: list[PairedScenario],
    sample_sizes: list[int],
    margin: float,
    z_value: float,
    simulations: int,
    seed: int,
) -> pd.DataFrame:
    rows = []
    rng = np.random.default_rng(seed)
    for scenario in scenarios:
        for sample_size in sample_sizes:
            result = simulate_power(scenario, sample_size, margin, z_value, simulations, rng)
            rows.append(
                {
                    "scenario": scenario.name,
                    "n_pairs": sample_size,
                    "reference_success_rate": scenario.reference_success_rate,
                    "target_minus_reference": scenario.target_minus_reference,
                    "target_success_rate": scenario.reference_success_rate + scenario.target_minus_reference,
                    "discordance_rate": scenario.discordance_rate,
                    "margin": margin,
                    **result,
                }
            )
    return pd.DataFrame(rows)


def recommendation_table(power: pd.DataFrame, target_power: float) -> pd.DataFrame:
    rows = []
    for scenario, group in power.groupby("scenario", sort=False):
        eligible = group[group["estimated_power"] >= target_power].sort_values("n_pairs")
        if eligible.empty:
            rows.append(
                {
                    "scenario": scenario,
                    "target_power": target_power,
                    "recommended_min_pairs": np.nan,
                    "estimated_power_at_recommendation": np.nan,
                }
            )
        else:
            first = eligible.iloc[0]
            rows.append(
                {
                    "scenario": scenario,
                    "target_power": target_power,
                    "recommended_min_pairs": int(first["n_pairs"]),
                    "estimated_power_at_recommendation": float(first["estimated_power"]),
                }
            )
    return pd.DataFrame(rows)


def load_manifest_summary(manifest_path: Path | None) -> dict[str, object]:
    if manifest_path is None or not manifest_path.exists():
        return {}
    manifest = pd.read_csv(manifest_path)
    out: dict[str, object] = {
        "manifest_path": str(manifest_path),
        "manifest_tasks": int(len(manifest)),
    }
    if "repo" in manifest.columns:
        out["manifest_repositories"] = int(manifest["repo"].nunique())
    if "risk_tier" in manifest.columns:
        out["manifest_risk_tiers"] = ", ".join(
            f"{tier}={count}" for tier, count in manifest["risk_tier"].value_counts().sort_index().items()
        )
    return out


def markdown_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "_No rows._"

    def fmt(value: object) -> str:
        if pd.isna(value):
            return ""
        if isinstance(value, (float, np.floating)):
            return f"{float(value):.3f}"
        if isinstance(value, (int, np.integer)):
            return str(int(value))
        return str(value).replace("|", "\\|")

    columns = list(frame.columns)
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join(["---"] * len(columns)) + " |",
    ]
    for _, row in frame.iterrows():
        lines.append("| " + " | ".join(fmt(row[col]) for col in columns) + " |")
    return "\n".join(lines)


def write_report(path: Path, power: pd.DataFrame, recommendations: pd.DataFrame, manifest_summary: dict[str, object], args: argparse.Namespace) -> None:
    compact_power = power[
        power["n_pairs"].isin([24, 30, 60, 120, 200, 300, 400, 500, 600, 800, 1000])
    ][
        [
            "scenario",
            "n_pairs",
            "reference_success_rate",
            "target_minus_reference",
            "discordance_rate",
            "estimated_power",
            "mean_ci_lower",
        ]
    ].copy()
    lines = [
        "# Controlled Runtime Non-Inferiority Power Plan",
        "",
        "This report plans the paired solve-rate non-inferiority analysis before running additional repository tasks.",
        "It does not execute repository code or call an LLM.",
        "",
        "## Design Contract",
        "",
        f"- Solve-rate non-inferiority margin: {args.margin:.3f}",
        f"- Confidence level: {1.0 - args.alpha:.3f}",
        f"- Target planning power: {args.target_power:.2f}",
        f"- Simulations per scenario and sample size: {args.simulations}",
        "- Approximation: paired binary target-reference differences with a normal lower confidence bound.",
        "- Final paper analysis should still use the pre-specified paired bootstrap CI from `analyze_runtime_pairs.py`.",
        "",
    ]
    if manifest_summary:
        lines.extend(
            [
                "## Current Manifest",
                "",
                f"- Manifest: `{manifest_summary.get('manifest_path')}`",
                f"- Tasks: {manifest_summary.get('manifest_tasks')}",
                f"- Repositories: {manifest_summary.get('manifest_repositories', 'NA')}",
                f"- Risk tiers: {manifest_summary.get('manifest_risk_tiers', 'NA')}",
                "",
            ]
        )
    lines.extend(
        [
            "## Recommended Minimum Paired Tasks",
            "",
            markdown_table(recommendations),
            "",
            "## Power Grid",
            "",
            markdown_table(compact_power),
            "",
            "## Manuscript Interpretation",
            "",
            "- The existing 24-task manifest is useful for a pilot or first batch, but it is far below the likely publication-grade sample size for a 5 percentage-point margin.",
            "- With a 5 percentage-point margin, moderate paired discordance can require several hundred paired tasks for 80% planning power even when the true solve-rate difference is zero.",
            "- If the target controller loses about 2 percentage points in solve rate, the required paired sample size may exceed 1,000 paired tasks; this is the conservative scenario to use for planning.",
            "- A smaller controlled runtime study can still support feasibility, resource accounting, and directional evidence, but the manuscript should avoid strong solve-rate non-inferiority claims unless the observed CI supports them.",
            "- These calculations are planning approximations. The final claim must be based on observed paired results, the pre-specified bootstrap CI, and nonzero informative success evidence.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Plan paired non-inferiority sample size for controlled runtime experiments.")
    parser.add_argument("--output-dir", type=Path, default=Path("exp/results/emse_runtime/power_plan_v1"))
    parser.add_argument("--manifest", type=Path, default=Path("exp/results/emse_runtime/manifest_v1/task_manifest.csv"))
    parser.add_argument("--margin", type=float, default=0.05)
    parser.add_argument("--alpha", type=float, default=0.05)
    parser.add_argument("--target-power", type=float, default=0.80)
    parser.add_argument("--simulations", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=23)
    parser.add_argument("--sample-sizes", nargs="*", type=int, default=[24, 30, 40, 50, 60, 80, 100, 120, 160, 200, 300, 400, 500, 600, 800, 1000])
    args = parser.parse_args()

    if not (0 < args.margin < 1):
        raise ValueError("--margin must be between 0 and 1.")
    if not (0 < args.alpha < 1):
        raise ValueError("--alpha must be between 0 and 1.")
    if not (0 < args.target_power < 1):
        raise ValueError("--target-power must be between 0 and 1.")

    z_value = NormalDist().inv_cdf(1.0 - args.alpha / 2.0)
    out_dir = ensure_dir(args.output_dir)
    power = scenario_rows(DEFAULT_SCENARIOS, args.sample_sizes, args.margin, z_value, args.simulations, args.seed)
    recommendations = recommendation_table(power, args.target_power)
    manifest_summary = load_manifest_summary(args.manifest)

    power_csv = out_dir / "runtime_power_grid.csv"
    recommendations_csv = out_dir / "runtime_power_recommendations.csv"
    report_path = out_dir / "runtime_power_plan.md"
    power.to_csv(power_csv, index=False)
    recommendations.to_csv(recommendations_csv, index=False)
    write_report(report_path, power, recommendations, manifest_summary, args)
    print(f"Wrote runtime power grid to {power_csv}")
    print(f"Wrote runtime power recommendations to {recommendations_csv}")
    print(f"Wrote runtime power plan to {report_path}")


if __name__ == "__main__":
    main()
