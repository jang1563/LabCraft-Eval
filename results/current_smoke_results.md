# LabCraft-Eval Evaluation Results

Automatically aggregated from Inspect AI `.eval` logs in [results/current_smoke_logs](../results/current_smoke_logs).

## Per-model per-task summary

Mean overall score across the seed samples run for each (model, task) cell. `n` is the number of samples in that cell.

| Model | Task | n | overall (mean±std) | task_success | decision_quality | troubleshooting | efficiency |
|---|---|---:|---:|---:|---:|---:|---:|
| openai/gpt-4o-mini | `express_01` | 1 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 |
| openai/gpt-4o-mini | `gibson_01` | 1 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 |
| openai/gpt-4o-mini | `golden_gate_01` | 1 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 |
| openai/gpt-4o-mini | `miniprep_01` | 1 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 |
| openai/gpt-4o-mini | `purify_01` | 1 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 |

## Per-sample detail

| Model | Task | Sample | overall | task | decision | trouble | efficiency |
|---|---|---|---:|---:|---:|---:|---:|
| openai/gpt-4o-mini | `golden_gate_01` | `golden_gate_01_seeded` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| openai/gpt-4o-mini | `gibson_01` | `gibson_01_seeded` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| openai/gpt-4o-mini | `miniprep_01` | `miniprep_01_seeded` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| openai/gpt-4o-mini | `express_01` | `express_01_seeded` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| openai/gpt-4o-mini | `purify_01` | `purify_01_seeded` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
