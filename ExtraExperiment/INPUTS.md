# Input Inventory

This file records the datasets and input artifacts copied into the standalone
experiment module.

## Raw Or External Datasets

- `Dataset/AIDev/raw/`: AIDev Parquet tables used to build the pull-request
  workload feature table. The incomplete temporary download file from the source
  workspace was not copied.
- `Dataset/SWE-bench_Verified/`: SWE-bench Verified metadata and the test split
  Parquet used by the controlled-runtime task manifest.
- `Dataset/CodeTraceBench/swe_raw/openhands__verified/astropy__astropy-14096/`
  and `Dataset/CodeTraceBench/swe_raw/openhands__verified/astropy__astropy-7606/`:
  the two local trace directories referenced by the auxiliary existing-trace
  supplement. The full CodeTraceBench archive was not copied because only these
  two directories are referenced by the copied result summary.

## Analysis Inputs

- `results/runtime_control_protocol/manifest_v1/task_manifest.csv`: selected
  task manifest for the controlled-runtime protocol.
- `results/runtime_control_protocol/manifest_v1/runtime_execution_matrix.csv`:
  planned controller-by-task matrix.
- `results/runtime_control_protocol/first_wave_execution_bundle_v1/`: first-wave
  isolated execution manifest, row checklist, pair plan, and empty result
  template.
- `results/runtime_control_protocol/first_wave_execution_packets_v1/`: per-row
  execution packets for the first wave.
- `results/pull_request_workload_gate/aidev_pr_level_features.csv`: derived
  feature table used by the workload-gate analyses.
- `../exp/results/emse_runtime/learned_runtime_gate_combined60_feature_cal000_v1/`:
  completed 60-task executable context budget outputs used for the manuscript
  Study 3 score-gate result.
- `../exp/results/emse_runtime/lmstudio_executable_context_gate_repeat_analysis_v1/`:
  original 30-task subset check used as an internal consistency analysis.

## Evidence Boundary

The AIDev workload-gate result tables are completed observational outputs. The
completed Study 3 executable context budget outputs are stored under
`../exp/results/emse_runtime/`. The first-wave controlled-runtime materials in
this `ExtraExperiment` directory are legacy inputs, protocols, and readiness
artifacts until completed rows are recorded and validated.
