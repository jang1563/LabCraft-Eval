# HPC v0.2 Status

Updated: 2026-05-18

This page records the current HPC-only v0.2 execution state. The local machine is
used for editing, source inspection, git operations, and artifact review only.
Tests, API-backed Inspect runs, aggregation, and plotting are run on Cayuga.

Raw HPC bundles live under `results/hpc/<RUN_ID>/` and are ignored by git. Treat
the paths below as local artifact references, not public release links.

## Valid Bundles

| RUN_ID | Preset | Commit | Matrix | Status |
|---|---|---|---|---|
| `2026_05_v0_2_discovery_n10` | `discovery` | `4bd2f38` | 3 tasks x 4 models x 10 seeds | Valid: 120 manifests, 120 eval logs |
| `2026_05_v0_2_current_n10` | `current` | `4bd2f38` | 11 tasks x 4 models x 10 seeds | Source bundle: Anthropic full current matrix plus OpenAI snapshot tasks; OpenAI newer-task cells were quota-blocked |
| `2026_05_v0_2_current_openai_missing_n10` | explicit current subset | `177dbc8` | 6 newer current tasks x 2 OpenAI models x 10 seeds | Valid fill-in bundle: 120 manifests, 120 eval logs |
| `2026_05_v0_2_current_n10_completed` | `current` | `177dbc8` aggregation over mixed source logs | 11 tasks x 4 models x 10 seeds | Valid completed bundle: 440 deduplicated scored rows |
| `2026_05_v0_2_anthropic_all_seed10_19` | `all` | `c34107f` | 14 tasks x 2 Anthropic models x seeds 10-19 | Valid: 280 manifests, 280 eval logs |
| `2026_05_v0_2_safety_anthropic_s3_msglimit3` | `safety_case` | `073126a` | 30 scenarios x 2 Anthropic models x 3 seeds | Valid: 6 eval logs, 180 scored rows |
| `2026_05_v0_2_safety_openai_s3` | `safety_case` | `177dbc8` | 30 scenarios x 2 OpenAI models x 3 seeds | Valid: 6 eval logs, 180 scored rows |
| `2026_05_v0_2_safety_all_s3_completed` | `safety_case` | `177dbc8` aggregation over OpenAI and Anthropic safety logs | 30 scenarios x 4 models x 3 seeds | Valid combined safety summary: 360 deduplicated scored rows |

## Headline Results

Discovery N=10 is the cleanest complete four-model v0.2 slice so far. Mean
overall scores across the three discovery tasks are approximately:

| Model | Mean overall |
|---|---:|
| `anthropic/claude-sonnet-4-5` | 0.924 |
| `anthropic/claude-haiku-4-5` | 0.911 |
| `openai/gpt-4o` | 0.862 |
| `openai/gpt-4o-mini` | 0.837 |

Current N=10 is now complete after filling the quota-blocked OpenAI newer-task
cells. Mean overall scores across the 11 current tasks are approximately:

| Model | Mean overall |
|---|---:|
| `anthropic/claude-sonnet-4-5` | 0.925 |
| `anthropic/claude-haiku-4-5` | 0.920 |
| `openai/gpt-4o` | 0.864 |
| `openai/gpt-4o-mini` | 0.807 |

Safety-case live smoke is now valid across all four frontier models after
fixing the empty-completion issue:

| Model | aggregate | legitimate_helpfulness | boundary_precision | provenance_grounding | monitor_coverage | residual_risk_framing |
|---|---:|---:|---:|---:|---:|---:|
| `anthropic/claude-haiku-4-5` | 0.790 +- 0.117 | 0.824 +- 0.110 | 0.911 +- 0.286 | 0.608 +- 0.299 | 0.907 +- 0.149 | 0.701 +- 0.311 |
| `anthropic/claude-sonnet-4-5` | 0.759 +- 0.110 | 0.822 +- 0.108 | 0.922 +- 0.269 | 0.534 +- 0.364 | 0.896 +- 0.151 | 0.618 +- 0.373 |
| `openai/gpt-4o` | 0.729 +- 0.100 | 0.717 +- 0.144 | 0.978 +- 0.148 | 0.293 +- 0.368 | 0.804 +- 0.211 | 0.854 +- 0.130 |
| `openai/gpt-4o-mini` | 0.728 +- 0.104 | 0.722 +- 0.135 | 0.967 +- 0.181 | 0.291 +- 0.372 | 0.767 +- 0.238 | 0.895 +- 0.027 |

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
- Job `2955343`: OpenAI quota probe passed on `golden_gate_01 x gpt-4o-mini`.
- Job `2955344`: OpenAI missing current-task fill-in completed 120/120 cells.
- Job `2955465`: OpenAI missing current-task aggregation wrote 120 rows and
  scorecard plots.
- Manual HPC aggregation `2026_05_v0_2_current_n10_completed` wrote 440
  deduplicated current-task rows and plots from the original current bundle plus
  the OpenAI fill-in bundle.
- Job `2955472`: OpenAI safety-case live eval completed 6/6 cells with
  non-empty completions and validator success.
- Job `2955481`: OpenAI safety-case aggregation wrote 180 rows and intentionally
  skipped scorecard plots.
- Manual HPC aggregation `2026_05_v0_2_safety_all_s3_completed` wrote 360
  deduplicated safety-case rows across all four models.

## Next Actions

1. Decide whether `2026_05_v0_2_current_n10_completed` should become the public
   v0.2 current-task result page, or whether to keep it as an internal candidate
   until release notes and narrative framing are polished.
2. Decide whether Anthropic seed 0-19 should become a public N=20 stability
   slice, or remain an internal variance probe.
3. Decide whether `2026_05_v0_2_safety_all_s3_completed` should be promoted into
   a short public safety-case live-smoke page, separate from the simulator
   scorecard.
4. Promote only one curated v0.2 public result page; keep exploratory HPC
   bundles append-only and clearly separated from the frozen April 2026
   scorecard.
