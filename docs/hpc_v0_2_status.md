# HPC v0.2 Status

Updated: 2026-05-17

This page records the current HPC-only v0.2 execution state. The local machine is
used for editing, source inspection, git operations, and artifact review only.
Tests, API-backed Inspect runs, aggregation, and plotting are run on Cayuga.

Raw HPC bundles live under `results/hpc/<RUN_ID>/` and are ignored by git. Treat
the paths below as local artifact references, not public release links.

## Valid Bundles

| RUN_ID | Preset | Commit | Matrix | Status |
|---|---|---|---|---|
| `2026_05_v0_2_discovery_n10` | `discovery` | `4bd2f38` | 3 tasks x 4 models x 10 seeds | Valid: 120 manifests, 120 eval logs |
| `2026_05_v0_2_current_n10` | `current` | `4bd2f38` | 11 tasks x 4 models x 10 seeds | Partial: Anthropic full current matrix scored; OpenAI newer-task cells quota-blocked |
| `2026_05_v0_2_anthropic_all_seed10_19` | `all` | `c34107f` | 14 tasks x 2 Anthropic models x seeds 10-19 | Valid: 280 manifests, 280 eval logs |
| `2026_05_v0_2_safety_anthropic_s3_msglimit3` | `safety_case` | `073126a` | 30 scenarios x 2 Anthropic models x 3 seeds | Valid: 6 eval logs, 180 scored rows |

## Headline Results

Discovery N=10 is the cleanest complete four-model v0.2 slice so far. Mean
overall scores across the three discovery tasks are approximately:

| Model | Mean overall |
|---|---:|
| `anthropic/claude-sonnet-4-5` | 0.924 |
| `anthropic/claude-haiku-4-5` | 0.911 |
| `openai/gpt-4o` | 0.862 |
| `openai/gpt-4o-mini` | 0.837 |

Current N=10 should not be used for cross-provider model ranking yet. The
Anthropic rows cover all 11 current tasks across 10 seeds, but OpenAI only has
the historical snapshot tasks because the newer current-task cells hit provider
quota failures during the run.

Safety-case Anthropic live smoke is now valid after fixing the empty-completion
issue:

| Model | aggregate | legitimate_helpfulness | boundary_precision | provenance_grounding | monitor_coverage | residual_risk_framing |
|---|---:|---:|---:|---:|---:|---:|
| `anthropic/claude-haiku-4-5` | 0.790 +- 0.117 | 0.824 +- 0.110 | 0.911 +- 0.286 | 0.608 +- 0.299 | 0.907 +- 0.149 | 0.701 +- 0.311 |
| `anthropic/claude-sonnet-4-5` | 0.759 +- 0.110 | 0.822 +- 0.108 | 0.922 +- 0.269 | 0.534 +- 0.364 | 0.896 +- 0.151 | 0.618 +- 0.373 |

Do not report `2026_05_v0_2_safety_anthropic_s3` as a model-quality result. That
earlier bundle exposed a harness bug: `message_limit=2` allowed only system and
user messages, so the model completion was empty and the scorer returned a
floor-like score. Commit `073126a` fixes the task limit and makes the HPC cell
validator fail safety-case logs with empty model completions.

## Latest HPC Verification

- Job `2955181`: `hpc/slurm_checks.sh` passed on Cayuga with `296 passed`.
- Job `2955183`: safety-case Anthropic live eval completed 6/6 cells with
  non-empty completions and validator success.
- Job `2955193`: safety-case aggregation wrote 180 rows and intentionally
  skipped scorecard plots because safety-case axes are not wet-lab scorecard
  axes.

## Next Actions

1. Re-run the missing OpenAI current-task cells once quota is available:
   `golden_gate_01`, `gibson_01`, `miniprep_01`, `express_01`, `purify_01`,
   and `followup_01` for `openai/gpt-4o-mini` and `openai/gpt-4o`, seeds 0-9.
2. Aggregate a full current N=10 bundle only after those OpenAI cells exist.
3. Decide whether Anthropic seed 0-19 should become a public N=20 stability
   slice, or remain an internal variance probe.
4. Run safety-case OpenAI live smoke after quota recovery, using the fixed
   `message_limit=3` task and empty-completion validator.
5. Promote only one curated v0.2 public result page; keep exploratory HPC
   bundles append-only and clearly separated from the frozen April 2026
   scorecard.
