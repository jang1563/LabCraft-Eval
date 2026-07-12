# Discovery Decision Track

This bundle isolates the repo’s discovery-decision tasks:

- `perturb_followup_01`
- `target_prioritize_01`
- `target_validate_01`

> **Historical/pre-remediation artifact:** these stored runs predate removal of
> answer-bearing summary fields and exact scored identifiers from the discovery
> tool surface. The table describes that earlier prompt/tool contract and is not
> a leakage-free current model comparison.

What this track measures:

- whether an agent inspects perturbation-style evidence before acting
- whether it chooses the right next discovery experiment
- whether it interprets that result correctly
- whether it avoids wasted tool use

This track is intentionally small and auditable. It is not trying to be a general biomedical agent benchmark. The current implementation is a compact demonstration of discovery-decision scoring alongside simulator protocol execution; the historical numbers below should not be used as capability evidence.

Historical 2-model / 3-repeat bundle:

| Task | gpt-4o-mini | claude-sonnet-4-5 |
|---|---:|---:|
| `perturb_followup_01` | 0.814 ± 0.038 | 0.933 ± 0.000 |
| `target_prioritize_01` | 0.375 ± 0.043 | 0.425 ± 0.000 |
| `target_validate_01` | 0.867 ± 0.000 | 0.933 ± 0.067 |
| **Mean across tasks** | **0.685** | **0.764** |

Interpretation:

- Under the historical scorer, `perturb_followup_01` shows the largest stored model separation, concentrated in explanation of QC ambiguity and orthogonal non-support.
- The historical `target_validate_01` rows pass the assay and decision checks; their remaining score spread comes from the interpretation parser.
- Historical `target_prioritize_01` misses concentrate in final ranking/risk framing. A clean rerun is required before treating that as a current decision-quality signal.

Artifacts from this bundle:

- Aggregated table: [discovery_track_results.md](discovery_track_results.md)
- Plots: [discovery_track_plots/scorecard.png](discovery_track_plots/scorecard.png) and [discovery_track_plots/axis_heatmap.png](discovery_track_plots/axis_heatmap.png)
- Raw logs: `results/discovery_logs/`

Recommended public comparison bundle:

```bash
# Produces a new timestamped build/eval_runs/discovery_*/ bundle.
./scripts/run_discovery_bundle.sh
```

The tracked paths above are historical artifacts. The wrapper refuses to
overwrite them unless `ALLOW_TRACKED_DISCOVERY_OUTPUT=1` is explicitly set for
intentional maintenance.

Public-note framing:

- `perturb_followup_01` is the most perturbation-follow-up-specific task because it scores next-experiment choice under conflicting evidence.
- `target_prioritize_01` is the cleanest “do you inspect all the evidence before ranking?” task.
- `target_validate_01` is the fastest sanity check on whether the agent can choose and interpret the right first orthogonal assay.
