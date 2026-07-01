from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


DEFAULT_BUNDLE_DIR = Path("exp/results/emse_runtime/first_wave_execution_bundle_v1")
DEFAULT_OUTPUT_DIR = Path("exp/results/emse_runtime/first_wave_analysis_drill_v1")
DEFAULT_TARGET = "sempc_lite"
DEFAULT_REFERENCE = "rsrc_guarded"

PRIMARY_METRICS = ["success", "search_count", "read_count", "test_runs", "patch_attempts"]
RESOURCE_METRICS = [
    "verification_events",
    "patch_apply_successes",
    "fallback_events",
    "post_error_extra_work",
    "model_calls",
    "prompt_tokens",
    "completion_tokens",
    "total_tokens",
    "latency_seconds",
    "tool_calls",
    "context_files",
    "context_bytes",
    "files_changed",
    "lines_changed",
    "failed_verification_jobs",
    "recovery_attempts",
]


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_bundle(bundle_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    manifest_path = bundle_dir / "isolated_execution_manifest.csv"
    results_path = bundle_dir / "runtime_task_results_empty.csv"
    pair_plan_path = bundle_dir / "first_wave_pair_plan.csv"
    missing = [path for path in [manifest_path, results_path, pair_plan_path] if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing first-wave bundle files: {', '.join(str(path) for path in missing)}")
    return pd.read_csv(manifest_path), pd.read_csv(results_path), pd.read_csv(pair_plan_path)


def synthetic_metrics(pair_rank: int, controller: str, target: str, reference: str) -> dict[str, int | float]:
    """Deterministic synthetic rows for analysis-shape testing only."""
    # Include a mix of concordant success, target-only success, reference-only success, and both-fail rows.
    success_pattern = {
        0: {target: 1, reference: 1},
        1: {target: 1, reference: 1},
        2: {target: 1, reference: 0},
        3: {target: 0, reference: 1},
    }[pair_rank % 4]
    success = int(success_pattern.get(controller, 0))
    target_like = controller == target
    base = 2 + (pair_rank % 3)
    work_shift = -1 if target_like and pair_rank % 2 == 0 else 1 if not target_like and pair_rank % 2 == 0 else 0
    search = max(0, base + work_shift)
    read = max(1, base + 2 + (0 if target_like else 1))
    tests = max(1, 1 + (pair_rank % 2) + (0 if target_like else 1))
    patches = max(1, 1 + (0 if target_like else pair_rank % 2))
    prompt_tokens = 1200 + pair_rank * 17 + (80 if target_like else 40)
    completion_tokens = 260 + pair_rank * 5 + (20 if target_like else 10)
    total_tokens = prompt_tokens + completion_tokens
    return {
        "success": success,
        "final_target_test_pass": success,
        "catastrophic_failure": 0,
        "test_runs": tests,
        "verification_events": tests + 1,
        "search_count": search,
        "read_count": read,
        "patch_attempts": patches,
        "patch_apply_successes": patches if success else max(0, patches - 1),
        "fallback_events": 0 if success else 1,
        "post_error_extra_work": 0 if success else 2,
        "best_problem_reduction": 1.0 if success else 0.45,
        "final_problem_reduction": 1.0 if success else 0.35,
        "model_calls": 2 if target_like else 1,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "latency_seconds": round(12.5 + pair_rank * 0.6 + (2.0 if target_like else 1.0), 3),
        "tool_calls": search + read + tests,
        "context_files": read,
        "context_bytes": read * 4200,
        "files_changed": 1 + (pair_rank % 2),
        "lines_changed": 8 + pair_rank,
        "failed_verification_jobs": 0 if success else 1,
        "recovery_attempts": 0 if success else 1,
    }


def build_synthetic_results(
    results: pd.DataFrame,
    pair_plan: pd.DataFrame,
    target: str,
    reference: str,
    run_id: str,
) -> pd.DataFrame:
    out = results.copy()
    out["run_id"] = run_id
    if "execution_mode" in out.columns:
        out["execution_mode"] = "synthetic_evidence_drill"
    for col in PRIMARY_METRICS + RESOURCE_METRICS + ["final_target_test_pass", "catastrophic_failure", "best_problem_reduction", "final_problem_reduction"]:
        if col not in out.columns:
            out[col] = pd.NA

    for pair_rank, row in enumerate(pair_plan.sort_values("execution_priority_rank").itertuples(index=False), start=1):
        for controller in [target, reference]:
            mask = out["instance_id"].astype(str).eq(str(row.instance_id)) & out["controller"].astype(str).eq(controller)
            if int(mask.sum()) != 1:
                raise ValueError(f"Expected one result row for {row.instance_id}::{controller}, found {int(mask.sum())}.")
            values = synthetic_metrics(pair_rank, controller, target, reference)
            for col, value in values.items():
                out.loc[mask, col] = value
            out.loc[mask, "execute_status"] = "completed"
    return out


def write_report(path: Path, summary: dict[str, object]) -> None:
    lines = [
        "# First-Wave Synthetic Analysis Drill",
        "",
        "## Scope Boundary",
        "",
        "- This is a synthetic evidence-drill artifact.",
        "- It does not clone repositories, install dependencies, apply patches, run tests, or call LM Studio.",
        "- It exists only to verify that completed-looking first-wave rows can pass through validation, paired analysis, and publication-artifact generation.",
        "- Do not cite these values as solve-rate, resource-savings, or downstream-work evidence.",
        "",
        "## Summary",
        "",
    ]
    for key, value in summary.items():
        lines.append(f"- {key}: `{value}`")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Create synthetic first-wave completed rows to test runtime analysis plumbing only.")
    parser.add_argument("--bundle-dir", type=Path, default=DEFAULT_BUNDLE_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--target", default=DEFAULT_TARGET)
    parser.add_argument("--reference", default=DEFAULT_REFERENCE)
    parser.add_argument("--run-id", default="first_wave_synthetic_analysis_drill_v1")
    args = parser.parse_args()

    manifest, results, pair_plan = load_bundle(args.bundle_dir)
    output_dir = ensure_dir(args.output_dir)
    synthetic = build_synthetic_results(results, pair_plan, args.target, args.reference, args.run_id)
    results_path = output_dir / "runtime_task_results_synthetic_completed.csv"
    synthetic.to_csv(results_path, index=False)

    completed = synthetic["execute_status"].astype(str).str.lower().eq("completed")
    selected = synthetic["controller"].astype(str).isin([args.target, args.reference])
    summary = {
        "run_id": args.run_id,
        "source_bundle": str(args.bundle_dir),
        "output_dir": str(output_dir),
        "results_path": str(results_path),
        "manifest_rows": int(len(manifest)),
        "result_rows": int(len(synthetic)),
        "synthetic_completed_rows": int(completed.sum()),
        "primary_pair_rows": int((completed & selected).sum()),
        "paired_instances": int(pair_plan["instance_id"].nunique()),
        "target": args.target,
        "reference": args.reference,
        "execution_mode": "synthetic_evidence_drill",
        "evidence_status": "synthetic_drill_not_publication_evidence",
        "third_party_execution_performed": False,
        "lmstudio_called": False,
    }
    summary_path = output_dir / "first_wave_analysis_drill_summary.json"
    report_path = output_dir / "first_wave_analysis_drill_report.md"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    write_report(report_path, summary)
    print(f"Wrote synthetic first-wave results to {results_path}")
    print(f"Wrote synthetic drill report to {report_path}")


if __name__ == "__main__":
    main()
