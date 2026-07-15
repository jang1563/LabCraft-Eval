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
current-core models. All four models returned the expected resolved model
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

## Initial newer-task P1 diagnostic

P1 began with `golden_gate_01` only, following the one-task-at-a-time gate.
Revision `b20382a7c473bd73e9707e288fa7fd8b4a3732a1` was transferred as an exact
git bundle to a fresh detached checkout. The isolated preflight passed 507
tests, Ruff, shell syntax, registry validation, lock validation, wheel build,
isolated installation, and package smoke. The pinned environment used Inspect
0.3.245, OpenAI 2.45.0, and Anthropic 0.116.0.

The serial four-model array used RUN_ID
`2026_07_15_p1_golden_gate_seed0_b20382a` and the registered
`current_balanced` generation profile (`max_tokens=16384`,
`reasoning_effort=medium`):

| Model | Messages | Assistant turns | Tool calls | Task | Decision | Troubleshooting | Efficiency | Overall |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `openai/gpt-5.6-sol` | 24 | 9 | 13 | 1.000 | 1.000 | 1.000 | 0.500 | 0.950 |
| `openai/gpt-5.6-luna` | 23 | 9 | 12 | 1.000 | 1.000 | 1.000 | 0.500 | 0.950 |
| `anthropic/claude-sonnet-5` | 17 | 7 | 8 | 1.000 | 1.000 | 1.000 | 0.500 | 0.950 |
| `anthropic/claude-haiku-4-5-20251001` | 31 | 13 | 16 | 1.000 | 0.857 | 1.000 | 0.000 | 0.857 |

All four native logs had `status=success`, one sample with ID
`golden_gate_01_seeded_seed_00`, no error or exhausted limit, and exact
requested/resolved model identity. The independent postflight found exactly
four manifests and four non-empty logs; all manifests recorded schema 1.2.0,
the exact commit above, `worktree_dirty=false`, seed 0, the expected runtime
source, and Inspect 0.3.245. The model-registry SHA-256 was
`41913bf3abee56660dd7b455dc19f9f57d0939304d2a412cea1161837bd2667e`.
All four strict validators passed, and all four scheduler stderr files were
empty. This establishes infrastructure and provenance validity only.

The required semantic audit then reproduced pre-remediation contract defects:
the reference database lacked BsaI/BsmBI entries while presenting 25 C as the
headline T4 ligase condition; BsmBI was accepted for BsaI-flanked substrates;
plate/count could be omitted while reporting zero; final protocol fields were
not bound to the executed assembly; and the six-call full-efficiency budget
left no room for the reference evidence requested by the prompt. The supplied
four-fragment count was also incorrectly treated as an independent decision.

These defects plausibly contributed to Haiku's five enzyme lookups (four of
which returned no entry), 25 C ligation choice, and 16-call threshold crossing.
Therefore none of the four stored scores above is promoted, and no model-quality
interpretation is retained. The remediation makes the task BsaI-specific,
adds exact-ranked enzyme references, uses the cohesive-end 16 C T4 condition,
validates the exact 30-cycle 37 C / 16 C program, an ATP-containing one-pot
buffer, and the 60 C / five-minute terminal digest, requires a causal successful
assembly-to-countable-colony path within the canonical 25-250 range, binds every
reported field to that path, uses a fail-closed success token, and budgets two
reference calls. Because these changes are agent-visible and score-defining, a
fresh four-model clean-revision rerun was mandatory; that rerun is recorded
below.

## Remediated Golden Gate P1 sentinel verification

Revision `f7d5ba5062b69a3b33968d656272626c1870114c` was transferred as a
complete git bundle to a fresh detached checkout. The clean Cayuga preflight
passed 597 tests, Ruff, shell syntax, registry validation, wheel
build, isolated installation, and package smoke under Inspect 0.3.245.

The serial four-cell array used RUN_ID
`2026_07_15_p1_golden_gate_remediated_seed0_f7d5ba5`, seed 0, and the
registered `current_balanced` generation profile (`max_tokens=16384`,
`reasoning_effort=medium`):

| Model | Messages | Assistant turns | Tool calls | Task | Decision | Troubleshooting | Efficiency | Overall |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `openai/gpt-5.6-sol` | 21 | 7 | 12 | 1.000 | 1.000 | 1.000 | 0.500 | 0.950 |
| `openai/gpt-5.6-luna` | 20 | 8 | 10 | 1.000 | 1.000 | 1.000 | 0.500 | 0.950 |
| `anthropic/claude-sonnet-5` | 17 | 7 | 8 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| `anthropic/claude-haiku-4-5-20251001` | 18 | 8 | 8 | 0.000 | 1.000 | 1.000 | 1.000 | 0.600 |

All four cells completed with scheduler exit `0:0` and passed the built-in and
independently repeated strict validators. Independent postflight found exactly
four schema-1.2.0 manifests and four native logs, the exact clean commit and
runtime source, seed 0, Inspect 0.3.245, requested/resolved model identity, the
registered generation profile, and no error or exhausted limit. The registry
SHA-256 remained
`41913bf3abee56660dd7b455dc19f9f57d0939304d2a412cea1161837bd2667e`,
and all four evaluation stderr files were empty.

Semantic audit confirmed one causal, report-matched path for Sol, Luna, and
Sonnet: exact BsaI-family assembly conditions, a produced construct,
transformation, a prepared 100 ug/mL ampicillin plate, an undiluted 100 uL
plating, and 30 countable colonies. Haiku instead plated a 1:10 dilution,
observed three colonies with `status=count_out_of_range`, did not correct or
replate, and submitted `Interpretation: success`. Its task-success zero is
therefore a substantive failure under the repaired contract, not a parser or
scorer false negative.

This accepts `golden_gate_01` as the first completed P1 task: 4/20 cells and
1/5 tasks are contract-validated. These remain one-seed compatibility and
scorer-contract results, not comparative model-ranking evidence.

## Initial Gibson P1 diagnostic

The first hardened `gibson_01` gate used revision
`9afc917bc5366c485e0904f200c5248b0148c77e`, including the exact evaluation
revision validator, in a fresh detached checkout. Its clean Cayuga preflight
passed 715 tests, Ruff, shell syntax, registry validation, wheel build,
isolated installation, and package smoke under Inspect 0.3.245.

The serial array used RUN_ID `2026_07_15_p1_gibson_seed0_9afc917`, seed 0,
and the registered `current_balanced` generation profile. All four scheduler
cells exited `0:0`; the four native logs and four schema-1.2.0 manifests passed
the strict provenance validator with the exact clean revision, runtime source,
requested/resolved model identities, registry hash, and no error or exhausted
limit. All four evaluation stderr files were empty.

The stored task-success score was nevertheless zero in every cell. Semantic
audit found complete, report-matched, countable paths for Sol, Luna, and Sonnet
with 50, 34, and 34 colonies, respectively. Their only rejected field was the
scientifically valid method label `Gibson isothermal overlap assembly`; the
scorer required the exact token `Gibson` despite the prompt requesting a
generic method name. Changing only that label in offline replay changed each
task-success score from zero to one. Haiku's zero remained substantive because
its 3- and 0-colony observations were both outside the canonical countable
range and it did not replate.

The remediation replaces the brittle exact token with a finite allowlist of
canonical Gibson method labels while continuing to reject negated, fuzzy, and
unrelated labels. Because this is score-defining, the entire `9afc917` bundle
remains diagnostic-only and a fresh clean-revision rerun was required.

## Remediated Gibson P1 sentinel verification

Revision `fb6b6dd40d301b5035e6d06fc7e169fa98339c34` was transferred as a
complete bundle to a new detached checkout. The clean Cayuga preflight passed
728 tests, Ruff, shell syntax, registry validation, wheel build, isolated
installation, and package smoke under Inspect 0.3.245.

The serial four-cell array used RUN_ID
`2026_07_15_p1_gibson_remediated_seed0_fb6b6dd`, seed 0, and the registered
`current_balanced` profile (`max_tokens=16384`, `reasoning_effort=medium`):

| Model | Messages | Assistant turns | Tool calls | Task | Decision | Troubleshooting | Efficiency | Overall |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `openai/gpt-5.6-sol` | 20 | 9 | 9 | 1.000 | 1.000 | 1.000 | 0.500 | 0.950 |
| `openai/gpt-5.6-luna` | 17 | 8 | 7 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| `anthropic/claude-sonnet-5` | 14 | 6 | 6 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| `anthropic/claude-haiku-4-5-20251001` | 20 | 9 | 9 | 1.000 | 0.750 | 1.000 | 0.500 | 0.875 |

All four cells exited `0:0` and passed the built-in and independently repeated
strict validators. Independent postflight found exactly four schema-1.2.0
manifests and four native logs, the exact clean commit and runtime source, seed
0, Inspect 0.3.245, requested/resolved model identity, the registered profile,
and no error or exhausted limit. The model-registry SHA-256 remained
`41913bf3abee56660dd7b455dc19f9f57d0939304d2a412cea1161837bd2667e`,
and all four evaluation stderr files were empty.

Semantic audit confirmed one causal, report-matched path per cell: a supported
two-fragment assembly at 50 C for 15-60 minutes, a linked transformation, a
prepared 100 ug/mL ampicillin plate, an undiluted 100 uL plating, and a
countable colony result. Sol and Luna reported 50 colonies; Sonnet and Haiku
reported 34. Haiku first used an unsupported master-mix label, then correctly
reassembled and completed the valid path. Its 0.75 decision score preserves
that initial error, its troubleshooting score credits the correction, and an
unrelated out-of-range dilution plate is not hybridized into the accepted path.

This accepts `gibson_01` as the second completed P1 task: 8/20 cells and 2/5
tasks are contract-validated. These remain one-seed compatibility and
scorer-contract results, not comparative model-ranking evidence.

## Miniprep P1 sentinel verification

Revision `ff47e8aa96a5564fb58700b3eb9db7d54badec43` was transferred as a
complete bundle to a new detached checkout. The clean Cayuga preflight passed
836 tests, Ruff, shell syntax, registry validation, wheel build, isolated
installation, and package smoke under Python 3.13.7, Inspect 0.3.245, OpenAI
2.45.0, and Anthropic 0.116.0.

The serial four-cell array used RUN_ID
`2026_07_15_p1_miniprep_seed0_ff47e8a`, seed 0, and the registered
`current_balanced` profile (`max_tokens=16384`, `reasoning_effort=medium`):

| Model | Messages | Assistant turns | Tool calls | Task | Decision | Troubleshooting | Efficiency | Overall |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `openai/gpt-5.6-sol` | 5 | 2 | 1 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| `openai/gpt-5.6-luna` | 5 | 2 | 1 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| `anthropic/claude-sonnet-5` | 5 | 2 | 1 | 0.000 | 1.000 | 1.000 | 1.000 | 0.600 |
| `anthropic/claude-haiku-4-5-20251001` | 7 | 3 | 2 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |

All four cells exited `0:0` and passed the built-in and independently repeated
strict validators. Independent postflight found exactly four schema-1.2.0
manifests and four native logs, the exact clean commit and runtime source, seed
0, Inspect 0.3.245, requested/resolved model identity, the registered profile,
and no error or exhausted limit. The model-registry SHA-256 remained
`41913bf3abee56660dd7b455dc19f9f57d0939304d2a412cea1161837bd2667e`,
and all four evaluation stderr files were empty.

Semantic audit confirmed one causal, report-matched preparation each for Sol
and Luna. Sol used 5 mL for 3 minutes and produced 10 ug at 200 ng/uL; Luna
used 1.5 mL for 3 minutes and produced 3 ug at 60 ng/uL. Both used the seeded
culture, P1/P2/N3, the specified QIAprep 2.0 spin column, and 50 uL elution,
and both source-culture remaining volumes matched the simulator invariant.

Sonnet also produced a valid single preparation (3 mL, 5 minutes, 6 ug at
120 ng/uL), but its native final response contained two identical copies of
the complete 11-line report. The unique-report parser correctly assigned task
success zero rather than silently deduplicating repeated fields. Haiku first
used the wrong P1/P2/P3 sequence, observed an explicit failed preparation with
no culture consumption, corrected to P1/P2/N3, and succeeded on a second call.
Because the prompt requires exactly one `perform_miniprep` call, the scorer
correctly rejected the retry path instead of hybridizing its failed and
successful results. These are substantive model-level contract failures, not
scorer or infrastructure defects.

This accepts `miniprep_01` as the third completed P1 task: 12/20 cells and 3/5
tasks are contract-validated. These remain one-seed compatibility and
scorer-contract results, not comparative model-ranking evidence.

## Scale decision

All five snapshot tasks retain strict one-seed sentinel coverage, and P1 is
now 12/20 accepted cells after the remediated `golden_gate_01`, `gibson_01`,
and hardened `miniprep_01` gates. Earlier pre-remediation bundles remain
diagnostic-only. Human-baseline and multi-seed work remain intentionally
skipped. The next bounded gate is `express_01` on the same four-model,
seed-zero protocol. Frozen historical results and every cancelled, diagnostic,
or pre-remediation bundle remain excluded from promoted aggregates.
