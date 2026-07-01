from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from .report_runtime_batch_status import DEFAULT_PREFLIGHT, ensure_dir, read_json_optional


DEFAULT_LAUNCH_SUMMARY = Path("exp/results/emse_runtime/first_wave_launch_sheet_v1/first_wave_launch_summary.json")
DEFAULT_OUTPUT_DIR = Path("exp/results/emse_runtime/preflight_clearance_handoff_v1")
DEFAULT_ISOLATED_PREFLIGHT_DIR = Path("exp/results/emse_runtime/preflight_isolated_v1")
DEFAULT_ISOLATED_LAUNCH_DIR = Path("exp/results/emse_runtime/first_wave_launch_sheet_isolated_v1")


def check_rows(preflight: dict[str, Any]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for check in preflight.get("checks", []):
        rows.append(
            {
                "check": str(check.get("name", "")),
                "current_status": str(check.get("status", "")),
                "current_evidence": str(check.get("evidence", "")),
                "clearance_action": clearance_action(str(check.get("name", "")), str(check.get("status", ""))),
            }
        )
    return rows


def clearance_action(name: str, status: str) -> str:
    if status == "PASS":
        return "No action required unless the isolated shell differs from the current shell."
    if name == "isolation_ack":
        return "Only inside the approved isolated execution shell, set CAMC_RUNTIME_ISOLATION_ACK=1 or provide an approved ack file."
    if name == "sensitive_environment":
        return "Start the isolated shell without SSH_AUTH_SOCK and other personal/cloud/package credentials."
    if name == "lmstudio_models":
        return "Confirm the local LM Studio server is reachable from the isolated shell before row execution."
    return "Resolve this prerequisite before executing any third-party repository row."


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    fieldnames = ["check", "current_status", "current_evidence", "clearance_action"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_report(path: Path, summary: dict[str, Any], rows: list[dict[str, str]]) -> None:
    lines = [
        "# Controlled Runtime Preflight Clearance Handoff",
        "",
        "This is a handoff artifact for clearing the first-wave execution preflight. It does not execute repositories, call LM Studio, install dependencies, apply patches, or run tests.",
        "",
        "## Current State",
        "",
        f"- Current preflight status: `{summary['current_preflight_status']}`",
        f"- Current first-wave launch-ready rows: {summary['current_launch_ready_rows']}",
        f"- Current first-wave blocked rows: {summary['current_launch_blocked_rows']}",
        f"- Third-party execution performed by this script: `{summary['third_party_execution_performed_by_this_script']}`",
        "",
        "## Command Templates",
        "",
        "Run these only after the isolated execution environment is approved. Do not set the isolation acknowledgment in the ordinary development shell just to silence the guardrail.",
        "",
        "```bash",
        summary["isolated_preflight_command"],
        "```",
        "",
        "After a passing isolated preflight, regenerate a launch sheet against that isolated preflight report:",
        "",
        "```bash",
        summary["isolated_launch_sheet_command"],
        "```",
        "",
        "## Clearance Checklist",
        "",
        "| check | current_status | current_evidence | clearance_action |",
        "|---|---|---|---|",
    ]
    for row in rows:
        cells = [
            row["check"].replace("|", "\\|"),
            row["current_status"].replace("|", "\\|"),
            row["current_evidence"].replace("|", "\\|"),
            row["clearance_action"].replace("|", "\\|"),
        ]
        lines.append("| " + " | ".join(cells) + " |")
    lines.extend(
        [
            "",
            "## Evidence Boundary",
            "",
            "A passing preflight only allows controlled runtime rows to be executed in the approved isolated environment. It is not solve-rate, resource-savings, or downstream-work evidence. Publication evidence begins only after completed rows are recorded with observed metrics and pass runtime validation.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare a preflight-clearance handoff without executing repository code.")
    parser.add_argument("--preflight-summary", type=Path, default=DEFAULT_PREFLIGHT)
    parser.add_argument("--launch-summary", type=Path, default=DEFAULT_LAUNCH_SUMMARY)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--isolated-preflight-dir", type=Path, default=DEFAULT_ISOLATED_PREFLIGHT_DIR)
    parser.add_argument("--isolated-launch-dir", type=Path, default=DEFAULT_ISOLATED_LAUNCH_DIR)
    args = parser.parse_args()

    preflight = read_json_optional(args.preflight_summary)
    launch = read_json_optional(args.launch_summary)
    rows = check_rows(preflight)
    fail_checks = [row["check"] for row in rows if row["current_status"] == "FAIL"]
    warn_checks = [row["check"] for row in rows if row["current_status"] == "WARN"]
    output_dir = ensure_dir(args.output_dir)
    isolated_preflight_command = (
        "env -u SSH_AUTH_SOCK CAMC_RUNTIME_ISOLATION_ACK=1 "
        "python3 -m exp.scripts.emse_runtime.preflight_runtime_environment "
        f"--output-dir {args.isolated_preflight_dir}"
    )
    isolated_launch_sheet_command = (
        "python3 -m exp.scripts.emse_runtime.prepare_first_wave_launch_sheet "
        f"--preflight-summary {args.isolated_preflight_dir / 'runtime_preflight_summary.json'} "
        f"--output-dir {args.isolated_launch_dir}"
    )
    summary = {
        "current_preflight_status": str(preflight.get("status", preflight.get("overall_status", "unknown"))),
        "current_fail_checks": fail_checks,
        "current_warn_checks": warn_checks,
        "current_launch_ready_rows": int(launch.get("ready_rows", 0) or 0),
        "current_launch_blocked_rows": int(launch.get("blocked_rows", 0) or 0),
        "source_preflight_summary": str(args.preflight_summary),
        "source_launch_summary": str(args.launch_summary),
        "isolated_preflight_dir": str(args.isolated_preflight_dir),
        "isolated_launch_dir": str(args.isolated_launch_dir),
        "isolated_preflight_command": isolated_preflight_command,
        "isolated_launch_sheet_command": isolated_launch_sheet_command,
        "third_party_execution_performed_by_this_script": False,
    }
    write_csv(output_dir / "preflight_clearance_checklist.csv", rows)
    (output_dir / "preflight_clearance_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    write_report(output_dir / "preflight_clearance_handoff.md", summary, rows)
    print(f"Wrote preflight-clearance handoff to {output_dir / 'preflight_clearance_handoff.md'}")


if __name__ == "__main__":
    main()
