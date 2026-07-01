from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from .common import RESULTS_DIR, ensure_dir, write_json
from .evaluate_workload_gate import (
    FEATURE_SET_COLUMNS,
    evaluate_split,
    existing_columns,
    repository_disjoint_split,
    temporal_split,
)


FEATURE_SET_LABELS = {
    "defensible": "Defensible proposal evidence",
    "full_with_timing_sensitive": "Full with timing-sensitive PR aggregates",
    "text_repo_task": "Text, repository, and task only",
    "first_commit_only": "First observed commit details only",
}


def prepare_frame(path: Path, target_col: str, workload_col: str) -> pd.DataFrame:
    frame = pd.read_csv(path)
    frame = frame.dropna(subset=[target_col, workload_col]).copy()
    numeric_candidates: set[str] = set()
    categorical_candidates: set[str] = set()
    for numeric_features, categorical_features in FEATURE_SET_COLUMNS.values():
        numeric_candidates.update(numeric_features)
        categorical_candidates.update(categorical_features)
    for col in existing_columns(frame, sorted(numeric_candidates) + [target_col, workload_col]):
        frame[col] = pd.to_numeric(frame[col], errors="coerce")
    for col in existing_columns(frame, sorted(categorical_candidates)):
        frame[col] = frame[col].fillna("").astype(str)
    return frame


def compact_table(summary: pd.DataFrame) -> pd.DataFrame:
    rows = summary[
        summary["split"].isin(["temporal", "repository_disjoint"])
        & summary["selector"].eq("calibration_risk_budget")
        & summary["selector_value"].eq(0.10)
    ].copy()
    rows["feature_set_label"] = rows["feature_set"].map(FEATURE_SET_LABELS).fillna(rows["feature_set"])
    rows["feature_count"] = rows["features"].fillna("").map(lambda text: 0 if text == "" else len(text.split(",")))
    keep = [
        "split",
        "feature_set",
        "feature_set_label",
        "feature_count",
        "test_auc",
        "test_average_precision",
        "test_high_workload_rate",
        "test_acceptance_rate",
        "test_accepted_high_workload_rate",
        "test_high_workload_recall_by_abstention",
        "test_workload_share_abstained",
        "features",
    ]
    return rows[keep].sort_values(["split", "feature_set"]).reset_index(drop=True)


def markdown_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "_No rows._"
    display = frame.copy()
    display["split"] = display["split"].replace({"repository_disjoint": "Unseen repository", "temporal": "Temporal"})
    cols = [
        "split",
        "feature_set_label",
        "feature_count",
        "test_auc",
        "test_average_precision",
        "test_acceptance_rate",
        "test_accepted_high_workload_rate",
        "test_high_workload_recall_by_abstention",
    ]
    lines = [
        "| Split | Feature set | Features | AUC | AP | Accept | High if accepted | High-workload recall by routing |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for _, row in display[cols].iterrows():
        lines.append(
            "| {split} | {feature_set_label} | {feature_count:d} | {test_auc:.3f} | {test_average_precision:.3f} | {test_acceptance_rate:.3f} | {test_accepted_high_workload_rate:.3f} | {test_high_workload_recall_by_abstention:.3f} |".format(
                **row.to_dict()
            )
        )
    return "\n".join(lines)


def write_report(path: Path, table: pd.DataFrame) -> None:
    lines = [
        "# AIDev Feature Boundary Ablation",
        "",
        "This analysis checks whether the main gate depends on timing-sensitive pull-request API aggregate fields. The manuscript-facing gate uses the defensible proposal-evidence set. The full feature set includes PR API aggregates whose exact snapshot timing is not established by the public AIDev schema, so it is diagnostic only.",
        "",
        markdown_table(table),
        "",
        "## Claim Guidance",
        "",
        "- Allowed: the main result is based on the defensible proposal-evidence set, not on timing-sensitive PR API aggregates.",
        "- Allowed: the full feature set is an upper-bound diagnostic if those aggregate fields are available as initial snapshots in a deployment.",
        "- Not allowed: using the full feature set as primary evidence without proving aggregate field timing.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Ablate defensible and timing-sensitive AIDev gate feature sets.")
    parser.add_argument("--features", type=Path, default=RESULTS_DIR / "aidev_pr_level_features.csv")
    parser.add_argument("--output-dir", type=Path, default=RESULTS_DIR)
    parser.add_argument("--target", default="outcome_downstream_workload_log")
    parser.add_argument("--workload", default="outcome_downstream_workload_raw")
    parser.add_argument("--high-workload-quantile", type=float, default=0.80)
    parser.add_argument("--risk-budget", type=float, default=0.10)
    parser.add_argument("--seed", type=int, default=23)
    args = parser.parse_args()

    frame = prepare_frame(args.features, args.target, args.workload)
    split_specs: list[tuple[str, pd.DataFrame, pd.DataFrame, pd.DataFrame]] = [
        ("temporal", *temporal_split(frame)),
        ("repository_disjoint", *repository_disjoint_split(frame, args.seed)),
    ]

    rows = []
    for feature_set, (numeric_features, categorical_features) in FEATURE_SET_COLUMNS.items():
        for split_name, train, calibration, test in split_specs:
            split_rows = evaluate_split(
                split_name,
                train,
                calibration,
                test,
                args.target,
                args.workload,
                args.high_workload_quantile,
                accept_rates=[],
                risk_budgets=[args.risk_budget],
                numeric_feature_names=numeric_features,
                categorical_feature_names=categorical_features,
            )
            for row in split_rows:
                row["feature_set"] = feature_set
            rows.extend(split_rows)

    output_dir = ensure_dir(args.output_dir)
    summary = pd.DataFrame(rows)
    table = compact_table(summary)
    summary_path = output_dir / "aidev_feature_boundary_ablation.csv"
    table_path = output_dir / "aidev_feature_boundary_ablation_table.csv"
    report_path = output_dir / "aidev_feature_boundary_ablation_report.md"
    summary.to_csv(summary_path, index=False)
    table.to_csv(table_path, index=False)
    write_report(report_path, table)
    write_json(
        output_dir / "aidev_feature_boundary_ablation.json",
        {
            "summary_csv": str(summary_path),
            "table_csv": str(table_path),
            "report_md": str(report_path),
            "feature_sets": sorted(FEATURE_SET_COLUMNS),
            "risk_budget": args.risk_budget,
        },
    )
    print(f"Wrote feature boundary ablation to {table_path}")


if __name__ == "__main__":
    main()
