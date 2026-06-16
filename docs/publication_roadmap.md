# LabCraft-Eval Public Artifact Roadmap

Prepared: 2026-06-15

This roadmap turns LabCraft-Eval from a strong research repository into a
premium public benchmark artifact that is easy for both humans and machines to
understand. It complements the existing HPC v0.2 execution plan: HPC produces
trustworthy numbers; this roadmap makes the repository, release bundles, and
Hugging Face surfaces trustworthy to consume.

## North Star

GitHub is the source of truth for code, methodology, provenance, and release
history. Hugging Face is the distribution surface for machine-readable benchmark
records, result tables, and an interactive leaderboard.

The public experience should satisfy two tests:

- A human reviewer can understand the benchmark's purpose, novelty, limitations,
  safety scope, and quickstart path in the first few minutes.
- A machine consumer can load tasks, rubrics, citations, result rows, release
  manifests, and schema versions without scraping Markdown prose.

## Phase 1: Public Trust Layer

Goal: make the GitHub repository read as maintained research software.

Deliverables:

- Add GitHub Actions CI for tests, citation/scope checks, lint, and export-smoke
  validation.
- Add issue templates, a pull request template, and contribution guidance.
- Add a security and safety reporting policy distinct from the benchmark scope
  policy in `SAFETY.md`.
- Add a changelog that records public-facing releases, renames, result bundle
  promotions, and scorer changes.
- Keep the README as the entry point, but move deep implementation and release
  details into focused docs.

Definition of done:

- A new visitor sees CI, licenses, citation metadata, safety policy,
  contribution guidance, and release history without reading private notes.
- Every public-support path tells the user where to report code bugs, scoring
  issues, safety concerns, and commercial licensing questions.

## Phase 2: Machine-Readable Benchmark Package

Goal: export one stable data package that mirrors the public benchmark surface.

Deliverables:

- `schemas/*.schema.json` files for release manifests, task records, rubric
  records, citation records, and result rows.
- `scripts/export_hf_dataset.py`, producing:
  - `tasks.jsonl`
  - `rubrics.jsonl`
  - `ground_truth.jsonl`
  - `citations.jsonl`
  - `result_rows.jsonl`
  - `eval_log_manifest.jsonl`
  - `release_manifest.json`
- SHA-256 checksums for every exported artifact.
- A schema version and source commit in every exported record.
- CI checks that the export command completes and writes valid JSON.

Definition of done:

- Consumers can reproduce the benchmark inventory and reported result rows
  without importing LabCraft internals.
- A release bundle can be audited back to a commit SHA, result directory, task
  matrix, model matrix, seed range, and scorer version.

## Phase 3: Hugging Face Premium Surface

Goal: make Hugging Face the easiest way to inspect and reuse the benchmark data.

Recommended surfaces:

- Dataset repo: `LabCraft-Eval`
  - Dataset card with YAML metadata, tags, licenses, task categories, safety
    scope, intended use, out-of-scope use, data fields, and citation.
  - Viewer-friendly JSONL files for tasks, rubrics, citations, and result rows.
  - Release tags matching GitHub releases.
- Space: `LabCraft-Eval Leaderboard`
  - Track selector: frozen snapshot, current wet-lab, discovery, safety case.
  - Model x task scorecard.
  - Axis heatmap.
  - Seed variance view.
  - Links to exact release manifests and GitHub commit SHAs.
- Collection:
  - Dataset.
  - Leaderboard Space.
  - GitHub repository.
  - Paper or technical report, once available.

Definition of done:

- The HF dataset card explains how to use the data responsibly and points back
  to GitHub for code and reproducibility.
- The HF Space never reports a number without a manifest-backed source.

## Phase 4: v0.2 Scientific Credibility

Goal: promote a larger result bundle without weakening the frozen v0.1 snapshot.

Deliverables:

- Complete the HPC v0.2 N=10 candidate with append-only logs and manifests.
- Add a small expert baseline pilot on `transform_01`, `growth_01`, and one
  discovery task.
- Run a prompt-sensitivity sweep for the `growth_01` troubleshooting gap.
- Add a reasoning-focused companion to `transform_01` so the benchmark is not
  overread as only an output-format reliability test.
- Freeze and document scorer versions.

Definition of done:

- Public numbers cite commit SHA, run ID, task matrix, model matrix, seed range,
  aggregation command, and scorer version.
- The main claim remains narrow: compact, reproducible, benign wet-lab protocol
  and discovery-decision reliability with deterministic multi-axis scoring.

## Phase 5: Paper and Portfolio Grade

Goal: turn the repository into a polished research artifact.

Deliverables:

- Short technical report or preprint.
- One end-to-end trajectory walkthrough.
- Architecture diagram.
- Reproducibility capsule with exact environment, command, expected output, and
  checksum.
- GitHub release with attached machine-readable bundle.
- Matching Hugging Face dataset tag and optional DOI-bearing archive.

Definition of done:

- Reviewers can evaluate the idea, inspect the implementation, reproduce a
  smoke run, and download the canonical data bundle without asking for private
  context.

## Ownership Rules

- Do not overwrite historical `.eval` logs or published result files.
- Do not merge safety-case scores into wet-lab simulator leaderboards.
- Do not claim real wet-lab capability measurement; the simulator is
  citation-backed but not physically grounded.
- Do not broaden biological scope without updating `SAFETY.md`, tests, task
  metadata, and public release notes.
- Treat schema changes as release-relevant changes.

## Immediate Backlog

1. Add the public trust files: CI, issue templates, PR template,
   `CONTRIBUTING.md`, `SECURITY.md`, and `CHANGELOG.md`.
2. Add the first HF export skeleton and validate that it writes JSONL and a
   manifest from the current checked-in task/result files.
3. Add schema files for export records and keep them intentionally small until
   downstream consumers need additional fields.
4. Add `docs/hf_release.md` with the expected HF dataset layout and card
   sections.
5. After the skeleton lands, decide whether the first public HF bundle should be
   v0.1 frozen snapshot only or v0.1 plus clearly separated v0.2 candidate
   tracks.
