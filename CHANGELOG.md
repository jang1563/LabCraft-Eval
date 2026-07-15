# Changelog

All notable public-facing changes to LabCraft-Eval should be documented here.
This project keeps result bundles reproducible, so corrections should be
recorded rather than silently rewriting history.

## Unreleased

- Add a canonical project-status anchor with the scientific North Star, track
  roles, evidence limits, exact next gate, and P0-P3 promotion plan.
- Make the no-dependency Hugging Face quickstart manifest-first, safe for
  metadata-only snapshots, checksum-verified, and resistant to stale mutable-tag
  caches.
- Separate the current v0.1.2 metadata contract from historical provisional
  v0.1.1 scores in the leaderboard source, with explicit empty states and
  manifest-backed release selection.
- Align the README, safety scope, technical report, citation metadata, and
  release documentation around the flagship wet-lab benchmark, companion
  Discovery track, and separately scored experimental Safety Case track.
- Make API-backed HPC release cells reject dirty checkouts and drifted Inspect
  environments before launch, and require a clean native evaluation revision
  in the built-in strict cell validator.

## 0.1.2 - 2026-07-12

- Publish the integrity and provenance corrections as v0.1.2, generalize
  public HPC documentation, remove application-only framing, and add a
  regression check for public-surface hygiene.
- Align `growth_01` with its non-answer-bearing prompt by scoring defensible
  starting-OD and measurement-cadence ranges instead of hidden exact values,
  and separate agent-turn and hard-message caps so parallel tool results cannot
  terminate a valid final fit before completion.
- Accept source-backed OD600 0.01-0.10 starts and common colon, dash, and
  Markdown-table doubling-time reports so scientifically valid trajectories do
  not fail on arbitrary punctuation.
- Pin runtime imports to the submitted checkout, fail closed when a reused
  editable environment resolves `src` elsewhere, and record the verified source
  root in each HPC cell manifest.
- Count explicit screened-colony ID lists correctly instead of interpreting the
  numeric suffix of the first ID as the total screen size.
- Canonicalize common Q5 and Phusion labels before PCR simulation so aliases do
  not receive behavior or warnings that contradict their normalized identity.
- Score PCR decision quality from clean-target-band reactions rather than
  combining favorable parameters across unrelated failed attempts.
- Separate `transform_01` turn and message limits, accept unambiguous ordered
  CFU reports and consistency wording, score final usable cultures/counts, and
  allow one complete dilution retry within the reasonable call budget.
- Score `clone_01` decisions from successful digest/ligation reactions, treat
  same-workflow corrections as troubleshooting, match reagent filters without
  case sensitivity, and require successful reactions plus the observed
  transformant count for task-success credit.
- Accept Unicode superscript scientific notation in transformation reports and
  same-culture, same-dilution plate sums in clone transformant counts without
  permitting raw-count addition across different dilution factors.
- Add one central model registry with current cross-provider matrices,
  model-specific generation profiles, and exact requested/resolved model
  expectations for local and Slurm runners.
- Record provider-resolved model identity, provider, Inspect version, and
  Inspect-recorded generation configuration in new score exports; reject mixed
  alias resolutions and provenance mismatches.
- Pin Inspect and provider SDK versions together and document the minimal
  current-model compatibility-smoke workflow.
- Reject limit-exhausted Inspect samples from validated HPC cells and scored
  Hugging Face exports, even when Inspect produced a partial trajectory score.
- Mark the frozen v0.1.1 and later unbundled aggregate score pages as
  historical/provisional benchmark-development evidence rather than validated
  model or provider rankings.
- Remove answer-bearing simulator observations and prompt/tool-schema defaults,
  and validate every required miniprep, expression, and purification report
  field against the executed tool result.
- Require an exact structured success token for those three final reports,
  neutralize evaluated values in the human-baseline examples, and align current
  human runs with the agent runner's explicit integer seed convention.
- Make portfolio runs write to new `build/eval_runs/<RUN_ID>` bundles by
  default, require explicit aggregation/plot inputs and outputs, and reject
  invalid seed ranges before an API-backed evaluation starts.
- Canonicalize output paths before frozen-artifact guards, make plotting reject
  unreadable/non-success logs, and move the Discovery wrapper's defaults into
  a new timestamped build bundle.
- Give single- and multi-sample runs the same explicit seed identity so local
  and HPC execution agree on seed zero.
- Package the Safety Case policy resource, smoke-test that task from the wheel,
  pin the tested Inspect API version, and return invalid tool IDs/values as
  agent-visible structured errors.
- Reserve high live Safety Case provenance credit for scenario-allowlisted
  references, cap unverified citation-shaped text at low partial credit, and
  avoid penalizing explicit boundary statements that negate excluded terms.
- Regenerate the Safety Case fixture report under that stricter scorer and
  replace the unrelated `rs_005` antibody-validation PMID with protein-storage
  and recombinant-protein quality references.
- Clarify that v0.1.x runtime scoring is deterministic hard-coded logic; the
  checked-in JSON rubrics are audit/design artifacts rather than the live
  scoring source.
- Introduce the schema 0.2.0 clean-provenance contract for new Hugging Face
  score exports, preserving native `evaluation_revision` separately from the
  packaging `source_commit` and rejecting dirty packaging or evaluation
  revisions.
- Bundle raw Inspect logs in score-bearing exports, require non-empty pinned
  generation configuration, cross-check result/log provenance, and restrict
  destructive export cleanup to `build/`.
- Validate schema 0.2.0 task, result, eval-log-manifest, and release-manifest
  records against the checked-in executable JSON Schemas.
- Reject reserved-table aliases, path traversal, absolute paths, and symlinks
  that escape an HF export bundle in both validation and upload planning.
- Make executed Hugging Face uploads exact manifest replacements so stale
  remote score or plot files cannot survive a corrected bundle.
- Make metadata-only HF export the documented CI packaging-smoke path, and
  document non-empty output refusal plus explicit `--clean-output` behavior.
- Correct the Monod growth-model DOI and Bergkessel/Guthrie Colony PCR DOI in
  parameter metadata and corresponding source documents.
- Correct the historical `transform_01` full-success seed narrative without
  rewriting the frozen generated result table.

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
