# LabCraft-Eval Evaluation Results

Automatically aggregated from Inspect AI `.eval` logs in [results/followup_smoke_logs](../results/followup_smoke_logs).

## Per-model per-task summary

Mean overall score across the seed samples run for each (model, task) cell. `n` is the number of samples in that cell.

| Model | Task | n | overall (mean±std) | task_success | decision_quality | troubleshooting | efficiency |
|---|---|---:|---:|---:|---:|---:|---:|
| openai/gpt-4o-mini | `followup_01` | 1 | 0.475 ± 0.000 | 0.000 ± 0.000 | 0.750 ± 0.000 | 1.000 ± 0.000 | 0.500 ± 0.000 |

## Per-sample detail

| Model | Task | Sample | overall | task | decision | trouble | efficiency |
|---|---|---|---:|---:|---:|---:|---:|
| openai/gpt-4o-mini | `followup_01` | `followup_01_seeded` | 0.475 | 0.000 | 0.750 | 1.000 | 0.500 |
