# Current Task OpenAI Bundle

Small comparable bundle for the newer implemented tasks added after the frozen April 2026 5-task portfolio snapshot.

> **Historical/pre-remediation artifact:** these logs were collected with
> agent-facing assistant prompts that supplied several scored protocol choices.
> The current task definitions remove that guidance. Treat the table as a
> historical regression artifact, not as a current capability or reliability
> result.

This bundle is intentionally separate from both:

- the published historical portfolio in [results.md](results.md)
- the 1-model, 1-seed sanity-check track in [current_smoke.md](current_smoke.md)

## Configuration

- Models: `openai/gpt-4o-mini`, `openai/gpt-4o`
- Stored repetitions: 3 per task, identified by seed-labelled sample IDs
- Tasks:
  `golden_gate_01`, `gibson_01`, `miniprep_01`, `express_01`, `purify_01`

## Headline

The newer-task bundle is almost fully saturated for both OpenAI models.

- `gpt-4o-mini` received `1.000` on all five tasks across all three stored repetitions.
- `gpt-4o` also saturated four of five tasks.
- The only visible gap was `gibson_01`, where `gpt-4o` achieved `overall = 0.967 ± 0.029` because the historical correctness checks passed but the efficiency budget was missed on 2 of 3 repetitions.

## Summary

| Model | golden_gate_01 | gibson_01 | miniprep_01 | express_01 | purify_01 |
|---|---:|---:|---:|---:|---:|
| `openai/gpt-4o-mini` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| `openai/gpt-4o` | 1.000 | 0.967 | 1.000 | 1.000 | 1.000 |

## Interpretation

This is a small historical smoke slice:

- the stored logs exercise repeated evaluation and aggregation paths
- both OpenAI models meet the pre-remediation task-success and decision-quality checks in these stored responses
- `gibson_01` still exposes a small execution-efficiency difference that the deterministic scorer can detect

The seed labels identify repetitions and initialize task state. They do not
make every task stochastic: miniprep, expression, and purification are
deterministic across these labels. The observed spread therefore must not be
attributed solely to simulated laboratory variation.

## Files

- Aggregated table: [current_openai_results.md](current_openai_results.md)
- Raw eval logs: [current_openai_logs](current_openai_logs)
- Plots:
  [scorecard.png](current_openai_plots/scorecard.png)
  [axis_heatmap.png](current_openai_plots/axis_heatmap.png)

## Historical aggregation and current reruns

Re-aggregating the stored logs reconstructs this table. A new model run uses the
current, leakage-remediated task contract and is not an exact reproduction.

```bash
# Re-aggregate the immutable historical logs into build/ only.
python3 scripts/aggregate_eval_results.py \
  --log-dir results/current_openai_logs \
  --out build/historical_reaggregation/current_openai_3repeat/results.md

python3 scripts/plot_scorecard.py \
  --log-dir results/current_openai_logs \
  --out-dir build/historical_reaggregation/current_openai_3repeat/plots \
  --task-preset auto \
  --models openai/gpt-4o-mini openai/gpt-4o

# Run the current implementation as a new experiment.
RUN_ID=current_openai_3repeat_integrity \
LOG_DIR=build/eval_runs/current_openai_3repeat_integrity \
SEEDS=3 \
MODELS="openai/gpt-4o-mini openai/gpt-4o" \
TASKS="golden_gate_01 gibson_01 miniprep_01 express_01 purify_01" \
./scripts/run_portfolio_eval.sh
```
