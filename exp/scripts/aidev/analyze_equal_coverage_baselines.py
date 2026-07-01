from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from .common import RESULTS_DIR, ensure_dir, write_json
from .evaluate_gate_baselines import prepare_frame, score_bundles
from .evaluate_workload_gate import (
    decision_metrics,
    repository_disjoint_split,
    safe_auc,
    safe_average_precision,
    temporal_split,
    threshold_for_risk_budget,
)


def split_specs(frame: pd.DataFrame, seed: int) -> list[tuple[str, pd.DataFrame, pd.DataFrame, pd.DataFrame]]:
    return [
        ("temporal", *temporal_split(frame)),
        ("repository_disjoint", *repository_disjoint_split(frame, seed)),
    ]


def evaluate_split_equal_coverage(
    split_name: str,
    train: pd.DataFrame,
    calibration: pd.DataFrame,
    test: pd.DataFrame,
    target_col: str,
    workload_col: str,
    high_quantile: float,
    risk_budget: float,
) -> list[dict]:
    high_threshold = float(train[target_col].quantile(high_quantile))
    train_high = train[target_col] >= high_threshold
    cal_high = calibration[target_col] >= high_threshold
    test_high = test[target_col] >= high_threshold

    bundles = score_bundles(train, calibration, test, train_high, workload_col)
    main = next((bundle for bundle in bundles if bundle.name == "logistic_all_features"), None)
    if main is None:
        raise ValueError("Main defensible-features bundle is unavailable.")

    main_threshold, main_cal_acceptance, main_cal_risk = threshold_for_risk_budget(
        main.calibration_scores,
        cal_high,
        risk_budget,
    )

    rows = []
    for bundle in bundles:
        if bundle.name == "logistic_all_features":
            threshold = main_threshold
            selector = "risk_target_threshold"
        else:
            threshold = float(np.quantile(bundle.calibration_scores, max(min(main_cal_acceptance, 1.0), 0.0)))
            selector = "equal_calibration_coverage"

        row = {
            "split": split_name,
            "baseline": bundle.name,
            "selector": selector,
            "risk_budget": risk_budget,
            "target_calibration_acceptance": main_cal_acceptance,
            "main_calibrated_accepted_high_rate": main_cal_risk,
            "score_threshold": threshold,
            "test_auc": safe_auc(test_high, bundle.test_scores),
            "test_average_precision": safe_average_precision(test_high, bundle.test_scores),
            "features": bundle.features,
        }
        row.update(decision_metrics("calibration", bundle.calibration_scores, cal_high, calibration[workload_col], threshold))
        row.update(decision_metrics("test", bundle.test_scores, test_high, test[workload_col], threshold))
        rows.append(row)
    return rows


def compact_table(summary: pd.DataFrame) -> pd.DataFrame:
    keep = summary[summary["split"].eq("repository_disjoint")].copy()
    order = {
        "logistic_all_features": 0,
        "cost_sensitive_workload_logistic": 1,
        "categorical_prior": 2,
        "logistic_no_agent": 3,
        "simple_text_threshold": 4,
        "selective_uncertainty_only": 5,
    }
    keep["order"] = keep["baseline"].map(order).fillna(99)
    keep = keep.sort_values(["order", "baseline"])
    return keep[
        [
            "baseline",
            "selector",
            "target_calibration_acceptance",
            "calibration_acceptance_rate",
            "test_acceptance_rate",
            "test_accepted_high_workload_rate",
            "test_high_workload_recall_by_abstention",
            "test_workload_share_abstained",
            "test_auc",
            "test_average_precision",
        ]
    ].reset_index(drop=True)


def markdown_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "_No rows._"
    headers = list(frame.columns)
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for _, row in frame.iterrows():
        values = []
        for col in headers:
            value = row[col]
            if isinstance(value, (float, np.floating)):
                values.append(f"{float(value):.3f}")
            else:
                values.append(str(value).replace("|", "\\|"))
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def write_report(table: pd.DataFrame, path: Path) -> None:
    lines = [
        "# Equal Coverage Baseline Diagnostic",
        "",
        "This diagnostic compares baselines at the main gate's calibration coverage. The main defensible-features gate keeps its risk-target threshold; other baselines use score thresholds that match the main gate's calibration acceptance rate. Test metrics are then evaluated without using test outcomes to set thresholds.",
        "",
        markdown_table(table),
        "",
        "Allowed claim: workload-aware scoring retains low accepted risk at usable coverage under unseen repository evaluation better than simple text or uncertainty-only rules.",
        "Boundary: this is a retrospective observational diagnostic, not a deployed routing experiment.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare AIDev baselines at the main gate's calibration coverage.")
    parser.add_argument("--features", type=Path, default=RESULTS_DIR / "aidev_pr_level_features.csv")
    parser.add_argument("--output-dir", type=Path, default=RESULTS_DIR)
    parser.add_argument("--target", default="outcome_downstream_workload_log")
    parser.add_argument("--workload", default="outcome_downstream_workload_raw")
    parser.add_argument("--high-workload-quantile", type=float, default=0.80)
    parser.add_argument("--risk-budget", type=float, default=0.10)
    parser.add_argument("--seed", type=int, default=23)
    args = parser.parse_args()

    frame = prepare_frame(args.features, args.target, args.workload)
    rows = []
    for split_name, train, calibration, test in split_specs(frame, args.seed):
        rows.extend(
            evaluate_split_equal_coverage(
                split_name,
                train,
                calibration,
                test,
                args.target,
                args.workload,
                args.high_workload_quantile,
                args.risk_budget,
            )
        )

    output_dir = ensure_dir(args.output_dir)
    summary = pd.DataFrame(rows)
    table = compact_table(summary)
    summary_path = output_dir / "aidev_equal_coverage_baseline_summary.csv"
    table_path = output_dir / "aidev_equal_coverage_baseline_table.csv"
    report_path = output_dir / "aidev_equal_coverage_baseline_report.md"
    summary.to_csv(summary_path, index=False)
    table.to_csv(table_path, index=False)
    write_report(table, report_path)
    write_json(
        output_dir / "aidev_equal_coverage_baseline_summary.json",
        {
            "summary_csv": str(summary_path),
            "table_csv": str(table_path),
            "report": str(report_path),
            "rows": int(len(summary)),
            "risk_budget": args.risk_budget,
        },
    )
    print(f"Wrote equal coverage baseline diagnostic to {table_path}")


if __name__ == "__main__":
    main()
