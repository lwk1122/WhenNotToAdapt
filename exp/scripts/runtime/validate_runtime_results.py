from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

import pandas as pd


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

REQUIRED_ID_COLUMNS = ["instance_id", "controller"]
PRIMARY_OBSERVED_COLUMNS = ["success", "search_count", "read_count", "test_runs", "patch_attempts"]
COUNT_COLUMNS = [
    "catastrophic_failure",
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
    "latency_seconds",
    "tool_calls",
    "context_files",
    "context_bytes",
    "files_changed",
    "lines_changed",
    "failed_verification_jobs",
    "recovery_attempts",
]
BINARY_COLUMNS = ["success", "final_target_test_pass", "catastrophic_failure"]
PROMPT_ONLY_MARKERS = ["prompt_only", "dry_run", "offline_prompt_only", "lmstudio_prompt_only"]
COMPLETED_STATUSES = {"complete", "completed", "done", "succeeded", "success", "ran", "executed"}


def issue(severity: str, code: str, message: str) -> dict[str, str]:
    return {"severity": severity, "code": code, "message": message}


def selected_pair_rows(frame: pd.DataFrame, target: str, reference: str) -> pd.DataFrame:
    if "controller" not in frame.columns:
        return pd.DataFrame()
    return frame[frame["controller"].astype(str).isin([target, reference])].copy()


def numeric_series(frame: pd.DataFrame, column: str) -> pd.Series:
    return pd.to_numeric(frame[column], errors="coerce")


def validate_task_results(
    frame: pd.DataFrame,
    target: str,
    reference: str,
    metrics: Iterable[str] = DEFAULT_METRICS,
    allow_incomplete: bool = False,
    require_executed: bool = True,
) -> dict[str, object]:
    issues: list[dict[str, str]] = []

    missing_id = [col for col in REQUIRED_ID_COLUMNS if col not in frame.columns]
    for col in missing_id:
        issues.append(issue("error", "missing_id_column", f"Required column `{col}` is missing."))
    if missing_id:
        return {
            "status": "FAIL",
            "issues": issues,
            "rows": int(len(frame)),
            "selected_rows": 0,
            "paired_instances": 0,
            "target": target,
            "reference": reference,
        }

    selected = selected_pair_rows(frame, target, reference)
    target_rows = frame[frame["controller"].astype(str).eq(target)]
    reference_rows = frame[frame["controller"].astype(str).eq(reference)]
    if target_rows.empty:
        issues.append(issue("error", "missing_target_controller", f"No rows found for target controller `{target}`."))
    if reference_rows.empty:
        issues.append(issue("error", "missing_reference_controller", f"No rows found for reference controller `{reference}`."))

    duplicates = selected.duplicated(["instance_id", "controller"], keep=False)
    if duplicates.any():
        dup_count = int(duplicates.sum())
        issues.append(issue("error", "duplicate_instance_controller", f"Found {dup_count} duplicate instance/controller rows."))

    target_instances = set(target_rows["instance_id"].astype(str))
    reference_instances = set(reference_rows["instance_id"].astype(str))
    paired_instances = sorted(target_instances & reference_instances)
    if not paired_instances:
        issues.append(issue("error", "no_paired_instances", f"No paired instances found for `{target}` and `{reference}`."))

    if require_executed and "execution_mode" in selected.columns:
        modes = selected["execution_mode"].fillna("").astype(str).str.lower()
        prompt_only = modes.apply(lambda value: any(marker in value for marker in PROMPT_ONLY_MARKERS))
        if prompt_only.any():
            issues.append(
                issue(
                    "error",
                    "prompt_only_rows",
                    f"Selected rows include {int(prompt_only.sum())} prompt-only/dry-run rows; these are not executable evidence.",
                )
            )

    if require_executed and "execute_status" in selected.columns:
        statuses = selected["execute_status"].fillna("").astype(str).str.lower()
        incomplete = ~statuses.isin(COMPLETED_STATUSES)
        if incomplete.any():
            sample = ", ".join(sorted(statuses[incomplete].unique().tolist())[:5])
            issues.append(
                issue(
                    "error",
                    "incomplete_execute_status",
                    f"Selected rows include {int(incomplete.sum())} non-completed execute_status values: {sample}.",
                )
            )

    required_metric_cols = [col for col in PRIMARY_OBSERVED_COLUMNS if col not in selected.columns]
    for col in required_metric_cols:
        issues.append(issue("error", "missing_primary_metric", f"Primary observed metric `{col}` is missing."))

    checked_metrics = sorted(set(metrics) | set(PRIMARY_OBSERVED_COLUMNS))
    for col in checked_metrics:
        if col not in selected.columns:
            if col in PRIMARY_OBSERVED_COLUMNS:
                continue
            issues.append(issue("warning", "missing_secondary_metric", f"Secondary metric `{col}` is missing and will be skipped."))
            continue
        values = numeric_series(selected, col)
        non_missing = int(values.notna().sum())
        if col in PRIMARY_OBSERVED_COLUMNS and non_missing == 0:
            severity = "warning" if allow_incomplete else "error"
            issues.append(issue(severity, "empty_primary_metric", f"Primary observed metric `{col}` has no numeric values."))
        if col in BINARY_COLUMNS and non_missing > 0:
            invalid = values.dropna()[~values.dropna().isin([0, 1])]
            if not invalid.empty:
                issues.append(issue("error", "invalid_binary_metric", f"Binary metric `{col}` contains values outside {{0,1}}."))
        if col in COUNT_COLUMNS and non_missing > 0:
            negative = values.dropna()[values.dropna() < 0]
            if not negative.empty:
                issues.append(issue("error", "negative_count_metric", f"Count metric `{col}` contains negative values."))

    if "success" in selected.columns:
        success_values = numeric_series(selected, "success")
        if success_values.notna().any() and float(success_values.fillna(0).sum()) == 0.0:
            issues.append(
                issue(
                    "warning",
                    "zero_success_evidence",
                    "All selected success values are zero; non-inferiority may be mechanically satisfied but not informative.",
                )
            )

    errors = [item for item in issues if item["severity"] == "error"]
    return {
        "status": "FAIL" if errors else "PASS",
        "issues": issues,
        "rows": int(len(frame)),
        "selected_rows": int(len(selected)),
        "paired_instances": int(len(paired_instances)),
        "target": target,
        "reference": reference,
        "allow_incomplete": bool(allow_incomplete),
        "require_executed": bool(require_executed),
    }


def validation_issues_frame(validation: dict[str, object]) -> pd.DataFrame:
    return pd.DataFrame(validation.get("issues", []), columns=["severity", "code", "message"])


def write_validation_outputs(output_dir: Path, validation: dict[str, object]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "runtime_result_validation.json"
    csv_path = output_dir / "runtime_result_validation_issues.csv"
    md_path = output_dir / "runtime_result_validation.md"
    json_path.write_text(json.dumps(validation, indent=2), encoding="utf-8")
    issues = validation_issues_frame(validation)
    issues.to_csv(csv_path, index=False)
    lines = [
        "# Runtime Result Validation",
        "",
        f"- Status: {validation['status']}",
        f"- Target: `{validation['target']}`",
        f"- Reference: `{validation['reference']}`",
        f"- Rows: {validation['rows']}",
        f"- Selected rows: {validation['selected_rows']}",
        f"- Paired instances: {validation['paired_instances']}",
        f"- Require executed rows: {validation['require_executed']}",
        f"- Allow incomplete metrics: {validation['allow_incomplete']}",
        "",
        "## Issues",
        "",
    ]
    if issues.empty:
        lines.append("_No validation issues._")
    else:
        lines.extend(["| severity | code | message |", "|---|---|---|"])
        for _, row in issues.iterrows():
            msg = str(row["message"]).replace("|", "\\|")
            lines.append(f"| {row['severity']} | {row['code']} | {msg} |")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate controlled-runtime task results before paired analysis.")
    parser.add_argument("--task-results", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--target", default="sempc_lite")
    parser.add_argument("--reference", default="rsrc_guarded")
    parser.add_argument("--metrics", nargs="*", default=DEFAULT_METRICS)
    parser.add_argument("--allow-incomplete", action="store_true")
    parser.add_argument("--allow-prompt-only", action="store_true")
    args = parser.parse_args()

    frame = pd.read_csv(args.task_results)
    validation = validate_task_results(
        frame,
        target=args.target,
        reference=args.reference,
        metrics=args.metrics,
        allow_incomplete=args.allow_incomplete,
        require_executed=not args.allow_prompt_only,
    )
    write_validation_outputs(args.output_dir, validation)
    print(f"Runtime result validation status: {validation['status']}")
    if validation["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
