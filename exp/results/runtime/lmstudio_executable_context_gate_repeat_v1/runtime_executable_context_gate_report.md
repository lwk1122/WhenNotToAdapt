# LM Studio Executable Context-Gate Pilot

The model chooses among static candidate replacement implementations. The selected implementation is executed against local Python tests.

- Model: `qwen/qwen3.5-9b`
- Tasks: 30
- Result CSV: `exp/results/emse_runtime/lmstudio_executable_context_gate_repeat_v1/runtime_task_results.csv`
- Call log: `exp/results/emse_runtime/lmstudio_executable_context_gate_repeat_v1/runtime_call_log.jsonl`

| controller | n | success_rate | mean_calls | mean_total_tokens | mean_latency_s |
|---|---:|---:|---:|---:|---:|
| context_gate_high_only | 30 | 0.900 | 1.87 | 802.7 | 11.54 |
| context_gate_medium_high | 30 | 0.967 | 2.40 | 1067.6 | 14.54 |
| direct_low | 30 | 0.833 | 1.00 | 330.5 | 5.56 |
| standard_full | 30 | 0.967 | 3.00 | 1364.4 | 17.91 |
