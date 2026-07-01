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
DEFAULT_OUTPUT_DIR = Path("exp/results/emse_runtime/lmstudio_context_gate_challenge_v1")

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
        "instance_id": "ctx_window_boundary",
        "repo": "controlled/context",
        "risk_tier": "low",
        "issue": "The window helper drops the final valid window.",
        "buggy_code": """def windows(items, k):
    out = []
    for i in range(0, len(items) - k):
        out.append(items[i:i+k])
    return out
""",
        "options": """A. Return out[:-1] at the end.
B. Change range(0, len(items) - k) to range(1, len(items) - k).
C. Change range(0, len(items) - k) to range(0, len(items) - k + 1).
D. Change out.append(items[i:i+k]) to out.append(items[i:i+k+1]).""",
        "extra_context": "Regression check: windows([1, 2, 3], 2) must return [[1, 2], [2, 3]].",
        "answer": "C",
    },
    {
        "instance_id": "ctx_mutable_default",
        "repo": "controlled/context",
        "risk_tier": "low",
        "issue": "Repeated add_label calls leak labels from earlier calls.",
        "buggy_code": """def add_label(name, labels=[]):
    labels.append(name)
    return labels
""",
        "options": """A. Clear labels before appending name.
B. Use labels=None and create a new list inside the function when labels is None.
C. Return tuple(labels) instead of labels.
D. Replace append with labels = labels + [name] but keep labels=[].""",
        "extra_context": "Regression check: add_label('a') returns ['a']; a later add_label('b') returns ['b'].",
        "answer": "B",
    },
    {
        "instance_id": "ctx_cache_none",
        "repo": "controlled/context",
        "risk_tier": "medium",
        "issue": "Cached lookups repeat expensive work when the stored value is None or 0.",
        "buggy_code": """cache = {}

def get_or_load(key):
    value = cache.get(key)
    if not value:
        value = load(key)
        cache[key] = value
    return value
""",
        "options": """A. Replace the truthiness check with if key not in cache.
B. Replace cache.get(key) with cache[key] without a membership check.
C. Store only truthy values in the cache.
D. Return None whenever cache.get(key) is falsy.""",
        "extra_context": "Regression checks: cached None is a valid result and must not trigger a second load; cached 0 is also valid.",
        "answer": "A",
    },
    {
        "instance_id": "ctx_url_join",
        "repo": "controlled/context",
        "risk_tier": "low",
        "issue": "join_url('api/', '/users') returns 'api//users'.",
        "buggy_code": """def join_url(base, path):
    return base + "/" + path
""",
        "options": """A. Return base.rstrip('/') + '/' + path.lstrip('/').
B. Return base.lstrip('/') + '/' + path.rstrip('/').
C. Remove every slash from both strings before joining.
D. Return path + '/' + base.""",
        "extra_context": "Regression checks: join_url('https://x/', '/a') must keep 'https://'; only boundary slashes should be normalized.",
        "answer": "A",
    },
    {
        "instance_id": "ctx_date_range_semantics",
        "repo": "controlled/context",
        "risk_tier": "high",
        "issue": "The date range filter excludes records at one of the range boundaries.",
        "buggy_code": """def in_range(day, start, end):
    return start < day < end
""",
        "options": """A. Use start <= day <= end.
B. Use start < day <= end.
C. Use start <= day < end.
D. Keep both comparisons strict.""",
        "extra_context": "Regression checks: the product uses half-open windows. start is included; end is excluded. in_range(start, start, end) is True; in_range(end, start, end) is False.",
        "answer": "C",
    },
    {
        "instance_id": "ctx_duplicate_policy",
        "repo": "controlled/context",
        "risk_tier": "high",
        "issue": "The map builder keeps the wrong record when duplicate identifiers appear.",
        "buggy_code": """def build_map(rows):
    out = {}
    for row in rows:
        out.setdefault(row["id"], row)
    return out
""",
        "options": """A. Replace setdefault with out[row['id']] = row.
B. Sort rows by id before the loop.
C. Skip all duplicate identifiers.
D. Return a list of rows instead of a dictionary.""",
        "extra_context": "Regression checks: later rows are corrections and must override earlier rows with the same id.",
        "answer": "A",
    },
    {
        "instance_id": "ctx_zero_override",
        "repo": "controlled/context",
        "risk_tier": "high",
        "issue": "The timeout resolver ignores an explicit zero timeout.",
        "buggy_code": """def timeout(config, default=30):
    return config.get("timeout") or default
""",
        "options": """A. Return default whenever timeout is falsy.
B. Return config['timeout'] if 'timeout' in config else default.
C. Return max(config.get('timeout', default), default).
D. Convert timeout to a string before returning it.""",
        "extra_context": "Regression checks: timeout({'timeout': 0}) must return 0 because zero disables waiting; missing timeout returns the default.",
        "answer": "B",
    },
    {
        "instance_id": "ctx_retry_policy",
        "repo": "controlled/context",
        "risk_tier": "high",
        "issue": "The retry helper retries too broadly after permanent failures.",
        "buggy_code": """def should_retry(error, attempts, max_attempts):
    return attempts < max_attempts
""",
        "options": """A. Retry only TimeoutError and ConnectionError while attempts < max_attempts.
B. Retry any Exception while attempts < max_attempts.
C. Retry only ValueError while attempts < max_attempts.
D. Never retry when attempts is zero.""",
        "extra_context": "Regression checks: TimeoutError and ConnectionError are transient; ValueError is permanent and must not be retried.",
        "answer": "A",
    },
    {
        "instance_id": "ctx_stable_topk",
        "repo": "controlled/context",
        "risk_tier": "high",
        "issue": "The ranking function returns the wrong order for tied scores.",
        "buggy_code": """def top_items(items, k):
    return sorted(items, key=lambda item: item["score"], reverse=True)[:k]
""",
        "options": """A. Sort by (-score, id) before slicing.
B. Sort by score ascending before slicing.
C. Preserve input order among equal scores while sorting by score descending.
D. Convert scores to strings before sorting.""",
        "extra_context": "Regression checks: if two items have the same score, their original input order is the business-defined tie breaker.",
        "answer": "C",
    },
    {
        "instance_id": "ctx_timezone_order",
        "repo": "controlled/context",
        "risk_tier": "high",
        "issue": "Events are sometimes ordered incorrectly by timestamp.",
        "buggy_code": """def sort_events(events):
    return sorted(events, key=lambda event: event["timestamp"])
""",
        "options": """A. Parse timestamps as timezone-aware datetimes before sorting.
B. Sort timestamp strings in reverse order.
C. Strip punctuation from timestamp strings before sorting.
D. Sort by event title instead of timestamp.""",
        "extra_context": "Regression checks: timestamps include offsets such as 2025-01-01T09:00:00+02:00 and 2025-01-01T08:30:00+00:00; chronological UTC order is required.",
        "answer": "A",
    },
    {
        "instance_id": "ctx_dedup_unhashable",
        "repo": "controlled/context",
        "risk_tier": "medium",
        "issue": "The unique helper must preserve first-seen order.",
        "buggy_code": """def unique(items):
    return list(set(items))
""",
        "options": """A. Return sorted(set(items)).
B. Track seen values with a set and append unseen items.
C. Append an item only if no previous item compares equal to it.
D. Reverse the input before calling set().""",
        "extra_context": "Regression checks: items can be dictionaries, so the fix must handle unhashable values while preserving first-seen order.",
        "answer": "C",
    },
    {
        "instance_id": "ctx_flag_defaults",
        "repo": "controlled/context",
        "risk_tier": "high",
        "issue": "The feature flag reader silently disables flags when the config contains an unknown value.",
        "buggy_code": """def flag_enabled(value):
    return str(value).lower() in {"1", "true", "yes"}
""",
        "options": """A. Treat unknown values as False.
B. Raise ValueError for unknown string values after accepting known true and false forms.
C. Treat any non-empty string as True.
D. Return None for every string value.""",
        "extra_context": "Regression checks: 'true', '1', and 'yes' are true; 'false', '0', and 'no' are false; strings such as 'maybe' must raise an error instead of silently disabling the flag.",
        "answer": "B",
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
    label: str,
    reasoning_effort: str,
) -> CallRecord:
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.0,
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
            choice_match = re.search(r'"choice"\s*:\s*"([ABCD])"', stripped, flags=re.IGNORECASE)
            final_choice_match = re.search(r'"final_choice"\s*:\s*"([ABCD])"', stripped, flags=re.IGNORECASE)
            if final_choice_match:
                return {"final_choice": final_choice_match.group(1).upper(), "raw_response": text}
            if choice_match:
                return {"choice": choice_match.group(1).upper(), "raw_response": text}
            return {}
        return parsed if isinstance(parsed, dict) else {}


def normalize_choice(value: Any) -> str:
    text = str(value or "").strip().upper()
    match = re.search(r"\b([ABCD])\b", text)
    return match.group(1) if match else ""


def minimal_context(task: dict[str, str]) -> str:
    return f"""Issue:
{task['issue']}

Buggy code:
{task['buggy_code']}

Candidate patches:
{task['options']}
"""


def full_context(task: dict[str, str]) -> str:
    return f"""{minimal_context(task)}

Additional regression tests and operational constraints:
{task['extra_context']}
"""


def json_messages(system: str, user: str) -> list[dict[str, str]]:
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def usage_totals(calls: list[CallRecord]) -> dict[str, float]:
    return {
        "model_calls": float(len(calls)),
        "prompt_tokens": float(sum(call.prompt_tokens for call in calls)),
        "completion_tokens": float(sum(call.completion_tokens for call in calls)),
        "total_tokens": float(sum(call.total_tokens for call in calls)),
        "latency_seconds": float(sum(call.latency_seconds for call in calls)),
    }


def run_direct_low(task: dict[str, str], args: argparse.Namespace, model: str, controller: str = "direct_low") -> tuple[dict[str, Any], list[dict[str, Any]]]:
    calls: list[CallRecord] = []
    logs: list[dict[str, Any]] = []
    try:
        prompt = f"""Choose the best patch using only the low-context issue view.

{minimal_context(task)}

Return JSON with keys: choice, confidence, reason."""
        call = call_lmstudio(
            args.lmstudio_base_url,
            model,
            json_messages("You are a one-pass low-context code triage agent. Return compact JSON only.", prompt),
            args.timeout,
            260,
            "direct_low_answer",
            args.reasoning_effort,
        )
        calls.append(call)
        answer = parse_json_object(call.response_text)
        choice = normalize_choice(answer.get("choice"))
        notes = json.dumps({"answer": answer}, ensure_ascii=False)
    except (RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        choice = ""
        notes = f"direct_low failed: {exc}"
    row = result_row(task, controller, choice, usage_totals(calls), context="minimal")
    row.update({"read_count": 1, "patch_attempts": 1, "patch_apply_successes": row["success"], "route": "minimal_context", "notes": notes})
    logs.extend(call_log(task, controller, call) for call in calls)
    return row, logs


def run_standard_full(task: dict[str, str], args: argparse.Namespace, model: str, controller: str = "standard_full") -> tuple[dict[str, Any], list[dict[str, Any]]]:
    calls: list[CallRecord] = []
    logs: list[dict[str, Any]] = []
    try:
        system = "You are a full-context multi-step code triage agent. Return compact JSON only."
        diagnosis_prompt = f"""Diagnose the likely bug using the full issue, code, candidates, and regression constraints.

{full_context(task)}

Return JSON with keys: diagnosis, likely_choice, uncertainty."""
        call = call_lmstudio(args.lmstudio_base_url, model, json_messages(system, diagnosis_prompt), args.timeout, 420, "standard_diagnosis", args.reasoning_effort)
        calls.append(call)
        diagnosis = parse_json_object(call.response_text)

        decision_prompt = f"""Choose the best candidate patch.

Diagnosis JSON:
{json.dumps(diagnosis, ensure_ascii=False)}

{full_context(task)}

Return JSON with keys: choice, confidence, reason."""
        call = call_lmstudio(args.lmstudio_base_url, model, json_messages(system, decision_prompt), args.timeout, 320, "standard_decision", args.reasoning_effort)
        calls.append(call)
        decision = parse_json_object(call.response_text)

        verify_prompt = f"""Verify the proposed candidate against every regression constraint.

Proposed choice JSON:
{json.dumps(decision, ensure_ascii=False)}

{full_context(task)}

Return JSON with keys: final_choice, changed, verification_note."""
        call = call_lmstudio(args.lmstudio_base_url, model, json_messages(system, verify_prompt), args.timeout, 320, "standard_verify", args.reasoning_effort)
        calls.append(call)
        verify = parse_json_object(call.response_text)

        choice = normalize_choice(verify.get("final_choice")) or normalize_choice(decision.get("choice")) or normalize_choice(diagnosis.get("likely_choice"))
        notes = json.dumps({"diagnosis": diagnosis, "decision": decision, "verify": verify}, ensure_ascii=False)
    except (RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        choice = ""
        notes = f"standard_full failed: {exc}"
    row = result_row(task, controller, choice, usage_totals(calls), context="full")
    row.update(
        {
            "test_runs": 1,
            "verification_events": 1,
            "search_count": 1,
            "read_count": 3,
            "patch_attempts": 1,
            "patch_apply_successes": row["success"],
            "route": "full_context",
            "notes": notes,
        }
    )
    logs.extend(call_log(task, controller, call) for call in calls)
    return row, logs


def run_context_gate(task: dict[str, str], args: argparse.Namespace, model: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if task["risk_tier"] == "low":
        row, logs = run_direct_low(task, args, model, controller="context_gate")
        row["route"] = "gate_minimal_context"
        return row, logs
    row, logs = run_standard_full(task, args, model, controller="context_gate")
    row["fallback_events"] = 1
    row["route"] = "gate_full_context"
    return row, logs


def result_row(task: dict[str, str], controller: str, choice: str, totals: dict[str, float], context: str) -> dict[str, Any]:
    expected = task["answer"]
    success = int(choice == expected)
    context_text = full_context(task) if context == "full" else minimal_context(task)
    return {
        "run_id": "lmstudio_context_gate_challenge",
        "instance_id": task["instance_id"],
        "repo": task["repo"],
        "controller": controller,
        "execution_mode": "lmstudio_context_budget_challenge",
        "execute_status": "completed",
        "success": success,
        "final_target_test_pass": success,
        "catastrophic_failure": int(not choice),
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
        "context_bytes": len(context_text.encode("utf-8")),
        "files_changed": 0,
        "lines_changed": 0,
        "failed_verification_jobs": 0,
        "recovery_attempts": 0,
        "expected_choice": expected,
        "predicted_choice": choice,
        "route": "",
        "workload_risk": task["risk_tier"],
        "quality_risk": "low" if success else "high",
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


def write_report(path: Path, rows: list[dict[str, Any]], model: str, result_path: Path, calls_path: Path) -> None:
    by_controller: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_controller.setdefault(str(row["controller"]), []).append(row)
    lines = [
        "# LM Studio Context-Gate Challenge Pilot",
        "",
        "This pilot tests whether a zero-call metadata gate can decide when to buy additional context.",
        "Low-context controllers see only issue/code/options; full-context controllers also see regression constraints.",
        "",
        f"- Model: `{model}`",
        f"- Tasks: {len({row['instance_id'] for row in rows})}",
        f"- Result CSV: `{result_path}`",
        f"- Call log: `{calls_path}`",
        "",
        "## Controller Summary",
        "",
        "| controller | n | success_rate | mean_calls | mean_total_tokens | mean_latency_s |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for controller, items in sorted(by_controller.items()):
        lines.append(
            f"| {controller} | {len(items)} | {mean([float(row['success']) for row in items]):.3f} | "
            f"{mean([float(row['model_calls']) for row in items]):.2f} | {mean([float(row['total_tokens']) for row in items]):.1f} | "
            f"{mean([float(row['latency_seconds']) for row in items]):.2f} |"
        )
    lines.extend(["", "## Boundary", "", "- This is a controlled context-budget pilot, not repository-level patch execution.", "- It is useful only if the context gate is not dominated by direct_low."])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def selected_tasks(limit: int) -> list[dict[str, str]]:
    return TASKS if limit <= 0 else TASKS[: min(limit, len(TASKS))]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a context-budgeted paired runtime challenge against LM Studio.")
    parser.add_argument("--lmstudio-base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--model", default="")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--max-tasks", type=int, default=12)
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--reasoning-effort", default="none")
    parser.add_argument("--progress-every", type=int, default=3)
    args = parser.parse_args()

    output_dir = ensure_dir(args.output_dir)
    model = args.model or discover_model(args.lmstudio_base_url, args.timeout)
    tasks = selected_tasks(args.max_tasks)
    rows: list[dict[str, Any]] = []
    logs: list[dict[str, Any]] = []
    controllers = ["direct_low", "standard_full", "context_gate"]
    total = len(tasks) * len(controllers)
    completed = 0

    for task in tasks:
        for controller in controllers:
            if controller == "direct_low":
                row, call_rows = run_direct_low(task, args, model)
            elif controller == "standard_full":
                row, call_rows = run_standard_full(task, args, model)
            else:
                row, call_rows = run_context_gate(task, args, model)
            rows.append(row)
            logs.extend(call_rows)
            completed += 1
            if args.progress_every > 0 and (completed == 1 or completed % args.progress_every == 0 or completed == total):
                print(
                    f"[context-gate] {completed}/{total} {task['instance_id']}::{controller} "
                    f"route={row['route']} choice={row['predicted_choice']} expected={row['expected_choice']} "
                    f"success={row['success']} tokens={row['total_tokens']}",
                    flush=True,
                )

    result_path = output_dir / "runtime_task_results.csv"
    calls_path = output_dir / "runtime_call_log.jsonl"
    report_path = output_dir / "runtime_context_gate_report.md"
    summary_path = output_dir / "runtime_context_gate_summary.json"
    write_csv(result_path, rows, RESULT_COLUMNS)
    write_jsonl(calls_path, logs)
    write_report(report_path, rows, model, result_path, calls_path)
    summary_path.write_text(
        json.dumps(
            {
                "model": model,
                "tasks": len(tasks),
                "rows": len(rows),
                "risk_tier_counts": {tier: sum(1 for task in tasks if task["risk_tier"] == tier) for tier in ["low", "medium", "high"]},
                "result_csv": str(result_path),
                "report_md": str(report_path),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Wrote context-gate task results to {result_path}")
    print(f"Wrote context-gate report to {report_path}")


if __name__ == "__main__":
    main()
