from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from .common import (
    DATASET_DIR,
    RESULTS_DIR,
    available_tables,
    contains_text,
    count_by_pr,
    count_state_by_pr,
    ensure_dir,
    first_existing,
    merge_repository_features,
    numeric_column,
    read_table,
    text_length,
    to_datetime,
    write_json,
)


def attach_pr_id_to_review_comments(
    review_comments: pd.DataFrame | None,
    reviews: pd.DataFrame | None,
    prs: pd.DataFrame,
) -> pd.DataFrame | None:
    if review_comments is None or review_comments.empty:
        return review_comments
    if any(col in review_comments.columns for col in ["pr_id", "pull_request_id"]):
        return review_comments

    out = review_comments.copy()
    if (
        "pull_request_review_id" in out.columns
        and reviews is not None
        and not reviews.empty
        and {"id", "pr_id"}.issubset(reviews.columns)
    ):
        review_to_pr = reviews[["id", "pr_id"]].dropna(subset=["id", "pr_id"]).drop_duplicates("id")
        out = out.merge(
            review_to_pr.rename(columns={"id": "_review_id", "pr_id": "_review_pr_id"}),
            left_on="pull_request_review_id",
            right_on="_review_id",
            how="left",
        )
        out["pr_id"] = out["_review_pr_id"]
        out = out.drop(columns=["_review_id", "_review_pr_id"])

    missing = "pr_id" not in out.columns or out["pr_id"].isna().any()
    if missing and "pull_request_url" in out.columns and {"repo_url", "number", "id"}.issubset(prs.columns):
        parsed = out["pull_request_url"].fillna("").astype(str).str.extract(
            r"(?P<repo_url>https://api\.github\.com/repos/.+)/pulls/(?P<number>\d+)$"
        )
        parsed["number"] = pd.to_numeric(parsed["number"], errors="coerce")
        pr_lookup = prs[["repo_url", "number", "id"]].drop_duplicates(["repo_url", "number"])
        resolved = parsed.merge(pr_lookup, on=["repo_url", "number"], how="left")["id"]
        if "pr_id" in out.columns:
            out["pr_id"] = out["pr_id"].fillna(resolved)
        else:
            out["pr_id"] = resolved

    return out


def merge_task_type_features(prs: pd.DataFrame, task_type: pd.DataFrame | None) -> pd.DataFrame:
    if task_type is None or task_type.empty:
        return prs
    task_id_col = first_existing(task_type.columns, ["id", "pr_id", "pull_request_id"])
    pr_id_col = first_existing(prs.columns, ["id", "pr_id", "pull_request_id"])
    if task_id_col is None or pr_id_col is None:
        return prs

    cols = [task_id_col, *[col for col in ["type", "confidence", "reason"] if col in task_type.columns]]
    task_features = task_type[cols].drop_duplicates(subset=[task_id_col]).copy()
    renamed = {task_id_col: pr_id_col}
    if "type" in task_features.columns:
        renamed["type"] = "task_type"
    if "confidence" in task_features.columns:
        renamed["confidence"] = "task_type_confidence"
    if "reason" in task_features.columns:
        renamed["reason"] = "task_type_reason"
    task_features = task_features.rename(columns=renamed)
    return prs.merge(task_features, on=pr_id_col, how="left")


def first_commit_by_pr(commit_details: pd.DataFrame | None, timeline: pd.DataFrame | None) -> pd.Series:
    if timeline is not None and not timeline.empty and {"pr_id", "commit_id", "event"}.issubset(timeline.columns):
        committed = timeline[
            timeline["event"].fillna("").astype(str).str.lower().eq("committed")
            & timeline["commit_id"].notna()
        ].copy()
        if not committed.empty:
            return committed.drop_duplicates("pr_id").set_index("pr_id")["commit_id"].astype(str)

    if commit_details is None or commit_details.empty or not {"pr_id", "sha"}.issubset(commit_details.columns):
        return pd.Series(dtype=str)
    return commit_details.dropna(subset=["pr_id", "sha"]).drop_duplicates("pr_id").set_index("pr_id")["sha"].astype(str)


def summarize_commit_details(
    commit_details: pd.DataFrame | None,
    timeline: pd.DataFrame | None,
    prs: pd.DataFrame,
) -> pd.DataFrame:
    parent_key = first_existing(prs.columns, ["id", "pr_id", "pull_request_id"])
    if commit_details is None or commit_details.empty or parent_key is None or "pr_id" not in commit_details.columns:
        return pd.DataFrame(index=prs.index)

    details = commit_details.copy()
    details["pr_id"] = pd.to_numeric(details["pr_id"], errors="coerce")
    details["sha"] = details["sha"].fillna("").astype(str) if "sha" in details.columns else ""
    for col in ["additions", "deletions", "changes", "commit_stats_additions", "commit_stats_deletions", "commit_stats_total"]:
        if col in details.columns:
            details[col] = pd.to_numeric(details[col], errors="coerce").fillna(0.0)
    if "filename" in details.columns:
        details["filename"] = details["filename"].fillna("").astype(str)
    if "status" in details.columns:
        details["status"] = details["status"].fillna("").astype(str)

    first_commit = first_commit_by_pr(details, timeline)
    if not first_commit.empty:
        details = details.merge(first_commit.rename("_first_sha"), left_on="pr_id", right_index=True, how="left")
        initial_rows = details[details["sha"].eq(details["_first_sha"])].copy()
        followup_rows = details[~details["sha"].eq(details["_first_sha"])].copy()
    else:
        initial_rows = details.iloc[0:0].copy()
        followup_rows = details

    out = pd.DataFrame(index=prs.index)

    def assign_sum(frame: pd.DataFrame, source_col: str, target_col: str) -> None:
        if source_col not in frame.columns:
            out[target_col] = 0.0
            return
        values = frame.groupby("pr_id", dropna=False)[source_col].sum()
        out[target_col] = prs[parent_key].map(values).fillna(0.0).astype(float)

    def assign_nunique(frame: pd.DataFrame, source_col: str, target_col: str) -> None:
        if source_col not in frame.columns:
            out[target_col] = 0.0
            return
        values = frame.groupby("pr_id", dropna=False)[source_col].nunique()
        out[target_col] = prs[parent_key].map(values).fillna(0.0).astype(float)

    def assign_status_count(frame: pd.DataFrame, status: str, target_col: str) -> None:
        if "status" not in frame.columns:
            out[target_col] = 0.0
            return
        values = frame[frame["status"].str.lower().eq(status)].groupby("pr_id", dropna=False).size()
        out[target_col] = prs[parent_key].map(values).fillna(0.0).astype(float)

    def assign_tests_touched(frame: pd.DataFrame, target_col: str) -> None:
        if "filename" not in frame.columns:
            out[target_col] = 0.0
            return
        test_like = frame[
            frame["filename"].str.contains(r"(?:^|/)(?:tests?|test_|.*_test|.*\.spec\.|.*\.test\.)", case=False, regex=True, na=False)
        ]
        values = test_like.groupby("pr_id", dropna=False)["filename"].nunique()
        out[target_col] = prs[parent_key].map(values).fillna(0.0).astype(float)

    assign_nunique(initial_rows, "filename", "feature_initial_detail_changed_files")
    assign_sum(initial_rows, "additions", "feature_initial_detail_additions")
    assign_sum(initial_rows, "deletions", "feature_initial_detail_deletions")
    assign_sum(initial_rows, "changes", "feature_initial_detail_churn")
    assign_status_count(initial_rows, "added", "feature_initial_detail_added_files")
    assign_status_count(initial_rows, "modified", "feature_initial_detail_modified_files")
    assign_status_count(initial_rows, "removed", "feature_initial_detail_removed_files")
    assign_tests_touched(initial_rows, "feature_initial_detail_test_files")

    assign_nunique(details, "filename", "outcome_commit_detail_changed_files")
    assign_sum(details, "additions", "outcome_commit_detail_additions")
    assign_sum(details, "deletions", "outcome_commit_detail_deletions")
    assign_sum(details, "changes", "outcome_commit_detail_churn")
    assign_nunique(followup_rows, "filename", "outcome_followup_detail_changed_files")
    assign_sum(followup_rows, "additions", "outcome_followup_detail_additions")
    assign_sum(followup_rows, "deletions", "outcome_followup_detail_deletions")
    assign_sum(followup_rows, "changes", "outcome_followup_detail_churn")
    assign_tests_touched(followup_rows, "outcome_followup_detail_test_files")
    return out


def choose_pull_request_table(dataset_dir: Path) -> tuple[str, pd.DataFrame]:
    for name in ["pull_request", "all_pull_request"]:
        frame = read_table(dataset_dir, name)
        if frame is not None and not frame.empty:
            return name, frame
    raise FileNotFoundError(
        f"No AIDev pull-request table found under {dataset_dir}. Run download_aidev.py first or pass --dataset-dir."
    )


def build_feature_frame(dataset_dir: Path) -> tuple[pd.DataFrame, dict]:
    table_name, prs = choose_pull_request_table(dataset_dir)
    repositories = read_table(dataset_dir, "repository")
    prs = merge_repository_features(prs, repositories)

    reviews = read_table(dataset_dir, "pr_reviews")
    review_comments = read_table(dataset_dir, "pr_review_comments_v2")
    if review_comments is None:
        review_comments = read_table(dataset_dir, "pr_review_comments")
    review_comments = attach_pr_id_to_review_comments(review_comments, reviews, prs)
    pr_comments = read_table(dataset_dir, "pr_comments")
    pr_commits = read_table(dataset_dir, "pr_commits")
    commit_details = read_table(
        dataset_dir,
        "pr_commit_details",
        columns=[
            "sha",
            "pr_id",
            "commit_stats_total",
            "commit_stats_additions",
            "commit_stats_deletions",
            "filename",
            "status",
            "additions",
            "deletions",
            "changes",
        ],
    )
    timeline = read_table(dataset_dir, "pr_timeline", columns=["pr_id", "event", "commit_id", "created_at"])
    related_issue = read_table(dataset_dir, "related_issue")
    task_type = read_table(dataset_dir, "pr_task_type")
    prs = merge_task_type_features(prs, task_type)

    out = pd.DataFrame(index=prs.index)
    for col in ["id", "repo_id", "number", "html_url", "agent"]:
        if col in prs.columns:
            out[col] = prs[col]
    out["created_at"] = to_datetime(prs, "created_at")
    out["closed_at"] = to_datetime(prs, "closed_at")
    out["merged_at"] = to_datetime(prs, "merged_at")

    out["feature_title_chars"] = text_length(prs, "title")
    out["feature_body_chars"] = text_length(prs, "body")
    out["feature_title_mentions_test"] = contains_text(prs, "title", r"\b(?:test|pytest|ci|lint|build)\b")
    out["feature_body_mentions_test"] = contains_text(prs, "body", r"\b(?:test|pytest|ci|lint|build)\b")
    out["feature_body_mentions_fix"] = contains_text(prs, "body", r"\b(?:fix|bug|error|fail|issue)\b")

    for source_col, target_col in [
        ("changed_files", "feature_changed_files"),
        ("additions", "feature_additions"),
        ("deletions", "feature_deletions"),
        ("commits", "feature_initial_commit_count"),
        ("review_comments", "feature_initial_review_comment_count_api"),
        ("comments", "feature_initial_issue_comment_count_api"),
    ]:
        out[target_col] = numeric_column(prs, source_col)
    out["feature_churn"] = out["feature_additions"] + out["feature_deletions"]

    for source_col, target_col in [
        ("stargazers_count", "feature_repo_stars"),
        ("stars", "feature_repo_stars"),
        ("forks_count", "feature_repo_forks"),
        ("watchers_count", "feature_repo_watchers"),
        ("open_issues_count", "feature_repo_open_issues"),
    ]:
        if source_col in prs.columns:
            out[target_col] = numeric_column(prs, source_col)
    if "repo_language" in prs.columns:
        out["repo_language"] = prs["repo_language"].fillna("").astype(str)
    if "task_type" in prs.columns:
        out["feature_task_type"] = prs["task_type"].fillna("").astype(str)
    if "task_type_confidence" in prs.columns:
        out["feature_task_type_confidence"] = numeric_column(prs, "task_type_confidence")

    commit_summary = summarize_commit_details(commit_details, timeline, prs)
    for col in commit_summary.columns:
        out[col] = commit_summary[col]
    if not commit_summary.empty:
        out["feature_changed_files"] = out["feature_changed_files"].where(
            out["feature_changed_files"] > 0.0,
            out.get("feature_initial_detail_changed_files", 0.0),
        )
        out["feature_additions"] = out["feature_additions"].where(
            out["feature_additions"] > 0.0,
            out.get("feature_initial_detail_additions", 0.0),
        )
        out["feature_deletions"] = out["feature_deletions"].where(
            out["feature_deletions"] > 0.0,
            out.get("feature_initial_detail_deletions", 0.0),
        )
        out["feature_churn"] = out["feature_additions"] + out["feature_deletions"]

    out["outcome_review_count"] = count_by_pr(reviews, prs, "outcome_review_count")
    out["outcome_request_changes_count"] = count_state_by_pr(reviews, prs, "change", "outcome_request_changes_count")
    out["outcome_human_review_count"] = count_by_pr(
        reviews[reviews["user_type"].fillna("").astype(str).str.lower().eq("user")] if reviews is not None and "user_type" in reviews.columns else None,
        prs,
        "outcome_human_review_count",
    )
    out["outcome_inline_review_comment_count"] = count_by_pr(review_comments, prs, "outcome_inline_review_comment_count")
    out["outcome_issue_comment_count"] = count_by_pr(pr_comments, prs, "outcome_issue_comment_count")
    out["outcome_commit_count"] = count_by_pr(pr_commits, prs, "outcome_commit_count")
    out["outcome_followup_commit_count"] = (out["outcome_commit_count"] - 1.0).clip(lower=0.0)
    out["outcome_commit_detail_rows"] = count_by_pr(commit_details, prs, "outcome_commit_detail_rows")
    out["outcome_timeline_event_count"] = count_by_pr(timeline, prs, "outcome_timeline_event_count")
    out["outcome_related_issue_count"] = count_by_pr(related_issue, prs, "outcome_related_issue_count")

    if "merged_at" in out.columns:
        out["outcome_merged"] = out["merged_at"].notna().astype(float)
    if "closed_at" in out.columns:
        created = pd.to_datetime(out["created_at"], errors="coerce", utc=True)
        closed = pd.to_datetime(out["closed_at"], errors="coerce", utc=True)
        out["outcome_resolution_hours"] = ((closed - created).dt.total_seconds() / 3600.0).replace([np.inf, -np.inf], np.nan)

    workload_components = [
        "outcome_review_count",
        "outcome_request_changes_count",
        "outcome_inline_review_comment_count",
        "outcome_issue_comment_count",
        "outcome_followup_commit_count",
    ]
    out["outcome_downstream_workload_raw"] = out[workload_components].sum(axis=1)
    out["outcome_downstream_workload_log"] = np.log1p(out["outcome_downstream_workload_raw"])

    summary = {
        "pull_request_table": table_name,
        "rows": int(len(out)),
        "columns": list(out.columns),
        "available_tables": available_tables(dataset_dir),
        "nonzero_outcome_rates": {
            col: float((out[col] > 0).mean()) for col in workload_components if col in out.columns
        },
    }
    return out, summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Build AIDev PR-level proposal features and downstream workload outcomes.")
    parser.add_argument("--dataset-dir", type=Path, default=DATASET_DIR)
    parser.add_argument("--output-dir", type=Path, default=RESULTS_DIR)
    args = parser.parse_args()

    output_dir = ensure_dir(args.output_dir)
    frame, summary = build_feature_frame(args.dataset_dir)
    output_path = output_dir / "aidev_pr_level_features.csv"
    frame.to_csv(output_path, index=False)
    summary["output_path"] = str(output_path)
    write_json(output_dir / "aidev_feature_build_summary.json", summary)
    print(f"Wrote {len(frame)} PR-level rows to {output_path}")


if __name__ == "__main__":
    main()
