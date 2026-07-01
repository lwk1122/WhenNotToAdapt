from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import brier_score_loss

from .common import RESULTS_DIR, ensure_dir, write_json
from .evaluate_workload_gate import (
    CATEGORICAL_FEATURES,
    NUMERIC_FEATURES,
    existing_columns,
    make_model,
    repository_disjoint_split,
    safe_auc,
    safe_average_precision,
    temporal_split,
)


DEFAULT_COMPONENTS = [
    "outcome_review_count",
    "outcome_human_review_count",
    "outcome_request_changes_count",
    "outcome_inline_review_comment_count",
    "outcome_issue_comment_count",
    "outcome_followup_commit_count",
    "outcome_followup_detail_changed_files",
    "outcome_followup_detail_churn",
    "outcome_followup_detail_test_files",
    "outcome_related_issue_count",
]


def prepare_frame(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    for col in existing_columns(frame, NUMERIC_FEATURES + DEFAULT_COMPONENTS):
        frame[col] = pd.to_numeric(frame[col], errors="coerce")
    for col in existing_columns(frame, CATEGORICAL_FEATURES):
        frame[col] = frame[col].fillna("").astype(str)
    return frame


def component_label(train: pd.DataFrame, frame: pd.DataFrame, component: str, quantile: float) -> tuple[pd.Series, float, str]:
    threshold = float(train[component].dropna().quantile(quantile))
    if threshold <= 0.0:
        return frame[component].fillna(0.0) > 0.0, 0.0, "positive"
    return frame[component].fillna(0.0) >= threshold, threshold, f"q{quantile:.2f}"


def evaluate_component_split(
    split_name: str,
    train: pd.DataFrame,
    calibration: pd.DataFrame,
    test: pd.DataFrame,
    component: str,
    quantile: float,
) -> dict | None:
    numeric = existing_columns(train, NUMERIC_FEATURES)
    categorical = existing_columns(train, CATEGORICAL_FEATURES)
    features = numeric + categorical
    if component not in train.columns or not features:
        return None

    train_high, threshold, target_rule = component_label(train, train, component, quantile)
    test_high, _, _ = component_label(train, test, component, quantile)
    cal_high, _, _ = component_label(train, calibration, component, quantile)
    if train_high.nunique(dropna=False) < 2:
        return None

    model = make_model(numeric, categorical)
    model.fit(train[features], train_high)
    cal_scores = model.predict_proba(calibration[features])[:, 1]
    test_scores = model.predict_proba(test[features])[:, 1]

    return {
        "split": split_name,
        "component": component,
        "target_rule": target_rule,
        "threshold": threshold,
        "train_rows": int(len(train)),
        "calibration_rows": int(len(calibration)),
        "test_rows": int(len(test)),
        "train_positive_rate": float(train_high.mean()),
        "calibration_positive_rate": float(cal_high.mean()),
        "test_positive_rate": float(test_high.mean()),
        "test_auc": safe_auc(test_high, test_scores),
        "test_average_precision": safe_average_precision(test_high, test_scores),
        "test_brier": float(brier_score_loss(test_high, test_scores)) if test_high.nunique(dropna=False) > 1 else np.nan,
        "calibration_mean_score": float(np.mean(cal_scores)),
        "test_mean_score": float(np.mean(test_scores)),
        "features": ",".join(features),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Predict individual AIDev downstream-workload components from proposal-time features.")
    parser.add_argument("--features", type=Path, default=RESULTS_DIR / "aidev_pr_level_features.csv")
    parser.add_argument("--output-dir", type=Path, default=RESULTS_DIR)
    parser.add_argument("--components", nargs="*", default=DEFAULT_COMPONENTS)
    parser.add_argument("--positive-quantile", type=float, default=0.80)
    parser.add_argument("--seed", type=int, default=23)
    args = parser.parse_args()

    frame = prepare_frame(args.features)
    split_specs = [
        ("temporal", *temporal_split(frame)),
        ("repository_disjoint", *repository_disjoint_split(frame, args.seed)),
    ]

    rows = []
    for split_name, train, calibration, test in split_specs:
        for component in args.components:
            result = evaluate_component_split(split_name, train, calibration, test, component, args.positive_quantile)
            if result is not None:
                rows.append(result)

    output_dir = ensure_dir(args.output_dir)
    out = pd.DataFrame(rows)
    csv_path = output_dir / "aidev_workload_component_prediction.csv"
    out.to_csv(csv_path, index=False)
    write_json(
        output_dir / "aidev_workload_component_prediction.json",
        {
            "output_csv": str(csv_path),
            "rows": int(len(out)),
            "components": sorted(out["component"].unique().tolist()) if not out.empty else [],
            "splits": sorted(out["split"].unique().tolist()) if not out.empty else [],
        },
    )
    print(f"Wrote workload component prediction summary to {csv_path}")


if __name__ == "__main__":
    main()
