# Current Task Frontier Bundle

Small cross-provider bundle for the newer implemented tasks added after the frozen April 2026 5-task portfolio snapshot.

> **Historical/pre-remediation artifact:** these logs predate removal of
> answer-bearing protocol guidance from several agent-facing prompts. The table
> describes that historical prompt/scorer contract and is not a current model or
> provider comparison.

This bundle is intentionally separate from:

- the published historical portfolio in [results.md](results.md)
- the 1-model smoke track in [current_smoke.md](current_smoke.md)
- the OpenAI-only comparable slice in [current_openai.md](current_openai.md)

## Configuration

- Models: `openai/gpt-4o-mini`, `openai/gpt-4o`, `anthropic/claude-haiku-4-5`, `anthropic/claude-sonnet-4-5`
- Stored repetitions: 3 per task, identified by seed-labelled sample IDs
- Tasks:
  `golden_gate_01`, `gibson_01`, `miniprep_01`, `express_01`, `purify_01`

## Headline

The current-task frontier bundle is nearly saturated across all four models.

- `gpt-4o-mini` and `claude-sonnet-4-5` received `1.000` on all five tasks across all three stored repetitions.
- `gpt-4o` only dropped on `gibson_01`, with `overall = 0.967 ± 0.029` because efficiency fell to `0.667 ± 0.289` while every other axis stayed perfect.
- `claude-haiku-4-5` only dropped on the two assembly tasks, with `overall = 0.983 ± 0.029` on both `golden_gate_01` and `gibson_01`, again driven entirely by efficiency misses.

## Summary

| Model | Mean across tasks | golden_gate_01 | gibson_01 | miniprep_01 | express_01 | purify_01 |
|---|---:|---:|---:|---:|---:|---:|
| `openai/gpt-4o-mini` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| `openai/gpt-4o` | 0.993 | 1.000 | 0.967 | 1.000 | 1.000 | 1.000 |
| `anthropic/claude-haiku-4-5` | 0.993 | 0.983 | 0.983 | 1.000 | 1.000 | 1.000 |
| `anthropic/claude-sonnet-4-5` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |

## Interpretation

Within this historical scorer output, the non-perfect values are almost entirely
efficiency penalties rather than task-success or decision-quality penalties.

- All four models saturated `task_success`, `decision_quality`, and `troubleshooting` on every cell in this bundle.
- The only non-perfect scores came from extra tool use on assembly-style tasks.
- The slice is too small, saturated, and prompt-assisted to support a provider-level inference.

## Notes

The Anthropic raw log directory contains repeated reruns for some cells after an interrupted earlier run. The aggregated tables and plots in this bundle deduplicate repeated `(model, task, sample_id)` rows by keeping the latest `.eval` archive, so every reported cell here reflects exactly three stored repetitions.

## Files

- Aggregated table: [current_frontier_results.md](current_frontier_results.md)
- Raw eval logs: [current_openai_logs](current_openai_logs), [current_anthropic_logs](current_anthropic_logs)
- Plots: [scorecard.png](current_frontier_plots/scorecard.png), [axis_heatmap.png](current_frontier_plots/axis_heatmap.png)

## Historical aggregation and current reruns

Re-aggregating the stored logs reconstructs this table. New model calls use the
current leakage-remediated prompts and should be published as a separate run.

```bash
# Re-aggregate the immutable historical logs into build/ only.
python3 scripts/aggregate_eval_results.py \
  --log-dir results/current_openai_logs results/current_anthropic_logs \
  --out build/historical_reaggregation/current_frontier_3repeat/results.md

python3 scripts/plot_scorecard.py \
  --log-dir results/current_openai_logs results/current_anthropic_logs \
  --out-dir build/historical_reaggregation/current_frontier_3repeat/plots \
  --task-preset auto \
  --models openai/gpt-4o-mini openai/gpt-4o anthropic/claude-haiku-4-5 anthropic/claude-sonnet-4-5

# Run the current implementation as a new experiment.
RUN_ID=current_frontier_3repeat_integrity \
LOG_DIR=build/eval_runs/current_frontier_3repeat_integrity \
SEEDS=3 \
MODELS="openai/gpt-4o-mini openai/gpt-4o anthropic/claude-haiku-4-5 anthropic/claude-sonnet-4-5" \
TASKS="golden_gate_01 gibson_01 miniprep_01 express_01 purify_01" \
./scripts/run_portfolio_eval.sh
```
