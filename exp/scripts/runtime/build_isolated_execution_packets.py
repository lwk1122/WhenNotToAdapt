from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

import pandas as pd

from .dry_run_controller_harness import CONTROLLER_INSTRUCTIONS


DEFAULT_BUNDLE_DIR = Path("exp/results/emse_runtime/isolated_execution_bundle_v1")
DEFAULT_TASK_MANIFEST = Path("exp/results/emse_runtime/manifest_v1/task_manifest.csv")
DEFAULT_DRY_RUN_PLANS = Path("exp/results/emse_runtime/dry_run_offline_full_v1/runtime_dry_run_plans.csv")
DEFAULT_OUTPUT_DIR = Path("exp/results/emse_runtime/isolated_execution_packets_v1")

DRY_RUN_COLUMNS = [
    "instance_id",
    "controller",
    "decision",
    "workload_risk",
    "quality_risk",
    "planned_files_to_inspect",
    "planned_tests_to_run",
    "planned_read_count",
    "planned_test_count",
    "planned_patch_attempts",
    "patch_strategy",
    "stop_rule",
    "audit_reason",
]


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def parse_controllers(values: Iterable[str] | None) -> list[str] | None:
    if not values:
        return None
    out: list[str] = []
    for value in values:
        out.extend(part.strip() for part in str(value).split(",") if part.strip())
    return out or None


def safe_row_id(value: str) -> str:
    return value.replace("/", "_").replace(":", "_")


def clean_value(value: object) -> object:
    if pd.isna(value):
        return ""
    if hasattr(value, "item"):
        return value.item()
    return value


def as_text(value: object, limit: int) -> str:
    if pd.isna(value):
        return ""
    text = str(value)
    if limit <= 0 or len(text) <= limit:
        return text
    return text[:limit] + f"\n\n...[truncated to {limit} characters]"


def json_text(value: object) -> str:
    if pd.isna(value):
        return "[]"
    text = str(value)
    try:
        parsed = json.loads(text)
    except Exception:
        return text
    return json.dumps(parsed, indent=2, ensure_ascii=False)


def load_rows(bundle_dir: Path, task_manifest_path: Path, dry_run_plans_path: Path | None) -> pd.DataFrame:
    bundle_path = bundle_dir / "isolated_execution_manifest.csv"
    if not bundle_path.exists():
        raise FileNotFoundError(f"Missing isolated execution manifest: {bundle_path}")
    if not task_manifest_path.exists():
        raise FileNotFoundError(f"Missing task manifest: {task_manifest_path}")
    bundle = pd.read_csv(bundle_path)
    tasks = pd.read_csv(task_manifest_path)
    rows = bundle.merge(tasks, on=["instance_id", "repo", "base_commit"], how="left", suffixes=("", "_task"))
    if dry_run_plans_path and dry_run_plans_path.exists():
        dry = pd.read_csv(dry_run_plans_path)
        cols = [col for col in DRY_RUN_COLUMNS if col in dry.columns]
        rows = rows.merge(dry[cols], on=["instance_id", "controller"], how="left", suffixes=("", "_dry_run"))
    return rows


def filter_rows(rows: pd.DataFrame, controllers: list[str] | None, max_tasks: int) -> pd.DataFrame:
    out = rows.copy()
    if controllers:
        out = out[out["controller"].astype(str).isin(controllers)].copy()
    if max_tasks > 0:
        task_keys = out[["task_order", "instance_id"]].drop_duplicates().sort_values("task_order")
        keep = set(task_keys.head(max_tasks)["instance_id"].astype(str))
        out = out[out["instance_id"].astype(str).isin(keep)].copy()
    return out.sort_values(["task_order", "controller_order_within_task", "controller"]).reset_index(drop=True)


def packet_json(row: pd.Series, text_limit: int) -> dict[str, object]:
    controller = str(row["controller"])
    result_row_id = str(row["result_row_id"])
    return {
        "result_row_id": result_row_id,
        "bundle_id": clean_value(row.get("bundle_id", "")),
        "bundle_order": clean_value(row.get("bundle_order", "")),
        "run_group": clean_value(row.get("run_group", "")),
        "repo": clean_value(row.get("repo", "")),
        "instance_id": clean_value(row.get("instance_id", "")),
        "base_commit": clean_value(row.get("base_commit", "")),
        "controller": controller,
        "controller_policy": CONTROLLER_INSTRUCTIONS.get(controller, ""),
        "risk_tier": clean_value(row.get("risk_tier", "")),
        "difficulty": clean_value(row.get("difficulty", "")),
        "task_metrics": {
            "problem_tokens": clean_value(row.get("problem_tokens", "")),
            "hints_tokens": clean_value(row.get("hints_tokens", "")),
            "fail_to_pass_count": clean_value(row.get("fail_to_pass_count", "")),
            "pass_to_pass_count": clean_value(row.get("pass_to_pass_count", "")),
            "gold_patch_files": clean_value(row.get("gold_patch_files", "")),
            "gold_patch_lines": clean_value(row.get("gold_patch_lines", "")),
            "shadow_risk_score": clean_value(row.get("shadow_risk_score", "")),
        },
        "dry_run_plan": {
            "decision": clean_value(row.get("decision", "")),
            "workload_risk": clean_value(row.get("workload_risk", "")),
            "quality_risk": clean_value(row.get("quality_risk", "")),
            "planned_files_to_inspect": clean_value(row.get("planned_files_to_inspect", "")),
            "planned_tests_to_run": clean_value(row.get("planned_tests_to_run", "")),
            "planned_read_count": clean_value(row.get("planned_read_count", "")),
            "planned_test_count": clean_value(row.get("planned_test_count", "")),
            "planned_patch_attempts": clean_value(row.get("planned_patch_attempts", "")),
            "patch_strategy": clean_value(row.get("patch_strategy", "")),
            "stop_rule": clean_value(row.get("stop_rule", "")),
            "audit_reason": clean_value(row.get("audit_reason", "")),
        },
        "task_text": {
            "problem_statement": as_text(row.get("problem_statement", ""), text_limit),
            "hints_text": as_text(row.get("hints_text", ""), text_limit),
            "fail_to_pass": json_text(row.get("FAIL_TO_PASS", "")),
            "pass_to_pass": json_text(row.get("PASS_TO_PASS", "")),
        },
        "paths": {
            "planned_output_dir": clean_value(row.get("planned_output_dir", "")),
            "result_file": clean_value(row.get("result_file", "")),
            "bundle_dir": str(Path(str(row.get("result_file", ""))).parent) if clean_value(row.get("result_file", "")) else "",
            "log_dir": clean_value(row.get("log_dir", "")),
        },
        "safety": {
            "requires_isolation": True,
            "third_party_execution_performed": False,
            "packet_status": "no_execution_preparation",
        },
    }


def record_command(result_row_id: str, bundle_dir: str) -> str:
    return "\n".join(
        [
            ".venv_emse/bin/python -m exp.scripts.emse_runtime.record_isolated_runtime_result \\",
            f"  --bundle-dir {bundle_dir} \\",
            f"  --result-row-id {result_row_id} \\",
            "  --execute-status completed \\",
            "  --ack-isolated \\",
            "  --success <0-or-1> \\",
            "  --final-target-test-pass <0-or-1> \\",
            "  --catastrophic-failure <0-or-1> \\",
            "  --search-count <count> \\",
            "  --read-count <count> \\",
            "  --test-runs <count> \\",
            "  --patch-attempts <count> \\",
            "  --model-calls <count> \\",
            "  --prompt-tokens <count> \\",
            "  --completion-tokens <count> \\",
            "  --total-tokens <count> \\",
            "  --latency-seconds <seconds> \\",
            "  --preflight-passed \\",
            "  --sensitive-env-removed \\",
            "  --repo-snapshot-prepared \\",
            "  --dependencies-reviewed \\",
            "  --target-tests-run \\",
            '  --checklist-note "<preflight/checklist evidence summary>" \\',
            '  --evidence-note "<isolated log path and short result summary>"',
        ]
    )


def packet_markdown(packet: dict[str, object]) -> str:
    dry = packet["dry_run_plan"]  # type: ignore[index]
    metrics = packet["task_metrics"]  # type: ignore[index]
    text = packet["task_text"]  # type: ignore[index]
    paths = packet["paths"]  # type: ignore[index]
    result_row_id = str(packet["result_row_id"])
    bundle_dir = str(paths.get("bundle_dir", "exp/results/emse_runtime/isolated_execution_bundle_v1"))
    recorded_results = str(Path(str(paths.get("result_file", ""))).with_name("runtime_task_results_recorded.csv"))
    validation_dir = str(Path(bundle_dir).with_name(Path(bundle_dir).name + "_recorded_validation"))
    lines = [
        "# Isolated Runtime Execution Packet",
        "",
        "## Status",
        "",
        "- This packet is a no-execution preparation artifact.",
        "- It does not clone repositories, install dependencies, inspect files, apply patches, or run tests.",
        "- Use it only inside the approved isolated runtime after preflight passes.",
        "",
        "## Row",
        "",
        f"- Result row ID: `{result_row_id}`",
        f"- Repository: `{packet['repo']}`",
        f"- Instance: `{packet['instance_id']}`",
        f"- Base commit: `{packet['base_commit']}`",
        f"- Controller: `{packet['controller']}`",
        f"- Risk tier: `{packet['risk_tier']}`",
        f"- Difficulty: `{packet['difficulty']}`",
        f"- Planned output dir: `{paths['planned_output_dir']}`",
        f"- Log dir: `{paths['log_dir']}`",
        "",
        "## Controller Policy",
        "",
        str(packet["controller_policy"]),
        "",
        "## Dry-Run Plan",
        "",
        f"- Decision: `{dry.get('decision', '')}`",
        f"- Workload risk: `{dry.get('workload_risk', '')}`",
        f"- Quality risk: `{dry.get('quality_risk', '')}`",
        f"- Planned read count: `{dry.get('planned_read_count', '')}`",
        f"- Planned test count: `{dry.get('planned_test_count', '')}`",
        f"- Planned patch attempts: `{dry.get('planned_patch_attempts', '')}`",
        f"- Stop rule: {dry.get('stop_rule', '')}",
        f"- Audit reason: {dry.get('audit_reason', '')}",
        "",
        "Patch strategy:",
        "",
        str(dry.get("patch_strategy", "")) or "_Not available._",
        "",
        "Planned files to inspect:",
        "",
        "```json",
        str(dry.get("planned_files_to_inspect", "")) or "[]",
        "```",
        "",
        "Planned tests to run:",
        "",
        "```json",
        str(dry.get("planned_tests_to_run", "")) or "[]",
        "```",
        "",
        "## Task Metrics",
        "",
        f"- Problem tokens: `{metrics.get('problem_tokens', '')}`",
        f"- Hints tokens: `{metrics.get('hints_tokens', '')}`",
        f"- FAIL_TO_PASS count: `{metrics.get('fail_to_pass_count', '')}`",
        f"- PASS_TO_PASS count: `{metrics.get('pass_to_pass_count', '')}`",
        f"- Gold patch files proxy: `{metrics.get('gold_patch_files', '')}`",
        f"- Gold patch lines proxy: `{metrics.get('gold_patch_lines', '')}`",
        f"- Shadow risk score: `{metrics.get('shadow_risk_score', '')}`",
        "",
        "## Problem Statement",
        "",
        str(text.get("problem_statement", "")),
        "",
        "## Hints",
        "",
        str(text.get("hints_text", "")) or "_No hints text._",
        "",
        "## Known FAIL_TO_PASS Tests",
        "",
        "```json",
        str(text.get("fail_to_pass", "")),
        "```",
        "",
        "## Known PASS_TO_PASS Tests",
        "",
        "```json",
        str(text.get("pass_to_pass", "")),
        "```",
        "",
        "## Isolated Execution Checklist",
        "",
        "1. Confirm `preflight_runtime_environment.py` passes inside the isolated runtime.",
        "2. Prepare a disposable snapshot for the repository at the base commit.",
        "3. Remove or isolate sensitive environment variables before third-party code runs.",
        "4. Execute only bounded task-specific commands and capture logs under the packet log directory.",
        "5. Record observed metrics with the row recorder after execution.",
        "6. Run `validate_runtime_results.py` before any paired analysis.",
        "",
        "## Record Completed Row",
        "",
        "Fill placeholders only after the isolated run has produced observed metrics:",
        "",
        "```bash",
        record_command(result_row_id, bundle_dir),
        "```",
        "",
        "If `runtime_task_results_recorded.csv` already exists in the bundle directory, the recorder reads it by default before writing this row. Leave `--results-in` unset for ordinary row-by-row accumulation; use it only when intentionally branching from another results file.",
        "",
        "Only keep checklist flags that are true for the isolated run. Add `--dependencies-installed` only if dependencies were actually installed after review. Add `--validator-passed` only after the recorded results have passed validation.",
        "",
        "## Validation After Recording",
        "",
        "```bash",
        ".venv_emse/bin/python -m exp.scripts.emse_runtime.validate_runtime_results \\",
        f"  --task-results {recorded_results} \\",
        f"  --output-dir {validation_dir} \\",
        "  --target sempc_lite \\",
        "  --reference rsrc_guarded",
        "```",
        "",
    ]
    return "\n".join(lines)


def write_readme(path: Path, summary: dict[str, object]) -> None:
    lines = [
        "# Isolated Runtime Execution Packets",
        "",
        "These packets are no-execution preparation artifacts for the controlled runtime study.",
        "",
        f"- Packet rows: {summary['packet_rows']}",
        f"- Packet tasks: {summary['packet_tasks']}",
        f"- Controllers: {', '.join(summary['controllers'])}",
        f"- Packet index: `{summary['packet_index']}`",
        f"- Source bundle: `{summary['source_bundle']}`",
        f"- Source task manifest: `{summary['source_task_manifest']}`",
        "",
        "Use boundary:",
        "",
        "- Allowed: inspect task context, controller policy, recording commands, and required metrics.",
        "- Forbidden: treat packet generation as repository execution or policy-effect evidence.",
        "- Completed rows must be recorded with `record_isolated_runtime_result.py` after an approved isolated run.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build no-execution per-row packets for isolated controlled-runtime execution.")
    parser.add_argument("--bundle-dir", type=Path, default=DEFAULT_BUNDLE_DIR)
    parser.add_argument("--task-manifest", type=Path, default=DEFAULT_TASK_MANIFEST)
    parser.add_argument("--dry-run-plans", type=Path, default=DEFAULT_DRY_RUN_PLANS)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--controllers", nargs="*", default=None)
    parser.add_argument("--max-tasks", type=int, default=0)
    parser.add_argument("--text-limit", type=int, default=12000)
    args = parser.parse_args()

    output_dir = ensure_dir(args.output_dir)
    packet_dir = ensure_dir(output_dir / "packets")
    rows = filter_rows(
        load_rows(args.bundle_dir, args.task_manifest, args.dry_run_plans),
        parse_controllers(args.controllers),
        args.max_tasks,
    )
    if rows.empty:
        raise ValueError("No rows selected for packet generation.")

    index_rows: list[dict[str, object]] = []
    for _, row in rows.iterrows():
        packet = packet_json(row, args.text_limit)
        result_row_id = str(packet["result_row_id"])
        safe_name = safe_row_id(result_row_id)
        json_path = packet_dir / f"{safe_name}.json"
        md_path = packet_dir / f"{safe_name}.md"
        json_path.write_text(json.dumps(packet, indent=2, ensure_ascii=False), encoding="utf-8")
        md_path.write_text(packet_markdown(packet), encoding="utf-8")
        index_rows.append(
            {
                "bundle_order": packet["bundle_order"],
                "result_row_id": result_row_id,
                "instance_id": packet["instance_id"],
                "repo": packet["repo"],
                "controller": packet["controller"],
                "risk_tier": packet["risk_tier"],
                "difficulty": packet["difficulty"],
                "dry_run_decision": packet["dry_run_plan"]["decision"],  # type: ignore[index]
                "packet_md": str(md_path),
                "packet_json": str(json_path),
            }
        )

    index = pd.DataFrame(index_rows)
    index_path = output_dir / "packet_index.csv"
    summary_path = output_dir / "packet_summary.json"
    readme_path = output_dir / "README.md"
    index.to_csv(index_path, index=False)
    summary = {
        "packet_rows": int(len(index)),
        "packet_tasks": int(index["instance_id"].nunique()),
        "controllers": sorted(index["controller"].astype(str).unique().tolist()),
        "packet_index": str(index_path),
        "packet_dir": str(packet_dir),
        "source_bundle": str(args.bundle_dir),
        "source_task_manifest": str(args.task_manifest),
        "source_dry_run_plans": str(args.dry_run_plans),
        "third_party_execution_performed": False,
        "evidence_status": "no_execution_preparation",
    }
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    write_readme(readme_path, summary)
    print(f"Wrote packet index to {index_path}")
    print(f"Wrote {len(index)} packet rows to {packet_dir}")


if __name__ == "__main__":
    main()
