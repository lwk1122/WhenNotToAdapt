from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from certificate_diagnostics import (
    build_certificate_targets,
    certificate_feature_matrix,
    estimate_recovery_matrix,
    grouped_three_way_split,
    service_bin_labels,
    upper_quantile,
)
from common import (
    GOVERNANCE_MODES,
    MANIFEST_DIR,
    RESULTS_DIR,
    accuracy,
    auc_score,
    brier_score,
    clip_probabilities,
    ensure_dir,
    r2_score,
    ridge_fit,
    ridge_predict,
    write_json,
)
from structural_diagnostics import fit_state_compression, load_overlap


def mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.mean(np.abs(np.asarray(y_true, dtype=float) - np.asarray(y_pred, dtype=float))))


def rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.sqrt(np.mean((np.asarray(y_true, dtype=float) - np.asarray(y_pred, dtype=float)) ** 2)))


def corr(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    if len(y_true) < 2 or np.std(y_true) == 0 or np.std(y_pred) == 0:
        return float("nan")
    return float(np.corrcoef(y_true, y_pred)[0, 1])


def regression_rows(target: str, y_true: np.ndarray, y_pred: np.ndarray) -> list[dict]:
    return [
        {"target": target, "metric": "mae", "value": mae(y_true, y_pred)},
        {"target": target, "metric": "rmse", "value": rmse(y_true, y_pred)},
        {"target": target, "metric": "r2", "value": r2_score(y_true, y_pred)},
        {"target": target, "metric": "corr", "value": corr(y_true, y_pred)},
    ]


def binary_rows(target: str, y_true: np.ndarray, y_pred: np.ndarray) -> list[dict]:
    y_pred = clip_probabilities(y_pred)
    return [
        {"target": target, "metric": "auc", "value": auc_score(y_true, y_pred)},
        {"target": target, "metric": "brier", "value": brier_score(y_true, y_pred)},
        {"target": target, "metric": "accuracy", "value": accuracy(y_true, y_pred)},
    ]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate the semi-structured simulator primitives against held-out real trajectory proxies."
    )
    parser.add_argument("--manifest-dir", type=Path, default=MANIFEST_DIR)
    parser.add_argument("--output-dir", type=Path, default=RESULTS_DIR / "simulator_validation")
    parser.add_argument("--seed", type=int, default=37)
    args = parser.parse_args()

    output_dir = ensure_dir(args.output_dir)
    overlap = load_overlap(args.manifest_dir)
    _, overlap = fit_state_compression(overlap)
    certificate_path = RESULTS_DIR / "diagnostics" / "certificate_diagnostics.json"
    if certificate_path.exists():
        certificate_payload = json.loads(certificate_path.read_text(encoding="utf-8"))
        amp_anchor = float(certificate_payload["recovery_matrix"]["mean_future_bad_after_incorrect"])
    else:
        recovery_stats = estimate_recovery_matrix()
        amp_anchor = float(recovery_stats["mean_future_bad_after_incorrect"])
    frame = build_certificate_targets(overlap, amp_anchor)

    train_mask, cal_mask, test_mask = grouped_three_way_split(
        frame["instance_id"].tolist(),
        calibration_size=0.2,
        test_size=0.2,
        seed=args.seed,
    )
    train_df = frame.loc[train_mask].copy()
    cal_df = frame.loc[cal_mask].copy()
    test_df = frame.loc[test_mask].copy()

    x_train = certificate_feature_matrix(train_df)
    x_cal = certificate_feature_matrix(cal_df)
    x_test = certificate_feature_matrix(test_df)

    target_names = ["nominal_load_target", "recovery_load_target", "service_target"]
    weights = {
        name: ridge_fit(x_train, train_df[name].to_numpy(dtype=float), alpha=2.0)
        for name in target_names
    }
    failure_weights = ridge_fit(x_train, train_df["failure"].to_numpy(dtype=float), alpha=2.0)

    pred_cal = {name: ridge_predict(x_cal, weights[name]) for name in target_names}
    pred_test = {name: ridge_predict(x_test, weights[name]) for name in target_names}
    pred_failure_test = clip_probabilities(ridge_predict(x_test, failure_weights))

    test_df["pred_nominal_load"] = pred_test["nominal_load_target"]
    test_df["pred_recovery_load"] = np.maximum(0.0, pred_test["recovery_load_target"])
    test_df["pred_service"] = np.clip(pred_test["service_target"], 0.05, 1.0)
    test_df["pred_failure"] = pred_failure_test
    test_df["total_load_target"] = test_df["nominal_load_target"] + test_df["recovery_load_target"]
    test_df["pred_total_load"] = test_df["pred_nominal_load"] + test_df["pred_recovery_load"]

    metric_rows: list[dict] = []
    metric_rows.extend(binary_rows("failure", test_df["failure"].to_numpy(dtype=float), pred_failure_test))
    metric_rows.extend(
        regression_rows(
            "nominal_load",
            test_df["nominal_load_target"].to_numpy(dtype=float),
            test_df["pred_nominal_load"].to_numpy(dtype=float),
        )
    )
    metric_rows.extend(
        regression_rows(
            "recovery_load",
            test_df["recovery_load_target"].to_numpy(dtype=float),
            test_df["pred_recovery_load"].to_numpy(dtype=float),
        )
    )
    metric_rows.extend(
        regression_rows(
            "service",
            test_df["service_target"].to_numpy(dtype=float),
            test_df["pred_service"].to_numpy(dtype=float),
        )
    )
    metric_rows.extend(
        regression_rows(
            "total_load",
            test_df["total_load_target"].to_numpy(dtype=float),
            test_df["pred_total_load"].to_numpy(dtype=float),
        )
    )

    q_nominal = upper_quantile(cal_df["nominal_load_target"].to_numpy(dtype=float) - pred_cal["nominal_load_target"])
    q_recovery = upper_quantile(cal_df["recovery_load_target"].to_numpy(dtype=float) - pred_cal["recovery_load_target"])
    cal_service_bins, service_edges = service_bin_labels(cal_df)
    q_service_by_bin: dict[int, float] = {}
    for bin_id in sorted(cal_service_bins.unique().tolist()):
        mask = cal_service_bins == bin_id
        residuals = pred_cal["service_target"][mask] - cal_df.loc[mask, "service_target"].to_numpy(dtype=float)
        q_service_by_bin[int(bin_id)] = upper_quantile(residuals, alpha=0.05)
    global_q_service = upper_quantile(
        pred_cal["service_target"] - cal_df["service_target"].to_numpy(dtype=float),
        alpha=0.05,
    )
    test_service_bins, _ = service_bin_labels(test_df, reference_edges=service_edges)
    test_df["service_bin"] = test_service_bins

    calibration_rows = []
    for mode in GOVERNANCE_MODES:
        upper_total = (
            test_df["pred_nominal_load"].to_numpy(dtype=float)
            + q_nominal
            + mode.recovery_multiplier * np.maximum(0.0, test_df["pred_recovery_load"].to_numpy(dtype=float) + q_recovery)
        )
        actual_total = (
            test_df["nominal_load_target"].to_numpy(dtype=float)
            + mode.recovery_multiplier * test_df["recovery_load_target"].to_numpy(dtype=float)
        )
        service_q = np.asarray(
            [q_service_by_bin.get(int(bin_id), global_q_service) for bin_id in test_df["service_bin"].to_list()],
            dtype=float,
        )
        lower_service = mode.service_floor * np.maximum(0.05, test_df["pred_service"].to_numpy(dtype=float) - service_q)
        actual_service = mode.service_floor * test_df["service_target"].to_numpy(dtype=float)
        cert_headroom = lower_service - upper_total
        actual_headroom = actual_service - actual_total
        certified_positive = cert_headroom > 0
        actual_positive = actual_headroom > 0
        calibration_rows.append(
            {
                "mode": mode.name,
                "rows": int(len(test_df)),
                "load_violation_rate": float(np.mean(actual_total > upper_total)),
                "service_violation_rate": float(np.mean(actual_service < lower_service)),
                "certified_positive_rate": float(np.mean(certified_positive)),
                "actual_positive_rate": float(np.mean(actual_positive)),
                "certified_positive_precision": float(np.mean(actual_positive[certified_positive])) if certified_positive.any() else float("nan"),
                "certified_positive_recall": float(np.mean(certified_positive[actual_positive])) if actual_positive.any() else float("nan"),
                "headroom_sign_accuracy": float(np.mean(certified_positive == actual_positive)),
                "mean_certified_headroom": float(np.mean(cert_headroom)),
                "mean_actual_headroom": float(np.mean(actual_headroom)),
            }
        )

    metrics = pd.DataFrame(metric_rows)
    calibration = pd.DataFrame(calibration_rows)
    metrics.to_csv(output_dir / "simulator_validation_metrics.csv", index=False)
    calibration.to_csv(output_dir / "simulator_validation_calibration.csv", index=False)
    test_df.to_csv(output_dir / "simulator_validation_holdout_predictions.csv", index=False)

    payload = {
        "seed": args.seed,
        "train_rows": int(len(train_df)),
        "calibration_rows": int(len(cal_df)),
        "test_rows": int(len(test_df)),
        "metrics": metrics.to_dict("records"),
        "calibration": calibration.to_dict("records"),
        "q_nominal": float(q_nominal),
        "q_recovery": float(q_recovery),
        "q_service_global": float(global_q_service),
    }
    write_json(output_dir / "simulator_validation_summary.json", payload)

    print("Simulator validation complete.")
    print(metrics.to_string(index=False))
    print(calibration.to_string(index=False))


if __name__ == "__main__":
    main()
