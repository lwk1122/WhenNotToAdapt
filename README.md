This package contains the scripts, derived data, and result files.

# Manuscript Evidence Map

- Study 1 and Study 2 use the AIDev pull request workload-gate pipeline.
  The main scripts are in `exp/scripts/aidev/`, and the copied outputs are in
  `ExtraExperiment/results/pull_request_workload_gate/`.
- Study 3 uses the executable context budget experiment. The task scripts are
  in `exp/scripts/runtime/`, and the completed 60-task score-gate outputs are
  in `exp/results/runtime/learned_runtime_gate_combined60_feature_cal000_v1/`.
- The original 30-task subset check is in
  `exp/results/runtime/lmstudio_executable_context_gate_repeat_analysis_v1/`.
- The queue, trace, and proxy simulator files under `exp/results/theory_support/`
  support mechanism checks only. They are not the main field evidence.

# Main Result Files

- `ExtraExperiment/results/pull_request_workload_gate/aidev_main_gate_table.csv`
- `ExtraExperiment/results/pull_request_workload_gate/aidev_qcvl_proxy_summary.csv`
- `ExtraExperiment/results/pull_request_workload_gate/aidev_workload_sensitivity_table.csv`
- `ExtraExperiment/results/pull_request_workload_gate/aidev_resolution_survival_contrast.csv`
- `exp/results/runtime/learned_runtime_gate_combined60_feature_cal000_v1/learned_runtime_gate_summary.json`
- `exp/results/runtime/learned_runtime_gate_combined60_feature_cal000_v1/learned_runtime_task_results.csv`
- `exp/results/runtime/lmstudio_executable_context_gate_repeat_analysis_v1/runtime_repeat_analysis_report.md`

# Evidence Boundaries

The AIDev analyses are retrospective observational analyses. They support
workload risk selection in logged pull requests. The executable context budget
experiment supports route selection over fixed candidate repairs. It records
calls, tokens, latency, selected candidates, and local test outcomes for paired
low-context and full-context branches.

Several older first-wave controlled-runtime files remain in the package because
they document protocol development. They are clearly marked as prompt-only,
planning, dry-run, or non-evidence artifacts in their local README files. They
are not used as manuscript evidence for the completed Study 3 result.

# Basic Setup

Install the Python dependencies from the copied package root:

```bash
python3 -m venv .venv_replication
.venv_replication/bin/python -m pip install -r ExtraExperiment/requirements.txt
```

Most scripts expect the package root on `PYTHONPATH`, for example:

```bash
PYTHONPATH=. .venv_replication/bin/python -m exp.scripts.aidev.evaluate_workload_gate
PYTHONPATH=. .venv_replication/bin/python -m exp.scripts.runtime.analyze_learned_runtime_gate
```

Dataset downloads may require network access. The copied result files allow the
reported tables and diagnostics to be inspected without re-downloading all raw
inputs.
