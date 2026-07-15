# Hugging Face Release Plan

This document defines the intended Hugging Face packaging for LabCraft-Eval.
GitHub remains the source of truth for code, tests, methodology, and issue
tracking. Hugging Face should expose a clean benchmark-data surface that can be
loaded without scraping Markdown result pages.

The public v0.1.1 dataset remains a frozen historical artifact. Its result
rows preserve the original provenance limitations and are provisional
benchmark-development evidence. They also predate removal of answer-bearing
agent guidance, so they are not leakage-free current-task results. Schema 0.3.0
applies to new exports; do not silently rewrite or retag v0.1.1 as though it
met the new clean-evaluation contract.

The v0.1.2 Hub snapshot is a metadata-only release of the current task, schema,
citation, and manifest contracts. It intentionally omits score rows and raw
evaluation logs. The frozen v0.1.1 tag remains available for the historical
score-bearing artifact, while new scored releases must satisfy the schema 0.3.0
clean-provenance contract.

## Repository Layout

Recommended dataset repository files:

```text
README.md
release_manifest.json
tasks.jsonl
rubrics.jsonl
ground_truth.jsonl
citations.jsonl
result_rows.jsonl  # score-bearing exports only
eval_log_manifest.jsonl
eval_logs/          # raw evidence for score-bearing exports
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
  --no-results \
  --clean-output \
  --copy-plots
uv run python scripts/validate_hf_export.py build/hf_dataset
```

This is a metadata-only export: it packages task contracts, citations, optional
historical plot assets, and a manifest without publishing structured score
rows. CI uses this path because the smoke job is intended to validate packaging
rather than provide an evaluation evidence bundle. Copying a frozen plot does
not grant it schema 0.3 score provenance.

For a schema 0.3.0 score-bearing export, point explicitly to a directory of
successful, clean Inspect logs:

```bash
uv run python scripts/export_hf_dataset.py \
  --out-dir build/hf_scored_release \
  --release-name <release_name> \
  --log-dir results/<clean_log_bundle>
uv run python scripts/validate_hf_export.py build/hf_scored_release
```

The exporter rejects a dirty packaging worktree, dirty or incomplete native
evaluation revisions, empty/unpinned generation configuration, unregistered
requested model IDs, and provider/resolved identities that disagree with
`config/model_matrix.toml`. It bundles the raw `.eval` files under `eval_logs/`
so the public release contains its evidence. It also refuses
to write into a non-empty output directory. Use a new directory by default;
use `--clean-output` only when intentionally replacing a disposable export
directory under `build/` after checking its path.

Do not use `--copy-plots` for a scored release because that selects the frozen
v0.1.1 defaults. Either omit plots or pass one or more explicit `--plot` files
generated from the same clean log bundle.

Use `--plot path/to/plot.png` to export a custom plot set instead of the
default frozen snapshot scorecard and heatmap.

Do not upload an export bundle that fails validation. The validator checks
manifest checksums, byte counts, JSONL record counts, required record fields,
non-empty result rows when result export is enabled, consistency between result
rows and log-manifest rows, clean native evaluation provenance, and exact
registered model-resolution expectations.

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

Executed uploads are exact manifest replacements: the helper removes remote
files absent from the local upload plan in the same commit, while preserving
the Hub-managed `.gitattributes`. This prevents an older `result_rows.jsonl` or
plot from surviving a metadata-only or corrected release upload.

## Consumer Quickstart

The repository includes a no-dependency example that reads the public dataset
files from Hugging Face or an existing local export directory:

```bash
python3 examples/hf_quickstart.py
python3 examples/hf_quickstart.py --snapshot-dir build/hf_dataset
```

For notebook or analysis workflows that already use `huggingface_hub`, pin the
release, inspect the manifest first, and treat result rows as optional:

```python
import json
from pathlib import Path

from huggingface_hub import snapshot_download

snapshot_dir = Path(
    snapshot_download(
        "jang1563/LabCraft-Eval",
        repo_type="dataset",
        revision="v0.1.2",
    )
)
manifest = json.loads((snapshot_dir / "release_manifest.json").read_text())
manifest_paths = {entry["path"] for entry in manifest["files"]}
tasks = [json.loads(line) for line in (snapshot_dir / "tasks.jsonl").open()]
results = (
    [json.loads(line) for line in (snapshot_dir / "result_rows.jsonl").open()]
    if "result_rows.jsonl" in manifest_paths
    else []
)
```

`result_rows.jsonl` is absent from metadata-only exports. Consumers should
check the manifest/file list rather than assuming every snapshot publishes
scores.

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

- A clean GitHub packaging HEAD SHA stored as `source_commit`.
- A GitHub tag or release, when available.
- A matching Hugging Face dataset tag created from the uploaded snapshot commit.
- A `release_manifest.json` generated by that packaging commit.
- For score-bearing schema 0.3.0 releases, the clean native Inspect
  `evaluation_revision`, requested/resolved model identity, provider, Inspect
  version, and recorded generation configuration for every log.
- A named result bundle such as `v0.1_frozen_snapshot` or `hpc_v0_2_current_n10`.

`source_commit` describes export packaging. `evaluation_revision.commit`
describes the code recorded when a model evaluation ran. They may differ, and
release notes must report both rather than presenting the packaging commit as
the evaluation revision.

Do not overwrite existing HF tags. Publish corrected bundles with a new patch
tag and a changelog entry.

Do not promote the HPC v0.2 candidate or live Safety Case summary as an
independently auditable scored release until its raw logs are published and
pass the schema 0.3.0 clean and model-provenance checks. Aggregate Markdown alone is not
a score-bearing release bundle.

After uploading the dataset snapshot, verify the Hub refs and create the
matching dataset tag before announcing the release. The tag should point at the
Hub commit that contains the exported files for that release, not a later
working commit.

## Leaderboard Space

The optional HF Space should read only the exported files, not arbitrary GitHub
Markdown pages. The checked-in scaffold defaults to the current v0.1.2
metadata-only contract and exposes v0.1.1 in a separately labelled historical,
provisional score-bearing view. Each allowlisted release label is fixed to an
immutable dataset commit and expected source manifest. Minimum views:

- Release and evidence-tier selector.
- Model x task scorecard.
- Per-axis heatmap.
- Seed variance table.
- Track selector.
- Manifest and source-commit panel.

Each displayed number should link to the matching release manifest and result
row source.

The live Space may lag this checked-in behavior until the scaffold is explicitly
uploaded and verified.

Current Space:

- Live app: <https://huggingface.co/spaces/jang1563/LabCraft-Eval-Leaderboard>
- Source scaffold: [`spaces/leaderboard/`](../spaces/leaderboard/)
