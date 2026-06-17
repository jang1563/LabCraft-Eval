# Hugging Face Release Plan

This document defines the intended Hugging Face packaging for LabCraft-Eval.
GitHub remains the source of truth for code, tests, methodology, and issue
tracking. Hugging Face should expose a clean benchmark-data surface that can be
loaded without scraping Markdown result pages.

## Repository Layout

Recommended dataset repository files:

```text
README.md
release_manifest.json
tasks.jsonl
rubrics.jsonl
ground_truth.jsonl
citations.jsonl
result_rows.jsonl
eval_log_manifest.jsonl
plots/
  scorecard.png
  axis_heatmap.png
```

The first export implementation writes JSONL, a dataset-card `README.md`, an
optional `plots/` directory, and a manifest. Parquet files can be added later
once the field contracts settle.

The generated dataset card now declares separate Hugging Face viewer configs
for each JSONL table. This keeps the public Hub surface readable for humans
while preserving machine-friendly schemas for tasks, rubrics, ground truth,
citations, eval-log manifests, and result rows.

Recommended local export:

```bash
uv run python scripts/export_hf_dataset.py \
  --out-dir build/hf_dataset \
  --release-name local_export \
  --copy-plots
uv run python scripts/validate_hf_export.py build/hf_dataset
```

Use `--plot path/to/plot.png` to export a custom plot set instead of the
default frozen snapshot scorecard and heatmap.

Do not upload an export bundle that fails validation. The validator checks
manifest checksums, byte counts, JSONL record counts, required record fields,
and non-empty result rows when result export is enabled.

Prepare an upload dry-run:

```bash
uv run python scripts/upload_hf_dataset.py \
  build/hf_dataset \
  --repo-id jang1563/LabCraft-Eval
```

The upload helper validates the export before planning files. It does not write
to Hugging Face unless `--execute` is passed:

```bash
uv run python scripts/upload_hf_dataset.py \
  build/hf_dataset \
  --repo-id jang1563/LabCraft-Eval \
  --create-repo \
  --execute
```

Install `huggingface-hub>=0.36,<1.0` in the active environment before using
`--execute`. Avoid `huggingface-hub` 1.x in this v0.1.x environment because it
can pull a `click` version outside Inspect AI's supported range.
Authentication should come from the standard Hugging Face token mechanisms; do
not commit tokens or `.env` files.

## Consumer Quickstart

The repository includes a no-dependency example that reads the public dataset
files from Hugging Face or an existing local export directory:

```bash
python3 examples/hf_quickstart.py
python3 examples/hf_quickstart.py --snapshot-dir build/hf_dataset
```

For notebook or analysis workflows that already use `huggingface_hub`, load the
full snapshot and then parse the JSONL files:

```python
import json
from pathlib import Path

from huggingface_hub import snapshot_download

snapshot_dir = Path(snapshot_download("jang1563/LabCraft-Eval", repo_type="dataset"))
tasks = [json.loads(line) for line in (snapshot_dir / "tasks.jsonl").open()]
results = [json.loads(line) for line in (snapshot_dir / "result_rows.jsonl").open()]
```

## Dataset Card Sections

The export script generates a first-pass dataset card. Before public upload,
review the generated `README.md` for release-specific wording and links.

The Hugging Face dataset card should include:

- YAML metadata: license, tags, task categories, language, pretty name, and
  source repository.
- Dataset viewer configs that map each JSONL file to its own named config.
- Dataset summary.
- Benchmark tracks and task inventory.
- Data files and field descriptions.
- Link or inline summary for the Hugging Face export data dictionary.
- Intended use.
- Out-of-scope use.
- Safety scope.
- Provenance and manifest-verification instructions.
- Citation and license split.
- Reproducibility instructions.
- Known limitations.
- Contact and issue-reporting links.

## Suggested Tags

```yaml
pretty_name: LabCraft-Eval
language:
  - en
license: cc-by-nc-4.0
tags:
  - benchmark
  - agent-evaluation
  - inspect-ai
  - bioinformatics
  - microbiology
  - synthetic-data
  - stochastic-simulation
  - tabular
task_categories:
  - text-generation
  - question-answering
configs:
  - config_name: tasks
    data_files:
      - split: data
        path: tasks.jsonl
  - config_name: result_rows
    data_files:
      - split: data
        path: result_rows.jsonl
```

The dataset metadata uses `cc-by-nc-4.0` because the uploaded benchmark content
is under CC BY-NC 4.0. The code remains Apache-2.0 in GitHub; explain the
dual-license split in prose because the Hub metadata field is not expressive
enough to attach different licenses to different subtrees.

## Versioning

Every HF release should correspond to:

- A GitHub commit SHA.
- A GitHub tag or release, when available.
- A matching Hugging Face dataset tag created from the uploaded snapshot commit.
- A `release_manifest.json` generated from that exact commit.
- A named result bundle such as `v0.1_frozen_snapshot` or `hpc_v0_2_current_n10`.

Do not overwrite existing HF tags. Publish corrected bundles with a new patch
tag and a changelog entry.

After uploading the dataset snapshot, verify the Hub refs and create the
matching dataset tag before announcing the release. The tag should point at the
Hub commit that contains the exported files for that release, not a later
working commit.

## Leaderboard Space

The optional HF Space should read only the exported files, not arbitrary GitHub
Markdown pages. Minimum views:

- Model x task scorecard.
- Per-axis heatmap.
- Seed variance table.
- Track selector.
- Manifest and source-commit panel.

Each displayed number should link to the matching release manifest and result
row source.

Current Space:

- Live app: <https://huggingface.co/spaces/jang1563/LabCraft-Eval-Leaderboard>
- Source scaffold: [`spaces/leaderboard/`](../spaces/leaderboard/)
