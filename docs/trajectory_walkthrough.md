# Trajectory Walkthrough

This walkthrough shows how one LabCraft-Eval sample turns into a scored result.
It is intentionally implementation-level enough to audit, but short enough to
read before running the benchmark.

## 1. Task Contract

For `transform_01`, the public task prompt asks the agent to measure
transformation efficiency across four plasmid DNA inputs. The task contract is
stored in:

- `task_data/transform_01/rubric.json`
- `task_data/transform_01/ground_truth.json`
- `task_data/transform_01/SOURCES.md`

The prompt tells the model what to do. The ground-truth file tells the scorer
which experimental decisions matter, what ranges or values count as acceptable,
and which failure diagnoses should receive troubleshooting credit.

## 2. Seeded Simulation

`src/inspect_task.py` builds the Inspect sample and assigns a seed index in
sample metadata. During execution, `src/solvers.py` exposes lab operations such
as media preparation, transformation, plating, incubation, and colony counting.

Those operations mutate `LabState` objects in `src/environment/state.py`.
The current runner passes the explicit seed index into the simulator RNG. Some
operations, including plating and colony generation, use seeded draws; other
operations, including the growth model, are deterministic across seed labels.
The parameter bundles under `data/parameters/` record the values and citation
metadata used by both kinds of operation. Replaying a fixed tool trajectory with
the same current code and seed reproduces simulator observations, but a model
rerun is not guaranteed to reproduce the same generated trajectory.

## 3. Agent Trajectory

Inspect records the agent's tool calls, tool observations, and final answer in
an `.eval` log. LabCraft-Eval treats this trajectory as the primary evidence:
scores are based on what the agent actually did, not only on the final prose.

Useful audit locations:

- `results/logs/` for the frozen April 2026 snapshot logs.
- `results/current_*_logs/` for newer task bundles.
- `results/discovery_logs/` for Discovery Decision Track runs.

The tracked historical logs preserve their original task and scorer behavior.
Several early bundles used answer-bearing agent guidance that has since been
removed, so those scores should be re-aggregated as historical artifacts rather
than compared directly with a current rerun.

## 4. Four-Axis Scoring

`src/trajectory_scorer.py` scores each sample along four simulator axes:

| Axis | Evidence Used |
| --- | --- |
| Decision quality | Whether key experimental choices match the ground-truth decision points. |
| Task success | Whether the trajectory and final answer satisfy the task objective. |
| Troubleshooting | Whether the final answer recognizes known failure modes or uncertainty. |
| Efficiency | Whether the agent made progress with a reasonable number of tool calls. |

The scorer is deterministic. It parses tool calls and final answers, applies
task-specific scoring helpers, and writes per-axis values into result rows.
The checked-in JSON rubric trees document the intended hierarchy, but the live
v0.1.x scorer uses the hard-coded logic and fixed weights in
`src/trajectory_scorer.py`.

For the five P1 wet-lab tasks, each task sample and resulting `Score.metadata`
also carries a scorer-contract set, schema version, task scorer version, and
SHA-256 bindings. The local contract manifest under
`task_data/scorer_validity/` pins the exact scorer callable, ground truth,
rubric, report schema, decision IDs, and evidence policy. Its seven synthetic
fixture families per task exercise canonical and alternative valid paths plus
forged, partial, orphan, contradictory, and retry trajectories.

The 35-case deterministic regression is a technical conformance gate, not an
expert label. Every checked-in fixture currently remains
`pending_expert_review`; the promotion validator stays closed until all exact
fixture definitions, materialized trajectories, rationales, validity labels,
component vectors, and decision-level labels are reviewed and hash-frozen with
their scorer/source and ground-truth contract.

## 5. Published Result Row

Aggregation scripts deduplicate scored samples and export rows with:

- model identifier
- task id and track
- sample id
- source `.eval` log path
- creation timestamp
- token accounting when available
- per-axis scores

The Hugging Face export stores these rows in `result_rows.jsonl` and records the
source `.eval` checksums in `eval_log_manifest.jsonl`. The release manifest then
checksums every exported artifact so consumers can audit a public number back to
its source commit and log bundle.

The current P2a fixture corpus is local development-conformance evidence and is
not included in the v0.1.2 Hugging Face snapshot. It must not be described as a
public model result or held-out evaluation set.
