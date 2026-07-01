# AIDev Workload Definition Sensitivity

This diagnostic reruns the calibrated risk setting for the gate under alternative downstream workload definitions and high workload thresholds. It is observational evidence only; it does not estimate the causal effect of deploying the gate.

## Workload Definitions
- `aggregate_main`: Original review, reviews requesting changes, comment, and later commit workload.
- `communication_review`: Reviews, request changes, inline review comments, and issue comments.
- `human_review`: Human reviews, request changes, and inline review comments.
- `followup_revision`: Later commits, changed files, test-like files, and log later churn.
- `broad_with_related`: Original aggregate plus related issues and log later churn.

## Risk Setting Sensitivity Table
| split | definition | quantile | n | auc | average precision | base high workload rate | acceptance rate | accepted high workload rate | high workload recall by routing | mean workload accepted | mean workload routed | workload share routed |
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

## Skipped Fits
These fits were skipped because the training split did not contain both high workload classes under that definition and threshold.
| split | definition | quantile | error |
| --- | --- | --- | --- |
| Temporal | human_review | 0.750 | Split temporal has only one training class for high workload target. |
| Unseen repository | human_review | 0.750 | Split unseen repository has only one training class for high workload target. |
| Unseen repository | human_review | 0.800 | Split unseen repository has only one training class for high workload target. |
