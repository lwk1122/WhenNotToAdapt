from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pandas as pd

from .dry_run_controller_harness import ANALYSIS_RESULT_COLUMNS


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_BUNDLE_DIR = Path("exp/results/emse_runtime/first_wave_execution_bundle_v1")
DEFAULT_TASK_MANIFEST = Path("exp/results/emse_runtime/manifest_v1/task_manifest.csv")
DEFAULT_OUTPUT_DIR = Path("exp/results/emse_runtime/first_wave_shadow_bridge_v1")
DEFAULT_MODEL = os.environ.get("LMSTUDIO_MODEL", "qwen2.5-coder-7b-instruct-mlx")
DEFAULT_BASE_URL = os.environ.get("LMSTUDIO_BASE_URL", "http://127.0.0.1:1234/v1")
DEFAULT_CONTROLLERS = ["sempc_lite", "rsrc_guarded", "static_conservative", "minimal_verify"]
RESULT_COLUMNS = [*ANALYSIS_RESULT_COLUMNS, "execute_status"]


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing required file: {path}")
    return pd.read_csv(path)


def select_rows(bundle: pd.DataFrame, controllers: list[str], limit_tasks: int) -> pd.DataFrame:
    selected = bundle[bundle["controller"].astype(str).isin(controllers)].copy()
    if selected.empty:
        raise ValueError("No first-wave rows match the requested controllers.")
    task_order = selected[["bundle_order", "instance_id"]].drop_duplicates().sort_values("bundle_order")
    if limit_tasks > 0:
        keep = set(task_order.head(limit_tasks)["instance_id"].astype(str))
        selected = selected[selected["instance_id"].astype(str).isin(keep)].copy()
    if selected.empty:
        raise ValueError("No first-wave rows remain after applying --limit-tasks.")
    return selected.sort_values(["bundle_order", "controller_order_within_task", "controller"]).reset_index(drop=True)


def write_filtered_manifest(task_manifest: pd.DataFrame, selected_rows: pd.DataFrame, output_dir: Path) -> Path:
    instance_order = (
        selected_rows[["bundle_order", "instance_id"]]
        .drop_duplicates()
        .sort_values("bundle_order")
        .reset_index(drop=True)
    )
    order_map = {instance_id: idx for idx, instance_id in enumerate(instance_order["instance_id"].astype(str))}
    tasks = task_manifest[task_manifest["instance_id"].astype(str).isin(order_map)].copy()
    if tasks.empty:
        raise ValueError("Selected first-wave instances were not found in the task manifest.")
    tasks["_first_wave_order"] = tasks["instance_id"].astype(str).map(order_map)
    tasks = tasks.sort_values("_first_wave_order").drop(columns=["_first_wave_order"])
    manifest_path = output_dir / "first_wave_shadow_task_manifest.csv"
    tasks.to_csv(manifest_path, index=False)
    return manifest_path


def build_shadow_command(args: argparse.Namespace, manifest_path: Path, shadow_dir: Path, controllers: list[str]) -> list[str]:
    script = ROOT / "exp/scripts/theory_support/shadow_runtime_experiment.py"
    repo_cache_dir = shadow_dir / "repo_cache"
    command = [
        sys.executable,
        str(script),
        "--manifest",
        str(manifest_path),
        "--results-dir",
        str(shadow_dir),
        "--repo-cache-dir",
        str(repo_cache_dir),
        "--controllers",
        *controllers,
        "--backend",
        args.backend,
        "--base-url",
        args.base_url,
        "--model",
        args.model,
        "--max-steps",
        str(args.max_steps),
        "--continue-on-error",
        "--resume-existing",
    ]
    if args.live_repo:
        command.append("--live-repo")
    if args.allow_clone:
        command.append("--allow-clone")
    if args.prepare_snapshots:
        command.append("--prepare-snapshots")
    if args.snapshot_root:
        command.extend(["--snapshot-root", str(args.snapshot_root)])
    return command


def require_execution_clearance(args: argparse.Namespace) -> None:
    if not args.execute:
        return
    if not args.ack_third_party_code:
        raise ValueError("--execute requires --ack-third-party-code.")
    if not args.live_repo:
        raise ValueError("--execute requires --live-repo so the run is explicit about repository code execution.")
    if os.environ.get("CAMC_RUNTIME_ISOLATION_ACK") != "1":
        raise ValueError("--execute requires CAMC_RUNTIME_ISOLATION_ACK=1 in the approved isolated environment.")
    if os.environ.get("SSH_AUTH_SOCK"):
        raise ValueError("--execute refuses to run while SSH_AUTH_SOCK is present.")


def numeric_or_zero(row: pd.Series, column: str) -> Any:
    value = row.get(column, 0)
    if pd.isna(value):
        return 0
    return value


def convert_shadow_results(bundle_dir: Path, shadow_results_path: Path, run_id: str, output_dir: Path) -> Path:
    template_path = bundle_dir / "runtime_task_results_empty.csv"
    template = read_csv(template_path)
    shadow = read_csv(shadow_results_path)
    out = template.copy()
    for col in RESULT_COLUMNS:
        if col not in out.columns:
            out[col] = ""

    for _, shadow_row in shadow.iterrows():
        instance_id = str(shadow_row["instance_id"])
        controller = str(shadow_row["controller"])
        mask = out["instance_id"].astype(str).eq(instance_id) & out["controller"].astype(str).eq(controller)
        if int(mask.sum()) != 1:
            continue
        idx = out.index[mask][0]
        out.loc[idx, "run_id"] = run_id
        out.loc[idx, "repo"] = shadow_row.get("repo", out.loc[idx, "repo"])
        out.loc[idx, "execution_mode"] = "isolated_shadow_runtime"
        out.loc[idx, "execute_status"] = "completed"
        for col in ANALYSIS_RESULT_COLUMNS:
            if col in {"run_id", "instance_id", "repo", "controller", "execution_mode"}:
                continue
            if col in shadow_row.index:
                out.loc[idx, col] = numeric_or_zero(shadow_row, col)

    output_path = output_dir / "runtime_task_results_recorded.csv"
    out.to_csv(output_path, index=False)
    return output_path


def write_report(
    output_dir: Path,
    selected_rows: pd.DataFrame,
    manifest_path: Path,
    command: list[str],
    executed: bool,
    returncode: int | None,
    converted_results: Path | None,
    args: argparse.Namespace,
) -> None:
    summary = {
        "status": "executed" if executed else "plan_only",
        "returncode": returncode,
        "selected_rows": int(len(selected_rows)),
        "selected_tasks": int(selected_rows["instance_id"].nunique()),
        "repositories": int(selected_rows["repo"].nunique()),
        "controllers": sorted(selected_rows["controller"].astype(str).unique().tolist()),
        "backend": args.backend,
        "model": args.model,
        "live_repo": bool(args.live_repo),
        "allow_clone": bool(args.allow_clone),
        "manifest": rel(manifest_path),
        "converted_results": rel(converted_results) if converted_results else "",
        "command": command,
    }
    (output_dir / "first_wave_shadow_bridge_summary.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )

    validation_target = converted_results or (output_dir / "runtime_task_results_recorded.csv")
    lines = [
        "# First-Wave Shadow Runtime Bridge",
        "",
        f"- Status: `{summary['status']}`",
        f"- Selected tasks: `{summary['selected_tasks']}`",
        f"- Selected rows: `{summary['selected_rows']}`",
        f"- Controllers: `{', '.join(summary['controllers'])}`",
        f"- Backend: `{args.backend}`",
        f"- Model: `{args.model}`",
        f"- Live repository execution requested: `{bool(args.live_repo)}`",
        f"- Third-party execution performed in this bridge run: `{executed}`",
        "",
        "## Filtered Inputs",
        "",
        f"- Task manifest: `{rel(manifest_path)}`",
        f"- Row plan: `{rel(output_dir / 'first_wave_shadow_row_plan.csv')}`",
        "",
        "## Shadow Command",
        "",
        "```bash",
        " ".join(command),
        "```",
        "",
    ]
    if converted_results:
        lines.extend(
            [
                "## Converted Results",
                "",
                f"- Runtime result CSV: `{rel(converted_results)}`",
                "",
                "Validate before analysis:",
                "",
                "```bash",
                "python3 -m exp.scripts.emse_runtime.validate_runtime_results "
                f"--task-results {rel(converted_results)} "
                f"--output-dir {rel(output_dir / 'validation')} "
                "--target sempc_lite --reference rsrc_guarded",
                "```",
                "",
                "Then run paired analysis only if validation passes.",
            ]
        )
    else:
        lines.extend(
            [
                "## Evidence Boundary",
                "",
                "This run generated an execution plan only. It did not clone repositories, apply patches, run tests, or produce completed runtime rows.",
                "",
                "To execute, run the command through this bridge inside the approved isolated environment with `--execute --live-repo --ack-third-party-code` and `CAMC_RUNTIME_ISOLATION_ACK=1`.",
                "",
                "The expected post-run result path is:",
                "",
                f"- `{rel(validation_target)}`",
            ]
        )
    (output_dir / "first_wave_shadow_bridge_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Bridge the EMSE first-wave execution bundle to the older live shadow-runtime runner. "
            "Default behavior is plan-only and performs no repository execution."
        )
    )
    parser.add_argument("--bundle-dir", type=Path, default=DEFAULT_BUNDLE_DIR)
    parser.add_argument("--task-manifest", type=Path, default=DEFAULT_TASK_MANIFEST)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--controllers", nargs="+", default=DEFAULT_CONTROLLERS)
    parser.add_argument("--limit-tasks", type=int, default=0)
    parser.add_argument("--backend", choices=["mock", "lmstudio"], default="lmstudio")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--max-steps", type=int, default=6)
    parser.add_argument("--live-repo", action="store_true")
    parser.add_argument("--allow-clone", action="store_true")
    parser.add_argument("--prepare-snapshots", action="store_true")
    parser.add_argument("--snapshot-root", type=Path, default=None)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--ack-third-party-code", action="store_true")
    parser.add_argument("--run-id", default="first_wave_shadow_runtime_v1")
    parser.add_argument("--update-bundle-results", action="store_true")
    args = parser.parse_args()

    require_execution_clearance(args)
    output_dir = ensure_dir(args.output_dir)
    shadow_dir = ensure_dir(output_dir / "shadow_runtime_output")
    bundle = read_csv(args.bundle_dir / "isolated_execution_manifest.csv")
    task_manifest = read_csv(args.task_manifest)
    selected_rows = select_rows(bundle, args.controllers, args.limit_tasks)
    selected_rows.to_csv(output_dir / "first_wave_shadow_row_plan.csv", index=False)
    manifest_path = write_filtered_manifest(task_manifest, selected_rows, output_dir)
    command = build_shadow_command(args, manifest_path, shadow_dir, args.controllers)

    returncode: int | None = None
    converted_results: Path | None = None
    if args.execute:
        completed = subprocess.run(command, cwd=str(ROOT), check=False)
        returncode = int(completed.returncode)
        if returncode != 0:
            raise RuntimeError(f"Shadow runtime command failed with exit code {returncode}.")
        shadow_results = shadow_dir / "shadow_runtime_task_results.csv"
        converted_results = convert_shadow_results(args.bundle_dir, shadow_results, args.run_id, output_dir)
        if args.update_bundle_results:
            target = args.bundle_dir / "runtime_task_results_recorded.csv"
            shutil.copyfile(converted_results, target)
            converted_results = target

    write_report(
        output_dir=output_dir,
        selected_rows=selected_rows,
        manifest_path=manifest_path,
        command=command,
        executed=bool(args.execute),
        returncode=returncode,
        converted_results=converted_results,
        args=args,
    )
    print(f"Wrote first-wave bridge materials to {output_dir}")


if __name__ == "__main__":
    main()
