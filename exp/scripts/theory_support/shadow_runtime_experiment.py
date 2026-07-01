from __future__ import annotations

import argparse
import csv
import difflib
import json
import math
import os
import re
import shlex
import subprocess
import time
import urllib.error
import urllib.request
import urllib.request
import uuid
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from shutil import copytree, ignore_patterns, rmtree
from typing import Any
from zipfile import ZipFile

import numpy as np
import pandas as pd

from common import RESULTS_DIR, bootstrap_interval, ensure_dir, write_json


DEFAULT_RESULTS_DIR = RESULTS_DIR / "shadow_runtime"
DEFAULT_MANIFEST = DEFAULT_RESULTS_DIR / "task_manifest.csv"
DEFAULT_SNAPSHOT_DIR = DEFAULT_RESULTS_DIR / "snapshots"
DEFAULT_REPO_CACHE_DIR = Path("shadow_repo_cache")
SAFE_DELTA = 0.03
PERF_DELTA = 0.08
SAFE_Q = 0.85
SAFE_DEBT = 0.55
PERF_Q = 0.45
PERF_DEBT = 0.28
MAX_SEARCH_RESULTS = 20
MAX_FILE_CHARS = 1200
MAX_SEARCH_CHARS = 900
MAX_TASK_PROBLEM_CHARS = 2200
MAX_TASK_HINT_CHARS = 900
MAX_TASK_FAIL_TESTS = 10


SYSTEM_PROMPT = """You are a careful coding agent operating inside a bounded repository-editing experiment.
Return strict JSON only.
Do not include markdown fences.
Prefer small, precise changes.
If you are unsure, inspect first instead of patching blindly."""


INSPECT_PROMPT = """Task:
{task_brief}

Controller:
{controller_name}

Current runtime state:
{runtime_state}

Recent observations:
{recent_observations}

Return JSON with keys:
- search_queries: list[str] (0 to 3 concise rg-style search phrases)
- paths_to_read: list[str] (0 to 5 repo-relative paths worth reading next)
- hypothesis: str
- ready_to_patch: bool
"""


PATCH_PROMPT = """Task:
{task_brief}

Controller:
{controller_name}

Current runtime state:
{runtime_state}

Search observations:
{search_observations}

File snippets:
{file_snippets}

Return JSON with keys:
- file_edits: list[object] where each object has path, find, replace
- confidence: float
- reasoning_summary: str

Constraints:
- Prefer one or two minimal edits.
- Only edit files shown in the snippets.
- The find text must appear verbatim in the provided snippets.
- Return an empty list if no safe edit is available.
"""


CRITIQUE_PROMPT = """Task:
{task_brief}

Controller:
{controller_name}

Current runtime state:
{runtime_state}

Candidate patch:
{candidate_patch}

Return JSON with keys:
- decision: str (one of accept, revise, reject)
- projected_success: float
- file_edits: list[object] where each object has path, find, replace
- critique_summary: str
"""


REPAIR_PATCH_PROMPT = """Task:
{task_brief}

Controller:
{controller_name}

Current runtime state:
{runtime_state}

The previous unified diff could not be applied.
Apply error:
{apply_error}

Invalid diff:
{candidate_patch}

Relevant file snippets:
{file_snippets}

Return JSON with keys:
- file_edits: list[object] where each object has path, find, replace
- reasoning_summary: str

Constraints:
- Only edit files shown in the snippets.
- Keep edits small and precise.
- The find text must match the current file exactly.
- Return an empty list if no safe edit is available.
"""


JSON_PATTERN = re.compile(r"\{.*\}", re.DOTALL)
TRIPLE_QUOTED_FIELD_PATTERN = re.compile(r'"(?P<key>patch|revised_patch)"\s*:\s*"""(?P<value>.*?)"""', re.DOTALL)


@dataclass
class RuntimeState:
    q_ver: float
    diagnostic_debt: float
    recovery_mass: float
    contamination: float
    problem_pressure: float = 1.0
    progress_credit: float = 0.0
    last_verified_problem_count: float | None = None
    safe_steps: int = 0
    unsafe_steps: int = 0
    fallback_events: int = 0
    verification_events: int = 0
    lookahead_events: int = 0
    first_failure_step: int | None = None
    return_to_safe_steps: int | None = None
    unsafe_streak: int = 0


@dataclass
class EpisodeStats:
    controller: str
    instance_id: str
    repo: str
    success: int = 0
    catastrophic_failure: int = 0
    steps: int = 0
    search_count: int = 0
    read_count: int = 0
    patch_attempts: int = 0
    patch_apply_successes: int = 0
    decision_points: int = 0
    test_runs: int = 0
    verification_events: int = 0
    fallback_events: int = 0
    lookahead_events: int = 0
    safe_state_rate: float = 0.0
    unsafe_step_count: int = 0
    baseline_problem_count: float = math.nan
    best_problem_count: float = math.nan
    final_problem_count: float = math.nan
    best_problem_reduction: float = 0.0
    final_problem_reduction: float = 0.0
    progress_events: int = 0
    any_progress: int = 0
    post_error_extra_work: int = 0
    return_to_safe_steps: float = math.nan
    final_target_test_pass: int = 0
    model_calls: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    latency_seconds: float = 0.0
    tool_calls: int = 0
    context_files: int = 0
    context_bytes: int = 0
    files_changed: int = 0
    lines_changed: int = 0
    failed_verification_jobs: int = 0
    recovery_attempts: int = 0
    notes: str = ""


@dataclass
class TestRunMetrics:
    tests: int = 0
    failures: int = 0
    errors: int = 0
    skipped: int = 0
    inferred_from_junit: bool = False

    @property
    def problem_count(self) -> int:
        return int(self.failures + self.errors)


class LMStudioClient:
    def __init__(self, base_url: str, model: str, timeout_s: int = 120, api_key: str | None = None):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_s = timeout_s
        self.api_key = api_key
        self.model_calls = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.total_tokens = 0
        self.latency_seconds = 0.0

    def chat(self, messages: list[dict[str, str]], temperature: float = 0.2, max_tokens: int = 1200) -> str:
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", **({"Authorization": f"Bearer {self.api_key}"} if self.api_key else {})},
            method="POST",
        )
        start = time.perf_counter()
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s) as response:
                parsed = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"LM Studio request failed with HTTP {exc.code}: {body}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"LM Studio request failed: {exc}") from exc
        choices = parsed.get("choices") or []
        if not choices:
            raise RuntimeError(f"LM Studio returned no choices: {parsed}")
        content = str(choices[0]["message"]["content"])
        usage = parsed.get("usage") or {}
        prompt_tokens = int(usage.get("prompt_tokens") or estimate_message_tokens(messages))
        completion_tokens = int(usage.get("completion_tokens") or estimate_text_tokens(content))
        total_tokens = int(usage.get("total_tokens") or (prompt_tokens + completion_tokens))
        self.model_calls += 1
        self.prompt_tokens += prompt_tokens
        self.completion_tokens += completion_tokens
        self.total_tokens += total_tokens
        self.latency_seconds += time.perf_counter() - start
        return content


class MockClient:
    def __init__(self):
        self.counter = 0
        self.model_calls = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.total_tokens = 0
        self.latency_seconds = 0.0

    def chat(self, messages: list[dict[str, str]], temperature: float = 0.0, max_tokens: int = 200) -> str:
        last = messages[-1]["content"]
        start = time.perf_counter()
        self.counter += 1
        if "search_queries" in last:
            response = json.dumps(
                {
                    "search_queries": [],
                    "paths_to_read": [],
                    "hypothesis": "mock backend: no inspection performed",
                    "ready_to_patch": True,
                }
            )
            self.record_usage(messages, response, start)
            return response
        if "decision" in last and "Candidate patch" in last:
            response = json.dumps(
                {
                    "decision": "reject",
                    "projected_success": 0.0,
                    "file_edits": [],
                    "critique_summary": "mock backend: no revision",
                }
            )
            self.record_usage(messages, response, start)
            return response
        response = json.dumps(
            {
                "file_edits": [],
                "confidence": 0.0,
                "reasoning_summary": "mock backend: no patch proposed",
            }
        )
        self.record_usage(messages, response, start)
        return response

    def record_usage(self, messages: list[dict[str, str]], response: str, start: float) -> None:
        prompt_tokens = estimate_message_tokens(messages)
        completion_tokens = estimate_text_tokens(response)
        self.model_calls += 1
        self.prompt_tokens += prompt_tokens
        self.completion_tokens += completion_tokens
        self.total_tokens += prompt_tokens + completion_tokens
        self.latency_seconds += time.perf_counter() - start


def estimate_text_tokens(value: str) -> int:
    return max(1, int(math.ceil(len(str(value)) / 4.0)))


def estimate_message_tokens(messages: list[dict[str, str]]) -> int:
    return estimate_text_tokens(json.dumps(messages, ensure_ascii=False))


def usage_snapshot(client: LMStudioClient | MockClient) -> dict[str, float]:
    return {
        "model_calls": float(getattr(client, "model_calls", 0)),
        "prompt_tokens": float(getattr(client, "prompt_tokens", 0)),
        "completion_tokens": float(getattr(client, "completion_tokens", 0)),
        "total_tokens": float(getattr(client, "total_tokens", 0)),
        "latency_seconds": float(getattr(client, "latency_seconds", 0.0)),
    }


def usage_delta(client: LMStudioClient | MockClient, before: dict[str, float]) -> dict[str, float]:
    after = usage_snapshot(client)
    return {key: after[key] - before.get(key, 0.0) for key in after}


def parse_json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        repaired = repair_triple_quoted_json(stripped)
        repaired = escape_control_chars_in_json_strings(repaired)
        if repaired != stripped:
            try:
                return json.loads(repaired)
            except json.JSONDecodeError:
                stripped = repaired
        match = JSON_PATTERN.search(stripped)
        if not match:
            raise
        candidate = match.group(0)
        repaired = repair_triple_quoted_json(candidate)
        repaired = escape_control_chars_in_json_strings(repaired)
        return json.loads(repaired)


def repair_triple_quoted_json(text: str) -> str:
    def repl(match: re.Match[str]) -> str:
        key = match.group("key")
        value = match.group("value")
        escaped = json.dumps(value)[1:-1]
        return f'"{key}": "{escaped}"'

    return TRIPLE_QUOTED_FIELD_PATTERN.sub(repl, text)


def escape_control_chars_in_json_strings(text: str) -> str:
    output: list[str] = []
    in_string = False
    escaped = False
    for char in text:
        if in_string:
            if escaped:
                output.append(char)
                escaped = False
                continue
            if char == "\\":
                output.append(char)
                escaped = True
                continue
            if char == '"':
                output.append(char)
                in_string = False
                continue
            if char == "\n":
                output.append("\\n")
                continue
            if char == "\r":
                output.append("\\r")
                continue
            if char == "\t":
                output.append("\\t")
                continue
            output.append(char)
            continue

        output.append(char)
        if char == '"':
            in_string = True
            escaped = False

    return "".join(output)


def parse_list_field(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if value is None:
        return []
    text = str(value).strip()
    if not text:
        return []
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return []
    return [str(item) for item in parsed] if isinstance(parsed, list) else []


def sanitize_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value)


def clip_text(value: str, max_chars: int) -> str:
    text = value.strip()
    if len(text) <= max_chars:
        return text
    if max_chars <= 24:
        return text[:max_chars]
    head = max_chars - 20
    return text[:head].rstrip() + "\n...[truncated]"


def repo_cache_candidates(repo_cache_dir: Path, repo_name: str) -> list[Path]:
    owner, name = repo_name.split("/", 1)
    return [
        repo_cache_dir / f"{owner}__{name}",
        repo_cache_dir / name,
        repo_cache_dir / repo_name.replace("/", "__"),
    ]


def run_command(
    command: list[str],
    cwd: Path | None = None,
    timeout_s: int = 120,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    return subprocess.run(
        command,
        cwd=str(cwd) if cwd else None,
        text=True,
        encoding="utf-8",
        errors="ignore",
        capture_output=True,
        timeout=timeout_s,
        check=False,
        env=merged_env,
    )


def ensure_repo_cache(repo: str, repo_cache_dir: Path, allow_clone: bool) -> Path:
    ensure_dir(repo_cache_dir)
    for candidate in repo_cache_candidates(repo_cache_dir, repo):
        if candidate.exists():
            return candidate
    if not allow_clone:
        raise FileNotFoundError(f"No local clone found for {repo} under {repo_cache_dir}")
    target = repo_cache_dir / repo.replace("/", "__")
    clone = run_command(["git", "clone", "--filter=blob:none", f"https://github.com/{repo}.git", str(target)], timeout_s=900)
    if clone.returncode != 0:
        raise RuntimeError(f"git clone failed for {repo}: {clone.stderr.strip()}")
    return target


def ensure_worktree(repo_root: Path, workspace: Path, base_commit: str) -> None:
    if workspace.exists():
        return
    ensure_dir(workspace.parent)
    result = run_command(["git", "-C", str(repo_root), "worktree", "add", "--detach", str(workspace), base_commit], timeout_s=300)
    if result.returncode != 0:
        raise RuntimeError(f"git worktree add failed: {result.stderr.strip()}")


def ensure_git_repo(workspace: Path) -> None:
    git_dir = workspace / ".git"
    if git_dir.exists():
        return
    init = run_command(["git", "init"], cwd=workspace, timeout_s=120)
    if init.returncode != 0:
        raise RuntimeError(f"git init failed: {init.stderr.strip()}")
    run_command(["git", "config", "user.name", "shadow-runtime"], cwd=workspace, timeout_s=30)
    run_command(["git", "config", "user.email", "shadow-runtime@example.local"], cwd=workspace, timeout_s=30)
    add = run_command(["git", "add", "-A"], cwd=workspace, timeout_s=120)
    if add.returncode != 0:
        raise RuntimeError(f"git add failed: {add.stderr.strip()}")
    commit = run_command(["git", "commit", "-m", "snapshot"], cwd=workspace, timeout_s=120)
    if commit.returncode != 0:
        raise RuntimeError(f"git commit failed: {commit.stderr.strip()}")


def snapshot_dir_for_task(snapshot_root: Path, task_row: pd.Series) -> Path:
    return snapshot_root / sanitize_name(str(task_row["instance_id"]))


def prepare_snapshot_download(task_row: pd.Series, snapshot_root: Path) -> Path:
    ensure_dir(snapshot_root)
    target_dir = snapshot_dir_for_task(snapshot_root, task_row)
    if target_dir.exists():
        return target_dir
    owner, name = str(task_row["repo"]).split("/", 1)
    commit = str(task_row["base_commit"])
    zip_path = snapshot_root / f"{sanitize_name(task_row['instance_id'])}.zip"
    url = f"https://github.com/{owner}/{name}/archive/{commit}.zip"
    urllib.request.urlretrieve(url, zip_path)
    extract_dir = snapshot_root / f"_extract_{sanitize_name(task_row['instance_id'])}"
    if extract_dir.exists():
        rmtree(extract_dir)
    ensure_dir(extract_dir)
    with ZipFile(zip_path, "r") as archive:
        archive.extractall(extract_dir)
    inner_dirs = [path for path in extract_dir.iterdir() if path.is_dir()]
    if not inner_dirs:
        raise RuntimeError(f"No extracted directory found in {zip_path}")
    inner_dir = inner_dirs[0]
    if target_dir.exists():
        rmtree(target_dir)
    inner_dir.rename(target_dir)
    rmtree(extract_dir, ignore_errors=True)
    return target_dir


def ensure_snapshot_workspace(snapshot_dir: Path, workspace: Path) -> None:
    if workspace.exists():
        return
    ensure_dir(workspace.parent)
    copytree(
        snapshot_dir,
        workspace,
        ignore=ignore_patterns(
            ".pytest_cache",
            "pytest-cache-files-*",
            "__pycache__",
            "*.pyc",
            "*.pyo",
        ),
    )
    ensure_git_repo(workspace)


def target_test_command(task_row: pd.Series) -> list[str]:
    fail_tests = parse_list_field(task_row["FAIL_TO_PASS"])
    if fail_tests:
        direct_targets = [item for item in fail_tests if "::" in item or item.endswith(".py")]
        bare_names = [item for item in fail_tests if item not in direct_targets]
        command = ["python", "-m", "pytest", "-q"]
        if direct_targets:
            command.extend(direct_targets)
        if bare_names:
            expression = " or ".join(bare_names)
            command.extend(["-k", expression])
        return command
    return ["python", "-m", "pytest", "-q"]


def fallback_test_commands(task_row: pd.Series) -> list[list[str]]:
    fail_tests = parse_list_field(task_row["FAIL_TO_PASS"])
    fallbacks: list[list[str]] = []
    for item in fail_tests:
        if "::" in item:
            path_part, _, test_part = item.partition("::")
            if path_part:
                fallbacks.append(["python", "-m", "pytest", "-q", path_part])
            bare_test = test_part.split("::")[-1].strip()
            if bare_test:
                fallbacks.append(["python", "-m", "pytest", "-q", "-k", bare_test])
        elif item.endswith(".py"):
            fallbacks.append(["python", "-m", "pytest", "-q", item])
        else:
            fallbacks.append(["python", "-m", "pytest", "-q", "-k", item])
    if not fallbacks:
        fallbacks.append(["python", "-m", "pytest", "-q"])
    deduped: list[list[str]] = []
    seen: set[tuple[str, ...]] = set()
    for command in fallbacks:
        key = tuple(command)
        if key not in seen:
            deduped.append(command)
            seen.add(key)
    return deduped


def search_repo(workspace: Path, query: str) -> str:
    if not query.strip():
        return ""
    result = run_command(["rg", "-n", "--max-count", str(MAX_SEARCH_RESULTS), query, "."], cwd=workspace, timeout_s=60)
    output = (result.stdout or result.stderr or "").strip()
    return clip_text(output, MAX_SEARCH_CHARS)


def read_repo_file(workspace: Path, relative_path: str, max_lines: int = 160) -> str:
    target = workspace / relative_path
    if not target.exists() or not target.is_file():
        return f"[missing] {relative_path}"
    try:
        text = target.read_text(encoding="utf-8", errors="ignore")
    except OSError as exc:
        return f"[read-error] {relative_path}: {exc}"
    lines = text.splitlines()
    snippet = "\n".join(lines[:max_lines])
    return f"## {relative_path}\n{clip_text(snippet, MAX_FILE_CHARS)}"


def read_repo_context(workspace: Path, relative_path: str, query: str | None = None, radius: int = 24) -> str:
    target = workspace / relative_path
    if not target.exists() or not target.is_file():
        return f"[missing] {relative_path}"
    try:
        text = target.read_text(encoding="utf-8", errors="ignore")
    except OSError as exc:
        return f"[read-error] {relative_path}: {exc}"
    lines = text.splitlines()
    if not query:
        snippet = "\n".join(lines[: min(len(lines), 100)])
        return f"## {relative_path}\n{clip_text(snippet, MAX_FILE_CHARS)}"

    query_lower = query.lower()
    hit_idx = next((idx for idx, line in enumerate(lines) if query_lower in line.lower()), None)
    if hit_idx is None:
        snippet = "\n".join(lines[: min(len(lines), 100)])
        return f"## {relative_path}\n{clip_text(snippet, MAX_FILE_CHARS)}"
    start = max(0, hit_idx - radius)
    end = min(len(lines), hit_idx + radius + 1)
    snippet = "\n".join(lines[start:end])
    return f"## {relative_path} [lines {start + 1}-{end}]\n{clip_text(snippet, MAX_FILE_CHARS)}"


def apply_patch_text(workspace: Path, patch_text: str) -> tuple[bool, str]:
    patch_text = normalize_patch_text(patch_text)
    if patch_text.strip() == "NO_PATCH":
        return False, "no_patch"
    check = subprocess.run(
        ["git", "-C", str(workspace), "apply", "--check", "--whitespace=nowarn", "-"],
        input=patch_text,
        text=True,
        capture_output=True,
        timeout=120,
        check=False,
    )
    if check.returncode != 0:
        return False, check.stderr.strip() or "git apply --check failed"
    apply = subprocess.run(
        ["git", "-C", str(workspace), "apply", "--whitespace=nowarn", "-"],
        input=patch_text,
        text=True,
        capture_output=True,
        timeout=120,
        check=False,
    )
    if apply.returncode != 0:
        return False, apply.stderr.strip() or "git apply failed"
    return True, "applied"


def normalize_patch_text(patch_text: str) -> str:
    text = patch_text.strip()
    if not text:
        return "NO_PATCH"
    if text == "NO_PATCH":
        return text
    if text.startswith('"""') and text.endswith('"""') and len(text) >= 6:
        text = text[3:-3].strip()
    if text.startswith("```") and text.endswith("```"):
        lines = text.splitlines()
        if len(lines) >= 3:
            text = "\n".join(lines[1:-1]).strip()
    return text


def canonicalize_match_text(text: str) -> str:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    return "\n".join(" ".join(line.strip().split()) for line in lines).strip()


def approximate_find_target(original: str, find_text: str) -> str | None:
    target_norm = canonicalize_match_text(find_text)
    if not target_norm:
        return None
    original_lines = original.splitlines(keepends=True)
    target_lines = find_text.splitlines(keepends=True)
    if not original_lines or not target_lines:
        return None

    candidates: list[tuple[float, int, int, str]] = []
    min_window = max(1, len(target_lines) - 1)
    max_window = min(len(original_lines), len(target_lines) + 1)
    for window_size in range(min_window, max_window + 1):
        for start in range(0, len(original_lines) - window_size + 1):
            candidate = "".join(original_lines[start : start + window_size])
            ratio = difflib.SequenceMatcher(None, canonicalize_match_text(candidate), target_norm).ratio()
            if ratio >= 0.88:
                candidates.append((ratio, start, window_size, candidate))

    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0], reverse=True)
    best_ratio, _, _, best_candidate = candidates[0]
    second_ratio = candidates[1][0] if len(candidates) > 1 else -1.0
    if best_ratio >= 0.93 and best_ratio - second_ratio >= 0.03:
        return best_candidate
    return None


def apply_structured_edits(workspace: Path, file_edits: list[dict[str, Any]]) -> tuple[bool, str]:
    if not file_edits:
        return False, "no_structured_edits"
    for edit in file_edits:
        relative_path = str(edit.get("path", "")).strip().lstrip("./\\")
        find_text = str(edit.get("find", ""))
        replace_text = str(edit.get("replace", ""))
        if not relative_path or not find_text:
            return False, "structured_edit_missing_fields"
        target = workspace / relative_path
        if not target.exists() or not target.is_file():
            return False, f"missing_edit_target:{relative_path}"
        try:
            original = target.read_text(encoding="utf-8", errors="ignore")
        except OSError as exc:
            return False, f"read_error:{relative_path}:{exc}"
        target_find = find_text
        matches = original.count(target_find)
        if matches != 1:
            approx_target = approximate_find_target(original, find_text)
            if approx_target is not None:
                target_find = approx_target
                matches = original.count(target_find)
        if matches != 1:
            return False, f"find_match_count:{relative_path}:{matches}"
        updated = original.replace(target_find, replace_text, 1)
        if updated == original:
            return False, f"no_change:{relative_path}"
        try:
            target.write_text(updated, encoding="utf-8")
        except OSError as exc:
            return False, f"write_error:{relative_path}:{exc}"
    return True, "structured_edits_applied"


def run_target_tests(workspace: Path, task_row: pd.Series, timeout_s: int = 600) -> tuple[bool, str, TestRunMetrics]:
    pytest_root = workspace.parent.parent / "_pytest_tmp" / sanitize_name(workspace.name) / uuid.uuid4().hex
    process_tmp = pytest_root / "process_tmp"
    base_temp = pytest_root / "basetemp"
    ensure_dir(process_tmp)
    env = {
        "TMP": str(process_tmp),
        "TEMP": str(process_tmp),
        "TMPDIR": str(process_tmp),
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    candidate_commands = [target_test_command(task_row), *fallback_test_commands(task_row)]
    deduped: list[list[str]] = []
    seen: set[tuple[str, ...]] = set()
    for command in candidate_commands:
        augmented = [
            *command,
            "--basetemp",
            str(base_temp),
            "-o",
            f"cache_dir={pytest_root / 'cache'}",
            "-p",
            "no:cacheprovider",
        ]
        key = tuple(augmented)
        if key not in seen:
            deduped.append(augmented)
            seen.add(key)

    outputs: list[str] = []
    for command in deduped:
        junit_path = pytest_root / f"junit_{uuid.uuid4().hex}.xml"
        command_with_xml = [*command, "--junitxml", str(junit_path)]
        result = run_command(command_with_xml, cwd=workspace, timeout_s=timeout_s, env=env)
        combined = "\n".join(part for part in [result.stdout, result.stderr] if part).strip()
        outputs.append(f"$ {' '.join(command_with_xml)}\n{combined}")
        junit_metrics = infer_junit_metrics(junit_path)
        output_metrics = infer_output_metrics(combined)
        merged_metrics = merge_test_metrics(junit_metrics, output_metrics)
        if result.returncode == 0:
            return True, outputs[-1][:MAX_FILE_CHARS], merged_metrics
        if is_cleanup_noise_failure(combined):
            if merged_metrics.tests > 0:
                suffix = "\n[cleanup-noise-detected; junitxml used for pass/fail inference]"
                junit_success = merged_metrics.problem_count == 0
                if junit_success:
                    return True, (outputs[-1] + suffix)[:MAX_FILE_CHARS], merged_metrics
                return False, (outputs[-1] + suffix)[:MAX_FILE_CHARS], merged_metrics
        failure_text = combined.lower()
        if "not found" not in failure_text and "no match in any of" not in failure_text and "found no collectors" not in failure_text:
            return False, outputs[-1][:MAX_FILE_CHARS], merged_metrics
    return False, "\n\n".join(outputs)[:MAX_FILE_CHARS], TestRunMetrics()


def is_cleanup_noise_failure(output: str) -> bool:
    text = output.lower()
    return "pytest_sessionfinish" in text and "permissionerror" in text


def infer_output_metrics(output: str) -> TestRunMetrics | None:
    summary_matches = re.findall(r"(\d+)\s+(failed|error|errors|passed|skipped|xfailed|xpassed)", output.lower())
    if summary_matches:
        counts = {"passed": 0, "failed": 0, "errors": 0, "skipped": 0}
        for raw_count, label in summary_matches:
            count = int(raw_count)
            if label == "passed":
                counts["passed"] += count
            elif label == "failed":
                counts["failed"] += count
            elif label in {"error", "errors"}:
                counts["errors"] += count
            elif label == "skipped":
                counts["skipped"] += count
        total = counts["passed"] + counts["failed"] + counts["errors"] + counts["skipped"]
        if total > 0:
            return TestRunMetrics(
                tests=total,
                failures=counts["failed"],
                errors=counts["errors"],
                skipped=counts["skipped"],
                inferred_from_junit=False,
            )

    for line in output.splitlines():
        marker_line = line.strip()
        compact = marker_line.replace(" ", "")
        if not compact or "[100%]" not in compact:
            continue
        compact = compact.replace("[100%]", "")
        if compact and re.fullmatch(r"[.FsxXE]+", compact):
            return TestRunMetrics(
                tests=len(compact),
                failures=compact.count("F"),
                errors=compact.count("E"),
                skipped=compact.count("s") + compact.count("x"),
                inferred_from_junit=False,
            )
    return None


def merge_test_metrics(primary: TestRunMetrics | None, secondary: TestRunMetrics | None) -> TestRunMetrics:
    if primary is None and secondary is None:
        return TestRunMetrics()
    if primary is None:
        return secondary or TestRunMetrics()
    if secondary is None:
        return primary
    return TestRunMetrics(
        tests=max(primary.tests, secondary.tests),
        failures=max(primary.failures, secondary.failures),
        errors=max(primary.errors, secondary.errors),
        skipped=max(primary.skipped, secondary.skipped),
        inferred_from_junit=primary.inferred_from_junit or secondary.inferred_from_junit,
    )


def infer_junit_metrics(junit_path: Path) -> TestRunMetrics | None:
    if not junit_path.exists():
        return None
    try:
        tree = ET.parse(junit_path)
    except ET.ParseError:
        return None
    root = tree.getroot()
    tests = failures = errors = skipped = 0
    for node in root.iter():
        if node.tag in {"testsuite", "testsuites"}:
            tests += int(node.attrib.get("tests", "0") or 0)
            failures += int(node.attrib.get("failures", "0") or 0)
            errors += int(node.attrib.get("errors", "0") or 0)
            skipped += int(node.attrib.get("skipped", "0") or 0)
    if tests <= 0:
        return None
    return TestRunMetrics(
        tests=tests,
        failures=failures,
        errors=errors,
        skipped=skipped,
        inferred_from_junit=True,
    )


def task_brief(task_row: pd.Series) -> str:
    fail_tests = parse_list_field(task_row["FAIL_TO_PASS"])
    hints = str(task_row.get("hints_text") or "").strip()
    hint_block = clip_text(hints, MAX_TASK_HINT_CHARS) if hints else "(none)"
    problem_statement = clip_text(str(task_row["problem_statement"]), MAX_TASK_PROBLEM_CHARS)
    fail_block = "\n".join(f"- {item}" for item in fail_tests[:MAX_TASK_FAIL_TESTS]) if fail_tests else "- (not provided)"
    return (
        f"Repository: {task_row['repo']}\n"
        f"Instance: {task_row['instance_id']}\n"
        f"Base commit: {task_row['base_commit']}\n"
        f"Problem statement:\n{problem_statement}\n\n"
        f"Hints:\n{hint_block}\n\n"
        f"Target failing tests:\n{fail_block}\n"
    )


def controller_mode(task_row: pd.Series, state: RuntimeState, controller: str) -> tuple[str, float]:
    risk = 0.45 * float(task_row["e_proxy"]) + 0.35 * float(task_row["d_proxy"]) + 0.20 * float(task_row["q_proxy"])
    observed_bonus = 0.18 * max(0.0, 1.0 - state.problem_pressure) + 0.08 * state.progress_credit
    estimated_headroom = 0.30 - 0.22 * risk - 0.14 * state.q_ver - 0.10 * state.diagnostic_debt - 0.08 * state.recovery_mass + observed_bonus
    if controller == "minimal_verify":
        return "minimal", estimated_headroom
    if controller == "static_conservative":
        return "safe", estimated_headroom - 0.05
    if controller == "sempc_lite":
        if estimated_headroom >= PERF_DELTA and state.q_ver <= PERF_Q and state.diagnostic_debt <= PERF_DEBT:
            return "performance", estimated_headroom
        return "guarded", estimated_headroom
    if estimated_headroom <= SAFE_DELTA and state.diagnostic_debt > SAFE_DEBT and state.progress_credit < 0.45 and state.problem_pressure > 0.25:
        return "fallback", estimated_headroom
    if state.diagnostic_debt > SAFE_DEBT and state.problem_pressure > 0.45:
        return "fallback", estimated_headroom
    return "guarded", estimated_headroom


def should_verify_initial(controller: str, mode: str, task_row: pd.Series) -> bool:
    if controller == "minimal_verify":
        return False
    if controller == "static_conservative":
        return True
    return mode in {"fallback", "guarded"} and float(task_row["fail_to_pass_count"]) > 0


def should_verify_after_patch(controller: str, mode: str, patch_confidence: float, patch_applied: bool) -> bool:
    if not patch_applied:
        return False
    if controller == "minimal_verify":
        return False
    if controller == "static_conservative":
        return True
    if mode == "fallback":
        return True
    return patch_confidence < 0.72 or mode == "guarded"


def update_observed_problem_pressure(
    state: RuntimeState,
    observed_problem_count: float | None,
    baseline_problem_count: float | None,
) -> float:
    if observed_problem_count is None or baseline_problem_count is None or math.isnan(float(baseline_problem_count)):
        return 1.0
    baseline = max(float(baseline_problem_count), 1.0)
    observed = max(float(observed_problem_count), 0.0)
    normalized = min(observed / baseline, 1.25)
    improvement = max(0.0, 1.0 - min(normalized, 1.0))
    state.problem_pressure = 0.55 * state.problem_pressure + 0.45 * normalized
    state.progress_credit = max(
        0.0,
        min(
            1.0,
            0.60 * state.progress_credit + 0.55 * improvement - 0.12 * max(normalized - 1.0, 0.0),
        ),
    )
    state.last_verified_problem_count = observed
    return normalized


def update_runtime_state(
    state: RuntimeState,
    mode: str,
    verified: bool,
    test_passed: bool | None,
    patch_applied: bool,
    observed_problem_count: float | None = None,
    baseline_problem_count: float | None = None,
) -> None:
    normalized_problem = 1.0
    if verified:
        normalized_problem = update_observed_problem_pressure(state, observed_problem_count, baseline_problem_count)

    if verified:
        state.verification_events += 1
        state.q_ver = max(0.0, 0.68 * state.q_ver - 0.10)
        state.diagnostic_debt = max(0.0, 0.72 * state.diagnostic_debt - 0.08)
    else:
        state.q_ver = min(2.0, 0.92 * state.q_ver + (0.10 if patch_applied else 0.03))
        state.diagnostic_debt = min(2.0, 0.90 * state.diagnostic_debt + (0.08 if patch_applied else 0.03))

    if test_passed is False:
        failure_weight = 0.35 + 0.65 * min(normalized_problem, 1.0)
        state.recovery_mass = min(2.0, 0.82 * state.recovery_mass + 0.20 * failure_weight)
        state.diagnostic_debt = min(2.0, state.diagnostic_debt + 0.18 * failure_weight)
    elif test_passed is True:
        state.recovery_mass = max(0.0, 0.60 * state.recovery_mass - 0.05)
        state.diagnostic_debt = max(0.0, 0.70 * state.diagnostic_debt - 0.10)

    if verified and observed_problem_count is not None and baseline_problem_count is not None and not math.isnan(float(baseline_problem_count)):
        baseline = max(float(baseline_problem_count), 1.0)
        observed = max(float(observed_problem_count), 0.0)
        improvement = max(0.0, 1.0 - min(observed / baseline, 1.0))
        if improvement > 0.0:
            state.q_ver = max(0.0, state.q_ver - 0.06 * improvement)
            state.diagnostic_debt = max(0.0, state.diagnostic_debt - 0.12 * improvement)
            state.recovery_mass = max(0.0, state.recovery_mass - 0.14 * improvement)
        if observed <= 1.0:
            state.q_ver = max(0.0, state.q_ver - 0.06)
            state.diagnostic_debt = max(0.0, state.diagnostic_debt - 0.08)
            state.recovery_mass = max(0.0, state.recovery_mass - 0.10)

    if mode == "fallback":
        state.fallback_events += 1


def safe_state(estimated_headroom: float, state: RuntimeState) -> bool:
    pressure_relief = max(0.0, 1.0 - state.problem_pressure)
    safe_delta = SAFE_DELTA - 0.02 * state.progress_credit - 0.02 * pressure_relief
    safe_q = SAFE_Q + 0.12 * pressure_relief
    safe_debt = SAFE_DEBT + 0.16 * state.progress_credit
    return estimated_headroom > safe_delta and state.q_ver <= safe_q and state.diagnostic_debt <= safe_debt


def log_step(path: Path, payload: dict[str, Any]) -> None:
    ensure_dir(path.parent)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def safe_parse_json_object(text: str) -> dict[str, Any] | None:
    try:
        return parse_json_object(text)
    except Exception:
        return None


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def update_progress_stats(stats: EpisodeStats, metrics: TestRunMetrics) -> None:
    current_problem_count = float(metrics.problem_count)
    if math.isnan(stats.baseline_problem_count):
        stats.baseline_problem_count = current_problem_count
    if math.isnan(stats.best_problem_count):
        stats.best_problem_count = current_problem_count
    if current_problem_count < stats.best_problem_count:
        stats.best_problem_count = current_problem_count
        stats.progress_events += 1
    stats.final_problem_count = current_problem_count
    if not math.isnan(stats.baseline_problem_count):
        stats.best_problem_reduction = max(0.0, stats.baseline_problem_count - stats.best_problem_count)
        stats.final_problem_reduction = max(0.0, stats.baseline_problem_count - stats.final_problem_count)
        stats.any_progress = int(stats.best_problem_reduction > 0.0)


def workspace_change_stats(workspace: Path) -> tuple[int, int]:
    result = run_command(["git", "-C", str(workspace), "diff", "--numstat"], timeout_s=120)
    if result.returncode != 0:
        return 0, 0
    files_changed = 0
    lines_changed = 0
    for line in result.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        files_changed += 1
        for raw in parts[:2]:
            if raw.isdigit():
                lines_changed += int(raw)
    return files_changed, lines_changed


def run_episode(
    task_row: pd.Series,
    controller: str,
    client: LMStudioClient | MockClient,
    results_dir: Path,
    repo_cache_dir: Path | None,
    allow_clone: bool,
    max_steps: int,
    live_repo: bool,
    snapshot_root: Path | None,
) -> EpisodeStats:
    stats = EpisodeStats(controller=controller, instance_id=str(task_row["instance_id"]), repo=str(task_row["repo"]))
    usage_before = usage_snapshot(client)
    step_log_path = results_dir / "step_logs" / f"{controller}__{task_row['instance_id']}.jsonl"
    workspace = results_dir / "workspaces" / f"{controller}__{task_row['instance_id']}"

    state = RuntimeState(
        q_ver=float(task_row["q_proxy"]),
        diagnostic_debt=0.06 + 0.08 * float(task_row["e_proxy"]),
        recovery_mass=0.04 + 0.04 * float(task_row["d_proxy"]),
        contamination=0.02,
    )
    mode, estimated_headroom = controller_mode(task_row, state, controller)
    stats.decision_points = 1
    was_safe = safe_state(estimated_headroom, state)

    if live_repo:
        if snapshot_root is not None:
            snapshot_dir = snapshot_dir_for_task(snapshot_root, task_row)
            if not snapshot_dir.exists():
                raise FileNotFoundError(f"Snapshot not found for {task_row['instance_id']} under {snapshot_root}")
            ensure_snapshot_workspace(snapshot_dir, workspace)
        else:
            if repo_cache_dir is None:
                raise ValueError("repo_cache_dir is required when live_repo=True and snapshot_root is not used")
            repo_root = ensure_repo_cache(str(task_row["repo"]), repo_cache_dir, allow_clone=allow_clone)
            ensure_worktree(repo_root, workspace, str(task_row["base_commit"]))

    baseline_test_pass: bool | None = None
    if live_repo:
        baseline_probe_pass, baseline_probe_output, baseline_probe_metrics = run_target_tests(workspace, task_row)
        update_progress_stats(stats, baseline_probe_metrics)
        update_observed_problem_pressure(state, baseline_probe_metrics.problem_count, max(float(baseline_probe_metrics.problem_count), 1.0))
        log_step(
            step_log_path,
            {
                "step": -1,
                "phase": "baseline_probe",
                "controller": controller,
                "instance_id": task_row["instance_id"],
                "mode": mode,
                "estimated_headroom": estimated_headroom,
                "test_passed": baseline_probe_pass,
                "problem_count": baseline_probe_metrics.problem_count,
                "output": clip_text(baseline_probe_output, MAX_FILE_CHARS),
            },
        )
    if live_repo and should_verify_initial(controller, mode, task_row):
        baseline_test_pass, baseline_output, baseline_metrics = run_target_tests(workspace, task_row)
        stats.test_runs += 1
        stats.verification_events += 1
        update_progress_stats(stats, baseline_metrics)
        log_step(
            step_log_path,
            {
                "step": 0,
                "phase": "initial_verify",
                "controller": controller,
                "instance_id": task_row["instance_id"],
                "mode": mode,
                "estimated_headroom": estimated_headroom,
                "test_passed": baseline_test_pass,
                "problem_count": baseline_metrics.problem_count,
                "output": baseline_output,
            },
        )
        if baseline_test_pass is False and state.first_failure_step is None:
            state.first_failure_step = 0
        if baseline_test_pass is False:
            stats.failed_verification_jobs += 1
        update_runtime_state(
            state,
            mode,
            verified=True,
            test_passed=baseline_test_pass,
            patch_applied=False,
            observed_problem_count=baseline_metrics.problem_count,
            baseline_problem_count=stats.baseline_problem_count,
        )

    recent_observations = "No observations yet."
    final_test_pass = baseline_test_pass if baseline_test_pass is True else False

    for step in range(1, max_steps + 1):
        stats.steps = step
        mode, estimated_headroom = controller_mode(task_row, state, controller)
        stats.decision_points += 1
        current_safe = safe_state(estimated_headroom, state)
        if current_safe:
            state.safe_steps += 1
            if not was_safe and state.return_to_safe_steps is None:
                state.return_to_safe_steps = state.unsafe_streak
            state.unsafe_streak = 0
        else:
            state.unsafe_steps += 1
            state.unsafe_streak += 1
        was_safe = current_safe

        runtime_state_text = json.dumps(
            {
                "mode": mode,
                "estimated_headroom": round(estimated_headroom, 4),
                "q_ver": round(state.q_ver, 4),
                "diagnostic_debt": round(state.diagnostic_debt, 4),
                "recovery_mass": round(state.recovery_mass, 4),
                "problem_pressure": round(state.problem_pressure, 4),
                "progress_credit": round(state.progress_credit, 4),
                "safe": current_safe,
            },
            ensure_ascii=False,
        )

        inspect_messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": INSPECT_PROMPT.format(
                    task_brief=task_brief(task_row),
                    controller_name=controller,
                    runtime_state=runtime_state_text,
                    recent_observations=recent_observations,
                ),
            },
        ]
        inspect_payload = safe_parse_json_object(client.chat(inspect_messages)) or {}
        search_queries = [str(item) for item in inspect_payload.get("search_queries", [])[:3]]
        paths_to_read = [str(item) for item in inspect_payload.get("paths_to_read", [])[:5]]
        hypothesis = str(inspect_payload.get("hypothesis", ""))

        search_outputs: list[str] = []
        file_snippets: list[str] = []
        if live_repo:
            for query in search_queries:
                search_result = f"### search: {query}\n{search_repo(workspace, query)}"
                search_outputs.append(search_result)
                stats.context_bytes += len(search_result.encode("utf-8"))
                stats.search_count += 1
            query_map = {str(path): "" for path in paths_to_read}
            for relative_path in paths_to_read:
                best_query = ""
                path_name = Path(relative_path).name.lower()
                for query in search_queries:
                    query_lower = query.lower()
                    if path_name in query_lower or any(part in query_lower for part in path_name.replace(".", " ").split()):
                        best_query = query
                        break
                query_map[str(relative_path)] = best_query
            for relative_path in paths_to_read:
                snippet = read_repo_context(workspace, relative_path, query_map.get(str(relative_path)) or None)
                file_snippets.append(snippet)
                stats.read_count += 1
                stats.context_files += 1
                stats.context_bytes += len(snippet.encode("utf-8"))

        patch_messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": PATCH_PROMPT.format(
                    task_brief=task_brief(task_row),
                    controller_name=controller,
                    runtime_state=runtime_state_text,
                    search_observations="\n\n".join(search_outputs) or "(none)",
                    file_snippets="\n\n".join(file_snippets) or "(none)",
                ),
            },
        ]
        patch_payload = safe_parse_json_object(client.chat(patch_messages)) or {}
        file_edits = patch_payload.get("file_edits", [])
        if not isinstance(file_edits, list):
            file_edits = []
        patch_confidence = safe_float(patch_payload.get("confidence", 0.0), 0.0)
        reasoning_summary = str(patch_payload.get("reasoning_summary", "parse_fallback"))

        if controller == "sempc_lite" and mode == "performance" and file_edits:
            critique_messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": CRITIQUE_PROMPT.format(
                        task_brief=task_brief(task_row),
                        controller_name=controller,
                        runtime_state=runtime_state_text,
                        candidate_patch=clip_text(json.dumps(file_edits, ensure_ascii=False, indent=2), 3200),
                    ),
                },
            ]
            critique_payload = safe_parse_json_object(client.chat(critique_messages)) or {
                "decision": "reject",
                "projected_success": 0.0,
                "revised_patch": "NO_PATCH",
                "critique_summary": "parse_fallback",
            }
            stats.lookahead_events += 1
            state.lookahead_events += 1
            decision = str(critique_payload.get("decision", "accept"))
            if decision == "revise":
                revised = critique_payload.get("file_edits", critique_payload.get("revised_patch", file_edits))
                if isinstance(revised, list):
                    file_edits = revised
                patch_confidence = max(patch_confidence, safe_float(critique_payload.get("projected_success", patch_confidence), patch_confidence))
            elif decision == "reject":
                file_edits = []
            reasoning_summary = f"{reasoning_summary} | critique={critique_payload.get('critique_summary', '')}".strip()

        stats.patch_attempts += int(bool(file_edits))
        patch_applied = False
        apply_message = "no_patch"
        if live_repo and file_edits:
            patch_applied, apply_message = apply_structured_edits(
                workspace,
                [item for item in file_edits if isinstance(item, dict)],
            )
            if not patch_applied:
                try:
                    stats.recovery_attempts += 1
                    repair_messages = [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {
                            "role": "user",
                            "content": REPAIR_PATCH_PROMPT.format(
                                task_brief=task_brief(task_row),
                                controller_name=controller,
                                runtime_state=runtime_state_text,
                                apply_error=apply_message,
                                candidate_patch=clip_text(json.dumps(file_edits, ensure_ascii=False, indent=2), 3200),
                                file_snippets="\n\n".join(file_snippets) or "(none)",
                            ),
                        },
                    ]
                    repair_payload = safe_parse_json_object(client.chat(repair_messages)) or {}
                    repaired_edits = repair_payload.get("file_edits", [])
                    if isinstance(repaired_edits, list):
                        patch_applied, repair_message = apply_structured_edits(
                            workspace,
                            [item for item in repaired_edits if isinstance(item, dict)],
                        )
                        if patch_applied:
                            apply_message = repair_message
                        else:
                            apply_message = f"{apply_message} | repair={repair_message}"
                except Exception as exc:
                    apply_message = f"{apply_message} | repair=parse_error:{clip_text(str(exc), 160)}"
            if patch_applied:
                stats.patch_apply_successes += 1

        verify_now = should_verify_after_patch(controller, mode, patch_confidence, patch_applied)
        test_passed: bool | None = None
        test_output = ""
        if live_repo and verify_now:
            test_passed, test_output, test_metrics = run_target_tests(workspace, task_row)
            stats.test_runs += 1
            stats.verification_events += 1
            update_progress_stats(stats, test_metrics)
            if test_passed is False and state.first_failure_step is None:
                state.first_failure_step = step
            if test_passed is False:
                stats.failed_verification_jobs += 1
            if test_passed is True:
                final_test_pass = True
        else:
            test_metrics = TestRunMetrics()

        update_runtime_state(
            state,
            mode,
            verified=verify_now,
            test_passed=test_passed,
            patch_applied=patch_applied,
            observed_problem_count=(test_metrics.problem_count if verify_now else None),
            baseline_problem_count=stats.baseline_problem_count,
        )
        recent_observations = json.dumps(
            {
                "hypothesis": hypothesis,
                "reasoning_summary": reasoning_summary,
                "apply_message": apply_message,
                "test_passed": test_passed,
                "test_problem_count": test_metrics.problem_count if verify_now else None,
                "test_output_excerpt": clip_text(test_output, 500) if test_output else "",
            },
            ensure_ascii=False,
        )
        log_step(
            step_log_path,
            {
                "step": step,
                "phase": "loop",
                "controller": controller,
                "instance_id": task_row["instance_id"],
                "mode": mode,
                "estimated_headroom": estimated_headroom,
                "safe": current_safe,
                "problem_pressure": state.problem_pressure,
                "progress_credit": state.progress_credit,
                "search_queries": search_queries,
                "paths_to_read": paths_to_read,
                "patch_attempted": bool(file_edits),
                "patch_applied": patch_applied,
                "patch_confidence": patch_confidence,
                "verify_now": verify_now,
                "test_passed": test_passed,
                "test_problem_count": test_metrics.problem_count if verify_now else None,
                "apply_message": apply_message,
            },
        )

        if patch_applied and test_passed is True:
            stats.success = 1
            stats.final_target_test_pass = 1
            break
        if (
            controller in {"static_conservative", "rsrc_guarded", "sempc_lite"}
            and mode == "fallback"
            and state.unsafe_streak >= 4
            and stats.best_problem_reduction <= 0.0
        ):
            stats.notes = "fallback saturation"
            break
        if not live_repo and step >= 2:
            stats.notes = "mock smoke test"
            break

    if live_repo and not stats.final_target_test_pass:
        final_pass, _, final_metrics = run_target_tests(workspace, task_row)
        stats.test_runs += 1
        update_progress_stats(stats, final_metrics)
        if final_pass is False:
            stats.failed_verification_jobs += 1
        stats.final_target_test_pass = int(final_pass)
        stats.success = int(final_pass)

    stats.fallback_events = state.fallback_events
    stats.lookahead_events = state.lookahead_events
    stats.unsafe_step_count = state.unsafe_steps
    total_steps = max(state.safe_steps + state.unsafe_steps, 1)
    stats.safe_state_rate = state.safe_steps / total_steps
    if state.first_failure_step is not None:
        stats.post_error_extra_work = max(stats.steps - state.first_failure_step, 0)
    if state.return_to_safe_steps is not None:
        stats.return_to_safe_steps = float(state.return_to_safe_steps)
    if live_repo:
        stats.catastrophic_failure = int(stats.final_target_test_pass == 0 and stats.patch_apply_successes == 0 and stats.best_problem_reduction <= 0.0)
        stats.files_changed, stats.lines_changed = workspace_change_stats(workspace)
    stats.recovery_attempts += state.fallback_events
    stats.tool_calls = stats.search_count + stats.read_count + stats.test_runs + stats.patch_attempts
    usage = usage_delta(client, usage_before)
    stats.model_calls = int(usage["model_calls"])
    stats.prompt_tokens = int(usage["prompt_tokens"])
    stats.completion_tokens = int(usage["completion_tokens"])
    stats.total_tokens = int(usage["total_tokens"])
    stats.latency_seconds = float(usage["latency_seconds"])
    episode_path = results_dir / "episodes" / f"{controller}__{task_row['instance_id']}.json"
    write_json(episode_path, {key: value for key, value in stats.__dict__.items()})
    return stats


def aggregate_results(task_results: pd.DataFrame) -> pd.DataFrame:
    grouped = task_results.groupby("controller", dropna=False)
    summary = grouped.agg(
        tasks=("instance_id", "count"),
        success_rate=("success", "mean"),
        catastrophic_failure_rate=("catastrophic_failure", "mean"),
        avg_steps=("steps", "mean"),
        avg_search_count=("search_count", "mean"),
        avg_read_count=("read_count", "mean"),
        avg_patch_attempts=("patch_attempts", "mean"),
        patch_apply_rate=("patch_apply_successes", lambda s: float(np.mean(np.asarray(s, dtype=float) / np.maximum(task_results.loc[s.index, "patch_attempts"], 1)))),
        avg_test_runs=("test_runs", "mean"),
        verification_rate=("verification_events", lambda s: float(np.mean(np.asarray(s, dtype=float) / np.maximum(task_results.loc[s.index, "decision_points"], 1)))),
        fallback_rate=("fallback_events", lambda s: float(np.mean(np.asarray(s, dtype=float) / np.maximum(task_results.loc[s.index, "decision_points"], 1)))),
        safe_state_rate=("safe_state_rate", "mean"),
        progress_rate=("any_progress", "mean"),
        avg_baseline_problem_count=("baseline_problem_count", "mean"),
        avg_best_problem_count=("best_problem_count", "mean"),
        avg_final_problem_count=("final_problem_count", "mean"),
        avg_best_problem_reduction=("best_problem_reduction", "mean"),
        avg_final_problem_reduction=("final_problem_reduction", "mean"),
        avg_post_error_extra_work=("post_error_extra_work", "mean"),
        avg_return_to_safe=("return_to_safe_steps", "mean"),
        avg_model_calls=("model_calls", "mean"),
        avg_total_tokens=("total_tokens", "mean"),
        avg_latency_seconds=("latency_seconds", "mean"),
        avg_tool_calls=("tool_calls", "mean"),
        avg_context_files=("context_files", "mean"),
        avg_context_bytes=("context_bytes", "mean"),
        avg_files_changed=("files_changed", "mean"),
        avg_lines_changed=("lines_changed", "mean"),
        avg_failed_verification_jobs=("failed_verification_jobs", "mean"),
        avg_recovery_attempts=("recovery_attempts", "mean"),
    ).reset_index()
    return summary


def pairwise_shadow_results(task_results: pd.DataFrame, left: str, right: str) -> pd.DataFrame:
    left_rows = task_results[task_results["controller"] == left].set_index("instance_id")
    right_rows = task_results[task_results["controller"] == right].set_index("instance_id")
    joined = left_rows.join(right_rows, lsuffix="_left", rsuffix="_right", how="inner")
    if joined.empty:
        return pd.DataFrame()
    rows = []
    for metric in [
        "success",
        "catastrophic_failure",
        "patch_apply_successes",
        "test_runs",
        "verification_events",
        "fallback_events",
        "any_progress",
        "best_problem_reduction",
        "final_problem_reduction",
        "safe_state_rate",
        "post_error_extra_work",
        "return_to_safe_steps",
        "model_calls",
        "total_tokens",
        "latency_seconds",
        "tool_calls",
        "context_files",
        "context_bytes",
        "files_changed",
        "lines_changed",
        "failed_verification_jobs",
        "recovery_attempts",
    ]:
        diff = joined[f"{metric}_left"].astype(float) - joined[f"{metric}_right"].astype(float)
        ci_low, ci_high = bootstrap_interval(diff.to_numpy(dtype=float), rounds=400)
        rows.append(
            {
                "pair": f"{left} - {right}",
                "metric": metric,
                "mean_diff": float(diff.mean()),
                "ci_low": float(ci_low),
                "ci_high": float(ci_high),
                "n": int(len(diff)),
            }
        )
    return pd.DataFrame(rows)


def episode_result_path(results_dir: Path, controller: str, instance_id: str) -> Path:
    return results_dir / "episodes" / f"{controller}__{instance_id}.json"


def failed_episode_stats(controller: str, task_row: pd.Series, exc: Exception) -> EpisodeStats:
    stats = EpisodeStats(controller=controller, instance_id=str(task_row["instance_id"]), repo=str(task_row["repo"]))
    stats.catastrophic_failure = 1
    stats.notes = f"episode_error:{clip_text(str(exc), 240)}"
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a live repository-executing shadow-runtime experiment against LM Studio or a mock backend.")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--results-dir", type=Path, default=DEFAULT_RESULTS_DIR)
    parser.add_argument("--controllers", nargs="+", default=["minimal_verify", "static_conservative", "rsrc_guarded", "sempc_lite"])
    parser.add_argument("--backend", choices=["mock", "lmstudio"], default="mock")
    parser.add_argument("--base-url", default=os.environ.get("LMSTUDIO_BASE_URL", "http://localhost:1234/v1"))
    parser.add_argument("--model", default=os.environ.get("LMSTUDIO_MODEL", "Qwen/Qwen2.5-Coder-14B-Instruct-GGUF"))
    parser.add_argument("--api-key", default=os.environ.get("LMSTUDIO_API_KEY"))
    parser.add_argument("--repo-cache-dir", type=Path, default=DEFAULT_REPO_CACHE_DIR)
    parser.add_argument("--snapshot-root", type=Path, default=None)
    parser.add_argument("--prepare-snapshots", action="store_true", help="Download GitHub commit zip snapshots before running live episodes.")
    parser.add_argument("--allow-clone", action="store_true")
    parser.add_argument("--max-steps", type=int, default=6)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--live-repo", action="store_true", help="Enable real repository worktree setup, patch application, and test execution.")
    parser.add_argument("--resume-existing", action="store_true", help="Reuse existing per-episode JSON files in the results directory.")
    parser.add_argument("--continue-on-error", action="store_true", help="Record episode-level errors and continue instead of aborting the whole run.")
    args = parser.parse_args()

    ensure_dir(args.results_dir)
    tasks = pd.read_csv(args.manifest)
    if args.limit is not None:
        tasks = tasks.head(args.limit).copy()

    snapshot_root = args.snapshot_root
    if snapshot_root is None and args.prepare_snapshots:
        snapshot_root = DEFAULT_SNAPSHOT_DIR
    if snapshot_root is not None:
        ensure_dir(snapshot_root)
        if args.prepare_snapshots:
            for _, task_row in tasks.iterrows():
                path = prepare_snapshot_download(task_row, snapshot_root)
                print(f"[shadow-runtime] prepared snapshot for {task_row['instance_id']} at {path}")

    client: LMStudioClient | MockClient
    if args.backend == "lmstudio":
        client = LMStudioClient(base_url=args.base_url, model=args.model, api_key=args.api_key)
    else:
        client = MockClient()

    results: list[dict[str, Any]] = []
    for controller in args.controllers:
        for _, task_row in tasks.iterrows():
            existing_path = episode_result_path(args.results_dir, controller, str(task_row["instance_id"]))
            if args.resume_existing and existing_path.exists():
                payload = json.loads(existing_path.read_text(encoding="utf-8"))
                results.append(payload)
                print(
                    f"[shadow-runtime] resumed controller={controller} instance={task_row['instance_id']} "
                    f"success={payload.get('success')} steps={payload.get('steps')} tests={payload.get('test_runs')}"
                )
                continue
            try:
                stats = run_episode(
                    task_row=task_row,
                    controller=controller,
                    client=client,
                    results_dir=args.results_dir,
                    repo_cache_dir=args.repo_cache_dir,
                    allow_clone=args.allow_clone,
                    max_steps=args.max_steps,
                    live_repo=args.live_repo,
                    snapshot_root=snapshot_root,
                )
            except Exception as exc:
                if not args.continue_on_error:
                    raise
                stats = failed_episode_stats(controller, task_row, exc)
                write_json(existing_path, {key: value for key, value in stats.__dict__.items()})
            results.append(stats.__dict__)
            print(
                f"[shadow-runtime] controller={controller} instance={task_row['instance_id']} "
                f"success={stats.success} steps={stats.steps} tests={stats.test_runs}"
            )

    task_results = pd.DataFrame(results)
    task_results.to_csv(args.results_dir / "shadow_runtime_task_results.csv", index=False)

    summary = aggregate_results(task_results)
    summary.to_csv(args.results_dir / "shadow_runtime_summary.csv", index=False)
    pairwise = pairwise_shadow_results(task_results, "sempc_lite", "rsrc_guarded")
    if not pairwise.empty:
        pairwise.to_csv(args.results_dir / "shadow_runtime_pairwise.csv", index=False)

    write_json(
        args.results_dir / "shadow_runtime_summary.json",
        {
            "backend": args.backend,
            "model": args.model,
            "live_repo": bool(args.live_repo),
            "controllers": args.controllers,
            "tasks": int(len(tasks)),
            "summary_rows": summary.to_dict(orient="records"),
            "pairwise_rows": pairwise.to_dict(orient="records") if not pairwise.empty else [],
        },
    )
    print(f"Wrote shadow-runtime outputs to {args.results_dir}")


if __name__ == "__main__":
    main()
