from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from .prepare_isolated_execution_bundle import (
    build_checklist,
    build_empty_results,
    ensure_dir,
    frame_to_markdown,
    result_row_id,
)


DEFAULT_QUEUE = Path("exp/results/emse_runtime/execution_priority_v1/runtime_row_execution_queue.csv")
DEFAULT_TASK_PRIORITY = Path("exp/results/emse_runtime/execution_priority_v1/runtime_task_execution_priority.csv")
DEFAULT_OUTPUT_DIR = Path("exp/results/emse_runtime/first_wave_execution_bundle_v1")
DEFAULT_PACKET_DIR = Path("exp/results/emse_runtime/first_wave_execution_packets_v1/packets")
DEFAULT_BUNDLE_ID = "first_wave_bundle_v1"
DEFAULT_WAVE = "first_wave"
PAIR_CONTROLLERS = ("sempc_lite", "rsrc_guarded")


def load_queue(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    required = [
        "queue_row",
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
        "execution_priority_rank",
        "execution_wave",
        "primary_decision_class",
        "execution_priority_score",
        "suggested_controller_order",
        "suggested_queue_order",
        "packet_markdown",
    ]
    missing = [col for col in required if col not in frame.columns]
    if missing:
        raise ValueError(f"Execution queue is missing required columns: {', '.join(missing)}")
    return frame


def load_task_priority(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    required = [
        "execution_priority_rank",
        "repo",
        "instance_id",
        "primary_decision_class",
        "execution_priority_score",
        "execution_wave",
    ]
    missing = [col for col in required if col not in frame.columns]
    if missing:
        raise ValueError(f"Task priority table is missing required columns: {', '.join(missing)}")
    return frame


def select_wave(queue: pd.DataFrame, wave: str) -> pd.DataFrame:
    selected = queue[queue["execution_wave"].astype(str).eq(wave)].copy()
    if selected.empty:
        raise ValueError(f"No rows found for execution_wave={wave!r}.")
    return selected.sort_values(["suggested_queue_order", "queue_row", "controller"]).reset_index(drop=True)


def safe_row_id(value: str) -> str:
    return value.replace("/", "_").replace(":", "_")


def expected_packet_markdown(row: pd.Series, packet_dir: Path) -> str:
    return str(packet_dir / f"{safe_row_id(result_row_id(row))}.md")


def build_first_wave_manifest(rows: pd.DataFrame, output_dir: Path, bundle_id: str, packet_dir: Path) -> pd.DataFrame:
    manifest = rows.copy()
    manifest.insert(0, "bundle_order", range(1, len(manifest) + 1))
    manifest.insert(0, "bundle_id", bundle_id)
    if "packet_markdown" in manifest.columns:
        manifest["source_packet_markdown"] = manifest["packet_markdown"]
    manifest["result_row_id"] = manifest.apply(result_row_id, axis=1)
    manifest["packet_markdown"] = manifest.apply(lambda row: expected_packet_markdown(row, packet_dir), axis=1)
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


def packet_exists(path_value: object) -> bool:
    path = Path(str(path_value))
    return path.exists()


def build_pair_plan(manifest: pd.DataFrame, task_priority: pd.DataFrame) -> pd.DataFrame:
    task_lookup = task_priority.set_index("instance_id", drop=False)
    rows: list[dict[str, object]] = []
    for instance_id, group in manifest.groupby("instance_id", sort=False):
        by_controller = {str(row["controller"]): row for _, row in group.iterrows()}
        pair_rows = {controller: by_controller.get(controller) for controller in PAIR_CONTROLLERS}
        task_row = task_lookup.loc[instance_id] if instance_id in task_lookup.index else None
        if isinstance(task_row, pd.DataFrame):
            task_row = task_row.iloc[0]
        values: dict[str, object] = {
            "execution_priority_rank": int(group["execution_priority_rank"].iloc[0]),
            "instance_id": instance_id,
            "repo": group["repo"].iloc[0],
            "primary_decision_class": group["primary_decision_class"].iloc[0],
            "execution_priority_score": group["execution_priority_score"].iloc[0],
            "controllers_in_bundle": ",".join(group["controller"].astype(str).tolist()),
            "all_controller_rows": int(len(group)),
        }
        if task_row is not None:
            values.update(
                {
                    "risk_tier": task_row.get("risk_tier", ""),
                    "difficulty": task_row.get("difficulty", ""),
                    "problem_tokens": task_row.get("problem_tokens", ""),
                    "gold_patch_files": task_row.get("gold_patch_files", ""),
                    "gold_patch_lines": task_row.get("gold_patch_lines", ""),
                    "planned_work_contrast": task_row.get("planned_work_contrast", ""),
                }
            )
        for controller, row in pair_rows.items():
            prefix = controller.replace("-", "_")
            values[f"{prefix}_present"] = row is not None
            values[f"{prefix}_result_row_id"] = "" if row is None else row["result_row_id"]
            values[f"{prefix}_bundle_order"] = "" if row is None else int(row["bundle_order"])
            values[f"{prefix}_packet_markdown"] = "" if row is None else row["packet_markdown"]
            values[f"{prefix}_packet_exists"] = False if row is None else packet_exists(row["packet_markdown"])
        rows.append(values)
    return pd.DataFrame(rows).sort_values("execution_priority_rank").reset_index(drop=True)


def write_runbook(path: Path, summary: dict[str, object], sample_rows: pd.DataFrame, pair_plan: pd.DataFrame) -> None:
    pair_sample = pair_plan[
        [
            "execution_priority_rank",
            "instance_id",
            "repo",
            "primary_decision_class",
            "sempc_lite_result_row_id",
            "rsrc_guarded_result_row_id",
        ]
    ].head(12)
    lines = [
        "# First-Wave Isolated Runtime Execution Bundle",
        "",
        "## Status",
        "",
        "- This bundle is a no-execution preparation artifact for the first controlled-runtime wave.",
        "- No repository was cloned, inspected, patched, installed, or tested while generating it.",
        "- All result rows are intentionally marked `execute_status=not_run`.",
        "- The runtime validator must reject the empty result template until observed metrics are filled from approved isolated runs.",
        "",
        "## Bundle Contents",
        "",
        f"- Bundle ID: `{summary['bundle_id']}`",
        f"- Selected wave: `{summary['selected_wave']}`",
        f"- Selected rows: {summary['selected_rows']}",
        f"- Selected tasks: {summary['selected_tasks']}",
        f"- Selected controllers: {', '.join(summary['controllers'])}",
        f"- Pair controllers: {', '.join(summary['pair_controllers'])}",
        f"- Source queue: `{summary['source_queue']}`",
        f"- Execution manifest: `{summary['manifest_path']}`",
        f"- Empty result template: `{summary['result_template_path']}`",
        f"- Row checklist: `{summary['checklist_path']}`",
        f"- Pair plan: `{summary['pair_plan_path']}`",
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
        "## Execution Order",
        "",
        "Use `isolated_execution_manifest.csv` as the row-level queue. Keep the paired `sempc_lite` and `rsrc_guarded` rows adjacent for each task, then execute the fixed-controller controls (`static_conservative`, `minimal_verify`) if the row remains within the approved budget.",
        "",
        "For each row:",
        "",
        "1. Open the row packet linked in `packet_markdown`.",
        "2. Prepare a disposable repository snapshot at the specified base commit.",
        "3. Review dependency installation commands before running them.",
        "4. Execute only bounded, task-specific commands inside the isolated environment.",
        "5. Record observed metrics with `record_isolated_runtime_result.py`.",
        "6. Set `execute_status=completed` only after the row's observed metrics are complete.",
        "7. Re-run `validate_runtime_results.py` before any paired analysis.",
        "",
        "`record_isolated_runtime_result.py` appends safely by default: if `runtime_task_results_recorded.csv` already exists in the bundle directory and `--results-in` is not provided, the recorder reads that recorded file before writing the next row. This prevents later row records from resetting earlier completed rows back to the empty template.",
        "",
        "The placeholder `TODO_EXECUTE_IN_APPROVED_ISOLATED_ENV` is intentional. This bundle does not contain an auto-run command for untrusted repositories.",
        "",
        "## Recording Command Template",
        "",
        "```bash",
        ".venv_emse/bin/python -m exp.scripts.emse_runtime.record_isolated_runtime_result \\",
        "  --bundle-dir exp/results/emse_runtime/first_wave_execution_bundle_v1 \\",
        "  --result-row-id <instance_id::controller> \\",
        "  --run-id first_wave_runtime_v1 \\",
        "  --execute-status completed \\",
        "  --ack-isolated \\",
        "  --evidence-note '<short evidence note>' \\",
        "  --success <0-or-1> \\",
        "  --search-count <count> \\",
        "  --read-count <count> \\",
        "  --test-runs <count> \\",
        "  --patch-attempts <count> \\",
        "  --preflight-passed \\",
        "  --sensitive-env-removed \\",
        "  --repo-snapshot-prepared \\",
        "  --dependencies-reviewed \\",
        "  --target-tests-run \\",
        "  --checklist-note '<preflight/checklist evidence summary>'",
        "```",
        "",
        "Only keep checklist flags that are true for the isolated run. Add `--dependencies-installed` only if dependencies were actually installed after review. Add `--validator-passed` only after the recorded results have passed validation.",
        "",
        "## Negative Validation Command",
        "",
        "```bash",
        ".venv_emse/bin/python -m exp.scripts.emse_runtime.validate_runtime_results \\",
        "  --task-results exp/results/emse_runtime/first_wave_execution_bundle_v1/runtime_task_results_empty.csv \\",
        "  --output-dir exp/results/emse_runtime/first_wave_execution_bundle_v1_validation \\",
        "  --target sempc_lite \\",
        "  --reference rsrc_guarded",
        "```",
        "",
        "Expected status before real execution: `FAIL`, because rows are not completed and primary observed metrics are empty.",
        "",
        "## Pair Analysis Command After Validation Passes",
        "",
        "```bash",
        ".venv_emse/bin/python -m exp.scripts.emse_runtime.analyze_runtime_pairs \\",
        "  --task-results exp/results/emse_runtime/first_wave_execution_bundle_v1/runtime_task_results_recorded.csv \\",
        "  --output-dir exp/results/emse_runtime/first_wave_execution_bundle_v1_pair_analysis \\",
        "  --target sempc_lite \\",
        "  --reference rsrc_guarded \\",
        "  --success-margin 0.05 \\",
        "  --min-publication-pairs 30",
        "```",
        "",
        "## Pair Plan",
        "",
        frame_to_markdown(pair_sample),
        "",
        "## Sample Manifest Rows",
        "",
        frame_to_markdown(sample_rows),
        "",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_summary(
    output_dir: Path,
    bundle_id: str,
    wave: str,
    queue_path: Path,
    task_priority_path: Path,
    manifest: pd.DataFrame,
    result_template: pd.DataFrame,
    checklist: pd.DataFrame,
    pair_plan: pd.DataFrame,
    packet_dir: Path,
) -> dict[str, object]:
    controllers = sorted(manifest["controller"].astype(str).unique().tolist())
    decision_classes = manifest.groupby("primary_decision_class")["instance_id"].nunique().to_dict()
    packet_missing_count = int((~pair_plan[[f"{controller}_packet_exists" for controller in PAIR_CONTROLLERS]].all(axis=1)).sum())
    summary = {
        "bundle_id": bundle_id,
        "selected_wave": wave,
        "source_queue": str(queue_path),
        "source_task_priority": str(task_priority_path),
        "output_dir": str(output_dir),
        "manifest_path": str(output_dir / "isolated_execution_manifest.csv"),
        "result_template_path": str(output_dir / "runtime_task_results_empty.csv"),
        "checklist_path": str(output_dir / "row_execution_checklist.csv"),
        "pair_plan_path": str(output_dir / "first_wave_pair_plan.csv"),
        "expected_packet_dir": str(packet_dir),
        "runbook_path": str(output_dir / "execution_runbook.md"),
        "selected_rows": int(len(manifest)),
        "selected_tasks": int(manifest["instance_id"].nunique()),
        "controllers": controllers,
        "pair_controllers": list(PAIR_CONTROLLERS),
        "pair_plan_rows": int(len(pair_plan)),
        "decision_class_task_counts": {str(key): int(value) for key, value in decision_classes.items()},
        "result_column_count": int(len(result_template.columns)),
        "requires_isolation_rows": int(manifest["requires_isolation"].astype(str).str.lower().eq("true").sum()),
        "not_run_result_rows": int(result_template["execute_status"].astype(str).eq("not_run").sum()),
        "checklist_rows": int(len(checklist)),
        "missing_pair_packet_tasks": packet_missing_count,
        "evidence_status": "not_run",
        "third_party_execution_performed": False,
    }
    (output_dir / "first_wave_bundle_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare a no-execution first-wave isolated-runtime bundle from the execution priority queue.")
    parser.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    parser.add_argument("--task-priority", type=Path, default=DEFAULT_TASK_PRIORITY)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--packet-dir", type=Path, default=DEFAULT_PACKET_DIR)
    parser.add_argument("--bundle-id", default=DEFAULT_BUNDLE_ID)
    parser.add_argument("--wave", default=DEFAULT_WAVE)
    args = parser.parse_args()

    queue = load_queue(args.queue)
    task_priority = load_task_priority(args.task_priority)
    selected = select_wave(queue, args.wave)
    output_dir = ensure_dir(args.output_dir)
    manifest = build_first_wave_manifest(selected, output_dir, args.bundle_id, args.packet_dir)
    result_template = build_empty_results(selected, args.bundle_id)
    checklist = build_checklist(manifest)
    pair_plan = build_pair_plan(manifest, task_priority)

    manifest.to_csv(output_dir / "isolated_execution_manifest.csv", index=False)
    result_template.to_csv(output_dir / "runtime_task_results_empty.csv", index=False)
    checklist.to_csv(output_dir / "row_execution_checklist.csv", index=False)
    pair_plan.to_csv(output_dir / "first_wave_pair_plan.csv", index=False)
    summary = write_summary(
        output_dir,
        args.bundle_id,
        args.wave,
        args.queue,
        args.task_priority,
        manifest,
        result_template,
        checklist,
        pair_plan,
        args.packet_dir,
    )
    write_runbook(
        output_dir / "execution_runbook.md",
        summary,
        manifest[
            [
                "bundle_order",
                "queue_row",
                "execution_priority_rank",
                "instance_id",
                "repo",
                "controller",
                "primary_decision_class",
            ]
        ].head(12),
        pair_plan,
    )

    print(f"Prepared first-wave isolated execution bundle: {output_dir}")
    print(f"Rows: {summary['selected_rows']}; tasks: {summary['selected_tasks']}; controllers: {', '.join(summary['controllers'])}")
    print(f"Pair plan rows: {summary['pair_plan_rows']}; missing pair packet tasks: {summary['missing_pair_packet_tasks']}")
    print("Evidence status: not_run")


if __name__ == "__main__":
    main()
