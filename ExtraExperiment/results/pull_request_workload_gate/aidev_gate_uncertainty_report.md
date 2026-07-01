# AIDev Gate Uncertainty Report

This report adds repository cluster bootstrap uncertainty intervals to the main AIDev workload gate results. It reuses the same proposal time feature set, train/calibration/test split logic, logistic gate, and 0.10 calibration risk setting as the main AIDev gate analysis.

The bootstrap resamples repositories with replacement within the held-out test split. Intervals therefore describe test-set uncertainty under repository-level dependence; they do not turn the observational AIDev study into a causal policy-effect experiment.

## Main Metrics

| Split | Metric | Point estimate and 95% cluster bootstrap CI |
|---|---|---:|
| Temporal | AUC | 0.900 [0.692, 0.956] |
| Temporal | Average precision | 0.493 [0.442, 0.546] |
| Temporal | High workload base rate | 0.142 [0.064, 0.359] |
| Temporal | Acceptance rate | 0.842 [0.597, 0.930] |
| Temporal | Accepted high workload rate | 0.074 [0.029, 0.254] |
| Temporal | High workload recall by routing | 0.559 [0.496, 0.623] |
| Temporal | Mean workload, accepted | 1.693 [0.684, 5.776] |
| Temporal | Mean workload, routed | 11.650 [10.371, 13.209] |
| Temporal | Workload share routed | 0.564 [0.504, 0.625] |
| Unseen repository | AUC | 0.764 [0.702, 0.814] |
| Unseen repository | Average precision | 0.541 [0.477, 0.613] |
| Unseen repository | High workload base rate | 0.332 [0.254, 0.401] |
| Unseen repository | Acceptance rate | 0.313 [0.223, 0.417] |
| Unseen repository | Accepted high workload rate | 0.079 [0.049, 0.122] |
| Unseen repository | High workload recall by routing | 0.926 [0.888, 0.953] |
| Unseen repository | Mean workload, accepted | 1.375 [0.929, 2.025] |
| Unseen repository | Mean workload, routed | 9.043 [7.293, 10.712] |
| Unseen repository | Workload share routed | 0.935 [0.899, 0.959] |

## Claim Guidance

- Allowed: proposal time AIDev features show downstream workload signal under temporal and unseen repository splits, with uncertainty intervals around AUC, acceptance, accepted high workload rate, and workload routed to conservative handling.
- Allowed: unseen repository evaluation remains more conservative than temporal evaluation, with lower acceptance and higher workload routed to conservative handling.
- Not allowed: the AIDev gate causally reduces resource use or downstream rework for the same task. That requires the controlled runtime experiment.
