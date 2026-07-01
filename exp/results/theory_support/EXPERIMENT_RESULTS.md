# Experiment Results

## Run Summary

- Consolidated result directory: `results\theory_support`
- Benchmark seeds: `64`
- Online simulator seeds: `32`
- Online simulator horizon: `1200`
- Distribution reference dataset: `swe_bench_test`

## Dataset Inventory

| dataset | rows |
| --- | --- |
| swe_bench_tasks | 21527 |
| swe_verified_tasks | 500 |
| swe_smith_tasks | 59136 |
| swe_rebench_tasks | 27878 |
| swe_agent_trajectories | 80036 |
| codetrace_manifest | 4316 |

## Structural Diagnostics

| metric | value |
| --- | --- |
| Reduced AUC | 0.7815 |
| Full AUC | 0.7561 |
| AUC gain (full - reduced) | -0.0253 |
| Reduced-state support | True |
| Canonical context AUC | 0.7622 |
| Context strong-positive recall | 1.0000 |
| Context over-internalization rate | 0.0000 |
| Top-2 mean regret | 0.000868 |
| Top-2 exact match | 0.8000 |
| Verification-boundary violation (e) | 0.000000 |
| Verification-boundary violation (q) | 0.000000 |
| Far-inside verify miss rate | 0.000000 |
| Far-outside verify rate | 0.1806 |
| Continuous-effort mean | 0.4592 |
| Continuous-effort violation (q) | 0.2083 |
| Counterfactual optimal-effort mean | 0.3585 |
| Counterfactual interior-optimum share | 1.0000 |
| Counterfactual rule exact match | 0.3149 |
| Counterfactual rule one-step match | 1.0000 |
| Counterfactual rule mean regret | 0.018217 |
| Counterfactual violation (q) | 0.2000 |
| Governance monotonicity violation rate | 0.003350 |

## Simulator Predictive Validation

| target | metric | value |
| --- | --- | --- |
| failure | auc | 0.9341 |
| failure | brier | 0.0799 |
| failure | accuracy | 0.8531 |
| nominal_load | mae | 0.0048 |
| nominal_load | rmse | 0.0066 |
| nominal_load | r2 | 0.9850 |
| nominal_load | corr | 0.9944 |
| recovery_load | mae | 0.0430 |
| recovery_load | rmse | 0.0583 |
| recovery_load | r2 | 0.6036 |
| recovery_load | corr | 0.7840 |
| service | mae | 0.0214 |
| service | rmse | 0.0270 |
| service | r2 | 0.8467 |
| service | corr | 0.9284 |
| total_load | mae | 0.0439 |
| total_load | rmse | 0.0597 |
| total_load | r2 | 0.7581 |
| total_load | corr | 0.8747 |

## Simulator Calibration Validation

| mode | rows | load_violation_rate | service_violation_rate | certified_positive_rate | certified_positive_precision | certified_positive_recall | headroom_sign_accuracy |
| --- | --- | --- | --- | --- | --- | --- | --- |
| g0_aggressive | 354 | 0.1102 | 0.0395 | 0.4944 | 1.0000 | 0.5952 | 0.6638 |
| g1_balanced | 354 | 0.0989 | 0.0395 | 0.5763 | 1.0000 | 0.6645 | 0.7090 |
| g2_conservative | 354 | 0.0791 | 0.0395 | 0.6751 | 1.0000 | 0.7611 | 0.7881 |
| g3_safe | 354 | 0.0706 | 0.0395 | 0.7288 | 1.0000 | 0.7963 | 0.8136 |

## Repository-Executing Shadow Runtime Pilot

| controller | tasks | success_rate | catastrophic_failure_rate | avg_test_runs | verification_rate | safe_state_rate | progress_rate | avg_best_problem_reduction | avg_return_to_safe |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| minimal_verify | 8 | 0.0000 | 0.2500 | 1.0000 | 0.0000 | 0.0000 | 0.1250 | 2.2500 |  |
| rsrc_guarded | 8 | 0.0000 | 0.3750 | 3.1250 | 0.4250 | 0.4688 | 0.1250 | 0.2500 | 0.2500 |
| sempc_lite | 8 | 0.0000 | 0.3750 | 3.0000 | 0.4000 | 0.5312 | 0.1250 | 2.2500 | 0.6000 |
| static_conservative | 8 | 0.1250 | 0.2500 | 2.7500 | 0.4083 | 0.0000 | 0.2500 | 2.7500 |  |

## Shadow Runtime Pairwise

| pair | metric | mean_diff | ci_low | ci_high | n |
| --- | --- | --- | --- | --- | --- |
| sempc_lite - rsrc_guarded | success | 0.0000 | 0.0000 | 0.0000 | 8 |
| sempc_lite - rsrc_guarded | catastrophic_failure | 0.0000 | -0.5000 | 0.5000 | 8 |
| sempc_lite - rsrc_guarded | patch_apply_successes | 0.0000 | -1.2500 | 1.0000 | 8 |
| sempc_lite - rsrc_guarded | test_runs | -0.1250 | -1.3750 | 0.8750 | 8 |
| sempc_lite - rsrc_guarded | verification_events | -0.1250 | -1.3750 | 0.8750 | 8 |
| sempc_lite - rsrc_guarded | fallback_events | 0.0000 | 0.0000 | 0.0000 | 8 |
| sempc_lite - rsrc_guarded | any_progress | 0.0000 | -0.3750 | 0.2500 | 8 |
| sempc_lite - rsrc_guarded | best_problem_reduction | 2.0000 | -0.7500 | 6.5062 | 8 |
| sempc_lite - rsrc_guarded | final_problem_reduction | 2.0000 | -0.7500 | 6.5062 | 8 |
| sempc_lite - rsrc_guarded | safe_state_rate | 0.0625 | 0.0000 | 0.1875 | 8 |
| sempc_lite - rsrc_guarded | post_error_extra_work | 0.0000 | 0.0000 | 0.0000 | 8 |
| sempc_lite - rsrc_guarded | return_to_safe_steps | 0.0000 |  |  | 8 |

## Key Findings

- Reduced-state support is positive: reduced AUC = 0.7815, full AUC = 0.7561, and the gap is -0.0253.
- Out-of-simulator holdout validation now checks the semi-structured simulator primitives: failure AUC = 0.9341, total-load R2 = 0.7581, total-load correlation = 0.8747, and service R2 = 0.8467.
- Canonicalized context diagnostics are materially stronger than raw token counts: canonical additive AUC = 0.7622 vs raw additive AUC = 0.5786, mean canonical footprint CV drops from 2.2695 to 0.7685, and top-K exact-match = 0.8000.
- Lower-score context screening is conservative in the desired direction: strong-positive recall = 1.0000, over-internalization rate = 0.0000, and conservative set-match = 0.9895.
- Recovery amplification is visible in CodeTraceBench: mean future bad stages after an incorrect stage = 0.3437, and P(incorrect->incorrect) = 0.1175.
- Split-calibrated certificates are no longer degenerate: theta-safe nonempty rate = 0.7801, mean safe-set size = 2.6598, theta precision = 1.0000, and theta recall = 0.8365.
- Verification-boundary diagnostics are now directly observed through a counterfactual heatmap: monotonicity violations are 0.000000 along e and 0.000000 along q; far-inside miss rate is 0.000000.
- The continuous-effort extension is now empirically instantiated: mean optimal effort proxy = 0.4592, high-effort share = 0.4648, and q-monotonicity violation = 0.2083.
- A counterfactual effort-surface check aligns the theorem rule with the semi-structured runtime objective: optimal-effort mean = 0.3585, rule exact match = 0.3149, one-step match = 1.0000, rule mean regret = 0.018217, and counterfactual q-violation = 0.2000.
- The 8-task LM Studio repository-executing shadow runtime is best read as a pilot sanity check, not performance evidence: static_conservative is the only controller with nonzero live success (0.1250), while rsrc_guarded and sempc_lite have success 0.0000/0.0000; catastrophic-failure rates are 0.2500, 0.2500, 0.3750, and 0.3750 for minimal_verify, static_conservative, rsrc_guarded, and sempc_lite.
- Distribution shift is mild for Verified (0.1128) and moderate for Rebench (0.3834), but large for Smith (0.9272).
- On verified, SE-MPC should be read as a small local-improvement layer over RSRC, not as a dominant controller: success 0.4504->0.4578, operating-cost proxy 0.6923->0.6832, overload 0.0003->0.0003.
- On test, SE-MPC should be read as a small local-improvement layer over RSRC, not as a dominant controller: success 0.4368->0.4407, operating-cost proxy 0.6965->0.6907, overload 0.0002->0.0002.
- On rebench, SE-MPC should be read as a small local-improvement layer over RSRC, not as a dominant controller: success 0.4472->0.4603, operating-cost proxy 0.6906->0.6754, overload 0.0002->0.0002.
- On smith, SE-MPC should be read as a small local-improvement layer over RSRC, not as a dominant controller: success 0.3790->0.3804, operating-cost proxy 0.7137->0.7119, overload 0.0008->0.0008.
- The calibrated certificate remains conservative but no longer empty: positive certified headroom rate = 0.7801, benchmark-safe nonempty rate = 0.9326, and one-step load/service violations are 0.0462/0.0762.
- Online simulator on verified: SE-MPC remains close to RSRC, with overload 0.0000->0.0000, certified safe occupancy 0.5847->0.5819, benchmark action-safe occupancy 0.7198->0.7201, runtime-safe occupancy 0.7114->0.7120, action-safe precision 1.0000->1.0000, fallback 0.4153->0.4157, and negative drift outside safe 0.9912->0.9913.
- Loss-only CAMC on verified has activation rates 0.2148/0.0628/0.4979 for static-anchor, RSRC-anchor, and SE-MPC-candidate variants; post-switch violation rates are 0.0000/0.0000/0.0000; safety-augmented costs are 1.0104/1.0200/1.0236.
- Pareto-CAMC on verified turns CAMC into a non-inferiority filter: activation rates are 0.0000/0.0000/0.1906, post-switch violation rates are 0.0000/0.0000/0.0000, and success rates are 0.2898/0.2828/0.3078.
- Online simulator on test: SE-MPC remains close to RSRC, with overload 0.0001->0.0001, certified safe occupancy 0.5630->0.5615, benchmark action-safe occupancy 0.6633->0.6670, runtime-safe occupancy 0.6687->0.6750, action-safe precision 0.9988->0.9988, fallback 0.4370->0.4345, and negative drift outside safe 0.9911->0.9910.
- Loss-only CAMC on test has activation rates 0.3625/0.0729/0.5133 for static-anchor, RSRC-anchor, and SE-MPC-candidate variants; post-switch violation rates are 0.0001/0.0034/0.0009; safety-augmented costs are 1.1481/1.1565/1.1389.
- Pareto-CAMC on test turns CAMC into a non-inferiority filter: activation rates are 0.0000/0.0000/0.2631, post-switch violation rates are 0.0000/0.0000/0.0002, and success rates are 0.2832/0.2769/0.3034.
- Online simulator on rebench: SE-MPC remains close to RSRC, with overload 0.0002->0.0002, certified safe occupancy 0.5752->0.5724, benchmark action-safe occupancy 0.6793->0.6807, runtime-safe occupancy 0.7003->0.7050, action-safe precision 0.9987->0.9989, fallback 0.4248->0.4242, and negative drift outside safe 0.9744->0.9736.
- Loss-only CAMC on rebench has activation rates 0.2415/0.0880/0.4982 for static-anchor, RSRC-anchor, and SE-MPC-candidate variants; post-switch violation rates are 0.0000/0.0023/0.0017; safety-augmented costs are 1.1698/1.1880/1.1659.
- Pareto-CAMC on rebench turns CAMC into a non-inferiority filter: activation rates are 0.0000/0.0000/0.2016, post-switch violation rates are 0.0000/0.0000/0.0005, and success rates are 0.2739/0.2664/0.2933.
- Online simulator on smith: SE-MPC remains close to RSRC, with overload 0.0175->0.0176, certified safe occupancy 0.1527->0.1529, benchmark action-safe occupancy 0.2082->0.2085, runtime-safe occupancy 0.3089->0.3093, action-safe precision 0.9978->0.9981, fallback 0.8473->0.8470, and negative drift outside safe 0.8429->0.8424.
- Loss-only CAMC on smith has activation rates 0.0011/0.1485/0.1463 for static-anchor, RSRC-anchor, and SE-MPC-candidate variants; post-switch violation rates are 0.0000/0.0010/0.0005; safety-augmented costs are 1.4376/1.4457/1.4452.
- Pareto-CAMC on smith turns CAMC into a non-inferiority filter: activation rates are 0.0000/0.0193/0.0161, post-switch violation rates are 0.0000/0.0000/0.0000, and success rates are 0.2615/0.2629/0.2627.
- Headroom-conditioned drift now links calibration to stability more directly: negative-drift rates in certified-adverse states under RSRC are 0.7859 on test and 0.6446 on rebench, while benign positive-headroom states remain benchmark-safe at rates 0.6747 and 0.7132.
- The direct positive-headroom drift slice is now reported for theorem alignment: under RSRC with epsilon_s=0.03 and L>=0.5 outside the safe envelope, test/rebench rows are 26/51, with negative-drift rates 1.0000/1.0000.

## Certificate Diagnostics

| metric | value |
| --- | --- |
| Overall trajectory failure rate | 0.8327 |
| Mean future bad stages after incorrect | 0.3437 |
| Load violation rate | 0.0462 |
| Service violation rate | 0.0762 |
| Theta-safe nonempty rate | 0.7801 |
| Theta-safe mean size | 2.6598 |
| Benchmark-safe nonempty rate | 0.9326 |
| Theta-safe precision | 1.0000 |
| Theta-safe recall | 0.8365 |

## Distributional Diagnostics

| dataset | rows | mean_abs_feature_shift_vs_test | high_risk_share | g0_safe_rate | g3_safe_rate |
| --- | --- | --- | --- | --- | --- |
| swe_bench_train | 19008 | 0.4204 | 0.9821 | 0.9929 | 1.0000 |
| swe_bench_dev | 225 | 0.1504 | 0.9822 | 0.6311 | 1.0000 |
| swe_bench_test | 2294 | 0.0000 | 0.9926 | 0.7249 | 1.0000 |
| swe_verified | 500 | 0.1128 | 0.9940 | 0.8060 | 1.0000 |
| swe_rebench | 27878 | 0.3834 | 0.9880 | 0.7371 | 1.0000 |
| swe_smith | 59136 | 0.9272 | 0.9995 | 0.3151 | 1.0000 |

## Controller Benchmark

| dataset | controller | success_rate | discounted_cost | avg_workload | overload_rate | verification_rate |
| --- | --- | --- | --- | --- | --- | --- |
| verified | oracle_src | 0.5464 | 0.6404 | 0.0001 | 0.0000 | 1.0000 |
| verified | rsrc | 0.4504 | 0.6923 | 0.0001 | 0.0003 | 1.0000 |
| verified | se_mpc | 0.4578 | 0.6832 | 0.0001 | 0.0003 | 0.9862 |
| verified | greedy_myopic | 0.5471 | 0.6368 | 0.0012 | 0.0242 | 1.0000 |
| verified | static_conservative | 0.4606 | 0.6120 | 0.0000 | 0.0000 | 1.0000 |
| verified | static_aggressive | 0.5451 | 0.6567 | 0.0071 | 0.1117 | 1.0000 |
| verified | always_verify | 0.5474 | 0.6321 | 0.0001 | 0.0001 | 1.0000 |
| verified | always_verify_throttle | 0.4855 | 0.6146 | 0.0000 | 0.0000 | 1.0000 |
| verified | adaptive_threshold | 0.4775 | 0.6752 | 0.0001 | 0.0003 | 1.0000 |
| verified | maxweight_backlog | 0.4810 | 0.6478 | 0.0000 | 0.0001 | 1.0000 |
| verified | headroom_only | 0.4449 | 0.7249 | 0.0098 | 0.1446 | 1.0000 |
| verified | rsrc_no_recovery | 0.4482 | 0.7221 | 0.0095 | 0.1418 | 1.0000 |
| verified | rsrc_no_context | 0.4471 | 0.6947 | 0.0001 | 0.0008 | 1.0000 |
| verified | minimal_verify | 0.1982 | 0.5186 | 0.0188 | 0.3555 | 0.0000 |
| verified | plain_mpc | 0.5002 | 0.6270 | 0.0046 | 0.0981 | 0.8500 |
| test | oracle_src | 0.5264 | 0.6493 | 0.0002 | 0.0000 | 1.0000 |
| test | rsrc | 0.4368 | 0.6965 | 0.0001 | 0.0002 | 1.0000 |
| test | se_mpc | 0.4407 | 0.6907 | 0.0001 | 0.0002 | 0.9905 |
| test | greedy_myopic | 0.5265 | 0.6488 | 0.0028 | 0.0570 | 0.9983 |
| test | static_conservative | 0.4453 | 0.6204 | 0.0000 | 0.0000 | 1.0000 |
| test | static_aggressive | 0.5251 | 0.6764 | 0.0129 | 0.1830 | 1.0000 |
| test | always_verify | 0.5275 | 0.6397 | 0.0001 | 0.0000 | 1.0000 |
| test | always_verify_throttle | 0.4691 | 0.6217 | 0.0000 | 0.0000 | 1.0000 |
| test | adaptive_threshold | 0.4623 | 0.6803 | 0.0001 | 0.0002 | 1.0000 |
| test | maxweight_backlog | 0.4654 | 0.6523 | 0.0001 | 0.0005 | 1.0000 |
| test | headroom_only | 0.4294 | 0.7440 | 0.0167 | 0.2241 | 1.0000 |
| test | rsrc_no_recovery | 0.4344 | 0.7402 | 0.0163 | 0.2204 | 1.0000 |
| test | rsrc_no_context | 0.4317 | 0.6997 | 0.0001 | 0.0006 | 1.0000 |
| test | minimal_verify | 0.1832 | 0.5234 | 0.0205 | 0.3903 | 0.0000 |
| test | plain_mpc | 0.4811 | 0.6387 | 0.0064 | 0.1344 | 0.8500 |
| rebench | oracle_src | 0.5412 | 0.6382 | 0.0002 | 0.0000 | 1.0000 |
| rebench | rsrc | 0.4472 | 0.6906 | 0.0001 | 0.0002 | 1.0000 |
| rebench | se_mpc | 0.4603 | 0.6754 | 0.0001 | 0.0002 | 0.9797 |
| rebench | greedy_myopic | 0.5407 | 0.6409 | 0.0038 | 0.0811 | 0.9977 |
| rebench | static_conservative | 0.4569 | 0.6142 | 0.0000 | 0.0000 | 1.0000 |
| rebench | static_aggressive | 0.5397 | 0.6681 | 0.0147 | 0.1936 | 1.0000 |
| rebench | always_verify | 0.5420 | 0.6317 | 0.0001 | 0.0001 | 1.0000 |
| rebench | always_verify_throttle | 0.4883 | 0.6120 | 0.0000 | 0.0000 | 1.0000 |
| rebench | adaptive_threshold | 0.4809 | 0.6696 | 0.0001 | 0.0002 | 1.0000 |
| rebench | maxweight_backlog | 0.4846 | 0.6397 | 0.0001 | 0.0004 | 1.0000 |
| rebench | headroom_only | 0.4414 | 0.7365 | 0.0186 | 0.2296 | 1.0000 |
| rebench | rsrc_no_recovery | 0.4449 | 0.7339 | 0.0184 | 0.2277 | 1.0000 |
| rebench | rsrc_no_context | 0.4437 | 0.6929 | 0.0001 | 0.0004 | 1.0000 |
| rebench | minimal_verify | 0.1955 | 0.5151 | 0.0186 | 0.3574 | 0.0000 |
| rebench | plain_mpc | 0.4958 | 0.6266 | 0.0061 | 0.1269 | 0.8500 |
| smith | oracle_src | 0.4653 | 0.6697 | 0.0005 | 0.0000 | 1.0000 |
| smith | rsrc | 0.3790 | 0.7137 | 0.0003 | 0.0008 | 1.0000 |
| smith | se_mpc | 0.3804 | 0.7119 | 0.0003 | 0.0008 | 0.9972 |
| smith | greedy_myopic | 0.4641 | 0.6985 | 0.0166 | 0.3326 | 1.0000 |
| smith | static_conservative | 0.3856 | 0.6557 | 0.0000 | 0.0000 | 1.0000 |
| smith | static_aggressive | 0.4607 | 0.7719 | 0.0549 | 0.6197 | 1.0000 |
| smith | always_verify | 0.4661 | 0.6622 | 0.0003 | 0.0004 | 1.0000 |
| smith | always_verify_throttle | 0.3923 | 0.6560 | 0.0000 | 0.0000 | 1.0000 |
| smith | adaptive_threshold | 0.3863 | 0.7092 | 0.0003 | 0.0007 | 1.0000 |
| smith | maxweight_backlog | 0.3903 | 0.6728 | 0.0001 | 0.0000 | 1.0000 |
| smith | headroom_only | 0.3735 | 0.8412 | 0.0652 | 0.6742 | 1.0000 |
| smith | rsrc_no_recovery | 0.3736 | 0.8411 | 0.0652 | 0.6742 | 1.0000 |
| smith | rsrc_no_context | 0.3789 | 0.7138 | 0.0003 | 0.0008 | 1.0000 |
| smith | minimal_verify | 0.1301 | 0.5415 | 0.0317 | 0.6071 | 0.0000 |
| smith | plain_mpc | 0.4188 | 0.6766 | 0.0170 | 0.3333 | 0.8500 |

## Online Simulator

| dataset | controller | discounted_cost | success_rate | overload_rate | safe_occupancy_rate | benchmark_action_safe_occupancy_rate | benchmark_safe_occupancy_rate | safe_set_nonempty_rate | exact_safe_set_nonempty_rate | benchmark_action_set_nonempty_rate | fallback_rate | high_effort_rate | theta_benchmark_precision | theta_benchmark_recall | theta_nesting_precision | action_safe_precision | safe_event_precision | negative_drift_rate_outside_safe | avg_return_time_to_safe | certificate_load_violation_rate | certificate_service_violation_rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| rebench | adaptive_threshold | 0.4469 | 0.2021 | 0.0005 | 0.4499 | 0.6111 | 0.7268 | 0.4499 | 0.6112 | 0.6112 | 0.0000 | 0.5904 | 0.9997 | 0.7353 | 0.9997 | 0.9994 | 0.9900 | 0.9754 | 3.6843 | 0.0001 | 0.0879 |
| rebench | always_verify | 0.5226 | 0.3633 | 0.0001 | 0.2177 | 0.2727 | 0.3655 | 0.2177 | 0.2735 | 0.2735 | 0.0000 | 1.0000 | 0.9978 | 0.7935 | 0.9978 | 0.9940 | 0.6945 | 0.9870 | 6.3767 | 0.0001 | 0.3105 |
| rebench | always_verify_throttle | 0.5217 | 0.3641 | 0.0001 | 0.2497 | 0.3122 | 0.4054 | 0.2497 | 0.3126 | 0.3126 | 0.0000 | 1.0000 | 0.9974 | 0.7964 | 0.9974 | 0.9962 | 0.7962 | 0.9865 | 6.2461 | 0.0001 | 0.2947 |
| rebench | camc_rsrc_anchor | 0.4797 | 0.2604 | 0.0002 | 0.4997 | 0.6610 | 0.6952 | 0.5474 | 0.6616 | 0.6616 | 0.4526 | 0.8137 | 0.9996 | 0.8268 | 0.9996 | 0.9986 | 0.9423 | 0.9778 | 2.8877 | 0.0001 | 0.1702 |
| rebench | camc_sempc_candidate | 0.4696 | 0.2442 | 0.0002 | 0.4402 | 0.6679 | 0.7261 | 0.5361 | 0.6687 | 0.6687 | 0.4657 | 0.7399 | 0.9996 | 0.8010 | 0.9996 | 0.9997 | 0.9712 | 0.9789 | 2.9460 | 0.0001 | 0.1434 |
| rebench | camc_static_anchor | 0.4762 | 0.2705 | 0.0001 | 0.6401 | 0.7345 | 0.7664 | 0.6401 | 0.7345 | 0.7345 | 0.3599 | 0.8189 | 0.9997 | 0.8709 | 0.9997 | 0.9997 | 0.9751 | 0.9709 | 2.5180 | 0.0001 | 0.1625 |
| rebench | greedy_myopic | 0.4612 | 0.2152 | 0.0011 | 0.2558 | 0.3847 | 0.5441 | 0.3991 | 0.5226 | 0.5226 | 0.0000 | 0.6609 | 0.9995 | 0.7625 | 0.9995 | 1.0000 | 0.9885 | 0.9825 | 6.3934 | 0.0001 | 0.1676 |
| rebench | headroom_only | 0.4803 | 0.2653 | 0.0002 | 0.5790 | 0.6732 | 0.6931 | 0.5790 | 0.6738 | 0.6738 | 0.4210 | 0.8153 | 0.9996 | 0.8588 | 0.9996 | 0.9985 | 0.9408 | 0.9745 | 2.7352 | 0.0001 | 0.1791 |
| rebench | maxweight_backlog | 0.4790 | 0.2689 | 0.0002 | 0.6054 | 0.7047 | 0.7301 | 0.6054 | 0.7053 | 0.7053 | 0.0000 | 0.8173 | 0.9996 | 0.8579 | 0.9996 | 0.9987 | 0.9569 | 0.9727 | 2.6451 | 0.0001 | 0.1612 |
| rebench | minimal_verify | 0.4876 | 0.0311 | 0.0198 | 0.0009 | 0.0017 | 0.0017 | 0.0009 | 0.0017 | 0.0017 | 0.0000 | 0.0000 | 1.0000 | 0.5312 | 1.0000 | 1.0000 | 1.0000 | 0.8731 | 1180.2031 | 0.0012 | 0.0000 |
| rebench | oracle_src | 0.4522 | 0.1753 | 0.0009 | 0.4177 | 0.4177 | 0.5702 | 0.4177 | 0.4177 | 0.4177 | 0.0000 | 0.4966 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.9464 | 0.9732 | 4.4324 | 0.0002 | 0.0556 |
| rebench | pareto_camc_rsrc_anchor | 0.4799 | 0.2664 | 0.0002 | 0.5752 | 0.6793 | 0.7003 | 0.5752 | 0.6799 | 0.6799 | 0.4248 | 0.8156 | 0.9997 | 0.8456 | 0.9997 | 0.9987 | 0.9445 | 0.9744 | 2.7241 | 0.0001 | 0.1750 |
| rebench | pareto_camc_sempc_candidate | 0.4795 | 0.2933 | 0.0001 | 0.6229 | 0.7164 | 0.7354 | 0.6270 | 0.7165 | 0.7165 | 0.3753 | 0.8743 | 0.9990 | 0.8740 | 0.9990 | 0.9992 | 0.9598 | 0.9727 | 2.5669 | 0.0001 | 0.1668 |
| rebench | pareto_camc_static_anchor | 0.4762 | 0.2739 | 0.0001 | 0.6898 | 0.7760 | 0.8081 | 0.6898 | 0.7760 | 0.7760 | 0.3102 | 0.8218 | 0.9997 | 0.8885 | 0.9997 | 0.9997 | 0.9853 | 0.9667 | 2.4249 | 0.0001 | 0.1272 |
| rebench | plain_mpc | 0.4587 | 0.0974 | 0.0024 | 0.0045 | 0.0278 | 0.0869 | 0.0133 | 0.0461 | 0.0461 | 0.0000 | 0.2446 | 1.0000 | 0.2890 | 1.0000 | 1.0000 | 1.0000 | 0.9705 | 386.7825 | 0.0006 | 0.0071 |
| rebench | rsrc | 0.4799 | 0.2664 | 0.0002 | 0.5752 | 0.6793 | 0.7003 | 0.5752 | 0.6799 | 0.6799 | 0.4248 | 0.8156 | 0.9997 | 0.8456 | 0.9997 | 0.9987 | 0.9445 | 0.9744 | 2.7241 | 0.0001 | 0.1750 |
| rebench | rsrc_no_context | 0.4800 | 0.2655 | 0.0002 | 0.5747 | 0.6781 | 0.6982 | 0.5747 | 0.6786 | 0.6786 | 0.4253 | 0.8155 | 0.9996 | 0.8465 | 0.9996 | 0.9988 | 0.9431 | 0.9748 | 2.7312 | 0.0001 | 0.1780 |
| rebench | rsrc_no_recovery | 0.4803 | 0.2662 | 0.0002 | 0.5798 | 0.6745 | 0.6948 | 0.5798 | 0.6752 | 0.6752 | 0.4202 | 0.8153 | 0.9996 | 0.8584 | 0.9996 | 0.9985 | 0.9413 | 0.9741 | 2.7320 | 0.0001 | 0.1760 |
| rebench | se_mpc | 0.4791 | 0.2690 | 0.0002 | 0.5724 | 0.6807 | 0.7050 | 0.5758 | 0.6811 | 0.6811 | 0.4242 | 0.8155 | 0.9997 | 0.8451 | 0.9997 | 0.9989 | 0.9463 | 0.9736 | 2.6586 | 0.0001 | 0.1585 |
| rebench | static_aggressive | 0.4877 | 0.2589 | 0.0008 | 0.2938 | 0.3876 | 0.4929 | 0.4170 | 0.5029 | 0.5029 | 0.0000 | 0.8088 | 0.9998 | 0.8285 | 0.9998 | 0.9998 | 0.9734 | 0.9834 | 5.6416 | 0.0001 | 0.2467 |
| rebench | static_conservative | 0.4762 | 0.2739 | 0.0001 | 0.6898 | 0.7760 | 0.8081 | 0.6898 | 0.7760 | 0.7760 | 0.0000 | 0.8218 | 0.9997 | 0.8885 | 0.9997 | 0.9997 | 0.9853 | 0.9667 | 2.4249 | 0.0001 | 0.1272 |
| smith | adaptive_threshold | 0.5582 | 0.2287 | 0.0174 | 0.2526 | 0.3383 | 0.4354 | 0.2526 | 0.3385 | 0.3385 | 0.0000 | 0.9392 | 0.9994 | 0.7451 | 0.9994 | 0.9988 | 0.9554 | 0.8217 | 5.6560 | 0.0000 | 0.2555 |
| smith | always_verify | 0.5990 | 0.2809 | 0.0177 | 0.0795 | 0.1189 | 0.2193 | 0.0795 | 0.1192 | 0.1192 | 0.0000 | 1.0000 | 0.9972 | 0.6634 | 0.9972 | 0.9924 | 0.6727 | 0.8546 | 16.0263 | 0.0000 | 0.3560 |
| smith | always_verify_throttle | 0.5987 | 0.2812 | 0.0176 | 0.0862 | 0.1278 | 0.2341 | 0.0862 | 0.1279 | 0.1279 | 0.0000 | 1.0000 | 0.9979 | 0.6701 | 0.9979 | 0.9966 | 0.7884 | 0.8538 | 15.5207 | 0.0000 | 0.3500 |
| smith | camc_rsrc_anchor | 0.5862 | 0.2474 | 0.0178 | 0.1519 | 0.2379 | 0.3465 | 0.1724 | 0.2380 | 0.2380 | 0.8276 | 0.9388 | 0.9996 | 0.7221 | 0.9996 | 0.9995 | 0.9445 | 0.8422 | 8.9459 | 0.0000 | 0.2882 |
| smith | camc_sempc_candidate | 0.5862 | 0.2480 | 0.0178 | 0.1513 | 0.2374 | 0.3459 | 0.1718 | 0.2375 | 0.2375 | 0.8287 | 0.9396 | 0.9996 | 0.7214 | 0.9996 | 0.9995 | 0.9426 | 0.8421 | 8.9252 | 0.0000 | 0.2881 |
| smith | camc_static_anchor | 0.5890 | 0.2615 | 0.0173 | 0.1770 | 0.2364 | 0.3464 | 0.1770 | 0.2364 | 0.2364 | 0.8230 | 0.9768 | 0.9994 | 0.7476 | 0.9994 | 0.9994 | 0.9493 | 0.8390 | 8.4725 | 0.0000 | 0.2890 |
| smith | greedy_myopic | 0.5849 | 0.2330 | 0.0243 | 0.0669 | 0.1070 | 0.2057 | 0.1126 | 0.1584 | 0.1584 | 0.0000 | 0.9533 | 0.9986 | 0.7078 | 0.9986 | 1.0000 | 0.9676 | 0.8542 | 20.4275 | 0.0000 | 0.3987 |
| smith | headroom_only | 0.5900 | 0.2605 | 0.0175 | 0.1560 | 0.2068 | 0.3066 | 0.1560 | 0.2071 | 0.2071 | 0.8440 | 0.9766 | 0.9982 | 0.7508 | 0.9982 | 0.9969 | 0.8389 | 0.8422 | 8.8437 | 0.0000 | 0.3082 |
| smith | maxweight_backlog | 0.5896 | 0.2609 | 0.0174 | 0.1584 | 0.2160 | 0.3184 | 0.1584 | 0.2160 | 0.2160 | 0.0000 | 0.9768 | 0.9989 | 0.7315 | 0.9989 | 0.9987 | 0.8769 | 0.8420 | 8.8294 | 0.0000 | 0.3026 |
| smith | minimal_verify | 12.4593 | 0.0198 | 0.9869 | 0.0005 | 0.0013 | 0.0015 | 0.0005 | 0.0013 | 0.0013 | 0.0000 | 0.0000 | 1.0000 | 0.4333 | 1.0000 | 1.0000 | 1.0000 | 0.0108 | 1199.3438 | 0.0001 | 0.0000 |
| smith | oracle_src | 0.5545 | 0.2133 | 0.0185 | 0.3759 | 0.3759 | 0.4315 | 0.3759 | 0.3759 | 0.3759 | 0.0000 | 0.9215 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.7894 | 0.7832 | 3.8099 | 0.0000 | 0.2326 |
| smith | pareto_camc_rsrc_anchor | 0.5891 | 0.2629 | 0.0174 | 0.1668 | 0.2245 | 0.3325 | 0.1668 | 0.2245 | 0.2245 | 0.8332 | 0.9808 | 0.9994 | 0.7415 | 0.9994 | 0.9994 | 0.9307 | 0.8407 | 8.6282 | 0.0000 | 0.2964 |
| smith | pareto_camc_sempc_candidate | 0.5891 | 0.2627 | 0.0174 | 0.1686 | 0.2267 | 0.3345 | 0.1689 | 0.2267 | 0.2267 | 0.8316 | 0.9786 | 0.9992 | 0.7436 | 0.9992 | 0.9992 | 0.9310 | 0.8403 | 8.5709 | 0.0000 | 0.2946 |
| smith | pareto_camc_static_anchor | 0.5890 | 0.2615 | 0.0173 | 0.1772 | 0.2365 | 0.3466 | 0.1772 | 0.2365 | 0.2365 | 0.8228 | 0.9768 | 0.9994 | 0.7480 | 0.9994 | 0.9994 | 0.9490 | 0.8389 | 8.4710 | 0.0000 | 0.2888 |
| smith | plain_mpc | 0.6736 | 0.1214 | 0.1365 | 0.0638 | 0.1473 | 0.3657 | 0.1538 | 0.2601 | 0.2601 | 0.0000 | 0.7115 | 1.0000 | 0.5768 | 1.0000 | 1.0000 | 0.9997 | 0.7462 | 38.4334 | 0.0000 | 0.0791 |
| smith | rsrc | 0.5898 | 0.2605 | 0.0175 | 0.1527 | 0.2082 | 0.3089 | 0.1527 | 0.2083 | 0.2083 | 0.8473 | 0.9767 | 0.9986 | 0.7313 | 0.9986 | 0.9978 | 0.8485 | 0.8429 | 8.9831 | 0.0000 | 0.3074 |
| smith | rsrc_no_context | 0.5898 | 0.2605 | 0.0175 | 0.1527 | 0.2082 | 0.3089 | 0.1527 | 0.2083 | 0.2083 | 0.8473 | 0.9767 | 0.9986 | 0.7311 | 0.9986 | 0.9978 | 0.8486 | 0.8429 | 8.9859 | 0.0000 | 0.3076 |
| smith | rsrc_no_recovery | 0.5900 | 0.2605 | 0.0175 | 0.1560 | 0.2068 | 0.3066 | 0.1560 | 0.2071 | 0.2071 | 0.8440 | 0.9766 | 0.9983 | 0.7508 | 0.9983 | 0.9969 | 0.8387 | 0.8422 | 8.8413 | 0.0000 | 0.3081 |
| smith | se_mpc | 0.5898 | 0.2609 | 0.0176 | 0.1529 | 0.2085 | 0.3093 | 0.1530 | 0.2086 | 0.2086 | 0.8470 | 0.9767 | 0.9988 | 0.7321 | 0.9988 | 0.9981 | 0.8489 | 0.8424 | 8.9452 | 0.0000 | 0.3054 |
| smith | static_aggressive | 0.6123 | 0.2508 | 0.0271 | 0.0339 | 0.0547 | 0.1302 | 0.0606 | 0.0893 | 0.0893 | 0.0000 | 0.9748 | 0.9975 | 0.6738 | 0.9975 | 0.9994 | 0.9212 | 0.8575 | 40.6344 | 0.0000 | 0.4593 |
| smith | static_conservative | 0.5890 | 0.2615 | 0.0173 | 0.1772 | 0.2365 | 0.3466 | 0.1772 | 0.2365 | 0.2365 | 0.0000 | 0.9768 | 0.9994 | 0.7480 | 0.9994 | 0.9994 | 0.9490 | 0.8389 | 8.4710 | 0.0000 | 0.2888 |
| test | adaptive_threshold | 0.4456 | 0.2161 | 0.0003 | 0.5509 | 0.7273 | 0.8026 | 0.5509 | 0.7274 | 0.7274 | 0.0000 | 0.6993 | 0.9999 | 0.7568 | 0.9999 | 0.9999 | 0.9858 | 0.9894 | 2.9516 | 0.0001 | 0.0667 |
| test | always_verify | 0.5210 | 0.3587 | 0.0000 | 0.2159 | 0.2665 | 0.3586 | 0.2159 | 0.2670 | 0.2670 | 0.0000 | 1.0000 | 0.9992 | 0.8073 | 0.9992 | 0.9972 | 0.6907 | 0.9950 | 6.5380 | 0.0000 | 0.2548 |
| test | always_verify_throttle | 0.5201 | 0.3595 | 0.0000 | 0.2472 | 0.3008 | 0.3975 | 0.2472 | 0.3010 | 0.3010 | 0.0000 | 1.0000 | 0.9991 | 0.8197 | 0.9991 | 0.9981 | 0.7867 | 0.9948 | 6.4197 | 0.0000 | 0.2414 |
| test | camc_rsrc_anchor | 0.4855 | 0.2728 | 0.0001 | 0.5034 | 0.6548 | 0.6678 | 0.5464 | 0.6553 | 0.6553 | 0.4536 | 0.8929 | 0.9993 | 0.8328 | 0.9993 | 0.9986 | 0.9156 | 0.9920 | 2.9872 | 0.0001 | 0.1392 |
| test | camc_sempc_candidate | 0.4744 | 0.2536 | 0.0001 | 0.4535 | 0.6799 | 0.7160 | 0.5512 | 0.6803 | 0.6803 | 0.4506 | 0.7889 | 0.9997 | 0.8099 | 0.9997 | 0.9997 | 0.9604 | 0.9924 | 2.9368 | 0.0001 | 0.1161 |
| test | camc_static_anchor | 0.4833 | 0.2782 | 0.0001 | 0.5964 | 0.6901 | 0.7107 | 0.5964 | 0.6902 | 0.6902 | 0.4036 | 0.8947 | 0.9997 | 0.8636 | 0.9997 | 0.9996 | 0.9545 | 0.9904 | 2.8957 | 0.0001 | 0.1370 |
| test | greedy_myopic | 0.4597 | 0.2299 | 0.0005 | 0.2926 | 0.4298 | 0.5676 | 0.4560 | 0.5755 | 0.5755 | 0.0000 | 0.7741 | 0.9997 | 0.7914 | 0.9997 | 1.0000 | 0.9848 | 0.9933 | 5.7426 | 0.0001 | 0.1433 |
| test | headroom_only | 0.4862 | 0.2750 | 0.0001 | 0.5647 | 0.6568 | 0.6594 | 0.5647 | 0.6574 | 0.6574 | 0.4353 | 0.8937 | 0.9994 | 0.8582 | 0.9994 | 0.9985 | 0.9124 | 0.9911 | 2.9730 | 0.0002 | 0.1474 |
| test | maxweight_backlog | 0.4848 | 0.2793 | 0.0001 | 0.5956 | 0.6917 | 0.7025 | 0.5956 | 0.6920 | 0.6920 | 0.0000 | 0.8949 | 0.9996 | 0.8599 | 0.9996 | 0.9992 | 0.9393 | 0.9901 | 2.9078 | 0.0001 | 0.1277 |
| test | minimal_verify | 0.4651 | 0.0303 | 0.0054 | 0.0008 | 0.0017 | 0.0017 | 0.0008 | 0.0017 | 0.0017 | 0.0000 | 0.0000 | 1.0000 | 0.4844 | 1.0000 | 1.0000 | 1.0000 | 0.9343 | 1199.0312 | 0.0010 | 0.0000 |
| test | oracle_src | 0.4493 | 0.1845 | 0.0004 | 0.5191 | 0.5191 | 0.6761 | 0.5191 | 0.5191 | 0.5191 | 0.0000 | 0.5593 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.9442 | 0.9878 | 3.4226 | 0.0002 | 0.0360 |
| test | pareto_camc_rsrc_anchor | 0.4858 | 0.2769 | 0.0001 | 0.5630 | 0.6633 | 0.6687 | 0.5630 | 0.6637 | 0.6637 | 0.4370 | 0.8940 | 0.9995 | 0.8475 | 0.9995 | 0.9988 | 0.9190 | 0.9911 | 2.9671 | 0.0001 | 0.1419 |
| test | pareto_camc_sempc_candidate | 0.4875 | 0.3034 | 0.0001 | 0.5644 | 0.6691 | 0.6766 | 0.5755 | 0.6692 | 0.6692 | 0.4268 | 0.9313 | 0.9992 | 0.8592 | 0.9992 | 0.9994 | 0.9310 | 0.9912 | 2.8938 | 0.0000 | 0.1329 |
| test | pareto_camc_static_anchor | 0.4831 | 0.2832 | 0.0001 | 0.6855 | 0.7674 | 0.7886 | 0.6855 | 0.7674 | 0.7674 | 0.3145 | 0.8983 | 0.9996 | 0.8927 | 0.9996 | 0.9996 | 0.9789 | 0.9879 | 2.7459 | 0.0001 | 0.0997 |
| test | plain_mpc | 0.4549 | 0.1075 | 0.0012 | 0.0058 | 0.0371 | 0.1316 | 0.0204 | 0.0689 | 0.0689 | 0.0000 | 0.2511 | 1.0000 | 0.2925 | 1.0000 | 1.0000 | 1.0000 | 0.9880 | 279.0787 | 0.0007 | 0.0036 |
| test | rsrc | 0.4858 | 0.2769 | 0.0001 | 0.5630 | 0.6633 | 0.6687 | 0.5630 | 0.6637 | 0.6637 | 0.4370 | 0.8940 | 0.9995 | 0.8475 | 0.9995 | 0.9988 | 0.9190 | 0.9911 | 2.9671 | 0.0001 | 0.1419 |
| test | rsrc_no_context | 0.4859 | 0.2752 | 0.0001 | 0.5611 | 0.6608 | 0.6651 | 0.5611 | 0.6612 | 0.6612 | 0.4389 | 0.8939 | 0.9995 | 0.8478 | 0.9995 | 0.9987 | 0.9171 | 0.9912 | 2.9837 | 0.0002 | 0.1466 |
| test | rsrc_no_recovery | 0.4861 | 0.2767 | 0.0001 | 0.5669 | 0.6592 | 0.6627 | 0.5669 | 0.6597 | 0.6597 | 0.4331 | 0.8938 | 0.9994 | 0.8584 | 0.9994 | 0.9985 | 0.9138 | 0.9910 | 2.9571 | 0.0001 | 0.1427 |
| test | se_mpc | 0.4854 | 0.2803 | 0.0001 | 0.5615 | 0.6670 | 0.6750 | 0.5655 | 0.6673 | 0.6673 | 0.4345 | 0.8941 | 0.9994 | 0.8466 | 0.9994 | 0.9988 | 0.9211 | 0.9910 | 2.8810 | 0.0001 | 0.1297 |
| test | static_aggressive | 0.4928 | 0.2703 | 0.0004 | 0.2864 | 0.3681 | 0.4678 | 0.4039 | 0.4777 | 0.4777 | 0.0000 | 0.8888 | 0.9998 | 0.8449 | 0.9998 | 1.0000 | 0.9615 | 0.9941 | 6.0625 | 0.0001 | 0.2168 |
| test | static_conservative | 0.4831 | 0.2832 | 0.0001 | 0.6855 | 0.7674 | 0.7886 | 0.6855 | 0.7674 | 0.7674 | 0.0000 | 0.8983 | 0.9996 | 0.8927 | 0.9996 | 0.9996 | 0.9789 | 0.9879 | 2.7459 | 0.0001 | 0.0997 |
| verified | adaptive_threshold | 0.4370 | 0.2012 | 0.0000 | 0.4102 | 0.6679 | 0.7857 | 0.4102 | 0.6679 | 0.6679 | 0.0000 | 0.6095 | 1.0000 | 0.6119 | 1.0000 | 1.0000 | 0.9955 | 0.9920 | 4.4050 | 0.0002 | 0.0007 |
| verified | always_verify | 0.5155 | 0.3690 | 0.0000 | 0.2290 | 0.3008 | 0.3834 | 0.2290 | 0.3008 | 0.3008 | 0.0000 | 1.0000 | 0.9998 | 0.7596 | 0.9998 | 0.9998 | 0.7154 | 0.9951 | 6.1565 | 0.0000 | 0.0165 |
| verified | always_verify_throttle | 0.5145 | 0.3703 | 0.0000 | 0.2651 | 0.3400 | 0.4233 | 0.2651 | 0.3401 | 0.3401 | 0.0000 | 1.0000 | 1.0000 | 0.7773 | 1.0000 | 0.9995 | 0.8040 | 0.9948 | 6.1524 | 0.0000 | 0.0156 |
| verified | camc_rsrc_anchor | 0.4742 | 0.2784 | 0.0000 | 0.5271 | 0.7081 | 0.7081 | 0.5629 | 0.7081 | 0.7081 | 0.4371 | 0.8880 | 1.0000 | 0.7947 | 1.0000 | 1.0000 | 0.9399 | 0.9923 | 2.9138 | 0.0001 | 0.0051 |
| verified | camc_sempc_candidate | 0.4615 | 0.2564 | 0.0000 | 0.4359 | 0.7241 | 0.7494 | 0.5473 | 0.7241 | 0.7241 | 0.4532 | 0.7804 | 1.0000 | 0.7553 | 1.0000 | 1.0000 | 0.9725 | 0.9930 | 2.9631 | 0.0001 | 0.0050 |
| verified | camc_static_anchor | 0.4715 | 0.2859 | 0.0000 | 0.6580 | 0.7748 | 0.7812 | 0.6580 | 0.7748 | 0.7748 | 0.3420 | 0.8915 | 1.0000 | 0.8492 | 1.0000 | 1.0000 | 0.9773 | 0.9895 | 2.6911 | 0.0001 | 0.0036 |
| verified | greedy_myopic | 0.4512 | 0.2177 | 0.0000 | 0.2199 | 0.4248 | 0.5827 | 0.3921 | 0.5794 | 0.5794 | 0.0000 | 0.7044 | 0.9999 | 0.6735 | 0.9999 | 1.0000 | 0.9931 | 0.9943 | 8.0056 | 0.0001 | 0.0045 |
| verified | headroom_only | 0.4748 | 0.2821 | 0.0000 | 0.5913 | 0.7134 | 0.7033 | 0.5913 | 0.7134 | 0.7134 | 0.4087 | 0.8892 | 1.0000 | 0.8285 | 1.0000 | 1.0000 | 0.9401 | 0.9910 | 2.8601 | 0.0001 | 0.0043 |
| verified | maxweight_backlog | 0.4735 | 0.2851 | 0.0000 | 0.6187 | 0.7467 | 0.7397 | 0.6187 | 0.7468 | 0.7468 | 0.0000 | 0.8907 | 1.0000 | 0.8284 | 1.0000 | 0.9999 | 0.9524 | 0.9904 | 2.7390 | 0.0001 | 0.0036 |
| verified | minimal_verify | 0.4580 | 0.0289 | 0.0000 | 0.0021 | 0.0040 | 0.0040 | 0.0021 | 0.0040 | 0.0040 | 0.0000 | 0.0000 | 1.0000 | 0.5312 | 1.0000 | 1.0000 | 1.0000 | 0.9453 | 491.1406 | 0.0014 | 0.0000 |
| verified | oracle_src | 0.4408 | 0.1711 | 0.0000 | 0.3925 | 0.3925 | 0.5701 | 0.3925 | 0.3925 | 0.3925 | 0.0000 | 0.4588 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.9648 | 0.9907 | 5.3750 | 0.0003 | 0.0002 |
| verified | pareto_camc_rsrc_anchor | 0.4744 | 0.2828 | 0.0000 | 0.5847 | 0.7198 | 0.7114 | 0.5847 | 0.7198 | 0.7198 | 0.4153 | 0.8894 | 1.0000 | 0.8121 | 1.0000 | 1.0000 | 0.9419 | 0.9912 | 2.8198 | 0.0001 | 0.0043 |
| verified | pareto_camc_sempc_candidate | 0.4761 | 0.3078 | 0.0000 | 0.6206 | 0.7383 | 0.7322 | 0.6210 | 0.7383 | 0.7383 | 0.3796 | 0.9363 | 0.9999 | 0.8408 | 0.9999 | 0.9999 | 0.9566 | 0.9904 | 2.7578 | 0.0000 | 0.0037 |
| verified | pareto_camc_static_anchor | 0.4713 | 0.2898 | 0.0000 | 0.7007 | 0.8083 | 0.8177 | 0.7007 | 0.8083 | 0.8083 | 0.2993 | 0.8946 | 0.9999 | 0.8667 | 0.9999 | 0.9999 | 0.9865 | 0.9883 | 2.6055 | 0.0001 | 0.0023 |
| verified | plain_mpc | 0.4472 | 0.1144 | 0.0000 | 0.0097 | 0.0645 | 0.1539 | 0.0239 | 0.0979 | 0.0979 | 0.0000 | 0.2345 | 1.0000 | 0.2391 | 1.0000 | 1.0000 | 1.0000 | 0.9899 | 223.3084 | 0.0009 | 0.0000 |
| verified | rsrc | 0.4744 | 0.2828 | 0.0000 | 0.5847 | 0.7198 | 0.7114 | 0.5847 | 0.7198 | 0.7198 | 0.4153 | 0.8894 | 1.0000 | 0.8121 | 1.0000 | 1.0000 | 0.9419 | 0.9912 | 2.8198 | 0.0001 | 0.0043 |
| verified | rsrc_no_context | 0.4745 | 0.2823 | 0.0000 | 0.5843 | 0.7191 | 0.7105 | 0.5843 | 0.7191 | 0.7191 | 0.4157 | 0.8893 | 1.0000 | 0.8123 | 1.0000 | 1.0000 | 0.9415 | 0.9912 | 2.8204 | 0.0001 | 0.0043 |
| verified | rsrc_no_recovery | 0.4748 | 0.2825 | 0.0000 | 0.5915 | 0.7137 | 0.7041 | 0.5915 | 0.7137 | 0.7137 | 0.4085 | 0.8893 | 1.0000 | 0.8284 | 1.0000 | 1.0000 | 0.9407 | 0.9910 | 2.8590 | 0.0001 | 0.0043 |
| verified | se_mpc | 0.4737 | 0.2833 | 0.0000 | 0.5819 | 0.7201 | 0.7120 | 0.5843 | 0.7201 | 0.7201 | 0.4157 | 0.8891 | 1.0000 | 0.8112 | 1.0000 | 1.0000 | 0.9418 | 0.9913 | 2.8099 | 0.0001 | 0.0043 |
| verified | static_aggressive | 0.4814 | 0.2752 | 0.0000 | 0.2908 | 0.4038 | 0.4989 | 0.4163 | 0.5195 | 0.5195 | 0.0000 | 0.8855 | 1.0000 | 0.8003 | 1.0000 | 1.0000 | 0.9712 | 0.9947 | 5.9377 | 0.0001 | 0.0153 |
| verified | static_conservative | 0.4713 | 0.2898 | 0.0000 | 0.7007 | 0.8083 | 0.8177 | 0.7007 | 0.8083 | 0.8083 | 0.0000 | 0.8946 | 0.9999 | 0.8667 | 0.9999 | 0.9999 | 0.9865 | 0.9883 | 2.6055 | 0.0001 | 0.0023 |

## Online Dynamic Baselines

| dataset | controller | operating_cost_proxy | safety_augmented_cost | success_rate | overload_rate | verification_rate | fallback_rate | negative_drift_rate_outside_safe | avg_return_time_to_safe |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| rebench | adaptive_threshold | 0.4469 | 1.1256 | 0.2021 | 0.0005 | 0.5528 | 0.0000 | 0.9754 | 3.6843 |
| rebench | always_verify_throttle | 0.5217 | 1.2640 | 0.3641 | 0.0001 | 1.0000 | 0.0000 | 0.9865 | 6.2461 |
| rebench | camc_rsrc_anchor | 0.4797 | 1.1880 | 0.2604 | 0.0002 | 0.7044 | 0.4526 | 0.9778 | 2.8877 |
| rebench | camc_sempc_candidate | 0.4696 | 1.1659 | 0.2442 | 0.0002 | 0.6536 | 0.4657 | 0.9789 | 2.9460 |
| rebench | camc_static_anchor | 0.4762 | 1.1698 | 0.2705 | 0.0001 | 0.7228 | 0.3599 | 0.9709 | 2.5180 |
| rebench | headroom_only | 0.4803 | 1.1929 | 0.2653 | 0.0002 | 0.7198 | 0.4210 | 0.9745 | 2.7352 |
| rebench | maxweight_backlog | 0.4790 | 1.1727 | 0.2689 | 0.0002 | 0.7214 | 0.0000 | 0.9727 | 2.6451 |
| rebench | minimal_verify | 0.4876 | 1.2540 | 0.0311 | 0.0198 | 0.0000 | 0.0000 | 0.8731 | 1180.2031 |
| rebench | pareto_camc_rsrc_anchor | 0.4799 | 1.1880 | 0.2664 | 0.0002 | 0.7200 | 0.4248 | 0.9744 | 2.7241 |
| rebench | pareto_camc_sempc_candidate | 0.4795 | 1.1599 | 0.2933 | 0.0001 | 0.7814 | 0.3753 | 0.9727 | 2.5669 |
| rebench | pareto_camc_static_anchor | 0.4762 | 1.1354 | 0.2739 | 0.0001 | 0.7255 | 0.3102 | 0.9667 | 2.4249 |
| rebench | plain_mpc | 0.4587 | 1.1470 | 0.0974 | 0.0024 | 0.3228 | 0.0000 | 0.9705 | 386.7825 |
| rebench | rsrc | 0.4799 | 1.1880 | 0.2664 | 0.0002 | 0.7200 | 0.4248 | 0.9744 | 2.7241 |
| rebench | rsrc_no_context | 0.4800 | 1.1914 | 0.2655 | 0.0002 | 0.7199 | 0.4253 | 0.9748 | 2.7312 |
| rebench | rsrc_no_recovery | 0.4803 | 1.1893 | 0.2662 | 0.0002 | 0.7198 | 0.4202 | 0.9741 | 2.7320 |
| rebench | se_mpc | 0.4791 | 1.1704 | 0.2690 | 0.0002 | 0.7200 | 0.4242 | 0.9736 | 2.6586 |
| rebench | static_conservative | 0.4762 | 1.1354 | 0.2739 | 0.0001 | 0.7255 | 0.0000 | 0.9667 | 2.4249 |
| smith | adaptive_threshold | 0.5582 | 1.4015 | 0.2287 | 0.0174 | 0.8363 | 0.0000 | 0.8217 | 5.6560 |
| smith | always_verify_throttle | 0.5987 | 1.4881 | 0.2812 | 0.0176 | 1.0000 | 0.0000 | 0.8538 | 15.5207 |
| smith | camc_rsrc_anchor | 0.5862 | 1.4457 | 0.2474 | 0.0178 | 0.8942 | 0.8276 | 0.8422 | 8.9459 |
| smith | camc_sempc_candidate | 0.5862 | 1.4452 | 0.2480 | 0.0178 | 0.8952 | 0.8287 | 0.8421 | 8.9252 |
| smith | camc_static_anchor | 0.5890 | 1.4376 | 0.2615 | 0.0173 | 0.9314 | 0.8230 | 0.8390 | 8.4725 |
| smith | headroom_only | 0.5900 | 1.4570 | 0.2605 | 0.0175 | 0.9309 | 0.8440 | 0.8422 | 8.8437 |
| smith | maxweight_backlog | 0.5896 | 1.4511 | 0.2609 | 0.0174 | 0.9312 | 0.0000 | 0.8420 | 8.8294 |
| smith | minimal_verify | 12.4593 | 15.1683 | 0.0198 | 0.9869 | 0.0000 | 0.0000 | 0.0108 | 1199.3438 |
| smith | pareto_camc_rsrc_anchor | 0.5891 | 1.4435 | 0.2629 | 0.0174 | 0.9374 | 0.8332 | 0.8407 | 8.6282 |
| smith | pareto_camc_sempc_candidate | 0.5891 | 1.4421 | 0.2627 | 0.0174 | 0.9364 | 0.8316 | 0.8403 | 8.5709 |
| smith | pareto_camc_static_anchor | 0.5890 | 1.4374 | 0.2615 | 0.0173 | 0.9314 | 0.8228 | 0.8389 | 8.4710 |
| smith | plain_mpc | 0.6736 | 1.6767 | 0.1214 | 0.1365 | 0.5596 | 0.0000 | 0.7462 | 38.4334 |
| smith | rsrc | 0.5898 | 1.4562 | 0.2605 | 0.0175 | 0.9310 | 0.8473 | 0.8429 | 8.9831 |
| smith | rsrc_no_context | 0.5898 | 1.4563 | 0.2605 | 0.0175 | 0.9310 | 0.8473 | 0.8429 | 8.9859 |
| smith | rsrc_no_recovery | 0.5900 | 1.4569 | 0.2605 | 0.0175 | 0.9309 | 0.8440 | 0.8422 | 8.8413 |
| smith | se_mpc | 0.5898 | 1.4541 | 0.2609 | 0.0176 | 0.9310 | 0.8470 | 0.8424 | 8.9452 |
| smith | static_conservative | 0.5890 | 1.4374 | 0.2615 | 0.0173 | 0.9314 | 0.0000 | 0.8389 | 8.4710 |
| test | adaptive_threshold | 0.4456 | 1.0940 | 0.2161 | 0.0003 | 0.5962 | 0.0000 | 0.9894 | 2.9516 |
| test | always_verify_throttle | 0.5201 | 1.2179 | 0.3595 | 0.0000 | 1.0000 | 0.0000 | 0.9948 | 6.4197 |
| test | camc_rsrc_anchor | 0.4855 | 1.1565 | 0.2728 | 0.0001 | 0.7466 | 0.4536 | 0.9920 | 2.9872 |
| test | camc_sempc_candidate | 0.4744 | 1.1389 | 0.2536 | 0.0001 | 0.6856 | 0.4506 | 0.9924 | 2.9368 |
| test | camc_static_anchor | 0.4833 | 1.1481 | 0.2782 | 0.0001 | 0.7590 | 0.4036 | 0.9904 | 2.8957 |
| test | headroom_only | 0.4862 | 1.1627 | 0.2750 | 0.0001 | 0.7577 | 0.4353 | 0.9911 | 2.9730 |
| test | maxweight_backlog | 0.4848 | 1.1404 | 0.2793 | 0.0001 | 0.7592 | 0.0000 | 0.9901 | 2.9078 |
| test | minimal_verify | 0.4651 | 1.2032 | 0.0303 | 0.0054 | 0.0000 | 0.0000 | 0.9343 | 1199.0312 |
| test | pareto_camc_rsrc_anchor | 0.4858 | 1.1561 | 0.2769 | 0.0001 | 0.7579 | 0.4370 | 0.9911 | 2.9671 |
| test | pareto_camc_sempc_candidate | 0.4875 | 1.1298 | 0.3034 | 0.0001 | 0.8172 | 0.4268 | 0.9912 | 2.8938 |
| test | pareto_camc_static_anchor | 0.4831 | 1.1106 | 0.2832 | 0.0001 | 0.7630 | 0.3145 | 0.9879 | 2.7459 |
| test | plain_mpc | 0.4549 | 1.1299 | 0.1075 | 0.0012 | 0.3595 | 0.0000 | 0.9880 | 279.0787 |
| test | rsrc | 0.4858 | 1.1561 | 0.2769 | 0.0001 | 0.7579 | 0.4370 | 0.9911 | 2.9671 |
| test | rsrc_no_context | 0.4859 | 1.1615 | 0.2752 | 0.0001 | 0.7579 | 0.4389 | 0.9912 | 2.9837 |
| test | rsrc_no_recovery | 0.4861 | 1.1572 | 0.2767 | 0.0001 | 0.7578 | 0.4331 | 0.9910 | 2.9571 |
| test | se_mpc | 0.4854 | 1.1422 | 0.2803 | 0.0001 | 0.7581 | 0.4345 | 0.9910 | 2.8810 |
| test | static_conservative | 0.4831 | 1.1106 | 0.2832 | 0.0001 | 0.7630 | 0.0000 | 0.9879 | 2.7459 |
| verified | adaptive_threshold | 0.4370 | 1.0367 | 0.2012 | 0.0000 | 0.5416 | 0.0000 | 0.9920 | 4.4050 |
| verified | always_verify_throttle | 0.5145 | 1.0008 | 0.3703 | 0.0000 | 1.0000 | 0.0000 | 0.9948 | 6.1524 |
| verified | camc_rsrc_anchor | 0.4742 | 1.0200 | 0.2784 | 0.0000 | 0.7377 | 0.4371 | 0.9923 | 2.9138 |
| verified | camc_sempc_candidate | 0.4615 | 1.0236 | 0.2564 | 0.0000 | 0.6724 | 0.4532 | 0.9930 | 2.9631 |
| verified | camc_static_anchor | 0.4715 | 1.0104 | 0.2859 | 0.0000 | 0.7513 | 0.3420 | 0.9895 | 2.6911 |
| verified | headroom_only | 0.4748 | 1.0172 | 0.2821 | 0.0000 | 0.7479 | 0.4087 | 0.9910 | 2.8601 |
| verified | maxweight_backlog | 0.4735 | 1.0129 | 0.2851 | 0.0000 | 0.7496 | 0.0000 | 0.9904 | 2.7390 |
| verified | minimal_verify | 0.4580 | 1.1863 | 0.0289 | 0.0000 | 0.0000 | 0.0000 | 0.9453 | 491.1406 |
| verified | pareto_camc_rsrc_anchor | 0.4744 | 1.0162 | 0.2828 | 0.0000 | 0.7480 | 0.4153 | 0.9912 | 2.8198 |
| verified | pareto_camc_sempc_candidate | 0.4761 | 0.9986 | 0.3078 | 0.0000 | 0.8126 | 0.3796 | 0.9904 | 2.7578 |
| verified | pareto_camc_static_anchor | 0.4713 | 1.0061 | 0.2898 | 0.0000 | 0.7546 | 0.2993 | 0.9883 | 2.6055 |
| verified | plain_mpc | 0.4472 | 1.1115 | 0.1144 | 0.0000 | 0.3510 | 0.0000 | 0.9899 | 223.3084 |
| verified | rsrc | 0.4744 | 1.0162 | 0.2828 | 0.0000 | 0.7480 | 0.4153 | 0.9912 | 2.8198 |
| verified | rsrc_no_context | 0.4745 | 1.0166 | 0.2823 | 0.0000 | 0.7480 | 0.4157 | 0.9912 | 2.8204 |
| verified | rsrc_no_recovery | 0.4748 | 1.0168 | 0.2825 | 0.0000 | 0.7479 | 0.4085 | 0.9910 | 2.8590 |
| verified | se_mpc | 0.4737 | 1.0151 | 0.2833 | 0.0000 | 0.7477 | 0.4157 | 0.9913 | 2.8099 |
| verified | static_conservative | 0.4713 | 1.0061 | 0.2898 | 0.0000 | 0.7546 | 0.0000 | 0.9883 | 2.6055 |

## Online Pairwise

| dataset | metric | se_mpc_minus_rsrc | ci_low | ci_high |
| --- | --- | --- | --- | --- |
| rebench | discounted_cost | -0.0008 | -0.0011 | -0.0006 |
| rebench | success_rate | 0.0026 | 0.0021 | 0.0032 |
| rebench | overload_rate | 0.0000 | -0.0001 | 0.0001 |
| rebench | safe_occupancy_rate | -0.0028 | -0.0041 | -0.0015 |
| rebench | benchmark_action_safe_occupancy_rate | 0.0013 | 0.0003 | 0.0025 |
| rebench | benchmark_safe_occupancy_rate | 0.0047 | 0.0035 | 0.0059 |
| rebench | fallback_rate | -0.0007 | -0.0020 | 0.0006 |
| rebench | high_effort_rate | -0.0001 | -0.0003 | 0.0001 |
| rebench | theta_benchmark_precision | -0.0000 | -0.0001 | 0.0001 |
| rebench | theta_nesting_precision | -0.0000 | -0.0001 | 0.0001 |
| rebench | action_safe_precision | 0.0002 | -0.0001 | 0.0006 |
| rebench | safe_event_precision | 0.0018 | 0.0006 | 0.0032 |
| rebench | negative_drift_rate_outside_safe | -0.0007 | -0.0014 | -0.0002 |
| rebench | avg_return_time_to_safe | -0.0655 | -0.0808 | -0.0519 |
| smith | discounted_cost | -0.0000 | -0.0002 | 0.0002 |
| smith | success_rate | 0.0004 | 0.0002 | 0.0007 |
| smith | overload_rate | 0.0001 | 0.0000 | 0.0001 |
| smith | safe_occupancy_rate | 0.0002 | -0.0003 | 0.0007 |
| smith | benchmark_action_safe_occupancy_rate | 0.0003 | -0.0001 | 0.0009 |
| smith | benchmark_safe_occupancy_rate | 0.0004 | 0.0001 | 0.0007 |
| smith | fallback_rate | -0.0003 | -0.0008 | 0.0001 |
| smith | high_effort_rate | 0.0000 | 0.0000 | 0.0000 |
| smith | theta_benchmark_precision | 0.0001 | -0.0004 | 0.0007 |
| smith | theta_nesting_precision | 0.0001 | -0.0004 | 0.0007 |
| smith | action_safe_precision | 0.0003 | -0.0003 | 0.0010 |
| smith | safe_event_precision | 0.0003 | -0.0013 | 0.0015 |
| smith | negative_drift_rate_outside_safe | -0.0005 | -0.0007 | -0.0003 |
| smith | avg_return_time_to_safe | -0.0379 | -0.0744 | -0.0036 |
| test | discounted_cost | -0.0003 | -0.0006 | -0.0001 |
| test | success_rate | 0.0034 | 0.0029 | 0.0041 |
| test | overload_rate | 0.0000 | -0.0001 | 0.0001 |
| test | safe_occupancy_rate | -0.0015 | -0.0030 | 0.0003 |
| test | benchmark_action_safe_occupancy_rate | 0.0037 | 0.0026 | 0.0049 |
| test | benchmark_safe_occupancy_rate | 0.0063 | 0.0053 | 0.0074 |
| test | fallback_rate | -0.0025 | -0.0040 | -0.0010 |
| test | high_effort_rate | 0.0001 | -0.0001 | 0.0003 |
| test | theta_benchmark_precision | -0.0001 | -0.0003 | 0.0002 |
| test | theta_nesting_precision | -0.0001 | -0.0003 | 0.0002 |
| test | action_safe_precision | 0.0000 | -0.0003 | 0.0004 |
| test | safe_event_precision | 0.0021 | 0.0009 | 0.0033 |
| test | negative_drift_rate_outside_safe | -0.0001 | -0.0003 | 0.0001 |
| test | avg_return_time_to_safe | -0.0860 | -0.1006 | -0.0734 |
| verified | discounted_cost | -0.0007 | -0.0011 | -0.0003 |
| verified | success_rate | 0.0006 | 0.0002 | 0.0010 |
| verified | overload_rate | 0.0000 | 0.0000 | 0.0000 |
| verified | safe_occupancy_rate | -0.0027 | -0.0042 | -0.0016 |
| verified | benchmark_action_safe_occupancy_rate | 0.0004 | -0.0001 | 0.0010 |
| verified | benchmark_safe_occupancy_rate | 0.0006 | 0.0001 | 0.0011 |
| verified | fallback_rate | 0.0004 | -0.0006 | 0.0016 |
| verified | high_effort_rate | -0.0003 | -0.0007 | 0.0000 |
| verified | theta_benchmark_precision | 0.0000 | 0.0000 | 0.0000 |
| verified | theta_nesting_precision | 0.0000 | 0.0000 | 0.0000 |
| verified | action_safe_precision | 0.0000 | 0.0000 | 0.0000 |
| verified | safe_event_precision | -0.0001 | -0.0012 | 0.0009 |
| verified | negative_drift_rate_outside_safe | 0.0001 | 0.0000 | 0.0001 |
| verified | avg_return_time_to_safe | -0.0099 | -0.0226 | 0.0055 |

## Online Pairwise With Confidence Intervals

| dataset | metric | estimate [95% CI] |
| --- | --- | --- |
| rebench | discounted_cost | -0.0008 [-0.0011, -0.0006] |
| rebench | success_rate | 0.0026 [0.0021, 0.0032] |
| rebench | safe_event_precision | 0.0018 [0.0006, 0.0032] |
| rebench | avg_return_time_to_safe | -0.0655 [-0.0808, -0.0519] |
| smith | discounted_cost | -0.0000 [-0.0002, 0.0002] |
| smith | success_rate | 0.0004 [0.0002, 0.0007] |
| smith | safe_event_precision | 0.0003 [-0.0013, 0.0015] |
| smith | avg_return_time_to_safe | -0.0379 [-0.0744, -0.0036] |
| test | discounted_cost | -0.0003 [-0.0006, -0.0001] |
| test | success_rate | 0.0034 [0.0029, 0.0041] |
| test | safe_event_precision | 0.0021 [0.0009, 0.0033] |
| test | avg_return_time_to_safe | -0.0860 [-0.1006, -0.0734] |
| verified | discounted_cost | -0.0007 [-0.0011, -0.0003] |
| verified | success_rate | 0.0006 [0.0002, 0.0010] |
| verified | safe_event_precision | -0.0001 [-0.0012, 0.0009] |
| verified | avg_return_time_to_safe | -0.0099 [-0.0226, 0.0055] |

## Safety-Augmented Online Objectives

| dataset | controller | profile | estimate [95% CI] |
| --- | --- | --- | --- |
| rebench | adaptive_threshold | low | 0.6776 [0.6719, 0.6828] |
| rebench | adaptive_threshold | medium | 1.1256 [1.1162, 1.1343] |
| rebench | adaptive_threshold | high | 1.8004 [1.7851, 1.8145] |
| rebench | always_verify_throttle | low | 0.7839 [0.7782, 0.7892] |
| rebench | always_verify_throttle | medium | 1.2640 [1.2524, 1.2752] |
| rebench | always_verify_throttle | high | 1.9916 [1.9690, 2.0118] |
| rebench | camc_rsrc_anchor | low | 0.7243 [0.7197, 0.7281] |
| rebench | camc_rsrc_anchor | medium | 1.1880 [1.1795, 1.1953] |
| rebench | camc_rsrc_anchor | high | 1.8880 [1.8729, 1.9014] |
| rebench | camc_sempc_candidate | low | 0.7089 [0.7034, 0.7137] |
| rebench | camc_sempc_candidate | medium | 1.1659 [1.1563, 1.1749] |
| rebench | camc_sempc_candidate | high | 1.8553 [1.8375, 1.8700] |
| rebench | camc_static_anchor | low | 0.7155 [0.7107, 0.7195] |
| rebench | camc_static_anchor | medium | 1.1698 [1.1609, 1.1775] |
| rebench | camc_static_anchor | high | 1.8555 [1.8394, 1.8689] |
| rebench | headroom_only | low | 0.7268 [0.7222, 0.7308] |
| rebench | headroom_only | medium | 1.1929 [1.1840, 1.2005] |
| rebench | headroom_only | high | 1.8966 [1.8806, 1.9101] |
| rebench | maxweight_backlog | low | 0.7183 [0.7136, 0.7222] |
| rebench | maxweight_backlog | medium | 1.1727 [1.1641, 1.1806] |
| rebench | maxweight_backlog | high | 1.8585 [1.8425, 1.8725] |
| rebench | minimal_verify | low | 0.7447 [0.7331, 0.7567] |
| rebench | minimal_verify | medium | 1.2540 [1.2387, 1.2702] |
| rebench | minimal_verify | high | 2.0401 [2.0106, 2.0687] |
| rebench | pareto_camc_rsrc_anchor | low | 0.7247 [0.7201, 0.7285] |
| rebench | pareto_camc_rsrc_anchor | medium | 1.1880 [1.1792, 1.1955] |
| rebench | pareto_camc_rsrc_anchor | high | 1.8874 [1.8719, 1.9010] |
| rebench | pareto_camc_sempc_candidate | low | 0.7147 [0.7099, 0.7186] |
| rebench | pareto_camc_sempc_candidate | medium | 1.1599 [1.1502, 1.1678] |
| rebench | pareto_camc_sempc_candidate | high | 1.8321 [1.8142, 1.8465] |
| rebench | pareto_camc_static_anchor | low | 0.7023 [0.6972, 0.7065] |
| rebench | pareto_camc_static_anchor | medium | 1.1354 [1.1260, 1.1433] |
| rebench | pareto_camc_static_anchor | high | 1.7884 [1.7716, 1.8026] |
| rebench | plain_mpc | low | 0.6887 [0.6839, 0.6936] |
| rebench | plain_mpc | medium | 1.1470 [1.1407, 1.1524] |
| rebench | plain_mpc | high | 1.8373 [1.8283, 1.8447] |
| rebench | rsrc | low | 0.7247 [0.7201, 0.7285] |
| rebench | rsrc | medium | 1.1880 [1.1792, 1.1955] |
| rebench | rsrc | high | 1.8874 [1.8719, 1.9010] |
| rebench | rsrc_no_context | low | 0.7261 [0.7214, 0.7300] |
| rebench | rsrc_no_context | medium | 1.1914 [1.1827, 1.1990] |
| rebench | rsrc_no_context | high | 1.8942 [1.8778, 1.9077] |
| rebench | rsrc_no_recovery | low | 0.7254 [0.7208, 0.7293] |
| rebench | rsrc_no_recovery | medium | 1.1893 [1.1806, 1.1969] |
| rebench | rsrc_no_recovery | high | 1.8898 [1.8745, 1.9032] |
| rebench | se_mpc | low | 0.7174 [0.7123, 0.7216] |
| rebench | se_mpc | medium | 1.1704 [1.1609, 1.1786] |
| rebench | se_mpc | high | 1.8539 [1.8367, 1.8680] |
| rebench | static_conservative | low | 0.7023 [0.6972, 0.7065] |
| rebench | static_conservative | medium | 1.1354 [1.1260, 1.1433] |
| rebench | static_conservative | high | 1.7884 [1.7716, 1.8026] |
| smith | adaptive_threshold | low | 0.8536 [0.8424, 0.8657] |
| smith | adaptive_threshold | medium | 1.4015 [1.3854, 1.4191] |
| smith | adaptive_threshold | high | 2.2495 [2.2222, 2.2767] |
| smith | always_verify_throttle | low | 0.9141 [0.9021, 0.9264] |
| smith | always_verify_throttle | medium | 1.4881 [1.4699, 1.5049] |
| smith | always_verify_throttle | high | 2.3776 [2.3488, 2.4033] |
| smith | camc_rsrc_anchor | low | 0.8886 [0.8767, 0.9010] |
| smith | camc_rsrc_anchor | medium | 1.4457 [1.4285, 1.4622] |
| smith | camc_rsrc_anchor | high | 2.3086 [2.2816, 2.3352] |
| smith | camc_sempc_candidate | low | 0.8884 [0.8764, 0.9010] |
| smith | camc_sempc_candidate | medium | 1.4452 [1.4280, 1.4620] |
| smith | camc_sempc_candidate | high | 2.3076 [2.2798, 2.3345] |
| smith | camc_static_anchor | low | 0.8877 [0.8762, 0.9003] |
| smith | camc_static_anchor | medium | 1.4376 [1.4202, 1.4546] |
| smith | camc_static_anchor | high | 2.2892 [2.2617, 2.3158] |
| smith | headroom_only | low | 0.8959 [0.8846, 0.9083] |
| smith | headroom_only | medium | 1.4570 [1.4404, 1.4743] |
| smith | headroom_only | high | 2.3262 [2.2998, 2.3520] |
| smith | maxweight_backlog | low | 0.8933 [0.8818, 0.9058] |
| smith | maxweight_backlog | medium | 1.4511 [1.4344, 1.4681] |
| smith | maxweight_backlog | high | 2.3149 [2.2880, 2.3414] |
| smith | minimal_verify | low | 13.4445 [12.9670, 13.9747] |
| smith | minimal_verify | medium | 15.1683 [14.6891, 15.7006] |
| smith | minimal_verify | high | 18.8641 [18.3812, 19.4014] |
| smith | pareto_camc_rsrc_anchor | low | 0.8902 [0.8790, 0.9026] |
| smith | pareto_camc_rsrc_anchor | medium | 1.4435 [1.4267, 1.4604] |
| smith | pareto_camc_rsrc_anchor | high | 2.3006 [2.2730, 2.3270] |
| smith | pareto_camc_sempc_candidate | low | 0.8896 [0.8784, 0.9022] |
| smith | pareto_camc_sempc_candidate | medium | 1.4421 [1.4250, 1.4590] |
| smith | pareto_camc_sempc_candidate | high | 2.2977 [2.2699, 2.3248] |
| smith | pareto_camc_static_anchor | low | 0.8877 [0.8761, 0.9002] |
| smith | pareto_camc_static_anchor | medium | 1.4374 [1.4200, 1.4543] |
| smith | pareto_camc_static_anchor | high | 2.2888 [2.2613, 2.3153] |
| smith | plain_mpc | low | 1.0233 [0.8444, 1.3419] |
| smith | plain_mpc | medium | 1.6767 [1.4263, 2.0941] |
| smith | plain_mpc | high | 2.8122 [2.3780, 3.4788] |
| smith | rsrc | low | 0.8954 [0.8842, 0.9078] |
| smith | rsrc | medium | 1.4562 [1.4399, 1.4733] |
| smith | rsrc | high | 2.3247 [2.2985, 2.3504] |
| smith | rsrc_no_context | low | 0.8955 [0.8842, 0.9079] |
| smith | rsrc_no_context | medium | 1.4563 [1.4400, 1.4734] |
| smith | rsrc_no_context | high | 2.3249 [2.2987, 2.3507] |
| smith | rsrc_no_recovery | low | 0.8958 [0.8846, 0.9083] |
| smith | rsrc_no_recovery | medium | 1.4569 [1.4402, 1.4743] |
| smith | rsrc_no_recovery | high | 2.3260 [2.2996, 2.3518] |
| smith | se_mpc | low | 0.8946 [0.8834, 0.9070] |
| smith | se_mpc | medium | 1.4541 [1.4377, 1.4708] |
| smith | se_mpc | high | 2.3207 [2.2947, 2.3462] |
| smith | static_conservative | low | 0.8877 [0.8761, 0.9002] |
| smith | static_conservative | medium | 1.4374 [1.4200, 1.4543] |
| smith | static_conservative | high | 2.2888 [2.2613, 2.3153] |
| test | adaptive_threshold | low | 0.6651 [0.6597, 0.6695] |
| test | adaptive_threshold | medium | 1.0940 [1.0852, 1.1014] |
| test | adaptive_threshold | high | 1.7394 [1.7255, 1.7508] |
| test | always_verify_throttle | low | 0.7648 [0.7593, 0.7700] |
| test | always_verify_throttle | medium | 1.2179 [1.2060, 1.2286] |
| test | always_verify_throttle | high | 1.9036 [1.8819, 1.9246] |
| test | camc_rsrc_anchor | low | 0.7161 [0.7103, 0.7206] |
| test | camc_rsrc_anchor | medium | 1.1565 [1.1463, 1.1650] |
| test | camc_rsrc_anchor | high | 1.8206 [1.8028, 1.8355] |
| test | camc_sempc_candidate | low | 0.7017 [0.6956, 0.7069] |
| test | camc_sempc_candidate | medium | 1.1389 [1.1285, 1.1478] |
| test | camc_sempc_candidate | high | 1.7977 [1.7807, 1.8133] |
| test | camc_static_anchor | low | 0.7117 [0.7056, 0.7164] |
| test | camc_static_anchor | medium | 1.1481 [1.1371, 1.1569] |
| test | camc_static_anchor | high | 1.8062 [1.7875, 1.8218] |
| test | headroom_only | low | 0.7191 [0.7129, 0.7237] |
| test | headroom_only | medium | 1.1627 [1.1516, 1.1714] |
| test | headroom_only | high | 1.8319 [1.8130, 1.8474] |
| test | maxweight_backlog | low | 0.7097 [0.7036, 0.7145] |
| test | maxweight_backlog | medium | 1.1404 [1.1297, 1.1490] |
| test | maxweight_backlog | high | 1.7897 [1.7714, 1.8042] |
| test | minimal_verify | low | 0.7116 [0.7058, 0.7169] |
| test | minimal_verify | medium | 1.2032 [1.1956, 1.2101] |
| test | minimal_verify | high | 1.9467 [1.9346, 1.9592] |
| test | pareto_camc_rsrc_anchor | low | 0.7163 [0.7105, 0.7209] |
| test | pareto_camc_rsrc_anchor | medium | 1.1561 [1.1452, 1.1646] |
| test | pareto_camc_rsrc_anchor | high | 1.8194 [1.8012, 1.8350] |
| test | pareto_camc_sempc_candidate | low | 0.7083 [0.7026, 0.7127] |
| test | pareto_camc_sempc_candidate | medium | 1.1298 [1.1189, 1.1381] |
| test | pareto_camc_sempc_candidate | high | 1.7656 [1.7467, 1.7807] |
| test | pareto_camc_static_anchor | low | 0.6972 [0.6910, 0.7023] |
| test | pareto_camc_static_anchor | medium | 1.1106 [1.0995, 1.1197] |
| test | pareto_camc_static_anchor | high | 1.7331 [1.7142, 1.7485] |
| test | plain_mpc | low | 0.6802 [0.6758, 0.6843] |
| test | plain_mpc | medium | 1.1299 [1.1244, 1.1354] |
| test | plain_mpc | high | 1.8059 [1.7979, 1.8140] |
| test | rsrc | low | 0.7163 [0.7105, 0.7209] |
| test | rsrc | medium | 1.1561 [1.1452, 1.1646] |
| test | rsrc | high | 1.8194 [1.8012, 1.8350] |
| test | rsrc_no_context | low | 0.7184 [0.7123, 0.7231] |
| test | rsrc_no_context | medium | 1.1615 [1.1503, 1.1703] |
| test | rsrc_no_context | high | 1.8299 [1.8112, 1.8453] |
| test | rsrc_no_recovery | low | 0.7169 [0.7110, 0.7214] |
| test | rsrc_no_recovery | medium | 1.1572 [1.1464, 1.1661] |
| test | rsrc_no_recovery | high | 1.8214 [1.8030, 1.8368] |
| test | se_mpc | low | 0.7109 [0.7047, 0.7156] |
| test | se_mpc | medium | 1.1422 [1.1311, 1.1508] |
| test | se_mpc | high | 1.7925 [1.7740, 1.8081] |
| test | static_conservative | low | 0.6972 [0.6910, 0.7023] |
| test | static_conservative | medium | 1.1106 [1.0995, 1.1197] |
| test | static_conservative | high | 1.7331 [1.7142, 1.7485] |
| verified | adaptive_threshold | low | 0.6369 [0.6305, 0.6438] |
| verified | adaptive_threshold | medium | 1.0367 [1.0276, 1.0488] |
| verified | adaptive_threshold | high | 1.6364 [1.6216, 1.6545] |
| verified | always_verify_throttle | low | 0.6774 [0.6715, 0.6833] |
| verified | always_verify_throttle | medium | 1.0008 [0.9908, 1.0097] |
| verified | always_verify_throttle | high | 1.4864 [1.4696, 1.5013] |
| verified | camc_rsrc_anchor | low | 0.6564 [0.6502, 0.6627] |
| verified | camc_rsrc_anchor | medium | 1.0200 [1.0103, 1.0303] |
| verified | camc_rsrc_anchor | high | 1.5655 [1.5496, 1.5822] |
| verified | camc_sempc_candidate | low | 0.6491 [0.6419, 0.6559] |
| verified | camc_sempc_candidate | medium | 1.0236 [1.0134, 1.0340] |
| verified | camc_sempc_candidate | high | 1.5855 [1.5708, 1.6007] |
| verified | camc_static_anchor | low | 0.6513 [0.6448, 0.6578] |
| verified | camc_static_anchor | medium | 1.0104 [1.0004, 1.0202] |
| verified | camc_static_anchor | high | 1.5490 [1.5334, 1.5643] |
| verified | headroom_only | low | 0.6558 [0.6497, 0.6620] |
| verified | headroom_only | medium | 1.0172 [1.0076, 1.0266] |
| verified | headroom_only | high | 1.5593 [1.5439, 1.5742] |
| verified | maxweight_backlog | low | 0.6535 [0.6472, 0.6595] |
| verified | maxweight_backlog | medium | 1.0129 [1.0034, 1.0226] |
| verified | maxweight_backlog | high | 1.5521 [1.5376, 1.5666] |
| verified | minimal_verify | low | 0.7007 [0.6975, 0.7049] |
| verified | minimal_verify | medium | 1.1863 [1.1820, 1.1913] |
| verified | minimal_verify | high | 1.9146 [1.9081, 1.9213] |
| verified | pareto_camc_rsrc_anchor | low | 0.6552 [0.6491, 0.6613] |
| verified | pareto_camc_rsrc_anchor | medium | 1.0162 [1.0068, 1.0259] |
| verified | pareto_camc_rsrc_anchor | high | 1.5578 [1.5425, 1.5730] |
| verified | pareto_camc_sempc_candidate | low | 0.6505 [0.6440, 0.6566] |
| verified | pareto_camc_sempc_candidate | medium | 0.9986 [0.9888, 1.0077] |
| verified | pareto_camc_sempc_candidate | high | 1.5209 [1.5051, 1.5345] |
| verified | pareto_camc_static_anchor | low | 0.6497 [0.6433, 0.6562] |
| verified | pareto_camc_static_anchor | medium | 1.0061 [0.9962, 1.0162] |
| verified | pareto_camc_static_anchor | high | 1.5407 [1.5249, 1.5560] |
| verified | plain_mpc | low | 0.6686 [0.6614, 0.6754] |
| verified | plain_mpc | medium | 1.1115 [1.1014, 1.1204] |
| verified | plain_mpc | high | 1.7757 [1.7609, 1.7891] |
| verified | rsrc | low | 0.6552 [0.6491, 0.6613] |
| verified | rsrc | medium | 1.0162 [1.0068, 1.0259] |
| verified | rsrc | high | 1.5578 [1.5425, 1.5730] |
| verified | rsrc_no_context | low | 0.6554 [0.6492, 0.6615] |
| verified | rsrc_no_context | medium | 1.0166 [1.0071, 1.0261] |
| verified | rsrc_no_context | high | 1.5585 [1.5432, 1.5734] |
| verified | rsrc_no_recovery | low | 0.6557 [0.6495, 0.6618] |
| verified | rsrc_no_recovery | medium | 1.0168 [1.0073, 1.0264] |
| verified | rsrc_no_recovery | high | 1.5586 [1.5433, 1.5738] |
| verified | se_mpc | low | 0.6544 [0.6485, 0.6606] |
| verified | se_mpc | medium | 1.0151 [1.0054, 1.0246] |
| verified | se_mpc | high | 1.5563 [1.5409, 1.5711] |
| verified | static_conservative | low | 0.6497 [0.6433, 0.6562] |
| verified | static_conservative | medium | 1.0061 [0.9962, 1.0162] |
| verified | static_conservative | high | 1.5407 [1.5249, 1.5560] |

## Strong Baselines And Ablation Contrasts

| dataset | controller_a | controller_b | metric | estimate [95% CI] |
| --- | --- | --- | --- | --- |
| rebench | rsrc | static_conservative | safety_augmented_cost_medium | 0.0525 [0.0508, 0.0545] |
| rebench | rsrc | static_conservative | success_rate | -0.0074 [-0.0083, -0.0067] |
| rebench | rsrc | static_conservative | overload_rate | 0.0001 [0.0000, 0.0002] |
| rebench | rsrc | static_conservative | verification_rate | -0.0055 [-0.0060, -0.0051] |
| rebench | rsrc | static_conservative | negative_drift_rate_outside_safe | 0.0077 [0.0068, 0.0088] |
| rebench | rsrc | static_conservative | avg_return_time_to_safe | 0.2992 [0.2536, 0.3412] |
| rebench | se_mpc | static_conservative | safety_augmented_cost_medium | 0.0349 [0.0330, 0.0371] |
| rebench | se_mpc | static_conservative | success_rate | -0.0048 [-0.0058, -0.0041] |
| rebench | se_mpc | static_conservative | overload_rate | 0.0001 [0.0000, 0.0002] |
| rebench | se_mpc | static_conservative | verification_rate | -0.0055 [-0.0060, -0.0051] |
| rebench | se_mpc | static_conservative | negative_drift_rate_outside_safe | 0.0069 [0.0058, 0.0081] |
| rebench | se_mpc | static_conservative | avg_return_time_to_safe | 0.2337 [0.1967, 0.2761] |
| rebench | rsrc | headroom_only | safety_augmented_cost_medium | -0.0049 [-0.0058, -0.0040] |
| rebench | rsrc | headroom_only | success_rate | 0.0011 [0.0008, 0.0014] |
| rebench | rsrc | headroom_only | overload_rate | 0.0000 [0.0000, 0.0000] |
| rebench | rsrc | headroom_only | verification_rate | 0.0003 [0.0001, 0.0004] |
| rebench | rsrc | headroom_only | negative_drift_rate_outside_safe | -0.0001 [-0.0004, 0.0001] |
| rebench | rsrc | headroom_only | avg_return_time_to_safe | -0.0111 [-0.0282, 0.0046] |
| rebench | rsrc | rsrc_no_recovery | safety_augmented_cost_medium | -0.0014 [-0.0018, -0.0010] |
| rebench | rsrc | rsrc_no_recovery | success_rate | 0.0002 [0.0001, 0.0003] |
| rebench | rsrc | rsrc_no_recovery | overload_rate | 0.0000 [0.0000, 0.0000] |
| rebench | rsrc | rsrc_no_recovery | verification_rate | 0.0002 [0.0001, 0.0003] |
| rebench | rsrc | rsrc_no_recovery | negative_drift_rate_outside_safe | 0.0003 [0.0002, 0.0004] |
| rebench | rsrc | rsrc_no_recovery | avg_return_time_to_safe | -0.0078 [-0.0252, 0.0078] |
| rebench | rsrc | rsrc_no_context | safety_augmented_cost_medium | -0.0035 [-0.0042, -0.0027] |
| rebench | rsrc | rsrc_no_context | success_rate | 0.0009 [0.0006, 0.0013] |
| rebench | rsrc | rsrc_no_context | overload_rate | 0.0000 [0.0000, 0.0000] |
| rebench | rsrc | rsrc_no_context | verification_rate | 0.0001 [0.0000, 0.0002] |
| rebench | rsrc | rsrc_no_context | negative_drift_rate_outside_safe | -0.0004 [-0.0007, -0.0001] |
| rebench | rsrc | rsrc_no_context | avg_return_time_to_safe | -0.0071 [-0.0147, 0.0013] |
| rebench | se_mpc | rsrc | safety_augmented_cost_medium | -0.0176 [-0.0196, -0.0160] |
| rebench | se_mpc | rsrc | success_rate | 0.0026 [0.0021, 0.0032] |
| rebench | se_mpc | rsrc | overload_rate | 0.0000 [-0.0001, 0.0001] |
| rebench | se_mpc | rsrc | verification_rate | 0.0000 [-0.0001, 0.0001] |
| rebench | se_mpc | rsrc | negative_drift_rate_outside_safe | -0.0007 [-0.0014, -0.0001] |
| rebench | se_mpc | rsrc | avg_return_time_to_safe | -0.0655 [-0.0801, -0.0511] |
| rebench | camc_static_anchor | static_conservative | safety_augmented_cost_medium | 0.0344 [0.0328, 0.0359] |
| rebench | camc_static_anchor | static_conservative | success_rate | -0.0034 [-0.0039, -0.0029] |
| rebench | camc_static_anchor | static_conservative | overload_rate | 0.0000 [0.0000, 0.0001] |
| rebench | camc_static_anchor | static_conservative | verification_rate | -0.0028 [-0.0031, -0.0024] |
| rebench | camc_static_anchor | static_conservative | negative_drift_rate_outside_safe | 0.0042 [0.0036, 0.0048] |
| rebench | camc_static_anchor | static_conservative | avg_return_time_to_safe | 0.0930 [0.0682, 0.1204] |
| rebench | camc_rsrc_anchor | rsrc | safety_augmented_cost_medium | 0.0000 [-0.0015, 0.0015] |
| rebench | camc_rsrc_anchor | rsrc | success_rate | -0.0060 [-0.0066, -0.0053] |
| rebench | camc_rsrc_anchor | rsrc | overload_rate | 0.0000 [0.0000, 0.0001] |
| rebench | camc_rsrc_anchor | rsrc | verification_rate | -0.0156 [-0.0163, -0.0148] |
| rebench | camc_rsrc_anchor | rsrc | negative_drift_rate_outside_safe | 0.0034 [0.0030, 0.0039] |
| rebench | camc_rsrc_anchor | rsrc | avg_return_time_to_safe | 0.1636 [0.1382, 0.1917] |
| rebench | camc_sempc_candidate | static_conservative | safety_augmented_cost_medium | 0.0305 [0.0274, 0.0340] |
| rebench | camc_sempc_candidate | static_conservative | success_rate | -0.0296 [-0.0318, -0.0279] |
| rebench | camc_sempc_candidate | static_conservative | overload_rate | 0.0001 [0.0000, 0.0002] |
| rebench | camc_sempc_candidate | static_conservative | verification_rate | -0.0719 [-0.0738, -0.0699] |
| rebench | camc_sempc_candidate | static_conservative | negative_drift_rate_outside_safe | 0.0122 [0.0109, 0.0138] |
| rebench | camc_sempc_candidate | static_conservative | avg_return_time_to_safe | 0.5210 [0.4637, 0.5796] |
| rebench | camc_sempc_candidate | se_mpc | safety_augmented_cost_medium | -0.0044 [-0.0076, -0.0011] |
| rebench | camc_sempc_candidate | se_mpc | success_rate | -0.0248 [-0.0266, -0.0231] |
| rebench | camc_sempc_candidate | se_mpc | overload_rate | 0.0000 [0.0000, 0.0001] |
| rebench | camc_sempc_candidate | se_mpc | verification_rate | -0.0664 [-0.0683, -0.0645] |
| rebench | camc_sempc_candidate | se_mpc | negative_drift_rate_outside_safe | 0.0053 [0.0047, 0.0060] |
| rebench | camc_sempc_candidate | se_mpc | avg_return_time_to_safe | 0.2873 [0.2357, 0.3461] |
| rebench | headroom_only | minimal_verify | safety_augmented_cost_medium | -0.0611 [-0.0793, -0.0471] |
| rebench | headroom_only | minimal_verify | success_rate | 0.2342 [0.2297, 0.2386] |
| rebench | headroom_only | minimal_verify | overload_rate | -0.0196 [-0.0249, -0.0152] |
| rebench | headroom_only | minimal_verify | verification_rate | 0.7198 [0.7161, 0.7233] |
| rebench | headroom_only | minimal_verify | negative_drift_rate_outside_safe | 0.1014 [0.0977, 0.1055] |
| rebench | headroom_only | minimal_verify | avg_return_time_to_safe | -1177.4679 [-1196.3434, -1139.8464] |
| rebench | always_verify_throttle | always_verify | safety_augmented_cost_medium | -0.0156 [-0.0169, -0.0145] |
| rebench | always_verify_throttle | always_verify | success_rate | 0.0008 [0.0005, 0.0011] |
| rebench | always_verify_throttle | always_verify | overload_rate | 0.0000 [0.0000, 0.0000] |
| rebench | always_verify_throttle | always_verify | verification_rate | 0.0000 [0.0000, 0.0000] |
| rebench | always_verify_throttle | always_verify | negative_drift_rate_outside_safe | -0.0005 [-0.0006, -0.0004] |
| rebench | always_verify_throttle | always_verify | avg_return_time_to_safe | -0.1307 [-0.1958, -0.0587] |
| smith | rsrc | static_conservative | safety_augmented_cost_medium | 0.0187 [0.0175, 0.0201] |
| smith | rsrc | static_conservative | success_rate | -0.0009 [-0.0012, -0.0006] |
| smith | rsrc | static_conservative | overload_rate | 0.0002 [0.0001, 0.0003] |
| smith | rsrc | static_conservative | verification_rate | -0.0004 [-0.0005, -0.0003] |
| smith | rsrc | static_conservative | negative_drift_rate_outside_safe | 0.0040 [0.0034, 0.0044] |
| smith | rsrc | static_conservative | avg_return_time_to_safe | 0.5121 [0.3920, 0.6225] |
| smith | se_mpc | static_conservative | safety_augmented_cost_medium | 0.0167 [0.0152, 0.0181] |
| smith | se_mpc | static_conservative | success_rate | -0.0005 [-0.0009, -0.0001] |
| smith | se_mpc | static_conservative | overload_rate | 0.0003 [0.0001, 0.0004] |
| smith | se_mpc | static_conservative | verification_rate | -0.0005 [-0.0006, -0.0004] |
| smith | se_mpc | static_conservative | negative_drift_rate_outside_safe | 0.0035 [0.0030, 0.0039] |
| smith | se_mpc | static_conservative | avg_return_time_to_safe | 0.4742 [0.3574, 0.5802] |
| smith | rsrc | headroom_only | safety_augmented_cost_medium | -0.0009 [-0.0012, -0.0006] |
| smith | rsrc | headroom_only | success_rate | 0.0000 [0.0000, 0.0000] |
| smith | rsrc | headroom_only | overload_rate | 0.0000 [0.0000, 0.0000] |
| smith | rsrc | headroom_only | verification_rate | 0.0001 [0.0000, 0.0001] |
| smith | rsrc | headroom_only | negative_drift_rate_outside_safe | 0.0007 [0.0005, 0.0009] |
| smith | rsrc | headroom_only | avg_return_time_to_safe | 0.1394 [0.0921, 0.1894] |
| smith | rsrc | rsrc_no_recovery | safety_augmented_cost_medium | -0.0008 [-0.0011, -0.0004] |
| smith | rsrc | rsrc_no_recovery | success_rate | 0.0000 [0.0000, 0.0000] |
| smith | rsrc | rsrc_no_recovery | overload_rate | 0.0000 [0.0000, 0.0000] |
| smith | rsrc | rsrc_no_recovery | verification_rate | 0.0001 [0.0000, 0.0001] |
| smith | rsrc | rsrc_no_recovery | negative_drift_rate_outside_safe | 0.0007 [0.0005, 0.0009] |
| smith | rsrc | rsrc_no_recovery | avg_return_time_to_safe | 0.1418 [0.0962, 0.1900] |
| smith | rsrc | rsrc_no_context | safety_augmented_cost_medium | -0.0001 [-0.0002, -0.0000] |
| smith | rsrc | rsrc_no_context | success_rate | 0.0000 [0.0000, 0.0000] |
| smith | rsrc | rsrc_no_context | overload_rate | 0.0000 [0.0000, 0.0000] |
| smith | rsrc | rsrc_no_context | verification_rate | 0.0000 [0.0000, 0.0000] |
| smith | rsrc | rsrc_no_context | negative_drift_rate_outside_safe | -0.0000 [-0.0000, 0.0000] |
| smith | rsrc | rsrc_no_context | avg_return_time_to_safe | -0.0028 [-0.0111, 0.0000] |
| smith | se_mpc | rsrc | safety_augmented_cost_medium | -0.0020 [-0.0029, -0.0012] |
| smith | se_mpc | rsrc | success_rate | 0.0004 [0.0002, 0.0007] |
| smith | se_mpc | rsrc | overload_rate | 0.0001 [0.0000, 0.0001] |
| smith | se_mpc | rsrc | verification_rate | -0.0000 [-0.0001, 0.0000] |
| smith | se_mpc | rsrc | negative_drift_rate_outside_safe | -0.0005 [-0.0007, -0.0003] |
| smith | se_mpc | rsrc | avg_return_time_to_safe | -0.0379 [-0.0740, -0.0043] |
| smith | camc_static_anchor | static_conservative | safety_augmented_cost_medium | 0.0002 [0.0001, 0.0004] |
| smith | camc_static_anchor | static_conservative | success_rate | 0.0000 [0.0000, 0.0000] |
| smith | camc_static_anchor | static_conservative | overload_rate | 0.0000 [0.0000, 0.0000] |
| smith | camc_static_anchor | static_conservative | verification_rate | -0.0000 [-0.0000, 0.0000] |
| smith | camc_static_anchor | static_conservative | negative_drift_rate_outside_safe | 0.0000 [0.0000, 0.0001] |
| smith | camc_static_anchor | static_conservative | avg_return_time_to_safe | 0.0015 [-0.0067, 0.0090] |
| smith | camc_rsrc_anchor | rsrc | safety_augmented_cost_medium | -0.0105 [-0.0134, -0.0081] |
| smith | camc_rsrc_anchor | rsrc | success_rate | -0.0131 [-0.0143, -0.0120] |
| smith | camc_rsrc_anchor | rsrc | overload_rate | 0.0003 [0.0001, 0.0005] |
| smith | camc_rsrc_anchor | rsrc | verification_rate | -0.0368 [-0.0385, -0.0353] |
| smith | camc_rsrc_anchor | rsrc | negative_drift_rate_outside_safe | -0.0007 [-0.0011, -0.0002] |
| smith | camc_rsrc_anchor | rsrc | avg_return_time_to_safe | -0.0372 [-0.1960, 0.1081] |
| smith | camc_sempc_candidate | static_conservative | safety_augmented_cost_medium | 0.0078 [0.0050, 0.0100] |
| smith | camc_sempc_candidate | static_conservative | success_rate | -0.0135 [-0.0147, -0.0123] |
| smith | camc_sempc_candidate | static_conservative | overload_rate | 0.0005 [0.0003, 0.0008] |
| smith | camc_sempc_candidate | static_conservative | verification_rate | -0.0362 [-0.0380, -0.0348] |
| smith | camc_sempc_candidate | static_conservative | negative_drift_rate_outside_safe | 0.0032 [0.0026, 0.0038] |
| smith | camc_sempc_candidate | static_conservative | avg_return_time_to_safe | 0.4542 [0.3115, 0.5721] |
| smith | camc_sempc_candidate | se_mpc | safety_augmented_cost_medium | -0.0089 [-0.0119, -0.0064] |
| smith | camc_sempc_candidate | se_mpc | success_rate | -0.0130 [-0.0142, -0.0118] |
| smith | camc_sempc_candidate | se_mpc | overload_rate | 0.0003 [0.0001, 0.0005] |
| smith | camc_sempc_candidate | se_mpc | verification_rate | -0.0358 [-0.0374, -0.0343] |
| smith | camc_sempc_candidate | se_mpc | negative_drift_rate_outside_safe | -0.0003 [-0.0008, 0.0002] |
| smith | camc_sempc_candidate | se_mpc | avg_return_time_to_safe | -0.0199 [-0.1840, 0.1282] |
| smith | headroom_only | minimal_verify | safety_augmented_cost_medium | -13.7112 [-14.2113, -13.2090] |
| smith | headroom_only | minimal_verify | success_rate | 0.2407 [0.2364, 0.2454] |
| smith | headroom_only | minimal_verify | overload_rate | -0.9694 [-0.9728, -0.9667] |
| smith | headroom_only | minimal_verify | verification_rate | 0.9309 [0.9295, 0.9324] |
| smith | headroom_only | minimal_verify | negative_drift_rate_outside_safe | 0.8314 [0.8274, 0.8358] |
| smith | headroom_only | minimal_verify | avg_return_time_to_safe | -1190.5001 [-1190.8358, -1190.2280] |
| smith | always_verify_throttle | always_verify | safety_augmented_cost_medium | -0.0060 [-0.0069, -0.0051] |
| smith | always_verify_throttle | always_verify | success_rate | 0.0002 [0.0001, 0.0004] |
| smith | always_verify_throttle | always_verify | overload_rate | -0.0001 [-0.0002, -0.0000] |
| smith | always_verify_throttle | always_verify | verification_rate | 0.0000 [0.0000, 0.0000] |
| smith | always_verify_throttle | always_verify | negative_drift_rate_outside_safe | -0.0007 [-0.0009, -0.0006] |
| smith | always_verify_throttle | always_verify | avg_return_time_to_safe | -0.5055 [-0.6560, -0.3745] |
| test | rsrc | static_conservative | safety_augmented_cost_medium | 0.0455 [0.0431, 0.0481] |
| test | rsrc | static_conservative | success_rate | -0.0063 [-0.0072, -0.0054] |
| test | rsrc | static_conservative | overload_rate | 0.0001 [0.0000, 0.0001] |
| test | rsrc | static_conservative | verification_rate | -0.0050 [-0.0055, -0.0047] |
| test | rsrc | static_conservative | negative_drift_rate_outside_safe | 0.0031 [0.0026, 0.0036] |
| test | rsrc | static_conservative | avg_return_time_to_safe | 0.2211 [0.1676, 0.2697] |
| test | se_mpc | static_conservative | safety_augmented_cost_medium | 0.0316 [0.0290, 0.0342] |
| test | se_mpc | static_conservative | success_rate | -0.0029 [-0.0037, -0.0022] |
| test | se_mpc | static_conservative | overload_rate | 0.0001 [-0.0001, 0.0001] |
| test | se_mpc | static_conservative | verification_rate | -0.0049 [-0.0053, -0.0046] |
| test | se_mpc | static_conservative | negative_drift_rate_outside_safe | 0.0030 [0.0025, 0.0036] |
| test | se_mpc | static_conservative | avg_return_time_to_safe | 0.1351 [0.0824, 0.1837] |
| test | rsrc | headroom_only | safety_augmented_cost_medium | -0.0067 [-0.0077, -0.0057] |
| test | rsrc | headroom_only | success_rate | 0.0019 [0.0015, 0.0023] |
| test | rsrc | headroom_only | overload_rate | 0.0001 [0.0000, 0.0002] |
| test | rsrc | headroom_only | verification_rate | 0.0003 [0.0002, 0.0003] |
| test | rsrc | headroom_only | negative_drift_rate_outside_safe | -0.0000 [-0.0002, 0.0001] |
| test | rsrc | headroom_only | avg_return_time_to_safe | -0.0060 [-0.0261, 0.0121] |
| test | rsrc | rsrc_no_recovery | safety_augmented_cost_medium | -0.0012 [-0.0016, -0.0007] |
| test | rsrc | rsrc_no_recovery | success_rate | 0.0002 [0.0001, 0.0003] |
| test | rsrc | rsrc_no_recovery | overload_rate | 0.0000 [0.0000, 0.0000] |
| test | rsrc | rsrc_no_recovery | verification_rate | 0.0002 [0.0001, 0.0003] |
| test | rsrc | rsrc_no_recovery | negative_drift_rate_outside_safe | 0.0001 [0.0000, 0.0001] |
| test | rsrc | rsrc_no_recovery | avg_return_time_to_safe | 0.0100 [-0.0099, 0.0278] |
| test | rsrc | rsrc_no_context | safety_augmented_cost_medium | -0.0054 [-0.0064, -0.0045] |
| test | rsrc | rsrc_no_context | success_rate | 0.0017 [0.0013, 0.0021] |
| test | rsrc | rsrc_no_context | overload_rate | 0.0001 [0.0000, 0.0002] |
| test | rsrc | rsrc_no_context | verification_rate | 0.0001 [0.0000, 0.0001] |
| test | rsrc | rsrc_no_context | negative_drift_rate_outside_safe | -0.0001 [-0.0002, -0.0000] |
| test | rsrc | rsrc_no_context | avg_return_time_to_safe | -0.0166 [-0.0242, -0.0092] |
| test | se_mpc | rsrc | safety_augmented_cost_medium | -0.0139 [-0.0149, -0.0127] |
| test | se_mpc | rsrc | success_rate | 0.0034 [0.0029, 0.0041] |
| test | se_mpc | rsrc | overload_rate | 0.0000 [-0.0001, 0.0001] |
| test | se_mpc | rsrc | verification_rate | 0.0001 [0.0001, 0.0002] |
| test | se_mpc | rsrc | negative_drift_rate_outside_safe | -0.0001 [-0.0003, 0.0002] |
| test | se_mpc | rsrc | avg_return_time_to_safe | -0.0860 [-0.1004, -0.0741] |
| test | camc_static_anchor | static_conservative | safety_augmented_cost_medium | 0.0376 [0.0353, 0.0397] |
| test | camc_static_anchor | static_conservative | success_rate | -0.0051 [-0.0057, -0.0043] |
| test | camc_static_anchor | static_conservative | overload_rate | 0.0000 [0.0000, 0.0001] |
| test | camc_static_anchor | static_conservative | verification_rate | -0.0040 [-0.0044, -0.0037] |
| test | camc_static_anchor | static_conservative | negative_drift_rate_outside_safe | 0.0025 [0.0020, 0.0029] |
| test | camc_static_anchor | static_conservative | avg_return_time_to_safe | 0.1498 [0.1078, 0.1894] |
| test | camc_rsrc_anchor | rsrc | safety_augmented_cost_medium | 0.0004 [-0.0007, 0.0017] |
| test | camc_rsrc_anchor | rsrc | success_rate | -0.0041 [-0.0048, -0.0035] |
| test | camc_rsrc_anchor | rsrc | overload_rate | 0.0000 [0.0000, 0.0000] |
| test | camc_rsrc_anchor | rsrc | verification_rate | -0.0113 [-0.0120, -0.0107] |
| test | camc_rsrc_anchor | rsrc | negative_drift_rate_outside_safe | 0.0009 [0.0007, 0.0011] |
| test | camc_rsrc_anchor | rsrc | avg_return_time_to_safe | 0.0202 [-0.0101, 0.0539] |
| test | camc_sempc_candidate | static_conservative | safety_augmented_cost_medium | 0.0283 [0.0247, 0.0314] |
| test | camc_sempc_candidate | static_conservative | success_rate | -0.0296 [-0.0321, -0.0274] |
| test | camc_sempc_candidate | static_conservative | overload_rate | 0.0001 [-0.0000, 0.0002] |
| test | camc_sempc_candidate | static_conservative | verification_rate | -0.0773 [-0.0791, -0.0758] |
| test | camc_sempc_candidate | static_conservative | negative_drift_rate_outside_safe | 0.0044 [0.0036, 0.0052] |
| test | camc_sempc_candidate | static_conservative | avg_return_time_to_safe | 0.1909 [0.1310, 0.2517] |
| test | camc_sempc_candidate | se_mpc | safety_augmented_cost_medium | -0.0033 [-0.0059, -0.0011] |
| test | camc_sempc_candidate | se_mpc | success_rate | -0.0267 [-0.0291, -0.0247] |
| test | camc_sempc_candidate | se_mpc | overload_rate | 0.0000 [-0.0001, 0.0001] |
| test | camc_sempc_candidate | se_mpc | verification_rate | -0.0724 [-0.0741, -0.0709] |
| test | camc_sempc_candidate | se_mpc | negative_drift_rate_outside_safe | 0.0014 [0.0009, 0.0018] |
| test | camc_sempc_candidate | se_mpc | avg_return_time_to_safe | 0.0558 [0.0061, 0.1170] |
| test | headroom_only | minimal_verify | safety_augmented_cost_medium | -0.0404 [-0.0507, -0.0302] |
| test | headroom_only | minimal_verify | success_rate | 0.2447 [0.2394, 0.2508] |
| test | headroom_only | minimal_verify | overload_rate | -0.0054 [-0.0073, -0.0036] |
| test | headroom_only | minimal_verify | verification_rate | 0.7577 [0.7556, 0.7597] |
| test | headroom_only | minimal_verify | negative_drift_rate_outside_safe | 0.0567 [0.0546, 0.0595] |
| test | headroom_only | minimal_verify | avg_return_time_to_safe | -1196.0582 [-1196.1600, -1195.9650] |
| test | always_verify_throttle | always_verify | safety_augmented_cost_medium | -0.0135 [-0.0149, -0.0118] |
| test | always_verify_throttle | always_verify | success_rate | 0.0007 [0.0004, 0.0011] |
| test | always_verify_throttle | always_verify | overload_rate | 0.0000 [0.0000, 0.0000] |
| test | always_verify_throttle | always_verify | verification_rate | 0.0000 [0.0000, 0.0000] |
| test | always_verify_throttle | always_verify | negative_drift_rate_outside_safe | -0.0002 [-0.0002, -0.0001] |
| test | always_verify_throttle | always_verify | avg_return_time_to_safe | -0.1183 [-0.1777, -0.0520] |
| verified | rsrc | static_conservative | safety_augmented_cost_medium | 0.0102 [0.0086, 0.0118] |
| verified | rsrc | static_conservative | success_rate | -0.0071 [-0.0083, -0.0058] |
| verified | rsrc | static_conservative | overload_rate | 0.0000 [0.0000, 0.0000] |
| verified | rsrc | static_conservative | verification_rate | -0.0066 [-0.0072, -0.0060] |
| verified | rsrc | static_conservative | negative_drift_rate_outside_safe | 0.0029 [0.0018, 0.0041] |
| verified | rsrc | static_conservative | avg_return_time_to_safe | 0.2142 [0.1634, 0.2624] |
| verified | se_mpc | static_conservative | safety_augmented_cost_medium | 0.0090 [0.0073, 0.0109] |
| verified | se_mpc | static_conservative | success_rate | -0.0065 [-0.0078, -0.0052] |
| verified | se_mpc | static_conservative | overload_rate | 0.0000 [0.0000, 0.0000] |
| verified | se_mpc | static_conservative | verification_rate | -0.0069 [-0.0075, -0.0063] |
| verified | se_mpc | static_conservative | negative_drift_rate_outside_safe | 0.0030 [0.0019, 0.0042] |
| verified | se_mpc | static_conservative | avg_return_time_to_safe | 0.2043 [0.1538, 0.2542] |
| verified | rsrc | headroom_only | safety_augmented_cost_medium | -0.0009 [-0.0014, -0.0006] |
| verified | rsrc | headroom_only | success_rate | 0.0007 [0.0003, 0.0012] |
| verified | rsrc | headroom_only | overload_rate | 0.0000 [0.0000, 0.0000] |
| verified | rsrc | headroom_only | verification_rate | 0.0001 [0.0000, 0.0003] |
| verified | rsrc | headroom_only | negative_drift_rate_outside_safe | 0.0002 [0.0001, 0.0002] |
| verified | rsrc | headroom_only | avg_return_time_to_safe | -0.0403 [-0.0679, -0.0077] |
| verified | rsrc | rsrc_no_recovery | safety_augmented_cost_medium | -0.0006 [-0.0008, -0.0003] |
| verified | rsrc | rsrc_no_recovery | success_rate | 0.0003 [0.0001, 0.0005] |
| verified | rsrc | rsrc_no_recovery | overload_rate | 0.0000 [0.0000, 0.0000] |
| verified | rsrc | rsrc_no_recovery | verification_rate | 0.0001 [0.0000, 0.0003] |
| verified | rsrc | rsrc_no_recovery | negative_drift_rate_outside_safe | 0.0002 [0.0001, 0.0002] |
| verified | rsrc | rsrc_no_recovery | avg_return_time_to_safe | -0.0392 [-0.0675, -0.0063] |
| verified | rsrc | rsrc_no_context | safety_augmented_cost_medium | -0.0004 [-0.0008, -0.0001] |
| verified | rsrc | rsrc_no_context | success_rate | 0.0004 [0.0001, 0.0009] |
| verified | rsrc | rsrc_no_context | overload_rate | 0.0000 [0.0000, 0.0000] |
| verified | rsrc | rsrc_no_context | verification_rate | 0.0000 [0.0000, 0.0001] |
| verified | rsrc | rsrc_no_context | negative_drift_rate_outside_safe | -0.0000 [-0.0000, 0.0000] |
| verified | rsrc | rsrc_no_context | avg_return_time_to_safe | -0.0006 [-0.0097, 0.0071] |
| verified | se_mpc | rsrc | safety_augmented_cost_medium | -0.0011 [-0.0018, -0.0006] |
| verified | se_mpc | rsrc | success_rate | 0.0006 [0.0003, 0.0009] |
| verified | se_mpc | rsrc | overload_rate | 0.0000 [0.0000, 0.0000] |
| verified | se_mpc | rsrc | verification_rate | -0.0003 [-0.0004, -0.0001] |
| verified | se_mpc | rsrc | negative_drift_rate_outside_safe | 0.0001 [0.0000, 0.0001] |
| verified | se_mpc | rsrc | avg_return_time_to_safe | -0.0099 [-0.0237, 0.0048] |
| verified | camc_static_anchor | static_conservative | safety_augmented_cost_medium | 0.0043 [0.0034, 0.0052] |
| verified | camc_static_anchor | static_conservative | success_rate | -0.0039 [-0.0047, -0.0031] |
| verified | camc_static_anchor | static_conservative | overload_rate | 0.0000 [0.0000, 0.0000] |
| verified | camc_static_anchor | static_conservative | verification_rate | -0.0033 [-0.0037, -0.0027] |
| verified | camc_static_anchor | static_conservative | negative_drift_rate_outside_safe | 0.0013 [0.0007, 0.0018] |
| verified | camc_static_anchor | static_conservative | avg_return_time_to_safe | 0.0855 [0.0433, 0.1279] |
| verified | camc_rsrc_anchor | rsrc | safety_augmented_cost_medium | 0.0038 [0.0027, 0.0049] |
| verified | camc_rsrc_anchor | rsrc | success_rate | -0.0043 [-0.0055, -0.0032] |
| verified | camc_rsrc_anchor | rsrc | overload_rate | 0.0000 [0.0000, 0.0000] |
| verified | camc_rsrc_anchor | rsrc | verification_rate | -0.0103 [-0.0114, -0.0092] |
| verified | camc_rsrc_anchor | rsrc | negative_drift_rate_outside_safe | 0.0011 [0.0008, 0.0013] |
| verified | camc_rsrc_anchor | rsrc | avg_return_time_to_safe | 0.0940 [0.0443, 0.1450] |
| verified | camc_sempc_candidate | static_conservative | safety_augmented_cost_medium | 0.0176 [0.0146, 0.0208] |
| verified | camc_sempc_candidate | static_conservative | success_rate | -0.0334 [-0.0366, -0.0303] |
| verified | camc_sempc_candidate | static_conservative | overload_rate | 0.0000 [0.0000, 0.0000] |
| verified | camc_sempc_candidate | static_conservative | verification_rate | -0.0822 [-0.0850, -0.0798] |
| verified | camc_sempc_candidate | static_conservative | negative_drift_rate_outside_safe | 0.0047 [0.0031, 0.0063] |
| verified | camc_sempc_candidate | static_conservative | avg_return_time_to_safe | 0.3575 [0.2907, 0.4263] |
| verified | camc_sempc_candidate | se_mpc | safety_augmented_cost_medium | 0.0085 [0.0050, 0.0121] |
| verified | camc_sempc_candidate | se_mpc | success_rate | -0.0269 [-0.0301, -0.0241] |
| verified | camc_sempc_candidate | se_mpc | overload_rate | 0.0000 [0.0000, 0.0000] |
| verified | camc_sempc_candidate | se_mpc | verification_rate | -0.0753 [-0.0781, -0.0728] |
| verified | camc_sempc_candidate | se_mpc | negative_drift_rate_outside_safe | 0.0017 [0.0010, 0.0024] |
| verified | camc_sempc_candidate | se_mpc | avg_return_time_to_safe | 0.1532 [0.0740, 0.2319] |
| verified | headroom_only | minimal_verify | safety_augmented_cost_medium | -0.1691 [-0.1795, -0.1599] |
| verified | headroom_only | minimal_verify | success_rate | 0.2531 [0.2457, 0.2607] |
| verified | headroom_only | minimal_verify | overload_rate | 0.0000 [0.0000, 0.0000] |
| verified | headroom_only | minimal_verify | verification_rate | 0.7479 [0.7442, 0.7514] |
| verified | headroom_only | minimal_verify | negative_drift_rate_outside_safe | 0.0458 [0.0424, 0.0490] |
| verified | headroom_only | minimal_verify | avg_return_time_to_safe | -488.2805 [-496.1537, -472.6796] |
| verified | always_verify_throttle | always_verify | safety_augmented_cost_medium | -0.0028 [-0.0035, -0.0021] |
| verified | always_verify_throttle | always_verify | success_rate | 0.0013 [0.0009, 0.0018] |
| verified | always_verify_throttle | always_verify | overload_rate | 0.0000 [0.0000, 0.0000] |
| verified | always_verify_throttle | always_verify | verification_rate | 0.0000 [0.0000, 0.0000] |
| verified | always_verify_throttle | always_verify | negative_drift_rate_outside_safe | -0.0002 [-0.0003, -0.0002] |
| verified | always_verify_throttle | always_verify | avg_return_time_to_safe | -0.0041 [-0.1236, 0.1228] |

## SE-MPC Activation Diagnostics

| dataset | mpc_eligible_rate | mpc_activation_rate | mpc_fallback_to_rsrc_rate | mpc_mean_candidate_count | mpc_candidate_rejection_rate | mpc_mean_surrogate_improvement | mpc_verify_down_rate | mpc_verify_up_rate | mpc_atom_up_rate | mpc_mode_switch_rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| rebench | 0.0004 | 0.5312 | 0.4276 | 1.9688 | 0.0000 | 0.0749 | 0.5312 | 0.0000 | 0.0000 | 0.0000 |
| smith | 0.0001 | 0.0938 | 0.8471 | 0.2812 | 0.0000 | 0.0134 | 0.0938 | 0.0000 | 0.0000 | 0.0000 |
| test | 0.0002 | 0.2500 | 0.4385 | 0.8438 | 0.0000 | 0.0357 | 0.2500 | 0.0000 | 0.0000 | 0.0000 |
| verified | 0.0010 | 0.4375 | 0.4181 | 1.4531 | 0.0000 | 0.0623 | 0.4375 | 0.0000 | 0.0000 | 0.0000 |

## CAMC Gate Diagnostics

| dataset | controller | safety_augmented_cost | success_rate | overload_rate | verification_rate | fallback_rate | camc_activation_rate | camc_anchor_preservation_rate | camc_candidate_rejection_rate | camc_post_switch_violation_rate | camc_mean_certified_margin | camc_mean_activated_margin | camc_reject_safety_rate | camc_reject_loss_rate | camc_reject_benefit_rate | camc_reject_violation_rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| rebench | camc_rsrc_anchor | 1.1880 | 0.2604 | 0.0002 | 0.7044 | 0.4526 | 0.0880 | 0.9120 | 0.4760 | 0.0023 | -0.0384 | 0.0175 | 0.8150 | 0.0000 | 0.0000 | 0.0000 |
| rebench | camc_sempc_candidate | 1.1659 | 0.2442 | 0.0002 | 0.6536 | 0.4657 | 0.4982 | 0.5018 | 0.3436 | 0.0017 | 0.0944 | 0.1946 | 0.9807 | 0.0000 | 0.0000 | 0.0000 |
| rebench | camc_static_anchor | 1.1698 | 0.2705 | 0.0001 | 0.7228 | 0.3599 | 0.2415 | 0.7585 | 0.2198 | 0.0000 | -0.0379 | 0.0093 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| rebench | pareto_camc_rsrc_anchor | 1.1880 | 0.2664 | 0.0002 | 0.7200 | 0.4248 | 0.0000 | 1.0000 | 0.7440 | 0.0000 | -0.0582 | 0.0000 | 0.5065 | 0.4934 | 0.0001 | 0.0000 |
| rebench | pareto_camc_sempc_candidate | 1.1599 | 0.2933 | 0.0001 | 0.7814 | 0.3753 | 0.2016 | 0.7984 | 0.7258 | 0.0005 | -0.0333 | 0.0523 | 0.4185 | 0.3596 | 0.1111 | 0.1108 |
| rebench | pareto_camc_static_anchor | 1.1354 | 0.2739 | 0.0001 | 0.7255 | 0.3102 | 0.0000 | 1.0000 | 0.3922 | 0.0000 | -0.0696 | 0.0000 | 0.0000 | 0.1504 | 0.0000 | 0.8496 |
| smith | camc_rsrc_anchor | 1.4457 | 0.2474 | 0.0178 | 0.8942 | 0.8276 | 0.1485 | 0.8515 | 0.5141 | 0.0010 | 0.0264 | 0.1889 | 0.9852 | 0.0000 | 0.0000 | 0.0000 |
| smith | camc_sempc_candidate | 1.4452 | 0.2480 | 0.0178 | 0.8952 | 0.8287 | 0.1463 | 0.8537 | 0.5166 | 0.0005 | 0.0249 | 0.1824 | 0.9853 | 0.0000 | 0.0000 | 0.0000 |
| smith | camc_static_anchor | 1.4376 | 0.2615 | 0.0173 | 0.9314 | 0.8230 | 0.0011 | 0.9989 | 0.1320 | 0.0000 | -0.0191 | 0.0016 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| smith | pareto_camc_rsrc_anchor | 1.4435 | 0.2629 | 0.0174 | 0.9374 | 0.8332 | 0.0193 | 0.9807 | 0.6767 | 0.0000 | -0.0157 | 0.0579 | 0.7656 | 0.1610 | 0.0374 | 0.0360 |
| smith | pareto_camc_sempc_candidate | 1.4421 | 0.2627 | 0.0174 | 0.9364 | 0.8316 | 0.0161 | 0.9839 | 0.6791 | 0.0000 | -0.0165 | 0.0548 | 0.7627 | 0.1678 | 0.0354 | 0.0341 |
| smith | pareto_camc_static_anchor | 1.4374 | 0.2615 | 0.0173 | 0.9314 | 0.8228 | 0.0000 | 1.0000 | 0.1332 | 0.0000 | -0.0201 | 0.0000 | 0.0000 | 0.3564 | 0.0000 | 0.6436 |
| test | camc_rsrc_anchor | 1.1565 | 0.2728 | 0.0001 | 0.7466 | 0.4536 | 0.0729 | 0.9271 | 0.4963 | 0.0034 | -0.0368 | 0.0238 | 0.8156 | 0.0000 | 0.0000 | 0.0000 |
| test | camc_sempc_candidate | 1.1389 | 0.2536 | 0.0001 | 0.6856 | 0.4506 | 0.5133 | 0.4867 | 0.3455 | 0.0009 | 0.1011 | 0.2020 | 0.9818 | 0.0000 | 0.0000 | 0.0000 |
| test | camc_static_anchor | 1.1481 | 0.2782 | 0.0001 | 0.7590 | 0.4036 | 0.3625 | 0.6375 | 0.1149 | 0.0001 | -0.0290 | 0.0205 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| test | pareto_camc_rsrc_anchor | 1.1561 | 0.2769 | 0.0001 | 0.7579 | 0.4370 | 0.0000 | 1.0000 | 0.7488 | 0.0000 | -0.0512 | 0.0000 | 0.5348 | 0.4645 | 0.0007 | 0.0000 |
| test | pareto_camc_sempc_candidate | 1.1298 | 0.3034 | 0.0001 | 0.8172 | 0.4268 | 0.2631 | 0.7369 | 0.7005 | 0.0002 | -0.0104 | 0.0738 | 0.5077 | 0.2361 | 0.1239 | 0.1323 |
| test | pareto_camc_static_anchor | 1.1106 | 0.2832 | 0.0001 | 0.7630 | 0.3145 | 0.0000 | 1.0000 | 0.3892 | 0.0000 | -0.0622 | 0.0000 | 0.0000 | 0.1064 | 0.0016 | 0.8920 |
| verified | camc_rsrc_anchor | 1.0200 | 0.2784 | 0.0000 | 0.7377 | 0.4371 | 0.0628 | 0.9372 | 0.4861 | 0.0000 | -0.0458 | 0.0137 | 0.7932 | 0.0000 | 0.0000 | 0.0000 |
| verified | camc_sempc_candidate | 1.0236 | 0.2564 | 0.0000 | 0.6724 | 0.4532 | 0.4979 | 0.5021 | 0.3369 | 0.0000 | 0.0945 | 0.1961 | 0.9708 | 0.0000 | 0.0000 | 0.0000 |
| verified | camc_static_anchor | 1.0104 | 0.2859 | 0.0000 | 0.7513 | 0.3420 | 0.2148 | 0.7852 | 0.2391 | 0.0000 | -0.0460 | 0.0087 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| verified | pareto_camc_rsrc_anchor | 1.0162 | 0.2828 | 0.0000 | 0.7480 | 0.4153 | 0.0000 | 1.0000 | 0.7467 | 0.0000 | -0.0641 | 0.0000 | 0.5067 | 0.4933 | 0.0001 | 0.0000 |
| verified | pareto_camc_sempc_candidate | 0.9986 | 0.3078 | 0.0000 | 0.8126 | 0.3796 | 0.1906 | 0.8094 | 0.7348 | 0.0000 | -0.0361 | 0.0673 | 0.4344 | 0.2933 | 0.1258 | 0.1465 |
| verified | pareto_camc_static_anchor | 1.0061 | 0.2898 | 0.0000 | 0.7546 | 0.2993 | 0.0000 | 1.0000 | 0.3937 | 0.0000 | -0.0764 | 0.0000 | 0.0000 | 0.1738 | 0.0013 | 0.8249 |

## CAMC Pairwise With Clustered Confidence Intervals

| dataset | comparison | metric | estimate [95% CI] |
| --- | --- | --- | --- |
| rebench | CAMC-static minus static anchor | safety_augmented_cost_medium | 0.0344 [0.0326, 0.0358] |
| rebench | CAMC-static minus static anchor | success_rate | -0.0034 [-0.0038, -0.0029] |
| rebench | CAMC-static minus static anchor | overload_rate | 0.0000 [0.0000, 0.0001] |
| rebench | CAMC-static minus static anchor | fallback_rate | 0.3599 [0.3505, 0.3689] |
| rebench | CAMC-static minus static anchor | camc_activation_rate | 0.2415 [0.2342, 0.2489] |
| rebench | CAMC-static minus static anchor | camc_post_switch_violation_rate | 0.0000 [0.0000, 0.0000] |
| rebench | CAMC-RSRC minus RSRC anchor | safety_augmented_cost_medium | 0.0000 [-0.0014, 0.0014] |
| rebench | CAMC-RSRC minus RSRC anchor | success_rate | -0.0060 [-0.0066, -0.0054] |
| rebench | CAMC-RSRC minus RSRC anchor | overload_rate | 0.0000 [0.0000, 0.0001] |
| rebench | CAMC-RSRC minus RSRC anchor | fallback_rate | 0.0277 [0.0243, 0.0315] |
| rebench | CAMC-RSRC minus RSRC anchor | camc_activation_rate | 0.0880 [0.0841, 0.0916] |
| rebench | CAMC-RSRC minus RSRC anchor | camc_post_switch_violation_rate | 0.0023 [0.0008, 0.0039] |
| rebench | CAMC-SE-MPC minus static anchor | safety_augmented_cost_medium | 0.0305 [0.0269, 0.0338] |
| rebench | CAMC-SE-MPC minus static anchor | success_rate | -0.0296 [-0.0317, -0.0277] |
| rebench | CAMC-SE-MPC minus static anchor | overload_rate | 0.0001 [0.0000, 0.0002] |
| rebench | CAMC-SE-MPC minus static anchor | fallback_rate | 0.4657 [0.4553, 0.4761] |
| rebench | CAMC-SE-MPC minus static anchor | camc_activation_rate | 0.4982 [0.4884, 0.5078] |
| rebench | CAMC-SE-MPC minus static anchor | camc_post_switch_violation_rate | 0.0017 [0.0011, 0.0023] |
| rebench | CAMC-SE-MPC minus SE-MPC candidate | safety_augmented_cost_medium | -0.0044 [-0.0079, -0.0011] |
| rebench | CAMC-SE-MPC minus SE-MPC candidate | success_rate | -0.0248 [-0.0269, -0.0229] |
| rebench | CAMC-SE-MPC minus SE-MPC candidate | overload_rate | 0.0000 [0.0000, 0.0001] |
| rebench | CAMC-SE-MPC minus SE-MPC candidate | fallback_rate | 0.0415 [0.0348, 0.0481] |
| rebench | CAMC-SE-MPC minus SE-MPC candidate | camc_activation_rate | 0.4982 [0.4884, 0.5078] |
| rebench | CAMC-SE-MPC minus SE-MPC candidate | camc_post_switch_violation_rate | 0.0017 [0.0011, 0.0023] |
| rebench | Pareto-CAMC-static minus static anchor | safety_augmented_cost_medium | 0.0000 [0.0000, 0.0000] |
| rebench | Pareto-CAMC-static minus static anchor | success_rate | 0.0000 [0.0000, 0.0000] |
| rebench | Pareto-CAMC-static minus static anchor | overload_rate | 0.0000 [0.0000, 0.0000] |
| rebench | Pareto-CAMC-static minus static anchor | fallback_rate | 0.3102 [0.3014, 0.3187] |
| rebench | Pareto-CAMC-static minus static anchor | camc_activation_rate | 0.0000 [0.0000, 0.0000] |
| rebench | Pareto-CAMC-static minus static anchor | camc_post_switch_violation_rate | 0.0000 [0.0000, 0.0000] |
| rebench | Pareto-CAMC-RSRC minus RSRC anchor | safety_augmented_cost_medium | 0.0000 [0.0000, 0.0000] |
| rebench | Pareto-CAMC-RSRC minus RSRC anchor | success_rate | 0.0000 [0.0000, 0.0000] |
| rebench | Pareto-CAMC-RSRC minus RSRC anchor | overload_rate | 0.0000 [0.0000, 0.0000] |
| rebench | Pareto-CAMC-RSRC minus RSRC anchor | fallback_rate | 0.0000 [0.0000, 0.0000] |
| rebench | Pareto-CAMC-RSRC minus RSRC anchor | camc_activation_rate | 0.0000 [0.0000, 0.0000] |
| rebench | Pareto-CAMC-RSRC minus RSRC anchor | camc_post_switch_violation_rate | 0.0000 [0.0000, 0.0000] |
| rebench | Pareto-CAMC-SE-MPC minus static anchor | safety_augmented_cost_medium | 0.0245 [0.0220, 0.0269] |
| rebench | Pareto-CAMC-SE-MPC minus static anchor | success_rate | 0.0195 [0.0179, 0.0213] |
| rebench | Pareto-CAMC-SE-MPC minus static anchor | overload_rate | 0.0000 [0.0000, 0.0000] |
| rebench | Pareto-CAMC-SE-MPC minus static anchor | fallback_rate | 0.3753 [0.3663, 0.3851] |
| rebench | Pareto-CAMC-SE-MPC minus static anchor | camc_activation_rate | 0.2016 [0.1972, 0.2059] |
| rebench | Pareto-CAMC-SE-MPC minus static anchor | camc_post_switch_violation_rate | 0.0005 [0.0001, 0.0010] |
| rebench | Pareto-CAMC-SE-MPC minus SE-MPC candidate | safety_augmented_cost_medium | -0.0104 [-0.0136, -0.0072] |
| rebench | Pareto-CAMC-SE-MPC minus SE-MPC candidate | success_rate | 0.0243 [0.0226, 0.0264] |
| rebench | Pareto-CAMC-SE-MPC minus SE-MPC candidate | overload_rate | -0.0001 [-0.0002, 0.0000] |
| rebench | Pareto-CAMC-SE-MPC minus SE-MPC candidate | fallback_rate | -0.0489 [-0.0529, -0.0455] |
| rebench | Pareto-CAMC-SE-MPC minus SE-MPC candidate | camc_activation_rate | 0.2016 [0.1972, 0.2059] |
| rebench | Pareto-CAMC-SE-MPC minus SE-MPC candidate | camc_post_switch_violation_rate | 0.0005 [0.0001, 0.0010] |
| smith | CAMC-static minus static anchor | safety_augmented_cost_medium | 0.0002 [0.0001, 0.0004] |
| smith | CAMC-static minus static anchor | success_rate | 0.0000 [0.0000, 0.0000] |
| smith | CAMC-static minus static anchor | overload_rate | 0.0000 [0.0000, 0.0000] |
| smith | CAMC-static minus static anchor | fallback_rate | 0.8230 [0.8153, 0.8303] |
| smith | CAMC-static minus static anchor | camc_activation_rate | 0.0011 [0.0008, 0.0015] |
| smith | CAMC-static minus static anchor | camc_post_switch_violation_rate | 0.0000 [0.0000, 0.0000] |
| smith | CAMC-RSRC minus RSRC anchor | safety_augmented_cost_medium | -0.0105 [-0.0133, -0.0078] |
| smith | CAMC-RSRC minus RSRC anchor | success_rate | -0.0131 [-0.0144, -0.0120] |
| smith | CAMC-RSRC minus RSRC anchor | overload_rate | 0.0003 [0.0001, 0.0005] |
| smith | CAMC-RSRC minus RSRC anchor | fallback_rate | -0.0197 [-0.0222, -0.0168] |
| smith | CAMC-RSRC minus RSRC anchor | camc_activation_rate | 0.1485 [0.1417, 0.1558] |
| smith | CAMC-RSRC minus RSRC anchor | camc_post_switch_violation_rate | 0.0010 [0.0002, 0.0018] |
| smith | CAMC-SE-MPC minus static anchor | safety_augmented_cost_medium | 0.0078 [0.0050, 0.0106] |
| smith | CAMC-SE-MPC minus static anchor | success_rate | -0.0135 [-0.0148, -0.0123] |
| smith | CAMC-SE-MPC minus static anchor | overload_rate | 0.0005 [0.0003, 0.0008] |
| smith | CAMC-SE-MPC minus static anchor | fallback_rate | 0.8287 [0.8206, 0.8365] |
| smith | CAMC-SE-MPC minus static anchor | camc_activation_rate | 0.1463 [0.1396, 0.1540] |
| smith | CAMC-SE-MPC minus static anchor | camc_post_switch_violation_rate | 0.0005 [0.0002, 0.0013] |
| smith | CAMC-SE-MPC minus SE-MPC candidate | safety_augmented_cost_medium | -0.0089 [-0.0118, -0.0062] |
| smith | CAMC-SE-MPC minus SE-MPC candidate | success_rate | -0.0130 [-0.0143, -0.0118] |
| smith | CAMC-SE-MPC minus SE-MPC candidate | overload_rate | 0.0003 [0.0001, 0.0004] |
| smith | CAMC-SE-MPC minus SE-MPC candidate | fallback_rate | -0.0182 [-0.0209, -0.0155] |
| smith | CAMC-SE-MPC minus SE-MPC candidate | camc_activation_rate | 0.1463 [0.1396, 0.1540] |
| smith | CAMC-SE-MPC minus SE-MPC candidate | camc_post_switch_violation_rate | 0.0005 [0.0002, 0.0013] |
| smith | Pareto-CAMC-static minus static anchor | safety_augmented_cost_medium | 0.0000 [0.0000, 0.0000] |
| smith | Pareto-CAMC-static minus static anchor | success_rate | 0.0000 [0.0000, 0.0000] |
| smith | Pareto-CAMC-static minus static anchor | overload_rate | 0.0000 [0.0000, 0.0000] |
| smith | Pareto-CAMC-static minus static anchor | fallback_rate | 0.8228 [0.8151, 0.8302] |
| smith | Pareto-CAMC-static minus static anchor | camc_activation_rate | 0.0000 [0.0000, 0.0000] |
| smith | Pareto-CAMC-static minus static anchor | camc_post_switch_violation_rate | 0.0000 [0.0000, 0.0000] |
| smith | Pareto-CAMC-RSRC minus RSRC anchor | safety_augmented_cost_medium | -0.0126 [-0.0142, -0.0112] |
| smith | Pareto-CAMC-RSRC minus RSRC anchor | success_rate | 0.0024 [0.0019, 0.0029] |
| smith | Pareto-CAMC-RSRC minus RSRC anchor | overload_rate | -0.0001 [-0.0003, 0.0001] |
| smith | Pareto-CAMC-RSRC minus RSRC anchor | fallback_rate | -0.0141 [-0.0157, -0.0126] |
| smith | Pareto-CAMC-RSRC minus RSRC anchor | camc_activation_rate | 0.0193 [0.0182, 0.0203] |
| smith | Pareto-CAMC-RSRC minus RSRC anchor | camc_post_switch_violation_rate | 0.0000 [0.0000, 0.0000] |
| smith | Pareto-CAMC-SE-MPC minus static anchor | safety_augmented_cost_medium | 0.0047 [0.0034, 0.0058] |
| smith | Pareto-CAMC-SE-MPC minus static anchor | success_rate | 0.0013 [0.0008, 0.0017] |
| smith | Pareto-CAMC-SE-MPC minus static anchor | overload_rate | 0.0001 [-0.0000, 0.0002] |
| smith | Pareto-CAMC-SE-MPC minus static anchor | fallback_rate | 0.8316 [0.8246, 0.8386] |
| smith | Pareto-CAMC-SE-MPC minus static anchor | camc_activation_rate | 0.0161 [0.0150, 0.0171] |
| smith | Pareto-CAMC-SE-MPC minus static anchor | camc_post_switch_violation_rate | 0.0000 [0.0000, 0.0000] |
| smith | Pareto-CAMC-SE-MPC minus SE-MPC candidate | safety_augmented_cost_medium | -0.0120 [-0.0140, -0.0104] |
| smith | Pareto-CAMC-SE-MPC minus SE-MPC candidate | success_rate | 0.0018 [0.0011, 0.0024] |
| smith | Pareto-CAMC-SE-MPC minus SE-MPC candidate | overload_rate | -0.0002 [-0.0003, 0.0000] |
| smith | Pareto-CAMC-SE-MPC minus SE-MPC candidate | fallback_rate | -0.0154 [-0.0170, -0.0137] |
| smith | Pareto-CAMC-SE-MPC minus SE-MPC candidate | camc_activation_rate | 0.0161 [0.0150, 0.0171] |
| smith | Pareto-CAMC-SE-MPC minus SE-MPC candidate | camc_post_switch_violation_rate | 0.0000 [0.0000, 0.0000] |
| test | CAMC-static minus static anchor | safety_augmented_cost_medium | 0.0376 [0.0355, 0.0396] |
| test | CAMC-static minus static anchor | success_rate | -0.0051 [-0.0058, -0.0043] |
| test | CAMC-static minus static anchor | overload_rate | 0.0000 [0.0000, 0.0001] |
| test | CAMC-static minus static anchor | fallback_rate | 0.4036 [0.3933, 0.4136] |
| test | CAMC-static minus static anchor | camc_activation_rate | 0.3625 [0.3536, 0.3715] |
| test | CAMC-static minus static anchor | camc_post_switch_violation_rate | 0.0001 [0.0000, 0.0004] |
| test | CAMC-RSRC minus RSRC anchor | safety_augmented_cost_medium | 0.0004 [-0.0008, 0.0016] |
| test | CAMC-RSRC minus RSRC anchor | success_rate | -0.0041 [-0.0048, -0.0035] |
| test | CAMC-RSRC minus RSRC anchor | overload_rate | 0.0000 [0.0000, 0.0000] |
| test | CAMC-RSRC minus RSRC anchor | fallback_rate | 0.0165 [0.0147, 0.0184] |
| test | CAMC-RSRC minus RSRC anchor | camc_activation_rate | 0.0729 [0.0696, 0.0760] |
| test | CAMC-RSRC minus RSRC anchor | camc_post_switch_violation_rate | 0.0034 [0.0017, 0.0054] |
| test | CAMC-SE-MPC minus static anchor | safety_augmented_cost_medium | 0.0283 [0.0246, 0.0316] |
| test | CAMC-SE-MPC minus static anchor | success_rate | -0.0296 [-0.0320, -0.0273] |
| test | CAMC-SE-MPC minus static anchor | overload_rate | 0.0001 [-0.0001, 0.0002] |
| test | CAMC-SE-MPC minus static anchor | fallback_rate | 0.4506 [0.4420, 0.4598] |
| test | CAMC-SE-MPC minus static anchor | camc_activation_rate | 0.5133 [0.5041, 0.5230] |
| test | CAMC-SE-MPC minus static anchor | camc_post_switch_violation_rate | 0.0009 [0.0005, 0.0013] |
| test | CAMC-SE-MPC minus SE-MPC candidate | safety_augmented_cost_medium | -0.0033 [-0.0060, -0.0006] |
| test | CAMC-SE-MPC minus SE-MPC candidate | success_rate | -0.0267 [-0.0290, -0.0245] |
| test | CAMC-SE-MPC minus SE-MPC candidate | overload_rate | 0.0000 [-0.0001, 0.0001] |
| test | CAMC-SE-MPC minus SE-MPC candidate | fallback_rate | 0.0161 [0.0110, 0.0213] |
| test | CAMC-SE-MPC minus SE-MPC candidate | camc_activation_rate | 0.5133 [0.5041, 0.5230] |
| test | CAMC-SE-MPC minus SE-MPC candidate | camc_post_switch_violation_rate | 0.0009 [0.0005, 0.0013] |
| test | Pareto-CAMC-static minus static anchor | safety_augmented_cost_medium | 0.0000 [0.0000, 0.0000] |
| test | Pareto-CAMC-static minus static anchor | success_rate | 0.0000 [0.0000, 0.0000] |
| test | Pareto-CAMC-static minus static anchor | overload_rate | 0.0000 [0.0000, 0.0000] |
| test | Pareto-CAMC-static minus static anchor | fallback_rate | 0.3145 [0.3042, 0.3252] |
| test | Pareto-CAMC-static minus static anchor | camc_activation_rate | 0.0000 [0.0000, 0.0000] |
| test | Pareto-CAMC-static minus static anchor | camc_post_switch_violation_rate | 0.0000 [0.0000, 0.0000] |
| test | Pareto-CAMC-RSRC minus RSRC anchor | safety_augmented_cost_medium | 0.0000 [0.0000, 0.0000] |
| test | Pareto-CAMC-RSRC minus RSRC anchor | success_rate | 0.0000 [0.0000, 0.0000] |
| test | Pareto-CAMC-RSRC minus RSRC anchor | overload_rate | 0.0000 [0.0000, 0.0000] |
| test | Pareto-CAMC-RSRC minus RSRC anchor | fallback_rate | 0.0000 [0.0000, 0.0000] |
| test | Pareto-CAMC-RSRC minus RSRC anchor | camc_activation_rate | 0.0000 [0.0000, 0.0000] |
| test | Pareto-CAMC-RSRC minus RSRC anchor | camc_post_switch_violation_rate | 0.0000 [0.0000, 0.0000] |
| test | Pareto-CAMC-SE-MPC minus static anchor | safety_augmented_cost_medium | 0.0193 [0.0165, 0.0219] |
| test | Pareto-CAMC-SE-MPC minus static anchor | success_rate | 0.0201 [0.0187, 0.0215] |
| test | Pareto-CAMC-SE-MPC minus static anchor | overload_rate | 0.0000 [-0.0001, 0.0001] |
| test | Pareto-CAMC-SE-MPC minus static anchor | fallback_rate | 0.4268 [0.4174, 0.4359] |
| test | Pareto-CAMC-SE-MPC minus static anchor | camc_activation_rate | 0.2631 [0.2565, 0.2700] |
| test | Pareto-CAMC-SE-MPC minus static anchor | camc_post_switch_violation_rate | 0.0002 [0.0000, 0.0005] |
| test | Pareto-CAMC-SE-MPC minus SE-MPC candidate | safety_augmented_cost_medium | -0.0124 [-0.0157, -0.0092] |
| test | Pareto-CAMC-SE-MPC minus SE-MPC candidate | success_rate | 0.0230 [0.0215, 0.0245] |
| test | Pareto-CAMC-SE-MPC minus SE-MPC candidate | overload_rate | -0.0000 [-0.0001, 0.0001] |
| test | Pareto-CAMC-SE-MPC minus SE-MPC candidate | fallback_rate | -0.0078 [-0.0127, -0.0027] |
| test | Pareto-CAMC-SE-MPC minus SE-MPC candidate | camc_activation_rate | 0.2631 [0.2565, 0.2700] |
| test | Pareto-CAMC-SE-MPC minus SE-MPC candidate | camc_post_switch_violation_rate | 0.0002 [0.0000, 0.0005] |
| verified | CAMC-static minus static anchor | safety_augmented_cost_medium | 0.0043 [0.0034, 0.0053] |
| verified | CAMC-static minus static anchor | success_rate | -0.0039 [-0.0048, -0.0030] |
| verified | CAMC-static minus static anchor | overload_rate | 0.0000 [0.0000, 0.0000] |
| verified | CAMC-static minus static anchor | fallback_rate | 0.3420 [0.3294, 0.3552] |
| verified | CAMC-static minus static anchor | camc_activation_rate | 0.2148 [0.2061, 0.2246] |
| verified | CAMC-static minus static anchor | camc_post_switch_violation_rate | 0.0000 [0.0000, 0.0000] |
| verified | CAMC-RSRC minus RSRC anchor | safety_augmented_cost_medium | 0.0038 [0.0027, 0.0049] |
| verified | CAMC-RSRC minus RSRC anchor | success_rate | -0.0043 [-0.0054, -0.0032] |
| verified | CAMC-RSRC minus RSRC anchor | overload_rate | 0.0000 [0.0000, 0.0000] |
| verified | CAMC-RSRC minus RSRC anchor | fallback_rate | 0.0217 [0.0180, 0.0257] |
| verified | CAMC-RSRC minus RSRC anchor | camc_activation_rate | 0.0628 [0.0589, 0.0670] |
| verified | CAMC-RSRC minus RSRC anchor | camc_post_switch_violation_rate | 0.0000 [0.0000, 0.0000] |
| verified | CAMC-SE-MPC minus static anchor | safety_augmented_cost_medium | 0.0176 [0.0142, 0.0207] |
| verified | CAMC-SE-MPC minus static anchor | success_rate | -0.0334 [-0.0364, -0.0302] |
| verified | CAMC-SE-MPC minus static anchor | overload_rate | 0.0000 [0.0000, 0.0000] |
| verified | CAMC-SE-MPC minus static anchor | fallback_rate | 0.4532 [0.4402, 0.4666] |
| verified | CAMC-SE-MPC minus static anchor | camc_activation_rate | 0.4979 [0.4825, 0.5116] |
| verified | CAMC-SE-MPC minus static anchor | camc_post_switch_violation_rate | 0.0000 [0.0000, 0.0000] |
| verified | CAMC-SE-MPC minus SE-MPC candidate | safety_augmented_cost_medium | 0.0085 [0.0052, 0.0121] |
| verified | CAMC-SE-MPC minus SE-MPC candidate | success_rate | -0.0269 [-0.0299, -0.0241] |
| verified | CAMC-SE-MPC minus SE-MPC candidate | overload_rate | 0.0000 [0.0000, 0.0000] |
| verified | CAMC-SE-MPC minus SE-MPC candidate | fallback_rate | 0.0375 [0.0324, 0.0420] |
| verified | CAMC-SE-MPC minus SE-MPC candidate | camc_activation_rate | 0.4979 [0.4825, 0.5116] |
| verified | CAMC-SE-MPC minus SE-MPC candidate | camc_post_switch_violation_rate | 0.0000 [0.0000, 0.0000] |
| verified | Pareto-CAMC-static minus static anchor | safety_augmented_cost_medium | 0.0000 [0.0000, 0.0000] |
| verified | Pareto-CAMC-static minus static anchor | success_rate | 0.0000 [0.0000, 0.0000] |
| verified | Pareto-CAMC-static minus static anchor | overload_rate | 0.0000 [0.0000, 0.0000] |
| verified | Pareto-CAMC-static minus static anchor | fallback_rate | 0.2993 [0.2877, 0.3116] |
| verified | Pareto-CAMC-static minus static anchor | camc_activation_rate | 0.0000 [0.0000, 0.0000] |
| verified | Pareto-CAMC-static minus static anchor | camc_post_switch_violation_rate | 0.0000 [0.0000, 0.0000] |
| verified | Pareto-CAMC-RSRC minus RSRC anchor | safety_augmented_cost_medium | 0.0000 [0.0000, 0.0000] |
| verified | Pareto-CAMC-RSRC minus RSRC anchor | success_rate | 0.0000 [0.0000, 0.0000] |
| verified | Pareto-CAMC-RSRC minus RSRC anchor | overload_rate | 0.0000 [0.0000, 0.0000] |
| verified | Pareto-CAMC-RSRC minus RSRC anchor | fallback_rate | 0.0000 [0.0000, 0.0000] |
| verified | Pareto-CAMC-RSRC minus RSRC anchor | camc_activation_rate | 0.0000 [0.0000, 0.0000] |
| verified | Pareto-CAMC-RSRC minus RSRC anchor | camc_post_switch_violation_rate | 0.0000 [0.0000, 0.0000] |
| verified | Pareto-CAMC-SE-MPC minus static anchor | safety_augmented_cost_medium | -0.0075 [-0.0098, -0.0052] |
| verified | Pareto-CAMC-SE-MPC minus static anchor | success_rate | 0.0179 [0.0156, 0.0204] |
| verified | Pareto-CAMC-SE-MPC minus static anchor | overload_rate | 0.0000 [0.0000, 0.0000] |
| verified | Pareto-CAMC-SE-MPC minus static anchor | fallback_rate | 0.3796 [0.3663, 0.3926] |
| verified | Pareto-CAMC-SE-MPC minus static anchor | camc_activation_rate | 0.1906 [0.1843, 0.1968] |
| verified | Pareto-CAMC-SE-MPC minus static anchor | camc_post_switch_violation_rate | 0.0000 [0.0000, 0.0000] |
| verified | Pareto-CAMC-SE-MPC minus SE-MPC candidate | safety_augmented_cost_medium | -0.0165 [-0.0192, -0.0136] |
| verified | Pareto-CAMC-SE-MPC minus SE-MPC candidate | success_rate | 0.0244 [0.0216, 0.0273] |
| verified | Pareto-CAMC-SE-MPC minus SE-MPC candidate | overload_rate | 0.0000 [0.0000, 0.0000] |
| verified | Pareto-CAMC-SE-MPC minus SE-MPC candidate | fallback_rate | -0.0361 [-0.0433, -0.0284] |
| verified | Pareto-CAMC-SE-MPC minus SE-MPC candidate | camc_activation_rate | 0.1906 [0.1843, 0.1968] |
| verified | Pareto-CAMC-SE-MPC minus SE-MPC candidate | camc_post_switch_violation_rate | 0.0000 [0.0000, 0.0000] |

## CAMC Activation By Certified Slack

| dataset | controller | slack_quantile | rows | activation_rate | mean_certified_margin | mean_certified_slack | post_switch_violation_rate |
| --- | --- | --- | --- | --- | --- | --- | --- |
| rebench | camc_rsrc_anchor | Q1 | 3326 | 0.0000 |  | -0.1700 |  |
| rebench | camc_rsrc_anchor | Q2 | 8057 | 0.0000 |  | -0.0497 |  |
| rebench | camc_rsrc_anchor | Q3 | 10205 | 0.0847 | -0.0704 | -0.0008 | 0.0069 |
| rebench | camc_rsrc_anchor | Q4 | 9082 | 0.2137 | -0.0594 | 0.0368 | 0.0010 |
| rebench | camc_rsrc_anchor | Q5 | 7730 | 0.0744 | -0.0811 | 0.1104 | 0.0000 |
| rebench | camc_sempc_candidate | Q1 | 3393 | 0.0000 |  | -0.1734 |  |
| rebench | camc_sempc_candidate | Q2 | 7354 | 0.0000 |  | -0.0502 |  |
| rebench | camc_sempc_candidate | Q3 | 8237 | 0.2678 | 0.0567 | -0.0018 | 0.0054 |
| rebench | camc_sempc_candidate | Q4 | 10525 | 0.7862 | 0.1825 | 0.0380 | 0.0024 |
| rebench | camc_sempc_candidate | Q5 | 8891 | 0.9728 | 0.2166 | 0.1082 | 0.0000 |
| rebench | camc_static_anchor | Q1 | 2448 | 0.0000 |  | -0.1847 |  |
| rebench | camc_static_anchor | Q2 | 6375 | 0.0000 |  | -0.0489 |  |
| rebench | camc_static_anchor | Q3 | 9201 | 0.0790 | -0.1571 | -0.0006 | 0.0000 |
| rebench | camc_static_anchor | Q4 | 9013 | 0.2930 | -0.0582 | 0.0388 | 0.0000 |
| rebench | camc_static_anchor | Q5 | 11363 | 0.5197 | -0.0147 | 0.1131 | 0.0000 |
| rebench | pareto_camc_rsrc_anchor | Q1 | 3120 | 0.0000 |  | -0.1693 |  |
| rebench | pareto_camc_rsrc_anchor | Q2 | 7846 | 0.0000 |  | -0.0496 |  |
| rebench | pareto_camc_rsrc_anchor | Q3 | 9955 | 0.0000 | -0.1004 | -0.0010 |  |
| rebench | pareto_camc_rsrc_anchor | Q4 | 8376 | 0.0000 | -0.1042 | 0.0380 |  |
| rebench | pareto_camc_rsrc_anchor | Q5 | 9103 | 0.0000 | -0.0992 | 0.1119 |  |
| rebench | pareto_camc_sempc_candidate | Q1 | 2485 | 0.0000 |  | -0.1822 |  |
| rebench | pareto_camc_sempc_candidate | Q2 | 7056 | 0.0000 |  | -0.0487 |  |
| rebench | pareto_camc_sempc_candidate | Q3 | 7807 | 0.1444 | -0.0523 | -0.0015 | 0.0009 |
| rebench | pareto_camc_sempc_candidate | Q4 | 10914 | 0.3170 | -0.0517 | 0.0379 | 0.0009 |
| rebench | pareto_camc_sempc_candidate | Q5 | 10138 | 0.3113 | -0.0552 | 0.1137 | 0.0000 |
| rebench | pareto_camc_static_anchor | Q1 | 2167 | 0.0000 |  | -0.1935 |  |
| rebench | pareto_camc_static_anchor | Q2 | 5173 | 0.0000 |  | -0.0488 |  |
| rebench | pareto_camc_static_anchor | Q3 | 5363 | 0.0000 | -0.1013 | -0.0031 |  |
| rebench | pareto_camc_static_anchor | Q4 | 7731 | 0.0000 | -0.1034 | 0.0394 |  |
| rebench | pareto_camc_static_anchor | Q5 | 17966 | 0.0000 | -0.0999 | 0.1323 |  |
| smith | camc_rsrc_anchor | Q1 | 20083 | 0.0000 |  | -0.2330 |  |
| smith | camc_rsrc_anchor | Q2 | 8183 | 0.0000 |  | -0.0555 |  |
| smith | camc_rsrc_anchor | Q3 | 4708 | 0.1640 | 0.0022 | -0.0033 | 0.0052 |
| smith | camc_rsrc_anchor | Q4 | 3615 | 0.8658 | 0.1802 | 0.0352 | 0.0003 |
| smith | camc_rsrc_anchor | Q5 | 1811 | 0.9945 | 0.2313 | 0.1038 | 0.0000 |
| smith | camc_sempc_candidate | Q1 | 20096 | 0.0000 |  | -0.2330 |  |
| smith | camc_sempc_candidate | Q2 | 8197 | 0.0000 |  | -0.0555 |  |
| smith | camc_sempc_candidate | Q3 | 4715 | 0.1586 | -0.0021 | -0.0032 | 0.0040 |
| smith | camc_sempc_candidate | Q4 | 3606 | 0.8575 | 0.1761 | 0.0353 | 0.0000 |
| smith | camc_sempc_candidate | Q5 | 1786 | 0.9955 | 0.2183 | 0.1035 | 0.0000 |
| smith | camc_static_anchor | Q1 | 20050 | 0.0000 |  | -0.2322 |  |
| smith | camc_static_anchor | Q2 | 8507 | 0.0000 |  | -0.0549 |  |
| smith | camc_static_anchor | Q3 | 5452 | 0.0000 | -0.1821 | -0.0023 |  |
| smith | camc_static_anchor | Q4 | 2991 | 0.0017 | -0.0829 | 0.0354 | 0.0000 |
| smith | camc_static_anchor | Q5 | 1400 | 0.0279 | -0.0179 | 0.1017 | 0.0000 |
| smith | pareto_camc_rsrc_anchor | Q1 | 20295 | 0.0000 |  | -0.2313 |  |
| smith | pareto_camc_rsrc_anchor | Q2 | 8724 | 0.0000 |  | -0.0550 |  |
| smith | pareto_camc_rsrc_anchor | Q3 | 4161 | 0.0409 | -0.0916 | -0.0041 | 0.0000 |
| smith | pareto_camc_rsrc_anchor | Q4 | 3553 | 0.1047 | -0.0958 | 0.0368 | 0.0000 |
| smith | pareto_camc_rsrc_anchor | Q5 | 1667 | 0.1194 | -0.0934 | 0.0951 | 0.0000 |
| smith | pareto_camc_sempc_candidate | Q1 | 20253 | 0.0000 |  | -0.2315 |  |
| smith | pareto_camc_sempc_candidate | Q2 | 8688 | 0.0000 |  | -0.0550 |  |
| smith | pareto_camc_sempc_candidate | Q3 | 4154 | 0.0361 | -0.0941 | -0.0040 | 0.0000 |
| smith | pareto_camc_sempc_candidate | Q4 | 3523 | 0.0897 | -0.0986 | 0.0368 | 0.0000 |
| smith | pareto_camc_sempc_candidate | Q5 | 1782 | 0.0859 | -0.0986 | 0.0982 | 0.0000 |
| smith | pareto_camc_static_anchor | Q1 | 20047 | 0.0000 |  | -0.2322 |  |
| smith | pareto_camc_static_anchor | Q2 | 8505 | 0.0000 |  | -0.0549 |  |
| smith | pareto_camc_static_anchor | Q3 | 3994 | 0.0000 | -0.1127 | -0.0044 |  |
| smith | pareto_camc_static_anchor | Q4 | 3389 | 0.0000 | -0.1145 | 0.0371 |  |
| smith | pareto_camc_static_anchor | Q5 | 2465 | 0.0000 | -0.1118 | 0.1053 |  |
| test | camc_rsrc_anchor | Q1 | 2822 | 0.0000 |  | -0.1415 |  |
| test | camc_rsrc_anchor | Q2 | 8660 | 0.0000 |  | -0.0499 |  |
| test | camc_rsrc_anchor | Q3 | 11059 | 0.0650 | -0.0687 | -0.0010 | 0.0125 |
| test | camc_rsrc_anchor | Q4 | 8663 | 0.1951 | -0.0584 | 0.0369 | 0.0000 |
| test | camc_rsrc_anchor | Q5 | 7196 | 0.0543 | -0.0761 | 0.1073 | 0.0000 |
| test | camc_sempc_candidate | Q1 | 2651 | 0.0000 |  | -0.1459 |  |
| test | camc_sempc_candidate | Q2 | 7601 | 0.0000 |  | -0.0507 |  |
| test | camc_sempc_candidate | Q3 | 8843 | 0.2820 | 0.0608 | -0.0019 | 0.0024 |
| test | camc_sempc_candidate | Q4 | 10541 | 0.8174 | 0.1928 | 0.0380 | 0.0013 |
| test | camc_sempc_candidate | Q5 | 8764 | 0.9815 | 0.2280 | 0.1041 | 0.0000 |
| test | camc_static_anchor | Q1 | 2359 | 0.0000 |  | -0.1467 |  |
| test | camc_static_anchor | Q2 | 8107 | 0.0000 |  | -0.0492 |  |
| test | camc_static_anchor | Q3 | 10644 | 0.1378 | -0.1491 | -0.0008 | 0.0014 |
| test | camc_static_anchor | Q4 | 8526 | 0.5900 | -0.0353 | 0.0380 | 0.0000 |
| test | camc_static_anchor | Q5 | 8764 | 0.8470 | 0.0105 | 0.1083 | 0.0000 |
| test | pareto_camc_rsrc_anchor | Q1 | 2711 | 0.0000 |  | -0.1415 |  |
| test | pareto_camc_rsrc_anchor | Q2 | 8686 | 0.0000 |  | -0.0498 |  |
| test | pareto_camc_rsrc_anchor | Q3 | 10857 | 0.0000 | -0.0902 | -0.0012 |  |
| test | pareto_camc_rsrc_anchor | Q4 | 8068 | 0.0000 | -0.0942 | 0.0376 |  |
| test | pareto_camc_rsrc_anchor | Q5 | 8078 | 0.0000 | -0.0886 | 0.1082 |  |
| test | pareto_camc_sempc_candidate | Q1 | 2454 | 0.0000 |  | -0.1457 |  |
| test | pareto_camc_sempc_candidate | Q2 | 8625 | 0.0000 |  | -0.0490 |  |
| test | pareto_camc_sempc_candidate | Q3 | 9191 | 0.1654 | -0.0322 | -0.0015 | 0.0013 |
| test | pareto_camc_sempc_candidate | Q4 | 11552 | 0.4584 | -0.0180 | 0.0371 | 0.0000 |
| test | pareto_camc_sempc_candidate | Q5 | 6578 | 0.4997 | -0.0092 | 0.1001 | 0.0000 |
| test | pareto_camc_static_anchor | Q1 | 1873 | 0.0000 |  | -0.1558 |  |
| test | pareto_camc_static_anchor | Q2 | 5784 | 0.0000 |  | -0.0492 |  |
| test | pareto_camc_static_anchor | Q3 | 5882 | 0.0000 | -0.0909 | -0.0030 |  |
| test | pareto_camc_static_anchor | Q4 | 7990 | 0.0000 | -0.0935 | 0.0390 |  |
| test | pareto_camc_static_anchor | Q5 | 16871 | 0.0000 | -0.0894 | 0.1275 |  |
| verified | camc_rsrc_anchor | Q1 | 926 | 0.0000 |  | -0.1389 |  |
| verified | camc_rsrc_anchor | Q2 | 3308 | 0.0000 |  | -0.0489 |  |
| verified | camc_rsrc_anchor | Q3 | 4701 | 0.0483 | -0.0826 | -0.0009 | 0.0000 |
| verified | camc_rsrc_anchor | Q4 | 4015 | 0.1587 | -0.0713 | 0.0373 | 0.0000 |
| verified | camc_rsrc_anchor | Q5 | 3050 | 0.0462 | -0.0921 | 0.1037 | 0.0000 |
| verified | camc_sempc_candidate | Q1 | 907 | 0.0000 |  | -0.1413 |  |
| verified | camc_sempc_candidate | Q2 | 3020 | 0.0000 |  | -0.0491 |  |
| verified | camc_sempc_candidate | Q3 | 3694 | 0.2374 | 0.0476 | -0.0017 | 0.0000 |
| verified | camc_sempc_candidate | Q4 | 4918 | 0.7546 | 0.1738 | 0.0381 | 0.0000 |
| verified | camc_sempc_candidate | Q5 | 3461 | 0.9763 | 0.2243 | 0.1009 | 0.0000 |
| verified | camc_static_anchor | Q1 | 705 | 0.0000 |  | -0.1473 |  |
| verified | camc_static_anchor | Q2 | 2576 | 0.0000 |  | -0.0478 |  |
| verified | camc_static_anchor | Q3 | 4083 | 0.0622 | -0.1625 | -0.0006 | 0.0000 |
| verified | camc_static_anchor | Q4 | 4251 | 0.2270 | -0.0764 | 0.0386 | 0.0000 |
| verified | camc_static_anchor | Q5 | 4385 | 0.5058 | -0.0157 | 0.1050 | 0.0000 |
| verified | pareto_camc_rsrc_anchor | Q1 | 891 | 0.0000 |  | -0.1392 |  |
| verified | pareto_camc_rsrc_anchor | Q2 | 3244 | 0.0000 |  | -0.0487 |  |
| verified | pareto_camc_rsrc_anchor | Q3 | 4588 | 0.0000 | -0.1072 | -0.0010 |  |
| verified | pareto_camc_rsrc_anchor | Q4 | 3809 | 0.0000 | -0.1154 | 0.0382 |  |
| verified | pareto_camc_rsrc_anchor | Q5 | 3468 | 0.0000 | -0.1055 | 0.1047 |  |
| verified | pareto_camc_sempc_candidate | Q1 | 739 | 0.0000 |  | -0.1439 |  |
| verified | pareto_camc_sempc_candidate | Q2 | 3032 | 0.0000 |  | -0.0477 |  |
| verified | pareto_camc_sempc_candidate | Q3 | 3581 | 0.1201 | -0.0589 | -0.0021 | 0.0000 |
| verified | pareto_camc_sempc_candidate | Q4 | 5170 | 0.2557 | -0.0630 | 0.0379 | 0.0000 |
| verified | pareto_camc_sempc_candidate | Q5 | 3478 | 0.3729 | -0.0509 | 0.0973 | 0.0000 |
| verified | pareto_camc_static_anchor | Q1 | 639 | 0.0000 |  | -0.1508 |  |
| verified | pareto_camc_static_anchor | Q2 | 2132 | 0.0000 |  | -0.0479 |  |
| verified | pareto_camc_static_anchor | Q3 | 2365 | 0.0000 | -0.1092 | -0.0033 |  |
| verified | pareto_camc_static_anchor | Q4 | 3619 | 0.0000 | -0.1129 | 0.0394 |  |
| verified | pareto_camc_static_anchor | Q5 | 7245 | 0.0000 | -0.1073 | 0.1238 |  |

## CAMC Activation By Shift Bucket

| dataset | controller | shift_bucket | rows | activation_rate | anchor_preservation_rate | fallback_rate | mean_certified_margin | mean_certified_slack | post_switch_violation_rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| rebench | camc_rsrc_anchor | medium | 38400 | 0.0880 | 0.9120 | 0.4526 | -0.0702 | 0.0056 | 0.0024 |
| rebench | camc_sempc_candidate | medium | 38400 | 0.4982 | 0.5018 | 0.4657 | 0.1766 | 0.0102 | 0.0017 |
| rebench | camc_static_anchor | medium | 38400 | 0.2415 | 0.7585 | 0.3599 | -0.0592 | 0.0225 | 0.0000 |
| rebench | pareto_camc_rsrc_anchor | medium | 38400 | 0.0000 | 1.0000 | 0.4248 | -0.1012 | 0.0107 |  |
| rebench | pareto_camc_sempc_candidate | medium | 38400 | 0.2016 | 0.7984 | 0.3753 | -0.0533 | 0.0198 | 0.0005 |
| rebench | pareto_camc_static_anchor | medium | 38400 | 0.0000 | 1.0000 | 0.3102 | -0.1009 | 0.0519 |  |
| smith | camc_rsrc_anchor | high | 38400 | 0.1485 | 0.8515 | 0.8276 | 0.1529 | -0.1259 | 0.0009 |
| smith | camc_sempc_candidate | high | 38400 | 0.1463 | 0.8537 | 0.8287 | 0.1455 | -0.1261 | 0.0005 |
| smith | camc_static_anchor | high | 38400 | 0.0011 | 0.9989 | 0.8230 | -0.1080 | -0.1273 | 0.0000 |
| smith | pareto_camc_rsrc_anchor | high | 38400 | 0.0193 | 0.9807 | 0.8332 | -0.0943 | -0.1277 | 0.0000 |
| smith | pareto_camc_sempc_candidate | high | 38400 | 0.0161 | 0.9839 | 0.8316 | -0.0977 | -0.1270 | 0.0000 |
| smith | pareto_camc_static_anchor | high | 38400 | 0.0000 | 1.0000 | 0.8228 | -0.1132 | -0.1238 |  |
| test | camc_rsrc_anchor | low | 38400 | 0.0729 | 0.9271 | 0.4536 | -0.0674 | 0.0065 | 0.0032 |
| test | camc_sempc_candidate | low | 38400 | 0.5133 | 0.4867 | 0.4506 | 0.1841 | 0.0137 | 0.0009 |
| test | camc_static_anchor | low | 38400 | 0.3625 | 0.6375 | 0.4036 | -0.0487 | 0.0135 | 0.0001 |
| test | pareto_camc_rsrc_anchor | low | 38400 | 0.0000 | 1.0000 | 0.4370 | -0.0910 | 0.0091 |  |
| test | pareto_camc_sempc_candidate | low | 38400 | 0.2631 | 0.7369 | 0.4268 | -0.0182 | 0.0076 | 0.0002 |
| test | pareto_camc_static_anchor | low | 38400 | 0.0000 | 1.0000 | 0.3145 | -0.0907 | 0.0487 |  |
| verified | camc_rsrc_anchor | low | 16000 | 0.0628 | 0.9372 | 0.4371 | -0.0814 | 0.0107 | 0.0000 |
| verified | camc_sempc_candidate | low | 16000 | 0.4979 | 0.5021 | 0.4532 | 0.1728 | 0.0159 | 0.0000 |
| verified | camc_static_anchor | low | 16000 | 0.2148 | 0.7852 | 0.3420 | -0.0700 | 0.0247 | 0.0000 |
| verified | pareto_camc_rsrc_anchor | low | 16000 | 0.0000 | 1.0000 | 0.4153 | -0.1096 | 0.0139 |  |
| verified | pareto_camc_sempc_candidate | low | 16000 | 0.1906 | 0.8094 | 0.3796 | -0.0581 | 0.0172 | 0.0000 |
| verified | pareto_camc_static_anchor | low | 16000 | 0.0000 | 1.0000 | 0.2993 | -0.1091 | 0.0521 |  |

## Headroom-Conditioned Drift Support

| dataset | controller | adverse_rows | adverse_negative_drift_rate | adverse_negative_delta_sq_rate | adverse_high_load_rows | adverse_high_load_negative_drift_rate | benign_rows | benign_benchmark_safe_rate | benign_mean_exact_headroom |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| rebench | camc_rsrc_anchor | 1259 | 0.6608 | 0.0119 | 4 | 1.0000 | 37141 | 0.7084 | 0.2394 |
| rebench | camc_sempc_candidate | 1414 | 0.6810 | 0.0120 | 6 | 1.0000 | 36986 | 0.7402 | 0.2255 |
| rebench | camc_static_anchor | 1151 | 0.6499 | 0.0104 | 4 | 1.0000 | 37249 | 0.7788 | 0.2573 |
| rebench | oracle_src | 1681 | 0.6460 | 0.0161 | 13 | 0.9231 | 36719 | 0.5860 | 0.1643 |
| rebench | pareto_camc_rsrc_anchor | 1179 | 0.6446 | 0.0119 | 4 | 1.0000 | 37221 | 0.7132 | 0.2443 |
| rebench | pareto_camc_sempc_candidate | 1103 | 0.6419 | 0.0100 | 4 | 1.0000 | 37297 | 0.7479 | 0.2640 |
| rebench | pareto_camc_static_anchor | 1139 | 0.6514 | 0.0105 | 4 | 1.0000 | 37261 | 0.8205 | 0.2685 |
| rebench | rsrc | 1179 | 0.6446 | 0.0119 | 4 | 1.0000 | 37221 | 0.7132 | 0.2443 |
| rebench | se_mpc | 1211 | 0.6424 | 0.0124 | 4 | 1.0000 | 37189 | 0.7183 | 0.2397 |
| smith | camc_rsrc_anchor | 9402 | 0.4533 | 0.1272 | 490 | 0.6245 | 28998 | 0.4171 | 0.2112 |
| smith | camc_sempc_candidate | 9412 | 0.4531 | 0.1270 | 491 | 0.6232 | 28988 | 0.4166 | 0.2110 |
| smith | camc_static_anchor | 9318 | 0.4537 | 0.1262 | 480 | 0.6271 | 29082 | 0.4165 | 0.2210 |
| smith | oracle_src | 8548 | 0.3920 | 0.1026 | 375 | 0.5280 | 29852 | 0.5160 | 0.1906 |
| smith | pareto_camc_rsrc_anchor | 9307 | 0.4521 | 0.1264 | 480 | 0.6229 | 29093 | 0.4008 | 0.2203 |
| smith | pareto_camc_sempc_candidate | 9308 | 0.4521 | 0.1262 | 480 | 0.6229 | 29092 | 0.4030 | 0.2204 |
| smith | pareto_camc_static_anchor | 9318 | 0.4537 | 0.1262 | 480 | 0.6271 | 29082 | 0.4168 | 0.2210 |
| smith | rsrc | 9327 | 0.4518 | 0.1272 | 489 | 0.6258 | 29073 | 0.3709 | 0.2159 |
| smith | se_mpc | 9340 | 0.4511 | 0.1272 | 490 | 0.6265 | 29060 | 0.3715 | 0.2153 |
| test | camc_rsrc_anchor | 730 | 0.7918 | 0.0096 | 5 | 1.0000 | 37670 | 0.6741 | 0.2367 |
| test | camc_sempc_candidate | 857 | 0.8133 | 0.0093 | 6 | 1.0000 | 37543 | 0.7229 | 0.2219 |
| test | camc_static_anchor | 688 | 0.7849 | 0.0102 | 5 | 1.0000 | 37712 | 0.7170 | 0.2447 |
| test | oracle_src | 975 | 0.7703 | 0.0103 | 4 | 1.0000 | 37425 | 0.6860 | 0.1620 |
| test | pareto_camc_rsrc_anchor | 696 | 0.7859 | 0.0101 | 5 | 1.0000 | 37704 | 0.6747 | 0.2402 |
| test | pareto_camc_sempc_candidate | 670 | 0.7821 | 0.0119 | 5 | 1.0000 | 37730 | 0.6829 | 0.2488 |
| test | pareto_camc_static_anchor | 668 | 0.7844 | 0.0105 | 5 | 1.0000 | 37732 | 0.7948 | 0.2620 |
| test | rsrc | 696 | 0.7859 | 0.0101 | 5 | 1.0000 | 37704 | 0.6747 | 0.2402 |
| test | se_mpc | 711 | 0.7876 | 0.0098 | 5 | 1.0000 | 37689 | 0.6812 | 0.2361 |
| verified | camc_rsrc_anchor | 276 | 0.7899 | 0.0000 | 0 |  | 15724 | 0.7137 | 0.2486 |
| verified | camc_sempc_candidate | 339 | 0.8142 | 0.0029 | 0 |  | 15661 | 0.7552 | 0.2350 |
| verified | camc_static_anchor | 253 | 0.7747 | 0.0000 | 0 |  | 15747 | 0.7866 | 0.2637 |
| verified | oracle_src | 382 | 0.7670 | 0.0000 | 0 |  | 15618 | 0.5787 | 0.1529 |
| verified | pareto_camc_rsrc_anchor | 260 | 0.7769 | 0.0000 | 0 |  | 15740 | 0.7168 | 0.2519 |
| verified | pareto_camc_sempc_candidate | 235 | 0.7532 | 0.0000 | 0 |  | 15765 | 0.7376 | 0.2705 |
| verified | pareto_camc_static_anchor | 245 | 0.7714 | 0.0000 | 0 |  | 15755 | 0.8232 | 0.2732 |
| verified | rsrc | 260 | 0.7769 | 0.0000 | 0 |  | 15740 | 0.7168 | 0.2519 |
| verified | se_mpc | 261 | 0.7778 | 0.0000 | 0 |  | 15739 | 0.7174 | 0.2509 |

## Positive-Headroom Drift Slice

| dataset | controller | rows | mean drift [95% CI] | neg. drift [95% CI] | mean_exact_headroom |
| --- | --- | --- | --- | --- | --- |
| rebench | rsrc | 51 | -0.3339 [-0.3447, -0.3219] | 1.0000 [1.0000, 1.0000] | 0.1858 |
| rebench | se_mpc | 53 | -0.3376 [-0.3495, -0.3253] | 1.0000 [1.0000, 1.0000] | 0.1873 |
| rebench | static_conservative | 47 | -0.3378 [-0.3498, -0.3254] | 1.0000 [1.0000, 1.0000] | 0.1874 |
| smith | rsrc | 633 | -0.2643 [-0.2682, -0.2605] | 1.0000 [1.0000, 1.0000] | 0.1518 |
| smith | se_mpc | 635 | -0.2646 [-0.2679, -0.2608] | 1.0000 [1.0000, 1.0000] | 0.1520 |
| smith | static_conservative | 625 | -0.2653 [-0.2687, -0.2616] | 1.0000 [1.0000, 1.0000] | 0.1523 |
| test | rsrc | 26 | -0.3331 [-0.3485, -0.3178] | 1.0000 [1.0000, 1.0000] | 0.1595 |
| test | se_mpc | 27 | -0.3305 [-0.3460, -0.3125] | 1.0000 [1.0000, 1.0000] | 0.1564 |
| test | static_conservative | 25 | -0.3377 [-0.3569, -0.3182] | 1.0000 [1.0000, 1.0000] | 0.1610 |
| verified | rsrc | 0 |  |  |  |
| verified | se_mpc | 0 |  |  |  |
| verified | static_conservative | 0 |  |  |  |

## Headroom Calibration Slices

| dataset | controller | headroom_bin | mean_certified_headroom | mean_exact_headroom | exact_headroom_positive_rate | benchmark_safe_rate | negative_drift_rate | rows |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| rebench | rsrc | <=0 | -0.1933 | -0.1388 | 0.2731 | 0.2926 | 0.6446 | 1179 |
| rebench | rsrc | (0.08,0.15] | 0.1252 | 0.1965 | 1.0000 | 0.6718 | 1.0000 | 7773 |
| rebench | rsrc | >0.15 | 0.2136 | 0.2643 | 1.0000 | 0.7383 | 1.0000 | 27896 |
| rebench | se_mpc | <=0 | -0.1911 | -0.1371 | 0.2824 | 0.2964 | 0.6424 | 1211 |
| rebench | se_mpc | (0.08,0.15] | 0.1250 | 0.1945 | 1.0000 | 0.6894 | 1.0000 | 8479 |
| rebench | se_mpc | >0.15 | 0.2094 | 0.2610 | 1.0000 | 0.7424 | 1.0000 | 27049 |
| smith | rsrc | <=0 | -0.2379 | -0.1864 | 0.0986 | 0.1157 | 0.4518 | 9327 |
| smith | rsrc | (0.08,0.15] | 0.1184 | 0.1789 | 1.0000 | 0.3206 | 1.0000 | 8022 |
| smith | rsrc | >0.15 | 0.2076 | 0.2550 | 1.0000 | 0.4263 | 1.0000 | 17303 |
| smith | se_mpc | <=0 | -0.2380 | -0.1865 | 0.0993 | 0.1160 | 0.4511 | 9340 |
| smith | se_mpc | (0.08,0.15] | 0.1185 | 0.1788 | 1.0000 | 0.3224 | 1.0000 | 8083 |
| smith | se_mpc | >0.15 | 0.2066 | 0.2545 | 1.0000 | 0.4266 | 1.0000 | 17208 |
| test | rsrc | <=0 | -0.1617 | -0.1045 | 0.3420 | 0.3434 | 0.7859 | 696 |
| test | rsrc | (0.08,0.15] | 0.1258 | 0.2007 | 1.0000 | 0.6472 | 1.0000 | 8025 |
| test | rsrc | >0.15 | 0.2055 | 0.2563 | 1.0000 | 0.6936 | 1.0000 | 28348 |
| test | se_mpc | <=0 | -0.1607 | -0.1039 | 0.3488 | 0.3488 | 0.7876 | 711 |
| test | se_mpc | (0.08,0.15] | 0.1254 | 0.1980 | 1.0000 | 0.6698 | 1.0000 | 8915 |
| test | se_mpc | >0.15 | 0.2022 | 0.2538 | 1.0000 | 0.6967 | 1.0000 | 27373 |
| verified | rsrc | <=0 | -0.1354 | -0.0469 | 0.3808 | 0.3846 | 0.7769 | 260 |
| verified | rsrc | (0.08,0.15] | 0.1255 | 0.2276 | 1.0000 | 0.7031 | 1.0000 | 4675 |
| verified | rsrc | >0.15 | 0.1959 | 0.2683 | 1.0000 | 0.7375 | 1.0000 | 10414 |
| verified | se_mpc | <=0 | -0.1357 | -0.0473 | 0.3831 | 0.3870 | 0.7778 | 261 |
| verified | se_mpc | (0.08,0.15] | 0.1253 | 0.2269 | 1.0000 | 0.7034 | 1.0000 | 4814 |
| verified | se_mpc | >0.15 | 0.1951 | 0.2677 | 1.0000 | 0.7386 | 1.0000 | 10265 |

## Governance-Family Viability

| dataset | controller | family | load_threshold | rows | barrier_rate | mean_min_projected_drift |
| --- | --- | --- | --- | --- | --- | --- |
| rebench | camc_rsrc_anchor | g01 | 0.5000 | 0 |  |  |
| rebench | camc_rsrc_anchor | g012 | 0.5000 | 0 |  |  |
| rebench | camc_rsrc_anchor | all_modes | 0.5000 | 0 |  |  |
| rebench | camc_rsrc_anchor | g01 | 1.0000 | 0 |  |  |
| rebench | camc_rsrc_anchor | g012 | 1.0000 | 0 |  |  |
| rebench | camc_rsrc_anchor | all_modes | 1.0000 | 0 |  |  |
| rebench | camc_rsrc_anchor | g01 | 2.0000 | 0 |  |  |
| rebench | camc_rsrc_anchor | g012 | 2.0000 | 0 |  |  |
| rebench | camc_rsrc_anchor | all_modes | 2.0000 | 0 |  |  |
| rebench | camc_sempc_candidate | g01 | 0.5000 | 0 |  |  |
| rebench | camc_sempc_candidate | g012 | 0.5000 | 0 |  |  |
| rebench | camc_sempc_candidate | all_modes | 0.5000 | 0 |  |  |
| rebench | camc_sempc_candidate | g01 | 1.0000 | 0 |  |  |
| rebench | camc_sempc_candidate | g012 | 1.0000 | 0 |  |  |
| rebench | camc_sempc_candidate | all_modes | 1.0000 | 0 |  |  |
| rebench | camc_sempc_candidate | g01 | 2.0000 | 0 |  |  |
| rebench | camc_sempc_candidate | g012 | 2.0000 | 0 |  |  |
| rebench | camc_sempc_candidate | all_modes | 2.0000 | 0 |  |  |
| rebench | camc_static_anchor | g01 | 0.5000 | 0 |  |  |
| rebench | camc_static_anchor | g012 | 0.5000 | 0 |  |  |
| rebench | camc_static_anchor | all_modes | 0.5000 | 0 |  |  |
| rebench | camc_static_anchor | g01 | 1.0000 | 0 |  |  |
| rebench | camc_static_anchor | g012 | 1.0000 | 0 |  |  |
| rebench | camc_static_anchor | all_modes | 1.0000 | 0 |  |  |
| rebench | camc_static_anchor | g01 | 2.0000 | 0 |  |  |
| rebench | camc_static_anchor | g012 | 2.0000 | 0 |  |  |
| rebench | camc_static_anchor | all_modes | 2.0000 | 0 |  |  |
| rebench | oracle_src | g01 | 0.5000 | 90 | 0.9889 | -0.3008 |
| rebench | oracle_src | g012 | 0.5000 | 90 | 0.9889 | -0.3008 |
| rebench | oracle_src | all_modes | 0.5000 | 90 | 0.9889 | -0.3008 |
| rebench | oracle_src | g01 | 1.0000 | 0 |  |  |
| rebench | oracle_src | g012 | 1.0000 | 0 |  |  |
| rebench | oracle_src | all_modes | 1.0000 | 0 |  |  |
| rebench | oracle_src | g01 | 2.0000 | 0 |  |  |
| rebench | oracle_src | g012 | 2.0000 | 0 |  |  |
| rebench | oracle_src | all_modes | 2.0000 | 0 |  |  |
| rebench | pareto_camc_rsrc_anchor | g01 | 0.5000 | 0 |  |  |
| rebench | pareto_camc_rsrc_anchor | g012 | 0.5000 | 0 |  |  |
| rebench | pareto_camc_rsrc_anchor | all_modes | 0.5000 | 0 |  |  |
| rebench | pareto_camc_rsrc_anchor | g01 | 1.0000 | 0 |  |  |
| rebench | pareto_camc_rsrc_anchor | g012 | 1.0000 | 0 |  |  |
| rebench | pareto_camc_rsrc_anchor | all_modes | 1.0000 | 0 |  |  |
| rebench | pareto_camc_rsrc_anchor | g01 | 2.0000 | 0 |  |  |
| rebench | pareto_camc_rsrc_anchor | g012 | 2.0000 | 0 |  |  |
| rebench | pareto_camc_rsrc_anchor | all_modes | 2.0000 | 0 |  |  |
| rebench | pareto_camc_sempc_candidate | g01 | 0.5000 | 0 |  |  |
| rebench | pareto_camc_sempc_candidate | g012 | 0.5000 | 0 |  |  |
| rebench | pareto_camc_sempc_candidate | all_modes | 0.5000 | 0 |  |  |
| rebench | pareto_camc_sempc_candidate | g01 | 1.0000 | 0 |  |  |
| rebench | pareto_camc_sempc_candidate | g012 | 1.0000 | 0 |  |  |
| rebench | pareto_camc_sempc_candidate | all_modes | 1.0000 | 0 |  |  |
| rebench | pareto_camc_sempc_candidate | g01 | 2.0000 | 0 |  |  |
| rebench | pareto_camc_sempc_candidate | g012 | 2.0000 | 0 |  |  |
| rebench | pareto_camc_sempc_candidate | all_modes | 2.0000 | 0 |  |  |
| rebench | pareto_camc_static_anchor | g01 | 0.5000 | 0 |  |  |
| rebench | pareto_camc_static_anchor | g012 | 0.5000 | 0 |  |  |
| rebench | pareto_camc_static_anchor | all_modes | 0.5000 | 0 |  |  |
| rebench | pareto_camc_static_anchor | g01 | 1.0000 | 0 |  |  |
| rebench | pareto_camc_static_anchor | g012 | 1.0000 | 0 |  |  |
| rebench | pareto_camc_static_anchor | all_modes | 1.0000 | 0 |  |  |
| rebench | pareto_camc_static_anchor | g01 | 2.0000 | 0 |  |  |
| rebench | pareto_camc_static_anchor | g012 | 2.0000 | 0 |  |  |
| rebench | pareto_camc_static_anchor | all_modes | 2.0000 | 0 |  |  |
| rebench | rsrc | g01 | 0.5000 | 63 | 1.0000 | -0.3651 |
| rebench | rsrc | g012 | 0.5000 | 63 | 1.0000 | -0.3651 |
| rebench | rsrc | all_modes | 0.5000 | 63 | 1.0000 | -0.3651 |
| rebench | rsrc | g01 | 1.0000 | 0 |  |  |
| rebench | rsrc | g012 | 1.0000 | 0 |  |  |
| rebench | rsrc | all_modes | 1.0000 | 0 |  |  |
| rebench | rsrc | g01 | 2.0000 | 0 |  |  |
| rebench | rsrc | g012 | 2.0000 | 0 |  |  |
| rebench | rsrc | all_modes | 2.0000 | 0 |  |  |
| rebench | se_mpc | g01 | 0.5000 | 64 | 1.0000 | -0.3655 |
| rebench | se_mpc | g012 | 0.5000 | 64 | 1.0000 | -0.3655 |
| rebench | se_mpc | all_modes | 0.5000 | 64 | 1.0000 | -0.3655 |
| rebench | se_mpc | g01 | 1.0000 | 0 |  |  |
| rebench | se_mpc | g012 | 1.0000 | 0 |  |  |
| rebench | se_mpc | all_modes | 1.0000 | 0 |  |  |
| rebench | se_mpc | g01 | 2.0000 | 0 |  |  |
| rebench | se_mpc | g012 | 2.0000 | 0 |  |  |
| rebench | se_mpc | all_modes | 2.0000 | 0 |  |  |
| smith | camc_rsrc_anchor | g01 | 0.5000 | 0 |  |  |
| smith | camc_rsrc_anchor | g012 | 0.5000 | 0 |  |  |
| smith | camc_rsrc_anchor | all_modes | 0.5000 | 0 |  |  |
| smith | camc_rsrc_anchor | g01 | 1.0000 | 0 |  |  |
| smith | camc_rsrc_anchor | g012 | 1.0000 | 0 |  |  |
| smith | camc_rsrc_anchor | all_modes | 1.0000 | 0 |  |  |
| smith | camc_rsrc_anchor | g01 | 2.0000 | 0 |  |  |
| smith | camc_rsrc_anchor | g012 | 2.0000 | 0 |  |  |
| smith | camc_rsrc_anchor | all_modes | 2.0000 | 0 |  |  |
| smith | camc_sempc_candidate | g01 | 0.5000 | 0 |  |  |
| smith | camc_sempc_candidate | g012 | 0.5000 | 0 |  |  |
| smith | camc_sempc_candidate | all_modes | 0.5000 | 0 |  |  |
| smith | camc_sempc_candidate | g01 | 1.0000 | 0 |  |  |
| smith | camc_sempc_candidate | g012 | 1.0000 | 0 |  |  |
| smith | camc_sempc_candidate | all_modes | 1.0000 | 0 |  |  |
| smith | camc_sempc_candidate | g01 | 2.0000 | 0 |  |  |
| smith | camc_sempc_candidate | g012 | 2.0000 | 0 |  |  |
| smith | camc_sempc_candidate | all_modes | 2.0000 | 0 |  |  |
| smith | camc_static_anchor | g01 | 0.5000 | 0 |  |  |
| smith | camc_static_anchor | g012 | 0.5000 | 0 |  |  |
| smith | camc_static_anchor | all_modes | 0.5000 | 0 |  |  |
| smith | camc_static_anchor | g01 | 1.0000 | 0 |  |  |
| smith | camc_static_anchor | g012 | 1.0000 | 0 |  |  |
| smith | camc_static_anchor | all_modes | 1.0000 | 0 |  |  |
| smith | camc_static_anchor | g01 | 2.0000 | 0 |  |  |
| smith | camc_static_anchor | g012 | 2.0000 | 0 |  |  |
| smith | camc_static_anchor | all_modes | 2.0000 | 0 |  |  |
| smith | oracle_src | g01 | 0.5000 | 1244 | 0.8585 | -0.1791 |
| smith | oracle_src | g012 | 0.5000 | 1244 | 0.8585 | -0.1796 |
| smith | oracle_src | all_modes | 0.5000 | 1244 | 0.8585 | -0.1800 |
| smith | oracle_src | g01 | 1.0000 | 123 | 0.8699 | -0.1580 |
| smith | oracle_src | g012 | 1.0000 | 123 | 0.8699 | -0.1587 |
| smith | oracle_src | all_modes | 1.0000 | 123 | 0.8699 | -0.1591 |
| smith | oracle_src | g01 | 2.0000 | 3 | 1.0000 | -0.1358 |
| smith | oracle_src | g012 | 2.0000 | 3 | 1.0000 | -0.1365 |
| smith | oracle_src | all_modes | 2.0000 | 3 | 1.0000 | -0.1365 |
| smith | pareto_camc_rsrc_anchor | g01 | 0.5000 | 0 |  |  |
| smith | pareto_camc_rsrc_anchor | g012 | 0.5000 | 0 |  |  |
| smith | pareto_camc_rsrc_anchor | all_modes | 0.5000 | 0 |  |  |
| smith | pareto_camc_rsrc_anchor | g01 | 1.0000 | 0 |  |  |
| smith | pareto_camc_rsrc_anchor | g012 | 1.0000 | 0 |  |  |
| smith | pareto_camc_rsrc_anchor | all_modes | 1.0000 | 0 |  |  |
| smith | pareto_camc_rsrc_anchor | g01 | 2.0000 | 0 |  |  |
| smith | pareto_camc_rsrc_anchor | g012 | 2.0000 | 0 |  |  |
| smith | pareto_camc_rsrc_anchor | all_modes | 2.0000 | 0 |  |  |
| smith | pareto_camc_sempc_candidate | g01 | 0.5000 | 0 |  |  |
| smith | pareto_camc_sempc_candidate | g012 | 0.5000 | 0 |  |  |
| smith | pareto_camc_sempc_candidate | all_modes | 0.5000 | 0 |  |  |
| smith | pareto_camc_sempc_candidate | g01 | 1.0000 | 0 |  |  |
| smith | pareto_camc_sempc_candidate | g012 | 1.0000 | 0 |  |  |
| smith | pareto_camc_sempc_candidate | all_modes | 1.0000 | 0 |  |  |
| smith | pareto_camc_sempc_candidate | g01 | 2.0000 | 0 |  |  |
| smith | pareto_camc_sempc_candidate | g012 | 2.0000 | 0 |  |  |
| smith | pareto_camc_sempc_candidate | all_modes | 2.0000 | 0 |  |  |
| smith | pareto_camc_static_anchor | g01 | 0.5000 | 0 |  |  |
| smith | pareto_camc_static_anchor | g012 | 0.5000 | 0 |  |  |
| smith | pareto_camc_static_anchor | all_modes | 0.5000 | 0 |  |  |
| smith | pareto_camc_static_anchor | g01 | 1.0000 | 0 |  |  |
| smith | pareto_camc_static_anchor | g012 | 1.0000 | 0 |  |  |
| smith | pareto_camc_static_anchor | all_modes | 1.0000 | 0 |  |  |
| smith | pareto_camc_static_anchor | g01 | 2.0000 | 0 |  |  |
| smith | pareto_camc_static_anchor | g012 | 2.0000 | 0 |  |  |
| smith | pareto_camc_static_anchor | all_modes | 2.0000 | 0 |  |  |
| smith | rsrc | g01 | 0.5000 | 1226 | 0.8515 | -0.1759 |
| smith | rsrc | g012 | 0.5000 | 1226 | 0.8515 | -0.1765 |
| smith | rsrc | all_modes | 0.5000 | 1226 | 0.8515 | -0.1768 |
| smith | rsrc | g01 | 1.0000 | 100 | 0.8700 | -0.1725 |
| smith | rsrc | g012 | 1.0000 | 100 | 0.8700 | -0.1731 |
| smith | rsrc | all_modes | 1.0000 | 100 | 0.8700 | -0.1735 |
| smith | rsrc | g01 | 2.0000 | 0 |  |  |
| smith | rsrc | g012 | 2.0000 | 0 |  |  |
| smith | rsrc | all_modes | 2.0000 | 0 |  |  |
| smith | se_mpc | g01 | 0.5000 | 1226 | 0.8515 | -0.1759 |
| smith | se_mpc | g012 | 0.5000 | 1226 | 0.8515 | -0.1765 |
| smith | se_mpc | all_modes | 0.5000 | 1226 | 0.8515 | -0.1768 |
| smith | se_mpc | g01 | 1.0000 | 100 | 0.8700 | -0.1725 |
| smith | se_mpc | g012 | 1.0000 | 100 | 0.8700 | -0.1731 |
| smith | se_mpc | all_modes | 1.0000 | 100 | 0.8700 | -0.1735 |
| smith | se_mpc | g01 | 2.0000 | 0 |  |  |
| smith | se_mpc | g012 | 2.0000 | 0 |  |  |
| smith | se_mpc | all_modes | 2.0000 | 0 |  |  |
| test | camc_rsrc_anchor | g01 | 0.5000 | 0 |  |  |
| test | camc_rsrc_anchor | g012 | 0.5000 | 0 |  |  |
| test | camc_rsrc_anchor | all_modes | 0.5000 | 0 |  |  |
| test | camc_rsrc_anchor | g01 | 1.0000 | 0 |  |  |
| test | camc_rsrc_anchor | g012 | 1.0000 | 0 |  |  |
| test | camc_rsrc_anchor | all_modes | 1.0000 | 0 |  |  |
| test | camc_rsrc_anchor | g01 | 2.0000 | 0 |  |  |
| test | camc_rsrc_anchor | g012 | 2.0000 | 0 |  |  |
| test | camc_rsrc_anchor | all_modes | 2.0000 | 0 |  |  |
| test | camc_sempc_candidate | g01 | 0.5000 | 0 |  |  |
| test | camc_sempc_candidate | g012 | 0.5000 | 0 |  |  |
| test | camc_sempc_candidate | all_modes | 0.5000 | 0 |  |  |
| test | camc_sempc_candidate | g01 | 1.0000 | 0 |  |  |
| test | camc_sempc_candidate | g012 | 1.0000 | 0 |  |  |
| test | camc_sempc_candidate | all_modes | 1.0000 | 0 |  |  |
| test | camc_sempc_candidate | g01 | 2.0000 | 0 |  |  |
| test | camc_sempc_candidate | g012 | 2.0000 | 0 |  |  |
| test | camc_sempc_candidate | all_modes | 2.0000 | 0 |  |  |
| test | camc_static_anchor | g01 | 0.5000 | 0 |  |  |
| test | camc_static_anchor | g012 | 0.5000 | 0 |  |  |
| test | camc_static_anchor | all_modes | 0.5000 | 0 |  |  |
| test | camc_static_anchor | g01 | 1.0000 | 0 |  |  |
| test | camc_static_anchor | g012 | 1.0000 | 0 |  |  |
| test | camc_static_anchor | all_modes | 1.0000 | 0 |  |  |
| test | camc_static_anchor | g01 | 2.0000 | 0 |  |  |
| test | camc_static_anchor | g012 | 2.0000 | 0 |  |  |
| test | camc_static_anchor | all_modes | 2.0000 | 0 |  |  |
| test | oracle_src | g01 | 0.5000 | 48 | 1.0000 | -0.3129 |
| test | oracle_src | g012 | 0.5000 | 48 | 1.0000 | -0.3129 |
| test | oracle_src | all_modes | 0.5000 | 48 | 1.0000 | -0.3129 |
| test | oracle_src | g01 | 1.0000 | 0 |  |  |
| test | oracle_src | g012 | 1.0000 | 0 |  |  |
| test | oracle_src | all_modes | 1.0000 | 0 |  |  |
| test | oracle_src | g01 | 2.0000 | 0 |  |  |
| test | oracle_src | g012 | 2.0000 | 0 |  |  |
| test | oracle_src | all_modes | 2.0000 | 0 |  |  |
| test | pareto_camc_rsrc_anchor | g01 | 0.5000 | 0 |  |  |
| test | pareto_camc_rsrc_anchor | g012 | 0.5000 | 0 |  |  |
| test | pareto_camc_rsrc_anchor | all_modes | 0.5000 | 0 |  |  |
| test | pareto_camc_rsrc_anchor | g01 | 1.0000 | 0 |  |  |
| test | pareto_camc_rsrc_anchor | g012 | 1.0000 | 0 |  |  |
| test | pareto_camc_rsrc_anchor | all_modes | 1.0000 | 0 |  |  |
| test | pareto_camc_rsrc_anchor | g01 | 2.0000 | 0 |  |  |
| test | pareto_camc_rsrc_anchor | g012 | 2.0000 | 0 |  |  |
| test | pareto_camc_rsrc_anchor | all_modes | 2.0000 | 0 |  |  |
| test | pareto_camc_sempc_candidate | g01 | 0.5000 | 0 |  |  |
| test | pareto_camc_sempc_candidate | g012 | 0.5000 | 0 |  |  |
| test | pareto_camc_sempc_candidate | all_modes | 0.5000 | 0 |  |  |
| test | pareto_camc_sempc_candidate | g01 | 1.0000 | 0 |  |  |
| test | pareto_camc_sempc_candidate | g012 | 1.0000 | 0 |  |  |
| test | pareto_camc_sempc_candidate | all_modes | 1.0000 | 0 |  |  |
| test | pareto_camc_sempc_candidate | g01 | 2.0000 | 0 |  |  |
| test | pareto_camc_sempc_candidate | g012 | 2.0000 | 0 |  |  |
| test | pareto_camc_sempc_candidate | all_modes | 2.0000 | 0 |  |  |
| test | pareto_camc_static_anchor | g01 | 0.5000 | 0 |  |  |
| test | pareto_camc_static_anchor | g012 | 0.5000 | 0 |  |  |
| test | pareto_camc_static_anchor | all_modes | 0.5000 | 0 |  |  |
| test | pareto_camc_static_anchor | g01 | 1.0000 | 0 |  |  |
| test | pareto_camc_static_anchor | g012 | 1.0000 | 0 |  |  |
| test | pareto_camc_static_anchor | all_modes | 1.0000 | 0 |  |  |
| test | pareto_camc_static_anchor | g01 | 2.0000 | 0 |  |  |
| test | pareto_camc_static_anchor | g012 | 2.0000 | 0 |  |  |
| test | pareto_camc_static_anchor | all_modes | 2.0000 | 0 |  |  |
| test | rsrc | g01 | 0.5000 | 37 | 1.0000 | -0.3428 |
| test | rsrc | g012 | 0.5000 | 37 | 1.0000 | -0.3428 |
| test | rsrc | all_modes | 0.5000 | 37 | 1.0000 | -0.3428 |
| test | rsrc | g01 | 1.0000 | 0 |  |  |
| test | rsrc | g012 | 1.0000 | 0 |  |  |
| test | rsrc | all_modes | 1.0000 | 0 |  |  |
| test | rsrc | g01 | 2.0000 | 0 |  |  |
| test | rsrc | g012 | 2.0000 | 0 |  |  |
| test | rsrc | all_modes | 2.0000 | 0 |  |  |
| test | se_mpc | g01 | 0.5000 | 37 | 1.0000 | -0.3429 |
| test | se_mpc | g012 | 0.5000 | 37 | 1.0000 | -0.3429 |
| test | se_mpc | all_modes | 0.5000 | 37 | 1.0000 | -0.3429 |
| test | se_mpc | g01 | 1.0000 | 0 |  |  |
| test | se_mpc | g012 | 1.0000 | 0 |  |  |
| test | se_mpc | all_modes | 1.0000 | 0 |  |  |
| test | se_mpc | g01 | 2.0000 | 0 |  |  |
| test | se_mpc | g012 | 2.0000 | 0 |  |  |
| test | se_mpc | all_modes | 2.0000 | 0 |  |  |
| verified | camc_rsrc_anchor | g01 | 0.5000 | 0 |  |  |
| verified | camc_rsrc_anchor | g012 | 0.5000 | 0 |  |  |
| verified | camc_rsrc_anchor | all_modes | 0.5000 | 0 |  |  |
| verified | camc_rsrc_anchor | g01 | 1.0000 | 0 |  |  |
| verified | camc_rsrc_anchor | g012 | 1.0000 | 0 |  |  |
| verified | camc_rsrc_anchor | all_modes | 1.0000 | 0 |  |  |
| verified | camc_rsrc_anchor | g01 | 2.0000 | 0 |  |  |
| verified | camc_rsrc_anchor | g012 | 2.0000 | 0 |  |  |
| verified | camc_rsrc_anchor | all_modes | 2.0000 | 0 |  |  |
| verified | camc_sempc_candidate | g01 | 0.5000 | 0 |  |  |
| verified | camc_sempc_candidate | g012 | 0.5000 | 0 |  |  |
| verified | camc_sempc_candidate | all_modes | 0.5000 | 0 |  |  |
| verified | camc_sempc_candidate | g01 | 1.0000 | 0 |  |  |
| verified | camc_sempc_candidate | g012 | 1.0000 | 0 |  |  |
| verified | camc_sempc_candidate | all_modes | 1.0000 | 0 |  |  |
| verified | camc_sempc_candidate | g01 | 2.0000 | 0 |  |  |
| verified | camc_sempc_candidate | g012 | 2.0000 | 0 |  |  |
| verified | camc_sempc_candidate | all_modes | 2.0000 | 0 |  |  |
| verified | camc_static_anchor | g01 | 0.5000 | 0 |  |  |
| verified | camc_static_anchor | g012 | 0.5000 | 0 |  |  |
| verified | camc_static_anchor | all_modes | 0.5000 | 0 |  |  |
| verified | camc_static_anchor | g01 | 1.0000 | 0 |  |  |
| verified | camc_static_anchor | g012 | 1.0000 | 0 |  |  |
| verified | camc_static_anchor | all_modes | 1.0000 | 0 |  |  |
| verified | camc_static_anchor | g01 | 2.0000 | 0 |  |  |
| verified | camc_static_anchor | g012 | 2.0000 | 0 |  |  |
| verified | camc_static_anchor | all_modes | 2.0000 | 0 |  |  |
| verified | oracle_src | g01 | 0.5000 | 0 |  |  |
| verified | oracle_src | g012 | 0.5000 | 0 |  |  |
| verified | oracle_src | all_modes | 0.5000 | 0 |  |  |
| verified | oracle_src | g01 | 1.0000 | 0 |  |  |
| verified | oracle_src | g012 | 1.0000 | 0 |  |  |
| verified | oracle_src | all_modes | 1.0000 | 0 |  |  |
| verified | oracle_src | g01 | 2.0000 | 0 |  |  |
| verified | oracle_src | g012 | 2.0000 | 0 |  |  |
| verified | oracle_src | all_modes | 2.0000 | 0 |  |  |
| verified | pareto_camc_rsrc_anchor | g01 | 0.5000 | 0 |  |  |
| verified | pareto_camc_rsrc_anchor | g012 | 0.5000 | 0 |  |  |
| verified | pareto_camc_rsrc_anchor | all_modes | 0.5000 | 0 |  |  |
| verified | pareto_camc_rsrc_anchor | g01 | 1.0000 | 0 |  |  |
| verified | pareto_camc_rsrc_anchor | g012 | 1.0000 | 0 |  |  |
| verified | pareto_camc_rsrc_anchor | all_modes | 1.0000 | 0 |  |  |
| verified | pareto_camc_rsrc_anchor | g01 | 2.0000 | 0 |  |  |
| verified | pareto_camc_rsrc_anchor | g012 | 2.0000 | 0 |  |  |
| verified | pareto_camc_rsrc_anchor | all_modes | 2.0000 | 0 |  |  |
| verified | pareto_camc_sempc_candidate | g01 | 0.5000 | 0 |  |  |
| verified | pareto_camc_sempc_candidate | g012 | 0.5000 | 0 |  |  |
| verified | pareto_camc_sempc_candidate | all_modes | 0.5000 | 0 |  |  |
| verified | pareto_camc_sempc_candidate | g01 | 1.0000 | 0 |  |  |
| verified | pareto_camc_sempc_candidate | g012 | 1.0000 | 0 |  |  |
| verified | pareto_camc_sempc_candidate | all_modes | 1.0000 | 0 |  |  |
| verified | pareto_camc_sempc_candidate | g01 | 2.0000 | 0 |  |  |
| verified | pareto_camc_sempc_candidate | g012 | 2.0000 | 0 |  |  |
| verified | pareto_camc_sempc_candidate | all_modes | 2.0000 | 0 |  |  |
| verified | pareto_camc_static_anchor | g01 | 0.5000 | 0 |  |  |
| verified | pareto_camc_static_anchor | g012 | 0.5000 | 0 |  |  |
| verified | pareto_camc_static_anchor | all_modes | 0.5000 | 0 |  |  |
| verified | pareto_camc_static_anchor | g01 | 1.0000 | 0 |  |  |
| verified | pareto_camc_static_anchor | g012 | 1.0000 | 0 |  |  |
| verified | pareto_camc_static_anchor | all_modes | 1.0000 | 0 |  |  |
| verified | pareto_camc_static_anchor | g01 | 2.0000 | 0 |  |  |
| verified | pareto_camc_static_anchor | g012 | 2.0000 | 0 |  |  |
| verified | pareto_camc_static_anchor | all_modes | 2.0000 | 0 |  |  |
| verified | rsrc | g01 | 0.5000 | 0 |  |  |
| verified | rsrc | g012 | 0.5000 | 0 |  |  |
| verified | rsrc | all_modes | 0.5000 | 0 |  |  |
| verified | rsrc | g01 | 1.0000 | 0 |  |  |
| verified | rsrc | g012 | 1.0000 | 0 |  |  |
| verified | rsrc | all_modes | 1.0000 | 0 |  |  |
| verified | rsrc | g01 | 2.0000 | 0 |  |  |
| verified | rsrc | g012 | 2.0000 | 0 |  |  |
| verified | rsrc | all_modes | 2.0000 | 0 |  |  |
| verified | se_mpc | g01 | 0.5000 | 0 |  |  |
| verified | se_mpc | g012 | 0.5000 | 0 |  |  |
| verified | se_mpc | all_modes | 0.5000 | 0 |  |  |
| verified | se_mpc | g01 | 1.0000 | 0 |  |  |
| verified | se_mpc | g012 | 1.0000 | 0 |  |  |
| verified | se_mpc | all_modes | 1.0000 | 0 |  |  |
| verified | se_mpc | g01 | 2.0000 | 0 |  |  |
| verified | se_mpc | g012 | 2.0000 | 0 |  |  |
| verified | se_mpc | all_modes | 2.0000 | 0 |  |  |

## Best Frontiers Per Dataset

| dataset | controller | success_rate | discounted_cost | overload_rate |
| --- | --- | --- | --- | --- |
| rebench | always_verify_throttle | 0.4883 | 0.6120 | 0.0000 |
| rebench | static_conservative | 0.4569 | 0.6142 | 0.0000 |
| rebench | oracle_src | 0.5412 | 0.6382 | 0.0000 |
| smith | static_conservative | 0.3856 | 0.6557 | 0.0000 |
| smith | always_verify_throttle | 0.3923 | 0.6560 | 0.0000 |
| smith | oracle_src | 0.4653 | 0.6697 | 0.0000 |
| test | static_conservative | 0.4453 | 0.6204 | 0.0000 |
| test | always_verify_throttle | 0.4691 | 0.6217 | 0.0000 |
| test | oracle_src | 0.5264 | 0.6493 | 0.0000 |
| verified | static_conservative | 0.4606 | 0.6120 | 0.0000 |
| verified | always_verify_throttle | 0.4855 | 0.6146 | 0.0000 |
| verified | oracle_src | 0.5464 | 0.6404 | 0.0000 |
