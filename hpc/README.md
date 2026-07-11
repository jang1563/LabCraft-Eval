# LabCraft-Eval HPC Workflow

This directory contains the recommended HPC-only execution surface for
LabCraft-Eval. Local machines should be used for editing, review, and git
operations only; tests, builds, Inspect runs, aggregation, and plotting should be
submitted to the cluster.

The scripts are intentionally generic Slurm wrappers. Set site-specific account,
partition, time, and environment setup through `SBATCH_*` flags and environment
variables rather than editing benchmark logic.

## One-Time Setup

Clone or sync the repository on the HPC filesystem, then create a Python
environment with the project installed:

```bash
cd /path/to/LabCraft-Eval
python3.13 -m venv /path/to/labcraft-py313
/path/to/labcraft-py313/bin/python -m pip install -e ".[dev,analysis,providers]"
```

If the cluster already has a prepared environment, point the scripts at it:

```bash
export PYTHON_BIN=/path/to/labcraft-py313/bin/python
export INSPECT_BIN=/path/to/labcraft-py313/bin/inspect
```

Or submit the setup helper on HPC:

```bash
mkdir -p results/hpc/slurm
VENV_DIR=/home/fs01/jak4013/labcraft-py313 sbatch hpc/slurm_setup_env.sh
```

API keys should be made available on the compute node through the cluster's
normal secret mechanism. The existing runner also sources `$HOME/.api_keys` when
present.

The `providers` extra pins the OpenAI and Anthropic SDK versions used by scored
runs. Do not install rolling provider SDKs on top of that environment; change the
pins and lockfile together, then re-run the HPC checks.

On Cayuga, load the current Slurm client before submitting jobs:

```bash
module load slurm/25.05.0
```

## Submit Evaluation Array

Each array element runs exactly one `(task, model, seed)` cell by calling
`scripts/run_portfolio_eval.sh` with `SEEDS=1` and a concrete `SEED_START`.

Before API-backed evaluation, run code checks on HPC:

```bash
mkdir -p results/hpc/slurm
VENV_DIR=/home/fs01/jak4013/labcraft-py313 sbatch hpc/slurm_checks.sh
```

Example: run the current plus discovery tasks across 10 seeds and 4 models.
There are 14 tasks in `TASK_PRESET=all`; with 4 models and 10 seeds, submit
`14 * 4 * 10 = 560` array elements.

```bash
mkdir -p results/hpc/slurm

RUN_ID=2026_07_current_all_n10 \
TASK_PRESET=all \
SEEDS_TOTAL=10 \
MODEL_MATRIX=current_balanced \
sbatch --array=0-559%32 hpc/slurm_eval_array.sh
```

Use `%32` or a smaller throttle if API rate limits are tight. For a small smoke
on HPC, reduce the matrix:

HPC release cells always use the generation profile registered in
`config/model_matrix.toml`. The array runner rejects inherited
`GENERATE_CONFIG_FILE` and `GENERATE_CONFIG_ARGS` overrides so its cell
manifest cannot disagree with the intended model profile. Edit and review the
registry for an intentional HPC profile change.

```bash
mkdir -p results/hpc/slurm

RUN_ID=2026_07_model_refresh_smoke \
TASKS="growth_01" \
SEEDS_TOTAL=1 \
MODEL_MATRIX=current_balanced \
sbatch --array=0-3%1 hpc/slurm_eval_array.sh
```

## Aggregate and Plot

After all evaluation jobs finish, submit the aggregation job on HPC:

```bash
mkdir -p results/hpc/slurm

RUN_ID=2026_07_current_all_n10 \
TASK_PRESET=all \
MODEL_MATRIX=current_balanced \
sbatch hpc/slurm_aggregate.sh
```

The default output layout is:

```text
results/hpc/<RUN_ID>/
  logs/                  # Inspect .eval archives
  manifests/             # one JSON manifest per array element
  aggregate_manifest.json
  results.md
  plots/
    scorecard.png
    axis_heatmap.png
```

Do not overwrite previous bundles. Re-use an existing `RUN_ID` only when
intentionally extending or repairing that exact run; otherwise create a new
`RUN_ID`.

## Recommended v0.2 Matrices

Start small, then scale:

| Bundle | Purpose | Tasks | Models | Seeds |
|---|---|---|---|---:|
| `model_refresh_smoke` | Verify cluster env, API compatibility, and resolved IDs | `growth_01` | `current_balanced` | 1 |
| `v0_2_current_n10` | Larger wet-lab execution slice | `TASK_PRESET=current` | 4 frontier models | 10 |
| `v0_2_discovery_n10` | Discovery-decision reliability | `TASK_PRESET=discovery` | 4 frontier models | 10 |
| `v0_2_all_n20` | Candidate public v0.2 bundle | `TASK_PRESET=all` | final model list | 20 |

Keep the frozen April 2026 snapshot tied to `results/logs` and the v0.1.0
release. HPC bundles should live under `results/hpc/<RUN_ID>` until one is
promoted in a future release.
