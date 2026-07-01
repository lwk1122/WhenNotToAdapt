from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


DEFAULT_CONTROLLERS = ["static_conservative", "rsrc_guarded", "sempc_lite", "minimal_verify"]


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def build_matrix(manifest: pd.DataFrame, controllers: list[str], output_root: Path, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows: list[dict[str, object]] = []
    manifest_order = manifest.copy().reset_index(drop=True)
    manifest_order["task_order"] = np.arange(1, len(manifest_order) + 1)

    for _, task in manifest_order.iterrows():
        controller_order = list(controllers)
        rng.shuffle(controller_order)
        for controller_idx, controller in enumerate(controller_order, start=1):
            instance_id = str(task["instance_id"])
            rows.append(
                {
                    "run_group": "manifest_v1_first_batch",
                    "task_order": int(task["task_order"]),
                    "controller_order_within_task": controller_idx,
                    "repo": task.get("repo", ""),
                    "instance_id": instance_id,
                    "base_commit": task.get("base_commit", ""),
                    "risk_tier": task.get("risk_tier", ""),
                    "difficulty": task.get("difficulty", ""),
                    "controller": controller,
                    "planned_output_dir": str(output_root / "manifest_v1_first_batch" / instance_id / controller),
                    "execute_status": "not_run",
                    "requires_isolation": True,
                    "notes": "Do not execute outside approved isolated runtime.",
                }
            )
    return pd.DataFrame(rows)


def write_report(path: Path, matrix: pd.DataFrame, manifest_path: Path) -> None:
    controller_counts = matrix["controller"].value_counts().sort_index()
    risk_counts = matrix.drop_duplicates("instance_id")["risk_tier"].value_counts().sort_index()
    lines = [
        "# Controlled Runtime Execution Matrix",
        "",
        f"Manifest: `{manifest_path}`",
        "",
        "This execution matrix expands the task manifest into task-controller rows for the controlled runtime study.",
        "It does not execute repository code. Rows are marked `not_run` until completed inside an approved isolated environment.",
        "",
        "## Scope",
        "",
        f"- Unique tasks: {matrix['instance_id'].nunique()}",
        f"- Repositories: {matrix['repo'].nunique()}",
        f"- Planned task-controller runs: {len(matrix)}",
        f"- Controllers: {', '.join(controller_counts.index.tolist())}",
        f"- Risk tiers: {', '.join(f'{tier}={count}' for tier, count in risk_counts.items())}",
        "",
        "## Controller Counts",
        "",
        "| controller | planned_runs |",
        "| --- | ---: |",
    ]
    for controller, count in controller_counts.items():
        lines.append(f"| {controller} | {int(count)} |")
    lines.extend(
        [
            "",
            "## Use",
            "",
            "- Treat this as a first-batch or pilot matrix, not a complete publication-grade sample.",
            "- Run each row only inside the approved isolated environment described in `paper/emse_controlled_runtime_protocol.md`.",
            "- After execution, append observed metrics to the runtime task-results CSV and analyze with `analyze_runtime_pairs.py`.",
            "- Keep unfinished rows as `not_run`; do not treat planned rows as evidence.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a no-execution task-controller matrix for controlled runtime experiments.")
    parser.add_argument("--manifest", type=Path, default=Path("exp/results/emse_runtime/manifest_v1/task_manifest.csv"))
    parser.add_argument("--output-dir", type=Path, default=Path("exp/results/emse_runtime/manifest_v1"))
    parser.add_argument("--output-root", type=Path, default=Path("exp/results/emse_runtime/runs"))
    parser.add_argument("--controllers", nargs="*", default=DEFAULT_CONTROLLERS)
    parser.add_argument("--seed", type=int, default=23)
    args = parser.parse_args()

    manifest = pd.read_csv(args.manifest)
    if "instance_id" not in manifest.columns:
        raise ValueError("Manifest must contain an instance_id column.")
    output_dir = ensure_dir(args.output_dir)
    matrix = build_matrix(manifest, args.controllers, args.output_root, args.seed)
    matrix_path = output_dir / "runtime_execution_matrix.csv"
    report_path = output_dir / "runtime_execution_matrix.md"
    matrix.to_csv(matrix_path, index=False)
    write_report(report_path, matrix, args.manifest)
    print(f"Wrote runtime execution matrix to {matrix_path}")
    print(f"Wrote runtime execution matrix report to {report_path}")


if __name__ == "__main__":
    main()
