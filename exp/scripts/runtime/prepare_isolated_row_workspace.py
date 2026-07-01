from __future__ import annotations

import argparse
import json
import re
import shlex
from pathlib import Path
from typing import Any

import pandas as pd


DEFAULT_PACKET_INDEX = Path("exp/results/emse_runtime/first_wave_execution_packets_v1/packet_index.csv")
DEFAULT_OUTPUT_DIR = Path("exp/results/emse_runtime/first_wave_workspace_plan_v1")
DEFAULT_BUNDLE_DIR = Path("exp/results/emse_runtime/first_wave_execution_bundle_v1")

REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9_.-]+")


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def safe_name(value: str) -> str:
    return SAFE_NAME_RE.sub("_", value).strip("_")


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Missing packet JSON: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def parse_json_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    text = str(value).strip()
    if not text:
        return []
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return [text]
    if isinstance(parsed, list):
        return [str(item) for item in parsed]
    return [str(parsed)]


def packet_paths(packet_index: Path, result_row_id: str, limit: int) -> list[Path]:
    index = pd.read_csv(packet_index)
    if result_row_id:
        selected = index[index["result_row_id"].astype(str).eq(result_row_id)].copy()
        if selected.empty:
            raise ValueError(f"No packet row found for result_row_id={result_row_id!r}.")
    else:
        selected = index.sort_values(["bundle_order", "controller"]).copy()
        if limit > 0:
            selected = selected.head(limit)
    return [Path(str(path)) for path in selected["packet_json"].tolist()]


def shell_single_quote(value: str) -> str:
    return shlex.quote(value)


def build_agent_prompt(packet: dict[str, Any]) -> str:
    task_text = packet.get("task_text", {})
    dry_run = packet.get("dry_run_plan", {})
    planned_files = parse_json_list(dry_run.get("planned_files_to_inspect"))
    planned_tests = parse_json_list(dry_run.get("planned_tests_to_run"))
    fail_to_pass = parse_json_list(task_text.get("fail_to_pass"))
    prompt = [
        "# Isolated Runtime Row Prompt",
        "",
        "You are operating inside an approved isolated execution environment.",
        "Do not use personal credentials or external services except the configured local model endpoint.",
        "Use only the repository snapshot and bounded tests for this row.",
        "",
        "## Row",
        "",
        f"- Result row ID: `{packet.get('result_row_id', '')}`",
        f"- Repository: `{packet.get('repo', '')}`",
        f"- Instance: `{packet.get('instance_id', '')}`",
        f"- Base commit: `{packet.get('base_commit', '')}`",
        f"- Controller: `{packet.get('controller', '')}`",
        f"- Dry-run decision: `{dry_run.get('decision', '')}`",
        "",
        "## Controller Policy",
        "",
        str(packet.get("controller_policy", "")),
        "",
        "## Dry-Run Plan",
        "",
        f"- Workload risk: `{dry_run.get('workload_risk', '')}`",
        f"- Quality risk: `{dry_run.get('quality_risk', '')}`",
        f"- Planned read count: `{dry_run.get('planned_read_count', '')}`",
        f"- Planned test count: `{dry_run.get('planned_test_count', '')}`",
        f"- Planned patch attempts: `{dry_run.get('planned_patch_attempts', '')}`",
        f"- Stop rule: {dry_run.get('stop_rule', '')}",
        f"- Audit reason: {dry_run.get('audit_reason', '')}",
        "",
        "Patch strategy:",
        "",
        str(dry_run.get("patch_strategy", "")),
        "",
        "Planned files to inspect:",
        "",
        json.dumps(planned_files, indent=2),
        "",
        "Planned tests to run:",
        "",
        json.dumps(planned_tests or fail_to_pass, indent=2),
        "",
        "## Problem Statement",
        "",
        str(task_text.get("problem_statement", "")),
        "",
        "## Hints",
        "",
        str(task_text.get("hints_text", "")),
        "",
        "## Completion Contract",
        "",
        "When the row is complete, report:",
        "",
        "- whether the target tests passed;",
        "- model calls and tokens;",
        "- search/read/tool/test counts;",
        "- patch attempts and patch apply successes;",
        "- files and lines changed;",
        "- failed verification jobs and recovery attempts;",
        "- any post-error extra work.",
    ]
    return "\n".join(prompt) + "\n"


def build_shell_template(packet: dict[str, Any], workspace_dir: Path) -> str:
    repo = str(packet.get("repo", ""))
    if not REPO_RE.match(repo):
        raise ValueError(f"Unsafe repository slug in packet: {repo!r}")
    base_commit = str(packet.get("base_commit", ""))
    tests = parse_json_list(packet.get("dry_run_plan", {}).get("planned_tests_to_run"))
    if not tests:
        tests = parse_json_list(packet.get("task_text", {}).get("fail_to_pass"))
    tests_text = " ".join(shell_single_quote(test) for test in tests)
    repo_url = f"https://github.com/{repo}.git"
    repo_dir = workspace_dir / "repo"
    lines = [
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        "",
        'if [[ "${CAMC_RUNTIME_ISOLATION_ACK:-}" != "1" ]]; then',
        '  echo "CAMC_RUNTIME_ISOLATION_ACK=1 is required inside the approved isolated environment." >&2',
        "  exit 2",
        "fi",
        'if [[ -n "${SSH_AUTH_SOCK:-}" ]]; then',
        '  echo "SSH_AUTH_SOCK must be removed before untrusted repository execution." >&2',
        "  exit 2",
        "fi",
        "",
        f"WORKSPACE={shell_single_quote(str(workspace_dir))}",
        f"REPO_DIR={shell_single_quote(str(repo_dir))}",
        f"REPO_URL={shell_single_quote(repo_url)}",
        f"BASE_COMMIT={shell_single_quote(base_commit)}",
        "",
        'mkdir -p "$WORKSPACE"',
        'if [[ ! -d "$REPO_DIR/.git" ]]; then',
        '  git clone --no-checkout "$REPO_URL" "$REPO_DIR"',
        "fi",
        'git -C "$REPO_DIR" fetch --depth 1 origin "$BASE_COMMIT" || true',
        'git -C "$REPO_DIR" checkout --force "$BASE_COMMIT"',
        "",
        "# Inspect dependencies before installing anything.",
        "# Add repository-specific dependency setup here only after review.",
        "",
        "# Focused tests from the packet. Run only after dependencies are reviewed.",
        f"# python -m pytest {tests_text}",
        "",
        "# After patching and verification, record metrics with record_command.sh.",
    ]
    return "\n".join(lines) + "\n"


def build_record_command(packet: dict[str, Any], bundle_dir: Path, workspace_dir: Path) -> str:
    result_row_id = str(packet.get("result_row_id", ""))
    source_log = workspace_dir / "row_execution.log"
    return (
        "python3 -m exp.scripts.emse_runtime.record_isolated_runtime_result "
        f"--bundle-dir {shell_single_quote(str(bundle_dir))} "
        f"--result-row-id {shell_single_quote(result_row_id)} "
        "--run-id first_wave_runtime_v1 "
        "--execute-status completed "
        "--ack-isolated "
        "--preflight-passed "
        "--sensitive-env-removed "
        "--repo-snapshot-prepared "
        "--dependencies-reviewed "
        "--target-tests-run "
        "--success <0-or-1> "
        "--final-target-test-pass <0-or-1> "
        "--catastrophic-failure <0-or-1> "
        "--search-count <count> "
        "--read-count <count> "
        "--test-runs <count> "
        "--patch-attempts <count> "
        "--patch-apply-successes <count> "
        "--verification-events <count> "
        "--failed-verification-jobs <count> "
        "--recovery-attempts <count> "
        "--post-error-extra-work <count> "
        "--model-calls <count> "
        "--prompt-tokens <count> "
        "--completion-tokens <count> "
        "--total-tokens <count> "
        "--latency-seconds <seconds> "
        "--tool-calls <count> "
        "--context-files <count> "
        "--context-bytes <count> "
        "--files-changed <count> "
        "--lines-changed <count> "
        f"--source-log {shell_single_quote(str(source_log))} "
        "--evidence-note '<brief observed execution evidence>' "
        "--checklist-note '<preflight/checklist evidence summary>'"
    )


def metrics_template() -> dict[str, object]:
    return {
        "success": None,
        "final_target_test_pass": None,
        "catastrophic_failure": None,
        "test_runs": None,
        "verification_events": None,
        "search_count": None,
        "read_count": None,
        "patch_attempts": None,
        "patch_apply_successes": None,
        "fallback_events": None,
        "post_error_extra_work": None,
        "model_calls": None,
        "prompt_tokens": None,
        "completion_tokens": None,
        "total_tokens": None,
        "latency_seconds": None,
        "tool_calls": None,
        "context_files": None,
        "context_bytes": None,
        "files_changed": None,
        "lines_changed": None,
        "failed_verification_jobs": None,
        "recovery_attempts": None,
    }


def write_row_workspace(packet_path: Path, output_dir: Path, bundle_dir: Path) -> dict[str, object]:
    packet = load_json(packet_path)
    result_row_id = str(packet.get("result_row_id", ""))
    if not result_row_id:
        raise ValueError(f"Packet lacks result_row_id: {packet_path}")
    workspace_dir = ensure_dir(output_dir / "rows" / safe_name(result_row_id))
    prompt_path = workspace_dir / "agent_prompt.md"
    shell_path = workspace_dir / "prepare_snapshot.sh"
    record_path = workspace_dir / "record_command.sh"
    metrics_path = workspace_dir / "metrics_template.json"
    summary_path = workspace_dir / "workspace_summary.json"
    readme_path = workspace_dir / "README.md"

    prompt_path.write_text(build_agent_prompt(packet), encoding="utf-8")
    shell_path.write_text(build_shell_template(packet, workspace_dir), encoding="utf-8")
    shell_path.chmod(0o755)
    record_path.write_text(build_record_command(packet, bundle_dir, workspace_dir) + "\n", encoding="utf-8")
    record_path.chmod(0o755)
    metrics_path.write_text(json.dumps(metrics_template(), indent=2) + "\n", encoding="utf-8")

    summary = {
        "result_row_id": result_row_id,
        "repo": packet.get("repo", ""),
        "instance_id": packet.get("instance_id", ""),
        "controller": packet.get("controller", ""),
        "base_commit": packet.get("base_commit", ""),
        "dry_run_decision": packet.get("dry_run_plan", {}).get("decision", ""),
        "workspace_dir": str(workspace_dir),
        "packet_json": str(packet_path),
        "agent_prompt": str(prompt_path),
        "prepare_snapshot_script": str(shell_path),
        "record_command": str(record_path),
        "metrics_template": str(metrics_path),
        "third_party_execution_performed": False,
        "evidence_status": "workspace_plan_only",
    }
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    readme = [
        "# Isolated Row Workspace Plan",
        "",
        "This directory is a preparation artifact only.",
        "Creating it does not clone repositories, install dependencies, apply patches, or run tests.",
        "",
        f"- Result row ID: `{result_row_id}`",
        f"- Repository: `{summary['repo']}`",
        f"- Controller: `{summary['controller']}`",
        f"- Agent prompt: `{prompt_path.name}`",
        f"- Snapshot setup template: `{shell_path.name}`",
        f"- Metrics template: `{metrics_path.name}`",
        f"- Record command template: `{record_path.name}`",
        "",
        "Run `prepare_snapshot.sh` only inside an approved isolated environment with `CAMC_RUNTIME_ISOLATION_ACK=1` and no sensitive environment exposure.",
    ]
    readme_path.write_text("\n".join(readme) + "\n", encoding="utf-8")
    return summary


def frame_to_markdown(frame: pd.DataFrame) -> str:
    headers = list(frame.columns)
    rows = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for _, row in frame.iterrows():
        rows.append("| " + " | ".join(str(row[col]) for col in headers) + " |")
    return "\n".join(rows)


def write_report(path: Path, rows: pd.DataFrame, summary: dict[str, object]) -> None:
    display = rows[
        [
            "result_row_id",
            "repo",
            "controller",
            "dry_run_decision",
            "workspace_dir",
        ]
    ].head(16)
    lines = [
        "# First-Wave Isolated Workspace Plan",
        "",
        "This report is generated without cloning repositories, installing dependencies, applying patches, or running tests.",
        "",
        "## Summary",
        "",
        f"- Rows planned: {summary['rows']}",
        f"- Tasks planned: {summary['tasks']}",
        f"- Controllers: {', '.join(summary['controllers'])}",
        f"- Third-party execution performed: {summary['third_party_execution_performed']}",
        f"- Evidence status: `{summary['evidence_status']}`",
        "",
        "## First Rows",
        "",
        frame_to_markdown(display),
        "",
        "## Use Boundary",
        "",
        "Use these workspaces as operator handoff artifacts inside an approved isolated environment. They are not runtime evidence until rows are executed, metrics are recorded, and validation passes.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare per-row isolated workspace artifacts without executing repositories.")
    parser.add_argument("--packet-index", type=Path, default=DEFAULT_PACKET_INDEX)
    parser.add_argument("--packet-json", type=Path, default=None)
    parser.add_argument("--result-row-id", default="")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--bundle-dir", type=Path, default=DEFAULT_BUNDLE_DIR)
    parser.add_argument("--limit", type=int, default=0, help="Limit rows when selecting from packet index; 0 means all rows.")
    args = parser.parse_args()

    output_dir = ensure_dir(args.output_dir)
    if args.packet_json:
        paths = [args.packet_json]
    else:
        paths = packet_paths(args.packet_index, args.result_row_id, args.limit)
    rows = [write_row_workspace(path, output_dir, args.bundle_dir) for path in paths]
    rows_frame = pd.DataFrame(rows)
    rows_frame.to_csv(output_dir / "workspace_index.csv", index=False)
    summary = {
        "rows": int(len(rows_frame)),
        "tasks": int(rows_frame["instance_id"].nunique()) if not rows_frame.empty else 0,
        "controllers": sorted(rows_frame["controller"].astype(str).unique().tolist()) if not rows_frame.empty else [],
        "output_dir": str(output_dir),
        "packet_index": str(args.packet_index),
        "bundle_dir": str(args.bundle_dir),
        "third_party_execution_performed": False,
        "evidence_status": "workspace_plan_only",
    }
    (output_dir / "workspace_plan_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    write_report(output_dir / "workspace_plan_report.md", rows_frame, summary)
    if not rows_frame.empty:
        first_prompt = Path(str(rows_frame.iloc[0]["agent_prompt"]))
        sample_prompt = output_dir / "sample_agent_prompt.md"
        sample_prompt.write_text(first_prompt.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"Wrote isolated workspace plan to {output_dir / 'workspace_plan_report.md'}")


if __name__ == "__main__":
    try:
        main()
    except (FileNotFoundError, ValueError) as exc:
        raise SystemExit(f"ERROR: {exc}") from None
