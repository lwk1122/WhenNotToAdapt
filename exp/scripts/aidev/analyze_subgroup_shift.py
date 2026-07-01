from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from .bootstrap_gate_uncertainty import compute_metrics, prediction_frame, prepare_frame, split_frame
from .common import RESULTS_DIR, ensure_dir, write_json


SUBGROUP_COLUMNS = ["agent", "repo_language", "feature_task_type", "repo_star_bucket", "initial_churn_bucket"]
REPORT_METRICS = [
    "rows",
    "repositories",
    "high_workload_rate",
    "auc",
    "average_precision",
    "acceptance_rate",
    "accepted_high_workload_rate",
    "high_workload_recall_by_abstention",
    "workload_share_abstained",
    "mean_workload_accepted",
    "mean_workload_abstained",
]


def add_bucket_columns(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    if "feature_repo_stars" in out.columns:
        stars = pd.to_numeric(out["feature_repo_stars"], errors="coerce").fillna(0.0)
        out["repo_star_bucket"] = pd.cut(
            stars,
            bins=[-0.1, 10, 100, 1000, np.inf],
            labels=["0-10", "11-100", "101-1000", ">1000"],
        ).astype(str)
    else:
        out["repo_star_bucket"] = "unknown"

    if "feature_initial_detail_churn" in out.columns:
        churn = pd.to_numeric(out["feature_initial_detail_churn"], errors="coerce").fillna(0.0)
    elif "feature_churn" in out.columns:
        churn = pd.to_numeric(out["feature_churn"], errors="coerce").fillna(0.0)
    else:
        churn = pd.Series(np.zeros(len(out)), index=out.index)
    out["initial_churn_bucket"] = pd.cut(
        churn,
        bins=[-0.1, 0, 50, 250, 1000, np.inf],
        labels=["0", "1-50", "51-250", "251-1000", ">1000"],
    ).astype(str)
    return out


def prediction_with_subgroups(
    split_name: str,
    train: pd.DataFrame,
    calibration: pd.DataFrame,
    test: pd.DataFrame,
    target_col: str,
    workload_col: str,
    high_quantile: float,
    risk_budget: float,
) -> tuple[pd.DataFrame, dict]:
    pred, metadata = prediction_frame(
        train,
        calibration,
        test,
        target_col,
        workload_col,
        high_quantile,
        risk_budget,
    )
    test_reset = add_bucket_columns(test).reset_index(drop=True)
    pred = pred.reset_index(drop=True)
    pred["split"] = split_name
    for col in SUBGROUP_COLUMNS:
        if col in test_reset.columns:
            pred[col] = test_reset[col].fillna("unknown").astype(str)
        else:
            pred[col] = "unknown"
    pred["accepted"] = pred["score"] <= metadata["score_threshold"]
    pred["abstained"] = ~pred["accepted"]
    return pred, metadata


def summarize_group(
    split: str,
    subgroup_type: str,
    subgroup_value: str,
    group: pd.DataFrame,
    threshold: float,
    risk_budget: float,
    min_rows: int,
    min_high: int,
    min_accepted_for_risk: int,
) -> dict:
    metrics = compute_metrics(group, threshold)
    high_count = int(group["high"].sum())
    accepted = group["score"].to_numpy(dtype=float) <= threshold
    accepted_count = int(accepted.sum())
    accepted_high_count = int((accepted & group["high"].to_numpy(dtype=bool)).sum())
    raw_over_budget = bool(metrics["accepted_high_workload_rate"] > risk_budget) if accepted_count else False
    row = {
        "split": split,
        "subgroup_type": subgroup_type,
        "subgroup_value": subgroup_value,
        "rows": int(len(group)),
        "repositories": int(group["repo_id"].nunique()),
        "high_count": high_count,
        "accepted_count": accepted_count,
        "accepted_high_count": accepted_high_count,
        "risk_budget": risk_budget,
        "score_threshold": threshold,
        "eligible_for_auc": bool(len(group) >= min_rows and high_count >= min_high and high_count < len(group)),
        "accepted_risk_over_budget_raw": raw_over_budget,
        "risk_over_budget": bool(raw_over_budget and accepted_count >= min_accepted_for_risk),
        "risk_flag_note": "enough accepted rows" if accepted_count >= min_accepted_for_risk else "low accepted rows",
    }
    row.update(metrics)
    return row


def subgroup_summary(
    pred: pd.DataFrame,
    metadata: dict,
    split: str,
    risk_budget: float,
    min_rows: int,
    min_high: int,
    min_accepted_for_risk: int,
) -> pd.DataFrame:
    rows = []
    threshold = float(metadata["score_threshold"])
    for subgroup_type in SUBGROUP_COLUMNS:
        for subgroup_value, group in pred.groupby(subgroup_type, dropna=False):
            if len(group) < min_rows:
                continue
            rows.append(
                summarize_group(
                    split,
                    subgroup_type,
                    str(subgroup_value),
                    group.reset_index(drop=True),
                    threshold,
                    risk_budget,
                    min_rows,
                    min_high,
                    min_accepted_for_risk,
                )
            )
    return pd.DataFrame(rows).sort_values(["split", "subgroup_type", "rows"], ascending=[True, True, False])


def compact_table(summary: pd.DataFrame) -> pd.DataFrame:
    if summary.empty:
        return summary
    cols = [
        "split",
        "subgroup_type",
        "subgroup_value",
        "rows",
        "repositories",
        "accepted_count",
        "accepted_high_count",
        "high_workload_rate",
        "acceptance_rate",
        "accepted_high_workload_rate",
        "risk_over_budget",
        "accepted_risk_over_budget_raw",
        "risk_flag_note",
        "high_workload_recall_by_abstention",
        "workload_share_abstained",
        "auc",
    ]
    return summary[cols].copy()


def format_value(value: object) -> str:
    if pd.isna(value):
        return ""
    if isinstance(value, (float, np.floating)):
        return f"{float(value):.3f}"
    if isinstance(value, (bool, np.bool_)):
        return "yes" if bool(value) else "no"
    return str(value).replace("|", "\\|")


def markdown_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "_No rows._"
    headers = list(frame.columns)
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for _, row in frame.iterrows():
        lines.append("| " + " | ".join(format_value(row[col]) for col in headers) + " |")
    return "\n".join(lines)


def display_frame(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    if "split" in out.columns:
        out["split"] = out["split"].replace({"repository_disjoint": "Unseen repository", "temporal": "Temporal"})
    if "subgroup_type" in out.columns:
        out["subgroup_type"] = out["subgroup_type"].replace(
            {
                "agent": "agent",
                "repo_language": "repository language",
                "repo_star_bucket": "repository stars",
                "feature_task_type": "task type",
                "initial_churn_bucket": "initial churn",
            }
        )
    return out.rename(
        columns={
            "subgroup_type": "subgroup",
            "subgroup_value": "value",
            "accepted_count": "accepted PRs",
            "accepted_high_count": "accepted high workload PRs",
            "high_workload_rate": "high workload rate",
            "acceptance_rate": "acceptance rate",
            "accepted_high_workload_rate": "accepted high workload rate",
            "risk_over_budget": "above budget",
            "accepted_risk_over_budget_raw": "raw above budget",
            "risk_flag_note": "flag note",
            "high_workload_recall_by_abstention": "high workload recall by routing",
            "workload_share_abstained": "workload share routed",
            "mean_workload_accepted": "mean workload accepted",
            "mean_workload_abstained": "mean workload routed",
        }
    )


def report_tables(summary: pd.DataFrame, min_rows: int) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    display = compact_table(summary)
    if display.empty:
        return display, display, display

    risk_flags = display[display["risk_over_budget"]].sort_values(
        ["split", "accepted_high_workload_rate", "rows"],
        ascending=[True, False, False],
    )
    low_coverage = display.sort_values(["split", "acceptance_rate", "rows"], ascending=[True, True, False])
    largest_groups = display[display["rows"] >= min_rows].sort_values(["split", "rows"], ascending=[True, False])
    return risk_flags.head(20), low_coverage.head(20), largest_groups.head(20)


def write_report(summary: pd.DataFrame, report_path: Path, min_rows: int) -> None:
    risk_flags, low_coverage, largest_groups = report_tables(summary, min_rows)
    lines = [
        "# AIDev Subgroup and Shift Diagnostics",
        "",
        "This report evaluates the global 0.10 risk setting for the workload gate within separate test subgroups. Subgroups are diagnostic only: the gate is calibrated globally, so subgroup accepted high workload rates are not guaranteed to stay below 0.10. Budget flags require enough accepted rows; raw over budget indicators with very small accepted counts should be treated as unstable diagnostics.",
        "",
        "## Main Diagnostic Questions",
        "",
        "- Which agents, languages, task types, repository size buckets, or initial churn buckets exceed the global accepted high workload budget?",
        "- Where does the gate become especially conservative by accepting few PRs?",
        "- Which large subgroups dominate the held-out evidence?",
        "",
        "## Subgroups Above the Global Risk Budget",
        "",
        markdown_table(display_frame(risk_flags)),
        "",
        "## Lowest Coverage Subgroups",
        "",
        markdown_table(display_frame(low_coverage)),
        "",
        "## Largest Held Out Subgroups",
        "",
        markdown_table(display_frame(largest_groups)),
        "",
        "## Claim Guidance",
        "",
        "- Allowed: the global gate is not uniformly calibrated across all subgroups; subgroup diagnostics identify where local or online calibration is needed.",
        "- Allowed: unseen repository shift concentrates high workload and conservative routing in specific agents/languages/task types.",
        "- Not allowed: subgroup differences prove causal differences in agent quality or repository difficulty. AIDev is observational and confounded.",
        "",
    ]
    report_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze subgroup behavior of the main AIDev workload gate.")
    parser.add_argument("--features", type=Path, default=RESULTS_DIR / "aidev_pr_level_features.csv")
    parser.add_argument("--output-dir", type=Path, default=RESULTS_DIR)
    parser.add_argument("--target", default="outcome_downstream_workload_log")
    parser.add_argument("--workload", default="outcome_downstream_workload_raw")
    parser.add_argument("--high-workload-quantile", type=float, default=0.80)
    parser.add_argument("--risk-budget", type=float, default=0.10)
    parser.add_argument("--splits", nargs="*", default=["temporal", "repository_disjoint"])
    parser.add_argument("--min-rows", type=int, default=100)
    parser.add_argument("--min-high", type=int, default=5)
    parser.add_argument("--min-accepted-for-risk", type=int, default=30)
    parser.add_argument("--seed", type=int, default=23)
    args = parser.parse_args()

    frame = prepare_frame(args.features, args.target, args.workload)
    rows = []
    prediction_rows = []
    for split_name in args.splits:
        train, calibration, test = split_frame(frame, split_name, args.seed)
        pred, metadata = prediction_with_subgroups(
            split_name,
            train,
            calibration,
            test,
            args.target,
            args.workload,
            args.high_workload_quantile,
            args.risk_budget,
        )
        prediction_rows.append(pred)
        split_summary = subgroup_summary(
            pred,
            metadata,
            split_name,
            args.risk_budget,
            args.min_rows,
            args.min_high,
            args.min_accepted_for_risk,
        )
        rows.append(split_summary)

    summary = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
    predictions = pd.concat(prediction_rows, ignore_index=True) if prediction_rows else pd.DataFrame()

    output_dir = ensure_dir(args.output_dir)
    summary_path = output_dir / "aidev_subgroup_gate_summary.csv"
    compact_path = output_dir / "aidev_subgroup_gate_table.csv"
    pred_path = output_dir / "aidev_subgroup_gate_predictions.csv"
    report_path = output_dir / "aidev_subgroup_gate_report.md"

    summary.to_csv(summary_path, index=False)
    compact_table(summary).to_csv(compact_path, index=False)
    predictions.to_csv(pred_path, index=False)
    write_report(summary, report_path, args.min_rows)
    write_json(
        output_dir / "aidev_subgroup_gate_summary.json",
        {
            "summary_csv": str(summary_path),
            "compact_csv": str(compact_path),
            "predictions_csv": str(pred_path),
            "report": str(report_path),
            "rows": int(len(summary)),
            "prediction_rows": int(len(predictions)),
            "splits": list(args.splits),
            "risk_budget": args.risk_budget,
            "min_rows": args.min_rows,
            "min_high": args.min_high,
            "min_accepted_for_risk": args.min_accepted_for_risk,
        },
    )
    print(f"Wrote subgroup gate summary to {summary_path}")
    print(f"Wrote subgroup gate report to {report_path}")


if __name__ == "__main__":
    main()
