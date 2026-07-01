# Learned Runtime Gate Analysis

This analysis evaluates a learned pre-routing gate with leave-one-task-out cross-fitting. Each held-out task is routed using a score and threshold learned from the other tasks only. The diagnostic risk tier is not used as a feature.

## Inputs

- `paper/ReplicationPackage/exp/results/emse_runtime/llamaserver_qwen3_4b_nothink_30_v1/runtime_task_results.csv`

## Learned Gate Routing

- Tasks: 30
- Full-beneficial tasks in observed paired branches: 1
- Full-beneficial tasks routed to full context: 0
- Route counts: `{"learned_minimal_context": 30}`
- Training calibration margin used for threshold selection: 0.000
- Evaluation non-inferiority margin: 0.100
- Learner: `feature_score`

## Controller Summary

| controller | n | success_rate | mean_calls | mean_total_tokens | mean_latency_s |
| --- | --- | --- | --- | --- | --- |
| context_gate_high_only | 30 | 0.8333 | 1.8667 | 578.6000 | 4.5294 |
| context_gate_medium_high | 30 | 0.8000 | 2.4000 | 759.3667 | 5.6664 |
| direct_low | 30 | 0.8333 | 1.0000 | 275.3667 | 2.9559 |
| learned_gate_loto | 30 | 0.8333 | 1.0000 | 275.3667 | 2.9559 |
| standard_full | 30 | 0.8333 | 3.0000 | 960.1000 | 6.8047 |

## Learned Gate vs Full Context

| target | reference | metric | direction | n_pairs | target_mean | reference_mean | mean_diff_target_minus_reference | ci_low | ci_high | both_success | target_only_success | reference_only_success | both_fail | noninferiority_margin | noninferior_by_ci | informative_success_evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| learned_gate_loto | standard_full | success | higher | 30 | 0.8333 | 0.8333 | 0.0000 | -0.1000 | 0.1000 | 24.0000 | 1.0000 | 1.0000 | 4.0000 | 0.1000 | False | True |
| learned_gate_loto | standard_full | model_calls | lower | 30 | 1.0000 | 3.0000 | -2.0000 | -2.0000 | -2.0000 |  |  |  |  |  |  |  |
| learned_gate_loto | standard_full | total_tokens | lower | 30 | 275.3667 | 960.1000 | -684.7333 | -719.5017 | -650.5250 |  |  |  |  |  |  |  |
| learned_gate_loto | standard_full | latency_seconds | lower | 30 | 2.9559 | 6.8047 | -3.8488 | -4.5092 | -3.1038 |  |  |  |  |  |  |  |
| learned_gate_loto | standard_full | total_observed_work | lower | 30 | 2.0000 | 6.0000 | -4.0000 | -4.0000 | -4.0000 |  |  |  |  |  |  |  |

## Learned Gate vs Low Context

| target | reference | metric | direction | n_pairs | target_mean | reference_mean | mean_diff_target_minus_reference | ci_low | ci_high | both_success | target_only_success | reference_only_success | both_fail | noninferiority_margin | noninferior_by_ci | informative_success_evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| learned_gate_loto | direct_low | success | higher | 30 | 0.8333 | 0.8333 | 0.0000 | 0.0000 | 0.0000 | 25.0000 | 0.0000 | 0.0000 | 5.0000 | 0.1000 | True | True |
| learned_gate_loto | direct_low | model_calls | lower | 30 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 |  |  |  |  |  |  |  |
| learned_gate_loto | direct_low | total_tokens | lower | 30 | 275.3667 | 275.3667 | 0.0000 | 0.0000 | 0.0000 |  |  |  |  |  |  |  |
| learned_gate_loto | direct_low | latency_seconds | lower | 30 | 2.9559 | 2.9559 | 0.0000 | 0.0000 | 0.0000 |  |  |  |  |  |  |  |
| learned_gate_loto | direct_low | total_observed_work | lower | 30 | 2.0000 | 2.0000 | 0.0000 | 0.0000 | 0.0000 |  |  |  |  |  |  |  |

## Interpretation Guardrails

- The learned gate uses pre-routing issue, buggy-code, and candidate-code features only.
- The held-out route for each task is produced by leave-one-task-out cross-fitting.
- This remains a controlled static-candidate code repair setting, not open-ended repository deployment.
