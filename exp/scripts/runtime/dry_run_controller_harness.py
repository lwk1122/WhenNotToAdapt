from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import pandas as pd


DEFAULT_MATRIX = Path("exp/results/emse_runtime/manifest_v1/runtime_execution_matrix.csv")
DEFAULT_MANIFEST = Path("exp/results/emse_runtime/manifest_v1/task_manifest.csv")
DEFAULT_OUTPUT_DIR = Path("exp/results/emse_runtime/dry_run_v1")

ANALYSIS_RESULT_COLUMNS = [
    "run_id",
    "instance_id",
    "repo",
    "controller",
    "execution_mode",
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
]


CONTROLLER_INSTRUCTIONS = {
    "static_conservative": (
        "Use a conservative workflow. Keep context and edits narrow. "
        "Plan only the most likely files and focused regression tests. "
        "Prefer inheriting the baseline unless the issue is clearly localized."
    ),
    "rsrc_guarded": (
        "Use a resource-guarded workflow. Spend extra search or tests only when "
        "the issue evidence suggests a high probability of solving value. "
        "Name the resource stop rule."
    ),
    "sempc_lite": (
        "Use the CASC-like gate. Compare adaptive effort with the baseline using "
        "workload, quality, risk, and calibration-coverage margins. Decide whether "
        "to adapt or inherit the baseline before proposing a patch plan."
    ),
    "minimal_verify": (
        "Use a low-verification diagnostic workflow. Produce the smallest plausible "
        "patch plan and one minimal check. This is not the primary comparator."
    ),
}

CONTROLLER_DECISION_CONSTRAINTS = {
    "static_conservative": (
        "Return decision=\"inherit_baseline\". This controller is the conservative baseline; "
        "it may list focused verification steps, but it must not buy adaptive effort."
    ),
    "minimal_verify": (
        "Return decision=\"minimal_plan\". This controller is a low-verification diagnostic baseline; "
        "it must not escalate to adaptive effort."
    ),
    "rsrc_guarded": (
        "Return decision=\"adapt\" only when the visible issue evidence justifies extra search or tests; "
        "otherwise return decision=\"inherit_baseline\"."
    ),
    "sempc_lite": (
        "Return decision=\"adapt\" only when adaptive effort is justified relative to the baseline by "
        "workload, quality, risk, and calibration-coverage margins; otherwise return decision=\"inherit_baseline\"."
    ),
}


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def truncate_text(text: Any, limit: int) -> str:
    value = "" if pd.isna(text) else str(text)
    return value if len(value) <= limit else value[:limit] + "\n...[truncated]"


def load_joined_rows(matrix_path: Path, manifest_path: Path) -> pd.DataFrame:
    matrix = pd.read_csv(matrix_path)
    manifest = pd.read_csv(manifest_path)
    needed = [
        "instance_id",
        "problem_statement",
        "hints_text",
        "FAIL_TO_PASS",
        "PASS_TO_PASS",
        "problem_tokens",
        "fail_to_pass_count",
        "pass_to_pass_count",
        "gold_patch_files",
        "gold_patch_lines",
        "shadow_risk_score",
        "risk_tier",
    ]
    manifest_cols = [col for col in needed if col in manifest.columns]
    joined = matrix.merge(manifest[manifest_cols], on="instance_id", how="left", suffixes=("", "_manifest"))
    if "risk_tier_manifest" in joined.columns:
        joined["risk_tier"] = joined["risk_tier"].fillna(joined["risk_tier_manifest"])
        joined = joined.drop(columns=["risk_tier_manifest"])
    return joined


def filter_rows(frame: pd.DataFrame, controllers: list[str] | None, max_tasks: int) -> pd.DataFrame:
    out = frame.copy()
    if controllers:
        out = out[out["controller"].isin(controllers)].copy()
    ordered_tasks = out[["task_order", "instance_id"]].drop_duplicates().sort_values("task_order")
    if max_tasks > 0:
        keep_instances = set(ordered_tasks.head(max_tasks)["instance_id"].astype(str))
        out = out[out["instance_id"].astype(str).isin(keep_instances)].copy()
    return out.sort_values(["task_order", "controller_order_within_task", "controller"]).reset_index(drop=True)


def build_prompt(row: pd.Series, text_limit: int) -> str:
    controller = str(row["controller"])
    instruction = CONTROLLER_INSTRUCTIONS.get(controller, CONTROLLER_INSTRUCTIONS["static_conservative"])
    decision_constraint = CONTROLLER_DECISION_CONSTRAINTS.get(controller, "Return a valid decision from the allowed set.")
    tests = truncate_text(row.get("FAIL_TO_PASS", ""), 1200)
    pass_tests = truncate_text(row.get("PASS_TO_PASS", ""), 800)
    problem = truncate_text(row.get("problem_statement", ""), text_limit)
    hints = truncate_text(row.get("hints_text", ""), 1200)
    return f"""You are planning a dry-run controller decision for a software-engineering agent.

Safety boundary:
- Do not claim tests were executed.
- Do not claim a patch was applied.
- Do not invent repository inspection results.
- Produce a plan only from the issue text and visible metadata.

Controller: {controller}
Controller policy: {instruction}
Decision contract: {decision_constraint}

Repository: {row.get('repo', '')}
Instance: {row.get('instance_id', '')}
Risk tier: {row.get('risk_tier', '')}
Difficulty: {row.get('difficulty', '')}
Problem token proxy: {row.get('problem_tokens', '')}
Fail-to-pass tests count: {row.get('fail_to_pass_count', '')}
Pass-to-pass tests count: {row.get('pass_to_pass_count', '')}
Gold patch file count proxy: {row.get('gold_patch_files', '')}
Gold patch line count proxy: {row.get('gold_patch_lines', '')}
Shadow risk score: {row.get('shadow_risk_score', '')}

Problem statement:
{problem}

Hints:
{hints}

Known fail-to-pass tests:
{tests}

Known pass-to-pass tests:
{pass_tests}

Return compact JSON with these keys:
- decision: one of ["inherit_baseline", "adapt", "minimal_plan"]
- files_to_inspect: list of likely file paths or modules, maximum 6
- tests_to_run: list of focused tests, maximum 6
- patch_strategy: one short paragraph
- workload_risk: one of ["low", "medium", "high"]
- quality_risk: one of ["low", "medium", "high"]
- stop_rule: one sentence
- audit_reason: one sentence explaining the controller decision
"""


def offline_plan(row: pd.Series) -> dict[str, Any]:
    controller = str(row["controller"])
    fail_count = int(pd.to_numeric(row.get("fail_to_pass_count", 0), errors="coerce") or 0)
    pass_count = int(pd.to_numeric(row.get("pass_to_pass_count", 0), errors="coerce") or 0)
    gold_files = int(pd.to_numeric(row.get("gold_patch_files", 0), errors="coerce") or 0)
    risk_tier = str(row.get("risk_tier", ""))
    if controller == "sempc_lite" and risk_tier == "high":
        decision = "inherit_baseline"
    elif controller in {"sempc_lite", "rsrc_guarded"} and (fail_count > 1 or gold_files > 1):
        decision = "adapt"
    elif controller == "minimal_verify":
        decision = "minimal_plan"
    else:
        decision = "inherit_baseline"
    tests = []
    try:
        parsed = json.loads(row.get("FAIL_TO_PASS", "[]"))
        if isinstance(parsed, list):
            tests = [str(item) for item in parsed[: min(3, len(parsed))]]
    except Exception:
        tests = []
    return {
        "decision": decision,
        "files_to_inspect": [],
        "tests_to_run": tests,
        "patch_strategy": "Dry-run heuristic plan only; inspect the issue-local implementation path before editing.",
        "workload_risk": "high" if risk_tier == "high" or pass_count > 20 else "medium",
        "quality_risk": "medium" if fail_count else "low",
        "stop_rule": "Stop after the planned focused checks; do not expand without a new gate decision.",
        "audit_reason": f"Offline dry-run plan for {controller}; no repository code was executed.",
    }


def request_json(url: str, method: str = "GET", payload: dict[str, Any] | None = None, timeout: float = 30.0) -> dict[str, Any]:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"} if payload is not None else {}
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def discover_model(base_url: str, timeout: float) -> str:
    models = request_json(base_url.rstrip("/") + "/models", timeout=timeout)
    data = models.get("data", [])
    if not data:
        raise RuntimeError("LM Studio /models returned no models.")
    return str(data[0].get("id", ""))


def call_lmstudio(base_url: str, model: str, prompt: str, timeout: float, max_tokens: int) -> tuple[str, dict[str, Any]]:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You produce conservative JSON-only dry-run plans for software-engineering agents."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.0,
        "max_tokens": max_tokens,
    }
    started = time.time()
    result = request_json(base_url.rstrip("/") + "/chat/completions", method="POST", payload=payload, timeout=timeout)
    elapsed = time.time() - started
    content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
    meta = {
        "model": model,
        "elapsed_seconds": elapsed,
        "usage": result.get("usage", {}),
    }
    return str(content), meta


def parse_model_plan(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`")
        if "\n" in stripped:
            stripped = stripped.split("\n", 1)[1]
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start >= 0 and end > start:
        stripped = stripped[start : end + 1]
    try:
        value = json.loads(stripped)
        return value if isinstance(value, dict) else {"raw_response": text}
    except Exception:
        return {"raw_response": text}


def count_list(value: Any) -> int:
    return len(value) if isinstance(value, list) else 0


def plan_to_row(row: pd.Series, plan: dict[str, Any], prompt: str, mode: str, model_meta: dict[str, Any]) -> dict[str, Any]:
    planned_files = count_list(plan.get("files_to_inspect"))
    planned_tests = count_list(plan.get("tests_to_run"))
    return {
        "run_id": "dry_run_v1",
        "instance_id": row.get("instance_id", ""),
        "repo": row.get("repo", ""),
        "controller": row.get("controller", ""),
        "execution_mode": f"{mode}_prompt_only",
        "task_order": row.get("task_order", ""),
        "controller_order_within_task": row.get("controller_order_within_task", ""),
        "risk_tier": row.get("risk_tier", ""),
        "difficulty": row.get("difficulty", ""),
        "decision": plan.get("decision", ""),
        "workload_risk": plan.get("workload_risk", ""),
        "quality_risk": plan.get("quality_risk", ""),
        "planned_files_to_inspect": json.dumps(plan.get("files_to_inspect", []), ensure_ascii=False),
        "planned_tests_to_run": json.dumps(plan.get("tests_to_run", []), ensure_ascii=False),
        "planned_read_count": planned_files,
        "planned_test_count": planned_tests,
        "planned_patch_attempts": 1 if plan.get("patch_strategy") else 0,
        "patch_strategy": plan.get("patch_strategy", ""),
        "stop_rule": plan.get("stop_rule", ""),
        "audit_reason": plan.get("audit_reason", ""),
        "prompt_chars": len(prompt),
        "model": model_meta.get("model", ""),
        "elapsed_seconds": model_meta.get("elapsed_seconds", 0.0),
        "prompt_tokens": model_meta.get("usage", {}).get("prompt_tokens", ""),
        "completion_tokens": model_meta.get("usage", {}).get("completion_tokens", ""),
        "total_tokens": model_meta.get("usage", {}).get("total_tokens", ""),
    }


def empty_analysis_template(plan_row: dict[str, Any]) -> dict[str, Any]:
    out = {col: "" for col in ANALYSIS_RESULT_COLUMNS}
    for col in ["run_id", "instance_id", "repo", "controller", "execution_mode"]:
        out[col] = plan_row.get(col, "")
    return out


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_report(path: Path, plans: pd.DataFrame, output_dir: Path, mode: str) -> None:
    controller_counts = plans["controller"].value_counts().sort_index()
    decision_counts = plans["decision"].fillna("").value_counts().sort_index()
    lines = [
        "# Controlled Runtime Dry-Run Harness Report",
        "",
        "This is a prompt-only dry run. It does not clone repositories, inspect files, apply patches, install dependencies, or run tests.",
        "",
        f"- Mode: `{mode}`",
        f"- Planned rows: {len(plans)}",
        f"- Tasks: {plans['instance_id'].nunique()}",
        f"- Controllers: {', '.join(controller_counts.index.astype(str).tolist())}",
        "",
        "## Controller Counts",
        "",
        "| controller | rows |",
        "|---|---:|",
    ]
    for controller, count in controller_counts.items():
        lines.append(f"| {controller} | {int(count)} |")
    lines.extend(["", "## Decision Counts", "", "| decision | rows |", "|---|---:|"])
    for decision, count in decision_counts.items():
        lines.append(f"| {decision or 'missing'} | {int(count)} |")
    lines.extend(
        [
            "",
            "## Outputs",
            "",
            f"- Plan rows: `{output_dir / 'runtime_dry_run_plans.csv'}`",
            f"- Prompt/response log: `{output_dir / 'runtime_dry_run_requests.jsonl'}`",
            f"- Analysis template: `{output_dir / 'runtime_task_results_template.csv'}`",
            "",
            "## Use Boundary",
            "",
            "- Use this output to validate controller prompts, logging fields, and result schema before isolated execution.",
            "- Do not use this output as solve-rate, resource-savings, or downstream-work evidence.",
            "- The analysis template intentionally leaves observed metrics blank.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Prompt-only dry-run harness for controlled runtime controllers.")
    parser.add_argument("--matrix", type=Path, default=DEFAULT_MATRIX)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--controllers", nargs="*", default=[])
    parser.add_argument("--max-tasks", type=int, default=2)
    parser.add_argument("--mode", choices=["offline", "lmstudio"], default="offline")
    parser.add_argument("--lmstudio-base-url", default="http://127.0.0.1:1234/v1")
    parser.add_argument("--model", default="")
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--max-tokens", type=int, default=700)
    parser.add_argument("--text-limit", type=int, default=5000)
    parser.add_argument("--progress-every", type=int, default=0, help="Print progress every N selected rows; 0 disables progress output.")
    args = parser.parse_args()

    output_dir = ensure_dir(args.output_dir)
    rows = filter_rows(load_joined_rows(args.matrix, args.manifest), args.controllers or None, args.max_tasks)
    if rows.empty:
        raise ValueError("No execution-matrix rows selected for dry run.")

    model = args.model
    if args.mode == "lmstudio" and not model:
        model = discover_model(args.lmstudio_base_url, args.timeout)

    plan_rows: list[dict[str, Any]] = []
    template_rows: list[dict[str, Any]] = []
    request_rows: list[dict[str, Any]] = []
    total_rows = len(rows)
    for row_number, (_, row) in enumerate(rows.iterrows(), start=1):
        prompt = build_prompt(row, args.text_limit)
        model_meta: dict[str, Any] = {"model": model}
        response_text = ""
        if args.mode == "lmstudio":
            try:
                response_text, model_meta = call_lmstudio(args.lmstudio_base_url, model, prompt, args.timeout, args.max_tokens)
                plan = parse_model_plan(response_text)
            except (urllib.error.URLError, TimeoutError, RuntimeError) as exc:
                plan = {
                    "decision": "missing",
                    "files_to_inspect": [],
                    "tests_to_run": [],
                    "patch_strategy": "",
                    "workload_risk": "",
                    "quality_risk": "",
                    "stop_rule": "",
                    "audit_reason": f"LM Studio dry run failed: {exc}",
                }
                model_meta["error"] = str(exc)
        else:
            plan = offline_plan(row)

        plan_row = plan_to_row(row, plan, prompt, args.mode, model_meta)
        plan_rows.append(plan_row)
        template_rows.append(empty_analysis_template(plan_row))
        request_rows.append(
            {
                "instance_id": row.get("instance_id", ""),
                "controller": row.get("controller", ""),
                "mode": args.mode,
                "prompt": prompt,
                "response_text": response_text,
                "parsed_plan": plan,
                "model_meta": model_meta,
            }
        )
        if args.progress_every > 0 and (row_number == 1 or row_number % args.progress_every == 0 or row_number == total_rows):
            print(
                f"[dry-run] {row_number}/{total_rows} "
                f"{row.get('instance_id', '')}::{row.get('controller', '')} "
                f"decision={plan_row.get('decision', '')}",
                flush=True,
            )

    plans = pd.DataFrame(plan_rows)
    template = pd.DataFrame(template_rows, columns=ANALYSIS_RESULT_COLUMNS)
    plans_path = output_dir / "runtime_dry_run_plans.csv"
    template_path = output_dir / "runtime_task_results_template.csv"
    requests_path = output_dir / "runtime_dry_run_requests.jsonl"
    report_path = output_dir / "runtime_dry_run_report.md"
    summary_path = output_dir / "runtime_dry_run_summary.json"

    plans.to_csv(plans_path, index=False)
    template.to_csv(template_path, index=False)
    write_jsonl(requests_path, request_rows)
    write_report(report_path, plans, output_dir, args.mode)
    summary_path.write_text(
        json.dumps(
            {
                "plans_csv": str(plans_path),
                "analysis_template_csv": str(template_path),
                "requests_jsonl": str(requests_path),
                "report_md": str(report_path),
                "rows": len(plans),
                "tasks": int(plans["instance_id"].nunique()),
                "controllers": sorted(plans["controller"].unique().tolist()),
                "mode": args.mode,
                "model": model,
                "safety": "prompt-only; no repository code executed",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Wrote dry-run plans to {plans_path}")
    print(f"Wrote dry-run report to {report_path}")


if __name__ == "__main__":
    main()
