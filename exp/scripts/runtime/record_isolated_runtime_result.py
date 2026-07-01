from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import pandas as pd

from .dry_run_controller_harness import ANALYSIS_RESULT_COLUMNS
from .validate_runtime_results import COMPLETED_STATUSES


DEFAULT_BUNDLE_DIR = Path("exp/results/emse_runtime/isolated_execution_bundle_v1")
DEFAULT_RESULTS_NAME = "runtime_task_results_empty.csv"
DEFAULT_RECORDED_RESULTS_NAME = "runtime_task_results_recorded.csv"

RESULT_COLUMNS = [
    *ANALYSIS_RESULT_COLUMNS,
    "execute_status",
]

PRIMARY_METRICS = ["success", "search_count", "read_count", "test_runs", "patch_attempts"]
BINARY_METRICS = ["success", "final_target_test_pass", "catastrophic_failure"]
COUNT_METRICS = [
    "test_runs",
    "verification_events",
    "search_count",
    "read_count",
    "patch_attempts",
    "patch_apply_successes",
    "fallback_events",
    "post_error_extra_work",
    "model_calls",
    "prompt_tokens",
    "completion_tokens",
    "total_tokens",
    "tool_calls",
    "context_files",
    "context_bytes",
    "files_changed",
    "lines_changed",
    "failed_verification_jobs",
    "recovery_attempts",
]
FLOAT_METRICS = ["best_problem_reduction", "final_problem_reduction", "latency_seconds"]
CHECKLIST_FLAG_COLUMNS = [
    "preflight_passed",
    "sensitive_env_removed",
    "repo_snapshot_prepared",
    "dependencies_reviewed",
    "dependencies_installed",
    "target_tests_run",
    "validator_passed",
]


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def clean_json_value(value: object) -> object:
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value


def safe_row_id(value: str) -> str:
    return value.replace("/", "_").replace(":", "_")


def load_bundle(bundle_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame, Path, Path]:
    manifest_path = bundle_dir / "isolated_execution_manifest.csv"
    results_path = bundle_dir / DEFAULT_RESULTS_NAME
    if not manifest_path.exists():
        raise FileNotFoundError(f"Missing execution manifest: {manifest_path}")
    if not results_path.exists():
        raise FileNotFoundError(f"Missing result template: {results_path}")
    return pd.read_csv(manifest_path), pd.read_csv(results_path), manifest_path, results_path


def select_manifest_row(manifest: pd.DataFrame, instance_id: str, controller: str, result_row_id: str) -> pd.Series:
    if result_row_id:
        selected = manifest[manifest["result_row_id"].astype(str).eq(result_row_id)]
    else:
        if not instance_id or not controller:
            raise ValueError("Provide either --result-row-id or both --instance-id and --controller.")
        selected = manifest[
            manifest["instance_id"].astype(str).eq(instance_id)
            & manifest["controller"].astype(str).eq(controller)
        ]
    if selected.empty:
        raise ValueError("No matching row found in isolated execution manifest.")
    if len(selected) > 1:
        raise ValueError("Multiple matching rows found in isolated execution manifest.")
    return selected.iloc[0]


def ensure_result_columns(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    for col in RESULT_COLUMNS:
        if col not in out.columns:
            out[col] = ""
    extras = [col for col in out.columns if col not in RESULT_COLUMNS]
    return out[[*RESULT_COLUMNS, *extras]]


def metric_values(args: argparse.Namespace) -> dict[str, int | float]:
    values: dict[str, int | float] = {}
    for col in [*BINARY_METRICS, *COUNT_METRICS, *FLOAT_METRICS]:
        value = getattr(args, col, None)
        if value is not None:
            values[col] = value
    return values


def validate_metrics(values: dict[str, int | float], execute_status: str) -> None:
    status = execute_status.lower()
    for col in BINARY_METRICS:
        if col in values and values[col] not in {0, 1}:
            raise ValueError(f"{col} must be 0 or 1.")
    for col in COUNT_METRICS:
        if col in values and values[col] < 0:
            raise ValueError(f"{col} must be non-negative.")
    for col in ["best_problem_reduction", "final_problem_reduction"]:
        if col in values and not (0.0 <= float(values[col]) <= 1.0):
            raise ValueError(f"{col} must be between 0 and 1.")
    if "latency_seconds" in values and values["latency_seconds"] < 0:
        raise ValueError("latency_seconds must be non-negative.")
    if status in COMPLETED_STATUSES:
        missing = [col for col in PRIMARY_METRICS if col not in values]
        if missing:
            raise ValueError(f"Completed rows require primary observed metrics: {', '.join(missing)}")


def require_execution_provenance(args: argparse.Namespace) -> None:
    status = args.execute_status.lower()
    if status not in COMPLETED_STATUSES:
        return
    ack_env = os.environ.get(args.ack_env, "")
    if not args.ack_isolated and ack_env != "1":
        raise ValueError(f"Recording a completed row requires --ack-isolated or {args.ack_env}=1.")
    if not args.evidence_note:
        raise ValueError("Recording a completed row requires --evidence-note.")


def update_results(
    results: pd.DataFrame,
    manifest_row: pd.Series,
    values: dict[str, int | float],
    execute_status: str,
    run_id: str,
) -> pd.DataFrame:
    out = ensure_result_columns(results)
    instance_id = str(manifest_row["instance_id"])
    controller = str(manifest_row["controller"])
    mask = out["instance_id"].astype(str).eq(instance_id) & out["controller"].astype(str).eq(controller)
    if not mask.any():
        new_row = {col: "" for col in out.columns}
        new_row.update(
            {
                "run_id": run_id,
                "instance_id": instance_id,
                "repo": manifest_row["repo"],
                "controller": controller,
                "execution_mode": "isolated_runtime",
            }
        )
        out = pd.concat([out, pd.DataFrame([new_row])], ignore_index=True)
        mask = out["instance_id"].astype(str).eq(instance_id) & out["controller"].astype(str).eq(controller)
    if int(mask.sum()) != 1:
        raise ValueError("Result table must contain exactly one row for the selected instance/controller.")
    row_index = out.index[mask][0]
    out.loc[row_index, "run_id"] = run_id
    out.loc[row_index, "instance_id"] = instance_id
    out.loc[row_index, "repo"] = manifest_row["repo"]
    out.loc[row_index, "controller"] = controller
    out.loc[row_index, "execution_mode"] = "isolated_runtime"
    out.loc[row_index, "execute_status"] = execute_status
    for col, value in values.items():
        out.loc[row_index, col] = value
    return out


def checklist_updates(args: argparse.Namespace, execute_status: str) -> dict[str, bool]:
    updates = {
        col: True
        for col in CHECKLIST_FLAG_COLUMNS
        if bool(getattr(args, col, False))
    }
    status = execute_status.lower()
    if status in COMPLETED_STATUSES:
        updates["observed_metrics_recorded"] = True
        if args.ack_isolated or os.environ.get(args.ack_env, "") == "1":
            updates["isolation_ack_present"] = True
    return updates


def update_checklist(
    bundle_dir: Path,
    result_row_id: str,
    updates: dict[str, bool],
    note: str,
) -> None:
    checklist_path = bundle_dir / "row_execution_checklist.csv"
    if not checklist_path.exists():
        return
    checklist = pd.read_csv(checklist_path)
    if "result_row_id" not in checklist.columns:
        return
    mask = checklist["result_row_id"].astype(str).eq(result_row_id)
    if not mask.any():
        return
    for col, value in updates.items():
        if col in checklist.columns:
            checklist.loc[mask, col] = bool(value)
    if note and "notes" in checklist.columns:
        checklist["notes"] = checklist["notes"].astype("object")
        existing = checklist.loc[mask, "notes"].fillna("").astype(str)
        checklist.loc[mask, "notes"] = existing.apply(lambda value: note if not value else f"{value}; {note}")
    checklist.to_csv(checklist_path, index=False)


def write_record(
    output_dir: Path,
    manifest_row: pd.Series,
    values: dict[str, int | float],
    args: argparse.Namespace,
    results_in: Path | None,
    results_out: Path | None,
) -> tuple[Path, Path]:
    ensure_dir(output_dir)
    result_row_id = str(manifest_row["result_row_id"])
    record = {
        "result_row_id": result_row_id,
        "instance_id": str(manifest_row["instance_id"]),
        "repo": str(manifest_row["repo"]),
        "controller": str(manifest_row["controller"]),
        "execute_status": args.execute_status,
        "metrics": values,
        "checklist_updates": checklist_updates(args, args.execute_status),
        "checklist_note": args.checklist_note,
        "evidence_note": args.evidence_note,
        "operator": args.operator,
        "source_log": str(args.source_log) if args.source_log else "",
        "results_in": str(results_in) if results_in else "",
        "results_out": str(results_out) if results_out else "",
        "preview_only": bool(args.preview_only),
        "safety": "This script records observed metrics only; it does not clone repositories, install dependencies, apply patches, or run tests.",
        "manifest_row": {key: clean_json_value(value) for key, value in manifest_row.to_dict().items()},
    }
    json_path = output_dir / f"{safe_row_id(result_row_id)}.json"
    md_path = output_dir / f"{safe_row_id(result_row_id)}.md"
    json_path.write_text(json.dumps(record, indent=2), encoding="utf-8")
    lines = [
        "# Isolated Runtime Row Record",
        "",
        f"- Row: `{result_row_id}`",
        f"- Repository: `{record['repo']}`",
        f"- Controller: `{record['controller']}`",
        f"- Execute status: `{args.execute_status}`",
        f"- Preview only: {bool(args.preview_only)}",
        f"- Results input: `{record['results_in']}`",
        f"- Results output: `{record['results_out']}`",
        "",
        "## Metrics",
        "",
    ]
    if values:
        lines.extend(["| metric | value |", "|---|---:|"])
        for key in sorted(values):
            lines.append(f"| `{key}` | {values[key]} |")
    else:
        lines.append("_No observed metrics were provided._")
    updates = checklist_updates(args, args.execute_status)
    lines.extend(["", "## Checklist Updates", ""])
    if updates:
        lines.extend(["| check | value |", "|---|---|"])
        for key in sorted(updates):
            lines.append(f"| `{key}` | {updates[key]} |")
    else:
        lines.append("_No checklist updates were requested._")
    if args.checklist_note:
        lines.extend(["", f"Checklist note: {args.checklist_note}"])
    lines.extend(
        [
            "",
            "## Evidence Note",
            "",
            args.evidence_note or "_No evidence note provided._",
            "",
            "## Safety Boundary",
            "",
            "This record was generated without cloning repositories, installing dependencies, applying patches, or running tests.",
        ]
    )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Record observed metrics for one isolated runtime row without executing repository code.")
    parser.add_argument("--bundle-dir", type=Path, default=DEFAULT_BUNDLE_DIR)
    parser.add_argument("--result-row-id", default="")
    parser.add_argument("--instance-id", default="")
    parser.add_argument("--controller", default="")
    parser.add_argument("--results-in", type=Path, default=None)
    parser.add_argument("--results-out", type=Path, default=None)
    parser.add_argument("--run-id", default="isolated_bundle_v1")
    parser.add_argument("--execute-status", default="not_run")
    parser.add_argument("--preview-only", action="store_true")
    parser.add_argument("--ack-isolated", action="store_true")
    parser.add_argument("--ack-env", default="CAMC_RUNTIME_ISOLATION_ACK")
    parser.add_argument("--evidence-note", default="")
    parser.add_argument("--operator", default="")
    parser.add_argument("--source-log", type=Path, default=None)
    parser.add_argument("--record-dir", type=Path, default=None)
    parser.add_argument("--no-update-checklist", action="store_true")
    parser.add_argument("--checklist-note", default="")

    for col in BINARY_METRICS:
        parser.add_argument(f"--{col.replace('_', '-')}", type=int)
    for col in COUNT_METRICS:
        parser.add_argument(f"--{col.replace('_', '-')}", type=int)
    for col in FLOAT_METRICS:
        parser.add_argument(f"--{col.replace('_', '-')}", type=float)
    for col in CHECKLIST_FLAG_COLUMNS:
        parser.add_argument(f"--{col.replace('_', '-')}", action="store_true")

    args = parser.parse_args()

    manifest, default_results, _, default_results_path = load_bundle(args.bundle_dir)
    manifest_row = select_manifest_row(manifest, args.instance_id, args.controller, args.result_row_id)
    values = metric_values(args)
    validate_metrics(values, args.execute_status)

    if not args.preview_only:
        require_execution_provenance(args)

    results_out = args.results_out or (args.bundle_dir / DEFAULT_RECORDED_RESULTS_NAME)
    default_recorded_path = args.bundle_dir / DEFAULT_RECORDED_RESULTS_NAME
    if args.results_in:
        results_in = args.results_in
    elif default_recorded_path.exists():
        results_in = default_recorded_path
    else:
        results_in = default_results_path
    results = pd.read_csv(results_in) if results_in != default_results_path else default_results
    record_dir = args.record_dir or (args.bundle_dir / "row_records")

    if args.preview_only:
        json_path, md_path = write_record(record_dir, manifest_row, values, args, results_in, None)
        print(f"Wrote row preview record to {json_path}")
        print(f"Wrote row preview report to {md_path}")
        return

    updated = update_results(results, manifest_row, values, args.execute_status, args.run_id)
    updated.to_csv(results_out, index=False)
    if not args.no_update_checklist:
        update_checklist(
            args.bundle_dir,
            str(manifest_row["result_row_id"]),
            checklist_updates(args, args.execute_status),
            args.checklist_note,
        )
    json_path, md_path = write_record(record_dir, manifest_row, values, args, results_in, results_out)
    print(f"Wrote updated results to {results_out}")
    print(f"Read prior results from {results_in}")
    print(f"Wrote row record to {json_path}")
    print(f"Wrote row report to {md_path}")


if __name__ == "__main__":
    try:
        main()
    except (FileNotFoundError, ValueError) as exc:
        raise SystemExit(f"ERROR: {exc}") from None
