# ExtraExperiment

This directory is a standalone copy of the added experiment modules. It keeps
the experiment code, protocol notes, derived result tables, figures, and
validation artifacts together without depending on the paper directory.

## Contents

- `scripts/pull_request_workload_gate/`: AIDev pull-request workload-gate
  feature construction, gate evaluation, baselines, uncertainty, subgroup,
  sensitivity, error-taxonomy, survival, table, and figure scripts.
- `results/pull_request_workload_gate/`: Derived AIDev feature tables,
  summaries, figures, LaTeX-ready tables, and diagnostic outputs.
- `scripts/runtime_control_protocol/`: Controlled-runtime planning,
  dry-run, validation, first-wave bundle, packet, power, and analysis scripts.
- `results/runtime_control_protocol/`: Runtime protocol outputs, dry-run
  checks, first-wave execution bundles, packet files, validation reports, and
  non-evidence analysis drills.
- `Dataset/`: Raw or external input datasets needed by the copied pipelines.
  This includes AIDev raw Parquet files, SWE-bench Verified input files, and
  the small CodeTraceBench trace subset referenced by the auxiliary trace scan.
- `artifact_package/`: Data dictionary files for the pull-request workload
  feature table.
- `docs/`: Experiment summaries and protocol notes in publication-neutral form.
- `INPUTS.md`: Input inventory and evidence-boundary notes.

## Evidence Boundary

The pull-request workload-gate results are completed observational evidence.
The controlled-runtime first-wave materials in this `ExtraExperiment` copy are
legacy execution protocols and readiness artifacts unless a completed result
table is explicitly recorded. They are not used as manuscript evidence for the
completed executable context budget experiment. The completed 60-task Study 3
outputs are stored in `../exp/results/runtime/`.

## Basic Setup

```bash
python3 -m venv .venv_experiment
.venv_experiment/bin/python -m pip install -r ExtraExperiment/requirements.txt
```

Run scripts with the project root on `PYTHONPATH`, for example:

```bash
PYTHONPATH=. .venv_experiment/bin/python -m ExtraExperiment.scripts.pull_request_workload_gate.evaluate_workload_gate
```
