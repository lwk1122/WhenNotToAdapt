# Runtime Pair Analysis

Source: `exp/results/emse_runtime/lmstudio_executable_context_gate_repeat_v1/runtime_task_results.csv`

## Non-inferiority Summary

- Target controller: `context_gate_medium_high`
- Reference controller: `standard_full`
- Paired tasks: 30
- Pre-specified solve-rate margin: 0.100
- Minimum paired tasks for publication-grade success claim: 30
- Success mean difference: 0.000
- Success bootstrap CI: [0.000, 0.000]
- Non-inferior by paired CI rule: True
- Success evidence informative: True
- Publication-ready success claim: True

## Resource Summary

- Total observed work mean difference: -1.200
- Total observed work bootstrap CI: [-1.867, -0.533]

## Metric Table

| target | reference | metric | direction | n_pairs | target_mean | reference_mean | mean_diff_target_minus_reference | ci_low | ci_high | both_success | target_only_success | reference_only_success | both_fail | noninferiority_margin | noninferior_by_ci | informative_success_evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| context_gate_medium_high | standard_full | success | higher | 30 | 0.9667 | 0.9667 | 0.0000 | 0.0000 | 0.0000 | 29.0000 | 0.0000 | 0.0000 | 1.0000 | 0.1000 | True | True |
| context_gate_medium_high | standard_full | final_target_test_pass | higher | 30 | 0.9667 | 0.9667 | 0.0000 | 0.0000 | 0.0000 | 29.0000 | 0.0000 | 0.0000 | 1.0000 | 0.1000 | True | True |
| context_gate_medium_high | standard_full | catastrophic_failure | lower | 30 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |  |  |  |  |  |  |  |
| context_gate_medium_high | standard_full | test_runs | lower | 30 | 0.7000 | 1.0000 | -0.3000 | -0.4667 | -0.1333 |  |  |  |  |  |  |  |
| context_gate_medium_high | standard_full | verification_events | lower | 30 | 0.7000 | 1.0000 | -0.3000 | -0.4667 | -0.1333 |  |  |  |  |  |  |  |
| context_gate_medium_high | standard_full | search_count | lower | 30 | 0.7000 | 1.0000 | -0.3000 | -0.4667 | -0.1333 |  |  |  |  |  |  |  |
| context_gate_medium_high | standard_full | read_count | lower | 30 | 2.4000 | 3.0000 | -0.6000 | -0.9333 | -0.2667 |  |  |  |  |  |  |  |
| context_gate_medium_high | standard_full | patch_attempts | lower | 30 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 |  |  |  |  |  |  |  |
| context_gate_medium_high | standard_full | patch_apply_successes | higher | 30 | 0.9667 | 0.9667 | 0.0000 | 0.0000 | 0.0000 |  |  |  |  |  |  |  |
| context_gate_medium_high | standard_full | fallback_events | lower | 30 | 0.7000 | 0.0000 | 0.7000 | 0.5333 | 0.8667 |  |  |  |  |  |  |  |
| context_gate_medium_high | standard_full | post_error_extra_work | lower | 30 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |  |  |  |  |  |  |  |
| context_gate_medium_high | standard_full | best_problem_reduction | higher | 30 | 0.9667 | 0.9667 | 0.0000 | 0.0000 | 0.0000 |  |  |  |  |  |  |  |
| context_gate_medium_high | standard_full | final_problem_reduction | higher | 30 | 0.9667 | 0.9667 | 0.0000 | 0.0000 | 0.0000 |  |  |  |  |  |  |  |
| context_gate_medium_high | standard_full | model_calls | lower | 30 | 2.4000 | 3.0000 | -0.6000 | -0.9333 | -0.2667 |  |  |  |  |  |  |  |
| context_gate_medium_high | standard_full | prompt_tokens | lower | 30 | 751.1667 | 969.4000 | -218.2333 | -338.6533 | -104.4942 |  |  |  |  |  |  |  |
| context_gate_medium_high | standard_full | completion_tokens | lower | 30 | 316.4000 | 395.0000 | -78.6000 | -123.0150 | -36.1325 |  |  |  |  |  |  |  |
| context_gate_medium_high | standard_full | total_tokens | lower | 30 | 1067.5667 | 1364.4000 | -296.8333 | -478.5008 | -140.7617 |  |  |  |  |  |  |  |
| context_gate_medium_high | standard_full | latency_seconds | lower | 30 | 14.5359 | 17.9066 | -3.3708 | -5.5292 | -1.5001 |  |  |  |  |  |  |  |
| context_gate_medium_high | standard_full | tool_calls | lower | 30 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |  |  |  |  |  |  |  |
| context_gate_medium_high | standard_full | context_files | lower | 30 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 |  |  |  |  |  |  |  |
| context_gate_medium_high | standard_full | context_bytes | lower | 30 | 584.3333 | 615.4333 | -31.1000 | -49.0042 | -14.7325 |  |  |  |  |  |  |  |
| context_gate_medium_high | standard_full | files_changed | lower | 30 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 |  |  |  |  |  |  |  |
| context_gate_medium_high | standard_full | lines_changed | lower | 30 | 2.9667 | 2.9667 | 0.0000 | 0.0000 | 0.0000 |  |  |  |  |  |  |  |
| context_gate_medium_high | standard_full | failed_verification_jobs | lower | 30 | 0.0333 | 0.0333 | 0.0000 | 0.0000 | 0.0000 |  |  |  |  |  |  |  |
| context_gate_medium_high | standard_full | recovery_attempts | lower | 30 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |  |  |  |  |  |  |  |
| context_gate_medium_high | standard_full | total_observed_work | lower | 30 | 4.8000 | 6.0000 | -1.2000 | -1.8667 | -0.5333 |  |  |  |  |  |  |  |

## Interpretation Guardrails

- This script fixes the analysis contract for future controlled runs.
- The existing 8-task pilot is a shape check, not publication-grade evidence.
- A CI rule can be mechanically satisfied when both controllers solve nothing; publication-ready success claims require informative success evidence and the pre-specified minimum paired task count.
- A formal EMSE claim requires a pre-specified task set, paired controller runs, and enough power for the chosen solve-rate margin.
