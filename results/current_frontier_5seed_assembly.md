# Current Frontier Assembly View (5 Seed-Labelled Repetitions)

Focused view of the two assembly tasks in the newer-task five-repeat frontier
bundle: `golden_gate_01` and `gibson_01`.

> These are historical pre-remediation scores. The agent-facing prompts used for
> these logs supplied several scored assembly choices; current task definitions
> do not. The five observations are descriptive and do not establish model
> stability.

This page isolates the two assembly tasks because all non-perfect stored values
in this historical five-repeat bundle occur there; the protein and miniprep rows
are saturated under the pre-remediation scorer.

## Key takeaway

- `gpt-4o-mini` and `claude-sonnet-4-5` receive perfect stored scores on both assembly tasks across all five repetitions.
- `gpt-4o` is still near-perfect, with only a small `gibson_01` efficiency penalty.
- `claude-haiku-4-5` is the only model with a task-success miss under the historical scorer: `golden_gate_01` falls to `0.910` because one response reported an incorrect final transformant value despite full recorded decision-quality credit.

## Assembly-task summary

| Model | golden_gate_01 | gibson_01 |
|---|---:|---:|
| `openai/gpt-4o-mini` | 1.000 | 1.000 |
| `openai/gpt-4o` | 1.000 | 0.980 |
| `anthropic/claude-haiku-4-5` | 0.910 | 0.970 |
| `anthropic/claude-sonnet-4-5` | 1.000 | 1.000 |

## Files

- Overall-only assembly scorecard: [scorecard.png](current_frontier_5seed_assembly_plots/scorecard.png)
- Assembly axis breakdown: [axis_heatmap.png](current_frontier_5seed_assembly_plots/axis_heatmap.png)
- Full five-repeat frontier bundle: [current_frontier_5seed.md](current_frontier_5seed.md)

## Historical plot reconstruction

This command reads the tracked logs but writes a new plot bundle under
`build/`; it does not modify the frozen result assets.

```bash
python3 scripts/plot_scorecard.py \
  --log-dir results/current_openai_logs results/current_anthropic_logs \
            results/current_openai_logs_seed34 results/current_anthropic_logs_seed34 \
  --out-dir build/historical_reaggregation/current_frontier_5repeat_assembly/plots \
  --tasks golden_gate_01 gibson_01 \
  --models openai/gpt-4o-mini openai/gpt-4o anthropic/claude-haiku-4-5 anthropic/claude-sonnet-4-5
```
