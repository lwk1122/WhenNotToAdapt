from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from .validate_runtime_results import validate_task_results, write_validation_outputs


DEFAULT_METRICS = [
    "success",
    "final_target_test_pass",
    "catastrophic_failure",
    "test_runs",
    "verification_events",
    "search_count",
    "read_count",
    "patch_attempts",
    "patch_apply_successes",
    "fallback_events",
    "post_error_extra_work",
    "best_problem_reduction",
    "final_problem_reduction",
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

LOWER_IS_BETTER = {
    "catastrophic_failure",
    "test_runs",
    "verification_events",
    "search_count",
    "read_count",
    "patch_attempts",
    "fallback_events",
    "post_error_extra_work",
    "total_observed_work",
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
}

HIGHER_IS_BETTER = {
    "success",
    "final_target_test_pass",
    "patch_apply_successes",
    "best_problem_reduction",
    "final_problem_reduction",
}


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def paired_frame(task_results: pd.DataFrame, target: str, reference: str) -> pd.DataFrame:
    target_rows = task_results[task_results["controller"] == target].set_index("instance_id")
    reference_rows = task_results[task_results["controller"] == reference].set_index("instance_id")
    joined = target_rows.join(reference_rows, lsuffix="_target", rsuffix="_reference", how="inner")
    if joined.empty:
        raise ValueError(f"No paired instances found for target={target!r} and reference={reference!r}.")
    return joined.reset_index()


def bootstrap_ci(values: np.ndarray, rounds: int, alpha: float, seed: int) -> tuple[float, float]:
    values = np.asarray(values, dtype=float)
    values = values[~np.isnan(values)]
    if len(values) == 0:
        return float("nan"), float("nan")
    if len(values) == 1:
        return float(values[0]), float(values[0])
    rng = np.random.default_rng(seed)
    means = np.empty(rounds, dtype=float)
    for idx in range(rounds):
        sample = rng.choice(values, size=len(values), replace=True)
        means[idx] = float(np.mean(sample))
    return float(np.quantile(means, alpha / 2.0)), float(np.quantile(means, 1.0 - alpha / 2.0))


def metric_direction(metric: str) -> str:
    if metric in LOWER_IS_BETTER:
        return "lower"
    if metric in HIGHER_IS_BETTER:
        return "higher"
    return "descriptive"


def add_derived_metrics(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    for suffix in ["target", "reference"]:
        cols = [f"{name}_{suffix}" for name in ["search_count", "read_count", "test_runs", "patch_attempts"] if f"{name}_{suffix}" in out.columns]
        if cols:
            out[f"total_observed_work_{suffix}"] = out[cols].astype(float).sum(axis=1)
    return out


def analyze_pair(
    task_results: pd.DataFrame,
    target: str,
    reference: str,
    metrics: list[str],
    success_margin: float,
    min_publication_pairs: int,
    ci_alpha: float,
    bootstrap_rounds: int,
    seed: int,
) -> tuple[pd.DataFrame, dict]:
    paired = add_derived_metrics(paired_frame(task_results, target, reference))
    metric_rows: list[dict[str, object]] = []
    for metric in [*metrics, "total_observed_work"]:
        target_col = f"{metric}_target"
        reference_col = f"{metric}_reference"
        if target_col not in paired.columns or reference_col not in paired.columns:
            continue
        target_values = pd.to_numeric(paired[target_col], errors="coerce")
        reference_values = pd.to_numeric(paired[reference_col], errors="coerce")
        diff = (target_values - reference_values).to_numpy(dtype=float)
        ci_low, ci_high = bootstrap_ci(diff, bootstrap_rounds, ci_alpha, seed + len(metric_rows))
        row = {
            "target": target,
            "reference": reference,
            "metric": metric,
            "direction": metric_direction(metric),
            "n_pairs": int(len(diff)),
            "target_mean": float(np.nanmean(target_values)),
            "reference_mean": float(np.nanmean(reference_values)),
            "mean_diff_target_minus_reference": float(np.nanmean(diff)),
            "ci_low": ci_low,
            "ci_high": ci_high,
        }
        if metric in {"success", "final_target_test_pass"}:
            both_success = int(((target_values == 1) & (reference_values == 1)).sum())
            target_only = int(((target_values == 1) & (reference_values == 0)).sum())
            reference_only = int(((target_values == 0) & (reference_values == 1)).sum())
            both_fail = int(((target_values == 0) & (reference_values == 0)).sum())
            informative = bool((target_values.sum() + reference_values.sum()) > 0)
            row.update(
                {
                    "both_success": both_success,
                    "target_only_success": target_only,
                    "reference_only_success": reference_only,
                    "both_fail": both_fail,
                    "noninferiority_margin": success_margin,
                    "noninferior_by_ci": bool(ci_low > -success_margin),
                    "informative_success_evidence": informative,
                }
            )
        metric_rows.append(row)

    success_row = next((row for row in metric_rows if row["metric"] == "success"), None)
    total_work_row = next((row for row in metric_rows if row["metric"] == "total_observed_work"), None)
    summary = {
        "target": target,
        "reference": reference,
        "n_pairs": int(len(paired)),
        "success_margin": success_margin,
        "success_noninferior_by_ci": bool(success_row.get("noninferior_by_ci")) if success_row else None,
        "success_evidence_informative": bool(success_row.get("informative_success_evidence")) if success_row else None,
        "publication_ready_success_claim": bool(success_row.get("noninferior_by_ci") and success_row.get("informative_success_evidence") and len(paired) >= min_publication_pairs)
        if success_row
        else None,
        "min_publication_pairs": int(min_publication_pairs),
        "success_mean_diff": float(success_row["mean_diff_target_minus_reference"]) if success_row else None,
        "success_ci_low": float(success_row["ci_low"]) if success_row else None,
        "success_ci_high": float(success_row["ci_high"]) if success_row else None,
        "total_observed_work_mean_diff": float(total_work_row["mean_diff_target_minus_reference"]) if total_work_row else None,
        "total_observed_work_ci_low": float(total_work_row["ci_low"]) if total_work_row else None,
        "total_observed_work_ci_high": float(total_work_row["ci_high"]) if total_work_row else None,
    }
    return pd.DataFrame(metric_rows), summary


def write_markdown_report(path: Path, summary: dict, metrics: pd.DataFrame, source_path: Path) -> None:
    ensure_dir(path.parent)
    lines = [
        "# Runtime Pair Analysis",
        "",
        f"Source: `{source_path}`",
        "",
        "## Non-inferiority Summary",
        "",
        f"- Target controller: `{summary['target']}`",
        f"- Reference controller: `{summary['reference']}`",
        f"- Paired tasks: {summary['n_pairs']}",
        f"- Pre-specified solve-rate margin: {summary['success_margin']:.3f}",
        f"- Minimum paired tasks for publication-grade success claim: {summary['min_publication_pairs']}",
        f"- Success mean difference: {summary['success_mean_diff']:.3f}"
        if summary["success_mean_diff"] is not None
        else "- Success mean difference: NA",
        f"- Success bootstrap CI: [{summary['success_ci_low']:.3f}, {summary['success_ci_high']:.3f}]"
        if summary["success_ci_low"] is not None
        else "- Success bootstrap CI: NA",
        f"- Non-inferior by paired CI rule: {summary['success_noninferior_by_ci']}",
        f"- Success evidence informative: {summary['success_evidence_informative']}",
        f"- Publication-ready success claim: {summary['publication_ready_success_claim']}",
        "",
        "## Resource Summary",
        "",
        f"- Total observed work mean difference: {summary['total_observed_work_mean_diff']:.3f}"
        if summary["total_observed_work_mean_diff"] is not None
        else "- Total observed work mean difference: NA",
        f"- Total observed work bootstrap CI: [{summary['total_observed_work_ci_low']:.3f}, {summary['total_observed_work_ci_high']:.3f}]"
        if summary["total_observed_work_ci_low"] is not None
        else "- Total observed work bootstrap CI: NA",
        "",
        "## Metric Table",
        "",
        frame_to_markdown(metrics),
        "",
        "## Interpretation Guardrails",
        "",
        "- This script fixes the analysis contract for future controlled runs.",
        "- The existing 8-task pilot is a shape check, not publication-grade evidence.",
        "- A CI rule can be mechanically satisfied when both controllers solve nothing; publication-ready success claims require informative success evidence and the pre-specified minimum paired task count.",
        "- A formal EMSE claim requires a pre-specified task set, paired controller runs, and enough power for the chosen solve-rate margin.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def format_cell(value: object) -> str:
    if pd.isna(value):
        return ""
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def frame_to_markdown(frame: pd.DataFrame) -> str:
    headers = list(frame.columns)
    rows = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for _, row in frame.iterrows():
        rows.append("| " + " | ".join(format_cell(row[col]) for col in headers) + " |")
    return "\n".join(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze paired controlled-runtime task results with non-inferiority and resource summaries.")
    parser.add_argument("--task-results", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--target", default="sempc_lite")
    parser.add_argument("--reference", default="rsrc_guarded")
    parser.add_argument("--success-margin", type=float, default=0.05)
    parser.add_argument("--min-publication-pairs", type=int, default=30)
    parser.add_argument("--ci-alpha", type=float, default=0.05)
    parser.add_argument("--bootstrap-rounds", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=23)
    parser.add_argument("--metrics", nargs="*", default=DEFAULT_METRICS)
    parser.add_argument("--allow-incomplete", action="store_true", help="Allow incomplete observed metrics. Intended only for schema debugging.")
    parser.add_argument("--allow-prompt-only", action="store_true", help="Allow prompt-only dry-run rows. Do not use for evidence claims.")
    args = parser.parse_args()

    task_results = pd.read_csv(args.task_results)
    output_dir = ensure_dir(args.output_dir)
    validation = validate_task_results(
        task_results,
        target=args.target,
        reference=args.reference,
        metrics=args.metrics,
        allow_incomplete=args.allow_incomplete,
        require_executed=not args.allow_prompt_only,
    )
    write_validation_outputs(output_dir, validation)
    if validation["status"] != "PASS":
        errors = [item["message"] for item in validation["issues"] if item["severity"] == "error"]
        raise ValueError("Runtime task-results validation failed: " + " ".join(errors))

    metrics, summary = analyze_pair(
        task_results=task_results,
        target=args.target,
        reference=args.reference,
        metrics=args.metrics,
        success_margin=args.success_margin,
        min_publication_pairs=args.min_publication_pairs,
        ci_alpha=args.ci_alpha,
        bootstrap_rounds=args.bootstrap_rounds,
        seed=args.seed,
    )

    metrics_path = output_dir / "runtime_pairwise_metrics.csv"
    summary_path = output_dir / "runtime_noninferiority_summary.csv"
    report_path = output_dir / "runtime_pair_analysis_report.md"
    metrics.to_csv(metrics_path, index=False)
    pd.DataFrame([summary]).to_csv(summary_path, index=False)
    write_markdown_report(report_path, summary, metrics, args.task_results)
    print(f"Wrote runtime pair metrics to {metrics_path}")
    print(f"Wrote runtime non-inferiority summary to {summary_path}")
    print(f"Wrote runtime report to {report_path}")


if __name__ == "__main__":
    main()
