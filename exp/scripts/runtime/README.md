# Controlled-Runtime Analysis

This directory contains analysis utilities for the controlled runtime evidence layer.

These scripts do not execute repository code. They analyze completed paired runtime result CSVs.
For the current manuscript, the completed executable context budget evidence is
the 60-task fixed-candidate route selection experiment in
`exp/results/runtime/learned_runtime_gate_combined60_feature_cal000_v1/`.
The older first-wave repository-execution files documented below are planning,
dry-run, or readiness artifacts unless a completed validated result table is
explicitly present.

## Pair Analysis

Run the paired non-inferiority and resource analysis:

```bash
/bin/python -m exp.scripts.runtime.analyze_runtime_pairs \
  --task-results exp/results/<run_dir>/shadow_runtime_task_results.csv \
  --output-dir exp/results/runtime/<analysis_dir> \
  --target sempc_lite \
  --reference rsrc_guarded \
  --success-margin 0.05 \
  --min-publication-pairs 30
```

Outputs:

- `runtime_pairwise_metrics.csv`
- `runtime_noninferiority_summary.csv`
- `runtime_pair_analysis_report.md`

## Power Planning

Plan paired sample sizes before running publication-grade repository experiments:

```bash
/bin/python -m exp.scripts.runtime.plan_runtime_power \
  --output-dir exp/results/runtime/power_plan_v1 \
  --manifest exp/results/runtime/manifest_v1/task_manifest.csv \
  --margin 0.05 \
  --target-power 0.80
```

Outputs:

- `runtime_power_grid.csv`
- `runtime_power_recommendations.csv`
- `runtime_power_plan.md`

## Execution Matrix

Create a no-execution task-controller schedule for the first controlled-runtime batch:

```bash
/bin/python -m exp.scripts.runtime.build_execution_matrix \
  --manifest exp/results/runtime/manifest_v1/task_manifest.csv \
  --output-dir exp/results/runtime/manifest_v1
```

Outputs:

- `runtime_execution_matrix.csv`
- `runtime_execution_matrix.md`

## Prompt-Only Dry Run

Validate controller prompts and result logging without cloning repositories or running tests:

```bash
/bin/python -m exp.scripts.runtime.dry_run_controller_harness \
  --matrix exp/results/runtime/manifest_v1/runtime_execution_matrix.csv \
  --manifest exp/results/runtime/manifest_v1/task_manifest.csv \
  --output-dir exp/results/runtime/dry_run_v1 \
  --max-tasks 2 \
  --mode offline
```

Optional local LM Studio prompt-only dry run:

```bash
/bin/python -m exp.scripts.runtime.dry_run_controller_harness \
  --output-dir exp/results/runtime/dry_run_lmstudio_smoke \
  --max-tasks 1 \
  --controllers sempc_lite \
  --mode lmstudio
```

Full LM Studio prompt-only contract dry run for the 24-task first batch:

```bash
/bin/python -m exp.scripts.runtime.dry_run_controller_harness \
  --output-dir exp/results/runtime/dry_run_lmstudio_full_contract_v1 \
  --max-tasks 24 \
  --mode lmstudio \
  --timeout 120 \
  --max-tokens 700 \
  --progress-every 8
```

Analyze the offline and LM Studio prompt-only plans:

```bash
/bin/python -m exp.scripts.runtime.analyze_dry_run_decisions \
  --dry-run-dirs exp/results/runtime/dry_run_offline_full_v1 exp/results/runtime/dry_run_lmstudio_full_contract_v1 \
  --output-dir exp/results/runtime/dry_run_analysis_lmstudio_contract_v1
```

Outputs:

- `runtime_dry_run_plans.csv`
- `runtime_dry_run_requests.jsonl`
- `runtime_task_results_template.csv`
- `runtime_dry_run_report.md`

Dry-run outputs are schema/prompt checks only. They are not solve-rate, resource-savings, or downstream-work evidence.

The current contract dry run covers 24 tasks x 4 controllers with LM Studio model `qwen2.5-coder-7b-instruct-mlx`. It records 0 missing decisions and 0 fixed-controller contract violations: `static_conservative` always returns `inherit_baseline`, `minimal_verify` always returns `minimal_plan`, while `sempc_lite` and `rsrc_guarded` retain adaptive decision freedom. The corresponding template is rejected by `validate_runtime_results.py` because prompt-only rows and empty observed metrics are not executable evidence.

## Current Pilot

The existing 8-task LM Studio pilot can validate the analysis shape:

```bash
/bin/python -m exp.scripts.runtime.analyze_runtime_pairs \
  --task-results exp/results/theory_support/shadow_runtime_sphinx8_lm_pilot/shadow_runtime_task_results.csv \
  --output-dir exp/results/runtime/pilot_pair_analysis \
  --target sempc_lite \
  --reference rsrc_guarded \
  --success-margin 0.05 \
  --min-publication-pairs 30
```

The pilot is not publication-grade evidence because it has only 8 paired tasks and no informative solve-rate successes for the primary pair.

## Result Validation

Validate a completed task-results CSV before paired analysis:

```bash
/bin/python -m exp.scripts.runtime.validate_runtime_results \
  --task-results exp/results/<run_dir>/shadow_runtime_task_results.csv \
  --output-dir exp/results/runtime/<validation_dir> \
  --target sempc_lite \
  --reference rsrc_guarded
```

`analyze_runtime_pairs.py` runs the same validation automatically before analysis. By default it rejects:

- missing `instance_id` or `controller` columns;
- missing target/reference controller rows;
- duplicate instance/controller rows;
- prompt-only or dry-run rows;
- non-completed `execute_status` values when present;
- empty primary observed metrics such as `success`, `search_count`, `read_count`, `test_runs`, and `patch_attempts`.

Use `--allow-incomplete` or `--allow-prompt-only` only for schema debugging, never for evidence claims.

## Batch Status Report

Summarize the current controlled-runtime batch without executing repository code:

```bash
/bin/python -m exp.scripts.runtime.report_runtime_batch_status
```

Outputs:

- `batch_status_v1/runtime_batch_status_report.md`
- `batch_status_v1/runtime_batch_status_summary.json`
- `batch_status_v1/runtime_execute_status_counts.csv`
- `batch_status_v1/runtime_controller_status.csv`
- `batch_status_v1/runtime_pair_readiness.csv`
- `batch_status_v1/runtime_checklist_summary.csv`

The status report is an evidence-hygiene artifact. It should show zero completed rows until isolated repository runs are actually performed and recorded.

## Execution Priority Plan

Rank the planned task-controller rows for a future isolated first wave:

```bash
/bin/python -m exp.scripts.runtime.plan_execution_priority
```

Outputs:

- `execution_priority_v1/runtime_task_execution_priority.csv`
- `execution_priority_v1/runtime_row_execution_queue.csv`
- `execution_priority_v1/runtime_execution_priority_plan.md`
- `execution_priority_v1/runtime_execution_priority_summary.json`

The current first wave selects 12 tasks / 48 controller rows. It prioritizes tasks where the contracted LM Studio prompt-only decisions differ between `sempc_lite` and `rsrc_guarded`, while keeping paired target/reference rows adjacent and all rows marked `not_run`. This is a queueing and audit artifact only; it is not execution evidence.

## First-Wave Execution Bundle

Materialize the recommended first-wave rows into a recorder-compatible no-execution bundle:

```bash
/bin/python -m exp.scripts.runtime.prepare_first_wave_execution_bundle
```

Outputs:

- `first_wave_execution_bundle_v1/isolated_execution_manifest.csv`
- `first_wave_execution_bundle_v1/runtime_task_results_empty.csv`
- `first_wave_execution_bundle_v1/row_execution_checklist.csv`
- `first_wave_execution_bundle_v1/first_wave_pair_plan.csv`
- `first_wave_execution_bundle_v1/execution_runbook.md`
- `first_wave_execution_bundle_v1/first_wave_bundle_summary.json`

The current bundle contains 12 tasks / 48 controller rows, keeps `sempc_lite` and `rsrc_guarded` pair rows adjacent, and includes `static_conservative` plus `minimal_verify` controls for the same tasks. It is compatible with `record_isolated_runtime_result.py --bundle-dir exp/results/runtime/first_wave_execution_bundle_v1`.

For ordinary row-by-row recording, leave `--results-in` unset. Once `runtime_task_results_recorded.csv` exists in the bundle directory, `record_isolated_runtime_result.py` reads it by default before writing the next row, preserving earlier completed rows.

Use checklist flags only for facts that are true for the isolated run: `--preflight-passed`, `--sensitive-env-removed`, `--repo-snapshot-prepared`, `--dependencies-reviewed`, `--dependencies-installed`, `--target-tests-run`, and `--validator-passed`. Completed rows automatically mark `observed_metrics_recorded`; rows recorded with `--ack-isolated` also mark `isolation_ack_present`.

Prepare per-row isolated workspace handoff artifacts without executing repositories:

```bash
/bin/python -m exp.scripts.runtime.prepare_isolated_row_workspace \
  --output-dir exp/results/runtime/first_wave_workspace_plan_v1
```

Outputs:

- `first_wave_workspace_plan_v1/workspace_index.csv`
- `first_wave_workspace_plan_v1/workspace_plan_summary.json`
- `first_wave_workspace_plan_v1/workspace_plan_report.md`
- per-row workspace directories under `first_wave_workspace_plan_v1/rows/`

The workspace plan writes an agent prompt, guarded snapshot setup shell template, metrics template, and recorder command for each first-wave row. It does not clone repositories, install dependencies, apply patches, or run tests. Run the generated shell templates only inside an approved isolated environment with `CAMC_RUNTIME_ISOLATION_ACK=1` and sensitive environment variables removed.

Summarize already-local external agent traces that overlap first-wave tasks:

```bash
/bin/python -m exp.scripts.runtime.summarize_existing_agent_traces
```

Outputs:

- `existing_agent_trace_supplement_v1/existing_agent_trace_summary.csv`
- `existing_agent_trace_supplement_v1/existing_agent_trace_summary.json`
- `existing_agent_trace_supplement_v1/existing_agent_trace_report.md`

This supplement does not execute repositories or models. It can inform qualitative error/rework taxonomy design, but it is not paired controlled-runtime evidence for `sempc_lite` versus `rsrc_guarded`.

Prepare a bridge from the first-wave bundle to the older live shadow-runtime runner:

```bash
/bin/python -m exp.scripts.runtime.run_first_wave_shadow_bridge \
  --output-dir exp/results/runtime/first_wave_shadow_bridge_v1
```

Outputs:

- `first_wave_shadow_bridge_v1/first_wave_shadow_task_manifest.csv`
- `first_wave_shadow_bridge_v1/first_wave_shadow_row_plan.csv`
- `first_wave_shadow_bridge_v1/first_wave_shadow_bridge_report.md`
- `first_wave_shadow_bridge_v1/first_wave_shadow_bridge_summary.json`

The default bridge run is plan-only and performs no repository execution. The bridge exists so an approved isolated operator can execute the first-wave rows with the already-instrumented shadow-runtime runner and convert the resulting `shadow_runtime_task_results.csv` into the current runtime schema. Actual execution requires all of the following: `--execute --live-repo --ack-third-party-code`, `CAMC_RUNTIME_ISOLATION_ACK=1`, and no `SSH_AUTH_SOCK` in the environment. Use `--update-bundle-results` only after a real isolated run if the converted rows should become the first-wave bundle's `runtime_task_results_recorded.csv`.

Prepare a Docker isolation plan for running the first-wave bridge:

```bash
/bin/python -m exp.scripts.runtime.prepare_first_wave_docker_isolation
```

Outputs:

- `first_wave_docker_isolation_plan_v1/Dockerfile`
- `first_wave_docker_isolation_plan_v1/run_first_wave_bridge_in_docker.sh`
- `first_wave_docker_isolation_plan_v1/validate_first_wave_docker_results.sh`
- `first_wave_docker_isolation_plan_v1/first_wave_docker_isolation_report.md`
- `first_wave_docker_isolation_plan_v1/first_wave_docker_isolation_summary.json`

This generator is plan-only. It does not build Docker images, launch containers, clone repositories, call LM Studio, apply patches, or run tests. The generated launch script is the execution boundary: it requires `CAMC_DOCKER_RUNTIME_ACK=1`, refuses to run with `SSH_AUTH_SOCK` or common credential-bearing environment variables, mounts the project read-only, and mounts only the runtime output directory read-write. The wrapper still uses the current shadow-runtime bridge, so it does not yet build official SWE-bench per-task environments; verify task dependency logs before interpreting rows as task-quality evidence.

Generate first-wave packets from the contracted LM Studio dry-run plans:

```bash
/bin/python -m exp.scripts.runtime.build_isolated_execution_packets \
  --bundle-dir exp/results/runtime/first_wave_execution_bundle_v1 \
  --dry-run-plans exp/results/runtime/dry_run_lmstudio_full_contract_v1/runtime_dry_run_plans.csv \
  --output-dir exp/results/runtime/first_wave_execution_packets_v1
```

Generate the first-wave status report:

```bash
/bin/python -m exp.scripts.runtime.report_first_wave_status
```

The first-wave status wrapper reads `runtime_task_results_recorded.csv` if it exists in the bundle directory; otherwise it reads `runtime_task_results_empty.csv`. It also writes `first_wave_status_source.json` so the selected result source is auditable. Legacy first-wave protocol status: 48 planned rows, 12 tasks, 0 completed rows, 0 primary-metric-complete rows, and 48 markdown plus 48 JSON packet files present. This status refers only to the older repository-execution first-wave bundle, not to the completed 60-task fixed-candidate Study 3.

Generate the first-wave operator launch sheet:

```bash
/bin/python -m exp.scripts.runtime.prepare_first_wave_launch_sheet
```

Outputs:

- `first_wave_launch_sheet_v1/first_wave_operator_launch_sheet.csv`
- `first_wave_launch_sheet_v1/first_wave_operator_launch_sheet.md`
- `first_wave_launch_sheet_v1/first_wave_launch_summary.json`

The launch sheet converts the first-wave packet index into row-level operator actions and recording command templates. It should show zero `ready_to_execute` rows until the isolated preflight is cleared and row-specific blockers are resolved. It is not execution evidence.

Generate the preflight-clearance handoff:

```bash
/bin/python -m exp.scripts.runtime.prepare_preflight_clearance_handoff
```

Outputs:

- `preflight_clearance_handoff_v1/preflight_clearance_handoff.md`
- `preflight_clearance_handoff_v1/preflight_clearance_summary.json`
- `preflight_clearance_handoff_v1/preflight_clearance_checklist.csv`

This handoff preserves the current failing preflight state and provides command templates for a later approved isolated shell. It must not be treated as a passing preflight or runtime evidence.

Validate the empty template before execution:

```bash
/bin/python -m exp.scripts.runtime.validate_runtime_results \
  --task-results exp/results/runtime/first_wave_execution_bundle_v1/runtime_task_results_empty.csv \
  --output-dir exp/results/runtime/first_wave_execution_bundle_v1_validation \
  --target sempc_lite \
  --reference rsrc_guarded
```

Expected status before real execution: `FAIL`, with `incomplete_execute_status` and `empty_primary_metric` issues. This negative validation prevents the first-wave template from being mistaken for policy-effect evidence.

## First-Wave Analysis Drill

Run a synthetic completed-row drill to verify the validation, pair-analysis, and publication-artifact plumbing:

```bash
/bin/python -m exp.scripts.runtime.make_first_wave_analysis_drill
/bin/python -m exp.scripts.runtime.validate_runtime_results \
  --task-results exp/results/runtime/first_wave_analysis_drill_v1/runtime_task_results_synthetic_completed.csv \
  --output-dir exp/results/runtime/first_wave_analysis_drill_validation_v1 \
  --target sempc_lite \
  --reference rsrc_guarded
/bin/python -m exp.scripts.runtime.analyze_runtime_pairs \
  --task-results exp/results/runtime/first_wave_analysis_drill_v1/runtime_task_results_synthetic_completed.csv \
  --output-dir exp/results/runtime/first_wave_analysis_drill_pair_analysis_v1 \
  --target sempc_lite \
  --reference rsrc_guarded \
  --success-margin 0.05 \
  --min-publication-pairs 30 \
  --bootstrap-rounds 500
/bin/python -m exp.scripts.runtime.make_runtime_publication_artifacts \
  --analysis-dir exp/results/runtime/first_wave_analysis_drill_pair_analysis_v1 \
  --output-dir exp/results/runtime/first_wave_analysis_drill_publication_artifacts_v1 \
  --evidence-status synthetic_drill_not_publication_evidence \
  --scope-note 'Synthetic first-wave rows verify the validation-analysis-publication plumbing only; no repository code was executed and no solve-rate or resource claim is supported.'
```

The drill creates 24 completed-looking primary rows for 12 first-wave pairs and verifies that the analysis scripts run end-to-end. It is explicitly synthetic: no repository code is executed, LM Studio is not called, `publication_ready_success_claim=false`, and the generated publication artifact is labeled `synthetic drill: not publication evidence`.

## Evidence Strategy

Summarize what the current controlled-runtime evidence can and cannot support:

```bash
/bin/python -m exp.scripts.runtime.plan_runtime_evidence_strategy
```

Outputs:

- `evidence_strategy_v1/runtime_evidence_strategy.md`
- `evidence_strategy_v1/runtime_evidence_strategy_summary.json`
- `evidence_strategy_v1/runtime_claim_gate_table.csv`
- `evidence_strategy_v1/runtime_evidence_stages.csv`

The strategy report combines batch status, pair-readiness status, power recommendations, and manuscript material-gap counts. It currently treats the 24-task first batch as feasibility/resource-accounting preparation, not as sufficient evidence for a strong 5 percentage-point solve-rate non-inferiority claim.
