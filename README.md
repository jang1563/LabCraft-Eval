# LabCraft-Eval

_Formerly **BioProtocolBench**; renamed 2026-05-31 to avoid a name collision with the unrelated [BioProBench](https://github.com/YuyangSunshine/bioprotocolbench) NLP corpus (Liu et al. 2025). The old GitHub URL auto-redirects here._

[![Code License: Apache-2.0](https://img.shields.io/badge/code%20license-Apache--2.0-blue.svg)](LICENSE)
[![Benchmark Content: CC BY-NC 4.0](https://img.shields.io/badge/benchmark%20content-CC%20BY--NC%204.0-lightgrey.svg)](LICENSE-DATA)
[![CI](https://github.com/jang1563/LabCraft-Eval/actions/workflows/ci.yml/badge.svg)](https://github.com/jang1563/LabCraft-Eval/actions/workflows/ci.yml)
[![CodeQL](https://github.com/jang1563/LabCraft-Eval/actions/workflows/codeql.yml/badge.svg)](https://github.com/jang1563/LabCraft-Eval/actions/workflows/codeql.yml)

An [Inspect AI](https://inspect.aisi.org.uk/) evaluation environment for measuring how well AI agents execute benign molecular-microbiology protocols inside a seeded laboratory simulator with task-dependent stochasticity.

Built on **LabCraft**, the underlying framework in [`src/`](src/). Each task places the agent in a seeded environment with a fixed tool set, a public protocol, and citation metadata for its task contract.

> Not to be confused with [BioProBench](https://github.com/YuyangSunshine/bioprotocolbench) (Liu et al., 2025), an NLP corpus of 556K instances. LabCraft-Eval is an agent evaluation environment with four-axis trajectory scoring.

## What the agent does

Each task gives the agent:

- A **protocol prompt** (e.g., "measure transformation efficiency across four plasmid inputs")
- Access to lab-operation tools (`prepare_media`, `transform`, `plate`, `incubate`, `count_colonies`, ...) and reference tools (`lookup_reagent`, `lookup_enzyme`, `check_safety`)
- A sample state seeded per run, with task-dependent deterministic operations and seeded stochastic operations such as plating and colony counts.

The agent must plan the experiment, call tools in the right order, interpret observations, and report quantitative results. In v0.1.x, a deterministic hard-coded trajectory scorer inspects the full interaction and computes four fixed-weight axes. The checked-in JSON rubrics document the intended hierarchy but do not drive runtime scoring.

## Current status

- **Implemented surface:** 14 runnable simulator and discovery-decision tasks, plus the separate `safety_case_01` safeguard-quality track.
- **Frozen scored snapshot:** 100 sample rows across 5 tasks, 4 frontier models, and 5 seed-labelled repetitions from April 2026. These v0.1.1 results are historical, provisional benchmark-development evidence—not a validated model ranking.
- **Current release:** the Hugging Face dataset `main` branch is a metadata-only v0.1.2 integrity release. The scored leaderboard intentionally remains pinned to the frozen v0.1.1 artifact.
- **Evidence trail:** raw frozen trajectories, per-sample scores, failure-mode analysis, and release/provenance documentation are linked below.

## Quickstart

```bash
git clone https://github.com/jang1563/LabCraft-Eval.git
cd LabCraft-Eval
pip install -e ".[dev,analysis,providers]"
inspect eval src/inspect_task.py@transform_01 --model openai/gpt-5.6-sol
```

See [Installation](#installation) and [Running](#running) for the full task and provider matrix, or inspect the public snapshot without extra dependencies:

```bash
python3 examples/hf_quickstart.py
```

## Read these limitations first

- The frozen v0.1.1 scorecard predates prompt/scorer leakage remediation and is not a leakage-free capability comparison.
- Five repetitions per cell are exploratory; the observed differences were not tested inferentially.
- Runtime scoring in v0.1.x is deterministic hard-coded matching rather than LLM-as-judge or JSON-rubric-driven, so final-answer parsing is brittle.
- Newer wet-lab, discovery, and safety-case tracks are reported separately and are not merged into the frozen leaderboard.

See [Key findings and limitations](#key-findings-and-limitations) for the full analysis before interpreting the numbers.

## Public artifacts and release tooling

| Surface | Link |
|---------|------|
| Code and benchmark repository | <https://github.com/jang1563/LabCraft-Eval> |
| Hugging Face dataset export | <https://huggingface.co/datasets/jang1563/LabCraft-Eval> |
| Hugging Face leaderboard Space | <https://huggingface.co/spaces/jang1563/LabCraft-Eval-Leaderboard> |
| Architecture overview | [docs/architecture.md](docs/architecture.md) |
| Trajectory walkthrough | [docs/trajectory_walkthrough.md](docs/trajectory_walkthrough.md) |
| HF export data dictionary | [docs/hf_data_dictionary.md](docs/hf_data_dictionary.md) |
| Technical report | [docs/technical_report.md](docs/technical_report.md) |
| Leaderboard Space plan | [docs/leaderboard_space_plan.md](docs/leaderboard_space_plan.md) |
| Frozen simulator scorecard | [results/results.md](results/results.md) |
| Failure-mode analysis | [results/analysis.md](results/analysis.md) |
| Discovery decision bundle | [results/discovery_track.md](results/discovery_track.md) |
| HPC v0.2 current-task candidate | [results/hpc_v0_2_current_n10.md](results/hpc_v0_2_current_n10.md) |
| Safety-case live smoke | [results/safety_case_live_v0_2.md](results/safety_case_live_v0_2.md) |
| Current model matrix and provenance | [docs/model_matrix.md](docs/model_matrix.md) |
| July 2026 model-refresh checkpoint | [docs/model_refresh_status_2026_07.md](docs/model_refresh_status_2026_07.md) |
| Public snapshot checklist | [docs/release_checklist.md](docs/release_checklist.md) |
| Public artifact roadmap | [docs/publication_roadmap.md](docs/publication_roadmap.md) |
| Hugging Face release plan | [docs/hf_release.md](docs/hf_release.md) |

Recommended reading path: start with the architecture overview and trajectory
walkthrough, then the frozen simulator scorecard, then the failure-mode
analysis, then the Discovery Decision Track. The Safety Case Track is separate
and optional; it is not merged into the simulator leaderboard.

Machine-readable path: use the Hugging Face export script to write JSONL files,
checksums, a release manifest, and a dataset-card `README.md` without scraping
Markdown result pages.

```bash
uv run python scripts/export_hf_dataset.py \
  --out-dir build/hf_dataset \
  --release-name local_export \
  --no-results \
  --clean-output \
  --copy-plots
uv run python scripts/validate_hf_export.py build/hf_dataset
```

This metadata-only command is also the path exercised by CI. It validates task,
rubric, ground-truth, citation, plot, and manifest packaging, but it does not
validate or publish structured score rows. Copied frozen plots remain
historical visual assets and do not acquire schema 0.3 score provenance from
this smoke path. Schema 0.3 score-bearing exports require an
explicit `--log-dir` containing successful `.eval` logs whose native Inspect
`evaluation_revision.dirty` value is `false` and whose generation configuration
is explicitly pinned. Score-bearing exports bundle the raw `.eval` evidence;
they do not publish checksum-only references to local or ignored log paths.

The exporter refuses a non-empty output directory by default so stale files
cannot leak into a release. Choose a new directory, or pass `--clean-output`
only when intentionally replacing a disposable export directory such as
`build/hf_dataset`. Destructive cleanup is restricted to children of `build/`.

The exporter also refuses a dirty packaging worktree, because a HEAD commit
cannot identify uncommitted files included in a release bundle.

The manifest and JSONL records use `source_commit` for the packaging HEAD commit
recorded when the exporter runs. Final releases should be built from a clean
packaging worktree. Score and log-manifest rows separately preserve
`evaluation_revision`, the native code revision recorded when Inspect ran the
evaluation. These commits can differ and must not be interpreted as the same
provenance field.

Before uploading a dataset snapshot, inspect the dry-run upload plan:

```bash
uv run python scripts/upload_hf_dataset.py \
  build/hf_dataset \
  --repo-id jang1563/LabCraft-Eval
```

For actual upload with `--execute`, install `huggingface-hub>=0.36,<1.0` in the
active environment first.

Quickly inspect the public Hugging Face snapshot without extra dependencies:

```bash
python3 examples/hf_quickstart.py
python3 examples/hf_quickstart.py --snapshot-dir build/hf_dataset
```

## Discovery Decision Track

LabCraft-Eval now also includes a separate **Discovery Decision Track** for perturbation-driven discovery decisions. Instead of executing a microbiology workflow end to end, these tasks evaluate whether an agent can inspect candidate-target evidence, choose the right next experiment, and interpret one orthogonal follow-up with an auditable scorer.

Current discovery-track tasks:

- `perturb_followup_01`: resolve one ambiguous perturbation hit with a single orthogonal follow-up
- `target_prioritize_01`: rank four candidate targets for an inflammatory-disease program
- `target_validate_01`: choose and interpret the best first validation assay for the lead target

This is meant to complement the wet-lab execution tasks, not replace them: the original LabCraft benchmark scores protocol execution inside the simulator, while the discovery track scores synthetic discovery decisions.

Quick discovery links:

- [results/discovery_track.md](results/discovery_track.md) for the historical bundle, scores, and pre-remediation limitations
- `./scripts/run_discovery_bundle.sh` to run the recommended 2-model / 3-repeat Discovery bundle into a new timestamped `build/eval_runs/` directory

## Optional Safety Case Track

LabCraft-Eval also includes a separate **Safety Case Track** for measuring
deployment-safeguard quality on legitimate bio-research requests. This track is
not a stochastic lab simulator and not a harmful-biology capability benchmark:
it is a single-turn conversational eval that checks whether a model stays
helpful on allowed BSL-1/BSL-2 research while keeping appropriate boundaries,
citations, monitoring signals, and residual-risk framing.

Current safety-case surface:

- `safety_case_01` — 30 legitimate scenarios across standard protocol support,
  reagent sourcing, data interpretation, method optimization, and literature guidance
- 60 synthetic fixture transcripts for scorer validation: one good-handling
  response and one targeted failure-mode response per scenario
- Five deterministic scoring axes: legitimate helpfulness, boundary precision,
  provenance grounding, monitor coverage, and residual-risk framing

Quick safety-case links:

- [results/safety_case_track.md](results/safety_case_track.md) for the fixture bundle summary
- `TASK_PRESET=safety_case ./scripts/run_portfolio_eval.sh` for live model runs

## Results

100 scored sample rows · 5 tasks · 4 frontier models · 5 seed-labelled repetitions · April 2026 · total API cost ~$2.50

> **Evidence status:** these frozen v0.1.1 scores are historical, provisional
> benchmark-development evidence. They preserve the originally published
> artifacts, including their original scorer behavior and provenance limits.
> Some agent-facing defaults and descriptions supplied choices that the scorer
> rewarded; those hints are removed in the current implementation. The frozen
> table is therefore not a leakage-free result or a validated ranking of
> wet-lab competence or model providers.

This scorecard is a frozen April 2026 portfolio snapshot covering the first five tasks: `transform_01`, `growth_01`, `pcr_01`, `screen_01`, and `clone_01`. The repo now implements 14 runnable simulator/decision tasks total: those five snapshot tasks, five newer wet-lab tasks (`golden_gate_01`, `gibson_01`, `miniprep_01`, `express_01`, `purify_01`), one follow-up decision task (`followup_01`), and three Discovery Decision Track tasks (`perturb_followup_01`, `target_prioritize_01`, `target_validate_01`). It also includes the separate `safety_case_01` safeguard-quality track. The newer wet-lab, discovery, and safety-case tracks are runnable today but are reported in separate result pages so the frozen scorecard remains stable.

See **[results/analysis.md](results/analysis.md)** for per-task failure-mode analysis, [results/results.md](results/results.md) for per-sample scores, and [results/logs/](results/logs/) for the raw Inspect trajectories.

For a separate historical sanity-check track on the newer implemented tasks, see **[results/current_smoke.md](results/current_smoke.md)**. That bundle is deliberately not merged into the scorecard because it is a single-model, single-repeat pre-remediation smoke run.

For a small historical three-repeat bundle on the newer tasks, see **[results/current_openai.md](results/current_openai.md)**. That track covers `gpt-4o-mini` and `gpt-4o` on `golden_gate_01`, `gibson_01`, `miniprep_01`, `express_01`, and `purify_01`; it predates the answer-leakage remediation and is not a current capability result.

For the corresponding historical cross-provider three-repeat bundle, see **[results/current_frontier.md](results/current_frontier.md)**. It combines `gpt-4o-mini`, `gpt-4o`, `claude-haiku-4-5`, and `claude-sonnet-4-5` on the same five tasks under the pre-remediation prompt/scorer contract.

For the 5-repeat extension of that same newer-task cross-provider slice, see **[results/current_frontier_5seed.md](results/current_frontier_5seed.md)**. That bundle combines the original 3-repeat runs with an incremental `seed_start=3` extension; it remains a small descriptive slice rather than a statistical stability study.

For the historical discovery-decision bundle, see **[results/discovery_track.md](results/discovery_track.md)**. It keeps the frozen microbiology snapshot untouched, but its stored runs predate the discovery-tool leakage remediation and are not current capability results.

For the safety-case fixture bundle, see **[results/safety_case_track.md](results/safety_case_track.md)**. That track keeps model-helpfulness and boundary precision visible without merging its conversational safeguard scores into the simulator scorecard.

For a larger HPC-only v0.2 current-task candidate, see **[results/hpc_v0_2_current_n10.md](results/hpc_v0_2_current_n10.md)**. That bundle covers 11 current tasks across 4 models and 10 repetitions per cell, but remains separate from the frozen April 2026 scorecard. Its raw `.eval` bundle is not currently public, so the summary is not independently re-aggregatable and should be treated as provisional until those artifacts are published.

For live Safety Case Track model results, see **[results/safety_case_live_v0_2.md](results/safety_case_live_v0_2.md)**. Those scores are conversational safeguard-quality scores and are not merged into the wet-lab simulator leaderboard. Their raw live-run bundle is also not public, so the summary is not independently auditable yet.

![Overall score by model and task](results/scorecard.png)

![Per-axis breakdown](results/axis_heatmap.png)

**Overall score by model × task** (mean ± stddev across 5 stored repetitions, scored in [0, 1]):

| Task | gpt-4o-mini | gpt-4o | claude-haiku-4-5 | claude-sonnet-4-5 |
|---|---:|---:|---:|---:|
| `transform_01` | 0.570 ± 0.045 | 0.440 ± 0.108 | 0.500 ± 0.197 | 0.480 ± 0.179 |
| `growth_01` | 0.560 ± 0.152 | 0.580 ± 0.217 | 0.890 ± 0.246 | 0.880 ± 0.241 |
| `pcr_01` | 0.970 ± 0.027 | 0.950 ± 0.000 | 0.950 ± 0.000 | 0.950 ± 0.000 |
| `screen_01` | 0.900 ± 0.197 | 0.840 ± 0.219 | 1.000 ± 0.000 | 1.000 ± 0.000 |
| `clone_01` | 0.722 ± 0.397 | 0.904 ± 0.103 | 0.940 ± 0.022 | 0.950 ± 0.000 |
| **Mean across tasks** | **0.744** | **0.743** | **0.856** | **0.852** |

Run the current implementation on the same task/model matrix. Every command
below writes to a new timestamped bundle under `build/eval_runs/`. The checked-in
`results/current_*` paths are historical evidence and are not run targets.

```bash
# The historical score table is frozen and cannot be exactly reproduced from
# rolling model aliases and the incomplete native provenance in its old logs.
# Create a new snapshot rerun bundle instead of modifying historical evidence.
RUN_ID="snapshot_$(date -u +%Y%m%dT%H%M%SZ)"
BUNDLE_DIR="build/eval_runs/${RUN_ID}"
RUN_ID="${RUN_ID}" \
LOG_DIR="${BUNDLE_DIR}/logs" \
SEEDS=5 \
MODELS="openai/gpt-4o-mini openai/gpt-4o anthropic/claude-haiku-4-5 anthropic/claude-sonnet-4-5" \
  ./scripts/run_portfolio_eval.sh
python3 scripts/aggregate_eval_results.py \
  --log-dir "${BUNDLE_DIR}/logs" \
  --out "${BUNDLE_DIR}/results.md"

# Run the current implemented task bundle into another new bundle.
RUN_ID="current_smoke_$(date -u +%Y%m%dT%H%M%SZ)"
BUNDLE_DIR="build/eval_runs/${RUN_ID}"
RUN_ID="${RUN_ID}" \
LOG_DIR="${BUNDLE_DIR}/logs" \
SEEDS=1 \
MODELS="openai/gpt-4o-mini" \
TASKS="golden_gate_01 gibson_01 miniprep_01 express_01 purify_01" \
  ./scripts/run_portfolio_eval.sh
python3 scripts/aggregate_eval_results.py \
  --log-dir "${BUNDLE_DIR}/logs" \
  --out "${BUNDLE_DIR}/results.md"
python3 scripts/plot_scorecard.py \
  --log-dir "${BUNDLE_DIR}/logs" \
  --out-dir "${BUNDLE_DIR}/plots" \
  --task-preset auto \
  --models openai/gpt-4o-mini

# Run a small comparable cross-provider bundle on the newer tasks.
RUN_ID="current_frontier_$(date -u +%Y%m%dT%H%M%SZ)"
BUNDLE_DIR="build/eval_runs/${RUN_ID}"
OPENAI_LOG_DIR="${BUNDLE_DIR}/openai_logs"
ANTHROPIC_LOG_DIR="${BUNDLE_DIR}/anthropic_logs"
RUN_ID="${RUN_ID}" \
LOG_DIR="${OPENAI_LOG_DIR}" \
SEEDS=3 \
MODELS="openai/gpt-4o-mini openai/gpt-4o" \
TASKS="golden_gate_01 gibson_01 miniprep_01 express_01 purify_01" \
  ./scripts/run_portfolio_eval.sh
RUN_ID="${RUN_ID}" \
LOG_DIR="${ANTHROPIC_LOG_DIR}" \
SEEDS=3 \
MODELS="anthropic/claude-haiku-4-5 anthropic/claude-sonnet-4-5" \
TASKS="golden_gate_01 gibson_01 miniprep_01 express_01 purify_01" \
  ./scripts/run_portfolio_eval.sh

# Aggregate and plot both provider runs inside the same new bundle.
python3 scripts/aggregate_eval_results.py \
  --log-dir "${OPENAI_LOG_DIR}" "${ANTHROPIC_LOG_DIR}" \
  --out "${BUNDLE_DIR}/results.md"
python3 scripts/plot_scorecard.py \
  --log-dir "${OPENAI_LOG_DIR}" "${ANTHROPIC_LOG_DIR}" \
  --out-dir "${BUNDLE_DIR}/plots" \
  --task-preset auto \
  --models openai/gpt-4o-mini openai/gpt-4o anthropic/claude-haiku-4-5 anthropic/claude-sonnet-4-5

# Extend this new bundle to 5 total repetitions by adding only seeds 03-04.
OPENAI_SEED34_LOG_DIR="${BUNDLE_DIR}/openai_logs_seed34"
ANTHROPIC_SEED34_LOG_DIR="${BUNDLE_DIR}/anthropic_logs_seed34"
RUN_ID="${RUN_ID}" \
LOG_DIR="${OPENAI_SEED34_LOG_DIR}" \
SEEDS=2 \
SEED_START=3 \
MODELS="openai/gpt-4o-mini openai/gpt-4o" \
TASKS="golden_gate_01 gibson_01 miniprep_01 express_01 purify_01" \
  ./scripts/run_portfolio_eval.sh
RUN_ID="${RUN_ID}" \
LOG_DIR="${ANTHROPIC_SEED34_LOG_DIR}" \
SEEDS=2 \
SEED_START=3 \
MODELS="anthropic/claude-haiku-4-5 anthropic/claude-sonnet-4-5" \
TASKS="golden_gate_01 gibson_01 miniprep_01 express_01 purify_01" \
  ./scripts/run_portfolio_eval.sh
python3 scripts/aggregate_eval_results.py \
  --log-dir "${OPENAI_LOG_DIR}" "${ANTHROPIC_LOG_DIR}" \
            "${OPENAI_SEED34_LOG_DIR}" "${ANTHROPIC_SEED34_LOG_DIR}" \
  --out "${BUNDLE_DIR}/results_5repeat.md"
python3 scripts/plot_scorecard.py \
  --log-dir "${OPENAI_LOG_DIR}" "${ANTHROPIC_LOG_DIR}" \
            "${OPENAI_SEED34_LOG_DIR}" "${ANTHROPIC_SEED34_LOG_DIR}" \
  --out-dir "${BUNDLE_DIR}/plots_5repeat" \
  --task-preset auto \
  --models openai/gpt-4o-mini openai/gpt-4o anthropic/claude-haiku-4-5 anthropic/claude-sonnet-4-5
```

## Key findings and limitations

### What this evaluation showed

1. **The observed troubleshooting difference is prompt-sensitive.** Under the historical default prompt, both Anthropic models score 1.00 on the `growth_01` troubleshooting axis across 10/10 runs, and both OpenAI models score 0.00. A follow-up ablation ([analysis.md § Ablation](results/analysis.md#ablation-is-the-openai-growth_01-troubleshooting-gap-prompt-sensitivity-or-model-behaviour)) adds a single explicit sentence instructing the agent to surface any `insufficient_points` fit warning. With that hint, `gpt-4o-mini` reaches 5/5 and `gpt-4o` 3/5 on troubleshooting, while task-success falls. This is descriptive evidence about one prompt/scorer configuration, not a provider-level capability conclusion.

2. **The two Anthropic model means differ by 0.004 in this frozen table** (`sonnet` 0.852, `haiku` 0.856). No hypothesis test, confidence interval, or power analysis was performed, so the snapshot does not establish statistical equivalence or a price-performance conclusion.

3. **The benchmark did useful work by finding infrastructure bugs.** The eval surfaced two latent simulator issues that hand-written tests missed: (a) `ligate` rejecting the `digest_NNN` shorthand that `gpt-4o` consistently used, killing 5/5 samples; (b) tool-layer `ValueError`s propagating through Inspect as fatal task failures instead of agent-visible observations, nuking an entire 5-seed cell when a digest produced no output fragments. Both are fixed and live in [src/environment/operations.py](src/environment/operations.py) and [src/tools/lab_tools.py](src/tools/lab_tools.py). Adversarial agent exploration is doing the bug-finding work that formal tests cannot.

### Limitations I want to flag before you build on these numbers

- **N = 5 repetitions is exploratory.** Task-success stddev averages 0.27 per cell, and one result flipping changes the mean by 0.20. The observed ~0.11 cluster difference was not tested inferentially and is not established as robust.
- **`transform_01` is the single hardest task (0.50 mean), but it is execution-constrained, not reasoning-limited.** Models that fail it do so by dropping one of four CFU/µg values or missing the `"consistent"` keyword, not by getting the biology wrong. If the goal were to probe reasoning depth, this task would need a redesign.
- **A single-variant prompt ablation is not an exhaustive test.** The growth_01 ablation above used one verbose prompt and showed an axis tradeoff. A proper prompt-sensitivity study would sweep across several variants (with different levels of instruction density and output-format scaffolding) and re-measure all four axes. That's the natural next step for the growth_01 story.
- **The v0.1.x runtime scorer is deterministic, hard-coded regex and tool-argument matching**, not LLM-as-judge and not JSON-rubric-driven. That makes a fixed scorer run repeatable, but final-answer parsing is brittle and the published scores remain tied to the exact historical scorer version.

These limitations are the top of the next-iteration backlog, documented in [results/analysis.md § "What a larger evaluation would add"](results/analysis.md).

## Tasks

Current implemented task inventory:

| Task | Domain | Objective |
|---|---|---|
| `transform_01` | Chemical transformation of *E. coli* | Measure CFU/µg across four DNA masses (10 pg → 10 ng) |
| `growth_01` | Liquid-culture growth characterization | Determine growth parameters from OD600 time-course |
| `pcr_01` | PCR optimization | Choose conditions that yield specific amplification |
| `screen_01` | pUC blue-white colony screening | Confirm recombinants by colony PCR with ≥95% confidence |
| `clone_01` | Restriction cloning end-to-end | Digest + ligate 950 bp insert into pUC19 with EcoRI/BamHI, transform, and confirm recombinants |
| `golden_gate_01` | Type IIS Golden Gate assembly | One-pot 4-fragment BsaI/T4 ligase assembly with 37 °C / 16 °C cycling, transform |
| `gibson_01` | Isothermal Gibson overlap assembly | 2-fragment master-mix assembly at 50 °C for 15 min, transform |
| `miniprep_01` | Alkaline lysis plasmid prep | P1/P2/P3 lysis + silica column; report concentration, A260/A280, yield |
| `express_01` | Recombinant protein expression | Induce benign His-tagged MBP-GFP expression in a T7 host and report soluble yield |
| `purify_01` | Ni-NTA affinity purification | Purify a benign His-tagged MBP-GFP fusion and report concentration, band, and purity |
| `followup_01` | Growth follow-up decision under ambiguous intervention data | Resolve whether a chloramphenicol slowdown is real or an undersampling artifact using the minimum follow-up experiment |
| `perturb_followup_01` | Perturbation follow-up | Resolve one ambiguous discovery hit with a single orthogonal assay |
| `target_prioritize_01` | Discovery target triage | Rank four candidate targets by perturbation strength, translation support, and liability risk |
| `target_validate_01` | Discovery validation | Choose and interpret the best first validation assay for the lead target |
| `safety_case_01` | Safety-case safeguard quality | Evaluate legitimate-helpfulness, boundary precision, provenance, monitor coverage, and residual-risk framing on 30 bio-research requests |

Each task directory (`task_data/<task_id>/`) contains `rubric.json` (hierarchical scoring tree), `ground_truth.json` (expected values with citation metadata), and `SOURCES.md` (citations).

## Scoring

Trajectory scoring (see [src/trajectory_scorer.py](src/trajectory_scorer.py)) produces four axes per task:

- **Task success**: were the requested values reported, within tolerance of ground truth?
- **Decision quality**: were the experimental choices (dilutions, controls, replicates) sound?
- **Troubleshooting**: did the agent recognize and recover from observed failure states or warnings?
- **Efficiency**: did the agent solve the task with a reasonable tool-call budget rather than wandering or hitting message-limit artifacts?

The checked-in JSON rubrics were authored using a hierarchy inspired by [PaperBench](https://openai.com/index/paperbench/). In v0.1.x they are audit/design artifacts: runtime scoring is implemented directly in `src/trajectory_scorer.py` with fixed top-level weights of 0.4 / 0.3 / 0.2 / 0.1. `src/rubric_utils.py` can load and compute JSON trees, but that path is not wired into live Inspect scoring.

$$S = \frac{\sum_j w_j \cdot s_j}{\sum_j w_j}$$

## Installation

```bash
git clone https://github.com/jang1563/LabCraft-Eval.git
cd LabCraft-Eval
pip install -e ".[dev,analysis,providers]"
```

The installable Python distribution is currently named `labcraft`, because
LabCraft is the simulator framework underneath LabCraft-Eval. For v0.1.x,
direct Python imports remain internal `src.*` imports to preserve the existing
Inspect task paths; the public execution surface is the Inspect task file and
the runner scripts below.

## Running

```bash
# Single task
inspect eval src/inspect_task.py@transform_01     --model openai/gpt-5.6-sol
inspect eval src/inspect_task.py@growth_01        --model anthropic/claude-sonnet-5
inspect eval src/inspect_task.py@pcr_01           --model openai/gpt-5.6-luna
inspect eval src/inspect_task.py@screen_01        --model openai/gpt-5.6-luna
inspect eval src/inspect_task.py@clone_01         --model openai/gpt-5.6-luna
inspect eval src/inspect_task.py@golden_gate_01   --model openai/gpt-5.6-luna
inspect eval src/inspect_task.py@gibson_01        --model openai/gpt-5.6-luna
inspect eval src/inspect_task.py@miniprep_01      --model openai/gpt-5.6-luna
inspect eval src/inspect_task.py@express_01       --model openai/gpt-5.6-luna
inspect eval src/inspect_task.py@purify_01        --model openai/gpt-5.6-luna
inspect eval src/inspect_task.py@followup_01      --model openai/gpt-5.6-luna
inspect eval src/inspect_task.py@perturb_followup_01   --model openai/gpt-5.6-luna
inspect eval src/inspect_task.py@target_prioritize_01  --model openai/gpt-5.6-luna
inspect eval src/inspect_task.py@target_validate_01    --model openai/gpt-5.6-luna
inspect eval src/inspect_task.py@safety_case_01        --model anthropic/claude-sonnet-5

# With explicit seed control for simulator sample IDs
inspect eval src/inspect_task.py@transform_01 \
    --model anthropic/claude-sonnet-5 \
    -T seeds=3 \
    -T seed_start=0

# Run the Discovery decision bundle with the current registered core
TASK_PRESET=discovery \
SEEDS=3 \
MODEL_MATRIX=current_balanced \
  ./scripts/run_portfolio_eval.sh

# Run the Safety Case Track
TASK_PRESET=safety_case \
SEEDS=1 \
MODELS="anthropic/claude-sonnet-5" \
  ./scripts/run_portfolio_eval.sh
```

Task entry points are registered via the `inspect_ai` plugin in [pyproject.toml](pyproject.toml).
For multi-task suites, prefer [scripts/run_portfolio_eval.sh](scripts/run_portfolio_eval.sh)
with `TASK_PRESET=snapshot`, `current`, `discovery`, `safety_case`, or `all`. The
`labcraft_suite()` Inspect entry point is kept only as a backwards-compatible
single-task smoke alias.

The portfolio runner reads the current matrix and a non-empty, model-specific
generation profile from [config/model_matrix.toml](config/model_matrix.toml).
Current reasoning models do not inherit the historical shared
`--temperature 0` setting. See [docs/model_matrix.md](docs/model_matrix.md) for
the exact IDs, profile overrides, requested/resolved model checks, and refresh
procedure.

For larger seed sweeps or release-candidate bundles, use the HPC-only workflow
in [hpc/README.md](hpc/README.md) and the v0.2 execution plan in
[docs/hpc_plan.md](docs/hpc_plan.md). Keep the frozen April 2026 snapshot
separate from new HPC bundles.

For a minimal manual expert-baseline workflow on `transform_01` and `growth_01`, see [docs/human_baseline.md](docs/human_baseline.md). The current CLI uses the same explicit seed-index convention and deterministic scorer as current agent runs, includes a pilot launcher at [scripts/run_human_baseline_pilot.py](scripts/run_human_baseline_pilot.py), and safely resumes `in_progress` sessions. Frozen v0.1.1 rows used an earlier seed convention and are contextual references rather than matched instances. The recommended first-pass labels are documented in [results/human_baseline_seed_plan.md](results/human_baseline_seed_plan.md), with aggregate artifacts in [results/human_baseline_pilot.md](results/human_baseline_pilot.md), [results/human_baseline_pilot.json](results/human_baseline_pilot.json), and [results/human_baseline_plots](results/human_baseline_plots).

## Repository layout

```
LabCraft-Eval/
├── README.md
├── CITATION.cff
├── LICENSE
├── LICENSE-DATA
├── NOTICE
├── SAFETY.md                 # Scope and safety policy
├── pyproject.toml
├── src/
│   ├── inspect_task.py       # @task entry points for all implemented tasks
│   ├── solvers.py            # Tool-augmented solvers per task
│   ├── environment/          # Seeded lab simulator (deterministic + stochastic operations)
│   ├── tasks/                # Per-task prompts and sample builders
│   ├── tools/                # lookup_reagent / lookup_enzyme / check_safety / lab ops
│   ├── trajectory_scorer.py  # Four-axis deterministic trajectory scorer
│   ├── rubric_utils.py       # JSON rubric utilities; not the v0.1.x runtime scorer
│   └── judge.py              # Legacy judge prompt utilities; trajectory scoring is deterministic
├── data/
│   ├── reagent_database.json     # 84 common reagents
│   ├── enzyme_database.json      # 46 enzymes
│   ├── safety_database.json      # 44 chemicals with GHS hazards
│   ├── discovery_track/          # Synthetic target/assay evidence for discovery tasks
│   ├── safety_case/              # Safety-case scenarios and scorer-validation fixtures
│   └── parameters/               # Stochastic parameters with citations
├── task_data/
│   ├── transform_01/         # rubric.json, ground_truth.json, SOURCES.md
│   ├── ...
│   ├── express_01/
│   └── purify_01/
├── environments/             # Docker sandbox
├── docs/schemas.md           # JSON schema contract
├── docs/release_checklist.md  # Public snapshot checklist
├── docs/publication_roadmap.md # GitHub/HF public artifact roadmap
├── docs/hf_release.md        # Hugging Face dataset and leaderboard plan
├── schemas/                  # Executable JSON Schema contracts for HF exports
└── tests/                    # Unit tests (environment, scorer, tools, rubrics)
```

## Safety scope

LabCraft-Eval is deliberately limited to BSL-1/BSL-2 benign molecular microbiology with standard *E. coli* strains, standard cloning vectors, and routine reagents. Select agents, gain-of-function work, mammalian virology, and any content aimed at increasing real-world capability for harmful biology are explicitly excluded. Full policy in [SAFETY.md](SAFETY.md).

Parameter, ground-truth, and safety records carry public citation metadata. The Gold / Silver / Bronze / Copper tier system is documented in [SAFETY.md](SAFETY.md), and [tests/test_citations.py](tests/test_citations.py) checks required citation fields and declared tiers. Those tests do not independently verify that every external source resolves or supports each numeric claim.

## Testing

```bash
pip install -e ".[dev,analysis]"
uv run --extra dev --extra analysis pytest
```

Tests cover seeded environment behavior, sample isolation, rubric loading, citation-record shape, tool contracts, and the hard-coded trajectory scorer. They do not make the JSON rubric files the runtime source of scoring truth.

## Citation

If you use LabCraft-Eval, cite the repository URL, the commit SHA, and the
result bundle or log directory you used. Machine-readable citation metadata is
available in [CITATION.cff](CITATION.cff), and the public snapshot checklist is
in [docs/release_checklist.md](docs/release_checklist.md).

## Related work

See **[results/positioning.md](results/positioning.md)** for a literature-grounded comparison against biology-agent and protocol benchmarks published in 2024–2026, including where this repo is genuinely novel (benign wet-lab protocol simulator + deterministic multi-axis trajectory scoring) and where it is honestly weaker (scale, real wet-lab grounding, human baselines).

Key references:

- [LAB-Bench / ProtocolQA](https://arxiv.org/abs/2407.10362) (FutureHouse, 2024): 2,400 text-only MCQ.
- [LABBench2](https://arxiv.org/abs/2604.09554) (FutureHouse/Edison Scientific, 2026): nearly 1,900 more realistic biology research tasks.
- [BioLP-bench](https://www.biorxiv.org/content/10.1101/2024.08.21.608694v1) (Ivanov, 2024): mistake-identification on real lab protocols.
- [BioProBench](https://arxiv.org/abs/2505.07889) (Liu et al., 2025): 556K text instances across 5 tasks on 27K protocols.
- [BoxingGym](https://arxiv.org/abs/2501.01540) (Gandhi/Goodman et al., 2025): interactive probabilistic environments scored by expected information gain.
- [BioAgent Bench](https://arxiv.org/abs/2601.21800) (Fa et al., 2026): end-to-end bioinformatics pipelines scored by LLM-as-judge.
- [BioMysteryBench](https://www.anthropic.com/research/Evaluating-Claude-For-Bioinformatics-With-BioMysteryBench) (Anthropic, 2026): real-world bioinformatics questions with objective ground truth and repeated-attempt reliability analysis.
- [GeneBench](https://www.biorxiv.org/content/10.64898/2026.04.22.720113) (Li/Ho, 2026): multi-stage inference in genomics and quantitative biology.
- [OpenAI × Red Queen Bio wet-lab framework](https://openai.com/index/accelerating-biological-research-in-the-wet-lab/) (2025): GPT-5 iteratively optimised a real molecular-cloning protocol, scored by physical assay (79× efficiency gain).
- [GPT-5 System Card](https://cdn.openai.com/gpt-5-system-card.pdf): ProtocolQA Open-Ended (108 questions) + TroubleshootingBench (52 non-public protocols × 3 questions; 80th-percentile PhD expert scores 36.4%).
- [PaperBench](https://openai.com/index/paperbench/) (OpenAI, 2025): inspiration for the checked-in rubric hierarchy; the v0.1.x runtime scorer remains hard-coded.
- [Inspect AI](https://inspect.aisi.org.uk/) (UK AISI): the evaluation framework this benchmark plugs into.

## License

LabCraft-Eval is dual-licensed:

- **Source code** (everything under `src/`, `tests/`, `environments/`, `docs/`, build config): [Apache License 2.0](LICENSE). Commercial use permitted.
- **Benchmark content** (everything under `task_data/` and `data/`: rubrics, ground-truth values, parameter distributions, citations, reagent/enzyme/safety databases): [Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0)](LICENSE-DATA). Free for research, teaching, and other non-commercial use with attribution.

For commercial use of the benchmark content (e.g., bundling with a commercial product, or evaluating models in a commercial training pipeline without a separate arrangement), please open an issue to discuss licensing.

See [NOTICE](NOTICE) for details on which files fall under which license.
