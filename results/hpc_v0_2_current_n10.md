# HPC v0.2 Current-Task Candidate (N=10)

This page promotes the completed HPC current-task bundle into a tracked,
reviewer-readable summary while keeping the frozen April 2026 scorecard
untouched.

The raw `.eval` archives remain under ignored local artifact directories in
`results/hpc/`. Do not treat this page as replacing [results.md](results.md);
it is a v0.2 candidate slice for the current implemented task surface.

> **Historical/pre-remediation artifact:** the source commits predate removal
> of answer-bearing agent guidance, explicit integer seed propagation, and the
> stricter report scorer. The raw logs are not public. This table is therefore
> not a leakage-free current-task result or a validated provider comparison.

## Configuration

- Candidate bundle: `2026_05_v0_2_current_n10_completed`
- Source bundles:
  - `2026_05_v0_2_current_n10`
  - `2026_05_v0_2_current_openai_missing_n10`
- Aggregation commit: `177dbc8`
- Rows: 440 deduplicated scored samples
- Tasks: `transform_01`, `growth_01`, `pcr_01`, `screen_01`, `clone_01`,
  `golden_gate_01`, `gibson_01`, `miniprep_01`, `express_01`, `purify_01`,
  `followup_01`
- Models: `openai/gpt-4o-mini`, `openai/gpt-4o`,
  `anthropic/claude-haiku-4-5`, `anthropic/claude-sonnet-4-5`
- Stored seed-labelled repetitions: 10 per `(model, task)` cell

The original current bundle was partial because OpenAI quota blocked the newer
current-task cells. The fill-in bundle completed those missing OpenAI cells on
2026-05-18, and the completed bundle was then aggregated across both log
directories.

## Headline

Mean overall score across the 11 current tasks:

| Model | Mean overall |
|---|---:|
| `anthropic/claude-sonnet-4-5` | 0.925 |
| `anthropic/claude-haiku-4-5` | 0.920 |
| `openai/gpt-4o` | 0.864 |
| `openai/gpt-4o-mini` | 0.807 |

Interpretation:

- The Anthropic models lead this current-task slice, but the margin between
  `claude-sonnet-4-5` and `claude-haiku-4-5` is small at this resolution.
- `openai/gpt-4o` is strong on the newer implementation tasks but is held back
  by weaker historical snapshot cells, especially `growth_01`, `clone_01`, and
  `transform_01`.
- `openai/gpt-4o-mini` saturates many newer tasks but remains weaker on
  `clone_01`, `growth_01`, `transform_01`, and `followup_01`.
- `transform_01` remains the sharpest execution-reporting stressor across all
  models; it should be discussed as an execution-reliability task rather than a
  deep reasoning task.

## Per-Task Summary

Mean score across the seed samples run for each `(model, task)` cell. `n` is the
number of samples in that cell.

| Model | Task | n | overall (mean±std) | task_success (mean±std) | decision_quality (mean±std) | troubleshooting (mean±std) | efficiency (mean±std) |
|---|---|---:|---:|---:|---:|---:|---:|
| anthropic/claude-haiku-4-5 | `clone_01` | 10 | 0.950 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 0.500 ± 0.000 |
| anthropic/claude-haiku-4-5 | `express_01` | 10 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 |
| anthropic/claude-haiku-4-5 | `followup_01` | 10 | 0.915 ± 0.129 | 0.900 ± 0.316 | 1.000 ± 0.000 | 1.000 ± 0.000 | 0.550 ± 0.158 |
| anthropic/claude-haiku-4-5 | `gibson_01` | 10 | 0.950 ± 0.125 | 0.900 ± 0.316 | 1.000 ± 0.000 | 1.000 ± 0.000 | 0.900 ± 0.211 |
| anthropic/claude-haiku-4-5 | `golden_gate_01` | 10 | 0.900 ± 0.160 | 0.800 ± 0.422 | 1.000 ± 0.000 | 1.000 ± 0.000 | 0.800 ± 0.258 |
| anthropic/claude-haiku-4-5 | `growth_01` | 10 | 0.990 ± 0.032 | 1.000 ± 0.000 | 0.967 ± 0.105 | 1.000 ± 0.000 | 1.000 ± 0.000 |
| anthropic/claude-haiku-4-5 | `miniprep_01` | 10 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 |
| anthropic/claude-haiku-4-5 | `pcr_01` | 10 | 0.950 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 0.500 ± 0.000 |
| anthropic/claude-haiku-4-5 | `purify_01` | 10 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 |
| anthropic/claude-haiku-4-5 | `screen_01` | 10 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 |
| anthropic/claude-haiku-4-5 | `transform_01` | 10 | 0.465 ± 0.053 | 0.000 ± 0.000 | 0.650 ± 0.053 | 1.000 ± 0.000 | 0.700 ± 0.422 |
| anthropic/claude-sonnet-4-5 | `clone_01` | 10 | 0.950 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 0.500 ± 0.000 |
| anthropic/claude-sonnet-4-5 | `express_01` | 10 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 |
| anthropic/claude-sonnet-4-5 | `followup_01` | 10 | 0.915 ± 0.024 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 0.150 ± 0.242 |
| anthropic/claude-sonnet-4-5 | `gibson_01` | 10 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 |
| anthropic/claude-sonnet-4-5 | `golden_gate_01` | 10 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 |
| anthropic/claude-sonnet-4-5 | `growth_01` | 10 | 0.875 ± 0.252 | 0.800 ± 0.422 | 0.900 ± 0.225 | 1.000 ± 0.000 | 0.850 ± 0.242 |
| anthropic/claude-sonnet-4-5 | `miniprep_01` | 10 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 |
| anthropic/claude-sonnet-4-5 | `pcr_01` | 10 | 0.950 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 0.500 ± 0.000 |
| anthropic/claude-sonnet-4-5 | `purify_01` | 10 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 |
| anthropic/claude-sonnet-4-5 | `screen_01` | 10 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 |
| anthropic/claude-sonnet-4-5 | `transform_01` | 10 | 0.480 ± 0.169 | 0.200 ± 0.422 | 0.667 ± 0.000 | 1.000 ± 0.000 | 0.000 ± 0.000 |
| openai/gpt-4o | `clone_01` | 10 | 0.682 ± 0.364 | 0.700 ± 0.483 | 0.790 ± 0.285 | 0.600 ± 0.516 | 0.450 ± 0.158 |
| openai/gpt-4o | `express_01` | 10 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 |
| openai/gpt-4o | `followup_01` | 10 | 0.835 ± 0.120 | 1.000 ± 0.000 | 0.800 ± 0.158 | 0.700 ± 0.483 | 0.550 ± 0.158 |
| openai/gpt-4o | `gibson_01` | 10 | 0.980 ± 0.026 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 0.800 ± 0.258 |
| openai/gpt-4o | `golden_gate_01` | 10 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 |
| openai/gpt-4o | `growth_01` | 10 | 0.550 ± 0.237 | 0.700 ± 0.483 | 0.500 ± 0.176 | 0.100 ± 0.316 | 1.000 ± 0.000 |
| openai/gpt-4o | `miniprep_01` | 10 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 |
| openai/gpt-4o | `pcr_01` | 10 | 0.942 ± 0.024 | 1.000 ± 0.000 | 0.975 ± 0.079 | 1.000 ± 0.000 | 0.500 ± 0.000 |
| openai/gpt-4o | `purify_01` | 10 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 |
| openai/gpt-4o | `screen_01` | 10 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 |
| openai/gpt-4o | `transform_01` | 10 | 0.515 ± 0.024 | 0.000 ± 0.000 | 0.733 ± 0.117 | 1.000 ± 0.000 | 0.950 ± 0.158 |
| openai/gpt-4o-mini | `clone_01` | 10 | 0.352 ± 0.315 | 0.500 ± 0.527 | 0.490 ± 0.331 | 0.000 ± 0.000 | 0.050 ± 0.158 |
| openai/gpt-4o-mini | `express_01` | 10 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 |
| openai/gpt-4o-mini | `followup_01` | 10 | 0.605 ± 0.185 | 0.600 ± 0.516 | 0.500 ± 0.000 | 0.900 ± 0.316 | 0.350 ± 0.242 |
| openai/gpt-4o-mini | `gibson_01` | 10 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 |
| openai/gpt-4o-mini | `golden_gate_01` | 10 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 |
| openai/gpt-4o-mini | `growth_01` | 10 | 0.530 ± 0.195 | 0.600 ± 0.516 | 0.500 ± 0.236 | 0.200 ± 0.422 | 1.000 ± 0.000 |
| openai/gpt-4o-mini | `miniprep_01` | 10 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 |
| openai/gpt-4o-mini | `pcr_01` | 10 | 0.955 ± 0.016 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 0.550 ± 0.158 |
| openai/gpt-4o-mini | `purify_01` | 10 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 |
| openai/gpt-4o-mini | `screen_01` | 10 | 0.930 ± 0.118 | 0.900 ± 0.316 | 1.000 ± 0.000 | 1.000 ± 0.000 | 0.700 ± 0.258 |
| openai/gpt-4o-mini | `transform_01` | 10 | 0.500 ± 0.078 | 0.000 ± 0.000 | 0.800 ± 0.131 | 0.900 ± 0.316 | 0.800 ± 0.258 |

## Notes

- This result is separate from the Discovery Decision Track. The discovery N=10
  HPC bundle is tracked in [docs/hpc_v0_2_status.md](../docs/hpc_v0_2_status.md)
  and should be promoted separately if needed.
- The completed current bundle combines logs generated at different commits.
  The scorer/task definitions used by the source evals are recorded in each
  source manifest; aggregation was performed at `177dbc8`.
- These results should be presented as a v0.2 candidate, not as a replacement
  for the April 2026 frozen scorecard.
