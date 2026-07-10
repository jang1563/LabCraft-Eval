# Followup-01 Discovery Extension

Small discovery-facing extension built on the existing growth toolchain.

This page is intentionally separate from the frozen April 2026 5-task portfolio snapshot. It adds one new task, `followup_01`, that shifts LabCraft-Eval from pure assay execution toward **next-experiment choice after ambiguous intervention data**.

> **Historical/provisional artifact:** the stored runs use an earlier task/scorer
> revision. The growth simulator is deterministic across seed labels; the labels
> distinguish repeated model trajectories, not independent noisy growth curves.
> These results therefore describe prompt-following and reporting variation
> under that historical contract.

## Why this task exists

`growth_01` and `followup_01` now cover two adjacent but distinct agent behaviors:

| Task | What the agent must do | Why it matters |
|---|---|---|
| `growth_01` | Execute a three-condition OD600 assay and report doubling times | Exercises protocol execution and reporting in a deterministic growth model |
| `followup_01` | Choose the minimum follow-up experiment after an ambiguous chloramphenicol result and decide whether the slowdown is real | Exercises targeted next-experiment choice against a fixed synthetic intervention effect |

This is the most discovery-aligned part of the repo so far: the task is still small, but it asks the agent to resolve an uncertain intervention effect instead of just running a known assay end to end.

## Configuration

- Smoke validation:
  `gpt-4o-mini`, 1 seed-labelled repetition, `results/followup_smoke_logs`
- Comparable bundle:
  `gpt-4o-mini`, `claude-sonnet-4-5`, 3 seed-labelled repetitions each, `results/followup_logs`
- Tools:
  existing growth-only stack (`inoculate_growth`, `incubate`, `measure_od600`, `fit_growth_curve`) plus reference tools

## Headline

`followup_01` is not saturated, and the errors are informative.

- `claude-sonnet-4-5` scored `0.933 ± 0.029`, with full `task_success`, `decision_quality`, and `troubleshooting` credit on all three stored repetitions. Its only misses were efficiency penalties from taking more measurements than necessary.
- `gpt-4o-mini` scored `0.633 ± 0.227`, with failures concentrated in the **conclusion / follow-up framing** rather than the final doubling-time measurement itself.
- The single smoke repetition landed at `0.475`: `gpt-4o-mini` failed the historical `task_success` check while still collecting enough data to fit the deterministic curve.

## What the failures look like

The task separates several behaviors that `growth_01` alone does not:

- **Correct measurement, wrong conclusion.** On `gpt-4o-mini` seed `00`, the model measured a 40-minute doubling time but still concluded `artifact`, zeroing `task_success`.
- **Correct follow-up data, wrong intervention interpretation.** On seed `02`, `gpt-4o-mini` again reported `40.0 minutes` but concluded `no real slowdown`, and it also lost troubleshooting credit after an earlier undersampled fit.
- **Over-collection under the scorer contract.** `claude-sonnet-4-5` met the correctness checks in all three repetitions but often paid an efficiency tax. This demonstrates the scorer's intended distinction; it does not independently validate “right science” in a physical laboratory.

## Files

- Aggregated smoke table: [followup_smoke_results.md](followup_smoke_results.md)
- Aggregated 3-repeat table: [followup_results.md](followup_results.md)
- Raw logs: [followup_smoke_logs](followup_smoke_logs), [followup_logs](followup_logs)
- Plots: [scorecard.png](followup_plots/scorecard.png), [axis_heatmap.png](followup_plots/axis_heatmap.png)
- Human baseline status for the older credibility track: [human_baseline_pilot.md](human_baseline_pilot.md), [coverage.png](human_baseline_plots/coverage.png)

## Historical aggregation and current reruns

The aggregation commands reconstruct the stored table. New model calls use the
current task/scorer revision and should be treated as a separate experiment.

```bash
# Re-aggregate the immutable historical logs into build/ only.
python3 scripts/aggregate_eval_results.py \
  --log-dir results/followup_logs \
  --out build/historical_reaggregation/followup_3repeat/results.md

python3 scripts/plot_scorecard.py \
  --log-dir results/followup_logs \
  --out-dir build/historical_reaggregation/followup_3repeat/plots \
  --tasks followup_01 \
  --models openai/gpt-4o-mini anthropic/claude-sonnet-4-5

# Run the current implementation as a new experiment.
RUN_ID=followup_3repeat_integrity \
LOG_DIR=build/eval_runs/followup_3repeat_integrity \
SEEDS=3 \
MODELS="openai/gpt-4o-mini anthropic/claude-sonnet-4-5" \
TASKS="followup_01" \
./scripts/run_portfolio_eval.sh
```
