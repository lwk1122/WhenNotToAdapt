from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from .common import RESULTS_DIR, ensure_dir, write_json


DISPLAY_COLUMNS = [
    "split",
    "selector",
    "selector_value",
    "test_rows",
    "test_auc",
    "test_average_precision",
    "test_high_workload_rate",
    "test_acceptance_rate",
    "test_accepted_high_workload_rate",
    "test_high_workload_recall_by_abstention",
    "test_abstention_precision_for_high_workload",
    "test_mean_workload_accepted",
    "test_mean_workload_abstained",
    "test_workload_share_abstained",
]

BASELINE_DISPLAY_COLUMNS = [
    "split",
    "baseline",
    "selector",
    "selector_value",
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

COMPONENT_DISPLAY_COLUMNS = [
    "split",
    "component",
    "target_rule",
    "threshold",
    "test_positive_rate",
    "test_auc",
    "test_average_precision",
    "test_brier",
]

ERROR_DISPLAY_COLUMNS = [
    "split",
    "case_type",
    "n",
    "share_of_split",
    "mean_gate_score",
    "mean_workload",
    "median_workload",
    "mean_outcome_review_count",
    "mean_outcome_issue_comment_count",
    "mean_outcome_followup_commit_count",
    "mean_outcome_followup_detail_churn",
    "top_agents",
]

UNCERTAINTY_METRIC_LABELS = {
    "auc": "AUC",
    "average_precision": "Average precision",
    "high_workload_rate": "High workload base rate",
    "acceptance_rate": "Acceptance rate",
    "accepted_high_workload_rate": "Accepted high workload rate",
    "high_workload_recall_by_abstention": "High workload recall by routing",
    "mean_workload_accepted": "Mean workload accepted",
    "mean_workload_abstained": "Mean workload routed",
    "workload_share_abstained": "Workload share routed",
}

SENSITIVITY_DISPLAY_COLUMNS = [
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

SURVIVAL_DISPLAY_COLUMNS = [
    "split",
    "gate_group",
    "rows",
    "closed_events",
    "censored_open",
    "observed_closure_rate",
    "km_median_days",
    "unresolved_probability_7d",
    "unresolved_probability_30d",
    "unresolved_probability_90d",
    "rmst_30d_days",
]

SURVIVAL_CONTRAST_METRICS = {
    "closed_rate_diff_accepted_minus_abstained",
    "unresolved_30d_diff_accepted_minus_abstained",
    "rmst_30d_days_diff_accepted_minus_abstained",
}

SPLIT_LABELS = {
    "temporal": "Temporal",
    "repository_disjoint": "Unseen repository",
}

BASELINE_LABELS = {
    "logistic_all_features": "Defensible features",
    "cost_sensitive_workload_logistic": "Workload weights",
    "logistic_no_agent": "No agent ID",
    "categorical_prior": "Categorical prior",
    "simple_text_threshold": "Text threshold",
    "selective_uncertainty_only": "Uncertainty threshold",
}

CASE_LABELS = {
    "safe_accept_low_workload": "Accept low workload",
    "false_accept_high_workload": "Accept high workload",
    "useful_abstain_high_workload": "Route high workload",
    "conservative_abstain_low_workload": "Route low workload",
}

SURVIVAL_CONTRAST_LABELS = {
    "closed_rate_diff_accepted_minus_abstained": "Observed closure rate, accepted minus routed",
    "unresolved_30d_diff_accepted_minus_abstained": "30-day unresolved probability, accepted minus routed",
    "rmst_30d_days_diff_accepted_minus_abstained": "30-day RMST unresolved, accepted minus routed",
}


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


def display_markdown_table(frame: pd.DataFrame) -> str:
    out = frame.copy()
    if "split" in out.columns:
        out["split"] = out["split"].map(SPLIT_LABELS).fillna(out["split"])
    if "baseline" in out.columns:
        out["baseline"] = out["baseline"].map(BASELINE_LABELS).fillna(out["baseline"])
    if "case_type" in out.columns:
        out["case_type"] = out["case_type"].map(CASE_LABELS).fillna(out["case_type"])
    if "gate_group" in out.columns:
        out["gate_group"] = out["gate_group"].replace({"abstained": "routed"})
    if "metric" in out.columns:
        out["metric"] = out["metric"].replace(SURVIVAL_CONTRAST_LABELS)
    out = out.rename(
        columns={
            "high_recall_abstained": "high_recall_routed",
            "abstention_precision": "routing_precision",
            "mean_workload_abstained": "mean_workload_routed",
            "workload_share_abstained": "workload_share_routed",
        }
    )
    return frame_to_markdown(out)


def readable_table(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame[DISPLAY_COLUMNS].copy()
    rename = {
        "selector_value": "setting",
        "test_rows": "n",
        "test_auc": "auc",
        "test_average_precision": "avg_precision",
        "test_high_workload_rate": "base_high_rate",
        "test_acceptance_rate": "accept_rate",
        "test_accepted_high_workload_rate": "accepted_high_rate",
        "test_high_workload_recall_by_abstention": "high_recall_abstained",
        "test_abstention_precision_for_high_workload": "abstention_precision",
        "test_mean_workload_accepted": "mean_workload_accepted",
        "test_mean_workload_abstained": "mean_workload_abstained",
        "test_workload_share_abstained": "workload_share_abstained",
    }
    return out.rename(columns=rename)


def readable_baseline_table(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame[BASELINE_DISPLAY_COLUMNS].copy()
    return out.rename(
        columns={
            "selector_value": "setting",
            "test_rows": "n",
            "test_auc": "auc",
            "test_average_precision": "avg_precision",
            "test_high_workload_rate": "base_high_rate",
            "test_acceptance_rate": "accept_rate",
            "test_accepted_high_workload_rate": "accepted_high_rate",
            "test_high_workload_recall_by_abstention": "high_recall_abstained",
            "test_mean_workload_accepted": "mean_workload_accepted",
            "test_mean_workload_abstained": "mean_workload_abstained",
            "test_workload_share_abstained": "workload_share_abstained",
        }
    )


def readable_component_table(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame[COMPONENT_DISPLAY_COLUMNS].copy()
    return out.rename(
        columns={
            "test_positive_rate": "positive_rate",
            "test_auc": "auc",
            "test_average_precision": "avg_precision",
            "test_brier": "brier",
        }
    )


def readable_error_table(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame[[col for col in ERROR_DISPLAY_COLUMNS if col in frame.columns]].copy()
    return out.rename(
        columns={
            "share_of_split": "share",
            "mean_gate_score": "mean_score",
            "mean_outcome_review_count": "mean_reviews",
            "mean_outcome_issue_comment_count": "mean_issue_comments",
            "mean_outcome_followup_commit_count": "mean_followup_commits",
            "mean_outcome_followup_detail_churn": "mean_followup_churn",
        }
    )


def readable_uncertainty_table(frame: pd.DataFrame) -> pd.DataFrame:
    rows = frame[frame["metric"].isin(UNCERTAINTY_METRIC_LABELS)].copy()
    rows["metric_label"] = rows["metric"].map(UNCERTAINTY_METRIC_LABELS)
    rows["point_ci"] = rows.apply(
        lambda row: f"{row['point']:.3f} [{row['ci_low']:.3f}, {row['ci_high']:.3f}]",
        axis=1,
    )
    return rows[
        [
            "split",
            "metric_label",
            "point_ci",
            "bootstrap_unit",
            "bootstrap_rounds",
            "bootstrap_valid_rounds",
        ]
    ].rename(
        columns={
            "metric_label": "metric",
            "point_ci": "point_95ci",
        }
    )


def readable_subgroup_table(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame
    rows = frame.copy()
    if "risk_over_budget" in rows.columns:
        risk = rows["risk_over_budget"].astype(str).str.lower().isin(["true", "1", "yes"])
    else:
        risk = pd.Series(False, index=rows.index)
    low_coverage = pd.to_numeric(rows.get("acceptance_rate", 1.0), errors="coerce").fillna(1.0) <= 0.05
    rows = rows[risk | low_coverage].copy()
    if rows.empty:
        rows = frame.copy()
    rows = rows.sort_values(
        ["split", "risk_over_budget", "acceptance_rate", "rows"],
        ascending=[True, False, True, False],
    ).head(30)
    cols = [
        "split",
        "subgroup_type",
        "subgroup_value",
        "rows",
        "accepted_count",
        "high_workload_rate",
        "acceptance_rate",
        "accepted_high_workload_rate",
        "risk_over_budget",
        "risk_flag_note",
        "workload_share_abstained",
        "auc",
    ]
    return rows[[col for col in cols if col in rows.columns]].copy()


def readable_sensitivity_table(frame: pd.DataFrame) -> pd.DataFrame:
    rows = frame[
        frame["split"].isin(["temporal", "repository_disjoint"])
        & frame["selector"].eq("calibration_risk_budget")
        & frame["selector_value"].eq(0.10)
    ].copy()
    out = rows[[col for col in SENSITIVITY_DISPLAY_COLUMNS if col in rows.columns]].copy()
    return out.rename(
        columns={
            "workload_definition": "definition",
            "high_workload_quantile": "quantile",
            "test_rows": "n",
            "test_auc": "auc",
            "test_average_precision": "avg_precision",
            "test_high_workload_rate": "base_high_rate",
            "test_acceptance_rate": "accept_rate",
            "test_accepted_high_workload_rate": "accepted_high_rate",
            "test_high_workload_recall_by_abstention": "high_recall_abstained",
            "test_mean_workload_accepted": "mean_workload_accepted",
            "test_mean_workload_abstained": "mean_workload_abstained",
            "test_workload_share_abstained": "workload_share_abstained",
        }
    ).sort_values(["split", "definition", "quantile"])


def readable_survival_table(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame[[col for col in SURVIVAL_DISPLAY_COLUMNS if col in frame.columns]].copy()
    return out.sort_values(["split", "gate_group"])


def readable_survival_contrast_table(frame: pd.DataFrame) -> pd.DataFrame:
    rows = frame[frame["metric"].isin(SURVIVAL_CONTRAST_METRICS)].copy()
    rows["metric"] = rows["metric"].map(SURVIVAL_CONTRAST_LABELS).fillna(rows["metric"])
    cols = [
        "split",
        "metric",
        "point",
        "ci_low",
        "ci_high",
        "bootstrap_unit",
        "bootstrap_rounds",
        "bootstrap_valid_rounds",
    ]
    metric_order = {label: idx for idx, label in enumerate(SURVIVAL_CONTRAST_LABELS.values())}
    rows["metric_order"] = rows["metric"].map(metric_order)
    rows = rows.sort_values(["split", "metric_order"])
    return rows[[col for col in cols if col in rows.columns]]


def main() -> None:
    parser = argparse.ArgumentParser(description="Create compact EMSE facing tables from AIDev workload gate results.")
    parser.add_argument("--summary", type=Path, default=RESULTS_DIR / "aidev_workload_gate_summary.csv")
    parser.add_argument("--baseline-summary", type=Path, default=RESULTS_DIR / "aidev_gate_baseline_summary.csv")
    parser.add_argument("--component-summary", type=Path, default=RESULTS_DIR / "aidev_workload_component_prediction.csv")
    parser.add_argument("--error-summary", type=Path, default=RESULTS_DIR / "aidev_gate_error_summary.csv")
    parser.add_argument("--uncertainty-summary", type=Path, default=RESULTS_DIR / "aidev_gate_uncertainty_summary.csv")
    parser.add_argument("--subgroup-summary", type=Path, default=RESULTS_DIR / "aidev_subgroup_gate_table.csv")
    parser.add_argument("--sensitivity-summary", type=Path, default=RESULTS_DIR / "aidev_workload_sensitivity_summary.csv")
    parser.add_argument("--survival-summary", type=Path, default=RESULTS_DIR / "aidev_resolution_survival_summary.csv")
    parser.add_argument("--survival-contrast", type=Path, default=RESULTS_DIR / "aidev_resolution_survival_contrast.csv")
    parser.add_argument("--output-dir", type=Path, default=RESULTS_DIR)
    args = parser.parse_args()

    output_dir = ensure_dir(args.output_dir)
    results = pd.read_csv(args.summary)

    main_rows = results[
        results["split"].isin(["temporal", "repository_disjoint"])
        & results["selector"].eq("calibration_risk_budget")
        & results["selector_value"].eq(0.10)
    ].copy()
    main_table = readable_table(main_rows)

    frontier = results[
        results["split"].isin(["temporal", "repository_disjoint"])
        & results["selector"].isin(["fixed_acceptance", "calibration_risk_budget"])
    ].copy()
    frontier_table = readable_table(frontier)

    agent_rows = results[
        results["split"].str.startswith("leave_agent_out:")
        & results["selector"].eq("calibration_risk_budget")
        & results["selector_value"].eq(0.10)
    ].copy()
    agent_rows["heldout_agent"] = agent_rows["split"].str.replace("leave_agent_out:", "", regex=False)
    agent_table = readable_table(agent_rows).drop(columns=["split"])
    agent_table.insert(0, "heldout_agent", agent_rows["heldout_agent"].to_numpy())

    baseline_table = pd.DataFrame()
    if args.baseline_summary.exists():
        baseline_results = pd.read_csv(args.baseline_summary)
        baseline_rows = baseline_results[
            baseline_results["split"].isin(["temporal", "repository_disjoint"])
            & baseline_results["selector"].eq("calibration_risk_budget")
            & baseline_results["selector_value"].eq(0.10)
        ].copy()
        baseline_table = readable_baseline_table(baseline_rows)

    component_table = pd.DataFrame()
    if args.component_summary.exists():
        component_results = pd.read_csv(args.component_summary)
        component_table = readable_component_table(component_results)

    error_table = pd.DataFrame()
    if args.error_summary.exists():
        error_results = pd.read_csv(args.error_summary)
        error_rows = error_results[error_results["split"].isin(["temporal", "repository_disjoint"])].copy()
        error_table = readable_error_table(error_rows)

    uncertainty_table = pd.DataFrame()
    if args.uncertainty_summary.exists():
        uncertainty_results = pd.read_csv(args.uncertainty_summary)
        uncertainty_table = readable_uncertainty_table(uncertainty_results)

    subgroup_table = pd.DataFrame()
    if args.subgroup_summary.exists():
        subgroup_results = pd.read_csv(args.subgroup_summary)
        subgroup_table = readable_subgroup_table(subgroup_results)

    sensitivity_table = pd.DataFrame()
    if args.sensitivity_summary.exists():
        sensitivity_results = pd.read_csv(args.sensitivity_summary)
        sensitivity_table = readable_sensitivity_table(sensitivity_results)

    survival_table = pd.DataFrame()
    if args.survival_summary.exists():
        survival_results = pd.read_csv(args.survival_summary)
        survival_table = readable_survival_table(survival_results)

    survival_contrast_table = pd.DataFrame()
    if args.survival_contrast.exists():
        survival_contrast_results = pd.read_csv(args.survival_contrast)
        survival_contrast_table = readable_survival_contrast_table(survival_contrast_results)

    main_csv = output_dir / "aidev_main_gate_table.csv"
    frontier_csv = output_dir / "aidev_frontier_table.csv"
    agent_csv = output_dir / "aidev_leave_agent_out_table.csv"
    baseline_csv = output_dir / "aidev_baseline_comparison_table.csv"
    component_csv = output_dir / "aidev_component_prediction_table.csv"
    error_csv = output_dir / "aidev_gate_error_table.csv"
    uncertainty_csv = output_dir / "aidev_gate_uncertainty_table.csv"
    subgroup_csv = output_dir / "aidev_subgroup_diagnostic_table.csv"
    sensitivity_csv = output_dir / "aidev_workload_sensitivity_table.csv"
    survival_csv = output_dir / "aidev_resolution_survival_table.csv"
    survival_contrast_csv = output_dir / "aidev_resolution_survival_contrast_table.csv"
    main_md = output_dir / "aidev_results_tables.md"

    main_table.to_csv(main_csv, index=False)
    frontier_table.to_csv(frontier_csv, index=False)
    agent_table.to_csv(agent_csv, index=False)
    if not baseline_table.empty:
        baseline_table.to_csv(baseline_csv, index=False)
    if not component_table.empty:
        component_table.to_csv(component_csv, index=False)
    if not error_table.empty:
        error_table.to_csv(error_csv, index=False)
    if not uncertainty_table.empty:
        uncertainty_table.to_csv(uncertainty_csv, index=False)
    if not subgroup_table.empty:
        subgroup_table.to_csv(subgroup_csv, index=False)
    if not sensitivity_table.empty:
        sensitivity_table.to_csv(sensitivity_csv, index=False)
    if not survival_table.empty:
        survival_table.to_csv(survival_csv, index=False)
    if not survival_contrast_table.empty:
        survival_contrast_table.to_csv(survival_contrast_csv, index=False)

    sections = [
        "# AIDev Workload Gate Results",
        "## Main Split Table",
        display_markdown_table(main_table),
        "## Main Split Uncertainty",
        display_markdown_table(uncertainty_table) if not uncertainty_table.empty else "(uncertainty summary not found)",
        "## Baseline Comparison",
        display_markdown_table(baseline_table) if not baseline_table.empty else "(baseline summary not found)",
        "## Workload Component Prediction",
        display_markdown_table(component_table) if not component_table.empty else "(component summary not found)",
        "## Gate Error and Routing Cases",
        display_markdown_table(error_table) if not error_table.empty else "(gate error summary not found)",
        "## Subgroup and Shift Diagnostics",
        display_markdown_table(subgroup_table) if not subgroup_table.empty else "(subgroup summary not found)",
        "## Workload Definition Sensitivity",
        display_markdown_table(sensitivity_table) if not sensitivity_table.empty else "(sensitivity summary not found)",
        "## Resolution-Time Survival Diagnostic",
        display_markdown_table(survival_table) if not survival_table.empty else "(resolution survival summary not found)",
        "## Resolution-Time Survival Contrasts",
        display_markdown_table(survival_contrast_table) if not survival_contrast_table.empty else "(resolution survival contrast not found)",
        "## Frontier Table",
        display_markdown_table(frontier_table),
        "## Leave One Agent Out Table",
        display_markdown_table(agent_table),
    ]
    markdown = "\n\n".join(sections)
    main_md.write_text(markdown + "\n", encoding="utf-8")
    write_json(
        output_dir / "aidev_results_table_summary.json",
        {
            "main_csv": str(main_csv),
            "frontier_csv": str(frontier_csv),
            "agent_csv": str(agent_csv),
            "baseline_csv": str(baseline_csv) if not baseline_table.empty else "",
            "component_csv": str(component_csv) if not component_table.empty else "",
            "error_csv": str(error_csv) if not error_table.empty else "",
            "uncertainty_csv": str(uncertainty_csv) if not uncertainty_table.empty else "",
            "subgroup_csv": str(subgroup_csv) if not subgroup_table.empty else "",
            "sensitivity_csv": str(sensitivity_csv) if not sensitivity_table.empty else "",
            "survival_csv": str(survival_csv) if not survival_table.empty else "",
            "survival_contrast_csv": str(survival_contrast_csv) if not survival_contrast_table.empty else "",
            "markdown": str(main_md),
            "main_rows": int(len(main_table)),
            "frontier_rows": int(len(frontier_table)),
            "agent_rows": int(len(agent_table)),
            "baseline_rows": int(len(baseline_table)),
            "component_rows": int(len(component_table)),
            "error_rows": int(len(error_table)),
            "uncertainty_rows": int(len(uncertainty_table)),
            "subgroup_rows": int(len(subgroup_table)),
            "sensitivity_rows": int(len(sensitivity_table)),
            "survival_rows": int(len(survival_table)),
            "survival_contrast_rows": int(len(survival_contrast_table)),
        },
    )
    print(f"Wrote AIDev result tables to {main_md}")


if __name__ == "__main__":
    main()
