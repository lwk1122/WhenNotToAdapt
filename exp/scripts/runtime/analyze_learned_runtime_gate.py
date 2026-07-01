from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .analyze_runtime_pairs import analyze_pair, frame_to_markdown
from .run_lmstudio_executable_context_gate import TASKS as BASE_TASKS
from .run_lmstudio_executable_context_gate_extra import EXTRA_TASKS


DEFAULT_RESULT_PATHS = [
    Path("exp/results/emse_runtime/lmstudio_executable_context_gate_v1/runtime_task_results.csv"),
    Path("exp/results/emse_runtime/lmstudio_executable_context_gate_extra_v1/runtime_task_results.csv"),
]
DEFAULT_OUTPUT_DIR = Path("exp/results/emse_runtime/learned_runtime_gate_v1")
KEY_METRICS = ["success", "model_calls", "total_tokens", "latency_seconds"]

KEYWORDS = [
    "boundary",
    "cache",
    "case",
    "config",
    "default",
    "duplicate",
    "email",
    "empty",
    "endpoint",
    "flag",
    "flatten",
    "interval",
    "merge",
    "missing",
    "nested",
    "none",
    "null",
    "order",
    "pagination",
    "percent",
    "permission",
    "policy",
    "priority",
    "range",
    "retry",
    "round",
    "sort",
    "status",
    "threshold",
    "timezone",
    "unknown",
    "unhashable",
    "version",
    "whitespace",
    "zero",
]


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def task_lookup() -> dict[str, dict[str, Any]]:
    tasks = {}
    for current in [*BASE_TASKS, *EXTRA_TASKS]:
        tasks[str(current["instance_id"])] = current
    return tasks


def candidate_text(current: dict[str, Any]) -> str:
    return "\n".join(str(current["candidates"][key]) for key in ["A", "B", "C", "D"])


def pre_route_text(current: dict[str, Any]) -> str:
    return "\n".join([str(current["issue"]), str(current["buggy_code"]), candidate_text(current)])


def count_pattern(text: str, pattern: str) -> int:
    return len(re.findall(pattern, text))


def extract_features(current: dict[str, Any]) -> dict[str, float]:
    issue = str(current["issue"])
    buggy = str(current["buggy_code"])
    candidates = [str(current["candidates"][key]) for key in ["A", "B", "C", "D"]]
    full_text = pre_route_text(current).lower()
    candidate_lengths = np.array([len(value) for value in candidates], dtype=float)
    feature: dict[str, float] = {
        "issue_chars": float(len(issue)),
        "issue_words": float(len(re.findall(r"[A-Za-z_]+", issue))),
        "buggy_chars": float(len(buggy)),
        "candidate_chars_mean": float(np.mean(candidate_lengths)),
        "candidate_chars_std": float(np.std(candidate_lengths)),
        "candidate_chars_max": float(np.max(candidate_lengths)),
        "candidate_lines_mean": float(np.mean([len(value.splitlines()) for value in candidates])),
        "num_comparators": float(sum(full_text.count(op) for op in ["<=", ">=", "==", "<", ">"])),
        "num_truthiness_ops": float(full_text.count(" or ") + full_text.count(" if ") + full_text.count(" not ")),
        "num_index_ops": float(full_text.count("[0]") + full_text.count("[-1]") + full_text.count("[:")),
        "num_dict_ops": float(full_text.count(".get(") + full_text.count("setdefault") + full_text.count("update(")),
        "num_sort_ops": float(full_text.count("sorted(") + full_text.count(".sort(")),
        "num_split_ops": float(full_text.count(".split(") + full_text.count(".rsplit(")),
        "num_imports": float(full_text.count("import ")),
    }
    for word in KEYWORDS:
        feature[f"kw_{word}"] = float(word in full_text)
    for token, name in [
        ("setdefault", "has_setdefault"),
        (".get(", "has_dict_get"),
        (" or ", "has_or"),
        ("sorted(", "has_sorted"),
        (".split(", "has_split"),
        (".lower(", "has_lower"),
        (".strip(", "has_strip"),
        ("range(", "has_range"),
        ("round(", "has_round"),
        (" / ", "has_division"),
        ("set(", "has_set"),
    ]:
        feature[name] = float(token in full_text)
    return feature


def heuristic_score_from_features(row: pd.Series) -> float:
    positive_terms = [
        "kw_boundary",
        "kw_duplicate",
        "kw_email",
        "kw_empty",
        "kw_endpoint",
        "kw_flag",
        "kw_flatten",
        "kw_interval",
        "kw_merge",
        "kw_nested",
        "kw_none",
        "kw_order",
        "kw_pagination",
        "kw_percent",
        "kw_permission",
        "kw_policy",
        "kw_priority",
        "kw_range",
        "kw_round",
        "kw_sort",
        "kw_status",
        "kw_threshold",
        "kw_timezone",
        "kw_unknown",
        "kw_unhashable",
        "kw_version",
        "kw_whitespace",
        "kw_zero",
        "has_setdefault",
        "has_dict_get",
        "has_sorted",
        "has_split",
        "has_range",
        "has_round",
        "has_division",
    ]
    score = 0.0
    for term in positive_terms:
        if term in row:
            score += float(row[term])
    score += 0.02 * float(row.get("issue_words", 0.0))
    score += 0.002 * float(row.get("candidate_chars_std", 0.0))
    score += 0.05 * float(row.get("num_comparators", 0.0))
    score += 0.10 * float(row.get("num_dict_ops", 0.0))
    return float(score)


def load_base_frame(paths: list[Path]) -> pd.DataFrame:
    frames = []
    for path in paths:
        if not path.exists():
            raise FileNotFoundError(path)
        frame = pd.read_csv(path)
        frame["source_result_csv"] = str(path)
        frames.append(frame)
    combined = pd.concat(frames, ignore_index=True)
    keep = combined[combined["controller"].isin(["direct_low", "standard_full"])].copy()
    keep = keep.drop_duplicates(["instance_id", "controller"], keep="first")
    return keep


def make_wide(base: pd.DataFrame) -> pd.DataFrame:
    index_cols = ["instance_id"]
    value_cols = ["success", "model_calls", "prompt_tokens", "completion_tokens", "total_tokens", "latency_seconds"]
    pieces = []
    for controller in ["direct_low", "standard_full"]:
        sub = base[base["controller"] == controller][index_cols + value_cols + ["workload_risk"]].copy()
        sub = sub.rename(columns={col: f"{col}_{controller}" for col in value_cols})
        sub = sub.rename(columns={"workload_risk": f"workload_risk_{controller}"})
        pieces.append(sub.set_index("instance_id"))
    wide = pieces[0].join(pieces[1], how="inner").reset_index()
    wide["workload_risk"] = wide["workload_risk_direct_low"].fillna(wide["workload_risk_standard_full"])
    wide["full_beneficial"] = (
        pd.to_numeric(wide["success_standard_full"], errors="coerce")
        > pd.to_numeric(wide["success_direct_low"], errors="coerce")
    ).astype(int)
    wide["full_hurts"] = (
        pd.to_numeric(wide["success_standard_full"], errors="coerce")
        < pd.to_numeric(wide["success_direct_low"], errors="coerce")
    ).astype(int)
    return wide


def feature_matrix(instance_ids: list[str], tasks: dict[str, dict[str, Any]]) -> tuple[np.ndarray, list[str], pd.DataFrame]:
    rows = []
    for instance_id in instance_ids:
        current = tasks.get(instance_id)
        if current is None:
            raise KeyError(f"No task metadata found for {instance_id}")
        rows.append({"instance_id": instance_id, **extract_features(current)})
    frame = pd.DataFrame(rows)
    feature_names = [col for col in frame.columns if col != "instance_id"]
    return frame[feature_names].to_numpy(dtype=float), feature_names, frame


def standardize(train_x: np.ndarray, test_x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    mean = train_x.mean(axis=0)
    scale = train_x.std(axis=0)
    scale[scale == 0] = 1.0
    return (train_x - mean) / scale, (test_x - mean) / scale


def sigmoid(values: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(values, -30, 30)))


def fit_logistic(train_x: np.ndarray, train_y: np.ndarray, l2: float, steps: int, lr: float) -> np.ndarray:
    x = np.column_stack([np.ones(len(train_x)), train_x])
    y = train_y.astype(float)
    weights = np.zeros(x.shape[1], dtype=float)
    if len(np.unique(y)) < 2:
        prevalence = np.clip(float(y.mean()), 1e-4, 1.0 - 1e-4)
        weights[0] = math.log(prevalence / (1.0 - prevalence))
        return weights
    for _ in range(steps):
        pred = sigmoid(x @ weights)
        penalty = np.r_[0.0, weights[1:]]
        grad = (x.T @ (pred - y)) / len(y) + l2 * penalty / len(y)
        weights -= lr * grad
    return weights


def predict_logistic(weights: np.ndarray, x: np.ndarray) -> np.ndarray:
    x_aug = np.column_stack([np.ones(len(x)), x])
    return sigmoid(x_aug @ weights)


def route_stats(frame: pd.DataFrame, route_full: np.ndarray) -> dict[str, float]:
    route_full = np.asarray(route_full, dtype=bool)
    success = np.where(route_full, frame["success_standard_full"], frame["success_direct_low"]).astype(float)
    tokens = np.where(route_full, frame["total_tokens_standard_full"], frame["total_tokens_direct_low"]).astype(float)
    calls = np.where(route_full, frame["model_calls_standard_full"], frame["model_calls_direct_low"]).astype(float)
    latency = np.where(route_full, frame["latency_seconds_standard_full"], frame["latency_seconds_direct_low"]).astype(float)
    return {
        "success": float(np.mean(success)),
        "total_tokens": float(np.mean(tokens)),
        "model_calls": float(np.mean(calls)),
        "latency_seconds": float(np.mean(latency)),
        "full_share": float(np.mean(route_full)),
    }


def choose_threshold(train: pd.DataFrame, scores: np.ndarray, margin: float) -> tuple[float, str]:
    full_success = float(pd.to_numeric(train["success_standard_full"], errors="coerce").mean())
    candidates = sorted(set(float(score) for score in scores))
    thresholds = [max(candidates) + 1.0, *candidates, min(candidates) - 1.0]
    rows = []
    for threshold in thresholds:
        route_full = scores >= threshold
        stats = route_stats(train, route_full)
        rows.append({"threshold": threshold, **stats, "success_gap_vs_full": full_success - stats["success"]})
    feasible = [row for row in rows if row["success_gap_vs_full"] <= margin + 1e-12]
    if feasible:
        best = min(feasible, key=lambda row: (row["total_tokens"], -row["success"], row["full_share"]))
        return float(best["threshold"]), "min_tokens_within_margin"
    best = min(rows, key=lambda row: (row["success_gap_vs_full"], row["total_tokens"]))
    return float(best["threshold"]), "fallback_smallest_success_gap"


def crossfit_learned_gate(wide: pd.DataFrame, tasks: dict[str, dict[str, Any]], args: argparse.Namespace) -> pd.DataFrame:
    instance_ids = wide["instance_id"].astype(str).tolist()
    all_x, feature_names, feature_frame = feature_matrix(instance_ids, tasks)
    heuristic_scores = feature_frame.apply(heuristic_score_from_features, axis=1).to_numpy(dtype=float)
    labels = wide["full_beneficial"].to_numpy(dtype=float)
    records = []
    for test_idx, instance_id in enumerate(instance_ids):
        train_mask = np.ones(len(instance_ids), dtype=bool)
        train_mask[test_idx] = False
        if args.learner == "feature_score":
            train_scores = heuristic_scores[train_mask]
            test_score = float(heuristic_scores[test_idx])
        else:
            train_x_raw = all_x[train_mask]
            test_x_raw = all_x[[test_idx]]
            train_x, test_x = standardize(train_x_raw, test_x_raw)
            train_y = labels[train_mask]
            weights = fit_logistic(train_x, train_y, l2=args.l2, steps=args.steps, lr=args.lr)
            train_scores = predict_logistic(weights, train_x)
            test_score = float(predict_logistic(weights, test_x)[0])
        train_frame = wide.loc[train_mask].reset_index(drop=True)
        threshold, threshold_rule = choose_threshold(train_frame, train_scores, args.calibration_margin)
        route_full = bool(test_score >= threshold)
        source = "standard_full" if route_full else "direct_low"
        row = wide.iloc[test_idx]
        records.append(
            {
                "instance_id": instance_id,
                "learned_score": test_score,
                "threshold": threshold,
                "threshold_rule": threshold_rule,
                "route_full": int(route_full),
                "route": "learned_full_context" if route_full else "learned_minimal_context",
                "source_controller": source,
                "full_beneficial": int(row["full_beneficial"]),
                "full_hurts": int(row["full_hurts"]),
                "workload_risk_for_diagnostic_only": row["workload_risk"],
                "direct_low_success": int(row["success_direct_low"]),
                "standard_full_success": int(row["success_standard_full"]),
                "feature_count": len(feature_names),
                "learner": args.learner,
            }
        )
    pred = pd.DataFrame(records)
    return pred.merge(feature_frame, on="instance_id", how="left")


def make_learned_rows(base: pd.DataFrame, predictions: pd.DataFrame) -> pd.DataFrame:
    rows = []
    indexed = base.set_index(["instance_id", "controller"])
    for _, pred in predictions.iterrows():
        instance_id = str(pred["instance_id"])
        source = str(pred["source_controller"])
        row = indexed.loc[(instance_id, source)].copy()
        row["instance_id"] = instance_id
        row["controller"] = "learned_gate_loto"
        row["route"] = pred["route"]
        row["fallback_events"] = int(pred["route_full"])
        row["workload_risk"] = row.get("workload_risk", "")
        row["notes"] = json.dumps(
            {
                "crossfit": "leave_one_task_out",
                "source_controller": source,
                "learned_score": float(pred["learned_score"]),
                "threshold": float(pred["threshold"]),
                "threshold_rule": pred["threshold_rule"],
                "risk_tier_not_used_for_learning": pred["workload_risk_for_diagnostic_only"],
            },
            ensure_ascii=False,
        )
        rows.append(row)
    return pd.DataFrame(rows).reset_index(drop=True)


def controller_summary(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for controller, group in frame.groupby("controller", dropna=False):
        rows.append(
            {
                "controller": controller,
                "n": int(len(group)),
                "success_rate": float(pd.to_numeric(group["success"], errors="coerce").mean()),
                "mean_calls": float(pd.to_numeric(group["model_calls"], errors="coerce").mean()),
                "mean_total_tokens": float(pd.to_numeric(group["total_tokens"], errors="coerce").mean()),
                "mean_latency_s": float(pd.to_numeric(group["latency_seconds"], errors="coerce").mean()),
            }
        )
    return pd.DataFrame(rows).sort_values("controller").reset_index(drop=True)


def write_report(
    path: Path,
    summary: pd.DataFrame,
    learned_vs_full: pd.DataFrame,
    learned_vs_low: pd.DataFrame,
    predictions: pd.DataFrame,
    result_paths: list[Path],
    args: argparse.Namespace,
) -> None:
    route_counts = predictions["route"].value_counts().to_dict()
    full_needed = int(predictions["full_beneficial"].sum())
    routed_full_needed = int(((predictions["full_beneficial"] == 1) & (predictions["route_full"] == 1)).sum())
    lines = [
        "# Learned Runtime Gate Analysis",
        "",
        "This analysis evaluates a learned pre-routing gate with leave-one-task-out cross-fitting. Each held-out task is routed using a score and threshold learned from the other tasks only. The diagnostic risk tier is not used as a feature.",
        "",
        "## Inputs",
        "",
    ]
    lines.extend(f"- `{path}`" for path in result_paths)
    lines.extend(
        [
            "",
            "## Learned Gate Routing",
            "",
            f"- Tasks: {len(predictions)}",
            f"- Full-beneficial tasks in observed paired branches: {full_needed}",
            f"- Full-beneficial tasks routed to full context: {routed_full_needed}",
            f"- Route counts: `{json.dumps(route_counts, sort_keys=True)}`",
            f"- Training calibration margin used for threshold selection: {args.calibration_margin:.3f}",
            f"- Evaluation non-inferiority margin: {args.success_margin:.3f}",
            f"- Learner: `{args.learner}`",
            "",
            "## Controller Summary",
            "",
            frame_to_markdown(summary),
            "",
            "## Learned Gate vs Full Context",
            "",
            frame_to_markdown(learned_vs_full),
            "",
            "## Learned Gate vs Low Context",
            "",
            frame_to_markdown(learned_vs_low),
            "",
            "## Interpretation Guardrails",
            "",
            "- The learned gate uses pre-routing issue, buggy-code, and candidate-code features only.",
            "- The held-out route for each task is produced by leave-one-task-out cross-fitting.",
            "- This remains a controlled static-candidate code repair setting, not open-ended repository deployment.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze a learned pre-routing runtime gate.")
    parser.add_argument("--result-paths", type=Path, nargs="+", default=DEFAULT_RESULT_PATHS)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--success-margin", type=float, default=0.10)
    parser.add_argument("--calibration-margin", type=float, default=0.05)
    parser.add_argument("--bootstrap-rounds", type=int, default=2000)
    parser.add_argument("--ci-alpha", type=float, default=0.05)
    parser.add_argument("--seed", type=int, default=23)
    parser.add_argument("--l2", type=float, default=1.0)
    parser.add_argument("--steps", type=int, default=1200)
    parser.add_argument("--lr", type=float, default=0.15)
    parser.add_argument("--learner", choices=["logistic", "feature_score"], default="logistic")
    args = parser.parse_args()

    output_dir = ensure_dir(args.output_dir)
    tasks = task_lookup()
    base = load_base_frame(args.result_paths)
    wide = make_wide(base)
    predictions = crossfit_learned_gate(wide, tasks, args)
    learned_rows = make_learned_rows(base, predictions)
    combined = pd.concat([base, learned_rows], ignore_index=True)
    # Include predefined gate rows from the source CSVs for side-by-side diagnostics when present.
    source_frames = [pd.read_csv(path) for path in args.result_paths]
    source_all = pd.concat(source_frames, ignore_index=True)
    predefined = source_all[source_all["controller"].isin(["context_gate_medium_high", "context_gate_high_only"])].copy()
    if not predefined.empty:
        combined = pd.concat([combined, predefined], ignore_index=True)

    predictions.to_csv(output_dir / "learned_gate_crossfit_predictions.csv", index=False)
    combined.to_csv(output_dir / "learned_runtime_task_results.csv", index=False)
    summary = controller_summary(combined)
    summary.to_csv(output_dir / "learned_gate_controller_summary.csv", index=False)

    learned_vs_full, learned_vs_full_summary = analyze_pair(
        combined,
        "learned_gate_loto",
        "standard_full",
        KEY_METRICS,
        args.success_margin,
        min_publication_pairs=30,
        ci_alpha=args.ci_alpha,
        bootstrap_rounds=args.bootstrap_rounds,
        seed=args.seed,
    )
    learned_vs_low, learned_vs_low_summary = analyze_pair(
        combined,
        "learned_gate_loto",
        "direct_low",
        KEY_METRICS,
        args.success_margin,
        min_publication_pairs=30,
        ci_alpha=args.ci_alpha,
        bootstrap_rounds=args.bootstrap_rounds,
        seed=args.seed + 101,
    )
    learned_vs_full.to_csv(output_dir / "learned_gate_vs_full_metrics.csv", index=False)
    learned_vs_low.to_csv(output_dir / "learned_gate_vs_low_metrics.csv", index=False)
    pd.DataFrame([learned_vs_full_summary]).to_csv(output_dir / "learned_gate_vs_full_summary.csv", index=False)
    pd.DataFrame([learned_vs_low_summary]).to_csv(output_dir / "learned_gate_vs_low_summary.csv", index=False)

    write_report(
        output_dir / "learned_runtime_gate_report.md",
        summary,
        learned_vs_full,
        learned_vs_low,
        predictions,
        args.result_paths,
        args,
    )
    (output_dir / "learned_runtime_gate_summary.json").write_text(
        json.dumps(
            {
                "n_tasks": int(predictions.shape[0]),
                "full_beneficial_tasks": int(predictions["full_beneficial"].sum()),
                "full_beneficial_routed_full": int(((predictions["full_beneficial"] == 1) & (predictions["route_full"] == 1)).sum()),
                "learned_vs_full": learned_vs_full_summary,
                "learned_vs_low": learned_vs_low_summary,
                "result_paths": [str(path) for path in args.result_paths],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Wrote learned runtime gate report to {output_dir / 'learned_runtime_gate_report.md'}")


if __name__ == "__main__":
    main()
