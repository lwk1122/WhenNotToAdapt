from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


DEFAULT_MANIFEST = Path("exp/results/emse_runtime/manifest_v1/task_manifest.csv")
DEFAULT_MATRIX = Path("exp/results/emse_runtime/manifest_v1/runtime_execution_matrix.csv")
DEFAULT_DRY_RUN_PLANS = Path("exp/results/emse_runtime/dry_run_lmstudio_full_contract_v1/runtime_dry_run_plans.csv")
DEFAULT_PACKET_DIR = Path("exp/results/emse_runtime/isolated_execution_packets_v1/packets")
DEFAULT_OUTPUT_DIR = Path("exp/results/emse_runtime/execution_priority_v1")
PRIMARY_TARGET = "sempc_lite"
PRIMARY_REFERENCE = "rsrc_guarded"
CONTROLLER_ORDER = {
    PRIMARY_TARGET: 1,
    PRIMARY_REFERENCE: 2,
    "static_conservative": 3,
    "minimal_verify": 4,
}
RISK_ORDER = {"high": 3, "mid": 2, "low": 1}


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_inputs(manifest_path: Path, matrix_path: Path, plans_path: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    manifest = pd.read_csv(manifest_path)
    matrix = pd.read_csv(matrix_path)
    plans = pd.read_csv(plans_path)
    for name, frame, required in [
        ("manifest", manifest, {"instance_id", "repo", "risk_tier", "selection_rank"}),
        ("matrix", matrix, {"instance_id", "controller", "execute_status"}),
        ("dry-run plans", plans, {"instance_id", "controller", "decision"}),
    ]:
        missing = sorted(required - set(frame.columns))
        if missing:
            raise ValueError(f"{name} is missing required columns: {', '.join(missing)}")
    return manifest, matrix, plans


def decision_class(target_decision: str, reference_decision: str) -> tuple[str, int]:
    target = str(target_decision)
    reference = str(reference_decision)
    if target == "adapt" and reference == "inherit_baseline":
        return "target_adapt_reference_inherit", 100
    if target == "inherit_baseline" and reference == "adapt":
        return "target_inherit_reference_adapt", 95
    if target == "adapt" and reference == "adapt":
        return "both_primary_adapt", 70
    if target == "inherit_baseline" and reference == "inherit_baseline":
        return "both_primary_inherit", 45
    return "missing_or_unexpected_primary_decision", 0


def build_task_priority(manifest: pd.DataFrame, plans: pd.DataFrame, first_wave_tasks: int) -> pd.DataFrame:
    pivot = plans.pivot_table(
        index="instance_id",
        columns="controller",
        values="decision",
        aggfunc="first",
    ).reset_index()
    planned_work = (
        plans.assign(
            planned_read_count=pd.to_numeric(plans.get("planned_read_count", 0), errors="coerce").fillna(0),
            planned_test_count=pd.to_numeric(plans.get("planned_test_count", 0), errors="coerce").fillna(0),
            planned_patch_attempts=pd.to_numeric(plans.get("planned_patch_attempts", 0), errors="coerce").fillna(0),
        )
        .groupby(["instance_id", "controller"], dropna=False)
        .agg(
            planned_read_count=("planned_read_count", "first"),
            planned_test_count=("planned_test_count", "first"),
            planned_patch_attempts=("planned_patch_attempts", "first"),
        )
        .reset_index()
    )
    target_work = planned_work[planned_work["controller"].eq(PRIMARY_TARGET)].rename(
        columns={
            "planned_read_count": "target_planned_read_count",
            "planned_test_count": "target_planned_test_count",
            "planned_patch_attempts": "target_planned_patch_attempts",
        }
    )[["instance_id", "target_planned_read_count", "target_planned_test_count", "target_planned_patch_attempts"]]
    reference_work = planned_work[planned_work["controller"].eq(PRIMARY_REFERENCE)].rename(
        columns={
            "planned_read_count": "reference_planned_read_count",
            "planned_test_count": "reference_planned_test_count",
            "planned_patch_attempts": "reference_planned_patch_attempts",
        }
    )[["instance_id", "reference_planned_read_count", "reference_planned_test_count", "reference_planned_patch_attempts"]]

    cols = [
        "selection_rank",
        "repo",
        "instance_id",
        "base_commit",
        "risk_tier",
        "difficulty",
        "difficulty_score",
        "problem_tokens",
        "fail_to_pass_count",
        "pass_to_pass_count",
        "gold_patch_files",
        "gold_patch_lines",
        "shadow_risk_score",
        "shadow_selection_score",
    ]
    available_cols = [col for col in cols if col in manifest.columns]
    task = manifest[available_cols].merge(pivot, on="instance_id", how="left")
    task = task.merge(target_work, on="instance_id", how="left").merge(reference_work, on="instance_id", how="left")

    classes = task.apply(
        lambda row: decision_class(row.get(PRIMARY_TARGET, ""), row.get(PRIMARY_REFERENCE, "")),
        axis=1,
        result_type="expand",
    )
    task["primary_decision_class"] = classes[0]
    task["decision_class_score"] = classes[1].astype(int)
    task["risk_balance_score"] = task["risk_tier"].map(RISK_ORDER).fillna(0).astype(int)
    task["planned_work_contrast"] = (
        task["target_planned_read_count"].fillna(0)
        + task["target_planned_test_count"].fillna(0)
        + task["target_planned_patch_attempts"].fillna(0)
        - task["reference_planned_read_count"].fillna(0)
        - task["reference_planned_test_count"].fillna(0)
        - task["reference_planned_patch_attempts"].fillna(0)
    )
    task["execution_priority_score"] = (
        task["decision_class_score"]
        + task["risk_balance_score"]
        + task["planned_work_contrast"].clip(lower=-5, upper=5)
        + pd.to_numeric(task.get("shadow_risk_score", 0), errors="coerce").fillna(0)
    )
    task = task.sort_values(
        ["execution_priority_score", "selection_rank"],
        ascending=[False, True],
    ).reset_index(drop=True)
    task.insert(0, "execution_priority_rank", range(1, len(task) + 1))
    task["execution_wave"] = task["execution_priority_rank"].le(first_wave_tasks).map({True: "first_wave", False: "reserve"})
    return task


def packet_path(packet_dir: Path, instance_id: str, controller: str) -> str:
    return str(packet_dir / f"{instance_id}__{controller}.md")


def build_row_queue(matrix: pd.DataFrame, task_priority: pd.DataFrame, packet_dir: Path) -> pd.DataFrame:
    fields = [
        "execution_priority_rank",
        "execution_wave",
        "primary_decision_class",
        "execution_priority_score",
        "instance_id",
        "repo",
        "risk_tier",
        PRIMARY_TARGET,
        PRIMARY_REFERENCE,
    ]
    queue = matrix.merge(task_priority[fields], on=["instance_id", "repo", "risk_tier"], how="left", suffixes=("", "_priority"))
    queue["suggested_controller_order"] = queue["controller"].map(CONTROLLER_ORDER).fillna(99).astype(int)
    queue["suggested_queue_order"] = (
        queue["execution_priority_rank"].fillna(9999).astype(int) * 10
        + queue["suggested_controller_order"]
    )
    queue["packet_markdown"] = queue.apply(
        lambda row: packet_path(packet_dir, str(row["instance_id"]), str(row["controller"])),
        axis=1,
    )
    queue = queue.sort_values(["suggested_queue_order", "task_order", "controller_order_within_task"]).reset_index(drop=True)
    queue.insert(0, "queue_row", range(1, len(queue) + 1))
    return queue


def markdown_table(frame: pd.DataFrame, max_rows: int = 24) -> str:
    if frame.empty:
        return "_No rows._"
    shown = frame.head(max_rows)

    def fmt(value: object) -> str:
        if pd.isna(value):
            return ""
        if isinstance(value, float):
            return f"{value:.3f}"
        return str(value).replace("|", "\\|").replace("\n", " ")

    cols = list(shown.columns)
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, row in shown.iterrows():
        lines.append("| " + " | ".join(fmt(row[col]) for col in cols) + " |")
    return "\n".join(lines)


def write_report(path: Path, task_priority: pd.DataFrame, row_queue: pd.DataFrame, first_wave_tasks: int) -> None:
    first_wave = task_priority[task_priority["execution_wave"].eq("first_wave")].copy()
    first_queue = row_queue[row_queue["execution_wave"].eq("first_wave")].copy()
    class_counts = task_priority["primary_decision_class"].value_counts().rename_axis("primary_decision_class").reset_index(name="tasks")
    wave_counts = task_priority.groupby(["execution_wave", "primary_decision_class"], dropna=False).size().reset_index(name="tasks")
    risk_counts = first_wave["risk_tier"].value_counts().rename_axis("risk_tier").reset_index(name="first_wave_tasks")
    controller_counts = first_queue["controller"].value_counts().rename_axis("controller").reset_index(name="first_wave_rows")

    lines = [
        "# Controlled Runtime Execution Priority Plan",
        "",
        "This is a no-execution planning artifact. It ranks the existing SWE-bench Verified task-controller rows for a future approved isolated run.",
        "",
        "## Scope",
        "",
        f"- Planned tasks ranked: {len(task_priority)}",
        f"- Recommended first-wave tasks: {min(first_wave_tasks, len(task_priority))}",
        f"- First-wave task-controller rows: {len(first_queue)}",
        f"- Primary comparison: `{PRIMARY_TARGET}` versus `{PRIMARY_REFERENCE}`",
        "",
        "## Priority Rule",
        "",
        "Tasks where the target and reference controllers make different contracted LM Studio prompt-only decisions are ranked first, because those rows are most likely to reveal whether the runtime gate changes work allocation. Risk tier and planned-work contrast are secondary tie-breakers. The ranking does not use any executed tests, patches, or repository inspection.",
        "",
        "## Decision-Class Counts",
        "",
        markdown_table(class_counts),
        "",
        "## First-Wave Composition",
        "",
        "### By Decision Class",
        "",
        markdown_table(wave_counts[wave_counts["execution_wave"].eq("first_wave")]),
        "",
        "### By Risk Tier",
        "",
        markdown_table(risk_counts),
        "",
        "### By Controller Rows",
        "",
        markdown_table(controller_counts),
        "",
        "## First-Wave Tasks",
        "",
        markdown_table(
            first_wave[
                [
                    "execution_priority_rank",
                    "repo",
                    "instance_id",
                    "risk_tier",
                    "primary_decision_class",
                    PRIMARY_TARGET,
                    PRIMARY_REFERENCE,
                    "execution_priority_score",
                ]
            ],
            max_rows=first_wave_tasks,
        ),
        "",
        "## First-Wave Row Queue",
        "",
        markdown_table(
            first_queue[
                [
                    "queue_row",
                    "execution_priority_rank",
                    "instance_id",
                    "controller",
                    "execute_status",
                    "packet_markdown",
                ]
            ],
            max_rows=first_wave_tasks * 4,
        ),
        "",
        "## Use Boundary",
        "",
        "- Do not execute rows unless the controlled-runtime preflight passes in an approved isolated environment.",
        "- Keep target/reference rows for the same `instance_id` paired and record both before paired analysis.",
        "- This priority plan is not solve-rate, resource-savings, patch-quality, or downstream-work evidence.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Plan a no-execution priority queue for controlled-runtime rows.")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--matrix", type=Path, default=DEFAULT_MATRIX)
    parser.add_argument("--dry-run-plans", type=Path, default=DEFAULT_DRY_RUN_PLANS)
    parser.add_argument("--packet-dir", type=Path, default=DEFAULT_PACKET_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--first-wave-tasks", type=int, default=12)
    args = parser.parse_args()

    manifest, matrix, plans = load_inputs(args.manifest, args.matrix, args.dry_run_plans)
    output_dir = ensure_dir(args.output_dir)
    task_priority = build_task_priority(manifest, plans, args.first_wave_tasks)
    row_queue = build_row_queue(matrix, task_priority, args.packet_dir)

    task_path = output_dir / "runtime_task_execution_priority.csv"
    queue_path = output_dir / "runtime_row_execution_queue.csv"
    report_path = output_dir / "runtime_execution_priority_plan.md"
    summary_path = output_dir / "runtime_execution_priority_summary.json"

    task_priority.to_csv(task_path, index=False)
    row_queue.to_csv(queue_path, index=False)
    write_report(report_path, task_priority, row_queue, args.first_wave_tasks)

    first_wave = task_priority[task_priority["execution_wave"].eq("first_wave")]
    summary = {
        "task_priority_csv": str(task_path),
        "row_queue_csv": str(queue_path),
        "report_md": str(report_path),
        "tasks_ranked": int(len(task_priority)),
        "first_wave_tasks": int(len(first_wave)),
        "first_wave_rows": int(row_queue["execution_wave"].eq("first_wave").sum()),
        "primary_target": PRIMARY_TARGET,
        "primary_reference": PRIMARY_REFERENCE,
        "decision_class_counts": task_priority["primary_decision_class"].value_counts().to_dict(),
        "first_wave_decision_class_counts": first_wave["primary_decision_class"].value_counts().to_dict(),
        "safety": "no-execution priority plan; no repository code executed",
    }
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Wrote execution priority report to {report_path}")
    print(f"Wrote task priority CSV to {task_path}")
    print(f"Wrote row queue CSV to {queue_path}")


if __name__ == "__main__":
    main()
