# LabCraft-Eval Technical Report

Version: v0.1.2
Author: Jihoon Kim, Weill Cornell Medicine

## Abstract

LabCraft-Eval is a compact Inspect AI benchmark for evaluating whether language
model agents can execute benign molecular-microbiology workflows inside a
seeded simulator with task-dependent deterministic and stochastic operations.
The benchmark combines public protocol prompts, tool-mediated lab operations,
citation metadata, and deterministic four-axis trajectory scoring. The v0.1.2
codebase implements 14 runnable simulator and decision tasks plus a separate
Safety Case Track. Its public Hugging Face v0.1.2 snapshot is intentionally a
metadata-only integrity release and contains no promoted result rows or raw
evaluation logs.

> **Evidence status:** the published v0.1.1 scorecard, early newer-task bundles,
> the HPC candidate, and live Safety Case summaries are historical or
> provisional artifacts. Some were collected before answer-bearing guidance was
> removed, with older scorer behavior or incomplete public provenance. Under the
> current contract, all five frozen snapshot tasks have passed a strict
> four-model, seed-zero compatibility sentinel. Those sentinel runs validate
> provider compatibility, provenance checks, and scorer contracts; they are not
> a promoted score-bearing release or a model/provider ranking.

## Motivation

Many model evaluations over biological protocols score final answers or static
question-answering behavior. LabCraft-Eval instead scores the full agent
trajectory: planning, tool calls, observations, interpretation, and final
reporting. This makes failure modes visible when a model reaches a plausible
answer through poor experimental decisions, or when it uses reasonable tools but
fails to diagnose uncertainty.

## Benchmark Design

Each runnable task exposes a protocol prompt, a fixed tool set, a seed-labelled
sample, ground-truth metadata, and a checked-in rubric design artifact. Some
operations use the seeded RNG, while others are deterministic across seed
labels. The agent interacts with lab operations such as media preparation,
transformation, incubation, measurement, assembly, purification, or
decision-support tools. The simulator returns observations, and Inspect records
the complete `.eval` trajectory.

The scientific flagship is the wet-lab execution and recovery surface. The
Discovery Decision Track is a companion decision-quality surface. The Safety
Case Track is experimental, uses a separate scoring contract, and is never
merged into the flagship leaderboard.

## Scoring

The simulator tasks are scored along four deterministic axes:

| Axis | Definition |
| --- | --- |
| Decision quality | Whether key tool-call choices match the ground-truth decision points. |
| Task success | Whether the trajectory and final answer satisfy the task objective. |
| Troubleshooting | Whether the answer recognizes relevant failures, uncertainty, or limitations. |
| Efficiency | Whether the agent makes progress with a reasonable number of tool calls. |

In v0.1.x, runtime scoring is implemented directly in
`src/trajectory_scorer.py` with fixed top-level weights. The JSON rubric trees
document the intended hierarchy but are not executed by the live Inspect scorer.

The unreleased local P2a conformance layer adds a versioned manifest for the
five P1 wet-lab scorers. It pins each scorer and Inspect builder, artifact
digests, report fields, decision IDs, and evidence policy. A 35-case synthetic
corpus covers canonical-valid, alternative-valid, forged, partial, orphan,
contradictory, and retry trajectories. The deterministic technical regression
passes locally, including fail-closed request/output evidence checks for Golden
Gate and Gibson, but its labels remain AI-assisted drafts pending 35/35 expert
review. It is not promoted benchmark evidence.

The Safety Case Track uses a separate conversational safeguard scorer and is not
merged into the wet-lab simulator leaderboard.

## Public Evidence

The frozen v0.1.1 scorecard reports 100 historical sample rows across five
simulator tasks, four models, and five seed-labelled repetitions. These
repetitions combine model-output variation, formatting and message-budget
effects, and task-dependent environment changes; they are not five independent
stochastic environments for every task. The scorecard is preserved for
historical audit and is not a current-contract comparison.

The v0.1.2 Hugging Face release is metadata-only. It publishes the benchmark
inventory, rubrics, ground truth, citations, schemas, plots retained as
historical visual assets, and a checksum-bearing release manifest. It
intentionally omits `result_rows.jsonl` and raw `.eval` logs, so it must not be
presented as a new scored benchmark release.

Current-contract evidence is recorded in
`docs/model_refresh_status_2026_07.md`. Five snapshot tasks (`transform_01`,
`growth_01`, `pcr_01`, `screen_01`, and `clone_01`) completed one strict
seed-zero sentinel across the registered four-model core matrix. Every retained
cell passed clean-revision, requested/resolved-model, generation-profile,
runtime-source, Inspect-version, manifest-schema, and no-limit-exhaustion
checks. Human-baseline and multi-seed collection remain intentionally skipped,
so these runs are compatibility and scorer-contract evidence only.

The five newer P1 wet-lab tasks separately completed 20/20 accepted strict cells
at their recorded clean evaluation commits. P2a subsequently changed the local
Golden Gate and Gibson scorer behavior to close forged-request, orphan-output,
and report-uniqueness gaps. Therefore the accepted P1 cells remain
commit-bound compatibility evidence; they are not a claim that those external
trajectories were rerun against the current working-tree scorer.

Key public surfaces:

- `results/results.md` for the historical frozen scorecard.
- `results/analysis.md` for historical failure-mode analysis.
- `results/discovery_track.md` for historical discovery-decision results.
- `results/hpc_v0_2_current_n10.md` for the provisional HPC candidate summary.
- `results/safety_case_live_v0_2.md` for the provisional live Safety Case summary.
- `PROJECT_STATUS.md` for the current continuation state and next gate.

## Reproducibility

The GitHub repository is the source of truth for code, tests, task definitions,
scorers, and release history. The Hugging Face dataset provides a
machine-readable snapshot with JSONL records and `release_manifest.json`. The
manifest records the source commit, schema version, byte counts, record counts,
and SHA-256 checksums for each exported artifact.

Minimum local checks:

```bash
uv run pytest
uv run python scripts/validate_scorer_contracts.py
# Remains exit 2 until all 35 exact fixture definitions are expert-approved.
uv run python scripts/validate_scorer_contracts.py --require-expert-approved
uv run python scripts/export_hf_dataset.py \
  --out-dir build/hf_dataset \
  --release-name local_export \
  --no-results \
  --clean-output \
  --copy-plots
uv run python scripts/validate_hf_export.py build/hf_dataset
```

## Safety Scope

LabCraft-Eval is intentionally scoped to benign BSL-1/BSL-2 educational and
research-support workflows. It is not a harmful-biology capability benchmark,
not a substitute for wet-lab validation, and not evidence of real-world
experimental competence. Safety scope and reporting guidance are maintained in
`SAFETY.md` and `SECURITY.md`.

## Limitations

- The simulator has citation metadata but is not physically grounded in a real
  lab; repository checks do not independently validate every scientific claim.
- The frozen scorecard is historical and should not be overread as a broad
  model capability ranking.
- Historical bundles collected with answer-bearing prompt guidance must not be
  interpreted as current, leakage-free protocol-reasoning results.
- The latest strict snapshot sentinels cover only one seed and were not promoted
  as a score-bearing public release.
- The P2a scorer corpus is synthetic development-conformance evidence with 0/35
  expert approvals; technical regression success alone does not validate its
  scientific labels or make it promotion-eligible.
- Human-baseline and multi-seed work are intentionally skipped at the current
  gate. Comparative reliability and paper-grade ranking claims remain blocked
  until an appropriate repeat design and external reference are completed.
- Current task bundles and HPC candidates remain separate until they are
  intentionally promoted under the release criteria in `PROJECT_STATUS.md`.

## Citation

If you use LabCraft-Eval, cite the repository URL, the exact source commit, and
the release manifest or result bundle used. For v0.1.2, use the GitHub release
and Hugging Face dataset tag that share the metadata-only manifest-backed
snapshot; do not attribute historical score rows to v0.1.2.
