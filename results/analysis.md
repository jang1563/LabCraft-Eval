# LabCraft-Eval Evaluation — Analysis

100 scored sample rows across 5 tasks × 4 frontier models × 5 seed-labelled repetitions, April 2026.
This document analyzes the frozen April 2026 portfolio snapshot only: `transform_01`, `growth_01`, `pcr_01`, `screen_01`, and `clone_01`. The repo now implements additional tasks, including `golden_gate_01`, `gibson_01`, `miniprep_01`, `express_01`, and `purify_01`, but those are not part of the headline tables below. A separate appendix near the end summarizes the newer-task 5-repeat frontier extension without merging it into the frozen snapshot. The repo also now includes a human-baseline workflow and pilot reporting for `transform_01` and `growth_01`, but no completed expert sessions are analyzed in this document yet.
Raw scores: [results.md](results.md). Raw trajectories: [logs/](logs/).

> **Historical/provisional evidence:** these tables preserve the published
> v0.1.1 scorer outputs and have not been rewritten or retroactively rescored.
> The frozen logs record dirty native evaluation revisions and do not fully pin
> model generation settings, so they cannot establish exact code-level
> reproducibility or attribute repeat-to-repeat variance solely to the
> simulator. Several historical agent-facing prompts and tool descriptions also
> supplied choices that the scorer rewarded; those hints have since been
> removed. Treat the results as benchmark-development evidence tied to that
> pre-remediation contract, not a validated model or provider ranking.

## Headline

The frozen table spans mean overall scores of **0.44 – 1.00** across the (model, task) grid. In this particular prompt/scorer snapshot, both Anthropic model means are ~0.85 and both OpenAI model means are ~0.74; no inferential comparison was performed.

| Model | Mean-across-tasks | Strongest task | Weakest task |
|---|---:|---|---|
| `claude-haiku-4-5` | **0.856** | `screen_01` (1.00) | `transform_01` (0.50) |
| `claude-sonnet-4-5` | 0.852 | `screen_01` (1.00) | `transform_01` (0.48) |
| `gpt-4o-mini` | 0.744 | `pcr_01` (0.97) | `growth_01` (0.56) |
| `gpt-4o` | 0.743 | `pcr_01` (0.95) | `transform_01` (0.44) |

Two findings the evaluation made visible that a single-model smoke would have hidden:

1. **`sonnet` and `haiku` have nearly equal descriptive means** on these five tasks (0.852 vs. 0.856). No confidence interval, hypothesis test, equivalence margin, or power analysis was defined, so the snapshot supports neither a difference nor an equivalence or price-performance conclusion.
2. **The largest observed cluster difference is concentrated in one axis.** On `growth_01`, the Anthropic model means are 0.89 overall and the OpenAI model means are 0.57. Under the baseline prompt, the ten OpenAI runs score troubleshooting = 0.00 and the ten Anthropic runs score 1.00. The later ablation shows this pattern is prompt-sensitive, so it should not be read as a provider-level capability result.

## Task difficulty ranking

Per-task mean overall across all four models:

| Task | Mean overall | Comment |
|---|---:|---|
| `pcr_01` | **0.955** | Saturated. All four models pick Q5 + DMSO + 60 s extension + 32 cycles and interpret the clean target band identically. |
| `screen_01` | 0.935 | Saturated for Anthropic (1.00 × 10/10); OpenAI models occasionally drop the `Confidence achieved:` final-answer field (task_success = 0 on 2/10 runs). |
| `clone_01` | 0.879 | Mostly saturated. Failure mode concentrated in `gpt-4o-mini` (0.72), where 2/5 repetitions skipped the troubleshooting language when the ligation yielded few transformants. |
| `growth_01` | 0.728 | Task-success nearly perfect (doubling times correct on 16/20), but OpenAI models score **0.00 on troubleshooting in all 10 runs**; Anthropic catches it every time. |
| `transform_01` | **0.498** | The compound-requirement task. Across 20 runs, only **2 cleared every gate**: haiku seed 02 and sonnet seed 00. Both produced biologically plausible ~10⁹ CFU/µg values. |

## The three most informative failure modes

### 1. `transform_01`: compound requirements are brittle

To score `task_success = 1.0`, an agent must:
1. Transform all four DNA masses (10 pg / 100 pg / 1 ng / 10 ng)
2. Choose dilutions that land each plate in the 25 – 250 colony "countable" range
3. Report CFU/µg for all four
4. Assert internal consistency

Observed behaviors across 20 stored repetitions (4 models × 5 repetitions):

| Pattern | Count | Notes |
|---|---:|---|
| Dilutions wrong on 1+ plates → "out of range" counts | 9 | dominant failure mode across all models |
| Reported only 2–3 of 4 masses | 6 | common when agents hit message_limit mid-analysis |
| Hit `message_limit` before finishing | 3 | haiku/sonnet prone to this on this task |
| Fully correct (passes task_success scorer) | **2** | haiku seed 02, sonnet seed 00 |

Task success by model: `gpt-4o-mini` 0/5, `gpt-4o` 0/5, `haiku` 1/5, `sonnet` 1/5.

This pattern shows sensitivity to a compound reporting contract, but it does not establish real wet-lab execution reliability or prove that the underlying chemistry was understood. For the two runs that cleared the historical scorer, the reported CFU/µg values were 4 – 6 × 10⁹, which is biologically plausible for chemically competent DH5α. The dominant observed failures were tool-use and final-report omissions.

### 2. `growth_01`: the troubleshooting axis catches an OpenAI blind spot

Every model determines the three doubling times correctly on most repetitions (task_success = 0.80 mean). Under the historical baseline prompt, the **troubleshooting axis** separates as follows:

- `gpt-4o` : **0.00** on all 5 repetitions
- `gpt-4o-mini` : **0.00** on all 5 repetitions
- `claude-haiku-4-5` : **1.00** on all 5 repetitions
- `claude-sonnet-4-5` : **1.00** on all 5 repetitions

The scorer flags a troubleshooting-relevant event when one growth-curve fit requires an explicit explanation of the late-time-course dilution issue. In these stored baseline runs, the Claude responses include that explanation and the GPT responses do not. The prompt ablation below changes the OpenAI scores, so this is a prompt- and scorer-conditioned historical observation rather than a provider-level inference.

### 3. `clone_01`: two latent simulator bugs surfaced by repeated agent exploration

During the first eval run (N=3), `gpt-4o` repeatedly passed `"digest_001"` as `vector_fragment_id` to the `ligate` tool — a reasonable misunderstanding (digest_id vs. output fragment_id). The tool raised an uncaught `ValueError`, killing all three `gpt-4o × clone_01` samples.

**Fix 1 committed**: `_resolve_ligation_fragment_id()` in [src/environment/operations.py](../src/environment/operations.py) now accepts `digest_NNN` or a numeric suffix and returns the output fragment transparently — same pattern as the existing `_resolve_pcr_reaction_id()` helper from Phase 2.

During the second run (N=5, adding sonnet), a *different* failure mode appeared: when the first digest used an incompatible buffer, it produced no output fragments, and the agent then passed the (valid) digest_id forward to `ligate`. The resolver hit an empty `output_fragment_ids` list and the ValueError once again killed the cell. 

**Fix 2 committed**: the tool layer now wraps the cloning and screening tool calls in try/except blocks that convert `ValueError` into a structured error observation (`{"status": "tool_error", "tool_name": ..., "message": ...}`). The agent sees the error as a normal tool result and can recover — a single bad argument no longer wastes 4 / 5 samples in a cell.

This run usefully found latent bugs in the surrounding infrastructure because agent traces exercised API paths that the then-existing hand-written tests had not covered.

## Repeat-level variability at N = 5

These standard deviations describe variability across stored model runs with different seed-labelled sample IDs. They combine model-output variation, final-answer formatting, message-budget effects, and task-dependent environment changes; the historical logs do not support assigning the variance to environmental stochasticity alone. Average σ across all 20 cells:

| Axis | Avg σ | Interpretation |
|---|---:|---|
| `task_success` | 0.27 | Binary-ish per sample; one seed flipping changes the mean by 0.20 at N = 5 |
| `decision_quality` | 0.06 | Decisions varied little in this stored run set |
| `troubleshooting` | 0.05 | Mostly all 0 or all 1 within each historical cell |
| `efficiency` | 0.14 | Bimodal: agents either hit the optimal call budget or drift into the reasonable budget |
| `overall` | 0.12 | Aggregates average out |

Going from N=3 → N=5 moved `claude-haiku-4-5` overall from 0.815 to 0.856 (+0.04), and `gpt-4o` from 0.777 to 0.743 (-0.03). This describes the stored extension only; it is not a bootstrap, independent resampling study, or statistical ranking test.

## Methodological notes

- **Historical and current seed semantics differ**: the frozen logs used sample-ID-derived simulator seeds. The current runner passes the integer `seed_index` explicitly. Identical visible labels therefore do not recreate the historical environment under current code. Even within one convention, seed labels do not guarantee bit-identical model generations, and many task operations are deterministic across labels.
- **The judge is the deterministic hard-coded trajectory scorer** in [src/trajectory_scorer.py](../src/trajectory_scorer.py), not an LLM-as-judge and not the checked-in JSON rubric tree. Most decision points match tool arguments; task-success and troubleshooting also parse the final answer with regex. A fixed transcript can therefore be rescored deterministically, while a full model rerun is not guaranteed to reproduce the same trajectory.
- **Cost**: ~$0.70 total for 45 runs (mix of gpt-4o-mini, gpt-4o, claude-haiku-4-5). Per-run cost is dominated by prompt-caching efficiency; runs with higher cache-read counts are effectively sub-cent.

## Ablation: is the OpenAI growth_01 troubleshooting gap prompt-sensitivity or model behaviour?

The baseline finding was striking but unfalsified: OpenAI models scored troubleshooting = 0.00 on all 10 stored `growth_01` repetitions; Anthropic scored 1.00 on all 10. Was this a genuine model-level gap, or an artefact of the baseline prompt not *asking* explicitly enough for troubleshooting discussion?

To test this, I added a single prompt variant to [src/tasks/growth_01.py](../src/tasks/growth_01.py) that explicitly instructs the agent to surface any `insufficient_points` result in the final answer, and collected 5 additional seed-labelled repetitions per OpenAI model. The baseline prompt remains the default; the variant is selected via the `LABCRAFT_GROWTH_PROMPT_VARIANT=verbose_troubleshoot` environment variable (see [results/ablation_growth_verbose.md](ablation_growth_verbose.md) for the variant's raw results).

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
2. **A residual difference remains in this one ablation.** `gpt-4o` misses the troubleshooting field on 2/5 verbose-prompt runs, whereas the stored Anthropic baseline responses include it. One prompt variant and five repetitions are insufficient to attribute that residual to a general model- or provider-level property.
3. **The prompt change coincides with an axis tradeoff.** Task-success drops from 0.80 to 0.20 – 0.40 across the two OpenAI cells under the verbose prompt. The stored responses show longer troubleshooting discussion alongside omitted or malformed doubling-time reports. Overall score is therefore approximately unchanged (mini 0.560 → 0.580; gpt-4o 0.580 → 0.560).

### Implications

- The defensible framing is: *the stored Anthropic responses volunteer troubleshooting discussion under the default prompt; the stored OpenAI responses improve on that field under explicit scaffolding*. Broader provider claims require more prompts, pinned generation settings, and a predeclared analysis.
- Prompt engineering for one axis can move another axis in the same small evaluation. Future prompt studies should inspect every axis rather than only the targeted one.
- Closing the trouble axis for OpenAI requires either a longer message budget (so the verbose discussion doesn't crowd out task output) or a final-answer template that separates `DOUBLING_TIMES:` from `NOTES:` sections so the task_success parser isn't competing with the troubleshooting narrative.

## Appendix: newer-task frontier extension

The analysis above remains about the published April 2026 five-task snapshot only. Separately, I ran a newer-task cross-provider bundle on `golden_gate_01`, `gibson_01`, `miniprep_01`, `express_01`, and `purify_01`, first at 3 repetitions and then as a 5-repeat extension using the `seed_start` task parameter so that labels `03`-`04` could be added without rerunning labels `00`-`02`.

See [current_frontier_5seed.md](current_frontier_5seed.md) and [current_frontier_5seed_results.md](current_frontier_5seed_results.md) for the full artifact set. This section is an appendix because those results are intentionally not merged into the frozen portfolio scorecard above.

### 5-repeat newer-task summary

| Model | Mean across newer tasks | Non-perfect cells |
|---|---:|---|
| `gpt-4o-mini` | **1.000** | none |
| `gpt-4o` | 0.996 | `gibson_01` = 0.980 (efficiency 0.800) |
| `claude-haiku-4-5` | 0.976 | `golden_gate_01` = 0.910, `gibson_01` = 0.970 |
| `claude-sonnet-4-5` | **1.000** | none |

### What the extra repetitions changed

The earlier 3-repeat frontier slice was nearly saturated across all four models, with only small efficiency differences on the assembly tasks. In the 5-repeat extension, one additional `claude-haiku-4-5` `golden_gate_01` response missed the final quantitative report despite correct recorded decisions.

On `golden_gate_01` seed `04`, `claude-haiku-4-5` made the correct experimental decisions:

- BsaI as the Type IIS enzyme
- T4 DNA ligase
- 37 C / 16 C cycling
- at least 25 cycles
- all four fragments

So `decision_quality = 1.0`, `troubleshooting = 1.0`, and `efficiency = 1.0`. But the agent saw a low-count plate, back-calculated that to `80` transformants in the final answer, and the deterministic scorer marked `task_success = 0.0`. That single sample drove the five-repeat `golden_gate_01` cell down to:

- `overall = 0.910 ± 0.175`
- `task_success = 0.800 ± 0.447`
- `efficiency = 0.900 ± 0.224`

This is a descriptive contrast with `gpt-4o`, whose remaining non-perfect newer-task cell is an efficiency issue (`gibson_01` = 0.980 with `task_success = 1.0` across all 5 stored repetitions).

### Interpretation

Descriptively, the 5-repeat newer-task slice shows:

1. No scorer miss in the five stored `gpt-4o-mini` or `claude-sonnet-4-5` repetitions for these tasks.
2. One `gpt-4o` efficiency penalty on `gibson_01`.
3. One additional `claude-haiku-4-5` final-answer miss on `golden_gate_01`.

This sample is too small and too close to saturation to establish comparative reliability.

### Method note

This extension exercised the repo's incremental seed-label workflow. [src/inspect_task.py](../src/inspect_task.py) supports `seed_start`, and [scripts/run_portfolio_eval.sh](../scripts/run_portfolio_eval.sh) threads that through to Inspect. That makes it possible to extend a bundle without duplicating earlier sample IDs; it does not make deterministic task operations stochastic.

## What a larger evaluation would add

Items 1, 2, and 4 from the original analysis are now done for the frozen snapshot (N=5, sonnet added, prompt ablation run above). For the newer-task frontier slice, a separate five-repeat extension is also stored. Remaining open directions:

1. **Run a clean, predeclared N=10–20 repetition study** on selected tasks, with pinned model generation settings, separate environment and model-replicate factors, and confidence intervals chosen before inspecting the results.
2. **Ablate the `efficiency` axis**. It has the second-loudest signal on some cells (haiku transform_01 efficiency = 0.10, sonnet transform_01 efficiency = 0.00) but correlates weakly with task success. Worth measuring whether it's capturing real waste or just message-limit artifacts.
3. **Per-axis radar per (model, task)** for reviewer readability — the current flat-table view hides which axis drives each model gap.
4. **Structured final-answer template for `growth_01`** to see if splitting doubling-time reporting from troubleshooting narrative eliminates the axis tradeoff uncovered in the ablation above.
