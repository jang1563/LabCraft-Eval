# Followup-01 Discovery Extension

Small discovery-facing extension built on the existing growth toolchain.

This page is intentionally separate from the frozen April 2026 5-task portfolio snapshot. It adds one new task, `followup_01`, that shifts LabCraft-Eval from pure assay execution toward **next-experiment choice after ambiguous intervention data**.

## Why this task exists

`growth_01` and `followup_01` now cover two adjacent but distinct agent behaviors:

| Task | What the agent must do | Why it matters |
|---|---|---|
| `growth_01` | Execute a three-condition OD600 assay and report doubling times | Measures protocol execution reliability inside a stochastic lab workflow |
| `followup_01` | Choose the minimum follow-up experiment after an ambiguous chloramphenicol result and decide whether the slowdown is real | Measures targeted next-experiment reasoning under noisy intervention data |

This is the most discovery-aligned part of the repo so far: the task is still small, but it asks the agent to resolve an uncertain intervention effect instead of just running a known assay end to end.

## Configuration

- Smoke validation:
  `gpt-4o-mini`, 1 seed, `results/followup_smoke_logs`
- Comparable bundle:
  `gpt-4o-mini`, `claude-sonnet-4-5`, 3 seeds each, `results/followup_logs`
- Tools:
  existing growth-only stack (`inoculate_growth`, `incubate`, `measure_od600`, `fit_growth_curve`) plus reference tools

## Headline

`followup_01` is not saturated, and the errors are informative.

- `claude-sonnet-4-5` scored `0.933 ± 0.029`, with perfect `task_success`, `decision_quality`, and `troubleshooting` on all 3 seeds. Its only misses were efficiency penalties from taking more measurements than necessary.
- `gpt-4o-mini` scored `0.633 ± 0.227`, with failures concentrated in the **conclusion / follow-up framing** rather than the final doubling-time measurement itself.
- The 1-seed smoke run already showed the task was useful: `gpt-4o-mini` landed at `0.475`, failing `task_success` while still collecting enough data to fit the curve.

## What the failures look like

The task separates several behaviors that `growth_01` alone does not:

- **Correct measurement, wrong conclusion.** On `gpt-4o-mini` seed `00`, the model measured a 40-minute doubling time but still concluded `artifact`, zeroing `task_success`.
- **Correct follow-up data, wrong intervention interpretation.** On seed `02`, `gpt-4o-mini` again reported `40.0 minutes` but concluded `no real slowdown`, and it also lost troubleshooting credit after an earlier undersampled fit.
- **Over-collection without biology errors.** `claude-sonnet-4-5` solved all 3 seeds correctly but often paid an efficiency tax, which is exactly the sort of “right science, slightly wasteful workflow” distinction the four-axis scorer is meant to capture.

## Files

- Aggregated smoke table: [followup_smoke_results.md](followup_smoke_results.md)
- Aggregated 3-seed table: [followup_results.md](followup_results.md)
- Raw logs: [followup_smoke_logs](followup_smoke_logs), [followup_logs](followup_logs)
- Plots: [scorecard.png](followup_plots/scorecard.png), [axis_heatmap.png](followup_plots/axis_heatmap.png)
- Human baseline status for the older credibility track: [human_baseline_pilot.md](human_baseline_pilot.md), [coverage.png](human_baseline_plots/coverage.png)

## Reproduce

```bash
INSPECT_BIN=.venv/bin/inspect \
LOG_DIR=results/followup_smoke_logs \
SEEDS=1 \
MODELS="openai/gpt-4o-mini" \
TASKS="followup_01" \
./scripts/run_portfolio_eval.sh

INSPECT_BIN=.venv/bin/inspect \
LOG_DIR=results/followup_logs \
SEEDS=3 \
MODELS="openai/gpt-4o-mini anthropic/claude-sonnet-4-5" \
TASKS="followup_01" \
./scripts/run_portfolio_eval.sh

./.venv/bin/python scripts/aggregate_eval_results.py \
  --log-dir results/followup_logs \
  --out results/followup_results.md

./.venv/bin/python scripts/plot_scorecard.py \
  --log-dir results/followup_logs \
  --out-dir results/followup_plots \
  --tasks followup_01 \
  --models openai/gpt-4o-mini anthropic/claude-sonnet-4-5
```
