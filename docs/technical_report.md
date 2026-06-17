# LabCraft-Eval Technical Report

Version: v0.1.1

## Abstract

LabCraft-Eval is a compact Inspect AI benchmark for evaluating whether language
model agents can execute benign molecular-microbiology workflows inside a
seeded stochastic simulator. The benchmark combines public protocol prompts,
tool-mediated lab operations, citation-backed task metadata, and deterministic
four-axis trajectory scoring. The v0.1.1 public release includes a frozen
five-task simulator snapshot, newer wet-lab task surfaces, a Discovery Decision
Track, and a separate Safety Case Track.

## Motivation

Many model evaluations over biological protocols score final answers or static
question-answering behavior. LabCraft-Eval instead scores the full agent
trajectory: planning, tool calls, observations, interpretation, and final
reporting. This makes failure modes visible when a model reaches a plausible
answer through poor experimental decisions, or when it uses reasonable tools but
fails to diagnose uncertainty.

## Benchmark Design

Each runnable task exposes a protocol prompt, a fixed tool set, seeded
stochastic state, citation-backed ground truth, and a hierarchical rubric. The
agent interacts with lab operations such as media preparation, transformation,
incubation, measurement, assembly, purification, or decision-support tools. The
simulator returns observations, and Inspect records the complete `.eval`
trajectory.

## Scoring

The simulator tasks are scored along four deterministic axes:

| Axis | Definition |
| --- | --- |
| Decision quality | Whether key tool-call choices match the ground-truth decision points. |
| Task success | Whether the trajectory and final answer satisfy the task objective. |
| Troubleshooting | Whether the answer recognizes relevant failures, uncertainty, or limitations. |
| Efficiency | Whether the agent makes progress with a reasonable number of tool calls. |

The Safety Case Track uses a separate conversational safeguard scorer and is not
merged into the wet-lab simulator leaderboard.

## Public Results

The frozen v0.1 scorecard reports 100 scored sample rows across five simulator
tasks, four frontier models, and five stochastic seeds. Newer task bundles,
discovery-decision results, HPC candidate bundles, and safety-case results are
reported on separate result pages to avoid changing the historical snapshot.

Key public surfaces:

- `results/results.md` for the frozen scorecard.
- `results/analysis.md` for failure-mode analysis.
- `results/discovery_track.md` for discovery-decision results.
- `results/hpc_v0_2_current_n10.md` for the larger HPC candidate bundle.
- `results/safety_case_live_v0_2.md` for live Safety Case Track results.

## Reproducibility

The GitHub repository is the source of truth for code, tests, task definitions,
scorers, and release history. The Hugging Face dataset provides a
machine-readable snapshot with JSONL files, plots, and `release_manifest.json`.
The manifest records the source commit, schema version, byte counts, record
counts, and SHA-256 checksums for each exported artifact.

Minimum local checks:

```bash
uv run pytest
uv run python scripts/export_hf_dataset.py --out-dir build/hf_dataset --release-name local_export --copy-plots
uv run python scripts/validate_hf_export.py build/hf_dataset
```

## Safety Scope

LabCraft-Eval is intentionally scoped to benign BSL-1/BSL-2 educational and
research-support workflows. It is not a harmful-biology capability benchmark,
not a substitute for wet-lab validation, and not evidence of real-world
experimental competence. Safety scope and reporting guidance are maintained in
`SAFETY.md` and `SECURITY.md`.

## Limitations

- The simulator is citation-backed but not physically grounded in a real lab.
- The frozen scorecard is intentionally compact and should not be overread as a
  broad model capability ranking.
- Current task bundles and HPC candidates are reported separately until they are
  intentionally promoted into a new release.
- Human baseline work is early and should be treated as calibration support,
  not a final expert reference distribution.

## Citation

If you use LabCraft-Eval, cite the repository URL, the source commit SHA, and
the release manifest or result bundle used. For v0.1.1, use the GitHub release
and Hugging Face dataset tag that share the same manifest-backed snapshot.
