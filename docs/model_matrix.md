# Model Matrix and Generation Provenance

LabCraft-Eval keeps the runnable model matrix and model-specific generation
profiles in [`config/model_matrix.toml`](../config/model_matrix.toml). Runner,
HPC, validation, aggregation, export, and plotting code must read this registry
instead of maintaining independent model lists.

The registry was last checked against provider documentation on 2026-07-11.
The default `current_balanced` matrix is:

| Registry key | Inspect model ID | Intended role |
|---|---|---|
| `gpt_5_6_sol` | `openai/gpt-5.6-sol` | OpenAI flagship |
| `gpt_5_6_luna` | `openai/gpt-5.6-luna` | OpenAI efficient tier |
| `claude_sonnet_5` | `anthropic/claude-sonnet-5` | Anthropic frontier tier |
| `claude_haiku_4_5` | `anthropic/claude-haiku-4-5-20251001` | Anthropic efficient tier |

`current_optional` adds `openai/gpt-5.6-terra` and
`anthropic/claude-fable-5`. `prior_modern` and `legacy_2026q2` exist only for
deliberate comparison or reproduction work; they are not current defaults.
The frozen checked-in result bundles remain unchanged and retain their
historical requested model IDs.

The current provider references are the [OpenAI model catalog](https://developers.openai.com/api/docs/models),
the [OpenAI latest-model guide](https://developers.openai.com/api/docs/guides/latest-model),
and the [Anthropic model overview](https://platform.claude.com/docs/en/about-claude/models/overview).
Re-check those primary sources before changing the registry.

## Why explicit IDs matter

Every active entry has both an Inspect request ID and an expected provider
response ID. New runs use explicit tier IDs rather than a family alias such as
`openai/gpt-5.6`. A successful API call is not sufficient evidence that the
intended model ran: the cell validator checks the resolved model recorded in
`sample.output.model` and fails on a mismatch or on mixed resolved snapshots.

OpenAI GPT-5.6 IDs are passed through by Inspect 0.3.245, but that release's
built-in catalog falls back to stale GPT-5 metadata. LabCraft-Eval therefore
registers the provider's official structural metadata from the central
registry before generation: context window, maximum output tokens, knowledge
cutoff, and reasoning support. Cost remains deliberately unregistered because
a flat Inspect `ModelCost` cannot represent GPT-5.6 long-context surcharges;
Inspect-derived GPT-5.6 cost estimates must not be treated as authoritative.

## Generation profiles

Each model has a non-empty `[models.<key>.generate]` profile. Current reasoning
models omit `temperature`; models that support reasoning effort use the
explicit registry value. This avoids the old shared `--temperature 0` setting,
which is not a portable cross-provider contract.

Inspect receives each profile through a generated `--generate-config` JSON
file. To inspect or validate the effective registry inputs without making an
API call:

```bash
python3 scripts/model_matrix.py validate
python3 scripts/model_matrix.py matrix current_balanced --format lines
python3 scripts/model_matrix.py generate-config openai/gpt-5.6-sol
python3 scripts/model_matrix.py model-info openai/gpt-5.6-sol
```

The portfolio runner uses `current_balanced` by default:

```bash
TASK_PRESET=discovery \
SEEDS=1 \
MODEL_MATRIX=current_balanced \
  ./scripts/run_portfolio_eval.sh
```

`MODELS` can select registered model IDs explicitly. Unregistered IDs fail
closed. The local portfolio runner retains `GENERATE_CONFIG_FILE` and the
legacy `GENERATE_CONFIG_ARGS` escape hatch for deliberate exploratory runs.
The Slurm array runner rejects both overrides and compares the native Inspect
generation configuration exactly with the registered profile.

## Recorded provenance

For schema 0.3 score-bearing rows, aggregation and export preserve:

- `requested_model`: the Inspect/provider request ID;
- `resolved_model`: the provider-returned model ID recorded by Inspect;
- `provider`;
- `effective_generation_config`: the generation configuration recorded in the
  native Inspect log; and
- `inspect_version`.

The requested and resolved IDs are intentionally separate. A rolling alias can
resolve differently over time, so an export fails if one requested ID maps to
multiple resolved IDs in the same release bundle. Clean evaluation and
packaging revisions remain separate release gates from model-identity
validation.

## Refresh procedure

1. Verify current IDs and positioning from the providers' primary model pages.
2. Update the registry entry, expected resolved ID, generation profile, and
   display metadata together.
3. Keep historical matrices and frozen result artifacts unchanged.
4. Run registry, unit, packaging, and schema checks on Cayuga.
5. Run one benign task with one seed per current-core model. Treat this as API
   compatibility evidence only, not as a model ranking.
6. Inspect every cell manifest and native `.eval` log for requested/resolved
   identity, provider, Inspect version, generation settings, stop reason, and
   refusal/error state before scheduling a larger evaluation.
