# LabCraft-Eval Evaluation Results

Automatically aggregated from Inspect AI `.eval` logs in [results/logs](../results/logs).

## Per-model per-task summary

Mean overall score across the seed samples run for each (model, task) cell. `n` is the number of samples in that cell.

| Model | Task | n | overall (mean±std) | task_success | decision_quality | troubleshooting | efficiency |
|---|---|---:|---:|---:|---:|---:|---:|
| anthropic/claude-haiku-4-5 | `clone_01` | 5 | 0.940 ± 0.022 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 0.400 ± 0.224 |
| anthropic/claude-haiku-4-5 | `growth_01` | 5 | 0.890 ± 0.246 | 0.800 ± 0.447 | 0.933 ± 0.149 | 1.000 ± 0.000 | 0.900 ± 0.224 |
| anthropic/claude-haiku-4-5 | `pcr_01` | 5 | 0.950 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 0.500 ± 0.000 |
| anthropic/claude-haiku-4-5 | `screen_01` | 5 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 |
| anthropic/claude-haiku-4-5 | `transform_01` | 5 | 0.500 ± 0.197 | 0.200 ± 0.447 | 0.700 ± 0.075 | 1.000 ± 0.000 | 0.100 ± 0.224 |
| anthropic/claude-sonnet-4-5 | `clone_01` | 5 | 0.950 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 0.500 ± 0.000 |
| anthropic/claude-sonnet-4-5 | `growth_01` | 5 | 0.880 ± 0.241 | 0.800 ± 0.447 | 0.933 ± 0.149 | 1.000 ± 0.000 | 0.800 ± 0.274 |
| anthropic/claude-sonnet-4-5 | `pcr_01` | 5 | 0.950 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 0.500 ± 0.000 |
| anthropic/claude-sonnet-4-5 | `screen_01` | 5 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 |
| anthropic/claude-sonnet-4-5 | `transform_01` | 5 | 0.480 ± 0.179 | 0.200 ± 0.447 | 0.667 ± 0.000 | 1.000 ± 0.000 | 0.000 ± 0.000 |
| openai/gpt-4o | `clone_01` | 5 | 0.904 ± 0.103 | 1.000 ± 0.000 | 0.980 ± 0.045 | 0.800 ± 0.447 | 0.500 ± 0.000 |
| openai/gpt-4o | `growth_01` | 5 | 0.580 ± 0.217 | 0.800 ± 0.447 | 0.533 ± 0.183 | 0.000 ± 0.000 | 1.000 ± 0.000 |
| openai/gpt-4o | `pcr_01` | 5 | 0.950 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 0.500 ± 0.000 |
| openai/gpt-4o | `screen_01` | 5 | 0.840 ± 0.219 | 0.600 ± 0.548 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 |
| openai/gpt-4o | `transform_01` | 5 | 0.440 ± 0.108 | 0.000 ± 0.000 | 0.700 ± 0.075 | 0.800 ± 0.447 | 0.700 ± 0.447 |
| openai/gpt-4o-mini | `clone_01` | 5 | 0.722 ± 0.397 | 0.800 ± 0.447 | 0.740 ± 0.305 | 0.600 ± 0.548 | 0.600 ± 0.548 |
| openai/gpt-4o-mini | `growth_01` | 5 | 0.560 ± 0.152 | 0.800 ± 0.447 | 0.467 ± 0.183 | 0.000 ± 0.000 | 1.000 ± 0.000 |
| openai/gpt-4o-mini | `pcr_01` | 5 | 0.970 ± 0.027 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 0.700 ± 0.274 |
| openai/gpt-4o-mini | `screen_01` | 5 | 0.900 ± 0.197 | 0.800 ± 0.447 | 1.000 ± 0.000 | 1.000 ± 0.000 | 0.800 ± 0.274 |
| openai/gpt-4o-mini | `transform_01` | 5 | 0.570 ± 0.045 | 0.000 ± 0.000 | 0.900 ± 0.149 | 1.000 ± 0.000 | 1.000 ± 0.000 |

## Per-sample detail

| Model | Task | Sample | overall | task | decision | trouble | efficiency |
|---|---|---|---:|---:|---:|---:|---:|
| anthropic/claude-haiku-4-5 | `clone_01` | `clone_01_seeded_seed_00` | 0.900 | 1.000 | 1.000 | 1.000 | 0.000 |
| anthropic/claude-haiku-4-5 | `clone_01` | `clone_01_seeded_seed_01` | 0.950 | 1.000 | 1.000 | 1.000 | 0.500 |
| anthropic/claude-haiku-4-5 | `clone_01` | `clone_01_seeded_seed_02` | 0.950 | 1.000 | 1.000 | 1.000 | 0.500 |
| anthropic/claude-haiku-4-5 | `clone_01` | `clone_01_seeded_seed_03` | 0.950 | 1.000 | 1.000 | 1.000 | 0.500 |
| anthropic/claude-haiku-4-5 | `clone_01` | `clone_01_seeded_seed_04` | 0.950 | 1.000 | 1.000 | 1.000 | 0.500 |
| anthropic/claude-haiku-4-5 | `growth_01` | `growth_01_seeded_seed_00` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| anthropic/claude-haiku-4-5 | `growth_01` | `growth_01_seeded_seed_01` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| anthropic/claude-haiku-4-5 | `growth_01` | `growth_01_seeded_seed_02` | 0.450 | 0.000 | 0.667 | 1.000 | 0.500 |
| anthropic/claude-haiku-4-5 | `growth_01` | `growth_01_seeded_seed_03` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| anthropic/claude-haiku-4-5 | `growth_01` | `growth_01_seeded_seed_04` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| anthropic/claude-haiku-4-5 | `pcr_01` | `pcr_01_seeded_seed_00` | 0.950 | 1.000 | 1.000 | 1.000 | 0.500 |
| anthropic/claude-haiku-4-5 | `pcr_01` | `pcr_01_seeded_seed_01` | 0.950 | 1.000 | 1.000 | 1.000 | 0.500 |
| anthropic/claude-haiku-4-5 | `pcr_01` | `pcr_01_seeded_seed_02` | 0.950 | 1.000 | 1.000 | 1.000 | 0.500 |
| anthropic/claude-haiku-4-5 | `pcr_01` | `pcr_01_seeded_seed_03` | 0.950 | 1.000 | 1.000 | 1.000 | 0.500 |
| anthropic/claude-haiku-4-5 | `pcr_01` | `pcr_01_seeded_seed_04` | 0.950 | 1.000 | 1.000 | 1.000 | 0.500 |
| anthropic/claude-haiku-4-5 | `screen_01` | `screen_01_seeded_seed_00` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| anthropic/claude-haiku-4-5 | `screen_01` | `screen_01_seeded_seed_01` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| anthropic/claude-haiku-4-5 | `screen_01` | `screen_01_seeded_seed_02` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| anthropic/claude-haiku-4-5 | `screen_01` | `screen_01_seeded_seed_03` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| anthropic/claude-haiku-4-5 | `screen_01` | `screen_01_seeded_seed_04` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| anthropic/claude-haiku-4-5 | `transform_01` | `transform_01_seeded_seed_00` | 0.400 | 0.000 | 0.667 | 1.000 | 0.000 |
| anthropic/claude-haiku-4-5 | `transform_01` | `transform_01_seeded_seed_01` | 0.400 | 0.000 | 0.667 | 1.000 | 0.000 |
| anthropic/claude-haiku-4-5 | `transform_01` | `transform_01_seeded_seed_02` | 0.850 | 1.000 | 0.833 | 1.000 | 0.000 |
| anthropic/claude-haiku-4-5 | `transform_01` | `transform_01_seeded_seed_03` | 0.400 | 0.000 | 0.667 | 1.000 | 0.000 |
| anthropic/claude-haiku-4-5 | `transform_01` | `transform_01_seeded_seed_04` | 0.450 | 0.000 | 0.667 | 1.000 | 0.500 |
| anthropic/claude-sonnet-4-5 | `clone_01` | `clone_01_seeded_seed_00` | 0.950 | 1.000 | 1.000 | 1.000 | 0.500 |
| anthropic/claude-sonnet-4-5 | `clone_01` | `clone_01_seeded_seed_01` | 0.950 | 1.000 | 1.000 | 1.000 | 0.500 |
| anthropic/claude-sonnet-4-5 | `clone_01` | `clone_01_seeded_seed_02` | 0.950 | 1.000 | 1.000 | 1.000 | 0.500 |
| anthropic/claude-sonnet-4-5 | `clone_01` | `clone_01_seeded_seed_03` | 0.950 | 1.000 | 1.000 | 1.000 | 0.500 |
| anthropic/claude-sonnet-4-5 | `clone_01` | `clone_01_seeded_seed_04` | 0.950 | 1.000 | 1.000 | 1.000 | 0.500 |
| anthropic/claude-sonnet-4-5 | `growth_01` | `growth_01_seeded_seed_00` | 0.450 | 0.000 | 0.667 | 1.000 | 0.500 |
| anthropic/claude-sonnet-4-5 | `growth_01` | `growth_01_seeded_seed_01` | 0.950 | 1.000 | 1.000 | 1.000 | 0.500 |
| anthropic/claude-sonnet-4-5 | `growth_01` | `growth_01_seeded_seed_02` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| anthropic/claude-sonnet-4-5 | `growth_01` | `growth_01_seeded_seed_03` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| anthropic/claude-sonnet-4-5 | `growth_01` | `growth_01_seeded_seed_04` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| anthropic/claude-sonnet-4-5 | `pcr_01` | `pcr_01_seeded_seed_00` | 0.950 | 1.000 | 1.000 | 1.000 | 0.500 |
| anthropic/claude-sonnet-4-5 | `pcr_01` | `pcr_01_seeded_seed_01` | 0.950 | 1.000 | 1.000 | 1.000 | 0.500 |
| anthropic/claude-sonnet-4-5 | `pcr_01` | `pcr_01_seeded_seed_02` | 0.950 | 1.000 | 1.000 | 1.000 | 0.500 |
| anthropic/claude-sonnet-4-5 | `pcr_01` | `pcr_01_seeded_seed_03` | 0.950 | 1.000 | 1.000 | 1.000 | 0.500 |
| anthropic/claude-sonnet-4-5 | `pcr_01` | `pcr_01_seeded_seed_04` | 0.950 | 1.000 | 1.000 | 1.000 | 0.500 |
| anthropic/claude-sonnet-4-5 | `screen_01` | `screen_01_seeded_seed_00` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| anthropic/claude-sonnet-4-5 | `screen_01` | `screen_01_seeded_seed_01` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| anthropic/claude-sonnet-4-5 | `screen_01` | `screen_01_seeded_seed_02` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| anthropic/claude-sonnet-4-5 | `screen_01` | `screen_01_seeded_seed_03` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| anthropic/claude-sonnet-4-5 | `screen_01` | `screen_01_seeded_seed_04` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| anthropic/claude-sonnet-4-5 | `transform_01` | `transform_01_seeded_seed_00` | 0.800 | 1.000 | 0.667 | 1.000 | 0.000 |
| anthropic/claude-sonnet-4-5 | `transform_01` | `transform_01_seeded_seed_01` | 0.400 | 0.000 | 0.667 | 1.000 | 0.000 |
| anthropic/claude-sonnet-4-5 | `transform_01` | `transform_01_seeded_seed_02` | 0.400 | 0.000 | 0.667 | 1.000 | 0.000 |
| anthropic/claude-sonnet-4-5 | `transform_01` | `transform_01_seeded_seed_03` | 0.400 | 0.000 | 0.667 | 1.000 | 0.000 |
| anthropic/claude-sonnet-4-5 | `transform_01` | `transform_01_seeded_seed_04` | 0.400 | 0.000 | 0.667 | 1.000 | 0.000 |
| openai/gpt-4o | `clone_01` | `clone_01_seeded_seed_00` | 0.950 | 1.000 | 1.000 | 1.000 | 0.500 |
| openai/gpt-4o | `clone_01` | `clone_01_seeded_seed_01` | 0.950 | 1.000 | 1.000 | 1.000 | 0.500 |
| openai/gpt-4o | `clone_01` | `clone_01_seeded_seed_02` | 0.950 | 1.000 | 1.000 | 1.000 | 0.500 |
| openai/gpt-4o | `clone_01` | `clone_01_seeded_seed_03` | 0.950 | 1.000 | 1.000 | 1.000 | 0.500 |
| openai/gpt-4o | `clone_01` | `clone_01_seeded_seed_04` | 0.720 | 1.000 | 0.900 | 0.000 | 0.500 |
| openai/gpt-4o | `growth_01` | `growth_01_seeded_seed_00` | 0.700 | 1.000 | 0.667 | 0.000 | 1.000 |
| openai/gpt-4o | `growth_01` | `growth_01_seeded_seed_01` | 0.600 | 1.000 | 0.333 | 0.000 | 1.000 |
| openai/gpt-4o | `growth_01` | `growth_01_seeded_seed_02` | 0.700 | 1.000 | 0.667 | 0.000 | 1.000 |
| openai/gpt-4o | `growth_01` | `growth_01_seeded_seed_03` | 0.200 | 0.000 | 0.333 | 0.000 | 1.000 |
| openai/gpt-4o | `growth_01` | `growth_01_seeded_seed_04` | 0.700 | 1.000 | 0.667 | 0.000 | 1.000 |
| openai/gpt-4o | `pcr_01` | `pcr_01_seeded_seed_00` | 0.950 | 1.000 | 1.000 | 1.000 | 0.500 |
| openai/gpt-4o | `pcr_01` | `pcr_01_seeded_seed_01` | 0.950 | 1.000 | 1.000 | 1.000 | 0.500 |
| openai/gpt-4o | `pcr_01` | `pcr_01_seeded_seed_02` | 0.950 | 1.000 | 1.000 | 1.000 | 0.500 |
| openai/gpt-4o | `pcr_01` | `pcr_01_seeded_seed_03` | 0.950 | 1.000 | 1.000 | 1.000 | 0.500 |
| openai/gpt-4o | `pcr_01` | `pcr_01_seeded_seed_04` | 0.950 | 1.000 | 1.000 | 1.000 | 0.500 |
| openai/gpt-4o | `screen_01` | `screen_01_seeded_seed_00` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| openai/gpt-4o | `screen_01` | `screen_01_seeded_seed_01` | 0.600 | 0.000 | 1.000 | 1.000 | 1.000 |
| openai/gpt-4o | `screen_01` | `screen_01_seeded_seed_02` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| openai/gpt-4o | `screen_01` | `screen_01_seeded_seed_03` | 0.600 | 0.000 | 1.000 | 1.000 | 1.000 |
| openai/gpt-4o | `screen_01` | `screen_01_seeded_seed_04` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| openai/gpt-4o | `transform_01` | `transform_01_seeded_seed_00` | 0.450 | 0.000 | 0.833 | 1.000 | 0.000 |
| openai/gpt-4o | `transform_01` | `transform_01_seeded_seed_01` | 0.500 | 0.000 | 0.667 | 1.000 | 1.000 |
| openai/gpt-4o | `transform_01` | `transform_01_seeded_seed_02` | 0.500 | 0.000 | 0.667 | 1.000 | 1.000 |
| openai/gpt-4o | `transform_01` | `transform_01_seeded_seed_03` | 0.500 | 0.000 | 0.667 | 1.000 | 1.000 |
| openai/gpt-4o | `transform_01` | `transform_01_seeded_seed_04` | 0.250 | 0.000 | 0.667 | 0.000 | 0.500 |
| openai/gpt-4o-mini | `clone_01` | `clone_01_seeded_seed_00` | 0.970 | 1.000 | 0.900 | 1.000 | 1.000 |
| openai/gpt-4o-mini | `clone_01` | `clone_01_seeded_seed_01` | 0.640 | 1.000 | 0.800 | 0.000 | 0.000 |
| openai/gpt-4o-mini | `clone_01` | `clone_01_seeded_seed_02` | 0.970 | 1.000 | 0.900 | 1.000 | 1.000 |
| openai/gpt-4o-mini | `clone_01` | `clone_01_seeded_seed_03` | 0.970 | 1.000 | 0.900 | 1.000 | 1.000 |
| openai/gpt-4o-mini | `clone_01` | `clone_01_seeded_seed_04` | 0.060 | 0.000 | 0.200 | 0.000 | 0.000 |
| openai/gpt-4o-mini | `growth_01` | `growth_01_seeded_seed_00` | 0.600 | 1.000 | 0.333 | 0.000 | 1.000 |
| openai/gpt-4o-mini | `growth_01` | `growth_01_seeded_seed_01` | 0.600 | 1.000 | 0.333 | 0.000 | 1.000 |
| openai/gpt-4o-mini | `growth_01` | `growth_01_seeded_seed_02` | 0.300 | 0.000 | 0.667 | 0.000 | 1.000 |
| openai/gpt-4o-mini | `growth_01` | `growth_01_seeded_seed_03` | 0.700 | 1.000 | 0.667 | 0.000 | 1.000 |
| openai/gpt-4o-mini | `growth_01` | `growth_01_seeded_seed_04` | 0.600 | 1.000 | 0.333 | 0.000 | 1.000 |
| openai/gpt-4o-mini | `pcr_01` | `pcr_01_seeded_seed_00` | 0.950 | 1.000 | 1.000 | 1.000 | 0.500 |
| openai/gpt-4o-mini | `pcr_01` | `pcr_01_seeded_seed_01` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| openai/gpt-4o-mini | `pcr_01` | `pcr_01_seeded_seed_02` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| openai/gpt-4o-mini | `pcr_01` | `pcr_01_seeded_seed_03` | 0.950 | 1.000 | 1.000 | 1.000 | 0.500 |
| openai/gpt-4o-mini | `pcr_01` | `pcr_01_seeded_seed_04` | 0.950 | 1.000 | 1.000 | 1.000 | 0.500 |
| openai/gpt-4o-mini | `screen_01` | `screen_01_seeded_seed_00` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| openai/gpt-4o-mini | `screen_01` | `screen_01_seeded_seed_01` | 0.550 | 0.000 | 1.000 | 1.000 | 0.500 |
| openai/gpt-4o-mini | `screen_01` | `screen_01_seeded_seed_02` | 0.950 | 1.000 | 1.000 | 1.000 | 0.500 |
| openai/gpt-4o-mini | `screen_01` | `screen_01_seeded_seed_03` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| openai/gpt-4o-mini | `screen_01` | `screen_01_seeded_seed_04` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| openai/gpt-4o-mini | `transform_01` | `transform_01_seeded_seed_00` | 0.600 | 0.000 | 1.000 | 1.000 | 1.000 |
| openai/gpt-4o-mini | `transform_01` | `transform_01_seeded_seed_01` | 0.600 | 0.000 | 1.000 | 1.000 | 1.000 |
| openai/gpt-4o-mini | `transform_01` | `transform_01_seeded_seed_02` | 0.500 | 0.000 | 0.667 | 1.000 | 1.000 |
| openai/gpt-4o-mini | `transform_01` | `transform_01_seeded_seed_03` | 0.550 | 0.000 | 0.833 | 1.000 | 1.000 |
| openai/gpt-4o-mini | `transform_01` | `transform_01_seeded_seed_04` | 0.600 | 0.000 | 1.000 | 1.000 | 1.000 |
