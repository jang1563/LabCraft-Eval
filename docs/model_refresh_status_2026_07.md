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
| `anthropic/claude-haiku-4-5-20251001` | `claude-haiku-4-5-20251001` | Incomplete: 80-message limit |

Haiku retry job `3077812` recorded `--message-limit 120` in its cell manifest
but again exhausted the message limit. The strengthened validator rejected the
cell. This confirms API and generation-profile compatibility, but not a
completed `growth_01` evaluation trajectory for Haiku 4.5.

## Scale decision

Do not launch a larger `current_balanced` benchmark from this checkpoint. First
decide whether to tighten the agent termination/task guidance for efficient
models, use a different benign compatibility task, or change the core matrix.
Then commit the implementation, rerun from a clean checkout, and require every
cell to pass the resolved-model, generation-config, clean-revision, and
no-limit-exhaustion gates.
