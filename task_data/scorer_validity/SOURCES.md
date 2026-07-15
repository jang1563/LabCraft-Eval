# Scorer-validity corpus provenance

This directory contains synthetic development conformance trajectories for the
five P1 wet-lab scorers. It does not introduce new scientific thresholds or
empirical performance claims. Each fixture is derived from the corresponding
task's checked-in ground truth, rubric, simulator contract, and report schema:

- `task_data/golden_gate_01/`
- `task_data/gibson_01/`
- `task_data/miniprep_01/`
- `task_data/express_01/`
- `task_data/purify_01/`

The manifest pins SHA-256 digests for each ground-truth, rubric, and fixture
artifact. The fixture labels and full score vectors remain an AI-assisted draft
pending expert review; they are not held-out evaluation data or model-ranking
evidence.

## Rejected Sources

- Raw model transcripts and native evaluation logs were rejected to avoid
  importing model-specific prose, run metadata, or non-minimal trajectories.
- Unversioned scorer behavior was rejected as a label source; expected vectors
  are explicit review targets rather than values regenerated from scorer output.
- External scientific sources were not duplicated here. Scientific conditions
  remain governed by each task's existing `SOURCES.md`, ground truth, and
  simulator contract.
