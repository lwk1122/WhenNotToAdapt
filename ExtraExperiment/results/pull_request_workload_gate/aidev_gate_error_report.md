# AIDev Gate Error and Routing Analysis

This report uses the same defensible-feature logistic gate and calibrated risk protocol as the main AIDev workload gate analysis.
It supports RQ4 by separating accepted low workload PRs, accepted high workload misses, routed high workload PRs, and routed low workload PRs.

## Split Diagnostics

| split | train_rows | calibration_rows | test_rows | risk_budget | high_workload_quantile | high_workload_threshold | score_threshold | calibrated_acceptance_target | calibrated_accepted_high_rate | test_auc | test_average_precision | test_acceptance_rate | test_accepted_high_workload_rate | features |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Temporal | 20157 | 6719 | 6720 | 0.100 | 0.800 | 2.079 | 0.769 | 0.828 | 0.100 | 0.900 | 0.493 | 0.842 | 0.074 | feature_title_chars,feature_body_chars,feature_title_mentions_test,feature_body_mentions_test,feature_body_mentions_fix,feature_repo_stars,feature_task_type_confidence,feature_initial_detail_changed_files,feature_initial_detail_additions,feature_initial_detail_deletions,feature_initial_detail_churn,feature_initial_detail_added_files,feature_initial_detail_modified_files,feature_initial_detail_removed_files,feature_initial_detail_test_files,agent,repo_language,feature_task_type |
| Unseen repository | 25652 | 4462 | 3482 | 0.100 | 0.800 | 1.792 | 0.357 | 0.315 | 0.100 | 0.764 | 0.541 | 0.313 | 0.079 | feature_title_chars,feature_body_chars,feature_title_mentions_test,feature_body_mentions_test,feature_body_mentions_fix,feature_repo_stars,feature_task_type_confidence,feature_initial_detail_changed_files,feature_initial_detail_additions,feature_initial_detail_deletions,feature_initial_detail_churn,feature_initial_detail_added_files,feature_initial_detail_modified_files,feature_initial_detail_removed_files,feature_initial_detail_test_files,agent,repo_language,feature_task_type |

## Case-Type Summary

| split | case | n | share | accepted_rate | high_workload_rate | mean_gate_score | mean_workload | median_workload | top_agents | mean_outcome_review_count | mean_outcome_human_review_count | mean_outcome_request_changes_count | mean_outcome_inline_review_comment_count | mean_outcome_issue_comment_count | mean_outcome_followup_commit_count | mean_outcome_followup_detail_changed_files | mean_outcome_followup_detail_churn | mean_outcome_followup_detail_test_files | mean_outcome_related_issue_count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Unseen repository | Route low workload | 1322 | 0.380 | 0.000 | 0.000 | 0.694 | 1.693 | 2.000 | Copilot=441; OpenAI_Codex=423; Devin=263; Cursor=152; Claude_Code=43 | 0.241 | 0.161 | 0.003 | 0.017 | 0.749 | 0.683 | 3.388 | 811.060 | 0.568 | 0.309 |
| Unseen repository | Accept high workload | 86 | 0.025 | 1.000 | 1.000 | 0.271 | 11.523 | 9.000 | OpenAI_Codex=72; Copilot=6; Cursor=6; Devin=2 | 1.721 | 0.628 | 0.151 | 1.756 | 1.721 | 6.174 | 16.012 | 1136.756 | 2.802 | 0.116 |
| Unseen repository | Accept low workload | 1003 | 0.288 | 1.000 | 0.000 | 0.223 | 0.504 | 0.000 | OpenAI_Codex=994; Cursor=6; Claude_Code=2; Copilot=1 | 0.088 | 0.060 | 0.000 | 0.010 | 0.195 | 0.211 | 0.905 | 65.578 | 0.163 | 0.025 |
| Unseen repository | Route high workload | 1071 | 0.308 | 0.000 | 1.000 | 0.799 | 18.115 | 12.000 | Copilot=534; Devin=307; Cursor=97; OpenAI_Codex=88; Claude_Code=45 | 3.809 | 2.371 | 0.230 | 3.782 | 3.670 | 6.624 | 42.569 | 6438.672 | 9.367 | 0.483 |
| Temporal | Route low workload | 531 | 0.079 | 0.000 | 0.000 | 0.853 | 2.866 | 3.000 | Copilot=363; Devin=104; Cursor=35; Claude_Code=29 | 0.412 | 0.311 | 0.009 | 0.060 | 1.047 | 1.337 | 9.578 | 4012.288 | 1.335 | 0.501 |
| Temporal | Accept high workload | 419 | 0.062 | 1.000 | 1.000 | 0.548 | 17.317 | 12.000 | Copilot=127; OpenAI_Codex=123; Cursor=91; Devin=43; Claude_Code=35 | 3.411 | 1.723 | 0.203 | 3.656 | 3.220 | 6.828 | 29.456 | 5859.391 | 6.685 | 0.303 |
| Temporal | Accept low workload | 5238 | 0.779 | 1.000 | 0.000 | 0.170 | 0.443 | 0.000 | OpenAI_Codex=4774; Cursor=183; Copilot=151; Devin=80; Claude_Code=50 | 0.058 | 0.028 | 0.001 | 0.021 | 0.179 | 0.184 | 1.117 | 197.226 | 0.156 | 0.031 |
| Temporal | Route high workload | 532 | 0.079 | 0.000 | 1.000 | 0.860 | 20.417 | 14.000 | Copilot=322; Devin=157; Claude_Code=35; Cursor=18 | 4.434 | 2.376 | 0.282 | 5.094 | 4.259 | 6.348 | 40.900 | 9079.186 | 7.976 | 0.492 |

## Example Cases

### Unseen repository: Route low workload

| split | case | html_url | agent | repo_language | feature_task_type | gate_score | score_threshold | outcome_downstream_workload_raw | case_summary |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Unseen repository | Route low workload | https://github.com/aldinokemal/go-whatsapp-web-multidevice/pull/338 | Cursor | Go | fix | 0.358 | 0.357 | 1.000 | Cursor / Go: 1 initial files; 7 initial churn; 1 issue comments |
| Unseen repository | Route low workload | https://github.com/MihaiCristianCondrea/Smart-Cleaner-for-Android/pull/197 | OpenAI_Codex | Kotlin | feat | 0.358 | 0.357 | 1.000 | OpenAI_Codex / Kotlin: 1 initial files; 191 initial churn; 1 follow-up commits |
| Unseen repository | Route low workload | https://github.com/MihaiCristianCondrea/Smart-Cleaner-for-Android/pull/154 | OpenAI_Codex | Kotlin | feat | 0.358 | 0.357 | 0.000 | OpenAI_Codex / Kotlin: 17 initial files; 255 initial churn |
| Unseen repository | Route low workload | https://github.com/eplatonoff/pilorama/pull/92 | OpenAI_Codex | QML | feat | 0.358 | 0.357 | 0.000 | OpenAI_Codex / QML: 1 initial files; 11 initial churn |
| Unseen repository | Route low workload | https://github.com/MihaiCristianCondrea/Smart-Cleaner-for-Android/pull/134 | OpenAI_Codex | Kotlin | feat | 0.358 | 0.357 | 0.000 | OpenAI_Codex / Kotlin: 3 initial files; 67 initial churn |
| Unseen repository | Route low workload | https://github.com/MihaiCristianCondrea/Smart-Cleaner-for-Android/pull/86 | OpenAI_Codex | Kotlin | feat | 0.358 | 0.357 | 0.000 | OpenAI_Codex / Kotlin: 9 initial files; 365 initial churn |

### Unseen repository: Accept high workload

| split | case | html_url | agent | repo_language | feature_task_type | gate_score | score_threshold | outcome_downstream_workload_raw | case_summary |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Unseen repository | Accept high workload | https://github.com/DogukanUrker/FlaskBlog/pull/191 | OpenAI_Codex | Python | feat | 0.340 | 0.357 | 43.000 | OpenAI_Codex / Python: 20 initial files; 127 initial churn; 17 follow-up commits; 23 inline review comments; 1 related issues |
| Unseen repository | Accept high workload | https://github.com/celestiaorg/celestia-core/pull/1948 | Copilot | Go | fix | 0.339 | 0.357 | 32.000 | Copilot / Go: 7 initial files; 3066 initial churn; 3 initial test-like files; 29 follow-up commits; 3 issue comments |
| Unseen repository | Accept high workload | https://github.com/coderamp-labs/gitingest/pull/315 | OpenAI_Codex | Python | feat | 0.275 | 0.357 | 30.000 | OpenAI_Codex / Python: 1 initial files; 75 initial churn; 1 initial test-like files; 29 follow-up commits; 1 issue comments |
| Unseen repository | Accept high workload | https://github.com/stanford-crfm/levanter/pull/1090 | OpenAI_Codex | Python | docs | 0.101 | 0.357 | 30.000 | OpenAI_Codex / Python: 5 initial files; 305 initial churn; 3 initial test-like files; 29 follow-up commits |
| Unseen repository | Accept high workload | https://github.com/GodsScion/Auto_job_applier_linkedIn/pull/58 | OpenAI_Codex | Python | feat | 0.214 | 0.357 | 29.000 | OpenAI_Codex / Python: 1 initial files; 28 initial churn; 29 follow-up commits |
| Unseen repository | Accept high workload | https://github.com/mega-sam/mega-sam/pull/37 | OpenAI_Codex | Python | feat | 0.259 | 0.357 | 26.000 | OpenAI_Codex / Python: 1 initial files; 113 initial churn; 26 follow-up commits |

### Unseen repository: Accept low workload

| split | case | html_url | agent | repo_language | feature_task_type | gate_score | score_threshold | outcome_downstream_workload_raw | case_summary |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Unseen repository | Accept low workload | https://github.com/mondaycom/vibe/pull/2917 | OpenAI_Codex | TypeScript | test | 0.035 | 0.357 | 0.000 | OpenAI_Codex / TypeScript: 86 initial files; 956 initial churn; 81 initial test-like files |
| Unseen repository | Accept low workload | https://github.com/jdeng/goheif/pull/34 | OpenAI_Codex | Go | docs | 0.037 | 0.357 | 0.000 | OpenAI_Codex / Go: 1 initial files; 25 initial churn |
| Unseen repository | Accept low workload | https://github.com/satmihir/fair/pull/15 | OpenAI_Codex | Go | docs | 0.041 | 0.357 | 0.000 | OpenAI_Codex / Go: 1 initial files; 36 initial churn |
| Unseen repository | Accept low workload | https://github.com/satmihir/fair/pull/16 | OpenAI_Codex | Go | docs | 0.048 | 0.357 | 0.000 | OpenAI_Codex / Go: 10 initial files; 130 initial churn; 1 initial test-like files |
| Unseen repository | Accept low workload | https://github.com/satmihir/fair/pull/20 | OpenAI_Codex | Go | docs | 0.055 | 0.357 | 0.000 | OpenAI_Codex / Go: 1 initial files; 13 initial churn |
| Unseen repository | Accept low workload | https://github.com/sebdah/goldie/pull/50 | OpenAI_Codex | Go | test | 0.059 | 0.357 | 0.000 | OpenAI_Codex / Go: 1 initial files; 40 initial churn; 1 initial test-like files |

### Unseen repository: Route high workload

| split | case | html_url | agent | repo_language | feature_task_type | gate_score | score_threshold | outcome_downstream_workload_raw | case_summary |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Unseen repository | Route high workload | https://github.com/spcl/dace/pull/2019 | Copilot | Python | feat | 0.823 | 0.357 | 150.000 | Copilot / Python: 1 initial files; 29 follow-up commits; 17 issue comments; 68 inline review comments; 1 related issues |
| Unseen repository | Route high workload | https://github.com/dotnet/macios/pull/23041 | Copilot | C# | test | 0.893 | 0.357 | 132.000 | Copilot / C#: 1 initial files; 13 follow-up commits; 30 issue comments; 54 inline review comments; 1 related issues |
| Unseen repository | Route high workload | https://github.com/microsoft/Qcodes/pull/7240 | Copilot | Python | fix | 0.834 | 0.357 | 117.000 | Copilot / Python: 29 follow-up commits; 8 issue comments; 50 inline review comments; 1 related issues |
| Unseen repository | Route high workload | https://github.com/dotnet/macios/pull/23045 | Copilot | C# | fix | 0.866 | 0.357 | 116.000 | Copilot / C#: 1 initial files; 19 follow-up commits; 30 issue comments; 32 inline review comments; 1 related issues |
| Unseen repository | Route high workload | https://github.com/spcl/dace/pull/2036 | Copilot | Python | docs | 0.696 | 0.357 | 114.000 | Copilot / Python: 1 initial files; 5 follow-up commits; 14 issue comments; 62 inline review comments; 1 related issues |
| Unseen repository | Route high workload | https://github.com/microsoft/typescript-go/pull/1387 | Copilot | Go | feat | 0.656 | 0.357 | 113.000 | Copilot / Go: 1 initial files; 29 follow-up commits; 12 issue comments; 42 inline review comments; 1 related issues |

### Temporal: Route low workload

| split | case | html_url | agent | repo_language | feature_task_type | gate_score | score_threshold | outcome_downstream_workload_raw | case_summary |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Temporal | Route low workload | https://github.com/Ljzd-PRO/KToolBox/pull/293 | Copilot | Python | feat | 0.769 | 0.769 | 6.000 | Copilot / Python: 1 initial files; 3 follow-up commits; 3 issue comments; 1 related issues |
| Temporal | Route low workload | https://github.com/Azure/azure-rest-api-specs/pull/36020 | Copilot | TypeSpec | docs | 0.770 | 0.769 | 3.000 | Copilot / TypeSpec: 1 initial files; 1 follow-up commits; 2 issue comments; 1 related issues |
| Temporal | Route low workload | https://github.com/QL-Win/QuickLook/pull/1723 | Copilot | C# | fix | 0.770 | 0.769 | 2.000 | Copilot / C#: 1 initial files; 2 follow-up commits; 1 related issues |
| Temporal | Route low workload | https://github.com/Voxelum/minecraft-launcher-core-node/pull/322 | Copilot | TypeScript | fix | 0.770 | 0.769 | 2.000 | Copilot / TypeScript: 1 initial files; 2 follow-up commits; 1 related issues |
| Temporal | Route low workload | https://github.com/crewAIInc/crewAI/pull/3221 | Devin | Python | fix | 0.770 | 0.769 | 3.000 | Devin / Python: 2 initial files; 171 initial churn; 1 initial test-like files; 1 follow-up commits; 2 issue comments |
| Temporal | Route low workload | https://github.com/microsoft/genaiscript/pull/1802 | Copilot | TypeScript | fix | 0.771 | 0.769 | 6.000 | Copilot / TypeScript: 1 initial files; 2 follow-up commits; 3 issue comments; 1 related issues |

### Temporal: Accept high workload

| split | case | html_url | agent | repo_language | feature_task_type | gate_score | score_threshold | outcome_downstream_workload_raw | case_summary |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Temporal | Accept high workload | https://github.com/justtrackio/gosoline/pull/1268 | Copilot | Go | feat | 0.691 | 0.769 | 115.000 | Copilot / Go: 1 initial files; 13 follow-up commits; 7 issue comments; 59 inline review comments; 1 related issues |
| Temporal | Accept high workload | https://github.com/nikolaydubina/go-instrument/pull/53 | Copilot | Go | fix | 0.635 | 0.769 | 100.000 | Copilot / Go: 1 initial files; 29 follow-up commits; 14 issue comments; 39 inline review comments; 1 related issues |
| Temporal | Accept high workload | https://github.com/dotnet/docs/pull/47428 | Copilot |  | docs | 0.748 | 0.769 | 97.000 | Copilot: 1 initial files; 8 follow-up commits; 5 issue comments; 53 inline review comments; 1 related issues |
| Temporal | Accept high workload | https://github.com/openai/codex/pull/1601 | OpenAI_Codex | Rust | refactor | 0.455 | 0.769 | 89.000 | OpenAI_Codex / Rust: 8 initial files; 157 initial churn; 3 initial test-like files; 29 follow-up commits; 37 inline review comments |
| Temporal | Accept high workload | https://github.com/onflow/flow-go/pull/7601 | Devin | Go | fix | 0.596 | 0.769 | 76.000 | Devin / Go: 4 initial files; 84 initial churn; 29 follow-up commits; 3 issue comments; 34 inline review comments |
| Temporal | Accept high workload | https://github.com/microsoft/typespec/pull/7984 | Copilot | Java | build | 0.685 | 0.769 | 71.000 | Copilot / Java: 1 initial files; 18 follow-up commits; 9 issue comments; 22 inline review comments; 1 related issues |

### Temporal: Accept low workload

| split | case | html_url | agent | repo_language | feature_task_type | gate_score | score_threshold | outcome_downstream_workload_raw | case_summary |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Temporal | Accept low workload | https://github.com/mochilang/mochi/pull/8859 | OpenAI_Codex | Go | test | 0.000 | 0.769 | 0.000 | OpenAI_Codex / Go: 300 initial files; 10780 initial churn; 298 initial test-like files |
| Temporal | Accept low workload | https://github.com/mochilang/mochi/pull/8839 | OpenAI_Codex | Go | test | 0.000 | 0.769 | 0.000 | OpenAI_Codex / Go: 300 initial files; 15142 initial churn; 300 initial test-like files |
| Temporal | Accept low workload | https://github.com/mochilang/mochi/pull/8825 | OpenAI_Codex | Go | test | 0.000 | 0.769 | 0.000 | OpenAI_Codex / Go: 300 initial files; 13250 initial churn; 300 initial test-like files |
| Temporal | Accept low workload | https://github.com/mochilang/mochi/pull/8840 | OpenAI_Codex | Go | test | 0.000 | 0.769 | 0.000 | OpenAI_Codex / Go: 300 initial files; 15145 initial churn; 300 initial test-like files |
| Temporal | Accept low workload | https://github.com/mochilang/mochi/pull/8821 | OpenAI_Codex | Go | test | 0.000 | 0.769 | 0.000 | OpenAI_Codex / Go: 300 initial files; 26412 initial churn; 300 initial test-like files |
| Temporal | Accept low workload | https://github.com/mochilang/mochi/pull/8886 | OpenAI_Codex | Go | feat | 0.000 | 0.769 | 0.000 | OpenAI_Codex / Go: 300 initial files; 23053 initial churn; 298 initial test-like files |

### Temporal: Route high workload

| split | case | html_url | agent | repo_language | feature_task_type | gate_score | score_threshold | outcome_downstream_workload_raw | case_summary |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Temporal | Route high workload | https://github.com/tphakala/birdnet-go/pull/981 | Claude_Code | Go | feat | 0.968 | 0.769 | 199.000 | Claude_Code / Go: 203 initial files; 47093 initial churn; 51 initial test-like files; 29 follow-up commits; 3 issue comments |
| Temporal | Route high workload | https://github.com/microsoft/Olive/pull/1996 | Copilot | Python | feat | 0.893 | 0.769 | 129.000 | Copilot / Python: 1 initial files; 29 follow-up commits; 10 issue comments; 67 inline review comments; 1 related issues |
| Temporal | Route high workload | https://github.com/microsoft/testfx/pull/6163 | Copilot | C# | feat | 0.884 | 0.769 | 117.000 | Copilot / C#: 22 follow-up commits; 17 issue comments; 48 inline review comments; 2 related issues |
| Temporal | Route high workload | https://github.com/NewFuture/DDNS/pull/528 | Copilot | Python | refactor | 0.802 | 0.769 | 99.000 | Copilot / Python: 1 initial files; 13 follow-up commits; 6 issue comments; 49 inline review comments; 1 related issues |
| Temporal | Route high workload | https://github.com/tphakala/birdnet-go/pull/1037 | Claude_Code | Go | feat | 0.787 | 0.769 | 96.000 | Claude_Code / Go: 5 initial files; 311 initial churn; 29 follow-up commits; 2 issue comments; 60 inline review comments |
| Temporal | Route high workload | https://github.com/microsoft/testfx/pull/6060 | Copilot | C# | perf | 0.834 | 0.769 | 95.000 | Copilot / C#: 1 initial files; 9 follow-up commits; 1 issue comments; 55 inline review comments; 1 related issues |
