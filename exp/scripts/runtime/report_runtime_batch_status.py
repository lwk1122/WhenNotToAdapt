from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

from .validate_runtime_results import validate_task_results


DEFAULT_MATRIX = Path("exp/results/emse_runtime/manifest_v1/runtime_execution_matrix.csv")
DEFAULT_TASK_MANIFEST = Path("exp/results/emse_runtime/manifest_v1/task_manifest.csv")
DEFAULT_RESULTS = Path("exp/results/emse_runtime/isolated_execution_bundle_v1/runtime_task_results_empty.csv")
DEFAULT_CHECKLIST = Path("exp/results/emse_runtime/isolated_execution_bundle_v1/row_execution_checklist.csv")
DEFAULT_PACKET_INDEX = Path("exp/results/emse_runtime/isolated_execution_packets_v1/packet_index.csv")
DEFAULT_PREFLIGHT = Path("exp/results/emse_runtime/preflight_v1/runtime_preflight_summary.json")
DEFAULT_OUTPUT_DIR = Path("exp/results/emse_runtime/batch_status_v1")

COMPLETED_STATUSES = {"complete", "completed", "done", "succeeded", "success", "ran", "executed"}
PRIMARY_METRICS = ["success", "search_count", "read_count", "test_runs", "patch_attempts"]
PRIMARY_COMPARISONS = [
    ("sempc_lite", "rsrc_guarded"),
    ("sempc_lite", "static_conservative"),
    ("sempc_lite", "minimal_verify"),
]


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def read_csv_optional(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def read_json_optional(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"read_error": str(exc)}


def status_counts(frame: pd.DataFrame, column: str) -> pd.DataFrame:
    if frame.empty or column not in frame.columns:
        return pd.DataFrame(columns=[column, "rows"])
    return (
        frame[column]
        .fillna("__missing__")
        .astype(str)
        .value_counts(dropna=False)
        .rename_axis(column)
        .reset_index(name="rows")
        .sort_values(column)
        .reset_index(drop=True)
    )


def result_row_id(row: pd.Series) -> str:
    return f"{row['instance_id']}::{row['controller']}"


def completed_mask(frame: pd.DataFrame) -> pd.Series:
    if frame.empty or "execute_status" not in frame.columns:
        return pd.Series([False] * len(frame), index=frame.index)
    return frame["execute_status"].fillna("").astype(str).str.lower().isin(COMPLETED_STATUSES)


def metric_complete_mask(frame: pd.DataFrame, metrics: list[str]) -> pd.Series:
    if frame.empty:
        return pd.Series(dtype=bool)
    missing = [metric for metric in metrics if metric not in frame.columns]
    if missing:
        return pd.Series([False] * len(frame), index=frame.index)
    numeric = frame[metrics].apply(pd.to_numeric, errors="coerce")
    return numeric.notna().all(axis=1)


def summarize_overview(matrix: pd.DataFrame, task_manifest: pd.DataFrame, results: pd.DataFrame) -> dict[str, Any]:
    completed = completed_mask(results)
    primary_complete = metric_complete_mask(results, PRIMARY_METRICS)
    return {
        "matrix_rows": int(len(matrix)),
        "matrix_tasks": int(matrix["instance_id"].nunique()) if "instance_id" in matrix.columns else 0,
        "matrix_repositories": int(matrix["repo"].nunique()) if "repo" in matrix.columns else 0,
        "task_manifest_rows": int(len(task_manifest)),
        "result_rows": int(len(results)),
        "completed_result_rows": int(completed.sum()),
        "primary_metric_complete_rows": int(primary_complete.sum()),
        "controllers": sorted(matrix["controller"].dropna().astype(str).unique().tolist()) if "controller" in matrix.columns else [],
        "risk_tiers": matrix["risk_tier"].dropna().astype(str).value_counts().sort_index().to_dict() if "risk_tier" in matrix.columns else {},
        "third_party_execution_performed_by_this_report": False,
    }


def summarize_controller_status(results: pd.DataFrame) -> pd.DataFrame:
    if results.empty or "controller" not in results.columns:
        return pd.DataFrame(columns=["controller", "rows", "completed_rows", "primary_metric_complete_rows"])
    completed = completed_mask(results)
    primary_complete = metric_complete_mask(results, PRIMARY_METRICS)
    out = results.assign(_completed=completed, _primary_complete=primary_complete)
    return (
        out.groupby("controller", dropna=False)
        .agg(
            rows=("controller", "size"),
            completed_rows=("_completed", "sum"),
            primary_metric_complete_rows=("_primary_complete", "sum"),
        )
        .reset_index()
        .sort_values("controller")
    )


def summarize_pair_readiness(results: pd.DataFrame, comparisons: list[tuple[str, str]]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    if results.empty or not {"instance_id", "controller"}.issubset(results.columns):
        return pd.DataFrame(columns=["target", "reference", "planned_pairs", "completed_pairs", "metric_complete_pairs", "validation_status", "validation_errors", "validation_warnings"])

    completed = completed_mask(results)
    primary_complete = metric_complete_mask(results, PRIMARY_METRICS)
    augmented = results.assign(_completed=completed, _primary_complete=primary_complete)
    for target, reference in comparisons:
        selected = augmented[augmented["controller"].astype(str).isin([target, reference])].copy()
        planned_instances = set(selected[selected["controller"].astype(str).eq(target)]["instance_id"].astype(str)) & set(
            selected[selected["controller"].astype(str).eq(reference)]["instance_id"].astype(str)
        )
        complete_instances = set(
            selected[selected["controller"].astype(str).eq(target) & selected["_completed"]]["instance_id"].astype(str)
        ) & set(selected[selected["controller"].astype(str).eq(reference) & selected["_completed"]]["instance_id"].astype(str))
        metric_instances = set(
            selected[selected["controller"].astype(str).eq(target) & selected["_completed"] & selected["_primary_complete"]]["instance_id"].astype(str)
        ) & set(
            selected[selected["controller"].astype(str).eq(reference) & selected["_completed"] & selected["_primary_complete"]]["instance_id"].astype(str)
        )
        validation = validate_task_results(results, target=target, reference=reference)
        issues = validation.get("issues", [])
        rows.append(
            {
                "target": target,
                "reference": reference,
                "planned_pairs": int(len(planned_instances)),
                "completed_pairs": int(len(complete_instances)),
                "metric_complete_pairs": int(len(metric_instances)),
                "validation_status": validation["status"],
                "validation_errors": int(sum(1 for item in issues if item.get("severity") == "error")),
                "validation_warnings": int(sum(1 for item in issues if item.get("severity") == "warning")),
            }
        )
    return pd.DataFrame(rows)


def summarize_checklist(checklist: pd.DataFrame) -> pd.DataFrame:
    if checklist.empty:
        return pd.DataFrame(columns=["check", "completed_rows", "total_rows", "completion_rate"])
    bool_cols = [
        col
        for col in checklist.columns
        if col
        not in {
            "result_row_id",
            "instance_id",
            "repo",
            "controller",
            "notes",
        }
    ]
    rows = []
    for col in bool_cols:
        values = checklist[col].fillna(False).astype(bool)
        rows.append(
            {
                "check": col,
                "completed_rows": int(values.sum()),
                "total_rows": int(len(values)),
                "completion_rate": float(values.mean()) if len(values) else 0.0,
            }
        )
    return pd.DataFrame(rows)


def summarize_packets(packet_index: pd.DataFrame) -> dict[str, Any]:
    if packet_index.empty:
        return {
            "packet_index_rows": 0,
            "packet_md_existing": 0,
            "packet_json_existing": 0,
            "missing_packet_files": [],
        }
    missing: list[str] = []
    md_existing = 0
    json_existing = 0
    for _, row in packet_index.iterrows():
        md_path = Path(str(row.get("packet_md", "")))
        json_path = Path(str(row.get("packet_json", "")))
        if md_path.exists():
            md_existing += 1
        else:
            missing.append(str(md_path))
        if json_path.exists():
            json_existing += 1
        else:
            missing.append(str(json_path))
    return {
        "packet_index_rows": int(len(packet_index)),
        "packet_md_existing": int(md_existing),
        "packet_json_existing": int(json_existing),
        "missing_packet_files": missing[:20],
        "missing_packet_file_count": int(len(missing)),
    }


def frame_to_markdown(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "_No rows._"
    headers = list(frame.columns)
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for _, row in frame.iterrows():
        cells = []
        for col in headers:
            value = row[col]
            if isinstance(value, float):
                cells.append(f"{value:.3f}")
            else:
                cells.append(str(value).replace("|", "\\|"))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def write_status_report(
    path: Path,
    overview: dict[str, Any],
    execute_counts: pd.DataFrame,
    controller_status: pd.DataFrame,
    pair_readiness: pd.DataFrame,
    checklist_summary: pd.DataFrame,
    packet_summary: dict[str, Any],
    preflight_summary: dict[str, Any],
    source_paths: dict[str, str],
) -> None:
    preflight_status = preflight_summary.get("status", preflight_summary.get("overall_status", "unknown"))
    lines = [
        "# Controlled Runtime Batch Status",
        "",
        "## Summary",
        "",
        f"- Matrix rows: {overview['matrix_rows']}",
        f"- Planned tasks: {overview['matrix_tasks']}",
        f"- Planned repositories: {overview['matrix_repositories']}",
        f"- Result rows: {overview['result_rows']}",
        f"- Completed result rows: {overview['completed_result_rows']}",
        f"- Rows with complete primary metrics: {overview['primary_metric_complete_rows']}",
        f"- Controllers: {', '.join(overview['controllers'])}",
        f"- Preflight status: `{preflight_status}`",
        f"- Packet files present: {packet_summary['packet_md_existing']} markdown and {packet_summary['packet_json_existing']} JSON rows out of {packet_summary['packet_index_rows']}",
        "- Third-party repository execution performed by this report: `False`",
        "",
        "## Evidence Status",
        "",
        "The current batch is not publication evidence until rows have `execute_status=completed` and observed primary metrics. Planned, prompt-only, and empty-template rows are explicitly excluded from paired runtime claims.",
        "",
        "## Execute Status Counts",
        "",
        frame_to_markdown(execute_counts),
        "",
        "## Controller Status",
        "",
        frame_to_markdown(controller_status),
        "",
        "## Pair Readiness",
        "",
        frame_to_markdown(pair_readiness),
        "",
        "## Checklist Completion",
        "",
        frame_to_markdown(checklist_summary),
        "",
        "## Packet Integrity",
        "",
        f"- Missing packet file count: {packet_summary.get('missing_packet_file_count', 0)}",
        "",
        "## Source Paths",
        "",
    ]
    for key, value in source_paths.items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(
        [
            "",
            "## Next Evidence Steps",
            "",
            "1. Re-run controlled-runtime preflight inside the approved isolated environment.",
            "2. Remove or isolate sensitive environment exposure, especially `SSH_AUTH_SOCK`.",
            f"3. Execute rows from the packet index listed above (`{source_paths.get('packet_index', '')}`) only inside that environment.",
            "4. Record completed rows with `record_isolated_runtime_result.py` and an evidence note.",
            "5. Run `validate_runtime_results.py`; only then run paired analysis and manuscript artifact generation.",
            "",
            "## Claim Guardrail",
            "",
            "This status report supports execution control and evidence hygiene. It does not support solve-rate non-inferiority, resource-savings, or downstream-work claims.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Report controlled-runtime batch readiness without executing third-party code.")
    parser.add_argument("--matrix", type=Path, default=DEFAULT_MATRIX)
    parser.add_argument("--task-manifest", type=Path, default=DEFAULT_TASK_MANIFEST)
    parser.add_argument("--task-results", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--checklist", type=Path, default=DEFAULT_CHECKLIST)
    parser.add_argument("--packet-index", type=Path, default=DEFAULT_PACKET_INDEX)
    parser.add_argument("--preflight-summary", type=Path, default=DEFAULT_PREFLIGHT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    matrix = read_csv_optional(args.matrix)
    task_manifest = read_csv_optional(args.task_manifest)
    results = read_csv_optional(args.task_results)
    checklist = read_csv_optional(args.checklist)
    packet_index = read_csv_optional(args.packet_index)
    preflight_summary = read_json_optional(args.preflight_summary)

    output_dir = ensure_dir(args.output_dir)
    overview = summarize_overview(matrix, task_manifest, results)
    execute_counts = status_counts(results, "execute_status")
    controller_status = summarize_controller_status(results)
    pair_readiness = summarize_pair_readiness(results, PRIMARY_COMPARISONS)
    checklist_summary = summarize_checklist(checklist)
    packet_summary = summarize_packets(packet_index)
    source_paths = {
        "matrix": str(args.matrix),
        "task_manifest": str(args.task_manifest),
        "task_results": str(args.task_results),
        "checklist": str(args.checklist),
        "packet_index": str(args.packet_index),
        "preflight_summary": str(args.preflight_summary),
    }

    execute_counts.to_csv(output_dir / "runtime_execute_status_counts.csv", index=False)
    controller_status.to_csv(output_dir / "runtime_controller_status.csv", index=False)
    pair_readiness.to_csv(output_dir / "runtime_pair_readiness.csv", index=False)
    checklist_summary.to_csv(output_dir / "runtime_checklist_summary.csv", index=False)
    (output_dir / "runtime_batch_status_summary.json").write_text(
        json.dumps(
            {
                "overview": overview,
                "packet_summary": packet_summary,
                "preflight_summary": preflight_summary,
                "source_paths": source_paths,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    write_status_report(
        output_dir / "runtime_batch_status_report.md",
        overview,
        execute_counts,
        controller_status,
        pair_readiness,
        checklist_summary,
        packet_summary,
        preflight_summary,
        source_paths,
    )
    print(f"Wrote controlled-runtime batch status to {output_dir / 'runtime_batch_status_report.md'}")


if __name__ == "__main__":
    main()
