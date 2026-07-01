from __future__ import annotations

import argparse
import html
import json
from pathlib import Path

import pandas as pd


DEFAULT_ANALYSIS_DIR = Path("exp/results/emse_runtime/pilot_pair_analysis_validated")
DEFAULT_OUTPUT_DIR = Path("exp/results/emse_runtime/pilot_publication_artifacts")

KEY_METRICS = [
    "success",
    "total_observed_work",
    "total_tokens",
    "model_calls",
    "latency_seconds",
    "test_runs",
    "patch_attempts",
    "failed_verification_jobs",
    "recovery_attempts",
]

DISPLAY_NAMES = {
    "success": "Solve rate",
    "total_observed_work": "Total observed work",
    "total_tokens": "Total tokens",
    "model_calls": "Model calls",
    "latency_seconds": "Latency seconds",
    "test_runs": "Test runs",
    "patch_attempts": "Patch attempts",
    "failed_verification_jobs": "Failed verification jobs",
    "recovery_attempts": "Recovery attempts",
}


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def require_columns(frame: pd.DataFrame, columns: list[str], path: Path) -> None:
    missing = [col for col in columns if col not in frame.columns]
    if missing:
        raise ValueError(f"{path} is missing required columns: {', '.join(missing)}")


def load_analysis(analysis_dir: Path) -> tuple[pd.DataFrame, dict[str, object]]:
    metrics_path = analysis_dir / "runtime_pairwise_metrics.csv"
    summary_path = analysis_dir / "runtime_noninferiority_summary.csv"
    if not metrics_path.exists():
        raise FileNotFoundError(f"Missing pairwise metrics: {metrics_path}")
    if not summary_path.exists():
        raise FileNotFoundError(f"Missing non-inferiority summary: {summary_path}")
    metrics = pd.read_csv(metrics_path)
    summary_frame = pd.read_csv(summary_path)
    require_columns(
        metrics,
        [
            "metric",
            "direction",
            "n_pairs",
            "target_mean",
            "reference_mean",
            "mean_diff_target_minus_reference",
            "ci_low",
            "ci_high",
        ],
        metrics_path,
    )
    if summary_frame.empty:
        raise ValueError(f"{summary_path} is empty.")
    return metrics, summary_frame.iloc[0].to_dict()


def key_metric_table(metrics: pd.DataFrame) -> pd.DataFrame:
    rows = metrics[metrics["metric"].astype(str).isin(KEY_METRICS)].copy()
    order = {metric: idx for idx, metric in enumerate(KEY_METRICS)}
    rows["metric_order"] = rows["metric"].map(order)
    rows["metric_label"] = rows["metric"].map(DISPLAY_NAMES).fillna(rows["metric"])
    cols = [
        "metric_label",
        "metric",
        "direction",
        "n_pairs",
        "target_mean",
        "reference_mean",
        "mean_diff_target_minus_reference",
        "ci_low",
        "ci_high",
    ]
    return rows.sort_values("metric_order")[cols].reset_index(drop=True)


def fmt(value: object, digits: int = 3) -> str:
    if pd.isna(value):
        return ""
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def markdown_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "_No key metrics available._"
    headers = [
        "Metric",
        "Direction",
        "Pairs",
        "Target mean",
        "Reference mean",
        "Diff",
        "95% CI",
    ]
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for _, row in frame.iterrows():
        ci = f"[{fmt(row['ci_low'])}, {fmt(row['ci_high'])}]"
        values = [
            str(row["metric_label"]),
            str(row["direction"]),
            str(int(row["n_pairs"])),
            fmt(row["target_mean"]),
            fmt(row["reference_mean"]),
            fmt(row["mean_diff_target_minus_reference"]),
            ci,
        ]
        lines.append("| " + " | ".join(value.replace("|", "\\|") for value in values) + " |")
    return "\n".join(lines)


def status_label(summary: dict[str, object], evidence_status: str = "") -> str:
    if "synthetic" in evidence_status.lower():
        return "synthetic drill: not publication evidence"
    ready = str(summary.get("publication_ready_success_claim", "")).lower() == "true"
    informative = str(summary.get("success_evidence_informative", "")).lower() == "true"
    pairs = int(float(summary.get("n_pairs", 0) or 0))
    min_pairs = int(float(summary.get("min_publication_pairs", 0) or 0))
    if ready:
        return "publication-ready by configured success gate"
    if not informative:
        return "shape check only: success evidence is not informative"
    if pairs < min_pairs:
        return "pilot only: below minimum paired-task guardrail"
    return "not publication-ready by configured success gate"


def write_report(
    path: Path,
    table: pd.DataFrame,
    summary: dict[str, object],
    analysis_dir: Path,
    figure_path: Path,
    evidence_status: str,
    scope_note: str,
) -> None:
    artifact_status = status_label(summary, evidence_status)
    lines = [
        "# Controlled Runtime Publication Artifacts",
        "",
        f"- Source analysis: `{analysis_dir}`",
        f"- Evidence status: `{evidence_status}`",
        f"- Target: `{summary.get('target', '')}`",
        f"- Reference: `{summary.get('reference', '')}`",
        f"- Paired tasks: {fmt(summary.get('n_pairs', ''))}",
        f"- Success margin: {fmt(summary.get('success_margin', ''))}",
        f"- Success mean diff: {fmt(summary.get('success_mean_diff', ''))}",
        f"- Success CI: [{fmt(summary.get('success_ci_low', ''))}, {fmt(summary.get('success_ci_high', ''))}]",
        f"- Success evidence informative: {summary.get('success_evidence_informative', '')}",
        f"- Publication-ready success claim: {summary.get('publication_ready_success_claim', '')}",
        f"- Artifact status: {artifact_status}",
        f"- Figure: `{figure_path}`",
        "",
    ]
    if scope_note:
        lines.extend(["## Scope Note", "", scope_note, ""])
    lines.extend([
        "## Table 4 Draft",
        "",
        markdown_table(table),
        "",
        "## Use Boundary",
        "",
        "- These artifacts summarize already validated pair-analysis outputs.",
        "- They do not make incomplete or prompt-only rows valid.",
        "- They do not turn synthetic drill rows into experiment evidence.",
        "- If the artifact status is not publication-ready, use the outputs only as pilot or schema-check material.",
    ])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def metric_row(metrics: pd.DataFrame, metric: str) -> pd.Series | None:
    rows = metrics[metrics["metric"].astype(str).eq(metric)]
    if rows.empty:
        return None
    return rows.iloc[0]


def scale(value: float, low: float, high: float, start: float, end: float) -> float:
    if high <= low:
        return (start + end) / 2
    return start + (value - low) * (end - start) / (high - low)


def write_svg(path: Path, metrics: pd.DataFrame, summary: dict[str, object], evidence_status: str = "") -> None:
    success = metric_row(metrics, "success")
    work = metric_row(metrics, "total_observed_work")
    width = 920
    height = 500
    margin = 70
    panel_gap = 70
    panel_width = (width - 2 * margin - panel_gap) / 2
    plot_top = 105
    plot_bottom = 410
    status = status_label(summary, evidence_status)

    def bar_panel(row: pd.Series | None, title: str, x0: float, positive_good: bool) -> list[str]:
        if row is None:
            return [
                f'<text x="{x0 + panel_width / 2:.1f}" y="250" text-anchor="middle" font-size="16" fill="#777">Metric unavailable</text>'
            ]
        target = float(row["target_mean"])
        reference = float(row["reference_mean"])
        hi = max(target, reference, 1.0 if row["metric"] == "success" else target, reference)
        lo = 0.0
        bar_w = 70
        x_target = x0 + panel_width * 0.32
        x_ref = x0 + panel_width * 0.68
        y_target = scale(target, lo, hi, plot_bottom, plot_top)
        y_ref = scale(reference, lo, hi, plot_bottom, plot_top)
        color_target = "#2b6cb0" if positive_good else "#b45309"
        color_ref = "#718096"
        lines = [
            f'<text x="{x0 + panel_width / 2:.1f}" y="82" text-anchor="middle" font-size="18" font-weight="600">{html.escape(title)}</text>',
            f'<line x1="{x0:.1f}" y1="{plot_bottom}" x2="{x0 + panel_width:.1f}" y2="{plot_bottom}" stroke="#333" />',
            f'<line x1="{x0:.1f}" y1="{plot_top}" x2="{x0:.1f}" y2="{plot_bottom}" stroke="#333" />',
            f'<rect x="{x_target - bar_w / 2:.1f}" y="{y_target:.1f}" width="{bar_w}" height="{plot_bottom - y_target:.1f}" fill="{color_target}" />',
            f'<rect x="{x_ref - bar_w / 2:.1f}" y="{y_ref:.1f}" width="{bar_w}" height="{plot_bottom - y_ref:.1f}" fill="{color_ref}" />',
            f'<text x="{x_target:.1f}" y="{y_target - 8:.1f}" text-anchor="middle" font-size="13">{target:.3f}</text>',
            f'<text x="{x_ref:.1f}" y="{y_ref - 8:.1f}" text-anchor="middle" font-size="13">{reference:.3f}</text>',
            f'<text x="{x_target:.1f}" y="{plot_bottom + 24}" text-anchor="middle" font-size="13">target</text>',
            f'<text x="{x_ref:.1f}" y="{plot_bottom + 24}" text-anchor="middle" font-size="13">reference</text>',
            f'<text x="{x0 + panel_width / 2:.1f}" y="{plot_bottom + 48}" text-anchor="middle" font-size="12">diff {float(row["mean_diff_target_minus_reference"]):.3f}, CI [{float(row["ci_low"]):.3f}, {float(row["ci_high"]):.3f}]</text>',
        ]
        return lines

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white" />',
        '<text x="460" y="36" text-anchor="middle" font-size="22" font-weight="700">Controlled runtime solve-resource summary</text>',
        f'<text x="460" y="60" text-anchor="middle" font-size="13" fill="#555">{html.escape(status)}</text>',
        *bar_panel(success, "Solve rate", margin, True),
        *bar_panel(work, "Total observed work", margin + panel_width + panel_gap, False),
        '<text x="460" y="480" text-anchor="middle" font-size="12" fill="#666">Generated from validated pair-analysis metrics; not a substitute for completed controlled runs.</text>',
        "</svg>",
    ]
    path.write_text("\n".join(svg), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Create manuscript-facing figures and tables from validated runtime pair-analysis outputs.")
    parser.add_argument("--analysis-dir", type=Path, default=DEFAULT_ANALYSIS_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--evidence-status", default="validated_pair_analysis")
    parser.add_argument("--scope-note", default="")
    args = parser.parse_args()

    metrics, summary = load_analysis(args.analysis_dir)
    output_dir = ensure_dir(args.output_dir)
    figure_dir = ensure_dir(output_dir / "figures")
    table = key_metric_table(metrics)

    table_csv = output_dir / "runtime_publication_key_metrics.csv"
    report_md = output_dir / "runtime_publication_artifacts.md"
    figure_svg = figure_dir / "runtime_solve_resource_summary.svg"
    summary_json = output_dir / "runtime_publication_artifact_summary.json"

    table.to_csv(table_csv, index=False)
    write_svg(figure_svg, metrics, summary, args.evidence_status)
    write_report(report_md, table, summary, args.analysis_dir, figure_svg, args.evidence_status, args.scope_note)
    artifact_status = status_label(summary, args.evidence_status)
    artifact_summary = {
        "source_analysis_dir": str(args.analysis_dir),
        "key_metrics_csv": str(table_csv),
        "report_md": str(report_md),
        "figure_svg": str(figure_svg),
        "evidence_status": args.evidence_status,
        "scope_note": args.scope_note,
        "artifact_status": artifact_status,
        "publication_ready_success_claim": bool(str(summary.get("publication_ready_success_claim", "")).lower() == "true"),
        "third_party_execution_performed": False,
    }
    summary_json.write_text(json.dumps(artifact_summary, indent=2), encoding="utf-8")
    print(f"Wrote runtime key metrics to {table_csv}")
    print(f"Wrote runtime report to {report_md}")
    print(f"Wrote runtime figure to {figure_svg}")


if __name__ == "__main__":
    try:
        main()
    except (FileNotFoundError, ValueError) as exc:
        raise SystemExit(f"ERROR: {exc}") from None
