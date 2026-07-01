from __future__ import annotations

import argparse
import html
from pathlib import Path

import numpy as np
import pandas as pd

from .common import RESULTS_DIR, ensure_dir, write_json
from .analyze_gate_errors import fit_and_label_split, prepare_frame
from .evaluate_workload_gate import repository_disjoint_split, temporal_split


HOUR = 1.0
DAY = 24.0 * HOUR
DEFAULT_HORIZONS_HOURS = [7 * DAY, 30 * DAY, 90 * DAY]


def markdown_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "_No rows._"

    def fmt(value: object) -> str:
        if pd.isna(value):
            return ""
        if isinstance(value, (float, np.floating)):
            return f"{float(value):.3f}"
        if isinstance(value, (int, np.integer)):
            return str(int(value))
        return str(value).replace("\n", " ").replace("|", "\\|")

    columns = list(frame.columns)
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join(["---"] * len(columns)) + " |",
    ]
    for _, row in frame.iterrows():
        lines.append("| " + " | ".join(fmt(row[col]) for col in columns) + " |")
    return "\n".join(lines)


def observation_cutoff(frame: pd.DataFrame) -> pd.Timestamp:
    candidates = []
    for col in ["created_at", "closed_at", "merged_at"]:
        if col in frame.columns:
            value = pd.to_datetime(frame[col], errors="coerce", utc=True).max()
            if pd.notna(value):
                candidates.append(value)
    if not candidates:
        raise ValueError("No timestamp columns are available for survival analysis.")
    return max(candidates)


def add_survival_columns(frame: pd.DataFrame, cutoff: pd.Timestamp) -> pd.DataFrame:
    out = frame.copy()
    created = pd.to_datetime(out["created_at"], errors="coerce", utc=True)
    closed = pd.to_datetime(out["closed_at"], errors="coerce", utc=True)
    event = closed.notna()
    end_time = closed.where(event, cutoff)
    duration = ((end_time - created).dt.total_seconds() / 3600.0).clip(lower=0.0)
    out["resolution_event"] = event.to_numpy(dtype=bool)
    out["resolution_time_hours"] = duration.to_numpy(dtype=float)
    return out.dropna(subset=["resolution_time_hours"])


def km_stats(times: np.ndarray, events: np.ndarray, horizons_hours: list[float]) -> dict[str, float]:
    valid = np.isfinite(times) & (times >= 0)
    times = times[valid]
    events = events[valid].astype(bool)
    if len(times) == 0:
        return {}

    event_times = np.sort(np.unique(times[events]))
    survival = 1.0
    median_hours = float("nan")
    max_horizon = max(horizons_hours)
    rmst_area = {horizon: 0.0 for horizon in horizons_hours}
    survival_at = {horizon: 1.0 for horizon in horizons_hours}

    for horizon in horizons_hours:
        survival = 1.0
        previous = 0.0
        for event_time in event_times[event_times <= horizon]:
            if event_time > previous:
                rmst_area[horizon] += survival * (event_time - previous)
                previous = float(event_time)
            at_risk = int(np.sum(times >= event_time))
            event_count = int(np.sum((times == event_time) & events))
            if at_risk > 0:
                survival *= 1.0 - event_count / at_risk
        if horizon > previous:
            rmst_area[horizon] += survival * (horizon - previous)
        survival_at[horizon] = survival

    survival = 1.0
    for event_time in event_times:
        at_risk = int(np.sum(times >= event_time))
        event_count = int(np.sum((times == event_time) & events))
        if at_risk > 0:
            survival *= 1.0 - event_count / at_risk
        if survival <= 0.5:
            median_hours = float(event_time)
            break
        if event_time > max_horizon and np.isfinite(median_hours):
            break

    out = {
        "km_median_hours": median_hours,
    }
    for horizon in horizons_hours:
        days = int(round(horizon / DAY))
        out[f"unresolved_probability_{days}d"] = survival_at[horizon]
        out[f"rmst_{days}d_hours"] = rmst_area[horizon]
    return out


def summarize_group(split: str, gate_group: str, frame: pd.DataFrame, horizons_hours: list[float]) -> dict[str, float | int | str]:
    times = frame["resolution_time_hours"].to_numpy(dtype=float)
    events = frame["resolution_event"].to_numpy(dtype=bool)
    closed_times = frame.loc[frame["resolution_event"], "resolution_time_hours"]
    stats = km_stats(times, events, horizons_hours)
    row: dict[str, float | int | str] = {
        "split": split,
        "gate_group": gate_group,
        "rows": int(len(frame)),
        "closed_events": int(events.sum()),
        "censored_open": int((~events).sum()),
        "observed_closure_rate": float(events.mean()) if len(events) else float("nan"),
        "median_closed_hours_observed": float(closed_times.median()) if len(closed_times) else float("nan"),
        **stats,
    }
    for horizon in horizons_hours:
        days = int(round(horizon / DAY))
        row[f"rmst_{days}d_days"] = float(row[f"rmst_{days}d_hours"]) / DAY
    if np.isfinite(float(row.get("km_median_hours", float("nan")))):
        row["km_median_days"] = float(row["km_median_hours"]) / DAY
    else:
        row["km_median_days"] = float("nan")
    return row


def summarize_split(split: str, frame: pd.DataFrame, horizons_hours: list[float]) -> list[dict]:
    rows = [summarize_group(split, "all", frame, horizons_hours)]
    rows.append(summarize_group(split, "accepted", frame[frame["accepted"]], horizons_hours))
    rows.append(summarize_group(split, "routed", frame[~frame["accepted"]], horizons_hours))
    return rows


def contrast_metrics(frame: pd.DataFrame, horizons_hours: list[float]) -> dict[str, float]:
    accepted = frame[frame["accepted"]]
    routed = frame[~frame["accepted"]]
    if accepted.empty or routed.empty:
        return {}
    acc = summarize_group("", "accepted", accepted, horizons_hours)
    routed_summary = summarize_group("", "routed", routed, horizons_hours)
    out = {
        "accepted_rows": int(acc["rows"]),
        "routed_rows": int(routed_summary["rows"]),
        "closed_rate_diff_accepted_minus_abstained": float(acc["observed_closure_rate"]) - float(routed_summary["observed_closure_rate"]),
    }
    for horizon in horizons_hours:
        days = int(round(horizon / DAY))
        out[f"unresolved_{days}d_diff_accepted_minus_abstained"] = (
            float(acc[f"unresolved_probability_{days}d"]) - float(routed_summary[f"unresolved_probability_{days}d"])
        )
        out[f"rmst_{days}d_days_diff_accepted_minus_abstained"] = (
            float(acc[f"rmst_{days}d_days"]) - float(routed_summary[f"rmst_{days}d_days"])
        )
    return out


def bootstrap_contrasts(
    split: str,
    frame: pd.DataFrame,
    horizons_hours: list[float],
    rounds: int,
    seed: int,
) -> list[dict]:
    point = contrast_metrics(frame, horizons_hours)
    if not point:
        return []

    rng = np.random.default_rng(seed)
    groups = frame["repo_id"].fillna("__missing_repo__").astype(str).to_numpy()
    unique_groups = np.unique(groups)
    group_indices = {group: np.flatnonzero(groups == group) for group in unique_groups}
    draws: dict[str, list[float]] = {metric: [] for metric, value in point.items() if isinstance(value, float)}

    for _ in range(rounds):
        sampled_groups = rng.choice(unique_groups, size=len(unique_groups), replace=True)
        idx = np.concatenate([group_indices[group] for group in sampled_groups])
        sample = frame.iloc[idx].reset_index(drop=True)
        metrics = contrast_metrics(sample, horizons_hours)
        for metric in draws:
            value = metrics.get(metric, float("nan"))
            if np.isfinite(value):
                draws[metric].append(float(value))

    rows = []
    for metric, values in draws.items():
        arr = np.asarray(values, dtype=float)
        rows.append(
            {
                "split": split,
                "metric": metric,
                "point": point[metric],
                "ci_low": float(np.quantile(arr, 0.025)) if len(arr) else float("nan"),
                "ci_high": float(np.quantile(arr, 0.975)) if len(arr) else float("nan"),
                "bootstrap_rounds": rounds,
                "bootstrap_valid_rounds": int(len(arr)),
                "bootstrap_unit": "repo",
                "accepted_rows": int(point["accepted_rows"]),
                "routed_rows": int(point["routed_rows"]),
            }
        )
    return rows


def survival_curve(frame: pd.DataFrame, horizon_hours: float) -> pd.DataFrame:
    times = frame["resolution_time_hours"].to_numpy(dtype=float)
    events = frame["resolution_event"].to_numpy(dtype=bool)
    valid = np.isfinite(times) & (times >= 0)
    times = times[valid]
    events = events[valid]
    event_times = np.sort(np.unique(times[events & (times <= horizon_hours)]))
    rows = [{"time_hours": 0.0, "survival": 1.0}]
    survival = 1.0
    for event_time in event_times:
        at_risk = int(np.sum(times >= event_time))
        event_count = int(np.sum((times == event_time) & events))
        if at_risk > 0:
            survival *= 1.0 - event_count / at_risk
        rows.append({"time_hours": float(event_time), "survival": survival})
    if rows[-1]["time_hours"] < horizon_hours:
        rows.append({"time_hours": horizon_hours, "survival": survival})
    return pd.DataFrame(rows)


class Svg:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.items: list[str] = []

    def line(self, x1: float, y1: float, x2: float, y2: float, color: str = "#111827", width: float = 1.0) -> None:
        self.items.append(
            f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{color}" stroke-width="{width:.1f}"/>'
        )

    def text(self, x: float, y: float, value: object, size: int = 11, anchor: str = "start", weight: str = "400", color: str = "#111827") -> None:
        escaped = html.escape(str(value))
        self.items.append(
            f'<text x="{x:.1f}" y="{y:.1f}" font-family="Arial, Helvetica, sans-serif" font-size="{size}" '
            f'font-weight="{weight}" fill="{color}" text-anchor="{anchor}">{escaped}</text>'
        )

    def path(self, points: list[tuple[float, float]], color: str, width: float = 2.0) -> None:
        if not points:
            return
        data = " ".join(("M" if idx == 0 else "L") + f"{x:.1f},{y:.1f}" for idx, (x, y) in enumerate(points))
        self.items.append(f'<path d="{data}" fill="none" stroke="{color}" stroke-width="{width:.1f}" stroke-linejoin="round"/>')

    def circle(self, x: float, y: float, radius: float, fill: str) -> None:
        self.items.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{radius:.1f}" fill="{fill}"/>')

    def save(self, path: Path) -> None:
        ensure_dir(path.parent)
        body = "\n  ".join(self.items)
        path.write_text(
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.width}" height="{self.height}" viewBox="0 0 {self.width} {self.height}">\n'
            f'  <rect width="100%" height="100%" fill="white"/>\n  {body}\n</svg>\n',
            encoding="utf-8",
        )


def scale(value: float, domain: tuple[float, float], output: tuple[float, float]) -> float:
    low, high = domain
    out_low, out_high = output
    if high <= low:
        return (out_low + out_high) / 2.0
    return out_low + (float(value) - low) * (out_high - out_low) / (high - low)


def write_figure(labeled: pd.DataFrame, path: Path, horizon_hours: float) -> None:
    svg = Svg(780, 430)
    svg.text(36, 32, "Censored time to closure diagnostic", size=16, weight="700")
    svg.text(36, 52, "Kaplan-Meier probability a PR remains unresolved; open PRs are right censored at the data cutoff.", size=11, color="#6B7280")
    panels = [("temporal", 82), ("repository_disjoint", 426)]
    colors = {"accepted": "#0072B2", "routed": "#D55E00"}
    labels = {"temporal": "Temporal", "repository_disjoint": "Unseen repository"}
    for split, left in panels:
        top, width, height = 86, 270, 230
        svg.text(left, top - 18, labels[split], size=12, weight="700")
        bottom = top + height
        svg.line(left, bottom, left + width, bottom)
        svg.line(left, top, left, bottom)
        for day in [0, 7, 14, 21, 30]:
            x = scale(day * DAY, (0, horizon_hours), (left, left + width))
            svg.line(x, bottom, x, bottom + 4)
            svg.text(x, bottom + 18, str(day), size=9, anchor="middle", color="#6B7280")
        for prob in [0.0, 0.25, 0.5, 0.75, 1.0]:
            y = scale(prob, (0, 1), (bottom, top))
            svg.line(left - 4, y, left, y)
            svg.text(left - 8, y + 3, f"{prob:.2f}", size=9, anchor="end", color="#6B7280")
        split_frame = labeled[labeled["split"] == split]
        for gate_group, color in colors.items():
            group = split_frame[split_frame["accepted"]] if gate_group == "accepted" else split_frame[~split_frame["accepted"]]
            curve = survival_curve(group, horizon_hours)
            points = [
                (
                    scale(row["time_hours"], (0, horizon_hours), (left, left + width)),
                    scale(row["survival"], (0, 1), (bottom, top)),
                )
                for _, row in curve.iterrows()
            ]
            svg.path(points, color, 2.0)
        svg.text(left + width / 2, bottom + 42, "Days since PR creation", size=10, anchor="middle")
    svg.circle(620, 94, 4, colors["accepted"])
    svg.text(632, 98, "Accepted", size=10)
    svg.circle(620, 116, 4, colors["routed"])
    svg.text(632, 120, "Routed", size=10)
    svg.text(36, 392, "Diagnostic only: accepted and routed PRs are observed groups, not randomized counterfactuals.", size=10, color="#6B7280")
    svg.save(path)


def readable_summary(summary: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "split",
        "gate_group",
        "rows",
        "closed_events",
        "censored_open",
        "observed_closure_rate",
        "km_median_days",
        "unresolved_probability_7d",
        "unresolved_probability_30d",
        "unresolved_probability_90d",
        "rmst_30d_days",
    ]
    return summary[[col for col in cols if col in summary.columns]].copy()


def readable_contrast(contrast: pd.DataFrame) -> pd.DataFrame:
    keep = [
        "split",
        "metric",
        "point",
        "ci_low",
        "ci_high",
        "bootstrap_unit",
        "bootstrap_rounds",
        "bootstrap_valid_rounds",
    ]
    metrics = {
        "unresolved_30d_diff_accepted_minus_abstained",
        "rmst_30d_days_diff_accepted_minus_abstained",
        "closed_rate_diff_accepted_minus_abstained",
    }
    rows = contrast[contrast["metric"].isin(metrics)].copy()
    metric_labels = {
        "unresolved_30d_diff_accepted_minus_abstained": "30-day unresolved probability, accepted minus routed",
        "rmst_30d_days_diff_accepted_minus_abstained": "30-day RMST unresolved, accepted minus routed",
        "closed_rate_diff_accepted_minus_abstained": "Observed closure rate, accepted minus routed",
    }
    rows["metric"] = rows["metric"].map(metric_labels).fillna(rows["metric"])
    return rows[[col for col in keep if col in rows.columns]]


def write_report(path: Path, summary: pd.DataFrame, contrast: pd.DataFrame, cutoff: pd.Timestamp, figure_path: Path) -> None:
    lines = [
        "# AIDev Resolution-Time Survival Diagnostic",
        "",
        f"Observation cutoff: `{cutoff.isoformat()}`.",
        "",
        "This diagnostic treats open PRs as right-censored rather than dropping them from resolution-time analysis. It uses Kaplan-Meier survival estimates and restricted mean time unresolved (RMST). The accepted and routed groups are observational gate outputs, not randomized counterfactuals.",
        "",
        "## Gate-Group Summary",
        "",
        markdown_table(readable_summary(summary)),
        "",
        "## Accepted-vs-Routed Cluster Bootstrap Contrasts",
        "",
        markdown_table(readable_contrast(contrast)),
        "",
        "## Figure",
        "",
        f"- `{figure_path}`",
        "",
        "## Claim Boundary",
        "",
        "- Allowed: report whether accepted and routed PRs differ in censored time-to-closure diagnostics.",
        "- Forbidden: claim that gate acceptance causally shortens or lengthens resolution time.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze censored AIDev time-to-closure diagnostics for gate outputs.")
    parser.add_argument("--features", type=Path, default=RESULTS_DIR / "aidev_pr_level_features.csv")
    parser.add_argument("--output-dir", type=Path, default=RESULTS_DIR)
    parser.add_argument("--target", default="outcome_downstream_workload_log")
    parser.add_argument("--workload", default="outcome_downstream_workload_raw")
    parser.add_argument("--high-workload-quantile", type=float, default=0.80)
    parser.add_argument("--risk-budget", type=float, default=0.10)
    parser.add_argument("--bootstrap-rounds", type=int, default=500)
    parser.add_argument("--seed", type=int, default=23)
    args = parser.parse_args()

    frame = prepare_frame(args.features, args.target, args.workload)
    cutoff = observation_cutoff(frame)
    split_specs = [
        ("temporal", *temporal_split(frame)),
        ("repository_disjoint", *repository_disjoint_split(frame, args.seed)),
    ]

    labeled_frames = []
    for split_name, train, calibration, test in split_specs:
        labeled, _ = fit_and_label_split(
            split_name,
            train,
            calibration,
            test,
            args.target,
            args.workload,
            args.high_workload_quantile,
            args.risk_budget,
        )
        labeled = add_survival_columns(labeled, cutoff)
        labeled_frames.append(labeled)

    labeled_all = pd.concat(labeled_frames, ignore_index=True)
    summary_rows = []
    contrast_rows = []
    for split, group in labeled_all.groupby("split", dropna=False):
        summary_rows.extend(summarize_split(str(split), group, DEFAULT_HORIZONS_HOURS))
        contrast_rows.extend(bootstrap_contrasts(str(split), group, DEFAULT_HORIZONS_HOURS, args.bootstrap_rounds, args.seed))

    output_dir = ensure_dir(args.output_dir)
    figure_dir = ensure_dir(output_dir / "figures")
    summary = pd.DataFrame(summary_rows)
    contrast = pd.DataFrame(contrast_rows)
    curves = []
    for (split, accepted), group in labeled_all.groupby(["split", "accepted"], dropna=False):
        curve = survival_curve(group, 30 * DAY)
        curve["split"] = split
        curve["gate_group"] = "accepted" if accepted else "routed"
        curves.append(curve)
    curve_frame = pd.concat(curves, ignore_index=True) if curves else pd.DataFrame()

    summary_path = output_dir / "aidev_resolution_survival_summary.csv"
    contrast_path = output_dir / "aidev_resolution_survival_contrast.csv"
    curve_path = output_dir / "aidev_resolution_survival_curves.csv"
    report_path = output_dir / "aidev_resolution_survival_report.md"
    figure_path = figure_dir / "aidev_resolution_survival.svg"

    summary.to_csv(summary_path, index=False)
    contrast.to_csv(contrast_path, index=False)
    curve_frame.to_csv(curve_path, index=False)
    write_figure(labeled_all, figure_path, 30 * DAY)
    write_report(report_path, summary, contrast, cutoff, figure_path)
    write_json(
        output_dir / "aidev_resolution_survival_summary.json",
        {
            "summary_csv": str(summary_path),
            "contrast_csv": str(contrast_path),
            "curves_csv": str(curve_path),
            "report_md": str(report_path),
            "figure_svg": str(figure_path),
            "rows": int(len(labeled_all)),
            "splits": sorted(labeled_all["split"].unique().tolist()),
            "observation_cutoff": cutoff.isoformat(),
            "bootstrap_rounds": args.bootstrap_rounds,
            "risk_budget": args.risk_budget,
        },
    )
    print(f"Wrote resolution survival diagnostic to {report_path}")


if __name__ == "__main__":
    main()
