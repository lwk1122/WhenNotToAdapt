from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import socket
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd


DEFAULT_MATRIX = Path("exp/results/emse_runtime/manifest_v1/runtime_execution_matrix.csv")
DEFAULT_MANIFEST = Path("exp/results/emse_runtime/manifest_v1/task_manifest.csv")
DEFAULT_SWEBENCH_PARQUET = Path("exp/Dataset/SWE-bench_Verified/data/test-00000-of-00001.parquet")
DEFAULT_OUTPUT_DIR = Path("exp/results/emse_runtime/preflight_v1")
DEFAULT_RUN_ROOT = Path("exp/results/emse_runtime/runs")
DEFAULT_LMSTUDIO_URL = "http://127.0.0.1:1234/v1"
SENSITIVE_ENV_PATTERNS = ["KEY", "TOKEN", "SECRET", "PASSWORD", "CREDENTIAL", "AUTH"]


@dataclass
class CheckResult:
    name: str
    status: str
    message: str
    evidence: str = ""

    def as_dict(self) -> dict[str, str]:
        return {
            "name": self.name,
            "status": self.status,
            "message": self.message,
            "evidence": self.evidence,
        }


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def check_file(path: Path, name: str) -> CheckResult:
    if path.exists() and path.is_file():
        return CheckResult(name, "PASS", "Required file exists.", str(path))
    return CheckResult(name, "FAIL", "Required file is missing.", str(path))


def check_matrix(matrix_path: Path, manifest_path: Path) -> list[CheckResult]:
    checks = [check_file(matrix_path, "execution_matrix_exists"), check_file(manifest_path, "task_manifest_exists")]
    if any(check.status == "FAIL" for check in checks):
        return checks

    matrix = pd.read_csv(matrix_path)
    manifest = pd.read_csv(manifest_path)
    required = {"instance_id", "controller", "execute_status", "requires_isolation", "planned_output_dir"}
    missing = sorted(required - set(matrix.columns))
    if missing:
        checks.append(CheckResult("execution_matrix_schema", "FAIL", "Execution matrix is missing required columns.", ",".join(missing)))
        return checks

    tasks = int(matrix["instance_id"].nunique())
    controllers = int(matrix["controller"].nunique())
    rows = int(len(matrix))
    manifest_tasks = int(manifest["instance_id"].nunique()) if "instance_id" in manifest.columns else 0
    status_counts = matrix["execute_status"].fillna("").astype(str).value_counts().to_dict()
    isolation_values = matrix["requires_isolation"].astype(str).str.lower().isin(["true", "1", "yes"])

    if manifest_tasks != tasks:
        checks.append(
            CheckResult(
                "execution_matrix_task_match",
                "FAIL",
                "Execution matrix task count does not match manifest task count.",
                f"matrix_tasks={tasks};manifest_tasks={manifest_tasks}",
            )
        )
    else:
        checks.append(
            CheckResult(
                "execution_matrix_task_match",
                "PASS",
                "Execution matrix task count matches manifest.",
                f"tasks={tasks};controllers={controllers};rows={rows}",
            )
        )

    if not isolation_values.all():
        checks.append(CheckResult("execution_matrix_isolation_flags", "FAIL", "Some matrix rows are not marked as requiring isolation."))
    else:
        checks.append(CheckResult("execution_matrix_isolation_flags", "PASS", "All matrix rows require isolation."))

    if set(status_counts) == {"not_run"}:
        checks.append(CheckResult("execution_matrix_status", "PASS", "All matrix rows are still planned and not run.", json.dumps(status_counts)))
    else:
        checks.append(CheckResult("execution_matrix_status", "WARN", "Execution matrix contains non-not_run statuses.", json.dumps(status_counts)))

    return checks


def check_writable_directory(path: Path) -> CheckResult:
    try:
        ensure_dir(path)
        probe = path / ".preflight_write_probe"
        probe.write_text("ok\n", encoding="utf-8")
        probe.unlink()
    except Exception as exc:
        return CheckResult("run_root_writable", "FAIL", "Run root is not writable.", f"{path}: {exc}")
    return CheckResult("run_root_writable", "PASS", "Run root is writable.", str(path))


def request_json(url: str, timeout: float) -> dict[str, Any]:
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def check_lmstudio(base_url: str, timeout: float, require: bool) -> CheckResult:
    url = base_url.rstrip("/") + "/models"
    try:
        payload = request_json(url, timeout)
    except (urllib.error.URLError, TimeoutError, socket.timeout, json.JSONDecodeError) as exc:
        return CheckResult(
            "lmstudio_models",
            "FAIL" if require else "WARN",
            "LM Studio /models endpoint is not reachable.",
            f"{url}: {exc}",
        )
    models = payload.get("data", [])
    if not models:
        return CheckResult("lmstudio_models", "FAIL" if require else "WARN", "LM Studio returned no available models.", url)
    model_ids = [str(item.get("id", "")) for item in models[:5]]
    return CheckResult("lmstudio_models", "PASS", "LM Studio /models endpoint is reachable.", ";".join(model_ids))


def check_binary(binary: str, required: bool) -> CheckResult:
    path = shutil.which(binary)
    if path:
        return CheckResult(f"binary_{binary}", "PASS", f"`{binary}` is available.", path)
    return CheckResult(f"binary_{binary}", "FAIL" if required else "WARN", f"`{binary}` is not available on PATH.")


def check_isolation_ack(require_ack: bool, ack_env: str, ack_file: Path | None) -> CheckResult:
    env_value = os.environ.get(ack_env, "")
    file_ok = bool(ack_file and ack_file.exists())
    if env_value == "1" or file_ok:
        evidence = f"{ack_env}=1" if env_value == "1" else str(ack_file)
        return CheckResult("isolation_ack", "PASS", "Isolation acknowledgment is present.", evidence)
    status = "FAIL" if require_ack else "WARN"
    evidence = f"set {ack_env}=1"
    if ack_file:
        evidence += f" or create {ack_file}"
    return CheckResult("isolation_ack", status, "Isolation acknowledgment is missing; do not execute third-party repository code.", evidence)


def check_sensitive_env() -> CheckResult:
    names = []
    for name in os.environ:
        upper = name.upper()
        if any(pattern in upper for pattern in SENSITIVE_ENV_PATTERNS):
            names.append(name)
    if not names:
        return CheckResult("sensitive_environment", "PASS", "No obvious sensitive environment variable names were detected.")
    redacted_names = ",".join(sorted(names)[:20])
    return CheckResult(
        "sensitive_environment",
        "WARN",
        "Potential sensitive environment variables are present; remove them before untrusted repository execution.",
        redacted_names,
    )


def overall_status(checks: list[CheckResult]) -> str:
    if any(check.status == "FAIL" for check in checks):
        return "FAIL"
    if any(check.status == "WARN" for check in checks):
        return "WARN"
    return "PASS"


def write_report(path: Path, checks: list[CheckResult], summary: dict[str, Any]) -> None:
    lines = [
        "# Controlled Runtime Preflight",
        "",
        f"- Overall status: **{summary['status']}**",
        f"- Platform: `{summary['platform']}`",
        f"- Python: `{summary['python']}`",
        f"- Matrix: `{summary['matrix']}`",
        f"- Manifest: `{summary['manifest']}`",
        "",
        "This preflight does not clone repositories, install dependencies, apply patches, or run tests. It checks whether the planned controlled-runtime experiment has the minimum local prerequisites and explicit isolation acknowledgment.",
        "",
        "## Checks",
        "",
        "| status | check | message | evidence |",
        "|---|---|---|---|",
    ]
    for check in checks:
        message = check.message.replace("|", "\\|")
        evidence = check.evidence.replace("|", "\\|")
        lines.append(f"| {check.status} | `{check.name}` | {message} | {evidence} |")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- `PASS` means the prerequisite was observed.",
            "- `WARN` means execution may be possible but the condition should be fixed or justified before evidence collection.",
            "- `FAIL` means the controlled runtime should not be executed yet.",
            "- This report is readiness evidence only; it is not solve-rate, resource-savings, or downstream-work evidence.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Preflight controlled-runtime execution prerequisites without running repository code.")
    parser.add_argument("--matrix", type=Path, default=DEFAULT_MATRIX)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--swebench-parquet", type=Path, default=DEFAULT_SWEBENCH_PARQUET)
    parser.add_argument("--run-root", type=Path, default=DEFAULT_RUN_ROOT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--lmstudio-url", default=DEFAULT_LMSTUDIO_URL)
    parser.add_argument("--lmstudio-timeout", type=float, default=5.0)
    parser.add_argument("--require-lmstudio", action="store_true", default=True)
    parser.add_argument("--no-require-lmstudio", action="store_false", dest="require_lmstudio")
    parser.add_argument("--require-docker", action="store_true", default=True)
    parser.add_argument("--no-require-docker", action="store_false", dest="require_docker")
    parser.add_argument("--require-isolation-ack", action="store_true", default=True)
    parser.add_argument("--no-require-isolation-ack", action="store_false", dest="require_isolation_ack")
    parser.add_argument("--ack-env", default="CAMC_RUNTIME_ISOLATION_ACK")
    parser.add_argument("--ack-file", type=Path, default=None)
    args = parser.parse_args()

    checks: list[CheckResult] = []
    checks.extend(check_matrix(args.matrix, args.manifest))
    checks.append(check_file(args.swebench_parquet, "swebench_verified_parquet_exists"))
    checks.append(check_writable_directory(args.run_root))
    checks.append(check_binary("docker", args.require_docker))
    checks.append(check_binary("git", True))
    checks.append(check_binary("python3", True))
    checks.append(check_lmstudio(args.lmstudio_url, args.lmstudio_timeout, args.require_lmstudio))
    checks.append(check_isolation_ack(args.require_isolation_ack, args.ack_env, args.ack_file))
    checks.append(check_sensitive_env())

    output_dir = ensure_dir(args.output_dir)
    status = overall_status(checks)
    summary = {
        "status": status,
        "platform": platform.platform(),
        "python": platform.python_version(),
        "matrix": str(args.matrix),
        "manifest": str(args.manifest),
        "swebench_parquet": str(args.swebench_parquet),
        "run_root": str(args.run_root),
        "lmstudio_url": args.lmstudio_url,
        "checks": [check.as_dict() for check in checks],
    }
    checks_frame = pd.DataFrame([check.as_dict() for check in checks])
    checks_path = output_dir / "runtime_preflight_checks.csv"
    summary_path = output_dir / "runtime_preflight_summary.json"
    report_path = output_dir / "runtime_preflight_report.md"
    checks_frame.to_csv(checks_path, index=False)
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    write_report(report_path, checks, summary)
    print(f"Controlled runtime preflight status: {status}")
    print(f"Wrote preflight report to {report_path}")
    if status == "FAIL":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
