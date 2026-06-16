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
- Keep `labcraft_suite()` as a single-task smoke alias unless a future breaking
  release introduces a real cross-task Inspect orchestration layer.

## Required checks

Run these checks on HPC for compute-constrained development. Do not use a local
laptop as the source of release verification when the project is in HPC-only
execution mode.

```bash
uv run pytest
uv run pytest tests/test_citations.py tests/test_scope_compliance.py tests/test_inspect_task.py
```

## Metadata checks

- Confirm [CITATION.cff](../CITATION.cff) has the intended version and release
  date.
- Confirm [README.md](../README.md), [NOTICE](../NOTICE), [LICENSE](../LICENSE),
  and [LICENSE-DATA](../LICENSE-DATA) describe the same licensing split.
- Confirm [pyproject.toml](../pyproject.toml) metadata points to the current
  repository and issue tracker.
- Confirm the Hugging Face dataset has a tag matching the GitHub release tag
  and that its `release_manifest.json` source commit matches the release notes.
- Include the commit SHA and log/result directory when reporting benchmark
  numbers.
- For HPC bundles, include the `RUN_ID`, `results/hpc/<RUN_ID>/aggregate_manifest.json`,
  Slurm array range, model matrix, task matrix, seed range, and aggregation
  command.

## Hugging Face export checks

Before uploading or tagging a Hugging Face dataset snapshot, generate and
validate the export bundle:

```bash
uv run python scripts/export_hf_dataset.py \
  --out-dir build/hf_dataset \
  --release-name <release_name> \
  --copy-plots
uv run python scripts/validate_hf_export.py build/hf_dataset
```

Do not upload bundles with empty `result_rows.jsonl`, checksum mismatches, or
missing plot assets.

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

## Result bundle checks

- Frozen snapshot results should stay tied to `results/logs`,
  `results/results.md`, and the top-level scorecard plots.
- Newer wet-lab task bundles should remain in their `results/current_*`
  directories unless intentionally promoted.
- Discovery Decision Track bundles should remain in `results/discovery_*`.
- HPC-scale candidate bundles should remain under `results/hpc/<RUN_ID>/` until
  intentionally promoted into a named public result page.
- Do not overwrite existing `.eval` logs when extending a seed range; use
  `SEED_START` and a separate `LOG_DIR` when needed.
