from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from .common import RESULTS_DIR, ensure_dir, write_json
from .evaluate_workload_gate import (
    CATEGORICAL_FEATURES,
    NUMERIC_FEATURES,
    existing_columns,
    leave_one_agent_splits,
    make_model,
    repository_disjoint_split,
    safe_auc,
    safe_average_precision,
    temporal_split,
    threshold_for_risk_budget,
)


COMPONENT_COLUMNS = [
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

SPLIT_LABELS = {
    "temporal": "Temporal",
    "repository_disjoint": "Unseen repository",
}

CASE_LABELS = {
    "safe_accept_low_workload": "Accept low workload",
    "false_accept_high_workload": "Accept high workload",
    "useful_abstain_high_workload": "Route high workload",
    "conservative_abstain_low_workload": "Route low workload",
}

CASE_COLUMNS = [
    "split",
    "case_type",
    "id",
    "html_url",
    "agent",
    "repo_id",
    "repo_language",
    "feature_task_type",
    "gate_score",
    "score_threshold",
    "score_margin_to_threshold",
    "accepted",
    "high_workload",
    "outcome_downstream_workload_raw",
    "feature_changed_files",
    "feature_additions",
    "feature_deletions",
    "feature_churn",
    "feature_initial_detail_changed_files",
    "feature_initial_detail_churn",
    "feature_initial_detail_test_files",
    *COMPONENT_COLUMNS,
    "case_summary",
]


def prepare_frame(path: Path, target_col: str, workload_col: str) -> pd.DataFrame:
    frame = pd.read_csv(path)
    frame = frame.dropna(subset=[target_col, workload_col]).copy()
    for col in existing_columns(frame, NUMERIC_FEATURES + COMPONENT_COLUMNS + [workload_col, target_col]):
        frame[col] = pd.to_numeric(frame[col], errors="coerce")
    for col in existing_columns(frame, CATEGORICAL_FEATURES + ["html_url"]):
        frame[col] = frame[col].fillna("").astype(str)
    return frame


def classify_cases(scores: np.ndarray, threshold: float, high: pd.Series) -> pd.Series:
    accepted = scores <= threshold
    high_arr = high.to_numpy(dtype=bool)
    labels = np.where(
        accepted & ~high_arr,
        "safe_accept_low_workload",
        np.where(
            accepted & high_arr,
            "false_accept_high_workload",
            np.where(high_arr, "useful_abstain_high_workload", "conservative_abstain_low_workload"),
        ),
    )
    return pd.Series(labels)


def case_summary(row: pd.Series) -> str:
    drivers = []
    changed = row.get("feature_changed_files", np.nan)
    churn = row.get("feature_churn", np.nan)
    tests = row.get("feature_initial_detail_test_files", np.nan)
    comments = row.get("outcome_issue_comment_count", np.nan)
    followups = row.get("outcome_followup_commit_count", np.nan)
    review_comments = row.get("outcome_inline_review_comment_count", np.nan)
    related = row.get("outcome_related_issue_count", np.nan)

    if pd.notna(changed) and changed > 0:
        drivers.append(f"{changed:.0f} initial files")
    if pd.notna(churn) and churn > 0:
        drivers.append(f"{churn:.0f} initial churn")
    if pd.notna(tests) and tests > 0:
        drivers.append(f"{tests:.0f} initial test-like files")
    if pd.notna(followups) and followups > 0:
        drivers.append(f"{followups:.0f} follow-up commits")
    if pd.notna(comments) and comments > 0:
        drivers.append(f"{comments:.0f} issue comments")
    if pd.notna(review_comments) and review_comments > 0:
        drivers.append(f"{review_comments:.0f} inline review comments")
    if pd.notna(related) and related > 0:
        drivers.append(f"{related:.0f} related issues")

    prefix = f"{row.get('agent', '')} / {row.get('repo_language', '')}".strip(" /")
    detail = "; ".join(drivers[:5]) if drivers else "low observed component counts"
    return f"{prefix}: {detail}"


def top_agents(frame: pd.DataFrame, limit: int = 5) -> str:
    if frame.empty or "agent" not in frame.columns:
        return ""
    counts = frame["agent"].fillna("").astype(str).value_counts().head(limit)
    return "; ".join(f"{idx}={int(val)}" for idx, val in counts.items())


def summarize_cases(test: pd.DataFrame) -> pd.DataFrame:
    rows = []
    component_cols = [col for col in COMPONENT_COLUMNS if col in test.columns]
    for (split, case_type), group in test.groupby(["split", "case_type"], dropna=False):
        row = {
            "split": split,
            "case_type": case_type,
            "n": int(len(group)),
            "share_of_split": float(len(group) / len(test[test["split"] == split])) if len(test[test["split"] == split]) else 0.0,
            "accepted_rate": float(group["accepted"].mean()) if len(group) else 0.0,
            "high_workload_rate": float(group["high_workload"].mean()) if len(group) else 0.0,
            "mean_gate_score": float(group["gate_score"].mean()) if len(group) else 0.0,
            "mean_workload": float(group["outcome_downstream_workload_raw"].mean()) if len(group) else 0.0,
            "median_workload": float(group["outcome_downstream_workload_raw"].median()) if len(group) else 0.0,
            "top_agents": top_agents(group),
        }
        for col in component_cols:
            row[f"mean_{col}"] = float(group[col].mean())
        rows.append(row)
    return pd.DataFrame(rows).sort_values(["split", "case_type"]).reset_index(drop=True)


def sample_cases(test: pd.DataFrame, examples_per_type: int) -> pd.DataFrame:
    samples = []
    for (split, case_type), group in test.groupby(["split", "case_type"], dropna=False):
        if group.empty:
            continue
        ordered = group.copy()
        if case_type == "false_accept_high_workload":
            ordered = ordered.sort_values(
                ["outcome_downstream_workload_raw", "gate_score"],
                ascending=[False, False],
            )
        elif case_type == "useful_abstain_high_workload":
            ordered = ordered.sort_values(
                ["outcome_downstream_workload_raw", "gate_score"],
                ascending=[False, False],
            )
        elif case_type == "conservative_abstain_low_workload":
            ordered = ordered.sort_values(
                ["score_margin_to_threshold", "outcome_downstream_workload_raw"],
                ascending=[True, True],
            )
        else:
            ordered = ordered.sort_values(
                ["gate_score", "outcome_downstream_workload_raw"],
                ascending=[True, True],
            )
        samples.append(ordered.head(examples_per_type))

    if not samples:
        return pd.DataFrame(columns=CASE_COLUMNS)
    out = pd.concat(samples, ignore_index=True)
    return out[[col for col in CASE_COLUMNS if col in out.columns]]


def markdown_table(frame: pd.DataFrame, floatfmt: str = ".3f") -> str:
    if frame.empty:
        return "_No rows._"

    def fmt(value: object) -> str:
        if pd.isna(value):
            return ""
        if isinstance(value, (float, np.floating)):
            return format(float(value), floatfmt)
        if isinstance(value, (int, np.integer)):
            return str(int(value))
        text = str(value).replace("\n", " ").replace("|", "\\|")
        return text

    columns = list(frame.columns)
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join(["---"] * len(columns)) + " |",
    ]
    for _, row in frame.iterrows():
        lines.append("| " + " | ".join(fmt(row[col]) for col in columns) + " |")
    return "\n".join(lines)


def display_frame(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    if "split" in out.columns:
        out["split"] = out["split"].map(SPLIT_LABELS).fillna(out["split"])
    if "case_type" in out.columns:
        out["case_type"] = out["case_type"].map(CASE_LABELS).fillna(out["case_type"])
    return out.rename(
        columns={
            "case_type": "case",
            "share_of_split": "share",
            "test_accepted_high_rate": "test_accepted_high_workload_rate",
        }
    )


def fit_and_label_split(
    split_name: str,
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
        raise ValueError("No proposal time features are available for gate error analysis.")

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
    threshold, cal_acceptance, cal_risk = threshold_for_risk_budget(cal_scores, cal_high, risk_budget)

    labeled = test.copy().reset_index(drop=True)
    labeled["split"] = split_name
    labeled["gate_score"] = test_scores
    labeled["score_threshold"] = threshold
    labeled["score_margin_to_threshold"] = labeled["gate_score"] - threshold
    labeled["accepted"] = labeled["gate_score"] <= threshold
    labeled["high_workload"] = test_high.reset_index(drop=True).astype(bool)
    labeled["case_type"] = classify_cases(test_scores, threshold, test_high)
    labeled["case_summary"] = labeled.apply(case_summary, axis=1)

    diagnostics = {
        "split": split_name,
        "train_rows": int(len(train)),
        "calibration_rows": int(len(calibration)),
        "test_rows": int(len(test)),
        "risk_budget": risk_budget,
        "high_workload_quantile": high_quantile,
        "high_workload_threshold": high_threshold,
        "score_threshold": threshold,
        "calibrated_acceptance_target": cal_acceptance,
        "calibrated_accepted_high_rate": cal_risk,
        "test_auc": safe_auc(test_high, test_scores),
        "test_average_precision": safe_average_precision(test_high, test_scores),
        "test_acceptance_rate": float(labeled["accepted"].mean()),
        "test_accepted_high_rate": float(labeled.loc[labeled["accepted"], "high_workload"].mean())
        if labeled["accepted"].any()
        else 0.0,
        "features": ",".join(features),
    }
    return labeled, diagnostics


def write_report(path: Path, diagnostics: pd.DataFrame, summary: pd.DataFrame, samples: pd.DataFrame) -> None:
    lines = [
        "# AIDev Gate Error and Routing Analysis",
        "",
        "This report uses the same defensible-feature logistic gate and calibrated risk protocol as the main AIDev workload gate analysis.",
        "It supports RQ4 by separating accepted low workload PRs, accepted high workload misses, routed high workload PRs, and routed low workload PRs.",
        "",
        "## Split Diagnostics",
        "",
        markdown_table(display_frame(diagnostics), floatfmt=".3f"),
        "",
        "## Case-Type Summary",
        "",
        markdown_table(display_frame(summary), floatfmt=".3f"),
        "",
        "## Example Cases",
        "",
    ]

    display_cols = [
        "split",
        "case_type",
        "html_url",
        "agent",
        "repo_language",
        "feature_task_type",
        "gate_score",
        "score_threshold",
        "outcome_downstream_workload_raw",
        "case_summary",
    ]
    for (split, case_type), group in samples.groupby(["split", "case_type"], dropna=False):
        split_label = SPLIT_LABELS.get(split, split)
        case_label = CASE_LABELS.get(case_type, case_type)
        lines.extend([f"### {split_label}: {case_label}", ""])
        lines.append(markdown_table(display_frame(group[[col for col in display_cols if col in group.columns]]), floatfmt=".3f"))
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze AIDev workload gate error and routing cases for RQ4.")
    parser.add_argument("--features", type=Path, default=RESULTS_DIR / "aidev_pr_level_features.csv")
    parser.add_argument("--output-dir", type=Path, default=RESULTS_DIR)
    parser.add_argument("--target", default="outcome_downstream_workload_log")
    parser.add_argument("--workload", default="outcome_downstream_workload_raw")
    parser.add_argument("--high-workload-quantile", type=float, default=0.80)
    parser.add_argument("--risk-budget", type=float, default=0.10)
    parser.add_argument("--examples-per-type", type=int, default=6)
    parser.add_argument("--include-agent-splits", action="store_true")
    parser.add_argument("--min-agent-test-rows", type=int, default=300)
    parser.add_argument("--seed", type=int, default=23)
    args = parser.parse_args()

    frame = prepare_frame(args.features, args.target, args.workload)
    split_specs: list[tuple[str, pd.DataFrame, pd.DataFrame, pd.DataFrame]] = [
        ("temporal", *temporal_split(frame)),
        ("repository_disjoint", *repository_disjoint_split(frame, args.seed)),
    ]
    if args.include_agent_splits:
        split_specs.extend(leave_one_agent_splits(frame, args.min_agent_test_rows))

    labeled_frames = []
    diagnostic_rows = []
    for split_name, train, calibration, test in split_specs:
        labeled, diagnostics = fit_and_label_split(
            split_name,
            train,
            calibration,
            test,
            args.target,
            args.workload,
            args.high_workload_quantile,
            args.risk_budget,
        )
        labeled_frames.append(labeled)
        diagnostic_rows.append(diagnostics)

    labeled_all = pd.concat(labeled_frames, ignore_index=True)
    diagnostics = pd.DataFrame(diagnostic_rows)
    summary = summarize_cases(labeled_all)
    samples = sample_cases(labeled_all, args.examples_per_type)

    output_dir = ensure_dir(args.output_dir)
    diagnostics_path = output_dir / "aidev_gate_error_diagnostics.csv"
    summary_path = output_dir / "aidev_gate_error_summary.csv"
    samples_path = output_dir / "aidev_gate_error_cases.csv"
    report_path = output_dir / "aidev_gate_error_report.md"

    diagnostics.to_csv(diagnostics_path, index=False)
    summary.to_csv(summary_path, index=False)
    samples.to_csv(samples_path, index=False)
    write_report(report_path, diagnostics, summary, samples)
    write_json(
        output_dir / "aidev_gate_error_analysis.json",
        {
            "diagnostics_csv": str(diagnostics_path),
            "summary_csv": str(summary_path),
            "cases_csv": str(samples_path),
            "report_md": str(report_path),
            "splits": diagnostics["split"].tolist(),
            "risk_budget": args.risk_budget,
            "examples_per_type": args.examples_per_type,
        },
    )
    print(f"Wrote gate error analysis to {report_path}")


if __name__ == "__main__":
    main()
