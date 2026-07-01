from __future__ import annotations

import argparse
import os
import subprocess
import uuid
from pathlib import Path

import pandas as pd

from common import RESULTS_DIR, ensure_dir, write_json
from prepare_shadow_runtime_tasks import VERIFIED_PARQUET, load_verified_tasks
from shadow_runtime_experiment import (
    ensure_snapshot_workspace,
    parse_list_field,
    prepare_snapshot_download,
    sanitize_name,
)


DEFAULT_RESULTS_DIR = RESULTS_DIR / "shadow_runtime_screen"


def classify_output(success: bool, output: str) -> str:
    text = (output or "").lower()
    if success:
        if " skipped" in text and "passed" not in text:
            return "skipped"
        return "pass"
    if "permissionerror" in text and "pytest_sessionfinish" in text:
        return "cleanup_noise"
    if "not found" in text or "found no collectors" in text or "no match in any of" in text:
        return "missing_test_node"
    if "skipped" in text and "deselected" in text:
        return "skipped"
    if "internalerror" in text:
        return "internal_error"
    if "importerror" in text or "modulenotfounderror" in text or "attributeerror" in text:
        return "env_error"
    if "failed" in text or "error" in text or "traceback" in text:
        return "test_failure"
    return "unknown_failure"


def exact_target_command(task_row: pd.Series) -> list[str]:
    fail_tests = parse_list_field(task_row["FAIL_TO_PASS"])
    if fail_tests:
        direct_targets = [item for item in fail_tests if "::" in item or item.endswith(".py")]
        bare_names = [item for item in fail_tests if item not in direct_targets]
        command = ["python", "-m", "pytest", "-q"]
        if direct_targets:
            command.extend(direct_targets)
        if bare_names:
            expression = " or ".join(bare_names)
            command.extend(["-k", expression])
        return command
    return ["python", "-m", "pytest", "-q"]


def run_exact_target_tests(workspace: Path, task_row: pd.Series, root_dir: Path, timeout_s: int) -> tuple[bool, str]:
    pytest_root = root_dir / "_pytest_tmp" / sanitize_name(str(task_row["instance_id"])) / uuid.uuid4().hex
    process_tmp = pytest_root / "process_tmp"
    base_temp = pytest_root / "basetemp"
    ensure_dir(process_tmp)
    env = os.environ.copy()
    env.update(
        {
            "TMP": str(process_tmp),
            "TEMP": str(process_tmp),
            "TMPDIR": str(process_tmp),
            "PYTHONDONTWRITEBYTECODE": "1",
        }
    )
    command = [
        *exact_target_command(task_row),
        "--maxfail",
        "1",
        "--basetemp",
        str(base_temp),
        "-o",
        f"cache_dir={pytest_root / 'cache'}",
        "-p",
        "no:cacheprovider",
    ]
    result = subprocess.run(
        command,
        cwd=str(workspace),
        text=True,
        capture_output=True,
        timeout=timeout_s,
        check=False,
        env=env,
    )
    combined = "\n".join(part for part in [result.stdout, result.stderr] if part).strip()
    return result.returncode == 0, f"$ {' '.join(command)}\n{combined}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Preflight-screen shadow-runtime tasks for snapshot availability and baseline test compatibility.")
    parser.add_argument("--input", type=Path, default=VERIFIED_PARQUET)
    parser.add_argument("--results-dir", type=Path, default=DEFAULT_RESULTS_DIR)
    parser.add_argument("--instance-ids", nargs="*", default=None)
    parser.add_argument("--repos", nargs="*", default=None)
    parser.add_argument("--limit", type=int, default=12)
    parser.add_argument("--timeout-s", type=int, default=600)
    args = parser.parse_args()

    ensure_dir(args.results_dir)
    snapshot_root = args.results_dir / "snapshots"
    workspace_root = args.results_dir / "workspaces"
    ensure_dir(snapshot_root)
    ensure_dir(workspace_root)

    raw = load_verified_tasks(args.input)
    if args.repos:
        raw = raw[raw["repo"].isin(set(args.repos))].copy()
    if args.instance_ids:
        raw = raw[raw["instance_id"].isin(set(args.instance_ids))].copy()
    raw = raw.head(args.limit).copy()

    rows: list[dict[str, object]] = []
    for _, task_row in raw.iterrows():
        instance_id = str(task_row["instance_id"])
        workspace = workspace_root / sanitize_name(instance_id)
        snapshot_status = "ok"
        try:
            snapshot_dir = prepare_snapshot_download(task_row, snapshot_root)
            ensure_snapshot_workspace(snapshot_dir, workspace)
        except Exception as exc:
            snapshot_status = f"download_error:{exc}"
            rows.append(
                {
                    "repo": task_row["repo"],
                    "instance_id": instance_id,
                    "base_commit": task_row["base_commit"],
                    "fail_to_pass_count": len(parse_list_field(task_row["FAIL_TO_PASS"])),
                    "snapshot_status": snapshot_status,
                    "baseline_status": "not_run",
                    "baseline_success": 0,
                    "baseline_output_path": "",
                }
            )
            continue

        success, output = run_exact_target_tests(workspace, task_row, args.results_dir, timeout_s=args.timeout_s)
        output_path = args.results_dir / "outputs" / f"{sanitize_name(instance_id)}.txt"
        ensure_dir(output_path.parent)
        output_path.write_text(output, encoding="utf-8")
        rows.append(
            {
                "repo": task_row["repo"],
                "instance_id": instance_id,
                "base_commit": task_row["base_commit"],
                "fail_to_pass_count": len(parse_list_field(task_row["FAIL_TO_PASS"])),
                "snapshot_status": snapshot_status,
                "baseline_status": classify_output(success, output),
                "baseline_success": int(success),
                "baseline_output_path": str(output_path),
            }
        )
        print(f"[screen] {instance_id} status={rows[-1]['baseline_status']}")

    results = pd.DataFrame(rows)
    csv_path = args.results_dir / "screen_results.csv"
    summary_path = args.results_dir / "screen_summary.json"
    results.to_csv(csv_path, index=False)
    write_json(
        summary_path,
        {
            "rows": int(len(results)),
            "status_counts": results["baseline_status"].value_counts().to_dict() if not results.empty else {},
            "snapshot_status_counts": results["snapshot_status"].value_counts().to_dict() if not results.empty else {},
        },
    )
    print(f"Wrote screening results to {csv_path}")


if __name__ == "__main__":
    main()
