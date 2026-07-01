from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from common import (
    DATASET_DIR,
    MANIFEST_DIR,
    codetrace_row_to_manifest,
    ensure_dir,
    iter_parquet_rows,
    manifest_paths,
    read_parquet,
    task_row_to_manifest,
    trajectory_row_to_manifest,
    write_json,
)


def build_swe_bench_tasks() -> pd.DataFrame:
    rows: list[dict] = []
    data_dir = DATASET_DIR / "SWE-bench" / "Data"
    for split in ["train", "dev", "test"]:
        path = data_dir / f"{split}-00000-of-00001.parquet"
        frame = read_parquet(path)
        for row in frame.to_dict("records"):
            rows.append(task_row_to_manifest(row, source="SWE-bench", split=split))
    return pd.DataFrame(rows)


def build_swe_verified_tasks() -> pd.DataFrame:
    path = DATASET_DIR / "SWE-bench_Verified" / "data" / "test-00000-of-00001.parquet"
    frame = read_parquet(path)
    rows = [task_row_to_manifest(row, source="SWE-bench_Verified", split="test") for row in frame.to_dict("records")]
    return pd.DataFrame(rows)


def build_swe_smith_tasks() -> pd.DataFrame:
    rows: list[dict] = []
    for path in sorted((DATASET_DIR / "SWE-smith" / "data").glob("*.parquet")):
        frame = read_parquet(path)
        for row in frame.to_dict("records"):
            rows.append(task_row_to_manifest(row, source="SWE-smith", split="train"))
    return pd.DataFrame(rows)


def build_swe_rebench_tasks() -> pd.DataFrame:
    rows: list[dict] = []
    for path in sorted((DATASET_DIR / "SWE-rebench" / "data").glob("*.parquet")):
        split_name = path.stem.split("-")[0]
        frame = read_parquet(path)
        for row in frame.to_dict("records"):
            manifest_row = task_row_to_manifest(row, source="SWE-rebench", split=split_name)
            meta = row.get("meta") or {}
            manifest_row["meta_modified_files"] = float(meta.get("num_modified_files") or 0)
            manifest_row["meta_has_test_patch"] = float(bool(meta.get("has_test_patch")))
            manifest_row["meta_issue_score"] = float(((meta.get("llm_score") or {}).get("issue_text_score")) or 0)
            manifest_row["meta_test_score"] = float(((meta.get("llm_score") or {}).get("test_score")) or 0)
            manifest_row["meta_difficulty_score"] = float(((meta.get("llm_score") or {}).get("difficulty_score")) or 0)
            rows.append(manifest_row)
    return pd.DataFrame(rows)


def build_swe_agent_trajectory_manifest(max_rows: int | None = None) -> pd.DataFrame:
    records: list[dict] = []
    seen = 0
    for path in sorted((DATASET_DIR / "SWE-agent-trajectories" / "data").glob("*.parquet")):
        for row in iter_parquet_rows(path):
            records.append(trajectory_row_to_manifest(row))
            seen += 1
            if max_rows is not None and seen >= max_rows:
                return pd.DataFrame(records)
    return pd.DataFrame(records)


def build_codetrace_manifest() -> pd.DataFrame:
    rows: list[dict] = []
    verified_path = DATASET_DIR / "CodeTraceBench" / "bench_manifest.verified.parquet"
    full_path = DATASET_DIR / "CodeTraceBench" / "bench_manifest.full.parquet"
    for split, path in [("verified", verified_path), ("full", full_path)]:
        frame = read_parquet(path)
        for row in frame.to_dict("records"):
            rows.append(codetrace_row_to_manifest(row, split=split))
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build lightweight manifests for theory-support experiments.")
    parser.add_argument("--output-dir", type=Path, default=MANIFEST_DIR, help="Output directory for generated CSV manifests.")
    parser.add_argument(
        "--max-trajectory-rows",
        type=int,
        default=None,
        help="Optional cap for SWE-agent trajectory rows, useful for smoke tests.",
    )
    args = parser.parse_args()

    output_dir = ensure_dir(args.output_dir)
    paths = manifest_paths(output_dir)

    swe_bench_tasks = build_swe_bench_tasks()
    swe_verified_tasks = build_swe_verified_tasks()
    swe_smith_tasks = build_swe_smith_tasks()
    swe_rebench_tasks = build_swe_rebench_tasks()
    swe_agent_trajectories = build_swe_agent_trajectory_manifest(max_rows=args.max_trajectory_rows)
    codetrace_manifest = build_codetrace_manifest()

    swe_bench_tasks.to_csv(paths["swe_bench_tasks"], index=False)
    swe_verified_tasks.to_csv(paths["swe_verified_tasks"], index=False)
    swe_smith_tasks.to_csv(paths["swe_smith_tasks"], index=False)
    swe_rebench_tasks.to_csv(paths["swe_rebench_tasks"], index=False)
    swe_agent_trajectories.to_csv(paths["swe_agent_trajectories"], index=False)
    codetrace_manifest.to_csv(paths["codetrace_manifest"], index=False)

    summary = {
        "swe_bench_tasks": int(len(swe_bench_tasks)),
        "swe_verified_tasks": int(len(swe_verified_tasks)),
        "swe_smith_tasks": int(len(swe_smith_tasks)),
        "swe_rebench_tasks": int(len(swe_rebench_tasks)),
        "swe_agent_trajectories": int(len(swe_agent_trajectories)),
        "codetrace_manifest": int(len(codetrace_manifest)),
        "output_dir": str(output_dir),
    }
    write_json(paths["manifest_summary"], summary)

    print("Manifest build complete.")
    for key, value in summary.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
