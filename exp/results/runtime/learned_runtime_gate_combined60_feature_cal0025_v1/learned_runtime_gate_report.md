# Learned Runtime Gate Analysis

This analysis evaluates a learned pre-routing gate with leave-one-task-out cross-fitting. Each held-out task is routed using a score and threshold learned from the other tasks only. The diagnostic risk tier is not used as a feature.

## Inputs

- `exp/results/emse_runtime/lmstudio_executable_context_gate_v1/runtime_task_results.csv`
- `exp/results/emse_runtime/lmstudio_executable_context_gate_extra_v1/runtime_task_results.csv`

## Learned Gate Routing

- Tasks: 60
- Full-beneficial tasks in observed paired branches: 5
- Full-beneficial tasks routed to full context: 3
- Route counts: `{"learned_full_context": 19, "learned_minimal_context": 41}`
- Training calibration margin used for threshold selection: 0.025
- Evaluation non-inferiority margin: 0.100
- Learner: `feature_score`

## Controller Summary

| controller | n | success_rate | mean_calls | mean_total_tokens | mean_latency_s |
| --- | --- | --- | --- | --- | --- |
| context_gate_high_only | 60 | 0.9500 | 1.8333 | 764.7167 | 15.0042 |
| context_gate_medium_high | 60 | 0.9833 | 2.4000 | 1054.0000 | 19.9158 |
| direct_low | 60 | 0.9000 | 1.0000 | 319.1833 | 7.1955 |
| learned_gate_loto | 60 | 0.9500 | 1.6333 | 668.6333 | 13.4356 |
| standard_full | 60 | 0.9833 | 3.0000 | 1331.5667 | 24.4005 |

## Learned Gate vs Full Context

| target | reference | metric | direction | n_pairs | target_mean | reference_mean | mean_diff_target_minus_reference | ci_low | ci_high | both_success | target_only_success | reference_only_success | both_fail | noninferiority_margin | noninferior_by_ci | informative_success_evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| learned_gate_loto | standard_full | success | higher | 60 | 0.9500 | 0.9833 | -0.0333 | -0.0833 | 0.0000 | 57.0000 | 0.0000 | 2.0000 | 1.0000 | 0.1000 | True | True |
| learned_gate_loto | standard_full | model_calls | lower | 60 | 1.6333 | 3.0000 | -1.3667 | -1.6000 | -1.1333 |  |  |  |  |  |  |  |
| learned_gate_loto | standard_full | total_tokens | lower | 60 | 668.6333 | 1331.5667 | -662.9333 | -780.5508 | -542.5146 |  |  |  |  |  |  |  |
| learned_gate_loto | standard_full | latency_seconds | lower | 60 | 13.4356 | 24.4005 | -10.9650 | -13.1048 | -9.0249 |  |  |  |  |  |  |  |
| learned_gate_loto | standard_full | total_observed_work | lower | 60 | 3.2667 | 6.0000 | -2.7333 | -3.2000 | -2.2000 |  |  |  |  |  |  |  |

## Learned Gate vs Low Context

| target | reference | metric | direction | n_pairs | target_mean | reference_mean | mean_diff_target_minus_reference | ci_low | ci_high | both_success | target_only_success | reference_only_success | both_fail | noninferiority_margin | noninferior_by_ci | informative_success_evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| learned_gate_loto | direct_low | success | higher | 60 | 0.9500 | 0.9000 | 0.0500 | 0.0000 | 0.1167 | 54.0000 | 3.0000 | 0.0000 | 3.0000 | 0.1000 | True | True |
| learned_gate_loto | direct_low | model_calls | lower | 60 | 1.6333 | 1.0000 | 0.6333 | 0.4000 | 0.8667 |  |  |  |  |  |  |  |
| learned_gate_loto | direct_low | total_tokens | lower | 60 | 668.6333 | 319.1833 | 349.4500 | 223.1654 | 487.4717 |  |  |  |  |  |  |  |
| learned_gate_loto | direct_low | latency_seconds | lower | 60 | 13.4356 | 7.1955 | 6.2401 | 3.8897 | 8.7445 |  |  |  |  |  |  |  |
| learned_gate_loto | direct_low | total_observed_work | lower | 60 | 3.2667 | 2.0000 | 1.2667 | 0.8000 | 1.7333 |  |  |  |  |  |  |  |

## Interpretation Guardrails

- The learned gate uses pre-routing issue, buggy-code, and candidate-code features only.
- The held-out route for each task is produced by leave-one-task-out cross-fitting.
- This remains a controlled static-candidate code repair setting, not open-ended repository deployment.
