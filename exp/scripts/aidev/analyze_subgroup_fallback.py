from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from .analyze_subgroup_shift import SUBGROUP_COLUMNS, add_bucket_columns
from .bootstrap_gate_uncertainty import compute_metrics, prediction_frame, prepare_frame, split_frame
from .common import RESULTS_DIR, ensure_dir, write_json


def attach_subgroups(pred: pd.DataFrame, frame: pd.DataFrame, split_name: str) -> pd.DataFrame:
    out = pred.reset_index(drop=True).copy()
    source = add_bucket_columns(frame).reset_index(drop=True)
    out["split"] = split_name
    for col in SUBGROUP_COLUMNS:
        out[col] = source[col].fillna("unknown").astype(str) if col in source.columns else "unknown"
    return out


def subgroup_risk_flags(
    cal_pred: pd.DataFrame,
    threshold: float,
    risk_budget: float,
    min_rows: int,
    min_accepted: int,
) -> tuple[set[tuple[str, str]], set[tuple[str, str]], pd.DataFrame]:
    risk_flags: set[tuple[str, str]] = set()
    support_flags: set[tuple[str, str]] = set()
    rows = []
    accepted = cal_pred["score"].to_numpy(dtype=float) <= threshold
    high = cal_pred["high"].to_numpy(dtype=bool)
    for col in SUBGROUP_COLUMNS:
        for value, group in cal_pred.groupby(col, dropna=False):
            if len(group) < min_rows:
                continue
            idx = group.index.to_numpy()
            group_accepted = accepted[idx]
            group_high = high[idx]
            accepted_count = int(group_accepted.sum())
            accepted_high = int((group_accepted & group_high).sum())
            accepted_risk = float(accepted_high / accepted_count) if accepted_count else 0.0
            flag_risk = accepted_count >= min_accepted and accepted_risk > risk_budget
            flag_support = accepted_count < min_accepted
            key = (col, str(value))
            if flag_risk:
                risk_flags.add(key)
            if flag_support:
                support_flags.add(key)
            rows.append(
                {
                    "subgroup_type": col,
                    "subgroup_value": str(value),
                    "calibration_rows": int(len(group)),
                    "calibration_accepted": accepted_count,
                    "calibration_accepted_high": accepted_high,
                    "calibration_accepted_high_rate": accepted_risk,
                    "risk_flag": bool(flag_risk),
                    "support_flag": bool(flag_support),
                }
            )
    return risk_flags, support_flags, pd.DataFrame(rows)


def forced_route_mask(pred: pd.DataFrame, flags: set[tuple[str, str]]) -> np.ndarray:
    mask = np.zeros(len(pred), dtype=bool)
    if not flags:
        return mask
    for col, value in flags:
        if col in pred.columns:
            mask |= pred[col].astype(str).to_numpy() == value
    return mask


def metrics_with_forced_route(pred: pd.DataFrame, threshold: float, force_route: np.ndarray) -> dict[str, float]:
    scores = pred["score"].to_numpy(dtype=float)
    high = pred["high"].to_numpy(dtype=bool)
    workload = pred["workload"].to_numpy(dtype=float)
    accepted = (scores <= threshold) & ~force_route
    routed = ~accepted

    accepted_count = int(accepted.sum())
    routed_count = int(routed.sum())
    high_count = int(high.sum())
    accepted_high = int((accepted & high).sum())
    routed_high = int((routed & high).sum())
    total_workload = float(workload.sum())
    routed_workload = float(workload[routed].sum())
    return {
        "rows": int(len(pred)),
        "acceptance_rate": float(accepted.mean()) if len(accepted) else 0.0,
        "routed_rate": float(routed.mean()) if len(routed) else 0.0,
        "accepted_high_workload_rate": float(accepted_high / accepted_count) if accepted_count else 0.0,
        "high_workload_recall_by_routing": float(routed_high / high_count) if high_count else 0.0,
        "routing_precision_for_high_workload": float(routed_high / routed_count) if routed_count else 0.0,
        "workload_share_routed": float(routed_workload / total_workload) if total_workload > 0 else 0.0,
        "mean_workload_accepted": float(workload[accepted].mean()) if accepted_count else 0.0,
        "mean_workload_routed": float(workload[routed].mean()) if routed_count else 0.0,
        "forced_route_share": float(force_route.mean()) if len(force_route) else 0.0,
    }


def evaluate_split(
    split_name: str,
    train: pd.DataFrame,
    calibration: pd.DataFrame,
    test: pd.DataFrame,
    target_col: str,
    workload_col: str,
    high_quantile: float,
    risk_budget: float,
    min_rows: int,
    min_accepted: int,
) -> tuple[list[dict], pd.DataFrame]:
    cal_pred_raw, metadata = prediction_frame(
        train,
        calibration,
        calibration,
        target_col,
        workload_col,
        high_quantile,
        risk_budget,
    )
    test_pred_raw, _ = prediction_frame(
        train,
        calibration,
        test,
        target_col,
        workload_col,
        high_quantile,
        risk_budget,
    )
    threshold = float(metadata["score_threshold"])
    cal_pred = attach_subgroups(cal_pred_raw, calibration, split_name)
    test_pred = attach_subgroups(test_pred_raw, test, split_name)
    risk_flags, support_flags, flag_table = subgroup_risk_flags(cal_pred, threshold, risk_budget, min_rows, min_accepted)

    strategies = [
        ("global_gate", set()),
        ("calibration_risk_flags", risk_flags),
        ("risk_or_low_support_flags", risk_flags | support_flags),
    ]
    rows = []
    global_metrics = compute_metrics(test_pred_raw, threshold)
    rows.append(
        {
            "split": split_name,
            "strategy": "global_gate",
            "flagged_groups": 0,
            "flagged_test_share": 0.0,
            "risk_budget": risk_budget,
            **{
                "acceptance_rate": global_metrics["acceptance_rate"],
                "routed_rate": 1.0 - global_metrics["acceptance_rate"],
                "accepted_high_workload_rate": global_metrics["accepted_high_workload_rate"],
                "high_workload_recall_by_routing": global_metrics["high_workload_recall_by_abstention"],
                "routing_precision_for_high_workload": global_metrics["abstention_precision_for_high_workload"],
                "workload_share_routed": global_metrics["workload_share_abstained"],
                "mean_workload_accepted": global_metrics["mean_workload_accepted"],
                "mean_workload_routed": global_metrics["mean_workload_abstained"],
                "forced_route_share": 0.0,
            },
        }
    )
    for strategy, flags in strategies[1:]:
        force = forced_route_mask(test_pred, flags)
        metrics = metrics_with_forced_route(test_pred, threshold, force)
        rows.append(
            {
                "split": split_name,
                "strategy": strategy,
                "flagged_groups": int(len(flags)),
                "flagged_test_share": float(force.mean()) if len(force) else 0.0,
                "risk_budget": risk_budget,
                **metrics,
            }
        )
    flag_table.insert(0, "split", split_name)
    return rows, flag_table


def compact_table(summary: pd.DataFrame) -> pd.DataFrame:
    keep = summary[summary["split"].eq("repository_disjoint")].copy()
    order = {"global_gate": 0, "calibration_risk_flags": 1, "risk_or_low_support_flags": 2}
    keep["order"] = keep["strategy"].map(order).fillna(99)
    keep = keep.sort_values("order")
    return keep[
        [
            "strategy",
            "flagged_groups",
            "flagged_test_share",
            "acceptance_rate",
            "accepted_high_workload_rate",
            "high_workload_recall_by_routing",
            "workload_share_routed",
            "mean_workload_accepted",
            "mean_workload_routed",
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
        "# Calibration Subgroup Fallback Diagnostic",
        "",
        "This diagnostic applies subgroup flags learned on the calibration split before evaluating the unseen repository test split. The global gate uses one threshold for all PRs. The risk-flag fallback routes PRs belonging to calibration subgroups whose accepted high workload rate exceeds the risk limit with enough accepted rows. The risk-or-low-support fallback additionally routes PRs from subgroups with insufficient calibration acceptance support.",
        "",
        markdown_table(table),
        "",
        "Allowed claim: subgroup monitoring can trade lower accepted risk for lower coverage under shift.",
        "Boundary: this is a retrospective fallback diagnostic and does not estimate outcomes after extra review.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate calibration-derived subgroup fallback rules for the AIDev gate.")
    parser.add_argument("--features", type=Path, default=RESULTS_DIR / "aidev_pr_level_features.csv")
    parser.add_argument("--output-dir", type=Path, default=RESULTS_DIR)
    parser.add_argument("--target", default="outcome_downstream_workload_log")
    parser.add_argument("--workload", default="outcome_downstream_workload_raw")
    parser.add_argument("--high-workload-quantile", type=float, default=0.80)
    parser.add_argument("--risk-budget", type=float, default=0.10)
    parser.add_argument("--splits", nargs="*", default=["temporal", "repository_disjoint"])
    parser.add_argument("--min-rows", type=int, default=100)
    parser.add_argument("--min-accepted", type=int, default=30)
    parser.add_argument("--seed", type=int, default=23)
    args = parser.parse_args()

    frame = prepare_frame(args.features, args.target, args.workload)
    summary_rows = []
    flag_tables = []
    for split_name in args.splits:
        train, calibration, test = split_frame(frame, split_name, args.seed)
        split_rows, split_flags = evaluate_split(
            split_name,
            train,
            calibration,
            test,
            args.target,
            args.workload,
            args.high_workload_quantile,
            args.risk_budget,
            args.min_rows,
            args.min_accepted,
        )
        summary_rows.extend(split_rows)
        flag_tables.append(split_flags)

    output_dir = ensure_dir(args.output_dir)
    summary = pd.DataFrame(summary_rows)
    flags = pd.concat(flag_tables, ignore_index=True) if flag_tables else pd.DataFrame()
    table = compact_table(summary)
    summary_path = output_dir / "aidev_subgroup_fallback_summary.csv"
    flags_path = output_dir / "aidev_subgroup_fallback_flags.csv"
    table_path = output_dir / "aidev_subgroup_fallback_table.csv"
    report_path = output_dir / "aidev_subgroup_fallback_report.md"
    summary.to_csv(summary_path, index=False)
    flags.to_csv(flags_path, index=False)
    table.to_csv(table_path, index=False)
    write_report(table, report_path)
    write_json(
        output_dir / "aidev_subgroup_fallback_summary.json",
        {
            "summary_csv": str(summary_path),
            "flags_csv": str(flags_path),
            "table_csv": str(table_path),
            "report": str(report_path),
            "risk_budget": args.risk_budget,
            "min_rows": args.min_rows,
            "min_accepted": args.min_accepted,
        },
    )
    print(f"Wrote subgroup fallback diagnostic to {table_path}")


if __name__ == "__main__":
    main()
