# LabCraft-Eval Public Artifact Roadmap

Prepared: 2026-06-15
Last reviewed: 2026-07-15
Current continuation anchor: [PROJECT_STATUS.md](../PROJECT_STATUS.md)

This roadmap tracks the work required to turn LabCraft-Eval into a premium,
scientifically defensible public benchmark. GitHub remains the source of truth
for code, methodology, provenance, and release history. Hugging Face remains
the distribution surface for manifest-backed benchmark records and, only when
available, promoted score-bearing evidence.

## Scientific North Star

> Auditable evaluation of whether AI agents can execute, diagnose, and recover
> benign molecular-biology workflows inside a stateful laboratory simulator.

The flagship contribution is the wet-lab execution and recovery benchmark. The
Discovery Decision Track is a companion decision-quality surface. The Safety
Case Track is an experimental, separately scored surface and must not be merged
into the flagship leaderboard.

The public experience should satisfy two tests:

- A human reviewer can identify the benchmark claim, evidence tier,
  limitations, safety scope, and reproducibility path in a few minutes.
- A machine consumer can load task, rubric, citation, manifest, and any
  promoted result records without scraping Markdown or guessing provenance.

## Previous Phase Reconciliation

| Previous phase | Status on 2026-07-15 | Disposition |
| --- | --- | --- |
| Phase 1: Public Trust Layer | **Completed for v0.1.2** | CI, contribution, security, changelog, citation, and release-trust files are present. Ongoing maintenance belongs to P0. |
| Phase 2: Machine-Readable Benchmark Package | **Completed for metadata-only releases** | Schema 0.3 export, validation, checksums, and manifest-backed packaging are implemented. A score-bearing current release remains gated. |
| Phase 3: Hugging Face Premium Surface | **Current / partial** | Dataset and leaderboard surfaces exist, but the public v0.1.2 dataset is metadata-only and historical score views must remain explicitly labelled. |
| Phase 4: v0.2 Scientific Credibility | **Superseded** | Replaced by the bounded P1-P3 sequence below. The historical HPC candidate is not a promoted current result. |
| Phase 5: Paper and Portfolio Grade | **Superseded** | Replaced by P3, after current-contract evidence and scientific-validity gates pass. |

## P0-P3 Status Board

| Priority | Status | Objective | Exit criteria |
| --- | --- | --- | --- |
| **P0: Public truth repair** | **Locally complete; public sync pending** | Make every public entry point accurately distinguish the v0.1.2 metadata release, historical provisional scores, and current compatibility evidence. | Quickstart is manifest-first and safe for metadata-only snapshots; historical leaderboard evidence is visibly labelled; README, safety scope, report, citation metadata, and continuation docs agree. |
| **P1: v0.2 contract gate** | **Completed — 20/20 accepted** | Validate the five newer flagship wet-lab tasks with the registered four-model core matrix and seed 0. | Every one of the 20 cells passes the strict validator with clean revision, exact requested/resolved model identity, registered generation profile, expected runtime source, current manifest schema, and no exhausted limits. Results remain compatibility/scorer-contract evidence, not a ranking. |
| **P2: Scientific depth and scorer validity** | **In progress — local conformance gate built; expert review pending** | Add tasks that discriminate execution, diagnosis, recovery, and counterfactual reasoning; reduce scorer brittleness. | At least one reasoning, one recovery, and one counterfactual task family; task-level scorer modules with explicit versions; expert-labelled valid/invalid trajectory fixtures; alternative-valid-path and wrong-path ablations; a declared held-out or rotating evaluation policy. |
| **P3: Current scored release and publication package** | **Deferred** | Promote a clean, independently auditable current-contract result bundle and package the benchmark for paper-level review. | Public raw `.eval` logs, manifest-backed result rows, exact code/model/generation provenance, reproducible aggregation, uncertainty appropriate to the repeat design, the promoted release added to the existing leaderboard selector, and a technical report that cites only promoted evidence. Human-baseline and multi-seed work must be explicitly reopened before comparative or paper-grade ranking claims. |

## Exact P1 Gate

Use seed 0 and the registered `current_balanced` matrix on:

- [x] `golden_gate_01` — 4/4 strict cells at `f7d5ba5`; pre-remediation
  `b20382a` remains diagnostic-only
- [x] `gibson_01` — 4/4 strict cells at `fb6b6dd`; pre-method-fix `9afc917`
  remains diagnostic-only
- [x] `miniprep_01` — 4/4 strict cells at `ff47e8a`; Sonnet's duplicate report
  and Haiku's exactly-once violation are retained as substantive model failures
- [x] `express_01` — 4/4 strict cells at `be47012`; Haiku's non-schema
  markdown, extra prose, and trailing text are retained as a substantive model
  report failure
- [x] `purify_01` — 4/4 strict cells at `3b460a2`; Haiku's prefatory sentence
  joined to the first required field is retained as a substantive model report
  failure

The P1 gate is complete. Preserve diagnostic and cancelled bundles, but exclude
them from promoted aggregates. Human-baseline and multi-seed work remain
intentionally skipped until those evidence tracks are explicitly reopened.

## Exact P2a Gate

Before adding new task families:

1. [x] define an explicit scorer contract/version manifest for the five P1
   tasks and bind it into task and future score metadata;
2. [x] create 35 AI-assisted draft trajectories covering canonical-valid,
   alternative-valid, forged, partial, orphan, contradictory, and retry paths;
3. [x] make the full component and decision vectors a deterministic local
   regression gate, including wheel-installed execution;
4. [ ] obtain expert review of every materialized trajectory and freeze all 35
   approved effective-definition hashes that bind the materialized trajectory
   and scorer contract; current status is 0/35 approved;
5. [ ] only then begin the reasoning, recovery, and counterfactual task
   families.

The local gate repaired request-only and orphan-output false accepts in the
Golden Gate and Gibson scorers and made both eight-line reports exact. Those
behavior changes do not rewrite the accepted P1 evidence: each P1 sentinel
remains bound to its recorded evaluation commit, and current HEAD has not been
rerun against external models under the P2a local-only authorization.

## Promotion Rules

A task may move from experimental to contract-validated only when all planned
P1 cells satisfy the strict provenance and completion gates. A task may move to
release-ready only after its scorer accepts scientifically valid alternative
paths, rejects known wrong paths, and its public prompt contains no
answer-bearing guidance.

A result bundle may be called current and score-bearing only when:

- native logs and aggregate records are public and independently
  re-aggregatable;
- the source commit, evaluation revision, model resolution, generation config,
  Inspect version, task matrix, seed/repeat design, and scorer version are
  recorded;
- every included cell is clean, complete, and free of limit exhaustion;
- historical, diagnostic, cancelled, and pre-remediation rows are excluded;
- the public dataset, leaderboard, report, and release notes reference the same
  immutable bundle.

Passing a one-seed sentinel does not establish a model ranking. A comparative
or publication-grade claim additionally requires a predeclared repeat design
and an appropriate external reference such as expert validation or a human
baseline.

## Ownership Rules

- Do not overwrite historical `.eval` logs or published result files.
- Do not merge Safety Case scores into wet-lab simulator leaderboards.
- Do not claim real wet-lab capability measurement; the simulator is
  citation-backed but not physically grounded.
- Do not broaden biological scope without updating `SAFETY.md`, tests, task
  metadata, and public release notes.
- Treat schema, scorer, task-contract, and promotion-state changes as
  release-relevant changes.
- Keep the v0.1.2 metadata-only release distinct from future score-bearing
  releases.
