from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from .common import RESULTS_DIR, ensure_dir, write_json
from .evaluate_workload_gate import (
    CATEGORICAL_FEATURES,
    NUMERIC_FEATURES,
    decision_metrics,
    existing_columns,
    leave_one_agent_splits,
    make_model,
    repository_disjoint_split,
    safe_auc,
    safe_average_precision,
    temporal_split,
    threshold_for_risk_budget,
)


@dataclass
class ScoreBundle:
    name: str
    calibration_scores: np.ndarray
    test_scores: np.ndarray
    features: str


def prepare_frame(path: Path, target_col: str, workload_col: str) -> pd.DataFrame:
    frame = pd.read_csv(path)
    frame = frame.dropna(subset=[target_col, workload_col]).copy()
    for col in existing_columns(frame, NUMERIC_FEATURES):
        frame[col] = pd.to_numeric(frame[col], errors="coerce")
    for col in existing_columns(frame, CATEGORICAL_FEATURES):
        frame[col] = frame[col].fillna("").astype(str)
    return frame


def fit_logistic_scores(
    name: str,
    train: pd.DataFrame,
    calibration: pd.DataFrame,
    test: pd.DataFrame,
    train_high: pd.Series,
    numeric_features: list[str],
    categorical_features: list[str],
    sample_weight: np.ndarray | None = None,
) -> ScoreBundle | None:
    features = numeric_features + categorical_features
    if not features:
        return None
    if train_high.nunique(dropna=False) < 2:
        return None
    model = make_model(numeric_features, categorical_features)
    fit_kwargs = {"classifier__sample_weight": sample_weight} if sample_weight is not None else {}
    model.fit(train[features], train_high, **fit_kwargs)
    return ScoreBundle(
        name=name,
        calibration_scores=model.predict_proba(calibration[features])[:, 1],
        test_scores=model.predict_proba(test[features])[:, 1],
        features=",".join(features),
    )


def workload_severity_weights(train: pd.DataFrame, train_high: pd.Series, workload_col: str) -> np.ndarray:
    workload = pd.to_numeric(train[workload_col], errors="coerce").fillna(0.0).clip(lower=0.0)
    severity = np.log1p(workload).to_numpy(dtype=float)
    high = train_high.to_numpy(dtype=bool)
    weights = np.ones(len(train), dtype=float)
    if not high.any():
        return weights
    positive_severity = severity[high]
    scale = float(np.quantile(positive_severity, 0.75))
    if scale <= 1e-12:
        return weights
    weights[high] = 1.0 + np.clip(positive_severity / scale, 0.0, 4.0)
    return weights


def zscore_from_train(train_values: pd.Series, values: pd.Series) -> pd.Series:
    train_numeric = pd.to_numeric(train_values, errors="coerce").fillna(0.0)
    numeric = pd.to_numeric(values, errors="coerce").fillna(0.0)
    mean = float(train_numeric.mean())
    std = float(train_numeric.std(ddof=0))
    if std <= 1e-12:
        return pd.Series(np.zeros(len(values), dtype=float), index=values.index)
    return ((numeric - mean) / std).clip(lower=-3, upper=3)


def simple_text_scores(train: pd.DataFrame, calibration: pd.DataFrame, test: pd.DataFrame) -> ScoreBundle:
    columns = [
        "feature_title_chars",
        "feature_body_chars",
        "feature_title_mentions_test",
        "feature_body_mentions_test",
        "feature_body_mentions_fix",
    ]

    def score(frame: pd.DataFrame) -> pd.Series:
        out = pd.Series(np.zeros(len(frame), dtype=float), index=frame.index)
        for col in columns:
            if col in train.columns and col in frame.columns:
                out += zscore_from_train(train[col], frame[col])
        return out

    return ScoreBundle(
        name="simple_text_threshold",
        calibration_scores=score(calibration).to_numpy(dtype=float),
        test_scores=score(test).to_numpy(dtype=float),
        features=",".join([col for col in columns if col in train.columns]),
    )


def smoothed_group_rate(train: pd.DataFrame, train_high: pd.Series, columns: list[str], alpha: float = 20.0) -> dict[tuple[str, str], float]:
    prior = float(train_high.mean())
    rates: dict[tuple[str, str], float] = {}
    for col in columns:
        if col not in train.columns:
            continue
        temp = pd.DataFrame({"group": train[col].fillna("").astype(str), "high": train_high.astype(float)})
        grouped = temp.groupby("group", dropna=False)["high"].agg(["sum", "count"])
        for group, row in grouped.iterrows():
            rates[(col, str(group))] = float((row["sum"] + alpha * prior) / (row["count"] + alpha))
    return rates


def categorical_prior_scores(
    train: pd.DataFrame,
    calibration: pd.DataFrame,
    test: pd.DataFrame,
    train_high: pd.Series,
) -> ScoreBundle:
    columns = [col for col in ["agent", "feature_task_type", "repo_language"] if col in train.columns]
    rates = smoothed_group_rate(train, train_high, columns)
    prior = float(train_high.mean())

    def score(frame: pd.DataFrame) -> np.ndarray:
        if not columns:
            return np.full(len(frame), prior, dtype=float)
        values = np.zeros((len(frame), len(columns)), dtype=float)
        for idx, col in enumerate(columns):
            groups = frame[col].fillna("").astype(str)
            values[:, idx] = [rates.get((col, group), prior) for group in groups]
        return values.mean(axis=1)

    return ScoreBundle(
        name="categorical_prior",
        calibration_scores=score(calibration),
        test_scores=score(test),
        features=",".join(columns) if columns else "intercept",
    )


def uncertainty_only_scores(base: ScoreBundle) -> ScoreBundle:
    def uncertainty(scores: np.ndarray) -> np.ndarray:
        return 1.0 - np.minimum(np.abs(scores - 0.5) * 2.0, 1.0)

    return ScoreBundle(
        name="selective_uncertainty_only",
        calibration_scores=uncertainty(base.calibration_scores),
        test_scores=uncertainty(base.test_scores),
        features=f"{base.features};score=prediction_uncertainty_only",
    )


def score_bundles(
    train: pd.DataFrame,
    calibration: pd.DataFrame,
    test: pd.DataFrame,
    train_high: pd.Series,
    workload_col: str,
) -> list[ScoreBundle]:
    numeric = existing_columns(train, NUMERIC_FEATURES)
    categorical = existing_columns(train, CATEGORICAL_FEATURES)
    bundles: list[ScoreBundle] = []

    all_feature_logistic = fit_logistic_scores("logistic_all_features", train, calibration, test, train_high, numeric, categorical)
    if all_feature_logistic is not None:
        bundles.append(all_feature_logistic)
        bundles.append(uncertainty_only_scores(all_feature_logistic))

    cost_sensitive_weights = workload_severity_weights(train, train_high, workload_col)
    cost_sensitive_logistic = fit_logistic_scores(
        "cost_sensitive_workload_logistic",
        train,
        calibration,
        test,
        train_high,
        numeric,
        categorical,
        sample_weight=cost_sensitive_weights,
    )
    if cost_sensitive_logistic is not None:
        cost_sensitive_logistic.features = f"{cost_sensitive_logistic.features};positive_sample_weight=1+clipped_log_workload_q75"
        bundles.append(cost_sensitive_logistic)

    no_agent_categorical = [col for col in categorical if col != "agent"]
    no_agent_logistic = fit_logistic_scores("logistic_no_agent", train, calibration, test, train_high, numeric, no_agent_categorical)
    if no_agent_logistic is not None:
        bundles.append(no_agent_logistic)

    bundles.append(categorical_prior_scores(train, calibration, test, train_high))
    bundles.append(simple_text_scores(train, calibration, test))
    return bundles


def evaluate_bundle(
    split_name: str,
    scorer: ScoreBundle,
    train: pd.DataFrame,
    calibration: pd.DataFrame,
    test: pd.DataFrame,
    target_col: str,
    workload_col: str,
    high_quantile: float,
    high_threshold: float,
    cal_high: pd.Series,
    test_high: pd.Series,
    accept_rates: list[float],
    risk_budgets: list[float],
) -> list[dict]:
    base = {
        "split": split_name,
        "baseline": scorer.name,
        "train_rows": int(len(train)),
        "calibration_rows": int(len(calibration)),
        "test_rows": int(len(test)),
        "target": target_col,
        "workload": workload_col,
        "high_workload_quantile": high_quantile,
        "high_workload_threshold": high_threshold,
        "test_auc": safe_auc(test_high, scorer.test_scores),
        "test_average_precision": safe_average_precision(test_high, scorer.test_scores),
        "features": scorer.features,
    }
    rows = []
    for accept_rate in accept_rates:
        threshold = float(np.quantile(scorer.calibration_scores, max(min(accept_rate, 1.0), 0.0)))
        row = {
            **base,
            "selector": "fixed_acceptance",
            "selector_value": accept_rate,
            "score_threshold": threshold,
        }
        row.update(decision_metrics("calibration", scorer.calibration_scores, cal_high, calibration[workload_col], threshold))
        row.update(decision_metrics("test", scorer.test_scores, test_high, test[workload_col], threshold))
        rows.append(row)

    for budget in risk_budgets:
        threshold, cal_acceptance, cal_risk = threshold_for_risk_budget(scorer.calibration_scores, cal_high, budget)
        row = {
            **base,
            "selector": "calibration_risk_budget",
            "selector_value": budget,
            "score_threshold": threshold,
            "calibrated_acceptance_target": cal_acceptance,
            "calibrated_accepted_high_rate": cal_risk,
        }
        row.update(decision_metrics("calibration", scorer.calibration_scores, cal_high, calibration[workload_col], threshold))
        row.update(decision_metrics("test", scorer.test_scores, test_high, test[workload_col], threshold))
        rows.append(row)

    return rows


def evaluate_split(
    split_name: str,
    train: pd.DataFrame,
    calibration: pd.DataFrame,
    test: pd.DataFrame,
    target_col: str,
    workload_col: str,
    high_quantile: float,
    accept_rates: list[float],
    risk_budgets: list[float],
) -> list[dict]:
    high_threshold = float(train[target_col].quantile(high_quantile))
    train_high = train[target_col] >= high_threshold
    cal_high = calibration[target_col] >= high_threshold
    test_high = test[target_col] >= high_threshold
    rows = []
    for scorer in score_bundles(train, calibration, test, train_high, workload_col):
        rows.extend(
            evaluate_bundle(
                split_name,
                scorer,
                train,
                calibration,
                test,
                target_col,
                workload_col,
                high_quantile,
                high_threshold,
                cal_high,
                test_high,
                accept_rates,
                risk_budgets,
            )
        )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare AIDev workload-gate baselines under the same calibration protocol.")
    parser.add_argument("--features", type=Path, default=RESULTS_DIR / "aidev_pr_level_features.csv")
    parser.add_argument("--output-dir", type=Path, default=RESULTS_DIR)
    parser.add_argument("--target", default="outcome_downstream_workload_log")
    parser.add_argument("--workload", default="outcome_downstream_workload_raw")
    parser.add_argument("--high-workload-quantile", type=float, default=0.80)
    parser.add_argument("--accept-rates", nargs="*", type=float, default=[0.2, 0.4, 0.6, 0.8])
    parser.add_argument("--risk-budgets", nargs="*", type=float, default=[0.05, 0.10, 0.15])
    parser.add_argument("--include-agent-splits", action="store_true")
    parser.add_argument("--min-agent-test-rows", type=int, default=300)
    parser.add_argument("--seed", type=int, default=23)
    args = parser.parse_args()

    frame = prepare_frame(args.features, args.target, args.workload)
    split_specs: list[tuple[str, pd.DataFrame, pd.DataFrame, pd.DataFrame]] = [
        ("temporal", *temporal_split(frame)),
        ("repository_disjoint", *repository_disjoint_split(frame, args.seed)),
    ]
    if args.include_agent_splits:
        split_specs.extend(leave_one_agent_splits(frame, args.min_agent_test_rows))

    rows = []
    for split_name, train, calibration, test in split_specs:
        rows.extend(
            evaluate_split(
                split_name,
                train,
                calibration,
                test,
                args.target,
                args.workload,
                args.high_workload_quantile,
                args.accept_rates,
                args.risk_budgets,
            )
        )

    output_dir = ensure_dir(args.output_dir)
    out = pd.DataFrame(rows)
    csv_path = output_dir / "aidev_gate_baseline_summary.csv"
    out.to_csv(csv_path, index=False)
    write_json(
        output_dir / "aidev_gate_baseline_summary.json",
        {
            "output_csv": str(csv_path),
            "rows": int(len(out)),
            "splits": sorted(out["split"].unique().tolist()),
            "baselines": sorted(out["baseline"].unique().tolist()),
            "selectors": sorted(out["selector"].unique().tolist()),
        },
    )
    print(f"Wrote gate baseline summary to {csv_path}")


if __name__ == "__main__":
    main()
