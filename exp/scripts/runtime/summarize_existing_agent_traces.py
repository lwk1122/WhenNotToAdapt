from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


DEFAULT_FIRST_WAVE_PAIR_PLAN = Path("exp/results/emse_runtime/first_wave_execution_bundle_v1/first_wave_pair_plan.csv")
DEFAULT_TRACE_ROOT = Path("exp/Dataset/CodeTraceBench/swe_raw")
DEFAULT_OUTPUT_DIR = Path("exp/results/emse_runtime/existing_agent_trace_supplement_v1")


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def trace_dirs(trace_root: Path, instance_id: str) -> list[Path]:
    if not trace_root.exists():
        return []
    return sorted(path for path in trace_root.glob(f"*/*{instance_id}*") if path.is_dir())


def count_tests(status: dict, group: str, outcome: str) -> int:
    return len(status.get(group, {}).get(outcome, []) or [])


def summarize_trace_dir(path: Path, instance_id: str) -> dict[str, object]:
    report_path = path / "report.json"
    report_item: dict = {}
    if report_path.exists():
        report = read_json(report_path)
        report_item = report.get(instance_id, {})
    status = report_item.get("tests_status", {}) if isinstance(report_item, dict) else {}
    event_files = sorted(path.glob("*.json"))
    event_files = [item for item in event_files if item.name != "report.json"]
    model_labels = sorted({item.name.split("__", 1)[0] for item in event_files if "__" in item.name})
    return {
        "instance_id": instance_id,
        "agent_trace_family": path.parent.name,
        "trace_dir": str(path),
        "report_json": str(report_path) if report_path.exists() else "",
        "event_json_files": len(event_files),
        "model_labels": ";".join(model_labels),
        "patch_exists": bool(report_item.get("patch_exists")) if report_item else None,
        "patch_successfully_applied": bool(report_item.get("patch_successfully_applied")) if report_item else None,
        "resolved": bool(report_item.get("resolved")) if report_item else None,
        "fail_to_pass_success": count_tests(status, "FAIL_TO_PASS", "success"),
        "fail_to_pass_failure": count_tests(status, "FAIL_TO_PASS", "failure"),
        "pass_to_pass_success": count_tests(status, "PASS_TO_PASS", "success"),
        "pass_to_pass_failure": count_tests(status, "PASS_TO_PASS", "failure"),
        "evidence_status": "external_trace_supplement_not_controlled_runtime",
    }


def frame_to_markdown(frame: pd.DataFrame) -> str:
    headers = list(frame.columns)
    rows = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for _, row in frame.iterrows():
        rows.append("| " + " | ".join("" if pd.isna(row[col]) else str(row[col]) for col in headers) + " |")
    return "\n".join(rows)


def write_report(path: Path, rows: pd.DataFrame, summary: dict[str, object]) -> None:
    display_cols = [
        "instance_id",
        "agent_trace_family",
        "event_json_files",
        "model_labels",
        "patch_successfully_applied",
        "resolved",
        "fail_to_pass_success",
        "fail_to_pass_failure",
        "pass_to_pass_success",
        "pass_to_pass_failure",
    ]
    display = rows[display_cols] if not rows.empty else pd.DataFrame(columns=display_cols)
    lines = [
        "# Existing Agent Trace Supplement",
        "",
        "This supplement scans local CodeTraceBench traces for first-wave task IDs.",
        "It does not execute repositories, call models, apply patches, or run tests.",
        "",
        "## Summary",
        "",
        f"- First-wave tasks: {summary['first_wave_tasks']}",
        f"- Covered tasks: {summary['covered_tasks']}",
        f"- Trace rows: {summary['trace_rows']}",
        f"- Evidence status: `{summary['evidence_status']}`",
        "",
        "## Trace Rows",
        "",
        frame_to_markdown(display),
        "",
        "## Interpretation Boundary",
        "",
        "These traces are external observational execution artifacts. They can support qualitative comparison and failure/rework taxonomy design, but they are not paired controlled-runtime evidence for `sempc_lite` versus `rsrc_guarded`.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize existing local agent traces that overlap first-wave runtime tasks.")
    parser.add_argument("--first-wave-pair-plan", type=Path, default=DEFAULT_FIRST_WAVE_PAIR_PLAN)
    parser.add_argument("--trace-root", type=Path, default=DEFAULT_TRACE_ROOT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    pair_plan = pd.read_csv(args.first_wave_pair_plan)
    rows: list[dict[str, object]] = []
    for instance_id in pair_plan["instance_id"].astype(str).tolist():
        for path in trace_dirs(args.trace_root, instance_id):
            rows.append(summarize_trace_dir(path, instance_id))
    output_dir = ensure_dir(args.output_dir)
    rows_frame = pd.DataFrame(rows)
    rows_frame.to_csv(output_dir / "existing_agent_trace_summary.csv", index=False)
    summary = {
        "first_wave_tasks": int(pair_plan["instance_id"].nunique()),
        "covered_tasks": int(rows_frame["instance_id"].nunique()) if not rows_frame.empty else 0,
        "trace_rows": int(len(rows_frame)),
        "trace_root": str(args.trace_root),
        "first_wave_pair_plan": str(args.first_wave_pair_plan),
        "third_party_execution_performed": False,
        "evidence_status": "external_trace_supplement_not_controlled_runtime",
    }
    (output_dir / "existing_agent_trace_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    write_report(output_dir / "existing_agent_trace_report.md", rows_frame, summary)
    print(f"Wrote existing trace supplement to {output_dir / 'existing_agent_trace_report.md'}")


if __name__ == "__main__":
    main()
