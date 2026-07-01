# AIDev Subgroup and Shift Diagnostics

This report evaluates the global 0.10 risk setting for the workload gate within separate test subgroups. Subgroups are diagnostic only: the gate is calibrated globally, so subgroup accepted high workload rates are not guaranteed to stay below 0.10. Budget flags require enough accepted rows; raw over budget indicators with very small accepted counts should be treated as unstable diagnostics.

## Main Diagnostic Questions

- Which agents, languages, task types, repository size buckets, or initial churn buckets exceed the global accepted high workload budget?
- Where does the gate become especially conservative by accepting few PRs?
- Which large subgroups dominate the held-out evidence?

## Subgroups Above the Global Risk Budget

| split | subgroup | value | rows | repositories | accepted PRs | accepted high workload PRs | high workload rate | acceptance rate | accepted high workload rate | above budget | raw above budget | flag note | high workload recall by routing | workload share routed | auc |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Unseen repository | repository language | Go | 222 | 37 | 58 | 20 | 0.568 | 0.261 | 0.345 | yes | yes | enough accepted rows | 0.841 | 0.887 | 0.676 |
| Unseen repository | repository stars | >1000 | 1214 | 217 | 159 | 26 | 0.470 | 0.131 | 0.164 | yes | yes | enough accepted rows | 0.954 | 0.967 | 0.700 |
| Unseen repository | initial churn | 251-1000 | 291 | 121 | 68 | 9 | 0.388 | 0.234 | 0.132 | yes | yes | enough accepted rows | 0.920 | 0.913 | 0.733 |
| Unseen repository | task type | test | 135 | 70 | 51 | 6 | 0.326 | 0.378 | 0.118 | yes | yes | enough accepted rows | 0.864 | 0.897 | 0.734 |
| Temporal | initial churn | 0 | 951 | 361 | 277 | 132 | 0.471 | 0.291 | 0.477 | yes | yes | enough accepted rows | 0.705 | 0.719 | 0.519 |
| Temporal | agent | Copilot | 963 | 357 | 278 | 127 | 0.466 | 0.289 | 0.457 | yes | yes | enough accepted rows | 0.717 | 0.726 | 0.534 |
| Temporal | repository language | Java | 110 | 23 | 82 | 37 | 0.491 | 0.745 | 0.451 | yes | yes | enough accepted rows | 0.315 | 0.353 | 0.613 |
| Temporal | agent | Claude_Code | 149 | 80 | 85 | 35 | 0.470 | 0.570 | 0.412 | yes | yes | enough accepted rows | 0.500 | 0.560 | 0.631 |
| Temporal | agent | Devin | 384 | 44 | 123 | 43 | 0.521 | 0.320 | 0.350 | yes | yes | enough accepted rows | 0.785 | 0.756 | 0.607 |
| Temporal | agent | Cursor | 327 | 108 | 274 | 91 | 0.333 | 0.838 | 0.332 | yes | yes | enough accepted rows | 0.165 | 0.196 | 0.455 |
| Temporal | repository language | TypeScript | 740 | 184 | 335 | 103 | 0.439 | 0.453 | 0.307 | yes | yes | enough accepted rows | 0.683 | 0.686 | 0.650 |
| Temporal | repository stars | >1000 | 1370 | 345 | 757 | 229 | 0.392 | 0.553 | 0.303 | yes | yes | enough accepted rows | 0.574 | 0.598 | 0.651 |
| Temporal | repository language | JavaScript | 143 | 50 | 79 | 22 | 0.238 | 0.552 | 0.278 | yes | yes | enough accepted rows | 0.353 | 0.423 | 0.534 |
| Temporal | repository language | Rust | 148 | 50 | 64 | 13 | 0.318 | 0.432 | 0.203 | yes | yes | enough accepted rows | 0.723 | 0.685 | 0.691 |
| Temporal | task type | docs | 493 | 142 | 451 | 75 | 0.178 | 0.915 | 0.166 | yes | yes | enough accepted rows | 0.148 | 0.206 | 0.789 |
| Temporal | repository language | HTML | 134 | 14 | 130 | 17 | 0.134 | 0.970 | 0.131 | yes | yes | enough accepted rows | 0.056 | 0.043 | 0.743 |
| Temporal | task type | fix | 1422 | 374 | 1136 | 139 | 0.188 | 0.799 | 0.122 | yes | yes | enough accepted rows | 0.481 | 0.449 | 0.834 |

## Lowest Coverage Subgroups

| split | subgroup | value | rows | repositories | accepted PRs | accepted high workload PRs | high workload rate | acceptance rate | accepted high workload rate | above budget | raw above budget | flag note | high workload recall by routing | workload share routed | auc |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Unseen repository | agent | Devin | 572 | 56 | 2 | 2 | 0.540 | 0.003 | 1.000 | no | yes | low accepted rows | 0.994 | 0.997 | 0.515 |
| Unseen repository | repository language | JavaScript | 232 | 41 | 1 | 0 | 0.470 | 0.004 | 0.000 | no | no | low accepted rows | 1.000 | 1.000 | 0.550 |
| Unseen repository | initial churn | 0 | 972 | 217 | 6 | 5 | 0.539 | 0.006 | 0.833 | no | yes | low accepted rows | 0.990 | 0.994 | 0.487 |
| Unseen repository | agent | Copilot | 982 | 213 | 7 | 6 | 0.550 | 0.007 | 0.857 | no | yes | low accepted rows | 0.989 | 0.992 | 0.493 |
| Unseen repository | repository language | Zig | 132 | 2 | 2 | 0 | 0.311 | 0.015 | 0.000 | no | no | low accepted rows | 1.000 | 0.996 | 0.745 |
| Unseen repository | agent | Cursor | 261 | 60 | 12 | 6 | 0.395 | 0.046 | 0.500 | no | yes | low accepted rows | 0.942 | 0.949 | 0.634 |
| Unseen repository | repository language | C# | 373 | 54 | 21 | 1 | 0.641 | 0.056 | 0.048 | no | no | low accepted rows | 0.996 | 0.997 | 0.672 |
| Unseen repository | repository stars | >1000 | 1214 | 217 | 159 | 26 | 0.470 | 0.131 | 0.164 | yes | yes | enough accepted rows | 0.954 | 0.967 | 0.700 |
| Unseen repository | initial churn | >1000 | 118 | 62 | 17 | 2 | 0.508 | 0.144 | 0.118 | no | yes | low accepted rows | 0.967 | 0.947 | 0.702 |
| Unseen repository | repository language | Rust | 145 | 23 | 23 | 6 | 0.483 | 0.159 | 0.261 | no | yes | low accepted rows | 0.914 | 0.936 | 0.665 |
| Unseen repository | initial churn | 251-1000 | 291 | 121 | 68 | 9 | 0.388 | 0.234 | 0.132 | yes | yes | enough accepted rows | 0.920 | 0.913 | 0.733 |
| Unseen repository | repository language | TypeScript | 681 | 115 | 165 | 15 | 0.358 | 0.242 | 0.091 | no | no | enough accepted rows | 0.939 | 0.940 | 0.724 |
| Unseen repository | task type | feat | 1270 | 318 | 325 | 26 | 0.381 | 0.256 | 0.080 | no | no | enough accepted rows | 0.946 | 0.947 | 0.770 |
| Unseen repository | repository language | Go | 222 | 37 | 58 | 20 | 0.568 | 0.261 | 0.345 | yes | yes | enough accepted rows | 0.841 | 0.887 | 0.676 |
| Unseen repository | task type | refactor | 259 | 97 | 71 | 5 | 0.305 | 0.274 | 0.070 | no | no | enough accepted rows | 0.937 | 0.952 | 0.791 |
| Unseen repository | task type | fix | 1136 | 317 | 411 | 29 | 0.287 | 0.362 | 0.071 | no | no | enough accepted rows | 0.911 | 0.917 | 0.761 |
| Unseen repository | task type | test | 135 | 70 | 51 | 6 | 0.326 | 0.378 | 0.118 | yes | yes | enough accepted rows | 0.864 | 0.897 | 0.734 |
| Unseen repository | repository language | Kotlin | 245 | 8 | 93 | 1 | 0.020 | 0.380 | 0.011 | no | no | enough accepted rows | 0.800 | 0.868 | 0.793 |
| Unseen repository | task type | docs | 415 | 127 | 160 | 7 | 0.323 | 0.386 | 0.044 | no | no | enough accepted rows | 0.948 | 0.954 | 0.806 |
| Unseen repository | initial churn | 51-250 | 870 | 195 | 338 | 32 | 0.282 | 0.389 | 0.095 | no | no | enough accepted rows | 0.869 | 0.868 | 0.793 |

## Largest Held Out Subgroups

| split | subgroup | value | rows | repositories | accepted PRs | accepted high workload PRs | high workload rate | acceptance rate | accepted high workload rate | above budget | raw above budget | flag note | high workload recall by routing | workload share routed | auc |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Unseen repository | repository stars | 101-1000 | 2268 | 345 | 930 | 60 | 0.259 | 0.410 | 0.065 | no | no | enough accepted rows | 0.898 | 0.902 | 0.781 |
| Unseen repository | agent | OpenAI_Codex | 1577 | 233 | 1066 | 72 | 0.101 | 0.676 | 0.068 | no | no | enough accepted rows | 0.550 | 0.557 | 0.705 |
| Unseen repository | task type | feat | 1270 | 318 | 325 | 26 | 0.381 | 0.256 | 0.080 | no | no | enough accepted rows | 0.946 | 0.947 | 0.770 |
| Unseen repository | initial churn | 1-50 | 1231 | 254 | 660 | 38 | 0.175 | 0.536 | 0.058 | no | no | enough accepted rows | 0.823 | 0.834 | 0.817 |
| Unseen repository | repository stars | >1000 | 1214 | 217 | 159 | 26 | 0.470 | 0.131 | 0.164 | yes | yes | enough accepted rows | 0.954 | 0.967 | 0.700 |
| Unseen repository | task type | fix | 1136 | 317 | 411 | 29 | 0.287 | 0.362 | 0.071 | no | no | enough accepted rows | 0.911 | 0.917 | 0.761 |
| Unseen repository | agent | Copilot | 982 | 213 | 7 | 6 | 0.550 | 0.007 | 0.857 | no | yes | low accepted rows | 0.989 | 0.992 | 0.493 |
| Unseen repository | initial churn | 0 | 972 | 217 | 6 | 5 | 0.539 | 0.006 | 0.833 | no | yes | low accepted rows | 0.990 | 0.994 | 0.487 |
| Unseen repository | initial churn | 51-250 | 870 | 195 | 338 | 32 | 0.282 | 0.389 | 0.095 | no | no | enough accepted rows | 0.869 | 0.868 | 0.793 |
| Unseen repository | repository language | TypeScript | 681 | 115 | 165 | 15 | 0.358 | 0.242 | 0.091 | no | no | enough accepted rows | 0.939 | 0.940 | 0.724 |
| Unseen repository | repository language | Python | 608 | 111 | 375 | 22 | 0.197 | 0.617 | 0.059 | no | no | enough accepted rows | 0.817 | 0.804 | 0.815 |
| Unseen repository | agent | Devin | 572 | 56 | 2 | 2 | 0.540 | 0.003 | 1.000 | no | yes | low accepted rows | 0.994 | 0.997 | 0.515 |
| Unseen repository | task type | docs | 415 | 127 | 160 | 7 | 0.323 | 0.386 | 0.044 | no | no | enough accepted rows | 0.948 | 0.954 | 0.806 |
| Unseen repository | repository language | C# | 373 | 54 | 21 | 1 | 0.641 | 0.056 | 0.048 | no | no | low accepted rows | 0.996 | 0.997 | 0.672 |
| Unseen repository | initial churn | 251-1000 | 291 | 121 | 68 | 9 | 0.388 | 0.234 | 0.132 | yes | yes | enough accepted rows | 0.920 | 0.913 | 0.733 |
| Unseen repository | agent | Cursor | 261 | 60 | 12 | 6 | 0.395 | 0.046 | 0.500 | no | yes | low accepted rows | 0.942 | 0.949 | 0.634 |
| Unseen repository | task type | refactor | 259 | 97 | 71 | 5 | 0.305 | 0.274 | 0.070 | no | no | enough accepted rows | 0.937 | 0.952 | 0.791 |
| Unseen repository | repository language | Kotlin | 245 | 8 | 93 | 1 | 0.020 | 0.380 | 0.011 | no | no | enough accepted rows | 0.800 | 0.868 | 0.793 |
| Unseen repository | repository language | JavaScript | 232 | 41 | 1 | 0 | 0.470 | 0.004 | 0.000 | no | no | low accepted rows | 1.000 | 1.000 | 0.550 |
| Unseen repository | repository language | Go | 222 | 37 | 58 | 20 | 0.568 | 0.261 | 0.345 | yes | yes | enough accepted rows | 0.841 | 0.887 | 0.676 |

## Claim Guidance

- Allowed: the global gate is not uniformly calibrated across all subgroups; subgroup diagnostics identify where local or online calibration is needed.
- Allowed: unseen repository shift concentrates high workload and conservative routing in specific agents/languages/task types.
- Not allowed: subgroup differences prove causal differences in agent quality or repository difficulty. AIDev is observational and confounded.
