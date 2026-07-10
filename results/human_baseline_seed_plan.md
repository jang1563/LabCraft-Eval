# Human Baseline Seed Plan

This is the recommended first-pass manual collection pack for the human baseline workflow on `transform_01` and `growth_01`.

The machine-readable source of truth for this plan lives in [results/human_baseline_seed_plan.json](../results/human_baseline_seed_plan.json); this page is the human-readable briefing version.

The goal is not to sample labels uniformly. It is to prioritize labels whose
frozen April 2026 rows showed disagreement or scorer failures. Current human
runs use the current prompt and explicit-seed convention, so these labels are
triage anchors rather than matched replays of the historical instances.

## Selection logic

- Keep the scope narrow: 6 baseline sessions total before expanding further.
- Prioritize labels where the four historical model rows disagreed sharply on `overall` or `task_success`.
- Include both "one model succeeds, others fail" cases and "everyone struggles" cases.
- Keep `growth_01` on the `baseline` prompt variant for a consistent current
  human protocol. Frozen model scores remain contextual because the historical
  seed and prompt contract differs.

## Primary pilot matrix

Scores below are listed in the order `gpt-4o-mini / gpt-4o / claude-haiku-4-5 / claude-sonnet-4-5`, taken from [results/results.md](../results/results.md).

| Task | Seed label | Why this label is worth a human run | Historical model signal |
|---|---:|---|---|
| `transform_01` | 0 | Clean "only one model gets it over the line" case. Useful first check for whether this task is straightforward for a human or unusually brittle to answer formatting and execution completeness. | `0.600 / 0.450 / 0.400 / 0.800`; only `claude-sonnet-4-5` reaches `task_success = 1.0` |
| `transform_01` | 2 | Strong historical disagreement on the hardest snapshot task; useful for checking current human execution and formatting without claiming an instance match. | `0.500 / 0.500 / 0.850 / 0.400`; only `claude-haiku-4-5` reaches `task_success = 1.0` |
| `transform_01` | 4 | Failure-rich stress case. Best transform seed for checking recovery and reporting under messy execution. | `0.600 / 0.250 / 0.450 / 0.400`; `gpt-4o` drops to `troubleshooting = 0.0` and `efficiency = 0.5` |
| `growth_01` | 1 | Clean provider split with OpenAI missing the troubleshooting narrative while Anthropic mostly clears it. Good first human check on the reporting requirement. | `0.600 / 0.600 / 1.000 / 0.950`; OpenAI `troubleshooting = 0.0`, Anthropic `troubleshooting = 1.0` |
| `growth_01` | 2 | Broadest historical cross-model spread on the growth task; useful as a current reporting check. The growth environment itself is deterministic across labels. | `0.300 / 0.700 / 0.450 / 1.000`; all four models land in different score bands |
| `growth_01` | 3 | Best single targeted miss for `gpt-4o`. Good robustness check on awkward or undersampled growth data. | `0.700 / 0.200 / 1.000 / 1.000`; only `gpt-4o` fully collapses on `task_success` |

## Run commands

Replace `expert_a` with the actual operator identifier. The default session filenames will be written under `results/human_baseline_sessions/` and now include the operator id automatically.

```bash
python3 scripts/run_human_baseline.py --task transform_01 --seed-index 0 --operator-id expert_a
python3 scripts/run_human_baseline.py --task transform_01 --seed-index 2 --operator-id expert_a
python3 scripts/run_human_baseline.py --task transform_01 --seed-index 4 --operator-id expert_a
python3 scripts/run_human_baseline.py --task growth_01 --seed-index 1 --operator-id expert_a
python3 scripts/run_human_baseline.py --task growth_01 --seed-index 2 --operator-id expert_a
python3 scripts/run_human_baseline.py --task growth_01 --seed-index 3 --operator-id expert_a
```

For a guided version of the same pack, use:

```bash
python3 scripts/run_human_baseline_pilot.py --operator-id expert_a --list
python3 scripts/run_human_baseline_pilot.py --operator-id expert_a
python3 scripts/run_human_baseline_pilot.py --operator-id expert_a --all
```

That launcher reads [results/human_baseline_seed_plan.json](../results/human_baseline_seed_plan.json), resumes the first `in_progress` session if one exists, otherwise launches the next `pending` seed, and skips already completed seeds by default.

Example output artifact names:

- `results/human_baseline_sessions/expert_a__transform_01_seed_00.json`
- `results/human_baseline_sessions/expert_a__growth_01_seed_03.json`
- `results/human_baseline_sessions/expert_a__growth_01__verbose_troubleshoot_seed_02.json`

## After collection

Regenerate the pilot summary with:

```bash
python3 scripts/aggregate_human_baseline.py
```

That will update [results/human_baseline_pilot.md](../results/human_baseline_pilot.md) with per-session detail and per-operator summary rows.
