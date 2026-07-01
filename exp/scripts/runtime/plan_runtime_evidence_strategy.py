from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import pandas as pd


DEFAULT_BATCH_SUMMARY = Path("exp/results/emse_runtime/batch_status_v1/runtime_batch_status_summary.json")
DEFAULT_PAIR_READINESS = Path("exp/results/emse_runtime/batch_status_v1/runtime_pair_readiness.csv")
DEFAULT_POWER_RECOMMENDATIONS = Path("exp/results/emse_runtime/power_plan_v1/runtime_power_recommendations.csv")
DEFAULT_POWER_GRID = Path("exp/results/emse_runtime/power_plan_v1/runtime_power_grid.csv")
DEFAULT_TASK_MANIFEST = Path("exp/results/emse_runtime/manifest_v1/task_manifest.csv")
DEFAULT_MANUSCRIPT = Path("paper/emse_manuscript_draft.tex")
DEFAULT_OUTPUT_DIR = Path("exp/results/emse_runtime/evidence_strategy_v1")


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def read_json_optional(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"read_error": str(exc)}


def read_csv_optional(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def count_material_gaps(path: Path) -> int:
    if not path.exists():
        return 0
    text = path.read_text(encoding="utf-8")
    return len(re.findall(r"\\materialgap\{", text))


def first_number(value: object) -> float | None:
    number = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(number):
        return None
    return float(number)


def summarize_power(recommendations: pd.DataFrame, grid: pd.DataFrame) -> dict[str, Any]:
    nonempty = recommendations.copy()
    if not nonempty.empty and "recommended_min_pairs" in nonempty.columns:
        nonempty["recommended_min_pairs"] = pd.to_numeric(nonempty["recommended_min_pairs"], errors="coerce")
        nonempty = nonempty.dropna(subset=["recommended_min_pairs"])
    equal = nonempty[nonempty["scenario"].astype(str).str.startswith("equal_success_")] if not nonempty.empty else pd.DataFrame()
    gain = nonempty[nonempty["scenario"].astype(str).str.contains("target_gain", na=False)] if not nonempty.empty else pd.DataFrame()
    loss = recommendations[
        recommendations["scenario"].astype(str).str.contains("target_loss", na=False)
    ] if not recommendations.empty and "scenario" in recommendations.columns else pd.DataFrame()

    def min_pairs(frame: pd.DataFrame) -> float | None:
        if frame.empty or "recommended_min_pairs" not in frame.columns:
            return None
        return first_number(frame["recommended_min_pairs"].min())

    grid_at_24: list[dict[str, Any]] = []
    if not grid.empty and {"scenario", "n_pairs", "estimated_power", "mean_ci_lower"}.issubset(grid.columns):
        numeric = grid.copy()
        numeric["n_pairs"] = pd.to_numeric(numeric["n_pairs"], errors="coerce")
        for _, row in numeric[numeric["n_pairs"].eq(24)].iterrows():
            grid_at_24.append(
                {
                    "scenario": str(row["scenario"]),
                    "estimated_power": first_number(row["estimated_power"]),
                    "mean_ci_lower": first_number(row["mean_ci_lower"]),
                }
            )

    return {
        "recommended_equal_success_min_pairs_min": min_pairs(equal),
        "recommended_equal_success_min_pairs_max": first_number(equal["recommended_min_pairs"].max()) if not equal.empty else None,
        "recommended_gain_scenario_min_pairs": min_pairs(gain),
        "target_loss_scenarios_without_recommendation": sorted(loss["scenario"].astype(str).tolist()) if not loss.empty else [],
        "power_rows_at_24_pairs": grid_at_24,
    }


def summarize_pair_readiness(pair_readiness: pd.DataFrame) -> dict[str, Any]:
    if pair_readiness.empty:
        return {
            "primary_comparisons": 0,
            "max_planned_pairs": 0,
            "max_completed_pairs": 0,
            "max_metric_complete_pairs": 0,
            "all_validation_pass": False,
        }
    numeric = pair_readiness.copy()
    for col in ["planned_pairs", "completed_pairs", "metric_complete_pairs"]:
        if col in numeric.columns:
            numeric[col] = pd.to_numeric(numeric[col], errors="coerce").fillna(0)
    return {
        "primary_comparisons": int(len(numeric)),
        "max_planned_pairs": int(numeric.get("planned_pairs", pd.Series(dtype=float)).max()) if "planned_pairs" in numeric else 0,
        "max_completed_pairs": int(numeric.get("completed_pairs", pd.Series(dtype=float)).max()) if "completed_pairs" in numeric else 0,
        "max_metric_complete_pairs": int(numeric.get("metric_complete_pairs", pd.Series(dtype=float)).max()) if "metric_complete_pairs" in numeric else 0,
        "all_validation_pass": bool(numeric["validation_status"].astype(str).str.upper().eq("PASS").all()) if "validation_status" in numeric else False,
    }


def build_claim_table(
    batch_summary: dict[str, Any],
    pair_summary: dict[str, Any],
    power_summary: dict[str, Any],
    material_gaps: int,
) -> pd.DataFrame:
    completed = int(batch_summary.get("completed_result_rows", 0) or 0)
    metric_complete = int(batch_summary.get("primary_metric_complete_rows", 0) or 0)
    planned_pairs = int(pair_summary.get("max_planned_pairs", 0) or 0)
    completed_pairs = int(pair_summary.get("max_completed_pairs", 0) or 0)
    metric_pairs = int(pair_summary.get("max_metric_complete_pairs", 0) or 0)
    validation_pass = bool(pair_summary.get("all_validation_pass", False))
    equal_min = power_summary.get("recommended_equal_success_min_pairs_min")
    strong_min = int(equal_min) if equal_min is not None else 600

    rows = [
        {
            "claim": "Runtime protocol and auditability",
            "status": "supported",
            "current_evidence": f"{planned_pairs} planned paired rows per primary comparison; packets and validation gates exist.",
            "minimum_gate": "packet integrity plus no-execution status report",
            "next_action": "Keep as protocol/readiness evidence.",
        },
        {
            "claim": "Feasibility of completed repository-level execution",
            "status": "missing" if completed == 0 else "partial",
            "current_evidence": f"{completed} completed rows; {metric_complete} rows with complete primary metrics.",
            "minimum_gate": "completed rows with primary metrics and validation PASS",
            "next_action": "Run first isolated rows, record metrics, then rerun validator and batch status.",
        },
        {
            "claim": "Directional resource-accounting comparison",
            "status": "missing" if metric_pairs == 0 or not validation_pass else "partial",
            "current_evidence": f"{metric_pairs} metric-complete paired rows; validation pass={validation_pass}.",
            "minimum_gate": "metric-complete paired rows for target/reference controllers",
            "next_action": "Analyze only after completed paired rows exist; report as directional unless sample is large.",
        },
        {
            "claim": "Solve-rate non-inferiority at 5 percentage points",
            "status": "missing",
            "current_evidence": f"{metric_pairs} metric-complete pairs; planning suggests about {strong_min}+ pairs under equal-success scenarios.",
            "minimum_gate": "observed paired CI lower bound above -0.05 and enough informative successes",
            "next_action": "Do not make this claim for the 24-task first batch; treat it as feasibility unless much larger paired execution is run.",
        },
        {
            "claim": "Manuscript ready without material runtime gaps",
            "status": "missing" if material_gaps else "supported",
            "current_evidence": f"{material_gaps} material-gap markers in the LaTeX draft.",
            "minimum_gate": "no unsupported runtime claims and no unresolved material-gap markers",
            "next_action": "Either complete validated runtime evidence or reframe the manuscript as AIDev-observational plus protocol.",
        },
    ]
    return pd.DataFrame(rows)


def build_stage_table(power_summary: dict[str, Any]) -> pd.DataFrame:
    equal_min = power_summary.get("recommended_equal_success_min_pairs_min")
    equal_max = power_summary.get("recommended_equal_success_min_pairs_max")
    equal_range = "600-1000"
    if equal_min is not None and equal_max is not None:
        equal_range = f"{int(equal_min)}-{int(equal_max)}"
    return pd.DataFrame(
        [
            {
                "stage": "S0 readiness",
                "paired_tasks": "0 completed",
                "allowed_manuscript_use": "protocol, safety, and evidence-hygiene readiness only",
                "disallowed_use": "solve-rate, resource-saving, or downstream-work effects",
            },
            {
                "stage": "S1 first-batch feasibility",
                "paired_tasks": "about 24 completed",
                "allowed_manuscript_use": "execution feasibility, logging completeness, qualitative failure modes, rough resource accounting",
                "disallowed_use": "formal solve-rate non-inferiority",
            },
            {
                "stage": "S2 preliminary controlled evidence",
                "paired_tasks": "60-120 completed",
                "allowed_manuscript_use": "directional paired effects with wide confidence intervals",
                "disallowed_use": "strong non-inferiority unless observed CI is unexpectedly tight and valid",
            },
            {
                "stage": "S3 strong non-inferiority evidence",
                "paired_tasks": f"about {equal_range} completed under equal-success planning scenarios",
                "allowed_manuscript_use": "pre-specified solve-rate non-inferiority if the observed CI supports it",
                "disallowed_use": "claiming non-inferiority from planned rows or prompt-only dry runs",
            },
        ]
    )


def frame_to_markdown(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "_No rows._"
    headers = list(frame.columns)
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for _, row in frame.iterrows():
        cells = []
        for col in headers:
            value = row[col]
            if isinstance(value, float):
                cells.append(f"{value:.3f}")
            else:
                cells.append(str(value).replace("|", "\\|"))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def write_report(
    path: Path,
    batch_summary: dict[str, Any],
    task_manifest: pd.DataFrame,
    pair_summary: dict[str, Any],
    power_summary: dict[str, Any],
    claim_table: pd.DataFrame,
    stage_table: pd.DataFrame,
    material_gaps: int,
    source_paths: dict[str, str],
) -> None:
    planned_tasks = int(batch_summary.get("matrix_tasks", 0) or len(task_manifest))
    planned_repositories = int(batch_summary.get("matrix_repositories", 0) or (task_manifest["repo"].nunique() if "repo" in task_manifest else 0))
    equal_min = power_summary.get("recommended_equal_success_min_pairs_min")
    equal_max = power_summary.get("recommended_equal_success_min_pairs_max")
    equal_text = "not available"
    if equal_min is not None and equal_max is not None:
        equal_text = f"{int(equal_min)}-{int(equal_max)} paired tasks"

    lines = [
        "# Controlled Runtime Evidence Strategy",
        "",
        "## Bottom Line",
        "",
        f"- Current first batch: {planned_tasks} planned tasks across {planned_repositories} repositories.",
        f"- Completed rows: {int(batch_summary.get('completed_result_rows', 0) or 0)}.",
        f"- Metric-complete paired rows: {int(pair_summary.get('max_metric_complete_pairs', 0) or 0)}.",
        f"- LaTeX material-gap markers: {material_gaps}.",
        f"- Existing power plan suggests {equal_text} for 80% planning power under equal-success non-inferiority scenarios.",
        "",
        "The 24-task first batch should be treated as feasibility and resource-accounting preparation, not as a basis for a strong 5 percentage-point solve-rate non-inferiority claim.",
        "",
        "## Claim Gate Table",
        "",
        frame_to_markdown(claim_table),
        "",
        "## Staged Evidence Interpretation",
        "",
        frame_to_markdown(stage_table),
        "",
        "## Power Snapshot at 24 Pairs",
        "",
    ]
    rows_at_24 = power_summary.get("power_rows_at_24_pairs", [])
    if rows_at_24:
        lines.extend(["| scenario | estimated_power | mean_ci_lower |", "| --- | ---: | ---: |"])
        for row in rows_at_24:
            power = row.get("estimated_power")
            lower = row.get("mean_ci_lower")
            lines.append(
                f"| {row.get('scenario')} | {power:.3f} | {lower:.3f} |"
                if power is not None and lower is not None
                else f"| {row.get('scenario')} |  |  |"
            )
    else:
        lines.append("_No 24-pair power rows were available._")

    loss_scenarios = power_summary.get("target_loss_scenarios_without_recommendation", [])
    lines.extend(
        [
            "",
            "## Recommended Manuscript Decision",
            "",
            "1. Keep AIDev as the main real-world evidence layer.",
            "2. Use the current runtime batch as execution-readiness evidence until rows are completed and validated.",
            "3. If only the 24-task first batch is completed, report it as a feasibility/runtime-accounting study and avoid formal non-inferiority language.",
            "4. If the paper keeps the strong runtime-gate identity, plan a much larger paired execution or weaken the solve-rate claim to an explicitly exploratory comparison.",
            "",
            "## Conservative Planning Note",
            "",
        ]
    )
    if loss_scenarios:
        lines.append(
            "The power plan produced no finite recommendation for these target-loss scenarios within the simulated grid: "
            + ", ".join(f"`{item}`" for item in loss_scenarios)
            + ". This reinforces that a small batch cannot support non-inferiority if the gate may lose even a few solve-rate points."
        )
    else:
        lines.append("No target-loss planning gaps were detected in the recommendation table.")
    lines.extend(
        [
            "",
            "## Source Paths",
            "",
        ]
    )
    for name, source in source_paths.items():
        lines.append(f"- {name}: `{source}`")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize what the controlled-runtime evidence can and cannot support.")
    parser.add_argument("--batch-summary", type=Path, default=DEFAULT_BATCH_SUMMARY)
    parser.add_argument("--pair-readiness", type=Path, default=DEFAULT_PAIR_READINESS)
    parser.add_argument("--power-recommendations", type=Path, default=DEFAULT_POWER_RECOMMENDATIONS)
    parser.add_argument("--power-grid", type=Path, default=DEFAULT_POWER_GRID)
    parser.add_argument("--task-manifest", type=Path, default=DEFAULT_TASK_MANIFEST)
    parser.add_argument("--manuscript", type=Path, default=DEFAULT_MANUSCRIPT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    batch_summary = read_json_optional(args.batch_summary)
    pair_readiness = read_csv_optional(args.pair_readiness)
    power_recommendations = read_csv_optional(args.power_recommendations)
    power_grid = read_csv_optional(args.power_grid)
    task_manifest = read_csv_optional(args.task_manifest)
    material_gaps = count_material_gaps(args.manuscript)

    pair_summary = summarize_pair_readiness(pair_readiness)
    power_summary = summarize_power(power_recommendations, power_grid)
    claim_table = build_claim_table(batch_summary, pair_summary, power_summary, material_gaps)
    stage_table = build_stage_table(power_summary)

    output_dir = ensure_dir(args.output_dir)
    claim_path = output_dir / "runtime_claim_gate_table.csv"
    stage_path = output_dir / "runtime_evidence_stages.csv"
    summary_path = output_dir / "runtime_evidence_strategy_summary.json"
    report_path = output_dir / "runtime_evidence_strategy.md"

    claim_table.to_csv(claim_path, index=False)
    stage_table.to_csv(stage_path, index=False)

    source_paths = {
        "batch_summary": str(args.batch_summary),
        "pair_readiness": str(args.pair_readiness),
        "power_recommendations": str(args.power_recommendations),
        "power_grid": str(args.power_grid),
        "task_manifest": str(args.task_manifest),
        "manuscript": str(args.manuscript),
    }
    summary = {
        "batch_summary": batch_summary,
        "pair_summary": pair_summary,
        "power_summary": power_summary,
        "material_gap_count": material_gaps,
        "claim_table": claim_table.to_dict(orient="records"),
        "stage_table": stage_table.to_dict(orient="records"),
        "source_paths": source_paths,
        "third_party_repository_execution_performed": False,
    }
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    write_report(
        report_path,
        batch_summary,
        task_manifest,
        pair_summary,
        power_summary,
        claim_table,
        stage_table,
        material_gaps,
        source_paths,
    )
    print(f"Wrote runtime evidence strategy to {report_path}")
    print(f"Wrote claim gate table to {claim_path}")


if __name__ == "__main__":
    main()
