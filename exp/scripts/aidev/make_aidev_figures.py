from __future__ import annotations

import argparse
import html
import os
from pathlib import Path

import pandas as pd

from .common import RESULTS_DIR, ensure_dir


DEFAULT_FIGURE_DIR = RESULTS_DIR / "figures"

COLORS = {
    "blue": "#0072B2",
    "orange": "#E69F00",
    "green": "#009E73",
    "vermillion": "#D55E00",
    "purple": "#CC79A7",
    "gray": "#6B7280",
    "light_gray": "#E5E7EB",
    "dark": "#111827",
}

CASE_ORDER = [
    "safe_accept_low_workload",
    "false_accept_high_workload",
    "useful_abstain_high_workload",
    "conservative_abstain_low_workload",
]

CASE_LABELS = {
    "safe_accept_low_workload": "Accept low",
    "false_accept_high_workload": "Accept high",
    "useful_abstain_high_workload": "Route high",
    "conservative_abstain_low_workload": "Route low",
}

CASE_COLORS = {
    "safe_accept_low_workload": COLORS["blue"],
    "false_accept_high_workload": COLORS["vermillion"],
    "useful_abstain_high_workload": COLORS["green"],
    "conservative_abstain_low_workload": COLORS["orange"],
}


class Svg:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.items: list[str] = []
        self.ops: list[tuple[str, dict[str, object]]] = []

    def line(self, x1: float, y1: float, x2: float, y2: float, color: str = COLORS["dark"], width: float = 1.0, dash: str | None = None) -> None:
        dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
        self.items.append(
            f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="{color}" stroke-width="{width:.1f}"{dash_attr}/>'
        )
        self.ops.append(("line", {"x1": x1, "y1": y1, "x2": x2, "y2": y2, "color": color, "width": width, "dash": dash}))

    def rect(self, x: float, y: float, width: float, height: float, fill: str, stroke: str | None = None) -> None:
        stroke_attr = f' stroke="{stroke}" stroke-width="1"' if stroke else ""
        self.items.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{width:.1f}" height="{height:.1f}" fill="{fill}"{stroke_attr}/>'
        )
        self.ops.append(("rect", {"x": x, "y": y, "width": width, "height": height, "fill": fill, "stroke": stroke}))

    def circle(self, x: float, y: float, radius: float, fill: str, stroke: str = "white") -> None:
        self.items.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{radius:.1f}" fill="{fill}" stroke="{stroke}" stroke-width="1.2"/>'
        )
        self.ops.append(("circle", {"x": x, "y": y, "radius": radius, "fill": fill, "stroke": stroke}))

    def text(self, x: float, y: float, value: object, size: int = 11, anchor: str = "start", weight: str = "400", color: str = COLORS["dark"]) -> None:
        escaped = html.escape(str(value))
        self.items.append(
            f'<text x="{x:.1f}" y="{y:.1f}" font-family="Arial, Helvetica, sans-serif" font-size="{size}" '
            f'font-weight="{weight}" fill="{color}" text-anchor="{anchor}">{escaped}</text>'
        )
        self.ops.append(("text", {"x": x, "y": y, "value": str(value), "size": size, "anchor": anchor, "weight": weight, "color": color}))

    def path(self, points: list[tuple[float, float]], color: str, width: float = 2.0) -> None:
        if not points:
            return
        data = " ".join(("M" if idx == 0 else "L") + f"{x:.1f},{y:.1f}" for idx, (x, y) in enumerate(points))
        self.items.append(f'<path d="{data}" fill="none" stroke="{color}" stroke-width="{width:.1f}" stroke-linejoin="round"/>')
        self.ops.append(("path", {"points": points, "color": color, "width": width}))

    def save(self, path: Path) -> None:
        ensure_dir(path.parent)
        body = "\n  ".join(self.items)
        path.write_text(
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.width}" height="{self.height}" viewBox="0 0 {self.width} {self.height}">\n'
            f'  <rect width="100%" height="100%" fill="white"/>\n  {body}\n</svg>\n',
            encoding="utf-8",
        )

    def save_pdf(self, path: Path) -> None:
        ensure_dir(path.parent)
        cache_dir = ensure_dir(Path(os.environ.get("TMPDIR", "/tmp")) / "camc_matplotlib_cache")
        os.environ.setdefault("MPLCONFIGDIR", str(cache_dir))
        os.environ.setdefault("XDG_CACHE_HOME", str(ensure_dir(cache_dir / "xdg")))
        import matplotlib

        matplotlib.use("pdf")
        import matplotlib.pyplot as plt
        from matplotlib.lines import Line2D
        from matplotlib.patches import Circle, Rectangle

        fig = plt.figure(figsize=(self.width / 100.0, self.height / 100.0), dpi=100)
        ax = fig.add_axes([0, 0, 1, 1])
        ax.set_xlim(0, self.width)
        ax.set_ylim(self.height, 0)
        ax.axis("off")
        ax.add_patch(Rectangle((0, 0), self.width, self.height, facecolor="white", edgecolor="none"))

        for kind, data in self.ops:
            if kind == "line":
                linestyle = "-"
                dash = data.get("dash")
                if isinstance(dash, str) and dash:
                    try:
                        linestyle = (0, tuple(float(part) for part in dash.split(",")))
                    except ValueError:
                        linestyle = "--"
                ax.add_line(
                    Line2D(
                        [float(data["x1"]), float(data["x2"])],
                        [float(data["y1"]), float(data["y2"])],
                        color=str(data["color"]),
                        linewidth=float(data["width"]),
                        linestyle=linestyle,
                    )
                )
            elif kind == "rect":
                ax.add_patch(
                    Rectangle(
                        (float(data["x"]), float(data["y"])),
                        float(data["width"]),
                        float(data["height"]),
                        facecolor=str(data["fill"]),
                        edgecolor=str(data["stroke"]) if data["stroke"] else "none",
                        linewidth=1.0,
                    )
                )
            elif kind == "circle":
                ax.add_patch(
                    Circle(
                        (float(data["x"]), float(data["y"])),
                        float(data["radius"]),
                        facecolor=str(data["fill"]),
                        edgecolor=str(data["stroke"]),
                        linewidth=1.2,
                    )
                )
            elif kind == "text":
                anchor = {"start": "left", "middle": "center", "end": "right"}.get(str(data["anchor"]), "left")
                ax.text(
                    float(data["x"]),
                    float(data["y"]),
                    str(data["value"]),
                    fontsize=int(data["size"]),
                    fontweight=str(data["weight"]),
                    color=str(data["color"]),
                    horizontalalignment=anchor,
                    verticalalignment="baseline",
                    fontfamily="Arial",
                )
            elif kind == "path":
                points = data["points"]
                if points:
                    xs, ys = zip(*points)
                    ax.plot(xs, ys, color=str(data["color"]), linewidth=float(data["width"]), solid_joinstyle="round")

        fig.savefig(path, format="pdf", bbox_inches="tight", pad_inches=0)
        plt.close(fig)


def save_publication_figure(svg: Svg, path: Path) -> Path:
    svg.save(path)
    svg.save_pdf(path.with_suffix(".pdf"))
    return path


def scale(value: float, domain: tuple[float, float], output: tuple[float, float]) -> float:
    low, high = domain
    out_low, out_high = output
    if high <= low:
        return (out_low + out_high) / 2.0
    return out_low + (float(value) - low) * (out_high - out_low) / (high - low)


def draw_axes(svg: Svg, left: int, top: int, width: int, height: int, x_label: str, y_label: str) -> None:
    bottom = top + height
    right = left + width
    svg.line(left, bottom, right, bottom, COLORS["dark"], 1.0)
    svg.line(left, top, left, bottom, COLORS["dark"], 1.0)
    for tick in [0.0, 0.25, 0.5, 0.75, 1.0]:
        x = scale(tick, (0, 1), (left, right))
        svg.line(x, bottom, x, bottom + 4, COLORS["dark"], 1.0)
        svg.text(x, bottom + 18, f"{tick:.2f}", size=9, anchor="middle", color=COLORS["gray"])
        y = scale(tick, (0, 1), (bottom, top))
        svg.line(left - 4, y, left, y, COLORS["dark"], 1.0)
        svg.text(left - 8, y + 3, f"{tick:.2f}", size=9, anchor="end", color=COLORS["gray"])
        if tick not in {0.0, 1.0}:
            svg.line(left, y, right, y, COLORS["light_gray"], 0.8)
    svg.text(left + width / 2, bottom + 40, x_label, size=11, anchor="middle")
    svg.text(left - 48, top + height / 2, y_label, size=11, anchor="middle")


def make_frontier_figure(results_dir: Path, figure_dir: Path) -> Path:
    frame = pd.read_csv(results_dir / "aidev_frontier_table.csv")
    svg = Svg(720, 430)
    left, top, width, height = 82, 72, 520, 270
    svg.text(36, 32, "AIDev coverage and risk frontier", size=16, weight="700")
    svg.text(36, 52, "High workload rate among accepted PRs; lower is safer at a given coverage.", size=11, color=COLORS["gray"])
    draw_axes(svg, left, top, width, height, "Acceptance rate", "High workload if accepted")

    split_colors = {"temporal": COLORS["blue"], "repository_disjoint": COLORS["vermillion"]}
    split_labels = {"temporal": "Temporal", "repository_disjoint": "Unseen repository"}
    for split, color in split_colors.items():
        rows = frame[frame["split"] == split].sort_values("accept_rate")
        points = [
            (
                scale(row["accept_rate"], (0, 1), (left, left + width)),
                scale(row["accepted_high_rate"], (0, 1), (top + height, top)),
            )
            for _, row in rows.iterrows()
        ]
        svg.path(points, color, 2.2)
        for _, row in rows.iterrows():
            x = scale(row["accept_rate"], (0, 1), (left, left + width))
            y = scale(row["accepted_high_rate"], (0, 1), (top + height, top))
            svg.circle(x, y, 4.2 if row["selector"] == "calibration_risk_budget" else 3.4, color)
    svg.rect(622, 86, 14, 4, COLORS["blue"])
    svg.text(642, 91, split_labels["temporal"], size=11)
    svg.rect(622, 108, 14, 4, COLORS["vermillion"])
    svg.text(642, 113, split_labels["repository_disjoint"], size=11)
    svg.text(622, 145, "Large markers: risk limit gates", size=10, color=COLORS["gray"])

    path = figure_dir / "aidev_coverage_risk_frontier.svg"
    return save_publication_figure(svg, path)


def make_baseline_figure(results_dir: Path, figure_dir: Path) -> Path:
    frame = pd.read_csv(results_dir / "aidev_baseline_comparison_table.csv")
    rows = frame[frame["split"] == "repository_disjoint"].copy()
    rows = rows.sort_values("accepted_high_rate")
    svg = Svg(720, 430)
    left, top, width, height = 86, 74, 500, 260
    svg.text(36, 32, "Unseen repository baseline comparison", size=16, weight="700")
    svg.text(36, 52, "Risk limit 0.10; rightward means more coverage, lower means fewer high workload PRs accepted.", size=11, color=COLORS["gray"])
    draw_axes(svg, left, top, width, height, "Acceptance rate", "High workload if accepted")

    color_map = {
        "logistic_all_features": COLORS["blue"],
        "cost_sensitive_workload_logistic": COLORS["vermillion"],
        "logistic_no_agent": COLORS["orange"],
        "categorical_prior": COLORS["green"],
        "simple_text_threshold": COLORS["gray"],
        "selective_uncertainty_only": COLORS["purple"],
    }
    label_map = {
        "logistic_all_features": "Defensible features",
        "cost_sensitive_workload_logistic": "Workload weights",
        "logistic_no_agent": "No agent ID",
        "categorical_prior": "Categorical prior",
        "simple_text_threshold": "Text threshold",
        "selective_uncertainty_only": "Uncertainty threshold",
    }
    for _, row in rows.iterrows():
        color = color_map.get(row["baseline"], COLORS["gray"])
        x = scale(row["accept_rate"], (0, 1), (left, left + width))
        y = scale(row["accepted_high_rate"], (0, 1), (top + height, top))
        svg.circle(x, y, 5.0, color)
        svg.text(min(x + 8, left + width + 10), y + 4, label_map.get(row["baseline"], row["baseline"]), size=10, color=color)

    path = figure_dir / "aidev_baseline_comparison.svg"
    return save_publication_figure(svg, path)


def make_component_figure(results_dir: Path, figure_dir: Path) -> Path:
    frame = pd.read_csv(results_dir / "aidev_component_prediction_table.csv")
    rows = frame[frame["split"] == "repository_disjoint"].sort_values("auc", ascending=True).copy()
    label_map = {
        "outcome_related_issue_count": "Related issues",
        "outcome_issue_comment_count": "Issue comments",
        "outcome_followup_commit_count": "Later commits",
        "outcome_followup_detail_changed_files": "Later files",
        "outcome_followup_detail_churn": "Later churn",
        "outcome_followup_detail_test_files": "Later files related to tests",
        "outcome_human_review_count": "Human reviews",
        "outcome_inline_review_comment_count": "Inline comments",
        "outcome_review_count": "Reviews",
        "outcome_request_changes_count": "Request changes",
    }

    row_h = 28
    svg = Svg(740, max(430, 128 + len(rows) * row_h + 54))
    left, top, width = 176, 74, 430
    svg.text(36, 32, "Component level workload predictability", size=16, weight="700")
    svg.text(36, 52, "Unseen repository AUCs from proposal time features; components remain visible rather than hidden in one score.", size=11, color=COLORS["gray"])
    svg.line(left, top + len(rows) * row_h + 6, left + width, top + len(rows) * row_h + 6, COLORS["dark"])
    for tick in [0.5, 0.6, 0.7, 0.8, 0.9, 1.0]:
        x = scale(tick, (0.5, 1.0), (left, left + width))
        svg.line(x, top - 8, x, top + len(rows) * row_h + 6, COLORS["light_gray"], 0.8)
        svg.text(x, top + len(rows) * row_h + 24, f"{tick:.1f}", size=9, anchor="middle", color=COLORS["gray"])
    for idx, (_, row) in enumerate(rows.iterrows()):
        y = top + idx * row_h
        x0 = scale(0.5, (0.5, 1.0), (left, left + width))
        x1 = scale(row["auc"], (0.5, 1.0), (left, left + width))
        svg.text(left - 10, y + 18, label_map.get(row["component"], row["component"]), size=11, anchor="end")
        svg.rect(x0, y + 5, max(1.0, x1 - x0), 16, COLORS["blue"])
        svg.text(x1 + 6, y + 18, f"{row['auc']:.3f}", size=10, color=COLORS["gray"])
    svg.text(left + width / 2, top + len(rows) * row_h + 44, "AUC", size=11, anchor="middle")

    path = figure_dir / "aidev_component_auc.svg"
    return save_publication_figure(svg, path)


def make_gate_error_figure(results_dir: Path, figure_dir: Path) -> Path:
    frame = pd.read_csv(results_dir / "aidev_gate_error_summary.csv")
    frame = frame[frame["split"].isin(["temporal", "repository_disjoint"])].copy()
    if frame.empty:
        raise ValueError("aidev_gate_error_summary.csv does not contain temporal or repository_disjoint rows.")

    split_labels = {
        "temporal": "Temporal",
        "repository_disjoint": "Unseen repository",
    }
    split_order = ["temporal", "repository_disjoint"]

    svg = Svg(760, 430)
    left, top, width, bar_h = 176, 98, 470, 58
    gap = 96
    svg.text(36, 32, "Gate error and routing composition", size=16, weight="700")
    svg.text(
        36,
        52,
        "Risk limit 0.10; repository shift leaves few high workload PRs accepted but increases low workload routing.",
        size=11,
        color=COLORS["gray"],
    )

    for idx, split in enumerate(split_order):
        rows = frame[frame["split"] == split].set_index("case_type")
        y = top + idx * (bar_h + gap)
        svg.text(left - 18, y + 34, split_labels[split], size=12, anchor="end", weight="700")
        svg.rect(left, y, width, bar_h, COLORS["light_gray"], stroke="#FFFFFF")
        x = left
        for case_type in CASE_ORDER:
            if case_type not in rows.index:
                continue
            share = float(rows.loc[case_type, "share_of_split"])
            n = int(rows.loc[case_type, "n"])
            segment_w = width * share
            svg.rect(x, y, segment_w, bar_h, CASE_COLORS[case_type], stroke="#FFFFFF")
            pct = f"{share * 100:.1f}%"
            label = CASE_LABELS[case_type]
            if segment_w >= 86:
                svg.text(x + segment_w / 2, y + 25, label, size=10, anchor="middle", weight="700", color="#FFFFFF")
                svg.text(x + segment_w / 2, y + 43, f"{pct}; n={n}", size=9, anchor="middle", color="#FFFFFF")
            elif segment_w >= 32:
                svg.text(x + segment_w / 2, y + 35, pct, size=9, anchor="middle", weight="700", color="#FFFFFF")
            x += segment_w

        svg.line(left, y + bar_h + 8, left + width, y + bar_h + 8, COLORS["dark"], 1.0)
        for tick in [0.0, 0.25, 0.5, 0.75, 1.0]:
            tx = scale(tick, (0, 1), (left, left + width))
            svg.line(tx, y + bar_h + 8, tx, y + bar_h + 14, COLORS["dark"], 1.0)
            svg.text(tx, y + bar_h + 29, f"{tick:.2f}", size=9, anchor="middle", color=COLORS["gray"])

    legend_x, legend_y = 90, 330
    for idx, case_type in enumerate(CASE_ORDER):
        row = idx // 2
        col = idx % 2
        x = legend_x + col * 270
        y = legend_y + row * 28
        svg.rect(x, y - 11, 14, 14, CASE_COLORS[case_type])
        svg.text(x + 22, y, CASE_LABELS[case_type], size=11)
    svg.text(
        90,
        396,
        "Labels are observational; controlled paired runs are needed for causal decision-error claims.",
        size=10,
        color=COLORS["gray"],
    )

    path = figure_dir / "aidev_gate_error_composition.svg"
    return save_publication_figure(svg, path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate editable SVG figures for the AIDev EMSE evidence package.")
    parser.add_argument("--results-dir", type=Path, default=RESULTS_DIR)
    parser.add_argument("--figure-dir", type=Path, default=DEFAULT_FIGURE_DIR)
    args = parser.parse_args()

    figure_dir = ensure_dir(args.figure_dir)
    paths = [
        make_frontier_figure(args.results_dir, figure_dir),
        make_baseline_figure(args.results_dir, figure_dir),
        make_component_figure(args.results_dir, figure_dir),
        make_gate_error_figure(args.results_dir, figure_dir),
    ]
    for path in paths:
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
