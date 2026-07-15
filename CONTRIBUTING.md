# Contributing to LabCraft-Eval

Thanks for helping improve LabCraft-Eval. This repository is both research
software and benchmark content, so changes need to preserve reproducibility,
provenance, and safety scope.

## Contribution Types

Useful contributions include:

- Fixing simulator, scoring, packaging, or documentation bugs.
- Improving tests for deterministic behavior, scoring edge cases, citations, or
  safety scope.
- Adding benign BSL-1/BSL-2 task surfaces that fit `SAFETY.md`.
- Improving machine-readable exports and release manifests.
- Improving result analysis without overwriting published result bundles.

## Safety Scope

Before proposing new biological content, read `SAFETY.md`.

LabCraft-Eval is limited to benign BSL-1/BSL-2 work and excludes select agents,
BSL-3/4 organisms, viral work, gain-of-function, toxins, virulence factors,
dual-use optimization language, and content intended to increase harmful
biological capability.

Every new task, reagent, parameter, threshold, and ground-truth value must trace
to public citable sources. Private lab notes and unsourced protocol lore are not
acceptable benchmark provenance.

## Development Setup

```bash
git clone https://github.com/jang1563/LabCraft-Eval.git
cd LabCraft-Eval
uv sync --extra dev --extra analysis
```

If you do not use `uv`, install the package in editable mode with the
development extras:

```bash
pip install -e ".[dev,analysis]"
```

## Expected Checks

For public releases, the full verification path belongs on the configured HPC
environment described in `docs/hpc_plan.md`.

For normal pull requests, run the smallest relevant local checks you can:

```bash
uv run ruff check .
uv run pytest tests/test_citations.py tests/test_scope_compliance.py tests/test_inspect_task.py
uv run python scripts/validate_scorer_contracts.py
uv run pytest
uv run python scripts/export_hf_dataset.py \
  --out-dir build/hf_export_smoke \
  --release-name smoke \
  --copy-plots
uv run python scripts/validate_hf_export.py build/hf_export_smoke
uv run python scripts/upload_hf_dataset.py \
  build/hf_export_smoke \
  --repo-id jang1563/LabCraft-Eval
```

The dry-run upload helper has no network side effects. Actual upload with
`--execute` requires `huggingface-hub>=0.36,<1.0` in the active environment.

The default scorer-contract validator checks deterministic technical
conformance. A release or change that claims expert-approved P1 fixtures must
also pass
`uv run python scripts/validate_scorer_contracts.py --require-expert-approved`;
it is expected to fail while the corpus remains a draft.

Do not run API-backed Inspect evaluations in CI or casual pull requests unless
the change explicitly requires it.

## Adding or Editing Tasks

Each task should include:

- `src/tasks/<task_id>.py`
- `task_data/<task_id>/rubric.json`
- `task_data/<task_id>/ground_truth.json`
- `task_data/<task_id>/SOURCES.md`
- Tests that cover task registration, rubric loading, citation compliance, and
  scorer behavior.

Keep task IDs stable once result bundles have been published. If a behavioral
change would invalidate old numbers, create a new task ID or document the scorer
version change in `CHANGELOG.md`.

## Result Bundle Rules

- Do not overwrite historical `.eval` logs or published result Markdown.
- Put new HPC-scale runs under `results/hpc/<RUN_ID>/` until intentionally
  promoted.
- Every reported number should cite commit SHA, log/result directory, task
  matrix, model matrix, seed range, aggregation command, and scorer version.
- Keep the Safety Case Track separate from wet-lab simulator leaderboards.

## Pull Request Checklist

- The change fits the scope in `SAFETY.md`.
- New or changed benchmark content has public citations.
- Relevant tests were added or updated.
- Machine-readable schema/export changes are documented.
- Public-facing behavior changes are noted in `CHANGELOG.md`.
