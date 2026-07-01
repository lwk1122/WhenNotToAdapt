# AIDev Feature Boundary Ablation

This analysis checks whether the main gate depends on timing-sensitive pull-request API aggregate fields. The report-facing gate uses the defensible proposal-evidence set. The full feature set includes PR API aggregates whose exact snapshot timing is not established by the public AIDev schema, so it is diagnostic only.

| Split | Feature set | Features | AUC | AP | Accept | High if accepted | High-workload recall by routing |
|---|---|---:|---:|---:|---:|---:|---:|
| Unseen repository | Defensible proposal evidence | 18 | 0.764 | 0.541 | 0.313 | 0.079 | 0.926 |
| Unseen repository | First observed commit details only | 8 | 0.593 | 0.398 | 0.000 | 0.000 | 1.000 |
| Unseen repository | Full with timing-sensitive PR aggregates | 25 | 0.764 | 0.540 | 0.312 | 0.079 | 0.926 |
| Unseen repository | Text, repository, and task only | 10 | 0.762 | 0.540 | 0.305 | 0.079 | 0.927 |
| Temporal | Defensible proposal evidence | 18 | 0.900 | 0.493 | 0.842 | 0.074 | 0.559 |
| Temporal | First observed commit details only | 8 | 0.810 | 0.362 | 0.811 | 0.081 | 0.537 |
| Temporal | Full with timing-sensitive PR aggregates | 25 | 0.900 | 0.493 | 0.842 | 0.074 | 0.559 |
| Temporal | Text, repository, and task only | 10 | 0.897 | 0.492 | 0.843 | 0.075 | 0.552 |

## Claim Guidance

- Allowed: the main result is based on the defensible proposal-evidence set, not on timing-sensitive PR API aggregates.
- Allowed: the full feature set is an upper-bound diagnostic if those aggregate fields are available as initial snapshots in a deployment.
- Not allowed: using the full feature set as primary evidence without proving aggregate field timing.
