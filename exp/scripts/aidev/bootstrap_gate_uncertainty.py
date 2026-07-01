from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score

from .common import RESULTS_DIR, ensure_dir, write_json
from .evaluate_workload_gate import (
    CATEGORICAL_FEATURES,
    NUMERIC_FEATURES,
    existing_columns,
    make_model,
    repository_disjoint_split,
    threshold_for_risk_budget,
    temporal_split,
)


MAIN_METRICS = [
    "auc",
    "average_precision",
    "brier",
    "high_workload_rate",
    "acceptance_rate",
    "accepted_high_workload_rate",
    "high_workload_recall_by_abstention",
    "abstention_precision_for_high_workload",
    "mean_workload_accepted",
    "mean_workload_abstained",
    "workload_share_abstained",
]


def prepare_frame(features_path: Path, target_col: str, workload_col: str) -> pd.DataFrame:
    frame = pd.read_csv(features_path)
    frame = frame.dropna(subset=[target_col, workload_col]).copy()
    for col in existing_columns(frame, NUMERIC_FEATURES):
        frame[col] = pd.to_numeric(frame[col], errors="coerce")
    for col in existing_columns(frame, CATEGORICAL_FEATURES):
        frame[col] = frame[col].fillna("").astype(str)
    return frame


def split_frame(frame: pd.DataFrame, split_name: str, seed: int) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if split_name == "temporal":
        return temporal_split(frame)
    if split_name == "repository_disjoint":
        return repository_disjoint_split(frame, seed)
    raise ValueError(f"Unsupported split: {split_name}")


def safe_auc(y_true: np.ndarray, scores: np.ndarray) -> float:
    if len(np.unique(y_true)) < 2:
        return float("nan")
    return float(roc_auc_score(y_true, scores))


def safe_average_precision(y_true: np.ndarray, scores: np.ndarray) -> float:
    if len(np.unique(y_true)) < 2:
        return float("nan")
    return float(average_precision_score(y_true, scores))


def prediction_frame(
    train: pd.DataFrame,
    calibration: pd.DataFrame,
    test: pd.DataFrame,
    target_col: str,
    workload_col: str,
    high_quantile: float,
    risk_budget: float,
) -> tuple[pd.DataFrame, dict]:
    numeric_features = existing_columns(train, NUMERIC_FEATURES)
    categorical_features = existing_columns(train, CATEGORICAL_FEATURES)
    features = numeric_features + categorical_features
    if not features:
        raise ValueError("No proposal time features are available for uncertainty analysis.")

    high_threshold = float(train[target_col].quantile(high_quantile))
    train_high = train[target_col] >= high_threshold
    cal_high = calibration[target_col] >= high_threshold
    if train_high.nunique(dropna=False) < 2:
        raise ValueError("Training split has only one high-workload class.")

    model = make_model(numeric_features, categorical_features)
    model.fit(train[features], train_high)

    cal_scores = model.predict_proba(calibration[features])[:, 1]
    threshold, cal_acceptance, cal_risk = threshold_for_risk_budget(cal_scores, cal_high, risk_budget)
    test_scores = model.predict_proba(test[features])[:, 1]
    test_high = (test[target_col] >= high_threshold).to_numpy(dtype=bool)

    pred = pd.DataFrame(
        {
            "repo_id": test["repo_id"].fillna("__missing_repo__").astype(str).to_numpy()
            if "repo_id" in test.columns
            else np.array(["__all__"] * len(test)),
            "score": test_scores,
            "high": test_high,
            "workload": pd.to_numeric(test[workload_col], errors="coerce").fillna(0.0).to_numpy(dtype=float),
        }
    )
    metadata = {
        "features": ",".join(features),
        "high_workload_threshold": high_threshold,
        "score_threshold": threshold,
        "calibrated_acceptance_target": cal_acceptance,
        "calibrated_accepted_high_rate": cal_risk,
    }
    return pred, metadata


def compute_metrics(pred: pd.DataFrame, threshold: float) -> dict[str, float]:
    scores = pred["score"].to_numpy(dtype=float)
    high = pred["high"].to_numpy(dtype=bool)
    workload = pred["workload"].to_numpy(dtype=float)
    accepted = scores <= threshold
    rejected = ~accepted

    accepted_count = int(accepted.sum())
    rejected_count = int(rejected.sum())
    high_count = int(high.sum())
    accepted_high = int((accepted & high).sum())
    intercepted_high = int((rejected & high).sum())
    total_workload = float(workload.sum())
    rejected_workload = float(workload[rejected].sum())

    return {
        "auc": safe_auc(high, scores),
        "average_precision": safe_average_precision(high, scores),
        "brier": float(brier_score_loss(high, scores)) if len(np.unique(high)) >= 2 else float("nan"),
        "high_workload_rate": float(high.mean()) if len(high) else float("nan"),
        "acceptance_rate": float(accepted.mean()) if len(accepted) else float("nan"),
        "accepted_high_workload_rate": float(accepted_high / accepted_count) if accepted_count else 0.0,
        "high_workload_recall_by_abstention": float(intercepted_high / high_count) if high_count else 0.0,
        "abstention_precision_for_high_workload": float(intercepted_high / rejected_count) if rejected_count else 0.0,
        "mean_workload_accepted": float(workload[accepted].mean()) if accepted_count else 0.0,
        "mean_workload_abstained": float(workload[rejected].mean()) if rejected_count else 0.0,
        "workload_share_abstained": float(rejected_workload / total_workload) if total_workload > 0 else 0.0,
    }


def bootstrap_indices(pred: pd.DataFrame, rng: np.random.Generator, unit: str) -> np.ndarray:
    if unit == "row":
        return rng.integers(0, len(pred), size=len(pred))

    if unit != "repo":
        raise ValueError(f"Unsupported bootstrap unit: {unit}")

    groups = pred["repo_id"].fillna("__missing_repo__").astype(str).to_numpy()
    unique_groups = np.unique(groups)
    group_indices = {group: np.flatnonzero(groups == group) for group in unique_groups}
    sampled_groups = rng.choice(unique_groups, size=len(unique_groups), replace=True)
    return np.concatenate([group_indices[group] for group in sampled_groups])


def summarize_bootstrap(
    split: str,
    pred: pd.DataFrame,
    threshold: float,
    risk_budget: float,
    bootstrap_unit: str,
    bootstrap_rounds: int,
    seed: int,
    metadata: dict,
) -> list[dict]:
    rng = np.random.default_rng(seed)
    point = compute_metrics(pred, threshold)
    draws = {metric: [] for metric in MAIN_METRICS}

    for _ in range(bootstrap_rounds):
        idx = bootstrap_indices(pred, rng, bootstrap_unit)
        sample = pred.iloc[idx].reset_index(drop=True)
        metrics = compute_metrics(sample, threshold)
        for metric in MAIN_METRICS:
            draws[metric].append(metrics[metric])

    rows = []
    for metric in MAIN_METRICS:
        values = np.asarray(draws[metric], dtype=float)
        valid = values[np.isfinite(values)]
        ci_low = float(np.quantile(valid, 0.025)) if len(valid) else float("nan")
        ci_high = float(np.quantile(valid, 0.975)) if len(valid) else float("nan")
        rows.append(
            {
                "split": split,
                "selector": "calibration_risk_budget",
                "risk_budget": risk_budget,
                "bootstrap_unit": bootstrap_unit,
                "bootstrap_rounds": bootstrap_rounds,
                "bootstrap_valid_rounds": int(len(valid)),
                "test_rows": int(len(pred)),
                "test_repositories": int(pred["repo_id"].nunique()),
                "metric": metric,
                "point": point[metric],
                "ci_low": ci_low,
                "ci_high": ci_high,
                **metadata,
            }
        )
    return rows


def format_ci(point: float, low: float, high: float) -> str:
    return f"{point:.3f} [{low:.3f}, {high:.3f}]"


def write_report(summary: pd.DataFrame, path: Path) -> None:
    display_metrics = [
        "auc",
        "average_precision",
        "high_workload_rate",
        "acceptance_rate",
        "accepted_high_workload_rate",
        "high_workload_recall_by_abstention",
        "mean_workload_accepted",
        "mean_workload_abstained",
        "workload_share_abstained",
    ]
    labels = {
        "auc": "AUC",
        "average_precision": "Average precision",
        "high_workload_rate": "High workload base rate",
        "acceptance_rate": "Acceptance rate",
        "accepted_high_workload_rate": "Accepted high workload rate",
        "high_workload_recall_by_abstention": "High workload recall by routing",
        "mean_workload_accepted": "Mean workload, accepted",
        "mean_workload_abstained": "Mean workload, routed",
        "workload_share_abstained": "Workload share routed",
    }

    lines = [
        "# AIDev Gate Uncertainty Report",
        "",
        "This report adds repository cluster bootstrap uncertainty intervals to the main AIDev workload gate results. It reuses the same proposal time feature set, train/calibration/test split logic, logistic gate, and 0.10 calibration risk setting as the main AIDev gate analysis.",
        "",
        "The bootstrap resamples repositories with replacement within the held-out test split. Intervals therefore describe test-set uncertainty under repository-level dependence; they do not turn the observational AIDev study into a causal policy-effect experiment.",
        "",
        "## Main Metrics",
        "",
        "| Split | Metric | Point estimate and 95% cluster bootstrap CI |",
        "|---|---|---:|",
    ]
    for split in summary["split"].drop_duplicates():
        split_summary = summary[summary["split"] == split]
        for metric in display_metrics:
            row = split_summary[split_summary["metric"] == metric].iloc[0]
            split_label = "Unseen repository" if split == "repository_disjoint" else str(split).capitalize()
            lines.append(f"| {split_label} | {labels[metric]} | {format_ci(row['point'], row['ci_low'], row['ci_high'])} |")

    lines.extend(
        [
            "",
            "## Claim Guidance",
            "",
            "- Allowed: proposal time AIDev features show downstream workload signal under temporal and unseen repository splits, with uncertainty intervals around AUC, acceptance, accepted high workload rate, and workload routed to conservative handling.",
            "- Allowed: unseen repository evaluation remains more conservative than temporal evaluation, with lower acceptance and higher workload routed to conservative handling.",
            "- Not allowed: the AIDev gate causally reduces resource use or downstream rework for the same task. That requires the controlled runtime experiment.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute repository cluster bootstrap CIs for main AIDev gate metrics.")
    parser.add_argument("--features", type=Path, default=RESULTS_DIR / "aidev_pr_level_features.csv")
    parser.add_argument("--output-dir", type=Path, default=RESULTS_DIR)
    parser.add_argument("--target", default="outcome_downstream_workload_log")
    parser.add_argument("--workload", default="outcome_downstream_workload_raw")
    parser.add_argument("--high-workload-quantile", type=float, default=0.80)
    parser.add_argument("--risk-budget", type=float, default=0.10)
    parser.add_argument("--splits", nargs="*", default=["temporal", "repository_disjoint"])
    parser.add_argument("--bootstrap-unit", choices=["repo", "row"], default="repo")
    parser.add_argument("--bootstrap-rounds", type=int, default=500)
    parser.add_argument("--seed", type=int, default=23)
    args = parser.parse_args()

    frame = prepare_frame(args.features, args.target, args.workload)
    rows = []
    for offset, split_name in enumerate(args.splits):
        train, calibration, test = split_frame(frame, split_name, args.seed)
        pred, metadata = prediction_frame(
            train,
            calibration,
            test,
            args.target,
            args.workload,
            args.high_workload_quantile,
            args.risk_budget,
        )
        rows.extend(
            summarize_bootstrap(
                split_name,
                pred,
                metadata["score_threshold"],
                args.risk_budget,
                args.bootstrap_unit,
                args.bootstrap_rounds,
                args.seed + 1000 * offset,
                metadata,
            )
        )

    output_dir = ensure_dir(args.output_dir)
    summary = pd.DataFrame(rows)
    csv_path = output_dir / "aidev_gate_uncertainty_summary.csv"
    report_path = output_dir / "aidev_gate_uncertainty_report.md"
    summary.to_csv(csv_path, index=False)
    write_report(summary, report_path)
    write_json(
        output_dir / "aidev_gate_uncertainty_summary.json",
        {
            "output_csv": str(csv_path),
            "output_report": str(report_path),
            "rows": int(len(summary)),
            "splits": list(args.splits),
            "risk_budget": args.risk_budget,
            "bootstrap_unit": args.bootstrap_unit,
            "bootstrap_rounds": args.bootstrap_rounds,
        },
    )
    print(f"Wrote AIDev gate uncertainty summary to {csv_path}")
    print(f"Wrote AIDev gate uncertainty report to {report_path}")


if __name__ == "__main__":
    main()
