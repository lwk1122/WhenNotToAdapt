# Controlled Runtime Protocol for the standalone module Revision

## Purpose

The controlled runtime study is the policy-effect evidence layer. AIDev establishes that post-proposal information in real agent-authored PRs predicts downstream workload. The controlled runtime study must answer a different question:

> On the same real repository tasks, does a conservative runtime gate reduce resource use and downstream work while preserving solve rate within a pre-specified non-inferiority margin?

This document fixes the analysis contract before additional live runs are executed.

## Task Set

Primary task source:

- SWE-bench Verified tasks from `ExtraExperiment/Dataset/SWE-bench_Verified/data/test-00000-of-00001.parquet`.

Prepared manifest:

- `ExtraExperiment/results/runtime_control_protocol/manifest_v1/task_manifest.csv`
- 24 tasks
- 9 repositories
- balanced high/mid/low risk tiers

Prepared execution matrix:

- `ExtraExperiment/results/runtime_control_protocol/manifest_v1/runtime_execution_matrix.csv`
- 96 planned task-controller rows
- all rows are marked `not_run`
- use only inside an approved isolated environment

Prompt-only dry-run harness:

- script: `ExtraExperiment/scripts/runtime_control_protocol/dry_run_controller_harness.py`
- offline dry-run output: `ExtraExperiment/results/runtime_control_protocol/dry_run_v1/`
- LM Studio smoke output: `ExtraExperiment/results/runtime_control_protocol/dry_run_lmstudio_smoke/`
- purpose: validate controller prompts, local-model connectivity, logging fields, and analysis-template columns before repository execution;
- safety boundary: no repository clone, file inspection, patch application, dependency installation, or test execution;
- evidence status: dry-run outputs are not solve-rate, resource-savings, or downstream-work evidence.

Minimum publication-grade run:

- at least 30 paired tasks remains the minimum analysis-script guardrail;
- however, power planning shows that a 5 percentage-point non-inferiority margin can require several hundred paired tasks for 80% planning power under moderate discordance;
- therefore, 24-30 paired tasks should be described only as a first batch, pilot, feasibility, or resource-accounting study unless the observed paired confidence interval is already decisive.

## Controllers

Minimum paired controllers:

1. `static_conservative`: conservative baseline with verification.
2. `rsrc_guarded`: workload-aware guarded controller.
3. `sempc_lite`: candidate CASC-like runtime gate with lookahead.
4. `minimal_verify`: diagnostic low-verification baseline, not a primary comparator.

Primary comparison:

- target: `sempc_lite`
- reference: `rsrc_guarded`

Secondary comparisons:

- `sempc_lite` versus `static_conservative`
- `rsrc_guarded` versus `static_conservative`

## Outcomes

Primary quality outcome:

- `success`: final target test pass.

Primary resource outcome:

- `total_observed_work = search_count + read_count + test_runs + patch_attempts`

Secondary outcomes:

- `test_runs`
- `verification_events`
- `search_count`
- `read_count`
- `patch_attempts`
- `patch_apply_successes`
- `catastrophic_failure`
- `post_error_extra_work`
- `best_problem_reduction`
- `final_problem_reduction`
- `model_calls`
- `prompt_tokens`
- `completion_tokens`
- `total_tokens`
- `latency_seconds`
- `tool_calls`
- `context_files`
- `context_bytes`
- `files_changed`
- `lines_changed`
- `failed_verification_jobs`
- `recovery_attempts`

## Non-Inferiority Rule

Solve-rate margin:

- default margin: 5 percentage points (`success_margin = 0.05`).

Paired difference:

- `diff = success_target - success_reference`.

Bootstrap confidence interval:

- paired task-level bootstrap;
- default 2,000 bootstrap rounds;
- 95% confidence interval.

CI rule:

- target is non-inferior by CI if the lower CI bound is greater than `-success_margin`.

Publication-ready success claim additionally requires:

- at least 30 paired tasks;
- nonzero success evidence across the paired target/reference runs;
- the CI rule above.

The additional requirements prevent a degenerate “both controllers solved nothing” run from being described as meaningful non-inferiority.

Power-planning output:

- `ExtraExperiment/results/runtime_control_protocol/power_plan_v1/runtime_power_plan.md`
- `ExtraExperiment/results/runtime_control_protocol/power_plan_v1/runtime_power_grid.csv`
- `ExtraExperiment/results/runtime_control_protocol/power_plan_v1/runtime_power_recommendations.csv`

The planning calculation is intentionally conservative. It uses paired binary target-reference differences and a normal lower confidence bound as an approximation. The final report analysis should still use the paired bootstrap CI produced by `analyze_runtime_pairs.py`.

## Resource Claim

Resource savings are paired differences:

- `resource_diff = resource_target - resource_reference`.

Negative values favor the target controller. Report mean paired difference and 95% paired bootstrap CI.

The resource claim is descriptive unless paired confidence intervals exclude zero or the direction is consistent across task families.

## Safety Boundary

Running SWE-bench tasks downloads and executes third-party repository code. The experiment should proceed only with explicit approval or an isolated execution setup.

Recommended safeguards:

- disposable workspace;
- no sensitive environment variables;
- bounded timeouts;
- no network access during test execution after snapshots are downloaded;
- command logging;
- per-task output capture;
- no arbitrary installation scripts unless explicitly reviewed.

Preflight command:

```bash
.venv_experiment/bin/python -m ExtraExperiment.scripts.runtime_control_protocol.preflight_runtime_environment
```

Preflight output:

- report: `ExtraExperiment/results/runtime_control_protocol/preflight_v1/runtime_preflight_report.md`
- checks: `ExtraExperiment/results/runtime_control_protocol/preflight_v1/runtime_preflight_checks.csv`
- summary: `ExtraExperiment/results/runtime_control_protocol/preflight_v1/runtime_preflight_summary.json`

Current preflight status:

- status: `FAIL`;
- passing prerequisites: execution matrix and manifest exist, 24 tasks match the 96-row matrix, all rows require isolation, SWE-bench Verified parquet exists, run root is writable, Docker/Git/Python are available, and LM Studio `/models` is reachable with `qwen2.5-coder-7b-instruct-mlx`;
- hard blocker: isolation acknowledgment is missing (`CAMC_RUNTIME_ISOLATION_ACK=1`);
- warning: `SSH_AUTH_SOCK` is present and should be removed or isolated before untrusted repository execution.

The preflight report is readiness evidence only. A `PASS` preflight should be required before any row in the execution matrix is executed, but it is not solve-rate, resource-savings, or downstream-work evidence.

## Isolated Execution Bundle

No-execution bundle generator:

- script: `ExtraExperiment/scripts/runtime_control_protocol/prepare_isolated_execution_bundle.py`
- packet generator: `ExtraExperiment/scripts/runtime_control_protocol/build_isolated_execution_packets.py`
- row recorder: `ExtraExperiment/scripts/runtime_control_protocol/record_isolated_runtime_result.py`
- output directory: `ExtraExperiment/results/runtime_control_protocol/isolated_execution_bundle_v1/`
- execution manifest: `ExtraExperiment/results/runtime_control_protocol/isolated_execution_bundle_v1/isolated_execution_manifest.csv`
- empty result template: `ExtraExperiment/results/runtime_control_protocol/isolated_execution_bundle_v1/runtime_task_results_empty.csv`
- row checklist: `ExtraExperiment/results/runtime_control_protocol/isolated_execution_bundle_v1/row_execution_checklist.csv`
- runbook: `ExtraExperiment/results/runtime_control_protocol/isolated_execution_bundle_v1/execution_runbook.md`
- summary: `ExtraExperiment/results/runtime_control_protocol/isolated_execution_bundle_v1/runtime_execution_bundle_summary.json`

Per-row execution packets:

- output directory: `ExtraExperiment/results/runtime_control_protocol/isolated_execution_packets_v1/`
- packet index: `ExtraExperiment/results/runtime_control_protocol/isolated_execution_packets_v1/packet_index.csv`
- packet summary: `ExtraExperiment/results/runtime_control_protocol/isolated_execution_packets_v1/packet_summary.json`
- packet README: `ExtraExperiment/results/runtime_control_protocol/isolated_execution_packets_v1/README.md`
- packet files: `ExtraExperiment/results/runtime_control_protocol/isolated_execution_packets_v1/packets/`
- scope: 96 markdown packets and 96 JSON packets, one pair for each planned task-controller row;
- each packet contains row metadata, controller policy, dry-run decision, problem statement, hints, known FAIL_TO_PASS/PASS_TO_PASS tests, isolated execution checklist, row-recorder command template, and validation command;
- packet generation performs no third-party repository clone, dependency installation, patching, or test execution.

Execution priority plan:

- script: `ExtraExperiment/scripts/runtime_control_protocol/plan_execution_priority.py`
- output directory: `ExtraExperiment/results/runtime_control_protocol/execution_priority_v1/`
- task ranking: `ExtraExperiment/results/runtime_control_protocol/execution_priority_v1/runtime_task_execution_priority.csv`
- row queue: `ExtraExperiment/results/runtime_control_protocol/execution_priority_v1/runtime_row_execution_queue.csv`
- report: `ExtraExperiment/results/runtime_control_protocol/execution_priority_v1/runtime_execution_priority_plan.md`
- summary: `ExtraExperiment/results/runtime_control_protocol/execution_priority_v1/runtime_execution_priority_summary.json`
- scope: 24 ranked tasks and a recommended first wave of 12 tasks / 48 task-controller rows;
- priority rule: execute target/reference decision-contrast tasks first, especially `sempc_lite=adapt` versus `rsrc_guarded=inherit_baseline`, while preserving paired rows and including both-inherit controls;
- evidence status: no-execution queueing and audit artifact only.

First-wave execution bundle:

- script: `ExtraExperiment/scripts/runtime_control_protocol/prepare_first_wave_execution_bundle.py`
- output directory: `ExtraExperiment/results/runtime_control_protocol/first_wave_execution_bundle_v1/`
- execution manifest: `ExtraExperiment/results/runtime_control_protocol/first_wave_execution_bundle_v1/isolated_execution_manifest.csv`
- empty result template: `ExtraExperiment/results/runtime_control_protocol/first_wave_execution_bundle_v1/runtime_task_results_empty.csv`
- row checklist: `ExtraExperiment/results/runtime_control_protocol/first_wave_execution_bundle_v1/row_execution_checklist.csv`
- pair plan: `ExtraExperiment/results/runtime_control_protocol/first_wave_execution_bundle_v1/first_wave_pair_plan.csv`
- runbook: `ExtraExperiment/results/runtime_control_protocol/first_wave_execution_bundle_v1/execution_runbook.md`
- summary: `ExtraExperiment/results/runtime_control_protocol/first_wave_execution_bundle_v1/first_wave_bundle_summary.json`
- validation output: `ExtraExperiment/results/runtime_control_protocol/first_wave_execution_bundle_v1_validation/runtime_result_validation.md`
- scope: 12 first-wave tasks and 48 task-controller rows, all marked `not_run`;
- first-wave composition: 9 `target_adapt_reference_inherit`, 1 `target_inherit_reference_adapt`, and 2 `both_primary_inherit` tasks;
- pair scope: 12 `sempc_lite` versus `rsrc_guarded` paired task instances, with `static_conservative` and `minimal_verify` controls kept for the same tasks;
- negative validation status: expected `FAIL` before execution because selected primary-comparison rows are `not_run` and primary observed metrics are empty;
- evidence status: recorder-compatible execution preparation only, not solve-rate, non-inferiority, resource-savings, or downstream-work evidence.

First-wave packet and status artifacts:

- packet generator: `ExtraExperiment/scripts/runtime_control_protocol/build_isolated_execution_packets.py`
- packet output directory: `ExtraExperiment/results/runtime_control_protocol/first_wave_execution_packets_v1/`
- packet index: `ExtraExperiment/results/runtime_control_protocol/first_wave_execution_packets_v1/packet_index.csv`
- packet summary: `ExtraExperiment/results/runtime_control_protocol/first_wave_execution_packets_v1/packet_summary.json`
- packet scope: 48 markdown packets and 48 JSON packets generated from the first-wave bundle and the contracted LM Studio dry-run plans;
- packet command guardrail: row-recorder commands in these packets include `--bundle-dir ExtraExperiment/results/runtime_control_protocol/first_wave_execution_bundle_v1`;
- recorder accumulation guardrail: when `runtime_task_results_recorded.csv` already exists in a bundle directory and `--results-in` is not provided, `record_isolated_runtime_result.py` reads the recorded file before writing the next row, preserving earlier completed rows;
- checklist recording: row-recorder flags can mark `preflight_passed`, `sensitive_env_removed`, `repo_snapshot_prepared`, `dependencies_reviewed`, `dependencies_installed`, `target_tests_run`, and `validator_passed`; completed rows automatically mark `observed_metrics_recorded`, and rows recorded with an isolation acknowledgment mark `isolation_ack_present`;
- status output directory: `ExtraExperiment/results/runtime_control_protocol/first_wave_batch_status_v1/`
- status report: `ExtraExperiment/results/runtime_control_protocol/first_wave_batch_status_v1/runtime_batch_status_report.md`
- legacy first-wave protocol status: 48 planned rows, 12 tasks, 8 repositories, 0 completed rows, 0 rows with complete primary metrics, 48 markdown packets, and 48 JSON packets present;
- evidence status: first-wave progress tracking only, not completed runtime evidence.

First-wave synthetic analysis drill:

- script: `ExtraExperiment/scripts/runtime_control_protocol/make_first_wave_analysis_drill.py`
- synthetic results: `ExtraExperiment/results/runtime_control_protocol/first_wave_analysis_drill_v1/runtime_task_results_synthetic_completed.csv`
- validation output: `ExtraExperiment/results/runtime_control_protocol/first_wave_analysis_drill_validation_v1/runtime_result_validation.md`
- pair-analysis output: `ExtraExperiment/results/runtime_control_protocol/first_wave_analysis_drill_pair_analysis_v1/runtime_pair_analysis_report.md`
- publication-artifact output: `ExtraExperiment/results/runtime_control_protocol/first_wave_analysis_drill_publication_artifacts_v1/runtime_publication_artifacts.md`
- scope: creates 24 completed-looking synthetic primary rows for 12 `sempc_lite` versus `rsrc_guarded` pairs to verify the validation-analysis-publication pipeline;
- current drill status: validation passes, paired analysis runs, and publication artifact generation runs;
- evidence boundary: `evidence_status=synthetic_drill_not_publication_evidence`, `third_party_execution_performed=false`, `lmstudio_called=false`, and `publication_ready_success_claim=false`.

Current bundle status:

- 96 selected task-controller rows;
- 24 selected SWE-bench Verified tasks;
- controllers: `minimal_verify`, `rsrc_guarded`, `sempc_lite`, and `static_conservative`;
- all 96 rows require isolation;
- all 96 result-template rows are intentionally marked `execute_status=not_run`;
- the refreshed result template has 31 columns, including model calls, tokens, latency, tool calls, context size, changed files/lines, failed verification jobs, and recovery attempts;
- no third-party repository clone, dependency installation, patching, or test execution was performed while preparing the bundle.

Row-recording guardrail:

- preview output: `ExtraExperiment/results/runtime_control_protocol/isolated_execution_bundle_v1/row_records/sphinx-doc__sphinx-10466__sempc_lite.md`
- a preview row record can be generated without execution and without changing the results CSV;
- writing a `completed` row requires either `--ack-isolated` or `CAMC_RUNTIME_ISOLATION_ACK=1`, plus an evidence note;
- after the first recorded row, later row records preserve earlier completed rows by reading `runtime_task_results_recorded.csv` by default;
- a guardrail check without the isolation acknowledgment fails with `ERROR: Recording a completed row requires --ack-isolated or CAMC_RUNTIME_ISOLATION_ACK=1.`

Validation status:

- validation output: `ExtraExperiment/results/runtime_control_protocol/isolated_execution_bundle_v1_validation/runtime_result_validation.md`
- expected status before real execution: `FAIL`;
- reason: the 48 selected primary-comparison rows for `sempc_lite` versus `rsrc_guarded` are non-completed `not_run` rows, and the primary observed metrics are empty.

This bundle is an execution-control artifact. It is useful for row-by-row isolated execution and audit, but it is not policy-effect evidence.

## Current Pilot Status

Existing pilot:

- source: `ExtraExperiment/results/runtime_control_protocol/shadow_runtime_helpers/shadow_runtime_sphinx8_lm_pilot/shadow_runtime_task_results.csv`
- paired tasks: 8
- output: `ExtraExperiment/results/runtime_control_protocol/pilot_pair_analysis/runtime_pair_analysis_report.md`

Interpretation:

- This pilot validates the analysis script shape.
- It is not publication-grade evidence.
- Both primary controllers have zero success in the pilot, so any mechanical CI non-inferiority result is not informative.

Current prompt-only dry-run status:

- Offline dry run: 2 tasks x 4 controllers, 8 planned rows.
- LM Studio smoke: 1 task x `sempc_lite`, model `qwen2.5-coder-7b-instruct-mlx`, prompt-only response parsed successfully.
- Full offline dry run: 24 tasks x 4 controllers, 96 planned rows in `ExtraExperiment/results/runtime_control_protocol/dry_run_offline_full_v1/`.
- LM Studio controller-coverage dry run: 1 task x 4 controllers in `ExtraExperiment/results/runtime_control_protocol/dry_run_lmstudio_controller_coverage_v1/`; model `qwen2.5-coder-7b-instruct-mlx`.
- Initial full LM Studio dry run: 24 tasks x 4 controllers in `ExtraExperiment/results/runtime_control_protocol/dry_run_lmstudio_full_v1/`; it exposed prompt-policy drift because `static_conservative` and `minimal_verify` sometimes returned `adapt`.
- Contracted full LM Studio dry run: 24 tasks x 4 controllers in `ExtraExperiment/results/runtime_control_protocol/dry_run_lmstudio_full_contract_v1/`; model `qwen2.5-coder-7b-instruct-mlx`; 96 rows, 0 missing decisions, 0 fixed-controller contract violations.
- Dry-run decision analysis: `ExtraExperiment/results/runtime_control_protocol/dry_run_analysis_lmstudio_contract_v1/dry_run_decision_analysis_report.md`.
- Contract summary: `ExtraExperiment/results/runtime_control_protocol/dry_run_analysis_lmstudio_contract_v1/dry_run_policy_contract_summary.csv`, with PASS for `static_conservative -> inherit_baseline` and `minimal_verify -> minimal_plan`.
- The dry-run template leaves observed metrics blank and should not be passed off as controlled-runtime evidence.
- The contracted LM Studio template is rejected by `validate_runtime_results.py` as intended: 48 selected prompt-only rows and empty primary observed metrics for the `sempc_lite` versus `rsrc_guarded` comparison.

Runtime-result validation status:

- validator script: `ExtraExperiment/scripts/runtime_control_protocol/validate_runtime_results.py`
- dry-run template validation: fails as intended because selected rows are prompt-only and primary observed metrics are empty;
- old 8-task pilot validation: passes input completeness, with a warning that all selected success values are zero;
- paired analysis now runs validation automatically and refuses invalid task-results files before computing non-inferiority or resource summaries.

Report-facing runtime artifact generator:

- script: `ExtraExperiment/scripts/runtime_control_protocol/make_runtime_publication_artifacts.py`
- pilot output: `ExtraExperiment/results/runtime_control_protocol/pilot_publication_artifacts/`
- key-metrics table: `ExtraExperiment/results/runtime_control_protocol/pilot_publication_artifacts/runtime_publication_key_metrics.csv`
- report: `ExtraExperiment/results/runtime_control_protocol/pilot_publication_artifacts/runtime_publication_artifacts.md`
- figure: `ExtraExperiment/results/runtime_control_protocol/pilot_publication_artifacts/figures/runtime_solve_resource_summary.svg`
- status: current pilot artifacts are marked `shape check only: success evidence is not informative`;
- use boundary: run this script only after `analyze_runtime_pairs.py` has produced validated pair-analysis outputs. It does not make incomplete rows or prompt-only rows valid.

The empty isolated result template was also checked against `analyze_runtime_pairs.py`; the analysis refuses it before any figure/table generation because selected primary-comparison rows are `not_run` and primary observed metrics are empty.

## Analysis Command

```bash
.venv_experiment/bin/python -m ExtraExperiment.scripts.runtime_control_protocol.analyze_runtime_pairs \
  --task-results ExtraExperiment/results/runtime_control_protocol/<run_dir>/shadow_runtime_task_results.csv \
  --output-dir ExtraExperiment/results/runtime_control_protocol/<analysis_dir> \
  --target sempc_lite \
  --reference rsrc_guarded \
  --success-margin 0.05 \
  --min-publication-pairs 30
```

The analysis command now performs runtime-result validation before computing paired statistics. It writes `runtime_result_validation.json`, `runtime_result_validation_issues.csv`, and `runtime_result_validation.md` to the output directory. By default, validation rejects prompt-only dry-run rows, non-completed execution rows, missing paired target/reference rows, duplicate instance/controller rows, and empty primary observed metrics. Override flags are intended only for schema debugging and must not be used for report evidence claims.
