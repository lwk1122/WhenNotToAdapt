from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

import pandas as pd

from .dry_run_controller_harness import ANALYSIS_RESULT_COLUMNS


DEFAULT_MATRIX = Path("exp/results/emse_runtime/manifest_v1/runtime_execution_matrix.csv")
DEFAULT_OUTPUT_DIR = Path("exp/results/emse_runtime/isolated_execution_bundle_v1")
DEFAULT_BUNDLE_ID = "isolated_bundle_v1"

RESULT_COLUMNS = [
    *ANALYSIS_RESULT_COLUMNS,
    "execute_status",
]

CHECKLIST_COLUMNS = [
    "result_row_id",
    "instance_id",
    "repo",
    "controller",
    "preflight_passed",
    "isolation_ack_present",
    "sensitive_env_removed",
    "repo_snapshot_prepared",
    "dependencies_reviewed",
    "dependencies_installed",
    "target_tests_run",
    "observed_metrics_recorded",
    "validator_passed",
    "notes",
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


def load_matrix(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    required = [
        "run_group",
        "task_order",
        "controller_order_within_task",
        "repo",
        "instance_id",
        "base_commit",
        "risk_tier",
        "difficulty",
        "controller",
        "planned_output_dir",
        "execute_status",
        "requires_isolation",
    ]
    missing = [col for col in required if col not in frame.columns]
    if missing:
        raise ValueError(f"Execution matrix is missing required columns: {', '.join(missing)}")
    return frame


def filter_rows(frame: pd.DataFrame, controllers: list[str] | None, max_tasks: int) -> pd.DataFrame:
    out = frame.copy()
    if controllers:
        out = out[out["controller"].astype(str).isin(controllers)].copy()
    if max_tasks > 0:
        task_keys = out[["task_order", "instance_id"]].drop_duplicates().sort_values("task_order")
        keep_instances = set(task_keys.head(max_tasks)["instance_id"].astype(str))
        out = out[out["instance_id"].astype(str).isin(keep_instances)].copy()
    return out.sort_values(["task_order", "controller_order_within_task", "controller"]).reset_index(drop=True)


def result_row_id(row: pd.Series) -> str:
    return f"{row['instance_id']}::{row['controller']}"


def build_bundle_manifest(rows: pd.DataFrame, output_dir: Path, bundle_id: str) -> pd.DataFrame:
    manifest = rows.copy()
    manifest.insert(0, "bundle_order", range(1, len(manifest) + 1))
    manifest.insert(0, "bundle_id", bundle_id)
    manifest["result_row_id"] = manifest.apply(result_row_id, axis=1)
    manifest["result_file"] = str(output_dir / "runtime_task_results_empty.csv")
    manifest["log_dir"] = manifest.apply(
        lambda row: str(output_dir / "logs" / str(row["instance_id"]) / str(row["controller"])),
        axis=1,
    )
    manifest["preflight_required"] = True
    manifest["isolation_ack_required"] = True
    manifest["expected_execution_mode"] = "isolated_runtime"
    manifest["evidence_status"] = "not_run"
    manifest["execution_command_placeholder"] = "TODO_EXECUTE_IN_APPROVED_ISOLATED_ENV"
    return manifest


def build_empty_results(rows: pd.DataFrame, bundle_id: str) -> pd.DataFrame:
    result_rows: list[dict[str, object]] = []
    for _, row in rows.iterrows():
        values = {col: "" for col in RESULT_COLUMNS}
        values.update(
            {
                "run_id": bundle_id,
                "instance_id": row["instance_id"],
                "repo": row["repo"],
                "controller": row["controller"],
                "execution_mode": "isolated_runtime",
                "execute_status": "not_run",
            }
        )
        result_rows.append(values)
    return pd.DataFrame(result_rows, columns=RESULT_COLUMNS)


def build_checklist(manifest: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for _, row in manifest.iterrows():
        values = {col: False for col in CHECKLIST_COLUMNS}
        values.update(
            {
                "result_row_id": row["result_row_id"],
                "instance_id": row["instance_id"],
                "repo": row["repo"],
                "controller": row["controller"],
                "notes": "",
            }
        )
        rows.append(values)
    return pd.DataFrame(rows, columns=CHECKLIST_COLUMNS)


def frame_to_markdown(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "_No rows._"
    headers = list(frame.columns)
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for _, row in frame.iterrows():
        lines.append("| " + " | ".join(str(row[col]) for col in headers) + " |")
    return "\n".join(lines)


def write_runbook(path: Path, summary: dict[str, object], sample_rows: pd.DataFrame) -> None:
    lines = [
        "# Isolated Runtime Execution Bundle",
        "",
        "## Status",
        "",
        "- This bundle is a no-execution preparation artifact.",
        "- No repository was cloned, inspected, patched, installed, or tested while generating it.",
        "- All result rows are intentionally marked `execute_status=not_run`.",
        "- The runtime validator must reject the empty result template until observed metrics are filled from approved isolated runs.",
        "",
        "## Bundle Contents",
        "",
        f"- Bundle ID: `{summary['bundle_id']}`",
        f"- Selected rows: {summary['selected_rows']}",
        f"- Selected tasks: {summary['selected_tasks']}",
        f"- Selected controllers: {', '.join(summary['controllers'])}",
        f"- Source matrix: `{summary['source_matrix']}`",
        f"- Execution manifest: `{summary['manifest_path']}`",
        f"- Empty result template: `{summary['result_template_path']}`",
        f"- Result columns: {summary['result_column_count']}",
        f"- Row checklist: `{summary['checklist_path']}`",
        "",
        "## Required Preflight",
        "",
        "Run this only in the approved isolated execution environment:",
        "",
        "```bash",
        ".venv_emse/bin/python -m exp.scripts.emse_runtime.preflight_runtime_environment",
        "```",
        "",
        "Proceed only if the preflight passes and the isolation decision is explicit. Do not set `CAMC_RUNTIME_ISOLATION_ACK=1` in the ordinary development shell just to silence the guardrail.",
        "",
        "Before executing third-party repositories, remove or isolate sensitive environment variables such as `SSH_AUTH_SOCK`, cloud credentials, package tokens, and personal API keys.",
        "",
        "## Per-Row Execution Contract",
        "",
        "For each row in `isolated_execution_manifest.csv`:",
        "",
        "1. Prepare a disposable repository snapshot at the specified base commit.",
        "2. Review dependency installation commands before running them.",
        "3. Execute only bounded, task-specific commands inside the isolated environment.",
        "4. Record observed metrics in `runtime_task_results_empty.csv` or a copied results file.",
        "5. Set `execute_status=completed` only after the row's observed metrics are complete.",
        "6. Run `validate_runtime_results.py` before any paired analysis.",
        "",
        "`record_isolated_runtime_result.py` appends safely by default: if `runtime_task_results_recorded.csv` already exists in the bundle directory and `--results-in` is not provided, the recorder reads that recorded file before writing the next row. This prevents later row records from resetting earlier completed rows back to the empty template.",
        "",
        "Use recorder checklist flags only for facts that are true for the isolated run: `--preflight-passed`, `--sensitive-env-removed`, `--repo-snapshot-prepared`, `--dependencies-reviewed`, `--dependencies-installed`, `--target-tests-run`, and `--validator-passed`. Use `--checklist-note` to store a short audit note for the row.",
        "",
        "The placeholder `TODO_EXECUTE_IN_APPROVED_ISOLATED_ENV` is intentional. This bundle does not contain an auto-run command for untrusted repositories.",
        "",
        "## Result Schema",
        "",
        "The result template includes primary quality and work metrics plus model/resource fields: `model_calls`, `prompt_tokens`, `completion_tokens`, `total_tokens`, `latency_seconds`, `tool_calls`, `context_files`, `context_bytes`, `files_changed`, `lines_changed`, `failed_verification_jobs`, and `recovery_attempts`.",
        "",
        "## Validation Command",
        "",
        "```bash",
        ".venv_emse/bin/python -m exp.scripts.emse_runtime.validate_runtime_results \\",
        "  --task-results exp/results/emse_runtime/isolated_execution_bundle_v1/runtime_task_results_empty.csv \\",
        "  --output-dir exp/results/emse_runtime/isolated_execution_bundle_v1_validation \\",
        "  --target sempc_lite \\",
        "  --reference rsrc_guarded",
        "```",
        "",
        "Expected status before real execution: `FAIL`, because rows are not completed and primary observed metrics are empty.",
        "",
        "## Analysis Command After Validation Passes",
        "",
        "```bash",
        ".venv_emse/bin/python -m exp.scripts.emse_runtime.analyze_runtime_pairs \\",
        "  --task-results exp/results/emse_runtime/<completed_run>/runtime_task_results.csv \\",
        "  --output-dir exp/results/emse_runtime/<completed_run>_pair_analysis \\",
        "  --target sempc_lite \\",
        "  --reference rsrc_guarded \\",
        "  --success-margin 0.05 \\",
        "  --min-publication-pairs 30",
        "```",
        "",
        "## Sample Rows",
        "",
        frame_to_markdown(sample_rows),
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def write_summary(
    output_dir: Path,
    bundle_id: str,
    matrix_path: Path,
    manifest: pd.DataFrame,
    result_template: pd.DataFrame,
    checklist: pd.DataFrame,
) -> dict[str, object]:
    controllers = sorted(manifest["controller"].astype(str).unique().tolist())
    summary = {
        "bundle_id": bundle_id,
        "source_matrix": str(matrix_path),
        "output_dir": str(output_dir),
        "manifest_path": str(output_dir / "isolated_execution_manifest.csv"),
        "result_template_path": str(output_dir / "runtime_task_results_empty.csv"),
        "checklist_path": str(output_dir / "row_execution_checklist.csv"),
        "runbook_path": str(output_dir / "execution_runbook.md"),
        "selected_rows": int(len(manifest)),
        "selected_tasks": int(manifest["instance_id"].nunique()),
        "controllers": controllers,
        "result_column_count": int(len(result_template.columns)),
        "result_columns": result_template.columns.tolist(),
        "requires_isolation_rows": int(manifest["requires_isolation"].astype(str).str.lower().eq("true").sum()),
        "not_run_result_rows": int(result_template["execute_status"].astype(str).eq("not_run").sum()),
        "checklist_rows": int(len(checklist)),
        "evidence_status": "not_run",
        "third_party_execution_performed": False,
    }
    (output_dir / "runtime_execution_bundle_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare a no-execution isolated-runtime bundle from the SWE-bench execution matrix.")
    parser.add_argument("--matrix", type=Path, default=DEFAULT_MATRIX)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--bundle-id", default=DEFAULT_BUNDLE_ID)
    parser.add_argument("--controllers", nargs="*", default=None, help="Optional controller names, comma-separated or repeated.")
    parser.add_argument("--max-tasks", type=int, default=0, help="Limit to the first N task instances after sorting; 0 keeps all tasks.")
    args = parser.parse_args()

    matrix = load_matrix(args.matrix)
    selected = filter_rows(matrix, parse_controllers(args.controllers), args.max_tasks)
    if selected.empty:
        raise ValueError("No execution rows selected for the isolated bundle.")

    output_dir = ensure_dir(args.output_dir)
    manifest = build_bundle_manifest(selected, output_dir, args.bundle_id)
    result_template = build_empty_results(selected, args.bundle_id)
    checklist = build_checklist(manifest)

    manifest.to_csv(output_dir / "isolated_execution_manifest.csv", index=False)
    result_template.to_csv(output_dir / "runtime_task_results_empty.csv", index=False)
    checklist.to_csv(output_dir / "row_execution_checklist.csv", index=False)
    summary = write_summary(output_dir, args.bundle_id, args.matrix, manifest, result_template, checklist)
    write_runbook(output_dir / "execution_runbook.md", summary, manifest[["bundle_order", "instance_id", "repo", "controller", "risk_tier"]].head(8))

    print(f"Prepared isolated execution bundle: {output_dir}")
    print(f"Rows: {summary['selected_rows']}; tasks: {summary['selected_tasks']}; controllers: {', '.join(summary['controllers'])}")
    print("Evidence status: not_run")


if __name__ == "__main__":
    main()
