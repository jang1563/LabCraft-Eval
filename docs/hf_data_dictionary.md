# Hugging Face Export Data Dictionary

The Hugging Face dataset export is a static, manifest-backed snapshot. It is
intended for inspection, lightweight analysis, and reproducible citation of
published result rows. It is not the executable benchmark runtime; use the
GitHub repository for code, tests, and reruns.

The existing v0.1.1 dataset is a frozen historical artifact and is not
retroactively rewritten. Its scores are provisional benchmark-development
evidence. Schema 0.3.0 is the contract for new exports and separates packaging
provenance, native evaluation provenance, and provider-resolved model identity.

The generated dataset card declares separate Hugging Face viewer configs for
the JSONL tables. Use the `result_rows` config for score analysis, and use
`tasks`, `rubrics`, `ground_truth`, `citations`, and `eval_log_manifest` for
audit context.

## Files

| File | Grain | Purpose |
| --- | --- | --- |
| `release_manifest.json` | One release | Packaging source commit, schema version, evaluation-provenance policy, file checksums, byte counts, and record counts. |
| `tasks.jsonl` | One row per task | Task inventory, track assignment, title, domain, objective, source paths, and license split. |
| `rubrics.jsonl` | One row per task with a rubric | Full checked-in rubric JSON payload for audit and downstream parsing. |
| `ground_truth.jsonl` | One row per task with ground truth | Full checked-in ground-truth JSON payload used by deterministic scorers. |
| `citations.jsonl` | One row per citation object | Extracted citation objects from task and parameter files, with source file and JSON path. |
| `eval_log_manifest.jsonl` | One row per included `.eval` log | Log checksum, requested/resolved identity, provider, Inspect version, native revision, effective generation configuration, status, and sample count. Empty in metadata-only exports. |
| `result_rows.jsonl` | One row per deduplicated scored sample | Published model/task/sample scores and provenance for reported result rows. |
| `eval_logs/` | One file per distinct included raw log | Bundled Inspect evidence addressed by `eval_log_manifest.jsonl.path` and covered by the release manifest. |
| `plots/` | One file per copied plot | PNG scorecards and heatmaps for quick visual review. |

## Common Fields

Most JSONL records include:

| Field | Meaning |
| --- | --- |
| `schema_version` | Export schema version for the record shape. |
| `source_commit` | Packaging HEAD commit recorded by the exporter. It is not necessarily the revision that produced an evaluation; release publishers must separately ensure the packaging worktree is clean. |
| `task_id` or `task` | LabCraft-Eval task identifier. |
| `track` | One of `snapshot`, `current_wet_lab`, `followup`, `discovery`, `safety_case`, or `other`. |

## Result Row Fields

`result_rows.jsonl` is the main table for machine consumers of published
scores.

| Field | Meaning |
| --- | --- |
| `model` | Compatibility alias for `requested_model`. |
| `requested_model` | Model ID requested through Inspect. |
| `resolved_model` | Model ID returned by the provider and recorded in the Inspect sample output. |
| `provider` | Provider inferred from the qualified request ID and checked against the resolved model. |
| `task` | Task identifier. |
| `track` | Track classification derived from the task id. |
| `status` | Inspect sample status. |
| `sample_id` | Seeded sample identifier. |
| `eval_log` | Source `.eval` filename. |
| `eval_log_path` | Bundle-relative path to the raw file under `eval_logs/`. |
| `source_eval_log_path` | Portable repo-relative source label, or filename when the original log lived outside the checkout. |
| `created` | Timestamp extracted from the Inspect log when available. |
| `evaluation_revision` | Native Inspect revision object from the source `.eval` log: `type`, `origin`, `commit`, and `dirty`. Schema 0.3.0 requires `dirty: false`. |
| `model_generate_config` | Generation settings recorded by Inspect for the source sample/log. |
| `effective_generation_config` | Non-empty generation configuration recorded by Inspect and checked against `model_generate_config`. |
| `inspect_version` | Inspect version recorded in native log package metadata. |
| `tokens` | Per-sample token accounting object when available. |
| `scores` | Object containing numeric score axes, usually including overall and per-axis values. |

## Packaging Versus Evaluation Provenance

`source_commit` answers “which repository revision assembled this export?”
`evaluation_revision.commit` answers “which code revision did Inspect record
when the evaluation ran?” These values may legitimately differ. A consumer
must retain both rather than relabelling historical scores with the packaging
commit.

Schema 0.3.0 also records `packaging_worktree_dirty: false`; the exporter
refuses to create the bundle if tracked or untracked packaging changes are not
committed.

For schema 0.3.0 score-bearing exports:

- every included `.eval` log must be successful;
- no included sample may record an Inspect evaluation-limit exhaustion;
- every native `evaluation_revision` must be complete and have `dirty: false`;
- `model_generate_config` must be a non-empty object with explicitly recorded
  generation settings;
- every result row must include non-empty requested/resolved model IDs,
  provider, effective generation configuration, and Inspect version;
- every requested ID must be registered in `config/model_matrix.toml`, and the
  provider/resolved ID must match that registry entry (with optional provider
  qualification on the resolved ID);
- result-row identity fields and effective configuration must match the
  corresponding `eval_log_manifest.jsonl` record;
- one requested alias must not resolve to multiple model snapshots in a single
  export;
- every raw `.eval` file must be bundled under `eval_logs/` and covered by both
  the eval-log manifest and release manifest;
- `result_rows.jsonl` must be non-empty; and
- `release_manifest.json.evaluation_provenance` records the clean-only policy,
  log count, zero dirty-log count, and the distinct evaluation commits.

If suitable clean logs are not available, use a metadata-only export with
`--no-results`. That path intentionally omits `result_rows.jsonl` and writes an
empty `eval_log_manifest.jsonl`; it validates benchmark packaging, not model
scores. The public CI export smoke uses this metadata-only path.

## Audit Pattern

1. Read `release_manifest.json`.
2. Check the manifest packaging `source_commit` and `schema_version`.
3. Verify the target file's SHA-256 and record count.
4. If present, load `result_rows.jsonl` for scores. Its absence identifies a
   metadata-only export.
5. Use `eval_log_manifest.jsonl` to map reported rows back to source logs and
   verify the clean native `evaluation_revision` and generation settings.
6. Use `tasks.jsonl`, `rubrics.jsonl`, and `ground_truth.jsonl` to inspect the
   task contract behind a score.
7. Keep tracks separate when aggregating results; the Safety Case Track and
   wet-lab simulator tracks use different score semantics.
8. Treat the frozen v0.1.1 score rows as historical/provisional; do not infer
   schema 0.3.0 clean and model-provenance guarantees for that older release.
