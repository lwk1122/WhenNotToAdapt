from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from .run_lmstudio_executable_context_gate import (
    RESULT_COLUMNS,
    discover_model,
    ensure_dir,
    run_direct_low,
    run_standard_full,
    task,
    write_jsonl,
)


DEFAULT_OUTPUT_DIR = Path("exp/results/emse_runtime/lmstudio_executable_context_gate_extra_v1")


EXTRA_TASKS: list[dict[str, Any]] = [
    task(
        "exec_extra_strip_case",
        "low",
        "Identifier normalization should ignore surrounding spaces and letter case.",
        "def solve(value):\n    return value",
        {
            "A": "def solve(value):\n    return value.strip().lower()",
            "B": "def solve(value):\n    return value.lower()",
            "C": "def solve(value):\n    return value.strip()",
            "D": "def solve(value):\n    return value.upper()",
        },
        "assert solve('  ABC ') == 'abc'\nassert solve('xYz') == 'xyz'",
        "A",
    ),
    task(
        "exec_extra_tail_value",
        "low",
        "The helper returns the first value when callers need the last value.",
        "def solve(values):\n    return values[0]",
        {
            "A": "def solve(values):\n    return values[-1]",
            "B": "def solve(values):\n    return values[1]",
            "C": "def solve(values):\n    return values[0]",
            "D": "def solve(values):\n    return None",
        },
        "assert solve([1, 2, 3]) == 3\nassert solve(['a']) == 'a'",
        "A",
    ),
    task(
        "exec_extra_drop_empty_parts",
        "low",
        "Comma splitting should remove empty fields created by repeated commas.",
        "def solve(text):\n    return text.split(',')",
        {
            "A": "def solve(text):\n    return [part for part in text.split(',') if part]",
            "B": "def solve(text):\n    return text.split(';')",
            "C": "def solve(text):\n    return [text]",
            "D": "def solve(text):\n    return []",
        },
        "assert solve('a,,b,') == ['a', 'b']\nassert solve('x') == ['x']",
        "A",
    ),
    task(
        "exec_extra_abs_error",
        "low",
        "The error metric should be absolute instead of signed.",
        "def solve(actual, expected):\n    return actual - expected",
        {
            "A": "def solve(actual, expected):\n    return abs(actual - expected)",
            "B": "def solve(actual, expected):\n    return expected - actual",
            "C": "def solve(actual, expected):\n    return actual + expected",
            "D": "def solve(actual, expected):\n    return 0",
        },
        "assert solve(3, 5) == 2\nassert solve(8, 5) == 3",
        "A",
    ),
    task(
        "exec_extra_keep_positive",
        "low",
        "The filter should keep positive values only.",
        "def solve(values):\n    return [v for v in values if v >= 0]",
        {
            "A": "def solve(values):\n    return [v for v in values if v > 0]",
            "B": "def solve(values):\n    return [v for v in values if v < 0]",
            "C": "def solve(values):\n    return values",
            "D": "def solve(values):\n    return []",
        },
        "assert solve([-1, 0, 2, 3]) == [2, 3]\nassert solve([0]) == []",
        "A",
    ),
    task(
        "exec_extra_cap_length",
        "low",
        "The list truncation helper should cap output length at k.",
        "def solve(values, k):\n    return values",
        {
            "A": "def solve(values, k):\n    return values[:k]",
            "B": "def solve(values, k):\n    return values[k:]",
            "C": "def solve(values, k):\n    return values[:-k]",
            "D": "def solve(values, k):\n    return []",
        },
        "assert solve([1, 2, 3], 2) == [1, 2]\nassert solve([1], 5) == [1]",
        "A",
    ),
    task(
        "exec_extra_missing_default",
        "low",
        "Missing dictionary keys should return the provided default value.",
        "def solve(mapping, key, default=None):\n    return mapping[key]",
        {
            "A": "def solve(mapping, key, default=None):\n    return mapping.get(key, default)",
            "B": "def solve(mapping, key, default=None):\n    return default",
            "C": "def solve(mapping, key, default=None):\n    return mapping[key]",
            "D": "def solve(mapping, key, default=None):\n    return None",
        },
        "assert solve({'a': 1}, 'a', 0) == 1\nassert solve({}, 'a', 0) == 0",
        "A",
    ),
    task(
        "exec_extra_reverse_flag",
        "low",
        "The sort helper should return values in descending order.",
        "def solve(values):\n    return sorted(values)",
        {
            "A": "def solve(values):\n    return sorted(values, reverse=True)",
            "B": "def solve(values):\n    return list(reversed(values))",
            "C": "def solve(values):\n    return sorted(values)",
            "D": "def solve(values):\n    return values",
        },
        "assert solve([2, 3, 1]) == [3, 2, 1]",
        "A",
    ),
    task(
        "exec_extra_nullable_cache",
        "medium",
        "Cache hits are not recognized for some stored values.",
        """
        cache = {}
        def solve(key, loader):
            if cache.get(key):
                return cache[key]
            cache[key] = loader(key)
            return cache[key]
        """,
        {
            "A": "cache = {}\ndef solve(key, loader):\n    if key in cache:\n        return cache[key]\n    cache[key] = loader(key)\n    return cache[key]",
            "B": "cache = {}\ndef solve(key, loader):\n    cache[key] = loader(key)\n    return cache[key]",
            "C": "cache = {}\ndef solve(key, loader):\n    return cache.get(key)",
            "D": "cache = {}\ndef solve(key, loader):\n    return loader(key)",
        },
        """
        calls = []
        def loader(key):
            calls.append(key)
            return None
        assert solve('x', loader) is None
        assert solve('x', loader) is None
        assert calls == ['x']
        """,
        "A",
    ),
    task(
        "exec_extra_one_level_merge",
        "medium",
        "Configuration merging drops nested defaults.",
        "def solve(defaults, user):\n    out = dict(defaults)\n    out.update(user)\n    return out",
        {
            "A": "def solve(defaults, user):\n    out = dict(defaults)\n    for key, value in user.items():\n        if isinstance(value, dict) and isinstance(out.get(key), dict):\n            merged = dict(out[key]); merged.update(value); out[key] = merged\n        else:\n            out[key] = value\n    return out",
            "B": "def solve(defaults, user):\n    return user",
            "C": "def solve(defaults, user):\n    return defaults",
            "D": "def solve(defaults, user):\n    defaults.update(user); return defaults",
        },
        "assert solve({'db': {'host': 'h', 'port': 1}}, {'db': {'port': 2}}) == {'db': {'host': 'h', 'port': 2}}",
        "A",
    ),
    task(
        "exec_extra_email_quoted",
        "medium",
        "Email domain extraction fails for valid quoted local parts.",
        "def solve(email):\n    return email.split('@')[1].lower()",
        {
            "A": "def solve(email):\n    return email.rsplit('@', 1)[1].lower()",
            "B": "def solve(email):\n    return email.split('@')[0].lower()",
            "C": "def solve(email):\n    return email.split('@')[-2].lower()",
            "D": "def solve(email):\n    return email.lower()",
        },
        "assert solve('a@example.com') == 'example.com'\nassert solve('\"a@b\"@Example.org') == 'example.org'",
        "A",
    ),
    task(
        "exec_extra_slug_unicode",
        "medium",
        "Slug generation leaves punctuation and repeated separators.",
        "def solve(text):\n    return text.strip().lower().replace(' ', '-')",
        {
            "A": "import re\ndef solve(text):\n    return re.sub(r'-+', '-', re.sub(r'[^a-z0-9]+', '-', text.strip().lower())).strip('-')",
            "B": "def solve(text):\n    return text.lower()",
            "C": "def solve(text):\n    return text.replace(' ', '')",
            "D": "def solve(text):\n    return text.strip()",
        },
        "assert solve(' Hello,   World!! ') == 'hello-world'\nassert solve('A--B') == 'a-b'",
        "A",
    ),
    task(
        "exec_extra_flatten_depth",
        "medium",
        "The flatten helper uses the wrong nesting depth.",
        "def solve(values):\n    out = []\n    for value in values:\n        if isinstance(value, list):\n            out.extend(solve(value))\n        else:\n            out.append(value)\n    return out",
        {
            "A": "def solve(values):\n    out = []\n    for value in values:\n        if isinstance(value, list): out.extend(value)\n        else: out.append(value)\n    return out",
            "B": "def solve(values):\n    return values",
            "C": "def solve(values):\n    return [x for row in values for x in row]",
            "D": "def solve(values):\n    return []",
        },
        "assert solve([1, [2, [3]], 4]) == [1, 2, [3], 4]",
        "A",
    ),
    task(
        "exec_extra_running_mean",
        "medium",
        "Running averages are rounded down.",
        "def solve(values):\n    total = 0\n    out = []\n    for i, value in enumerate(values, 1):\n        total += value\n        out.append(total // i)\n    return out",
        {
            "A": "def solve(values):\n    total = 0; out = []\n    for i, value in enumerate(values, 1):\n        total += value; out.append(total / i)\n    return out",
            "B": "def solve(values):\n    return [sum(values) / len(values)]",
            "C": "def solve(values):\n    return values",
            "D": "def solve(values):\n    return []",
        },
        "assert solve([1, 2]) == [1.0, 1.5]\nassert solve([2, 4, 6]) == [2.0, 3.0, 4.0]",
        "A",
    ),
    task(
        "exec_extra_unhashable_unique",
        "medium",
        "The unique helper should preserve first occurrence order.",
        "def solve(values):\n    return list(set(values))",
        {
            "A": "def solve(values):\n    out = []\n    for value in values:\n        if not any(value == old for old in out):\n            out.append(value)\n    return out",
            "B": "def solve(values):\n    return sorted(set(values))",
            "C": "def solve(values):\n    return values[::-1]",
            "D": "def solve(values):\n    return []",
        },
        "assert solve([3, 1, 3, 2]) == [3, 1, 2]\nassert solve([{'x': 1}, {'x': 1}]) == [{'x': 1}]",
        "A",
    ),
    task(
        "exec_extra_whitespace_all",
        "medium",
        "Whitespace normalization misses tabs and repeated spaces.",
        "def solve(text):\n    return text.strip().replace('  ', ' ')",
        {
            "A": "def solve(text):\n    return ' '.join(text.split())",
            "B": "def solve(text):\n    return text.replace(' ', '')",
            "C": "def solve(text):\n    return text.strip()",
            "D": "def solve(text):\n    return text",
        },
        "assert solve(' a   b\\tc ') == 'a b c'",
        "A",
    ),
    task(
        "exec_extra_half_open_interval",
        "high",
        "The interval predicate uses the wrong endpoint convention.",
        "def solve(x, start, end):\n    return start < x < end",
        {
            "A": "def solve(x, start, end):\n    return start <= x < end",
            "B": "def solve(x, start, end):\n    return start < x <= end",
            "C": "def solve(x, start, end):\n    return start <= x <= end",
            "D": "def solve(x, start, end):\n    return start < x < end",
        },
        "assert solve(10, 10, 20) is True\nassert solve(20, 10, 20) is False\nassert solve(15, 10, 20) is True",
        "A",
    ),
    task(
        "exec_extra_one_based_page",
        "high",
        "Pagination returns the wrong page slice.",
        "def solve(items, page, size):\n    start = page * size\n    return items[start:start + size]",
        {
            "A": "def solve(items, page, size):\n    start = (page - 1) * size\n    return items[start:start + size]",
            "B": "def solve(items, page, size):\n    start = page * size\n    return items[start:start + size]",
            "C": "def solve(items, page, size):\n    return items[:size]",
            "D": "def solve(items, page, size):\n    return items[-size:]",
        },
        "assert solve([1, 2, 3, 4, 5], 1, 2) == [1, 2]\nassert solve([1, 2, 3, 4, 5], 2, 2) == [3, 4]",
        "A",
    ),
    task(
        "exec_extra_deny_overrides",
        "high",
        "Permission resolution returns the wrong result when rules conflict.",
        "def solve(rules):\n    return any(rule == 'allow' for rule in rules)",
        {
            "A": "def solve(rules):\n    return False if 'deny' in rules else any(rule == 'allow' for rule in rules)",
            "B": "def solve(rules):\n    return any(rule == 'allow' for rule in rules)",
            "C": "def solve(rules):\n    return rules[-1] == 'allow'",
            "D": "def solve(rules):\n    return True",
        },
        "assert solve(['allow']) is True\nassert solve(['allow', 'deny']) is False\nassert solve([]) is False",
        "A",
    ),
    task(
        "exec_extra_status_order",
        "high",
        "Status sorting uses alphabetical order instead of the workflow order.",
        "def solve(values):\n    return sorted(values)",
        {
            "A": "def solve(values):\n    order = {'new': 0, 'active': 1, 'blocked': 2, 'done': 3}\n    return sorted(values, key=lambda value: order[value])",
            "B": "def solve(values):\n    return sorted(values)",
            "C": "def solve(values):\n    return list(reversed(values))",
            "D": "def solve(values):\n    return values",
        },
        "assert solve(['done', 'new', 'blocked', 'active']) == ['new', 'active', 'blocked', 'done']",
        "A",
    ),
    task(
        "exec_extra_timezone_compare",
        "high",
        "Timestamp ordering is wrong for offset-aware timestamps.",
        "def solve(events):\n    return sorted(events, key=lambda event: event['timestamp'])",
        {
            "A": "from datetime import datetime\ndef solve(events):\n    return sorted(events, key=lambda event: datetime.fromisoformat(event['timestamp']))",
            "B": "def solve(events):\n    return sorted(events, key=lambda event: event['timestamp'], reverse=True)",
            "C": "def solve(events):\n    return sorted(events, key=lambda event: event['title'])",
            "D": "def solve(events):\n    return events",
        },
        "events = [{'title': 'a', 'timestamp': '2025-01-01T09:00:00+02:00'}, {'title': 'b', 'timestamp': '2025-01-01T08:30:00+00:00'}]\nassert [event['title'] for event in solve(events)] == ['a', 'b']",
        "A",
    ),
    task(
        "exec_extra_version_policy",
        "high",
        "Version ordering is wrong for multi-digit version parts.",
        "def solve(values):\n    return sorted(values)",
        {
            "A": "def solve(values):\n    return sorted(values, key=lambda text: [int(part) for part in text.split('.')])",
            "B": "def solve(values):\n    return sorted(values)",
            "C": "def solve(values):\n    return sorted(values, key=len)",
            "D": "def solve(values):\n    return values",
        },
        "assert solve(['1.10', '1.2', '1.0']) == ['1.0', '1.2', '1.10']",
        "A",
    ),
    task(
        "exec_extra_unknown_flag",
        "high",
        "Feature flag parsing handles unsupported text incorrectly.",
        "def solve(value):\n    return str(value).strip().lower() in {'1', 'true', 'yes'}",
        {
            "A": "def solve(value):\n    text = str(value).strip().lower()\n    if text in {'1', 'true', 'yes'}: return True\n    if text in {'0', 'false', 'no'}: return False\n    raise ValueError(text)",
            "B": "def solve(value):\n    return bool(value)",
            "C": "def solve(value):\n    return str(value).strip().lower() in {'1', 'true', 'yes'}",
            "D": "def solve(value):\n    return None",
        },
        "assert solve('yes') is True\nassert solve('no') is False\ntry:\n    solve('maybe')\nexcept ValueError:\n    pass\nelse:\n    raise AssertionError('unknown flag must raise')",
        "A",
    ),
    task(
        "exec_extra_zero_policy",
        "high",
        "The resolver treats an explicit zero like a missing value.",
        "def solve(config, default=30):\n    return config.get('timeout') or default",
        {
            "A": "def solve(config, default=30):\n    return config['timeout'] if 'timeout' in config else default",
            "B": "def solve(config, default=30):\n    return config.get('timeout') or default",
            "C": "def solve(config, default=30):\n    return max(config.get('timeout', default), default)",
            "D": "def solve(config, default=30):\n    return default",
        },
        "assert solve({'timeout': 0}) == 0\nassert solve({'timeout': 5}) == 5\nassert solve({}) == 30",
        "A",
    ),
    task(
        "exec_extra_rounding_policy",
        "high",
        "Currency rounding uses the wrong half-value policy.",
        "def solve(cents):\n    return round(cents / 100, 2)",
        {
            "A": "from decimal import Decimal, ROUND_HALF_UP\ndef solve(cents):\n    return float((Decimal(cents) / Decimal(100)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))",
            "B": "def solve(cents):\n    return round(cents / 100, 2)",
            "C": "def solve(cents):\n    return int(cents / 100)",
            "D": "def solve(cents):\n    return cents / 100",
        },
        "assert solve(105) == 1.05\nassert solve(125) == 1.25",
        "A",
    ),
    task(
        "exec_extra_last_write_wins",
        "high",
        "Duplicate record handling keeps the wrong update.",
        "def solve(rows):\n    out = {}\n    for row in rows:\n        out.setdefault(row['id'], row)\n    return out",
        {
            "A": "def solve(rows):\n    out = {}\n    for row in rows:\n        out[row['id']] = row\n    return out",
            "B": "def solve(rows):\n    return {row['id']: row for row in reversed(rows)}",
            "C": "def solve(rows):\n    return rows",
            "D": "def solve(rows):\n    out = {}\n    for row in rows:\n        out.setdefault(row['id'], row)\n    return out",
        },
        "rows = [{'id': 1, 'v': 'old'}, {'id': 1, 'v': 'new'}]\nassert solve(rows)[1]['v'] == 'new'",
        "A",
    ),
    task(
        "exec_extra_percent_zero",
        "high",
        "Percent change has the wrong zero-baseline behavior.",
        "def solve(old, new):\n    return (new - old) / old",
        {
            "A": "def solve(old, new):\n    return 0 if old == 0 and new == 0 else float('inf') if old == 0 else (new - old) / old",
            "B": "def solve(old, new):\n    return new - old",
            "C": "def solve(old, new):\n    return (new - old) / new",
            "D": "def solve(old, new):\n    return 0",
        },
        "assert solve(10, 15) == 0.5\nassert solve(0, 0) == 0\nassert solve(0, 5) == float('inf')",
        "A",
    ),
    task(
        "exec_extra_minimum_floor",
        "low",
        "The score normalizer should never return a negative score.",
        "def solve(score):\n    return score",
        {
            "A": "def solve(score):\n    return max(score, 0)",
            "B": "def solve(score):\n    return min(score, 0)",
            "C": "def solve(score):\n    return abs(score)",
            "D": "def solve(score):\n    return score",
        },
        "assert solve(3) == 3\nassert solve(-2) == 0",
        "A",
    ),
    task(
        "exec_extra_empty_name_policy",
        "medium",
        "Display-name fallback handles empty user names incorrectly.",
        "def solve(user):\n    return user.get('name', 'Anonymous')",
        {
            "A": "def solve(user):\n    name = user.get('name')\n    return 'Anonymous' if name == '' else name if name is not None else 'Anonymous'",
            "B": "def solve(user):\n    return user.get('name', 'Anonymous')",
            "C": "def solve(user):\n    return user['name']",
            "D": "def solve(user):\n    return 'Anonymous'",
        },
        "assert solve({'name': 'Ada'}) == 'Ada'\nassert solve({'name': ''}) == 'Anonymous'\nassert solve({}) == 'Anonymous'",
        "A",
    ),
    task(
        "exec_extra_priority_order",
        "high",
        "Priority sorting uses the wrong severity order.",
        "def solve(items):\n    return sorted(items, key=lambda item: item['priority'])",
        {
            "A": "def solve(items):\n    order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}\n    return sorted(items, key=lambda item: order[item['priority']])",
            "B": "def solve(items):\n    return sorted(items, key=lambda item: item['priority'])",
            "C": "def solve(items):\n    return list(reversed(items))",
            "D": "def solve(items):\n    return items",
        },
        "items = [{'priority': 'low'}, {'priority': 'critical'}, {'priority': 'medium'}]\nassert [item['priority'] for item in solve(items)] == ['critical', 'medium', 'low']",
        "A",
    ),
]


def selected_tasks(limit: int) -> list[dict[str, Any]]:
    return EXTRA_TASKS if limit <= 0 else EXTRA_TASKS[: min(limit, len(EXTRA_TASKS))]


def derive_gate_rows(rows: list[dict[str, Any]], tasks: list[dict[str, Any]], policy: str) -> list[dict[str, Any]]:
    by_task: dict[str, dict[str, dict[str, Any]]] = {}
    for row in rows:
        by_task.setdefault(str(row["instance_id"]), {})[str(row["controller"])] = row
    derived: list[dict[str, Any]] = []
    for current in tasks:
        if current["instance_id"] not in by_task:
            continue
        use_full = current["risk_tier"] == "high" if policy == "high_only" else current["risk_tier"] in {"medium", "high"}
        source_name = "standard_full" if use_full else "direct_low"
        source = dict(by_task[current["instance_id"]][source_name])
        source["controller"] = f"context_gate_{policy}"
        source["route"] = "gate_full_context" if use_full else "gate_minimal_context"
        source["fallback_events"] = 1 if use_full else 0
        source["notes"] = json.dumps(
            {"derived_from": source_name, "policy": policy, "original_notes": source.get("notes", "")},
            ensure_ascii=False,
        )
        derived.append(source)
    return derived


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    ensure_dir(path.parent)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({col: row.get(col, "") for col in columns})


def mean(values: list[float]) -> float:
    return float(sum(values) / len(values)) if values else float("nan")


def write_report(path: Path, rows: list[dict[str, Any]], model: str, result_path: Path, calls_path: Path) -> None:
    by_controller: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_controller.setdefault(str(row["controller"]), []).append(row)
    lines = [
        "# LM Studio Executable Context-Gate Extra Wave",
        "",
        "The model chooses among static candidate replacement implementations. The selected implementation is executed against local Python tests.",
        "",
        f"- Model: `{model}`",
        f"- Extra tasks: {len({row['instance_id'] for row in rows})}",
        f"- Result CSV: `{result_path}`",
        f"- Call log: `{calls_path}`",
        "",
        "| controller | n | success_rate | mean_calls | mean_total_tokens | mean_latency_s |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for controller, items in sorted(by_controller.items()):
        lines.append(
            f"| {controller} | {len(items)} | {mean([float(row['success']) for row in items]):.3f} | "
            f"{mean([float(row['model_calls']) for row in items]):.2f} | "
            f"{mean([float(row['total_tokens']) for row in items]):.1f} | "
            f"{mean([float(row['latency_seconds']) for row in items]):.2f} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run extra executable context-gate tasks with LM Studio.")
    parser.add_argument("--lmstudio-base-url", default="http://127.0.0.1:1234/v1")
    parser.add_argument("--model", default="")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--max-tasks", type=int, default=30)
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--reasoning-effort", default="none")
    parser.add_argument("--progress-every", type=int, default=5)
    args = parser.parse_args()

    output_dir = ensure_dir(args.output_dir)
    model = args.model or discover_model(args.lmstudio_base_url, args.timeout)
    tasks = selected_tasks(args.max_tasks)
    rows: list[dict[str, Any]] = []
    logs: list[dict[str, Any]] = []
    total = len(tasks) * 2
    completed = 0
    for current in tasks:
        for controller in ["direct_low", "standard_full"]:
            if controller == "direct_low":
                row, call_rows = run_direct_low(current, args, model)
            else:
                row, call_rows = run_standard_full(current, args, model)
            rows.append(row)
            logs.extend(call_rows)
            completed += 1
            if args.progress_every > 0 and (completed == 1 or completed % args.progress_every == 0 or completed == total):
                print(
                    f"[exec-context-extra] {completed}/{total} {current['instance_id']}::{controller} "
                    f"choice={row['predicted_choice']} expected={row['expected_choice']} success={row['success']} "
                    f"tokens={row['total_tokens']}",
                    flush=True,
                )

    rows.extend(derive_gate_rows(rows, tasks, "medium_high"))
    rows.extend(derive_gate_rows(rows, tasks, "high_only"))

    result_path = output_dir / "runtime_task_results.csv"
    calls_path = output_dir / "runtime_call_log.jsonl"
    report_path = output_dir / "runtime_executable_context_gate_extra_report.md"
    summary_path = output_dir / "runtime_executable_context_gate_extra_summary.json"
    write_csv(result_path, rows, RESULT_COLUMNS)
    write_jsonl(calls_path, logs)
    write_report(report_path, rows, model, result_path, calls_path)
    summary_path.write_text(
        json.dumps(
            {
                "model": model,
                "tasks": len(tasks),
                "rows": len(rows),
                "risk_tier_counts": {tier: sum(1 for item in tasks if item["risk_tier"] == tier) for tier in ["low", "medium", "high"]},
                "result_csv": str(result_path),
                "report_md": str(report_path),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Wrote extra executable context-gate results to {result_path}")
    print(f"Wrote extra executable context-gate report to {report_path}")


if __name__ == "__main__":
    main()
