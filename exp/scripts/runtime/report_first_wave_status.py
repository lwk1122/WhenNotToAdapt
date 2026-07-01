from __future__ import annotations

import argparse
import json
from pathlib import Path

from .report_runtime_batch_status import (
    DEFAULT_PREFLIGHT,
    DEFAULT_TASK_MANIFEST,
    PRIMARY_COMPARISONS,
    ensure_dir,
    read_csv_optional,
    read_json_optional,
    status_counts,
    summarize_checklist,
    summarize_controller_status,
    summarize_overview,
    summarize_packets,
    summarize_pair_readiness,
    write_status_report,
)


FIRST_WAVE_BUNDLE_DIR = Path("exp/results/emse_runtime/first_wave_execution_bundle_v1")
FIRST_WAVE_EMPTY_RESULTS = FIRST_WAVE_BUNDLE_DIR / "runtime_task_results_empty.csv"
FIRST_WAVE_RECORDED_RESULTS = FIRST_WAVE_BUNDLE_DIR / "runtime_task_results_recorded.csv"
FIRST_WAVE_MATRIX = FIRST_WAVE_BUNDLE_DIR / "isolated_execution_manifest.csv"
FIRST_WAVE_CHECKLIST = FIRST_WAVE_BUNDLE_DIR / "row_execution_checklist.csv"
FIRST_WAVE_PACKET_INDEX = Path("exp/results/emse_runtime/first_wave_execution_packets_v1/packet_index.csv")
FIRST_WAVE_OUTPUT_DIR = Path("exp/results/emse_runtime/first_wave_batch_status_v1")


def resolve_task_results(explicit_path: Path | None) -> tuple[Path, str]:
    if explicit_path is not None:
        return explicit_path, "explicit"
    if FIRST_WAVE_RECORDED_RESULTS.exists():
        return FIRST_WAVE_RECORDED_RESULTS, "recorded"
    return FIRST_WAVE_EMPTY_RESULTS, "empty_template"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Report first-wave controlled-runtime status, preferring recorded rows when present."
    )
    parser.add_argument("--task-results", type=Path, default=None)
    parser.add_argument("--matrix", type=Path, default=FIRST_WAVE_MATRIX)
    parser.add_argument("--task-manifest", type=Path, default=DEFAULT_TASK_MANIFEST)
    parser.add_argument("--checklist", type=Path, default=FIRST_WAVE_CHECKLIST)
    parser.add_argument("--packet-index", type=Path, default=FIRST_WAVE_PACKET_INDEX)
    parser.add_argument("--preflight-summary", type=Path, default=DEFAULT_PREFLIGHT)
    parser.add_argument("--output-dir", type=Path, default=FIRST_WAVE_OUTPUT_DIR)
    args = parser.parse_args()

    selected_results, selected_kind = resolve_task_results(args.task_results)
    matrix = read_csv_optional(args.matrix)
    task_manifest = read_csv_optional(args.task_manifest)
    results = read_csv_optional(selected_results)
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
        "task_results": str(selected_results),
        "checklist": str(args.checklist),
        "packet_index": str(args.packet_index),
        "preflight_summary": str(args.preflight_summary),
    }
    source_selection = {
        "selected_results_kind": selected_kind,
        "selected_task_results": str(selected_results),
        "recorded_results": str(FIRST_WAVE_RECORDED_RESULTS),
        "recorded_results_exists": FIRST_WAVE_RECORDED_RESULTS.exists(),
        "empty_template_results": str(FIRST_WAVE_EMPTY_RESULTS),
        "third_party_execution_performed_by_this_script": False,
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
                "source_selection": source_selection,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (output_dir / "first_wave_status_source.json").write_text(
        json.dumps(source_selection, indent=2),
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
    print(
        "Wrote first-wave controlled-runtime status to "
        f"{output_dir / 'runtime_batch_status_report.md'} using {selected_kind} results."
    )


if __name__ == "__main__":
    main()
