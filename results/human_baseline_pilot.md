# Human Baseline Pilot

Manual baseline sessions aggregated from [results/human_baseline_sessions](../results/human_baseline_sessions).

These sessions are intentionally separate from the frozen model-only portfolio snapshot. They provide early human context under the current prompt, scorer, and explicit-seed convention. Frozen same-label model rows are contextual only: they used an earlier seed convention and are not matched simulator instances.

## Status

No completed human baseline sessions have been checked in yet.

The recommended first-pass collection set is documented in [results/human_baseline_seed_plan.md](../results/human_baseline_seed_plan.md).

## Planned coverage

| Task | Seed | Human sessions | Prompt split | Operators | Snapshot overall range | Snapshot best |
|---|---:|---:|---|---|---:|---|
| `transform_01` | 0 | 0 | - | - | 0.400-0.800 | 0.800 (claude-sonnet-4-5) |
| `transform_01` | 2 | 0 | - | - | 0.400-0.850 | 0.850 (claude-haiku-4-5) |
| `transform_01` | 4 | 0 | - | - | 0.250-0.600 | 0.600 (gpt-4o-mini) |
| `growth_01` | 1 | 0 | - | - | 0.600-1.000 | 1.000 (claude-haiku-4-5) |
| `growth_01` | 2 | 0 | - | - | 0.300-1.000 | 1.000 (claude-sonnet-4-5) |
| `growth_01` | 3 | 0 | - | - | 0.200-1.000 | 1.000 (claude-sonnet-4-5) |

## Next step

Use [docs/human_baseline.md](../docs/human_baseline.md) together with the seed plan above, collect 1-3 expert sessions on `transform_01` and `growth_01`, then rerun:

```bash
python3 scripts/aggregate_human_baseline.py
```

The aggregator also writes a structured JSON sidecar for downstream plotting and comparison scripts.
