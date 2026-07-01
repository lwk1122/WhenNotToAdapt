# Equal Coverage Baseline Diagnostic

This diagnostic compares baselines at the main gate's calibration coverage. The main defensible-features gate keeps its risk-target threshold; other baselines use score thresholds that match the main gate's calibration acceptance rate. Test metrics are then evaluated without using test outcomes to set thresholds.

| baseline | selector | target_calibration_acceptance | calibration_acceptance_rate | test_acceptance_rate | test_accepted_high_workload_rate | test_high_workload_recall_by_abstention | test_workload_share_abstained | test_auc | test_average_precision |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| logistic_all_features | risk_target_threshold | 0.315 | 0.315 | 0.313 | 0.079 | 0.926 | 0.935 | 0.764 | 0.541 |
| cost_sensitive_workload_logistic | equal_calibration_coverage | 0.315 | 0.315 | 0.310 | 0.077 | 0.928 | 0.938 | 0.765 | 0.541 |
| categorical_prior | equal_calibration_coverage | 0.315 | 0.342 | 0.396 | 0.107 | 0.873 | 0.881 | 0.749 | 0.534 |
| logistic_no_agent | equal_calibration_coverage | 0.315 | 0.315 | 0.339 | 0.120 | 0.877 | 0.889 | 0.726 | 0.517 |
| simple_text_threshold | equal_calibration_coverage | 0.315 | 0.315 | 0.271 | 0.235 | 0.809 | 0.831 | 0.660 | 0.498 |
| selective_uncertainty_only | equal_calibration_coverage | 0.315 | 0.315 | 0.265 | 0.491 | 0.609 | 0.595 | 0.376 | 0.276 |

Allowed claim: workload-aware scoring retains low accepted risk at usable coverage under unseen repository evaluation better than simple text or uncertainty-only rules.
Boundary: this is a retrospective observational diagnostic, not a deployed routing experiment.
