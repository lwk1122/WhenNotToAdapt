# LM Studio Executable Context-Gate Pilot

The model chooses among static candidate replacement implementations. The selected implementation is executed against local Python tests.

- Model: `Qwen3-4B-Q4_K_M.gguf`
- Tasks: 4
- Result CSV: `paper/ReplicationPackage/exp/results/emse_runtime/llamaserver_qwen3_4b_smoke_v1/runtime_task_results.csv`
- Call log: `paper/ReplicationPackage/exp/results/emse_runtime/llamaserver_qwen3_4b_smoke_v1/runtime_call_log.jsonl`

| controller | n | success_rate | mean_calls | mean_total_tokens | mean_latency_s |
|---|---:|---:|---:|---:|---:|
| context_gate_high_only | 4 | 0.000 | 1.00 | 487.2 | 9.60 |
| context_gate_medium_high | 4 | 0.000 | 1.00 | 487.2 | 9.60 |
| direct_low | 4 | 0.000 | 1.00 | 487.2 | 9.60 |
| standard_full | 4 | 0.000 | 3.00 | 1928.0 | 39.95 |
