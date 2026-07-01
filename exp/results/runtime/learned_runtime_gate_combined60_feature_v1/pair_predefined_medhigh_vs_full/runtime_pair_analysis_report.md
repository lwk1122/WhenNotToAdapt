# Runtime Pair Analysis

Source: `exp/results/emse_runtime/learned_runtime_gate_combined60_feature_v1/learned_runtime_task_results.csv`

## Non-inferiority Summary

- Target controller: `context_gate_medium_high`
- Reference controller: `standard_full`
- Paired tasks: 60
- Pre-specified solve-rate margin: 0.100
- Minimum paired tasks for publication-grade success claim: 30
- Success mean difference: 0.000
- Success bootstrap CI: [0.000, 0.000]
- Non-inferior by paired CI rule: True
- Success evidence informative: True
- Publication-ready success claim: True

## Resource Summary

- Total observed work mean difference: -1.200
- Total observed work bootstrap CI: [-1.667, -0.733]

## Metric Table

| target | reference | metric | direction | n_pairs | target_mean | reference_mean | mean_diff_target_minus_reference | ci_low | ci_high | both_success | target_only_success | reference_only_success | both_fail | noninferiority_margin | noninferior_by_ci | informative_success_evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| context_gate_medium_high | standard_full | success | higher | 60 | 0.9833 | 0.9833 | 0.0000 | 0.0000 | 0.0000 | 59.0000 | 0.0000 | 0.0000 | 1.0000 | 0.1000 | True | True |
| context_gate_medium_high | standard_full | final_target_test_pass | higher | 60 | 0.9833 | 0.9833 | 0.0000 | 0.0000 | 0.0000 | 59.0000 | 0.0000 | 0.0000 | 1.0000 | 0.1000 | True | True |
| context_gate_medium_high | standard_full | catastrophic_failure | lower | 60 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |  |  |  |  |  |  |  |
| context_gate_medium_high | standard_full | test_runs | lower | 60 | 0.7000 | 1.0000 | -0.3000 | -0.4167 | -0.1833 |  |  |  |  |  |  |  |
| context_gate_medium_high | standard_full | verification_events | lower | 60 | 0.7000 | 1.0000 | -0.3000 | -0.4167 | -0.1833 |  |  |  |  |  |  |  |
| context_gate_medium_high | standard_full | search_count | lower | 60 | 0.7000 | 1.0000 | -0.3000 | -0.4167 | -0.2000 |  |  |  |  |  |  |  |
| context_gate_medium_high | standard_full | read_count | lower | 60 | 2.4000 | 3.0000 | -0.6000 | -0.8333 | -0.4000 |  |  |  |  |  |  |  |
| context_gate_medium_high | standard_full | patch_attempts | lower | 60 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 |  |  |  |  |  |  |  |
| context_gate_medium_high | standard_full | patch_apply_successes | higher | 60 | 0.9833 | 0.9833 | 0.0000 | 0.0000 | 0.0000 |  |  |  |  |  |  |  |
| context_gate_medium_high | standard_full | fallback_events | lower | 60 | 0.7000 | 0.0000 | 0.7000 | 0.5833 | 0.8167 |  |  |  |  |  |  |  |
| context_gate_medium_high | standard_full | post_error_extra_work | lower | 60 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |  |  |  |  |  |  |  |
| context_gate_medium_high | standard_full | best_problem_reduction | higher | 60 | 0.9833 | 0.9833 | 0.0000 | 0.0000 | 0.0000 |  |  |  |  |  |  |  |
| context_gate_medium_high | standard_full | final_problem_reduction | higher | 60 | 0.9833 | 0.9833 | 0.0000 | 0.0000 | 0.0000 |  |  |  |  |  |  |  |
| context_gate_medium_high | standard_full | model_calls | lower | 60 | 2.4000 | 3.0000 | -0.6000 | -0.8333 | -0.3667 |  |  |  |  |  |  |  |
| context_gate_medium_high | standard_full | prompt_tokens | lower | 60 | 743.9167 | 947.7667 | -203.8500 | -283.5917 | -125.9929 |  |  |  |  |  |  |  |
| context_gate_medium_high | standard_full | completion_tokens | lower | 60 | 310.0833 | 383.8000 | -73.7167 | -103.4338 | -44.8488 |  |  |  |  |  |  |  |
| context_gate_medium_high | standard_full | total_tokens | lower | 60 | 1054.0000 | 1331.5667 | -277.5667 | -390.6654 | -168.9817 |  |  |  |  |  |  |  |
| context_gate_medium_high | standard_full | latency_seconds | lower | 60 | 19.9158 | 24.4005 | -4.4847 | -6.3566 | -2.7414 |  |  |  |  |  |  |  |
| context_gate_medium_high | standard_full | tool_calls | lower | 60 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |  |  |  |  |  |  |  |
| context_gate_medium_high | standard_full | context_files | lower | 60 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 |  |  |  |  |  |  |  |
| context_gate_medium_high | standard_full | context_bytes | lower | 60 | 564.2833 | 591.3333 | -27.0500 | -38.7000 | -16.5663 |  |  |  |  |  |  |  |
| context_gate_medium_high | standard_full | files_changed | lower | 60 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 |  |  |  |  |  |  |  |
| context_gate_medium_high | standard_full | lines_changed | lower | 60 | 3.0500 | 3.0500 | 0.0000 | 0.0000 | 0.0000 |  |  |  |  |  |  |  |
| context_gate_medium_high | standard_full | failed_verification_jobs | lower | 60 | 0.0167 | 0.0167 | 0.0000 | 0.0000 | 0.0000 |  |  |  |  |  |  |  |
| context_gate_medium_high | standard_full | recovery_attempts | lower | 60 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |  |  |  |  |  |  |  |
| context_gate_medium_high | standard_full | total_observed_work | lower | 60 | 4.8000 | 6.0000 | -1.2000 | -1.6667 | -0.7333 |  |  |  |  |  |  |  |

## Interpretation Guardrails

- This script fixes the analysis contract for future controlled runs.
- The existing 8-task pilot is a shape check, not publication-grade evidence.
- A CI rule can be mechanically satisfied when both controllers solve nothing; publication-ready success claims require informative success evidence and the pre-specified minimum paired task count.
- A formal EMSE claim requires a pre-specified task set, paired controller runs, and enough power for the chosen solve-rate margin.
