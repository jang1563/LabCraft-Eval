# Model Refresh Status — 2026-07-11

This is a compatibility and infrastructure checkpoint, not a model-quality
result. Early runs below used an intentionally dirty implementation checkout;
only sections explicitly labeled as clean-revision verification satisfy the
current provenance gate.

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
- `transform_01` uses the same separate 40-turn/160-message protection and
  scores conditions from cultures that produced usable downstream counts
- `clone_01` scores successful digest/ligation conditions, credits corrected
  retries as troubleshooting, and verifies successful reactions and reported
  transformant counts against the trajectory

## Cayuga verification

The implementation was copied to an isolated Cayuga scratch checkout before
verification. Site-specific paths and scheduler identifiers are omitted because
they do not affect reproduction; immutable code revisions and check outcomes
are recorded below.

Environment setup completed successfully. The final check passed 458 tests,
Ruff, shell syntax, registry validation, wheel
build, isolated wheel installation, Inspect entry-point import, and GPT-5.6
metadata registration.

The compatibility array ran `growth_01`, seed 0, serially across the four
current-core models. All four providers returned the expected resolved model
ID with the registered `{max_tokens: 16384, reasoning_effort: medium}` profile
and Inspect 0.3.245:

| Requested model | Resolved model | Current cell status |
|---|---|---|
| `openai/gpt-5.6-sol` | `gpt-5.6-sol` | Valid |
| `openai/gpt-5.6-luna` | `gpt-5.6-luna` | Valid |
| `anthropic/claude-sonnet-5` | `claude-sonnet-5` | Valid |
| `anthropic/claude-haiku-4-5-20251001` | `claude-haiku-4-5-20251001` | Compatible; original run incomplete |

The Haiku retry recorded `--message-limit 120` in its cell manifest
but again exhausted the message limit. The strengthened validator rejected the
cell. Trajectory inspection showed that this was not a repeated-call loop: the
model completed a reasonable 30-minute pilot, diagnosed one undersampled fit,
reran at 20-minute cadence, and issued the final three fit calls immediately
before the message-only limit terminated the sample. Inspect counts each
parallel tool result as a separate message, so raising only that limit did not
address the task-contract problem.

After aligning the non-answer-bearing prompt and scorer, the Haiku compatibility
smoke completed in 63 seconds and passed the strict cell validator. It used
59 messages, 15 assistant turns, and 42 tool calls: all three cultures started
at OD600 0.05, every incubation used a 15-minute interval, and all three final
fits were analyzable. Re-scoring that transcript with the final consistency
rule produced 1.0 on task success, decision quality, troubleshooting, and
efficiency. This is a single compatibility smoke from a dirty checkout, not a
model-quality estimate.

The final contract check passed 462 tests, Ruff, shell syntax,
registry validation, wheel build, isolated installation, and package smoke in
the pinned Cayuga environment.

## Clean revision verification

The first clean-checkout array exposed two remaining scorer false
negatives: colon-only final-answer parsing rejected dash-formatted reports, and
the OD600 lower bound rejected scientifically defensible 0.01 and 0.02 starts.
The original logs remain unchanged. Replaying their trajectories after the
source-backed OD600 0.01-0.10 correction and colon/dash/Markdown-table parser
fix produced 1.0 on all four axes for all four models.

During the next clean run, source-path inspection found that the reused virtual
environment was editable-installed from an older checkout. That array was
cancelled and is invalid for release use. The runner now prefixes the submitted
checkout on `PYTHONPATH`, fails before any API call when the imported `src` root
does not match `REPO_ROOT`, and records that root in cell manifest schema 1.2.0.

Final code revision `557194792520d27e64c545bed127402061fb9d0c` was copied to a
fresh isolated checkout. The isolated check passed 467 tests, Ruff, shell
syntax, registry validation, wheel build, isolated installation, and package
smoke. The compatibility array then completed `growth_01`, seed 0, serially
across the four current
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

## Non-growth sentinel verification

The next gate used `pcr_01` and `screen_01`, seed 0, across the same four-model
matrix. The initial clean array exposed a screen-parser false negative:
three models listed six explicit colony IDs, but the parser read the numeric
suffix of `white_001` as a total count of one. The source trajectories were
correct and remain unchanged. Commit `35b8221d6f7dc856e6f49659575166baf6938aaf`
fixed ID-list counting; the post-fix check passed 468 tests and the clean array
stored full-success screen scores:

| Screen model | Messages | Assistant turns | Tool calls | Task | Decision | Troubleshooting | Efficiency | Overall |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `openai/gpt-5.6-sol` | 7 | 3 | 2 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| `openai/gpt-5.6-luna` | 7 | 3 | 2 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| `anthropic/claude-sonnet-5` | 7 | 3 | 2 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| `anthropic/claude-haiku-4-5-20251001` | 9 | 4 | 3 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |

PCR audit found that common Q5 labels normalized to canonical Q5 in the output
but could still receive unsupported-polymerase simulator behavior. Commit
`cbbebbd128bbf2fde99de1e57507018d72abf9ce` canonicalized Q5 and Phusion before
simulation; the post-fix check passed 472 tests and the clean PCR array
completed cleanly. A final scorer audit then prevented favorable parameters
from unrelated failed attempts being combined into decision credit: commit
`5229e270297357a7a6adbed3b6aec5a77bcc62d9` restricts PCR decision matching to
`clean_target_band` reactions, and the final check passed 473 tests.

Replaying the clean PCR trajectories under that final scorer contract
produced:

| PCR model | Messages | Assistant turns | Tool calls | Task | Decision | Troubleshooting | Efficiency | Overall |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `openai/gpt-5.6-sol` | 26 | 9 | 15 | 1.000 | 0.750 | 1.000 | 0.000 | 0.825 |
| `openai/gpt-5.6-luna` | 22 | 8 | 12 | 1.000 | 1.000 | 1.000 | 0.000 | 0.900 |
| `anthropic/claude-sonnet-5` | 13 | 5 | 6 | 1.000 | 1.000 | 1.000 | 0.500 | 0.950 |
| `anthropic/claude-haiku-4-5-20251001` | 17 | 6 | 9 | 1.000 | 1.000 | 1.000 | 0.000 | 0.900 |

Sol's PCR decision score is a legitimate protocol-choice difference: its
successful reaction used a 75-second extension, outside the cited 40-60 second
range. All eight retained screen/PCR cells passed requested/resolved model,
generation profile, clean worktree, schema 1.2.0, runtime-source-root, and
no-limit-exhaustion gates. These remain one-seed sentinel runs, and neither the
initial parser-diagnostic rows nor frozen historical artifacts were rewritten.

## Remaining snapshot sentinel verification

The first `transform_01` / `clone_01` array at clean revision
`50f5cdd72e903745fb07d7c1357a69c1ae430ca6` exposed four contract issues while
leaving the source logs unchanged: a 40-message-only transform cap terminated a
valid batched run; successful dilution, digest, and ligation retries were mixed
with failed attempts for decision scoring; reagent filters treated
`Ampicillin` and `ampicillin` differently; and clone task success did not verify
successful reactions or the reported transformant count.

Commit `9a60771a0d1f8c9d72901ddacf065df91f848a3b` separated the transform
turn/message limits, restricted decision scoring to usable final workflows,
made string filters case-insensitive, credited trajectory-resolved clone
failures, and strengthened clone task-success reconstruction. Its clean
diagnostic array then exposed two report-shape false negatives:
Unicode superscript exponents such as `10⁹` were not parsed, and a valid sum of
two same-culture, same-dilution plates was compared only with the largest
individual plate count. Commit `5168651364ad29529c14b9275b04f794a340f15f`
accepts those forms while continuing to reject raw-count sums across different
dilutions.

One infrastructure retry was also required. The shared Cayuga environment had
drifted to Inspect 0.3.222, so the pinned metadata check failed and the
evaluation array was cancelled. A new immutable environment restored Inspect
0.3.245, OpenAI 2.45.0, and Anthropic 0.116.0. The cancelled bundle is
diagnostic-only and must not be aggregated.

Final revision `5168651364ad29529c14b9275b04f794a340f15f` was copied to a fresh
isolated checkout. The final check passed 484 tests, Ruff, shell syntax,
registry validation, wheel build, isolated installation, and package smoke.
The final serial array used RUN_ID
`2026_07_12_snapshot_remaining_final_5168651`:

| Task | Model | Messages | Assistant turns | Tool calls | Task | Decision | Troubleshooting | Efficiency | Overall |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `transform_01` | `openai/gpt-5.6-sol` | 33 | 8 | 23 | 1.000 | 1.000 | 1.000 | 0.500 | 0.950 |
| `transform_01` | `openai/gpt-5.6-luna` | 47 | 10 | 35 | 1.000 | 0.667 | 1.000 | 0.000 | 0.800 |
| `transform_01` | `anthropic/claude-sonnet-5` | 41 | 9 | 30 | 1.000 | 0.833 | 1.000 | 0.000 | 0.850 |
| `transform_01` | `anthropic/claude-haiku-4-5-20251001` | 24 | 5 | 17 | 0.000 | 0.500 | 1.000 | 0.500 | 0.400 |
| `clone_01` | `openai/gpt-5.6-sol` | 44 | 17 | 25 | 1.000 | 1.000 | 1.000 | 0.000 | 0.900 |
| `clone_01` | `openai/gpt-5.6-luna` | 27 | 11 | 14 | 1.000 | 1.000 | 1.000 | 0.500 | 0.950 |
| `clone_01` | `anthropic/claude-sonnet-5` | 28 | 11 | 15 | 1.000 | 1.000 | 1.000 | 0.500 | 0.950 |
| `clone_01` | `anthropic/claude-haiku-4-5-20251001` | 29 | 13 | 14 | 1.000 | 1.000 | 1.000 | 0.500 | 0.950 |

Haiku's transform task failure is substantive rather than parser-related. Only
one count observation reached `status=plated`; the remaining observations were
outside the cited 25-250 range, so the trajectory never produced a valid
four-mass measurement set. All eight final cells passed requested/resolved
model, generation profile, clean worktree, schema 1.2.0, exact runtime source,
Inspect-version, and no-limit-exhaustion gates.

## Scale decision

All five snapshot tasks now have a strict one-seed sentinel across the four
current-core models. These runs validate compatibility and scorer contracts;
they are not comparative quality estimates. Human-baseline and multi-seed work
remain intentionally skipped. The next bounded gate should use the same
four-model, seed-zero protocol on the newer current wet-lab tasks, while frozen
historical results and every cancelled or diagnostic bundle remain excluded
from promoted aggregates.
