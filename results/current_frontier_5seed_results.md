# LabCraft-Eval Evaluation Results

Automatically aggregated from Inspect AI `.eval` logs in [results/current_openai_logs](../results/current_openai_logs), [results/current_anthropic_logs](../results/current_anthropic_logs), [results/current_openai_logs_seed34](../results/current_openai_logs_seed34), [results/current_anthropic_logs_seed34](../results/current_anthropic_logs_seed34).

Repeated reruns with the same `(model, task, sample_id)` are deduplicated by keeping the latest `.eval` archive. 12 duplicate sample rows were ignored.

## Per-model per-task summary

Mean overall score across the seed samples run for each (model, task) cell. `n` is the number of samples in that cell.

| Model | Task | n | overall (mean±std) | task_success | decision_quality | troubleshooting | efficiency |
|---|---|---:|---:|---:|---:|---:|---:|
| anthropic/claude-haiku-4-5 | `express_01` | 5 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 |
| anthropic/claude-haiku-4-5 | `gibson_01` | 5 | 0.970 ± 0.045 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 0.700 ± 0.447 |
| anthropic/claude-haiku-4-5 | `golden_gate_01` | 5 | 0.910 ± 0.175 | 0.800 ± 0.447 | 1.000 ± 0.000 | 1.000 ± 0.000 | 0.900 ± 0.224 |
| anthropic/claude-haiku-4-5 | `miniprep_01` | 5 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 |
| anthropic/claude-haiku-4-5 | `purify_01` | 5 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 |
| anthropic/claude-sonnet-4-5 | `express_01` | 5 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 |
| anthropic/claude-sonnet-4-5 | `gibson_01` | 5 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 |
| anthropic/claude-sonnet-4-5 | `golden_gate_01` | 5 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 |
| anthropic/claude-sonnet-4-5 | `miniprep_01` | 5 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 |
| anthropic/claude-sonnet-4-5 | `purify_01` | 5 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 |
| openai/gpt-4o | `express_01` | 5 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 |
| openai/gpt-4o | `gibson_01` | 5 | 0.980 ± 0.027 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 0.800 ± 0.274 |
| openai/gpt-4o | `golden_gate_01` | 5 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 |
| openai/gpt-4o | `miniprep_01` | 5 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 |
| openai/gpt-4o | `purify_01` | 5 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 |
| openai/gpt-4o-mini | `express_01` | 5 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 |
| openai/gpt-4o-mini | `gibson_01` | 5 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 |
| openai/gpt-4o-mini | `golden_gate_01` | 5 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 |
| openai/gpt-4o-mini | `miniprep_01` | 5 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 |
| openai/gpt-4o-mini | `purify_01` | 5 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 |

## Per-sample detail

| Model | Task | Sample | overall | task | decision | trouble | efficiency |
|---|---|---|---:|---:|---:|---:|---:|
| anthropic/claude-haiku-4-5 | `express_01` | `express_01_seeded_seed_00` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| anthropic/claude-haiku-4-5 | `express_01` | `express_01_seeded_seed_01` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| anthropic/claude-haiku-4-5 | `express_01` | `express_01_seeded_seed_02` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| anthropic/claude-haiku-4-5 | `express_01` | `express_01_seeded_seed_03` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| anthropic/claude-haiku-4-5 | `express_01` | `express_01_seeded_seed_04` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| anthropic/claude-haiku-4-5 | `gibson_01` | `gibson_01_seeded_seed_00` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| anthropic/claude-haiku-4-5 | `gibson_01` | `gibson_01_seeded_seed_01` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| anthropic/claude-haiku-4-5 | `gibson_01` | `gibson_01_seeded_seed_02` | 0.950 | 1.000 | 1.000 | 1.000 | 0.500 |
| anthropic/claude-haiku-4-5 | `gibson_01` | `gibson_01_seeded_seed_03` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| anthropic/claude-haiku-4-5 | `gibson_01` | `gibson_01_seeded_seed_04` | 0.900 | 1.000 | 1.000 | 1.000 | 0.000 |
| anthropic/claude-haiku-4-5 | `golden_gate_01` | `golden_gate_01_seeded_seed_00` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| anthropic/claude-haiku-4-5 | `golden_gate_01` | `golden_gate_01_seeded_seed_01` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| anthropic/claude-haiku-4-5 | `golden_gate_01` | `golden_gate_01_seeded_seed_02` | 0.950 | 1.000 | 1.000 | 1.000 | 0.500 |
| anthropic/claude-haiku-4-5 | `golden_gate_01` | `golden_gate_01_seeded_seed_03` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| anthropic/claude-haiku-4-5 | `golden_gate_01` | `golden_gate_01_seeded_seed_04` | 0.600 | 0.000 | 1.000 | 1.000 | 1.000 |
| anthropic/claude-haiku-4-5 | `miniprep_01` | `miniprep_01_seeded_seed_00` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| anthropic/claude-haiku-4-5 | `miniprep_01` | `miniprep_01_seeded_seed_01` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| anthropic/claude-haiku-4-5 | `miniprep_01` | `miniprep_01_seeded_seed_02` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| anthropic/claude-haiku-4-5 | `miniprep_01` | `miniprep_01_seeded_seed_03` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| anthropic/claude-haiku-4-5 | `miniprep_01` | `miniprep_01_seeded_seed_04` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| anthropic/claude-haiku-4-5 | `purify_01` | `purify_01_seeded_seed_00` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| anthropic/claude-haiku-4-5 | `purify_01` | `purify_01_seeded_seed_01` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| anthropic/claude-haiku-4-5 | `purify_01` | `purify_01_seeded_seed_02` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| anthropic/claude-haiku-4-5 | `purify_01` | `purify_01_seeded_seed_03` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| anthropic/claude-haiku-4-5 | `purify_01` | `purify_01_seeded_seed_04` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| anthropic/claude-sonnet-4-5 | `express_01` | `express_01_seeded_seed_00` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| anthropic/claude-sonnet-4-5 | `express_01` | `express_01_seeded_seed_01` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| anthropic/claude-sonnet-4-5 | `express_01` | `express_01_seeded_seed_02` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| anthropic/claude-sonnet-4-5 | `express_01` | `express_01_seeded_seed_03` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| anthropic/claude-sonnet-4-5 | `express_01` | `express_01_seeded_seed_04` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| anthropic/claude-sonnet-4-5 | `gibson_01` | `gibson_01_seeded_seed_00` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| anthropic/claude-sonnet-4-5 | `gibson_01` | `gibson_01_seeded_seed_01` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| anthropic/claude-sonnet-4-5 | `gibson_01` | `gibson_01_seeded_seed_02` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| anthropic/claude-sonnet-4-5 | `gibson_01` | `gibson_01_seeded_seed_03` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| anthropic/claude-sonnet-4-5 | `gibson_01` | `gibson_01_seeded_seed_04` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| anthropic/claude-sonnet-4-5 | `golden_gate_01` | `golden_gate_01_seeded_seed_00` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| anthropic/claude-sonnet-4-5 | `golden_gate_01` | `golden_gate_01_seeded_seed_01` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| anthropic/claude-sonnet-4-5 | `golden_gate_01` | `golden_gate_01_seeded_seed_02` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| anthropic/claude-sonnet-4-5 | `golden_gate_01` | `golden_gate_01_seeded_seed_03` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| anthropic/claude-sonnet-4-5 | `golden_gate_01` | `golden_gate_01_seeded_seed_04` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| anthropic/claude-sonnet-4-5 | `miniprep_01` | `miniprep_01_seeded_seed_00` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| anthropic/claude-sonnet-4-5 | `miniprep_01` | `miniprep_01_seeded_seed_01` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| anthropic/claude-sonnet-4-5 | `miniprep_01` | `miniprep_01_seeded_seed_02` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| anthropic/claude-sonnet-4-5 | `miniprep_01` | `miniprep_01_seeded_seed_03` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| anthropic/claude-sonnet-4-5 | `miniprep_01` | `miniprep_01_seeded_seed_04` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| anthropic/claude-sonnet-4-5 | `purify_01` | `purify_01_seeded_seed_00` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| anthropic/claude-sonnet-4-5 | `purify_01` | `purify_01_seeded_seed_01` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| anthropic/claude-sonnet-4-5 | `purify_01` | `purify_01_seeded_seed_02` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| anthropic/claude-sonnet-4-5 | `purify_01` | `purify_01_seeded_seed_03` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| anthropic/claude-sonnet-4-5 | `purify_01` | `purify_01_seeded_seed_04` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| openai/gpt-4o | `express_01` | `express_01_seeded_seed_00` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| openai/gpt-4o | `express_01` | `express_01_seeded_seed_01` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| openai/gpt-4o | `express_01` | `express_01_seeded_seed_02` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| openai/gpt-4o | `express_01` | `express_01_seeded_seed_03` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| openai/gpt-4o | `express_01` | `express_01_seeded_seed_04` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| openai/gpt-4o | `gibson_01` | `gibson_01_seeded_seed_00` | 0.950 | 1.000 | 1.000 | 1.000 | 0.500 |
| openai/gpt-4o | `gibson_01` | `gibson_01_seeded_seed_01` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| openai/gpt-4o | `gibson_01` | `gibson_01_seeded_seed_02` | 0.950 | 1.000 | 1.000 | 1.000 | 0.500 |
| openai/gpt-4o | `gibson_01` | `gibson_01_seeded_seed_03` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| openai/gpt-4o | `gibson_01` | `gibson_01_seeded_seed_04` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| openai/gpt-4o | `golden_gate_01` | `golden_gate_01_seeded_seed_00` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| openai/gpt-4o | `golden_gate_01` | `golden_gate_01_seeded_seed_01` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| openai/gpt-4o | `golden_gate_01` | `golden_gate_01_seeded_seed_02` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| openai/gpt-4o | `golden_gate_01` | `golden_gate_01_seeded_seed_03` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| openai/gpt-4o | `golden_gate_01` | `golden_gate_01_seeded_seed_04` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| openai/gpt-4o | `miniprep_01` | `miniprep_01_seeded_seed_00` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| openai/gpt-4o | `miniprep_01` | `miniprep_01_seeded_seed_01` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| openai/gpt-4o | `miniprep_01` | `miniprep_01_seeded_seed_02` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| openai/gpt-4o | `miniprep_01` | `miniprep_01_seeded_seed_03` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| openai/gpt-4o | `miniprep_01` | `miniprep_01_seeded_seed_04` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| openai/gpt-4o | `purify_01` | `purify_01_seeded_seed_00` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| openai/gpt-4o | `purify_01` | `purify_01_seeded_seed_01` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| openai/gpt-4o | `purify_01` | `purify_01_seeded_seed_02` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| openai/gpt-4o | `purify_01` | `purify_01_seeded_seed_03` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| openai/gpt-4o | `purify_01` | `purify_01_seeded_seed_04` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| openai/gpt-4o-mini | `express_01` | `express_01_seeded_seed_00` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| openai/gpt-4o-mini | `express_01` | `express_01_seeded_seed_01` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| openai/gpt-4o-mini | `express_01` | `express_01_seeded_seed_02` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| openai/gpt-4o-mini | `express_01` | `express_01_seeded_seed_03` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| openai/gpt-4o-mini | `express_01` | `express_01_seeded_seed_04` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| openai/gpt-4o-mini | `gibson_01` | `gibson_01_seeded_seed_00` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| openai/gpt-4o-mini | `gibson_01` | `gibson_01_seeded_seed_01` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| openai/gpt-4o-mini | `gibson_01` | `gibson_01_seeded_seed_02` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| openai/gpt-4o-mini | `gibson_01` | `gibson_01_seeded_seed_03` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| openai/gpt-4o-mini | `gibson_01` | `gibson_01_seeded_seed_04` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| openai/gpt-4o-mini | `golden_gate_01` | `golden_gate_01_seeded_seed_00` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| openai/gpt-4o-mini | `golden_gate_01` | `golden_gate_01_seeded_seed_01` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| openai/gpt-4o-mini | `golden_gate_01` | `golden_gate_01_seeded_seed_02` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| openai/gpt-4o-mini | `golden_gate_01` | `golden_gate_01_seeded_seed_03` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| openai/gpt-4o-mini | `golden_gate_01` | `golden_gate_01_seeded_seed_04` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| openai/gpt-4o-mini | `miniprep_01` | `miniprep_01_seeded_seed_00` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| openai/gpt-4o-mini | `miniprep_01` | `miniprep_01_seeded_seed_01` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| openai/gpt-4o-mini | `miniprep_01` | `miniprep_01_seeded_seed_02` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| openai/gpt-4o-mini | `miniprep_01` | `miniprep_01_seeded_seed_03` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| openai/gpt-4o-mini | `miniprep_01` | `miniprep_01_seeded_seed_04` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| openai/gpt-4o-mini | `purify_01` | `purify_01_seeded_seed_00` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| openai/gpt-4o-mini | `purify_01` | `purify_01_seeded_seed_01` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| openai/gpt-4o-mini | `purify_01` | `purify_01_seeded_seed_02` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| openai/gpt-4o-mini | `purify_01` | `purify_01_seeded_seed_03` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| openai/gpt-4o-mini | `purify_01` | `purify_01_seeded_seed_04` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
