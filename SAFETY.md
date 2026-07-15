# LabCraft Safety Scope

LabCraft-Eval is a public evaluation environment for benign biology tasks across
several BSL-1/2 domains. Its flagship purpose is to measure whether agents can
execute, diagnose, and recover routine wet-lab workflows while keeping every
trajectory auditable. The repository also contains companion decision tasks and
an experimental, text-only safeguard-quality track. Those tracks have distinct
contracts and are never merged into one leaderboard.

## Track Boundaries

- **Flagship wet-lab simulator:** executable, seeded molecular-microbiology and
  biochemistry tasks with fixed tools and deterministic trajectory scoring.
- **Companion Discovery Decision Track:** synthetic, non-simulator evidence
  triage and next-experiment decisions with no lab-operation execution. It
  complements the simulator but does not broaden its organism or
  laboratory-operation scope.
- **Experimental Safety Case Track:** single-turn, text-only evaluation of
  legitimate helpfulness, boundary precision, provenance, monitoring, and
  residual-risk framing. It has no lab-operation tools, does not run the seeded
  simulator, and is not a harmful-biology capability benchmark.

The Safety Case Track may use standard, non-viral mammalian cell-line,
non-infectious primary-cell, or archived fixed-sample research scenarios as
benign policy examples. Examples include routine transfection, knockdown,
immunoassay, imaging, sequencing-library, and literature-support questions.
They do not become executable LabCraft simulator tasks, and their scores remain
outside the simulator and Discovery leaderboards.

## Simulator and Discovery Included Scope

- **BSL-1 and BSL-2 benign molecular microbiology**
  - Standard laboratory *E. coli* strains (DH5alpha, BL21, BL21(DE3), Stbl3)
  - Benign industrial/lab bacterial species (*B. subtilis*, *P. putida*) on an opt-in basis
  - Benign phage-biology elements used in routine cloning workflows (lambda, M13)
  - Standard cloning vectors (pUC19, pET, pGEX) and routine reagents (LB, SOC, ampicillin, kanamycin, polymerases, ligases, common buffers)
- **Benign yeast genetics**
  - *Saccharomyces cerevisiae* laboratory strains (BY4741, W303, S288C and their derivatives) for transformation, auxotrophic selection, and growth characterisation
- **In-vitro biochemistry on benign, non-toxic proteins only**
  - Model enzymes (β-galactosidase, alkaline phosphatase, restriction enzymes, DNA/RNA polymerases)
  - Fluorescent proteins (GFP, mCherry, mScarlet) and structural affinity tags (His-tag, MBP, GST, Strep-tag)
  - Standard host housekeeping proteins
  - Workflows: induction, cell lysis, affinity purification, SDS-PAGE, spectrophotometric activity assays, Michaelis–Menten kinetics
- **BSL-1 adherent mammalian cell lines for non-viral work**
  - Approved candidate lines for future task expansion: HEK293, HeLa, NIH-3T3, CHO and close derivatives
  - Operations: thawing, passaging, counting (trypan blue), non-viral transfection (Lipofectamine or equivalent), **benign reporter assays only** (GFP, mCherry, luciferase, β-galactosidase, SEAP)
- Text and structured-tool observations for simulated experiments

## Simulator and Discovery Exclusions

The following are outside the executable simulator and synthetic Discovery task
surface. Their appearance as a benign, text-only Safety Case policy example does
not authorize a simulator task or an executable tool contract.

- Primary human or animal tissue; primary-cell isolation or culture; iPSCs,
  ESCs, organoids, and 3D cultures
- Flow-cytometric sorting of primary cells
- Mammalian-cell operations beyond the benign, non-viral reporter workflows
  listed above

## Project-Wide Excluded Scope

These exclusions are **non-negotiable** and override every track-specific
included scope wherever they overlap.

- **All viral work** — transduction, lentivirus / AAV / retrovirus production or titer, cytopathic-effect scoring, packaging lines, viral vectors as cargo in transfection
- CDC select agents; any BSL-3 or BSL-4 organism
- Gain-of-function work, pathogen enhancement, or dual-use optimisation language
- Mammalian virology, viral titer assays, or cytopathic-effect scoring
- Gene drives and their construction
- Sequences > 20 bp unless they are clearly limited to standard cloning-vector fragments
- **Expression of toxins, virulence factors, cytokines, pore-forming proteins, receptor agonists/antagonists targeting human signalling, or any protein with therapeutic or offensive potential** — regardless of host (*E. coli*, yeast, or mammalian)
- Any task content intended to increase real-world capability for harmful biological work

## Provenance requirement for new organisms

Every strain, cell line, or host referenced in a task must have a checked-in public registry reference (ATCC, DSMZ, ECACC, EUROSCARF, Addgene, or equivalent) in the relevant task metadata or a future organism registry before the task is released. The current implemented task set is constrained to the task surfaces under `task_data/` and the checked-in reagent, enzyme, safety, and parameter data under `data/`.

## Public-Data Commitment

Every parameter, threshold, protocol template, reagent specification, and safety statement in LabCraft must trace to a public, citable source. Private lab notebooks, unpublished observations, anecdotal lab knowledge, blogs, and unsourced tutorials are not valid source material for the benchmark.

## Source Quality Tiers

LabCraft uses a four-tier source system:

- Gold: canonical, highly cited, peer-reviewed foundational sources
- Silver: peer-reviewed sources with DOI from reputable venues
- Bronze: authoritative reference material such as vendor specifications, regulatory documents, and curated databases
- Copper: attributed community protocol resources for non-critical context

Excluded sources are not used directly.

Core stochastic parameters must meet the tier requirements defined in the implementation plan and enforced by tests. When a suitable citation is unavailable, the parameter or claim does not enter LabCraft.

## Automated Scope Enforcement

LabCraft ships an always-on automated safety guard: `tests/test_scope_compliance.py` scans every task-surface file (`src/`, `data/`, `task_data/`, `docs/methodology.md` when present) for a reviewable list of exclusion keywords on every `pytest` run, and fails the suite if any match. The keyword list is in `tests/scope_exclusion_keywords.txt`. Files that legitimately discuss excluded content — this `SAFETY.md`, `results/positioning.md` (related-work discussion), `results/analysis.md` (findings), the scope-compliance test itself, and the keyword list — are explicitly allowlisted inside the test.

## Reporting Concerns

If you identify a safety, sourcing, or scope concern, open a repository issue labeled `safety` or contact the maintainer through the repository profile associated with this project. Please include the file path, the concerning content, and why it appears to exceed the stated scope.
