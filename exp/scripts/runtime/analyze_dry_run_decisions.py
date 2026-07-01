from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


DEFAULT_DRY_RUN_DIRS = [
    Path("exp/results/emse_runtime/dry_run_offline_full_v1"),
    Path("exp/results/emse_runtime/dry_run_lmstudio_full_contract_v1"),
]
OBSERVED_COLUMNS = ["success", "test_runs", "search_count", "read_count", "patch_attempts"]
FIXED_DECISION_CONTRACTS = {
    "static_conservative": "inherit_baseline",
    "minimal_verify": "minimal_plan",
}


def load_plans(dry_run_dirs: list[Path]) -> tuple[pd.DataFrame, list[dict]]:
    frames = []
    diagnostics = []
    for directory in dry_run_dirs:
        plan_path = directory / "runtime_dry_run_plans.csv"
        template_path = directory / "runtime_task_results_template.csv"
        if not plan_path.exists():
            diagnostics.append({"run_label": directory.name, "status": "missing_plans", "path": str(plan_path)})
            continue
        frame = pd.read_csv(plan_path)
        frame["run_label"] = directory.name
        frames.append(frame)

        template_status = "missing_template"
        empty_observed = ""
        if template_path.exists():
            template = pd.read_csv(template_path)
            available = [col for col in OBSERVED_COLUMNS if col in template.columns]
            if available:
                empty = template[available].isna().all().all() or (template[available].fillna("").astype(str).eq("").all().all())
                template_status = "observed_metrics_empty" if empty else "observed_metrics_present"
                empty_observed = ",".join(available)
            else:
                template_status = "observed_columns_missing"
        diagnostics.append({"run_label": directory.name, "status": template_status, "path": str(template_path), "checked_columns": empty_observed})

    if not frames:
        return pd.DataFrame(), diagnostics
    return pd.concat(frames, ignore_index=True), diagnostics


def decision_summary(plans: pd.DataFrame) -> pd.DataFrame:
    grouped = plans.groupby(["run_label", "controller", "decision"], dropna=False).size().reset_index(name="rows")
    totals = plans.groupby(["run_label", "controller"], dropna=False).size().reset_index(name="controller_rows")
    out = grouped.merge(totals, on=["run_label", "controller"], how="left")
    out["share_within_controller"] = out["rows"] / out["controller_rows"]
    return out.sort_values(["run_label", "controller", "decision"]).reset_index(drop=True)


def risk_decision_summary(plans: pd.DataFrame) -> pd.DataFrame:
    cols = ["run_label", "controller", "risk_tier", "decision"]
    out = plans.groupby(cols, dropna=False).size().reset_index(name="rows")
    return out.sort_values(cols).reset_index(drop=True)


def planned_work_summary(plans: pd.DataFrame) -> pd.DataFrame:
    numeric_cols = ["planned_read_count", "planned_test_count", "planned_patch_attempts", "prompt_chars"]
    for col in numeric_cols:
        if col in plans.columns:
            plans[col] = pd.to_numeric(plans[col], errors="coerce")
    aggregations = {
        "rows": ("instance_id", "count"),
        "tasks": ("instance_id", "nunique"),
    }
    for col in numeric_cols:
        if col in plans.columns:
            aggregations[f"mean_{col}"] = (col, "mean")
            aggregations[f"max_{col}"] = (col, "max")
    return plans.groupby(["run_label", "controller"], dropna=False).agg(**aggregations).reset_index()


def lm_usage_summary(plans: pd.DataFrame) -> pd.DataFrame:
    rows = plans[plans.get("execution_mode", "").astype(str).str.contains("lmstudio", na=False)].copy()
    if rows.empty:
        return pd.DataFrame()
    for col in ["elapsed_seconds", "prompt_tokens", "completion_tokens", "total_tokens"]:
        if col in rows.columns:
            rows[col] = pd.to_numeric(rows[col], errors="coerce")
    return (
        rows.groupby(["run_label", "controller"], dropna=False)
        .agg(
            rows=("instance_id", "count"),
            model=("model", lambda values: ";".join(sorted(set(str(value) for value in values if pd.notna(value))))),
            mean_elapsed_seconds=("elapsed_seconds", "mean"),
            max_elapsed_seconds=("elapsed_seconds", "max"),
            mean_prompt_tokens=("prompt_tokens", "mean"),
            mean_completion_tokens=("completion_tokens", "mean"),
            mean_total_tokens=("total_tokens", "mean"),
        )
        .reset_index()
    )


def instance_decision_variation(plans: pd.DataFrame) -> pd.DataFrame:
    out = (
        plans.groupby(["run_label", "instance_id"], dropna=False)
        .agg(
            repo=("repo", "first"),
            controllers=("controller", "nunique"),
            distinct_decisions=("decision", "nunique"),
            decisions=("decision", lambda values: ";".join(sorted(set(str(value) for value in values)))),
        )
        .reset_index()
    )
    return out.sort_values(["run_label", "distinct_decisions", "instance_id"], ascending=[True, False, True])


def policy_contract_summary(plans: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (run_label, controller), group in plans.groupby(["run_label", "controller"], dropna=False):
        expected = FIXED_DECISION_CONTRACTS.get(str(controller), "")
        if expected:
            violations = group[group["decision"].astype(str) != expected]
            status = "PASS" if violations.empty else "FAIL"
            observed = ";".join(sorted(set(str(value) for value in group["decision"].dropna())))
            rows.append(
                {
                    "run_label": run_label,
                    "controller": controller,
                    "contract": f"decision == {expected}",
                    "rows": int(len(group)),
                    "violations": int(len(violations)),
                    "observed_decisions": observed,
                    "status": status,
                }
            )
        else:
            observed = ";".join(sorted(set(str(value) for value in group["decision"].dropna())))
            rows.append(
                {
                    "run_label": run_label,
                    "controller": controller,
                    "contract": "adaptive decision allowed",
                    "rows": int(len(group)),
                    "violations": 0,
                    "observed_decisions": observed,
                    "status": "INFO",
                }
            )
    return pd.DataFrame(rows).sort_values(["run_label", "controller"]).reset_index(drop=True)


def markdown_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "_No rows._"

    def fmt(value: object) -> str:
        if pd.isna(value):
            return ""
        if isinstance(value, float):
            return f"{value:.3f}"
        return str(value).replace("|", "\\|").replace("\n", " ")

    cols = list(frame.columns)
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, row in frame.iterrows():
        lines.append("| " + " | ".join(fmt(row[col]) for col in cols) + " |")
    return "\n".join(lines)


def write_report(
    path: Path,
    plans: pd.DataFrame,
    decisions: pd.DataFrame,
    work: pd.DataFrame,
    lm_usage: pd.DataFrame,
    variation: pd.DataFrame,
    contracts: pd.DataFrame,
    diagnostics: pd.DataFrame,
) -> None:
    lines = [
        "# Controlled Runtime Dry-Run Decision Analysis",
        "",
        "This report summarizes prompt-only dry-run controller plans. It does not include repository execution, patches, tests, or solve-rate evidence.",
        "",
        "## Scope",
        "",
        f"- Rows: {len(plans)}",
        f"- Tasks: {plans['instance_id'].nunique() if 'instance_id' in plans.columns else 0}",
        f"- Run labels: {', '.join(sorted(plans['run_label'].unique().tolist())) if not plans.empty else ''}",
        "",
        "## Decision Summary",
        "",
        markdown_table(decisions),
        "",
        "## Planned Work Summary",
        "",
        markdown_table(work),
        "",
        "## LM Studio Usage",
        "",
        markdown_table(lm_usage),
        "",
        "## Instance Decision Variation",
        "",
        markdown_table(variation.head(30)),
        "",
        "## Policy Contract Checks",
        "",
        markdown_table(contracts),
        "",
        "## Template Diagnostics",
        "",
        markdown_table(diagnostics),
        "",
        "## Use Boundary",
        "",
        "- Allowed: check controller prompt differentiation, logging schema, and LM Studio latency/token budget.",
        "- Forbidden: claim solve-rate, resource-savings, patch quality, or downstream-work effects.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize controlled-runtime prompt-only dry-run controller decisions.")
    parser.add_argument("--dry-run-dirs", nargs="*", type=Path, default=DEFAULT_DRY_RUN_DIRS)
    parser.add_argument("--output-dir", type=Path, default=Path("exp/results/emse_runtime/dry_run_analysis_v1"))
    args = parser.parse_args()

    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    plans, diagnostics_list = load_plans(args.dry_run_dirs)
    if plans.empty:
        raise ValueError("No dry-run plan rows found.")

    decisions = decision_summary(plans)
    risk_decisions = risk_decision_summary(plans)
    work = planned_work_summary(plans)
    lm_usage = lm_usage_summary(plans)
    variation = instance_decision_variation(plans)
    contracts = policy_contract_summary(plans)
    diagnostics = pd.DataFrame(diagnostics_list)

    plans_path = output_dir / "dry_run_combined_plans.csv"
    decisions_path = output_dir / "dry_run_decision_summary.csv"
    risk_path = output_dir / "dry_run_risk_decision_summary.csv"
    work_path = output_dir / "dry_run_planned_work_summary.csv"
    lm_path = output_dir / "dry_run_lm_usage_summary.csv"
    variation_path = output_dir / "dry_run_instance_decision_variation.csv"
    contracts_path = output_dir / "dry_run_policy_contract_summary.csv"
    diagnostics_path = output_dir / "dry_run_template_diagnostics.csv"
    report_path = output_dir / "dry_run_decision_analysis_report.md"

    plans.to_csv(plans_path, index=False)
    decisions.to_csv(decisions_path, index=False)
    risk_decisions.to_csv(risk_path, index=False)
    work.to_csv(work_path, index=False)
    lm_usage.to_csv(lm_path, index=False)
    variation.to_csv(variation_path, index=False)
    contracts.to_csv(contracts_path, index=False)
    diagnostics.to_csv(diagnostics_path, index=False)
    write_report(report_path, plans, decisions, work, lm_usage, variation, contracts, diagnostics)

    summary = {
        "combined_plans_csv": str(plans_path),
        "decision_summary_csv": str(decisions_path),
        "risk_decision_summary_csv": str(risk_path),
        "planned_work_summary_csv": str(work_path),
        "lm_usage_summary_csv": str(lm_path),
        "instance_decision_variation_csv": str(variation_path),
        "policy_contract_summary_csv": str(contracts_path),
        "template_diagnostics_csv": str(diagnostics_path),
        "report_md": str(report_path),
        "rows": int(len(plans)),
        "tasks": int(plans["instance_id"].nunique()),
        "run_labels": sorted(plans["run_label"].unique().tolist()),
        "safety": "prompt-only; no repository code executed",
    }
    (output_dir / "dry_run_decision_analysis_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Wrote dry-run decision analysis to {report_path}")


if __name__ == "__main__":
    main()
