# LabCraft-Eval Project Status

Last reviewed: 2026-07-15
Public release: `v0.1.2`
Detailed roadmap: [docs/publication_roadmap.md](docs/publication_roadmap.md)

## Scientific North Star

> Auditable evaluation of whether AI agents can execute, diagnose, and recover
> benign molecular-biology workflows inside a stateful laboratory simulator.

LabCraft-Eval measures simulator-mediated scientific trajectories, not physical
wet-lab competence and not broad biology capability.

## Track Roles

| Role | Track | Status |
| --- | --- | --- |
| **Flagship** | Wet-lab execution and recovery: five frozen snapshot tasks, five newer wet-lab tasks, and `followup_01` | Active; snapshot sentinels retained, `golden_gate_01` contract-validated, P1 at 4/20 cells |
| **Companion** | Discovery Decision Track: `perturb_followup_01`, `target_prioritize_01`, `target_validate_01` | Runnable; historical public evidence remains provisional |
| **Experimental / separate** | Safety Case Track: `safety_case_01` | Runnable; separate scorer and public surface, never merged into flagship scores |

## Verified State

- GitHub release `v0.1.2` is the current public integrity release.
- The v0.1.2 Hugging Face dataset is metadata-only: no promoted result rows or
  raw `.eval` logs are attributed to this release.
- The codebase implements 14 runnable simulator/decision tasks plus the
  separate Safety Case Track.
- All five frozen snapshot tasks completed a strict seed-0 sentinel across the
  registered `current_balanced` four-model matrix. Retained cells passed clean
  revision, requested/resolved model, generation-profile, runtime-source,
  Inspect-version, manifest-schema, and no-limit-exhaustion gates.
- The first `golden_gate_01` P1 array completed four of four technical cells at
  clean revision `b20382a7c473bd73e9707e288fa7fd8b4a3732a1`, but semantic
  audit reproduced scorer false positives and reference-contract defects. The
  bundle remains diagnostic-only and excluded from accepted evidence.
- The remediated `golden_gate_01` array at clean revision
  `f7d5ba5062b69a3b33968d656272626c1870114c` passed all four strict cells and
  independent semantic/postflight audit. P1 is now 4/20 accepted cells. One
  Haiku trajectory correctly scored task success 0 after it failed to recover
  from a three-colony, out-of-range plate; this is retained as substantive
  compatibility evidence, not treated as infrastructure failure.
- The retained five-task snapshot sentinels validate compatibility and scorer
  contracts. They are not a public score-bearing release and do not support
  comparative model ranking.
- Historical v0.1.1, newer-task, Discovery, HPC, and live Safety Case summaries
  remain historical or provisional unless explicitly promoted under the rules
  below.

Evidence ledger: [docs/model_refresh_status_2026_07.md](docs/model_refresh_status_2026_07.md)
Release contract: [docs/release_checklist.md](docs/release_checklist.md)

## Current Constraints

- Human-baseline collection is intentionally skipped for the current gate.
- Multi-seed collection is intentionally skipped for the current gate.
- Therefore, current work may establish task/model compatibility and scorer
  correctness, but not comparative reliability, confidence intervals, or a
  publication-grade ranking.
- Diagnostic, cancelled, dirty-checkout, limit-exhausted, pre-remediation, and
  historical rows must remain outside promoted aggregates.

## Exact Next Gate

Run seed 0 for the registered `current_balanced` matrix on these five newer
flagship wet-lab tasks:

1. `golden_gate_01` — complete at `f7d5ba5`
2. `gibson_01` — next
3. `miniprep_01`
4. `express_01`
5. `purify_01`

Use the existing immutable-checkout HPC path and strict cell validator. Run one
task at a time, inspect any failure before scaling, preserve source logs, and
exclude diagnostic retries from promoted aggregates.

## Promotion Criteria

A task becomes **contract-validated** only when every planned cell passes:

- clean immutable evaluation revision;
- exact requested/resolved model and provider identity;
- registered, non-empty effective generation configuration;
- expected runtime source root and pinned Inspect version;
- current manifest schema and complete native log;
- no message, token, turn, time, or cost limit exhaustion;
- scorer acceptance of known valid alternative paths and rejection of known
  wrong paths;
- no answer-bearing guidance in the agent-facing prompt.

A bundle becomes a **current score-bearing release** only when its raw `.eval`
logs and manifest-backed result rows are public, independently
re-aggregatable, tied to the same immutable code/model/task/scorer contract,
and consistently referenced by GitHub, Hugging Face, the leaderboard, and the
technical report.

A **comparative or paper-grade claim** additionally requires a predeclared
repeat design and an appropriate external reference such as expert validation
or a human baseline. One-seed sentinel results must remain labelled as
compatibility/scorer-contract evidence.

## Current Priority Board

- **P0 — locally complete; public sync pending:** public truth repair and
  consistent release/evidence labels are committed locally but not pushed.
- **P1 — in progress:** 4/20 cells accepted; `golden_gate_01` is
  contract-validated and `gibson_01` is next.
- **P2 — planned:** reasoning, recovery, and counterfactual task depth plus
  modular/versioned scorer validation.
- **P3 — deferred:** clean current scored release, leaderboard promotion, and
  publication package after evidence gates pass.
