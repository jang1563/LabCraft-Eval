# Release Checklist

Use this checklist before tagging or announcing a public LabCraft-Eval
snapshot.

## Scope and naming

- Keep the public benchmark name as LabCraft-Eval and the v0.1.x installable
  distribution name as `labcraft`.
- Treat direct `src.*` imports as internal compatibility paths for v0.1.x.
  Avoid introducing a second public import namespace in a patch release.
- Keep multi-task execution on [scripts/run_portfolio_eval.sh](../scripts/run_portfolio_eval.sh)
  presets: `snapshot`, `current`, `discovery`, `safety_case`, and `all`.
- Validate `config/model_matrix.toml` and confirm the release uses the intended
  registered matrix, exact provider IDs, and non-empty per-model generation
  profiles. The Slurm array runner rejects `GENERATE_CONFIG_FILE` and legacy
  `GENERATE_CONFIG_ARGS` overrides so its manifest and native log can be
  compared exactly; update the registry deliberately for a release run.
- Confirm every new scored row records requested model, provider-resolved
  model, provider, Inspect-recorded effective generation configuration, and
  Inspect version. Fail the release on a requested/resolved mismatch or on one
  requested alias resolving to multiple snapshots.
- Reject any cell whose native Inspect sample records a message, token, turn,
  time, or cost limit; a scored partial trajectory is not a completed cell.
- Keep `labcraft_suite()` as a single-task smoke alias unless a future breaking
  release introduces a real cross-task Inspect orchestration layer.

## Required checks

Run these checks on HPC for compute-constrained development. Do not use a local
laptop as the source of release verification when the project is in HPC-only
execution mode.

```bash
uv sync --extra dev --extra analysis --extra providers
uv run python scripts/model_matrix.py validate
uv run python scripts/validate_scorer_contracts.py
uv run pytest
uv run pytest tests/test_citations.py tests/test_scope_compliance.py tests/test_inspect_task.py
```

The default scorer-contract command is the technical regression gate. Any
release that promotes the P1 fixture corpus or makes expert-validated scorer
claims must additionally pass:

```bash
uv run python scripts/validate_scorer_contracts.py --require-expert-approved
```

That command intentionally exits 2 while any exact effective fixture definition
is pending, stale, rejected, or not hash-bound to an expert decision.

- Confirm the latest `CodeQL` workflow run has completed successfully for
  `main`, or document why code scanning was skipped for the release.

## Metadata checks

- Confirm [CITATION.cff](../CITATION.cff) has the intended version and release
  date.
- Confirm [.zenodo.json](../.zenodo.json) matches the intended release title,
  creators, version, date, license split, and related identifiers.
- Confirm [README.md](../README.md), [NOTICE](../NOTICE), [LICENSE](../LICENSE),
  and [LICENSE-DATA](../LICENSE-DATA) describe the same licensing split.
- Confirm [pyproject.toml](../pyproject.toml) metadata points to the current
  repository and issue tracker.
- Confirm the Hugging Face dataset has a tag matching the GitHub release tag
  and that its `release_manifest.json` source commit matches the release notes.
- Include the commit SHA and log/result directory when reporting benchmark
  numbers.
- Distinguish the export packaging `source_commit` from each log's native
  `evaluation_revision.commit`; report both for schema 0.3.0 scored releases.
- Require `evaluation_revision.dirty: false` and a recorded
  non-empty effective generation configuration for every score-bearing schema
  0.3.0 log.
- Confirm the packaging worktree is clean before final export. The exporter
  fails closed otherwise because `source_commit` cannot represent uncommitted
  packaging changes.
- For HPC bundles, include the `RUN_ID`, `results/hpc/<RUN_ID>/aggregate_manifest.json`,
  Slurm array range, model matrix, task matrix, seed range, and aggregation
  command.

## Hugging Face export checks

Before uploading or tagging a metadata-only Hugging Face dataset snapshot,
generate and validate the export bundle:

```bash
uv run python scripts/export_hf_dataset.py \
  --out-dir build/hf_dataset \
  --release-name <release_name> \
  --no-results \
  --clean-output \
  --copy-plots
uv run python scripts/validate_hf_export.py build/hf_dataset
```

The CI HF export smoke follows this metadata-only path. It checks packaging and
manifest integrity but does not validate model scores. Metadata-only exports
must omit `result_rows.jsonl` and have an empty `eval_log_manifest.jsonl`.
Copied historical plots are visual assets only and do not make this a
score-bearing evidence bundle.

For a score-bearing schema 0.3.0 release, use a fresh output directory and an
explicit clean log bundle:

```bash
uv run python scripts/export_hf_dataset.py \
  --out-dir build/hf_scored_release \
  --release-name <release_name> \
  --log-dir results/<clean_log_bundle>
uv run python scripts/validate_hf_export.py build/hf_scored_release
```

Do not upload score-bearing bundles with empty `result_rows.jsonl`, checksum
mismatches, missing plot assets, dirty/incomplete evaluation revisions, or
empty/unpinned generation configuration. The exporter must fail rather than silently
omit a bad log.

Confirm that each eval-log-manifest path points to a raw `.eval` file bundled
under `eval_logs/`. If plots are included, pass explicit `--plot` files
generated from this log bundle; do not use the frozen default `--copy-plots`.

The exporter refuses a non-empty output directory. Prefer a new directory;
pass `--clean-output` only when deliberately replacing a disposable build
directory under `build/`. Never use it to rewrite an immutable release bundle
or HF tag.

Before performing a network upload, inspect the dry-run plan:

```bash
uv run python scripts/upload_hf_dataset.py \
  build/hf_dataset \
  --repo-id jang1563/LabCraft-Eval
```

Only upload after the plan matches the intended file set:

```bash
uv pip install 'huggingface-hub>=0.36,<1.0'
uv run python scripts/upload_hf_dataset.py \
  build/hf_dataset \
  --repo-id jang1563/LabCraft-Eval \
  --create-repo \
  --execute
```

An executed upload removes remote files absent from the manifest-backed plan in
the same commit, except for the Hub-managed `.gitattributes`. Confirm that this
exact-replacement behavior is intended for the target revision.

## Result bundle checks

- Frozen snapshot results should stay tied to `results/logs`,
  `results/results.md`, and the top-level scorecard plots.
- Treat the published v0.1.1 scorecard as historical/provisional evidence and
  preserve its generated tables and raw files unchanged. Integrity corrections
  belong in documentation, code, tests, and a new release rather than a silent
  rewrite.
- Newer wet-lab task bundles should remain in their `results/current_*`
  directories unless intentionally promoted.
- Discovery Decision Track bundles should remain in `results/discovery_*`.
- HPC-scale candidate bundles should remain under `results/hpc/<RUN_ID>/` until
  intentionally promoted into a named public result page.
- Do not call the HPC v0.2 or live Safety Case summary independently auditable
  until the raw run bundles are public and can be re-aggregated.
- Do not overwrite existing `.eval` logs when extending a seed range; use
  `SEED_START` and a separate `LOG_DIR` when needed.
