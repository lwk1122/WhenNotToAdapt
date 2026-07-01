---
type: results-report
date: 2026-06-25
experiment_line: standalone_module-agentic-software-engineering
round: current-standalone_module-vs-ijoc
purpose: summarize-new-experiments-and-results-relative-to-ijoc-version
status: updated
current_report:
  - ExtraExperiment/report_context/workload_gate_report.tex
ijoc_reference:
  - reference_archive/report_ijoc.tex
  - reference_archive/online_supplement_ijoc.tex
primary_new_results:
  - ExtraExperiment/results/pull_request_workload_gate/aidev_main_gate_table.csv
  - ExtraExperiment/results/pull_request_workload_gate/aidev_gate_uncertainty_table.csv
  - ExtraExperiment/results/pull_request_workload_gate/aidev_baseline_comparison_table.csv
  - ExtraExperiment/results/pull_request_workload_gate/aidev_equal_coverage_baseline_table.csv
  - ExtraExperiment/results/pull_request_workload_gate/aidev_feature_boundary_ablation_table.csv
  - ExtraExperiment/results/pull_request_workload_gate/aidev_component_prediction_table.csv
  - ExtraExperiment/results/pull_request_workload_gate/aidev_workload_sensitivity_table.csv
  - ExtraExperiment/results/pull_request_workload_gate/aidev_subgroup_diagnostic_table.csv
  - ExtraExperiment/results/pull_request_workload_gate/aidev_subgroup_fallback_table.csv
  - ExtraExperiment/results/pull_request_workload_gate/aidev_gate_error_table.csv
  - ExtraExperiment/results/pull_request_workload_gate/aidev_resolution_survival_contrast_table.csv
evidence_boundary:
  - ExtraExperiment/results/runtime_control_protocol/first_wave_batch_status_v1/runtime_batch_status_summary.json
  - ExtraExperiment/artifact_package/artifact_validation_report.md
---

# standalone module 新增实验与结果汇总：相对 IJOC 版本

## 1. 一句话结论

当前 standalone module 版本相对 IJOC 版本的实质性新增实验，是以 AIDev 为核心的真实 agent-authored PR 观测研究。它新增了 `33,596` 个真实 PR、`2,807` 个 repository、`5` 类 agent 的 proposal-time workload gate 评估，并形成 temporal split、unseen repository split、baseline comparison、equal-coverage diagnostic、feature-boundary ablation、component prediction、workload sensitivity、subgroup/fallback、gate error taxonomy 和 survival diagnostic。

IJOC 版本已有的 known-kernel queue、trace/proxy diagnostics、proxy simulator 和 255-task synthetic runtime 并没有消失。当前 standalone module 稿件把它们降级为 supplementary mechanism checks，用来解释选择机制，而不是作为真实软件工程主证据。

以下记录是早期 first-wave repository-execution protocol 的历史状态，不是当前主文 Study 3 的完成状态。该 first-wave 包准备了 `12` tasks / `48` rows，但状态是 `0 completed rows` 和 `0 primary-metric-complete rows`。因此它只能作为 protocol 或 future work 记录，不能作为 standalone module 的真实 runtime 结果。当前主文使用的完成版 fixed-candidate Study 3 结果位于 `../exp/results/emse_runtime/`。

## 2. 论文身份变化

| 维度 | IJOC 版本 | 当前 standalone module 版本 | 是否为新增证据 |
|---|---|---|---|
| 论文身份 | 通用 OR/control 框架，强调 workload externality 和 Robust Pareto-CASC | 真实软件工程观测研究，强调 agent PR workload triage 和 calibration-selected gate | 是，定位改变 |
| 主证据 | known-kernel queue、trace/proxy diagnostics、proxy simulator、synthetic runtime | AIDev 真实 PR 观测研究为主，旧实验为机制补充 | 是 |
| 数据单位 | 构造环境、trace proxy state、synthetic task、live synthetic Python task | 一个 agent-authored pull request | 是 |
| 主要决策 | 是否选择 adaptive action 或额外 context | PR 是否进入 standard path，还是 routed for extra review/checks | 是 |
| 主要结论 | 选择器在构造环境和 proxy model 中按设计工作；synthetic runtime 可节省资源 | proposal-time 信息能预测 downstream workload；gate 在 shift 下以 coverage contraction 换取较低 standard-path risk | 是 |
| 因果边界 | 旧稿容易被读成 action-level workload externality | 明确声明 AIDev 不识别 action-level causal effect | 是，边界更清楚 |
| 旧实验位置 | 主 empirical ladder | Supplementary mechanism checks | 不是新实验，是重新定位 |

## 3. 当前 standalone module 版本新增实验总表

| 新增分析 | IJOC 版本是否已有 | 当前结果 | 支撑的 claim |
|---|---:|---|---|
| AIDev main gate study | 否 | 33,596 real agent PRs；temporal AUC 0.900；unseen repository AUC 0.764 | 真实 PR proposal-time 信息含有 downstream workload signal |
| Temporal risk-coverage selection | 否 | standard-path rate 0.842；standard-path high-workload rate 0.074；base rate 0.142 | calibration-selected gate 可形成 risk-coverage tradeoff |
| Unseen repository risk-coverage selection | 否 | standard-path rate 0.313；standard-path high-workload rate 0.079；base rate 0.332 | repository shift 下 gate 主要通过收缩 coverage 保持较低 point estimate |
| Repository-cluster bootstrap | 否 | unseen repository standard-path high-workload 0.079 [0.049, 0.122] | 主结果有 repository-level uncertainty，但不是 distribution-free guarantee |
| Baseline comparison | 否 | workload-weighted logistic 接近主模型；no-agent、prior、text、uncertainty baselines 更弱或 coverage collapse | 贡献不是最强分类器，而是 auditable workload gate |
| Equal-coverage diagnostic | 否 | 同等 calibration coverage 下，主模型 high-workload 0.079；text 0.235；uncertainty 0.491 | 低 risk 不是单纯由低 coverage 造成 |
| Feature-boundary ablation | 否 | defensible features 与 full timing-sensitive aggregate features 均 AUC 0.764 | 主结果不依赖 snapshot timing 不清楚的 PR API aggregates |
| Component prediction | 否 | related issues AUC 0.934；issue comments 0.825；later commits 0.776；human reviews 0.747 | workload 不是单一黑箱指标，多个后续工作通道可被预测 |
| Workload-definition sensitivity | 否 | 5 definitions、3 thresholds、2 splits；27 valid fits、3 skipped sparse fits | 主结论对合理 workload 定义稳定，sparse human-review target 是 limitation |
| Subgroup and cross-agent diagnostics | 否 | OpenAI Codex coverage 0.676/high 0.068；Copilot 0.007；Devin 0.003 | global calibration transfer 有局部性，需要 subgroup monitoring/recalibration |
| Local fallback diagnostic | 否 | risk-flag fallback coverage 0.087/high 0.063；risk-or-low-support coverage 0.082/high 0.039 | 更保守的 local fallback 可降低 standard-path risk，但代价是 coverage |
| Gate error taxonomy | 否 | unseen repo: standard low 1,003；standard high 86；routed high 1,071；routed low 1,322 | shift 下主要代价是低 workload PR 被 routed，而不是大量 high workload PR 进入 standard path |
| Resolution-time survival diagnostic | 否 | 30-day unresolved probability 0.047 vs 0.144；RMST 2.218 vs 6.458 days | standard/routed strata 在 resolution dynamics 上不同，但不是 treatment effect |
| Artifact/evidence boundary validation | 部分无 | validation PASS；0 failures；0 warnings；runtime non-evidence 边界被检查 | 可复现性和证据边界更强 |
| Legacy first-wave controlled runtime package | 否 | 12 tasks / 48 rows prepared；0 completed rows | 只是 protocol，不是 empirical result；不对应当前主文 Study 3 完成结果 |

## 4. AIDev Study 1：新增主实验

### 4.1 数据、特征和 outcome

当前 standalone module 主文的 Study 1 使用 AIDev 派生表：

- `33,596` agent-authored PRs；
- `2,807` repositories；
- `5` agents；
- `85` nonempty repository languages；
- `12` inferred task types；
- `31,284` closed PRs 和 `2,312` open/censored PRs。

主 gate 使用 `18` 个 defensible proposal features，包括 title/body 长度和关键词、repository language/stars、task type/confidence、agent identity，以及 first observed commit detail fields。PR API aggregate fields 被排除在主 gate 外，因为公开 schema 不能证明这些字段一定是 proposal-time snapshot。

主 workload score 是以下后续工作量的等权和：

- review records；
- request-change outcomes；
- inline review comments；
- issue comments；
- later commits after the first observed commit SHA。

High workload label 由对应 split 的 training set 中 primary workload score 的 80th percentile 定义。主 calibration risk limit 为 `0.10`。

### 4.2 Split 设计

| Split | Fit rows | Calibration rows | Test rows | 目的 |
|---|---:|---:|---:|---|
| Temporal | 20,157 | 6,719 | 6,720 | 时间外推 |
| Unseen repository | 25,652 | 4,462 | 3,482 | repository-disjoint 外部有效性压力测试 |

Unseen repository split 中 fit/calibration/test 的 repository identifier overlap 为 0。当前主文把 unseen repository split 作为更强的 external-validity test。

## 5. AIDev main gate 结果

| Split | AUC | AP | Base high-workload rate | Standard-path rate | Standard-path high-workload rate | High-workload routed share | Mean workload standard | Mean workload routed | Workload share routed |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Temporal | 0.900 | 0.493 | 0.142 | 0.842 | 0.074 | 0.559 | 1.693 | 11.650 | 0.564 |
| Unseen repository | 0.764 | 0.541 | 0.332 | 0.313 | 0.079 | 0.926 | 1.375 | 9.043 | 0.935 |

核心解释：

- Temporal split 下，gate 将 standard-path high-workload rate 从 base 0.142 降到 0.074，同时保留 84.2% 的 standard-path coverage。
- Unseen repository split 下，base high-workload rate 高达 0.332，gate 的 standard-path coverage 收缩到 31.3%，standard-path high-workload point estimate 为 0.079。
- 这不是“gate 消除了 93.5% workload”。正确写法是：在 retrospective grouping 中，routed group 包含 93.5% observed workload。
- AIDev 没有记录 routed workflow 实施后的反事实结果，因此不能说 gate causally reduces workload。

Repository-cluster bootstrap 结果：

| Split | Metric | Point estimate and 95% CI |
|---|---|---|
| Temporal | AUC | 0.900 [0.692, 0.956] |
| Temporal | Standard-path rate | 0.842 [0.597, 0.930] |
| Temporal | Standard-path high-workload rate | 0.074 [0.029, 0.254] |
| Temporal | Workload share routed | 0.564 [0.504, 0.625] |
| Unseen repository | AUC | 0.764 [0.702, 0.814] |
| Unseen repository | Standard-path rate | 0.312 [0.223, 0.416] |
| Unseen repository | Standard-path high-workload rate | 0.079 [0.049, 0.122] |
| Unseen repository | Workload share routed | 0.935 [0.899, 0.959] |

注意：unseen repository 的 high-workload CI 上界超过 0.10，因此主文应写“point estimate remains below the risk target”，不能写“guarantees the 10% target”。

## 6. 新增 baseline 与 equal-coverage 结果

### 6.1 Risk-target comparison

Unseen repository split、risk limit 0.10 下：

| Method | AUC | Standard-path rate | Standard-path high-workload rate | Workload share routed |
|---|---:|---:|---:|---:|
| Defensible proposal features | 0.764 | 0.313 | 0.079 | 0.935 |
| Workload-weighted logistic | 0.765 | 0.304 | 0.077 | 0.939 |
| Logistic without agent identity | 0.726 | 0.273 | 0.107 | 0.922 |
| Categorical prior | 0.749 | 0.305 | 0.094 | 0.918 |
| Simple text threshold | 0.660 | 0.001 | near-empty | 1.000 |
| Selective uncertainty only | 0.376 | 0.000 | near-empty | 0.999 |

结论：

- Workload-weighted logistic 是强 baseline，与主模型几乎持平。
- 因此论文不应声称“预测器性能最强”。
- 贡献应写成：把 workload prediction、calibration、routing 和 auditability 组合成一个可审计 decision layer。

### 6.2 Equal-coverage diagnostic

同等 calibration coverage 下，unseen repository test 的 standard-path high-workload rate 为：

| Method | Standard-path high-workload rate |
|---|---:|
| Defensible proposal features | 0.079 |
| Workload-weighted logistic | 0.077 |
| Categorical prior | 0.107 |
| Logistic without agent identity | 0.120 |
| Simple text threshold | 0.235 |
| Selective uncertainty only | 0.491 |

这个新增分析解决了一个重要审稿质疑：低 risk 不只是因为 gate 接受得少。若强制弱 baseline 接受相近比例，它们的 standard-path risk 明显更高。

## 7. 新增 feature-boundary 与 leakage 结果

当前 standalone module 版本新增了 timing boundary 和 feature-boundary ablation。主文明确区分：

- main defensible proposal features；
- first observed commit detail fields；
- timing-sensitive PR API aggregates；
- downstream outcomes。

关键结果：

- Defensible feature set 和包含 timing-sensitive API aggregate 的 full set 在 unseen repository 下都得到 AUC 0.764，standard-path rate 约 0.31，standard-path high-workload rate 0.079。
- Text/repo/task feature set 接近，AUC 0.762，standard-path rate 0.305，standard-path high-workload rate 0.079。
- First observed commit details alone 明显更弱，在 0.10 risk limit 下基本无法提供有效 gate。

这部分是 IJOC 版本没有的，因为 IJOC 主要讨论 trace/proxy observability ladder，而不是 AIDev public schema 下的 PR timing boundary。

## 8. 新增 component prediction 结果

Unseen repository split 下，各 workload component 的主要结果如下：

| Component | Positive rate | AUC | Average precision |
|---|---:|---:|---:|
| Related issue count | 0.274 | 0.934 | 0.851 |
| Issue comment count | 0.330 | 0.825 | 0.679 |
| Later commit count | 0.372 | 0.776 | 0.605 |
| Later changed files | 0.420 | 0.768 | 0.673 |
| Later churn | 0.348 | 0.767 | 0.591 |
| Later files related to tests | 0.228 | 0.756 | 0.479 |
| Human review count | 0.277 | 0.748 | 0.463 |
| Inline review comments | 0.186 | 0.706 | 0.341 |
| Review count | 0.348 | 0.705 | 0.519 |
| Request changes | 0.045 | 0.687 | 0.079 |

结论：

- AIDev 的 signal 不只来自一个 composite score。
- related issues、issue comments、later commits、later files/churn 是最强工作量通道。
- request changes 很稀疏，AP 低，不能单独作为主 outcome。

## 9. 新增 workload-definition sensitivity

当前 standalone module 版本对 workload 定义做了系统敏感性分析：

- 5 个 workload definitions；
- 3 个 high-workload thresholds；
- 2 种 split；
- 27 个 valid fits；
- 3 个 skipped fits，原因是 sparse human-review target 只有一个 training class。

0.80 threshold 下的主结果：

| Definition | Temporal AUC | Temporal standard-path high | Unseen repo AUC | Unseen repo standard-path high |
|---|---:|---:|---:|---:|
| Primary aggregate | 0.900 | 0.074 | 0.764 | 0.079 |
| Communication review | 0.910 | 0.073 | 0.769 | 0.098 |
| Later revision | 0.900 | 0.068 | 0.760 | 0.092 |
| Broad with issues | 0.907 | 0.069 | 0.786 | 0.076 |
| Human reviews | 0.888 | 0.081 | skipped | skipped |

结论：

- 主 pattern 对 aggregate、communication、later revision、broad definitions 稳定。
- sparse human-review-only target 不稳定，应作为 limitation，而不是主证据。

## 10. 新增 subgroup、agent shift 与 fallback 结果

Unseen repository split 的 subgroup diagnostics 显示 global gate 的转移性有限：

- OpenAI Codex subgroup: standard-path coverage 0.676，standard-path high-workload rate 0.068。
- Copilot subgroup: standard-path coverage 0.007。
- Devin subgroup: standard-path coverage 0.003。
- 仍有若干 shifted subgroups 超过 0.10 risk target，包括 repositories with more than 1000 stars、initial churn 251-1000、Go repositories、test task labels。

新增 local fallback diagnostic：

| Strategy | Flagged groups | Flagged test share | Standard-path rate | Standard-path high-workload rate | Workload share routed |
|---|---:|---:|---:|---:|---:|
| Global gate | 0 | 0.000 | 0.313 | 0.079 | 0.935 |
| Calibration risk flags | 6 | 0.789 | 0.087 | 0.063 | 0.986 |
| Risk or low support flags | 15 | 0.904 | 0.082 | 0.039 | 0.992 |

解释：

- 这不是新的主方法，而是 deployment diagnostic。
- 它表明 local calibration 能进一步降低 standard-path risk，但会显著牺牲 coverage。
- 该结果支持 Discussion 中的 local/rolling recalibration、coverage monitoring 和 fallback requirement。

## 11. 新增 gate error taxonomy

Unseen repository split、risk limit 0.10 下：

| Observational category | n | Share | Mean workload | Median workload |
|---|---:|---:|---:|---:|
| Standard-path low workload | 1,003 | 0.288 | 0.504 | 0 |
| Standard-path high workload | 86 | 0.025 | 11.523 | 9 |
| Routed high workload | 1,071 | 0.308 | 18.115 | 12 |
| Routed low workload | 1,322 | 0.380 | 1.693 | 2 |

Temporal split 下：

| Observational category | n | Share | Mean workload | Median workload |
|---|---:|---:|---:|---:|
| Standard-path low workload | 5,238 | 0.779 | 0.443 | 0 |
| Standard-path high workload | 419 | 0.062 | 17.317 | 12 |
| Routed high workload | 532 | 0.079 | 20.417 | 14 |
| Routed low workload | 531 | 0.079 | 2.866 | 3 |

写作边界：

- 这些类别是 observational categories，不是因果错误类型。
- `routed low workload` 不应写成 false rejection，因为没有观察该 PR 进入 routed workflow 后的 counterfactual。
- unseen repository 下主要代价是 routed low workload，而不是 standard-path high workload。

## 12. 新增 resolution-time survival diagnostic

当前版本新增了 right-censoring 处理：

- observation cutoff: 2025-07-30 23:20:55 UTC；
- open PRs 作为 censored observations；
- 使用 Kaplan-Meier unresolved probability 和 30-day RMST。

Unseen repository split：

| Group | Rows | Closed events | Censored open | 30-day unresolved probability | 30-day RMST |
|---|---:|---:|---:|---:|---:|
| Standard path | 1,085 | 1,029 | 56 | 0.047 | 2.218 days |
| Routed | 2,397 | 2,102 | 295 | 0.144 | 6.458 days |

Standard-path minus routed bootstrap contrasts：

| Metric | Point | 95% CI |
|---|---:|---:|
| Observed closure-rate difference | 0.072 | [0.038, 0.111] |
| 30-day unresolved probability difference | -0.098 | [-0.155, -0.052] |
| 30-day RMST unresolved difference | -4.258 days | [-6.156, -2.856] |

解释：

- Standard-path PRs 在观测上更快关闭、更少 unresolved。
- 这只能作为 risk strata diagnostic，不能解释为 routing treatment effect。

## 13. IJOC 版本已有并被保留的实验

### 13.1 Known-kernel queue

IJOC 版本已经包含该实验。当前 standalone module 稿件保留为 supplementary mechanism check。

设计：

- generated primitives；
- 64 seeds；
- horizon 600；
- low、mixed、high shift；
- oracle no-adaptation region 已知；
- 比较 loss-only rule 和 Pareto gate。

结果：

- low shift: adaptive action use 下降 25.88 percentage points；no-adaptation recall 从 0.1335 升到 1.0000；activation precision 从 0.733 升到 1.000。
- mixed shift: adaptive action use 下降 8.04 percentage points；activation precision 提升 80.72 percentage points。
- high shift: 两者都继承 baseline，因此 contrast 为 0。

当前写法应限于：当 primitives generated and observable 时，Pareto rule 能恢复 intended no-adaptation logic。它不是 AIDev 真实 PR 证据。

### 13.2 Trace/proxy diagnostics 和 proxy simulator

IJOC 版本已有：

- full-proxy predictive diagnostics；
- post-proposal certificate diagnostics；
- proxy simulator；
- loss-only vs Pareto gate frontier comparison。

关键旧结果包括：

- full-proxy failure AUC 0.9341、service R2 0.8467、total-load R2 0.7581；
- post-proposal certificate precision 0.9608，但 theta-safe nonempty rate 0.1496、recall 0.1522；
- proxy simulator 中 Pareto-CASC 相对 loss-only switching 减少 over-activation，并恢复 success。

当前 standalone module 稿件将这些放入 supplement，因为：

- full-proxy stack 包含 oracle 或 post-outcome channels；
- simulator transition 与 predictor 来自同一 trace-derived construction；
- AIDev 已经提供更直接的真实 PR proposal-time evidence。

### 13.3 Controlled synthetic repository execution

IJOC 版本已有该 live synthetic runtime experiment。当前 standalone module 稿件保留为 supplementary mechanism check。

设计：

- 45、90、120-task replications；
- pooled 255 paired task comparisons；
- public synthetic Python repair tasks；
- plain、always adapt、Pareto gate workflows；
- task regions 被人为划分为 anchor-sufficient、adaptation-useful、low-value-adaptation。

主要旧结果：

- Pareto gate workflow solves 100%；
- always adapt solves 98.4%；
- exact paired equality test `p=0.125`；
- 相对 always adapt，Pareto gate 减少 model calls 1.149/task [1.075, 1.231]；
- tokens 减少 933/task [854, 1,022]；
- latency 减少 8.31 seconds/task [7.65, 9.00]；
- accounting cost 减少 0.956/task [0.877, 1.045]。

当前 standalone module 版本的正确表述：

- 可以说 selective context purchase 在 constructed task stream 中 observed comparable solved-task performance with lower resource use。
- 不能说正式 non-inferiority。
- 不能推广到 natural repository traffic。

## 14. 当前 runtime first wave：新增 protocol，但不是新增结果

当前版本确实新增了 controlled runtime 的执行准备，但它仍然没有 completed evidence。

已经完成的准备：

- SWE-bench Verified task manifest；
- 24-task / 96-row execution matrix；
- LM Studio prompt-only dry run；
- first-wave 12-task / 48-row execution bundle；
- first-wave packets；
- Docker isolation plan；
- row recorder；
- batch status report；
- synthetic analysis drill。

当前 first-wave scope：

- selected tasks: 12；
- selected rows: 48；
- repositories: 8；
- controllers: `minimal_verify`, `rsrc_guarded`, `sempc_lite`, `static_conservative`；
- primary pair: `sempc_lite` vs `rsrc_guarded`；
- pair rows: 12。

当前状态：

- completed result rows: 0；
- primary-metric-complete rows: 0；
- selected result file: empty template；
- third-party repository execution performed: false；
- first-wave preflight still records a FAIL state due isolation acknowledgment / clearance boundary；
- synthetic drill explicitly marked non-evidence。

因此该部分不能用于报告：

- solve rate；
- tokens；
- calls；
- tests；
- patch attempts；
- failed verification；
- recovery attempts；
- downstream/rework reduction；
- `sempc_lite` vs `rsrc_guarded` paired treatment effect。

如果未来要正式声称 5 percentage-point solve-rate non-inferiority，当前 power plan 仍显示大约需要 600-1000 paired tasks。12-task 或 24-task 规模只能作为 pilot 或 feasibility/resource-accounting evidence。

## 15. 当前 standalone module 版本能支持的主 claims

当前证据可以支持：

1. 真实 agent-authored PR 在 proposal/review timing boundary 上已经包含 downstream workload signal。
2. Calibration-selected workload gate 可以把 prediction 转化成 standard-path risk 与 coverage 的透明权衡。
3. Under unseen repository shift, gate 主要通过 standard-path coverage contraction 维持较低 standard-path high-workload point estimate。
4. Workload signal 分布在 review、comments、later commits、later churn、related issues 等多个 component 上。
5. 简单 text threshold 或 uncertainty threshold 不能替代 workload-aware calibrated gate；但 workload-weighted logistic 是强 baseline，论文不应主张 predictive dominance。
6. Global calibration 在 agent/repository subgroup 上有明显 locality，需要 monitoring、fallback 或 local recalibration。
7. AIDev 支持 observational workload triage，不支持 causal workload reduction。

当前证据不能支持：

1. Gate causally reduces downstream workload in real repositories。
2. 同一 PR 在 standard handling 和 routed handling 下的 counterfactual comparison。
3. Extra adaptation 或 extra verification 的 action-level causal effect。
4. `sempc_lite` 相对 `rsrc_guarded` 的真实 paired solve-rate non-inferiority。
5. 真实 runtime 中 tokens/calls/tests/patch attempts/failed verification/recovery attempts 的节省。
6. 多 model/agent controlled runtime 泛化。

## 16. 相对 IJOC 的最重要增量

从投稿角度看，最重要的增量不是“又加了一个实验”，而是证据结构改变了：

- IJOC 版本的实证主线容易被批评为 framework-constructed environments。
- 当前 standalone module 版本把主证据转移到 AIDev 真实 PR 数据，直接回应“constructed for that purpose”的问题。
- IJOC 版本强调 action-induced workload externality；当前版本承认 AIDev 只观测 historical workflow 下的 downstream workload，因此只声称 proposal-time workload triage。
- IJOC 版本的 runtime 结果来自 synthetic task regions；当前版本把它降为 mechanism check，避免过度声称。
- 当前版本新增了 standalone module 更期待的 empirical software engineering elements：dataset profile、timing boundary、component outcomes、repository-disjoint evaluation、subgroup shift、survival/censoring、error taxonomy、artifact validation。

## 17. 主要 artifact 索引

### 当前 standalone report

- `ExtraExperiment/report_context/workload_gate_report.tex`
- `ExtraExperiment/report_context/workload_gate_report_supplement.tex`

### IJOC reference

- `reference_archive/report_ijoc.tex`
- `reference_archive/online_supplement_ijoc.tex`

### AIDev 新增结果

- Main gate: `ExtraExperiment/results/pull_request_workload_gate/aidev_main_gate_table.csv`
- Bootstrap uncertainty: `ExtraExperiment/results/pull_request_workload_gate/aidev_gate_uncertainty_table.csv`
- Calibration diagnostics: `ExtraExperiment/results/pull_request_workload_gate/aidev_calibration_diagnostics_table.csv`
- Baselines: `ExtraExperiment/results/pull_request_workload_gate/aidev_baseline_comparison_table.csv`
- Equal coverage: `ExtraExperiment/results/pull_request_workload_gate/aidev_equal_coverage_baseline_table.csv`
- Feature boundary: `ExtraExperiment/results/pull_request_workload_gate/aidev_feature_boundary_ablation_table.csv`
- Components: `ExtraExperiment/results/pull_request_workload_gate/aidev_component_prediction_table.csv`
- Workload sensitivity: `ExtraExperiment/results/pull_request_workload_gate/aidev_workload_sensitivity_table.csv`
- Subgroups: `ExtraExperiment/results/pull_request_workload_gate/aidev_subgroup_diagnostic_table.csv`
- Fallback: `ExtraExperiment/results/pull_request_workload_gate/aidev_subgroup_fallback_table.csv`
- Error taxonomy: `ExtraExperiment/results/pull_request_workload_gate/aidev_gate_error_table.csv`
- Survival: `ExtraExperiment/results/pull_request_workload_gate/aidev_resolution_survival_contrast_table.csv`
- Figures: `ExtraExperiment/results/pull_request_workload_gate/figures/`
- LaTeX tables: `ExtraExperiment/results/pull_request_workload_gate/tables_tex/`

### Runtime protocol and non-evidence boundary

- First-wave bundle: `ExtraExperiment/results/runtime_control_protocol/first_wave_execution_bundle_v1/first_wave_bundle_summary.json`
- First-wave batch status: `ExtraExperiment/results/runtime_control_protocol/first_wave_batch_status_v1/runtime_batch_status_summary.json`
- Runtime power plan: `ExtraExperiment/results/runtime_control_protocol/power_plan_v1/runtime_power_plan.md`
- Artifact validation: `ExtraExperiment/artifact_package/artifact_validation_report.md`
