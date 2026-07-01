from __future__ import annotations

import json
import math
import random
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, Sequence

import numpy as np
import pandas as pd
import pyarrow.parquet as pq


ROOT = Path(__file__).resolve().parents[2]
DATASET_DIR = ROOT / "Dataset"
RESULTS_DIR = ROOT / "results" / "theory_support"
MANIFEST_DIR = RESULTS_DIR / "manifests"


TEST_PATTERN = re.compile(r"\b(pytest|test_|assert|failed|passed|traceback)\b", re.IGNORECASE)
SEARCH_PATTERN = re.compile(r"\b(rg\b|grep\b|find\b|search\b|locate\b|open\b|cat\b|sed\b)", re.IGNORECASE)
UNCERTAINTY_PATTERN = re.compile(r"\b(maybe|perhaps|not sure|unclear|guess|probably)\b", re.IGNORECASE)
DIFF_HEADER_PATTERN = re.compile(r"^diff --git ", re.MULTILINE)


@dataclass(frozen=True)
class GovernanceMode:
    name: str
    recovery_multiplier: float
    service_floor: float
    verification_bias: float


GOVERNANCE_MODES: list[GovernanceMode] = [
    GovernanceMode("g0_aggressive", recovery_multiplier=1.00, service_floor=1.00, verification_bias=0.00),
    GovernanceMode("g1_balanced", recovery_multiplier=0.82, service_floor=0.98, verification_bias=0.05),
    GovernanceMode("g2_conservative", recovery_multiplier=0.66, service_floor=0.96, verification_bias=0.10),
    GovernanceMode("g3_safe", recovery_multiplier=0.52, service_floor=0.94, verification_bias=0.15),
]

EFFORT_LEVELS = np.asarray([0.0, 1.0 / 3.0, 2.0 / 3.0, 1.0], dtype=float)


def verification_threshold(e_value: float | np.ndarray, d_value: float | np.ndarray, q_value: float | np.ndarray):
    return 0.45 - 0.22 * np.asarray(e_value) + 0.14 * np.asarray(q_value) - 0.08 * np.asarray(d_value)


def verification_margin(e_value: float | np.ndarray, d_value: float | np.ndarray, q_value: float | np.ndarray):
    return np.asarray(d_value) - verification_threshold(e_value, d_value, q_value)


def quantize_effort(value: float) -> float:
    clipped = float(np.clip(value, 0.0, 1.0))
    return float(EFFORT_LEVELS[int(np.argmin(np.abs(EFFORT_LEVELS - clipped)))])


def shift_effort(value: float, steps: int) -> float:
    idx = int(np.argmin(np.abs(EFFORT_LEVELS - float(value))))
    new_idx = int(np.clip(idx + steps, 0, len(EFFORT_LEVELS) - 1))
    return float(EFFORT_LEVELS[new_idx])


def verification_effort(e_value: float, d_value: float, q_value: float) -> float:
    margin = max(float(verification_margin(e_value, d_value, q_value)) - 0.42, 0.0)
    raw = 0.02 + 3.00 * margin
    return quantize_effort(raw)


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_json(path: Path, payload: dict) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def read_parquet(path: Path, columns: Sequence[str] | None = None) -> pd.DataFrame:
    return pq.read_table(path, columns=list(columns) if columns else None).to_pandas()


def iter_parquet_rows(path: Path, columns: Sequence[str] | None = None, batch_size: int = 256) -> Iterator[dict]:
    parquet_file = pq.ParquetFile(path)
    for batch in parquet_file.iter_batches(batch_size=batch_size, columns=list(columns) if columns else None):
        for row in batch.to_pylist():
            yield row


def parse_json_list(value) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return []
        try:
            parsed = json.loads(stripped)
            return parsed if isinstance(parsed, list) else []
        except json.JSONDecodeError:
            return []
    return []


def to_list(value) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, np.ndarray):
        return value.tolist()
    return list(value) if isinstance(value, tuple) else []


def text_len(value: str | None) -> int:
    return len(value or "")


def token_proxy(value: str | None) -> float:
    return round(text_len(value) / 4.0, 3)


def difficulty_to_score(value: str | None) -> float:
    mapping = {"easy": 0.25, "medium": 0.55, "hard": 0.85}
    return mapping.get((value or "").lower(), 0.5)


def diff_stats(patch: str | None) -> tuple[int, int, int]:
    patch = patch or ""
    file_count = len(DIFF_HEADER_PATTERN.findall(patch))
    added = 0
    removed = 0
    for line in patch.splitlines():
        if line.startswith("+++ ") or line.startswith("--- "):
            continue
        if line.startswith("+"):
            added += 1
        elif line.startswith("-"):
            removed += 1
    return file_count, added, removed


def eval_fail_mentions(logs: str | None) -> int:
    logs = logs or ""
    return len(re.findall(r"\b(FAIL|FAILED|ERROR|Traceback)\b", logs, flags=re.IGNORECASE))


def summarize_trajectory(trajectory: list[dict] | None, early_cutoff: int = 8) -> dict[str, float]:
    trajectory = trajectory or []
    events = trajectory[1:] if trajectory and trajectory[0].get("role") == "system" else trajectory
    steps = len(events)
    early_events = events[:early_cutoff]

    ai_turns = sum(1 for event in events if event.get("role") == "assistant" or event.get("role") == "ai")
    user_turns = sum(1 for event in events if event.get("role") == "user")
    total_chars = sum(len(event.get("text") or "") for event in events)
    early_ai_chars = sum(
        len(event.get("text") or "")
        for event in early_events
        if event.get("role") == "assistant" or event.get("role") == "ai"
    )
    early_user_chars = sum(len(event.get("text") or "") for event in early_events if event.get("role") == "user")
    early_text = "\n".join(event.get("text") or "" for event in early_events)

    return {
        "trajectory_steps": float(steps),
        "trajectory_ai_turns": float(ai_turns),
        "trajectory_user_turns": float(user_turns),
        "trajectory_total_chars": float(total_chars),
        "early_ai_chars": float(early_ai_chars),
        "early_user_chars": float(early_user_chars),
        "early_test_mentions": float(len(TEST_PATTERN.findall(early_text))),
        "early_search_mentions": float(len(SEARCH_PATTERN.findall(early_text))),
        "early_uncertainty_mentions": float(len(UNCERTAINTY_PATTERN.findall(early_text))),
    }


def trajectory_row_to_manifest(row: dict) -> dict:
    patch_files, patch_added, patch_removed = diff_stats(row.get("generated_patch"))
    traj_summary = summarize_trajectory(row.get("trajectory"))
    exit_status = row.get("exit_status") or ""
    return {
        "instance_id": row.get("instance_id"),
        "model_name": row.get("model_name"),
        "target": bool(row.get("target")),
        "exit_status": exit_status,
        "exit_submit": float("submit" in exit_status.lower()),
        "generated_patch_files": float(patch_files),
        "generated_patch_added": float(patch_added),
        "generated_patch_removed": float(patch_removed),
        "generated_patch_lines": float(patch_added + patch_removed),
        "eval_log_chars": float(text_len(row.get("eval_logs"))),
        "eval_fail_mentions": float(eval_fail_mentions(row.get("eval_logs"))),
        **traj_summary,
    }


def task_row_to_manifest(row: dict, source: str, split: str | None = None) -> dict:
    fail_to_pass = parse_json_list(row.get("FAIL_TO_PASS"))
    pass_to_pass = parse_json_list(row.get("PASS_TO_PASS"))
    test_patch = row.get("test_patch") or ""
    patch = row.get("patch") or ""
    patch_files, patch_added, patch_removed = diff_stats(patch)
    test_patch_files, test_added, test_removed = diff_stats(test_patch)
    return {
        "source": source,
        "split": split or "",
        "repo": row.get("repo"),
        "instance_id": row.get("instance_id"),
        "problem_chars": float(text_len(row.get("problem_statement"))),
        "problem_tokens": float(token_proxy(row.get("problem_statement"))),
        "hints_chars": float(text_len(row.get("hints_text"))),
        "hints_tokens": float(token_proxy(row.get("hints_text"))),
        "hints_nonempty": float(bool((row.get("hints_text") or "").strip())),
        "fail_to_pass_count": float(len(fail_to_pass)),
        "pass_to_pass_count": float(len(pass_to_pass)),
        "fail_tests_tokens": float(token_proxy(json.dumps(fail_to_pass, ensure_ascii=False))),
        "pass_tests_tokens": float(token_proxy(json.dumps(pass_to_pass, ensure_ascii=False))),
        "gold_patch_files": float(patch_files),
        "gold_patch_added": float(patch_added),
        "gold_patch_removed": float(patch_removed),
        "gold_patch_lines": float(patch_added + patch_removed),
        "gold_test_patch_files": float(test_patch_files),
        "gold_test_patch_lines": float(test_added + test_removed),
        "difficulty": row.get("difficulty", ""),
        "difficulty_score": float(difficulty_to_score(row.get("difficulty"))),
    }


def codetrace_row_to_manifest(row: dict, split: str) -> dict:
    incorrect_stages = to_list(row.get("incorrect_stages"))
    incorrect_steps_total = 0
    unuseful_steps_total = 0
    incorrect_stage_ids: set[int] = set()
    unuseful_stage_ids: set[int] = set()
    for stage in incorrect_stages:
        incorrect_steps = to_list(stage.get("incorrect_step_ids"))
        unuseful_steps = to_list(stage.get("unuseful_step_ids"))
        incorrect_steps_total += len(incorrect_steps)
        unuseful_steps_total += len(unuseful_steps)
        if incorrect_steps:
            incorrect_stage_ids.add(int(stage.get("stage_id", -1)))
        if unuseful_steps:
            unuseful_stage_ids.add(int(stage.get("stage_id", -1)))
    stage_count = float(row.get("stage_count") or 0)
    return {
        "split": split,
        "traj_id": row.get("traj_id"),
        "agent": row.get("agent"),
        "model": row.get("model"),
        "task_name": row.get("task_name"),
        "task_slug": row.get("task_slug"),
        "difficulty": row.get("difficulty"),
        "difficulty_score": float(difficulty_to_score(row.get("difficulty"))),
        "category": row.get("category"),
        "solved": bool(row.get("solved")),
        "step_count": float(row.get("step_count") or 0),
        "stage_count": stage_count,
        "incorrect_error_stage_count": float(row.get("incorrect_error_stage_count") or 0),
        "incorrect_steps_total": float(incorrect_steps_total),
        "unuseful_steps_total": float(unuseful_steps_total),
        "incorrect_stage_ratio": float(len(incorrect_stage_ids) / stage_count) if stage_count else 0.0,
        "unuseful_stage_ratio": float(len(unuseful_stage_ids) / stage_count) if stage_count else 0.0,
        "artifact_path": row.get("artifact_path", ""),
    }


def grouped_train_test_split(groups: Sequence[str], test_size: float = 0.2, seed: int = 7) -> tuple[np.ndarray, np.ndarray]:
    unique_groups = sorted(set(groups))
    rng = random.Random(seed)
    rng.shuffle(unique_groups)
    cutoff = max(1, int(len(unique_groups) * (1 - test_size)))
    train_groups = set(unique_groups[:cutoff])
    train_mask = np.array([group in train_groups for group in groups], dtype=bool)
    test_mask = ~train_mask
    return train_mask, test_mask


def add_intercept(matrix: np.ndarray) -> np.ndarray:
    return np.concatenate([np.ones((matrix.shape[0], 1), dtype=float), matrix], axis=1)


def ridge_fit(features: np.ndarray, targets: np.ndarray, alpha: float = 1.0) -> np.ndarray:
    x = add_intercept(features)
    ridge = alpha * np.eye(x.shape[1])
    ridge[0, 0] = 0.0
    return np.linalg.solve(x.T @ x + ridge, x.T @ targets)


def ridge_predict(features: np.ndarray, weights: np.ndarray) -> np.ndarray:
    return add_intercept(features) @ weights


def clip_probabilities(values: np.ndarray) -> np.ndarray:
    return np.clip(values, 1e-6, 1 - 1e-6)


def brier_score(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    y_pred = clip_probabilities(y_pred)
    return float(np.mean((y_true - y_pred) ** 2))


def accuracy(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.mean((y_pred >= 0.5) == (y_true >= 0.5)))


def auc_score(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    pos = y_pred[y_true == 1]
    neg = y_pred[y_true == 0]
    if len(pos) == 0 or len(neg) == 0:
        return float("nan")
    wins = 0.0
    for p in pos:
        wins += np.sum(p > neg)
        wins += 0.5 * np.sum(p == neg)
    return float(wins / (len(pos) * len(neg)))


def r2_score(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    denom = np.sum((y_true - y_true.mean()) ** 2)
    if denom == 0:
        return 0.0
    return float(1 - np.sum((y_true - y_pred) ** 2) / denom)


def standardize_frame(frame: pd.DataFrame, columns: Sequence[str]) -> pd.DataFrame:
    result = frame.copy()
    for column in columns:
        mean = result[column].mean()
        std = result[column].std(ddof=0)
        result[column] = 0.0 if std == 0 else (result[column] - mean) / std
    return result


def sigmoid(x: np.ndarray | float) -> np.ndarray | float:
    return 1.0 / (1.0 + np.exp(-x))


def bootstrap_interval(values: Sequence[float], seed: int = 7, rounds: int = 500) -> tuple[float, float]:
    values = np.asarray(values, dtype=float)
    if len(values) == 0:
        return float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    draws = []
    for _ in range(rounds):
        sample = rng.choice(values, size=len(values), replace=True)
        draws.append(float(sample.mean()))
    return float(np.quantile(draws, 0.025)), float(np.quantile(draws, 0.975))


def manifest_paths(output_dir: Path | None = None) -> dict[str, Path]:
    base = MANIFEST_DIR if output_dir is None else output_dir
    return {
        "swe_bench_tasks": base / "swe_bench_tasks.csv",
        "swe_verified_tasks": base / "swe_verified_tasks.csv",
        "swe_smith_tasks": base / "swe_smith_tasks.csv",
        "swe_rebench_tasks": base / "swe_rebench_tasks.csv",
        "swe_agent_trajectories": base / "swe_agent_trajectories.csv",
        "codetrace_manifest": base / "codetrace_manifest.csv",
        "manifest_summary": base / "manifest_summary.json",
    }
