from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
DATASET_DIR = ROOT / "Dataset" / "AIDev"
RAW_DIR = DATASET_DIR / "raw"
RESULTS_DIR = ROOT / "results" / "emse_aidev"


DEFAULT_TABLES = [
    "pull_request",
    "repository",
    "pr_reviews",
    "pr_review_comments_v2",
    "pr_review_comments",
    "pr_comments",
    "pr_commits",
    "pr_commit_details",
    "pr_timeline",
    "related_issue",
    "pr_task_type",
    "issue",
]


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_json(path: Path, payload: dict) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def find_parquet_files(dataset_dir: Path, table_name: str) -> list[Path]:
    """Find AIDev table parquet files under several common HF layouts."""
    root = dataset_dir if dataset_dir.exists() else RAW_DIR
    if not root.exists():
        return []

    table_lower = table_name.lower()
    matches = []
    for path in root.rglob("*.parquet"):
        parts = [part.lower() for part in path.parts]
        stem = path.stem.lower()
        if table_lower in parts or stem.startswith(table_lower) or f"/{table_lower}/" in path.as_posix().lower():
            matches.append(path)
    return sorted(set(matches))


def available_tables(dataset_dir: Path) -> dict[str, list[str]]:
    return {name: [str(path) for path in find_parquet_files(dataset_dir, name)] for name in DEFAULT_TABLES}


def read_table(dataset_dir: Path, table_name: str, columns: Sequence[str] | None = None) -> pd.DataFrame | None:
    files = find_parquet_files(dataset_dir, table_name)
    if not files:
        return None
    frames = []
    for path in files:
        try:
            frames.append(pd.read_parquet(path, columns=list(columns) if columns else None))
        except Exception as exc:
            print(f"warning: skipping unreadable parquet {path}: {exc}")
    if not frames:
        return None
    return pd.concat(frames, ignore_index=True) if len(frames) > 1 else frames[0]


def first_existing(columns: Iterable[str], candidates: Sequence[str]) -> str | None:
    column_set = set(columns)
    for candidate in candidates:
        if candidate in column_set:
            return candidate
    return None


def text_length(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame.columns:
        return pd.Series(np.zeros(len(frame), dtype=float), index=frame.index)
    return frame[column].fillna("").astype(str).str.len().astype(float)


def contains_text(frame: pd.DataFrame, column: str, pattern: str) -> pd.Series:
    if column not in frame.columns:
        return pd.Series(np.zeros(len(frame), dtype=float), index=frame.index)
    return frame[column].fillna("").astype(str).str.contains(pattern, case=False, regex=True).astype(float)


def to_datetime(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame.columns:
        return pd.Series(pd.NaT, index=frame.index)
    return pd.to_datetime(frame[column], errors="coerce", utc=True)


def numeric_column(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame.columns:
        return pd.Series(np.zeros(len(frame), dtype=float), index=frame.index)
    return pd.to_numeric(frame[column], errors="coerce").fillna(0.0).astype(float)


def direct_pr_key(child: pd.DataFrame, parent: pd.DataFrame) -> tuple[str, str] | None:
    parent_key = first_existing(parent.columns, ["id", "pull_request_id", "pr_id"])
    if parent_key is None:
        return None
    for child_key in ["pull_request_id", "pr_id", "pr_number_id", "id"]:
        if child_key in child.columns:
            return child_key, parent_key
    return None


def count_by_pr(child: pd.DataFrame | None, parent: pd.DataFrame, name: str) -> pd.Series:
    if child is None or child.empty:
        return pd.Series(np.zeros(len(parent), dtype=float), index=parent.index, name=name)

    direct_key = direct_pr_key(child, parent)
    if direct_key is not None:
        child_key, parent_key = direct_key
        counts = child.groupby(child_key, dropna=False).size()
        return parent[parent_key].map(counts).fillna(0.0).astype(float).rename(name)

    if {"repo_id", "number"}.issubset(child.columns) and {"repo_id", "number"}.issubset(parent.columns):
        counts = child.groupby(["repo_id", "number"], dropna=False).size()
        index = pd.MultiIndex.from_frame(parent[["repo_id", "number"]])
        return pd.Series(index.map(counts).fillna(0.0).astype(float), index=parent.index, name=name)

    return pd.Series(np.zeros(len(parent), dtype=float), index=parent.index, name=name)


def count_state_by_pr(child: pd.DataFrame | None, parent: pd.DataFrame, state_pattern: str, name: str) -> pd.Series:
    if child is None or child.empty:
        return pd.Series(np.zeros(len(parent), dtype=float), index=parent.index, name=name)

    state_col = first_existing(child.columns, ["state", "event", "review_state"])
    if state_col is None:
        return pd.Series(np.zeros(len(parent), dtype=float), index=parent.index, name=name)

    filtered = child[child[state_col].fillna("").astype(str).str.contains(state_pattern, case=False, regex=True)].copy()
    return count_by_pr(filtered, parent, name)


def merge_repository_features(prs: pd.DataFrame, repositories: pd.DataFrame | None) -> pd.DataFrame:
    if repositories is None or repositories.empty or "repo_id" not in prs.columns:
        return prs
    repo_key = first_existing(repositories.columns, ["id", "repo_id"])
    if repo_key is None:
        return prs

    candidate_cols = [
        repo_key,
        *[col for col in ["language", "stargazers_count", "stars", "forks_count", "watchers_count", "open_issues_count"] if col in repositories.columns],
    ]
    repo_features = repositories[candidate_cols].drop_duplicates(subset=[repo_key]).copy()
    renamed = {repo_key: "repo_id"}
    if "language" in repo_features.columns:
        renamed["language"] = "repo_language"
    repo_features = repo_features.rename(columns=renamed)
    return prs.merge(repo_features, on="repo_id", how="left")
