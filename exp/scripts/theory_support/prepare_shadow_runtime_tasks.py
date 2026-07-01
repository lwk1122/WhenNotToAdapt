from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from common import DATASET_DIR, RESULTS_DIR, ensure_dir, write_json
from controller_benchmark import apply_priors, fit_priors


DEFAULT_OUTPUT_DIR = RESULTS_DIR / "shadow_runtime"
VERIFIED_PARQUET = DATASET_DIR / "SWE-bench_Verified" / "data" / "test-00000-of-00001.parquet"


def parse_json_list(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []


def load_verified_tasks(path: Path) -> pd.DataFrame:
    frame = pq.read_table(path).to_pandas()
    frame["FAIL_TO_PASS"] = frame["FAIL_TO_PASS"].map(parse_json_list)
    frame["PASS_TO_PASS"] = frame["PASS_TO_PASS"].map(parse_json_list)
    frame["problem_tokens"] = frame["problem_statement"].fillna("").map(lambda text: len(text) / 4.0)
    frame["hints_tokens"] = frame["hints_text"].fillna("").map(lambda text: len(text) / 4.0)
    frame["hints_nonempty"] = frame["hints_text"].fillna("").map(lambda text: float(bool(text.strip())))
    frame["fail_to_pass_count"] = frame["FAIL_TO_PASS"].map(len).astype(float)
    frame["pass_to_pass_count"] = frame["PASS_TO_PASS"].map(len).astype(float)
    frame["fail_tests_tokens"] = frame["FAIL_TO_PASS"].map(lambda items: len(json.dumps(items, ensure_ascii=False)) / 4.0)
    frame["pass_tests_tokens"] = frame["PASS_TO_PASS"].map(lambda items: len(json.dumps(items, ensure_ascii=False)) / 4.0)
    frame["gold_patch_files"] = frame["patch"].fillna("").map(lambda text: float(text.count("diff --git ")))
    frame["gold_patch_lines"] = frame["patch"].fillna("").map(
        lambda text: float(sum(1 for line in text.splitlines() if line.startswith("+") or line.startswith("-")))
    )
    difficulty_map = {
        "15 min - 1 hour": 0.50,
        "1-4 hours": 0.70,
        "<15 min fix": 0.25,
        ">4 hours": 0.90,
    }
    frame["difficulty_score"] = frame["difficulty"].map(lambda value: difficulty_map.get(value or "", 0.50)).astype(float)
    return frame


def score_shadow_tasks(tasks: pd.DataFrame) -> pd.DataFrame:
    risk_prior, atom_prior = fit_priors(RESULTS_DIR / "manifests")
    scored = apply_priors(tasks, risk_prior, atom_prior)
    scored["shadow_risk_score"] = (
        0.45 * scored["e_proxy"]
        + 0.30 * scored["d_proxy"]
        + 0.15 * scored["q_proxy"]
        + 0.10 * scored["difficulty_score"]
    )
    manageable = (
        1.0
        - np.clip(scored["fail_to_pass_count"] / 8.0, 0.0, 1.0)
        + 0.35 * np.clip(1.0 - scored["gold_patch_lines"] / 120.0, 0.0, 1.0)
    )
    scored["shadow_selection_score"] = 0.75 * scored["shadow_risk_score"] + 0.25 * manageable
    if len(scored) >= 3 and scored["shadow_risk_score"].nunique() >= 3:
        scored["risk_tier"] = pd.qcut(
            scored["shadow_risk_score"].rank(method="first"),
            q=3,
            labels=["low", "mid", "high"],
            duplicates="drop",
        )
        scored["risk_tier"] = scored["risk_tier"].astype(str)
    else:
        scored["risk_tier"] = "mid"
    return scored


def select_shadow_subset(tasks: pd.DataFrame, limit: int, max_per_repo: int) -> pd.DataFrame:
    selected_indices: list[int] = []
    repo_counts: dict[str, int] = {}
    tiers = ["high", "mid", "low"]
    tier_frames = {
        tier: tasks[tasks["risk_tier"] == tier].sort_values(
            ["shadow_selection_score", "shadow_risk_score", "fail_to_pass_count"],
            ascending=[False, False, True],
        )
        for tier in tiers
    }

    exhausted = False
    while len(selected_indices) < limit and not exhausted:
        exhausted = True
        for tier in tiers:
            tier_frame = tier_frames[tier]
            for idx, row in tier_frame.iterrows():
                repo = str(row["repo"])
                if idx in selected_indices:
                    continue
                if repo_counts.get(repo, 0) >= max_per_repo:
                    continue
                selected_indices.append(int(idx))
                repo_counts[repo] = repo_counts.get(repo, 0) + 1
                exhausted = False
                break
            if len(selected_indices) >= limit:
                break

    subset = tasks.loc[selected_indices].copy()
    subset = subset.sort_values(["risk_tier", "shadow_selection_score"], ascending=[False, False]).reset_index(drop=True)
    subset["selection_rank"] = np.arange(1, len(subset) + 1)
    return subset


def manifest_payload(frame: pd.DataFrame, limit: int, max_per_repo: int) -> dict:
    return {
        "source": "SWE-bench_Verified",
        "rows": int(len(frame)),
        "requested_limit": int(limit),
        "max_per_repo": int(max_per_repo),
        "risk_tier_counts": frame["risk_tier"].value_counts().to_dict(),
        "repo_counts": frame["repo"].value_counts().to_dict(),
        "mean_shadow_risk_score": float(frame["shadow_risk_score"].mean()) if not frame.empty else 0.0,
        "columns": list(frame.columns),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare a live shadow-runtime task manifest from local SWE-bench Verified data.")
    parser.add_argument("--input", type=Path, default=VERIFIED_PARQUET)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--limit", type=int, default=24)
    parser.add_argument("--max-per-repo", type=int, default=4)
    parser.add_argument("--repos", nargs="*", default=None, help="Optional repo allowlist such as sympy/sympy sphinx-doc/sphinx")
    parser.add_argument("--instance-ids", nargs="*", default=None, help="Optional explicit instance-id allowlist")
    args = parser.parse_args()

    ensure_dir(args.output_dir)
    raw_tasks = load_verified_tasks(args.input)
    if args.repos:
        raw_tasks = raw_tasks[raw_tasks["repo"].isin(set(args.repos))].copy()
    if args.instance_ids:
        raw_tasks = raw_tasks[raw_tasks["instance_id"].isin(set(args.instance_ids))].copy()
    scored_tasks = score_shadow_tasks(raw_tasks)
    subset = select_shadow_subset(scored_tasks, limit=args.limit, max_per_repo=args.max_per_repo)

    selected_columns = [
        "selection_rank",
        "repo",
        "instance_id",
        "base_commit",
        "problem_statement",
        "hints_text",
        "FAIL_TO_PASS",
        "PASS_TO_PASS",
        "difficulty",
        "difficulty_score",
        "problem_tokens",
        "hints_tokens",
        "fail_to_pass_count",
        "pass_to_pass_count",
        "gold_patch_files",
        "gold_patch_lines",
        "e_proxy",
        "d_proxy",
        "q_proxy",
        "shadow_risk_score",
        "shadow_selection_score",
        "risk_tier",
    ]
    subset = subset[selected_columns].copy()
    subset["FAIL_TO_PASS"] = subset["FAIL_TO_PASS"].map(lambda items: json.dumps(items, ensure_ascii=False))
    subset["PASS_TO_PASS"] = subset["PASS_TO_PASS"].map(lambda items: json.dumps(items, ensure_ascii=False))

    csv_path = args.output_dir / "task_manifest.csv"
    json_path = args.output_dir / "task_manifest.json"
    summary_path = args.output_dir / "task_manifest_summary.json"

    subset.to_csv(csv_path, index=False)
    json_path.write_text(subset.to_json(orient="records", force_ascii=False, indent=2), encoding="utf-8")
    write_json(summary_path, manifest_payload(subset, limit=args.limit, max_per_repo=args.max_per_repo))

    print(f"Wrote shadow-runtime task manifest to {csv_path}")
    print(f"Selected {len(subset)} tasks across {subset['repo'].nunique()} repositories.")


if __name__ == "__main__":
    main()
