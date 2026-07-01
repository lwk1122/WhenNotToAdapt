# LM Studio Executable Context-Gate Pilot

The model chooses among static candidate replacement implementations. The selected implementation is executed against local Python tests.

- Model: `Qwen3-4B-Q4_K_M.gguf`
- Tasks: 30
- Result CSV: `paper/ReplicationPackage/exp/results/emse_runtime/llamaserver_qwen3_4b_nothink_30_v1/runtime_task_results.csv`
- Call log: `paper/ReplicationPackage/exp/results/emse_runtime/llamaserver_qwen3_4b_nothink_30_v1/runtime_call_log.jsonl`

| controller | n | success_rate | mean_calls | mean_total_tokens | mean_latency_s |
|---|---:|---:|---:|---:|---:|
| context_gate_high_only | 30 | 0.833 | 1.87 | 578.6 | 4.53 |
| context_gate_medium_high | 30 | 0.800 | 2.40 | 759.4 | 5.67 |
| direct_low | 30 | 0.833 | 1.00 | 275.4 | 2.96 |
| standard_full | 30 | 0.833 | 3.00 | 960.1 | 6.80 |
