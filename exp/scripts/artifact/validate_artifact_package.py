"""Validate the staged EMSE artifact package without running experiments."""

from __future__ import annotations

import json
import ast
import csv
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


csv.field_size_limit(sys.maxsize)

ROOT = Path(__file__).resolve().parents[3]
MANIFEST = ROOT / "paper" / "emse_artifact_package" / "ARTIFACT_MANIFEST.json"
REPORT_MD = ROOT / "paper" / "emse_artifact_package" / "artifact_validation_report.md"
REPORT_JSON = ROOT / "paper" / "emse_artifact_package" / "artifact_validation_report.json"
FIGURE_TABLE_CONTRACTS = ROOT / "paper" / "emse_artifact_package" / "FIGURE_TABLE_CONTRACTS.json"
SUBMISSION_BLOCKERS = ROOT / "paper" / "emse_springer_submission" / "SUBMISSION_BLOCKERS.md"
SPRINGER_FLAT_UPLOAD_MANIFEST = ROOT / "paper" / "emse_springer_submission" / "SPRINGER_FLAT_UPLOAD_MANIFEST.json"
COVER_LETTER = ROOT / "paper" / "emse_springer_submission" / "COVER_LETTER_DRAFT.md"
MAIN_TEX = ROOT / "paper" / "emse_springer_submission" / "emse_observational_protocol_springer.tex"
SUPPLEMENT_TEX = ROOT / "paper" / "emse_springer_submission" / "emse_online_supplement.tex"
FEATURE_TABLE = ROOT / "exp" / "results" / "emse_aidev" / "aidev_pr_level_features.csv"
DATA_DICTIONARY_CSV = ROOT / "paper" / "emse_artifact_package" / "aidev_pr_level_data_dictionary.csv"
DATA_DICTIONARY_MD = ROOT / "paper" / "emse_artifact_package" / "aidev_pr_level_data_dictionary.md"
GATE_SCRIPT = ROOT / "exp" / "scripts" / "emse_aidev" / "evaluate_workload_gate.py"
PROMPT_DRY_RUN_SUMMARY = ROOT / "exp" / "results" / "emse_runtime" / "dry_run_lmstudio_full_contract_v1" / "runtime_dry_run_summary.json"
PROMPT_DRY_RUN_CONTRACTS = ROOT / "exp" / "results" / "emse_runtime" / "dry_run_analysis_lmstudio_contract_v1" / "dry_run_policy_contract_summary.csv"
PROMPT_DRY_RUN_VALIDATION = ROOT / "exp" / "results" / "emse_runtime" / "dry_run_lmstudio_contract_validation" / "runtime_result_validation.json"
EXECUTION_PRIORITY_SUMMARY = ROOT / "exp" / "results" / "emse_runtime" / "execution_priority_v1" / "runtime_execution_priority_summary.json"
EXECUTION_PRIORITY_TASKS = ROOT / "exp" / "results" / "emse_runtime" / "execution_priority_v1" / "runtime_task_execution_priority.csv"
EXECUTION_PRIORITY_QUEUE = ROOT / "exp" / "results" / "emse_runtime" / "execution_priority_v1" / "runtime_row_execution_queue.csv"
FIRST_WAVE_SUMMARY = ROOT / "exp" / "results" / "emse_runtime" / "first_wave_execution_bundle_v1" / "first_wave_bundle_summary.json"
FIRST_WAVE_MANIFEST = ROOT / "exp" / "results" / "emse_runtime" / "first_wave_execution_bundle_v1" / "isolated_execution_manifest.csv"
FIRST_WAVE_RESULTS = ROOT / "exp" / "results" / "emse_runtime" / "first_wave_execution_bundle_v1" / "runtime_task_results_empty.csv"
FIRST_WAVE_CHECKLIST = ROOT / "exp" / "results" / "emse_runtime" / "first_wave_execution_bundle_v1" / "row_execution_checklist.csv"
FIRST_WAVE_PAIR_PLAN = ROOT / "exp" / "results" / "emse_runtime" / "first_wave_execution_bundle_v1" / "first_wave_pair_plan.csv"
FIRST_WAVE_VALIDATION = ROOT / "exp" / "results" / "emse_runtime" / "first_wave_execution_bundle_v1_validation" / "runtime_result_validation.json"
FIRST_WAVE_PACKET_SUMMARY = ROOT / "exp" / "results" / "emse_runtime" / "first_wave_execution_packets_v1" / "packet_summary.json"
FIRST_WAVE_PACKET_INDEX = ROOT / "exp" / "results" / "emse_runtime" / "first_wave_execution_packets_v1" / "packet_index.csv"
FIRST_WAVE_BATCH_STATUS = ROOT / "exp" / "results" / "emse_runtime" / "first_wave_batch_status_v1" / "runtime_batch_status_summary.json"
FIRST_WAVE_STATUS_SOURCE = ROOT / "exp" / "results" / "emse_runtime" / "first_wave_batch_status_v1" / "first_wave_status_source.json"
FIRST_WAVE_LAUNCH_SUMMARY = ROOT / "exp" / "results" / "emse_runtime" / "first_wave_launch_sheet_v1" / "first_wave_launch_summary.json"
FIRST_WAVE_LAUNCH_SHEET = ROOT / "exp" / "results" / "emse_runtime" / "first_wave_launch_sheet_v1" / "first_wave_operator_launch_sheet.csv"
PREFLIGHT_CLEARANCE_SUMMARY = ROOT / "exp" / "results" / "emse_runtime" / "preflight_clearance_handoff_v1" / "preflight_clearance_summary.json"
PREFLIGHT_CLEARANCE_CHECKLIST = ROOT / "exp" / "results" / "emse_runtime" / "preflight_clearance_handoff_v1" / "preflight_clearance_checklist.csv"
FIRST_WAVE_BRIDGE_SUMMARY = ROOT / "exp" / "results" / "emse_runtime" / "first_wave_shadow_bridge_v1" / "first_wave_shadow_bridge_summary.json"
FIRST_WAVE_BRIDGE_ROW_PLAN = ROOT / "exp" / "results" / "emse_runtime" / "first_wave_shadow_bridge_v1" / "first_wave_shadow_row_plan.csv"
FIRST_WAVE_BRIDGE_TASK_MANIFEST = ROOT / "exp" / "results" / "emse_runtime" / "first_wave_shadow_bridge_v1" / "first_wave_shadow_task_manifest.csv"
FIRST_WAVE_DOCKER_SUMMARY = ROOT / "exp" / "results" / "emse_runtime" / "first_wave_docker_isolation_plan_v1" / "first_wave_docker_isolation_summary.json"
FIRST_WAVE_DOCKER_LAUNCH = ROOT / "exp" / "results" / "emse_runtime" / "first_wave_docker_isolation_plan_v1" / "run_first_wave_bridge_in_docker.sh"
FIRST_WAVE_DOCKER_VALIDATE = ROOT / "exp" / "results" / "emse_runtime" / "first_wave_docker_isolation_plan_v1" / "validate_first_wave_docker_results.sh"
FIRST_WAVE_DOCKERFILE = ROOT / "exp" / "results" / "emse_runtime" / "first_wave_docker_isolation_plan_v1" / "Dockerfile"
FIRST_WAVE_DRILL_SUMMARY = ROOT / "exp" / "results" / "emse_runtime" / "first_wave_analysis_drill_v1" / "first_wave_analysis_drill_summary.json"
FIRST_WAVE_DRILL_RESULTS = ROOT / "exp" / "results" / "emse_runtime" / "first_wave_analysis_drill_v1" / "runtime_task_results_synthetic_completed.csv"
FIRST_WAVE_DRILL_VALIDATION = ROOT / "exp" / "results" / "emse_runtime" / "first_wave_analysis_drill_validation_v1" / "runtime_result_validation.json"
FIRST_WAVE_DRILL_PAIR_SUMMARY = ROOT / "exp" / "results" / "emse_runtime" / "first_wave_analysis_drill_pair_analysis_v1" / "runtime_noninferiority_summary.csv"
FIRST_WAVE_DRILL_PUBLICATION_SUMMARY = ROOT / "exp" / "results" / "emse_runtime" / "first_wave_analysis_drill_publication_artifacts_v1" / "runtime_publication_artifact_summary.json"


REQUIRED_DATA_DICTIONARY_COLUMNS = {
    "column",
    "group",
    "decision_time_status",
    "source_or_derivation",
    "definition",
    "unit_or_scale",
    "missing_value_rule",
    "used_in_main_gate",
    "pandas_dtype",
    "non_null_count",
    "missing_count",
    "missing_rate",
    "min",
    "max",
    "n_unique",
    "observed_values_sample",
}

REQUIRED_FIGURE_TABLE_IDS = {
    "tab:casc-mapping-new",
    "fig:runtime-gate-overview",
    "tab:related-positioning",
    "tab:dataset-profile",
    "tab:timing-boundary",
    "tab:split-profile",
    "tab:gate-spec",
    "tab:aidev-components",
    "fig:aidev-components",
    "tab:aidev-main",
    "tab:aidev-calibration",
    "fig:aidev-frontier",
    "tab:aidev-baselines",
    "tab:aidev-equal-coverage",
    "fig:aidev-baselines",
    "tab:aidev-feature-boundary",
    "tab:workload-sensitivity-main",
    "tab:aidev-subgroups",
    "tab:aidev-local-fallback",
    "tab:aidev-errors",
    "fig:aidev-errors",
    "tab:aidev-survival",
    "tab:mechanism-validation",
    "fig:synthetic-runtime",
    "fig:supp-observability",
    "fig:supp-pareto-filtering",
}

REQUIRED_CONTRACT_FIELDS = {
    "id",
    "type",
    "manuscript_location",
    "artifact_paths",
    "source_paths",
    "claim_supported",
    "unique_evidence_role",
    "statistics",
    "source_trace",
    "accessibility",
    "reviewer_risk",
}

REQUIRED_SUBMISSION_BLOCKER_TERMS = {
    "TODO-corresponding-email": "corresponding author email",
    "TODO affiliation": "affiliation",
    "TODO country": "country",
    "Funding statement": "funding statement",
    "Competing interests statement": "competing interests statement",
    "Ethics/consent declaration confirmation": "ethics/consent declaration confirmation",
    "Author contribution statement confirmation": "author contribution statement confirmation",
    "AI-use statement": "AI-use statement",
    "Public archive DOI or reviewer link": "artifact DOI or reviewer link",
    "Special issue routing": "special issue routing",
    "Cover letter finalization": "cover letter finalization",
    "Prior dissemination and overlap confirmation": "prior dissemination and overlap confirmation",
    "Originality and exclusive submission confirmation": "originality and exclusive submission confirmation",
    "Author and institutional approval confirmation": "author and institutional approval confirmation",
    "Mutable source metadata": "delayed source metadata recheck",
}

TERMINOLOGY_GUARD_FILES = [
    MAIN_TEX,
    SUPPLEMENT_TEX,
    COVER_LETTER,
    ROOT / "paper" / "emse_artifact_package" / "FIGURE_TABLE_CONTRACTS.md",
    FIGURE_TABLE_CONTRACTS,
]

DISALLOWED_READER_TERMS = [
    "calibrated workload selection",
    "calibrated selective gate",
    "calibrated evidence",
    "calibrated triage",
    "conservative workflow",
    "conservative handling",
    "control theorem",
    "controlled synthetic repository execution validation",
    "counterfactual conservative workflow",
    "broader selector",
    "coverage contraction",
    "full control model",
    "full selector",
    "held out data",
    "mechanism/control studies",
    "mechanism consistency",
    "mechanism validation",
    "legacy Pareto workflow",
    "observational selection risk metric",
    "risk budget",
    "selection mechanism",
    "selection rule",
    "selector",
    "risk/coverage",
    "scope-control table",
    "shift contraction",
    "static conservative",
    "target budget",
    "activation",
    "causal policy effect metric",
    "selective context purchase",
    "validation risk proxy",
    "workload composite",
    "workload-aware",
]

DISALLOWED_FLAT_UPLOAD_SUFFIXES = {
    ".aux",
    ".blg",
    ".fdb_latexmk",
    ".fls",
    ".log",
    ".out",
}

ALLOWED_FLAT_UPLOAD_SUFFIXES = {
    ".bib",
    ".bst",
    ".cls",
    ".pdf",
    ".tex",
}


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def add_check(checks: list[dict[str, str]], name: str, status: str, detail: str) -> None:
    checks.append({"name": name, "status": status, "detail": detail})


def flatten_manifest_paths(manifest: dict[str, Any]) -> list[str]:
    groups = manifest.get("public_package_files", {})
    paths: list[str] = []
    for value in groups.values():
        if isinstance(value, list):
            paths.extend(str(item) for item in value)
    return paths


def extract_list_constants(path: Path, names: set[str]) -> dict[str, list[str]]:
    module = ast.parse(path.read_text(encoding="utf-8"))
    values: dict[str, list[str]] = {}
    for node in module.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id in names:
                values[target.id] = list(ast.literal_eval(node.value))
    missing = names - set(values)
    if missing:
        raise ValueError(f"Could not extract constants from {path}: {', '.join(sorted(missing))}")
    return values


def csv_header(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        return next(reader)


def validate_latex_artifact(
    checks: list[dict[str, str]],
    *,
    tex: Path,
    log: Path,
    pdf: Path,
    outputs_check: str,
    log_check: str,
    artifact_label: str,
    todo_label: str,
) -> None:
    if not tex.exists() or not log.exists() or not pdf.exists():
        add_check(checks, outputs_check, "FAIL", f"{artifact_label} tex/log/pdf is incomplete.")
        return
    tex_text = tex.read_text(encoding="utf-8")
    log_text = log.read_text(encoding="utf-8")
    failures = []
    if tex_text.count("\\materialgap{"):
        failures.append("materialgap markers remain")
    if "undefined citations" in log_text.lower() or ("citation" in log_text.lower() and "undefined" in log_text.lower()):
        failures.append("undefined citations")
    if "undefined references" in log_text.lower() or ("reference" in log_text.lower() and "undefined" in log_text.lower()):
        failures.append("undefined references")
    if "LaTeX Error: File" in log_text:
        failures.append("missing file error")
    if "Rerun to get" in log_text or "may have changed" in log_text:
        failures.append("rerun warning")
    if "Overfull \\hbox" in log_text:
        failures.append("overfull boxes")
    if failures:
        add_check(checks, log_check, "FAIL", "; ".join(failures))
    else:
        todo_count = tex_text.count("TODO")
        add_check(checks, log_check, "PASS", f"Clean log; {todo_count} known {todo_label} TODO tokens remain.")


def validate_latex_log(checks: list[dict[str, str]]) -> None:
    staging = ROOT / "paper" / "emse_springer_submission"
    validate_latex_artifact(
        checks,
        tex=staging / "emse_observational_protocol_springer.tex",
        log=staging / "emse_observational_protocol_springer.log",
        pdf=staging / "emse_observational_protocol_springer.pdf",
        outputs_check="springer_latex_outputs",
        log_check="springer_latex_log",
        artifact_label="Springer main manuscript staging",
        todo_label="metadata/declaration",
    )
    validate_latex_artifact(
        checks,
        tex=staging / "emse_online_supplement.tex",
        log=staging / "emse_online_supplement.log",
        pdf=staging / "emse_online_supplement.pdf",
        outputs_check="springer_supplement_outputs",
        log_check="springer_supplement_latex_log",
        artifact_label="Springer online supplement staging",
        todo_label="metadata",
    )


def extract_main_title() -> str:
    text = MAIN_TEX.read_text(encoding="utf-8")
    match = re.search(r"\\title(?:\[[^\]]*\])?\{([^{}]+)\}", text)
    if not match:
        return ""
    return " ".join(match.group(1).split())


def validate_cover_letter_consistency(manifest: dict[str, Any], checks: list[dict[str, str]]) -> None:
    manifest_paths = set(flatten_manifest_paths(manifest))
    rel_path = COVER_LETTER.relative_to(ROOT).as_posix()
    if rel_path not in manifest_paths:
        add_check(checks, "cover_letter_consistency", "FAIL", f"{rel_path} is not listed in the artifact manifest.")
        return
    if not COVER_LETTER.exists() or not MAIN_TEX.exists():
        add_check(checks, "cover_letter_consistency", "FAIL", "Cover letter or main TeX file is missing.")
        return
    manuscript_title = extract_main_title()
    cover_text = COVER_LETTER.read_text(encoding="utf-8")
    if not manuscript_title:
        add_check(checks, "cover_letter_consistency", "FAIL", "Could not parse the manuscript title from the main TeX file.")
    elif manuscript_title not in cover_text:
        add_check(checks, "cover_letter_consistency", "FAIL", f"Cover letter does not contain the current manuscript title: {manuscript_title}")
    else:
        add_check(checks, "cover_letter_consistency", "PASS", "Cover letter contains the current manuscript title.")


def validate_terminology_guard(checks: list[dict[str, str]]) -> None:
    missing_files = [path.relative_to(ROOT).as_posix() for path in TERMINOLOGY_GUARD_FILES if not path.exists()]
    if missing_files:
        add_check(checks, "terminology_guard", "FAIL", f"Missing files for terminology guard: {', '.join(missing_files)}")
        return

    hits: list[str] = []
    for path in TERMINOLOGY_GUARD_FILES:
        text = path.read_text(encoding="utf-8").casefold()
        rel_path = path.relative_to(ROOT).as_posix()
        for term in DISALLOWED_READER_TERMS:
            if term.casefold() in text:
                hits.append(f"{rel_path}: {term}")

    if hits:
        add_check(checks, "terminology_guard", "FAIL", f"Visible old terminology remains: {'; '.join(hits[:12])}")
    else:
        add_check(
            checks,
            "terminology_guard",
            "PASS",
            f"No disallowed older terminology in {len(TERMINOLOGY_GUARD_FILES)} active visible files.",
        )


def validate_springer_source_dependencies(manifest: dict[str, Any], checks: list[dict[str, str]]) -> None:
    manifest_paths = set(flatten_manifest_paths(manifest))
    staging = ROOT / "paper" / "emse_springer_submission"
    fls_paths = [
        staging / "emse_observational_protocol_springer.fls",
        staging / "emse_online_supplement.fls",
    ]
    missing_fls = [path.relative_to(ROOT).as_posix() for path in fls_paths if not path.exists()]
    if missing_fls:
        add_check(checks, "springer_source_dependency_fls", "FAIL", f"Missing LaTeX recorder files: {', '.join(missing_fls)}")
        return

    required = {
        "paper/emse_springer_submission/emse_observational_protocol_springer.tex",
        "paper/emse_springer_submission/emse_online_supplement.tex",
        "paper/emse_springer_submission/references_emse.bib",
        "paper/emse_springer_submission/sn-jnl.cls",
        "paper/emse_springer_submission/sn-basic.bst",
    }
    suffixes = {".tex", ".pdf", ".cls", ".bib", ".bst"}
    for fls_path in fls_paths:
        for line in fls_path.read_text(encoding="utf-8").splitlines():
            if not line.startswith("INPUT "):
                continue
            raw = line.removeprefix("INPUT ").strip()
            if not raw:
                continue
            candidate = Path(raw)
            if not candidate.is_absolute():
                candidate = staging / candidate
            try:
                rel = candidate.resolve().relative_to(ROOT).as_posix()
            except ValueError:
                continue
            if candidate.suffix.lower() in suffixes:
                required.add(rel)

    missing = sorted(path for path in required if path not in manifest_paths)
    if missing:
        add_check(checks, "springer_source_dependency_manifest", "FAIL", f"{len(missing)} local source dependencies are not listed in the manifest: {', '.join(missing[:8])}")
    else:
        add_check(checks, "springer_source_dependency_manifest", "PASS", f"All {len(required)} local Springer source dependencies are listed in the manifest.")


def springer_fls_required_dependencies() -> set[str]:
    staging = ROOT / "paper" / "emse_springer_submission"
    fls_paths = [
        staging / "emse_observational_protocol_springer.fls",
        staging / "emse_online_supplement.fls",
    ]
    required = {
        "emse_observational_protocol_springer.tex",
        "emse_online_supplement.tex",
        "references_emse.bib",
        "sn-jnl.cls",
        "sn-basic.bst",
    }
    suffixes = {".tex", ".pdf", ".cls", ".bib", ".bst"}
    for fls_path in fls_paths:
        if not fls_path.exists():
            continue
        for line in fls_path.read_text(encoding="utf-8").splitlines():
            if not line.startswith("INPUT "):
                continue
            raw = line.removeprefix("INPUT ").strip()
            if not raw:
                continue
            candidate = Path(raw)
            if not candidate.is_absolute():
                candidate = staging / candidate
            try:
                rel_to_staging = candidate.resolve().relative_to(staging.resolve()).as_posix()
            except ValueError:
                continue
            if candidate.suffix.lower() in suffixes and "/" not in rel_to_staging:
                required.add(rel_to_staging)
    return required


def validate_springer_flat_upload_manifest(manifest: dict[str, Any], checks: list[dict[str, str]]) -> None:
    manifest_paths = set(flatten_manifest_paths(manifest))
    rel_path = SPRINGER_FLAT_UPLOAD_MANIFEST.relative_to(ROOT).as_posix()
    if rel_path not in manifest_paths:
        add_check(checks, "springer_flat_upload_manifest", "FAIL", f"{rel_path} is not listed in the artifact manifest.")
        return
    if not SPRINGER_FLAT_UPLOAD_MANIFEST.exists():
        add_check(checks, "springer_flat_upload_manifest", "FAIL", f"Missing flat upload manifest: {rel_path}")
        return
    try:
        upload_manifest = load_json(SPRINGER_FLAT_UPLOAD_MANIFEST)
    except json.JSONDecodeError as exc:
        add_check(checks, "springer_flat_upload_manifest", "FAIL", f"Invalid flat upload JSON: {exc}")
        return

    staging = ROOT / "paper" / "emse_springer_submission"
    files = upload_manifest.get("flat_upload_files", [])
    if not isinstance(files, list) or not files:
        add_check(checks, "springer_flat_upload_manifest", "FAIL", "flat_upload_files must be a nonempty list.")
        return

    upload_files = [str(item) for item in files]
    duplicate_files = sorted({item for item in upload_files if upload_files.count(item) > 1})
    nested_files = sorted(item for item in upload_files if "/" in item or "\\" in item)
    missing_files = sorted(item for item in upload_files if not (staging / item).exists())
    disallowed_suffixes = sorted(item for item in upload_files if Path(item).suffix.lower() in DISALLOWED_FLAT_UPLOAD_SUFFIXES)
    unsupported_suffixes = sorted(item for item in upload_files if Path(item).suffix.lower() not in ALLOWED_FLAT_UPLOAD_SUFFIXES)
    required = springer_fls_required_dependencies()
    missing_required = sorted(required - set(upload_files))

    if duplicate_files or nested_files or missing_files or disallowed_suffixes or unsupported_suffixes or missing_required:
        details = []
        if duplicate_files:
            details.append(f"duplicates: {', '.join(duplicate_files)}")
        if nested_files:
            details.append(f"nested paths: {', '.join(nested_files)}")
        if missing_files:
            details.append(f"missing files: {', '.join(missing_files[:8])}")
        if disallowed_suffixes:
            details.append(f"build products listed: {', '.join(disallowed_suffixes)}")
        if unsupported_suffixes:
            details.append(f"unsupported suffixes: {', '.join(unsupported_suffixes)}")
        if missing_required:
            details.append(f"required compile dependencies absent: {', '.join(missing_required[:8])}")
        add_check(checks, "springer_flat_upload_manifest", "FAIL", " | ".join(details))
    else:
        add_check(
            checks,
            "springer_flat_upload_manifest",
            "PASS",
            f"Flat upload manifest lists {len(upload_files)} root-level source files and covers {len(required)} LaTeX compile dependencies.",
        )


def validate_figure_table_contracts(manifest: dict[str, Any], checks: list[dict[str, str]]) -> None:
    manifest_paths = set(flatten_manifest_paths(manifest))
    if not FIGURE_TABLE_CONTRACTS.exists():
        add_check(checks, "figure_table_contracts", "FAIL", f"Missing contract ledger: {FIGURE_TABLE_CONTRACTS.relative_to(ROOT)}")
        return
    try:
        contracts = load_json(FIGURE_TABLE_CONTRACTS)
    except json.JSONDecodeError as exc:
        add_check(checks, "figure_table_contracts", "FAIL", f"Invalid contract JSON: {exc}")
        return

    items = contracts.get("items", [])
    if not isinstance(items, list):
        add_check(checks, "figure_table_contracts", "FAIL", "Contract JSON does not contain an items list.")
        return

    ids = [str(item.get("id", "")) for item in items if isinstance(item, dict)]
    observed = set(ids)
    missing_ids = sorted(REQUIRED_FIGURE_TABLE_IDS - observed)
    extra_ids = sorted(observed - REQUIRED_FIGURE_TABLE_IDS)
    duplicate_ids = sorted({item_id for item_id in ids if ids.count(item_id) > 1})
    field_failures: list[str] = []
    path_failures: list[str] = []
    manifest_failures: list[str] = []

    for item in items:
        if not isinstance(item, dict):
            field_failures.append("non-dict item")
            continue
        item_id = str(item.get("id", ""))
        missing_fields = sorted(field for field in REQUIRED_CONTRACT_FIELDS if field not in item)
        if missing_fields:
            field_failures.append(f"{item_id}: missing {', '.join(missing_fields)}")
        if item.get("type") not in {"figure", "table"}:
            field_failures.append(f"{item_id}: invalid type {item.get('type')}")
        for field in REQUIRED_CONTRACT_FIELDS - {"artifact_paths", "source_paths"}:
            if not str(item.get(field, "")).strip():
                field_failures.append(f"{item_id}: empty {field}")
        for field in ["artifact_paths", "source_paths"]:
            paths = item.get(field, [])
            if not isinstance(paths, list) or not paths:
                field_failures.append(f"{item_id}: {field} must be a nonempty list")
                continue
            for raw_path in paths:
                rel_path = str(raw_path)
                if not rel_path.strip():
                    field_failures.append(f"{item_id}: blank path in {field}")
                    continue
                if not (ROOT / rel_path).exists():
                    path_failures.append(f"{item_id}: {rel_path}")
                if rel_path not in manifest_paths:
                    manifest_failures.append(f"{item_id}: {rel_path}")

    if missing_ids or extra_ids or duplicate_ids or field_failures or path_failures or manifest_failures:
        details = []
        if missing_ids:
            details.append(f"missing ids: {', '.join(missing_ids)}")
        if extra_ids:
            details.append(f"extra ids: {', '.join(extra_ids)}")
        if duplicate_ids:
            details.append(f"duplicate ids: {', '.join(duplicate_ids)}")
        if field_failures:
            details.append(f"field failures: {'; '.join(field_failures[:5])}")
        if path_failures:
            details.append(f"missing paths: {'; '.join(path_failures[:5])}")
        if manifest_failures:
            details.append(f"paths absent from manifest: {'; '.join(manifest_failures[:5])}")
        add_check(checks, "figure_table_contracts", "FAIL", " | ".join(details))
    else:
        figure_count = sum(1 for item in items if item.get("type") == "figure")
        table_count = sum(1 for item in items if item.get("type") == "table")
        add_check(checks, "figure_table_contracts", "PASS", f"All {len(items)} figure/table contracts are complete, listed in the manifest, and path-resolvable ({figure_count} figures, {table_count} tables).")


def validate_submission_blockers(manifest: dict[str, Any], checks: list[dict[str, str]]) -> None:
    manifest_paths = set(flatten_manifest_paths(manifest))
    rel_path = SUBMISSION_BLOCKERS.relative_to(ROOT).as_posix()
    if rel_path not in manifest_paths:
        add_check(checks, "submission_blockers_tracked", "FAIL", f"{rel_path} is not listed in the manifest.")
        return
    if not SUBMISSION_BLOCKERS.exists():
        add_check(checks, "submission_blockers_tracked", "FAIL", f"Missing blocker ledger: {rel_path}")
        return

    text = SUBMISSION_BLOCKERS.read_text(encoding="utf-8")
    missing_terms = [
        label
        for term, label in REQUIRED_SUBMISSION_BLOCKER_TERMS.items()
        if term not in text
    ]
    if missing_terms:
        add_check(checks, "submission_blockers_tracked", "FAIL", f"Blocker ledger is missing tracked items: {', '.join(missing_terms)}")
        return

    staging = ROOT / "paper" / "emse_springer_submission"
    tex_todo_count = 0
    for tex_name in ["emse_observational_protocol_springer.tex", "emse_online_supplement.tex"]:
        tex_path = staging / tex_name
        if tex_path.exists():
            tex_todo_count += tex_path.read_text(encoding="utf-8").count("TODO")

    add_check(
        checks,
        "submission_blockers_tracked",
        "PASS",
        f"Known author/external submission blockers are tracked in {rel_path}; {tex_todo_count} TeX TODO tokens remain intentionally unresolved.",
    )


def validate_aidev_summary(checks: list[dict[str, str]]) -> None:
    summary_path = ROOT / "exp" / "results" / "emse_aidev" / "aidev_feature_build_summary.json"
    if not summary_path.exists():
        add_check(checks, "aidev_feature_summary", "FAIL", "Missing AIDev feature build summary.")
        return
    summary = load_json(summary_path)
    rows = summary.get("rows")
    required_tables = {
        "pull_request",
        "repository",
        "pr_reviews",
        "pr_review_comments_v2",
        "pr_comments",
        "pr_commits",
        "pr_commit_details",
        "pr_timeline",
        "related_issue",
        "pr_task_type",
    }
    available = set(summary.get("available_tables", {}))
    missing = sorted(required_tables - available)
    if rows != 33596:
        add_check(checks, "aidev_feature_rows", "FAIL", f"Expected 33596 PR rows, found {rows}.")
    else:
        add_check(checks, "aidev_feature_rows", "PASS", "AIDev feature table reports 33596 PR rows.")
    if missing:
        add_check(checks, "aidev_required_tables", "FAIL", f"Missing table summaries: {', '.join(missing)}")
    else:
        add_check(checks, "aidev_required_tables", "PASS", "Required AIDev source table families are recorded.")


def validate_data_dictionary(checks: list[dict[str, str]]) -> None:
    missing_files = [
        path.relative_to(ROOT).as_posix()
        for path in [FEATURE_TABLE, DATA_DICTIONARY_CSV, DATA_DICTIONARY_MD, GATE_SCRIPT]
        if not path.exists()
    ]
    if missing_files:
        add_check(checks, "aidev_data_dictionary_files", "FAIL", f"Missing files: {', '.join(missing_files)}")
        return
    empty_files = [
        path.relative_to(ROOT).as_posix()
        for path in [DATA_DICTIONARY_CSV, DATA_DICTIONARY_MD]
        if path.stat().st_size == 0
    ]
    if empty_files:
        add_check(checks, "aidev_data_dictionary_nonempty", "FAIL", f"Empty files: {', '.join(empty_files)}")
        return
    add_check(checks, "aidev_data_dictionary_files", "PASS", "AIDev data dictionary CSV/Markdown files are present.")

    feature_columns = csv_header(FEATURE_TABLE)
    with DATA_DICTIONARY_CSV.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    dict_columns = rows[0].keys() if rows else []
    missing_metadata = sorted(REQUIRED_DATA_DICTIONARY_COLUMNS - set(dict_columns))
    if missing_metadata:
        add_check(checks, "aidev_data_dictionary_schema", "FAIL", f"Missing metadata columns: {', '.join(missing_metadata)}")
    else:
        add_check(checks, "aidev_data_dictionary_schema", "PASS", "Data dictionary has the required metadata columns.")

    documented_columns = [row.get("column", "") for row in rows]
    if documented_columns != feature_columns:
        missing = sorted(set(feature_columns) - set(documented_columns))
        extra = sorted(set(documented_columns) - set(feature_columns))
        detail = f"Feature columns={len(feature_columns)}, dictionary rows={len(rows)}"
        if missing:
            detail += f"; missing: {', '.join(missing[:8])}"
        if extra:
            detail += f"; extra: {', '.join(extra[:8])}"
        add_check(checks, "aidev_data_dictionary_columns", "FAIL", detail)
    else:
        add_check(checks, "aidev_data_dictionary_columns", "PASS", f"Data dictionary covers all {len(feature_columns)} feature table columns in order.")

    constants = extract_list_constants(GATE_SCRIPT, {"NUMERIC_FEATURES", "CATEGORICAL_FEATURES"})
    main_gate_features = (set(constants["NUMERIC_FEATURES"]) | set(constants["CATEGORICAL_FEATURES"])) & set(feature_columns)
    marked_features = {row.get("column", "") for row in rows if row.get("used_in_main_gate") == "yes"}
    if marked_features != main_gate_features:
        missing = sorted(main_gate_features - marked_features)
        extra = sorted(marked_features - main_gate_features)
        detail = []
        if missing:
            detail.append(f"missing yes: {', '.join(missing[:8])}")
        if extra:
            detail.append(f"unexpected yes: {', '.join(extra[:8])}")
        add_check(checks, "aidev_data_dictionary_gate_features", "FAIL", "; ".join(detail))
    else:
        add_check(checks, "aidev_data_dictionary_gate_features", "PASS", f"Main gate feature flags match {len(main_gate_features)} present gate features.")

    leaked_outcomes = [
        row.get("column", "")
        for row in rows
        if row.get("column", "").startswith("outcome_")
        and (row.get("decision_time_status", "").startswith("proposal_time") or row.get("used_in_main_gate") == "yes")
    ]
    if leaked_outcomes:
        add_check(checks, "aidev_data_dictionary_outcome_boundary", "FAIL", f"Outcome fields marked as proposal/gate fields: {', '.join(leaked_outcomes[:8])}")
    else:
        add_check(checks, "aidev_data_dictionary_outcome_boundary", "PASS", "Outcome fields are not marked as proposal time gate predictors.")

    row_by_name = {row.get("column", ""): row for row in rows}
    raw_source = row_by_name.get("outcome_downstream_workload_raw", {}).get("source_or_derivation", "").lower()
    log_source = row_by_name.get("outcome_downstream_workload_log", {}).get("source_or_derivation", "").lower()
    if "sum" not in raw_source or "log1p" not in log_source:
        add_check(checks, "aidev_data_dictionary_workload_derivation", "FAIL", "Workload raw/log derivations are not documented as sum and log1p.")
    else:
        add_check(checks, "aidev_data_dictionary_workload_derivation", "PASS", "Primary workload raw/log derivations are documented.")


def validate_prompt_dry_run(checks: list[dict[str, str]]) -> None:
    missing_files = [
        path.relative_to(ROOT).as_posix()
        for path in [PROMPT_DRY_RUN_SUMMARY, PROMPT_DRY_RUN_CONTRACTS, PROMPT_DRY_RUN_VALIDATION]
        if not path.exists()
    ]
    if missing_files:
        add_check(checks, "runtime_prompt_dry_run_files", "FAIL", f"Missing files: {', '.join(missing_files)}")
        return
    summary = load_json(PROMPT_DRY_RUN_SUMMARY)
    if summary.get("rows") == 96 and summary.get("tasks") == 24 and summary.get("mode") == "lmstudio":
        safety = str(summary.get("safety", "")).lower()
        if "prompt-only" in safety and "no repository code executed" in safety:
            add_check(checks, "runtime_prompt_dry_run_scope", "PASS", "Contracted LM Studio dry run has 96 rows, 24 tasks, and prompt only safety scope.")
        else:
            add_check(checks, "runtime_prompt_dry_run_scope", "FAIL", f"Dry run safety text is unexpected: {summary.get('safety')}")
    else:
        add_check(checks, "runtime_prompt_dry_run_scope", "FAIL", f"Unexpected dry run summary rows/tasks/mode: rows={summary.get('rows')}; tasks={summary.get('tasks')}; mode={summary.get('mode')}")

    with PROMPT_DRY_RUN_CONTRACTS.open("r", encoding="utf-8", newline="") as handle:
        contract_rows = list(csv.DictReader(handle))
    required_contracts = {
        ("static_conservative", "PASS"),
        ("minimal_verify", "PASS"),
    }
    observed_contracts = {
        (row.get("controller", ""), row.get("status", ""))
        for row in contract_rows
        if row.get("run_label") == "dry_run_lmstudio_full_contract_v1"
    }
    violations = [
        row
        for row in contract_rows
        if row.get("run_label") == "dry_run_lmstudio_full_contract_v1"
        and row.get("status") == "FAIL"
    ]
    if required_contracts.issubset(observed_contracts) and not violations:
        add_check(checks, "runtime_prompt_dry_run_contracts", "PASS", "Fixed controller prompt contracts pass for static_conservative and minimal_verify.")
    else:
        add_check(checks, "runtime_prompt_dry_run_contracts", "FAIL", f"Prompt contract failures or missing passes: {violations[:4]}")

    validation = load_json(PROMPT_DRY_RUN_VALIDATION)
    issue_codes = {str(issue.get("code", "")) for issue in validation.get("issues", [])}
    if validation.get("status") == "FAIL" and {"prompt_only_rows", "empty_primary_metric"}.issubset(issue_codes):
        add_check(checks, "runtime_prompt_dry_run_negative_validation", "PASS", "Prompt only contract template is rejected as non evidence by runtime validator.")
    else:
        add_check(checks, "runtime_prompt_dry_run_negative_validation", "FAIL", f"Unexpected prompt template validation status/issues: {validation.get('status')}; {sorted(issue_codes)}")


def validate_execution_priority(checks: list[dict[str, str]]) -> None:
    missing_files = [
        path.relative_to(ROOT).as_posix()
        for path in [EXECUTION_PRIORITY_SUMMARY, EXECUTION_PRIORITY_TASKS, EXECUTION_PRIORITY_QUEUE]
        if not path.exists()
    ]
    if missing_files:
        add_check(checks, "runtime_execution_priority_files", "FAIL", f"Missing files: {', '.join(missing_files)}")
        return
    summary = load_json(EXECUTION_PRIORITY_SUMMARY)
    if summary.get("tasks_ranked") == 24 and summary.get("first_wave_tasks") == 12 and summary.get("first_wave_rows") == 48:
        add_check(checks, "runtime_execution_priority_scope", "PASS", "Execution priority ranks 24 tasks and marks 12 tasks / 48 rows as first wave.")
    else:
        add_check(
            checks,
            "runtime_execution_priority_scope",
            "FAIL",
            f"Unexpected priority scope: tasks={summary.get('tasks_ranked')}; first_wave_tasks={summary.get('first_wave_tasks')}; first_wave_rows={summary.get('first_wave_rows')}",
        )

    with EXECUTION_PRIORITY_TASKS.open("r", encoding="utf-8", newline="") as handle:
        task_rows = list(csv.DictReader(handle))
    first_wave_classes = {
        row.get("primary_decision_class", "")
        for row in task_rows
        if row.get("execution_wave") == "first_wave"
    }
    if {"target_adapt_reference_inherit", "target_inherit_reference_adapt", "both_primary_inherit"}.issubset(first_wave_classes):
        add_check(checks, "runtime_execution_priority_first_wave_mix", "PASS", "First wave includes target/reference contrast tasks plus both inherit controls.")
    else:
        add_check(checks, "runtime_execution_priority_first_wave_mix", "FAIL", f"First wave decision classes are incomplete: {sorted(first_wave_classes)}")

    with EXECUTION_PRIORITY_QUEUE.open("r", encoding="utf-8", newline="") as handle:
        queue_rows = list(csv.DictReader(handle))
    first_wave_queue = [row for row in queue_rows if row.get("execution_wave") == "first_wave"]
    non_not_run = [row for row in queue_rows if row.get("execute_status") != "not_run"]
    missing_packets = [
        row.get("packet_markdown", "")
        for row in first_wave_queue
        if row.get("packet_markdown") and not (ROOT / row["packet_markdown"]).exists()
    ]
    if len(queue_rows) == 96 and len(first_wave_queue) == 48 and not non_not_run and not missing_packets:
        add_check(checks, "runtime_execution_priority_queue", "PASS", "Execution queue has 96 not run rows, 48 first wave rows, and first wave packet links exist.")
    else:
        detail = f"queue_rows={len(queue_rows)}; first_wave_rows={len(first_wave_queue)}; non_not_run={len(non_not_run)}; missing_packets={len(missing_packets)}"
        add_check(checks, "runtime_execution_priority_queue", "FAIL", detail)


def validate_runtime_boundary(checks: list[dict[str, str]]) -> None:
    batch_path = ROOT / "exp" / "results" / "emse_runtime" / "batch_status_v1" / "runtime_batch_status_summary.json"
    strategy_path = ROOT / "exp" / "results" / "emse_runtime" / "evidence_strategy_v1" / "runtime_evidence_strategy_summary.json"
    if not batch_path.exists() or not strategy_path.exists():
        add_check(checks, "runtime_status_files", "FAIL", "Missing runtime batch or evidence strategy summary.")
        return
    batch = load_json(batch_path)
    overview = batch.get("overview", {})
    completed = overview.get("completed_result_rows")
    performed = overview.get("third_party_execution_performed_by_this_report")
    packets = batch.get("packet_summary", {})
    if completed != 0:
        add_check(checks, "runtime_completed_rows_boundary", "FAIL", f"Expected 0 completed rows for protocol only package; found {completed}.")
    else:
        add_check(checks, "runtime_completed_rows_boundary", "PASS", "Runtime batch status reports 0 completed rows.")
    if performed is not False:
        add_check(checks, "runtime_no_execution_boundary", "FAIL", "Batch report does not preserve the boundary for no execution.")
    else:
        add_check(checks, "runtime_no_execution_boundary", "PASS", "Batch report states no third party execution was performed by the report.")
    if packets.get("missing_packet_file_count") != 0:
        add_check(checks, "runtime_packet_integrity", "FAIL", f"Missing packet files: {packets.get('missing_packet_file_count')}")
    else:
        add_check(checks, "runtime_packet_integrity", "PASS", "Runtime packet index reports no missing packet files.")
    strategy = load_json(strategy_path)
    if strategy.get("material_gap_count") == 5:
        add_check(checks, "runtime_evidence_strategy_boundary", "PASS", "Evidence strategy still flags 5 runtime material gaps for the strong manuscript.")
    else:
        add_check(checks, "runtime_evidence_strategy_boundary", "WARN", f"Unexpected material_gap_count={strategy.get('material_gap_count')}; re-audit manuscript scope.")


def validate_first_wave_bundle(checks: list[dict[str, str]]) -> None:
    required_paths = [
        FIRST_WAVE_SUMMARY,
        FIRST_WAVE_MANIFEST,
        FIRST_WAVE_RESULTS,
        FIRST_WAVE_CHECKLIST,
        FIRST_WAVE_PAIR_PLAN,
        FIRST_WAVE_VALIDATION,
        FIRST_WAVE_PACKET_SUMMARY,
        FIRST_WAVE_PACKET_INDEX,
        FIRST_WAVE_BATCH_STATUS,
    ]
    missing_files = [path.relative_to(ROOT).as_posix() for path in required_paths if not path.exists()]
    if missing_files:
        add_check(checks, "runtime_first_wave_bundle_files", "FAIL", f"Missing files: {', '.join(missing_files)}")
        return

    summary = load_json(FIRST_WAVE_SUMMARY)
    expected_counts = {
        "selected_rows": 48,
        "selected_tasks": 12,
        "pair_plan_rows": 12,
        "not_run_result_rows": 48,
        "checklist_rows": 48,
        "missing_pair_packet_tasks": 0,
    }
    count_failures = [
        f"{key}={summary.get(key)}"
        for key, expected in expected_counts.items()
        if summary.get(key) != expected
    ]
    if (
        summary.get("third_party_execution_performed") is False
        and summary.get("evidence_status") == "not_run"
        and not count_failures
    ):
        add_check(checks, "runtime_first_wave_bundle_scope", "PASS", "First wave bundle has 12 tasks / 48 not run rows, complete pair packets, and no execution evidence.")
    else:
        detail = "; ".join(count_failures) or "unexpected evidence boundary"
        detail += f"; third_party_execution_performed={summary.get('third_party_execution_performed')}; evidence_status={summary.get('evidence_status')}"
        add_check(checks, "runtime_first_wave_bundle_scope", "FAIL", detail)

    with FIRST_WAVE_MANIFEST.open("r", encoding="utf-8", newline="") as handle:
        manifest_rows = list(csv.DictReader(handle))
    with FIRST_WAVE_RESULTS.open("r", encoding="utf-8", newline="") as handle:
        result_rows = list(csv.DictReader(handle))
    with FIRST_WAVE_CHECKLIST.open("r", encoding="utf-8", newline="") as handle:
        checklist_rows = list(csv.DictReader(handle))
    with FIRST_WAVE_PAIR_PLAN.open("r", encoding="utf-8", newline="") as handle:
        pair_rows = list(csv.DictReader(handle))

    controllers = {row.get("controller", "") for row in manifest_rows}
    statuses = {row.get("execute_status", "") for row in result_rows}
    pair_complete = all(
        row.get("sempc_lite_present") == "True"
        and row.get("rsrc_guarded_present") == "True"
        and row.get("sempc_lite_packet_exists") == "True"
        and row.get("rsrc_guarded_packet_exists") == "True"
        for row in pair_rows
    )
    if (
        len(manifest_rows) == 48
        and len(result_rows) == 48
        and len(checklist_rows) == 48
        and len(pair_rows) == 12
        and statuses == {"not_run"}
        and controllers == {"minimal_verify", "rsrc_guarded", "sempc_lite", "static_conservative"}
        and pair_complete
    ):
        add_check(checks, "runtime_first_wave_bundle_tables", "PASS", "First wave manifest, results, checklist, and pair plan tables are internally consistent and remain not run.")
    else:
        detail = (
            f"manifest={len(manifest_rows)}; results={len(result_rows)}; checklist={len(checklist_rows)}; "
            f"pairs={len(pair_rows)}; statuses={sorted(statuses)}; controllers={sorted(controllers)}; pair_complete={pair_complete}"
        )
        add_check(checks, "runtime_first_wave_bundle_tables", "FAIL", detail)

    validation = load_json(FIRST_WAVE_VALIDATION)
    issue_codes = {str(issue.get("code", "")) for issue in validation.get("issues", [])}
    if (
        validation.get("status") == "FAIL"
        and validation.get("rows") == 48
        and validation.get("selected_rows") == 24
        and validation.get("paired_instances") == 12
        and {"incomplete_execute_status", "empty_primary_metric"}.issubset(issue_codes)
    ):
        add_check(checks, "runtime_first_wave_negative_validation", "PASS", "First wave empty result template is rejected as incomplete non evidence.")
    else:
        detail = (
            f"status={validation.get('status')}; rows={validation.get('rows')}; "
            f"selected_rows={validation.get('selected_rows')}; paired_instances={validation.get('paired_instances')}; "
            f"issues={sorted(issue_codes)}"
        )
        add_check(checks, "runtime_first_wave_negative_validation", "FAIL", detail)

    packet_summary = load_json(FIRST_WAVE_PACKET_SUMMARY)
    with FIRST_WAVE_PACKET_INDEX.open("r", encoding="utf-8", newline="") as handle:
        packet_rows = list(csv.DictReader(handle))
    missing_packet_files = []
    for row in packet_rows:
        for col in ["packet_md", "packet_json"]:
            path = row.get(col, "")
            if not path or not (ROOT / path).exists():
                missing_packet_files.append(path)
    if (
        packet_summary.get("packet_rows") == 48
        and packet_summary.get("packet_tasks") == 12
        and packet_summary.get("third_party_execution_performed") is False
        and packet_summary.get("source_dry_run_plans") == "exp/results/emse_runtime/dry_run_lmstudio_full_contract_v1/runtime_dry_run_plans.csv"
        and len(packet_rows) == 48
        and not missing_packet_files
    ):
        add_check(checks, "runtime_first_wave_packet_integrity", "PASS", "First wave packet set has 48 LM contract packet rows and all packet files exist.")
    else:
        detail = (
            f"summary_rows={packet_summary.get('packet_rows')}; summary_tasks={packet_summary.get('packet_tasks')}; "
            f"index_rows={len(packet_rows)}; missing_packet_files={len(missing_packet_files)}; "
            f"source_dry_run_plans={packet_summary.get('source_dry_run_plans')}; "
            f"third_party_execution_performed={packet_summary.get('third_party_execution_performed')}"
        )
        add_check(checks, "runtime_first_wave_packet_integrity", "FAIL", detail)

    batch_status = load_json(FIRST_WAVE_BATCH_STATUS)
    status_source = load_json(FIRST_WAVE_STATUS_SOURCE) if FIRST_WAVE_STATUS_SOURCE.exists() else {}
    overview = batch_status.get("overview", {})
    packet_status = batch_status.get("packet_summary", {})
    source_selection = batch_status.get("source_selection", status_source)
    selected_kind = source_selection.get("selected_results_kind", "unknown")
    recorded_exists = bool(source_selection.get("recorded_results_exists", False))
    completed_rows = overview.get("completed_result_rows")
    metric_complete_rows = overview.get("primary_metric_complete_rows")
    expected_empty = selected_kind in {"empty_template", "unknown"} and not recorded_exists
    completed_status_ok = completed_rows == 0 and metric_complete_rows == 0 if expected_empty else (
        isinstance(completed_rows, int)
        and isinstance(metric_complete_rows, int)
        and 0 <= metric_complete_rows <= completed_rows <= overview.get("result_rows", -1)
    )
    if (
        overview.get("matrix_rows") == 48
        and overview.get("matrix_tasks") == 12
        and overview.get("result_rows") == 48
        and completed_status_ok
        and overview.get("third_party_execution_performed_by_this_report") is False
        and packet_status.get("packet_index_rows") == 48
        and packet_status.get("missing_packet_file_count") == 0
        and source_selection.get("third_party_execution_performed_by_this_script", False) is False
    ):
        if expected_empty:
            detail = "First wave status report tracks 48 planned rows, 0 completed rows, and complete packet integrity."
        else:
            detail = (
                "First wave status report tracks recorded progress with complete packet integrity "
                f"(completed={completed_rows}; metric_complete={metric_complete_rows}; source={selected_kind})."
            )
        add_check(checks, "runtime_first_wave_batch_status", "PASS", detail)
    else:
        detail = (
            f"matrix_rows={overview.get('matrix_rows')}; matrix_tasks={overview.get('matrix_tasks')}; "
            f"result_rows={overview.get('result_rows')}; completed={overview.get('completed_result_rows')}; "
            f"metric_complete={overview.get('primary_metric_complete_rows')}; "
            f"packet_index_rows={packet_status.get('packet_index_rows')}; missing_packet_file_count={packet_status.get('missing_packet_file_count')}; "
            f"selected_results_kind={selected_kind}; recorded_results_exists={recorded_exists}"
        )
        add_check(checks, "runtime_first_wave_batch_status", "FAIL", detail)


def validate_first_wave_launch_sheet(checks: list[dict[str, str]]) -> None:
    if not FIRST_WAVE_LAUNCH_SUMMARY.exists() or not FIRST_WAVE_LAUNCH_SHEET.exists():
        add_check(checks, "runtime_first_wave_launch_sheet", "FAIL", "Missing first wave launch sheet outputs.")
        return
    summary = load_json(FIRST_WAVE_LAUNCH_SUMMARY)
    with FIRST_WAVE_LAUNCH_SHEET.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    required_cols = {
        "launch_order",
        "result_row_id",
        "repo",
        "instance_id",
        "controller",
        "ready_to_execute",
        "blockers",
        "recording_checklist_complete",
        "recording_checklist_missing",
        "record_completed_command_template",
    }
    missing_cols = required_cols - set(rows[0].keys() if rows else [])
    ready_values = [str(row.get("ready_to_execute", "")).lower() == "true" for row in rows]
    completed_templates = [row.get("record_completed_command_template", "") for row in rows]
    if (
        summary.get("rows") == 48
        and summary.get("tasks") == 12
        and summary.get("repositories") == 8
        and summary.get("ready_rows") == 0
        and summary.get("blocked_rows") == 48
        and summary.get("preflight_status") == "FAIL"
        and summary.get("third_party_execution_performed_by_this_script") is False
        and len(rows) == 48
        and not missing_cols
        and not any(ready_values)
        and all("record_isolated_runtime_result" in command for command in completed_templates)
    ):
        add_check(checks, "runtime_first_wave_launch_sheet", "PASS", "First wave launch sheet tracks 48 blocked rows and records command templates without execution.")
    else:
        detail = (
            f"summary_rows={summary.get('rows')}; csv_rows={len(rows)}; tasks={summary.get('tasks')}; "
            f"ready={summary.get('ready_rows')}; blocked={summary.get('blocked_rows')}; "
            f"preflight={summary.get('preflight_status')}; missing_cols={sorted(missing_cols)}; "
            f"third_party_execution={summary.get('third_party_execution_performed_by_this_script')}"
        )
        add_check(checks, "runtime_first_wave_launch_sheet", "FAIL", detail)


def validate_preflight_clearance_handoff(checks: list[dict[str, str]]) -> None:
    if not PREFLIGHT_CLEARANCE_SUMMARY.exists() or not PREFLIGHT_CLEARANCE_CHECKLIST.exists():
        add_check(checks, "runtime_preflight_clearance_handoff", "FAIL", "Missing preflight clearance handoff outputs.")
        return
    summary = load_json(PREFLIGHT_CLEARANCE_SUMMARY)
    with PREFLIGHT_CLEARANCE_CHECKLIST.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    check_names = {row.get("check", "") for row in rows}
    command = summary.get("isolated_preflight_command", "")
    launch_command = summary.get("isolated_launch_sheet_command", "")
    if (
        summary.get("current_preflight_status") == "FAIL"
        and summary.get("current_fail_checks") == ["isolation_ack"]
        and "sensitive_environment" in summary.get("current_warn_checks", [])
        and summary.get("current_launch_ready_rows") == 0
        and summary.get("current_launch_blocked_rows") == 48
        and summary.get("third_party_execution_performed_by_this_script") is False
        and {"isolation_ack", "sensitive_environment", "lmstudio_models"}.issubset(check_names)
        and "CAMC_RUNTIME_ISOLATION_ACK=1" in command
        and "env -u SSH_AUTH_SOCK" in command
        and "preflight_isolated_v1" in command
        and "prepare_first_wave_launch_sheet" in launch_command
    ):
        add_check(checks, "runtime_preflight_clearance_handoff", "PASS", "Preflight clearance handoff preserves current FAIL state and provides isolated shell command templates only.")
    else:
        detail = (
            f"status={summary.get('current_preflight_status')}; fail_checks={summary.get('current_fail_checks')}; "
            f"warn_checks={summary.get('current_warn_checks')}; ready={summary.get('current_launch_ready_rows')}; "
            f"blocked={summary.get('current_launch_blocked_rows')}; checks={sorted(check_names)}; "
            f"third_party_execution={summary.get('third_party_execution_performed_by_this_script')}"
        )
        add_check(checks, "runtime_preflight_clearance_handoff", "FAIL", detail)


def validate_first_wave_shadow_bridge(checks: list[dict[str, str]]) -> None:
    required = [FIRST_WAVE_BRIDGE_SUMMARY, FIRST_WAVE_BRIDGE_ROW_PLAN, FIRST_WAVE_BRIDGE_TASK_MANIFEST]
    missing = [path.relative_to(ROOT).as_posix() for path in required if not path.exists()]
    if missing:
        add_check(checks, "runtime_first_wave_shadow_bridge", "FAIL", f"Missing bridge files: {', '.join(missing)}")
        return

    summary = load_json(FIRST_WAVE_BRIDGE_SUMMARY)
    with FIRST_WAVE_BRIDGE_ROW_PLAN.open("r", encoding="utf-8", newline="") as handle:
        row_plan = list(csv.DictReader(handle))
    with FIRST_WAVE_BRIDGE_TASK_MANIFEST.open("r", encoding="utf-8", newline="") as handle:
        task_rows = list(csv.DictReader(handle))
    controllers = {row.get("controller", "") for row in row_plan}
    instances = {row.get("instance_id", "") for row in row_plan}
    task_instances = {row.get("instance_id", "") for row in task_rows}
    command = [str(item) for item in summary.get("command", [])]
    command_text = " ".join(command)
    if (
        summary.get("status") == "plan_only"
        and summary.get("selected_rows") == 48
        and summary.get("selected_tasks") == 12
        and summary.get("repositories") == 8
        and summary.get("live_repo") is False
        and summary.get("allow_clone") is False
        and not summary.get("converted_results")
        and len(row_plan) == 48
        and len(task_rows) == 12
        and len(instances) == 12
        and task_instances == instances
        and controllers == {"minimal_verify", "rsrc_guarded", "sempc_lite", "static_conservative"}
        and "shadow_runtime_experiment.py" in command_text
        and "--live-repo" not in command
        and "--allow-clone" not in command
    ):
        add_check(checks, "runtime_first_wave_shadow_bridge", "PASS", "First wave bridge is plan only for 12 tasks / 48 rows and performs no repository execution.")
    else:
        detail = (
            f"status={summary.get('status')}; rows={summary.get('selected_rows')}/{len(row_plan)}; "
            f"tasks={summary.get('selected_tasks')}/{len(task_rows)}; repos={summary.get('repositories')}; "
            f"live_repo={summary.get('live_repo')}; allow_clone={summary.get('allow_clone')}; "
            f"converted_results={summary.get('converted_results')}; controllers={sorted(controllers)}"
        )
        add_check(checks, "runtime_first_wave_shadow_bridge", "FAIL", detail)


def validate_first_wave_docker_isolation(checks: list[dict[str, str]]) -> None:
    required = [FIRST_WAVE_DOCKER_SUMMARY, FIRST_WAVE_DOCKER_LAUNCH, FIRST_WAVE_DOCKER_VALIDATE, FIRST_WAVE_DOCKERFILE]
    missing = [path.relative_to(ROOT).as_posix() for path in required if not path.exists()]
    if missing:
        add_check(checks, "runtime_first_wave_docker_isolation", "FAIL", f"Missing Docker isolation files: {', '.join(missing)}")
        return

    summary = load_json(FIRST_WAVE_DOCKER_SUMMARY)
    launch_text = FIRST_WAVE_DOCKER_LAUNCH.read_text(encoding="utf-8")
    validate_text = FIRST_WAVE_DOCKER_VALIDATE.read_text(encoding="utf-8")
    dockerfile_text = FIRST_WAVE_DOCKERFILE.read_text(encoding="utf-8")
    controllers = set(summary.get("controllers", []))
    guard_tokens = [
        "CAMC_DOCKER_RUNTIME_ACK",
        "CAMC_LIMIT_TASKS",
        "SSH_AUTH_SOCK",
        "_TOKEN=",
        "CAMC_RUNTIME_ISOLATION_ACK=1",
        ":/work:ro",
        ":/work/exp/results/emse_runtime/first_wave_docker_runtime_v1:rw",
    ]
    if (
        summary.get("status") == "plan_only"
        and summary.get("selected_rows") == 48
        and summary.get("selected_tasks") == 12
        and summary.get("repositories") == 8
        and summary.get("third_party_execution_performed") is False
        and summary.get("docker_build_performed") is False
        and summary.get("docker_run_performed") is False
        and summary.get("root_mount") == "read_only"
        and summary.get("runtime_output_mount") == "read_write"
        and summary.get("sensitive_env_guard") is True
        and controllers == {"minimal_verify", "rsrc_guarded", "sempc_lite", "static_conservative"}
        and all(token in launch_text for token in guard_tokens)
        and "run_first_wave_shadow_bridge" in launch_text
        and "--execute" in launch_text
        and "--live-repo" in launch_text
        and "validate_runtime_results" in validate_text
        and "analyze_runtime_pairs" in validate_text
        and "make_runtime_publication_artifacts" in validate_text
        and "python:3.11-slim" in dockerfile_text
        and "pip install pandas numpy pyarrow" in dockerfile_text
    ):
        add_check(checks, "runtime_first_wave_docker_isolation", "PASS", "Docker isolation plan is plan only, guarded, and scoped to the 12 task / 48 row first wave.")
    else:
        detail = (
            f"status={summary.get('status')}; rows={summary.get('selected_rows')}; tasks={summary.get('selected_tasks')}; "
            f"repos={summary.get('repositories')}; third_party={summary.get('third_party_execution_performed')}; "
            f"docker_build={summary.get('docker_build_performed')}; docker_run={summary.get('docker_run_performed')}; "
            f"root_mount={summary.get('root_mount')}; output_mount={summary.get('runtime_output_mount')}; "
            f"controllers={sorted(controllers)}"
        )
        add_check(checks, "runtime_first_wave_docker_isolation", "FAIL", detail)


def validate_recorder_accumulation(checks: list[dict[str, str]]) -> None:
    if not FIRST_WAVE_MANIFEST.exists():
        add_check(checks, "runtime_recorder_accumulation", "FAIL", "Missing first wave manifest for recorder accumulation check.")
        return
    try:
        with tempfile.TemporaryDirectory(prefix="camc_recorder_check_") as tmp:
            bundle = Path(tmp) / "bundle"
            shutil.copytree(FIRST_WAVE_MANIFEST.parent, bundle)
            recorded = bundle / "runtime_task_results_recorded.csv"
            if recorded.exists():
                recorded.unlink()
            with (bundle / "isolated_execution_manifest.csv").open("r", encoding="utf-8", newline="") as handle:
                rows = [
                    row
                    for row in csv.DictReader(handle)
                    if row.get("controller") in {"sempc_lite", "rsrc_guarded"}
                ][:2]
            if len(rows) != 2:
                add_check(checks, "runtime_recorder_accumulation", "FAIL", f"Expected two first wave primary rows, found {len(rows)}.")
                return
            for idx, row in enumerate(rows, start=1):
                cmd = [
                    sys.executable,
                    "-m",
                    "exp.scripts.emse_runtime.record_isolated_runtime_result",
                    "--bundle-dir",
                    str(bundle),
                    "--result-row-id",
                    row["result_row_id"],
                    "--run-id",
                    "artifact_recorder_accumulation_check",
                    "--execute-status",
                    "completed",
                    "--ack-isolated",
                    "--evidence-note",
                    "synthetic artifact package recorder accumulation check; no repository code executed",
                    "--success",
                    str(idx % 2),
                    "--search-count",
                    str(idx),
                    "--read-count",
                    str(idx + 1),
                    "--test-runs",
                    str(idx + 2),
                    "--patch-attempts",
                    str(idx + 3),
                    "--preflight-passed",
                    "--sensitive-env-removed",
                    "--repo-snapshot-prepared",
                    "--dependencies-reviewed",
                    "--target-tests-run",
                    "--checklist-note",
                    f"synthetic recorder accumulation checklist row {idx}",
                ]
                subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=True)
            with recorded.open("r", encoding="utf-8", newline="") as handle:
                result_rows = list(csv.DictReader(handle))
            completed = [
                row
                for row in result_rows
                if row.get("execute_status", "").lower() in {"complete", "completed", "done", "succeeded", "success", "ran", "executed"}
            ]
            if len(completed) != 2:
                add_check(checks, "runtime_recorder_accumulation", "FAIL", f"Expected 2 accumulated completed rows, found {len(completed)}.")
                return
            by_row = {f"{row['instance_id']}::{row['controller']}": row for row in completed}
            missing = [row["result_row_id"] for row in rows if row["result_row_id"] not in by_row]
            if missing:
                add_check(checks, "runtime_recorder_accumulation", "FAIL", f"Recorded table lost rows: {', '.join(missing)}")
                return
            with (bundle / "row_execution_checklist.csv").open("r", encoding="utf-8", newline="") as handle:
                checklist_rows = list(csv.DictReader(handle))
            checklist_by_row = {row["result_row_id"]: row for row in checklist_rows}
            required_true = [
                "preflight_passed",
                "isolation_ack_present",
                "sensitive_env_removed",
                "repo_snapshot_prepared",
                "dependencies_reviewed",
                "target_tests_run",
                "observed_metrics_recorded",
            ]
            checklist_failures = []
            for source_row in rows:
                item = checklist_by_row.get(source_row["result_row_id"], {})
                for col in required_true:
                    if str(item.get(col, "")).lower() != "true":
                        checklist_failures.append(f"{source_row['result_row_id']}:{col}")
                if str(item.get("dependencies_installed", "")).lower() == "true":
                    checklist_failures.append(f"{source_row['result_row_id']}:dependencies_installed unexpectedly true")
                if "synthetic recorder accumulation checklist row" not in str(item.get("notes", "")):
                    checklist_failures.append(f"{source_row['result_row_id']}:missing checklist note")
            if checklist_failures:
                add_check(checks, "runtime_recorder_accumulation", "FAIL", f"Checklist update failures: {', '.join(checklist_failures[:6])}")
                return
            add_check(checks, "runtime_recorder_accumulation", "PASS", "Recorder preserves prior completed rows and writes explicit checklist evidence for sequential first wave records.")
    except Exception as exc:
        add_check(checks, "runtime_recorder_accumulation", "FAIL", f"Recorder accumulation check failed: {exc}")


def validate_first_wave_analysis_drill(checks: list[dict[str, str]]) -> None:
    required_paths = [
        FIRST_WAVE_DRILL_SUMMARY,
        FIRST_WAVE_DRILL_RESULTS,
        FIRST_WAVE_DRILL_VALIDATION,
        FIRST_WAVE_DRILL_PAIR_SUMMARY,
        FIRST_WAVE_DRILL_PUBLICATION_SUMMARY,
    ]
    missing_files = [path.relative_to(ROOT).as_posix() for path in required_paths if not path.exists()]
    if missing_files:
        add_check(checks, "runtime_first_wave_analysis_drill_files", "FAIL", f"Missing files: {', '.join(missing_files)}")
        return

    summary = load_json(FIRST_WAVE_DRILL_SUMMARY)
    validation = load_json(FIRST_WAVE_DRILL_VALIDATION)
    publication = load_json(FIRST_WAVE_DRILL_PUBLICATION_SUMMARY)
    with FIRST_WAVE_DRILL_RESULTS.open("r", encoding="utf-8", newline="") as handle:
        result_rows = list(csv.DictReader(handle))
    completed = [row for row in result_rows if row.get("execute_status", "").lower() in {"completed", "complete", "done", "succeeded", "success", "ran", "executed"}]
    modes = {row.get("execution_mode", "") for row in completed}
    if (
        summary.get("evidence_status") == "synthetic_drill_not_publication_evidence"
        and summary.get("third_party_execution_performed") is False
        and summary.get("lmstudio_called") is False
        and summary.get("result_rows") == 48
        and summary.get("synthetic_completed_rows") == 24
        and summary.get("primary_pair_rows") == 24
        and summary.get("paired_instances") == 12
        and len(result_rows) == 48
        and len(completed) == 24
        and modes == {"synthetic_evidence_drill"}
    ):
        add_check(checks, "runtime_first_wave_analysis_drill_scope", "PASS", "Synthetic drill has 24 completed looking primary rows and is explicitly marked non evidence.")
    else:
        detail = (
            f"evidence_status={summary.get('evidence_status')}; third_party_execution_performed={summary.get('third_party_execution_performed')}; "
            f"lmstudio_called={summary.get('lmstudio_called')}; result_rows={summary.get('result_rows')}; "
            f"synthetic_completed_rows={summary.get('synthetic_completed_rows')}; completed={len(completed)}; modes={sorted(modes)}"
        )
        add_check(checks, "runtime_first_wave_analysis_drill_scope", "FAIL", detail)

    if validation.get("status") == "PASS" and validation.get("selected_rows") == 24 and validation.get("paired_instances") == 12:
        add_check(checks, "runtime_first_wave_analysis_drill_validation", "PASS", "Synthetic drill passes runtime result validation for the primary pair.")
    else:
        detail = f"status={validation.get('status')}; selected_rows={validation.get('selected_rows')}; paired_instances={validation.get('paired_instances')}"
        add_check(checks, "runtime_first_wave_analysis_drill_validation", "FAIL", detail)

    with FIRST_WAVE_DRILL_PAIR_SUMMARY.open("r", encoding="utf-8", newline="") as handle:
        pair_rows = list(csv.DictReader(handle))
    pair = pair_rows[0] if pair_rows else {}
    publication_ready = str(pair.get("publication_ready_success_claim", "")).lower() == "true"
    n_pairs = int(float(pair.get("n_pairs", 0) or 0))
    if n_pairs == 12 and not publication_ready:
        add_check(checks, "runtime_first_wave_analysis_drill_pair_gate", "PASS", "Synthetic pair analysis runs but remains below publication ready guardrail.")
    else:
        add_check(checks, "runtime_first_wave_analysis_drill_pair_gate", "FAIL", f"n_pairs={n_pairs}; publication_ready_success_claim={pair.get('publication_ready_success_claim')}")

    if (
        publication.get("evidence_status") == "synthetic_drill_not_publication_evidence"
        and publication.get("artifact_status") == "synthetic drill: not publication evidence"
        and publication.get("publication_ready_success_claim") is False
        and publication.get("third_party_execution_performed") is False
    ):
        add_check(checks, "runtime_first_wave_analysis_drill_publication_boundary", "PASS", "Synthetic publication artifacts are explicitly marked as non evidence.")
    else:
        detail = (
            f"evidence_status={publication.get('evidence_status')}; artifact_status={publication.get('artifact_status')}; "
            f"publication_ready_success_claim={publication.get('publication_ready_success_claim')}; "
            f"third_party_execution_performed={publication.get('third_party_execution_performed')}"
        )
        add_check(checks, "runtime_first_wave_analysis_drill_publication_boundary", "FAIL", detail)


def validate_manifest_paths(manifest: dict[str, Any], checks: list[dict[str, str]]) -> None:
    paths = flatten_manifest_paths(manifest)
    missing = [path for path in paths if not (ROOT / path).exists()]
    empty = [path for path in paths if (ROOT / path).exists() and (ROOT / path).is_file() and (ROOT / path).stat().st_size == 0]
    raw_listed = [path for path in paths if path.startswith("exp/Dataset/")]
    if missing:
        add_check(checks, "manifest_paths_exist", "FAIL", f"{len(missing)} missing paths: {', '.join(missing[:8])}")
    else:
        add_check(checks, "manifest_paths_exist", "PASS", f"All {len(paths)} manifest package paths exist.")
    if empty:
        add_check(checks, "manifest_paths_nonempty", "FAIL", f"{len(empty)} zero byte files: {', '.join(empty[:8])}")
    else:
        add_check(checks, "manifest_paths_nonempty", "PASS", "All manifest package files are non empty.")
    if raw_listed:
        add_check(checks, "raw_third_party_data_not_packaged", "FAIL", f"Manifest lists raw third party dataset paths as package files: {', '.join(raw_listed)}")
    else:
        add_check(checks, "raw_third_party_data_not_packaged", "PASS", "Manifest does not list exp/Dataset raw data as public package files.")


def write_reports(checks: list[dict[str, str]]) -> int:
    fail_count = sum(1 for check in checks if check["status"] == "FAIL")
    warn_count = sum(1 for check in checks if check["status"] == "WARN")
    status = "PASS" if fail_count == 0 else "FAIL"
    payload = {"overall_status": status, "fail_count": fail_count, "warn_count": warn_count, "checks": checks}
    REPORT_JSON.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = [
        "# EMSE Artifact Package Validation Report",
        "",
        f"Overall status: **{status}**",
        "",
        f"- Failures: {fail_count}",
        f"- Warnings: {warn_count}",
        "",
        "| Check | Status | Detail |",
        "|---|---|---|",
    ]
    for check in checks:
        detail = check["detail"].replace("|", "\\|")
        lines.append(f"| `{check['name']}` | {check['status']} | {detail} |")
    lines.append("")
    lines.append("This validator checks package completeness and evidence boundaries only. It does not rerun AIDev analysis or execute third party repository code.")
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0 if fail_count == 0 else 1


def main() -> int:
    checks: list[dict[str, str]] = []
    if not MANIFEST.exists():
        add_check(checks, "manifest_exists", "FAIL", f"Missing manifest: {MANIFEST}")
        return write_reports(checks)
    try:
        manifest = load_json(MANIFEST)
    except json.JSONDecodeError as exc:
        add_check(checks, "manifest_parse", "FAIL", f"Invalid JSON: {exc}")
        return write_reports(checks)
    add_check(checks, "manifest_parse", "PASS", f"Loaded {MANIFEST.relative_to(ROOT)}.")
    validate_manifest_paths(manifest, checks)
    validate_aidev_summary(checks)
    validate_data_dictionary(checks)
    validate_prompt_dry_run(checks)
    validate_execution_priority(checks)
    validate_runtime_boundary(checks)
    validate_first_wave_bundle(checks)
    validate_first_wave_launch_sheet(checks)
    validate_preflight_clearance_handoff(checks)
    validate_first_wave_shadow_bridge(checks)
    validate_first_wave_docker_isolation(checks)
    validate_recorder_accumulation(checks)
    validate_first_wave_analysis_drill(checks)
    validate_latex_log(checks)
    validate_cover_letter_consistency(manifest, checks)
    validate_terminology_guard(checks)
    validate_springer_source_dependencies(manifest, checks)
    validate_springer_flat_upload_manifest(manifest, checks)
    validate_figure_table_contracts(manifest, checks)
    validate_submission_blockers(manifest, checks)
    return write_reports(checks)


if __name__ == "__main__":
    raise SystemExit(main())
