from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from .common import RESULTS_DIR, ensure_dir, write_json


FEATURE_COLUMNS = [
    "feature_title_chars",
    "feature_body_chars",
    "feature_title_mentions_test",
    "feature_body_mentions_test",
    "feature_body_mentions_fix",
    "feature_changed_files",
    "feature_additions",
    "feature_deletions",
    "feature_churn",
    "feature_initial_commit_count",
    "feature_repo_stars",
    "feature_repo_forks",
    "feature_repo_open_issues",
]


def zscore(train: pd.Series, values: pd.Series) -> pd.Series:
    mean = float(train.mean())
    std = float(train.std(ddof=0))
    if std <= 1e-12:
        return pd.Series(np.zeros(len(values), dtype=float), index=values.index)
    return (values - mean) / std


def structural_score(train: pd.DataFrame, frame: pd.DataFrame) -> pd.Series:
    score = pd.Series(np.zeros(len(frame), dtype=float), index=frame.index)
    for col in FEATURE_COLUMNS:
        if col not in frame.columns or col not in train.columns:
            continue
        score += zscore(train[col].fillna(0.0), frame[col].fillna(0.0)).clip(lower=-3, upper=3)
    return score


def temporal_split(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if "created_at" not in frame.columns:
        shuffled = frame.sample(frac=1.0, random_state=23).reset_index(drop=True)
    else:
        shuffled = frame.assign(_created=pd.to_datetime(frame["created_at"], errors="coerce", utc=True))
        shuffled = shuffled.sort_values(["_created"], na_position="last").drop(columns=["_created"]).reset_index(drop=True)
    n = len(shuffled)
    train_end = int(0.6 * n)
    cal_end = int(0.8 * n)
    return shuffled.iloc[:train_end].copy(), shuffled.iloc[train_end:cal_end].copy(), shuffled.iloc[cal_end:].copy()


def evaluate_gate(frame: pd.DataFrame, target_col: str, high_workload_quantile: float, accept_rate: float) -> dict:
    train, calibration, test = temporal_split(frame)
    if min(len(train), len(calibration), len(test)) == 0:
        raise ValueError("Temporal split produced an empty train, calibration, or test partition.")

    train_score = structural_score(train, train)
    cal_score = structural_score(train, calibration)
    test_score = structural_score(train, test)

    high_threshold = float(train[target_col].quantile(high_workload_quantile))
    cal_high = calibration[target_col] >= high_threshold
    test_high = test[target_col] >= high_threshold

    score_threshold = float(cal_score.quantile(max(min(accept_rate, 1.0), 0.0)))
    accepted = test_score <= score_threshold
    rejected = ~accepted

    accepted_count = int(accepted.sum())
    rejected_count = int(rejected.sum())
    high_count = int(test_high.sum())
    intercepted_high = int((rejected & test_high).sum())
    false_reject_low = int((rejected & ~test_high).sum())
    accepted_high = int((accepted & test_high).sum())

    return {
        "rows": {"train": int(len(train)), "calibration": int(len(calibration)), "test": int(len(test))},
        "target": target_col,
        "high_workload_quantile": high_workload_quantile,
        "high_workload_threshold": high_threshold,
        "accept_rate_target": accept_rate,
        "score_threshold": score_threshold,
        "acceptance_rate": float(accepted.mean()),
        "abstention_rate": float(rejected.mean()),
        "high_workload_rate": float(test_high.mean()),
        "high_workload_recall_by_abstention": float(intercepted_high / high_count) if high_count else 0.0,
        "abstention_precision_for_high_workload": float(intercepted_high / rejected_count) if rejected_count else 0.0,
        "accepted_high_workload_rate": float(accepted_high / accepted_count) if accepted_count else 0.0,
        "false_reject_low_count": false_reject_low,
        "intercepted_high_workload_count": intercepted_high,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a first-pass calibrated abstention diagnostic on AIDev features.")
    parser.add_argument("--features", type=Path, default=RESULTS_DIR / "aidev_pr_level_features.csv")
    parser.add_argument("--output-dir", type=Path, default=RESULTS_DIR)
    parser.add_argument("--target", default="outcome_downstream_workload_log")
    parser.add_argument("--high-workload-quantile", type=float, default=0.80)
    parser.add_argument("--accept-rates", nargs="*", type=float, default=[0.2, 0.4, 0.6, 0.8])
    args = parser.parse_args()

    frame = pd.read_csv(args.features)
    if args.target not in frame.columns:
        raise ValueError(f"Target column {args.target!r} not found in {args.features}")

    output_dir = ensure_dir(args.output_dir)
    results = [
        evaluate_gate(frame, args.target, args.high_workload_quantile, accept_rate)
        for accept_rate in args.accept_rates
    ]
    result_frame = pd.DataFrame(results)
    csv_path = output_dir / "aidev_abstention_temporal_summary.csv"
    result_frame.to_csv(csv_path, index=False)
    write_json(output_dir / "aidev_abstention_temporal_summary.json", {"results": results, "output_csv": str(csv_path)})
    print(f"Wrote abstention summary to {csv_path}")


if __name__ == "__main__":
    main()
