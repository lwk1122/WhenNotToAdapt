from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from .analyze_runtime_pairs import analyze_pair, frame_to_markdown


DEFAULT_OUTPUT_DIR = Path("exp/results/emse_runtime/lmstudio_executable_context_gate_repeat_analysis_v1")
DEFAULT_RUN_DIRS = [
    Path("exp/results/emse_runtime/lmstudio_executable_context_gate_v1"),
    Path("exp/results/emse_runtime/lmstudio_executable_context_gate_repeat_v1"),
]


KEY_METRICS = ["success", "model_calls", "total_tokens", "latency_seconds"]


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_runs(run_dirs: list[Path]) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for index, run_dir in enumerate(run_dirs, start=1):
        path = run_dir / "runtime_task_results.csv"
        if not path.exists():
            raise FileNotFoundError(path)
        frame = pd.read_csv(path)
        frame["replicate_id"] = f"replicate_{index}"
        frame["source_result_dir"] = str(run_dir)
        frame["original_instance_id"] = frame["instance_id"].astype(str)
        frame["instance_id"] = frame["replicate_id"] + "::" + frame["original_instance_id"]
        frames.append(frame)
    if not frames:
        raise ValueError("No run directories were provided.")
    return pd.concat(frames, ignore_index=True)


def controller_summary(frame: pd.DataFrame) -> pd.DataFrame:
    grouped = frame.groupby("controller", dropna=False)
    rows = []
    for controller, items in grouped:
        rows.append(
            {
                "controller": controller,
                "n": int(len(items)),
                "success_rate": float(pd.to_numeric(items["success"], errors="coerce").mean()),
                "mean_calls": float(pd.to_numeric(items["model_calls"], errors="coerce").mean()),
                "mean_total_tokens": float(pd.to_numeric(items["total_tokens"], errors="coerce").mean()),
                "mean_latency_s": float(pd.to_numeric(items["latency_seconds"], errors="coerce").mean()),
            }
        )
    return pd.DataFrame(rows).sort_values("controller").reset_index(drop=True)


def run_pair(frame: pd.DataFrame, target: str, reference: str, args: argparse.Namespace) -> tuple[pd.DataFrame, dict]:
    return analyze_pair(
        task_results=frame,
        target=target,
        reference=reference,
        metrics=KEY_METRICS,
        success_margin=args.success_margin,
        min_publication_pairs=args.min_publication_pairs,
        ci_alpha=args.ci_alpha,
        bootstrap_rounds=args.bootstrap_rounds,
        seed=args.seed,
    )


def write_report(
    path: Path,
    summary: pd.DataFrame,
    medium_high_vs_full: pd.DataFrame,
    medium_high_vs_low: pd.DataFrame,
    high_only_vs_full: pd.DataFrame,
    run_dirs: list[Path],
) -> None:
    lines = [
        "# Executable Context-Gate Repeat Analysis",
        "",
        "This analysis treats each `replicate x task` pair as the paired unit. It is a small repeatability check over the same controlled task set, not a new independent benchmark.",
        "",
        "## Source Runs",
        "",
    ]
    lines.extend(f"- `{run_dir}`" for run_dir in run_dirs)
    lines.extend(
        [
            "",
            "## Controller Summary",
            "",
            frame_to_markdown(summary),
            "",
            "## Medium/High Gate vs Full Context",
            "",
            frame_to_markdown(medium_high_vs_full),
            "",
            "## Medium/High Gate vs Low Context",
            "",
            frame_to_markdown(medium_high_vs_low),
            "",
            "## High-Only Gate vs Full Context",
            "",
            frame_to_markdown(high_only_vs_full),
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Aggregate repeated executable context-gate runs.")
    parser.add_argument("--run-dirs", type=Path, nargs="+", default=DEFAULT_RUN_DIRS)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--success-margin", type=float, default=0.10)
    parser.add_argument("--min-publication-pairs", type=int, default=30)
    parser.add_argument("--ci-alpha", type=float, default=0.05)
    parser.add_argument("--bootstrap-rounds", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=23)
    args = parser.parse_args()

    output_dir = ensure_dir(args.output_dir)
    combined = load_runs(args.run_dirs)
    combined_path = output_dir / "runtime_task_results_repeated.csv"
    combined.to_csv(combined_path, index=False)

    summary = controller_summary(combined)
    summary.to_csv(output_dir / "runtime_repeat_controller_summary.csv", index=False)

    mh_full, mh_full_summary = run_pair(combined, "context_gate_medium_high", "standard_full", args)
    mh_low, mh_low_summary = run_pair(combined, "context_gate_medium_high", "direct_low", args)
    high_full, high_full_summary = run_pair(combined, "context_gate_high_only", "standard_full", args)

    mh_full.to_csv(output_dir / "medium_high_vs_full_metrics.csv", index=False)
    mh_low.to_csv(output_dir / "medium_high_vs_low_metrics.csv", index=False)
    high_full.to_csv(output_dir / "high_only_vs_full_metrics.csv", index=False)
    pd.DataFrame([mh_full_summary]).to_csv(output_dir / "medium_high_vs_full_summary.csv", index=False)
    pd.DataFrame([mh_low_summary]).to_csv(output_dir / "medium_high_vs_low_summary.csv", index=False)
    pd.DataFrame([high_full_summary]).to_csv(output_dir / "high_only_vs_full_summary.csv", index=False)

    write_report(
        output_dir / "runtime_repeat_analysis_report.md",
        summary,
        mh_full,
        mh_low,
        high_full,
        args.run_dirs,
    )
    print(f"Wrote repeated context-gate analysis to {output_dir / 'runtime_repeat_analysis_report.md'}")


if __name__ == "__main__":
    main()
