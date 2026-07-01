# Study 1 Draft: Real-World Downstream Workload Evidence from AIDev

## Study Purpose

The AIDev study tests whether proposal-time information in real agent-authored pull requests contains enough signal to support a conservative downstream-workload gate. This study is observational. It evaluates workload measurement, prediction, calibration, and shift behavior; it does not estimate the causal effect of accepting or rejecting adaptive effort for the same task.

## Research Questions Addressed

**RQ1:** Can downstream review and rework workload be measured and predicted from proposal-time information in real agent-authored PRs?

**RQ2:** Does calibrated gating remain conservative under temporal, repository-disjoint, and cross-agent shifts?

## Data and Unit of Analysis

We use AIDev-pop as the real-world observational data source. The current feature table contains 33,596 agent-authored pull requests. Each row is a pull request with proposal-time features and downstream workload outcomes. The observed agents include OpenAI Codex, Copilot, Devin, Cursor, and Claude Code.

The decision point is post-proposal: the agent has produced an initial pull request, and the gate decides whether the workflow should permit additional agent effort, verification, or escalation. This decision point is important because it allows initial PR metadata and initial patch features to be observed while excluding review outcomes and follow-up work from the feature set.

## Feature Construction

The proposal-time feature set uses information visible at or near the initial PR proposal:

- repository metadata, including language and activity descriptors;
- agent identity;
- task type when available;
- issue and PR title/body descriptors;
- initial patch structure, including changed files, additions, deletions, churn, and test-like files.

Initial patch features are derived from `pr_commit_details` and `pr_timeline`. The first committed `commit_id` per PR is used as the best available approximation of the proposal-time diff. Commit-detail rows after the initial commit are treated as follow-up outcomes, not decision-time features.

The design deliberately excludes review comments, request-change events, follow-up commits, post-review churn, merge/close status, resolution time, and any other post-outcome information from the predictor. Full-proxy or oracle-style variables should only be used for diagnostics, not for the main Study 1 claims.

## Downstream Workload Outcomes

The study reports individual workload components before using any aggregate score. Current outcomes include:

- review count;
- human review count;
- request-changes count;
- inline review comments;
- issue comments;
- follow-up commit count, approximated as `max(pr_commit_count - 1, 0)`;
- follow-up changed files;
- follow-up detail churn;
- follow-up test-like files;
- related issue count;
- resolution time and merge indicator as secondary outcomes.

The aggregate downstream workload target is a count-based composite and excludes timeline event count to avoid double-counting comments, reviews, and commits.

## Splits and Calibration

The main evaluation uses three shift-aware designs:

1. **Temporal split:** train, calibrate, and test on chronological partitions.
2. **Repository-disjoint split:** evaluate on repositories not used for training/calibration.
3. **Leave-one-agent-out split:** train without one agent and test on that held-out agent.

The calibrated gate accepts a PR only if the predicted probability of high downstream workload clears a pre-specified risk budget. Otherwise, the gate abstains by inheriting the conservative baseline workflow. This framing treats abstention as an operational decision, not as a missing prediction.

## Main Results

### Temporal Split

In the temporal split, proposal-time features predict high downstream workload with AUC 0.900 and average precision 0.493. At the calibrated 0.10 risk budget, the gate accepts 84.2% of test PRs. The accepted high-workload rate is 0.074, compared with a test-set high-workload base rate of 0.142. Abstained PRs contain 56.4% of total downstream workload.

This result supports the claim that proposal-time information contains meaningful downstream-workload signal when training, calibration, and testing follow chronological deployment order.

Using 500 repository-cluster bootstrap resamples of the held-out test split, the temporal AUC is 0.900 [0.692, 0.956], acceptance rate is 0.842 [0.597, 0.930], accepted high-workload rate is 0.074 [0.029, 0.254], and workload share abstained is 0.564 [0.504, 0.625].

### Repository-Disjoint Split

Under repository-disjoint shift, performance drops but remains operationally useful. The AUC is 0.764 and average precision is 0.540. At the same 0.10 risk budget, acceptance contracts to 31.2%. The accepted high-workload rate is 0.079, compared with a test-set base rate of 0.332. Abstained PRs contain 93.5% of total downstream workload.

The contraction is an important result rather than only a weakness. It shows the gate becoming more selective under stronger shift. The tradeoff is lower coverage: a conservative gate can protect against high downstream workload, but it may reject many potentially acceptable PRs when repository-level generalization is uncertain.

The repository-disjoint cluster-bootstrap intervals are tighter for the main operational metrics: AUC is 0.764 [0.702, 0.814], acceptance rate is 0.312 [0.223, 0.416], accepted high-workload rate is 0.079 [0.049, 0.122], high-workload recall by abstention is 0.926 [0.888, 0.953], and workload share abstained is 0.935 [0.899, 0.959].

### Baseline Comparison

The all-feature workload gate is compared with several simpler baselines under the same calibration protocol:

- a logistic model without agent identity;
- a workload-severity-weighted cost-sensitive logistic classifier;
- a categorical prior over agent, task type, and repository language;
- a simple title/body threshold rule;
- an uncertainty-only selective abstention rule.

On the repository-disjoint split at risk budget 0.10, the all-feature gate accepts 31.2% of PRs with accepted high-workload rate 0.079. The cost-sensitive classifier accepts 30.6% with accepted high-workload rate 0.077, making it a close workload-aware competitor rather than a dominated strawman. The categorical prior accepts 30.5% with accepted high-workload rate 0.094. The no-agent logistic model accepts 27.7% with accepted high-workload rate 0.108. The simple text threshold accepts almost nothing at this risk budget, making it conservative but not operationally useful. The uncertainty-only rule is not a reliable substitute under repository shift.

These comparisons support the narrower claim that calibrated workload-aware gating is not merely reproducing a generic conservative threshold over text length, agent priors, or uncertainty. They should not be written as a decisive win over every workload-aware classifier.

### Workload Components

Component-level prediction shows that downstream workload is not a single homogeneous outcome. Under the repository-disjoint split, the strongest component signals are:

| Component | AUC |
|---|---:|
| Related issue count | 0.934 |
| Issue comment count | 0.825 |
| Follow-up commit count | 0.776 |
| Follow-up changed files | 0.768 |
| Follow-up detail churn | 0.767 |
| Follow-up test-like files | 0.756 |
| Human review count | 0.747 |
| Inline review comments | 0.706 |
| Review count | 0.706 |
| Request changes | 0.687 |

This pattern argues for reporting workload components alongside any aggregate score. Related issues, issue comments, follow-up commits, and follow-up churn/files carry stronger and more stable signal than request-change events, which are rarer.

### Workload Definition Sensitivity

We rerun the same calibrated 0.10 risk-budget gate under five workload definitions: the original aggregate, a communication/review aggregate, a human-review aggregate, a follow-up revision/churn aggregate, and a broader aggregate that adds related issues and follow-up churn. We also vary the high-workload threshold across the 0.75, 0.80, and 0.90 training quantiles.

At the 0.80 threshold, the qualitative result is stable. In the temporal split, AUC ranges from 0.888 to 0.910 across valid definitions, acceptance ranges from 0.828 to 0.842, and accepted high-workload rates range from 0.068 to 0.081. In the repository-disjoint split, the aggregate, communication, follow-up, and broad definitions produce AUCs from 0.760 to 0.786, acceptance from 0.208 to 0.382, and accepted high-workload rates from 0.078 to 0.097. The repository-disjoint human-review fit at the 0.80 threshold is invalid because the training split contains only one high-workload class under that sparse target.

The sensitivity results support two cautions. First, human-review-only targets are too sparse for low high-workload thresholds. Second, very high thresholds can make temporal calibration accept nearly all PRs, which removes the workload-abstention benefit. The report should therefore report workload components and sensitivity diagnostics alongside the aggregate gate result.

### Cross-Agent Transfer

Leave-one-agent-out results show severe agent shift. The gate is much less reliable when a held-out agent differs from agents seen during training and calibration. For example, held-out OpenAI Codex has AUC 0.451 and held-out Copilot has AUC 0.507 under the current setup.

This result should be reported plainly. It limits broad cross-agent generalization claims and motivates agent-specific, local, or online calibration before deployment.

### Subgroup and Shift Diagnostics

The subgroup diagnostic evaluates the same global 0.10 risk-budget gate within held-out agent, language, task-type, repository-star, and initial-churn subgroups. This analysis is diagnostic: the gate is calibrated globally, so subgroup accepted high-workload rates are not guaranteed to remain below 0.10.

The repository-disjoint split shows the most important pattern. OpenAI Codex is the largest held-out agent subgroup with 1,577 PRs; the global gate accepts 67.3% of those PRs with accepted high-workload rate 0.068. In contrast, Copilot and Devin have high observed high-workload rates, 0.550 and 0.540, and the gate accepts only 0.8% and 0.3% of PRs. These are low-coverage diagnostics rather than reliable subgroup risk estimates.

Several non-agent subgroups exceed the global risk budget with enough accepted rows to flag them. In the repository-disjoint split, the \(>1000\)-star repository bucket has accepted high-workload rate 0.164 with 159 accepted PRs, Go repositories have accepted high-workload rate 0.339 with 59 accepted PRs, and test-task PRs have accepted high-workload rate 0.118 with 51 accepted PRs. These results support a local or online calibration design before deployment.

### Resolution-Time Survival Diagnostic

Resolution time is a secondary outcome because AIDev contains open PRs. Dropping those rows would bias the analysis toward PRs that have already resolved. We therefore treat open PRs as right-censored at the latest timestamp in the feature table, 2025-07-30 23:20:55 UTC, and report Kaplan-Meier unresolved probabilities plus restricted mean time unresolved (RMST).

Under the repository-disjoint split, accepted PRs have observed closure rate 0.948, while abstained PRs have observed closure rate 0.877. The Kaplan-Meier unresolved probability at 30 days is 0.047 for accepted PRs and 0.144 for abstained PRs. The 30-day RMST is 2.22 days for accepted PRs and 6.46 days for abstained PRs. Repository-cluster bootstrap contrasts give accepted-minus-abstained differences of -0.098 [-0.155, -0.052] for 30-day unresolved probability and -4.24 [-6.15, -2.82] days for 30-day RMST.

This is a validity diagnostic, not a causal result. Accepted and abstained PRs are observed gate strata, not randomized counterfactuals.

## Interpretation

The AIDev study supports three report claims:

1. Downstream review and rework workload can be operationalized using real PR artifacts rather than only synthetic proxy environments.
2. Proposal-time PR, repository, agent, task, and initial-diff features contain enough signal to support calibrated workload-aware abstention.
3. Repository and agent shift materially affect coverage and reliability, so conservative contraction and recalibration should be treated as core deployment behavior.
4. The workload conclusion is not tied to one aggregate score, but sparse and extreme-threshold workload targets should be handled as sensitivity diagnostics rather than primary claims.
5. Resolution-time summaries should handle open PRs as right-censored; accepted PRs are observationally separated from abstained PRs on censored time-to-closure diagnostics.

The study does not show that CASC causally improves outcomes for the same task. Because AIDev is observational, accepted and abstained PRs are not counterfactual versions of the same task. The controlled runtime study must provide the paired policy-effect evidence.

## Threats to Validity

**Observational confounding.** AIDev records PR artifacts and outcomes, not randomized gate decisions. The results support prediction and calibration, not causal deployment superiority.

**Decision-time ambiguity.** Initial patch features are reconstructed from the first committed PR event. This is the best available approximation of proposal-time information, but the exact internal agent trajectory is not observed.

**Outcome proxy limitations.** Review comments, follow-up commits, churn, and related issues are imperfect proxies for human effort or code quality. They should be interpreted as downstream workload indicators, not direct welfare measures. Component-level, workload-definition sensitivity, and censored resolution-time diagnostics should accompany any aggregate score.

**Resolution-time censoring.** Kaplan-Meier and RMST summaries handle open PRs more appropriately than complete-case resolution-time summaries, but they do not remove observational confounding between gate strata.

**Repository and agent imbalance.** The agent and repository distributions are uneven. Random row splits would overstate generalization; temporal, repository-disjoint, and leave-one-agent-out splits are therefore the primary designs.

**Rare event instability.** Request-change events are relatively rare and should not carry the main workload claim by thstandalone_modulelves.

**Patch-data limitations.** Very large diffs may be incomplete or affected by GitHub API limits. The report should report data coverage and use component-level sensitivity checks.

## Report Integration Notes

- Use this study as the first empirical result section.
- Lead with component workload measurement before aggregate workload.
- Use repository-disjoint results as the main external-validity stress test.
- Present cross-agent degradation as a limitation and deployment requirement, not a failure to hide.
- Refer to Study 2 for any claim about actual resource savings or solve-rate preservation under the gate.
