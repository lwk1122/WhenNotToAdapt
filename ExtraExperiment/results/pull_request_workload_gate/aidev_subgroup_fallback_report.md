# Calibration Subgroup Fallback Diagnostic

This diagnostic applies subgroup flags learned on the calibration split before evaluating the unseen repository test split. The global gate uses one threshold for all PRs. The risk-flag fallback routes PRs belonging to calibration subgroups whose accepted high workload rate exceeds the risk limit with enough accepted rows. The risk-or-low-support fallback additionally routes PRs from subgroups with insufficient calibration acceptance support.

| strategy | flagged_groups | flagged_test_share | acceptance_rate | accepted_high_workload_rate | high_workload_recall_by_routing | workload_share_routed | mean_workload_accepted | mean_workload_routed |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| global_gate | 0 | 0.000 | 0.313 | 0.079 | 0.926 | 0.935 | 1.375 | 9.043 |
| calibration_risk_flags | 6 | 0.789 | 0.087 | 0.063 | 0.984 | 0.986 | 1.066 | 7.176 |
| risk_or_low_support_flags | 15 | 0.904 | 0.082 | 0.039 | 0.990 | 0.992 | 0.637 | 7.178 |

Allowed claim: subgroup monitoring can trade lower accepted risk for lower coverage under shift.
Boundary: this is a retrospective fallback diagnostic and does not estimate outcomes after extra review.
