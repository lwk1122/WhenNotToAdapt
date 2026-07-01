from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

from common import (
    GOVERNANCE_MODES,
    MANIFEST_DIR,
    RESULTS_DIR,
    clip_probabilities,
    ensure_dir,
    manifest_paths,
    ridge_fit,
    ridge_predict,
    sigmoid,
    write_json,
)
from structural_diagnostics import fit_context_atom_diagnostics, fit_state_compression, load_overlap


TASK_FEATURE_COLS = [
    "problem_tokens",
    "hints_tokens",
    "hints_nonempty",
    "fail_to_pass_count",
    "pass_to_pass_count",
    "gold_patch_files",
    "gold_patch_lines",
]

ATOM_COLS = ["problem_tokens", "hints_tokens", "fail_tests_tokens", "pass_tests_tokens"]


def standardize(train_frame: pd.DataFrame, frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    result = frame.copy()
    for column in columns:
        mean = train_frame[column].mean()
        std = train_frame[column].std(ddof=0)
        result[column] = 0.0 if std == 0 or np.isnan(std) else (result[column] - mean) / std
    return result


def fit_priors(manifest_dir: Path) -> tuple[dict, dict]:
    overlap = load_overlap(manifest_dir)
    _, overlap = fit_state_compression(overlap)
    context = fit_context_atom_diagnostics(overlap)

    train_std = standardize(overlap, overlap, TASK_FEATURE_COLS)
    risk_weights = ridge_fit(train_std[TASK_FEATURE_COLS].to_numpy(dtype=float), overlap["failure"].to_numpy(dtype=float), alpha=2.0)
    risk_prior = {
        "weights": risk_weights.tolist(),
        "task_means": {column: float(overlap[column].mean()) for column in TASK_FEATURE_COLS},
        "task_stds": {column: float(overlap[column].std(ddof=0)) for column in TASK_FEATURE_COLS},
    }
    atom_prior = {
        "weights": context["additive_atom_weights"],
        "means": {column: float(overlap[column].mean()) for column in ATOM_COLS},
        "stds": {column: float(overlap[column].std(ddof=0)) for column in ATOM_COLS},
    }
    return risk_prior, atom_prior


def apply_priors(tasks: pd.DataFrame, risk_prior: dict, atom_prior: dict) -> pd.DataFrame:
    frame = tasks.copy()
    standardized = frame.copy()
    for column in TASK_FEATURE_COLS:
        mean = risk_prior["task_means"][column]
        std = risk_prior["task_stds"][column]
        standardized[column] = 0.0 if std == 0 else (standardized[column] - mean) / std
    risk_weights = np.asarray(risk_prior["weights"], dtype=float)
    frame["e_proxy"] = clip_probabilities(ridge_predict(standardized[TASK_FEATURE_COLS].to_numpy(dtype=float), risk_weights))
    frame["d_proxy"] = sigmoid(
        0.55 * np.log1p(frame["fail_to_pass_count"])
        + 0.30 * np.log1p(frame["pass_to_pass_count"])
        + 0.10 * frame["gold_patch_files"]
        + 0.05 * frame["problem_tokens"] / 100.0
    )
    frame["q_proxy"] = sigmoid(
        0.60 * np.log1p(frame["fail_to_pass_count"])
        + 0.15 * np.log1p(frame["pass_to_pass_count"])
        + 0.06 * frame["problem_tokens"] / 100.0
    )
    atom_weights = atom_prior["weights"]
    for atom in ATOM_COLS:
        mean = atom_prior["means"][atom]
        std = atom_prior["stds"][atom]
        standardized_atom = 0.0 if std == 0 else (frame[atom] - mean) / std
        frame[f"{atom}__score"] = standardized_atom * atom_weights.get(atom, 0.0)
    return frame


def candidate_modes(e_value: float, d_value: float, q_value: float, conservative: bool) -> list[dict]:
    modes = []
    risk = min(0.99, e_value + (0.10 if conservative else 0.0))
    for mode in GOVERNANCE_MODES:
        nominal_load = 0.18 + 0.22 * d_value + 0.18 * q_value
        recovery_load = risk * mode.recovery_multiplier * (0.20 + 0.25 * d_value + 0.12 * q_value)
        headroom = mode.service_floor - (nominal_load + recovery_load)
        modes.append({"mode": mode.name, "headroom": headroom, "service": mode.service_floor, "bias": mode.verification_bias, "amp": mode.recovery_multiplier})
    return modes


def select_mode(controller: str, e_value: float, d_value: float, q_value: float, exact_risk: float) -> dict:
    if controller == "static_conservative":
        return candidate_modes(e_value, d_value, q_value, conservative=True)[-1]
    if controller == "static_aggressive":
        return candidate_modes(e_value, d_value, q_value, conservative=False)[0]
    if controller == "greedy_myopic":
        modes = candidate_modes(e_value, d_value, q_value, conservative=False)
        return modes[1] if q_value > 0.8 else modes[0]
    if controller == "plain_mpc":
        modes = candidate_modes(e_value, d_value, q_value, conservative=False)
        return min(modes, key=lambda item: abs(item["headroom"]))
    if controller == "always_verify_throttle":
        modes = candidate_modes(e_value, d_value, q_value, conservative=True)
        target = 3 if q_value > 0.8 else 2
        safe_modes = [mode for mode in modes[target:] if mode["headroom"] > 0]
        return safe_modes[0] if safe_modes else modes[-1]
    if controller == "maxweight_backlog":
        modes = candidate_modes(e_value, d_value, q_value, conservative=True)
        target = 3 if q_value > 0.85 else 1
        safe_modes = [mode for mode in modes[target:] if mode["headroom"] > 0]
        return safe_modes[0] if safe_modes else modes[-1]
    if controller == "oracle_src":
        modes = candidate_modes(exact_risk, d_value, q_value, conservative=False)
    else:
        modes = candidate_modes(e_value, d_value, q_value, conservative=True)
    safe_modes = [mode for mode in modes if mode["headroom"] > 0]
    return safe_modes[0] if safe_modes else modes[-1]


def select_verification(controller: str, e_value: float, d_value: float, q_value: float, exact_risk: float) -> float:
    if controller in {"always_verify", "always_verify_throttle"}:
        return 1.0
    if controller == "minimal_verify":
        return 0.0
    threshold_risk = exact_risk if controller == "oracle_src" else min(0.99, e_value + 0.08)
    boundary = 0.45 - 0.22 * threshold_risk + 0.14 * q_value
    verify = 1.0 if d_value >= boundary else 0.0
    if controller == "plain_mpc" and q_value < 0.5:
        verify = max(0.0, verify - 0.25)
    if controller == "greedy_myopic":
        verify = 1.0 if (d_value + e_value) > 1.15 else 0.0
    if controller == "adaptive_threshold":
        boundary = 0.45 - 0.22 * min(0.99, e_value + 0.02) + 0.14 * max(q_value - 0.05, 0.0)
        verify = 1.0 if d_value >= boundary else 0.0
    if controller == "maxweight_backlog" and q_value > 0.85:
        verify = 1.0
    return float(np.clip(verify, 0.0, 1.0))


def select_context(controller: str, row: pd.Series, safe_mode: dict) -> tuple[int, float]:
    score_cols = [f"{atom}__score" for atom in ATOM_COLS]
    scores = [(atom, float(row[atom])) for atom in score_cols]
    scores.sort(key=lambda item: item[1], reverse=True)
    if controller == "oracle_src":
        chosen = [score for _, score in scores[:2] if score > 0]
    elif controller == "minimal_verify":
        chosen = [score for _, score in scores[:1] if score > 0]
    elif controller in {"rsrc_no_context", "headroom_only"}:
        chosen = []
    elif controller in {"adaptive_threshold", "always_verify_throttle", "maxweight_backlog"}:
        chosen = [score for _, score in scores[:1] if score > 0.02]
    else:
        conservative_margin = 0.05 if controller in {"rsrc", "se_mpc", "static_conservative", "rsrc_no_recovery"} else 0.0
        chosen = [score for _, score in scores[:2] if score - conservative_margin > 0]
    if controller == "se_mpc" and safe_mode["headroom"] > 0.10:
        chosen = [score for _, score in scores[:3] if score > -0.02]
    return len(chosen), float(sum(chosen))


def candidate_headrooms(e_values: np.ndarray, d_values: np.ndarray, q_values: np.ndarray, conservative: bool) -> np.ndarray:
    risk = np.minimum(0.99, e_values + (0.10 if conservative else 0.0))
    nominal_load = 0.18 + 0.22 * d_values + 0.18 * q_values
    rows = []
    for mode in GOVERNANCE_MODES:
        recovery_load = risk * mode.recovery_multiplier * (0.20 + 0.25 * d_values + 0.12 * q_values)
        rows.append(mode.service_floor - (nominal_load + recovery_load))
    return np.vstack(rows)


def select_safe_mode_indices(headrooms: np.ndarray) -> np.ndarray:
    safe_mask = headrooms > 0
    chosen = np.argmax(safe_mask, axis=0)
    chosen = chosen.astype(int)
    no_safe = ~safe_mask.any(axis=0)
    chosen[no_safe] = len(GOVERNANCE_MODES) - 1
    return chosen


def simulate_controller(tasks: pd.DataFrame, controller: str, seeds: int) -> dict:
    e_values = tasks["e_proxy"].to_numpy(dtype=float)
    d_values = tasks["d_proxy"].to_numpy(dtype=float)
    q_values = tasks["q_proxy"].to_numpy(dtype=float)
    difficulty = tasks.get("difficulty_score", pd.Series(0.5, index=tasks.index)).to_numpy(dtype=float)
    score_matrix = tasks[[f"{atom}__score" for atom in ATOM_COLS]].to_numpy(dtype=float)
    mode_services = np.asarray([mode.service_floor for mode in GOVERNANCE_MODES], dtype=float)
    mode_biases = np.asarray([mode.verification_bias for mode in GOVERNANCE_MODES], dtype=float)
    mode_amps = np.asarray([mode.recovery_multiplier for mode in GOVERNANCE_MODES], dtype=float)

    mode_counter: Counter[str] = Counter()
    all_success: list[float] = []
    all_cost: list[float] = []
    all_workload: list[float] = []
    all_overload: list[float] = []
    all_return_time: list[float] = []
    all_verify: list[float] = []
    all_atoms: list[float] = []

    for seed in range(seeds):
        rng = np.random.default_rng(seed + 101)
        exact_risk = np.clip(
            0.55 * e_values + 0.25 * d_values + 0.15 * q_values + 0.10 * difficulty + rng.normal(0.0, 0.03, size=len(tasks)),
            0.02,
            0.98,
        )

        if controller == "static_conservative":
            mode_idx = np.full(len(tasks), len(GOVERNANCE_MODES) - 1, dtype=int)
            headrooms = candidate_headrooms(e_values, d_values, q_values, conservative=True)
        elif controller == "static_aggressive":
            mode_idx = np.zeros(len(tasks), dtype=int)
            headrooms = candidate_headrooms(e_values, d_values, q_values, conservative=False)
        elif controller == "greedy_myopic":
            mode_idx = np.where(q_values > 0.8, 1, 0).astype(int)
            headrooms = candidate_headrooms(e_values, d_values, q_values, conservative=False)
        elif controller == "plain_mpc":
            headrooms = candidate_headrooms(e_values, d_values, q_values, conservative=False)
            mode_idx = np.argmin(np.abs(headrooms), axis=0).astype(int)
        elif controller == "always_verify_throttle":
            headrooms = candidate_headrooms(e_values, d_values, q_values, conservative=True)
            mode_idx = np.where(q_values > 0.8, len(GOVERNANCE_MODES) - 1, len(GOVERNANCE_MODES) - 2).astype(int)
        elif controller == "maxweight_backlog":
            headrooms = candidate_headrooms(e_values, d_values, q_values, conservative=True)
            mode_idx = np.where(q_values > 0.85, len(GOVERNANCE_MODES) - 1, 1).astype(int)
        elif controller == "oracle_src":
            headrooms = candidate_headrooms(exact_risk, d_values, q_values, conservative=False)
            mode_idx = select_safe_mode_indices(headrooms)
        else:
            headrooms = candidate_headrooms(e_values, d_values, q_values, conservative=True)
            if controller in {"headroom_only", "rsrc_no_recovery"}:
                nominal_load = 0.18 + 0.22 * d_values + 0.18 * q_values
                headrooms = np.vstack([mode.service_floor - nominal_load for mode in GOVERNANCE_MODES])
            mode_idx = select_safe_mode_indices(headrooms)

        chosen_headroom = headrooms[mode_idx, np.arange(len(tasks))]
        chosen_service = mode_services[mode_idx]
        chosen_bias = mode_biases[mode_idx]
        chosen_amp = mode_amps[mode_idx]

        if controller in {"always_verify", "always_verify_throttle"}:
            verify = np.ones(len(tasks), dtype=float)
        elif controller == "minimal_verify":
            verify = np.zeros(len(tasks), dtype=float)
        else:
            threshold_risk = exact_risk if controller == "oracle_src" else np.minimum(0.99, e_values + 0.08)
            boundary = 0.45 - 0.22 * threshold_risk + 0.14 * q_values
            verify = (d_values >= boundary).astype(float)
            if controller == "plain_mpc":
                verify = np.maximum(0.0, verify - 0.25 * (q_values < 0.5))
            if controller == "greedy_myopic":
                verify = (d_values + e_values > 1.15).astype(float)
            if controller == "adaptive_threshold":
                threshold_risk = np.minimum(0.99, e_values + 0.02)
                boundary = 0.45 - 0.22 * threshold_risk + 0.14 * np.maximum(q_values - 0.05, 0.0)
                verify = (d_values >= boundary).astype(float)
            if controller == "maxweight_backlog":
                verify = np.maximum(verify, (q_values > 0.85).astype(float))

        sorted_scores = np.sort(score_matrix, axis=1)[:, ::-1]
        if controller == "oracle_src":
            chosen_scores = np.where(sorted_scores[:, :2] > 0, sorted_scores[:, :2], 0.0)
        elif controller == "minimal_verify":
            chosen_scores = np.where(sorted_scores[:, :1] > 0, sorted_scores[:, :1], 0.0)
        elif controller in {"rsrc_no_context", "headroom_only"}:
            chosen_scores = np.zeros((len(tasks), 1), dtype=float)
        elif controller in {"adaptive_threshold", "always_verify_throttle", "maxweight_backlog"}:
            chosen_scores = np.where(sorted_scores[:, :1] > 0.02, sorted_scores[:, :1], 0.0)
        else:
            conservative_margin = 0.05 if controller in {"rsrc", "se_mpc", "static_conservative", "rsrc_no_recovery"} else 0.0
            chosen_scores = np.where(sorted_scores[:, :2] - conservative_margin > 0, sorted_scores[:, :2], 0.0)
        if controller == "se_mpc":
            se_mask = sorted_scores[:, :3] > -0.02
            se_scores = np.where(se_mask, sorted_scores[:, :3], 0.0)
            use_three = chosen_headroom > 0.10
            context_gain = np.where(use_three, se_scores.sum(axis=1), chosen_scores.sum(axis=1))
            atoms_selected = np.where(use_three, se_mask.sum(axis=1), (chosen_scores != 0).sum(axis=1))
        else:
            context_gain = chosen_scores.sum(axis=1)
            atoms_selected = (chosen_scores != 0).sum(axis=1)

        if controller == "se_mpc":
            verify = np.maximum(0.0, verify - 0.10 * (chosen_headroom > 0.08))
        if controller == "plain_mpc":
            verify = np.maximum(0.0, verify - 0.15)

        verification_benefit = 0.30 * verify + 0.08 * chosen_bias
        context_benefit = 0.05 * atoms_selected + 0.06 * np.maximum(context_gain, 0.0)
        failure_prob = np.clip(exact_risk - verification_benefit - context_benefit + 0.04 * np.maximum(0.0, q_values - 0.5), 0.02, 0.98)
        success = (rng.random(len(tasks)) > failure_prob).astype(float)

        nominal_load = 0.15 + 0.20 * d_values + 0.15 * q_values + 0.10 * verify + 0.03 * atoms_selected
        recovery_load = failure_prob * chosen_amp * (0.25 + 0.35 * d_values + 0.20 * q_values)
        workload = np.maximum(0.0, nominal_load + recovery_load - chosen_service)
        overload = (workload > 0.02).astype(float)
        return_time = 1.0 + workload / np.maximum(chosen_service, 0.10) + failure_prob * chosen_amp
        discounted_cost = workload + 0.35 * verify + 0.50 * recovery_load + 0.30 * (1.0 - success)

        mode_counts = np.bincount(mode_idx, minlength=len(GOVERNANCE_MODES))
        for index, count in enumerate(mode_counts):
            if count:
                mode_counter[GOVERNANCE_MODES[index].name] += int(count)

        all_success.extend(success.tolist())
        all_cost.extend(discounted_cost.tolist())
        all_workload.extend(workload.tolist())
        all_overload.extend(overload.tolist())
        all_return_time.extend(return_time.tolist())
        all_verify.extend(verify.tolist())
        all_atoms.extend(atoms_selected.astype(float).tolist())

    frame = pd.DataFrame(
        {
            "success": all_success,
            "cost": all_cost,
            "workload": all_workload,
            "overload": all_overload,
            "return_time": all_return_time,
            "verification": all_verify,
            "atoms_selected": all_atoms,
        }
    )
    return {
        "controller": controller,
        "success_rate": float(frame["success"].mean()),
        "discounted_cost": float(frame["cost"].mean()),
        "avg_workload": float(frame["workload"].mean()),
        "overload_rate": float(frame["overload"].mean()),
        "avg_return_time": float(frame["return_time"].mean()),
        "verification_rate": float(frame["verification"].mean()),
        "avg_atoms_selected": float(frame["atoms_selected"].mean()),
        "mode_distribution": dict(mode_counter),
    }


def load_datasets(dataset: str, paths: dict[str, Path]) -> dict[str, pd.DataFrame]:
    datasets: dict[str, pd.DataFrame] = {}
    if dataset in {"verified", "both", "all"}:
        datasets["verified"] = pd.read_csv(paths["swe_verified_tasks"])
    if dataset in {"test", "both", "all"}:
        swe_bench = pd.read_csv(paths["swe_bench_tasks"])
        datasets["test"] = swe_bench[swe_bench["split"] == "test"].copy()
    if dataset in {"rebench", "all"}:
        datasets["rebench"] = pd.read_csv(paths["swe_rebench_tasks"])
    if dataset in {"smith", "all"}:
        datasets["smith"] = pd.read_csv(paths["swe_smith_tasks"])
    return datasets


def main() -> None:
    parser = argparse.ArgumentParser(description="Run dataset-grounded controller benchmarks for the theorem support layer.")
    parser.add_argument("--manifest-dir", type=Path, default=MANIFEST_DIR)
    parser.add_argument("--output-dir", type=Path, default=RESULTS_DIR / "benchmark")
    parser.add_argument("--dataset", choices=["verified", "test", "both", "rebench", "smith", "all"], default="both")
    parser.add_argument("--max-tasks", type=int, default=None)
    parser.add_argument("--seeds", type=int, default=24)
    args = parser.parse_args()

    output_dir = ensure_dir(args.output_dir)
    paths = manifest_paths(args.manifest_dir)
    risk_prior, atom_prior = fit_priors(args.manifest_dir)

    datasets = load_datasets(args.dataset, paths)

    controller_names = [
        "oracle_src",
        "rsrc",
        "se_mpc",
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

    all_results = []
    for dataset_name, frame in datasets.items():
        if args.max_tasks is not None:
            frame = frame.head(args.max_tasks).copy()
        prepared = apply_priors(frame, risk_prior, atom_prior)
        for controller in controller_names:
            result = simulate_controller(prepared, controller, seeds=args.seeds)
            result["dataset"] = dataset_name
            result["task_count"] = int(len(prepared))
            all_results.append(result)

    results_frame = pd.DataFrame(all_results)
    results_frame.to_csv(output_dir / "controller_results.csv", index=False)
    write_json(output_dir / "controller_results.json", {"results": all_results, "seeds": args.seeds})

    print("Controller benchmark complete.")
    print(results_frame[["dataset", "controller", "success_rate", "discounted_cost", "avg_workload", "overload_rate"]].to_string(index=False))


if __name__ == "__main__":
    main()
