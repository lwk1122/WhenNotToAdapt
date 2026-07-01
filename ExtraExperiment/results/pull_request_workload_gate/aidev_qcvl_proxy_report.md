# AIDev Q/C/V/L Proxy Diagnostic

This diagnostic uses the same defensible-feature gate, temporal and repository-disjoint splits, and 0.10 calibrated risk budget as the main AIDev experiment.
The quantities are empirical proxies for the theoretical primitives, not causal measurements of counterfactual workflow outcomes.

- Q proxy: merged pull request and closure within 30 days.
- C proxy: log-scaled first-observed patch churn, changed files, and test-like files.
- Xi proxy: downstream workload score used in the main gate.
- V proxy: unresolved after 30 days or at least one request-changes review.
- L proxy: training-standardized sum of C, Xi, V, and one minus merge rate.

## Gate Diagnostics

| split | train_rows | calibration_rows | test_rows | risk_budget | test_acceptance_rate | test_high_workload_rate | test_accepted_high_rate | source_predictions |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| temporal | 20157 | 6719 | 6720 | 0.100 | 0.842 | 0.142 | 0.074 | /Users/wenkai/Desktop/CAMC/ExtraExperiment/results/pull_request_workload_gate/aidev_subgroup_gate_predictions.csv |
| repository_disjoint | 25652 | 4462 | 3482 | 0.100 | 0.313 | 0.332 | 0.079 | /Users/wenkai/Desktop/CAMC/ExtraExperiment/results/pull_request_workload_gate/aidev_subgroup_gate_predictions.csv |

## Group Means

| split | group | n | coverage | Q merge | Q close 30d | C burden | Xi workload | V risk | L proxy |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Temporal | All test PRs | 6720 | 1.000 | 0.746 | 0.901 | 5.485 | 3.268 | 0.114 | 0.323 |
| Temporal | Standard path | 5657 | 0.842 | 0.798 | 0.934 | 6.068 | 1.693 | 0.074 | 0.167 |
| Temporal | Routed | 1063 | 0.158 | 0.468 | 0.727 | 2.381 | 11.650 | 0.328 | 1.152 |
| Unseen repository | All test PRs | 3482 | 1.000 | 0.632 | 0.872 | 3.508 | 6.644 | 0.162 | 0.326 |
| Unseen repository | Standard path | 1089 | 0.313 | 0.810 | 0.944 | 4.187 | 1.375 | 0.063 | -0.724 |
| Unseen repository | Routed | 2393 | 0.687 | 0.550 | 0.839 | 3.198 | 9.043 | 0.206 | 0.803 |

## Repository-Cluster Bootstrap Contrasts

| split | metric | std_minus_routed | ci_low | ci_high | direction |
| --- | --- | --- | --- | --- | --- |
| Temporal | Q: merge rate | 0.330 | 0.091 | 0.403 | higher is better |
| Temporal | Q: closed within 30 days | 0.207 | 0.091 | 0.256 | higher is better |
| Temporal | C: initial burden proxy | 3.688 | 1.121 | 4.758 | lower is better |
| Temporal | Xi: downstream workload | -9.957 | -11.765 | -5.599 | lower is better |
| Temporal | V: violation-risk proxy | -0.255 | -0.311 | -0.122 | lower is better |
| Temporal | L: composite loss proxy | -0.984 | -1.601 | -0.503 | lower is better |
| Unseen repository | Q: merge rate | 0.260 | 0.175 | 0.346 | higher is better |
| Unseen repository | Q: closed within 30 days | 0.105 | 0.057 | 0.159 | higher is better |
| Unseen repository | C: initial burden proxy | 0.989 | 0.330 | 1.725 | lower is better |
| Unseen repository | Xi: downstream workload | -7.668 | -9.382 | -6.024 | lower is better |
| Unseen repository | V: violation-risk proxy | -0.143 | -0.199 | -0.096 | lower is better |
| Unseen repository | L: composite loss proxy | -1.528 | -1.882 | -1.161 | lower is better |
