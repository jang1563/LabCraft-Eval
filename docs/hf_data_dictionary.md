# Hugging Face Export Data Dictionary

The Hugging Face dataset export is a static, manifest-backed snapshot. It is
intended for inspection, lightweight analysis, and reproducible citation of
published result rows. It is not the executable benchmark runtime; use the
GitHub repository for code, tests, and reruns.

## Files

| File | Grain | Purpose |
| --- | --- | --- |
| `release_manifest.json` | One release | Source commit, schema version, file checksums, byte counts, and record counts. |
| `tasks.jsonl` | One row per task | Task inventory, track assignment, title, domain, objective, source paths, and license split. |
| `rubrics.jsonl` | One row per task with a rubric | Full checked-in rubric JSON payload for audit and downstream parsing. |
| `ground_truth.jsonl` | One row per task with ground truth | Full checked-in ground-truth JSON payload used by deterministic scorers. |
| `citations.jsonl` | One row per citation object | Extracted citation objects from task and parameter files, with source file and JSON path. |
| `eval_log_manifest.jsonl` | One row per included `.eval` log | Log path, log directory, filename, byte count, and SHA-256 checksum. |
| `result_rows.jsonl` | One row per deduplicated scored sample | Published model/task/sample scores and provenance for reported result rows. |
| `plots/` | One file per copied plot | PNG scorecards and heatmaps for quick visual review. |

## Common Fields

Most JSONL records include:

| Field | Meaning |
| --- | --- |
| `schema_version` | Export schema version for the record shape. |
| `source_commit` | GitHub commit SHA used to generate that record. |
| `task_id` or `task` | LabCraft-Eval task identifier. |
| `track` | One of `snapshot`, `current_wet_lab`, `followup`, `discovery`, `safety_case`, or `other`. |

## Result Row Fields

`result_rows.jsonl` is the main table for machine consumers of published
scores.

| Field | Meaning |
| --- | --- |
| `model` | Model identifier reported by Inspect. |
| `task` | Task identifier. |
| `track` | Track classification derived from the task id. |
| `status` | Inspect sample status. |
| `sample_id` | Seeded sample identifier. |
| `eval_log` | Source `.eval` filename. |
| `eval_log_path` | Repo-relative path to the source `.eval` log. |
| `created` | Timestamp extracted from the Inspect log when available. |
| `tokens` | Token accounting object when available. |
| `scores` | Object containing numeric score axes, usually including overall and per-axis values. |

## Audit Pattern

1. Read `release_manifest.json`.
2. Check the manifest `source_commit` and `schema_version`.
3. Verify the target file's SHA-256 and record count.
4. Load `result_rows.jsonl` for scores.
5. Use `eval_log_manifest.jsonl` to map reported rows back to source logs.
6. Use `tasks.jsonl`, `rubrics.jsonl`, and `ground_truth.jsonl` to inspect the
   task contract behind a score.
