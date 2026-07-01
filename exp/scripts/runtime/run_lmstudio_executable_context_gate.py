from __future__ import annotations

import argparse
import csv
import json
import math
import re
import socket
import subprocess
import tempfile
import textwrap
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_BASE_URL = "http://127.0.0.1:1234/v1"
DEFAULT_OUTPUT_DIR = Path("exp/results/emse_runtime/lmstudio_executable_context_gate_v1")

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


def c(code: str) -> str:
    return textwrap.dedent(code).strip() + "\n"


def task(
    instance_id: str,
    risk_tier: str,
    issue: str,
    buggy_code: str,
    candidates: dict[str, str],
    tests: str,
    answer: str,
) -> dict[str, Any]:
    return {
        "instance_id": instance_id,
        "repo": "controlled/executable",
        "risk_tier": risk_tier,
        "issue": issue,
        "buggy_code": c(buggy_code),
        "candidates": {key: c(value) for key, value in candidates.items()},
        "tests": c(tests),
        "answer": answer,
    }


TASKS: list[dict[str, Any]] = [
    task(
        "exec_window_boundary",
        "low",
        "The window helper drops the final valid window.",
        """
        def solve(items, k):
            out = []
            for i in range(0, len(items) - k):
                out.append(items[i:i+k])
            return out
        """,
        {
            "A": "def solve(items, k):\n    return [items[i:i+k+1] for i in range(0, len(items) - k)]",
            "B": "def solve(items, k):\n    return [items[i:i+k] for i in range(1, len(items) - k)]",
            "C": "def solve(items, k):\n    return [items[i:i+k] for i in range(0, len(items) - k + 1)]",
            "D": "def solve(items, k):\n    return [] if k else [items]",
        },
        "assert solve([1, 2, 3], 2) == [[1, 2], [2, 3]]\nassert solve([1, 2], 2) == [[1, 2]]",
        "C",
    ),
    task(
        "exec_mutable_default",
        "low",
        "Repeated calls leak labels from earlier calls.",
        "def solve(name, labels=[]):\n    labels.append(name)\n    return labels",
        {
            "A": "def solve(name, labels=[]):\n    labels.clear()\n    labels.append(name)\n    return labels",
            "B": "def solve(name, labels=None):\n    if labels is None:\n        labels = []\n    labels.append(name)\n    return labels",
            "C": "def solve(name, labels=[]):\n    labels.append(name)\n    return tuple(labels)",
            "D": "def solve(name, labels=[]):\n    labels = labels + [name]\n    return labels",
        },
        "assert solve('a') == ['a']\nassert solve('b') == ['b']\nseed = ['x']\nassert solve('y', seed) == ['x', 'y']",
        "B",
    ),
    task(
        "exec_join_url",
        "low",
        "URL joining creates duplicate slashes at the boundary.",
        "def solve(base, path):\n    return base + '/' + path",
        {
            "A": "def solve(base, path):\n    return base.rstrip('/') + '/' + path.lstrip('/')",
            "B": "def solve(base, path):\n    return base.lstrip('/') + '/' + path.rstrip('/')",
            "C": "def solve(base, path):\n    return base.replace('/', '') + '/' + path.replace('/', '')",
            "D": "def solve(base, path):\n    return path + '/' + base",
        },
        "assert solve('api/', '/users') == 'api/users'\nassert solve('https://x/', '/a') == 'https://x/a'",
        "A",
    ),
    task(
        "exec_topk_order",
        "low",
        "top_k returns the smallest values instead of the largest values.",
        "def solve(scores, k):\n    return sorted(scores)[:k]",
        {
            "A": "def solve(scores, k):\n    return sorted(scores)[-k:]",
            "B": "def solve(scores, k):\n    return sorted(scores, reverse=True)[:k]",
            "C": "def solve(scores, k):\n    return scores[:k]",
            "D": "def solve(scores, k):\n    return [min(scores)]",
        },
        "assert solve([5, 1, 4], 2) == [5, 4]\nassert solve([1], 1) == [1]",
        "B",
    ),
    task(
        "exec_bool_parse",
        "low",
        "Boolean parsing treats non-empty strings such as 'false' as True.",
        "def solve(value):\n    return bool(value)",
        {
            "A": "def solve(value):\n    return value is not None",
            "B": "def solve(value):\n    return not bool(value)",
            "C": "def solve(value):\n    return str(value).strip().lower() in {'1', 'true', 'yes'}",
            "D": "def solve(value):\n    return bool(str(value))",
        },
        "assert solve('true') is True\nassert solve('false') is False\nassert solve(' yes ') is True\nassert solve('0') is False",
        "C",
    ),
    task(
        "exec_cache_falsy",
        "medium",
        "Cached lookups repeat expensive work when the stored result is falsy.",
        """
        cache = {}
        def solve(key, load):
            value = cache.get(key)
            if not value:
                value = load(key)
                cache[key] = value
            return value
        """,
        {
            "A": "cache = {}\ndef solve(key, load):\n    if key not in cache:\n        cache[key] = load(key)\n    return cache[key]",
            "B": "cache = {}\ndef solve(key, load):\n    return cache[key]",
            "C": "cache = {}\ndef solve(key, load):\n    value = load(key)\n    if value:\n        cache[key] = value\n    return value",
            "D": "cache = {}\ndef solve(key, load):\n    return None if not cache.get(key) else cache[key]",
        },
        """
        calls = []
        def load(key):
            calls.append(key)
            return 0
        assert solve('a', load) == 0
        assert solve('a', load) == 0
        assert calls == ['a']
        """,
        "A",
    ),
    task(
        "exec_date_half_open",
        "high",
        "The date range filter excludes records at one boundary.",
        "def solve(day, start, end):\n    return start < day < end",
        {
            "A": "def solve(day, start, end):\n    return start <= day <= end",
            "B": "def solve(day, start, end):\n    return start < day <= end",
            "C": "def solve(day, start, end):\n    return start <= day < end",
            "D": "def solve(day, start, end):\n    return start < day < end",
        },
        "assert solve(10, 10, 20) is True\nassert solve(20, 10, 20) is False\nassert solve(15, 10, 20) is True",
        "C",
    ),
    task(
        "exec_duplicate_last_wins",
        "high",
        "The map builder keeps the wrong duplicate record.",
        """
        def solve(rows):
            out = {}
            for row in rows:
                out.setdefault(row['id'], row)
            return out
        """,
        {
            "A": "def solve(rows):\n    out = {}\n    for row in rows:\n        out[row['id']] = row\n    return out",
            "B": "def solve(rows):\n    return {row['id']: row for row in sorted(rows, key=lambda r: r['id'])}",
            "C": "def solve(rows):\n    seen = set(); out = {}\n    for row in rows:\n        if row['id'] not in seen:\n            out[row['id']] = row; seen.add(row['id'])\n    return out",
            "D": "def solve(rows):\n    return rows",
        },
        "rows = [{'id': 1, 'v': 'old'}, {'id': 1, 'v': 'new'}]\nassert solve(rows)[1]['v'] == 'new'",
        "A",
    ),
    task(
        "exec_zero_override",
        "high",
        "The timeout resolver ignores an explicit zero timeout.",
        "def solve(config, default=30):\n    return config.get('timeout') or default",
        {
            "A": "def solve(config, default=30):\n    return config.get('timeout') or default",
            "B": "def solve(config, default=30):\n    return config['timeout'] if 'timeout' in config else default",
            "C": "def solve(config, default=30):\n    return max(config.get('timeout', default), default)",
            "D": "def solve(config, default=30):\n    return str(config.get('timeout', default))",
        },
        "assert solve({'timeout': 0}) == 0\nassert solve({}) == 30\nassert solve({'timeout': 5}) == 5",
        "B",
    ),
    task(
        "exec_retry_transient",
        "high",
        "The retry helper retries permanent failures too broadly.",
        "def solve(error, attempts, max_attempts):\n    return attempts < max_attempts",
        {
            "A": "def solve(error, attempts, max_attempts):\n    return isinstance(error, (TimeoutError, ConnectionError)) and attempts < max_attempts",
            "B": "def solve(error, attempts, max_attempts):\n    return isinstance(error, Exception) and attempts < max_attempts",
            "C": "def solve(error, attempts, max_attempts):\n    return isinstance(error, ValueError) and attempts < max_attempts",
            "D": "def solve(error, attempts, max_attempts):\n    return attempts == 0",
        },
        "assert solve(TimeoutError(), 0, 3) is True\nassert solve(ConnectionError(), 1, 3) is True\nassert solve(ValueError(), 0, 3) is False\nassert solve(TimeoutError(), 3, 3) is False",
        "A",
    ),
    task(
        "exec_stable_topk",
        "high",
        "The ranking function returns the wrong order for tied scores.",
        "def solve(items, k):\n    return sorted(items, key=lambda item: item['score'], reverse=True)[:k]",
        {
            "A": "def solve(items, k):\n    return sorted(items, key=lambda item: (-item['score'], item['id']))[:k]",
            "B": "def solve(items, k):\n    return sorted(items, key=lambda item: item['score'])[:k]",
            "C": "def solve(items, k):\n    return sorted(enumerate(items), key=lambda pair: (-pair[1]['score'], pair[0]))[:k] and [pair[1] for pair in sorted(enumerate(items), key=lambda pair: (-pair[1]['score'], pair[0]))[:k]]",
            "D": "def solve(items, k):\n    return items[:k]",
        },
        "items = [{'id': 2, 'score': 9}, {'id': 1, 'score': 9}, {'id': 3, 'score': 8}]\nassert [x['id'] for x in solve(items, 2)] == [2, 1]",
        "C",
    ),
    task(
        "exec_timezone_sort",
        "high",
        "Events are ordered incorrectly by timestamp.",
        "def solve(events):\n    return sorted(events, key=lambda event: event['timestamp'])",
        {
            "A": "from datetime import datetime\ndef solve(events):\n    return sorted(events, key=lambda event: datetime.fromisoformat(event['timestamp']))",
            "B": "def solve(events):\n    return sorted(events, key=lambda event: event['timestamp'], reverse=True)",
            "C": "def solve(events):\n    return sorted(events, key=lambda event: event['timestamp'].replace('-', ''))",
            "D": "def solve(events):\n    return sorted(events, key=lambda event: event['title'])",
        },
        "events = [{'title': 'a', 'timestamp': '2025-01-01T09:00:00+02:00'}, {'title': 'b', 'timestamp': '2025-01-01T08:30:00+00:00'}]\nassert [e['title'] for e in solve(events)] == ['a', 'b']",
        "A",
    ),
    task(
        "exec_dedup_unhashable",
        "medium",
        "The unique helper must preserve first-seen order and support unhashable values.",
        "def solve(items):\n    return list(set(items))",
        {
            "A": "def solve(items):\n    return sorted(set(items))",
            "B": "def solve(items):\n    seen = set(); out = []\n    for item in items:\n        if item not in seen:\n            seen.add(item); out.append(item)\n    return out",
            "C": "def solve(items):\n    out = []\n    for item in items:\n        if not any(item == prev for prev in out):\n            out.append(item)\n    return out",
            "D": "def solve(items):\n    return list(reversed(items))",
        },
        "assert solve([3, 1, 3, 2]) == [3, 1, 2]\nassert solve([{'a': 1}, {'a': 1}, {'b': 2}]) == [{'a': 1}, {'b': 2}]",
        "C",
    ),
    task(
        "exec_flag_unknown",
        "high",
        "The feature flag reader silently accepts unknown values.",
        "def solve(value):\n    return str(value).lower() in {'1', 'true', 'yes'}",
        {
            "A": "def solve(value):\n    return str(value).lower() in {'1', 'true', 'yes'}",
            "B": "def solve(value):\n    text = str(value).strip().lower()\n    if text in {'1', 'true', 'yes'}: return True\n    if text in {'0', 'false', 'no'}: return False\n    raise ValueError(text)",
            "C": "def solve(value):\n    return bool(value)",
            "D": "def solve(value):\n    return None",
        },
        "assert solve('yes') is True\nassert solve('no') is False\ntry:\n    solve('maybe')\nexcept ValueError:\n    pass\nelse:\n    raise AssertionError('unknown value must raise')",
        "B",
    ),
    task(
        "exec_casefold_ids",
        "high",
        "Identifier normalization misses equivalent Unicode case variants.",
        "def solve(value):\n    return value.strip().lower()",
        {
            "A": "def solve(value):\n    return value.strip().lower()",
            "B": "def solve(value):\n    return value.strip().casefold()",
            "C": "def solve(value):\n    return value.lower()",
            "D": "def solve(value):\n    return value.upper()",
        },
        "assert solve('  ABC ') == 'abc'\nassert solve('Straße') == 'strasse'",
        "B",
    ),
    task(
        "exec_version_sort",
        "high",
        "Version strings are sorted lexicographically.",
        "def solve(values):\n    return sorted(values)",
        {
            "A": "def solve(values):\n    return sorted(values, key=lambda text: [int(part) for part in text.split('.')])",
            "B": "def solve(values):\n    return sorted(values, reverse=True)",
            "C": "def solve(values):\n    return sorted(values, key=len)",
            "D": "def solve(values):\n    return values",
        },
        "assert solve(['1.10', '1.2', '1.0']) == ['1.0', '1.2', '1.10']",
        "A",
    ),
    task(
        "exec_safe_divide",
        "medium",
        "The ratio helper crashes on zero denominators.",
        "def solve(numerator, denominator):\n    return numerator / denominator",
        {
            "A": "def solve(numerator, denominator):\n    return 0 if denominator == 0 else numerator / denominator",
            "B": "def solve(numerator, denominator):\n    return numerator // denominator",
            "C": "def solve(numerator, denominator):\n    return None if numerator == 0 else numerator / denominator",
            "D": "def solve(numerator, denominator):\n    return denominator / numerator",
        },
        "assert solve(4, 2) == 2\nassert solve(4, 0) == 0",
        "A",
    ),
    task(
        "exec_flatten_one_level",
        "medium",
        "The flattener recursively flattens too much.",
        "def solve(values):\n    out = []\n    for value in values:\n        if isinstance(value, list):\n            out.extend(solve(value))\n        else:\n            out.append(value)\n    return out",
        {
            "A": "def solve(values):\n    out = []\n    for value in values:\n        if isinstance(value, list): out.extend(value)\n        else: out.append(value)\n    return out",
            "B": "def solve(values):\n    return values",
            "C": "def solve(values):\n    return [item for sub in values for item in sub]",
            "D": "def solve(values):\n    return []",
        },
        "assert solve([1, [2, [3]], 4]) == [1, 2, [3], 4]",
        "A",
    ),
    task(
        "exec_clip_bounds",
        "low",
        "The clipping helper fails to cap high values.",
        "def solve(value, low, high):\n    return max(value, low)",
        {
            "A": "def solve(value, low, high):\n    return min(value, low)",
            "B": "def solve(value, low, high):\n    return max(value, high)",
            "C": "def solve(value, low, high):\n    return min(max(value, low), high)",
            "D": "def solve(value, low, high):\n    return value",
        },
        "assert solve(5, 0, 10) == 5\nassert solve(-1, 0, 10) == 0\nassert solve(12, 0, 10) == 10",
        "C",
    ),
    task(
        "exec_merge_defaults",
        "high",
        "Merging user config mutates the defaults shared by later calls.",
        "def solve(defaults, user):\n    defaults.update(user)\n    return defaults",
        {
            "A": "def solve(defaults, user):\n    defaults.update(user)\n    return defaults",
            "B": "def solve(defaults, user):\n    out = dict(defaults)\n    out.update(user)\n    return out",
            "C": "def solve(defaults, user):\n    return user",
            "D": "def solve(defaults, user):\n    return defaults",
        },
        "defaults = {'timeout': 30}\nout = solve(defaults, {'timeout': 5})\nassert out == {'timeout': 5}\nassert defaults == {'timeout': 30}",
        "B",
    ),
    task(
        "exec_slugify_spaces",
        "medium",
        "Slug generation leaves repeated separators.",
        "def solve(text):\n    return text.strip().lower().replace(' ', '-')",
        {
            "A": "import re\ndef solve(text):\n    return re.sub(r'-+', '-', re.sub(r'[^a-z0-9]+', '-', text.strip().lower())).strip('-')",
            "B": "def solve(text):\n    return text.lower()",
            "C": "def solve(text):\n    return text.replace(' ', '')",
            "D": "def solve(text):\n    return text.strip().upper().replace(' ', '-')",
        },
        "assert solve(' Hello,   World!! ') == 'hello-world'\nassert solve('A--B') == 'a-b'",
        "A",
    ),
    task(
        "exec_email_domain",
        "medium",
        "The email domain extractor fails when the local part contains @ in quotes.",
        "def solve(email):\n    return email.split('@')[1].lower()",
        {
            "A": "def solve(email):\n    return email.split('@')[1].lower()",
            "B": "def solve(email):\n    return email.rsplit('@', 1)[1].lower()",
            "C": "def solve(email):\n    return email.split('@')[0].lower()",
            "D": "def solve(email):\n    return email.upper()",
        },
        "assert solve('a@example.com') == 'example.com'\nassert solve('\"a@b\"@Example.COM') == 'example.com'",
        "B",
    ),
    task(
        "exec_parse_int_base",
        "low",
        "Integer parsing should accept whitespace around decimal text.",
        "def solve(text):\n    return int(text)",
        {
            "A": "def solve(text):\n    return int(text.strip())",
            "B": "def solve(text):\n    return float(text)",
            "C": "def solve(text):\n    return len(text)",
            "D": "def solve(text):\n    return int(text, 16)",
        },
        "assert solve(' 42 ') == 42\nassert solve('-3') == -3",
        "A",
    ),
    task(
        "exec_chunk_tail",
        "low",
        "Chunking drops the final short chunk.",
        "def solve(items, size):\n    return [items[i:i+size] for i in range(0, len(items) - size, size)]",
        {
            "A": "def solve(items, size):\n    return [items[i:i+size] for i in range(0, len(items), size)]",
            "B": "def solve(items, size):\n    return [items]",
            "C": "def solve(items, size):\n    return []",
            "D": "def solve(items, size):\n    return [items[i:i+size+1] for i in range(0, len(items), size)]",
        },
        "assert solve([1, 2, 3, 4, 5], 2) == [[1, 2], [3, 4], [5]]",
        "A",
    ),
    task(
        "exec_mode_tie",
        "high",
        "The mode helper returns the wrong value when counts tie.",
        "def solve(values):\n    counts = {}\n    for value in values:\n        counts[value] = counts.get(value, 0) + 1\n    return max(counts, key=counts.get)",
        {
            "A": "def solve(values):\n    counts = {}\n    for value in values: counts[value] = counts.get(value, 0) + 1\n    return min(counts, key=lambda value: (-counts[value], value))",
            "B": "def solve(values):\n    return values[0]",
            "C": "def solve(values):\n    return values[-1]",
            "D": "def solve(values):\n    return None",
        },
        "assert solve([2, 1, 2, 1]) == 1\nassert solve([3, 3, 2]) == 3",
        "A",
    ),
    task(
        "exec_running_average",
        "medium",
        "The running average uses integer division.",
        "def solve(values):\n    total = 0\n    out = []\n    for i, value in enumerate(values, 1):\n        total += value\n        out.append(total // i)\n    return out",
        {
            "A": "def solve(values):\n    total = 0; out = []\n    for i, value in enumerate(values, 1):\n        total += value; out.append(total / i)\n    return out",
            "B": "def solve(values):\n    return values",
            "C": "def solve(values):\n    return [sum(values) / len(values)]",
            "D": "def solve(values):\n    return [0 for _ in values]",
        },
        "assert solve([1, 2]) == [1.0, 1.5]\nassert solve([2, 4, 6]) == [2.0, 3.0, 4.0]",
        "A",
    ),
    task(
        "exec_strip_prefix",
        "low",
        "Prefix stripping removes matching characters instead of one exact prefix.",
        "def solve(text, prefix):\n    return text.lstrip(prefix)",
        {
            "A": "def solve(text, prefix):\n    return text[len(prefix):] if text.startswith(prefix) else text",
            "B": "def solve(text, prefix):\n    return text.replace(prefix, '')",
            "C": "def solve(text, prefix):\n    return text.rstrip(prefix)",
            "D": "def solve(text, prefix):\n    return prefix + text",
        },
        "assert solve('foobar', 'foo') == 'bar'\nassert solve('ofobar', 'foo') == 'ofobar'",
        "A",
    ),
    task(
        "exec_group_threshold",
        "high",
        "The classifier applies the threshold in the wrong direction.",
        "def solve(score, threshold):\n    return score <= threshold",
        {
            "A": "def solve(score, threshold):\n    return score >= threshold",
            "B": "def solve(score, threshold):\n    return score > threshold",
            "C": "def solve(score, threshold):\n    return score < threshold",
            "D": "def solve(score, threshold):\n    return True",
        },
        "assert solve(0.8, 0.7) is True\nassert solve(0.7, 0.7) is True\nassert solve(0.6, 0.7) is False",
        "A",
    ),
    task(
        "exec_normalize_whitespace",
        "medium",
        "Whitespace normalization preserves repeated spaces and tabs.",
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
        "exec_percent_change",
        "high",
        "Percent change crashes when the baseline is zero.",
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


def call_lmstudio(base_url: str, model: str, messages: list[dict[str, str]], timeout: float, max_tokens: int, label: str, reasoning_effort: str) -> CallRecord:
    payload = {"model": model, "messages": messages, "temperature": 0.0, "max_tokens": max_tokens}
    if reasoning_effort:
        payload["reasoning_effort"] = reasoning_effort
    start = time.perf_counter()
    parsed = request_json(base_url.rstrip("/") + "/chat/completions", method="POST", payload=payload, timeout=timeout)
    latency = time.perf_counter() - start
    choices = parsed.get("choices") or []
    if not choices:
        raise RuntimeError(f"LM Studio returned no choices: {parsed}")
    message = choices[0].get("message", {})
    text = str(message.get("content", "") or message.get("reasoning_content", "") or "")
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
        if match:
            try:
                parsed = json.loads(match.group(0))
                return parsed if isinstance(parsed, dict) else {}
            except json.JSONDecodeError:
                pass
        for key in ["final_choice", "choice", "likely_choice"]:
            choice_match = re.search(rf'"{key}"\s*:\s*"([ABCD])"', stripped, flags=re.IGNORECASE)
            if choice_match:
                return {key: choice_match.group(1).upper(), "raw_response": text}
    return {}


def normalize_choice(value: Any) -> str:
    text = str(value or "").strip().upper()
    match = re.search(r"\b([ABCD])\b", text)
    return match.group(1) if match else ""


def candidate_text(task: dict[str, Any]) -> str:
    parts = []
    for key in ["A", "B", "C", "D"]:
        parts.append(f"{key}:\n{task['candidates'][key]}")
    return "\n".join(parts)


def minimal_context(task: dict[str, Any]) -> str:
    return f"""Issue:
{task['issue']}

Buggy code:
{task['buggy_code']}

Candidate replacement implementations:
{candidate_text(task)}
"""


def full_context(task: dict[str, Any]) -> str:
    return f"""{minimal_context(task)}

Executable tests:
{task['tests']}
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


def evaluate_choice(task: dict[str, Any], choice: str, timeout: float = 2.0) -> tuple[int, str]:
    if choice not in task["candidates"]:
        return 0, "invalid_choice"
    program = task["candidates"][choice] + "\n" + task["tests"]
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as handle:
        handle.write(program)
        path = Path(handle.name)
    try:
        result = subprocess.run(["python3", str(path)], text=True, capture_output=True, timeout=timeout, check=False)
    except subprocess.TimeoutExpired:
        path.unlink(missing_ok=True)
        return 0, "timeout"
    finally:
        path.unlink(missing_ok=True)
    if result.returncode == 0:
        return 1, "tests_passed"
    return 0, (result.stderr or result.stdout or "tests_failed")[-500:]


def run_direct_low(task: dict[str, Any], args: argparse.Namespace, model: str, controller: str = "direct_low") -> tuple[dict[str, Any], list[dict[str, Any]]]:
    calls: list[CallRecord] = []
    logs: list[dict[str, Any]] = []
    try:
        prompt = f"""Choose the best replacement implementation using only the issue and candidate code. The tests are not visible in this low-context workflow.

{minimal_context(task)}

Return compact JSON with keys: choice, confidence, reason."""
        call = call_lmstudio(args.lmstudio_base_url, model, json_messages("You are a one-pass low-context code agent. Return JSON only.", prompt), args.timeout, 300, "direct_low_answer", args.reasoning_effort)
        calls.append(call)
        parsed = parse_json_object(call.response_text)
        choice = normalize_choice(parsed.get("choice"))
        notes = {"parsed": parsed}
    except (RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        choice = ""
        notes = {"error": str(exc)}
    success, eval_note = evaluate_choice(task, choice)
    row = result_row(task, controller, choice, success, eval_note, usage_totals(calls), context="minimal")
    row.update({"read_count": 1, "patch_attempts": 1, "patch_apply_successes": success, "route": "minimal_context", "notes": json.dumps(notes, ensure_ascii=False)})
    logs.extend(call_log(task, controller, call) for call in calls)
    return row, logs


def run_standard_full(task: dict[str, Any], args: argparse.Namespace, model: str, controller: str = "standard_full") -> tuple[dict[str, Any], list[dict[str, Any]]]:
    calls: list[CallRecord] = []
    logs: list[dict[str, Any]] = []
    try:
        system = "You are a full-context multi-step code agent. Return compact JSON only."
        diagnosis_prompt = f"""Diagnose the bug using the visible tests and candidate implementations.

{full_context(task)}

Return JSON with keys: diagnosis, likely_choice, uncertainty."""
        call = call_lmstudio(args.lmstudio_base_url, model, json_messages(system, diagnosis_prompt), args.timeout, 500, "standard_diagnosis", args.reasoning_effort)
        calls.append(call)
        diagnosis = parse_json_object(call.response_text)

        decision_prompt = f"""Choose the implementation most likely to pass the executable tests.

Diagnosis JSON:
{json.dumps(diagnosis, ensure_ascii=False)}

{full_context(task)}

Return JSON with keys: choice, confidence, reason."""
        call = call_lmstudio(args.lmstudio_base_url, model, json_messages(system, decision_prompt), args.timeout, 380, "standard_decision", args.reasoning_effort)
        calls.append(call)
        decision = parse_json_object(call.response_text)

        verify_prompt = f"""Verify the proposed choice against the tests. You may change it if another candidate is more likely to pass.

Proposed choice JSON:
{json.dumps(decision, ensure_ascii=False)}

{full_context(task)}

Return JSON with keys: final_choice, changed, verification_note."""
        call = call_lmstudio(args.lmstudio_base_url, model, json_messages(system, verify_prompt), args.timeout, 380, "standard_verify", args.reasoning_effort)
        calls.append(call)
        verify = parse_json_object(call.response_text)
        choice = normalize_choice(verify.get("final_choice")) or normalize_choice(decision.get("choice")) or normalize_choice(diagnosis.get("likely_choice"))
        notes = {"diagnosis": diagnosis, "decision": decision, "verify": verify}
    except (RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        choice = ""
        notes = {"error": str(exc)}
    success, eval_note = evaluate_choice(task, choice)
    row = result_row(task, controller, choice, success, eval_note, usage_totals(calls), context="full")
    row.update(
        {
            "test_runs": 1,
            "verification_events": 1,
            "search_count": 1,
            "read_count": 3,
            "patch_attempts": 1,
            "patch_apply_successes": success,
            "route": "full_context",
            "notes": json.dumps(notes, ensure_ascii=False),
        }
    )
    logs.extend(call_log(task, controller, call) for call in calls)
    return row, logs


def result_row(task: dict[str, Any], controller: str, choice: str, success: int, eval_note: str, totals: dict[str, float], context: str) -> dict[str, Any]:
    context_text = full_context(task) if context == "full" else minimal_context(task)
    return {
        "run_id": "lmstudio_executable_context_gate",
        "instance_id": task["instance_id"],
        "repo": task["repo"],
        "controller": controller,
        "execution_mode": "lmstudio_executable_context_budget",
        "execute_status": "completed",
        "success": int(success),
        "final_target_test_pass": int(success),
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
        "files_changed": 1,
        "lines_changed": len(task["candidates"].get(choice, "").splitlines()) if choice in task["candidates"] else 0,
        "failed_verification_jobs": 0 if success else 1,
        "recovery_attempts": 0,
        "expected_choice": task["answer"],
        "predicted_choice": choice,
        "route": "",
        "workload_risk": task["risk_tier"],
        "quality_risk": "low" if success else "high",
        "notes": json.dumps({"eval_note": eval_note}, ensure_ascii=False),
    }


def call_log(task: dict[str, Any], controller: str, call: CallRecord) -> dict[str, Any]:
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


def selected_tasks(limit: int) -> list[dict[str, Any]]:
    return TASKS if limit <= 0 else TASKS[: min(limit, len(TASKS))]


def derive_gate_rows(rows: list[dict[str, Any]], policy: str) -> list[dict[str, Any]]:
    by_task: dict[str, dict[str, dict[str, Any]]] = {}
    for row in rows:
        by_task.setdefault(str(row["instance_id"]), {})[str(row["controller"])] = row
    derived: list[dict[str, Any]] = []
    for task in TASKS:
        if task["instance_id"] not in by_task:
            continue
        use_full = task["risk_tier"] == "high" if policy == "high_only" else task["risk_tier"] in {"medium", "high"}
        source_name = "standard_full" if use_full else "direct_low"
        source = dict(by_task[task["instance_id"]][source_name])
        source["controller"] = f"context_gate_{policy}"
        source["route"] = "gate_full_context" if use_full else "gate_minimal_context"
        source["fallback_events"] = 1 if use_full else 0
        source["notes"] = json.dumps({"derived_from": source_name, "policy": policy, "original_notes": source.get("notes", "")}, ensure_ascii=False)
        derived.append(source)
    return derived


def write_report(path: Path, rows: list[dict[str, Any]], model: str, result_path: Path, calls_path: Path) -> None:
    by_controller: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_controller.setdefault(str(row["controller"]), []).append(row)
    lines = [
        "# LM Studio Executable Context-Gate Pilot",
        "",
        "The model chooses among static candidate replacement implementations. The selected implementation is executed against local Python tests.",
        "",
        f"- Model: `{model}`",
        f"- Tasks: {len({row['instance_id'] for row in rows})}",
        f"- Result CSV: `{result_path}`",
        f"- Call log: `{calls_path}`",
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
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run an executable snippet context-gate experiment with LM Studio.")
    parser.add_argument("--lmstudio-base-url", default=DEFAULT_BASE_URL)
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
                    f"[exec-context] {completed}/{total} {current['instance_id']}::{controller} "
                    f"choice={row['predicted_choice']} expected={row['expected_choice']} success={row['success']} tokens={row['total_tokens']}",
                    flush=True,
                )

    rows.extend(derive_gate_rows(rows, "medium_high"))
    rows.extend(derive_gate_rows(rows, "high_only"))

    result_path = output_dir / "runtime_task_results.csv"
    calls_path = output_dir / "runtime_call_log.jsonl"
    report_path = output_dir / "runtime_executable_context_gate_report.md"
    summary_path = output_dir / "runtime_executable_context_gate_summary.json"
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
    print(f"Wrote executable context-gate results to {result_path}")
    print(f"Wrote executable context-gate report to {report_path}")


if __name__ == "__main__":
    main()
