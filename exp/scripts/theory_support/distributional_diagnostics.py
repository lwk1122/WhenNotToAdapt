from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from common import GOVERNANCE_MODES, MANIFEST_DIR, RESULTS_DIR, ensure_dir, manifest_paths, write_json
from controller_benchmark import TASK_FEATURE_COLS, apply_priors, fit_priors


PROFILE_COLUMNS = [
    "problem_tokens",
    "fail_to_pass_count",
    "pass_to_pass_count",
    "gold_patch_lines",
    "e_proxy",
    "d_proxy",
    "q_proxy",
]


def load_profile_datasets(paths: dict[str, Path]) -> dict[str, pd.DataFrame]:
    swe_bench = pd.read_csv(paths["swe_bench_tasks"])
    return {
        "swe_bench_train": swe_bench[swe_bench["split"] == "train"].copy(),
        "swe_bench_dev": swe_bench[swe_bench["split"] == "dev"].copy(),
        "swe_bench_test": swe_bench[swe_bench["split"] == "test"].copy(),
        "swe_verified": pd.read_csv(paths["swe_verified_tasks"]),
        "swe_rebench": pd.read_csv(paths["swe_rebench_tasks"]),
        "swe_smith": pd.read_csv(paths["swe_smith_tasks"]),
    }


def summarize_profile(name: str, frame: pd.DataFrame) -> dict:
    nominal_load = 0.18 + 0.22 * frame["d_proxy"] + 0.18 * frame["q_proxy"]
    mode_stats = []
    for mode in GOVERNANCE_MODES:
        recovery_load = frame["e_proxy"] * mode.recovery_multiplier * (0.20 + 0.25 * frame["d_proxy"] + 0.12 * frame["q_proxy"])
        headroom = mode.service_floor - (nominal_load + recovery_load)
        mode_stats.append(
            {
                "mode": mode.name,
                "mean_headroom": float(headroom.mean()),
                "p10_headroom": float(np.quantile(headroom, 0.10)),
                "safe_rate": float((headroom > 0).mean()),
            }
        )

    return {
        "dataset": name,
        "rows": int(len(frame)),
        "unique_repos": int(frame["repo"].nunique()) if "repo" in frame.columns else 0,
        "problem_tokens_mean": float(frame["problem_tokens"].mean()),
        "problem_tokens_p95": float(np.quantile(frame["problem_tokens"], 0.95)),
        "fail_to_pass_mean": float(frame["fail_to_pass_count"].mean()),
        "fail_to_pass_p95": float(np.quantile(frame["fail_to_pass_count"], 0.95)),
        "pass_to_pass_mean": float(frame["pass_to_pass_count"].mean()),
        "pass_to_pass_p95": float(np.quantile(frame["pass_to_pass_count"], 0.95)),
        "gold_patch_lines_mean": float(frame["gold_patch_lines"].mean()),
        "gold_patch_lines_p95": float(np.quantile(frame["gold_patch_lines"], 0.95)),
        "e_proxy_mean": float(frame["e_proxy"].mean()),
        "e_proxy_p95": float(np.quantile(frame["e_proxy"], 0.95)),
        "high_risk_share": float((frame["e_proxy"] >= 0.60).mean()),
        "d_proxy_mean": float(frame["d_proxy"].mean()),
        "d_proxy_p95": float(np.quantile(frame["d_proxy"], 0.95)),
        "high_exposure_share": float((frame["d_proxy"] >= 0.80).mean()),
        "q_proxy_mean": float(frame["q_proxy"].mean()),
        "q_proxy_p95": float(np.quantile(frame["q_proxy"], 0.95)),
        "high_queue_share": float((frame["q_proxy"] >= 0.80).mean()),
        "mode_headroom": mode_stats,
    }


def compute_shift(reference: pd.DataFrame, frame: pd.DataFrame) -> dict:
    z_deltas = {}
    for column in TASK_FEATURE_COLS:
        ref_mean = float(reference[column].mean())
        ref_std = float(reference[column].std(ddof=0))
        delta = float(frame[column].mean()) - ref_mean
        z_deltas[column] = 0.0 if ref_std == 0 or np.isnan(ref_std) else delta / ref_std
    abs_z = np.abs(np.asarray(list(z_deltas.values()), dtype=float))
    return {
        "mean_abs_feature_shift": float(abs_z.mean()),
        "max_abs_feature_shift": float(abs_z.max()) if len(abs_z) else 0.0,
        "feature_shift_z": z_deltas,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Profile dataset shifts and headroom stress across the local experiment datasets.")
    parser.add_argument("--manifest-dir", type=Path, default=MANIFEST_DIR)
    parser.add_argument("--output-dir", type=Path, default=RESULTS_DIR / "diagnostics")
    args = parser.parse_args()

    output_dir = ensure_dir(args.output_dir)
    paths = manifest_paths(args.manifest_dir)
    risk_prior, atom_prior = fit_priors(args.manifest_dir)
    datasets = {name: apply_priors(frame, risk_prior, atom_prior) for name, frame in load_profile_datasets(paths).items()}

    reference = datasets["swe_bench_test"]
    profiles = [summarize_profile(name, frame) for name, frame in datasets.items()]
    shifts = {name: compute_shift(reference, frame) for name, frame in datasets.items()}

    profile_rows = []
    for profile in profiles:
        safe_lookup = {item["mode"]: item["safe_rate"] for item in profile["mode_headroom"]}
        p10_lookup = {item["mode"]: item["p10_headroom"] for item in profile["mode_headroom"]}
        profile_rows.append(
            {
                "dataset": profile["dataset"],
                "rows": profile["rows"],
                "unique_repos": profile["unique_repos"],
                "problem_tokens_mean": profile["problem_tokens_mean"],
                "problem_tokens_p95": profile["problem_tokens_p95"],
                "e_proxy_mean": profile["e_proxy_mean"],
                "e_proxy_p95": profile["e_proxy_p95"],
                "d_proxy_mean": profile["d_proxy_mean"],
                "d_proxy_p95": profile["d_proxy_p95"],
                "q_proxy_mean": profile["q_proxy_mean"],
                "q_proxy_p95": profile["q_proxy_p95"],
                "high_risk_share": profile["high_risk_share"],
                "high_exposure_share": profile["high_exposure_share"],
                "high_queue_share": profile["high_queue_share"],
                "g0_safe_rate": safe_lookup.get("g0_aggressive", 0.0),
                "g3_safe_rate": safe_lookup.get("g3_safe", 0.0),
                "g0_p10_headroom": p10_lookup.get("g0_aggressive", 0.0),
                "g3_p10_headroom": p10_lookup.get("g3_safe", 0.0),
                "mean_abs_feature_shift_vs_test": shifts[profile["dataset"]]["mean_abs_feature_shift"],
                "max_abs_feature_shift_vs_test": shifts[profile["dataset"]]["max_abs_feature_shift"],
            }
        )

    pd.DataFrame(profile_rows).to_csv(output_dir / "dataset_profiles.csv", index=False)
    write_json(
        output_dir / "distributional_diagnostics.json",
        {
            "reference_dataset": "swe_bench_test",
            "profiles": profiles,
            "shift_vs_test": shifts,
        },
    )
    print("Distributional diagnostics complete.")
    print(pd.DataFrame(profile_rows)[["dataset", "rows", "mean_abs_feature_shift_vs_test", "g0_safe_rate", "g3_safe_rate"]].to_string(index=False))


if __name__ == "__main__":
    main()
