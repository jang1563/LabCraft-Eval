# Hugging Face Leaderboard Space Plan

This plan defines the optional interactive Hugging Face Space for
LabCraft-Eval. The Space should be a read-only visualization layer over the
exported dataset files, not a second benchmark implementation.

Live Space: <https://huggingface.co/spaces/jang1563/LabCraft-Eval-Leaderboard>

Source scaffold: [`spaces/leaderboard/`](../spaces/leaderboard/)

## Source Contract

The checked-in Space source supports two pinned, manifest-backed evidence tiers:

- `v0.1.2` — current metadata and task contracts; selected by default and
  intentionally score-free.
- `v0.1.1` — frozen historical provisional scores; available through the
  release/evidence selector.

Every supported release must provide:

- `release_manifest.json`
- `tasks.jsonl`

Score-bearing releases may additionally provide:

- `result_rows.jsonl`
- `eval_log_manifest.jsonl`
- `plots/scorecard.png`
- `plots/axis_heatmap.png`

It should not scrape GitHub Markdown pages or infer scores from prose. Every
displayed score should be traceable to `result_rows.jsonl` and the matching
manifest checksum. A metadata-only release must render a clear empty state and
must not display copied historical plots as current evidence.

## Minimum Views

| View | Purpose |
| --- | --- |
| Scorecard | Model by task mean score, grouped by benchmark track. |
| Axis heatmap | Per-axis score profile for decision quality, task success, troubleshooting, and efficiency. |
| Release/evidence selector | Separate current metadata contracts from historical provisional scores. |
| Seed variance | Per-model/per-task variance and sample count when score rows exist. |
| Provenance panel | Release name, source commit, schema version, manifest checksum, and result-row count. |
| Task inventory | Task id, track, domain, objective, and source-path links. |

## Interaction Rules

- Default to the current v0.1.2 metadata-only release.
- Keep v0.1.1 score-bearing views explicitly labelled historical and
  provisional.
- Keep current wet-lab, discovery, and safety-case tracks visually separated.
- Link each score table to the exact release manifest and source commit.
- Show row counts and missing-data warnings before plotting.
- Never merge Safety Case Track scores into wet-lab simulator leaderboards.

## Implementation Sketch

Use a small Gradio or Streamlit app:

1. Resolve only allowlisted release labels and file paths, with each label fixed
   to an immutable Hugging Face dataset commit and expected source manifest.
2. Download `release_manifest.json` first, then fetch only declared app inputs.
3. Validate byte counts, SHA-256 checksums, JSONL record counts, release name,
   and current-schema model provenance before rendering.
4. Load JSONL files with the standard library.
5. Build score tables only when `result_rows.jsonl` is manifest-declared.
6. Render plot files only for a score-bearing selected release.

The checked-in scaffold implements this selector with v0.1.2 as the default and
v0.1.1 as the historical score-bearing view. The live Space may lag the
checked-in behavior until the scaffold is explicitly uploaded and verified.
