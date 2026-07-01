# AIDev Resolution-Time Survival Diagnostic

Observation cutoff: `2025-07-30T23:20:55+00:00`.

This diagnostic treats open PRs as right-censored rather than dropping them from resolution-time analysis. It uses Kaplan-Meier survival estimates and restricted mean time unresolved (RMST). The accepted and routed groups are observational gate outputs, not randomized counterfactuals.

## Gate-Group Summary

| split | gate_group | rows | closed_events | censored_open | observed_closure_rate | km_median_days | unresolved_probability_7d | unresolved_probability_30d | unresolved_probability_90d | rmst_30d_days |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| repository_disjoint | all | 3482 | 3131 | 351 | 0.899 | 0.090 | 0.203 | 0.114 | 0.054 | 5.134 |
| repository_disjoint | accepted | 1089 | 1033 | 56 | 0.949 | 0.003 | 0.077 | 0.046 | 0.027 | 2.211 |
| repository_disjoint | routed | 2393 | 2098 | 295 | 0.877 | 0.374 | 0.261 | 0.145 | 0.070 | 6.469 |
| temporal | all | 6720 | 6057 | 663 | 0.901 | 0.001 | 0.091 | 0.066 | 0.066 | 2.548 |
| temporal | accepted | 5657 | 5284 | 373 | 0.934 | 0.000 | 0.059 | 0.045 | 0.045 | 1.720 |
| temporal | routed | 1063 | 773 | 290 | 0.727 | 0.806 | 0.260 | 0.182 | 0.182 | 7.026 |

## Accepted-vs-Routed Cluster Bootstrap Contrasts

| split | metric | point | ci_low | ci_high | bootstrap_unit | bootstrap_rounds | bootstrap_valid_rounds |
| --- | --- | --- | --- | --- | --- | --- | --- |
| repository_disjoint | Observed closure rate, accepted minus routed | 0.072 | 0.038 | 0.111 | repo | 500 | 500 |
| repository_disjoint | 30-day unresolved probability, accepted minus routed | -0.098 | -0.155 | -0.052 | repo | 500 | 500 |
| repository_disjoint | 30-day RMST unresolved, accepted minus routed | -4.258 | -6.156 | -2.856 | repo | 500 | 500 |
| temporal | Observed closure rate, accepted minus routed | 0.207 | 0.091 | 0.252 | repo | 500 | 500 |
| temporal | 30-day unresolved probability, accepted minus routed | -0.137 | -0.191 | -0.011 | repo | 500 | 500 |
| temporal | 30-day RMST unresolved, accepted minus routed | -5.306 | -6.788 | -1.962 | repo | 500 | 500 |

## Figure

- `ExtraExperiment/results/pull_request_workload_gate/figures/aidev_resolution_survival.svg`

## Claim Boundary

- Allowed: report whether accepted and routed PRs differ in censored time-to-closure diagnostics.
- Forbidden: claim that gate acceptance causally shortens or lengthens resolution time.
