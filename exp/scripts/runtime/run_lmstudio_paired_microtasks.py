from __future__ import annotations

import argparse
import csv
import json
import math
import re
import socket
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_BASE_URL = "http://127.0.0.1:1234/v1"
DEFAULT_OUTPUT_DIR = Path("exp/results/emse_runtime/lmstudio_paired_microtask_pilot")

RESULT_COLUMNS = [
    "run_id",
    "instance_id",
    "repo",
    "controller",
    "execution_mode",
    "execute_status",
    "success",
    "final_target_test_pass",
    "catastrophic_failure",
    "test_runs",
    "verification_events",
    "search_count",
    "read_count",
    "patch_attempts",
    "patch_apply_successes",
    "fallback_events",
    "post_error_extra_work",
    "best_problem_reduction",
    "final_problem_reduction",
    "model_calls",
    "prompt_tokens",
    "completion_tokens",
    "total_tokens",
    "latency_seconds",
    "tool_calls",
    "context_files",
    "context_bytes",
    "files_changed",
    "lines_changed",
    "failed_verification_jobs",
    "recovery_attempts",
    "expected_choice",
    "predicted_choice",
    "route",
    "workload_risk",
    "quality_risk",
    "notes",
]

TASKS: list[dict[str, str]] = [
    {
        "instance_id": "micro_off_by_one_window",
        "repo": "controlled/micro",
        "risk_tier": "low",
        "issue": "The sliding window helper should return all windows of length k. It currently drops the final valid window.",
        "buggy_code": """def windows(items, k):
    out = []
    for i in range(0, len(items) - k):
        out.append(items[i:i+k])
    return out
""",
        "options": """A. Change out.append(items[i:i+k]) to out.append(items[i:i+k+1]).
B. Return out[:-1] at the end.
C. Change range(0, len(items) - k) to range(0, len(items) - k + 1).
D. Change range(0, len(items) - k) to range(1, len(items) - k).""",
        "answer": "C",
    },
    {
        "instance_id": "micro_mutable_default",
        "repo": "controlled/micro",
        "risk_tier": "medium",
        "issue": "Repeated calls to add_label leak labels from earlier calls.",
        "buggy_code": """def add_label(name, labels=[]):
    labels.append(name)
    return labels
""",
        "options": """A. Replace labels.append(name) with labels = labels + [name] but keep labels=[].
B. Use labels=None, create a new list inside the function when labels is None.
C. Clear labels before appending name.
D. Return tuple(labels) instead of labels.""",
        "answer": "B",
    },
    {
        "instance_id": "micro_even_median",
        "repo": "controlled/micro",
        "risk_tier": "low",
        "issue": "median([1, 3]) returns 3, but the expected value is 2.0.",
        "buggy_code": """def median(values):
    ordered = sorted(values)
    mid = len(ordered) // 2
    return ordered[mid]
""",
        "options": """A. For all lengths, return ordered[mid - 1].
B. Sort in reverse order before taking mid.
C. Convert all values to strings before sorting.
D. For even lengths, return (ordered[mid - 1] + ordered[mid]) / 2.""",
        "answer": "D",
    },
    {
        "instance_id": "micro_cache_key",
        "repo": "controlled/micro",
        "risk_tier": "medium",
        "issue": "The cached fetch result ignores locale, so fetch('home', 'fr') can return the English page.",
        "buggy_code": """cache = {}

def fetch(page, locale):
    key = page
    if key not in cache:
        cache[key] = load_page(page, locale)
    return cache[key]
""",
        "options": """A. Use key = (page, locale).
B. Use key = locale only.
C. Delete the cache lookup.
D. Call load_page(page, 'en') for every locale.""",
        "answer": "A",
    },
    {
        "instance_id": "micro_boolean_parse",
        "repo": "controlled/micro",
        "risk_tier": "low",
        "issue": "parse_bool('false') returns True because non-empty strings are truthy.",
        "buggy_code": """def parse_bool(value):
    return bool(value)
""",
        "options": """A. Return value is not None.
B. Return not bool(value).
C. Normalize strings and return True only for values such as 'true', '1', and 'yes'.
D. Wrap the value in str() and then bool().""",
        "answer": "C",
    },
    {
        "instance_id": "micro_topk_order",
        "repo": "controlled/micro",
        "risk_tier": "low",
        "issue": "top_k([5, 1, 4], 2) should return [5, 4], but returns [1, 4].",
        "buggy_code": """def top_k(scores, k):
    return sorted(scores)[:k]
""",
        "options": """A. Return sorted(scores)[-k:] without changing order.
B. Sort with reverse=True before slicing.
C. Return scores[:k] without sorting.
D. Use min(scores) instead of sorted(scores).""",
        "answer": "B",
    },
    {
        "instance_id": "micro_retry_condition",
        "repo": "controlled/micro",
        "risk_tier": "medium",
        "issue": "The retry loop retries after validation errors, but should only retry transient timeout errors.",
        "buggy_code": """def should_retry(error):
    return isinstance(error, Exception)
""",
        "options": """A. Return not isinstance(error, TimeoutError).
B. Always return True.
C. Retry only when str(error) is empty.
D. Return isinstance(error, TimeoutError).""",
        "answer": "D",
    },
    {
        "instance_id": "micro_interval_overlap",
        "repo": "controlled/micro",
        "risk_tier": "medium",
        "issue": "Closed intervals that touch at an endpoint should overlap. overlap((1, 3), (3, 5)) currently returns False.",
        "buggy_code": """def overlap(a, b):
    return a[0] < b[1] and b[0] < a[1]
""",
        "options": """A. Use >= comparisons for both sides.
B. Return a == b.
C. Use <= comparisons for closed intervals: a[0] <= b[1] and b[0] <= a[1].
D. Sort the two intervals and compare only their starts.""",
        "answer": "C",
    },
    {
        "instance_id": "micro_path_join",
        "repo": "controlled/micro",
        "risk_tier": "medium",
        "issue": "join_url('api/', '/users') returns 'api//users'. It should return 'api/users'.",
        "buggy_code": """def join_url(base, path):
    return base + "/" + path
""",
        "options": """A. Return base.rstrip('/') + '/' + path.lstrip('/').
B. Return base.lstrip('/') + '/' + path.rstrip('/').
C. Remove every slash from both strings.
D. Return path + '/' + base.""",
        "answer": "A",
    },
    {
        "instance_id": "micro_deduplicate_order",
        "repo": "controlled/micro",
        "risk_tier": "low",
        "issue": "unique([3, 1, 3, 2]) should preserve first-seen order and return [3, 1, 2].",
        "buggy_code": """def unique(items):
    return list(set(items))
""",
        "options": """A. Return sorted(set(items)).
B. Reverse the input before calling set().
C. Convert each item to a string before deduplicating.
D. Track a seen set while appending unseen items to an output list.""",
        "answer": "D",
    },
    {
        "instance_id": "micro_shadowed_counter",
        "repo": "controlled/micro",
        "risk_tier": "high",
        "issue": "count_matches always returns 0 because the inner assignment shadows the counter update.",
        "buggy_code": """def count_matches(rows, target):
    count = 0
    for row in rows:
        if row == target:
            count = count
    return count
""",
        "options": """A. Initialize count to 1.
B. Replace count = count with count += 1.
C. Return len(rows) for every target.
D. Break immediately when the first matching row is found.""",
        "answer": "B",
    },
    {
        "instance_id": "micro_nested_config",
        "repo": "controlled/micro",
        "risk_tier": "high",
        "issue": "A missing nested config key raises KeyError. The function should return the provided default instead.",
        "buggy_code": """def get_timeout(config, default=30):
    return config["network"]["timeout"]
""",
        "options": """A. Catch every exception and return None.
B. Return default without reading config.
C. Use config.get('network', {}).get('timeout', default).
D. Use config['timeout'] instead of config['network']['timeout'].""",
        "answer": "C",
    },
]


@dataclass
class CallRecord:
    label: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    latency_seconds: float
    response_text: str


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def estimate_text_tokens(value: str) -> int:
    return max(1, int(math.ceil(len(str(value)) / 4.0)))


def estimate_message_tokens(messages: list[dict[str, str]]) -> int:
    return estimate_text_tokens(json.dumps(messages, ensure_ascii=False))


def request_json(url: str, method: str = "GET", payload: dict[str, Any] | None = None, timeout: float = 30.0) -> dict[str, Any]:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"} if payload is not None else {}
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def discover_model(base_url: str, timeout: float) -> str:
    payload = request_json(base_url.rstrip("/") + "/models", timeout=timeout)
    models = payload.get("data", [])
    model_ids = [str(item.get("id", "")) for item in models if "embedding" not in str(item.get("id", "")).lower()]
    if not model_ids:
        raise RuntimeError("LM Studio /models returned no chat model.")
    return model_ids[0]


def call_lmstudio(
    base_url: str,
    model: str,
    messages: list[dict[str, str]],
    timeout: float,
    max_tokens: int,
    temperature: float,
    label: str,
    reasoning_effort: str,
) -> CallRecord:
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if reasoning_effort:
        payload["reasoning_effort"] = reasoning_effort
    start = time.perf_counter()
    parsed = request_json(base_url.rstrip("/") + "/chat/completions", method="POST", payload=payload, timeout=timeout)
    latency = time.perf_counter() - start
    choices = parsed.get("choices") or []
    if not choices:
        raise RuntimeError(f"LM Studio returned no choices: {parsed}")
    message = choices[0].get("message", {})
    content = str(message.get("content", "") or "")
    reasoning = str(message.get("reasoning_content", "") or "")
    text = content if content.strip() else reasoning
    usage = parsed.get("usage") or {}
    prompt_tokens = int(usage.get("prompt_tokens") or estimate_message_tokens(messages))
    completion_tokens = int(usage.get("completion_tokens") or estimate_text_tokens(text))
    total_tokens = int(usage.get("total_tokens") or (prompt_tokens + completion_tokens))
    return CallRecord(label, prompt_tokens, completion_tokens, total_tokens, latency, text)


JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


def parse_json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`")
        if "\n" in stripped:
            stripped = stripped.split("\n", 1)[1]
    try:
        parsed = json.loads(stripped)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        match = JSON_RE.search(stripped)
        if not match:
            return {}
        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}


def normalize_choice(value: Any) -> str:
    text = str(value or "").strip().upper()
    match = re.search(r"\b([ABCD])\b", text)
    return match.group(1) if match else ""


def full_task_text(task: dict[str, str]) -> str:
    return f"""Issue:
{task['issue']}

Buggy code:
{task['buggy_code']}

Candidate patches:
{task['options']}
"""


def compact_gate_text(task: dict[str, str]) -> str:
    return f"""Issue:
{task['issue']}

Buggy code:
{task['buggy_code']}

Visible risk tier from pre-execution metadata: {task['risk_tier']}
"""


def json_messages(system: str, user: str) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def usage_totals(calls: list[CallRecord]) -> dict[str, float]:
    return {
        "model_calls": float(len(calls)),
        "prompt_tokens": float(sum(call.prompt_tokens for call in calls)),
        "completion_tokens": float(sum(call.completion_tokens for call in calls)),
        "total_tokens": float(sum(call.total_tokens for call in calls)),
        "latency_seconds": float(sum(call.latency_seconds for call in calls)),
    }


def run_standard(task: dict[str, str], args: argparse.Namespace, model: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    calls: list[CallRecord] = []
    logs: list[dict[str, Any]] = []
    system = "You are a standard multi-step software agent. Return compact JSON only."
    try:
        diagnosis_prompt = f"""Diagnose the bug before choosing a patch.

{full_task_text(task)}

Return JSON with keys: diagnosis, likely_choice, uncertainty."""
        call = call_lmstudio(
            args.lmstudio_base_url,
            model,
            json_messages(system, diagnosis_prompt),
            args.timeout,
            420,
            0.0,
            "standard_diagnosis",
            args.reasoning_effort,
        )
        calls.append(call)
        diagnosis = parse_json_object(call.response_text)

        decision_prompt = f"""Use the diagnosis to choose the best patch.

Diagnosis JSON:
{json.dumps(diagnosis, ensure_ascii=False)}

{full_task_text(task)}

Return JSON with keys: choice, confidence, reason."""
        call = call_lmstudio(
            args.lmstudio_base_url,
            model,
            json_messages(system, decision_prompt),
            args.timeout,
            260,
            0.0,
            "standard_decision",
            args.reasoning_effort,
        )
        calls.append(call)
        decision = parse_json_object(call.response_text)

        verify_prompt = f"""Verify the proposed choice against the issue and code.

Proposed choice JSON:
{json.dumps(decision, ensure_ascii=False)}

{full_task_text(task)}

Return JSON with keys: final_choice, changed, verification_note."""
        call = call_lmstudio(
            args.lmstudio_base_url,
            model,
            json_messages(system, verify_prompt),
            args.timeout,
            260,
            0.0,
            "standard_verify",
            args.reasoning_effort,
        )
        calls.append(call)
        verification = parse_json_object(call.response_text)

        choice = normalize_choice(verification.get("final_choice")) or normalize_choice(decision.get("choice")) or normalize_choice(diagnosis.get("likely_choice"))
        route = "standard_multistep"
        workload_risk = str(diagnosis.get("uncertainty", "unknown"))[:40]
        quality_risk = "low" if choice else "high"
        notes = json.dumps({"diagnosis": diagnosis, "decision": decision, "verification": verification}, ensure_ascii=False)
    except (RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        choice = ""
        route = "standard_error"
        workload_risk = "unknown"
        quality_risk = "high"
        notes = f"standard workflow failed: {exc}"

    expected = task["answer"]
    success = int(choice == expected)
    catastrophic = int(not choice)
    totals = usage_totals(calls)
    row = base_result_row(task, "standard_agent", choice, expected, success, catastrophic, totals)
    row.update(
        {
            "test_runs": 1,
            "verification_events": 1,
            "search_count": 1,
            "read_count": 3,
            "patch_attempts": 1,
            "patch_apply_successes": success,
            "route": route,
            "workload_risk": workload_risk,
            "quality_risk": quality_risk,
            "notes": notes,
        }
    )
    for call in calls:
        logs.append(call_log(task, "standard_agent", call))
    return row, logs


def run_gated_guarded(task: dict[str, str], args: argparse.Namespace, model: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    calls: list[CallRecord] = []
    logs: list[dict[str, Any]] = []
    system = "You are a proposal-time workload gate for agentic code workflows. Return compact JSON only."
    try:
        gate_prompt = f"""Decide whether this task should use a direct low-cost workflow or a guarded workflow.

Use only pre-execution information. Do not solve the task yet.

{compact_gate_text(task)}

Return JSON with keys:
- route: one of ["direct", "guarded"]
- workload_risk: one of ["low", "medium", "high"]
- quality_risk: one of ["low", "medium", "high"]
- reason: one short sentence"""
        call = call_lmstudio(
            args.lmstudio_base_url,
            model,
            json_messages(system, gate_prompt),
            args.timeout,
            220,
            0.0,
            "gated_gate",
            args.reasoning_effort,
        )
        calls.append(call)
        gate = parse_json_object(call.response_text)
        route = str(gate.get("route", "")).strip().lower()
        workload_risk = str(gate.get("workload_risk", task["risk_tier"])).strip().lower()
        if route not in {"direct", "guarded"}:
            route = "guarded" if workload_risk == "high" else "direct"

        if route == "guarded":
            answer_prompt = f"""Use the guarded workflow. Make one bounded pass. Do not request extra search or verification.

{full_task_text(task)}

Return JSON with keys: choice, confidence, stop_rule."""
            max_tokens = 210
            answer_system = "You are a resource-guarded code agent. Return compact JSON only."
        else:
            answer_prompt = f"""Use the direct low-cost workflow. Choose the best patch without a separate verification round.

{full_task_text(task)}

Return JSON with keys: choice, confidence, reason."""
            max_tokens = 190
            answer_system = "You are a direct low-cost code agent. Return compact JSON only."
        call = call_lmstudio(
            args.lmstudio_base_url,
            model,
            json_messages(answer_system, answer_prompt),
            args.timeout,
            max_tokens,
            0.0,
            "gated_answer",
            args.reasoning_effort,
        )
        calls.append(call)
        answer = parse_json_object(call.response_text)
        choice = normalize_choice(answer.get("choice"))
        quality_risk = str(gate.get("quality_risk", "unknown"))[:40]
        notes = json.dumps({"gate": gate, "answer": answer}, ensure_ascii=False)
    except (RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        choice = ""
        route = "gated_error"
        workload_risk = "unknown"
        quality_risk = "high"
        notes = f"gated workflow failed: {exc}"

    expected = task["answer"]
    success = int(choice == expected)
    catastrophic = int(not choice)
    totals = usage_totals(calls)
    row = base_result_row(task, "gated_guarded", choice, expected, success, catastrophic, totals)
    row.update(
        {
            "test_runs": 0,
            "verification_events": 0,
            "search_count": 1,
            "read_count": 2,
            "patch_attempts": 1,
            "patch_apply_successes": success,
            "fallback_events": 1 if route == "guarded" else 0,
            "route": route,
            "workload_risk": workload_risk,
            "quality_risk": quality_risk,
            "notes": notes,
        }
    )
    for call in calls:
        logs.append(call_log(task, "gated_guarded", call))
    return row, logs


def run_direct_once(task: dict[str, str], args: argparse.Namespace, model: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    calls: list[CallRecord] = []
    logs: list[dict[str, Any]] = []
    system = "You are a direct one-pass code triage agent. Return compact JSON only."
    try:
        answer_prompt = f"""Choose the best patch in one pass. Do not run a separate gate or verification round.

{full_task_text(task)}

Return JSON with keys: choice, confidence, reason."""
        call = call_lmstudio(
            args.lmstudio_base_url,
            model,
            json_messages(system, answer_prompt),
            args.timeout,
            220,
            0.0,
            "direct_answer",
            args.reasoning_effort,
        )
        calls.append(call)
        answer = parse_json_object(call.response_text)
        choice = normalize_choice(answer.get("choice"))
        route = "direct_once"
        workload_risk = "not_estimated"
        quality_risk = "low" if choice else "high"
        notes = json.dumps({"answer": answer}, ensure_ascii=False)
    except (RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        choice = ""
        route = "direct_error"
        workload_risk = "unknown"
        quality_risk = "high"
        notes = f"direct workflow failed: {exc}"

    expected = task["answer"]
    success = int(choice == expected)
    catastrophic = int(not choice)
    totals = usage_totals(calls)
    row = base_result_row(task, "direct_once", choice, expected, success, catastrophic, totals)
    row.update(
        {
            "test_runs": 0,
            "verification_events": 0,
            "search_count": 0,
            "read_count": 1,
            "patch_attempts": 1,
            "patch_apply_successes": success,
            "route": route,
            "workload_risk": workload_risk,
            "quality_risk": quality_risk,
            "notes": notes,
        }
    )
    for call in calls:
        logs.append(call_log(task, "direct_once", call))
    return row, logs


def base_result_row(
    task: dict[str, str],
    controller: str,
    choice: str,
    expected: str,
    success: int,
    catastrophic: int,
    totals: dict[str, float],
) -> dict[str, Any]:
    return {
        "run_id": "lmstudio_paired_microtask_pilot",
        "instance_id": task["instance_id"],
        "repo": task["repo"],
        "controller": controller,
        "execution_mode": "lmstudio_controlled_microtask",
        "execute_status": "completed",
        "success": success,
        "final_target_test_pass": success,
        "catastrophic_failure": catastrophic,
        "test_runs": 0,
        "verification_events": 0,
        "search_count": 0,
        "read_count": 0,
        "patch_attempts": 0,
        "patch_apply_successes": 0,
        "fallback_events": 0,
        "post_error_extra_work": 0,
        "best_problem_reduction": float(success),
        "final_problem_reduction": float(success),
        "model_calls": int(totals["model_calls"]),
        "prompt_tokens": int(totals["prompt_tokens"]),
        "completion_tokens": int(totals["completion_tokens"]),
        "total_tokens": int(totals["total_tokens"]),
        "latency_seconds": round(float(totals["latency_seconds"]), 4),
        "tool_calls": 0,
        "context_files": 1,
        "context_bytes": len(full_task_text(task).encode("utf-8")),
        "files_changed": 0,
        "lines_changed": 0,
        "failed_verification_jobs": 0,
        "recovery_attempts": 0,
        "expected_choice": expected,
        "predicted_choice": choice,
        "route": "",
        "workload_risk": "",
        "quality_risk": "",
        "notes": "",
    }


def call_log(task: dict[str, str], controller: str, call: CallRecord) -> dict[str, Any]:
    return {
        "instance_id": task["instance_id"],
        "controller": controller,
        "call_label": call.label,
        "prompt_tokens": call.prompt_tokens,
        "completion_tokens": call.completion_tokens,
        "total_tokens": call.total_tokens,
        "latency_seconds": call.latency_seconds,
        "response_text": call.response_text,
    }


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    ensure_dir(path.parent)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({col: row.get(col, "") for col in columns})


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    ensure_dir(path.parent)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def mean(values: list[float]) -> float:
    return float(sum(values) / len(values)) if values else float("nan")


def summarize(rows: list[dict[str, Any]], model: str, output_dir: Path) -> dict[str, Any]:
    by_controller: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_controller.setdefault(str(row["controller"]), []).append(row)

    controller_summary: dict[str, dict[str, float]] = {}
    for controller, items in by_controller.items():
        controller_summary[controller] = {
            "n": len(items),
            "success_rate": mean([float(row["success"]) for row in items]),
            "mean_model_calls": mean([float(row["model_calls"]) for row in items]),
            "mean_total_tokens": mean([float(row["total_tokens"]) for row in items]),
            "mean_prompt_tokens": mean([float(row["prompt_tokens"]) for row in items]),
            "mean_completion_tokens": mean([float(row["completion_tokens"]) for row in items]),
            "mean_latency_seconds": mean([float(row["latency_seconds"]) for row in items]),
        }

    paired_diffs = []
    task_ids = sorted({str(row["instance_id"]) for row in rows})
    for instance_id in task_ids:
        task_rows = [row for row in rows if row["instance_id"] == instance_id]
        standard = next((row for row in task_rows if row["controller"] == "standard_agent"), None)
        gated = next((row for row in task_rows if row["controller"] == "gated_guarded"), None)
        if not standard or not gated:
            continue
        paired_diffs.append(
            {
                "instance_id": instance_id,
                "success_diff_gated_minus_standard": float(gated["success"]) - float(standard["success"]),
                "token_diff_gated_minus_standard": float(gated["total_tokens"]) - float(standard["total_tokens"]),
                "call_diff_gated_minus_standard": float(gated["model_calls"]) - float(standard["model_calls"]),
                "latency_diff_gated_minus_standard": float(gated["latency_seconds"]) - float(standard["latency_seconds"]),
            }
        )

    token_diff = mean([row["token_diff_gated_minus_standard"] for row in paired_diffs])
    standard_tokens = controller_summary.get("standard_agent", {}).get("mean_total_tokens", float("nan"))
    percent_token_change = 100.0 * token_diff / standard_tokens if standard_tokens and not math.isnan(standard_tokens) else float("nan")
    summary = {
        "model": model,
        "output_dir": str(output_dir),
        "tasks": len(task_ids),
        "rows": len(rows),
        "controllers": controller_summary,
        "paired_mean_success_diff_gated_minus_standard": mean([row["success_diff_gated_minus_standard"] for row in paired_diffs]),
        "paired_mean_token_diff_gated_minus_standard": token_diff,
        "paired_mean_token_percent_change": percent_token_change,
        "paired_mean_call_diff_gated_minus_standard": mean([row["call_diff_gated_minus_standard"] for row in paired_diffs]),
        "paired_mean_latency_diff_gated_minus_standard": mean([row["latency_diff_gated_minus_standard"] for row in paired_diffs]),
        "interpretation": "Controlled microtask pilot; measures LM Studio call-level resource use, not repository-level agent execution.",
    }
    return summary


def write_report(path: Path, summary: dict[str, Any], result_path: Path, calls_path: Path) -> None:
    controllers = summary["controllers"]
    lines = [
        "# LM Studio Paired Microtask Runtime Pilot",
        "",
        "This controlled pilot compares the same local model on the same self-contained code-repair triage tasks.",
        "It measures prompt/completion tokens, model calls, latency, and answer correctness. It does not execute third-party repositories or validate patch application.",
        "",
        f"- Model: `{summary['model']}`",
        f"- Tasks: {summary['tasks']}",
        f"- Result CSV: `{result_path}`",
        f"- Call log: `{calls_path}`",
        "",
        "## Controller Summary",
        "",
        "| controller | n | success_rate | mean_calls | mean_total_tokens | mean_latency_s |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for controller, values in sorted(controllers.items()):
        lines.append(
            f"| {controller} | {int(values['n'])} | {values['success_rate']:.3f} | "
            f"{values['mean_model_calls']:.2f} | {values['mean_total_tokens']:.1f} | {values['mean_latency_seconds']:.2f} |"
        )
    lines.extend(
        [
            "",
            "## Paired Gated Minus Standard",
            "",
            f"- Success-rate difference: {summary['paired_mean_success_diff_gated_minus_standard']:.3f}",
            f"- Mean token difference: {summary['paired_mean_token_diff_gated_minus_standard']:.1f}",
            f"- Mean token percent change: {summary['paired_mean_token_percent_change']:.1f}%",
            f"- Mean model-call difference: {summary['paired_mean_call_diff_gated_minus_standard']:.2f}",
            f"- Mean latency difference: {summary['paired_mean_latency_diff_gated_minus_standard']:.2f}s",
            "",
            "## Evidence Boundary",
            "",
            "- Use this as a first runtime/token sanity check for the gate design.",
            "- Do not present it as repository-level SWE-bench evidence.",
            "- A manuscript-level runtime claim still requires paired repository or agent-workflow execution with direct token/model-call logging.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def selected_tasks(limit: int) -> list[dict[str, str]]:
    if limit <= 0:
        return TASKS
    return TASKS[: min(limit, len(TASKS))]


def run_order(task_index: int, mode: str) -> list[str]:
    if mode == "standard-first":
        return ["standard_agent", "gated_guarded"]
    if mode == "gated-first":
        return ["gated_guarded", "standard_agent"]
    return ["standard_agent", "gated_guarded"] if task_index % 2 == 0 else ["gated_guarded", "standard_agent"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a paired LM Studio runtime/token pilot on controlled code-repair microtasks.")
    parser.add_argument("--lmstudio-base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--model", default="")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--max-tasks", type=int, default=8)
    parser.add_argument("--timeout", type=float, default=90.0)
    parser.add_argument("--order", choices=["alternate", "standard-first", "gated-first"], default="alternate")
    parser.add_argument("--progress-every", type=int, default=1)
    parser.add_argument("--reasoning-effort", default="none", help="OpenAI-compatible reasoning_effort value; use empty string to omit.")
    parser.add_argument("--include-direct-baseline", action="store_true", help="Also run a one-pass direct baseline as a diagnostic comparator.")
    args = parser.parse_args()

    output_dir = ensure_dir(args.output_dir)
    model = args.model or discover_model(args.lmstudio_base_url, args.timeout)
    tasks = selected_tasks(args.max_tasks)
    rows: list[dict[str, Any]] = []
    call_logs: list[dict[str, Any]] = []
    total_runs = len(tasks) * (3 if args.include_direct_baseline else 2)
    completed = 0

    for index, task in enumerate(tasks):
        controllers = run_order(index, args.order)
        if args.include_direct_baseline:
            controllers.append("direct_once")
        for controller in controllers:
            if controller == "standard_agent":
                row, logs = run_standard(task, args, model)
            elif controller == "gated_guarded":
                row, logs = run_gated_guarded(task, args, model)
            else:
                row, logs = run_direct_once(task, args, model)
            rows.append(row)
            call_logs.extend(logs)
            completed += 1
            if args.progress_every > 0 and (completed == 1 or completed % args.progress_every == 0 or completed == total_runs):
                print(
                    f"[microtask] {completed}/{total_runs} "
                    f"{task['instance_id']}::{controller} "
                    f"choice={row['predicted_choice']} expected={row['expected_choice']} "
                    f"success={row['success']} tokens={row['total_tokens']}",
                    flush=True,
                )

    result_path = output_dir / "runtime_task_results.csv"
    calls_path = output_dir / "runtime_call_log.jsonl"
    summary_path = output_dir / "runtime_microtask_summary.json"
    report_path = output_dir / "runtime_microtask_report.md"

    write_csv(result_path, rows, RESULT_COLUMNS)
    write_jsonl(calls_path, call_logs)
    summary = summarize(rows, model, output_dir)
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    write_report(report_path, summary, result_path, calls_path)
    print(f"Wrote runtime task results to {result_path}")
    print(f"Wrote microtask report to {report_path}")


if __name__ == "__main__":
    main()
