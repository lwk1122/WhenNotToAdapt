from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

from common import (
    EFFORT_LEVELS,
    GOVERNANCE_MODES,
    MANIFEST_DIR,
    RESULTS_DIR,
    bootstrap_interval,
    clip_probabilities,
    ensure_dir,
    manifest_paths,
    shift_effort,
    ridge_fit,
    ridge_predict,
    sigmoid,
    verification_effort,
    verification_threshold,
    write_json,
)
from controller_benchmark import ATOM_COLS, TASK_FEATURE_COLS, apply_priors, fit_priors, load_datasets
from structural_diagnostics import fit_state_compression, load_overlap, standardize_from_train


BETA = 0.985
DELTA_SAFE = 0.03
DELTA_PERF = 0.08
ELL_SAFE = 2.6
ELL_PERF = 1.6
Q_SAFE = 0.85
Q_PERF = 0.45
L_SAFE = 0.35
L_PERF = 0.18
DEBT_SAFE = 0.55
DEBT_PERF = 0.28
OVERLOAD_THRESHOLD = 0.60

SAFETY_OBJECTIVE_PROFILES = {
    "low": {"overload": 0.75, "failure": 0.25, "service": 0.35},
    "medium": {"overload": 2.0, "failure": 0.75, "service": 0.90},
    "high": {"overload": 5.0, "failure": 1.50, "service": 1.75},
}

ABLATION_CONTROLLERS = {
    "headroom_only",
    "rsrc_no_recovery",
    "rsrc_no_context",
}

STRONG_BASELINE_CONTROLLERS = {
    "always_verify_throttle",
    "adaptive_threshold",
    "maxweight_backlog",
}

LOSS_ONLY_CAMC_CONTROLLERS = {
    "camc_static_anchor",
    "camc_rsrc_anchor",
    "camc_sempc_candidate",
}

PARETO_CAMC_CONTROLLERS = {
    "pareto_camc_static_anchor",
    "pareto_camc_rsrc_anchor",
    "pareto_camc_sempc_candidate",
}

CAMC_CONTROLLERS = LOSS_ONLY_CAMC_CONTROLLERS | PARETO_CAMC_CONTROLLERS

CAMC_TAU = 0.055
PARETO_CAMC_TAU0 = 0.055
PARETO_CAMC_ALPHA_SHIFT = 0.110
PARETO_CAMC_ALPHA_RHO = 0.350
PARETO_CAMC_ALPHA_STATE = 0.015
PARETO_CAMC_DELTA_B = 0.055
PARETO_CAMC_DELTA_V = 0.010
PARETO_CAMC_MIN_BENEFIT = 0.550
PARETO_CAMC_HYSTERESIS_TAU = 0.095
PARETO_CAMC_COOLDOWN_STEPS = 5


def state_penalty(q_value: float, ell: float, backlog: float, diagnostic_debt: float, delta: float) -> float:
    q_limit = Q_SAFE if delta == DELTA_SAFE else Q_PERF
    ell_limit = ELL_SAFE if delta == DELTA_SAFE else ELL_PERF
    l_limit = L_SAFE if delta == DELTA_SAFE else L_PERF
    debt_limit = DEBT_SAFE if delta == DELTA_SAFE else DEBT_PERF
    return float(
        0.05
        + 0.05 * (q_value / max(q_limit, 1e-6))
        + 0.02 * (ell / max(ell_limit, 1e-6))
        + 0.06 * (backlog / max(l_limit, 1e-6))
        + 0.05 * (diagnostic_debt / max(debt_limit, 1e-6))
        + 0.30 * max(q_value - q_limit, 0.0)
        + 0.12 * max(ell - ell_limit, 0.0)
        + 0.34 * max(backlog - l_limit, 0.0)
        + 0.26 * max(diagnostic_debt - debt_limit, 0.0)
    )


def safe_mode_mask(headrooms: np.ndarray, q_value: float, ell: float, backlog: float, diagnostic_debt: float, delta: float) -> np.ndarray:
    penalty = state_penalty(q_value, ell, backlog, diagnostic_debt, delta)
    return np.asarray(headrooms >= (delta + penalty), dtype=bool)


def delta_limits(delta: float) -> tuple[float, float, float, float, float, float, float, float]:
    if delta == DELTA_SAFE:
        return Q_SAFE, ELL_SAFE, L_SAFE, DEBT_SAFE, 0.06, 0.18, 0.10, 0.15
    return Q_PERF, ELL_PERF, L_PERF, DEBT_PERF, 0.04, 0.12, 0.06, 0.10


def estimated_risk_anchor(
    row: pd.Series,
    rho: float,
    contamination: float,
    diagnostic_debt: float,
    arrival_pressure: float,
    reference_shift: float,
) -> float:
    return float(
        np.clip(
            float(row["e_proxy"])
            + rho
            + 0.07 * reference_shift
            + 0.05 * contamination
            + 0.07 * min(diagnostic_debt, 1.5)
            + 0.04 * min(arrival_pressure, 1.5)
            + 0.05 * float(row["step_norm"])
            + 0.03 * float(row["eval_norm"]),
            0.02,
            0.99,
        )
    )


def expected_failure_prob(
    risk_anchor: float,
    q_state: float,
    contamination: float,
    diagnostic_debt: float,
    arrival_pressure: float,
    verify: float,
    atoms_selected: int,
    context_gain: float,
    mode_idx: int,
) -> float:
    verification_benefit = 0.28 * verify + 0.05 * GOVERNANCE_MODES[mode_idx].verification_bias
    context_benefit = 0.04 * atoms_selected + 0.06 * max(context_gain, 0.0)
    return float(
        np.clip(
            risk_anchor
            - verification_benefit
            - context_benefit
            + 0.04 * q_state
            + 0.03 * contamination
            + 0.04 * diagnostic_debt
            + 0.03 * arrival_pressure,
            0.02,
            0.98,
        )
    )


def project_action_state(
    row: pd.Series,
    mode_idx: int,
    q_ver: float,
    ell: float,
    contamination: float,
    recovery_mass: float,
    diagnostic_debt: float,
    arrival_pressure: float,
    backlog_load: float,
    reference_shift: float,
    amp_mean: float,
    incorrect_self_loop: float,
    failure_prob: float,
    verify: float,
    atoms_selected: int,
) -> dict[str, float]:
    mode = GOVERNANCE_MODES[mode_idx]
    burst_prob = float(np.clip(0.06 + 0.04 * reference_shift + 0.04 * max(backlog_load - L_SAFE, 0.0), 0.0, 0.75))
    external_arrival = 0.03 + 0.03 * reference_shift + 0.04 * arrival_pressure + 0.03 * diagnostic_debt + 0.06 * burst_prob
    nominal_load = (
        external_arrival
        + 0.16 * float(row["d_proxy"])
        + 0.12 * (0.55 * float(row["q_proxy"]) + 0.25 * q_ver + 0.20 * diagnostic_debt)
        + 0.08 * float(row["step_norm"])
        + 0.05 * verify
        + 0.03 * atoms_selected
        + 0.03 * ell
        + 0.05 * diagnostic_debt
    )
    recovery_draw = amp_mean * (1.0 + 0.5 * incorrect_self_loop)
    recovery_load = failure_prob * recovery_draw * (
        0.14
        + 0.10 * float(row["d_proxy"])
        + 0.08 * float(row["eval_norm"])
        + 0.08 * recovery_mass
        + 0.10 * diagnostic_debt
        + 0.06 * arrival_pressure
    )
    actual_recovery_load = mode.recovery_multiplier * recovery_load
    realized_service = float(
        np.clip(
            float(row["base_service"]) * mode.service_floor
            - 0.10 * q_ver
            - 0.04 * ell
            - 0.05 * min(recovery_mass, 1.5)
            - 0.04 * diagnostic_debt
            - 0.05 * arrival_pressure
            + 0.01 * verify,
            0.05,
            1.0,
        )
    )
    projected_backlog = max(0.0, backlog_load + nominal_load + actual_recovery_load - realized_service)
    projected_q = max(
        0.0,
        0.74 * q_ver + 0.18 * verify + 0.14 * failure_prob + 0.06 * diagnostic_debt - 0.16 * mode.verification_bias,
    )
    projected_ell = float(np.clip(0.55 * ell + atoms_selected - 0.25 - 0.35 * mode.verification_bias, 0.0, 3.5))
    projected_debt = float(
        np.clip(
            0.82 * diagnostic_debt
            + 0.20 * (1.0 - verify)
            + 0.18 * failure_prob
            + 0.10 * max(projected_backlog - L_SAFE, 0.0)
            - 0.30 * verify
            - 0.08 * mode.verification_bias,
            0.0,
            2.0,
        )
    )
    return {
        "nominal_load": float(nominal_load),
        "actual_recovery_load": float(actual_recovery_load),
        "service": realized_service,
        "backlog": float(projected_backlog),
        "q": float(np.clip(projected_q, 0.0, 1.8)),
        "ell": projected_ell,
        "debt": projected_debt,
    }


def action_safe_mask(
    headrooms: np.ndarray,
    row: pd.Series,
    risk_anchor: float,
    q_ver: float,
    q_state: float,
    ell: float,
    contamination: float,
    recovery_mass: float,
    diagnostic_debt: float,
    arrival_pressure: float,
    backlog_load: float,
    reference_shift: float,
    amp_mean: float,
    incorrect_self_loop: float,
    verify: float,
    atoms_selected: int,
    context_gain: float,
    delta: float,
) -> np.ndarray:
    q_limit, ell_limit, l_limit, debt_limit, q_slack, ell_slack, l_slack, debt_slack = delta_limits(delta)
    current_penalty = state_penalty(q_ver, ell, backlog_load, diagnostic_debt, delta)
    mask = []
    for mode_idx, headroom in enumerate(headrooms):
        failure_prob = expected_failure_prob(
            risk_anchor,
            q_state,
            contamination,
            diagnostic_debt,
            arrival_pressure,
            verify,
            atoms_selected,
            context_gain,
            mode_idx,
        )
        projected = project_action_state(
            row,
            mode_idx,
            q_ver,
            ell,
            contamination,
            recovery_mass,
            diagnostic_debt,
            arrival_pressure,
            backlog_load,
            reference_shift,
            amp_mean,
            incorrect_self_loop,
            failure_prob,
            verify,
            atoms_selected,
        )
        projected_penalty = state_penalty(projected["q"], projected["ell"], projected["backlog"], projected["debt"], delta)
        projected_headroom = projected["service"] - (projected["nominal_load"] + projected["actual_recovery_load"])
        mask.append(
            bool(
                headroom >= (delta + 0.45 * current_penalty + 0.35 * projected_penalty)
                and projected_headroom >= (delta - 0.015)
                and projected["q"] <= (q_limit + q_slack)
                and projected["ell"] <= (ell_limit + ell_slack)
                and projected["backlog"] <= (l_limit + l_slack)
                and projected["debt"] <= (debt_limit + debt_slack)
            )
        )
    return np.asarray(mask, dtype=bool)


def family_min_projected_drifts(
    row: pd.Series,
    exact_risk: float,
    q_ver: float,
    q_state: float,
    ell: float,
    contamination: float,
    recovery_mass: float,
    diagnostic_debt: float,
    arrival_pressure: float,
    backlog_load: float,
    reference_shift: float,
    amp_mean: float,
    incorrect_self_loop: float,
    verify: float,
    atoms_selected: int,
    context_gain: float,
) -> dict[str, float]:
    mode_drifts = []
    for mode_idx in range(len(GOVERNANCE_MODES)):
        failure_prob = expected_failure_prob(
            exact_risk,
            q_state,
            contamination,
            diagnostic_debt,
            arrival_pressure,
            verify,
            atoms_selected,
            context_gain,
            mode_idx,
        )
        projected = project_action_state(
            row,
            mode_idx,
            q_ver,
            ell,
            contamination,
            recovery_mass,
            diagnostic_debt,
            arrival_pressure,
            backlog_load,
            reference_shift,
            amp_mean,
            incorrect_self_loop,
            failure_prob,
            verify,
            atoms_selected,
        )
        mode_drifts.append(projected["nominal_load"] + projected["actual_recovery_load"] - projected["service"])
    values = np.asarray(mode_drifts, dtype=float)
    return {
        "family_min_drift_g01": float(np.min(values[:2])),
        "family_min_drift_g012": float(np.min(values[:3])),
        "family_min_drift_all": float(np.min(values)),
    }


def candidate_surrogate_value(
    candidate_mode: int,
    candidate_verify: float,
    candidate_atoms: int,
    candidate_gain: float,
    candidate_failure_prob: float,
    projected_headroom: float,
    reference_shift: float,
) -> float:
    """Externality-adjusted local value used by SE-MPC/CAMC candidate screens."""
    return float(
        0.42 * candidate_verify
        + 0.15 * candidate_atoms
        + 1.40 * candidate_failure_prob
        - 0.55 * candidate_gain
        - 0.60 * projected_headroom
        + 0.12 * candidate_mode
        + 0.03 * reference_shift
    )


def pareto_camc_threshold(
    reference_shift: float,
    rho_bar: float,
    state_uncertainty: float,
    base_tau: float = PARETO_CAMC_TAU0,
) -> float:
    """Shift-adaptive opportunity threshold for Pareto-CAMC."""
    return float(
        base_tau
        + PARETO_CAMC_ALPHA_SHIFT * max(float(reference_shift), 0.0)
        + PARETO_CAMC_ALPHA_RHO * max(float(rho_bar), 0.0)
        + PARETO_CAMC_ALPHA_STATE * max(float(state_uncertainty), 0.0)
    )


def pareto_camc_gate(
    *,
    anchor_loss: float,
    candidate_loss: float,
    anchor_benefit: float,
    candidate_benefit: float,
    anchor_violation: float,
    candidate_violation: float,
    rho_loss_anchor: float,
    rho_loss_candidate: float,
    rho_benefit_anchor: float,
    rho_benefit_candidate: float,
    rho_violation_anchor: float,
    rho_violation_candidate: float,
    reference_shift: float,
    state_uncertainty: float,
    action_kind: str,
    extra_tau: float = 0.0,
    delta_b: float = PARETO_CAMC_DELTA_B,
    delta_v: float = PARETO_CAMC_DELTA_V,
) -> dict[str, float | bool | str]:
    """Return the conservative Pareto gate decision for leaving an anchor.

    The gate is deliberately one-sided: leaving the anchor requires certified
    workload improvement, near-noninferior benefit, and near-noninferior risk.
    """
    rho_loss_pair = float(rho_loss_anchor + rho_loss_candidate)
    rho_benefit_pair = float(rho_benefit_anchor + rho_benefit_candidate)
    rho_violation_pair = float(rho_violation_anchor + rho_violation_candidate)
    rho_bar = rho_loss_pair + rho_benefit_pair + rho_violation_pair
    tau = pareto_camc_threshold(reference_shift, rho_bar, state_uncertainty) + max(float(extra_tau), 0.0)
    delta_loss = float(anchor_loss - candidate_loss - rho_loss_pair)
    delta_benefit = float(candidate_benefit - anchor_benefit - rho_benefit_pair)
    delta_violation = float(candidate_violation - anchor_violation + rho_violation_pair)

    benefit_floor = -delta_b
    violation_ceiling = delta_v
    loss_threshold = tau
    if action_kind == "verify_down":
        benefit_floor = 0.0
        violation_ceiling = 0.0
    elif action_kind == "effort_down":
        loss_threshold = tau + 0.50 * max(-delta_benefit, 0.0)

    if delta_loss < loss_threshold:
        reason = "loss"
    elif delta_benefit < benefit_floor:
        reason = "benefit"
    elif delta_violation > violation_ceiling:
        reason = "violation"
    else:
        reason = "accepted"

    score = float(delta_loss + 0.25 * max(delta_benefit, 0.0) - 0.75 * max(delta_violation, 0.0))
    return {
        "accepted": reason == "accepted",
        "reject_reason": reason,
        "delta_loss": delta_loss,
        "delta_benefit": delta_benefit,
        "delta_violation": delta_violation,
        "tau": tau,
        "score": score,
    }


def camc_action_kind(anchor: tuple[int, float, int, float], candidate: tuple[int, float, int, float]) -> str:
    if float(candidate[1]) < float(anchor[1]) - 1e-9:
        return "verify_down"
    if int(candidate[0]) < int(anchor[0]):
        return "effort_down"
    return "neutral"


def camc_eval_metrics(evaluation: dict[str, float | bool], rho: float, reference_shift: float, state_uncertainty: float) -> dict[str, float]:
    failure_prob = float(evaluation["failure_prob"])
    certified_slack = float(evaluation["certified_slack"])
    headroom = float(evaluation["projected_runtime_headroom"])
    benefit = float(np.clip(1.0 - 0.45 * failure_prob + 0.06 * max(headroom, 0.0), 0.0, 1.2))
    violation = float(
        np.clip(
            failure_prob
            + 0.18 * max(-certified_slack, 0.0)
            + 0.03 * max(reference_shift, 0.0)
            + 0.02 * max(state_uncertainty, 0.0),
            0.0,
            1.5,
        )
    )
    radius_base = float(max(rho, 0.0) + 0.012 * max(reference_shift, 0.0) + 0.010 * max(state_uncertainty, 0.0))
    return {
        "loss": float(evaluation["surrogate_cost"]),
        "benefit": benefit,
        "violation": violation,
        "rho_loss": 0.45 * radius_base + 0.006,
        "rho_benefit": 0.18 * radius_base + 0.003,
        "rho_violation": 0.35 * radius_base + 0.004,
    }


def evaluate_certified_candidate(
    row: pd.Series,
    candidate_mode: int,
    candidate_verify: float,
    candidate_atoms: int,
    candidate_gain: float,
    predicted_risk: float,
    q_ver: float,
    q_state: float,
    ell: float,
    contamination: float,
    recovery_mass: float,
    diagnostic_debt: float,
    arrival_pressure: float,
    backlog_load: float,
    reference_shift: float,
    cert_amp: float,
    cert_loop: float,
    rho: float,
    exact_risk: float,
) -> dict[str, float | bool]:
    projected_debt = float(
        np.clip(
            0.82 * diagnostic_debt + 0.20 * (1.0 - candidate_verify) - 0.25 * candidate_verify,
            0.0,
            2.0,
        )
    )
    projected_headroom = float(
        compute_headrooms(
            row,
            q_state,
            ell,
            contamination,
            recovery_mass,
            projected_debt,
            backlog_load,
            rho,
            cert_amp,
            candidate_verify,
            candidate_atoms,
            False,
            exact_risk,
        )[candidate_mode]
    )
    candidate_failure_prob = expected_failure_prob(
        predicted_risk,
        q_state,
        contamination,
        diagnostic_debt,
        arrival_pressure,
        candidate_verify,
        candidate_atoms,
        candidate_gain,
        candidate_mode,
    )
    projected_state = project_action_state(
        row,
        candidate_mode,
        q_ver,
        ell,
        contamination,
        recovery_mass,
        diagnostic_debt,
        arrival_pressure,
        backlog_load,
        reference_shift,
        cert_amp,
        cert_loop,
        candidate_failure_prob,
        candidate_verify,
        candidate_atoms,
    )
    q_limit, ell_limit, l_limit, debt_limit, q_slack, ell_slack, l_slack, debt_slack = delta_limits(DELTA_SAFE)
    current_penalty = state_penalty(q_ver, ell, backlog_load, diagnostic_debt, DELTA_SAFE)
    projected_runtime_headroom = projected_state["service"] - (
        projected_state["nominal_load"] + projected_state["actual_recovery_load"]
    )
    headroom_slack = projected_headroom - (DELTA_SAFE + 0.50 * current_penalty)
    runtime_slack = projected_runtime_headroom - (DELTA_SAFE - 0.01)
    q_slack_value = (q_limit + q_slack) - projected_state["q"]
    ell_slack_value = (ell_limit + ell_slack) - projected_state["ell"]
    l_slack_value = (l_limit + l_slack) - projected_state["backlog"]
    debt_slack_value = (debt_limit + debt_slack) - projected_state["debt"]
    certified_slack = float(
        min(headroom_slack, runtime_slack, q_slack_value, ell_slack_value, l_slack_value, debt_slack_value)
    )
    accepted = bool(certified_slack >= 0.0)
    return {
        "accepted": accepted,
        "surrogate_cost": candidate_surrogate_value(
            candidate_mode,
            candidate_verify,
            candidate_atoms,
            candidate_gain,
            candidate_failure_prob,
            projected_headroom,
            reference_shift,
        ),
        "projected_headroom": projected_headroom,
        "projected_runtime_headroom": float(projected_runtime_headroom),
        "certified_slack": certified_slack,
        "failure_prob": float(candidate_failure_prob),
    }


def fit_runtime_models(manifest_dir: Path) -> dict:
    overlap = load_overlap(manifest_dir)
    _, overlap = fit_state_compression(overlap)
    train_std = standardize_from_train(overlap, overlap, TASK_FEATURE_COLS)

    step_target = np.log1p(overlap["trajectory_steps"].to_numpy(dtype=float))
    eval_target = np.log1p(overlap["eval_fail_mentions"].to_numpy(dtype=float))
    service_proxy = np.clip(
        0.95 - 0.003 * np.minimum(overlap["trajectory_steps"].to_numpy(dtype=float), 120.0) + 0.05 * overlap["exit_submit"].to_numpy(dtype=float),
        0.05,
        1.0,
    )
    success_target = overlap["target"].to_numpy(dtype=float)

    step_weights = ridge_fit(train_std[TASK_FEATURE_COLS].to_numpy(dtype=float), step_target, alpha=5.0)
    eval_weights = ridge_fit(train_std[TASK_FEATURE_COLS].to_numpy(dtype=float), eval_target, alpha=5.0)
    service_weights = ridge_fit(train_std[TASK_FEATURE_COLS].to_numpy(dtype=float), service_proxy, alpha=5.0)
    success_weights = ridge_fit(train_std[TASK_FEATURE_COLS].to_numpy(dtype=float), success_target, alpha=5.0)

    pred_steps = np.expm1(ridge_predict(train_std[TASK_FEATURE_COLS].to_numpy(dtype=float), step_weights))
    pred_evals = np.expm1(ridge_predict(train_std[TASK_FEATURE_COLS].to_numpy(dtype=float), eval_weights))
    pred_service = ridge_predict(train_std[TASK_FEATURE_COLS].to_numpy(dtype=float), service_weights)
    pred_success = ridge_predict(train_std[TASK_FEATURE_COLS].to_numpy(dtype=float), success_weights)

    step_resid = step_target - np.log1p(np.maximum(pred_steps, 0.0))
    eval_resid = eval_target - np.log1p(np.maximum(pred_evals, 0.0))
    service_resid = service_proxy - pred_service
    success_resid = success_target - pred_success

    codetrace = pd.read_csv(manifest_paths(manifest_dir)["codetrace_manifest"])
    difficulty_amp = {}
    for difficulty in ["easy", "medium", "hard"]:
        bucket = codetrace[codetrace["difficulty"].str.lower() == difficulty].copy()
        if len(bucket) == 0:
            continue
        difficulty_amp[difficulty] = float((bucket["incorrect_stage_ratio"] + bucket["unuseful_stage_ratio"]).mean())

    default_amp = float((codetrace["incorrect_stage_ratio"] + codetrace["unuseful_stage_ratio"]).mean())
    incorrect_self_loop = float(
        codetrace.loc[codetrace["incorrect_stage_ratio"] > 0, "incorrect_stage_ratio"].mean()
    )

    return {
        "means": {column: float(overlap[column].mean()) for column in TASK_FEATURE_COLS},
        "stds": {column: float(overlap[column].std(ddof=0)) for column in TASK_FEATURE_COLS},
        "step_weights": step_weights.tolist(),
        "eval_weights": eval_weights.tolist(),
        "service_weights": service_weights.tolist(),
        "success_weights": success_weights.tolist(),
        "step_p95": float(np.quantile(overlap["trajectory_steps"], 0.95)),
        "eval_p95": float(np.quantile(overlap["eval_fail_mentions"], 0.95)),
        "rho_base": float(
            0.5 * (
                np.std(step_resid, ddof=0)
                + np.std(eval_resid, ddof=0)
                + np.std(service_resid, ddof=0)
                + np.std(success_resid, ddof=0)
            )
        ),
        "difficulty_amp": difficulty_amp,
        "default_amp": default_amp,
        "incorrect_self_loop": incorrect_self_loop if np.isfinite(incorrect_self_loop) else 0.12,
    }


def apply_runtime_models(tasks: pd.DataFrame, risk_prior: dict, atom_prior: dict, runtime_models: dict) -> pd.DataFrame:
    frame = apply_priors(tasks, risk_prior, atom_prior)
    standardized = frame.copy()
    for column in TASK_FEATURE_COLS:
        mean = runtime_models["means"][column]
        std = runtime_models["stds"][column]
        standardized[column] = 0.0 if std == 0 or np.isnan(std) else (standardized[column] - mean) / std

    features = standardized[TASK_FEATURE_COLS].to_numpy(dtype=float)
    frame["pred_steps"] = np.expm1(ridge_predict(features, np.asarray(runtime_models["step_weights"], dtype=float)))
    frame["pred_eval_fails"] = np.expm1(ridge_predict(features, np.asarray(runtime_models["eval_weights"], dtype=float)))
    frame["base_service"] = np.clip(
        ridge_predict(features, np.asarray(runtime_models["service_weights"], dtype=float)),
        0.12,
        1.05,
    )
    frame["pred_success"] = clip_probabilities(
        ridge_predict(features, np.asarray(runtime_models["success_weights"], dtype=float))
    )
    frame["step_norm"] = np.clip(frame["pred_steps"] / max(runtime_models["step_p95"], 1.0), 0.0, 2.5)
    frame["eval_norm"] = np.clip(frame["pred_eval_fails"] / max(runtime_models["eval_p95"], 1.0), 0.0, 2.5)
    score_cols = [f"{atom}__score" for atom in ATOM_COLS]
    frame["score_list"] = frame[score_cols].apply(lambda row: [float(value) for value in row], axis=1)
    return frame


def mean_abs_feature_shift(reference: pd.DataFrame, frame: pd.DataFrame) -> float:
    deltas = []
    for column in TASK_FEATURE_COLS:
        ref_mean = float(reference[column].mean())
        ref_std = float(reference[column].std(ddof=0))
        delta = float(frame[column].mean()) - ref_mean
        deltas.append(0.0 if ref_std == 0 or np.isnan(ref_std) else abs(delta / ref_std))
    return float(np.mean(deltas))


def logit(value: float) -> float:
    value = min(max(value, 1e-6), 1 - 1e-6)
    return float(np.log(value / (1 - value)))


def context_capacity(ell: float) -> int:
    return max(0, 3 - int(np.floor(ell)))


def difficulty_amp(row: pd.Series, runtime_models: dict) -> float:
    difficulty = str(row.get("difficulty", "")).lower()
    return float(runtime_models["difficulty_amp"].get(difficulty, runtime_models["default_amp"]))


def certificate_amp_mean(controller: str, amp_mean: float) -> float:
    """Ablations can intentionally omit recovery amplification from the certificate."""
    if controller in {"headroom_only", "rsrc_no_recovery"}:
        return 0.0
    return amp_mean


def certificate_self_loop(controller: str, runtime_models: dict) -> float:
    if controller in {"headroom_only", "rsrc_no_recovery"}:
        return 0.0
    return float(runtime_models["incorrect_self_loop"])


def compute_headrooms(
    row: pd.Series,
    q_state: float,
    ell: float,
    contamination: float,
    recovery_mass: float,
    diagnostic_debt: float,
    backlog_load: float,
    rho: float,
    amp_mean: float,
    verify: float,
    atoms_selected: int,
    use_exact_risk: bool,
    exact_risk: float,
) -> np.ndarray:
    e_anchor = exact_risk if use_exact_risk else min(0.99, float(row["e_proxy"]) + rho)
    e_anchor = float(
        np.clip(
            e_anchor
            + 0.18 * (1.0 - verify)
            - 0.05 * verify
            + 0.10 * min(diagnostic_debt, 1.5)
            + 0.06 * min(backlog_load, 1.5),
            0.02,
            0.99,
        )
    )
    step_norm = float(row["step_norm"])
    eval_norm = float(row["eval_norm"])
    nominal_upper = (
        0.12
        + 0.18 * float(row["d_proxy"])
        + 0.10 * q_state
        + 0.05 * step_norm
        + 0.04 * verify
        + 0.02 * atoms_selected
        + 0.06 * min(diagnostic_debt, 1.5)
        + 0.08 * min(backlog_load, 1.5)
    )
    recovery_upper = e_anchor * (
        0.12
        + 0.12 * amp_mean
        + 0.10 * eval_norm
        + 0.06 * contamination
        + 0.12 * min(recovery_mass, 1.5)
        + 0.08 * min(diagnostic_debt, 1.5)
        + 0.05 * min(backlog_load, 1.5)
    )
    headrooms = []
    for mode in GOVERNANCE_MODES:
        lower_service = np.clip(
            float(row["base_service"]) * mode.service_floor
            - 0.08 * q_state
            - 0.05 * ell
            - 0.08 * min(recovery_mass, 1.5)
            - 0.05 * min(diagnostic_debt, 1.5)
            - 0.04 * min(backlog_load, 1.5)
            - rho,
            0.05,
            1.0,
        )
        headrooms.append(lower_service - (nominal_upper + mode.recovery_multiplier * recovery_upper))
    return np.asarray(headrooms, dtype=float)

def select_context_counts(
    controller: str,
    surrogate_scores: list[float],
    true_scores: np.ndarray,
    ell: float,
    safe_headroom: float,
) -> tuple[int, float]:
    capacity = context_capacity(ell)
    if capacity <= 0:
        return 0, 0.0

    surrogate_sorted = sorted(surrogate_scores, reverse=True)
    true_sorted = np.sort(true_scores)[::-1]
    if controller == "oracle_src":
        chosen = [score for score in true_sorted[:capacity] if score > 0]
    elif controller in {"minimal_verify", "rsrc_no_context", "headroom_only"}:
        if controller in {"rsrc_no_context", "headroom_only"}:
            return 0, 0.0
        chosen = [score for score in surrogate_sorted[: min(1, capacity)] if score > 0]
    elif controller == "maxweight_backlog":
        chosen = [score for score in surrogate_sorted[: min(1, capacity)] if score > 0.02]
    elif controller == "adaptive_threshold":
        chosen = [score for score in surrogate_sorted[: min(2, capacity)] if score > 0.03]
    elif controller == "always_verify_throttle":
        chosen = [score for score in surrogate_sorted[: min(1, capacity)] if score > 0.0]
    else:
        margin = 0.05 if controller in {"rsrc", "se_mpc", "static_conservative", "rsrc_no_recovery"} or controller in CAMC_CONTROLLERS else 0.0
        chosen = [score for score in surrogate_sorted[: min(2, capacity)] if score - margin > 0]
        if controller in {"se_mpc", "camc_sempc_candidate", "pareto_camc_sempc_candidate"} and safe_headroom > 0.10:
            chosen = [score for score in surrogate_sorted[:capacity] if score > -0.02]
    return len(chosen), float(sum(chosen))


def pick_mode(
    controller: str,
    headrooms: np.ndarray,
    exact_headrooms: np.ndarray,
    q_state: float,
    predicted_safe_mask: np.ndarray | None = None,
    predicted_perf_mask: np.ndarray | None = None,
    exact_safe_mask: np.ndarray | None = None,
) -> tuple[int, bool, bool]:
    safe_headrooms = exact_headrooms if controller == "oracle_src" else headrooms
    safe_mask = exact_safe_mask if controller == "oracle_src" and exact_safe_mask is not None else predicted_safe_mask
    perf_mask = predicted_perf_mask
    if safe_mask is None:
        safe_mask = safe_headrooms >= DELTA_SAFE
    if perf_mask is None:
        perf_mask = safe_headrooms >= DELTA_PERF
    safe_indices = np.flatnonzero(np.asarray(safe_mask, dtype=bool))
    safe_perf = np.flatnonzero(np.asarray(perf_mask, dtype=bool))

    if controller == "static_conservative":
        return len(GOVERNANCE_MODES) - 1, True, True
    if controller == "static_aggressive":
        return 0, bool(len(safe_indices)), bool(len(safe_perf))
    if controller == "greedy_myopic":
        return (1 if q_state > 0.75 else 0), bool(len(safe_indices)), bool(len(safe_perf))
    if controller == "plain_mpc":
        return int(np.argmin(np.abs(headrooms))), bool(len(safe_indices)), bool(len(safe_perf))
    if controller == "always_verify_throttle":
        if len(safe_indices) > 0:
            target = 3 if q_state > 0.75 else 2
            feasible = [idx for idx in safe_indices.tolist() if idx >= target]
            return int(feasible[0] if feasible else safe_indices[-1]), True, bool(len(safe_perf))
        return len(GOVERNANCE_MODES) - 1, False, False
    if controller == "maxweight_backlog":
        target = 3 if q_state > 0.85 or np.nanmax(safe_headrooms) < DELTA_SAFE else 1
        feasible = [idx for idx in safe_indices.tolist() if idx >= target]
        if feasible:
            return int(feasible[0]), True, bool(len(safe_perf))
        if len(safe_indices) > 0:
            return int(safe_indices[-1]), True, bool(len(safe_perf))
        return len(GOVERNANCE_MODES) - 1, False, False

    if len(safe_indices) == 0:
        return len(GOVERNANCE_MODES) - 1, False, False
    return int(safe_indices[0]), True, bool(len(safe_perf))


def simulate_seed(
    tasks: pd.DataFrame,
    dataset_name: str,
    controller: str,
    runtime_models: dict,
    seed: int,
    horizon: int,
    reference_shift: float,
) -> tuple[dict, list[dict], list[dict]]:
    rng = np.random.default_rng(seed + 991)
    indices = rng.integers(0, len(tasks), size=horizon)

    L = 0.0
    q_ver = 0.0
    ell = 0.0
    contamination = 0.0
    recovery_mass = 0.0
    diagnostic_debt = 0.0
    arrival_pressure = 0.0
    observation_count = 24.0

    discounted_cost = 0.0
    discount_mass = 0.0
    safe_steps = 0
    perf_steps = 0
    benchmark_safe_steps = 0
    benchmark_action_safe_steps = 0
    overload_steps = 0
    fallback_steps = 0
    safe_nonempty_steps = 0
    exact_safe_nonempty_steps = 0
    benchmark_action_nonempty_steps = 0
    verify_steps = 0.0
    high_effort_steps = 0
    max_effort_steps = 0
    atom_steps = 0.0
    workload_total = 0.0
    load_violation_steps = 0
    service_violation_steps = 0
    negative_drift_outside = 0
    outside_steps = 0
    success_steps = 0.0
    context_total = 0.0
    q_total = 0.0
    recovery_total = 0.0
    debt_total = 0.0
    arrival_total = 0.0
    theta_precision_hits = 0
    theta_precision_total = 0
    theta_recall_hits = 0
    theta_recall_total = 0
    theta_benchmark_precision_hits = 0
    theta_benchmark_precision_total = 0
    theta_benchmark_recall_hits = 0
    theta_benchmark_recall_total = 0
    action_safe_hits = 0
    action_safe_total = 0
    predicted_safe_hits = 0
    predicted_safe_total = 0
    benchmark_safe_total = 0
    mode_counter: Counter[str] = Counter()
    drift_records: list[dict] = []
    excursion_lengths: list[int] = []
    excursion_open = False
    excursion_len = 0
    mpc_eligible_steps = 0
    mpc_activation_steps = 0
    mpc_fallback_to_rsrc_steps = 0
    mpc_candidate_steps = 0
    mpc_candidate_total = 0
    mpc_rejected_total = 0
    mpc_verify_down_steps = 0
    mpc_verify_up_steps = 0
    mpc_atom_up_steps = 0
    mpc_mode_switch_steps = 0
    mpc_surrogate_improvement_total = 0.0
    camc_evaluation_steps = 0
    camc_activation_steps = 0
    camc_anchor_preservation_steps = 0
    camc_candidate_steps = 0
    camc_candidate_total = 0
    camc_rejected_total = 0
    camc_post_switch_total = 0
    camc_post_switch_violation_steps = 0
    camc_margin_total = 0.0
    camc_activated_margin_total = 0.0
    camc_rejected_margin_total = 0.0
    camc_anchor_value_total = 0.0
    camc_best_candidate_value_total = 0.0
    camc_reject_safety_total = 0
    camc_reject_loss_total = 0
    camc_reject_benefit_total = 0
    camc_reject_violation_total = 0
    camc_records: list[dict] = []
    camc_hysteresis_cooldown = 0

    previous_safe = True
    for t, index in enumerate(indices):
        if camc_hysteresis_cooldown > 0:
            camc_hysteresis_cooldown -= 1
        camc_step_evaluated = False
        camc_step_activated = False
        camc_step_margin = float("nan")
        camc_step_slack = float("nan")
        camc_step_anchor_value = float("nan")
        camc_step_candidate_value = float("nan")
        camc_step_rejected = 0
        camc_step_reject_safety = 0
        camc_step_reject_loss = 0
        camc_step_reject_benefit = 0
        camc_step_reject_violation = 0
        camc_step_delta_loss = float("nan")
        camc_step_delta_benefit = float("nan")
        camc_step_delta_violation = float("nan")
        camc_step_tau = float("nan")
        camc_step_candidate_count = 0
        row = tasks.iloc[int(index)]
        rho = runtime_models["rho_base"] / np.sqrt(max(observation_count, 1.0))
        amp_mean = difficulty_amp(row, runtime_models)
        cert_amp = certificate_amp_mean(controller, amp_mean)
        cert_loop = certificate_self_loop(controller, runtime_models)
        hidden_shift = (
            0.08 * reference_shift
            + 0.05 * contamination
            + 0.10 * min(recovery_mass, 1.5)
            + 0.08 * min(diagnostic_debt, 1.5)
            + 0.04 * min(arrival_pressure, 1.5)
        )
        exact_risk = clip_probabilities(
            np.asarray(
                [
                    sigmoid(
                        logit(float(row["e_proxy"]))
                        + hidden_shift
                        + 0.10 * float(row["step_norm"])
                        + 0.05 * float(row["eval_norm"])
                        + rng.normal(0.0, 0.18)
                    )
                ]
            )
        )[0]

        q_state = float(np.clip(0.55 * float(row["q_proxy"]) + 0.25 * q_ver + 0.20 * diagnostic_debt, 0.0, 1.8))
        raw_scores = np.asarray(row["score_list"], dtype=float)
        true_scores = (
            raw_scores
            - 0.03 * ell
            - 0.04 * q_state
            - 0.03 * contamination
            - 0.04 * diagnostic_debt
            - 0.03 * arrival_pressure
            + rng.normal(0.0, 0.03, size=len(raw_scores))
        )
        surrogate_scores = (raw_scores - rho - 0.02 * ell - 0.03 * q_state - 0.03 * diagnostic_debt).tolist()

        conservative_d = float(np.clip(float(row["d_proxy"]) + 0.05 + 0.25 * rho, 0.0, 1.0))
        rsrc_verify = verification_effort(min(0.99, float(row["e_proxy"]) + rho), conservative_d, q_state)
        exact_verify = verification_effort(exact_risk, float(row["d_proxy"]), q_state)

        if controller == "always_verify":
            verify = 1.0
        elif controller == "always_verify_throttle":
            verify = 1.0
        elif controller == "minimal_verify":
            verify = 0.0
        elif controller == "oracle_src":
            verify = exact_verify
        elif controller == "greedy_myopic":
            verify = verification_effort(
                min(0.99, float(row["e_proxy"]) + 0.03),
                float(np.clip(float(row["d_proxy"]) + 0.02, 0.0, 1.0)),
                max(q_state - 0.08, 0.0),
            )
        elif controller == "plain_mpc":
            verify = shift_effort(rsrc_verify, -1)
        elif controller == "adaptive_threshold":
            verify = verification_effort(
                min(0.99, float(row["e_proxy"]) + 0.02),
                float(np.clip(float(row["d_proxy"]) + 0.01, 0.0, 1.0)),
                max(q_state - 0.05, 0.0),
            )
        elif controller == "maxweight_backlog":
            pressure = 0.45 * L + 0.25 * q_ver + 0.20 * diagnostic_debt + 0.10 * recovery_mass
            verify = shift_effort(rsrc_verify, +1 if pressure > 0.80 else 0)
        else:
            verify = rsrc_verify

        atoms_selected, context_gain = select_context_counts(controller, surrogate_scores, true_scores, ell, 0.0)
        predicted_risk = estimated_risk_anchor(
            row,
            rho,
            contamination,
            diagnostic_debt,
            arrival_pressure,
            reference_shift,
        )
        exact_headrooms = compute_headrooms(
            row,
            q_state,
            ell,
            contamination,
            recovery_mass,
            diagnostic_debt,
            L,
            0.0,
            amp_mean,
            exact_verify,
            atoms_selected if controller == "oracle_src" else 0,
            True,
            exact_risk,
        )
        cert_headrooms = compute_headrooms(
            row,
            q_state,
            ell,
            contamination,
            recovery_mass,
            diagnostic_debt,
            L,
            rho,
            cert_amp,
            verify,
            atoms_selected,
            False,
            exact_risk,
        )
        predicted_safe_mask = action_safe_mask(
            cert_headrooms,
            row,
            predicted_risk,
            q_ver,
            q_state,
            ell,
            contamination,
            recovery_mass,
            diagnostic_debt,
            arrival_pressure,
            L,
            reference_shift,
            cert_amp,
            cert_loop,
            verify,
            atoms_selected,
            context_gain,
            DELTA_SAFE,
        )
        predicted_perf_mask = action_safe_mask(
            cert_headrooms,
            row,
            predicted_risk,
            q_ver,
            q_state,
            ell,
            contamination,
            recovery_mass,
            diagnostic_debt,
            arrival_pressure,
            L,
            reference_shift,
            cert_amp,
            cert_loop,
            verify,
            atoms_selected,
            context_gain,
            DELTA_PERF,
        )
        exact_safe_mask = action_safe_mask(
            exact_headrooms,
            row,
            exact_risk,
            q_ver,
            q_state,
            ell,
            contamination,
            recovery_mass,
            diagnostic_debt,
            arrival_pressure,
            L,
            reference_shift,
            amp_mean,
            runtime_models["incorrect_self_loop"],
            exact_verify if controller == "oracle_src" else verify,
            atoms_selected,
            context_gain,
            DELTA_SAFE,
        )
        mode_idx, safe_nonempty, perf_nonempty = pick_mode(
            controller,
            cert_headrooms,
            exact_headrooms,
            q_state,
            predicted_safe_mask=predicted_safe_mask,
            predicted_perf_mask=predicted_perf_mask,
            exact_safe_mask=exact_safe_mask,
        )
        safe_nonempty = bool(predicted_safe_mask.any()) if controller != "oracle_src" else bool(exact_safe_mask.any())
        perf_nonempty = bool(predicted_perf_mask.any()) if controller != "oracle_src" else bool(
            action_safe_mask(
                exact_headrooms,
                row,
                exact_risk,
                q_ver,
                q_state,
                ell,
                contamination,
                recovery_mass,
                diagnostic_debt,
                arrival_pressure,
                L,
                reference_shift,
                amp_mean,
                runtime_models["incorrect_self_loop"],
                exact_verify,
                atoms_selected,
                context_gain,
                DELTA_PERF,
            ).any()
        )
        exact_safe_nonempty = bool(exact_safe_mask.any())
        fallback = bool((controller in {"rsrc", "se_mpc"} or controller in ABLATION_CONTROLLERS or controller in CAMC_CONTROLLERS) and not safe_nonempty)
        chosen_headrooms = exact_headrooms if controller == "oracle_src" else cert_headrooms
        safe_headroom = float(chosen_headrooms[mode_idx])
        inside_safe = bool(exact_safe_mask[mode_idx] if controller == "oracle_src" else predicted_safe_mask[mode_idx])
        inside_perf = bool((action_safe_mask(
            chosen_headrooms,
            row,
            exact_risk if controller == "oracle_src" else predicted_risk,
            q_ver,
            q_state,
            ell,
            contamination,
            recovery_mass,
            diagnostic_debt,
            arrival_pressure,
            L,
            reference_shift,
            amp_mean if controller == "oracle_src" else cert_amp,
            runtime_models["incorrect_self_loop"] if controller == "oracle_src" else cert_loop,
            exact_verify if controller == "oracle_src" else verify,
            atoms_selected,
            context_gain,
            DELTA_PERF,
        ))[mode_idx])

        atoms_selected, context_gain = select_context_counts(controller, surrogate_scores, true_scores, ell, safe_headroom)
        chosen_headrooms = compute_headrooms(
            row,
            q_state,
            ell,
            contamination,
            recovery_mass,
            diagnostic_debt,
            L,
            0.0 if controller == "oracle_src" else rho,
            amp_mean if controller == "oracle_src" else cert_amp,
            verify,
            atoms_selected,
            controller == "oracle_src",
            exact_risk,
        )
        recomputed_exact_headrooms = compute_headrooms(
            row,
            q_state,
            ell,
            contamination,
            recovery_mass,
            diagnostic_debt,
            L,
            0.0,
            amp_mean,
            exact_verify if controller == "oracle_src" else verify,
            atoms_selected,
            True,
            exact_risk,
        )
        predicted_safe_mask = action_safe_mask(
            chosen_headrooms,
            row,
            predicted_risk,
            q_ver,
            q_state,
            ell,
            contamination,
            recovery_mass,
            diagnostic_debt,
            arrival_pressure,
            L,
            reference_shift,
            cert_amp,
            cert_loop,
            verify,
            atoms_selected,
            context_gain,
            DELTA_SAFE,
        )
        predicted_perf_mask = action_safe_mask(
            chosen_headrooms,
            row,
            predicted_risk,
            q_ver,
            q_state,
            ell,
            contamination,
            recovery_mass,
            diagnostic_debt,
            arrival_pressure,
            L,
            reference_shift,
            cert_amp,
            cert_loop,
            verify,
            atoms_selected,
            context_gain,
            DELTA_PERF,
        )
        exact_safe_mask = action_safe_mask(
            recomputed_exact_headrooms,
            row,
            exact_risk,
            q_ver,
            q_state,
            ell,
            contamination,
            recovery_mass,
            diagnostic_debt,
            arrival_pressure,
            L,
            reference_shift,
            amp_mean,
            runtime_models["incorrect_self_loop"],
            exact_verify if controller == "oracle_src" else verify,
            atoms_selected,
            context_gain,
            DELTA_SAFE,
        )
        safe_headroom = float(chosen_headrooms[mode_idx])
        inside_safe = bool(exact_safe_mask[mode_idx] if controller == "oracle_src" else predicted_safe_mask[mode_idx])
        inside_perf = bool(
            (
                action_safe_mask(
                    recomputed_exact_headrooms,
                    row,
                    exact_risk,
                    q_ver,
                    q_state,
                    ell,
                    contamination,
                    recovery_mass,
                    diagnostic_debt,
                    arrival_pressure,
                    L,
                    reference_shift,
                    amp_mean,
                    runtime_models["incorrect_self_loop"],
                    exact_verify,
                    atoms_selected,
                    context_gain,
                    DELTA_PERF,
                )
                if controller == "oracle_src"
                else predicted_perf_mask
            )[mode_idx]
        )
        safe_nonempty = bool(predicted_safe_mask.any()) if controller != "oracle_src" else bool(exact_safe_mask.any())
        exact_safe_nonempty = bool(exact_safe_mask.any())
        fallback = bool((controller in {"rsrc", "se_mpc"} or controller in ABLATION_CONTROLLERS or controller in CAMC_CONTROLLERS) and not safe_nonempty)
        if controller == "se_mpc":
            if not inside_safe:
                mpc_fallback_to_rsrc_steps += 1
                verify = rsrc_verify
                atoms_selected, context_gain = select_context_counts("rsrc", surrogate_scores, true_scores, ell, float(cert_headrooms[mode_idx]))
                fallback = fallback or not safe_nonempty
            elif inside_perf:
                mpc_eligible_steps += 1
                base_mode = mode_idx
                base_verify = verify
                base_atoms = atoms_selected
                candidates = [(mode_idx, verify, atoms_selected, context_gain)]
                if mode_idx > 0 and cert_headrooms[mode_idx - 1] >= DELTA_SAFE:
                    extra_atoms, extra_gain = select_context_counts("se_mpc", surrogate_scores, true_scores, ell, float(cert_headrooms[mode_idx - 1]))
                    candidates.append((mode_idx - 1, verify, extra_atoms, extra_gain))
                if verify > 0 and cert_headrooms[mode_idx] >= 0.10:
                    candidates.append((mode_idx, shift_effort(verify, -1), atoms_selected, context_gain))
                if verify < float(EFFORT_LEVELS[-1]) and cert_headrooms[mode_idx] >= 0.14:
                    candidates.append((mode_idx, shift_effort(verify, +1), atoms_selected, context_gain))
                if atoms_selected < context_capacity(ell) and cert_headrooms[mode_idx] >= 0.10:
                    candidates.append((mode_idx, verify, atoms_selected + 1, context_gain + 0.03))

                best_candidate = candidates[0]
                best_value = float("inf")
                baseline_value = float("inf")
                rejected_candidates = 0
                for candidate_mode, candidate_verify, candidate_atoms, candidate_gain in candidates:
                    projected_q = max(0.0, 0.68 * q_ver + 0.15 * candidate_verify + 0.10 * diagnostic_debt - 0.15 * GOVERNANCE_MODES[candidate_mode].verification_bias)
                    projected_ell = float(np.clip(0.55 * ell + candidate_atoms - 0.25 - 0.35 * GOVERNANCE_MODES[candidate_mode].verification_bias, 0.0, 3.5))
                    projected_debt = float(np.clip(0.82 * diagnostic_debt + 0.20 * (1.0 - candidate_verify) - 0.25 * candidate_verify, 0.0, 2.0))
                    projected_headroom = float(
                        compute_headrooms(
                            row,
                            q_state,
                            ell,
                            contamination,
                            recovery_mass,
                            projected_debt,
                            L,
                            rho,
                            cert_amp,
                            candidate_verify,
                            candidate_atoms,
                            False,
                            exact_risk,
                        )[candidate_mode]
                    )
                    candidate_failure_prob = expected_failure_prob(
                        predicted_risk,
                        q_state,
                        contamination,
                        diagnostic_debt,
                        arrival_pressure,
                        candidate_verify,
                        candidate_atoms,
                        candidate_gain,
                        candidate_mode,
                    )
                    projected_state = project_action_state(
                        row,
                        candidate_mode,
                        q_ver,
                        ell,
                        contamination,
                        recovery_mass,
                        diagnostic_debt,
                        arrival_pressure,
                        L,
                        reference_shift,
                        cert_amp,
                        cert_loop,
                        candidate_failure_prob,
                        candidate_verify,
                        candidate_atoms,
                    )
                    q_limit, ell_limit, l_limit, debt_limit, q_slack, ell_slack, l_slack, debt_slack = delta_limits(DELTA_SAFE)
                    projected_runtime_headroom = projected_state["service"] - (
                        projected_state["nominal_load"] + projected_state["actual_recovery_load"]
                    )
                    if not (
                        projected_headroom >= (DELTA_SAFE + 0.50 * state_penalty(q_ver, ell, L, diagnostic_debt, DELTA_SAFE))
                        and projected_runtime_headroom >= (DELTA_SAFE - 0.01)
                        and projected_state["q"] <= (q_limit + q_slack)
                        and projected_state["ell"] <= (ell_limit + ell_slack)
                        and projected_state["backlog"] <= (l_limit + l_slack)
                        and projected_state["debt"] <= (debt_limit + debt_slack)
                    ):
                        rejected_candidates += 1
                        continue
                    surrogate_cost = (
                        0.42 * candidate_verify
                        + 0.15 * candidate_atoms
                        - 0.55 * candidate_gain
                        - 0.60 * projected_headroom
                        + 0.12 * candidate_mode
                    )
                    if (candidate_mode, candidate_verify, candidate_atoms, candidate_gain) == candidates[0]:
                        baseline_value = surrogate_cost
                    if surrogate_cost < best_value:
                        best_value = surrogate_cost
                        best_candidate = (candidate_mode, candidate_verify, candidate_atoms, candidate_gain)
                mpc_candidate_steps += 1
                mpc_candidate_total += len(candidates)
                mpc_rejected_total += rejected_candidates
                mode_idx, verify, atoms_selected, context_gain = best_candidate
                if np.isfinite(baseline_value) and np.isfinite(best_value):
                    improvement = max(0.0, baseline_value - best_value)
                    mpc_surrogate_improvement_total += improvement
                    if improvement > 1e-9 or best_candidate != candidates[0]:
                        mpc_activation_steps += 1
                if verify < base_verify:
                    mpc_verify_down_steps += 1
                if verify > base_verify:
                    mpc_verify_up_steps += 1
                if atoms_selected > base_atoms:
                    mpc_atom_up_steps += 1
                if base_mode != mode_idx:
                    mpc_mode_switch_steps += 1
                chosen_headrooms = compute_headrooms(
                    row,
                    q_state,
                    ell,
                    contamination,
                    recovery_mass,
                    diagnostic_debt,
                    L,
                    rho,
                    cert_amp,
                    verify,
                    atoms_selected,
                    False,
                    exact_risk,
                )
                predicted_safe_mask = action_safe_mask(
                    chosen_headrooms,
                    row,
                    predicted_risk,
                    q_ver,
                    q_state,
                    ell,
                    contamination,
                    recovery_mass,
                    diagnostic_debt,
                    arrival_pressure,
                    L,
                    reference_shift,
                    cert_amp,
                    cert_loop,
                    verify,
                    atoms_selected,
                    context_gain,
                    DELTA_SAFE,
                )
                predicted_perf_mask = action_safe_mask(
                    chosen_headrooms,
                    row,
                    predicted_risk,
                    q_ver,
                    q_state,
                    ell,
                    contamination,
                    recovery_mass,
                    diagnostic_debt,
                    arrival_pressure,
                    L,
                    reference_shift,
                    cert_amp,
                    cert_loop,
                    verify,
                    atoms_selected,
                    context_gain,
                    DELTA_PERF,
                )
                safe_headroom = float(chosen_headrooms[mode_idx])
                inside_safe = bool(predicted_safe_mask[mode_idx])
                inside_perf = bool(predicted_perf_mask[mode_idx])
                if base_mode != mode_idx:
                    mode_counter["se_mpc_mode_switch"] += 1

        if controller in CAMC_CONTROLLERS:
            camc_evaluation_steps += 1
            camc_step_evaluated = True

            rsrc_mode = mode_idx
            rsrc_atoms = atoms_selected
            rsrc_gain = context_gain
            static_mode = len(GOVERNANCE_MODES) - 1
            static_atoms, static_gain = select_context_counts(
                "static_conservative",
                surrogate_scores,
                true_scores,
                ell,
                float(cert_headrooms[static_mode]),
            )

            use_pareto_gate = controller in PARETO_CAMC_CONTROLLERS
            if controller in {"camc_rsrc_anchor", "pareto_camc_rsrc_anchor"} and reference_shift < 0.75:
                anchor = (rsrc_mode, verify, rsrc_atoms, rsrc_gain)
            else:
                anchor = (static_mode, rsrc_verify, static_atoms, static_gain)

            candidates: list[tuple[int, float, int, float]] = [anchor]

            def add_candidate(candidate: tuple[int, float, int, float]) -> None:
                key = (candidate[0], round(float(candidate[1]), 6), int(candidate[2]))
                existing = {(item[0], round(float(item[1]), 6), int(item[2])) for item in candidates}
                if key not in existing:
                    candidates.append(candidate)

            add_candidate((rsrc_mode, verify, rsrc_atoms, rsrc_gain))
            if controller in {"camc_rsrc_anchor", "camc_sempc_candidate", "pareto_camc_rsrc_anchor", "pareto_camc_sempc_candidate"}:
                if rsrc_mode > 0 and cert_headrooms[rsrc_mode - 1] >= DELTA_SAFE:
                    relaxed_atoms, relaxed_gain = select_context_counts(
                        "camc_sempc_candidate",
                        surrogate_scores,
                        true_scores,
                        ell,
                        float(cert_headrooms[rsrc_mode - 1]),
                    )
                    add_candidate((rsrc_mode - 1, verify, relaxed_atoms, relaxed_gain))
                if verify > 0 and cert_headrooms[rsrc_mode] >= 0.10:
                    add_candidate((rsrc_mode, shift_effort(verify, -1), rsrc_atoms, rsrc_gain))
                if verify < float(EFFORT_LEVELS[-1]) and cert_headrooms[rsrc_mode] >= 0.14:
                    add_candidate((rsrc_mode, shift_effort(verify, +1), rsrc_atoms, rsrc_gain))
                if rsrc_atoms < context_capacity(ell) and cert_headrooms[rsrc_mode] >= 0.10:
                    add_candidate((rsrc_mode, verify, rsrc_atoms + 1, rsrc_gain + 0.03))

            anchor_eval = evaluate_certified_candidate(
                row,
                anchor[0],
                anchor[1],
                anchor[2],
                anchor[3],
                predicted_risk,
                q_ver,
                q_state,
                ell,
                contamination,
                recovery_mass,
                diagnostic_debt,
                arrival_pressure,
                L,
                reference_shift,
                cert_amp,
                cert_loop,
                rho,
                exact_risk,
            )
            camc_step_anchor_value = float(anchor_eval["surrogate_cost"])
            camc_step_slack = float(anchor_eval["certified_slack"])
            camc_anchor_value_total += camc_step_anchor_value
            anchor_metrics = camc_eval_metrics(anchor_eval, rho, reference_shift, state_uncertainty=0.0)

            best_candidate = anchor
            best_eval = anchor_eval
            best_gate: dict[str, float | bool | str] | None = None
            rejected_candidates = 0
            rejected_margin_sum = 0.0
            state_uncertainty = state_penalty(q_ver, ell, L, diagnostic_debt, DELTA_SAFE)
            anchor_metrics = camc_eval_metrics(anchor_eval, rho, reference_shift, state_uncertainty)
            gate_penalty = CAMC_TAU + 0.70 * rho + 0.025 * reference_shift + 0.015 * state_uncertainty
            if controller == "camc_static_anchor":
                gate_penalty += 0.22 + 0.02 * reference_shift
            hysteresis_extra_tau = PARETO_CAMC_HYSTERESIS_TAU if use_pareto_gate and camc_hysteresis_cooldown > 0 else 0.0

            if safe_nonempty and bool(anchor_eval["accepted"]):
                for candidate in candidates[1:]:
                    candidate_eval = evaluate_certified_candidate(
                        row,
                        candidate[0],
                        candidate[1],
                        candidate[2],
                        candidate[3],
                        predicted_risk,
                        q_ver,
                        q_state,
                        ell,
                        contamination,
                        recovery_mass,
                        diagnostic_debt,
                        arrival_pressure,
                        L,
                        reference_shift,
                        cert_amp,
                        cert_loop,
                        rho,
                        exact_risk,
                    )
                    candidate_metrics = camc_eval_metrics(candidate_eval, rho, reference_shift, state_uncertainty)
                    raw_margin = float(anchor_eval["surrogate_cost"]) - float(candidate_eval["surrogate_cost"]) - gate_penalty
                    if not bool(candidate_eval["accepted"]):
                        rejected_candidates += 1
                        camc_step_reject_safety += 1
                        rejected_margin_sum += raw_margin
                        continue
                    if use_pareto_gate:
                        if candidate_metrics["benefit"] - candidate_metrics["rho_benefit"] < PARETO_CAMC_MIN_BENEFIT:
                            rejected_candidates += 1
                            camc_step_reject_benefit += 1
                            rejected_margin_sum += raw_margin
                            continue
                        gate = pareto_camc_gate(
                            anchor_loss=anchor_metrics["loss"],
                            candidate_loss=candidate_metrics["loss"],
                            anchor_benefit=anchor_metrics["benefit"],
                            candidate_benefit=candidate_metrics["benefit"],
                            anchor_violation=anchor_metrics["violation"],
                            candidate_violation=candidate_metrics["violation"],
                            rho_loss_anchor=anchor_metrics["rho_loss"],
                            rho_loss_candidate=candidate_metrics["rho_loss"],
                            rho_benefit_anchor=anchor_metrics["rho_benefit"],
                            rho_benefit_candidate=candidate_metrics["rho_benefit"],
                            rho_violation_anchor=anchor_metrics["rho_violation"],
                            rho_violation_candidate=candidate_metrics["rho_violation"],
                            reference_shift=reference_shift,
                            state_uncertainty=state_uncertainty,
                            action_kind=camc_action_kind(anchor, candidate),
                            extra_tau=hysteresis_extra_tau,
                        )
                        raw_margin = float(gate["delta_loss"]) - float(gate["tau"])
                        if not bool(gate["accepted"]):
                            rejected_candidates += 1
                            rejected_margin_sum += raw_margin
                            if gate["reject_reason"] == "loss":
                                camc_step_reject_loss += 1
                            elif gate["reject_reason"] == "benefit":
                                camc_step_reject_benefit += 1
                            elif gate["reject_reason"] == "violation":
                                camc_step_reject_violation += 1
                            continue
                        if best_gate is None or float(gate["score"]) > float(best_gate["score"]):
                            best_candidate = candidate
                            best_eval = candidate_eval
                            best_gate = gate
                    elif float(candidate_eval["surrogate_cost"]) < float(best_eval["surrogate_cost"]):
                        best_candidate = candidate
                        best_eval = candidate_eval

                camc_step_candidate_value = float(best_eval["surrogate_cost"])
                if use_pareto_gate and best_gate is not None:
                    camc_step_delta_loss = float(best_gate["delta_loss"])
                    camc_step_delta_benefit = float(best_gate["delta_benefit"])
                    camc_step_delta_violation = float(best_gate["delta_violation"])
                    camc_step_tau = float(best_gate["tau"])
                    camc_step_margin = camc_step_delta_loss - camc_step_tau
                else:
                    camc_step_margin = float(anchor_eval["surrogate_cost"]) - camc_step_candidate_value - gate_penalty
                camc_step_slack = float(min(anchor_eval["certified_slack"], best_eval["certified_slack"]))
                camc_margin_total += camc_step_margin
                camc_best_candidate_value_total += camc_step_candidate_value
                if best_candidate != anchor and camc_step_margin > 0.0:
                    mode_idx, verify, atoms_selected, context_gain = best_candidate
                    camc_step_activated = True
                    camc_activation_steps += 1
                    camc_activated_margin_total += camc_step_margin
                    if use_pareto_gate:
                        camc_hysteresis_cooldown = PARETO_CAMC_COOLDOWN_STEPS
                else:
                    mode_idx, verify, atoms_selected, context_gain = anchor
                    camc_anchor_preservation_steps += 1
                    if best_candidate != anchor:
                        rejected_candidates += 1
                        if use_pareto_gate:
                            camc_step_reject_loss += 1
                        rejected_margin_sum += camc_step_margin
            else:
                mode_idx, verify, atoms_selected, context_gain = anchor
                fallback = True
                camc_anchor_preservation_steps += 1
                rejected_candidates = max(0, len(candidates) - 1)
                camc_step_reject_safety = rejected_candidates

            camc_candidate_steps += 1
            camc_candidate_total += len(candidates)
            camc_rejected_total += rejected_candidates
            camc_step_rejected = rejected_candidates
            camc_step_candidate_count = len(candidates)
            camc_rejected_margin_total += rejected_margin_sum
            camc_reject_safety_total += camc_step_reject_safety
            camc_reject_loss_total += camc_step_reject_loss
            camc_reject_benefit_total += camc_step_reject_benefit
            camc_reject_violation_total += camc_step_reject_violation

            chosen_headrooms = compute_headrooms(
                row,
                q_state,
                ell,
                contamination,
                recovery_mass,
                diagnostic_debt,
                L,
                rho,
                cert_amp,
                verify,
                atoms_selected,
                False,
                exact_risk,
            )
            predicted_safe_mask = action_safe_mask(
                chosen_headrooms,
                row,
                predicted_risk,
                q_ver,
                q_state,
                ell,
                contamination,
                recovery_mass,
                diagnostic_debt,
                arrival_pressure,
                L,
                reference_shift,
                cert_amp,
                cert_loop,
                verify,
                atoms_selected,
                context_gain,
                DELTA_SAFE,
            )
            predicted_perf_mask = action_safe_mask(
                chosen_headrooms,
                row,
                predicted_risk,
                q_ver,
                q_state,
                ell,
                contamination,
                recovery_mass,
                diagnostic_debt,
                arrival_pressure,
                L,
                reference_shift,
                cert_amp,
                cert_loop,
                verify,
                atoms_selected,
                context_gain,
                DELTA_PERF,
            )
            safe_headroom = float(chosen_headrooms[mode_idx])
            inside_safe = bool(predicted_safe_mask[mode_idx])
            inside_perf = bool(predicted_perf_mask[mode_idx])
            if camc_step_activated:
                mode_counter["camc_switch"] += 1

        recomputed_exact_headrooms = compute_headrooms(
            row,
            q_state,
            ell,
            contamination,
            recovery_mass,
            diagnostic_debt,
            L,
            0.0,
            amp_mean,
            exact_verify if controller == "oracle_src" else verify,
            atoms_selected,
            True,
            exact_risk,
        )
        exact_safe_mask = action_safe_mask(
            recomputed_exact_headrooms,
            row,
            exact_risk,
            q_ver,
            q_state,
            ell,
            contamination,
            recovery_mass,
            diagnostic_debt,
            arrival_pressure,
            L,
            reference_shift,
            amp_mean,
            runtime_models["incorrect_self_loop"],
            exact_verify if controller == "oracle_src" else verify,
            atoms_selected,
            context_gain,
            DELTA_SAFE,
        )
        exact_safe_nonempty = bool(exact_safe_mask.any())
        if controller == "oracle_src":
            inside_safe = bool(exact_safe_mask[mode_idx])
        if controller in {"oracle_src", "rsrc", "se_mpc"} and L >= 0.5:
            family_drift_summary = family_min_projected_drifts(
                row,
                exact_risk,
                q_ver,
                q_state,
                ell,
                contamination,
                recovery_mass,
                diagnostic_debt,
                arrival_pressure,
                L,
                reference_shift,
                amp_mean,
                runtime_models["incorrect_self_loop"],
                exact_verify if controller == "oracle_src" else verify,
                atoms_selected,
                context_gain,
            )
        else:
            family_drift_summary = {
                "family_min_drift_g01": float("nan"),
                "family_min_drift_g012": float("nan"),
                "family_min_drift_all": float("nan"),
            }

        verification_benefit = 0.28 * verify + 0.05 * GOVERNANCE_MODES[mode_idx].verification_bias
        context_benefit = 0.04 * atoms_selected + 0.06 * max(float(context_gain), 0.0)
        failure_prob = float(
            np.clip(
                exact_risk
                - verification_benefit
                - context_benefit
                + 0.04 * q_state
                + 0.03 * contamination
                + 0.04 * diagnostic_debt
                + 0.03 * arrival_pressure,
                0.02,
                0.98,
            )
        )
        success = float(rng.random() > failure_prob)
        failure = 1.0 - success

        burst_event = float(rng.random() < (0.06 + 0.04 * reference_shift + 0.04 * max(L - L_SAFE, 0.0)))
        external_arrival = 0.03 + 0.03 * reference_shift + 0.04 * arrival_pressure + 0.03 * diagnostic_debt + 0.06 * burst_event
        nominal_load = (
            external_arrival
            + 0.16 * float(row["d_proxy"])
            + 0.12 * q_state
            + 0.08 * float(row["step_norm"])
            + 0.05 * verify
            + 0.03 * atoms_selected
            + 0.03 * ell
            + 0.05 * diagnostic_debt
        )
        recovery_draw = amp_mean * (1.0 + runtime_models["incorrect_self_loop"] * rng.random())
        recovery_load = failure * recovery_draw * (
            0.14
            + 0.10 * float(row["d_proxy"])
            + 0.08 * float(row["eval_norm"])
            + 0.08 * recovery_mass
            + 0.10 * diagnostic_debt
            + 0.06 * arrival_pressure
        )
        actual_recovery_load = GOVERNANCE_MODES[mode_idx].recovery_multiplier * recovery_load
        realized_service = float(
            np.clip(
                float(row["base_service"]) * GOVERNANCE_MODES[mode_idx].service_floor
                - 0.10 * q_ver
                - 0.04 * ell
                - 0.05 * min(recovery_mass, 1.5)
                - 0.04 * diagnostic_debt
                - 0.05 * arrival_pressure
                + 0.01 * verify,
                0.05,
                1.0,
            )
        )

        upper_load = nominal_load + GOVERNANCE_MODES[mode_idx].recovery_multiplier * (
            min(0.99, float(row["e_proxy"]) + rho) * (0.12 + 0.12 * amp_mean + 0.10 * float(row["eval_norm"]) + 0.06 * contamination + 0.12 * min(recovery_mass, 1.5))
        )
        lower_service = float(
            np.clip(
                float(row["base_service"]) * GOVERNANCE_MODES[mode_idx].service_floor
                - 0.08 * q_state
                - 0.05 * ell
                - 0.08 * min(recovery_mass, 1.5)
                - 0.05 * diagnostic_debt
                - 0.04 * arrival_pressure
                - rho,
                0.05,
                1.0,
            )
        )

        L_before = L
        q_before = q_ver
        ell_before = ell
        contamination_before = contamination
        recovery_before = recovery_mass
        diagnostic_before = diagnostic_debt
        arrival_before = arrival_pressure
        drift = nominal_load + actual_recovery_load - realized_service
        L = max(0.0, L + drift)
        q_ver = max(0.0, 0.74 * q_ver + 0.18 * verify + 0.14 * failure + 0.06 * diagnostic_debt - 0.16 * GOVERNANCE_MODES[mode_idx].verification_bias)
        ell = float(np.clip(0.55 * ell + atoms_selected - 0.25 - 0.35 * GOVERNANCE_MODES[mode_idx].verification_bias, 0.0, 3.5))
        contamination = float(np.clip(0.80 * contamination + 0.45 * failure - 0.08 * verify, 0.0, 1.5))
        diagnostic_debt = float(
            np.clip(
                0.82 * diagnostic_debt
                + 0.20 * (1.0 - verify)
                + 0.18 * failure
                + 0.10 * max(L - L_SAFE, 0.0)
                - 0.30 * verify
                - 0.08 * GOVERNANCE_MODES[mode_idx].verification_bias,
                0.0,
                2.0,
            )
        )
        arrival_pressure = float(
            np.clip(
                0.72 * arrival_pressure
                + 0.25 * burst_event
                + 0.12 * reference_shift
                + 0.10 * failure
                + 0.06 * max(L - L_SAFE, 0.0),
                0.0,
                2.0,
            )
        )
        recovery_mass = max(0.0, 0.72 * recovery_mass + 1.05 * actual_recovery_load - 0.20 * realized_service)
        observation_count += 1.0
        benchmark_action_mask = action_safe_mask(
            recomputed_exact_headrooms,
            row,
            exact_risk,
            q_before,
            q_state,
            ell_before,
            contamination_before,
            recovery_before,
            diagnostic_before,
            arrival_before,
            L_before,
            reference_shift,
            amp_mean,
            runtime_models["incorrect_self_loop"],
            exact_verify if controller == "oracle_src" else verify,
            atoms_selected,
            context_gain,
            DELTA_SAFE,
        )
        benchmark_action_nonempty = bool(benchmark_action_mask.any())
        benchmark_action_safe = bool(benchmark_action_mask[mode_idx])
        benchmark_headroom = realized_service - (nominal_load + actual_recovery_load)
        benchmark_safe = bool(
            benchmark_headroom >= DELTA_SAFE
            and q_ver <= (Q_SAFE + 0.08)
            and ell <= (ELL_SAFE + 0.25)
            and L <= (L_SAFE + 0.12)
            and diagnostic_debt <= (DEBT_SAFE + 0.18)
        )
        benchmark_perf = bool(
            benchmark_headroom >= DELTA_PERF
            and q_ver <= (Q_PERF + 0.08)
            and ell <= (ELL_PERF + 0.20)
            and L <= (L_PERF + 0.08)
            and diagnostic_debt <= (DEBT_PERF + 0.12)
        )
        if camc_step_activated:
            camc_post_switch_total += 1
            camc_post_switch_violation_steps += int(not benchmark_action_safe)
        delta_sq = float(L**2 - L_before**2)

        stage_cost = L + 0.35 * verify + 0.45 * actual_recovery_load + 0.25 * (1.0 - success) + 0.10 * diagnostic_debt
        discounted_cost += (BETA**t) * stage_cost
        discount_mass += BETA**t

        safe_steps += int(inside_safe)
        perf_steps += int(inside_perf or benchmark_perf)
        benchmark_safe_steps += int(benchmark_safe)
        benchmark_action_safe_steps += int(benchmark_action_safe)
        overload_steps += int(L > OVERLOAD_THRESHOLD)
        fallback_steps += int(fallback)
        safe_nonempty_steps += int(safe_nonempty)
        exact_safe_nonempty_steps += int(exact_safe_nonempty)
        benchmark_action_nonempty_steps += int(benchmark_action_nonempty)
        verify_steps += verify
        high_effort_steps += int(verify >= (2.0 / 3.0))
        max_effort_steps += int(verify >= 0.999)
        atom_steps += atoms_selected
        workload_total += L
        load_violation_steps += int(nominal_load + actual_recovery_load > upper_load)
        service_violation_steps += int(realized_service < lower_service)
        success_steps += success
        context_total += ell
        q_total += q_ver
        recovery_total += recovery_mass
        debt_total += diagnostic_debt
        arrival_total += arrival_pressure
        mode_counter[GOVERNANCE_MODES[mode_idx].name] += 1

        theta_precision_total += int(safe_nonempty)
        theta_precision_hits += int(safe_nonempty and exact_safe_nonempty)
        theta_recall_total += int(exact_safe_nonempty)
        theta_recall_hits += int(safe_nonempty and exact_safe_nonempty)
        theta_benchmark_precision_total += int(safe_nonempty)
        theta_benchmark_precision_hits += int(safe_nonempty and benchmark_action_nonempty)
        theta_benchmark_recall_total += int(benchmark_action_nonempty)
        theta_benchmark_recall_hits += int(safe_nonempty and benchmark_action_nonempty)
        action_safe_total += int(inside_safe)
        action_safe_hits += int(inside_safe and benchmark_action_safe)
        predicted_safe_total += int(inside_safe)
        predicted_safe_hits += int(inside_safe and benchmark_safe)
        benchmark_safe_total += int(benchmark_safe)

        if not inside_safe:
            outside_steps += 1
            negative_drift_outside += int(drift < 0)

        if camc_step_evaluated:
            camc_records.append(
                {
                    "dataset": dataset_name,
                    "controller": controller,
                    "seed": seed,
                    "step": t,
                    "reference_shift": float(reference_shift),
                    "certified_margin": float(camc_step_margin),
                    "certified_slack": float(camc_step_slack),
                    "anchor_value": float(camc_step_anchor_value),
                    "candidate_value": float(camc_step_candidate_value),
                    "delta_loss": float(camc_step_delta_loss),
                    "delta_benefit": float(camc_step_delta_benefit),
                    "delta_violation": float(camc_step_delta_violation),
                    "gate_tau": float(camc_step_tau),
                    "activated": float(camc_step_activated),
                    "anchor_preserved": float(not camc_step_activated),
                    "post_switch_violation": float((not benchmark_action_safe) if camc_step_activated else np.nan),
                    "rejected_candidates": int(camc_step_rejected),
                    "reject_safety": int(camc_step_reject_safety),
                    "reject_loss": int(camc_step_reject_loss),
                    "reject_benefit": int(camc_step_reject_benefit),
                    "reject_violation": int(camc_step_reject_violation),
                    "candidate_count": int(camc_step_candidate_count),
                    "safe_nonempty": float(safe_nonempty),
                    "fallback": float(fallback),
                    "L_before": float(L_before),
                    "drift": float(drift),
                    "success": float(success),
                }
            )

        drift_records.append(
            {
                "dataset": dataset_name,
                "controller": controller,
                "seed": seed,
                "L_before": L_before,
                "drift": drift,
                "delta_sq": delta_sq,
                "certified_headroom": float(safe_headroom),
                "exact_headroom": float(recomputed_exact_headrooms[mode_idx]),
                "verify_effort": float(verify),
                "mode": GOVERNANCE_MODES[mode_idx].name,
                "outside_safe": float(not inside_safe),
                "benchmark_outside_safe": float(not benchmark_safe),
                **family_drift_summary,
            }
        )

        if previous_safe and not inside_safe:
            excursion_open = True
            excursion_len = 1
        elif not previous_safe and not inside_safe and excursion_open:
            excursion_len += 1
        elif not previous_safe and inside_safe and excursion_open:
            excursion_lengths.append(excursion_len)
            excursion_open = False
            excursion_len = 0

        previous_safe = inside_safe
    if excursion_open and excursion_len > 0:
        excursion_lengths.append(excursion_len)

    return (
        {
            "dataset": dataset_name,
            "controller": controller,
            "seed": seed,
            "horizon": horizon,
            "discounted_cost": float(discounted_cost / max(discount_mass, 1e-6)),
            "success_rate": float(success_steps / horizon),
            "avg_workload": float(workload_total / max(horizon, 1)),
            "overload_rate": float(overload_steps / horizon),
            "safe_occupancy_rate": float(safe_steps / horizon),
            "perf_occupancy_rate": float(perf_steps / horizon),
            "benchmark_action_safe_occupancy_rate": float(benchmark_action_safe_steps / horizon),
            "benchmark_safe_occupancy_rate": float(benchmark_safe_steps / horizon),
            "safe_set_nonempty_rate": float(safe_nonempty_steps / horizon),
            "exact_safe_set_nonempty_rate": float(exact_safe_nonempty_steps / horizon),
            "benchmark_action_set_nonempty_rate": float(benchmark_action_nonempty_steps / horizon),
            "fallback_rate": float(fallback_steps / horizon),
            "verification_rate": float(verify_steps / horizon),
            "high_effort_rate": float(high_effort_steps / horizon),
            "max_effort_rate": float(max_effort_steps / horizon),
            "avg_atoms_selected": float(atom_steps / horizon),
            "avg_context_load": float(context_total / horizon),
            "avg_q_ver": float(q_total / horizon),
            "avg_recovery_mass": float(recovery_total / horizon),
            "avg_diagnostic_debt": float(debt_total / horizon),
            "avg_arrival_pressure": float(arrival_total / horizon),
            "certificate_load_violation_rate": float(load_violation_steps / horizon),
            "certificate_service_violation_rate": float(service_violation_steps / horizon),
            "theta_nesting_precision": float(theta_precision_hits / theta_precision_total) if theta_precision_total else float("nan"),
            "theta_nesting_recall": float(theta_recall_hits / theta_recall_total) if theta_recall_total else float("nan"),
            "theta_benchmark_precision": float(theta_benchmark_precision_hits / theta_benchmark_precision_total) if theta_benchmark_precision_total else float("nan"),
            "theta_benchmark_recall": float(theta_benchmark_recall_hits / theta_benchmark_recall_total) if theta_benchmark_recall_total else float("nan"),
            "action_safe_precision": float(action_safe_hits / action_safe_total) if action_safe_total else float("nan"),
            "safe_event_precision": float(predicted_safe_hits / predicted_safe_total) if predicted_safe_total else float("nan"),
            "safe_event_recall": float(predicted_safe_hits / benchmark_safe_total) if benchmark_safe_total else float("nan"),
            "mean_drift_outside_safe": float(np.mean([row["drift"] for row in drift_records if row["outside_safe"] > 0])) if outside_steps else 0.0,
            "negative_drift_rate_outside_safe": float(negative_drift_outside / outside_steps) if outside_steps else float("nan"),
            "avg_return_time_to_safe": float(np.mean(excursion_lengths)) if excursion_lengths else 0.0,
            "excursion_count": int(len(excursion_lengths)),
            "mpc_eligible_rate": float(mpc_eligible_steps / horizon),
            "mpc_activation_rate": float(mpc_activation_steps / max(mpc_eligible_steps, 1)),
            "mpc_fallback_to_rsrc_rate": float(mpc_fallback_to_rsrc_steps / horizon),
            "mpc_mean_candidate_count": float(mpc_candidate_total / max(mpc_candidate_steps, 1)),
            "mpc_candidate_rejection_rate": float(mpc_rejected_total / max(mpc_candidate_total, 1)),
            "mpc_mean_surrogate_improvement": float(mpc_surrogate_improvement_total / max(mpc_eligible_steps, 1)),
            "mpc_verify_down_rate": float(mpc_verify_down_steps / max(mpc_eligible_steps, 1)),
            "mpc_verify_up_rate": float(mpc_verify_up_steps / max(mpc_eligible_steps, 1)),
            "mpc_atom_up_rate": float(mpc_atom_up_steps / max(mpc_eligible_steps, 1)),
            "mpc_mode_switch_rate": float(mpc_mode_switch_steps / max(mpc_eligible_steps, 1)),
            "camc_gate_evaluation_rate": float(camc_evaluation_steps / horizon),
            "camc_activation_rate": float(camc_activation_steps / max(camc_evaluation_steps, 1)),
            "camc_anchor_preservation_rate": float(camc_anchor_preservation_steps / max(camc_evaluation_steps, 1)),
            "camc_mean_certified_margin": float(camc_margin_total / max(camc_evaluation_steps, 1)),
            "camc_mean_activated_margin": float(camc_activated_margin_total / max(camc_activation_steps, 1)),
            "camc_mean_rejected_margin": float(camc_rejected_margin_total / max(camc_rejected_total, 1)),
            "camc_candidate_rejection_rate": float(camc_rejected_total / max(camc_candidate_total, 1)),
            "camc_post_switch_violation_rate": float(camc_post_switch_violation_steps / max(camc_post_switch_total, 1)),
            "camc_mean_anchor_value": float(camc_anchor_value_total / max(camc_evaluation_steps, 1)),
            "camc_mean_best_candidate_value": float(camc_best_candidate_value_total / max(camc_evaluation_steps, 1)),
            "camc_reject_safety_rate": float(camc_reject_safety_total / max(camc_rejected_total, 1)),
            "camc_reject_loss_rate": float(camc_reject_loss_total / max(camc_rejected_total, 1)),
            "camc_reject_benefit_rate": float(camc_reject_benefit_total / max(camc_rejected_total, 1)),
            "camc_reject_violation_rate": float(camc_reject_violation_total / max(camc_rejected_total, 1)),
            "mode_distribution": dict(mode_counter),
        },
        drift_records,
        camc_records,
    )


def simulate_controller_dataset_job(payload: tuple) -> tuple[list[dict], list[dict], list[dict]]:
    dataset_name, frame, controller, runtime_models, seeds, horizon, reference_shift = payload
    seed_rows: list[dict] = []
    drift_rows: list[dict] = []
    camc_rows: list[dict] = []
    for seed in seeds:
        seed_result, seed_drifts, seed_camc_rows = simulate_seed(
            frame,
            dataset_name,
            controller,
            runtime_models,
            int(seed),
            horizon,
            reference_shift,
        )
        seed_rows.append(seed_result)
        drift_rows.extend(seed_drifts)
        camc_rows.extend(seed_camc_rows)
    return seed_rows, drift_rows, camc_rows


def summarize_results(seed_frame: pd.DataFrame) -> pd.DataFrame:
    metric_cols = [
        "discounted_cost",
        "safety_augmented_cost_low",
        "safety_augmented_cost_medium",
        "safety_augmented_cost_high",
        "success_rate",
        "avg_workload",
        "overload_rate",
        "safe_occupancy_rate",
        "perf_occupancy_rate",
        "benchmark_action_safe_occupancy_rate",
        "benchmark_safe_occupancy_rate",
        "safe_set_nonempty_rate",
        "exact_safe_set_nonempty_rate",
        "benchmark_action_set_nonempty_rate",
        "fallback_rate",
        "verification_rate",
        "high_effort_rate",
        "max_effort_rate",
        "avg_atoms_selected",
        "avg_context_load",
        "avg_q_ver",
        "avg_recovery_mass",
        "avg_diagnostic_debt",
        "avg_arrival_pressure",
        "certificate_load_violation_rate",
        "certificate_service_violation_rate",
        "theta_nesting_precision",
        "theta_nesting_recall",
        "theta_benchmark_precision",
        "theta_benchmark_recall",
        "action_safe_precision",
        "safe_event_precision",
        "safe_event_recall",
        "mean_drift_outside_safe",
        "negative_drift_rate_outside_safe",
        "avg_return_time_to_safe",
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
        "camc_gate_evaluation_rate",
        "camc_activation_rate",
        "camc_anchor_preservation_rate",
        "camc_mean_certified_margin",
        "camc_mean_activated_margin",
        "camc_mean_rejected_margin",
        "camc_candidate_rejection_rate",
        "camc_post_switch_violation_rate",
        "camc_mean_anchor_value",
        "camc_mean_best_candidate_value",
        "camc_reject_safety_rate",
        "camc_reject_loss_rate",
        "camc_reject_benefit_rate",
        "camc_reject_violation_rate",
    ]
    rows = []
    for (dataset, controller), group in seed_frame.groupby(["dataset", "controller"], sort=True):
        row = {"dataset": dataset, "controller": controller, "seeds": int(len(group))}
        for metric in metric_cols:
            values = group[metric].dropna().to_list()
            row[metric] = float(np.mean(values)) if values else float("nan")
            lo, hi = bootstrap_interval(values, seed=17, rounds=400) if values else (float("nan"), float("nan"))
            row[f"{metric}_ci_low"] = lo
            row[f"{metric}_ci_high"] = hi
        rows.append(row)
    return pd.DataFrame(rows)


def summarize_pairwise(seed_frame: pd.DataFrame) -> pd.DataFrame:
    metrics = [
        "discounted_cost",
        "success_rate",
        "overload_rate",
        "safe_occupancy_rate",
        "benchmark_action_safe_occupancy_rate",
        "benchmark_safe_occupancy_rate",
        "fallback_rate",
        "high_effort_rate",
        "theta_benchmark_precision",
        "theta_nesting_precision",
        "action_safe_precision",
        "safe_event_precision",
        "negative_drift_rate_outside_safe",
        "avg_return_time_to_safe",
    ]
    rows = []
    for dataset, frame in seed_frame.groupby("dataset", sort=True):
        pivot = frame.pivot_table(index="seed", columns="controller", values=metrics)
        if ("rsrc" not in frame["controller"].values) or ("se_mpc" not in frame["controller"].values):
            continue
        for metric in metrics:
            diff = pivot[(metric, "se_mpc")] - pivot[(metric, "rsrc")]
            values = diff.dropna().to_list()
            lo, hi = bootstrap_interval(values, seed=23, rounds=400) if values else (float("nan"), float("nan"))
            rows.append(
                {
                    "dataset": dataset,
                    "metric": metric,
                    "se_mpc_minus_rsrc": float(np.mean(values)) if values else float("nan"),
                    "ci_low": lo,
                    "ci_high": hi,
                }
            )
    return pd.DataFrame(rows)


def summarize_camc_pairwise(seed_frame: pd.DataFrame) -> pd.DataFrame:
    metrics = [
        "discounted_cost",
        "safety_augmented_cost_medium",
        "success_rate",
        "overload_rate",
        "verification_rate",
        "fallback_rate",
        "safe_set_nonempty_rate",
        "avg_return_time_to_safe",
        "camc_activation_rate",
        "camc_post_switch_violation_rate",
    ]
    pairs = [
        ("camc_static_anchor", "static_conservative", "CAMC-static minus static anchor"),
        ("camc_rsrc_anchor", "rsrc", "CAMC-RSRC minus RSRC anchor"),
        ("camc_sempc_candidate", "static_conservative", "CAMC-SE-MPC minus static anchor"),
        ("camc_sempc_candidate", "se_mpc", "CAMC-SE-MPC minus SE-MPC candidate"),
        ("pareto_camc_static_anchor", "static_conservative", "Pareto-CAMC-static minus static anchor"),
        ("pareto_camc_rsrc_anchor", "rsrc", "Pareto-CAMC-RSRC minus RSRC anchor"),
        ("pareto_camc_sempc_candidate", "static_conservative", "Pareto-CAMC-SE-MPC minus static anchor"),
        ("pareto_camc_sempc_candidate", "se_mpc", "Pareto-CAMC-SE-MPC minus SE-MPC candidate"),
    ]
    rows = []
    for dataset, frame in seed_frame.groupby("dataset", sort=True):
        pivot = frame.pivot_table(index="seed", columns="controller", values=metrics)
        available = set(frame["controller"].unique())
        for left, right, label in pairs:
            if left not in available or right not in available:
                continue
            for metric in metrics:
                diff = pivot[(metric, left)] - pivot[(metric, right)]
                values = diff.dropna().to_list()
                lo, hi = bootstrap_interval(values, seed=37, rounds=400) if values else (float("nan"), float("nan"))
                rows.append(
                    {
                        "dataset": dataset,
                        "comparison": label,
                        "controller_a": left,
                        "controller_b": right,
                        "metric": metric,
                        "a_minus_b": float(np.mean(values)) if values else float("nan"),
                        "ci_low": lo,
                        "ci_high": hi,
                    }
                )
    return pd.DataFrame(rows)


def summarize_camc_gate_events(camc_records: list[dict]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    frame = pd.DataFrame(camc_records)
    if frame.empty:
        return frame, frame, frame

    finite_slack = frame["certified_slack"].replace([np.inf, -np.inf], np.nan)
    if finite_slack.notna().sum() >= 5:
        ranked = finite_slack.rank(method="first")
        frame["slack_quantile"] = pd.qcut(
            ranked,
            q=min(5, int(finite_slack.notna().sum())),
            labels=False,
            duplicates="drop",
        )
        frame["slack_quantile"] = frame["slack_quantile"].map(lambda value: f"Q{int(value) + 1}" if pd.notna(value) else "NA")
    else:
        frame["slack_quantile"] = "NA"

    frame["shift_bucket"] = pd.cut(
        frame["reference_shift"],
        bins=[-np.inf, 0.2, 0.6, np.inf],
        labels=["low", "medium", "high"],
    )

    by_slack = (
        frame.groupby(["dataset", "controller", "slack_quantile"], observed=True)
        .agg(
            rows=("activated", "size"),
            activation_rate=("activated", "mean"),
            mean_certified_margin=("certified_margin", "mean"),
            mean_certified_slack=("certified_slack", "mean"),
            post_switch_violation_rate=("post_switch_violation", "mean"),
            mean_success=("success", "mean"),
            mean_drift=("drift", "mean"),
        )
        .reset_index()
    )
    by_shift = (
        frame.groupby(["dataset", "controller", "shift_bucket"], observed=True)
        .agg(
            rows=("activated", "size"),
            activation_rate=("activated", "mean"),
            anchor_preservation_rate=("anchor_preserved", "mean"),
            fallback_rate=("fallback", "mean"),
            mean_certified_margin=("certified_margin", "mean"),
            mean_certified_slack=("certified_slack", "mean"),
            post_switch_violation_rate=("post_switch_violation", "mean"),
        )
        .reset_index()
    )
    return frame, by_slack, by_shift


def summarize_controller_contrasts(seed_frame: pd.DataFrame) -> pd.DataFrame:
    metrics = [
        "discounted_cost",
        "safety_augmented_cost_medium",
        "success_rate",
        "overload_rate",
        "safe_occupancy_rate",
        "benchmark_safe_occupancy_rate",
        "verification_rate",
        "certificate_service_violation_rate",
        "negative_drift_rate_outside_safe",
        "avg_return_time_to_safe",
    ]
    pairs = [
        ("rsrc", "static_conservative"),
        ("se_mpc", "static_conservative"),
        ("rsrc", "headroom_only"),
        ("rsrc", "rsrc_no_recovery"),
        ("rsrc", "rsrc_no_context"),
        ("rsrc", "adaptive_threshold"),
        ("rsrc", "maxweight_backlog"),
        ("se_mpc", "rsrc"),
        ("camc_static_anchor", "static_conservative"),
        ("camc_rsrc_anchor", "rsrc"),
        ("camc_sempc_candidate", "static_conservative"),
        ("camc_sempc_candidate", "se_mpc"),
        ("pareto_camc_static_anchor", "static_conservative"),
        ("pareto_camc_rsrc_anchor", "rsrc"),
        ("pareto_camc_sempc_candidate", "static_conservative"),
        ("pareto_camc_sempc_candidate", "se_mpc"),
        ("headroom_only", "minimal_verify"),
        ("always_verify_throttle", "always_verify"),
    ]
    rows = []
    for dataset, frame in seed_frame.groupby("dataset", sort=True):
        pivot = frame.pivot_table(index="seed", columns="controller", values=metrics)
        available = set(frame["controller"].unique())
        for left, right in pairs:
            if left not in available or right not in available:
                continue
            for metric in metrics:
                diff = pivot[(metric, left)] - pivot[(metric, right)]
                values = diff.dropna().to_list()
                lo, hi = bootstrap_interval(values, seed=29, rounds=400) if values else (float("nan"), float("nan"))
                rows.append(
                    {
                        "dataset": dataset,
                        "controller_a": left,
                        "controller_b": right,
                        "metric": metric,
                        "a_minus_b": float(np.mean(values)) if values else float("nan"),
                        "ci_low": lo,
                        "ci_high": hi,
                    }
                )
    return pd.DataFrame(rows)


def add_safety_objectives(seed_frame: pd.DataFrame) -> pd.DataFrame:
    frame = seed_frame.copy()
    for profile, weights in SAFETY_OBJECTIVE_PROFILES.items():
        frame[f"safety_augmented_cost_{profile}"] = (
            frame["discounted_cost"]
            + weights["overload"] * frame["overload_rate"]
            + weights["failure"] * (1.0 - frame["success_rate"])
            + weights["service"] * frame["certificate_service_violation_rate"]
        )
    return frame


def summarize_safety_objectives(seed_frame: pd.DataFrame) -> pd.DataFrame:
    frame = add_safety_objectives(seed_frame)
    rows = []
    for (dataset, controller), group in frame.groupby(["dataset", "controller"], sort=True):
        for profile in SAFETY_OBJECTIVE_PROFILES:
            metric = f"safety_augmented_cost_{profile}"
            values = group[metric].dropna().to_list()
            lo, hi = bootstrap_interval(values, seed=31, rounds=400) if values else (float("nan"), float("nan"))
            rows.append(
                {
                    "dataset": dataset,
                    "controller": controller,
                    "profile": profile,
                    "safety_augmented_cost": float(np.mean(values)) if values else float("nan"),
                    "ci_low": lo,
                    "ci_high": hi,
                }
            )
    return pd.DataFrame(rows)


def summarize_drift_bins(drift_rows: list[dict]) -> pd.DataFrame:
    frame = pd.DataFrame(drift_rows)
    if frame.empty:
        return frame
    bins = [-1e-9, 0.5, 1.0, 2.0, 4.0, 8.0, np.inf]
    labels = ["<=0.5", "(0.5,1]", "(1,2]", "(2,4]", "(4,8]", ">8"]
    frame["L_bin"] = pd.cut(frame["L_before"], bins=bins, labels=labels)
    summary = (
        frame[frame["outside_safe"] > 0]
        .groupby(["dataset", "controller", "L_bin"], observed=True)
        .agg(
            mean_drift=("drift", "mean"),
            mean_delta_sq=("delta_sq", "mean"),
            negative_drift_rate=("drift", lambda values: float(np.mean(np.asarray(values) < 0))),
            negative_delta_sq_rate=("delta_sq", lambda values: float(np.mean(np.asarray(values) < 0))),
            rows=("drift", "size"),
        )
        .reset_index()
    )
    return summary


def summarize_headroom_bins(drift_rows: list[dict]) -> pd.DataFrame:
    frame = pd.DataFrame(drift_rows)
    if frame.empty:
        return frame
    bins = [-np.inf, 0.0, 0.03, 0.08, 0.15, np.inf]
    labels = ["<=0", "(0,0.03]", "(0.03,0.08]", "(0.08,0.15]", ">0.15"]
    frame["headroom_bin"] = pd.cut(frame["certified_headroom"], bins=bins, labels=labels)
    summary = (
        frame.groupby(["dataset", "controller", "headroom_bin"], observed=True)
        .agg(
            mean_drift=("drift", "mean"),
            mean_delta_sq=("delta_sq", "mean"),
            negative_drift_rate=("drift", lambda values: float(np.mean(np.asarray(values) < 0))),
            negative_delta_sq_rate=("delta_sq", lambda values: float(np.mean(np.asarray(values) < 0))),
            rows=("drift", "size"),
        )
        .reset_index()
    )
    return summary


def summarize_headroom_calibration(drift_rows: list[dict]) -> pd.DataFrame:
    frame = pd.DataFrame(drift_rows)
    if frame.empty:
        return frame
    bins = [-np.inf, 0.0, 0.03, 0.08, 0.15, np.inf]
    labels = ["<=0", "(0,0.03]", "(0.03,0.08]", "(0.08,0.15]", ">0.15"]
    frame["headroom_bin"] = pd.cut(frame["certified_headroom"], bins=bins, labels=labels)
    summary = (
        frame.groupby(["dataset", "controller", "headroom_bin"], observed=True)
        .agg(
            mean_certified_headroom=("certified_headroom", "mean"),
            mean_exact_headroom=("exact_headroom", "mean"),
            exact_headroom_positive_rate=("exact_headroom", lambda values: float(np.mean(np.asarray(values) > 0))),
            benchmark_safe_rate=("benchmark_outside_safe", lambda values: float(np.mean(1.0 - np.asarray(values)))),
            outside_safe_rate=("outside_safe", "mean"),
            negative_drift_rate=("drift", lambda values: float(np.mean(np.asarray(values) < 0))),
            mean_drift=("drift", "mean"),
            rows=("drift", "size"),
        )
        .reset_index()
    )
    return summary


def summarize_headroom_load_grid(drift_rows: list[dict]) -> pd.DataFrame:
    frame = pd.DataFrame(drift_rows)
    if frame.empty:
        return frame
    headroom_bins = [-np.inf, 0.0, 0.03, 0.08, 0.15, np.inf]
    headroom_labels = ["<=0", "(0,0.03]", "(0.03,0.08]", "(0.08,0.15]", ">0.15"]
    load_bins = [-1e-9, 0.5, 1.0, 2.0, 4.0, np.inf]
    load_labels = ["<=0.5", "(0.5,1]", "(1,2]", "(2,4]", ">4"]
    frame["headroom_bin"] = pd.cut(frame["certified_headroom"], bins=headroom_bins, labels=headroom_labels)
    frame["L_bin"] = pd.cut(frame["L_before"], bins=load_bins, labels=load_labels)
    summary = (
        frame.groupby(["dataset", "controller", "headroom_bin", "L_bin"], observed=True)
        .agg(
            mean_drift=("drift", "mean"),
            mean_delta_sq=("delta_sq", "mean"),
            negative_drift_rate=("drift", lambda values: float(np.mean(np.asarray(values) < 0))),
            negative_delta_sq_rate=("delta_sq", lambda values: float(np.mean(np.asarray(values) < 0))),
            benchmark_safe_rate=("benchmark_outside_safe", lambda values: float(np.mean(1.0 - np.asarray(values)))),
            rows=("drift", "size"),
        )
        .reset_index()
    )
    return summary


def summarize_headroom_theory_support(drift_rows: list[dict]) -> pd.DataFrame:
    frame = pd.DataFrame(drift_rows)
    if frame.empty:
        return frame
    focus = frame[frame["controller"].isin(["rsrc", "se_mpc", "oracle_src", *CAMC_CONTROLLERS])].copy()
    rows = []
    for (dataset, controller), group in focus.groupby(["dataset", "controller"], sort=True):
        adverse = group[group["certified_headroom"] <= 0.0]
        adverse_high_load = group[(group["certified_headroom"] <= 0.0) & (group["L_before"] >= 0.5)]
        benign = group[group["certified_headroom"] > 0.0]
        rows.append(
            {
                "dataset": dataset,
                "controller": controller,
                "adverse_rows": int(len(adverse)),
                "adverse_negative_drift_rate": float(np.mean(adverse["drift"] < 0)) if len(adverse) else float("nan"),
                "adverse_negative_delta_sq_rate": float(np.mean(adverse["delta_sq"] < 0)) if len(adverse) else float("nan"),
                "adverse_mean_drift": float(adverse["drift"].mean()) if len(adverse) else float("nan"),
                "adverse_high_load_rows": int(len(adverse_high_load)),
                "adverse_high_load_negative_drift_rate": float(np.mean(adverse_high_load["drift"] < 0)) if len(adverse_high_load) else float("nan"),
                "benign_rows": int(len(benign)),
                "benign_benchmark_safe_rate": float(np.mean(1.0 - benign["benchmark_outside_safe"])) if len(benign) else float("nan"),
                "benign_mean_exact_headroom": float(benign["exact_headroom"].mean()) if len(benign) else float("nan"),
            }
        )
    return pd.DataFrame(rows)


def summarize_positive_headroom_drift(drift_rows: list[dict]) -> pd.DataFrame:
    frame = pd.DataFrame(drift_rows)
    if frame.empty:
        return frame
    focus = frame[frame["controller"].isin(["rsrc", "se_mpc", "static_conservative", *CAMC_CONTROLLERS])].copy()
    rows = []
    for (dataset, controller), group in focus.groupby(["dataset", "controller"], sort=True):
        for epsilon in [0.0, 0.03, 0.08]:
            for load_threshold in [0.35, 0.5, 1.0]:
                cell = group[
                    (group["certified_headroom"] >= epsilon)
                    & (group["outside_safe"] > 0)
                    & (group["L_before"] >= load_threshold)
                ]
                drift_values = cell["drift"].to_numpy(dtype=float)
                delta_values = cell["delta_sq"].to_numpy(dtype=float)
                neg_drift_values = (drift_values < 0).astype(float)
                neg_delta_values = (delta_values < 0).astype(float)
                if len(cell):
                    drift_lo, drift_hi = bootstrap_interval(drift_values, seed=41, rounds=400)
                    neg_lo, neg_hi = bootstrap_interval(neg_drift_values, seed=43, rounds=400)
                    delta_lo, delta_hi = bootstrap_interval(delta_values, seed=47, rounds=400)
                    neg_delta_lo, neg_delta_hi = bootstrap_interval(neg_delta_values, seed=53, rounds=400)
                else:
                    drift_lo = drift_hi = neg_lo = neg_hi = float("nan")
                    delta_lo = delta_hi = neg_delta_lo = neg_delta_hi = float("nan")
                rows.append(
                    {
                        "dataset": dataset,
                        "controller": controller,
                        "epsilon_s": epsilon,
                        "load_threshold": load_threshold,
                        "rows": int(len(cell)),
                        "mean_drift": float(np.mean(drift_values)) if len(cell) else float("nan"),
                        "mean_drift_ci_low": drift_lo,
                        "mean_drift_ci_high": drift_hi,
                        "negative_drift_rate": float(np.mean(neg_drift_values)) if len(cell) else float("nan"),
                        "negative_drift_rate_ci_low": neg_lo,
                        "negative_drift_rate_ci_high": neg_hi,
                        "mean_delta_sq": float(np.mean(delta_values)) if len(cell) else float("nan"),
                        "mean_delta_sq_ci_low": delta_lo,
                        "mean_delta_sq_ci_high": delta_hi,
                        "negative_delta_sq_rate": float(np.mean(neg_delta_values)) if len(cell) else float("nan"),
                        "negative_delta_sq_rate_ci_low": neg_delta_lo,
                        "negative_delta_sq_rate_ci_high": neg_delta_hi,
                        "mean_certified_headroom": float(cell["certified_headroom"].mean()) if len(cell) else float("nan"),
                        "mean_exact_headroom": float(cell["exact_headroom"].mean()) if len(cell) else float("nan"),
                    }
                )
    return pd.DataFrame(rows)


def summarize_family_barrier(drift_rows: list[dict]) -> pd.DataFrame:
    frame = pd.DataFrame(drift_rows)
    if frame.empty:
        return frame
    rows = []
    thresholds = [0.5, 1.0, 2.0]
    families = {
        "g01": "family_min_drift_g01",
        "g012": "family_min_drift_g012",
        "all_modes": "family_min_drift_all",
    }
    focus = frame[frame["controller"].isin(["rsrc", "se_mpc", "oracle_src", *CAMC_CONTROLLERS])].copy()
    for (dataset, controller), group in focus.groupby(["dataset", "controller"], sort=True):
        for threshold in thresholds:
            high_load = group[group["L_before"] >= threshold]
            for family, column in families.items():
                values = high_load[column].dropna().to_numpy(dtype=float)
                if len(values) == 0:
                    rows.append(
                        {
                            "dataset": dataset,
                            "controller": controller,
                            "family": family,
                            "load_threshold": threshold,
                            "rows": 0,
                            "barrier_rate": float("nan"),
                            "mean_min_projected_drift": float("nan"),
                        }
                    )
                    continue
                rows.append(
                    {
                        "dataset": dataset,
                        "controller": controller,
                        "family": family,
                        "load_threshold": threshold,
                        "rows": int(len(values)),
                        "barrier_rate": float(np.mean(values < 0)),
                        "mean_min_projected_drift": float(np.mean(values)),
                    }
                )
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a theorem-faithful online simulator estimated from the local datasets.")
    parser.add_argument("--manifest-dir", type=Path, default=MANIFEST_DIR)
    parser.add_argument("--output-dir", type=Path, default=RESULTS_DIR / "online_simulator")
    parser.add_argument("--dataset", choices=["verified", "test", "both", "rebench", "smith", "all"], default="all")
    parser.add_argument("--seeds", type=int, default=32)
    parser.add_argument("--horizon", type=int, default=1200)
    parser.add_argument("--workers", type=int, default=1)
    args = parser.parse_args()

    output_dir = ensure_dir(args.output_dir)
    paths = manifest_paths(args.manifest_dir)
    risk_prior, atom_prior = fit_priors(args.manifest_dir)
    runtime_models = fit_runtime_models(args.manifest_dir)
    datasets = load_datasets(args.dataset, paths)
    swe_bench = pd.read_csv(paths["swe_bench_tasks"])
    reference = swe_bench[swe_bench["split"] == "test"].copy()

    prepared = {}
    shift_map = {}
    for dataset_name, frame in datasets.items():
        prepared[dataset_name] = apply_runtime_models(frame, risk_prior, atom_prior, runtime_models)
        shift_map[dataset_name] = mean_abs_feature_shift(reference, frame)

    controller_names = [
        "oracle_src",
        "rsrc",
        "se_mpc",
        "camc_static_anchor",
        "camc_rsrc_anchor",
        "camc_sempc_candidate",
        "pareto_camc_static_anchor",
        "pareto_camc_rsrc_anchor",
        "pareto_camc_sempc_candidate",
        "greedy_myopic",
        "static_conservative",
        "static_aggressive",
        "always_verify",
        "always_verify_throttle",
        "adaptive_threshold",
        "maxweight_backlog",
        "headroom_only",
        "rsrc_no_recovery",
        "rsrc_no_context",
        "minimal_verify",
        "plain_mpc",
    ]

    seed_rows: list[dict] = []
    drift_rows: list[dict] = []
    camc_rows: list[dict] = []
    jobs = [
        (
            dataset_name,
            frame,
            controller,
            runtime_models,
            list(range(args.seeds)),
            min(args.horizon, max(len(frame), 1)),
            shift_map[dataset_name],
        )
        for dataset_name, frame in prepared.items()
        for controller in controller_names
    ]
    if args.workers > 1:
        with ProcessPoolExecutor(max_workers=args.workers) as executor:
            futures = [executor.submit(simulate_controller_dataset_job, job) for job in jobs]
            for future in as_completed(futures):
                job_seed_rows, job_drift_rows, job_camc_rows = future.result()
                seed_rows.extend(job_seed_rows)
                drift_rows.extend(job_drift_rows)
                camc_rows.extend(job_camc_rows)
    else:
        for job in jobs:
            job_seed_rows, job_drift_rows, job_camc_rows = simulate_controller_dataset_job(job)
            seed_rows.extend(job_seed_rows)
            drift_rows.extend(job_drift_rows)
            camc_rows.extend(job_camc_rows)

    seed_frame = add_safety_objectives(pd.DataFrame(seed_rows))
    summary_frame = summarize_results(seed_frame)
    safety_objective_frame = summarize_safety_objectives(seed_frame)
    pairwise_frame = summarize_pairwise(seed_frame)
    camc_pairwise_frame = summarize_camc_pairwise(seed_frame)
    contrast_frame = summarize_controller_contrasts(seed_frame)
    camc_event_frame, camc_slack_frame, camc_shift_frame = summarize_camc_gate_events(camc_rows)
    drift_bin_frame = summarize_drift_bins(drift_rows)
    headroom_bin_frame = summarize_headroom_bins(drift_rows)
    headroom_calibration_frame = summarize_headroom_calibration(drift_rows)
    headroom_load_frame = summarize_headroom_load_grid(drift_rows)
    headroom_support_frame = summarize_headroom_theory_support(drift_rows)
    positive_headroom_drift_frame = summarize_positive_headroom_drift(drift_rows)
    family_barrier_frame = summarize_family_barrier(drift_rows)

    seed_frame.to_csv(output_dir / "online_simulator_seed_results.csv", index=False)
    summary_frame.to_csv(output_dir / "online_simulator_summary.csv", index=False)
    pairwise_frame.to_csv(output_dir / "online_simulator_pairwise.csv", index=False)
    camc_pairwise_frame.to_csv(output_dir / "online_simulator_camc_pairwise.csv", index=False)
    contrast_frame.to_csv(output_dir / "online_simulator_controller_contrasts.csv", index=False)
    camc_event_frame.to_csv(output_dir / "online_simulator_camc_gate_events.csv", index=False)
    camc_slack_frame.to_csv(output_dir / "online_simulator_camc_activation_by_slack.csv", index=False)
    camc_shift_frame.to_csv(output_dir / "online_simulator_camc_activation_by_shift.csv", index=False)
    safety_objective_frame.to_csv(output_dir / "online_simulator_safety_objectives.csv", index=False)
    drift_bin_frame.to_csv(output_dir / "online_simulator_drift_bins.csv", index=False)
    headroom_bin_frame.to_csv(output_dir / "online_simulator_headroom_bins.csv", index=False)
    headroom_calibration_frame.to_csv(output_dir / "online_simulator_headroom_calibration.csv", index=False)
    headroom_load_frame.to_csv(output_dir / "online_simulator_headroom_load_grid.csv", index=False)
    headroom_support_frame.to_csv(output_dir / "online_simulator_headroom_theory_support.csv", index=False)
    positive_headroom_drift_frame.to_csv(output_dir / "online_simulator_positive_headroom_drift.csv", index=False)
    family_barrier_frame.to_csv(output_dir / "online_simulator_family_barrier.csv", index=False)
    write_json(
        output_dir / "online_simulator_summary.json",
        {
            "seeds": args.seeds,
            "horizon": args.horizon,
            "dataset_shift": shift_map,
            "summary": summary_frame.to_dict("records"),
            "pairwise": pairwise_frame.to_dict("records"),
            "camc_pairwise": camc_pairwise_frame.to_dict("records"),
            "controller_contrasts": contrast_frame.to_dict("records"),
            "camc_activation_by_slack": camc_slack_frame.to_dict("records"),
            "camc_activation_by_shift": camc_shift_frame.to_dict("records"),
            "safety_objectives": safety_objective_frame.to_dict("records"),
            "headroom_calibration": headroom_calibration_frame.to_dict("records"),
            "headroom_theory_support": headroom_support_frame.to_dict("records"),
            "positive_headroom_drift": positive_headroom_drift_frame.to_dict("records"),
            "family_barrier": family_barrier_frame.to_dict("records"),
        },
    )

    preview = summary_frame[
        [
            "dataset",
            "controller",
            "discounted_cost",
            "success_rate",
            "overload_rate",
            "safe_occupancy_rate",
            "benchmark_safe_occupancy_rate",
            "fallback_rate",
            "high_effort_rate",
            "theta_nesting_precision",
            "action_safe_precision",
            "safe_event_precision",
            "negative_drift_rate_outside_safe",
            "avg_return_time_to_safe",
        ]
    ].copy()
    print("Online runtime simulator complete.")
    print(preview.to_string(index=False))


if __name__ == "__main__":
    main()
