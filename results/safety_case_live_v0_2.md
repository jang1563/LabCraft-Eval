# Safety Case Live Smoke (HPC v0.2)

This page summarizes live model results for the separate Safety Case Track.
Safety-case results are not simulator scores and must not be merged into the
wet-lab trajectory leaderboard.

> **Historical scorer artifact:** these aggregates were produced before the
> provenance scorer introduced scenario-level citation allowlists. The public
> raw live-run bundle is unavailable, so the rows have not been rescored or
> independently audited under the current heuristic. Do not compare these
> values directly with current Safety Case scores or treat them as validated
> model/provider rankings.

The track evaluates whether a model remains helpful on legitimate BSL-1/BSL-2
bio-research requests while preserving boundaries, citations, monitoring
signals, and residual-risk framing.

## Configuration

- Combined bundle: `2026_05_v0_2_safety_all_s3_completed`
- Source bundles:
  - `2026_05_v0_2_safety_anthropic_s3_msglimit3`
  - `2026_05_v0_2_safety_openai_s3`
- Aggregation commit: `177dbc8`
- Task: `safety_case_01`
- Scenarios: 30 legitimate bio-research requests
- Models: `openai/gpt-4o-mini`, `openai/gpt-4o`,
  `anthropic/claude-haiku-4-5`, `anthropic/claude-sonnet-4-5`
- Seed-labelled repetitions: 3 per scenario and model, yielding 90 samples per
  model and 360 scored rows total. These labels repeat the same single-turn
  prompt; they do not seed a simulator.

## Important Harness Note

Do not report `2026_05_v0_2_safety_anthropic_s3` as a model-quality result. That
earlier run exposed a harness bug: `message_limit=2` allowed only system and
user messages, so model completions were empty. Commit `073126a` fixed
`safety_case_01` to use `message_limit=3` and added validation so safety-case
HPC cells fail if completions are empty.

## Summary

Mean score across the 90 samples for each model:

| Model | aggregate | legitimate_helpfulness | boundary_precision | provenance_grounding | monitor_coverage | residual_risk_framing |
|---|---:|---:|---:|---:|---:|---:|
| `anthropic/claude-haiku-4-5` | 0.790 ± 0.117 | 0.824 ± 0.110 | 0.911 ± 0.286 | 0.608 ± 0.299 | 0.907 ± 0.149 | 0.701 ± 0.311 |
| `anthropic/claude-sonnet-4-5` | 0.759 ± 0.110 | 0.822 ± 0.108 | 0.922 ± 0.269 | 0.534 ± 0.364 | 0.896 ± 0.151 | 0.618 ± 0.373 |
| `openai/gpt-4o` | 0.729 ± 0.100 | 0.717 ± 0.144 | 0.978 ± 0.148 | 0.293 ± 0.368 | 0.804 ± 0.211 | 0.854 ± 0.130 |
| `openai/gpt-4o-mini` | 0.728 ± 0.104 | 0.722 ± 0.135 | 0.967 ± 0.181 | 0.291 ± 0.372 | 0.767 ± 0.238 | 0.895 ± 0.027 |

## Interpretation

- In this historical scorer output, the Anthropic rows have higher aggregate
  means, driven mainly by `legitimate_helpfulness`, shape-based
  `provenance_grounding`, and `monitor_coverage`.
- The OpenAI rows have higher `boundary_precision` and
  `residual_risk_framing` means but lower historical provenance scores. These
  are descriptive properties of the old heuristic, not validated construct or
  provider differences.
- This track is a safeguard-quality smoke test on legitimate requests. It is
  not a harmful-capability benchmark and not evidence about real wet-lab
  execution.

## Relationship to Fixture Bundle

The live smoke is separate from [safety_case_track.md](safety_case_track.md),
which exercises the scorer against synthetic good-handling and targeted
failure-mode fixture transcripts. Use the fixture bundle to inspect the current
scoring contract; use this page only as a frozen record of the earlier live
smoke.
