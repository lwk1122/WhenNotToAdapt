from __future__ import annotations

import argparse
import json
import os
import stat
from pathlib import Path
from typing import Any


DEFAULT_OUTPUT_DIR = Path("exp/results/emse_runtime/first_wave_docker_isolation_plan_v1")
DEFAULT_RUNTIME_OUTPUT_DIR = Path("exp/results/emse_runtime/first_wave_docker_runtime_v1")
DEFAULT_BRIDGE_SUMMARY = Path("exp/results/emse_runtime/first_wave_shadow_bridge_v1/first_wave_shadow_bridge_summary.json")
DEFAULT_MODEL = "qwen2.5-coder-7b-instruct-mlx"
DEFAULT_IMAGE = "camc-emse-first-wave-runtime:latest"


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Missing JSON file: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def make_executable(path: Path) -> None:
    mode = path.stat().st_mode
    path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def dockerfile_text() -> str:
    return """FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \\
    PIP_NO_CACHE_DIR=1

RUN apt-get update \\
    && apt-get install -y --no-install-recommends \\
       ca-certificates \\
       build-essential \\
       git \\
       ripgrep \\
    && rm -rf /var/lib/apt/lists/*

RUN python -m pip install pandas numpy pyarrow

WORKDIR /work
CMD ["python3", "-m", "exp.scripts.emse_runtime.run_first_wave_shadow_bridge", "--help"]
"""


def launch_script_text(runtime_output_dir: Path, image_name: str, model: str) -> str:
    return f"""#!/usr/bin/env bash
set -euo pipefail

PLAN_DIR="$(cd "$(dirname "${{BASH_SOURCE[0]}}")" && pwd)"
CAMC_ROOT="${{CAMC_ROOT:-$(cd "$PLAN_DIR/../../../.." && pwd)}}"
RUNTIME_OUTPUT="${{CAMC_RUNTIME_OUTPUT:-$CAMC_ROOT/{runtime_output_dir.as_posix()}}}"
IMAGE_NAME="${{CAMC_DOCKER_IMAGE:-{image_name}}}"
LMSTUDIO_BASE_URL="${{LMSTUDIO_BASE_URL:-http://host.docker.internal:1234/v1}}"
LMSTUDIO_MODEL="${{LMSTUDIO_MODEL:-{model}}}"
LIMIT_TASKS="${{CAMC_LIMIT_TASKS:-0}}"

if [[ "${{CAMC_DOCKER_RUNTIME_ACK:-}}" != "1" ]]; then
  echo "CAMC_DOCKER_RUNTIME_ACK=1 is required before building/running the isolated first-wave container." >&2
  exit 2
fi

if [[ -n "${{SSH_AUTH_SOCK:-}}" ]]; then
  echo "SSH_AUTH_SOCK must be removed before launching untrusted repository execution." >&2
  exit 2
fi

if env | grep -E '(_TOKEN=|_PASSWORD=|AWS_|GCP_|GOOGLE_|AZURE_|OPENAI_API_KEY=|ANTHROPIC_API_KEY=|GITHUB_TOKEN=)' >/dev/null; then
  echo "Potential credential-bearing environment variables are present; launch from a scrubbed shell." >&2
  exit 2
fi

mkdir -p "$RUNTIME_OUTPUT"

docker build -f "$PLAN_DIR/Dockerfile" -t "$IMAGE_NAME" "$PLAN_DIR"

docker run --rm \\
  --name camc-emse-first-wave-runtime \\
  --network bridge \\
  -e PYTHONDONTWRITEBYTECODE=1 \\
  -e CAMC_RUNTIME_ISOLATION_ACK=1 \\
  -e LMSTUDIO_BASE_URL="$LMSTUDIO_BASE_URL" \\
  -e LMSTUDIO_MODEL="$LMSTUDIO_MODEL" \\
  -v "$CAMC_ROOT:/work:ro" \\
  -v "$RUNTIME_OUTPUT:/work/{runtime_output_dir.as_posix()}:rw" \\
  -w /work \\
  "$IMAGE_NAME" \\
  python3 -m exp.scripts.emse_runtime.run_first_wave_shadow_bridge \\
    --output-dir {runtime_output_dir.as_posix()} \\
    --execute \\
    --live-repo \\
    --ack-third-party-code \\
    --allow-clone \\
    --limit-tasks "$LIMIT_TASKS" \\
    --base-url "$LMSTUDIO_BASE_URL" \\
    --model "$LMSTUDIO_MODEL"
"""


def validation_script_text(runtime_output_dir: Path) -> str:
    result_path = runtime_output_dir / "runtime_task_results_recorded.csv"
    validation_dir = runtime_output_dir / "validation"
    analysis_dir = runtime_output_dir / "pair_analysis"
    publication_dir = runtime_output_dir / "publication_artifacts"
    return f"""#!/usr/bin/env bash
set -euo pipefail

python3 -m exp.scripts.emse_runtime.validate_runtime_results \\
  --task-results {result_path.as_posix()} \\
  --output-dir {validation_dir.as_posix()} \\
  --target sempc_lite \\
  --reference rsrc_guarded

python3 -m exp.scripts.emse_runtime.analyze_runtime_pairs \\
  --task-results {result_path.as_posix()} \\
  --output-dir {analysis_dir.as_posix()} \\
  --target sempc_lite \\
  --reference rsrc_guarded \\
  --success-margin 0.05 \\
  --min-publication-pairs 30

python3 -m exp.scripts.emse_runtime.make_runtime_publication_artifacts \\
  --analysis-dir {analysis_dir.as_posix()} \\
  --output-dir {publication_dir.as_posix()} \\
  --evidence-status first_wave_isolated_runtime_pilot \\
  --scope-note 'First-wave isolated runtime pilot; do not use for 5pp solve-rate non-inferiority unless the paired CI is decisive.'
"""


def report_text(summary: dict[str, Any], runtime_output_dir: Path, image_name: str) -> str:
    rows = int(summary.get("selected_rows", 0) or 0)
    tasks = int(summary.get("selected_tasks", 0) or 0)
    repos = int(summary.get("repositories", 0) or 0)
    controllers = ", ".join(summary.get("controllers", []))
    return f"""# First-Wave Docker Isolation Plan

## Scope

- Status: `plan_only`
- Selected tasks: `{tasks}`
- Selected rows: `{rows}`
- Repositories: `{repos}`
- Controllers: `{controllers}`
- Docker image tag: `{image_name}`
- Runtime output directory: `{runtime_output_dir.as_posix()}`
- Third-party repository execution performed by this plan generator: `False`
- Docker build performed by this plan generator: `False`
- Docker run performed by this plan generator: `False`

## Generated Files

- `Dockerfile`
- `run_first_wave_bridge_in_docker.sh`
- `validate_first_wave_docker_results.sh`
- `first_wave_docker_isolation_summary.json`

## Execution Boundary

The generated launch script is the first artifact in this workflow that can execute third-party repository code. It refuses to run unless:

1. `CAMC_DOCKER_RUNTIME_ACK=1` is set in the host shell;
2. `SSH_AUTH_SOCK` is absent;
3. common credential-bearing environment variables are absent;
4. Docker is available;
5. the operator explicitly runs the launch script.

The launch mounts the repository root read-only at `/work` and mounts only `{runtime_output_dir.as_posix()}` read-write for cloned repositories, logs, and converted result CSVs.

For an isolated smoke run, set `CAMC_LIMIT_TASKS=1`. The default `CAMC_LIMIT_TASKS=0` executes the full first-wave selection.

## Known Limitation

This wrapper isolates the current shadow-runtime bridge. The bridge can clone repositories and run focused pytest commands, but it does not yet build the official SWE-bench per-task environments. Rows produced by this path should therefore be treated as first-wave pilot/runtime feasibility evidence unless task-level dependency setup is verified in the logs.

## Post-Run Validation

After a real isolated Docker run, execute:

```bash
bash {DEFAULT_OUTPUT_DIR.as_posix()}/validate_first_wave_docker_results.sh
```

Do not run paired analysis or manuscript artifact generation if validation fails.
"""


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prepare a plan-only Docker wrapper for the first-wave controlled-runtime bridge."
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--runtime-output-dir", type=Path, default=DEFAULT_RUNTIME_OUTPUT_DIR)
    parser.add_argument("--bridge-summary", type=Path, default=DEFAULT_BRIDGE_SUMMARY)
    parser.add_argument("--image-name", default=DEFAULT_IMAGE)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    args = parser.parse_args()

    output_dir = ensure_dir(args.output_dir)
    bridge_summary = load_json(args.bridge_summary)

    dockerfile = output_dir / "Dockerfile"
    launch_script = output_dir / "run_first_wave_bridge_in_docker.sh"
    validation_script = output_dir / "validate_first_wave_docker_results.sh"
    report = output_dir / "first_wave_docker_isolation_report.md"
    summary_path = output_dir / "first_wave_docker_isolation_summary.json"

    dockerfile.write_text(dockerfile_text(), encoding="utf-8")
    launch_script.write_text(
        launch_script_text(args.runtime_output_dir, args.image_name, args.model),
        encoding="utf-8",
    )
    validation_script.write_text(validation_script_text(args.runtime_output_dir), encoding="utf-8")
    make_executable(launch_script)
    make_executable(validation_script)

    summary = {
        "status": "plan_only",
        "selected_rows": int(bridge_summary.get("selected_rows", 0) or 0),
        "selected_tasks": int(bridge_summary.get("selected_tasks", 0) or 0),
        "repositories": int(bridge_summary.get("repositories", 0) or 0),
        "controllers": bridge_summary.get("controllers", []),
        "bridge_summary": str(args.bridge_summary),
        "runtime_output_dir": str(args.runtime_output_dir),
        "image_name": args.image_name,
        "model": args.model,
        "third_party_execution_performed": False,
        "docker_build_performed": False,
        "docker_run_performed": False,
        "host_ack_required": "CAMC_DOCKER_RUNTIME_ACK=1",
        "container_ack_provided": "CAMC_RUNTIME_ISOLATION_ACK=1",
        "limit_tasks_env": "CAMC_LIMIT_TASKS",
        "sensitive_env_guard": True,
        "root_mount": "read_only",
        "runtime_output_mount": "read_write",
        "known_limitation": "The wrapper does not build official SWE-bench per-task environments; dependency setup must be verified before treating rows as task-quality evidence.",
        "generated_files": {
            "dockerfile": str(dockerfile),
            "launch_script": str(launch_script),
            "validation_script": str(validation_script),
            "report": str(report),
        },
    }
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    report.write_text(report_text(summary, args.runtime_output_dir, args.image_name), encoding="utf-8")

    print(f"Wrote Docker isolation plan to {output_dir}")


if __name__ == "__main__":
    main()
