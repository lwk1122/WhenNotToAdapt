from __future__ import annotations

import argparse
import sys

from build_manifests import main as build_manifests_main
from certificate_diagnostics import main as certificate_diagnostics_main
from controller_benchmark import main as controller_benchmark_main
from distributional_diagnostics import main as distributional_diagnostics_main
from online_runtime_simulator import main as online_runtime_simulator_main
from render_report import main as render_report_main
from simulator_validation import main as simulator_validation_main
from structural_diagnostics import main as structural_diagnostics_main


def run_subcommand(name: str, fn, extra_args: list[str] | None = None) -> None:
    old_argv = sys.argv
    try:
        sys.argv = [name, *(extra_args or [])]
        fn()
    finally:
        sys.argv = old_argv


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the full theory-support experiment stack.")
    parser.add_argument("--skip-manifests", action="store_true", help="Reuse existing manifests instead of rebuilding them.")
    parser.add_argument("--benchmark-dataset", choices=["verified", "test", "both", "rebench", "smith", "all"], default="all")
    parser.add_argument("--benchmark-seeds", type=int, default=64)
    parser.add_argument("--benchmark-max-tasks", type=int, default=None)
    parser.add_argument("--online-seeds", type=int, default=32)
    parser.add_argument("--online-horizon", type=int, default=1200)
    args = parser.parse_args()

    if not args.skip_manifests:
        print("1/8 Building manifests...")
        run_subcommand("build_manifests.py", build_manifests_main)
    else:
        print("1/8 Skipping manifest build and reusing existing files...")

    print("2/8 Running structural diagnostics...")
    run_subcommand("structural_diagnostics.py", structural_diagnostics_main)
    print("3/8 Running certificate diagnostics...")
    run_subcommand("certificate_diagnostics.py", certificate_diagnostics_main)
    print("4/8 Running distributional diagnostics...")
    run_subcommand("distributional_diagnostics.py", distributional_diagnostics_main)
    print("5/8 Running simulator predictive validation...")
    run_subcommand("simulator_validation.py", simulator_validation_main)

    print("6/8 Running controller benchmark...")
    controller_args = ["--dataset", args.benchmark_dataset, "--seeds", str(args.benchmark_seeds)]
    if args.benchmark_max_tasks is not None:
        controller_args.extend(["--max-tasks", str(args.benchmark_max_tasks)])
    run_subcommand("controller_benchmark.py", controller_benchmark_main, controller_args)

    print("7/8 Running theorem-faithful online simulator...")
    online_args = ["--dataset", args.benchmark_dataset, "--seeds", str(args.online_seeds), "--horizon", str(args.online_horizon)]
    run_subcommand("online_runtime_simulator.py", online_runtime_simulator_main, online_args)

    print("8/8 Rendering markdown report...")
    run_subcommand("render_report.py", render_report_main)
    print("All theory-support scripts finished.")


if __name__ == "__main__":
    main()
