# LabCraft-Eval Evaluation Results

Automatically aggregated from Inspect AI `.eval` logs in [results/followup_logs](../results/followup_logs).

## Per-model per-task summary

Mean overall score across the seed samples run for each (model, task) cell. `n` is the number of samples in that cell.

| Model | Task | n | overall (mean±std) | task_success | decision_quality | troubleshooting | efficiency |
|---|---|---:|---:|---:|---:|---:|---:|
| anthropic/claude-sonnet-4-5 | `followup_01` | 3 | 0.933 ± 0.029 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 0.333 ± 0.289 |
| openai/gpt-4o-mini | `followup_01` | 3 | 0.633 ± 0.227 | 0.667 ± 0.577 | 0.667 ± 0.144 | 0.667 ± 0.577 | 0.333 ± 0.289 |

## Per-sample detail

| Model | Task | Sample | overall | task | decision | trouble | efficiency |
|---|---|---|---:|---:|---:|---:|---:|
| anthropic/claude-sonnet-4-5 | `followup_01` | `followup_01_seeded_seed_00` | 0.900 | 1.000 | 1.000 | 1.000 | 0.000 |
| anthropic/claude-sonnet-4-5 | `followup_01` | `followup_01_seeded_seed_01` | 0.950 | 1.000 | 1.000 | 1.000 | 0.500 |
| anthropic/claude-sonnet-4-5 | `followup_01` | `followup_01_seeded_seed_02` | 0.950 | 1.000 | 1.000 | 1.000 | 0.500 |
| openai/gpt-4o-mini | `followup_01` | `followup_01_seeded_seed_00` | 0.425 | 0.000 | 0.750 | 1.000 | 0.000 |
| openai/gpt-4o-mini | `followup_01` | `followup_01_seeded_seed_01` | 0.875 | 1.000 | 0.750 | 1.000 | 0.500 |
| openai/gpt-4o-mini | `followup_01` | `followup_01_seeded_seed_02` | 0.600 | 1.000 | 0.500 | 0.000 | 0.500 |
