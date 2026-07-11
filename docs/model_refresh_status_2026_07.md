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

## Scale decision

The current four-model core matrix is API-compatible. Do not promote these
dirty-checkout smokes as benchmark results. Commit the contract correction,
rerun the small compatibility matrix from that clean revision, and require
every cell to pass the resolved-model, generation-config, clean-revision, and
no-limit-exhaustion gates before scaling to multiple tasks or seeds.
