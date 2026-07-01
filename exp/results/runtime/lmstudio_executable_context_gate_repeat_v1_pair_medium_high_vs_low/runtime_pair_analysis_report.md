# Runtime Pair Analysis

Source: `exp/results/emse_runtime/lmstudio_executable_context_gate_repeat_v1/runtime_task_results.csv`

## Non-inferiority Summary

- Target controller: `context_gate_medium_high`
- Reference controller: `direct_low`
- Paired tasks: 30
- Pre-specified solve-rate margin: 0.100
- Minimum paired tasks for publication-grade success claim: 30
- Success mean difference: 0.133
- Success bootstrap CI: [0.033, 0.267]
- Non-inferior by paired CI rule: True
- Success evidence informative: True
- Publication-ready success claim: True

## Resource Summary

- Total observed work mean difference: 2.800
- Total observed work bootstrap CI: [2.133, 3.467]

## Metric Table

| target | reference | metric | direction | n_pairs | target_mean | reference_mean | mean_diff_target_minus_reference | ci_low | ci_high | both_success | target_only_success | reference_only_success | both_fail | noninferiority_margin | noninferior_by_ci | informative_success_evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| context_gate_medium_high | direct_low | success | higher | 30 | 0.9667 | 0.8333 | 0.1333 | 0.0333 | 0.2667 | 25.0000 | 4.0000 | 0.0000 | 1.0000 | 0.1000 | True | True |
| context_gate_medium_high | direct_low | final_target_test_pass | higher | 30 | 0.9667 | 0.8333 | 0.1333 | 0.0333 | 0.2667 | 25.0000 | 4.0000 | 0.0000 | 1.0000 | 0.1000 | True | True |
| context_gate_medium_high | direct_low | catastrophic_failure | lower | 30 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |  |  |  |  |  |  |  |
| context_gate_medium_high | direct_low | test_runs | lower | 30 | 0.7000 | 0.0000 | 0.7000 | 0.5333 | 0.8667 |  |  |  |  |  |  |  |
| context_gate_medium_high | direct_low | verification_events | lower | 30 | 0.7000 | 0.0000 | 0.7000 | 0.5333 | 0.8667 |  |  |  |  |  |  |  |
| context_gate_medium_high | direct_low | search_count | lower | 30 | 0.7000 | 0.0000 | 0.7000 | 0.5333 | 0.8667 |  |  |  |  |  |  |  |
| context_gate_medium_high | direct_low | read_count | lower | 30 | 2.4000 | 1.0000 | 1.4000 | 1.0667 | 1.7333 |  |  |  |  |  |  |  |
| context_gate_medium_high | direct_low | patch_attempts | lower | 30 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 |  |  |  |  |  |  |  |
| context_gate_medium_high | direct_low | patch_apply_successes | higher | 30 | 0.9667 | 0.8333 | 0.1333 | 0.0333 | 0.2667 |  |  |  |  |  |  |  |
| context_gate_medium_high | direct_low | fallback_events | lower | 30 | 0.7000 | 0.0000 | 0.7000 | 0.5333 | 0.8667 |  |  |  |  |  |  |  |
| context_gate_medium_high | direct_low | post_error_extra_work | lower | 30 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |  |  |  |  |  |  |  |
| context_gate_medium_high | direct_low | best_problem_reduction | higher | 30 | 0.9667 | 0.8333 | 0.1333 | 0.0333 | 0.2667 |  |  |  |  |  |  |  |
| context_gate_medium_high | direct_low | final_problem_reduction | higher | 30 | 0.9667 | 0.8333 | 0.1333 | 0.0333 | 0.2667 |  |  |  |  |  |  |  |
| context_gate_medium_high | direct_low | model_calls | lower | 30 | 2.4000 | 1.0000 | 1.4000 | 1.0667 | 1.7333 |  |  |  |  |  |  |  |
| context_gate_medium_high | direct_low | prompt_tokens | lower | 30 | 751.1667 | 205.3333 | 545.8333 | 411.6850 | 667.4442 |  |  |  |  |  |  |  |
| context_gate_medium_high | direct_low | completion_tokens | lower | 30 | 316.4000 | 125.1667 | 191.2333 | 132.1992 | 256.6125 |  |  |  |  |  |  |  |
| context_gate_medium_high | direct_low | total_tokens | lower | 30 | 1067.5667 | 330.5000 | 737.0667 | 548.1267 | 918.5883 |  |  |  |  |  |  |  |
| context_gate_medium_high | direct_low | latency_seconds | lower | 30 | 14.5359 | 5.5556 | 8.9802 | 6.4568 | 11.4424 |  |  |  |  |  |  |  |
| context_gate_medium_high | direct_low | tool_calls | lower | 30 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |  |  |  |  |  |  |  |
| context_gate_medium_high | direct_low | context_files | lower | 30 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 |  |  |  |  |  |  |  |
| context_gate_medium_high | direct_low | context_bytes | lower | 30 | 584.3333 | 500.2333 | 84.1000 | 60.7000 | 107.2683 |  |  |  |  |  |  |  |
| context_gate_medium_high | direct_low | files_changed | lower | 30 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 |  |  |  |  |  |  |  |
| context_gate_medium_high | direct_low | lines_changed | lower | 30 | 2.9667 | 3.0000 | -0.0333 | -0.1000 | 0.0000 |  |  |  |  |  |  |  |
| context_gate_medium_high | direct_low | failed_verification_jobs | lower | 30 | 0.0333 | 0.1667 | -0.1333 | -0.2667 | -0.0333 |  |  |  |  |  |  |  |
| context_gate_medium_high | direct_low | recovery_attempts | lower | 30 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |  |  |  |  |  |  |  |
| context_gate_medium_high | direct_low | total_observed_work | lower | 30 | 4.8000 | 2.0000 | 2.8000 | 2.1333 | 3.4667 |  |  |  |  |  |  |  |

## Interpretation Guardrails

- This script fixes the analysis contract for future controlled runs.
- The existing 8-task pilot is a shape check, not publication-grade evidence.
- A CI rule can be mechanically satisfied when both controllers solve nothing; publication-ready success claims require informative success evidence and the pre-specified minimum paired task count.
- A formal EMSE claim requires a pre-specified task set, paired controller runs, and enough power for the chosen solve-rate margin.
