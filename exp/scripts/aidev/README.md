# AIDev Analysis Scripts

This directory contains the first AIDev pipeline. This pipeline builds an
observational validation layer from real AIDev PRs after proposal generation:

1. Download or locate AIDev tables.
2. Build PR level proposal time features and downstream workload outcomes.
3. Run conservative calibrated routing diagnostics under realistic splits.

## Expected Data Layout

By default, scripts read from:

```text
exp/Dataset/AIDev/
```

The downloader writes Hugging Face files under:

```text
exp/Dataset/AIDev/raw/
```

The feature builder searches recursively for Parquet files whose path contains table names such as
`pull_request`, `repository`, `pr_reviews`, `pr_review_comments_v2`, `pr_commits`, and `pr_timeline`.

## Dependencies

Install the revision dependencies from the repository root:

```bash
python3 -m venv 
/bin/python -m pip install -r requirements.txt
```

Network access is needed only for downloading the dataset or installing packages.

## Commands

Download selected AIDev tables. The default downloader uses `curl --continue-at -` and
validates Parquet footers, so interrupted files such as large commit detail tables can be resumed:

```bash
/bin/python -m exp.scripts.aidev.download_aidev
```

If Hugging Face snapshot/Xet download stalls, use the default `curl` method or download individual
Parquet tables into `exp/Dataset/AIDev/raw/` and rerun the feature builder. The current core pipeline uses
`pull_request`, `repository`, `pr_reviews`, `pr_review_comments_v2`, `pr_comments`,
`pr_commits`, `related_issue`, and `pr_task_type`.

Resume specific useful tables:

```bash
/bin/python -m exp.scripts.aidev.download_aidev --method curl --tables pr_commit_details pr_timeline
```

Build PR level features and outcomes:

```bash
/bin/python -m exp.scripts.aidev.build_features
```

Run the initial lightweight calibrated routing diagnostic:

```bash
/bin/python -m exp.scripts.aidev.evaluate_abstention
```

Run the split evaluation:

```bash
/bin/python -m exp.scripts.aidev.evaluate_workload_gate
```

Compare gate baselines under the same calibration protocol. This includes the defensible-feature gate,
uncertainty threshold rule, logistic model without agent identity, categorical prior, simple text threshold, and a
logistic classifier with workload weights:

```bash
/bin/python -m exp.scripts.aidev.evaluate_gate_baselines
```

Evaluate individual downstream workload components:

```bash
/bin/python -m exp.scripts.aidev.evaluate_workload_components
```

Analyze gate error and routing cases for RQ4:

```bash
/bin/python -m exp.scripts.aidev.analyze_gate_errors
```

Compute repository cluster bootstrap uncertainty intervals for the main workload gate metrics:

```bash
/bin/python -m exp.scripts.aidev.bootstrap_gate_uncertainty
```

Analyze subgroup and shift diagnostics for the global workload gate:

```bash
/bin/python -m exp.scripts.aidev.analyze_subgroup_shift
```

Check whether timing-sensitive PR API aggregate fields drive the gate:

```bash
/bin/python -m exp.scripts.aidev.analyze_feature_boundary_ablation
```

Analyze censored time to closure diagnostics for accepted and routed PRs:

```bash
/bin/python -m exp.scripts.aidev.analyze_resolution_survival
```

Evaluate whether the gate conclusions change under alternative downstream workload definitions and high workload thresholds:

```bash
/bin/python -m exp.scripts.aidev.evaluate_workload_sensitivity
```

Create manuscript facing result tables:

```bash
/bin/python -m exp.scripts.aidev.summarize_aidev_results
```

Generate editable SVG figures and LaTeX ready PDF copies:

```bash
/bin/python -m exp.scripts.aidev.make_aidev_figures
```

Generate LaTeX table inputs for the manuscript:

```bash
/bin/python -m exp.scripts.aidev.make_latex_tables
```

Outputs are written to:

```text
exp/results/aidev/
```

Main output files:

- `aidev_pr_level_features.csv`
- `aidev_feature_build_summary.json`
- `aidev_workload_gate_summary.csv`
- `aidev_workload_gate_summary.json`
- `aidev_gate_baseline_summary.csv`
- `aidev_workload_component_prediction.csv`
- `aidev_gate_error_report.md`
- `aidev_gate_error_summary.csv`
- `aidev_gate_error_cases.csv`
- `aidev_gate_uncertainty_summary.csv`
- `aidev_gate_uncertainty_report.md`
- `aidev_gate_uncertainty_table.csv`
- `aidev_feature_boundary_ablation_table.csv`
- `aidev_subgroup_gate_summary.csv`
- `aidev_subgroup_gate_table.csv`
- `aidev_subgroup_diagnostic_table.csv`
- `aidev_subgroup_gate_report.md`
- `aidev_resolution_survival_summary.csv`
- `aidev_resolution_survival_contrast.csv`
- `aidev_resolution_survival_report.md`
- `aidev_workload_sensitivity_summary.csv`
- `aidev_workload_sensitivity_report.md`
- `aidev_workload_sensitivity_table.csv`
- `aidev_results_tables.md`
- `figures/aidev_coverage_risk_frontier.svg`
- `figures/aidev_coverage_risk_frontier.pdf`
- `figures/aidev_baseline_comparison.svg`
- `figures/aidev_baseline_comparison.pdf`
- `figures/aidev_component_auc.svg`
- `figures/aidev_component_auc.pdf`
- `figures/aidev_gate_error_composition.svg`
- `figures/aidev_gate_error_composition.pdf`
- `figures/aidev_resolution_survival.svg`
- `tables_tex/aidev_main_gate_table.tex`
- `tables_tex/aidev_baseline_comparison_table.tex`
- `tables_tex/aidev_component_auc_table.tex`
- `tables_tex/aidev_feature_boundary_ablation_table.tex`
- `tables_tex/aidev_subgroup_diagnostic_table.tex`
- `tables_tex/aidev_gate_error_table.tex`
- `tables_tex/aidev_survival_contrast_table.tex`
- `tables_tex/aidev_latex_table_manifest.json`
