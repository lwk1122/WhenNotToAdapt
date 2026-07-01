from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from common import (
    DATASET_DIR,
    GOVERNANCE_MODES,
    MANIFEST_DIR,
    RESULTS_DIR,
    bootstrap_interval,
    ensure_dir,
    grouped_train_test_split,
    manifest_paths,
    read_parquet,
    ridge_fit,
    ridge_predict,
    to_list,
    write_json,
)
from structural_diagnostics import fit_state_compression, load_overlap


STAGE_TYPES = ["clean", "unuseful", "incorrect"]
ALPHA = 0.10
SERVICE_ALPHA = 0.05


def failure_root_summary(trajectories: pd.DataFrame) -> dict:
    frame = trajectories.copy()
    frame["failure"] = 1.0 - frame["target"].astype(float)
    grouped = (
        frame.groupby("model_name")
        .agg(
            rows=("instance_id", "size"),
            failure_rate=("failure", "mean"),
            solved_rate=("target", "mean"),
            submit_rate=("exit_submit", "mean"),
            avg_steps=("trajectory_steps", "mean"),
            avg_eval_fails=("eval_fail_mentions", "mean"),
        )
        .reset_index()
        .sort_values("rows", ascending=False)
    )
    return {
        "overall_failure_rate": float(frame["failure"].mean()),
        "top_models": grouped.head(10).to_dict("records"),
    }


def estimate_recovery_matrix() -> dict:
    verified = read_parquet(DATASET_DIR / "CodeTraceBench" / "bench_manifest.verified.parquet")
    transition_counts = pd.DataFrame(0.0, index=STAGE_TYPES, columns=STAGE_TYPES)
    future_bad_counts = []
    difficulty_buckets: dict[str, list[float]] = {"easy": [], "medium": [], "hard": []}

    for row in verified.to_dict("records"):
        stage_map = {int(stage["stage_id"]): "clean" for stage in to_list(row.get("stages"))}
        for bad_stage in to_list(row.get("incorrect_stages")):
            stage_id = int(bad_stage.get("stage_id", -1))
            incorrect_steps = to_list(bad_stage.get("incorrect_step_ids"))
            unuseful_steps = to_list(bad_stage.get("unuseful_step_ids"))
            if incorrect_steps:
                stage_map[stage_id] = "incorrect"
            elif unuseful_steps:
                stage_map[stage_id] = "unuseful"

        ordered = [stage_map[int(stage["stage_id"])] for stage in sorted(to_list(row.get("stages")), key=lambda s: int(s["stage_id"]))]
        for left, right in zip(ordered[:-1], ordered[1:]):
            transition_counts.loc[left, right] += 1

        for idx, stage_type in enumerate(ordered):
            if stage_type == "incorrect":
                future_bad = sum(1 for later in ordered[idx + 1 :] if later != "clean")
                future_bad_counts.append(float(future_bad))
                difficulty_buckets.get((row.get("difficulty") or "").lower(), []).append(float(future_bad))

    transition_probs = transition_counts.div(transition_counts.sum(axis=1).replace(0, np.nan), axis=0).fillna(0.0)
    difficulty_summary = {}
    for difficulty, values in difficulty_buckets.items():
        if not values:
            continue
        lo, hi = bootstrap_interval(values, seed=13, rounds=300)
        difficulty_summary[difficulty] = {
            "mean_future_bad_after_incorrect": float(np.mean(values)),
            "ci95": [lo, hi],
        }

    return {
        "transition_counts": transition_counts.to_dict(orient="index"),
        "transition_probabilities": transition_probs.to_dict(orient="index"),
        "mean_future_bad_after_incorrect": float(np.mean(future_bad_counts)) if future_bad_counts else 0.0,
        "difficulty_summary": difficulty_summary,
    }


def uncertainty_shrinkage(trajectories: pd.DataFrame) -> dict:
    sizes = [100, 250, 500, 1000, 2500, 5000, 10000, len(trajectories)]
    sizes = sorted(set(size for size in sizes if size <= len(trajectories)))
    failures = (1.0 - trajectories["target"].astype(float)).to_numpy(dtype=float)
    results = []
    for size in sizes:
        sample = failures[:size]
        p_hat = float(sample.mean())
        radius = 1.96 * float(np.sqrt(max(p_hat * (1 - p_hat), 1e-6) / size))
        results.append({"sample_size": int(size), "failure_rate": p_hat, "radius": radius})
    return {"curve": results}


def grouped_three_way_split(groups: list[str], calibration_size: float = 0.2, test_size: float = 0.2, seed: int = 23) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    train_mask, temp_mask = grouped_train_test_split(groups, test_size=calibration_size + test_size, seed=seed)
    temp_groups = [group for group, keep in zip(groups, temp_mask) if keep]
    cal_submask, test_submask = grouped_train_test_split(temp_groups, test_size=test_size / (calibration_size + test_size), seed=seed + 1)

    calibration_mask = np.zeros(len(groups), dtype=bool)
    test_mask = np.zeros(len(groups), dtype=bool)
    temp_indices = np.flatnonzero(temp_mask)
    calibration_mask[temp_indices[cal_submask]] = True
    test_mask[temp_indices[test_submask]] = True
    return train_mask, calibration_mask, test_mask


def certificate_feature_matrix(frame: pd.DataFrame) -> np.ndarray:
    return np.column_stack(
        [
            frame["e_proxy"].to_numpy(dtype=float),
            frame["d_proxy"].to_numpy(dtype=float),
            frame["q_proxy"].to_numpy(dtype=float),
            np.log1p(frame["trajectory_steps"].to_numpy(dtype=float)),
            np.log1p(frame["eval_fail_mentions"].to_numpy(dtype=float)),
            frame["early_test_mentions"].to_numpy(dtype=float),
            frame["early_search_mentions"].to_numpy(dtype=float),
            frame["early_uncertainty_mentions"].to_numpy(dtype=float),
            frame["generated_patch_files"].to_numpy(dtype=float),
            frame["generated_patch_lines"].to_numpy(dtype=float) / 100.0,
        ]
    )


def upper_quantile(values: np.ndarray, alpha: float = ALPHA) -> float:
    if len(values) == 0:
        return 0.0
    return float(np.quantile(values, 1.0 - alpha, method="higher"))


def service_bin_labels(frame: pd.DataFrame, reference_edges: np.ndarray | None = None) -> tuple[pd.Series, np.ndarray]:
    values = frame["q_proxy"].to_numpy(dtype=float)
    if reference_edges is None:
        quantiles = np.quantile(values, [0.0, 1 / 3, 2 / 3, 1.0])
        edges = np.asarray(quantiles, dtype=float)
        for idx in range(1, len(edges)):
            if edges[idx] <= edges[idx - 1]:
                edges[idx] = edges[idx - 1] + 1e-6
    else:
        edges = np.asarray(reference_edges, dtype=float)
    labels = pd.cut(
        frame["q_proxy"],
        bins=edges,
        include_lowest=True,
        labels=False,
    )
    labels = labels.astype("Int64").fillna(len(edges) - 2).astype(int)
    return labels, edges


def build_certificate_targets(overlap: pd.DataFrame, amp_anchor: float) -> pd.DataFrame:
    frame = overlap.copy()
    eval_ratio = frame["eval_fail_mentions"].to_numpy(dtype=float) / max(float(frame["eval_fail_mentions"].quantile(0.95)), 1.0)
    step_ratio = frame["trajectory_steps"].to_numpy(dtype=float) / max(float(frame["trajectory_steps"].quantile(0.95)), 1.0)

    frame["nominal_load_target"] = (
        0.10
        + 0.16 * frame["d_proxy"]
        + 0.12 * frame["q_proxy"]
        + 0.04 * np.log1p(frame["trajectory_steps"])
        + 0.02 * frame["early_test_mentions"]
        + 0.015 * frame["generated_patch_files"]
    )
    frame["recovery_load_target"] = frame["failure"] * (
        0.08
        + 0.12 * amp_anchor
        + 0.08 * frame["d_proxy"]
        + 0.06 * eval_ratio
        + 0.04 * step_ratio
    )
    frame["service_target"] = np.clip(
        0.96
        - 0.0025 * np.minimum(frame["trajectory_steps"], 120.0)
        + 0.04 * frame["exit_submit"]
        - 0.02 * eval_ratio
        - 0.01 * frame["early_uncertainty_mentions"],
        0.05,
        1.0,
    )
    return frame


def certificate_validity(manifest_dir: Path) -> dict:
    overlap = load_overlap(manifest_dir)
    _, overlap = fit_state_compression(overlap)
    recovery_stats = estimate_recovery_matrix()
    amp_anchor = recovery_stats["mean_future_bad_after_incorrect"]
    frame = build_certificate_targets(overlap, amp_anchor)

    train_mask, cal_mask, test_mask = grouped_three_way_split(frame["instance_id"].tolist(), calibration_size=0.2, test_size=0.2, seed=23)
    train_df = frame.loc[train_mask].copy()
    cal_df = frame.loc[cal_mask].copy()
    test_df = frame.loc[test_mask].copy()

    x_train = certificate_feature_matrix(train_df)
    x_cal = certificate_feature_matrix(cal_df)
    x_test = certificate_feature_matrix(test_df)

    nominal_weights = ridge_fit(x_train, train_df["nominal_load_target"].to_numpy(dtype=float), alpha=2.0)
    recovery_weights = ridge_fit(x_train, train_df["recovery_load_target"].to_numpy(dtype=float), alpha=2.0)
    service_weights = ridge_fit(x_train, train_df["service_target"].to_numpy(dtype=float), alpha=2.0)

    cal_pred_nominal = ridge_predict(x_cal, nominal_weights)
    cal_pred_recovery = ridge_predict(x_cal, recovery_weights)
    cal_pred_service = ridge_predict(x_cal, service_weights)
    q_nominal = upper_quantile(cal_df["nominal_load_target"].to_numpy(dtype=float) - cal_pred_nominal)
    q_recovery = upper_quantile(cal_df["recovery_load_target"].to_numpy(dtype=float) - cal_pred_recovery)
    cal_service_bins, service_edges = service_bin_labels(cal_df)
    q_service_by_bin: dict[int, float] = {}
    for bin_id in sorted(cal_service_bins.unique().tolist()):
        mask = cal_service_bins == bin_id
        residuals = cal_pred_service[mask] - cal_df.loc[mask, "service_target"].to_numpy(dtype=float)
        q_service_by_bin[int(bin_id)] = upper_quantile(residuals, alpha=SERVICE_ALPHA)
    global_q_service = upper_quantile(cal_pred_service - cal_df["service_target"].to_numpy(dtype=float), alpha=SERVICE_ALPHA)

    test_df["pred_nominal_load"] = ridge_predict(x_test, nominal_weights)
    test_df["pred_recovery_load"] = ridge_predict(x_test, recovery_weights)
    test_df["pred_service"] = ridge_predict(x_test, service_weights)
    test_service_bins, _ = service_bin_labels(test_df, reference_edges=service_edges)
    test_df["upper_nominal_load"] = test_df["pred_nominal_load"] + q_nominal
    test_df["upper_recovery_load"] = np.maximum(0.0, test_df["pred_recovery_load"] + q_recovery)
    test_df["service_bin"] = test_service_bins
    test_df["q_service_local"] = test_df["service_bin"].map(q_service_by_bin).fillna(global_q_service)
    test_df["lower_service_base"] = np.maximum(0.05, test_df["pred_service"] - test_df["q_service_local"])

    mode_rows = []
    safe_set_sizes = []
    benchmark_safe_sizes = []
    predicted_nonempty = []
    benchmark_nonempty = []
    all_cert_headrooms = []
    for _, row in test_df.iterrows():
        cert_count = 0
        bench_count = 0
        for mode in GOVERNANCE_MODES:
            upper_total = float(row["upper_nominal_load"] + mode.recovery_multiplier * row["upper_recovery_load"])
            lower_service = float(np.clip(mode.service_floor * row["lower_service_base"], 0.05, 1.0))
            actual_total = float(row["nominal_load_target"] + mode.recovery_multiplier * row["recovery_load_target"])
            actual_service = float(np.clip(mode.service_floor * row["service_target"], 0.05, 1.0))
            cert_headroom = lower_service - upper_total
            actual_headroom = actual_service - actual_total
            cert_safe = cert_headroom > 0.0
            benchmark_safe = actual_headroom > 0.0
            cert_count += int(cert_safe)
            bench_count += int(benchmark_safe)
            all_cert_headrooms.append(cert_headroom)
            mode_rows.append(
                {
                    "instance_id": row["instance_id"],
                    "mode": mode.name,
                    "upper_total_load": upper_total,
                    "lower_service": lower_service,
                    "actual_total_load": actual_total,
                    "actual_service": actual_service,
                    "certified_headroom": cert_headroom,
                    "actual_headroom": actual_headroom,
                    "load_violation": float(actual_total > upper_total),
                    "service_violation": float(actual_service < lower_service),
                    "cert_safe": float(cert_safe),
                    "benchmark_safe": float(benchmark_safe),
                }
            )
        safe_set_sizes.append(cert_count)
        benchmark_safe_sizes.append(bench_count)
        predicted_nonempty.append(cert_count > 0)
        benchmark_nonempty.append(bench_count > 0)

    mode_frame = pd.DataFrame(mode_rows)
    mode_summary = (
        mode_frame.groupby("mode")
        .agg(
            load_violation_rate=("load_violation", "mean"),
            service_violation_rate=("service_violation", "mean"),
            cert_safe_rate=("cert_safe", "mean"),
            benchmark_safe_rate=("benchmark_safe", "mean"),
            mean_certified_headroom=("certified_headroom", "mean"),
            mean_actual_headroom=("actual_headroom", "mean"),
        )
        .reset_index()
    )

    theta_precision = float(
        np.mean([bench for pred, bench in zip(predicted_nonempty, benchmark_nonempty) if pred])
    ) if any(predicted_nonempty) else float("nan")
    theta_recall = float(
        np.mean([pred for pred, bench in zip(predicted_nonempty, benchmark_nonempty) if bench])
    ) if any(benchmark_nonempty) else float("nan")

    rho_curve = []
    theta_curve = []
    cal_indices = list(range(len(cal_df)))
    for size in [64, 128, 256, 384, len(cal_df)]:
        if size > len(cal_df):
            continue
        prefix = cal_indices[:size]
        prefix_nom = upper_quantile(cal_df["nominal_load_target"].to_numpy(dtype=float)[prefix] - cal_pred_nominal[prefix])
        prefix_rec = upper_quantile(cal_df["recovery_load_target"].to_numpy(dtype=float)[prefix] - cal_pred_recovery[prefix])
        prefix_bins = cal_service_bins.iloc[prefix] if isinstance(cal_service_bins, pd.Series) else cal_service_bins[prefix]
        prefix_q_service_by_bin: dict[int, float] = {}
        for bin_id in sorted(np.unique(np.asarray(prefix_bins, dtype=int)).tolist()):
            mask = np.asarray(prefix_bins, dtype=int) == bin_id
            residuals = cal_pred_service[prefix][mask] - cal_df["service_target"].to_numpy(dtype=float)[prefix][mask]
            prefix_q_service_by_bin[int(bin_id)] = upper_quantile(residuals, alpha=SERVICE_ALPHA)
        prefix_svc = float(np.mean(list(prefix_q_service_by_bin.values()))) if prefix_q_service_by_bin else global_q_service
        prefix_svc_max = float(np.max(list(prefix_q_service_by_bin.values()))) if prefix_q_service_by_bin else global_q_service
        rho_curve.append(
            {
                "calibration_size": int(size),
                "rho_nominal": prefix_nom,
                "rho_recovery": prefix_rec,
                "rho_service": prefix_svc,
                "rho_service_max": prefix_svc_max,
            }
        )

        cert_nonempty = []
        cert_sizes = []
        for _, row in test_df.iterrows():
            cert_count = 0
            for mode in GOVERNANCE_MODES:
                upper_total = float((row["pred_nominal_load"] + prefix_nom) + mode.recovery_multiplier * max(0.0, row["pred_recovery_load"] + prefix_rec))
                local_service_q = prefix_q_service_by_bin.get(int(row["service_bin"]), global_q_service)
                lower_service = float(np.clip(mode.service_floor * max(0.05, row["pred_service"] - local_service_q), 0.05, 1.0))
                cert_count += int((lower_service - upper_total) > 0.0)
            cert_nonempty.append(cert_count > 0)
            cert_sizes.append(cert_count)
        theta_curve.append(
            {
                "calibration_size": int(size),
                "theta_safe_nonempty_rate": float(np.mean(cert_nonempty)),
                "theta_safe_mean_size": float(np.mean(cert_sizes)),
            }
        )

    return {
        "train_rows": int(len(train_df)),
        "calibration_rows": int(len(cal_df)),
        "test_rows": int(len(test_df)),
        "alpha": ALPHA,
        "q_nominal": q_nominal,
        "q_recovery": q_recovery,
        "q_service": global_q_service,
        "q_service_by_bin": {str(key): value for key, value in q_service_by_bin.items()},
        "load_violation_rate": float(mode_frame["load_violation"].mean()),
        "service_violation_rate": float(mode_frame["service_violation"].mean()),
        "positive_headroom_rate": float(np.mean(predicted_nonempty)),
        "theta_safe_nonempty_rate": float(np.mean(predicted_nonempty)),
        "theta_safe_mean_size": float(np.mean(safe_set_sizes)),
        "benchmark_safe_nonempty_rate": float(np.mean(benchmark_nonempty)),
        "benchmark_safe_mean_size": float(np.mean(benchmark_safe_sizes)),
        "theta_safe_precision": theta_precision,
        "theta_safe_recall": theta_recall,
        "mean_certified_headroom": float(np.mean(all_cert_headrooms)),
        "rho_curve": rho_curve,
        "theta_safe_curve": theta_curve,
        "one_step_validity_by_mode": mode_summary.to_dict("records"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run certificate and recovery diagnostics for theory support.")
    parser.add_argument("--manifest-dir", type=Path, default=MANIFEST_DIR)
    parser.add_argument("--output-dir", type=Path, default=RESULTS_DIR / "diagnostics")
    args = parser.parse_args()

    output_dir = ensure_dir(args.output_dir)
    paths = manifest_paths(args.manifest_dir)
    trajectories = pd.read_csv(paths["swe_agent_trajectories"])

    payload = {
        "failure_root_summary": failure_root_summary(trajectories),
        "recovery_matrix": estimate_recovery_matrix(),
        "uncertainty_shrinkage": uncertainty_shrinkage(trajectories),
        "certificate_validity": certificate_validity(args.manifest_dir),
    }
    write_json(output_dir / "certificate_diagnostics.json", payload)
    print("Certificate diagnostics complete.")
    print(f"Overall failure rate: {payload['failure_root_summary']['overall_failure_rate']:.4f}")


if __name__ == "__main__":
    main()
