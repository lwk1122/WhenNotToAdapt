from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from .common import RESULTS_DIR, ensure_dir, write_json


NUMERIC_FEATURES = [
    "feature_title_chars",
    "feature_body_chars",
    "feature_title_mentions_test",
    "feature_body_mentions_test",
    "feature_body_mentions_fix",
    "feature_repo_stars",
    "feature_repo_forks",
    "feature_repo_watchers",
    "feature_repo_open_issues",
    "feature_task_type_confidence",
    "feature_initial_detail_changed_files",
    "feature_initial_detail_additions",
    "feature_initial_detail_deletions",
    "feature_initial_detail_churn",
    "feature_initial_detail_added_files",
    "feature_initial_detail_modified_files",
    "feature_initial_detail_removed_files",
    "feature_initial_detail_test_files",
]

CATEGORICAL_FEATURES = ["agent", "repo_language", "feature_task_type"]

TIMING_SENSITIVE_PR_API_FEATURES = [
    "feature_changed_files",
    "feature_additions",
    "feature_deletions",
    "feature_churn",
    "feature_initial_commit_count",
    "feature_initial_review_comment_count_api",
    "feature_initial_issue_comment_count_api",
]

TEXT_NUMERIC_FEATURES = [
    "feature_title_chars",
    "feature_body_chars",
    "feature_title_mentions_test",
    "feature_body_mentions_test",
    "feature_body_mentions_fix",
]

REPO_TASK_NUMERIC_FEATURES = [
    "feature_repo_stars",
    "feature_repo_forks",
    "feature_repo_watchers",
    "feature_repo_open_issues",
    "feature_task_type_confidence",
]

FIRST_COMMIT_NUMERIC_FEATURES = [
    "feature_initial_detail_changed_files",
    "feature_initial_detail_additions",
    "feature_initial_detail_deletions",
    "feature_initial_detail_churn",
    "feature_initial_detail_added_files",
    "feature_initial_detail_modified_files",
    "feature_initial_detail_removed_files",
    "feature_initial_detail_test_files",
]

FEATURE_SET_COLUMNS = {
    "defensible": (NUMERIC_FEATURES, CATEGORICAL_FEATURES),
    "full_with_timing_sensitive": (NUMERIC_FEATURES + TIMING_SENSITIVE_PR_API_FEATURES, CATEGORICAL_FEATURES),
    "text_repo_task": (TEXT_NUMERIC_FEATURES + REPO_TASK_NUMERIC_FEATURES, CATEGORICAL_FEATURES),
    "first_commit_only": (FIRST_COMMIT_NUMERIC_FEATURES, []),
}


def existing_columns(frame: pd.DataFrame, columns: list[str]) -> list[str]:
    return [col for col in columns if col in frame.columns]


def sorted_by_time(frame: pd.DataFrame) -> pd.DataFrame:
    if "created_at" not in frame.columns:
        return frame.sample(frac=1.0, random_state=23).reset_index(drop=True)
    return (
        frame.assign(_created=pd.to_datetime(frame["created_at"], errors="coerce", utc=True))
        .sort_values("_created", na_position="last")
        .drop(columns=["_created"])
        .reset_index(drop=True)
    )


def temporal_split(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    ordered = sorted_by_time(frame)
    train_end = int(0.6 * len(ordered))
    cal_end = int(0.8 * len(ordered))
    return ordered.iloc[:train_end].copy(), ordered.iloc[train_end:cal_end].copy(), ordered.iloc[cal_end:].copy()


def repository_disjoint_split(frame: pd.DataFrame, seed: int) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if "repo_id" not in frame.columns:
        return temporal_split(frame)
    groups = frame["repo_id"].fillna("__missing_repo__")
    first_split = GroupShuffleSplit(n_splits=1, test_size=0.4, random_state=seed)
    train_idx, tmp_idx = next(first_split.split(frame, groups=groups))
    train = frame.iloc[train_idx].copy()
    tmp = frame.iloc[tmp_idx].copy()

    second_split = GroupShuffleSplit(n_splits=1, test_size=0.5, random_state=seed + 1)
    tmp_groups = tmp["repo_id"].fillna("__missing_repo__")
    cal_local_idx, test_local_idx = next(second_split.split(tmp, groups=tmp_groups))
    calibration = tmp.iloc[cal_local_idx].copy()
    test = tmp.iloc[test_local_idx].copy()
    return train, calibration, test


def leave_one_agent_splits(frame: pd.DataFrame, min_test_rows: int) -> list[tuple[str, pd.DataFrame, pd.DataFrame, pd.DataFrame]]:
    if "agent" not in frame.columns:
        return []
    splits = []
    for agent, test in frame.groupby("agent", dropna=False):
        if len(test) < min_test_rows:
            continue
        train_cal = sorted_by_time(frame[frame["agent"] != agent].copy())
        if len(train_cal) < min_test_rows:
            continue
        train_end = int(0.75 * len(train_cal))
        train = train_cal.iloc[:train_end].copy()
        calibration = train_cal.iloc[train_end:].copy()
        splits.append((f"leave_agent_out:{agent}", train, calibration, sorted_by_time(test.copy())))
    return splits


def make_model(numeric_features: list[str], categorical_features: list[str]) -> Pipeline:
    numeric = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
    categorical = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore", min_frequency=20)),
        ]
    )
    preprocess = ColumnTransformer(
        transformers=[
            ("num", numeric, numeric_features),
            ("cat", categorical, categorical_features),
        ],
        remainder="drop",
    )
    classifier = LogisticRegression(max_iter=2000, class_weight="balanced", solver="lbfgs")
    return Pipeline(steps=[("preprocess", preprocess), ("classifier", classifier)])


def safe_auc(y_true: pd.Series, score: np.ndarray) -> float | None:
    if y_true.nunique(dropna=False) < 2:
        return None
    return float(roc_auc_score(y_true, score))


def safe_average_precision(y_true: pd.Series, score: np.ndarray) -> float | None:
    if y_true.nunique(dropna=False) < 2:
        return None
    return float(average_precision_score(y_true, score))


def threshold_for_risk_budget(scores: np.ndarray, high: pd.Series, budget: float) -> tuple[float, float, float]:
    order = np.argsort(scores)
    sorted_scores = scores[order]
    sorted_high = high.to_numpy(dtype=float)[order]
    counts = np.arange(1, len(sorted_scores) + 1)
    accepted_high_rate = np.cumsum(sorted_high) / counts
    valid = np.flatnonzero(accepted_high_rate <= budget)
    if len(valid) == 0:
        return float("-inf"), 0.0, 0.0
    idx = int(valid[-1])
    return float(sorted_scores[idx]), float((idx + 1) / len(sorted_scores)), float(accepted_high_rate[idx])


def decision_metrics(prefix: str, scores: np.ndarray, high: pd.Series, workload: pd.Series, threshold: float) -> dict:
    accepted = scores <= threshold
    rejected = ~accepted
    high_arr = high.to_numpy(dtype=bool)
    workload_arr = workload.to_numpy(dtype=float)
    accepted_count = int(accepted.sum())
    rejected_count = int(rejected.sum())
    high_count = int(high_arr.sum())
    intercepted_high = int((rejected & high_arr).sum())
    accepted_high = int((accepted & high_arr).sum())
    rejected_workload = float(workload_arr[rejected].sum())
    total_workload = float(workload_arr.sum())

    return {
        f"{prefix}_rows": int(len(high)),
        f"{prefix}_acceptance_rate": float(accepted.mean()) if len(accepted) else 0.0,
        f"{prefix}_abstention_rate": float(rejected.mean()) if len(rejected) else 0.0,
        f"{prefix}_high_workload_rate": float(high_arr.mean()) if len(high_arr) else 0.0,
        f"{prefix}_accepted_high_workload_rate": float(accepted_high / accepted_count) if accepted_count else 0.0,
        f"{prefix}_high_workload_recall_by_abstention": float(intercepted_high / high_count) if high_count else 0.0,
        f"{prefix}_abstention_precision_for_high_workload": float(intercepted_high / rejected_count) if rejected_count else 0.0,
        f"{prefix}_mean_workload_accepted": float(workload_arr[accepted].mean()) if accepted_count else 0.0,
        f"{prefix}_mean_workload_abstained": float(workload_arr[rejected].mean()) if rejected_count else 0.0,
        f"{prefix}_workload_share_abstained": float(rejected_workload / total_workload) if total_workload > 0 else 0.0,
    }


def evaluate_split(
    split_name: str,
    train: pd.DataFrame,
    calibration: pd.DataFrame,
    test: pd.DataFrame,
    target_col: str,
    workload_col: str,
    high_quantile: float,
    accept_rates: list[float],
    risk_budgets: list[float],
    numeric_feature_names: list[str] | None = None,
    categorical_feature_names: list[str] | None = None,
) -> list[dict]:
    numeric_source = NUMERIC_FEATURES if numeric_feature_names is None else numeric_feature_names
    categorical_source = CATEGORICAL_FEATURES if categorical_feature_names is None else categorical_feature_names
    numeric_features = existing_columns(train, numeric_source)
    categorical_features = existing_columns(train, categorical_source)
    features = numeric_features + categorical_features
    if not features:
        raise ValueError("No proposal-time features are available for gate evaluation.")

    high_threshold = float(train[target_col].quantile(high_quantile))
    train_high = train[target_col] >= high_threshold
    cal_high = calibration[target_col] >= high_threshold
    test_high = test[target_col] >= high_threshold
    if train_high.nunique(dropna=False) < 2:
        raise ValueError(f"Split {split_name} has only one training class for high-workload target.")

    model = make_model(numeric_features, categorical_features)
    model.fit(train[features], train_high)
    cal_scores = model.predict_proba(calibration[features])[:, 1]
    test_scores = model.predict_proba(test[features])[:, 1]

    base = {
        "split": split_name,
        "train_rows": int(len(train)),
        "calibration_rows": int(len(calibration)),
        "test_rows": int(len(test)),
        "target": target_col,
        "workload": workload_col,
        "high_workload_quantile": high_quantile,
        "high_workload_threshold": high_threshold,
        "test_auc": safe_auc(test_high, test_scores),
        "test_average_precision": safe_average_precision(test_high, test_scores),
        "test_brier": float(brier_score_loss(test_high, test_scores)),
        "features": ",".join(features),
    }

    rows = []
    for accept_rate in accept_rates:
        threshold = float(np.quantile(cal_scores, max(min(accept_rate, 1.0), 0.0)))
        row = {
            **base,
            "selector": "fixed_acceptance",
            "selector_value": accept_rate,
            "score_threshold": threshold,
        }
        row.update(decision_metrics("calibration", cal_scores, cal_high, calibration[workload_col], threshold))
        row.update(decision_metrics("test", test_scores, test_high, test[workload_col], threshold))
        rows.append(row)

    for budget in risk_budgets:
        threshold, cal_acceptance, cal_risk = threshold_for_risk_budget(cal_scores, cal_high, budget)
        row = {
            **base,
            "selector": "calibration_risk_budget",
            "selector_value": budget,
            "score_threshold": threshold,
            "calibrated_acceptance_target": cal_acceptance,
            "calibrated_accepted_high_rate": cal_risk,
        }
        row.update(decision_metrics("calibration", cal_scores, cal_high, calibration[workload_col], threshold))
        row.update(decision_metrics("test", test_scores, test_high, test[workload_col], threshold))
        rows.append(row)

    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate calibrated AIDev downstream-workload gates across realistic splits.")
    parser.add_argument("--features", type=Path, default=RESULTS_DIR / "aidev_pr_level_features.csv")
    parser.add_argument("--output-dir", type=Path, default=RESULTS_DIR)
    parser.add_argument("--target", default="outcome_downstream_workload_log")
    parser.add_argument("--workload", default="outcome_downstream_workload_raw")
    parser.add_argument("--high-workload-quantile", type=float, default=0.80)
    parser.add_argument("--accept-rates", nargs="*", type=float, default=[0.2, 0.4, 0.6, 0.8])
    parser.add_argument("--risk-budgets", nargs="*", type=float, default=[0.05, 0.10, 0.15])
    parser.add_argument("--min-agent-test-rows", type=int, default=300)
    parser.add_argument("--seed", type=int, default=23)
    args = parser.parse_args()

    frame = pd.read_csv(args.features)
    frame = frame.dropna(subset=[args.target, args.workload]).copy()
    for col in existing_columns(frame, NUMERIC_FEATURES):
        frame[col] = pd.to_numeric(frame[col], errors="coerce")
    for col in existing_columns(frame, CATEGORICAL_FEATURES):
        frame[col] = frame[col].fillna("").astype(str)

    split_specs: list[tuple[str, pd.DataFrame, pd.DataFrame, pd.DataFrame]] = [
        ("temporal", *temporal_split(frame)),
        ("repository_disjoint", *repository_disjoint_split(frame, args.seed)),
    ]
    split_specs.extend(leave_one_agent_splits(frame, args.min_agent_test_rows))

    rows = []
    for split_name, train, calibration, test in split_specs:
        rows.extend(
            evaluate_split(
                split_name,
                train,
                calibration,
                test,
                args.target,
                args.workload,
                args.high_workload_quantile,
                args.accept_rates,
                args.risk_budgets,
            )
        )

    output_dir = ensure_dir(args.output_dir)
    out = pd.DataFrame(rows)
    csv_path = output_dir / "aidev_workload_gate_summary.csv"
    out.to_csv(csv_path, index=False)
    write_json(
        output_dir / "aidev_workload_gate_summary.json",
        {
            "output_csv": str(csv_path),
            "rows": len(rows),
            "splits": sorted(out["split"].unique().tolist()),
            "selectors": sorted(out["selector"].unique().tolist()),
        },
    )
    print(f"Wrote workload gate summary to {csv_path}")


if __name__ == "__main__":
    main()
