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
| **Flagship** | Wet-lab execution and recovery: five frozen snapshot tasks, five newer wet-lab tasks, `followup_01`, and development-only `pcr_causal_reasoning_01` | Active; snapshot sentinels retained, all five newer wet-lab tasks contract-validated, P1 complete at 20/20 cells, first P2b task isolated from promotion |
| **Companion** | Discovery Decision Track: `perturb_followup_01`, `target_prioritize_01`, `target_validate_01` | Runnable; historical public evidence remains provisional |
| **Experimental / separate** | Safety Case Track: `safety_case_01` | Runnable; separate scorer and public surface, never merged into flagship scores |

## Verified State

- GitHub release `v0.1.2` is the current public integrity release.
- The v0.1.2 Hugging Face dataset is metadata-only: no promoted result rows or
  raw `.eval` logs are attributed to this release.
- The public portfolio implements 14 runnable simulator/decision tasks plus the
  separate Safety Case Track. A two-case `pcr_causal_reasoning_01` task is also
  implemented under the non-exported `p2b_dev` preset.
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
  independent semantic/postflight audit. One
  Haiku trajectory correctly scored task success 0 after it failed to recover
  from a three-colony, out-of-range plate; this is retained as substantive
  compatibility evidence, not treated as infrastructure failure.
- The first hardened `gibson_01` array at clean revision
  `9afc917bc5366c485e0904f200c5248b0148c77e` passed all four technical cells,
  but its scorer rejected valid Gibson method labels in three final reports.
  That pre-fix bundle remains diagnostic-only and excluded from accepted
  evidence.
- The remediated `gibson_01` array at clean revision
  `fb6b6dd40d301b5035e6d06fc7e169fa98339c34` passed all four strict cells and
  independent semantic/postflight audit. Each report binds to one complete
  assembly, transformation, Amp100 plate, plating, and count path. P1 is now
  8/20 accepted cells and 2/5 tasks.
- The hardened `miniprep_01` array at clean revision
  `ff47e8aa96a5564fb58700b3eb9db7d54badec43` passed all four strict cells and
  independent semantic/postflight audit. Sol and Luna produced one valid causal
  preparation and one unique matching report. Sonnet's valid preparation was
  correctly denied task-success credit because its native response duplicated
  the complete 11-line report. Haiku first used P1/P2/P3, then recovered with
  P1/P2/N3 in a second call; the fail-closed scorer correctly rejected the
  prompt's exactly-once violation rather than hybridizing the retry. P1 is now
  12/20 accepted cells and 3/5 tasks.
- The hardened `express_01` array at clean revision
  `be470123917ba0d8a9cc6ecb0b5b113e5a5db464` passed all four strict cells and
  independent semantic/postflight audit. Every model retrieved the exact seeded
  workflow and produced one accepted causal expression/lysate result. Sol, Luna,
  and Sonnet returned exact matching 11-line reports. Haiku's experiment was
  valid, but its markdown, extra prose, and trailing text were correctly denied
  task-success credit by the strict report parser. P1 is now 16/20 accepted cells
  and 4/5 tasks.
- The hardened `purify_01` array at clean revision
  `3b460a25292ad41b817c0091ab829e89832bb732` passed all four strict cells and
  independent scientific, semantic, and postflight audit. Every model retrieved
  the exact seeded QIAGEN Ni-NTA Superflow workflow and produced one accepted,
  causal purification result. Sol, Luna, and Sonnet returned exact matching
  16-line reports. Haiku's experiment was valid, but its prefatory sentence was
  joined directly to the first report field and was correctly denied task-success
  credit by the strict parser. P1 is complete at 20/20 accepted cells and 5/5
  tasks.
- The retained five-task snapshot sentinels validate compatibility and scorer
  contracts. They are not a public score-bearing release and do not support
  comparative model ranking.
- The local P2a foundation now pins scorer contract v1 for all five P1 tasks
  and runs 35 synthetic development-conformance trajectories across canonical,
  alternative-valid, forged, partial, orphan, contradictory, and retry cases.
  This work closed request-only, orphan-output, and non-unique-report false
  accepts in the Golden Gate and Gibson scorers. The technical regression gate
  passes, but all fixture labels remain AI-assisted drafts with 0/35 expert
  approvals, so the promotion gate remains closed.
- The first P2b development task, `pcr_causal_reasoning_01`, pairs two opaque
  GC-rich PCR failures with the same coarse gel phenotype but different causal
  settings. It requires one-variable diagnosis, one corrective PCR, a linked
  gel, and a non-executed counterfactual. Its scorer and fixtures are versioned
  separately from P1, and its contract is explicitly development-unreviewed,
  expert-review-skipped, non-promotable, and not ready for external evaluation.
- Historical v0.1.1, newer-task, Discovery, HPC, and live Safety Case summaries
  remain historical or provisional unless explicitly promoted under the rules
  below.

Evidence ledger: [docs/model_refresh_status_2026_07.md](docs/model_refresh_status_2026_07.md)
Release contract: [docs/release_checklist.md](docs/release_checklist.md)

## Current Constraints

- Expert review is intentionally skipped for the authorized local P2b work.
  This is a sequencing waiver only: the P1 review state remains 0/35 approved,
  and neither P1 nor P2b gains promotion status.
- Human-baseline collection is intentionally skipped for the current gate.
- Multi-seed collection is intentionally skipped for the current gate.
- External model/HPC execution, push, and public synchronization are outside
  the current authorization.
- Therefore, current work may establish task/model compatibility and scorer
  correctness, but not comparative reliability, confidence intervals, or a
  publication-grade ranking.
- Diagnostic, cancelled, dirty-checkout, limit-exhausted, pre-remediation, and
  historical rows must remain outside promoted aggregates.

## Exact Next Gate

Complete the **local P2b development gate** without treating the expert-review
waiver as approval:

1. keep the P1 35-fixture regression passing and its promotion gate closed;
2. require the P2b two-case scorer to accept canonical and alternative-valid
   one-variable recoveries and reject request-only, orphan, partial, forged,
   shortcut, contradictory, and retry paths as declared;
3. require exact task/scorer/ground-truth/rubric/fixture hashes and deterministic
   full score vectors from both the source tree and installed wheel;
4. keep `promotion_eligible=false`, `evaluation_policy_ready=false`, and
   `external_evaluation_authorized=false` until those gates are explicitly
   reopened;
5. only then choose the next distinct recovery or counterfactual family. The
   current two-case PCR family is the first depth unit, not completion of all P2
   scientific-validity exit criteria.

Keep the completed P1 bundles append-only and outside comparative ranking
claims. The Golden Gate and Gibson scorer behavior changed locally during P2a,
so the accepted P1 sentinels remain evidence for their recorded commits rather
than live validation of current HEAD. No external rerun is authorized in this
gate. Exclude diagnostic retries from promoted aggregates.

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
- **P1 — complete:** 20/20 strict cells accepted and all five newer wet-lab
  tasks contract-validated; one-seed evidence remains compatibility/scorer
  evidence rather than a ranking.
- **P2 — in progress, development-only:** P1 scorer v1 manifests and a 35-case
  regression remain technically green with expert review intentionally skipped;
  the first two-case causal reasoning/recovery/counterfactual task is locally
  isolated and non-promotable.
- **P3 — deferred:** clean current scored release, leaderboard promotion, and
  publication package after evidence gates pass.
