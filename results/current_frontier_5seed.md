# Current Task Frontier Bundle (5 Seed-Labelled Repetitions)

Expanded cross-provider bundle for the newer implemented tasks, extending the
earlier 3-repeat slice to five seed-labelled repetitions per task. These labels
do not imply five independent stochastic environments: assembly/plating paths
contain seeded draws, while miniprep, expression, and purification operations
in this bundle are deterministic across seed labels.

> **Historical/pre-remediation artifact:** these logs were collected before the
> integrity patch removed answer-bearing protocol guidance from agent-facing
> assistant prompts and tightened result validation. The stored scores describe
> that historical prompt/scorer contract. They are not comparable to a run of
> the current task definitions and do not establish model stability or provider
> capability.

This bundle is intentionally separate from:

- the published historical portfolio in [results.md](results.md)
- the 1-model smoke track in [current_smoke.md](current_smoke.md)
- the OpenAI-only 3-repeat slice in [current_openai.md](current_openai.md)
- the earlier cross-provider 3-repeat slice in [current_frontier.md](current_frontier.md)

## Configuration

- Models: `openai/gpt-4o-mini`, `openai/gpt-4o`, `anthropic/claude-haiku-4-5`, `anthropic/claude-sonnet-4-5`
- Stored repetitions: 5 per task, labelled `seed_00` through `seed_04`
- Tasks:
  `golden_gate_01`, `gibson_01`, `miniprep_01`, `express_01`, `purify_01`
- Construction:
  labels `00`-`02` come from the existing 3-repeat logs
  labels `03`-`04` were added later via the `seed_start` task parameter

## Headline

The stored five-repeat table differs from the earlier three-repeat table.

- `gpt-4o-mini` and `claude-sonnet-4-5` received perfect scorer outputs across all five tasks and all five stored repetitions.
- `gpt-4o` is slightly higher than in the 3-repeat table, ending at `0.996` mean across tasks with its only gap on `gibson_01` efficiency.
- `claude-haiku-4-5` moved to `0.976` mean across tasks because one added `golden_gate_01` response missed the historical task-success contract and one `gibson_01` response incurred an efficiency penalty.

## Summary

| Model | Mean across tasks | golden_gate_01 | gibson_01 | miniprep_01 | express_01 | purify_01 |
|---|---:|---:|---:|---:|---:|---:|
| `openai/gpt-4o-mini` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| `openai/gpt-4o` | 0.996 | 1.000 | 0.980 | 1.000 | 1.000 | 1.000 |
| `anthropic/claude-haiku-4-5` | 0.976 | 0.910 | 0.970 | 1.000 | 1.000 | 1.000 |
| `anthropic/claude-sonnet-4-5` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |

## Interpretation

This larger stored slice adds one final-answer miss that was absent from the
earlier three repetitions. At this sample size, and under the pre-remediation
prompt, that is a descriptive observation rather than evidence of stability or
instability.

- No scorer miss appears in the five stored `gpt-4o-mini` or `claude-sonnet-4-5` repetitions.
- `gpt-4o` meets the historical correctness checks but receives an execution-efficiency penalty on `gibson_01` in 1 of 5 stored samples.
- In the `golden_gate_01` repetition labelled `seed_04`, `claude-haiku-4-5` met the historical decision checks but converted a low-count plate into an incorrect final transformant report (`80`), causing `task_success = 0.0`. Its `gibson_01` `seed_04` response also incurred an efficiency penalty.

## Notes

The Anthropic 3-repeat raw log directory contains repeated reruns for some cells after an interrupted earlier run. The aggregated tables and plots here deduplicate repeated `(model, task, sample_id)` rows by keeping the latest `.eval` archive.

The five-repeat bundle is assembled from four log directories: the original
three-repeat OpenAI and Anthropic runs, plus separate `seed_03`/`seed_04`
extension runs collected with `SEED_START=3`.

## Files

- Aggregated table: [current_frontier_5seed_results.md](current_frontier_5seed_results.md)
- Raw eval logs: [current_openai_logs](current_openai_logs), [current_anthropic_logs](current_anthropic_logs), [current_openai_logs_seed34](current_openai_logs_seed34), [current_anthropic_logs_seed34](current_anthropic_logs_seed34)
- Plots: [scorecard.png](current_frontier_5seed_plots/scorecard.png), [axis_heatmap.png](current_frontier_5seed_plots/axis_heatmap.png)
- Focused assembly-task view: [current_frontier_5seed_assembly.md](current_frontier_5seed_assembly.md)

## Historical aggregation and current reruns

The aggregation commands below reconstruct tables from the stored logs. Running
the model commands today uses the current prompts, scorer, model endpoints, and
generation configuration, so it creates a new experiment rather than exactly
reproducing this historical table.

```bash
# Re-aggregate the immutable historical logs into build/ only.
python3 scripts/aggregate_eval_results.py \
  --log-dir results/current_openai_logs results/current_anthropic_logs \
            results/current_openai_logs_seed34 results/current_anthropic_logs_seed34 \
  --out build/historical_reaggregation/current_frontier_5repeat/results.md

python3 scripts/plot_scorecard.py \
  --log-dir results/current_openai_logs results/current_anthropic_logs \
            results/current_openai_logs_seed34 results/current_anthropic_logs_seed34 \
  --out-dir build/historical_reaggregation/current_frontier_5repeat/plots \
  --task-preset auto \
  --models openai/gpt-4o-mini openai/gpt-4o anthropic/claude-haiku-4-5 anthropic/claude-sonnet-4-5

# Run the current implementation as a new experiment.
RUN_ID=current_frontier_5repeat_integrity \
LOG_DIR=build/eval_runs/current_frontier_5repeat_integrity \
SEEDS=5 \
MODELS="openai/gpt-4o-mini openai/gpt-4o anthropic/claude-haiku-4-5 anthropic/claude-sonnet-4-5" \
TASKS="golden_gate_01 gibson_01 miniprep_01 express_01 purify_01" \
./scripts/run_portfolio_eval.sh

python3 scripts/aggregate_eval_results.py \
  --log-dir build/eval_runs/current_frontier_5repeat_integrity \
  --out build/eval_runs/current_frontier_5repeat_integrity/results.md
```
