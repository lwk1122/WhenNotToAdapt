"""Build a column-level data dictionary for the AIDev PR feature table."""

from __future__ import annotations

import argparse
import ast
import csv
import json
import numbers
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
FEATURES_PATH = ROOT / "exp" / "results" / "emse_aidev" / "aidev_pr_level_features.csv"
SUMMARY_PATH = ROOT / "exp" / "results" / "emse_aidev" / "aidev_feature_build_summary.json"
OUTPUT_CSV = ROOT / "paper" / "emse_artifact_package" / "aidev_pr_level_data_dictionary.csv"
OUTPUT_MD = ROOT / "paper" / "emse_artifact_package" / "aidev_pr_level_data_dictionary.md"
GATE_SCRIPT = ROOT / "exp" / "scripts" / "emse_aidev" / "evaluate_workload_gate.py"


OUTPUT_COLUMNS = [
    "column",
    "group",
    "decision_time_status",
    "source_or_derivation",
    "definition",
    "unit_or_scale",
    "missing_value_rule",
    "used_in_main_gate",
    "pandas_dtype",
    "non_null_count",
    "missing_count",
    "missing_rate",
    "min",
    "max",
    "n_unique",
    "observed_values_sample",
]


COLUMN_INFO: dict[str, dict[str, str]] = {
    "id": {
        "group": "identifier",
        "decision_time_status": "proposal_time_identifier",
        "source_or_derivation": "AIDev pull_request.id.",
        "definition": "AIDev pull-request identifier used as the row key.",
        "unit_or_scale": "identifier",
        "missing_value_rule": "Required row identifier; missing values indicate an unusable PR row.",
    },
    "repo_id": {
        "group": "identifier",
        "decision_time_status": "proposal_time_identifier",
        "source_or_derivation": "AIDev pull_request.repo_id.",
        "definition": "Repository identifier associated with the pull request.",
        "unit_or_scale": "identifier",
        "missing_value_rule": "Required for unseen repository splitting; missing values are treated as missing repository group labels.",
    },
    "number": {
        "group": "identifier",
        "decision_time_status": "proposal_time_identifier",
        "source_or_derivation": "AIDev pull_request.number.",
        "definition": "Pull-request number within the repository.",
        "unit_or_scale": "integer identifier",
        "missing_value_rule": "Required for PR lookup and descriptive reporting.",
    },
    "html_url": {
        "group": "identifier",
        "decision_time_status": "proposal_time_identifier",
        "source_or_derivation": "AIDev pull_request.html_url.",
        "definition": "GitHub web URL for the pull request.",
        "unit_or_scale": "URL",
        "missing_value_rule": "Used for auditability only; missing values do not enter models.",
    },
    "agent": {
        "group": "proposal_metadata",
        "decision_time_status": "proposal_time_feature",
        "source_or_derivation": "AIDev pull_request.agent.",
        "definition": "Coding-agent label reported for the PR.",
        "unit_or_scale": "categorical label",
        "missing_value_rule": "Categorical imputer fills missing values in the main gate pipeline.",
    },
    "created_at": {
        "group": "proposal_metadata",
        "decision_time_status": "proposal_time_metadata",
        "source_or_derivation": "AIDev pull_request.created_at parsed as datetime text in CSV output.",
        "definition": "Pull-request creation timestamp used for chronological splits.",
        "unit_or_scale": "UTC timestamp",
        "missing_value_rule": "Rows with missing timestamps sort to the end of chronological splits.",
    },
    "closed_at": {
        "group": "outcome_status",
        "decision_time_status": "post_proposal_status",
        "source_or_derivation": "AIDev pull_request.closed_at parsed as datetime text in CSV output.",
        "definition": "Pull-request close timestamp used to derive resolution time.",
        "unit_or_scale": "UTC timestamp",
        "missing_value_rule": "Missing values indicate open or unavailable close time; resolution hours are missing.",
    },
    "merged_at": {
        "group": "outcome_status",
        "decision_time_status": "post_proposal_status",
        "source_or_derivation": "AIDev pull_request.merged_at parsed as datetime text in CSV output.",
        "definition": "Pull-request merge timestamp used to derive merged status.",
        "unit_or_scale": "UTC timestamp",
        "missing_value_rule": "Missing values indicate unmerged or unavailable merge time.",
    },
    "feature_title_chars": {
        "group": "proposal_text_feature",
        "decision_time_status": "proposal_time_feature",
        "source_or_derivation": "Character count of AIDev pull_request.title.",
        "definition": "Length of the PR title.",
        "unit_or_scale": "characters",
        "missing_value_rule": "Missing title text is counted as zero characters.",
    },
    "feature_body_chars": {
        "group": "proposal_text_feature",
        "decision_time_status": "proposal_time_feature",
        "source_or_derivation": "Character count of AIDev pull_request.body.",
        "definition": "Length of the PR body.",
        "unit_or_scale": "characters",
        "missing_value_rule": "Missing body text is counted as zero characters.",
    },
    "feature_title_mentions_test": {
        "group": "proposal_text_feature",
        "decision_time_status": "proposal_time_feature",
        "source_or_derivation": "Regex flag over PR title for test, pytest, ci, lint, or build terms.",
        "definition": "Whether the PR title explicitly mentions testing or CI/build language.",
        "unit_or_scale": "binary indicator",
        "missing_value_rule": "Missing title text maps to 0.",
    },
    "feature_body_mentions_test": {
        "group": "proposal_text_feature",
        "decision_time_status": "proposal_time_feature",
        "source_or_derivation": "Regex flag over PR body for test, pytest, ci, lint, or build terms.",
        "definition": "Whether the PR body explicitly mentions testing or CI/build language.",
        "unit_or_scale": "binary indicator",
        "missing_value_rule": "Missing body text maps to 0.",
    },
    "feature_body_mentions_fix": {
        "group": "proposal_text_feature",
        "decision_time_status": "proposal_time_feature",
        "source_or_derivation": "Regex flag over PR body for fix, bug, error, fail, or issue terms.",
        "definition": "Whether the PR body uses fix/failure language.",
        "unit_or_scale": "binary indicator",
        "missing_value_rule": "Missing body text maps to 0.",
    },
    "feature_changed_files": {
        "group": "timing_sensitive_api_aggregate",
        "decision_time_status": "timing_sensitive_diagnostic_feature",
        "source_or_derivation": "AIDev pull_request.changed_files, with first-commit detail fallback when the API field is zero.",
        "definition": "Changed-file count from the PR API aggregate; exact snapshot timing is not used for the main gate.",
        "unit_or_scale": "files",
        "missing_value_rule": "Used only in timing-boundary diagnostics unless a deployment proves initial-snapshot availability.",
    },
    "feature_additions": {
        "group": "timing_sensitive_api_aggregate",
        "decision_time_status": "timing_sensitive_diagnostic_feature",
        "source_or_derivation": "AIDev pull_request.additions, with first-commit detail fallback when the API field is zero.",
        "definition": "Added-line count from the PR API aggregate; exact snapshot timing is not used for the main gate.",
        "unit_or_scale": "lines",
        "missing_value_rule": "Used only in timing-boundary diagnostics unless a deployment proves initial-snapshot availability.",
    },
    "feature_deletions": {
        "group": "timing_sensitive_api_aggregate",
        "decision_time_status": "timing_sensitive_diagnostic_feature",
        "source_or_derivation": "AIDev pull_request.deletions, with first-commit detail fallback when the API field is zero.",
        "definition": "Deleted-line count from the PR API aggregate; exact snapshot timing is not used for the main gate.",
        "unit_or_scale": "lines",
        "missing_value_rule": "Used only in timing-boundary diagnostics unless a deployment proves initial-snapshot availability.",
    },
    "feature_initial_commit_count": {
        "group": "timing_sensitive_api_aggregate",
        "decision_time_status": "timing_sensitive_diagnostic_feature",
        "source_or_derivation": "AIDev pull_request.commits.",
        "definition": "Commit count reported on the PR API record; exact snapshot timing is not used for the main gate.",
        "unit_or_scale": "commits",
        "missing_value_rule": "Used only in timing-boundary diagnostics unless a deployment proves initial-snapshot availability.",
    },
    "feature_initial_review_comment_count_api": {
        "group": "timing_sensitive_api_aggregate",
        "decision_time_status": "timing_sensitive_diagnostic_feature",
        "source_or_derivation": "AIDev pull_request.review_comments.",
        "definition": "Review-comment count reported on the PR API record; exact snapshot timing is not used for the main gate.",
        "unit_or_scale": "comments",
        "missing_value_rule": "Used only in timing-boundary diagnostics unless a deployment proves initial-snapshot availability.",
    },
    "feature_initial_issue_comment_count_api": {
        "group": "timing_sensitive_api_aggregate",
        "decision_time_status": "timing_sensitive_diagnostic_feature",
        "source_or_derivation": "AIDev pull_request.comments.",
        "definition": "Issue-thread comment count reported on the PR API record; exact snapshot timing is not used for the main gate.",
        "unit_or_scale": "comments",
        "missing_value_rule": "Used only in timing-boundary diagnostics unless a deployment proves initial-snapshot availability.",
    },
    "feature_churn": {
        "group": "timing_sensitive_api_aggregate",
        "decision_time_status": "timing_sensitive_diagnostic_feature",
        "source_or_derivation": "feature_additions + feature_deletions.",
        "definition": "Line churn from timing-sensitive PR API aggregate fields.",
        "unit_or_scale": "lines",
        "missing_value_rule": "Used only in timing-boundary diagnostics unless a deployment proves initial-snapshot availability.",
    },
    "feature_repo_stars": {
        "group": "repository_feature",
        "decision_time_status": "proposal_time_feature",
        "source_or_derivation": "AIDev repository stargazers_count or stars.",
        "definition": "Repository star count.",
        "unit_or_scale": "stars",
        "missing_value_rule": "Numeric imputer fills missing values in the main gate pipeline.",
    },
    "feature_repo_forks": {
        "group": "repository_feature",
        "decision_time_status": "proposal_time_feature",
        "source_or_derivation": "AIDev repository forks_count.",
        "definition": "Repository fork count.",
        "unit_or_scale": "forks",
        "missing_value_rule": "Numeric imputer fills missing values in the main gate pipeline.",
    },
    "feature_repo_watchers": {
        "group": "repository_feature",
        "decision_time_status": "proposal_time_feature",
        "source_or_derivation": "AIDev repository watchers_count.",
        "definition": "Repository watcher count.",
        "unit_or_scale": "watchers",
        "missing_value_rule": "Numeric imputer fills missing values in the main gate pipeline.",
    },
    "feature_repo_open_issues": {
        "group": "repository_feature",
        "decision_time_status": "proposal_time_feature",
        "source_or_derivation": "AIDev repository open_issues_count.",
        "definition": "Repository open-issue count.",
        "unit_or_scale": "issues",
        "missing_value_rule": "Numeric imputer fills missing values in the main gate pipeline.",
    },
    "repo_language": {
        "group": "repository_feature",
        "decision_time_status": "proposal_time_feature",
        "source_or_derivation": "AIDev repository language.",
        "definition": "Primary repository programming language.",
        "unit_or_scale": "categorical label",
        "missing_value_rule": "Categorical imputer fills missing values in the main gate pipeline.",
    },
    "feature_task_type": {
        "group": "proposal_task_feature",
        "decision_time_status": "proposal_time_feature",
        "source_or_derivation": "AIDev pr_task_type.type.",
        "definition": "Task-type label assigned in the AIDev release.",
        "unit_or_scale": "categorical label",
        "missing_value_rule": "Categorical imputer fills missing values in the main gate pipeline.",
    },
    "feature_task_type_confidence": {
        "group": "proposal_task_feature",
        "decision_time_status": "proposal_time_feature",
        "source_or_derivation": "AIDev pr_task_type.confidence.",
        "definition": "Confidence score associated with the AIDev task-type label.",
        "unit_or_scale": "score",
        "missing_value_rule": "Numeric imputer fills missing values in the main gate pipeline.",
    },
    "feature_initial_detail_changed_files": {
        "group": "proposal_diff_feature",
        "decision_time_status": "proposal_time_feature",
        "source_or_derivation": "Unique filenames in pr_commit_details for the first PR commit.",
        "definition": "Changed-file count in the first observed commit.",
        "unit_or_scale": "files",
        "missing_value_rule": "Absent commit-detail rows map to 0.",
    },
    "feature_initial_detail_additions": {
        "group": "proposal_diff_feature",
        "decision_time_status": "proposal_time_feature",
        "source_or_derivation": "Sum of additions in pr_commit_details for the first PR commit.",
        "definition": "Added lines in the first observed commit.",
        "unit_or_scale": "lines",
        "missing_value_rule": "Absent commit-detail rows map to 0.",
    },
    "feature_initial_detail_deletions": {
        "group": "proposal_diff_feature",
        "decision_time_status": "proposal_time_feature",
        "source_or_derivation": "Sum of deletions in pr_commit_details for the first PR commit.",
        "definition": "Deleted lines in the first observed commit.",
        "unit_or_scale": "lines",
        "missing_value_rule": "Absent commit-detail rows map to 0.",
    },
    "feature_initial_detail_churn": {
        "group": "proposal_diff_feature",
        "decision_time_status": "proposal_time_feature",
        "source_or_derivation": "Sum of changes in pr_commit_details for the first PR commit.",
        "definition": "Line churn in the first observed commit.",
        "unit_or_scale": "lines",
        "missing_value_rule": "Absent commit-detail rows map to 0.",
    },
    "feature_initial_detail_added_files": {
        "group": "proposal_diff_feature",
        "decision_time_status": "proposal_time_feature",
        "source_or_derivation": "Count of first-commit pr_commit_details rows with status added.",
        "definition": "Added-file count in the first observed commit.",
        "unit_or_scale": "files",
        "missing_value_rule": "Absent commit-detail rows map to 0.",
    },
    "feature_initial_detail_modified_files": {
        "group": "proposal_diff_feature",
        "decision_time_status": "proposal_time_feature",
        "source_or_derivation": "Count of first-commit pr_commit_details rows with status modified.",
        "definition": "Modified-file count in the first observed commit.",
        "unit_or_scale": "files",
        "missing_value_rule": "Absent commit-detail rows map to 0.",
    },
    "feature_initial_detail_removed_files": {
        "group": "proposal_diff_feature",
        "decision_time_status": "proposal_time_feature",
        "source_or_derivation": "Count of first-commit pr_commit_details rows with status removed.",
        "definition": "Removed-file count in the first observed commit.",
        "unit_or_scale": "files",
        "missing_value_rule": "Absent commit-detail rows map to 0.",
    },
    "feature_initial_detail_test_files": {
        "group": "proposal_diff_feature",
        "decision_time_status": "proposal_time_feature",
        "source_or_derivation": "Unique first-commit filenames matching test-like path/name patterns.",
        "definition": "Test-like files touched in the first observed commit.",
        "unit_or_scale": "files",
        "missing_value_rule": "Absent commit-detail rows map to 0.",
    },
    "outcome_commit_detail_changed_files": {
        "group": "post_proposal_commit_outcome",
        "decision_time_status": "post_proposal_outcome",
        "source_or_derivation": "Unique filenames across all pr_commit_details rows for the PR.",
        "definition": "Total changed-file count observed in commit-detail records.",
        "unit_or_scale": "files",
        "missing_value_rule": "Absent commit-detail rows map to 0.",
    },
    "outcome_commit_detail_additions": {
        "group": "post_proposal_commit_outcome",
        "decision_time_status": "post_proposal_outcome",
        "source_or_derivation": "Sum of additions across all pr_commit_details rows for the PR.",
        "definition": "Total added lines observed in commit-detail records.",
        "unit_or_scale": "lines",
        "missing_value_rule": "Absent commit-detail rows map to 0.",
    },
    "outcome_commit_detail_deletions": {
        "group": "post_proposal_commit_outcome",
        "decision_time_status": "post_proposal_outcome",
        "source_or_derivation": "Sum of deletions across all pr_commit_details rows for the PR.",
        "definition": "Total deleted lines observed in commit-detail records.",
        "unit_or_scale": "lines",
        "missing_value_rule": "Absent commit-detail rows map to 0.",
    },
    "outcome_commit_detail_churn": {
        "group": "post_proposal_commit_outcome",
        "decision_time_status": "post_proposal_outcome",
        "source_or_derivation": "Sum of changes across all pr_commit_details rows for the PR.",
        "definition": "Total line churn observed in commit-detail records.",
        "unit_or_scale": "lines",
        "missing_value_rule": "Absent commit-detail rows map to 0.",
    },
    "outcome_followup_detail_changed_files": {
        "group": "post_proposal_followup_outcome",
        "decision_time_status": "post_proposal_outcome",
        "source_or_derivation": "Unique filenames in pr_commit_details rows after the first PR commit.",
        "definition": "Changed-file count in follow-up commits after the first observed commit.",
        "unit_or_scale": "files",
        "missing_value_rule": "Absent follow-up commit-detail rows map to 0.",
    },
    "outcome_followup_detail_additions": {
        "group": "post_proposal_followup_outcome",
        "decision_time_status": "post_proposal_outcome",
        "source_or_derivation": "Sum of additions in pr_commit_details rows after the first PR commit.",
        "definition": "Added lines in follow-up commits after the first observed commit.",
        "unit_or_scale": "lines",
        "missing_value_rule": "Absent follow-up commit-detail rows map to 0.",
    },
    "outcome_followup_detail_deletions": {
        "group": "post_proposal_followup_outcome",
        "decision_time_status": "post_proposal_outcome",
        "source_or_derivation": "Sum of deletions in pr_commit_details rows after the first PR commit.",
        "definition": "Deleted lines in follow-up commits after the first observed commit.",
        "unit_or_scale": "lines",
        "missing_value_rule": "Absent follow-up commit-detail rows map to 0.",
    },
    "outcome_followup_detail_churn": {
        "group": "post_proposal_followup_outcome",
        "decision_time_status": "post_proposal_outcome",
        "source_or_derivation": "Sum of changes in pr_commit_details rows after the first PR commit.",
        "definition": "Line churn in follow-up commits after the first observed commit.",
        "unit_or_scale": "lines",
        "missing_value_rule": "Absent follow-up commit-detail rows map to 0.",
    },
    "outcome_followup_detail_test_files": {
        "group": "post_proposal_followup_outcome",
        "decision_time_status": "post_proposal_outcome",
        "source_or_derivation": "Unique follow-up filenames matching test-like path/name patterns.",
        "definition": "Test-like files touched in follow-up commits after the first observed commit.",
        "unit_or_scale": "files",
        "missing_value_rule": "Absent follow-up commit-detail rows map to 0.",
    },
    "outcome_review_count": {
        "group": "review_outcome",
        "decision_time_status": "post_proposal_outcome",
        "source_or_derivation": "Count of AIDev pr_reviews rows linked to the PR.",
        "definition": "Number of PR reviews observed after proposal.",
        "unit_or_scale": "reviews",
        "missing_value_rule": "No linked review rows map to 0.",
    },
    "outcome_request_changes_count": {
        "group": "review_outcome",
        "decision_time_status": "post_proposal_outcome",
        "source_or_derivation": "Count of AIDev pr_reviews rows whose state contains change.",
        "definition": "Number of review decisions requesting changes.",
        "unit_or_scale": "reviews",
        "missing_value_rule": "No linked reviews requesting changes map to 0.",
    },
    "outcome_human_review_count": {
        "group": "review_outcome",
        "decision_time_status": "post_proposal_outcome",
        "source_or_derivation": "Count of AIDev pr_reviews rows with user_type equal to user.",
        "definition": "Number of human-user review records.",
        "unit_or_scale": "reviews",
        "missing_value_rule": "No linked human review rows map to 0.",
    },
    "outcome_inline_review_comment_count": {
        "group": "review_outcome",
        "decision_time_status": "post_proposal_outcome",
        "source_or_derivation": "Count of AIDev pr_review_comments_v2 rows linked to the PR.",
        "definition": "Number of inline review comments.",
        "unit_or_scale": "comments",
        "missing_value_rule": "No linked inline review comments map to 0.",
    },
    "outcome_issue_comment_count": {
        "group": "discussion_outcome",
        "decision_time_status": "post_proposal_outcome",
        "source_or_derivation": "Count of AIDev pr_comments rows linked to the PR.",
        "definition": "Number of PR issue-thread comments.",
        "unit_or_scale": "comments",
        "missing_value_rule": "No linked issue comments map to 0.",
    },
    "outcome_commit_count": {
        "group": "commit_outcome",
        "decision_time_status": "post_proposal_outcome",
        "source_or_derivation": "Count of AIDev pr_commits rows linked to the PR.",
        "definition": "Total commit count observed for the PR.",
        "unit_or_scale": "commits",
        "missing_value_rule": "No linked commit rows map to 0.",
    },
    "outcome_followup_commit_count": {
        "group": "commit_outcome",
        "decision_time_status": "post_proposal_outcome",
        "source_or_derivation": "max(outcome_commit_count - 1, 0).",
        "definition": "Commit count after the first observed proposal commit.",
        "unit_or_scale": "commits",
        "missing_value_rule": "Derived from outcome_commit_count after its missing-value handling.",
    },
    "outcome_commit_detail_rows": {
        "group": "commit_outcome",
        "decision_time_status": "post_proposal_outcome",
        "source_or_derivation": "Count of AIDev pr_commit_details rows linked to the PR.",
        "definition": "Number of file-level commit-detail rows.",
        "unit_or_scale": "rows",
        "missing_value_rule": "No linked commit-detail rows map to 0.",
    },
    "outcome_timeline_event_count": {
        "group": "timeline_outcome",
        "decision_time_status": "post_proposal_outcome",
        "source_or_derivation": "Count of AIDev pr_timeline rows linked to the PR.",
        "definition": "Number of timeline events recorded for the PR.",
        "unit_or_scale": "events",
        "missing_value_rule": "No linked timeline rows map to 0.",
    },
    "outcome_related_issue_count": {
        "group": "discussion_outcome",
        "decision_time_status": "post_proposal_outcome",
        "source_or_derivation": "Count of AIDev related_issue rows linked to the PR.",
        "definition": "Number of issues related to the PR.",
        "unit_or_scale": "issues",
        "missing_value_rule": "No linked related-issue rows map to 0.",
    },
    "outcome_merged": {
        "group": "resolution_outcome",
        "decision_time_status": "post_proposal_outcome",
        "source_or_derivation": "Indicator that merged_at is non-missing.",
        "definition": "Whether the PR was merged.",
        "unit_or_scale": "binary indicator",
        "missing_value_rule": "Missing merged_at maps to 0.",
    },
    "outcome_resolution_hours": {
        "group": "resolution_outcome",
        "decision_time_status": "post_proposal_outcome",
        "source_or_derivation": "closed_at - created_at in hours.",
        "definition": "Elapsed time from PR creation to close.",
        "unit_or_scale": "hours",
        "missing_value_rule": "Missing when created_at or closed_at is unavailable; open PRs are treated as censored in survival diagnostics.",
    },
    "outcome_downstream_workload_raw": {
        "group": "derived_workload_outcome",
        "decision_time_status": "derived_post_proposal_outcome",
        "source_or_derivation": "Sum of outcome_review_count, outcome_request_changes_count, outcome_inline_review_comment_count, outcome_issue_comment_count, and outcome_followup_commit_count.",
        "definition": "Primary aggregate downstream workload count used for gate diagnostics.",
        "unit_or_scale": "count",
        "missing_value_rule": "Derived from workload components after absent linked rows map to 0.",
    },
    "outcome_downstream_workload_log": {
        "group": "derived_workload_outcome",
        "decision_time_status": "derived_post_proposal_outcome",
        "source_or_derivation": "log1p(outcome_downstream_workload_raw).",
        "definition": "Log-transformed primary downstream workload target.",
        "unit_or_scale": "log count",
        "missing_value_rule": "Derived from outcome_downstream_workload_raw.",
    },
}


def extract_list_constants(path: Path, names: set[str]) -> dict[str, list[str]]:
    module = ast.parse(path.read_text(encoding="utf-8"))
    values: dict[str, list[str]] = {}
    for node in module.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id in names:
                values[target.id] = list(ast.literal_eval(node.value))
    missing = names - set(values)
    if missing:
        raise ValueError(f"Could not extract constants from {path}: {', '.join(sorted(missing))}")
    return values


def load_summary(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def format_number(value: Any) -> str:
    if pd.isna(value):
        return ""
    if isinstance(value, numbers.Integral) and not isinstance(value, bool):
        return str(int(value))
    if isinstance(value, numbers.Real) and not isinstance(value, bool):
        return f"{float(value):.6g}"
    return str(value)


def sample_values(series: pd.Series, limit: int = 5) -> str:
    values = series.dropna().drop_duplicates().head(limit).tolist()
    return "; ".join(format_number(value) for value in values)


def numeric_bounds(series: pd.Series) -> tuple[str, str]:
    if not pd.api.types.is_numeric_dtype(series):
        return "", ""
    non_null = series.dropna()
    if non_null.empty:
        return "", ""
    return format_number(non_null.min()), format_number(non_null.max())


def default_column_info(column: str) -> dict[str, str]:
    if column.startswith("feature_"):
        return {
            "group": "proposal_feature",
            "decision_time_status": "proposal_time_feature",
            "source_or_derivation": "Derived in exp/scripts/emse_aidev/build_features.py.",
            "definition": "Proposal-time feature used for AIDev gate diagnostics.",
            "unit_or_scale": "see build_features.py",
            "missing_value_rule": "Model-specific imputers handle missing values when used as predictors.",
        }
    if column.startswith("outcome_"):
        return {
            "group": "post_proposal_outcome",
            "decision_time_status": "post_proposal_outcome",
            "source_or_derivation": "Derived in exp/scripts/emse_aidev/build_features.py.",
            "definition": "Outcome observed after the initial proposal.",
            "unit_or_scale": "see build_features.py",
            "missing_value_rule": "Absent linked rows generally map to 0 unless documented otherwise.",
        }
    return {
        "group": "metadata",
        "decision_time_status": "metadata",
        "source_or_derivation": "AIDev source table or derived metadata.",
        "definition": "Metadata column.",
        "unit_or_scale": "metadata",
        "missing_value_rule": "Not used by the main gate unless explicitly marked.",
    }


def build_rows(frame: pd.DataFrame, gate_features: set[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for column in frame.columns:
        series = frame[column]
        info = {**default_column_info(column), **COLUMN_INFO.get(column, {})}
        min_value, max_value = numeric_bounds(series)
        missing_count = int(series.isna().sum())
        row = {
            "column": column,
            **info,
            "used_in_main_gate": "yes" if column in gate_features else "no",
            "pandas_dtype": str(series.dtype),
            "non_null_count": int(series.notna().sum()),
            "missing_count": missing_count,
            "missing_rate": f"{missing_count / len(frame):.6f}" if len(frame) else "0.000000",
            "min": min_value,
            "max": max_value,
            "n_unique": int(series.nunique(dropna=True)),
            "observed_values_sample": sample_values(series),
        }
        rows.append(row)
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, rows: list[dict[str, Any]], summary: dict[str, Any]) -> None:
    source_rows = summary.get("rows", len(rows))
    lines = [
        "# AIDev PR Level Feature Data Dictionary",
        "",
        "This generated dictionary documents `exp/results/emse_aidev/aidev_pr_level_features.csv`.",
        "",
        f"- Source feature rows: {source_rows}",
        f"- Documented columns: {len(rows)}",
        "- Decision time rule: `proposal_time_*` fields may be used by the gate after proposal; `timing_sensitive_*` fields are diagnostic only unless a deployment proves initial-snapshot availability; `post_proposal_*` and `derived_post_proposal_*` fields are outcomes and must not be used as predictors.",
        "- Main gate feature membership follows `NUMERIC_FEATURES` and `CATEGORICAL_FEATURES` in `exp/scripts/emse_aidev/evaluate_workload_gate.py`, restricted to columns present in the feature table.",
        "",
        "| Column | Decision time | Main gate | Definition | Source/derivation | Missing rule |",
        "|---|---|---:|---|---|---|",
    ]
    for row in rows:
        lines.append(
            "| {column} | {decision_time_status} | {used_in_main_gate} | {definition} | {source_or_derivation} | {missing_value_rule} |".format(
                **{key: str(value).replace("|", "\\|") for key, value in row.items()}
            )
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the AIDev PR-level feature data dictionary.")
    parser.add_argument("--features", type=Path, default=FEATURES_PATH)
    parser.add_argument("--summary", type=Path, default=SUMMARY_PATH)
    parser.add_argument("--output-csv", type=Path, default=OUTPUT_CSV)
    parser.add_argument("--output-md", type=Path, default=OUTPUT_MD)
    args = parser.parse_args()

    frame = pd.read_csv(args.features)
    constants = extract_list_constants(GATE_SCRIPT, {"NUMERIC_FEATURES", "CATEGORICAL_FEATURES"})
    gate_features = set(constants["NUMERIC_FEATURES"]) | set(constants["CATEGORICAL_FEATURES"])
    rows = build_rows(frame, gate_features)
    summary = load_summary(args.summary)
    write_csv(args.output_csv, rows)
    write_markdown(args.output_md, rows, summary)
    print(f"Wrote {len(rows)} column definitions to {args.output_csv}")
    print(f"Wrote Markdown dictionary to {args.output_md}")


if __name__ == "__main__":
    main()
