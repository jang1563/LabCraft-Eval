# Model Refresh Status — 2026-07-11

This is a compatibility and infrastructure checkpoint, not a model-quality
result. The runs below used an intentionally dirty implementation checkout and
must not be promoted into a scored release.

## Implemented contract

- Central registry: `config/model_matrix.toml`
- Default matrix: `current_balanced`
- Exact Inspect/provider pins: Inspect 0.3.245, OpenAI SDK 2.45.0, Anthropic
  SDK 0.116.0
- Per-model generation profiles with requested/resolved model validation
- GPT-5.6 structural `ModelInfo` registered from provider documentation
- HF schema 0.3 requested/resolved/provider/config/Inspect provenance
- Limit-exhausted samples rejected by the HPC cell validator and scored export
- `growth_01` uses source-backed defensible ranges rather than hidden exact
  starting-OD/cadence answers, with consistency required across each run
- `growth_01` separates a 40-turn agent cap from a 160-message hard cap so
  parallel tool results do not consume the agent-iteration budget

## Cayuga verification

Remote implementation checkout:

```text
/home/fs01/jak4013/codex_runs/BioProtocolBench-model-refresh-20260711
```

Environment setup job `3077724` completed successfully. Final check job
`3077811` passed 458 tests, Ruff, shell syntax, registry validation, wheel
build, isolated wheel installation, Inspect entry-point import, and GPT-5.6
metadata registration.

Compatibility array `3077769` ran `growth_01`, seed 0, serially across the four
current-core models. All four providers returned the expected resolved model
ID with the registered `{max_tokens: 16384, reasoning_effort: medium}` profile
and Inspect 0.3.245:

| Requested model | Resolved model | Current cell status |
|---|---|---|
| `openai/gpt-5.6-sol` | `gpt-5.6-sol` | Valid |
| `openai/gpt-5.6-luna` | `gpt-5.6-luna` | Valid |
| `anthropic/claude-sonnet-5` | `claude-sonnet-5` | Valid |
| `anthropic/claude-haiku-4-5-20251001` | `claude-haiku-4-5-20251001` | Compatible; original run incomplete |

Haiku retry job `3077812` recorded `--message-limit 120` in its cell manifest
but again exhausted the message limit. The strengthened validator rejected the
cell. Trajectory inspection showed that this was not a repeated-call loop: the
model completed a reasonable 30-minute pilot, diagnosed one undersampled fit,
reran at 20-minute cadence, and issued the final three fit calls immediately
before the message-only limit terminated the sample. Inspect counts each
parallel tool result as a separate message, so raising only that limit did not
address the task-contract problem.

After aligning the non-answer-bearing prompt and scorer, Haiku smoke job
`3079675` completed in 63 seconds and passed the strict cell validator. It used
59 messages, 15 assistant turns, and 42 tool calls: all three cultures started
at OD600 0.05, every incubation used a 15-minute interval, and all three final
fits were analyzable. Re-scoring that transcript with the final consistency
rule produced 1.0 on task success, decision quality, troubleshooting, and
efficiency. This is a single compatibility smoke from a dirty checkout, not a
model-quality estimate.

Final contract check job `3079676` passed 462 tests, Ruff, shell syntax,
registry validation, wheel build, isolated installation, and package smoke in
the pinned Cayuga environment.

## Clean revision verification

The first clean-checkout array (`3079678`) exposed two remaining scorer false
negatives: colon-only final-answer parsing rejected dash-formatted reports, and
the OD600 lower bound rejected scientifically defensible 0.01 and 0.02 starts.
The original logs remain unchanged. Replaying their trajectories after the
source-backed OD600 0.01-0.10 correction and colon/dash/Markdown-table parser
fix produced 1.0 on all four axes for all four models.

During the next clean run, source-path inspection found that the reused virtual
environment was editable-installed from an older checkout. Array `3079683` was
cancelled and is invalid for release use. The runner now prefixes the submitted
checkout on `PYTHONPATH`, fails before any API call when the imported `src` root
does not match `REPO_ROOT`, and records that root in cell manifest schema 1.2.0.

Final code revision `557194792520d27e64c545bed127402061fb9d0c` was copied to:

```text
/home/fs01/jak4013/codex_runs/BioProtocolBench-runtime-5571947
```

Check job `3079688` passed 467 tests, Ruff, shell syntax, registry validation,
wheel build, isolated installation, and package smoke. Compatibility array
`3079689` then completed `growth_01`, seed 0, serially across the four current
core models:

| Requested model | Resolved model | Messages | Assistant turns | Tool calls | Stored overall |
|---|---|---:|---:|---:|---:|
| `openai/gpt-5.6-sol` | `gpt-5.6-sol` | 47 | 12 | 33 | 1.000 |
| `openai/gpt-5.6-luna` | `gpt-5.6-luna` | 47 | 12 | 33 | 1.000 |
| `anthropic/claude-sonnet-5` | `claude-sonnet-5` | 55 | 14 | 39 | 1.000 |
| `anthropic/claude-haiku-4-5-20251001` | `claude-haiku-4-5-20251001` | 59 | 15 | 42 | 1.000 |

Every cell passed the strict validator with Inspect 0.3.245, the registered
generation profile, `worktree_dirty=false`, manifest schema 1.2.0, the exact
commit above, and the expected runtime source root. These four rows are still
compatibility smokes from one task and one seed, not comparative model-quality
estimates.

## Scale decision

The current four-model core matrix and runtime-provenance path are compatible.
The next scale gate should remain small: run selected non-growth tasks at one
seed from a clean revision, confirm task-specific scorer validity, and only
then choose a multi-seed matrix. Keep the frozen historical results and the
invalidated/cancelled diagnostic arrays out of any promoted aggregate.
