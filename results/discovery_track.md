# Discovery Decision Track

This bundle isolates the repo’s discovery-decision tasks:

- `perturb_followup_01`
- `target_prioritize_01`
- `target_validate_01`

What this track measures:

- whether an agent inspects perturbation-style evidence before acting
- whether it chooses the right next discovery experiment
- whether it interprets that result correctly
- whether it avoids wasted tool use

This track is intentionally small and auditable. It is not trying to be a general biomedical agent benchmark. The point is to create a compact, recruiter-readable demonstration that LabCraft-Eval can evaluate discovery-decision quality as well as wet-lab execution reliability.

Current 2-model / 3-seed bundle:

| Task | gpt-4o-mini | claude-sonnet-4-5 |
|---|---:|---:|
| `perturb_followup_01` | 0.814 ± 0.038 | 0.933 ± 0.000 |
| `target_prioritize_01` | 0.375 ± 0.043 | 0.425 ± 0.000 |
| `target_validate_01` | 0.867 ± 0.000 | 0.933 ± 0.067 |
| **Mean across tasks** | **0.685** | **0.764** |

Interpretation:

- `perturb_followup_01` is already the strongest discriminator in this bundle. Both models complete the task, but `claude-sonnet-4-5` is better at explaining the QC ambiguity and the orthogonal non-support cleanly.
- `target_validate_01` is also healthy: both models choose the right assay and decision, with the remaining spread coming from interpretation quality rather than experimental choice.
- `target_prioritize_01` is the current weak point for both models. The failure mode is not coverage or tool use; it is getting the final ranking/risk framing exactly right. That makes it a useful discovery-facing task because it exposes a real decision-quality gap rather than a simulator-execution bug.

Artifacts from this bundle:

- Aggregated table: [discovery_track_results.md](discovery_track_results.md)
- Plots: [discovery_track_plots/scorecard.png](discovery_track_plots/scorecard.png) and [discovery_track_plots/axis_heatmap.png](discovery_track_plots/axis_heatmap.png)
- Raw logs: `results/discovery_logs/`

Recommended public comparison bundle:

```bash
./scripts/run_discovery_bundle.sh

# Equivalent explicit commands:
LOG_DIR=results/discovery_logs \
TASK_PRESET=discovery \
SEEDS=3 \
MODELS="openai/gpt-4o-mini anthropic/claude-sonnet-4-5" \
  ./scripts/run_portfolio_eval.sh
uv run python scripts/aggregate_eval_results.py --log-dir results/discovery_logs --out results/discovery_track_results.md
uv run python scripts/plot_scorecard.py --log-dir results/discovery_logs --out-dir results/discovery_track_plots --task-preset discovery --models openai/gpt-4o-mini anthropic/claude-sonnet-4-5
```

Public-note framing:

- `perturb_followup_01` is the most perturbation-follow-up-specific task because it scores next-experiment choice under conflicting evidence.
- `target_prioritize_01` is the cleanest “do you inspect all the evidence before ranking?” task.
- `target_validate_01` is the fastest sanity check on whether the agent can choose and interpret the right first orthogonal assay.
