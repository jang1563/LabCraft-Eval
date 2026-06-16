# Changelog

All notable public-facing changes to LabCraft-Eval should be documented here.
This project keeps result bundles reproducible, so corrections should be
recorded rather than silently rewriting history.

## Unreleased

- Nothing yet.

## 0.1.1 - 2026-06-16

- Add a public artifact roadmap for GitHub and Hugging Face release quality.
- Add GitHub community-health files and CI scaffolding.
- Add initial Hugging Face export documentation, schemas, and export skeleton.
- Harden the Hugging Face export path so result logs and plot assets fail
  loudly when missing or unreadable.
- Add Hugging Face export validation for manifest checksums, JSONL record
  counts, required fields, and scored result rows.
- Add a dry-run-first Hugging Face dataset upload helper that validates bundles
  before any network write.
- Add citation metadata and a no-dependency Hugging Face quickstart example.
- Refresh GitHub Actions versions for the public CI workflow.
- Publish the first Hugging Face dataset export at
  `https://huggingface.co/datasets/jang1563/LabCraft-Eval`.

## 0.1.0 - 2026-04-25

- Publish the initial LabCraft-Eval benchmark snapshot under the former
  BioProtocolBench name.
- Include five frozen simulator tasks: `transform_01`, `growth_01`, `pcr_01`,
  `screen_01`, and `clone_01`.
- Publish deterministic four-axis trajectory scoring and citation-backed task
  metadata.
- Include Apache-2.0 licensing for code and CC BY-NC 4.0 licensing for
  benchmark content.

## 0.1.x - 2026-05-31

- Rename the public project to LabCraft-Eval to avoid a name collision with the
  unrelated BioProBench NLP corpus.
- Keep the installable Python distribution name as `labcraft` for v0.1.x.
- Add or promote newer wet-lab tasks, follow-up decision tasks, Discovery
  Decision Track tasks, Safety Case Track fixtures, and HPC v0.2 planning
  documents while keeping the frozen April 2026 scorecard separate.
