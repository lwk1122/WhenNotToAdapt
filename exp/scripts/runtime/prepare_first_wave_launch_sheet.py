from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

from .report_first_wave_status import (
    FIRST_WAVE_BUNDLE_DIR,
    FIRST_WAVE_CHECKLIST,
    FIRST_WAVE_MATRIX,
    FIRST_WAVE_OUTPUT_DIR,
    FIRST_WAVE_PACKET_INDEX,
    resolve_task_results,
)
from .report_runtime_batch_status import DEFAULT_PREFLIGHT, ensure_dir, frame_to_markdown, read_json_optional
from .validate_runtime_results import COMPLETED_STATUSES


DEFAULT_OUTPUT_DIR = Path("exp/results/emse_runtime/first_wave_launch_sheet_v1")
PRIMARY_CHECKLIST_FLAGS = [
    "preflight_passed",
    "isolation_ack_present",
    "sensitive_env_removed",
    "repo_snapshot_prepared",
    "dependencies_reviewed",
    "dependencies_installed",
    "target_tests_run",
    "observed_metrics_recorded",
    "validator_passed",
]


def read_csv_required(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing required CSV: {path}")
    return pd.read_csv(path)


def bool_value(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def completed_status(value: object) -> bool:
    return str(value).strip().lower() in COMPLETED_STATUSES


def compact_blockers(items: list[str]) -> str:
    return "; ".join(items) if items else ""


def record_command_template(bundle_dir: Path, result_row_id: str) -> str:
    return (
        "python3 -m exp.scripts.emse_runtime.record_isolated_runtime_result "
        f"--bundle-dir {bundle_dir} "
        f"--result-row-id {result_row_id} "
        "--execute-status completed "
        "--ack-isolated "
        "--preflight-passed "
        "--sensitive-env-removed "
        "--repo-snapshot-prepared "
        "--dependencies-reviewed "
        "--dependencies-installed "
        "--target-tests-run "
        "--validator-passed "
        "--success <0-or-1> "
        "--search-count <count> "
        "--read-count <count> "
        "--test-runs <count> "
        "--patch-attempts <count> "
        "--model-calls <count> "
        "--prompt-tokens <count> "
        "--completion-tokens <count> "
        "--total-tokens <count> "
        "--latency-seconds <seconds> "
        "--source-log <path-to-row-log> "
        "--evidence-note '<brief observed execution evidence>'"
    )


def preview_command(bundle_dir: Path, result_row_id: str) -> str:
    return (
        "python3 -m exp.scripts.emse_runtime.record_isolated_runtime_result "
        f"--bundle-dir {bundle_dir} "
        f"--result-row-id {result_row_id} "
        "--preview-only"
    )


def build_launch_sheet(
    manifest: pd.DataFrame,
    packets: pd.DataFrame,
    checklist: pd.DataFrame,
    results: pd.DataFrame,
    preflight: dict[str, Any],
    bundle_dir: Path,
) -> pd.DataFrame:
    packet_cols = ["result_row_id", "dry_run_decision", "packet_md", "packet_json"]
    packet_lookup = packets[packet_cols].copy() if set(packet_cols).issubset(packets.columns) else pd.DataFrame()
    checklist_lookup = checklist.copy()
    result_lookup = results[["instance_id", "controller", "execute_status"]].copy()
    result_lookup = result_lookup.rename(columns={"execute_status": "current_execute_status"})

    rows = manifest.merge(packet_lookup, on="result_row_id", how="left", suffixes=("", "_packet_index"))
    rows = rows.merge(checklist_lookup, on=["result_row_id", "instance_id", "repo", "controller"], how="left")
    rows = rows.merge(result_lookup, on=["instance_id", "controller"], how="left")

    preflight_status = str(preflight.get("status", preflight.get("overall_status", "unknown")))
    preflight_passed = preflight_status.upper() == "PASS"
    out_rows: list[dict[str, Any]] = []
    for _, row in rows.sort_values(["bundle_order", "controller"]).iterrows():
        result_row_id = str(row["result_row_id"])
        packet_md = Path(str(row.get("packet_md", "")))
        packet_json = Path(str(row.get("packet_json", "")))
        packet_files_present = bool(packet_md.exists() and packet_json.exists())
        current_status = str(row.get("current_execute_status", row.get("execute_status", "not_run")))
        is_completed = completed_status(current_status)
        checklist_values = {
            flag: bool_value(row.get(flag, False))
            for flag in PRIMARY_CHECKLIST_FLAGS
        }
        missing_recording_checks = [
            flag
            for flag, value in checklist_values.items()
            if not value
        ]
        blockers: list[str] = []
        if not preflight_passed:
            blockers.append(f"preflight_status={preflight_status}")
        if not packet_files_present:
            blockers.append("missing_packet_file")
        if is_completed:
            blockers.append("already_completed")
        ready_to_execute = not blockers
        action = "execute_in_approved_isolated_env" if ready_to_execute else "blocked_until_prerequisites_clear"
        out_row = {
            "launch_order": int(row.get("bundle_order", len(out_rows) + 1)),
            "result_row_id": result_row_id,
            "repo": str(row["repo"]),
            "instance_id": str(row["instance_id"]),
            "controller": str(row["controller"]),
            "primary_decision_class": str(row.get("primary_decision_class", "")),
            "dry_run_decision": str(row.get("dry_run_decision", "")),
            "risk_tier": str(row.get("risk_tier", "")),
            "difficulty": str(row.get("difficulty", "")),
            "current_execute_status": current_status,
            "preflight_status": preflight_status,
            "packet_files_present": packet_files_present,
            "ready_to_execute": ready_to_execute,
            "operator_action": action,
            "blockers": compact_blockers(blockers),
            "recording_checklist_complete": not missing_recording_checks,
            "recording_checklist_missing": compact_blockers(missing_recording_checks),
            "packet_md": str(packet_md),
            "packet_json": str(packet_json),
            "log_dir": str(row.get("log_dir", "")),
            "record_preview_command": preview_command(bundle_dir, result_row_id),
            "record_completed_command_template": record_command_template(bundle_dir, result_row_id),
        }
        out_row.update(checklist_values)
        out_rows.append(out_row)
    return pd.DataFrame(out_rows)


def write_report(path: Path, sheet: pd.DataFrame, summary: dict[str, Any]) -> None:
    display_cols = [
        "launch_order",
        "result_row_id",
        "repo",
        "controller",
        "dry_run_decision",
        "current_execute_status",
        "ready_to_execute",
        "blockers",
    ]
    preview = sheet[display_cols].head(16).copy()
    lines = [
        "# First-Wave Operator Launch Sheet",
        "",
        "This is an execution-control artifact. It does not execute repositories, call LM Studio, install dependencies, apply patches, or run tests.",
        "",
        "## Summary",
        "",
        f"- Rows: {summary['rows']}",
        f"- Tasks: {summary['tasks']}",
        f"- Repositories: {summary['repositories']}",
        f"- Ready rows: {summary['ready_rows']}",
        f"- Blocked rows: {summary['blocked_rows']}",
        f"- Preflight status: `{summary['preflight_status']}`",
        f"- Selected result source: `{summary['selected_results_kind']}`",
        f"- Third-party execution performed by this script: `{summary['third_party_execution_performed_by_this_script']}`",
        "",
        "## First Rows",
        "",
        frame_to_markdown(preview),
        "",
        "## Use Boundary",
        "",
        "Use this sheet to assign and record first-wave rows after an approved isolated preflight. Rows with pre-execution blockers must not be executed as publication evidence. Checklist columns track what has been recorded for completed rows; missing checklist flags on a not-run row are not themselves pre-execution blockers.",
        "",
        "## Next Steps",
        "",
        "1. Clear preflight blockers in the approved isolated environment.",
        "2. Execute rows in `launch_order` only after `ready_to_execute=True` or after explicitly documenting why the row-specific blocker has been resolved.",
        "3. Record completed rows with the generated `record_completed_command_template` and observed metrics.",
        "4. Re-run first-wave status, runtime validation, paired analysis, and artifact validation.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare a first-wave operator launch sheet without executing repository code.")
    parser.add_argument("--manifest", type=Path, default=FIRST_WAVE_MATRIX)
    parser.add_argument("--packet-index", type=Path, default=FIRST_WAVE_PACKET_INDEX)
    parser.add_argument("--checklist", type=Path, default=FIRST_WAVE_CHECKLIST)
    parser.add_argument("--task-results", type=Path, default=None)
    parser.add_argument("--preflight-summary", type=Path, default=DEFAULT_PREFLIGHT)
    parser.add_argument("--bundle-dir", type=Path, default=FIRST_WAVE_BUNDLE_DIR)
    parser.add_argument("--status-output-dir", type=Path, default=FIRST_WAVE_OUTPUT_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    selected_results, selected_kind = resolve_task_results(args.task_results)
    manifest = read_csv_required(args.manifest)
    packets = read_csv_required(args.packet_index)
    checklist = read_csv_required(args.checklist)
    results = read_csv_required(selected_results)
    preflight = read_json_optional(args.preflight_summary)

    output_dir = ensure_dir(args.output_dir)
    sheet = build_launch_sheet(manifest, packets, checklist, results, preflight, args.bundle_dir)
    summary = {
        "rows": int(len(sheet)),
        "tasks": int(sheet["instance_id"].nunique()) if "instance_id" in sheet.columns else 0,
        "repositories": int(sheet["repo"].nunique()) if "repo" in sheet.columns else 0,
        "ready_rows": int(sheet["ready_to_execute"].sum()) if "ready_to_execute" in sheet.columns else 0,
        "blocked_rows": int((~sheet["ready_to_execute"]).sum()) if "ready_to_execute" in sheet.columns else 0,
        "preflight_status": str(preflight.get("status", preflight.get("overall_status", "unknown"))),
        "selected_results_kind": selected_kind,
        "selected_task_results": str(selected_results),
        "source_manifest": str(args.manifest),
        "source_packet_index": str(args.packet_index),
        "source_checklist": str(args.checklist),
        "source_preflight_summary": str(args.preflight_summary),
        "third_party_execution_performed_by_this_script": False,
        "status_output_dir": str(args.status_output_dir),
    }
    sheet.to_csv(output_dir / "first_wave_operator_launch_sheet.csv", index=False)
    (output_dir / "first_wave_launch_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    write_report(output_dir / "first_wave_operator_launch_sheet.md", sheet, summary)
    print(f"Wrote first-wave operator launch sheet to {output_dir / 'first_wave_operator_launch_sheet.md'}")


if __name__ == "__main__":
    try:
        main()
    except (FileNotFoundError, ValueError) as exc:
        raise SystemExit(f"ERROR: {exc}") from None
