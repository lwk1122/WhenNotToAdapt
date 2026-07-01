# AIDev Workload Gate Results

## Main Split Table

| split | selector | setting | n | auc | avg_precision | base_high_rate | accept_rate | accepted_high_rate | high_recall_routed | routing_precision | mean_workload_accepted | mean_workload_routed | workload_share_routed |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Temporal | calibration_risk_budget | 0.100 | 6720 | 0.900 | 0.493 | 0.142 | 0.842 | 0.074 | 0.559 | 0.500 | 1.693 | 11.650 | 0.564 |
| Unseen repository | calibration_risk_budget | 0.100 | 3482 | 0.764 | 0.541 | 0.332 | 0.313 | 0.079 | 0.926 | 0.448 | 1.375 | 9.043 | 0.935 |

## Main Split Uncertainty

| split | metric | point_95ci | bootstrap_unit | bootstrap_rounds | bootstrap_valid_rounds |
| --- | --- | --- | --- | --- | --- |
| Temporal | AUC | 0.900 [0.692, 0.956] | repo | 500 | 500 |
| Temporal | Average precision | 0.493 [0.442, 0.546] | repo | 500 | 500 |
| Temporal | High workload base rate | 0.142 [0.064, 0.359] | repo | 500 | 500 |
| Temporal | Acceptance rate | 0.842 [0.597, 0.930] | repo | 500 | 500 |
| Temporal | Accepted high workload rate | 0.074 [0.029, 0.254] | repo | 500 | 500 |
| Temporal | High workload recall by routing | 0.559 [0.496, 0.623] | repo | 500 | 500 |
| Temporal | Mean workload accepted | 1.693 [0.684, 5.776] | repo | 500 | 500 |
| Temporal | Mean workload routed | 11.650 [10.371, 13.209] | repo | 500 | 500 |
| Temporal | Workload share routed | 0.564 [0.504, 0.625] | repo | 500 | 500 |
| Unseen repository | AUC | 0.764 [0.702, 0.814] | repo | 500 | 500 |
| Unseen repository | Average precision | 0.541 [0.477, 0.613] | repo | 500 | 500 |
| Unseen repository | High workload base rate | 0.332 [0.254, 0.401] | repo | 500 | 500 |
| Unseen repository | Acceptance rate | 0.313 [0.223, 0.417] | repo | 500 | 500 |
| Unseen repository | Accepted high workload rate | 0.079 [0.049, 0.122] | repo | 500 | 500 |
| Unseen repository | High workload recall by routing | 0.926 [0.888, 0.953] | repo | 500 | 500 |
| Unseen repository | Mean workload accepted | 1.375 [0.929, 2.025] | repo | 500 | 500 |
| Unseen repository | Mean workload routed | 9.043 [7.293, 10.712] | repo | 500 | 500 |
| Unseen repository | Workload share routed | 0.935 [0.899, 0.959] | repo | 500 | 500 |

## Baseline Comparison

| split | baseline | selector | setting | n | auc | avg_precision | base_high_rate | accept_rate | accepted_high_rate | high_recall_routed | mean_workload_accepted | mean_workload_routed | workload_share_routed |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Temporal | Defensible features | calibration_risk_budget | 0.100 | 6720 | 0.900 | 0.493 | 0.142 | 0.842 | 0.074 | 0.559 | 1.693 | 11.650 | 0.564 |
| Temporal | Uncertainty threshold | calibration_risk_budget | 0.100 | 6720 | 0.712 | 0.279 | 0.142 | 0.703 | 0.082 | 0.593 | 2.031 | 6.196 | 0.563 |
| Temporal | Workload weights | calibration_risk_budget | 0.100 | 6720 | 0.899 | 0.494 | 0.142 | 0.843 | 0.074 | 0.558 | 1.690 | 11.741 | 0.564 |
| Temporal | No agent ID | calibration_risk_budget | 0.100 | 6720 | 0.893 | 0.497 | 0.142 | 0.846 | 0.074 | 0.556 | 1.684 | 11.977 | 0.564 |
| Temporal | Categorical prior | calibration_risk_budget | 0.100 | 6720 | 0.885 | 0.478 | 0.142 | 0.822 | 0.071 | 0.590 | 1.725 | 10.392 | 0.566 |
| Temporal | Text threshold | calibration_risk_budget | 0.100 | 6720 | 0.786 | 0.417 | 0.142 | 0.815 | 0.076 | 0.564 | 1.700 | 10.191 | 0.576 |
| Unseen repository | Defensible features | calibration_risk_budget | 0.100 | 3482 | 0.764 | 0.541 | 0.332 | 0.313 | 0.079 | 0.926 | 1.375 | 9.043 | 0.935 |
| Unseen repository | Uncertainty threshold | calibration_risk_budget | 0.100 | 3482 | 0.376 | 0.276 | 0.332 | 0.000 | 1.000 | 0.999 | 16.000 | 6.642 | 0.999 |
| Unseen repository | Workload weights | calibration_risk_budget | 0.100 | 3482 | 0.765 | 0.541 | 0.332 | 0.304 | 0.077 | 0.930 | 1.331 | 8.964 | 0.939 |
| Unseen repository | No agent ID | calibration_risk_budget | 0.100 | 3482 | 0.726 | 0.517 | 0.332 | 0.273 | 0.107 | 0.912 | 1.907 | 8.419 | 0.922 |
| Unseen repository | Categorical prior | calibration_risk_budget | 0.100 | 3482 | 0.749 | 0.534 | 0.332 | 0.305 | 0.094 | 0.914 | 1.783 | 8.778 | 0.918 |
| Unseen repository | Text threshold | calibration_risk_budget | 0.100 | 3482 | 0.660 | 0.498 | 0.332 | 0.001 | 0.000 | 1.000 | 0.000 | 6.650 | 1.000 |

## Workload Component Prediction

| split | component | target_rule | threshold | positive_rate | auc | avg_precision | brier |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Temporal | outcome_review_count | q0.80 | 1.000 | 0.170 | 0.892 | 0.507 | 0.133 |
| Temporal | outcome_human_review_count | q0.80 | 1.000 | 0.122 | 0.895 | 0.463 | 0.131 |
| Temporal | outcome_request_changes_count | positive | 0.000 | 0.023 | 0.861 | 0.104 | 0.124 |
| Temporal | outcome_inline_review_comment_count | positive | 0.000 | 0.101 | 0.868 | 0.332 | 0.144 |
| Temporal | outcome_issue_comment_count | q0.80 | 2.000 | 0.165 | 0.924 | 0.643 | 0.093 |
| Temporal | outcome_followup_commit_count | q0.80 | 2.000 | 0.188 | 0.909 | 0.634 | 0.110 |
| Temporal | outcome_followup_detail_changed_files | q0.80 | 4.000 | 0.156 | 0.901 | 0.583 | 0.120 |
| Temporal | outcome_followup_detail_churn | q0.80 | 148.000 | 0.149 | 0.912 | 0.590 | 0.115 |
| Temporal | outcome_followup_detail_test_files | positive | 0.000 | 0.122 | 0.883 | 0.478 | 0.140 |
| Temporal | outcome_related_issue_count | positive | 0.000 | 0.121 | 0.968 | 0.768 | 0.061 |
| Unseen repository | outcome_review_count | q0.80 | 1.000 | 0.348 | 0.705 | 0.519 | 0.278 |
| Unseen repository | outcome_human_review_count | positive | 0.000 | 0.277 | 0.748 | 0.463 | 0.262 |
| Unseen repository | outcome_request_changes_count | positive | 0.000 | 0.045 | 0.687 | 0.079 | 0.299 |
| Unseen repository | outcome_inline_review_comment_count | positive | 0.000 | 0.186 | 0.706 | 0.341 | 0.303 |
| Unseen repository | outcome_issue_comment_count | q0.80 | 2.000 | 0.330 | 0.824 | 0.676 | 0.201 |
| Unseen repository | outcome_followup_commit_count | q0.80 | 2.000 | 0.372 | 0.776 | 0.605 | 0.234 |
| Unseen repository | outcome_followup_detail_changed_files | q0.80 | 2.000 | 0.420 | 0.768 | 0.673 | 0.234 |
| Unseen repository | outcome_followup_detail_churn | q0.80 | 62.000 | 0.348 | 0.767 | 0.590 | 0.248 |
| Unseen repository | outcome_followup_detail_test_files | positive | 0.000 | 0.242 | 0.755 | 0.444 | 0.254 |
| Unseen repository | outcome_related_issue_count | positive | 0.000 | 0.274 | 0.934 | 0.851 | 0.110 |

## Gate Error and Routing Cases

| split | case_type | n | share | mean_score | mean_workload | median_workload | mean_reviews | mean_issue_comments | mean_followup_commits | mean_followup_churn | top_agents |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Unseen repository | Route low workload | 1322 | 0.380 | 0.694 | 1.693 | 2.000 | 0.241 | 0.749 | 0.683 | 811.060 | Copilot=441; OpenAI_Codex=423; Devin=263; Cursor=152; Claude_Code=43 |
| Unseen repository | Accept high workload | 86 | 0.025 | 0.271 | 11.523 | 9.000 | 1.721 | 1.721 | 6.174 | 1136.756 | OpenAI_Codex=72; Copilot=6; Cursor=6; Devin=2 |
| Unseen repository | Accept low workload | 1003 | 0.288 | 0.223 | 0.504 | 0.000 | 0.088 | 0.195 | 0.211 | 65.578 | OpenAI_Codex=994; Cursor=6; Claude_Code=2; Copilot=1 |
| Unseen repository | Route high workload | 1071 | 0.308 | 0.799 | 18.115 | 12.000 | 3.809 | 3.670 | 6.624 | 6438.672 | Copilot=534; Devin=307; Cursor=97; OpenAI_Codex=88; Claude_Code=45 |
| Temporal | Route low workload | 531 | 0.079 | 0.853 | 2.866 | 3.000 | 0.412 | 1.047 | 1.337 | 4012.288 | Copilot=363; Devin=104; Cursor=35; Claude_Code=29 |
| Temporal | Accept high workload | 419 | 0.062 | 0.548 | 17.317 | 12.000 | 3.411 | 3.220 | 6.828 | 5859.391 | Copilot=127; OpenAI_Codex=123; Cursor=91; Devin=43; Claude_Code=35 |
| Temporal | Accept low workload | 5238 | 0.779 | 0.170 | 0.443 | 0.000 | 0.058 | 0.179 | 0.184 | 197.226 | OpenAI_Codex=4774; Cursor=183; Copilot=151; Devin=80; Claude_Code=50 |
| Temporal | Route high workload | 532 | 0.079 | 0.860 | 20.417 | 14.000 | 4.434 | 4.259 | 6.348 | 9079.186 | Copilot=322; Devin=157; Claude_Code=35; Cursor=18 |

## Subgroup and Shift Diagnostics

| split | subgroup_type | subgroup_value | rows | accepted_count | high_workload_rate | acceptance_rate | accepted_high_workload_rate | risk_over_budget | risk_flag_note | workload_share_routed | auc |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Unseen repository | repo_star_bucket | >1000 | 1214 | 159 | 0.470 | 0.131 | 0.164 | True | enough accepted rows | 0.967 | 0.700 |
| Unseen repository | initial_churn_bucket | 251-1000 | 291 | 68 | 0.388 | 0.234 | 0.132 | True | enough accepted rows | 0.913 | 0.733 |
| Unseen repository | repo_language | Go | 222 | 58 | 0.568 | 0.261 | 0.345 | True | enough accepted rows | 0.887 | 0.676 |
| Unseen repository | feature_task_type | test | 135 | 51 | 0.326 | 0.378 | 0.118 | True | enough accepted rows | 0.897 | 0.734 |
| Unseen repository | agent | Devin | 572 | 2 | 0.540 | 0.003 | 1.000 | False | low accepted rows | 0.997 | 0.515 |
| Unseen repository | repo_language | JavaScript | 232 | 1 | 0.470 | 0.004 | 0.000 | False | low accepted rows | 1.000 | 0.550 |
| Unseen repository | initial_churn_bucket | 0 | 972 | 6 | 0.539 | 0.006 | 0.833 | False | low accepted rows | 0.994 | 0.487 |
| Unseen repository | agent | Copilot | 982 | 7 | 0.550 | 0.007 | 0.857 | False | low accepted rows | 0.992 | 0.493 |
| Unseen repository | repo_language | Zig | 132 | 2 | 0.311 | 0.015 | 0.000 | False | low accepted rows | 0.996 | 0.745 |
| Unseen repository | agent | Cursor | 261 | 12 | 0.395 | 0.046 | 0.500 | False | low accepted rows | 0.949 | 0.634 |
| Temporal | agent | Copilot | 963 | 278 | 0.466 | 0.289 | 0.457 | True | enough accepted rows | 0.726 | 0.534 |
| Temporal | initial_churn_bucket | 0 | 951 | 277 | 0.471 | 0.291 | 0.477 | True | enough accepted rows | 0.719 | 0.519 |
| Temporal | agent | Devin | 384 | 123 | 0.521 | 0.320 | 0.350 | True | enough accepted rows | 0.756 | 0.607 |
| Temporal | repo_language | Rust | 148 | 64 | 0.318 | 0.432 | 0.203 | True | enough accepted rows | 0.685 | 0.691 |
| Temporal | repo_language | TypeScript | 740 | 335 | 0.439 | 0.453 | 0.307 | True | enough accepted rows | 0.686 | 0.650 |
| Temporal | repo_language | JavaScript | 143 | 79 | 0.238 | 0.552 | 0.278 | True | enough accepted rows | 0.423 | 0.534 |
| Temporal | repo_star_bucket | >1000 | 1370 | 757 | 0.392 | 0.553 | 0.303 | True | enough accepted rows | 0.598 | 0.651 |
| Temporal | agent | Claude_Code | 149 | 85 | 0.470 | 0.570 | 0.412 | True | enough accepted rows | 0.560 | 0.631 |
| Temporal | repo_language | Java | 110 | 82 | 0.491 | 0.745 | 0.451 | True | enough accepted rows | 0.353 | 0.613 |
| Temporal | feature_task_type | fix | 1422 | 1136 | 0.188 | 0.799 | 0.122 | True | enough accepted rows | 0.449 | 0.834 |
| Temporal | agent | Cursor | 327 | 274 | 0.333 | 0.838 | 0.332 | True | enough accepted rows | 0.196 | 0.455 |
| Temporal | feature_task_type | docs | 493 | 451 | 0.178 | 0.915 | 0.166 | True | enough accepted rows | 0.206 | 0.789 |
| Temporal | repo_language | HTML | 134 | 130 | 0.134 | 0.970 | 0.131 | True | enough accepted rows | 0.043 | 0.743 |

## Workload Definition Sensitivity

| split | definition | quantile | n | auc | avg_precision | base_high_rate | accept_rate | accepted_high_rate | high_recall_routed | mean_workload_accepted | mean_workload_routed | workload_share_routed |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Unseen repository | aggregate_main | 0.750 | 3482 | 0.810 | 0.752 | 0.465 | 0.178 | 0.082 | 0.968 | 0.947 | 7.876 | 0.975 |
| Unseen repository | aggregate_main | 0.800 | 3482 | 0.764 | 0.541 | 0.332 | 0.313 | 0.079 | 0.926 | 1.375 | 9.043 | 0.935 |
| Unseen repository | aggregate_main | 0.900 | 3482 | 0.745 | 0.323 | 0.184 | 0.654 | 0.104 | 0.631 | 3.874 | 11.885 | 0.619 |
| Unseen repository | broad_with_related | 0.750 | 3482 | 0.808 | 0.688 | 0.422 | 0.246 | 0.074 | 0.957 | 1.814 | 12.251 | 0.954 |
| Unseen repository | broad_with_related | 0.800 | 3482 | 0.786 | 0.579 | 0.346 | 0.365 | 0.076 | 0.920 | 2.388 | 13.880 | 0.910 |
| Unseen repository | broad_with_related | 0.900 | 3482 | 0.755 | 0.329 | 0.184 | 0.683 | 0.110 | 0.593 | 6.115 | 17.354 | 0.569 |
| Unseen repository | communication_review | 0.750 | 3482 | 0.797 | 0.735 | 0.445 | 0.240 | 0.109 | 0.941 | 0.688 | 5.220 | 0.960 |
| Unseen repository | communication_review | 0.800 | 3482 | 0.769 | 0.568 | 0.339 | 0.382 | 0.098 | 0.890 | 0.920 | 6.121 | 0.915 |
| Unseen repository | communication_review | 0.900 | 3482 | 0.758 | 0.360 | 0.185 | 0.619 | 0.088 | 0.706 | 1.900 | 7.772 | 0.715 |
| Unseen repository | followup_revision | 0.750 | 3482 | 0.786 | 0.709 | 0.439 | 0.008 | 0.071 | 0.999 | 5.938 | 23.663 | 0.998 |
| Unseen repository | followup_revision | 0.800 | 3482 | 0.760 | 0.584 | 0.352 | 0.246 | 0.092 | 0.935 | 3.324 | 30.114 | 0.965 |
| Unseen repository | followup_revision | 0.900 | 3482 | 0.712 | 0.308 | 0.180 | 0.623 | 0.104 | 0.640 | 13.153 | 40.669 | 0.652 |
| Unseen repository | human_review | 0.900 | 3482 | 0.745 | 0.397 | 0.213 | 0.576 | 0.110 | 0.704 | 0.869 | 3.809 | 0.763 |
| Temporal | aggregate_main | 0.750 | 6720 | 0.909 | 0.593 | 0.181 | 0.784 | 0.071 | 0.690 | 1.190 | 10.812 | 0.714 |
| Temporal | aggregate_main | 0.800 | 6720 | 0.900 | 0.493 | 0.142 | 0.842 | 0.074 | 0.559 | 1.693 | 11.650 | 0.564 |
| Temporal | aggregate_main | 0.900 | 6720 | 0.884 | 0.271 | 0.066 | 1.000 | 0.066 | 0.000 | 3.268 | 0.000 | 0.000 |
| Temporal | broad_with_related | 0.750 | 6720 | 0.913 | 0.611 | 0.173 | 0.796 | 0.064 | 0.705 | 1.837 | 16.587 | 0.698 |
| Temporal | broad_with_related | 0.800 | 6720 | 0.907 | 0.528 | 0.141 | 0.840 | 0.069 | 0.591 | 2.481 | 17.249 | 0.569 |
| Temporal | broad_with_related | 0.900 | 6720 | 0.886 | 0.271 | 0.065 | 1.000 | 0.065 | 0.000 | 4.842 | 0.000 | 0.000 |
| Temporal | communication_review | 0.750 | 6720 | 0.920 | 0.630 | 0.178 | 0.801 | 0.070 | 0.683 | 0.827 | 7.180 | 0.683 |
| Temporal | communication_review | 0.800 | 6720 | 0.910 | 0.518 | 0.146 | 0.842 | 0.073 | 0.577 | 1.026 | 7.767 | 0.587 |
| Temporal | communication_review | 0.900 | 6720 | 0.884 | 0.314 | 0.079 | 0.991 | 0.076 | 0.036 | 2.039 | 7.597 | 0.034 |
| Temporal | followup_revision | 0.750 | 6720 | 0.912 | 0.651 | 0.180 | 0.783 | 0.063 | 0.728 | 2.935 | 38.246 | 0.783 |
| Temporal | followup_revision | 0.800 | 6720 | 0.900 | 0.556 | 0.144 | 0.832 | 0.068 | 0.608 | 4.746 | 39.538 | 0.628 |
| Temporal | followup_revision | 0.900 | 6720 | 0.869 | 0.267 | 0.068 | 1.000 | 0.068 | 0.000 | 10.607 | 0.000 | 0.000 |
| Temporal | human_review | 0.800 | 6720 | 0.888 | 0.490 | 0.154 | 0.828 | 0.081 | 0.565 | 0.471 | 3.712 | 0.621 |
| Temporal | human_review | 0.900 | 6720 | 0.884 | 0.335 | 0.087 | 0.977 | 0.080 | 0.102 | 0.938 | 4.929 | 0.110 |

## Resolution-Time Survival Diagnostic

| split | gate_group | rows | closed_events | censored_open | observed_closure_rate | km_median_days | unresolved_probability_7d | unresolved_probability_30d | unresolved_probability_90d | rmst_30d_days |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Unseen repository | accepted | 1089 | 1033 | 56 | 0.949 | 0.003 | 0.077 | 0.046 | 0.027 | 2.211 |
| Unseen repository | all | 3482 | 3131 | 351 | 0.899 | 0.090 | 0.203 | 0.114 | 0.054 | 5.134 |
| Unseen repository | routed | 2393 | 2098 | 295 | 0.877 | 0.374 | 0.261 | 0.145 | 0.070 | 6.469 |
| Temporal | accepted | 5657 | 5284 | 373 | 0.934 | 0.000 | 0.059 | 0.045 | 0.045 | 1.720 |
| Temporal | all | 6720 | 6057 | 663 | 0.901 | 0.001 | 0.091 | 0.066 | 0.066 | 2.548 |
| Temporal | routed | 1063 | 773 | 290 | 0.727 | 0.806 | 0.260 | 0.182 | 0.182 | 7.026 |

## Resolution-Time Survival Contrasts

| split | metric | point | ci_low | ci_high | bootstrap_unit | bootstrap_rounds | bootstrap_valid_rounds |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Unseen repository | Observed closure rate, accepted minus routed | 0.072 | 0.038 | 0.111 | repo | 500 | 500 |
| Unseen repository | 30-day unresolved probability, accepted minus routed | -0.098 | -0.155 | -0.052 | repo | 500 | 500 |
| Unseen repository | 30-day RMST unresolved, accepted minus routed | -4.258 | -6.156 | -2.856 | repo | 500 | 500 |
| Temporal | Observed closure rate, accepted minus routed | 0.207 | 0.091 | 0.252 | repo | 500 | 500 |
| Temporal | 30-day unresolved probability, accepted minus routed | -0.137 | -0.191 | -0.011 | repo | 500 | 500 |
| Temporal | 30-day RMST unresolved, accepted minus routed | -5.306 | -6.788 | -1.962 | repo | 500 | 500 |

## Frontier Table

| split | selector | setting | n | auc | avg_precision | base_high_rate | accept_rate | accepted_high_rate | high_recall_routed | routing_precision | mean_workload_accepted | mean_workload_routed | workload_share_routed |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Temporal | fixed_acceptance | 0.200 | 6720 | 0.900 | 0.493 | 0.142 | 0.259 | 0.003 | 0.994 | 0.190 | 0.094 | 4.375 | 0.993 |
| Temporal | fixed_acceptance | 0.400 | 6720 | 0.900 | 0.493 | 0.142 | 0.506 | 0.005 | 0.982 | 0.281 | 0.135 | 6.472 | 0.979 |
| Temporal | fixed_acceptance | 0.600 | 6720 | 0.900 | 0.493 | 0.142 | 0.696 | 0.015 | 0.926 | 0.431 | 0.395 | 9.830 | 0.916 |
| Temporal | fixed_acceptance | 0.800 | 6720 | 0.900 | 0.493 | 0.142 | 0.823 | 0.066 | 0.614 | 0.492 | 1.530 | 11.366 | 0.614 |
| Temporal | calibration_risk_budget | 0.050 | 6720 | 0.900 | 0.493 | 0.142 | 0.752 | 0.035 | 0.813 | 0.463 | 0.797 | 10.744 | 0.817 |
| Temporal | calibration_risk_budget | 0.100 | 6720 | 0.900 | 0.493 | 0.142 | 0.842 | 0.074 | 0.559 | 0.500 | 1.693 | 11.650 | 0.564 |
| Temporal | calibration_risk_budget | 0.150 | 6720 | 0.900 | 0.493 | 0.142 | 0.952 | 0.121 | 0.184 | 0.545 | 2.785 | 12.882 | 0.188 |
| Unseen repository | fixed_acceptance | 0.200 | 3482 | 0.764 | 0.541 | 0.332 | 0.196 | 0.041 | 0.976 | 0.403 | 0.905 | 8.045 | 0.973 |
| Unseen repository | fixed_acceptance | 0.400 | 3482 | 0.764 | 0.541 | 0.332 | 0.447 | 0.107 | 0.857 | 0.514 | 1.979 | 10.409 | 0.867 |
| Unseen repository | fixed_acceptance | 0.600 | 3482 | 0.764 | 0.541 | 0.332 | 0.644 | 0.208 | 0.596 | 0.556 | 3.859 | 11.674 | 0.626 |
| Unseen repository | fixed_acceptance | 0.800 | 3482 | 0.764 | 0.541 | 0.332 | 0.806 | 0.279 | 0.324 | 0.556 | 5.442 | 11.646 | 0.340 |
| Unseen repository | calibration_risk_budget | 0.050 | 3482 | 0.764 | 0.541 | 0.332 | 0.136 | 0.038 | 0.984 | 0.379 | 0.907 | 7.546 | 0.981 |
| Unseen repository | calibration_risk_budget | 0.100 | 3482 | 0.764 | 0.541 | 0.332 | 0.313 | 0.079 | 0.926 | 0.448 | 1.375 | 9.043 | 0.935 |
| Unseen repository | calibration_risk_budget | 0.150 | 3482 | 0.764 | 0.541 | 0.332 | 0.506 | 0.146 | 0.777 | 0.523 | 2.713 | 10.672 | 0.793 |

## Leave One Agent Out Table

| heldout_agent | selector | setting | n | auc | avg_precision | base_high_rate | accept_rate | accepted_high_rate | high_recall_routed | routing_precision | mean_workload_accepted | mean_workload_routed | workload_share_routed |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Claude_Code | calibration_risk_budget | 0.100 | 459 | 0.642 | 0.612 | 0.468 | 0.717 | 0.410 | 0.372 | 0.615 | 9.018 | 15.900 | 0.411 |
| Copilot | calibration_risk_budget | 0.100 | 4970 | 0.507 | 0.569 | 0.575 | 0.842 | 0.579 | 0.153 | 0.555 | 13.238 | 13.316 | 0.159 |
| Cursor | calibration_risk_budget | 0.100 | 1541 | 0.574 | 0.458 | 0.377 | 0.947 | 0.362 | 0.090 | 0.642 | 6.247 | 11.827 | 0.095 |
| Devin | calibration_risk_budget | 0.100 | 4827 | 0.572 | 0.757 | 0.708 | 0.636 | 0.675 | 0.393 | 0.765 | 8.272 | 10.794 | 0.427 |
| OpenAI_Codex | calibration_risk_budget | 0.100 | 21799 | 0.451 | 0.016 | 0.017 | 0.277 | 0.021 | 0.667 | 0.016 | 1.674 | 1.017 | 0.613 |
