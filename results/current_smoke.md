# Current Task Smoke Bundle

Smoke-validation bundle for the newer implemented tasks added after the frozen April 2026 5-task portfolio snapshot.

> **Historical/pre-remediation artifact:** this smoke used answer-bearing
> assistant guidance that has since been removed. Its all-perfect score confirms
> completion of that historical harness path; it is not evidence of current task
> difficulty or model capability.

This bundle is intentionally separate from the published portfolio results in [results.md](results.md):

- It uses **1 model**: `openai/gpt-4o-mini`
- It uses **1 seed-labelled repetition per task**
- It covers the newer implemented tasks:
  `golden_gate_01`, `gibson_01`, `miniprep_01`, `express_01`, `purify_01`
- It is a **sanity-check / regression-smoke track**, not a comparable benchmark slice

## Outcome

All five smoke runs completed successfully on April 16, 2026, with `overall = 1.0` on the deterministic trajectory scorer.

| Task | Model | Repetitions | Overall |
|---|---|---:|---:|
| `golden_gate_01` | `openai/gpt-4o-mini` | 1 | 1.000 |
| `gibson_01` | `openai/gpt-4o-mini` | 1 | 1.000 |
| `miniprep_01` | `openai/gpt-4o-mini` | 1 | 1.000 |
| `express_01` | `openai/gpt-4o-mini` | 1 | 1.000 |
| `purify_01` | `openai/gpt-4o-mini` | 1 | 1.000 |

## Files

- Aggregated table: [current_smoke_results.md](current_smoke_results.md)
- Raw eval logs: [current_smoke_logs](current_smoke_logs)
- Plots:
  [scorecard.png](current_smoke_plots/scorecard.png)
  [axis_heatmap.png](current_smoke_plots/axis_heatmap.png)

## Historical aggregation and current rerun

Re-aggregate the historical log without modifying tracked results, or run the
current implementation into a new `build/eval_runs/` bundle:

```bash
python3 scripts/aggregate_eval_results.py \
  --log-dir results/current_smoke_logs \
  --out build/historical_reaggregation/current_smoke/results.md

python3 scripts/plot_scorecard.py \
  --log-dir results/current_smoke_logs \
  --out-dir build/historical_reaggregation/current_smoke/plots \
  --task-preset auto \
  --models openai/gpt-4o-mini

RUN_ID=current_smoke_integrity \
LOG_DIR=build/eval_runs/current_smoke_integrity \
SEEDS=1 \
MODELS="openai/gpt-4o-mini" \
TASKS="golden_gate_01 gibson_01 miniprep_01 express_01 purify_01" \
./scripts/run_portfolio_eval.sh
```
