# RQ4 Draft: Gate Errors, Abstentions, and Shift Behavior

## Section Purpose

This section explains what the AIDev gate accepts, abstains from, and misses. It should be used as an interpretability and validity section, not as causal evidence. In AIDev, an abstained low-workload PR is an over-conservative observational case, not a proven false rejection, because the dataset does not contain the counterfactual workflow that would have run under a different gate decision.

## Analysis Setup

We apply the same all-feature logistic workload gate used in Study 1. The target is high aggregate downstream workload at the training-set 80th percentile, and the gate threshold is chosen on the calibration split at risk budget 0.10. Each held-out PR is assigned to one of four categories:

- **Safe accept:** accepted by the gate and not high workload.
- **False accept:** accepted by the gate but high workload.
- **Useful abstain:** abstained by the gate and high workload.
- **Conservative abstain:** abstained by the gate but not high workload.

These categories are diagnostic labels. They describe gate behavior against observed downstream workload, but they do not imply that a different gate decision would have caused a different PR outcome.

## Main Patterns

### Temporal Split

Under the temporal split, most PRs are safe accepts. The gate accepts 5,239 low-workload PRs, representing 78.0% of the test set. It misses 419 high-workload PRs, or 6.2% of the test set. It abstains from 532 high-workload PRs, or 7.9%, and conservatively abstains from 530 low-workload PRs, also 7.9%.

The two high-workload categories have much larger downstream burden than the low-workload categories. False accepts average 17.3 units of downstream workload, while useful abstentions average 20.4. Safe accepts average only 0.44. Conservative abstentions average 2.87, indicating that some abstained PRs still carry moderate review or follow-up activity even though they are below the high-workload threshold.

### Repository-Disjoint Split

Repository-disjoint shift produces a different error profile. Safe accepts fall to 999 PRs, or 28.7% of the test set. False accepts fall to 86 PRs, or 2.5%. Useful abstentions increase to 1,071 PRs, or 30.8%. Conservative abstentions also increase to 1,326 PRs, or 38.1%.

This is the clearest evidence of conservative contraction under repository shift. The gate intercepts most high-workload PRs, but it does so by abstaining from many low-workload PRs as well. Useful abstentions average 18.1 units of downstream workload, compared with 11.5 for false accepts, 1.69 for conservative abstentions, and 0.51 for safe accepts.

## Error Taxonomy

### 1. High-Workload Misses

False accepts are accepted PRs that later show high review or rework burden. In the repository-disjoint split, these cases are rare but consequential: 86 PRs, with mean downstream workload 11.5 and median 9.0. They are dominated by OpenAI Codex cases in the current split, with 72 of 86 examples. Many involve substantial follow-up commits or inline review comments despite low predicted risk.

Report interpretation:

> False accepts show where proposal-time features understate later review and rework burden. They are the operational cost of preserving coverage.

### 2. High-Workload Abstentions

Useful abstentions are PRs that the gate refuses and that later show high downstream workload. Under repository-disjoint shift, they form 30.8% of the test set and account for high average workload. They are dominated by Copilot and Devin cases in the current split. Many examples involve many follow-up commits, issue comments, inline review comments, or related issues.

Report interpretation:

> Useful abstentions are the main success mode of the conservative gate: the gate identifies PRs whose proposal-time evidence suggests elevated downstream burden.

### 3. Conservative Abstentions

Conservative abstentions are PRs that are below the high-workload threshold but still rejected by the gate. Under repository-disjoint shift, this category is large: 38.1% of the test set. These cases quantify the coverage cost of conservative calibration. They should not be described as definitive false rejections because AIDev does not observe what would have happened under the accepted adaptive workflow.

Report interpretation:

> Conservative abstentions are the price of shift robustness. The gate avoids many high-workload PRs, but at the cost of rejecting many low-workload PRs when repository-level generalization is uncertain.

### 4. Safe Accepts

Safe accepts are accepted PRs with low observed downstream workload. Under the temporal split, this is the dominant category. Under repository-disjoint shift, it shrinks sharply. In the current split, safe accepts are dominated by OpenAI Codex PRs, reflecting the dataset and split structure. This supports the broader finding that agent and repository distributions strongly affect gate coverage.

Report interpretation:

> Safe accepts are the coverage value of the gate. Their contraction under repository shift should be reported together with the reduction in false accepts.

## Suggested Table

| Split | Safe accept | False accept | Useful abstain | Conservative abstain | Main interpretation |
|---|---:|---:|---:|---:|---|
| Temporal | 5,239 (78.0%) | 419 (6.2%) | 532 (7.9%) | 530 (7.9%) | High coverage with moderate high-workload misses. |
| Repository-disjoint | 999 (28.7%) | 86 (2.5%) | 1,071 (30.8%) | 1,326 (38.1%) | Strong conservative contraction under repository shift. |

## Suggested Main-Text Paragraph

The error analysis clarifies what the calibrated gate gains and loses. In the temporal split, the gate mostly accepts low-workload PRs: 5,239 safe accepts, or 78.0% of the test set. It still misses 419 high-workload PRs. In the repository-disjoint split, the gate becomes much more conservative: false accepts fall to 86 PRs, or 2.5% of the test set, but conservative abstentions rise to 1,326 PRs, or 38.1%. This pattern is consistent with the intended shift behavior. The gate protects against high downstream workload by shrinking coverage when repository-level generalization is weak. The cost is that many below-threshold PRs inherit the baseline. Because AIDev is observational, these low-workload abstentions should be interpreted as coverage cost rather than as counterfactual false rejections.

## Validity Guardrails

- Do not call conservative abstentions "false rejections" unless a paired controlled runtime result exists.
- Do not claim false accepts or useful abstentions are causal effects of the gate.
- Use this section to support interpretability, calibration tradeoffs, and shift behavior.
- Use controlled runtime traces, once available, to validate whether the same error taxonomy holds when the same task is run under paired workflows.

## Source Artifacts

- Full report: `ExtraExperiment/results/pull_request_workload_gate/aidev_gate_error_report.md`
- Summary table: `ExtraExperiment/results/pull_request_workload_gate/aidev_gate_error_summary.csv`
- Sampled cases: `ExtraExperiment/results/pull_request_workload_gate/aidev_gate_error_cases.csv`
- Report-facing compact table: `ExtraExperiment/results/pull_request_workload_gate/aidev_gate_error_table.csv`
