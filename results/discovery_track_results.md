# LabCraft-Eval Evaluation Results

Automatically aggregated from Inspect AI `.eval` logs in [results/discovery_logs](../results/discovery_logs).

## Per-model per-task summary

Mean overall score across the seed samples run for each (model, task) cell. `n` is the number of samples in that cell.

| Model | Task | n | overall (mean±std) | task_success | decision_quality | troubleshooting | efficiency |
|---|---|---:|---:|---:|---:|---:|---:|
| anthropic/claude-sonnet-4-5 | `perturb_followup_01` | 3 | 0.933 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 0.667 ± 0.000 | 1.000 ± 0.000 |
| anthropic/claude-sonnet-4-5 | `target_prioritize_01` | 3 | 0.425 ± 0.000 | 0.000 ± 0.000 | 0.750 ± 0.000 | 0.500 ± 0.000 | 1.000 ± 0.000 |
| anthropic/claude-sonnet-4-5 | `target_validate_01` | 3 | 0.933 ± 0.067 | 1.000 ± 0.000 | 1.000 ± 0.000 | 0.667 ± 0.333 | 1.000 ± 0.000 |
| openai/gpt-4o-mini | `perturb_followup_01` | 3 | 0.814 ± 0.038 | 1.000 ± 0.000 | 0.750 ± 0.000 | 0.444 ± 0.192 | 1.000 ± 0.000 |
| openai/gpt-4o-mini | `target_prioritize_01` | 3 | 0.375 ± 0.043 | 0.000 ± 0.000 | 0.917 ± 0.144 | 0.000 ± 0.000 | 1.000 ± 0.000 |
| openai/gpt-4o-mini | `target_validate_01` | 3 | 0.867 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 0.333 ± 0.000 | 1.000 ± 0.000 |

## Per-sample detail

| Model | Task | Sample | overall | task | decision | trouble | efficiency |
|---|---|---|---:|---:|---:|---:|---:|
| anthropic/claude-sonnet-4-5 | `perturb_followup_01` | `perturb_followup_01_seeded_seed_00` | 0.933 | 1.000 | 1.000 | 0.667 | 1.000 |
| anthropic/claude-sonnet-4-5 | `perturb_followup_01` | `perturb_followup_01_seeded_seed_01` | 0.933 | 1.000 | 1.000 | 0.667 | 1.000 |
| anthropic/claude-sonnet-4-5 | `perturb_followup_01` | `perturb_followup_01_seeded_seed_02` | 0.933 | 1.000 | 1.000 | 0.667 | 1.000 |
| anthropic/claude-sonnet-4-5 | `target_prioritize_01` | `target_prioritize_01_seeded_seed_00` | 0.425 | 0.000 | 0.750 | 0.500 | 1.000 |
| anthropic/claude-sonnet-4-5 | `target_prioritize_01` | `target_prioritize_01_seeded_seed_01` | 0.425 | 0.000 | 0.750 | 0.500 | 1.000 |
| anthropic/claude-sonnet-4-5 | `target_prioritize_01` | `target_prioritize_01_seeded_seed_02` | 0.425 | 0.000 | 0.750 | 0.500 | 1.000 |
| anthropic/claude-sonnet-4-5 | `target_validate_01` | `target_validate_01_seeded_seed_00` | 0.867 | 1.000 | 1.000 | 0.333 | 1.000 |
| anthropic/claude-sonnet-4-5 | `target_validate_01` | `target_validate_01_seeded_seed_01` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| anthropic/claude-sonnet-4-5 | `target_validate_01` | `target_validate_01_seeded_seed_02` | 0.933 | 1.000 | 1.000 | 0.667 | 1.000 |
| openai/gpt-4o-mini | `perturb_followup_01` | `perturb_followup_01_seeded_seed_00` | 0.858 | 1.000 | 0.750 | 0.667 | 1.000 |
| openai/gpt-4o-mini | `perturb_followup_01` | `perturb_followup_01_seeded_seed_01` | 0.792 | 1.000 | 0.750 | 0.333 | 1.000 |
| openai/gpt-4o-mini | `perturb_followup_01` | `perturb_followup_01_seeded_seed_02` | 0.792 | 1.000 | 0.750 | 0.333 | 1.000 |
| openai/gpt-4o-mini | `target_prioritize_01` | `target_prioritize_01_seeded_seed_00` | 0.325 | 0.000 | 0.750 | 0.000 | 1.000 |
| openai/gpt-4o-mini | `target_prioritize_01` | `target_prioritize_01_seeded_seed_01` | 0.400 | 0.000 | 1.000 | 0.000 | 1.000 |
| openai/gpt-4o-mini | `target_prioritize_01` | `target_prioritize_01_seeded_seed_02` | 0.400 | 0.000 | 1.000 | 0.000 | 1.000 |
| openai/gpt-4o-mini | `target_validate_01` | `target_validate_01_seeded_seed_00` | 0.867 | 1.000 | 1.000 | 0.333 | 1.000 |
| openai/gpt-4o-mini | `target_validate_01` | `target_validate_01_seeded_seed_01` | 0.867 | 1.000 | 1.000 | 0.333 | 1.000 |
| openai/gpt-4o-mini | `target_validate_01` | `target_validate_01_seeded_seed_02` | 0.867 | 1.000 | 1.000 | 0.333 | 1.000 |
