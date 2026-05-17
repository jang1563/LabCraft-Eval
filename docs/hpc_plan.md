# HPC-Only v0.2 Plan

Prepared: 2026-05-16

This plan treats the local machine as an editing and review surface only.
Benchmark execution, aggregation, plotting, tests, and package builds belong on
HPC. The aim is to turn BioProtocolBench from a public v0.1 snapshot into a
larger, reproducible v0.2 result bundle without overwriting the frozen April
2026 scorecard.

Current run status is tracked separately in
[docs/hpc_v0_2_status.md](hpc_v0_2_status.md).

## Operating Rules

- Local allowed: code/document edits, git status/diff/log, source inspection,
  remote metadata checks, and small text searches.
- Local avoided: `pytest`, `ruff`, build commands, Inspect evaluation,
  aggregation over `.eval` logs, plotting, and package verification.
- HPC required: all tests, all benchmark runs, result aggregation, plot
  generation, release verification, and any API-backed evaluation.
- Provider clients (`openai`, `anthropic`) are installed in the HPC venv by
  [hpc/slurm_setup_env.sh](../hpc/slurm_setup_env.sh); missing provider extras
  should be fixed in the setup job rather than ad hoc in evaluation jobs.
- On Cayuga, load `slurm/25.05.0` before `sbatch`; the default `/usr/bin/sbatch`
  may be an incompatible older client.
- Result bundles must be append-only. Use a new `RUN_ID` unless intentionally
  repairing or extending the same bundle.
- Every reported number must cite commit SHA, log directory, task matrix, model
  matrix, seed range, and aggregation command.

## Execution Phases

### Phase 1: Cluster Smoke

Goal: prove the HPC environment, Python environment, API keys, and Slurm wrapper
all work.

Matrix:

- Tasks: `growth_01 perturb_followup_01`
- Models: `openai/gpt-4o-mini`
- Seeds: 1
- Expected array size: 2

Command:

```bash
mkdir -p results/hpc/slurm

RUN_ID=2026_05_hpc_smoke \
TASKS="growth_01 perturb_followup_01" \
SEEDS_TOTAL=1 \
MODELS="openai/gpt-4o-mini" \
sbatch --array=0-1%1 hpc/slurm_eval_array.sh
```

Aggregate:

```bash
mkdir -p results/hpc/slurm

RUN_ID=2026_05_hpc_smoke \
TASK_PRESET=auto \
MODELS="openai/gpt-4o-mini" \
sbatch hpc/slurm_aggregate.sh
```

### Phase 2: v0.2 Candidate N=10

Goal: create a stable larger-seed bundle while keeping wet-lab execution and
discovery decision results separable.

Wet-lab/current matrix:

- `TASK_PRESET=current`
- 11 tasks
- 4 frontier models
- 10 seeds
- Array size: 440

Discovery matrix:

- `TASK_PRESET=discovery`
- 3 tasks
- 4 frontier models
- 10 seeds
- Array size: 120

Run as two bundles so downstream analysis can discuss protocol execution and
discovery decisions independently.

### Phase 3: Prompt Sensitivity Sweep

Goal: turn the current one-off `growth_01` ablation into a proper sensitivity
curve.

Candidate variants:

- default prompt
- explicit troubleshooting-warning prompt
- structured final-answer schema prompt
- concise warning plus schema prompt
- high-reasoning narrative prompt

Implementation should keep prompt variants under separate task IDs or an
explicit task parameter so the logs remain auditable. Do not merge these results
into the main leaderboard; report them as a prompt-sensitivity analysis.

### Phase 4: Human Baseline Pilot

Goal: add a reviewer-facing anchor point without pretending to have a large
human study.

Minimum viable design:

- Tasks: `transform_01`, `growth_01`, and one discovery task
- Seeds: 3-5 per task
- Participants: one domain expert first; two if feasible
- Output: a pilot result table with confidence caveats, not a leaderboard

Use the existing human-baseline CLI and aggregate on HPC.

### Phase 5: v0.2 Release Candidate

Promote only after the following are complete on HPC:

- Full test suite
- Citation/scope focused tests
- v0.2 candidate aggregation and plots
- Positioning document updated for May 2026 literature
- Release checklist updated with HPC bundle metadata
- GitHub release notes include commit SHA, run IDs, and exact matrices

## Recommended Public Framing

BioProtocolBench should not claim to compete with large bioinformatics agent
benchmarks on breadth. The defensible v0.2 claim is narrower:

> BioProtocolBench is a compact, reproducible, interactive benchmark for benign
> wet-lab protocol execution and discovery-decision reliability. Its distinctive
> contribution is seeded stochastic simulation plus deterministic multi-axis
> trajectory scoring.

This keeps the project complementary to LABBench2, BixBench, BioAgent Bench,
BioMysteryBench, CompBioBench, GeneBench, and PromptBio-Bench rather than
overclaiming against them.
