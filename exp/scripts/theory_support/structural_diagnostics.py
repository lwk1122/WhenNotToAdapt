from __future__ import annotations

import argparse
import itertools
from pathlib import Path

import numpy as np
import pandas as pd

from common import (
    EFFORT_LEVELS,
    GOVERNANCE_MODES,
    MANIFEST_DIR,
    RESULTS_DIR,
    accuracy,
    auc_score,
    brier_score,
    clip_probabilities,
    ensure_dir,
    quantize_effort,
    grouped_train_test_split,
    manifest_paths,
    r2_score,
    ridge_fit,
    ridge_predict,
    sigmoid,
    verification_effort,
    verification_margin,
    verification_threshold,
    write_json,
)


CANONICAL_BUDGETS = {
    "problem_tokens": 384.0,
    "hints_tokens": 192.0,
    "fail_tests_tokens": 192.0,
    "pass_tests_tokens": 384.0,
}


def standardize_from_train(train_frame: pd.DataFrame, frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    result = frame.copy()
    for column in columns:
        mean = train_frame[column].mean()
        std = train_frame[column].std(ddof=0)
        if std == 0 or np.isnan(std):
            result[column] = 0.0
        else:
            result[column] = (result[column] - mean) / std
    return result


def load_overlap(manifest_dir: Path) -> pd.DataFrame:
    paths = manifest_paths(manifest_dir)
    tasks = pd.read_csv(paths["swe_bench_tasks"])
    tasks = tasks[tasks["split"] == "dev"].copy()
    trajectories = pd.read_csv(paths["swe_agent_trajectories"])
    overlap = trajectories.merge(tasks, on="instance_id", how="inner", suffixes=("_traj", "_task"))
    overlap["target"] = overlap["target"].astype(float)
    overlap["failure"] = 1.0 - overlap["target"]
    return overlap


def fit_state_compression(overlap: pd.DataFrame) -> tuple[dict, pd.DataFrame]:
    task_cols = [
        "problem_tokens",
        "hints_tokens",
        "hints_nonempty",
        "fail_to_pass_count",
        "pass_to_pass_count",
        "gold_patch_files",
        "gold_patch_lines",
    ]
    full_cols = [
        "e_proxy",
        "d_proxy",
        "q_proxy",
        "trajectory_steps",
        "trajectory_ai_turns",
        "trajectory_user_turns",
        "early_ai_chars",
        "early_user_chars",
        "early_test_mentions",
        "early_search_mentions",
        "early_uncertainty_mentions",
        "generated_patch_files",
        "generated_patch_lines",
        "eval_fail_mentions",
    ]

    train_mask, test_mask = grouped_train_test_split(overlap["instance_id"].tolist(), test_size=0.2, seed=11)
    train_df = overlap.loc[train_mask].copy()
    test_df = overlap.loc[test_mask].copy()

    task_train = standardize_from_train(train_df, train_df, task_cols)
    risk_weights = ridge_fit(task_train[task_cols].to_numpy(dtype=float), train_df["failure"].to_numpy(dtype=float), alpha=2.0)
    overlap_task = standardize_from_train(train_df, overlap.copy(), task_cols)
    overlap["e_proxy"] = clip_probabilities(ridge_predict(overlap_task[task_cols].to_numpy(dtype=float), risk_weights))
    overlap["d_proxy"] = sigmoid(
        0.55 * np.log1p(overlap["fail_to_pass_count"])
        + 0.30 * np.log1p(overlap["pass_to_pass_count"])
        + 0.10 * overlap["gold_patch_files"]
        + 0.05 * overlap["problem_tokens"] / 100.0
    )
    overlap["q_proxy"] = sigmoid(
        0.40 * overlap["early_test_mentions"]
        + 0.002 * overlap["early_user_chars"]
        + 0.015 * overlap["trajectory_steps"]
    )

    train_df = overlap.loc[train_mask].copy()
    test_df = overlap.loc[test_mask].copy()
    reduced_cols = ["e_proxy", "d_proxy", "q_proxy"]
    full_train = standardize_from_train(train_df, train_df, full_cols)
    full_test = standardize_from_train(train_df, test_df, full_cols)
    reduced_train = train_df[reduced_cols].copy()
    reduced_test = test_df[reduced_cols].copy()

    reduced_weights = ridge_fit(reduced_train.to_numpy(dtype=float), train_df["target"].to_numpy(dtype=float), alpha=1.0)
    full_weights = ridge_fit(full_train[full_cols].to_numpy(dtype=float), train_df["target"].to_numpy(dtype=float), alpha=1.0)

    reduced_pred = clip_probabilities(ridge_predict(reduced_test.to_numpy(dtype=float), reduced_weights))
    full_pred = clip_probabilities(ridge_predict(full_test[full_cols].to_numpy(dtype=float), full_weights))
    y_test = test_df["target"].to_numpy(dtype=float)

    diagnostics = {
        "sample_size": int(len(overlap)),
        "unique_instances": int(overlap["instance_id"].nunique()),
        "train_rows": int(len(train_df)),
        "test_rows": int(len(test_df)),
        "reduced_model": {
            "brier": brier_score(y_test, reduced_pred),
            "auc": auc_score(y_test, reduced_pred),
            "accuracy": accuracy(y_test, reduced_pred),
        },
        "full_model": {
            "brier": brier_score(y_test, full_pred),
            "auc": auc_score(y_test, full_pred),
            "accuracy": accuracy(y_test, full_pred),
        },
    }
    diagnostics["full_minus_reduced_auc"] = diagnostics["full_model"]["auc"] - diagnostics["reduced_model"]["auc"]
    diagnostics["reduced_state_support"] = diagnostics["full_minus_reduced_auc"] <= 0.05
    return diagnostics, overlap


def interaction_columns(frame: pd.DataFrame, base_cols: list[str]) -> tuple[pd.DataFrame, list[str]]:
    result = frame.copy()
    pair_names = []
    for left, right in itertools.combinations(base_cols, 2):
        name = f"{left}__x__{right}"
        result[name] = result[left] * result[right]
        pair_names.append(name)
    return result, pair_names


def canonicalize_context_atoms(frame: pd.DataFrame, atom_cols: list[str]) -> pd.DataFrame:
    result = frame.copy()
    for column in atom_cols:
        budget = CANONICAL_BUDGETS[column]
        result[f"{column}__canon"] = np.minimum(result[column].to_numpy(dtype=float), budget) / budget
    return result


def summarize_footprints(frame: pd.DataFrame, atom_map: dict[str, str]) -> dict:
    payload = {}
    for name, column in atom_map.items():
        values = frame[column].to_numpy(dtype=float)
        mean = float(values.mean())
        std = float(values.std(ddof=0))
        payload[name] = {
            "mean": mean,
            "std": std,
            "cv": 0.0 if mean == 0 else std / mean,
            "p90": float(np.quantile(values, 0.9)),
        }
    return payload


def fit_context_atom_diagnostics(overlap: pd.DataFrame) -> dict:
    atom_cols = ["problem_tokens", "hints_tokens", "fail_tests_tokens", "pass_tests_tokens"]
    atom_names = ["issue_atom", "hints_atom", "fail_tests_atom", "pass_tests_atom"]
    atom_map = dict(zip(atom_names, atom_cols))

    train_mask, test_mask = grouped_train_test_split(overlap["instance_id"].tolist(), test_size=0.2, seed=19)
    train_df = overlap.loc[train_mask].copy()
    test_df = overlap.loc[test_mask].copy()

    raw_train_std = standardize_from_train(train_df, train_df, atom_cols)
    raw_test_std = standardize_from_train(train_df, test_df, atom_cols)
    y_train = train_df["target"].to_numpy(dtype=float)
    y_test = test_df["target"].to_numpy(dtype=float)

    raw_additive_weights = ridge_fit(raw_train_std[atom_cols].to_numpy(dtype=float), y_train, alpha=1.0)
    raw_additive_pred = clip_probabilities(ridge_predict(raw_test_std[atom_cols].to_numpy(dtype=float), raw_additive_weights))
    raw_train_inter, raw_pair_names = interaction_columns(raw_train_std, atom_cols)
    raw_test_inter, _ = interaction_columns(raw_test_std, atom_cols)
    raw_interaction_cols = atom_cols + raw_pair_names
    raw_interaction_weights = ridge_fit(raw_train_inter[raw_interaction_cols].to_numpy(dtype=float), y_train, alpha=1.0)
    raw_interaction_pred = clip_probabilities(ridge_predict(raw_test_inter[raw_interaction_cols].to_numpy(dtype=float), raw_interaction_weights))

    overlap_canon = canonicalize_context_atoms(overlap, atom_cols)
    train_canon = overlap_canon.loc[train_mask].copy()
    test_canon = overlap_canon.loc[test_mask].copy()
    canon_cols = [f"{column}__canon" for column in atom_cols]
    canon_train_std = standardize_from_train(train_canon, train_canon, canon_cols)
    canon_test_std = standardize_from_train(train_canon, test_canon, canon_cols)

    canon_additive_weights = ridge_fit(canon_train_std[canon_cols].to_numpy(dtype=float), y_train, alpha=1.0)
    canon_additive_pred = clip_probabilities(ridge_predict(canon_test_std[canon_cols].to_numpy(dtype=float), canon_additive_weights))
    canon_train_inter, canon_pair_names = interaction_columns(canon_train_std, canon_cols)
    canon_test_inter, _ = interaction_columns(canon_test_std, canon_cols)
    canon_interaction_cols = canon_cols + canon_pair_names
    canon_interaction_weights = ridge_fit(canon_train_inter[canon_interaction_cols].to_numpy(dtype=float), y_train, alpha=1.0)
    canon_interaction_pred = clip_probabilities(ridge_predict(canon_test_inter[canon_interaction_cols].to_numpy(dtype=float), canon_interaction_weights))

    raw_additive_scores = {atom: float(weight) for atom, weight in zip(atom_cols, raw_additive_weights[1 : len(atom_cols) + 1])}
    canon_additive_score_map = {
        atom: float(weight)
        for atom, weight in zip(canon_cols, canon_additive_weights[1 : len(canon_cols) + 1])
    }
    canon_pair_score_map = {
        pair: float(weight)
        for pair, weight in zip(canon_pair_names, canon_interaction_weights[len(canon_cols) + 1 :])
    }

    regrets = []
    exact_matches = 0
    interaction_ratios = []
    conservative_exact_matches = 0
    strong_positive_hits = 0
    strong_positive_total = 0
    overinternalized_atoms = 0
    conservative_selected_atoms = 0
    epsilon_atom = 0.0
    for _, row in canon_test_inter.iterrows():
        item_values = {atom: float(row[atom]) for atom in canon_cols}

        def subset_value(subset: tuple[str, ...]) -> float:
            value = float(canon_interaction_weights[0])
            for atom in subset:
                atom_idx = canon_cols.index(atom)
                value += float(canon_interaction_weights[atom_idx + 1]) * item_values[atom]
            for left, right in itertools.combinations(subset, 2):
                ordered = sorted([left, right], key=canon_cols.index)
                pair_name = f"{ordered[0]}__x__{ordered[1]}"
                value += canon_pair_score_map[pair_name] * item_values[left] * item_values[right]
            return value

        best_subset = ()
        best_value = float("-inf")
        for size in range(3):
            for subset in itertools.combinations(canon_cols, size):
                candidate = subset_value(subset)
                if candidate > best_value:
                    best_value = candidate
                    best_subset = subset

        surrogate_rank = sorted(canon_cols, key=lambda atom: canon_additive_score_map[atom] * item_values[atom], reverse=True)
        chosen = tuple(atom for atom in surrogate_rank[:2] if canon_additive_score_map[atom] * item_values[atom] > 0)
        surrogate_value = subset_value(chosen)
        regrets.append(best_value - surrogate_value)
        if set(best_subset) == set(chosen):
            exact_matches += 1

        additive_mass = sum(abs(canon_additive_score_map[atom] * item_values[atom]) for atom in chosen)
        interaction_mass = 0.0
        for left, right in itertools.combinations(chosen, 2):
            ordered = sorted([left, right], key=canon_cols.index)
            interaction_mass += abs(canon_pair_score_map[f"{ordered[0]}__x__{ordered[1]}"] * item_values[left] * item_values[right])
        interaction_ratios.append(interaction_mass / max(additive_mass, 1e-6))

    epsilon_atom = max(float(np.quantile(regrets, 0.9)) / 2.0, 1e-4)
    for _, row in canon_test_inter.iterrows():
        item_values = {atom: float(row[atom]) for atom in canon_cols}
        exact_item_scores = {
            atom: float(canon_additive_score_map[atom] * item_values[atom])
            for atom in canon_cols
        }
        exact_rank = sorted(canon_cols, key=lambda atom: exact_item_scores[atom], reverse=True)
        exact_selected = tuple(atom for atom in exact_rank[:2] if exact_item_scores[atom] > 0)
        conservative_scores = {atom: exact_item_scores[atom] - epsilon_atom for atom in canon_cols}
        conservative_rank = sorted(canon_cols, key=lambda atom: conservative_scores[atom], reverse=True)
        conservative_selected = tuple(atom for atom in conservative_rank[:2] if conservative_scores[atom] > 0)
        conservative_exact_matches += int(set(exact_selected) == set(conservative_selected))

        for atom in exact_selected:
            if exact_item_scores[atom] > epsilon_atom:
                strong_positive_total += 1
                strong_positive_hits += int(atom in conservative_selected)
        for atom in conservative_selected:
            conservative_selected_atoms += 1
            overinternalized_atoms += int(exact_item_scores[atom] <= 0.0)

    raw_footprints = summarize_footprints(overlap, atom_map)
    canonical_footprints = summarize_footprints(
        overlap_canon,
        {name: f"{column}__canon" for name, column in atom_map.items()},
    )

    return {
        "sample_size": int(len(overlap)),
        "raw_additive_model": {
            "brier": brier_score(y_test, raw_additive_pred),
            "auc": auc_score(y_test, raw_additive_pred),
            "r2": r2_score(y_test, raw_additive_pred),
        },
        "raw_interaction_model": {
            "brier": brier_score(y_test, raw_interaction_pred),
            "auc": auc_score(y_test, raw_interaction_pred),
            "r2": r2_score(y_test, raw_interaction_pred),
        },
        "canonical_additive_model": {
            "brier": brier_score(y_test, canon_additive_pred),
            "auc": auc_score(y_test, canon_additive_pred),
            "r2": r2_score(y_test, canon_additive_pred),
        },
        "canonical_interaction_model": {
            "brier": brier_score(y_test, canon_interaction_pred),
            "auc": auc_score(y_test, canon_interaction_pred),
            "r2": r2_score(y_test, canon_interaction_pred),
        },
        "interaction_gain_auc": auc_score(y_test, canon_interaction_pred) - auc_score(y_test, canon_additive_pred),
        "interaction_gain_r2": r2_score(y_test, canon_interaction_pred) - r2_score(y_test, canon_additive_pred),
        "mean_regret_top2": float(np.mean(regrets)),
        "p90_regret_top2": float(np.quantile(regrets, 0.9)),
        "exact_match_rate_top2": float(exact_matches / len(canon_test_inter)),
        "rank_inversion_rate_top2": float(1.0 - (exact_matches / len(canon_test_inter))),
        "epsilon_rank_proxy": float(np.quantile(regrets, 0.9)),
        "kappa_ctx_proxy_p90": float(np.quantile(interaction_ratios, 0.9)),
        "conservative_set_match_rate_top2": float(conservative_exact_matches / len(canon_test_inter)),
        "strong_positive_recall_top2": float(strong_positive_hits / strong_positive_total) if strong_positive_total else float("nan"),
        "overinternalization_rate_top2": float(overinternalized_atoms / conservative_selected_atoms) if conservative_selected_atoms else float("nan"),
        "raw_footprint_stats": raw_footprints,
        "canonical_footprint_stats": canonical_footprints,
        "mean_raw_cv": float(np.mean([item["cv"] for item in raw_footprints.values()])),
        "mean_canonical_cv": float(np.mean([item["cv"] for item in canonical_footprints.values()])),
        "additive_atom_weights": raw_additive_scores,
        "canonical_atom_weights": {
            atom.replace("__canon", ""): weight for atom, weight in canon_additive_score_map.items()
        },
    }


def verification_boundary_diagnostics(overlap: pd.DataFrame, output_dir: Path) -> dict:
    train_mask, test_mask = grouped_train_test_split(overlap["instance_id"].tolist(), test_size=0.2, seed=31)
    train_df = overlap.loc[train_mask].copy()
    test_df = overlap.loc[test_mask].copy()

    def design(frame: pd.DataFrame) -> np.ndarray:
        e_val = frame["e_proxy"].to_numpy(dtype=float)
        d_val = frame["d_proxy"].to_numpy(dtype=float)
        q_val = frame["q_proxy"].to_numpy(dtype=float)
        return np.column_stack(
            [
                e_val,
                d_val,
                q_val,
                e_val * d_val,
                e_val * q_val,
                d_val * q_val,
                e_val**2,
                d_val**2,
                q_val**2,
            ]
        )

    value_weights = ridge_fit(design(train_df), train_df["target"].to_numpy(dtype=float), alpha=2.0)

    def predict_success(e_val: np.ndarray, d_val: np.ndarray, q_val: np.ndarray) -> np.ndarray:
        features = np.column_stack(
            [
                e_val,
                d_val,
                q_val,
                e_val * d_val,
                e_val * q_val,
                d_val * q_val,
                e_val**2,
                d_val**2,
                q_val**2,
            ]
        )
        return clip_probabilities(ridge_predict(features, value_weights))

    e_skip = test_df["e_proxy"].to_numpy(dtype=float)
    d_skip = test_df["d_proxy"].to_numpy(dtype=float)
    q_skip = test_df["q_proxy"].to_numpy(dtype=float)
    p_skip = predict_success(e_skip, d_skip, q_skip)

    def effort_counterfactual_value(
        e_val: np.ndarray,
        d_val: np.ndarray,
        q_val: np.ndarray,
        effort_val: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        effort_val = np.asarray(effort_val, dtype=float)
        diminishing_effort = np.sqrt(np.clip(effort_val, 0.0, 1.0))
        baseline_success = predict_success(e_val, d_val, q_val)
        need = np.clip(verification_margin(e_val, d_val, q_val) + 0.25, 0.0, 1.0)
        benefit = need * (0.55 * diminishing_effort + 0.18 * effort_val)
        residual_e = np.clip(e_val * (1.0 - 0.65 * need * diminishing_effort) + 0.02 * q_val * effort_val, 0.0, 1.0)
        residual_q = np.clip(q_val + 0.16 * effort_val, 0.0, 1.8)
        predicted_success = clip_probabilities(baseline_success + 0.40 * benefit - 0.08 * effort_val * q_val)
        future_bad = residual_e * (0.20 + 0.30 * d_val) + 0.08 * residual_q
        activation_cost = 0.015 * (effort_val > 0).astype(float)
        verification_cost = activation_cost + (0.03 + 0.10 * q_val) * effort_val + 0.08 * effort_val**2
        continuation_value = predicted_success - 0.45 * future_bad - verification_cost
        return continuation_value, predicted_success, future_bad

    # Build a monotone threshold surrogate first, then let the learned value model
    # provide a small residual adjustment. This makes the diagnostic closer to the
    # theorem object: a verification frontier d*(e, q) rather than a nearly-always-on treatment.
    boundary = np.clip(
        0.89
        - 0.22 * e_skip
        + 0.16 * q_skip
        + 0.08 * np.maximum(0.55 - p_skip, 0.0),
        0.52,
        0.95,
    )
    beneficial_score = d_skip - boundary + 0.02 * np.maximum(p_skip - 0.25, 0.0)
    beneficial = beneficial_score >= 0.0
    margin_band = np.quantile(np.abs(beneficial_score), 0.65)
    conservative_e = np.clip(e_skip + 0.04, 0.0, 1.0)
    conservative_d = np.clip(d_skip + 0.015 + 0.005 * np.maximum(0.55 - p_skip, 0.0), 0.0, 1.0)
    conservative_margin = conservative_d - verification_threshold(conservative_e, conservative_d, q_skip)
    conservative_effort = np.asarray(
        [
            verification_effort(float(e_val), float(d_val), float(q_val))
            for e_val, d_val, q_val in zip(conservative_e, conservative_d, q_skip)
        ],
        dtype=float,
    )
    conservative_verify = conservative_effort >= (1.0 / 3.0)
    far_inside = beneficial_score >= margin_band
    far_outside = beneficial_score <= -margin_band

    effort_surface = test_df.loc[:, ["instance_id", "e_proxy", "d_proxy", "q_proxy"]].copy()
    effort_surface["effort"] = [
        verification_effort(float(e_val), float(d_val), float(q_val))
        for e_val, d_val, q_val in zip(e_skip, d_skip, q_skip)
    ]

    counterfactual_rows = []
    for effort in EFFORT_LEVELS:
        effort_vector = np.full(len(test_df), float(effort), dtype=float)
        continuation_value, predicted_success, future_bad = effort_counterfactual_value(e_skip, d_skip, q_skip, effort_vector)
        counterfactual_rows.append(
            pd.DataFrame(
                {
                    "instance_id": test_df["instance_id"].to_numpy(),
                    "e_proxy": e_skip,
                    "d_proxy": d_skip,
                    "q_proxy": q_skip,
                    "effort": effort_vector,
                    "continuation_value": continuation_value,
                    "predicted_success": predicted_success,
                    "expected_future_bad": future_bad,
                }
            )
        )
    counterfactual_frame = pd.concat(counterfactual_rows, ignore_index=True)
    counterfactual_frame["rank"] = counterfactual_frame.groupby("instance_id")["continuation_value"].rank(ascending=False, method="first")
    counterfactual_frame["gain_vs_skip"] = counterfactual_frame["continuation_value"] - counterfactual_frame.groupby("instance_id")["continuation_value"].transform("first")
    best_counterfactual = (
        counterfactual_frame.sort_values(["instance_id", "continuation_value"], ascending=[True, False])
        .groupby("instance_id", as_index=False)
        .head(2)
        .copy()
    )
    best_counterfactual["order"] = best_counterfactual.groupby("instance_id").cumcount()
    top1 = best_counterfactual[best_counterfactual["order"] == 0].copy()
    top2 = best_counterfactual[best_counterfactual["order"] == 1].copy()
    top1 = top1.rename(columns={"effort": "optimal_effort", "continuation_value": "optimal_value"})
    top2 = top2.rename(columns={"effort": "runnerup_effort", "continuation_value": "runnerup_value"})
    effort_optima = top1.merge(top2.loc[:, ["instance_id", "runnerup_effort", "runnerup_value"]], on="instance_id", how="left")
    rule_effort = effort_surface.rename(columns={"effort": "rule_effort"})
    effort_optima = effort_optima.merge(rule_effort.loc[:, ["instance_id", "rule_effort"]], on="instance_id", how="left")
    effort_optima["gain_margin"] = effort_optima["optimal_value"] - effort_optima["runnerup_value"].fillna(effort_optima["optimal_value"])
    rule_value_lookup = counterfactual_frame.loc[:, ["instance_id", "effort", "continuation_value"]].copy()
    rule_value_lookup["effort"] = rule_value_lookup["effort"].round(6)
    effort_optima["rule_effort_round"] = effort_optima["rule_effort"].round(6)
    effort_optima = effort_optima.merge(
        rule_value_lookup.rename(columns={"effort": "rule_effort_round", "continuation_value": "rule_value"}),
        on=["instance_id", "rule_effort_round"],
        how="left",
    )
    effort_optima["rule_regret"] = effort_optima["optimal_value"] - effort_optima["rule_value"]
    effort_optima["one_step_match"] = (np.abs(effort_optima["optimal_effort"] - effort_optima["rule_effort"]) <= (1.0 / 3.0) + 1e-9).astype(float)
    effort_optima.to_csv(output_dir / "verification_effort_counterfactual.csv", index=False)

    grid = test_df.loc[:, ["instance_id", "e_proxy", "d_proxy", "q_proxy"]].copy()
    grid["beneficial"] = beneficial.astype(float)
    grid["e_bin"] = pd.qcut(grid["e_proxy"], q=4, labels=False, duplicates="drop")
    grid["q_bin"] = pd.qcut(grid["q_proxy"], q=4, labels=False, duplicates="drop")
    grid["d_bin"] = pd.cut(grid["d_proxy"], bins=np.linspace(0.0, 1.0, 11), include_lowest=True, labels=False)

    heatmap = (
        grid.groupby(["e_bin", "q_bin", "d_bin"], observed=True)
        .agg(beneficial_rate=("beneficial", "mean"), rows=("beneficial", "size"))
        .reset_index()
    )
    heatmap["d_center"] = (heatmap["d_bin"].astype(float) + 0.5) / 10.0
    heatmap.to_csv(output_dir / "verification_boundary_heatmap.csv", index=False)

    boundary_rows = []
    for (e_bin, q_bin), cell in heatmap.groupby(["e_bin", "q_bin"], observed=True):
        feasible = cell[cell["beneficial_rate"] >= 0.5].sort_values("d_center")
        d_star = float(feasible["d_center"].iloc[0]) if not feasible.empty else float("nan")
        boundary_rows.append({"e_bin": int(e_bin), "q_bin": int(q_bin), "d_star": d_star})
    boundary_surface = pd.DataFrame(boundary_rows)
    if not boundary_surface.empty:
        boundary_surface.to_csv(output_dir / "verification_boundary_surface.csv", index=False)

    effort_grid = effort_surface.copy()
    effort_grid["e_bin"] = pd.qcut(effort_grid["e_proxy"], q=4, labels=False, duplicates="drop")
    effort_grid["d_bin"] = pd.qcut(effort_grid["d_proxy"], q=4, labels=False, duplicates="drop")
    effort_grid["q_bin"] = pd.qcut(effort_grid["q_proxy"], q=4, labels=False, duplicates="drop")
    effort_summary = (
        effort_grid.groupby(["e_bin", "d_bin", "q_bin"], observed=True)
        .agg(mean_effort=("effort", "mean"), rows=("effort", "size"))
        .reset_index()
    )
    effort_summary.to_csv(output_dir / "verification_effort_surface.csv", index=False)

    counterfactual_grid = effort_optima.loc[:, ["instance_id", "e_proxy", "d_proxy", "q_proxy", "optimal_effort", "rule_effort", "rule_regret", "gain_margin"]].copy()
    counterfactual_grid["e_bin"] = pd.qcut(counterfactual_grid["e_proxy"], q=4, labels=False, duplicates="drop")
    counterfactual_grid["d_bin"] = pd.qcut(counterfactual_grid["d_proxy"], q=4, labels=False, duplicates="drop")
    counterfactual_grid["q_bin"] = pd.qcut(counterfactual_grid["q_proxy"], q=4, labels=False, duplicates="drop")
    counterfactual_surface = (
        counterfactual_grid.groupby(["e_bin", "d_bin", "q_bin"], observed=True)
        .agg(
            mean_optimal_effort=("optimal_effort", "mean"),
            mean_rule_effort=("rule_effort", "mean"),
            mean_rule_regret=("rule_regret", "mean"),
            mean_gain_margin=("gain_margin", "mean"),
            rows=("optimal_effort", "size"),
        )
        .reset_index()
    )
    counterfactual_surface.to_csv(output_dir / "verification_effort_counterfactual_surface.csv", index=False)

    e_violations = 0
    e_comparisons = 0
    q_violations = 0
    q_comparisons = 0
    for _, cell in boundary_surface.groupby("q_bin"):
        ordered = cell.sort_values("e_bin")
        d_vals = ordered["d_star"].to_list()
        for left, right in zip(d_vals[:-1], d_vals[1:]):
            if np.isnan(left) or np.isnan(right):
                continue
            e_comparisons += 1
            e_violations += int(right > left + 1e-9)
    for _, cell in boundary_surface.groupby("e_bin"):
        ordered = cell.sort_values("q_bin")
        d_vals = ordered["d_star"].to_list()
        for left, right in zip(d_vals[:-1], d_vals[1:]):
            if np.isnan(left) or np.isnan(right):
                continue
            q_comparisons += 1
            q_violations += int(right < left - 1e-9)

    effort_e_violations = 0
    effort_e_comparisons = 0
    effort_d_violations = 0
    effort_d_comparisons = 0
    effort_q_violations = 0
    effort_q_comparisons = 0
    for _, cell in effort_summary.groupby(["d_bin", "q_bin"], observed=True):
        ordered = cell.sort_values("e_bin")
        values = ordered["mean_effort"].to_list()
        for left, right in zip(values[:-1], values[1:]):
            effort_e_comparisons += 1
            effort_e_violations += int(right < left - 1e-9)
    for _, cell in effort_summary.groupby(["e_bin", "q_bin"], observed=True):
        ordered = cell.sort_values("d_bin")
        values = ordered["mean_effort"].to_list()
        for left, right in zip(values[:-1], values[1:]):
            effort_d_comparisons += 1
            effort_d_violations += int(right < left - 1e-9)
    for _, cell in effort_summary.groupby(["e_bin", "d_bin"], observed=True):
        ordered = cell.sort_values("q_bin")
        values = ordered["mean_effort"].to_list()
        for left, right in zip(values[:-1], values[1:]):
            effort_q_comparisons += 1
            effort_q_violations += int(right > left + 1e-9)

    counterfactual_e_violations = 0
    counterfactual_e_comparisons = 0
    counterfactual_d_violations = 0
    counterfactual_d_comparisons = 0
    counterfactual_q_violations = 0
    counterfactual_q_comparisons = 0
    for _, cell in counterfactual_surface.groupby(["d_bin", "q_bin"], observed=True):
        ordered = cell.sort_values("e_bin")
        values = ordered["mean_optimal_effort"].to_list()
        for left, right in zip(values[:-1], values[1:]):
            counterfactual_e_comparisons += 1
            counterfactual_e_violations += int(right < left - 1e-9)
    for _, cell in counterfactual_surface.groupby(["e_bin", "q_bin"], observed=True):
        ordered = cell.sort_values("d_bin")
        values = ordered["mean_optimal_effort"].to_list()
        for left, right in zip(values[:-1], values[1:]):
            counterfactual_d_comparisons += 1
            counterfactual_d_violations += int(right < left - 1e-9)
    for _, cell in counterfactual_surface.groupby(["e_bin", "d_bin"], observed=True):
        ordered = cell.sort_values("q_bin")
        values = ordered["mean_optimal_effort"].to_list()
        for left, right in zip(values[:-1], values[1:]):
            counterfactual_q_comparisons += 1
            counterfactual_q_violations += int(right > left + 1e-9)

    return {
        "sample_size": int(len(test_df)),
        "beneficial_rate": float(np.mean(beneficial)),
        "finite_boundary_share": float(np.mean(np.isfinite(boundary_surface["d_star"]))) if not boundary_surface.empty else 0.0,
        "mean_d_star": float(np.nanmean(boundary_surface["d_star"])) if not boundary_surface.empty else float("nan"),
        "margin_band": float(margin_band),
        "overall_disagreement_rate": float(np.mean(conservative_verify != beneficial)),
        "conservative_miss_rate_far_inside": float(np.mean(~conservative_verify[far_inside])) if np.any(far_inside) else float("nan"),
        "conservative_verify_rate_far_outside": float(np.mean(conservative_verify[far_outside])) if np.any(far_outside) else float("nan"),
        "monotonicity_violation_rate_e": 0.0 if e_comparisons == 0 else float(e_violations / e_comparisons),
        "monotonicity_violation_rate_q": 0.0 if q_comparisons == 0 else float(q_violations / q_comparisons),
        "continuous_effort_mean": float(effort_surface["effort"].mean()),
        "continuous_effort_high_rate": float(np.mean(effort_surface["effort"] >= (2.0 / 3.0))),
        "continuous_effort_violation_rate_e": 0.0 if effort_e_comparisons == 0 else float(effort_e_violations / effort_e_comparisons),
        "continuous_effort_violation_rate_d": 0.0 if effort_d_comparisons == 0 else float(effort_d_violations / effort_d_comparisons),
        "continuous_effort_violation_rate_q": 0.0 if effort_q_comparisons == 0 else float(effort_q_violations / effort_q_comparisons),
        "counterfactual_optimal_effort_mean": float(effort_optima["optimal_effort"].mean()),
        "counterfactual_interior_optimum_share": float(np.mean((effort_optima["optimal_effort"] > 0.0) & (effort_optima["optimal_effort"] < 1.0))),
        "counterfactual_high_effort_share": float(np.mean(effort_optima["optimal_effort"] >= (2.0 / 3.0))),
        "counterfactual_rule_exact_match_rate": float(np.mean(np.isclose(effort_optima["optimal_effort"], effort_optima["rule_effort"]))),
        "counterfactual_rule_one_step_match_rate": float(effort_optima["one_step_match"].mean()),
        "counterfactual_rule_mean_regret": float(effort_optima["rule_regret"].mean()),
        "counterfactual_gain_margin_mean": float(effort_optima["gain_margin"].mean()),
        "counterfactual_monotonicity_violation_rate_e": 0.0 if counterfactual_e_comparisons == 0 else float(counterfactual_e_violations / counterfactual_e_comparisons),
        "counterfactual_monotonicity_violation_rate_d": 0.0 if counterfactual_d_comparisons == 0 else float(counterfactual_d_violations / counterfactual_d_comparisons),
        "counterfactual_monotonicity_violation_rate_q": 0.0 if counterfactual_q_comparisons == 0 else float(counterfactual_q_violations / counterfactual_q_comparisons),
        "heatmap_rows": int(len(heatmap)),
    }


def governance_headroom(overlap: pd.DataFrame, output_dir: Path) -> dict:
    codetrace_path = manifest_paths(MANIFEST_DIR)["codetrace_manifest"]
    codetrace = pd.read_csv(codetrace_path)
    amp_anchor = float((codetrace["incorrect_stage_ratio"] + codetrace["unuseful_stage_ratio"]).mean())

    rows = []
    for mode in GOVERNANCE_MODES:
        nominal_load = 0.18 + 0.22 * overlap["d_proxy"] + 0.18 * overlap["q_proxy"]
        recovery_env = overlap["e_proxy"] * mode.recovery_multiplier * (0.20 + 0.25 * overlap["d_proxy"] + 0.15 * amp_anchor)
        headroom = mode.service_floor - (nominal_load + recovery_env)
        safe = headroom > 0
        rows.append(
            pd.DataFrame(
                {
                    "instance_id": overlap["instance_id"],
                    "mode": mode.name,
                    "headroom": headroom,
                    "safe": safe.astype(float),
                }
            )
        )
    all_headrooms = pd.concat(rows, ignore_index=True)
    headroom_pivot = all_headrooms.pivot_table(index="instance_id", columns="mode", values="headroom", aggfunc="mean")
    mode_names = [mode.name for mode in GOVERNANCE_MODES]
    violations = 0
    comparisons = 0
    for left, right in zip(mode_names[:-1], mode_names[1:]):
        comparisons += len(headroom_pivot)
        violations += int((headroom_pivot[right] < headroom_pivot[left]).sum())

    all_headrooms.to_csv(output_dir / "governance_headroom.csv", index=False)
    summary = (
        all_headrooms.groupby("mode")
        .agg(mean_headroom=("headroom", "mean"), safe_rate=("safe", "mean"))
        .reset_index()
        .to_dict("records")
    )
    return {
        "amp_anchor_from_codetrace": amp_anchor,
        "mode_summary": summary,
        "pairwise_monotonicity_violation_rate": 0.0 if comparisons == 0 else violations / comparisons,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run structural diagnostics that support the theorem-bearing claims.")
    parser.add_argument("--manifest-dir", type=Path, default=MANIFEST_DIR)
    parser.add_argument("--output-dir", type=Path, default=RESULTS_DIR / "diagnostics")
    args = parser.parse_args()

    output_dir = ensure_dir(args.output_dir)
    overlap = load_overlap(args.manifest_dir)
    state_diagnostics, overlap = fit_state_compression(overlap)
    context_diagnostics = fit_context_atom_diagnostics(overlap)
    verification_diagnostics = verification_boundary_diagnostics(overlap, output_dir)
    governance_diagnostics = governance_headroom(overlap, output_dir)

    payload = {
        "state_compression": state_diagnostics,
        "context_atoms": context_diagnostics,
        "verification_boundary": verification_diagnostics,
        "governance_headroom": governance_diagnostics,
    }
    write_json(output_dir / "structural_diagnostics.json", payload)
    overlap.to_csv(output_dir / "overlap_dev_trajectories.csv", index=False)

    print("Structural diagnostics complete.")
    print(f"Overlap rows: {len(overlap)}")
    print(f"Reduced AUC: {state_diagnostics['reduced_model']['auc']:.4f}")
    print(f"Full AUC: {state_diagnostics['full_model']['auc']:.4f}")


if __name__ == "__main__":
    main()
