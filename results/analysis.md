# LabCraft-Eval Evaluation — Analysis

100 scored sample rows across 5 tasks × 4 frontier models × 5 stochastic seeds, April 2026.
This document analyzes the frozen April 2026 portfolio snapshot only: `transform_01`, `growth_01`, `pcr_01`, `screen_01`, and `clone_01`. The repo now implements additional tasks, including `golden_gate_01`, `gibson_01`, `miniprep_01`, `express_01`, and `purify_01`, but those are not part of the headline tables below. A separate appendix near the end summarizes the newer-task 5-seed frontier extension without merging it into the frozen snapshot. The repo also now includes a human-baseline workflow and pilot reporting for `transform_01` and `growth_01`, but no completed expert sessions are analyzed in this document yet.
Raw scores: [results.md](results.md). Raw trajectories: [logs/](logs/).

## Headline

The benchmark **discriminates**: mean overall scores span **0.44 – 1.00** across the (model, task) grid. **Provider, not price tier, is what matters** — both Anthropic models cluster at ~0.85, both OpenAI models at ~0.74.

| Model | Mean-across-tasks | Strongest task | Weakest task |
|---|---:|---|---|
| `claude-haiku-4-5` | **0.856** | `screen_01` (1.00) | `transform_01` (0.50) |
| `claude-sonnet-4-5` | 0.852 | `screen_01` (1.00) | `transform_01` (0.48) |
| `gpt-4o-mini` | 0.744 | `pcr_01` (0.97) | `growth_01` (0.56) |
| `gpt-4o` | 0.743 | `pcr_01` (0.95) | `transform_01` (0.44) |

Two findings the evaluation made visible that a single-model smoke would have hidden:

1. **`sonnet` does not beat `haiku`** on these five tasks. Means are within 0.004 of each other; on the one task where they differ (`clone_01` sonnet 0.95 vs. haiku 0.94), the gap is one-sample noise. For lab-execution reasoning at this scope, the 6× sonnet-over-haiku price premium buys nothing measurable.
2. **The provider gap is concentrated in one axis.** On `growth_01`, Anthropic models score 0.89 overall vs. OpenAI 0.57 — an entire 0.32 spread. Both OpenAI models score **troubleshooting = 0.00 on all 10 runs**; both Anthropic models score **troubleshooting = 1.00 on all 10 runs**. This is a deterministic behavioral split, not sampling noise.

## Task difficulty ranking

Per-task mean overall across all four models:

| Task | Mean overall | Comment |
|---|---:|---|
| `pcr_01` | **0.955** | Saturated. All four models pick Q5 + DMSO + 60 s extension + 32 cycles and interpret the clean target band identically. |
| `screen_01` | 0.935 | Saturated for Anthropic (1.00 × 10/10); OpenAI models occasionally drop the `Confidence achieved:` final-answer field (task_success = 0 on 2/10 runs). |
| `clone_01` | 0.879 | Mostly saturated. Failure mode concentrated in `gpt-4o-mini` (0.72), where 2/5 seeds skipped the troubleshooting language when the ligation yielded few transformants. |
| `growth_01` | 0.728 | Task-success nearly perfect (doubling times correct on 16/20), but OpenAI models score **0.00 on troubleshooting in all 10 runs**; Anthropic catches it every time. |
| `transform_01` | **0.498** | The compound-requirement task. Across 20 runs, only **2 cleared every gate**: haiku seed 01 and sonnet seed 02. Both produced biologically plausible ~10⁹ CFU/µg values. |

## The three most informative failure modes

### 1. `transform_01`: compound requirements are brittle

To score `task_success = 1.0`, an agent must:
1. Transform all four DNA masses (10 pg / 100 pg / 1 ng / 10 ng)
2. Choose dilutions that land each plate in the 25 – 250 colony "countable" range
3. Report CFU/µg for all four
4. Assert internal consistency

Observed behaviors across 20 seeds (4 models × 5 seeds):

| Pattern | Count | Notes |
|---|---:|---|
| Dilutions wrong on 1+ plates → "out of range" counts | 9 | dominant failure mode across all models |
| Reported only 2–3 of 4 masses | 6 | common when agents hit message_limit mid-analysis |
| Hit `message_limit` before finishing | 3 | haiku/sonnet prone to this on this task |
| Fully correct (passes task_success scorer) | **2** | haiku seed 01, sonnet seed 02 |

Task success by model: `gpt-4o-mini` 0/5, `gpt-4o` 0/5, `haiku` 1/5, `sonnet` 1/5.

This is exactly the *execution reliability* deficit that matters for real wet-lab automation: the agents know the chemistry, but they can't reliably juggle a compound multi-measurement reporting contract. For the two runs that *did* complete it, the reported CFU/µg values were 4 – 6 × 10⁹ — biologically plausible for chemically-competent DH5α. The benchmark isn't punishing models for getting the biology wrong; it's punishing them for execution slips.

### 2. `growth_01`: the troubleshooting axis catches an OpenAI blind spot

Every model determines the three doubling times correctly on most seeds (task_success = 0.80 mean). The **troubleshooting axis** splits deterministically:

- `gpt-4o` : **0.00** on all 5 seeds
- `gpt-4o-mini` : **0.00** on all 5 seeds
- `claude-haiku-4-5` : **1.00** on all 5 seeds
- `claude-sonnet-4-5` : **1.00** on all 5 seeds

The scorer flags a troubleshooting-relevant event when one of the growth-curve fits shows the LB culture saturating and requires an explicit explanation of the late-time-course dilution issue. Both Claude models explain this every time. Both GPT models report the doubling time correctly *but never explain the late-time-course issue* — not because the task is hidden from them, but because the behavior is provider-level. This is a useful, reproducible, interpretable gap.

### 3. `clone_01`: two latent simulator bugs surfaced by adversarial seed play

During the first eval run (N=3), `gpt-4o` repeatedly passed `"digest_001"` as `vector_fragment_id` to the `ligate` tool — a reasonable misunderstanding (digest_id vs. output fragment_id). The tool raised an uncaught `ValueError`, killing all three `gpt-4o × clone_01` samples.

**Fix 1 committed**: `_resolve_ligation_fragment_id()` in [src/environment/operations.py](../src/environment/operations.py) now accepts `digest_NNN` or a numeric suffix and returns the output fragment transparently — same pattern as the existing `_resolve_pcr_reaction_id()` helper from Phase 2.

During the second run (N=5, adding sonnet), a *different* failure mode appeared: when the first digest used an incompatible buffer, it produced no output fragments, and the agent then passed the (valid) digest_id forward to `ligate`. The resolver hit an empty `output_fragment_ids` list and the ValueError once again killed the cell. 

**Fix 2 committed**: the tool layer now wraps the cloning and screening tool calls in try/except blocks that convert `ValueError` into a structured error observation (`{"status": "tool_error", "tool_name": ..., "message": ...}`). The agent sees the error as a normal tool result and can recover — a single bad argument no longer wastes 4 / 5 samples in a cell.

This is the most valuable thing an agent eval does: **it finds latent bugs in the surrounding infrastructure that a deterministic unit test would never hit**, because real agents explore the API surface in ways hand-written tests don't.

## Seed-level stability at N = 5

Standard deviations tell you how noisy the stochastic environment is under a fixed (model, task). Average σ across all 20 cells:

| Axis | Avg σ | Interpretation |
|---|---:|---|
| `task_success` | 0.27 | Binary-ish per sample; one seed flipping changes the mean by 0.20 at N = 5 |
| `decision_quality` | 0.06 | Decisions are reproducible (same prompt → same choice) |
| `troubleshooting` | 0.05 | Deterministic within provider (all 0 or all 1 for most cells) |
| `efficiency` | 0.14 | Bimodal: agents either hit the optimal call budget or drift into the reasonable budget |
| `overall` | 0.12 | Aggregates average out |

Going from N=3 → N=5 moved `claude-haiku-4-5` overall from 0.815 to 0.856 (+0.04), and `gpt-4o` from 0.777 to 0.743 (-0.03). The N=3 values were within the resulting stddev envelope — i.e., the earlier rankings held up under resampling.

## Methodological notes

- **Sample IDs embed the seed**: `transform_01_seeded_seed_02` etc. The state's RNG is seeded from `stable_seed_from_sample(sample_id)` (SHA-256 of the ID), so identical IDs reproduce bit-for-bit. Running with `-T seeds=N` expands to N distinct IDs → N distinct seeds.
- **The judge is the deterministic trajectory scorer** in [src/trajectory_scorer.py](../src/trajectory_scorer.py), not an LLM-as-judge. Most decision points are exact-match on tool arguments (enzyme name, buffer, temperature, molar ratio), so scoring is reproducible and auditable. Two of the four axes (task_success, troubleshooting) parse the final answer with regex, which is more brittle but still deterministic.
- **Cost**: ~$0.70 total for 45 runs (mix of gpt-4o-mini, gpt-4o, claude-haiku-4-5). Per-run cost is dominated by prompt-caching efficiency; runs with higher cache-read counts are effectively sub-cent.

## Ablation: is the OpenAI growth_01 troubleshooting gap prompt-sensitivity or model behaviour?

The baseline finding was striking but unfalsified: OpenAI models scored troubleshooting = 0.00 on all 10 `growth_01` seeds; Anthropic scored 1.00 on all 10. Was this a genuine model-level gap, or an artefact of the baseline prompt not *asking* explicitly enough for troubleshooting discussion?

To test this, I added a single prompt variant to [src/tasks/growth_01.py](../src/tasks/growth_01.py) that explicitly instructs the agent to surface any `insufficient_points` result in the final answer, and re-ran 5 seeds per OpenAI model. The baseline prompt remains the default; the variant is selected via the `LABCRAFT_GROWTH_PROMPT_VARIANT=verbose_troubleshoot` environment variable (see [results/ablation_growth_verbose.md](ablation_growth_verbose.md) for the variant's raw results).

### Variant prompt (the only change)

Added to the final-answer instructions:

> *IMPORTANT: if any of the fit_growth_curve calls returned status `"insufficient_points"` or warned that not enough OD600 measurements were in the usable fitting range, you must briefly explain which condition was affected and that the fit was undersampled before giving the final ranking.*

### Results

| Model | Prompt | task_success | decision_quality | **troubleshooting** | efficiency | overall |
|---|---|---:|---:|---:|---:|---:|
| `gpt-4o-mini` | baseline | **0.80** | 0.47 | 0.00 | 1.00 | 0.560 |
| `gpt-4o-mini` | verbose | 0.20 | 0.67 | **1.00** | 1.00 | 0.580 |
| `gpt-4o` | baseline | **0.80** | 0.53 | 0.00 | 1.00 | 0.580 |
| `gpt-4o` | verbose | 0.40 | 0.60 | **0.60** | 1.00 | 0.560 |

### What this tells us

1. **The gap was partially prompt-sensitive.** `gpt-4o-mini` went from 0/5 to **5/5** on troubleshooting with a single added sentence. `gpt-4o` went from 0/5 to 3/5. The "deterministic provider split" claim from the baseline analysis is therefore **too strong** — some of the split was the OpenAI models failing to surface an issue they *could* recognise if asked.
2. **But the gap was also partially model-level.** `gpt-4o` still misses the troubleshooting prompt on 2/5 seeds *even when explicitly told* to report it, whereas both Anthropic models hit 1.0 on the baseline prompt without the hint. Claude models *volunteer* this discussion; GPT models only surface it when explicitly prompted, and gpt-4o doesn't even do it reliably then.
3. **Prompt sensitivity introduces a tradeoff, not a free win.** Task-success dropped from 0.80 to 0.20 – 0.40 across both OpenAI models under the verbose prompt. The agents spent enough extra tokens discussing the fit warnings that they either ran out of message budget before reporting all three doubling times correctly, or they garbled the final-answer schema. Overall score is therefore ~unchanged (mini 0.560 → 0.580; gpt-4o 0.580 → 0.560). **Moving one axis moved the other.**

### Implications

- The honest framing is: *Anthropic models volunteer troubleshooting discussion under the default prompt; OpenAI models require explicit scaffolding, and even with scaffolding gpt-4o is unreliable*. This is a more defensible finding than "provider-level deterministic split".
- Prompt engineering for single axes in multi-axis rubrics can be actively harmful. Any future prompt iteration should look at composite scores, not just the axis being targeted.
- Closing the trouble axis for OpenAI requires either a longer message budget (so the verbose discussion doesn't crowd out task output) or a final-answer template that separates `DOUBLING_TIMES:` from `NOTES:` sections so the task_success parser isn't competing with the troubleshooting narrative.

## Appendix: newer-task frontier extension

The analysis above remains about the published April 2026 five-task snapshot only. Separately, I ran a newer-task cross-provider bundle on `golden_gate_01`, `gibson_01`, `miniprep_01`, `express_01`, and `purify_01`, first at 3 seeds and then as a 5-seed extension using the new `seed_start` task parameter so that seeds `03`-`04` could be added without rerunning seeds `00`-`02`.

See [current_frontier_5seed.md](current_frontier_5seed.md) and [current_frontier_5seed_results.md](current_frontier_5seed_results.md) for the full artifact set. This section is an appendix because those results are intentionally not merged into the frozen portfolio scorecard above.

### 5-seed newer-task summary

| Model | Mean across newer tasks | Non-perfect cells |
|---|---:|---|
| `gpt-4o-mini` | **1.000** | none |
| `gpt-4o` | 0.996 | `gibson_01` = 0.980 (efficiency 0.800) |
| `claude-haiku-4-5` | 0.976 | `golden_gate_01` = 0.910, `gibson_01` = 0.970 |
| `claude-sonnet-4-5` | **1.000** | none |

### What the extra seeds changed

The earlier 3-seed frontier slice looked nearly saturated across all four models, with only small efficiency differences on the assembly tasks. The 5-seed extension changed that story in one important way: it showed that `claude-haiku-4-5` is not just slightly less efficient on the assembly tasks, but less stable in final quantitative reporting on `golden_gate_01`.

On `golden_gate_01` seed `04`, `claude-haiku-4-5` made the correct experimental decisions:

- BsaI as the Type IIS enzyme
- T4 DNA ligase
- 37 C / 16 C cycling
- at least 25 cycles
- all four fragments

So `decision_quality = 1.0`, `troubleshooting = 1.0`, and `efficiency = 1.0`. But the agent saw a low-count plate, back-calculated that to `80` transformants in the final answer, and the deterministic scorer marked `task_success = 0.0`. That single sample drove the 5-seed `golden_gate_01` cell down to:

- `overall = 0.910 ± 0.175`
- `task_success = 0.800 ± 0.447`
- `efficiency = 0.900 ± 0.224`

This is a useful contrast with `gpt-4o`, whose remaining non-perfect newer-task cell is still only an efficiency issue (`gibson_01` = 0.980 with `task_success = 1.0` across all 5 seeds).

### Interpretation

The 5-seed newer-task slice sharpens the model ranking:

1. `gpt-4o-mini` and `claude-sonnet-4-5` now look genuinely stable on this task family, not just lucky over three seeds.
2. `gpt-4o` still appears highly reliable, with its only residual gap on `gibson_01` efficiency.
3. `claude-haiku-4-5` is the one model where the extra seeds changed the qualitative interpretation: the assembly-task variance is not just wasted tool calls, but also a real final-answer correctness miss.

### Method note

This extension also validated the repo's incremental-seed workflow. [src/inspect_task.py](../src/inspect_task.py) now supports `seed_start`, and [scripts/run_portfolio_eval.sh](../scripts/run_portfolio_eval.sh) threads that through to Inspect. That makes it possible to extend an existing multi-seed bundle without duplicating earlier seeds or contaminating the aggregate with repeated sample IDs.

## What a larger evaluation would add

Items 1, 2, and 4 from the original analysis are now done for the frozen snapshot (N=5, sonnet added, prompt ablation run above). For the newer-task frontier slice, a separate 5-seed extension is now also complete. Remaining open directions:

1. **Raise N further to 10 – 20 seeds** on the two discriminating tasks (`transform_01` and `growth_01`) to tighten the task_success stddev from ~0.45 down to ~0.20 — enough to publish confidence intervals.
2. **Ablate the `efficiency` axis**. It has the second-loudest signal on some cells (haiku transform_01 efficiency = 0.10, sonnet transform_01 efficiency = 0.00) but correlates weakly with task success. Worth measuring whether it's capturing real waste or just message-limit artifacts.
3. **Per-axis radar per (model, task)** for reviewer readability — the current flat-table view hides which axis drives each model gap.
4. **Structured final-answer template for `growth_01`** to see if splitting doubling-time reporting from troubleshooting narrative eliminates the axis tradeoff uncovered in the ablation above.
