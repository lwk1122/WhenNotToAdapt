# Executable Context-Gate Repeat Analysis

This analysis treats each `replicate x task` pair as the paired unit. It is a small repeatability check over the same controlled task set, not a new independent benchmark.

## Source Runs

- `exp/results/emse_runtime/lmstudio_executable_context_gate_v1`
- `exp/results/emse_runtime/lmstudio_executable_context_gate_repeat_v1`

## Controller Summary

| controller | n | success_rate | mean_calls | mean_total_tokens | mean_latency_s |
| --- | --- | --- | --- | --- | --- |
| context_gate_high_only | 60 | 0.9000 | 1.8667 | 802.6667 | 13.8539 |
| context_gate_medium_high | 60 | 0.9667 | 2.4000 | 1067.5667 | 17.5096 |
| direct_low | 60 | 0.8333 | 1.0000 | 330.5000 | 6.5105 |
| standard_full | 60 | 0.9667 | 3.0000 | 1364.4000 | 21.6253 |

## Medium/High Gate vs Full Context

| target | reference | metric | direction | n_pairs | target_mean | reference_mean | mean_diff_target_minus_reference | ci_low | ci_high | both_success | target_only_success | reference_only_success | both_fail | noninferiority_margin | noninferior_by_ci | informative_success_evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| context_gate_medium_high | standard_full | success | higher | 60 | 0.9667 | 0.9667 | 0.0000 | 0.0000 | 0.0000 | 58.0000 | 0.0000 | 0.0000 | 2.0000 | 0.1000 | True | True |
| context_gate_medium_high | standard_full | model_calls | lower | 60 | 2.4000 | 3.0000 | -0.6000 | -0.8333 | -0.3667 |  |  |  |  |  |  |  |
| context_gate_medium_high | standard_full | total_tokens | lower | 60 | 1067.5667 | 1364.4000 | -296.8333 | -418.9654 | -184.5096 |  |  |  |  |  |  |  |
| context_gate_medium_high | standard_full | latency_seconds | lower | 60 | 17.5096 | 21.6253 | -4.1156 | -5.9073 | -2.5537 |  |  |  |  |  |  |  |
| context_gate_medium_high | standard_full | total_observed_work | lower | 60 | 4.8000 | 6.0000 | -1.2000 | -1.6667 | -0.7333 |  |  |  |  |  |  |  |

## Medium/High Gate vs Low Context

| target | reference | metric | direction | n_pairs | target_mean | reference_mean | mean_diff_target_minus_reference | ci_low | ci_high | both_success | target_only_success | reference_only_success | both_fail | noninferiority_margin | noninferior_by_ci | informative_success_evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| context_gate_medium_high | direct_low | success | higher | 60 | 0.9667 | 0.8333 | 0.1333 | 0.0500 | 0.2167 | 50.0000 | 8.0000 | 0.0000 | 2.0000 | 0.1000 | True | True |
| context_gate_medium_high | direct_low | model_calls | lower | 60 | 2.4000 | 1.0000 | 1.4000 | 1.1667 | 1.6333 |  |  |  |  |  |  |  |
| context_gate_medium_high | direct_low | total_tokens | lower | 60 | 1067.5667 | 330.5000 | 737.0667 | 605.8958 | 861.3400 |  |  |  |  |  |  |  |
| context_gate_medium_high | direct_low | latency_seconds | lower | 60 | 17.5096 | 6.5105 | 10.9991 | 8.7989 | 13.4658 |  |  |  |  |  |  |  |
| context_gate_medium_high | direct_low | total_observed_work | lower | 60 | 4.8000 | 2.0000 | 2.8000 | 2.3333 | 3.2667 |  |  |  |  |  |  |  |

## High-Only Gate vs Full Context

| target | reference | metric | direction | n_pairs | target_mean | reference_mean | mean_diff_target_minus_reference | ci_low | ci_high | both_success | target_only_success | reference_only_success | both_fail | noninferiority_margin | noninferior_by_ci | informative_success_evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| context_gate_high_only | standard_full | success | higher | 60 | 0.9000 | 0.9667 | -0.0667 | -0.1333 | -0.0167 | 54.0000 | 0.0000 | 4.0000 | 2.0000 | 0.1000 | False | True |
| context_gate_high_only | standard_full | model_calls | lower | 60 | 1.8667 | 3.0000 | -1.1333 | -1.3667 | -0.8667 |  |  |  |  |  |  |  |
| context_gate_high_only | standard_full | total_tokens | lower | 60 | 802.6667 | 1364.4000 | -561.7333 | -685.1979 | -432.4646 |  |  |  |  |  |  |  |
| context_gate_high_only | standard_full | latency_seconds | lower | 60 | 13.8539 | 21.6253 | -7.7713 | -9.6593 | -5.9511 |  |  |  |  |  |  |  |
| context_gate_high_only | standard_full | total_observed_work | lower | 60 | 3.7333 | 6.0000 | -2.2667 | -2.7333 | -1.8000 |  |  |  |  |  |  |  |
