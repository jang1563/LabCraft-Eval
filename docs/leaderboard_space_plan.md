# Hugging Face Leaderboard Space Plan

This plan defines the optional interactive Hugging Face Space for
LabCraft-Eval. The Space should be a read-only visualization layer over the
exported dataset files, not a second benchmark implementation.

## Source Contract

The Space must read only these files from the Hugging Face dataset snapshot:

- `release_manifest.json`
- `tasks.jsonl`
- `result_rows.jsonl`
- `eval_log_manifest.jsonl`
- `plots/scorecard.png`
- `plots/axis_heatmap.png`

It should not scrape GitHub Markdown pages or infer scores from prose. Every
displayed score should be traceable to `result_rows.jsonl` and the matching
manifest checksum.

## Minimum Views

| View | Purpose |
| --- | --- |
| Scorecard | Model by task mean score, grouped by benchmark track. |
| Axis heatmap | Per-axis score profile for decision quality, task success, troubleshooting, and efficiency. |
| Seed variance | Per-model/per-task variance and sample count. |
| Provenance panel | Release name, source commit, schema version, manifest checksum, and result-row count. |
| Task inventory | Task id, track, domain, objective, and source-path links. |

## Interaction Rules

- Default to the frozen simulator snapshot.
- Keep current wet-lab, discovery, and safety-case tracks visually separated.
- Link each score table to the exact release manifest and source commit.
- Show row counts and missing-data warnings before plotting.
- Never merge Safety Case Track scores into wet-lab simulator leaderboards.

## Implementation Sketch

Use a small Gradio or Streamlit app:

1. Download the pinned dataset snapshot with `huggingface_hub.snapshot_download`.
2. Validate `release_manifest.json` record counts before rendering.
3. Load JSONL files with the standard library or pandas.
4. Build score tables from `result_rows.jsonl`.
5. Render copied plot files as static visual anchors.

The first Space version can be static and pinned to `v0.1.1`. A later version
can add a release selector once multiple manifest-backed snapshots exist.
