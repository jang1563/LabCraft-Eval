# LabCraft-Eval Evaluation Results

Automatically aggregated from Inspect AI `.eval` logs in [results/logs_ablation_growth_verbose](../results/logs_ablation_growth_verbose).

## Per-model per-task summary

Mean overall score across the seed samples run for each (model, task) cell. `n` is the number of samples in that cell.

| Model | Task | n | overall (mean±std) | task_success | decision_quality | troubleshooting | efficiency |
|---|---|---:|---:|---:|---:|---:|---:|
| openai/gpt-4o | `growth_01` | 5 | 0.560 ± 0.152 | 0.400 ± 0.548 | 0.600 ± 0.279 | 0.600 ± 0.548 | 1.000 ± 0.000 |
| openai/gpt-4o-mini | `growth_01` | 5 | 0.580 ± 0.239 | 0.200 ± 0.447 | 0.667 ± 0.236 | 1.000 ± 0.000 | 1.000 ± 0.000 |

## Per-sample detail

| Model | Task | Sample | overall | task | decision | trouble | efficiency |
|---|---|---|---:|---:|---:|---:|---:|
| openai/gpt-4o-mini | `growth_01` | `growth_01_seeded_seed_00` | 0.500 | 0.000 | 0.667 | 1.000 | 1.000 |
| openai/gpt-4o-mini | `growth_01` | `growth_01_seeded_seed_01` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| openai/gpt-4o-mini | `growth_01` | `growth_01_seeded_seed_02` | 0.500 | 0.000 | 0.667 | 1.000 | 1.000 |
| openai/gpt-4o-mini | `growth_01` | `growth_01_seeded_seed_03` | 0.500 | 0.000 | 0.667 | 1.000 | 1.000 |
| openai/gpt-4o-mini | `growth_01` | `growth_01_seeded_seed_04` | 0.400 | 0.000 | 0.333 | 1.000 | 1.000 |
| openai/gpt-4o | `growth_01` | `growth_01_seeded_seed_00` | 0.700 | 1.000 | 0.667 | 0.000 | 1.000 |
| openai/gpt-4o | `growth_01` | `growth_01_seeded_seed_01` | 0.700 | 1.000 | 0.667 | 0.000 | 1.000 |
| openai/gpt-4o | `growth_01` | `growth_01_seeded_seed_02` | 0.400 | 0.000 | 0.333 | 1.000 | 1.000 |
| openai/gpt-4o | `growth_01` | `growth_01_seeded_seed_03` | 0.600 | 0.000 | 1.000 | 1.000 | 1.000 |
| openai/gpt-4o | `growth_01` | `growth_01_seeded_seed_04` | 0.400 | 0.000 | 0.333 | 1.000 | 1.000 |
