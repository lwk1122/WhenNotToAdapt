from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from .common import RESULTS_DIR, ensure_dir, write_json
from .evaluate_workload_gate import (
    CATEGORICAL_FEATURES,
    NUMERIC_FEATURES,
    evaluate_split,
    existing_columns,
    repository_disjoint_split,
    temporal_split,
)


@dataclass(frozen=True)
class WorkloadDefinition:
    name: str
    description: str
    raw_column: str
    target_column: str


def numeric(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame.columns:
        return pd.Series(np.zeros(len(frame), dtype=float), index=frame.index)
    return pd.to_numeric(frame[column], errors="coerce").fillna(0.0).astype(float)


def add_workload_definitions(frame: pd.DataFrame) -> tuple[pd.DataFrame, list[WorkloadDefinition]]:
    out = frame.copy()
    definitions = [
        WorkloadDefinition(
            name="aggregate_main",
            description="Original review, reviews requesting changes, comment, and later commit workload.",
            raw_column="sensitivity_aggregate_main_raw",
            target_column="sensitivity_aggregate_main_log",
        ),
        WorkloadDefinition(
            name="communication_review",
            description="Reviews, request changes, inline review comments, and issue comments.",
            raw_column="sensitivity_communication_review_raw",
            target_column="sensitivity_communication_review_log",
        ),
        WorkloadDefinition(
            name="human_review",
            description="Human reviews, request changes, and inline review comments.",
            raw_column="sensitivity_human_review_raw",
            target_column="sensitivity_human_review_log",
        ),
        WorkloadDefinition(
            name="followup_revision",
            description="Later commits, changed files, test-like files, and log later churn.",
            raw_column="sensitivity_followup_revision_raw",
            target_column="sensitivity_followup_revision_log",
        ),
        WorkloadDefinition(
            name="broad_with_related",
            description="Original aggregate plus related issues and log later churn.",
            raw_column="sensitivity_broad_with_related_raw",
            target_column="sensitivity_broad_with_related_log",
        ),
    ]

    out["sensitivity_aggregate_main_raw"] = numeric(out, "outcome_downstream_workload_raw")
    out["sensitivity_communication_review_raw"] = (
        numeric(out, "outcome_review_count")
        + numeric(out, "outcome_request_changes_count")
        + numeric(out, "outcome_inline_review_comment_count")
        + numeric(out, "outcome_issue_comment_count")
    )
    out["sensitivity_human_review_raw"] = (
        numeric(out, "outcome_human_review_count")
        + numeric(out, "outcome_request_changes_count")
        + numeric(out, "outcome_inline_review_comment_count")
    )
    out["sensitivity_followup_revision_raw"] = (
        numeric(out, "outcome_followup_commit_count")
        + numeric(out, "outcome_followup_detail_changed_files")
        + numeric(out, "outcome_followup_detail_test_files")
        + np.log1p(numeric(out, "outcome_followup_detail_churn"))
    )
    out["sensitivity_broad_with_related_raw"] = (
        numeric(out, "outcome_downstream_workload_raw")
        + numeric(out, "outcome_related_issue_count")
        + np.log1p(numeric(out, "outcome_followup_detail_churn"))
    )

    for definition in definitions:
        out[definition.raw_column] = pd.to_numeric(out[definition.raw_column], errors="coerce").fillna(0.0).clip(lower=0.0)
        out[definition.target_column] = np.log1p(out[definition.raw_column])

    return out, definitions


def prepare_frame(features_path: Path) -> tuple[pd.DataFrame, list[WorkloadDefinition]]:
    frame = pd.read_csv(features_path)
    frame, definitions = add_workload_definitions(frame)
    for col in existing_columns(frame, NUMERIC_FEATURES):
        frame[col] = pd.to_numeric(frame[col], errors="coerce")
    for col in existing_columns(frame, CATEGORICAL_FEATURES):
        frame[col] = frame[col].fillna("").astype(str)
    return frame, definitions


def split_specs(frame: pd.DataFrame, seed: int) -> list[tuple[str, pd.DataFrame, pd.DataFrame, pd.DataFrame]]:
    return [
        ("temporal", *temporal_split(frame)),
        ("repository_disjoint", *repository_disjoint_split(frame, seed)),
    ]


def format_value(value: object) -> str:
    if pd.isna(value):
        return ""
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def frame_to_markdown(frame: pd.DataFrame) -> str:
    headers = list(frame.columns)
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for _, row in frame.iterrows():
        lines.append("| " + " | ".join(format_value(row[col]) for col in headers) + " |")
    return "\n".join(lines)


def readable_table(summary: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "split",
        "workload_definition",
        "high_workload_quantile",
        "test_rows",
        "test_auc",
        "test_average_precision",
        "test_high_workload_rate",
        "test_acceptance_rate",
        "test_accepted_high_workload_rate",
        "test_high_workload_recall_by_abstention",
        "test_mean_workload_accepted",
        "test_mean_workload_abstained",
        "test_workload_share_abstained",
    ]
    rename = {
        "workload_definition": "definition",
        "high_workload_quantile": "quantile",
        "test_rows": "n",
        "test_auc": "auc",
        "test_average_precision": "avg_precision",
        "test_high_workload_rate": "base_high_rate",
        "test_acceptance_rate": "accept_rate",
        "test_accepted_high_workload_rate": "accepted_high_rate",
        "test_high_workload_recall_by_abstention": "high_recall_routed",
        "test_mean_workload_accepted": "mean_workload_accepted",
        "test_mean_workload_abstained": "mean_workload_routed",
        "test_workload_share_abstained": "workload_share_routed",
    }
    return summary[[col for col in cols if col in summary.columns]].rename(columns=rename)


def write_report(summary: pd.DataFrame, skipped: list[dict], definitions: list[WorkloadDefinition], path: Path) -> None:
    compact = readable_table(summary)
    compact = compact.sort_values(["split", "definition", "quantile"]).reset_index(drop=True)
    compact["split"] = compact["split"].replace({"repository_disjoint": "Unseen repository", "temporal": "Temporal"})
    compact_display = compact.rename(
        columns={
            "avg_precision": "average precision",
            "base_high_rate": "base high workload rate",
            "accept_rate": "acceptance rate",
            "accepted_high_rate": "accepted high workload rate",
            "high_recall_routed": "high workload recall by routing",
            "mean_workload_accepted": "mean workload accepted",
            "mean_workload_routed": "mean workload routed",
            "workload_share_routed": "workload share routed",
        }
    )

    lines = [
        "# AIDev Workload Definition Sensitivity",
        "",
        "This diagnostic reruns the calibrated risk setting for the gate under alternative downstream workload definitions and high workload thresholds. It is observational evidence only; it does not estimate the causal effect of deploying the gate.",
        "",
        "## Workload Definitions",
    ]
    for definition in definitions:
        lines.append(f"- `{definition.name}`: {definition.description}")

    lines.extend(
        [
            "",
        "## Risk Setting Sensitivity Table",
            frame_to_markdown(compact_display),
        ]
    )

    if skipped:
        skipped_frame = pd.DataFrame(skipped)
        skipped_frame = skipped_frame.replace({"repository_disjoint": "Unseen repository", "temporal": "Temporal"})
        skipped_frame = skipped_frame.rename(
            columns={
                "workload_definition": "definition",
                "high_workload_quantile": "quantile",
            }
        )
        if "error" in skipped_frame.columns:
            skipped_frame["error"] = (
                skipped_frame["error"]
                .str.replace("high-workload", "high workload", regex=False)
                .str.replace("repository_disjoint", "unseen repository", regex=False)
            )
        lines.extend(
            [
                "",
                "## Skipped Fits",
                "These fits were skipped because the training split did not contain both high workload classes under that definition and threshold.",
                frame_to_markdown(skipped_frame),
            ]
        )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate AIDev gate sensitivity to workload definitions and high workload thresholds.")
    parser.add_argument("--features", type=Path, default=RESULTS_DIR / "aidev_pr_level_features.csv")
    parser.add_argument("--output-dir", type=Path, default=RESULTS_DIR)
    parser.add_argument("--high-workload-quantiles", nargs="*", type=float, default=[0.75, 0.80, 0.90])
    parser.add_argument("--risk-budget", type=float, default=0.10)
    parser.add_argument("--seed", type=int, default=23)
    args = parser.parse_args()

    frame, definitions = prepare_frame(args.features)
    rows: list[dict] = []
    skipped: list[dict] = []

    for definition in definitions:
        for quantile in args.high_workload_quantiles:
            for split_name, train, calibration, test in split_specs(frame, args.seed):
                try:
                    evaluated = evaluate_split(
                        split_name=split_name,
                        train=train,
                        calibration=calibration,
                        test=test,
                        target_col=definition.target_column,
                        workload_col=definition.raw_column,
                        high_quantile=quantile,
                        accept_rates=[],
                        risk_budgets=[args.risk_budget],
                    )
                except ValueError as exc:
                    skipped.append(
                        {
                            "split": split_name,
                            "workload_definition": definition.name,
                            "high_workload_quantile": quantile,
                            "error": str(exc),
                        }
                    )
                    continue

                for row in evaluated:
                    row["workload_definition"] = definition.name
                    row["workload_description"] = definition.description
                    rows.append(row)

    output_dir = ensure_dir(args.output_dir)
    summary = pd.DataFrame(rows)
    csv_path = output_dir / "aidev_workload_sensitivity_summary.csv"
    table_path = output_dir / "aidev_workload_sensitivity_table.csv"
    report_path = output_dir / "aidev_workload_sensitivity_report.md"

    summary.to_csv(csv_path, index=False)
    readable = readable_table(summary).sort_values(["split", "definition", "quantile"]).reset_index(drop=True)
    readable.to_csv(table_path, index=False)
    write_report(summary, skipped, definitions, report_path)

    write_json(
        output_dir / "aidev_workload_sensitivity_summary.json",
        {
            "output_csv": str(csv_path),
            "table_csv": str(table_path),
            "report": str(report_path),
            "rows": int(len(summary)),
            "skipped_rows": len(skipped),
            "risk_budget": args.risk_budget,
            "high_workload_quantiles": args.high_workload_quantiles,
            "workload_definitions": [definition.name for definition in definitions],
            "skipped": skipped,
        },
    )
    print(f"Wrote workload sensitivity summary to {csv_path}")


if __name__ == "__main__":
    main()
