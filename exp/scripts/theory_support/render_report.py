from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from common import RESULTS_DIR


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def fmt(value: float, digits: int = 4) -> str:
    return f"{value:.{digits}f}"


def markdown_table(frame: pd.DataFrame) -> str:
    header = "| " + " | ".join(frame.columns) + " |"
    separator = "| " + " | ".join(["---"] * len(frame.columns)) + " |"
    rows = ["| " + " | ".join(str(value) for value in row) + " |" for row in frame.astype(object).itertuples(index=False, name=None)]
    return "\n".join([header, separator, *rows])


def benchmark_lookup(frame: pd.DataFrame, dataset: str, controller: str) -> pd.Series:
    return frame[(frame["dataset"] == dataset) & (frame["controller"] == controller)].iloc[0]


def main() -> None:
    parser = argparse.ArgumentParser(description="Render a consolidated markdown report from theory-support experiment outputs.")
    parser.add_argument("--results-dir", type=Path, default=RESULTS_DIR)
    parser.add_argument("--output", type=Path, default=RESULTS_DIR / "EXPERIMENT_RESULTS.md")
    args = parser.parse_args()

    manifest_summary = load_json(args.results_dir / "manifests" / "manifest_summary.json")
    structural = load_json(args.results_dir / "diagnostics" / "structural_diagnostics.json")
    certificate = load_json(args.results_dir / "diagnostics" / "certificate_diagnostics.json")
    distribution = load_json(args.results_dir / "diagnostics" / "distributional_diagnostics.json")
    benchmark = pd.read_csv(args.results_dir / "benchmark" / "controller_results.csv")
    benchmark_meta = load_json(args.results_dir / "benchmark" / "controller_results.json")
    online_meta = load_json(args.results_dir / "online_simulator" / "online_simulator_summary.json")
    online_summary = pd.read_csv(args.results_dir / "online_simulator" / "online_simulator_summary.csv")
    online_pairwise = pd.read_csv(args.results_dir / "online_simulator" / "online_simulator_pairwise.csv")
    camc_pairwise = pd.read_csv(args.results_dir / "online_simulator" / "online_simulator_camc_pairwise.csv")
    camc_by_slack = pd.read_csv(args.results_dir / "online_simulator" / "online_simulator_camc_activation_by_slack.csv")
    camc_by_shift = pd.read_csv(args.results_dir / "online_simulator" / "online_simulator_camc_activation_by_shift.csv")
    safety_objectives = pd.read_csv(args.results_dir / "online_simulator" / "online_simulator_safety_objectives.csv")
    headroom_calibration = pd.read_csv(args.results_dir / "online_simulator" / "online_simulator_headroom_calibration.csv")
    headroom_support = pd.read_csv(args.results_dir / "online_simulator" / "online_simulator_headroom_theory_support.csv")
    positive_headroom_drift = pd.read_csv(args.results_dir / "online_simulator" / "online_simulator_positive_headroom_drift.csv")
    family_barrier = pd.read_csv(args.results_dir / "online_simulator" / "online_simulator_family_barrier.csv")
    controller_contrasts = pd.read_csv(args.results_dir / "online_simulator" / "online_simulator_controller_contrasts.csv")
    simulator_validation_metrics = pd.read_csv(args.results_dir / "simulator_validation" / "simulator_validation_metrics.csv")
    simulator_validation_calibration = pd.read_csv(args.results_dir / "simulator_validation" / "simulator_validation_calibration.csv")
    shadow_dir = args.results_dir / "shadow_runtime_sphinx8_lm_pilot"
    shadow_summary = pd.read_csv(shadow_dir / "shadow_runtime_summary.csv")
    shadow_pairwise = pd.read_csv(shadow_dir / "shadow_runtime_pairwise.csv")

    dataset_rows = pd.DataFrame(
        [
            {"dataset": key, "rows": value}
            for key, value in manifest_summary.items()
            if key != "output_dir"
        ]
    )

    structural_rows = pd.DataFrame(
        [
            {
                "metric": "Reduced AUC",
                "value": fmt(structural["state_compression"]["reduced_model"]["auc"]),
            },
            {
                "metric": "Full AUC",
                "value": fmt(structural["state_compression"]["full_model"]["auc"]),
            },
            {
                "metric": "AUC gain (full - reduced)",
                "value": fmt(structural["state_compression"]["full_minus_reduced_auc"]),
            },
            {
                "metric": "Reduced-state support",
                "value": str(structural["state_compression"]["reduced_state_support"]),
            },
            {
                "metric": "Canonical context AUC",
                "value": fmt(structural["context_atoms"]["canonical_additive_model"]["auc"]),
            },
            {
                "metric": "Context strong-positive recall",
                "value": fmt(structural["context_atoms"]["strong_positive_recall_top2"]),
            },
            {
                "metric": "Context over-internalization rate",
                "value": fmt(structural["context_atoms"]["overinternalization_rate_top2"]),
            },
            {
                "metric": "Top-2 mean regret",
                "value": fmt(structural["context_atoms"]["mean_regret_top2"], digits=6),
            },
            {
                "metric": "Top-2 exact match",
                "value": fmt(structural["context_atoms"]["exact_match_rate_top2"]),
            },
            {
                "metric": "Verification-boundary violation (e)",
                "value": fmt(structural["verification_boundary"]["monotonicity_violation_rate_e"], digits=6),
            },
            {
                "metric": "Verification-boundary violation (q)",
                "value": fmt(structural["verification_boundary"]["monotonicity_violation_rate_q"], digits=6),
            },
            {
                "metric": "Far-inside verify miss rate",
                "value": fmt(structural["verification_boundary"]["conservative_miss_rate_far_inside"], digits=6),
            },
            {
                "metric": "Far-outside verify rate",
                "value": fmt(structural["verification_boundary"]["conservative_verify_rate_far_outside"]),
            },
            {
                "metric": "Continuous-effort mean",
                "value": fmt(structural["verification_boundary"]["continuous_effort_mean"]),
            },
            {
                "metric": "Continuous-effort violation (q)",
                "value": fmt(structural["verification_boundary"]["continuous_effort_violation_rate_q"]),
            },
            {
                "metric": "Counterfactual optimal-effort mean",
                "value": fmt(structural["verification_boundary"]["counterfactual_optimal_effort_mean"]),
            },
            {
                "metric": "Counterfactual interior-optimum share",
                "value": fmt(structural["verification_boundary"]["counterfactual_interior_optimum_share"]),
            },
            {
                "metric": "Counterfactual rule exact match",
                "value": fmt(structural["verification_boundary"]["counterfactual_rule_exact_match_rate"]),
            },
            {
                "metric": "Counterfactual rule one-step match",
                "value": fmt(structural["verification_boundary"]["counterfactual_rule_one_step_match_rate"]),
            },
            {
                "metric": "Counterfactual rule mean regret",
                "value": fmt(structural["verification_boundary"]["counterfactual_rule_mean_regret"], digits=6),
            },
            {
                "metric": "Counterfactual violation (q)",
                "value": fmt(structural["verification_boundary"]["counterfactual_monotonicity_violation_rate_q"]),
            },
            {
                "metric": "Governance monotonicity violation rate",
                "value": fmt(structural["governance_headroom"]["pairwise_monotonicity_violation_rate"], digits=6),
            },
        ]
    )

    certificate_rows = pd.DataFrame(
        [
            {
                "metric": "Overall trajectory failure rate",
                "value": fmt(certificate["failure_root_summary"]["overall_failure_rate"]),
            },
            {
                "metric": "Mean future bad stages after incorrect",
                "value": fmt(certificate["recovery_matrix"]["mean_future_bad_after_incorrect"]),
            },
            {
                "metric": "Load violation rate",
                "value": fmt(certificate["certificate_validity"]["load_violation_rate"]),
            },
            {
                "metric": "Service violation rate",
                "value": fmt(certificate["certificate_validity"]["service_violation_rate"]),
            },
            {
                "metric": "Theta-safe nonempty rate",
                "value": fmt(certificate["certificate_validity"]["positive_headroom_rate"]),
            },
            {
                "metric": "Theta-safe mean size",
                "value": fmt(certificate["certificate_validity"]["theta_safe_mean_size"]),
            },
            {
                "metric": "Benchmark-safe nonempty rate",
                "value": fmt(certificate["certificate_validity"]["benchmark_safe_nonempty_rate"]),
            },
            {
                "metric": "Theta-safe precision",
                "value": fmt(certificate["certificate_validity"]["theta_safe_precision"]),
            },
            {
                "metric": "Theta-safe recall",
                "value": fmt(certificate["certificate_validity"]["theta_safe_recall"]),
            },
        ]
    )

    profile_frame = pd.read_csv(args.results_dir / "diagnostics" / "dataset_profiles.csv")
    profile_rows = profile_frame[
        [
            "dataset",
            "rows",
            "mean_abs_feature_shift_vs_test",
            "high_risk_share",
            "g0_safe_rate",
            "g3_safe_rate",
        ]
    ].copy()
    for column in ["mean_abs_feature_shift_vs_test", "high_risk_share", "g0_safe_rate", "g3_safe_rate"]:
        profile_rows[column] = profile_rows[column].map(fmt)

    benchmark_rows = benchmark[
        [
            "dataset",
            "controller",
            "success_rate",
            "discounted_cost",
            "avg_workload",
            "overload_rate",
            "verification_rate",
        ]
    ].copy()
    for column in ["success_rate", "discounted_cost", "avg_workload", "overload_rate", "verification_rate"]:
        benchmark_rows[column] = benchmark_rows[column].map(fmt)

    online_rows = online_summary[
        [
            "dataset",
            "controller",
            "discounted_cost",
            "success_rate",
            "overload_rate",
            "safe_occupancy_rate",
            "benchmark_action_safe_occupancy_rate",
            "benchmark_safe_occupancy_rate",
            "safe_set_nonempty_rate",
            "exact_safe_set_nonempty_rate",
            "benchmark_action_set_nonempty_rate",
            "fallback_rate",
            "high_effort_rate",
            "theta_benchmark_precision",
            "theta_benchmark_recall",
            "theta_nesting_precision",
            "action_safe_precision",
            "safe_event_precision",
            "negative_drift_rate_outside_safe",
            "avg_return_time_to_safe",
            "certificate_load_violation_rate",
            "certificate_service_violation_rate",
        ]
    ].copy()
    for column in [
        "discounted_cost",
        "success_rate",
        "overload_rate",
        "safe_occupancy_rate",
        "benchmark_action_safe_occupancy_rate",
        "benchmark_safe_occupancy_rate",
        "safe_set_nonempty_rate",
        "exact_safe_set_nonempty_rate",
        "benchmark_action_set_nonempty_rate",
        "fallback_rate",
        "high_effort_rate",
        "theta_benchmark_precision",
        "theta_benchmark_recall",
        "theta_nesting_precision",
        "action_safe_precision",
        "safe_event_precision",
        "negative_drift_rate_outside_safe",
        "avg_return_time_to_safe",
        "certificate_load_violation_rate",
        "certificate_service_violation_rate",
    ]:
        online_rows[column] = online_rows[column].map(fmt)

    pairwise_rows = online_pairwise.copy()
    for column in ["se_mpc_minus_rsrc", "ci_low", "ci_high"]:
        pairwise_rows[column] = pairwise_rows[column].map(fmt)
    pairwise_focus = online_pairwise[
        online_pairwise["metric"].isin(["discounted_cost", "success_rate", "safe_event_precision", "avg_return_time_to_safe"])
    ].copy()
    pairwise_focus["estimate [95% CI]"] = pairwise_focus.apply(
        lambda row: f"{fmt(row['se_mpc_minus_rsrc'])} [{fmt(row['ci_low'])}, {fmt(row['ci_high'])}]",
        axis=1,
    )
    pairwise_focus = pairwise_focus[["dataset", "metric", "estimate [95% CI]"]]

    dynamic_baseline_rows = online_summary[
        online_summary["controller"].isin(
            [
                "rsrc",
                "se_mpc",
                "camc_static_anchor",
                "camc_rsrc_anchor",
                "camc_sempc_candidate",
                "pareto_camc_static_anchor",
                "pareto_camc_rsrc_anchor",
                "pareto_camc_sempc_candidate",
                "static_conservative",
                "minimal_verify",
                "plain_mpc",
                "always_verify_throttle",
                "adaptive_threshold",
                "maxweight_backlog",
                "headroom_only",
                "rsrc_no_recovery",
                "rsrc_no_context",
            ]
        )
    ][
        [
            "dataset",
            "controller",
            "discounted_cost",
            "safety_augmented_cost_medium",
            "success_rate",
            "overload_rate",
            "verification_rate",
            "fallback_rate",
            "negative_drift_rate_outside_safe",
            "avg_return_time_to_safe",
        ]
    ].copy()
    dynamic_baseline_rows = dynamic_baseline_rows.rename(
        columns={
            "discounted_cost": "operating_cost_proxy",
            "safety_augmented_cost_medium": "safety_augmented_cost",
        }
    )
    for column in [
        "operating_cost_proxy",
        "safety_augmented_cost",
        "success_rate",
        "overload_rate",
        "verification_rate",
        "fallback_rate",
        "negative_drift_rate_outside_safe",
        "avg_return_time_to_safe",
    ]:
        dynamic_baseline_rows[column] = dynamic_baseline_rows[column].map(lambda value: fmt(value) if pd.notna(value) else "")

    safety_objective_rows = safety_objectives[
        safety_objectives["controller"].isin(
            [
                "rsrc",
                "se_mpc",
                "camc_static_anchor",
                "camc_rsrc_anchor",
                "camc_sempc_candidate",
                "pareto_camc_static_anchor",
                "pareto_camc_rsrc_anchor",
                "pareto_camc_sempc_candidate",
                "static_conservative",
                "minimal_verify",
                "plain_mpc",
                "always_verify_throttle",
                "adaptive_threshold",
                "maxweight_backlog",
                "headroom_only",
                "rsrc_no_recovery",
                "rsrc_no_context",
            ]
        )
        & safety_objectives["profile"].isin(["low", "medium", "high"])
    ].copy()
    safety_objective_rows["estimate [95% CI]"] = safety_objective_rows.apply(
        lambda row: f"{fmt(row['safety_augmented_cost'])} [{fmt(row['ci_low'])}, {fmt(row['ci_high'])}]",
        axis=1,
    )
    safety_objective_rows = safety_objective_rows[["dataset", "controller", "profile", "estimate [95% CI]"]]

    validation_rows = simulator_validation_metrics.copy()
    validation_rows["value"] = validation_rows["value"].map(lambda value: fmt(value) if pd.notna(value) else "")

    validation_calibration_rows = simulator_validation_calibration[
        [
            "mode",
            "rows",
            "load_violation_rate",
            "service_violation_rate",
            "certified_positive_rate",
            "certified_positive_precision",
            "certified_positive_recall",
            "headroom_sign_accuracy",
        ]
    ].copy()
    for column in [
        "load_violation_rate",
        "service_violation_rate",
        "certified_positive_rate",
        "certified_positive_precision",
        "certified_positive_recall",
        "headroom_sign_accuracy",
    ]:
        validation_calibration_rows[column] = validation_calibration_rows[column].map(lambda value: fmt(value) if pd.notna(value) else "")

    shadow_summary_rows = shadow_summary[
        [
            "controller",
            "tasks",
            "success_rate",
            "catastrophic_failure_rate",
            "avg_test_runs",
            "verification_rate",
            "safe_state_rate",
            "progress_rate",
            "avg_best_problem_reduction",
            "avg_return_to_safe",
        ]
    ].copy()
    for column in [
        "success_rate",
        "catastrophic_failure_rate",
        "avg_test_runs",
        "verification_rate",
        "safe_state_rate",
        "progress_rate",
        "avg_best_problem_reduction",
        "avg_return_to_safe",
    ]:
        shadow_summary_rows[column] = shadow_summary_rows[column].map(lambda value: fmt(value) if pd.notna(value) else "")

    shadow_pairwise_rows = shadow_pairwise.copy()
    for column in ["mean_diff", "ci_low", "ci_high"]:
        shadow_pairwise_rows[column] = shadow_pairwise_rows[column].map(lambda value: fmt(value) if pd.notna(value) else "")

    contrast_focus = controller_contrasts[
        controller_contrasts["metric"].isin(
            [
                "safety_augmented_cost_medium",
                "overload_rate",
                "success_rate",
                "verification_rate",
                "negative_drift_rate_outside_safe",
                "avg_return_time_to_safe",
            ]
        )
        & controller_contrasts["controller_a"].isin(["rsrc", "se_mpc", "camc_static_anchor", "camc_rsrc_anchor", "camc_sempc_candidate", "headroom_only", "always_verify_throttle"])
        & controller_contrasts["controller_b"].isin(
            ["static_conservative", "rsrc", "se_mpc", "headroom_only", "rsrc_no_recovery", "rsrc_no_context", "minimal_verify", "always_verify"]
        )
    ].copy()
    contrast_focus["estimate [95% CI]"] = contrast_focus.apply(
        lambda row: f"{fmt(row['a_minus_b'])} [{fmt(row['ci_low'])}, {fmt(row['ci_high'])}]",
        axis=1,
    )
    contrast_focus = contrast_focus[["dataset", "controller_a", "controller_b", "metric", "estimate [95% CI]"]]

    mpc_activation_rows = online_summary[
        online_summary["controller"].isin(["se_mpc"])
    ][
        [
            "dataset",
            "mpc_eligible_rate",
            "mpc_activation_rate",
            "mpc_fallback_to_rsrc_rate",
            "mpc_mean_candidate_count",
            "mpc_candidate_rejection_rate",
            "mpc_mean_surrogate_improvement",
            "mpc_verify_down_rate",
            "mpc_verify_up_rate",
            "mpc_atom_up_rate",
            "mpc_mode_switch_rate",
        ]
    ].copy()
    for column in [
        "mpc_eligible_rate",
        "mpc_activation_rate",
        "mpc_fallback_to_rsrc_rate",
        "mpc_mean_candidate_count",
        "mpc_candidate_rejection_rate",
        "mpc_mean_surrogate_improvement",
        "mpc_verify_down_rate",
        "mpc_verify_up_rate",
        "mpc_atom_up_rate",
        "mpc_mode_switch_rate",
    ]:
        mpc_activation_rows[column] = mpc_activation_rows[column].map(lambda value: fmt(value) if pd.notna(value) else "")

    camc_gate_rows = online_summary[
        online_summary["controller"].isin(
            [
                "camc_static_anchor",
                "camc_rsrc_anchor",
                "camc_sempc_candidate",
                "pareto_camc_static_anchor",
                "pareto_camc_rsrc_anchor",
                "pareto_camc_sempc_candidate",
            ]
        )
    ][
        [
            "dataset",
            "controller",
            "safety_augmented_cost_medium",
            "success_rate",
            "overload_rate",
            "verification_rate",
            "fallback_rate",
            "camc_activation_rate",
            "camc_anchor_preservation_rate",
            "camc_candidate_rejection_rate",
            "camc_post_switch_violation_rate",
            "camc_mean_certified_margin",
            "camc_mean_activated_margin",
            "camc_reject_safety_rate",
            "camc_reject_loss_rate",
            "camc_reject_benefit_rate",
            "camc_reject_violation_rate",
        ]
    ].copy()
    camc_gate_rows = camc_gate_rows.rename(columns={"safety_augmented_cost_medium": "safety_augmented_cost"})
    for column in [
        "safety_augmented_cost",
        "success_rate",
        "overload_rate",
        "verification_rate",
        "fallback_rate",
        "camc_activation_rate",
        "camc_anchor_preservation_rate",
        "camc_candidate_rejection_rate",
        "camc_post_switch_violation_rate",
        "camc_mean_certified_margin",
        "camc_mean_activated_margin",
        "camc_reject_safety_rate",
        "camc_reject_loss_rate",
        "camc_reject_benefit_rate",
        "camc_reject_violation_rate",
    ]:
        camc_gate_rows[column] = camc_gate_rows[column].map(lambda value: fmt(value) if pd.notna(value) else "")

    camc_pairwise_focus = camc_pairwise[
        camc_pairwise["metric"].isin(
            [
                "safety_augmented_cost_medium",
                "success_rate",
                "overload_rate",
                "fallback_rate",
                "camc_activation_rate",
                "camc_post_switch_violation_rate",
            ]
        )
    ].copy()
    camc_pairwise_focus["estimate [95% CI]"] = camc_pairwise_focus.apply(
        lambda row: f"{fmt(row['a_minus_b'])} [{fmt(row['ci_low'])}, {fmt(row['ci_high'])}]",
        axis=1,
    )
    camc_pairwise_focus = camc_pairwise_focus[["dataset", "comparison", "metric", "estimate [95% CI]"]]

    camc_slack_rows = camc_by_slack.copy()
    for column in [
        "activation_rate",
        "mean_certified_margin",
        "mean_certified_slack",
        "post_switch_violation_rate",
        "mean_success",
        "mean_drift",
    ]:
        camc_slack_rows[column] = camc_slack_rows[column].map(lambda value: fmt(value) if pd.notna(value) else "")
    camc_slack_rows = camc_slack_rows[
        [
            "dataset",
            "controller",
            "slack_quantile",
            "rows",
            "activation_rate",
            "mean_certified_margin",
            "mean_certified_slack",
            "post_switch_violation_rate",
        ]
    ]

    camc_shift_rows = camc_by_shift.copy()
    for column in [
        "activation_rate",
        "anchor_preservation_rate",
        "fallback_rate",
        "mean_certified_margin",
        "mean_certified_slack",
        "post_switch_violation_rate",
    ]:
        camc_shift_rows[column] = camc_shift_rows[column].map(lambda value: fmt(value) if pd.notna(value) else "")
    camc_shift_rows = camc_shift_rows[
        [
            "dataset",
            "controller",
            "shift_bucket",
            "rows",
            "activation_rate",
            "anchor_preservation_rate",
            "fallback_rate",
            "mean_certified_margin",
            "mean_certified_slack",
            "post_switch_violation_rate",
        ]
    ]

    headroom_support_rows = headroom_support[
        [
            "dataset",
            "controller",
            "adverse_rows",
            "adverse_negative_drift_rate",
            "adverse_negative_delta_sq_rate",
            "adverse_high_load_rows",
            "adverse_high_load_negative_drift_rate",
            "benign_rows",
            "benign_benchmark_safe_rate",
            "benign_mean_exact_headroom",
        ]
    ].copy()
    for column in [
        "adverse_negative_drift_rate",
        "adverse_negative_delta_sq_rate",
        "adverse_high_load_negative_drift_rate",
        "benign_benchmark_safe_rate",
        "benign_mean_exact_headroom",
    ]:
        headroom_support_rows[column] = headroom_support_rows[column].map(lambda value: fmt(value) if pd.notna(value) else "")

    headroom_calibration_rows = headroom_calibration[
        headroom_calibration["headroom_bin"].isin(["<=0", "(0.08,0.15]", ">0.15"])
        & headroom_calibration["controller"].isin(["rsrc", "se_mpc"])
    ][
        [
            "dataset",
            "controller",
            "headroom_bin",
            "mean_certified_headroom",
            "mean_exact_headroom",
            "exact_headroom_positive_rate",
            "benchmark_safe_rate",
            "negative_drift_rate",
            "rows",
        ]
    ].copy()
    for column in [
        "mean_certified_headroom",
        "mean_exact_headroom",
        "exact_headroom_positive_rate",
        "benchmark_safe_rate",
        "negative_drift_rate",
    ]:
        headroom_calibration_rows[column] = headroom_calibration_rows[column].map(lambda value: fmt(value) if pd.notna(value) else "")

    positive_headroom_rows = positive_headroom_drift[
        positive_headroom_drift["controller"].isin(["rsrc", "se_mpc", "static_conservative"])
        & (positive_headroom_drift["epsilon_s"] == 0.03)
        & (positive_headroom_drift["load_threshold"] == 0.5)
    ][
        [
            "dataset",
            "controller",
            "rows",
            "mean_drift",
            "mean_drift_ci_low",
            "mean_drift_ci_high",
            "negative_drift_rate",
            "negative_drift_rate_ci_low",
            "negative_drift_rate_ci_high",
            "mean_exact_headroom",
        ]
    ].copy()
    positive_headroom_rows["mean drift [95% CI]"] = positive_headroom_rows.apply(
        lambda row: "" if pd.isna(row["mean_drift"]) else f"{fmt(row['mean_drift'])} [{fmt(row['mean_drift_ci_low'])}, {fmt(row['mean_drift_ci_high'])}]",
        axis=1,
    )
    positive_headroom_rows["neg. drift [95% CI]"] = positive_headroom_rows.apply(
        lambda row: "" if pd.isna(row["negative_drift_rate"]) else f"{fmt(row['negative_drift_rate'])} [{fmt(row['negative_drift_rate_ci_low'])}, {fmt(row['negative_drift_rate_ci_high'])}]",
        axis=1,
    )
    positive_headroom_rows["mean_exact_headroom"] = positive_headroom_rows["mean_exact_headroom"].map(lambda value: fmt(value) if pd.notna(value) else "")
    positive_headroom_rows = positive_headroom_rows[["dataset", "controller", "rows", "mean drift [95% CI]", "neg. drift [95% CI]", "mean_exact_headroom"]]

    family_barrier_rows = family_barrier[
        ["dataset", "controller", "family", "load_threshold", "rows", "barrier_rate", "mean_min_projected_drift"]
    ].copy()
    for column in ["load_threshold", "barrier_rate", "mean_min_projected_drift"]:
        family_barrier_rows[column] = family_barrier_rows[column].map(lambda value: fmt(value) if pd.notna(value) else "")

    top_by_dataset = (
        benchmark.sort_values(["dataset", "overload_rate", "discounted_cost", "success_rate"], ascending=[True, True, True, False])
        .groupby("dataset")
        .head(3)
        .loc[:, ["dataset", "controller", "success_rate", "discounted_cost", "overload_rate"]]
        .copy()
    )
    for column in ["success_rate", "discounted_cost", "overload_rate"]:
        top_by_dataset[column] = top_by_dataset[column].map(fmt)

    key_findings = []
    def validation_value(target: str, metric: str) -> float:
        match = simulator_validation_metrics[
            (simulator_validation_metrics["target"] == target)
            & (simulator_validation_metrics["metric"] == metric)
        ]
        return float(match["value"].iloc[0]) if not match.empty else float("nan")

    key_findings.append(
        f"Reduced-state support is positive: reduced AUC = {fmt(structural['state_compression']['reduced_model']['auc'])}, full AUC = {fmt(structural['state_compression']['full_model']['auc'])}, and the gap is {fmt(structural['state_compression']['full_minus_reduced_auc'])}."
    )
    key_findings.append(
        f"Out-of-simulator holdout validation now checks the semi-structured simulator primitives: failure AUC = {fmt(validation_value('failure', 'auc'))}, total-load R2 = {fmt(validation_value('total_load', 'r2'))}, total-load correlation = {fmt(validation_value('total_load', 'corr'))}, and service R2 = {fmt(validation_value('service', 'r2'))}."
    )
    key_findings.append(
        f"Canonicalized context diagnostics are materially stronger than raw token counts: canonical additive AUC = {fmt(structural['context_atoms']['canonical_additive_model']['auc'])} vs raw additive AUC = {fmt(structural['context_atoms']['raw_additive_model']['auc'])}, mean canonical footprint CV drops from {fmt(structural['context_atoms']['mean_raw_cv'])} to {fmt(structural['context_atoms']['mean_canonical_cv'])}, and top-K exact-match = {fmt(structural['context_atoms']['exact_match_rate_top2'])}."
    )
    key_findings.append(
        f"Lower-score context screening is conservative in the desired direction: strong-positive recall = {fmt(structural['context_atoms']['strong_positive_recall_top2'])}, over-internalization rate = {fmt(structural['context_atoms']['overinternalization_rate_top2'])}, and conservative set-match = {fmt(structural['context_atoms']['conservative_set_match_rate_top2'])}."
    )
    key_findings.append(
        f"Recovery amplification is visible in CodeTraceBench: mean future bad stages after an incorrect stage = {fmt(certificate['recovery_matrix']['mean_future_bad_after_incorrect'])}, and P(incorrect->incorrect) = {fmt(certificate['recovery_matrix']['transition_probabilities']['incorrect']['incorrect'])}."
    )
    key_findings.append(
        f"Split-calibrated certificates are no longer degenerate: theta-safe nonempty rate = {fmt(certificate['certificate_validity']['theta_safe_nonempty_rate'])}, mean safe-set size = {fmt(certificate['certificate_validity']['theta_safe_mean_size'])}, theta precision = {fmt(certificate['certificate_validity']['theta_safe_precision'])}, and theta recall = {fmt(certificate['certificate_validity']['theta_safe_recall'])}."
    )
    key_findings.append(
        f"Verification-boundary diagnostics are now directly observed through a counterfactual heatmap: monotonicity violations are {fmt(structural['verification_boundary']['monotonicity_violation_rate_e'], digits=6)} along e and {fmt(structural['verification_boundary']['monotonicity_violation_rate_q'], digits=6)} along q; far-inside miss rate is {fmt(structural['verification_boundary']['conservative_miss_rate_far_inside'], digits=6)}."
    )
    key_findings.append(
        f"The continuous-effort extension is now empirically instantiated: mean optimal effort proxy = {fmt(structural['verification_boundary']['continuous_effort_mean'])}, high-effort share = {fmt(structural['verification_boundary']['continuous_effort_high_rate'])}, and q-monotonicity violation = {fmt(structural['verification_boundary']['continuous_effort_violation_rate_q'])}."
    )
    key_findings.append(
        f"A counterfactual effort-surface check aligns the theorem rule with the semi-structured runtime objective: optimal-effort mean = {fmt(structural['verification_boundary']['counterfactual_optimal_effort_mean'])}, rule exact match = {fmt(structural['verification_boundary']['counterfactual_rule_exact_match_rate'])}, one-step match = {fmt(structural['verification_boundary']['counterfactual_rule_one_step_match_rate'])}, rule mean regret = {fmt(structural['verification_boundary']['counterfactual_rule_mean_regret'], digits=6)}, and counterfactual q-violation = {fmt(structural['verification_boundary']['counterfactual_monotonicity_violation_rate_q'])}."
    )
    shadow_static = shadow_summary[shadow_summary["controller"] == "static_conservative"].iloc[0]
    shadow_rsrc = shadow_summary[shadow_summary["controller"] == "rsrc_guarded"].iloc[0]
    shadow_sempc = shadow_summary[shadow_summary["controller"] == "sempc_lite"].iloc[0]
    shadow_minimal = shadow_summary[shadow_summary["controller"] == "minimal_verify"].iloc[0]
    key_findings.append(
        f"The 8-task LM Studio repository-executing shadow runtime is best read as a pilot sanity check, not performance evidence: static_conservative is the only controller with nonzero live success ({fmt(shadow_static['success_rate'])}), while rsrc_guarded and sempc_lite have success {fmt(shadow_rsrc['success_rate'])}/{fmt(shadow_sempc['success_rate'])}; catastrophic-failure rates are {fmt(shadow_minimal['catastrophic_failure_rate'])}, {fmt(shadow_static['catastrophic_failure_rate'])}, {fmt(shadow_rsrc['catastrophic_failure_rate'])}, and {fmt(shadow_sempc['catastrophic_failure_rate'])} for minimal_verify, static_conservative, rsrc_guarded, and sempc_lite."
    )
    key_findings.append(
        f"Distribution shift is mild for Verified ({fmt(profile_frame.loc[profile_frame['dataset'] == 'swe_verified', 'mean_abs_feature_shift_vs_test'].iloc[0])}) and moderate for Rebench ({fmt(profile_frame.loc[profile_frame['dataset'] == 'swe_rebench', 'mean_abs_feature_shift_vs_test'].iloc[0])}), but large for Smith ({fmt(profile_frame.loc[profile_frame['dataset'] == 'swe_smith', 'mean_abs_feature_shift_vs_test'].iloc[0])})."
    )
    for dataset in ["verified", "test", "rebench", "smith"]:
        rsrc = benchmark_lookup(benchmark, dataset, "rsrc")
        se_mpc = benchmark_lookup(benchmark, dataset, "se_mpc")
        key_findings.append(
            f"On {dataset}, SE-MPC should be read as a small local-improvement layer over RSRC, not as a dominant controller: success {fmt(rsrc['success_rate'])}->{fmt(se_mpc['success_rate'])}, operating-cost proxy {fmt(rsrc['discounted_cost'])}->{fmt(se_mpc['discounted_cost'])}, overload {fmt(rsrc['overload_rate'])}->{fmt(se_mpc['overload_rate'])}."
        )
    key_findings.append(
        f"The calibrated certificate remains conservative but no longer empty: positive certified headroom rate = {fmt(certificate['certificate_validity']['positive_headroom_rate'])}, benchmark-safe nonempty rate = {fmt(certificate['certificate_validity']['benchmark_safe_nonempty_rate'])}, and one-step load/service violations are {fmt(certificate['certificate_validity']['load_violation_rate'])}/{fmt(certificate['certificate_validity']['service_violation_rate'])}."
    )
    for dataset in ["verified", "test", "rebench", "smith"]:
        dataset_rows_online = online_summary[online_summary["dataset"] == dataset]
        if dataset_rows_online.empty:
            continue
        rsrc_online = benchmark_lookup(online_summary, dataset, "rsrc")
        se_online = benchmark_lookup(online_summary, dataset, "se_mpc")
        key_findings.append(
            f"Online simulator on {dataset}: SE-MPC remains close to RSRC, with overload {fmt(rsrc_online['overload_rate'])}->{fmt(se_online['overload_rate'])}, certified safe occupancy {fmt(rsrc_online['safe_occupancy_rate'])}->{fmt(se_online['safe_occupancy_rate'])}, benchmark action-safe occupancy {fmt(rsrc_online['benchmark_action_safe_occupancy_rate'])}->{fmt(se_online['benchmark_action_safe_occupancy_rate'])}, runtime-safe occupancy {fmt(rsrc_online['benchmark_safe_occupancy_rate'])}->{fmt(se_online['benchmark_safe_occupancy_rate'])}, action-safe precision {fmt(rsrc_online['action_safe_precision'])}->{fmt(se_online['action_safe_precision'])}, fallback {fmt(rsrc_online['fallback_rate'])}->{fmt(se_online['fallback_rate'])}, and negative drift outside safe {fmt(rsrc_online['negative_drift_rate_outside_safe'])}->{fmt(se_online['negative_drift_rate_outside_safe'])}."
        )
        if {"camc_static_anchor", "camc_rsrc_anchor", "camc_sempc_candidate"}.issubset(set(dataset_rows_online["controller"])):
            camc_static = benchmark_lookup(online_summary, dataset, "camc_static_anchor")
            camc_rsrc = benchmark_lookup(online_summary, dataset, "camc_rsrc_anchor")
            camc_sempc = benchmark_lookup(online_summary, dataset, "camc_sempc_candidate")
            key_findings.append(
                f"Loss-only CAMC on {dataset} has activation rates {fmt(camc_static['camc_activation_rate'])}/{fmt(camc_rsrc['camc_activation_rate'])}/{fmt(camc_sempc['camc_activation_rate'])} for static-anchor, RSRC-anchor, and SE-MPC-candidate variants; post-switch violation rates are {fmt(camc_static['camc_post_switch_violation_rate'])}/{fmt(camc_rsrc['camc_post_switch_violation_rate'])}/{fmt(camc_sempc['camc_post_switch_violation_rate'])}; safety-augmented costs are {fmt(camc_static['safety_augmented_cost_medium'])}/{fmt(camc_rsrc['safety_augmented_cost_medium'])}/{fmt(camc_sempc['safety_augmented_cost_medium'])}."
            )
        if {"pareto_camc_static_anchor", "pareto_camc_rsrc_anchor", "pareto_camc_sempc_candidate"}.issubset(set(dataset_rows_online["controller"])):
            pareto_static = benchmark_lookup(online_summary, dataset, "pareto_camc_static_anchor")
            pareto_rsrc = benchmark_lookup(online_summary, dataset, "pareto_camc_rsrc_anchor")
            pareto_sempc = benchmark_lookup(online_summary, dataset, "pareto_camc_sempc_candidate")
            key_findings.append(
                f"Pareto-CAMC on {dataset} turns CAMC into a non-inferiority filter: activation rates are {fmt(pareto_static['camc_activation_rate'])}/{fmt(pareto_rsrc['camc_activation_rate'])}/{fmt(pareto_sempc['camc_activation_rate'])}, post-switch violation rates are {fmt(pareto_static['camc_post_switch_violation_rate'])}/{fmt(pareto_rsrc['camc_post_switch_violation_rate'])}/{fmt(pareto_sempc['camc_post_switch_violation_rate'])}, and success rates are {fmt(pareto_static['success_rate'])}/{fmt(pareto_rsrc['success_rate'])}/{fmt(pareto_sempc['success_rate'])}."
            )
    adverse_test_rsrc = headroom_support[(headroom_support["dataset"] == "test") & (headroom_support["controller"] == "rsrc")]
    adverse_rebench_rsrc = headroom_support[(headroom_support["dataset"] == "rebench") & (headroom_support["controller"] == "rsrc")]
    if not adverse_test_rsrc.empty and not adverse_rebench_rsrc.empty:
        key_findings.append(
            f"Headroom-conditioned drift now links calibration to stability more directly: negative-drift rates in certified-adverse states under RSRC are {fmt(adverse_test_rsrc['adverse_negative_drift_rate'].iloc[0])} on test and {fmt(adverse_rebench_rsrc['adverse_negative_drift_rate'].iloc[0])} on rebench, while benign positive-headroom states remain benchmark-safe at rates {fmt(adverse_test_rsrc['benign_benchmark_safe_rate'].iloc[0])} and {fmt(adverse_rebench_rsrc['benign_benchmark_safe_rate'].iloc[0])}."
        )
    positive_test_rsrc = positive_headroom_drift[
        (positive_headroom_drift["dataset"] == "test")
        & (positive_headroom_drift["controller"] == "rsrc")
        & (positive_headroom_drift["epsilon_s"] == 0.03)
        & (positive_headroom_drift["load_threshold"] == 0.5)
    ]
    positive_rebench_rsrc = positive_headroom_drift[
        (positive_headroom_drift["dataset"] == "rebench")
        & (positive_headroom_drift["controller"] == "rsrc")
        & (positive_headroom_drift["epsilon_s"] == 0.03)
        & (positive_headroom_drift["load_threshold"] == 0.5)
    ]
    if not positive_test_rsrc.empty and not positive_rebench_rsrc.empty:
        key_findings.append(
            f"The direct positive-headroom drift slice is now reported for theorem alignment: under RSRC with epsilon_s=0.03 and L>=0.5 outside the safe envelope, test/rebench rows are {int(positive_test_rsrc['rows'].iloc[0])}/{int(positive_rebench_rsrc['rows'].iloc[0])}, with negative-drift rates {fmt(positive_test_rsrc['negative_drift_rate'].iloc[0])}/{fmt(positive_rebench_rsrc['negative_drift_rate'].iloc[0])}."
        )

    lines = [
        "# Experiment Results",
        "",
        "## Run Summary",
        "",
        f"- Consolidated result directory: `{args.results_dir}`",
        f"- Benchmark seeds: `{benchmark_meta['seeds']}`",
        f"- Online simulator seeds: `{online_meta['seeds']}`",
        f"- Online simulator horizon: `{online_meta['horizon']}`",
        f"- Distribution reference dataset: `{distribution['reference_dataset']}`",
        "",
        "## Dataset Inventory",
        "",
        markdown_table(dataset_rows),
        "",
        "## Structural Diagnostics",
        "",
        markdown_table(structural_rows),
        "",
        "## Simulator Predictive Validation",
        "",
        markdown_table(validation_rows),
        "",
        "## Simulator Calibration Validation",
        "",
        markdown_table(validation_calibration_rows),
        "",
        "## Repository-Executing Shadow Runtime Pilot",
        "",
        markdown_table(shadow_summary_rows),
        "",
        "## Shadow Runtime Pairwise",
        "",
        markdown_table(shadow_pairwise_rows),
        "",
        "## Key Findings",
        "",
        *[f"- {line}" for line in key_findings],
        "",
        "## Certificate Diagnostics",
        "",
        markdown_table(certificate_rows),
        "",
        "## Distributional Diagnostics",
        "",
        markdown_table(profile_rows),
        "",
        "## Controller Benchmark",
        "",
        markdown_table(benchmark_rows),
        "",
        "## Online Simulator",
        "",
        markdown_table(online_rows),
        "",
        "## Online Dynamic Baselines",
        "",
        markdown_table(dynamic_baseline_rows),
        "",
        "## Online Pairwise",
        "",
        markdown_table(pairwise_rows),
        "",
        "## Online Pairwise With Confidence Intervals",
        "",
        markdown_table(pairwise_focus),
        "",
        "## Safety-Augmented Online Objectives",
        "",
        markdown_table(safety_objective_rows),
        "",
        "## Strong Baselines And Ablation Contrasts",
        "",
        markdown_table(contrast_focus),
        "",
        "## SE-MPC Activation Diagnostics",
        "",
        markdown_table(mpc_activation_rows),
        "",
        "## CAMC Gate Diagnostics",
        "",
        markdown_table(camc_gate_rows),
        "",
        "## CAMC Pairwise With Clustered Confidence Intervals",
        "",
        markdown_table(camc_pairwise_focus),
        "",
        "## CAMC Activation By Certified Slack",
        "",
        markdown_table(camc_slack_rows),
        "",
        "## CAMC Activation By Shift Bucket",
        "",
        markdown_table(camc_shift_rows),
        "",
        "## Headroom-Conditioned Drift Support",
        "",
        markdown_table(headroom_support_rows),
        "",
        "## Positive-Headroom Drift Slice",
        "",
        markdown_table(positive_headroom_rows),
        "",
        "## Headroom Calibration Slices",
        "",
        markdown_table(headroom_calibration_rows),
        "",
        "## Governance-Family Viability",
        "",
        markdown_table(family_barrier_rows),
        "",
        "## Best Frontiers Per Dataset",
        "",
        markdown_table(top_by_dataset),
        "",
    ]
    args.output.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote report to {args.output}")


if __name__ == "__main__":
    main()
