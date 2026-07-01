from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from .common import RESULTS_DIR, ensure_dir, write_json


DEFAULT_OUTPUT_DIR = RESULTS_DIR / "tables_tex"

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

EQUAL_COVERAGE_BASELINE_LABELS = {
    **BASELINE_LABELS,
    "logistic_all_features": "Defensible",
    "categorical_prior": "Prior",
    "simple_text_threshold": "Text",
    "selective_uncertainty_only": "Uncertainty",
}

FALLBACK_STRATEGY_LABELS = {
    "global_gate": "Global",
    "calibration_risk_flags": "Risk fallback",
    "risk_or_low_support_flags": "Risk/support",
}

FEATURE_SET_LABELS = {
    "defensible": "Defensible",
    "full_with_timing_sensitive": "With API aggregates",
    "text_repo_task": "Text, repo, task",
    "first_commit_only": "First commit only",
}

COMPONENT_LABELS = {
    "outcome_related_issue_count": "Related issues",
    "outcome_issue_comment_count": "Issue comments",
    "outcome_followup_commit_count": "Later commits",
    "outcome_followup_detail_changed_files": "Later files",
    "outcome_followup_detail_churn": "Later churn",
    "outcome_followup_detail_test_files": "Later files related to tests",
    "outcome_human_review_count": "Human reviews",
    "outcome_inline_review_comment_count": "Inline comments",
    "outcome_review_count": "Reviews",
    "outcome_request_changes_count": "Request changes",
}

CASE_LABELS = {
    "safe_accept_low_workload": "Std. low workload",
    "false_accept_high_workload": "Std. high workload",
    "useful_abstain_high_workload": "Route high workload",
    "conservative_abstain_low_workload": "Route low workload",
}

SURVIVAL_METRIC_LABELS = {
    "unresolved_30d_diff_accepted_minus_abstained": "Unresolved probability at 30 days",
    "rmst_30d_days_diff_accepted_minus_abstained": "RMST unresolved over 30 days",
    "closed_rate_diff_accepted_minus_abstained": "Observed closure rate",
    "30-day unresolved probability, accepted minus routed": "Unresolved probability at 30 days",
    "30-day RMST unresolved, accepted minus routed": "RMST unresolved over 30 days",
    "Observed closure rate, accepted minus routed": "Observed closure rate",
}


def latex_escape(value: object) -> str:
    text = "" if pd.isna(value) else str(value)
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(ch, ch) for ch in text)


def fmt_float(value: object, digits: int = 3) -> str:
    if pd.isna(value):
        return ""
    return f"{float(value):.{digits}f}"


def fmt_supported_rate(coverage: object, value: object, min_coverage: float = 0.01) -> str:
    if pd.isna(coverage) or float(coverage) < min_coverage:
        return "--"
    return fmt_float(value)


def fmt_count_supported_rate(count: object, value: object, min_count: int = 30) -> str:
    if pd.isna(count) or int(count) < min_count:
        return "--"
    return fmt_float(value)


def fmt_int(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(int(value))


def fmt_ci(point: object, low: object, high: object, digits: int = 3) -> str:
    if pd.isna(point):
        return ""
    return f"{float(point):.{digits}f} [{float(low):.{digits}f}, {float(high):.{digits}f}]"


def write_latex_table(
    path: Path,
    caption: str,
    label: str,
    headers: list[str],
    rows: list[list[str]],
    align: str,
    note: str | None = None,
    resize_to_width: bool = False,
    tabcolsep: str | None = None,
) -> None:
    ensure_dir(path.parent)
    lines = [
        r"\begin{table}[t]",
        r"\centering",
        r"\scriptsize",
        rf"\caption{{{latex_escape(caption)}}}",
        rf"\label{{{label}}}",
    ]
    if tabcolsep is not None:
        lines.append(rf"\setlength{{\tabcolsep}}{{{tabcolsep}}}")
    if resize_to_width:
        lines.append(r"\resizebox{\linewidth}{!}{%")
    lines.extend(
        [
            rf"\begin{{tabular}}{{{align}}}",
        r"\toprule",
        " & ".join(latex_escape(header) for header in headers) + r" \\",
        r"\midrule",
        ]
    )
    for row in rows:
        lines.append(" & ".join(row) + r" \\")
    lines.extend([r"\bottomrule", r"\end{tabular}"])
    if resize_to_width:
        lines.append("}")
    if note:
        lines.append(rf"\par\footnotesize{{{latex_escape(note)}}}")
    lines.append(r"\end{table}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main_gate_table(source: Path, output_dir: Path) -> Path:
    frame = pd.read_csv(source)
    keep_metrics = [
        ("AUC", ("AUC",)),
        ("AP", ("Average precision",)),
        ("Base high workload", ("High workload base rate", "High-workload base rate")),
        ("Std. path", ("Acceptance rate",)),
        ("High std.", ("Accepted high workload rate", "Accepted high-workload rate")),
        ("Workload routed", ("Workload share routed", "Workload share abstained")),
    ]
    split_frames = {
        split: frame[frame["split"].eq(split)].set_index("metric")
        for split in ["temporal", "repository_disjoint"]
    }
    rows = []
    for label, metric_names in keep_metrics:
        row = [latex_escape(label)]
        for split in ["temporal", "repository_disjoint"]:
            split_rows = split_frames[split]
            metric = next((name for name in metric_names if name in split_rows.index), None)
            if metric is None:
                raise KeyError(f"Missing metric; expected one of {metric_names}")
            row.append(latex_escape(split_rows.loc[metric, "point_95ci"]))
        rows.append(row)
    path = output_dir / "aidev_main_gate_table.tex"
    write_latex_table(
        path,
        "Main retrospective AIDev gate results at risk limit 0.10 with repository cluster bootstrap intervals.",
        "tab:aidev-main",
        ["Metric", "Temporal", "Unseen repository"],
        rows,
        "lll",
        "Std. path denotes the retrospective standard-path group. Intervals are 95% repository cluster bootstrap intervals over test repositories.",
    )
    return path


def calibration_diagnostics_table(source: Path, output_dir: Path) -> Path:
    frame = pd.read_csv(source)
    rows = frame[
        frame["split"].isin(["temporal", "repository_disjoint"])
        & frame["selector"].eq("calibration_risk_budget")
        & frame["selector_value"].eq(0.10)
    ].copy()
    rows["split_order"] = rows["split"].map({"temporal": 0, "repository_disjoint": 1})
    rows = rows.sort_values("split_order")
    body = []
    for _, row in rows.iterrows():
        body.append(
            [
                latex_escape(SPLIT_LABELS[row["split"]]),
                fmt_float(row["test_brier"]),
                fmt_float(row["score_threshold"]),
                fmt_float(row["calibration_acceptance_rate"]),
                fmt_float(row["calibration_accepted_high_workload_rate"]),
                fmt_float(row["test_acceptance_rate"]),
                fmt_float(row["test_accepted_high_workload_rate"]),
            ]
        )
    path = output_dir / "aidev_calibration_diagnostics_table.tex"
    write_latex_table(
        path,
        "Calibration diagnostics for the main AIDev gate at risk limit 0.10.",
        "tab:aidev-calibration",
        ["Split", "Brier", "Thresh.", "Cal. acc.", "Cal. high", "Test acc.", "Test high"],
        body,
        "lrrrrrr",
        "The threshold is selected on the calibration split. Cal. high and Test high report high workload rates in the standard-path group. Brier is reported on the test split as a score diagnostic; the decision claim is risk selection, not perfect probability calibration.",
        tabcolsep="3pt",
    )
    return path


def baseline_table(source: Path, output_dir: Path) -> Path:
    frame = pd.read_csv(source)
    rows = frame[frame["split"].eq("repository_disjoint")].copy()
    rows = rows.sort_values(["accepted_high_rate", "accept_rate"], ascending=[True, False])
    body = []
    for _, row in rows.iterrows():
        body.append(
            [
                latex_escape(BASELINE_LABELS.get(row["baseline"], row["baseline"])),
                fmt_float(row["auc"]),
                fmt_float(row["avg_precision"]),
                fmt_float(row["accept_rate"]),
                fmt_supported_rate(row["accept_rate"], row["accepted_high_rate"]),
                fmt_float(row["workload_share_abstained"]),
            ]
        )
    path = output_dir / "aidev_baseline_comparison_table.tex"
    write_latex_table(
        path,
        "Unseen repository retrospective baseline comparison at risk limit 0.10.",
        "tab:aidev-baselines",
        ["Baseline", "AUC", "AP", "Std. path", "High std.", "Work routed"],
        body,
        "lrrrrr",
        "Std. path denotes the retrospective standard-path group. High std. is not interpreted when coverage is below 0.01. Very low coverage baselines are diagnostic rather than operationally useful.",
    )
    return path


def feature_boundary_table(source: Path, output_dir: Path) -> Path:
    frame = pd.read_csv(source)
    rows = frame[frame["split"].isin(["temporal", "repository_disjoint"])].copy()
    rows["split_order"] = rows["split"].map({"temporal": 0, "repository_disjoint": 1})
    rows["feature_order"] = rows["feature_set"].map(
        {
            "defensible": 0,
            "full_with_timing_sensitive": 1,
            "text_repo_task": 2,
            "first_commit_only": 3,
        }
    )
    rows = rows.sort_values(["split_order", "feature_order"])
    body = []
    for _, row in rows.iterrows():
        body.append(
            [
                latex_escape("Unseen repo" if row["split"] == "repository_disjoint" else SPLIT_LABELS.get(row["split"], row["split"])),
                latex_escape(FEATURE_SET_LABELS.get(row["feature_set"], row["feature_set"])),
                fmt_int(row["feature_count"]),
                fmt_float(row["test_auc"]),
                fmt_float(row["test_average_precision"]),
                fmt_float(row["test_acceptance_rate"]),
                fmt_supported_rate(row["test_acceptance_rate"], row["test_accepted_high_workload_rate"]),
                fmt_float(row["test_high_workload_recall_by_abstention"]),
            ]
        )
    path = output_dir / "aidev_feature_boundary_ablation_table.tex"
    lines = [
        r"\begin{table}[t]",
        r"\centering",
        r"\small",
        r"\caption{Feature boundary ablation at risk limit 0.10.}",
        r"\label{tab:aidev-feature-boundary}",
        r"\setlength{\tabcolsep}{1pt}",
        r"\begin{tabularx}{\linewidth}{p{0.12\linewidth}p{0.22\linewidth}rrrrrr}",
        r"\toprule",
        "Split & Feature set & Features & AUC & AP & Std. path & High std. & High routed \\\\",
        r"\midrule",
    ]
    for row in body:
        lines.append(" & ".join(row) + r" \\")
    lines.extend(
        [
            r"\bottomrule",
            r"\end{tabularx}",
            r"\par\footnotesize{The main gate uses defensible proposal evidence. Timing-sensitive PR API aggregate fields are reported only as a diagnostic because their exact snapshot timing is not established by the public AIDev schema.}",
            r"\end{table}",
        ]
    )
    ensure_dir(path.parent)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def component_table(source: Path, output_dir: Path) -> Path:
    frame = pd.read_csv(source)
    rows = frame[frame["split"].eq("repository_disjoint")].copy()
    rows = rows.sort_values("auc", ascending=False)
    body = []
    for _, row in rows.iterrows():
        body.append(
            [
                latex_escape(COMPONENT_LABELS.get(row["component"], row["component"])),
                fmt_float(row["positive_rate"]),
                fmt_float(row["auc"]),
                fmt_float(row["avg_precision"]),
            ]
        )
    path = output_dir / "aidev_component_auc_table.tex"
    write_latex_table(
        path,
        "Unseen repository prediction of downstream workload components.",
        "tab:aidev-components",
        ["Component", "Positive rate", "AUC", "AP"],
        body,
        "lrrr",
        "The table reports component level targets so that review, communication, later work, and churn outcomes are not hidden inside one aggregate score.",
    )
    return path


def equal_coverage_baseline_table(source: Path, output_dir: Path) -> Path:
    frame = pd.read_csv(source)
    rows = frame.copy()
    order = {
        "logistic_all_features": 0,
        "cost_sensitive_workload_logistic": 1,
        "categorical_prior": 2,
        "logistic_no_agent": 3,
        "simple_text_threshold": 4,
        "selective_uncertainty_only": 5,
    }
    rows["order"] = rows["baseline"].map(order).fillna(99)
    rows = rows.sort_values(["order", "baseline"])
    body = []
    for _, row in rows.iterrows():
        body.append(
            [
                latex_escape(EQUAL_COVERAGE_BASELINE_LABELS.get(row["baseline"], row["baseline"])),
                fmt_float(row["test_acceptance_rate"]),
                fmt_float(row["test_accepted_high_workload_rate"]),
                fmt_float(row["test_high_workload_recall_by_abstention"]),
                fmt_float(row["test_workload_share_abstained"]),
                fmt_float(row["test_auc"]),
                fmt_float(row["test_average_precision"]),
            ]
        )
    path = output_dir / "aidev_equal_coverage_baseline_table.tex"
    write_latex_table(
        path,
        "Unseen repository equal-coverage baseline diagnostic.",
        "tab:aidev-equal-coverage",
        ["Baseline", "Std. path", "High std.", "High route", "Work route", "AUC", "AP"],
        body,
        "lrrrrrr",
        "All non-main baselines are thresholded to match the main gate's calibration standard-path rate. Test outcomes are used only for evaluation.",
        tabcolsep="2pt",
    )
    return path


def subgroup_fallback_table(source: Path, output_dir: Path) -> Path:
    frame = pd.read_csv(source)
    rows = frame.copy()
    order = {"global_gate": 0, "calibration_risk_flags": 1, "risk_or_low_support_flags": 2}
    rows["order"] = rows["strategy"].map(order).fillna(99)
    rows = rows.sort_values(["order", "strategy"])
    body = []
    for _, row in rows.iterrows():
        body.append(
            [
                latex_escape(FALLBACK_STRATEGY_LABELS.get(row["strategy"], row["strategy"])),
                fmt_int(row["flagged_groups"]),
                fmt_float(row["flagged_test_share"]),
                fmt_float(row["acceptance_rate"]),
                fmt_float(row["accepted_high_workload_rate"]),
                fmt_float(row["high_workload_recall_by_routing"]),
                fmt_float(row["workload_share_routed"]),
            ]
        )
    path = output_dir / "aidev_subgroup_fallback_table.tex"
    write_latex_table(
        path,
        "Unseen repository calibration-subgroup fallback diagnostic.",
        "tab:aidev-local-fallback",
        ["Strategy", "Flags", "Flag share", "Std. path", "High std.", "High route", "Work route"],
        body,
        "lrrrrrr",
        "Fallback flags are learned on calibration subgroups, then applied to the unseen repository test split. Lower standard-path risk comes with lower coverage.",
        tabcolsep="2pt",
    )
    return path


def subgroup_table(source: Path, output_dir: Path) -> Path:
    frame = pd.read_csv(source)
    rows = frame[frame["split"].isin(["temporal", "repository_disjoint"])].copy()
    rows["split_order"] = rows["split"].map({"repository_disjoint": 0, "temporal": 1})
    rows["risk_order"] = rows["risk_over_budget"].astype(str).str.lower().isin(["true", "1", "yes"])
    rows = (
        rows.sort_values(["split_order", "risk_order", "acceptance_rate", "rows"], ascending=[True, False, True, False])
        .groupby("split", group_keys=False)
        .head(6)
    )
    body = []
    subgroup_labels = {
        "agent": "Agent",
        "repo_language": "Lang.",
        "repo_star_bucket": "Stars",
        "feature_task_type": "Task type",
        "initial_churn_bucket": "Churn",
    }
    for _, row in rows.iterrows():
        body.append(
            [
                latex_escape("Unseen repo" if row["split"] == "repository_disjoint" else SPLIT_LABELS.get(row["split"], row["split"])),
                latex_escape(subgroup_labels.get(row["subgroup_type"], row["subgroup_type"])),
                latex_escape(row["subgroup_value"]),
                fmt_int(row["rows"]),
                fmt_int(row["accepted_count"]),
                fmt_float(row["high_workload_rate"]),
                fmt_float(row["acceptance_rate"]),
                fmt_count_supported_rate(row["accepted_count"], row["accepted_high_workload_rate"]),
                latex_escape("yes" if str(row["risk_over_budget"]).lower() in {"true", "1", "yes"} else "no"),
            ]
        )
    path = output_dir / "aidev_subgroup_diagnostic_table.tex"
    lines = [
        r"\begin{table}[t]",
        r"\centering",
        r"\scriptsize",
        r"\caption{AIDev subgroup diagnostics for the globally calibrated gate.}",
        r"\label{tab:aidev-subgroups}",
        r"\setlength{\tabcolsep}{1pt}",
        r"\begin{tabularx}{\linewidth}{p{0.12\linewidth}p{0.10\linewidth}Yrrrrrl}",
        r"\toprule",
        "Split & Group & Value & PRs & Std. PRs & Base high & Std. path & High std. & Flag \\\\",
        r"\midrule",
    ]
    for row in body:
        lines.append(" & ".join(row) + r" \\")
    lines.extend(
        [
            r"\bottomrule",
            r"\end{tabularx}",
            r"\par\footnotesize{Flags use the global 0.10 risk limit and require enough standard-path PRs. High std. is not interpreted when fewer than 30 PRs enter the standard path. These are diagnostics for local calibration, not causal comparisons among agents or repositories.}",
            r"\end{table}",
        ]
    )
    ensure_dir(path.parent)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def gate_error_table(source: Path, output_dir: Path) -> Path:
    frame = pd.read_csv(source)
    rows = frame[frame["split"].isin(["temporal", "repository_disjoint"])].copy()
    rows["split_order"] = rows["split"].map({"temporal": 0, "repository_disjoint": 1})
    rows["case_order"] = rows["case_type"].map(
        {
            "safe_accept_low_workload": 0,
            "false_accept_high_workload": 1,
            "useful_abstain_high_workload": 2,
            "conservative_abstain_low_workload": 3,
        }
    )
    rows = rows.sort_values(["split_order", "case_order"])
    body = []
    for _, row in rows.iterrows():
        body.append(
            [
                latex_escape(SPLIT_LABELS[row["split"]]),
                latex_escape(CASE_LABELS.get(row["case_type"], row["case_type"])),
                fmt_int(row["n"]),
                fmt_float(row["share"]),
                fmt_float(row["mean_workload"]),
                fmt_float(row["mean_score"]),
            ]
        )
    path = output_dir / "aidev_gate_error_table.tex"
    write_latex_table(
        path,
        "Retrospective AIDev gate error and routing composition at risk limit 0.10.",
        "tab:aidev-errors",
        ["Split", "Case", "PRs", "Share", "Mean workload", "Mean score"],
        body,
        "llrrrr",
        "Labels are observational retrospective strata; they do not identify causal decision errors.",
        tabcolsep="3pt",
    )
    return path


def survival_contrast_table(source: Path, output_dir: Path) -> Path:
    frame = pd.read_csv(source)
    metrics = [
        "unresolved_30d_diff_accepted_minus_abstained",
        "rmst_30d_days_diff_accepted_minus_abstained",
        "closed_rate_diff_accepted_minus_abstained",
        "30-day unresolved probability, accepted minus routed",
        "30-day RMST unresolved, accepted minus routed",
        "Observed closure rate, accepted minus routed",
    ]
    rows = frame[frame["metric"].isin(metrics)].copy()
    rows["split_order"] = rows["split"].map({"temporal": 0, "repository_disjoint": 1})
    rows["metric_order"] = rows["metric"].map({metric: idx % 3 for idx, metric in enumerate(metrics)})
    rows = rows.sort_values(["split_order", "metric_order"])
    body = []
    for _, row in rows.iterrows():
        body.append(
            [
                latex_escape(SPLIT_LABELS[row["split"]]),
                latex_escape(SURVIVAL_METRIC_LABELS.get(row["metric"], row["metric"])),
                fmt_ci(row["point"], row["ci_low"], row["ci_high"]),
            ]
        )
    path = output_dir / "aidev_survival_contrast_table.tex"
    write_latex_table(
        path,
        "Standard-path minus routed censored resolution time diagnostics.",
        "tab:aidev-survival",
        ["Split", "Metric", "Difference [95% CI]"],
        body,
        "llr",
        "Contrasts compare observed gate strata and should not be interpreted as causal effects.",
    )
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate LaTeX tables for the AIDev EMSE manuscript.")
    parser.add_argument("--results-dir", type=Path, default=RESULTS_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    output_dir = ensure_dir(args.output_dir)
    generated = [
        main_gate_table(args.results_dir / "aidev_gate_uncertainty_table.csv", output_dir),
        calibration_diagnostics_table(args.results_dir / "aidev_workload_gate_summary.csv", output_dir),
        baseline_table(args.results_dir / "aidev_baseline_comparison_table.csv", output_dir),
        equal_coverage_baseline_table(args.results_dir / "aidev_equal_coverage_baseline_table.csv", output_dir),
        feature_boundary_table(args.results_dir / "aidev_feature_boundary_ablation_table.csv", output_dir),
        component_table(args.results_dir / "aidev_component_prediction_table.csv", output_dir),
        subgroup_table(args.results_dir / "aidev_subgroup_diagnostic_table.csv", output_dir),
        subgroup_fallback_table(args.results_dir / "aidev_subgroup_fallback_table.csv", output_dir),
        gate_error_table(args.results_dir / "aidev_gate_error_table.csv", output_dir),
        survival_contrast_table(args.results_dir / "aidev_resolution_survival_contrast_table.csv", output_dir),
    ]
    write_json(
        output_dir / "aidev_latex_table_manifest.json",
        {
            "generated_tables": [str(path) for path in generated],
            "source_results_dir": str(args.results_dir),
        },
    )
    for path in generated:
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
