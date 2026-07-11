#!/usr/bin/env bash
#SBATCH --job-name=bpb-aggregate
#SBATCH --output=results/hpc/slurm/%x_%j.out
#SBATCH --error=results/hpc/slurm/%x_%j.err
#SBATCH --time=00:30:00
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G

set -euo pipefail

REPO_ROOT="${REPO_ROOT:-${SLURM_SUBMIT_DIR:-$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)}}"
cd "$REPO_ROOT"

: "${RUN_ID:?Set RUN_ID to the bundle name under results/hpc.}"
: "${TASK_PRESET:=auto}"
: "${MODEL_MATRIX:=}"
: "${MODELS:=}"
: "${VENV_DIR:=/home/fs01/jak4013/labcraft-py313}"
: "${BUNDLE_DIR:=${REPO_ROOT}/results/hpc/${RUN_ID}}"
: "${LOG_DIR:=${BUNDLE_DIR}/logs}"
: "${RESULTS_OUT:=${BUNDLE_DIR}/results.md}"
: "${PLOTS_OUT_DIR:=${BUNDLE_DIR}/plots}"

mkdir -p "$BUNDLE_DIR" "$PLOTS_OUT_DIR" "${REPO_ROOT}/results/hpc/slurm"

python_exec() {
  if [ -n "${PYTHON_BIN:-}" ]; then
    "${PYTHON_BIN}" "$@"
    return
  fi
  if [ -x "${VENV_DIR}/bin/python" ]; then
    "${VENV_DIR}/bin/python" "$@"
    return
  fi
  if [ -x "${REPO_ROOT}/.venv/bin/python" ]; then
    "${REPO_ROOT}/.venv/bin/python" "$@"
    return
  fi
  if command -v uv >/dev/null 2>&1; then
    uv run python "$@"
    return
  fi
  python3 "$@"
}

if [ -n "$MODELS" ]; then
  MODEL_SOURCE="explicit"
elif [ -n "$MODEL_MATRIX" ]; then
  MODELS=$(python_exec scripts/model_matrix.py matrix "$MODEL_MATRIX" --format space)
  MODEL_SOURCE="matrix:${MODEL_MATRIX}"
else
  MODEL_SOURCE="observed"
fi

COMMIT_SHA="$(git rev-parse HEAD)"
WORKTREE_DIRTY=0
if [ -n "$(git status --porcelain --untracked-files=all)" ]; then
  WORKTREE_DIRTY=1
fi
MANIFEST_COUNT=$(find "${BUNDLE_DIR}/manifests" -name 'cell_*.json' -type f 2>/dev/null | wc -l | tr -d ' ')
EVAL_COUNT=$(find "${LOG_DIR}" -name '*.eval' -type f 2>/dev/null | wc -l | tr -d ' ')
MODEL_REGISTRY_SHA256=$(python_exec -c \
  'import hashlib, pathlib; print(hashlib.sha256(pathlib.Path("config/model_matrix.toml").read_bytes()).hexdigest())')

python_exec - \
  "${BUNDLE_DIR}/aggregate_manifest.json" \
  "$RUN_ID" "$COMMIT_SHA" "$WORKTREE_DIRTY" "$TASK_PRESET" "$MODEL_SOURCE" \
  "$MODEL_MATRIX" "$MODELS" "$MODEL_REGISTRY_SHA256" \
  "$LOG_DIR" "$RESULTS_OUT" "$PLOTS_OUT_DIR" \
  "$MANIFEST_COUNT" "$EVAL_COUNT" <<'PY'
import json
import sys
from pathlib import Path

(
    manifest_path,
    run_id,
    commit_sha,
    worktree_dirty,
    task_preset,
    model_source,
    model_matrix,
    models,
    model_registry_sha256,
    log_dir,
    results_out,
    plots_out_dir,
    manifest_count,
    eval_count,
) = sys.argv[1:]

payload = {
    "schema_version": "1.1.0",
    "run_id": run_id,
    "commit_sha": commit_sha,
    "worktree_dirty": worktree_dirty == "1",
    "task_preset": task_preset,
    "model_source": model_source,
    "model_matrix": model_matrix if model_source.startswith("matrix:") else None,
    "models": models.split(),
    "model_registry_sha256": model_registry_sha256,
    "log_dir": log_dir,
    "results_out": results_out,
    "plots_out_dir": plots_out_dir,
    "manifest_count": int(manifest_count),
    "eval_count": int(eval_count),
}
Path(manifest_path).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
PY

echo "Aggregating LabCraft-Eval HPC bundle"
echo "  run_id:         ${RUN_ID}"
echo "  commit_sha:     ${COMMIT_SHA}"
echo "  dirty:          ${WORKTREE_DIRTY}"
echo "  model_source:   ${MODEL_SOURCE}"
echo "  models:         ${MODELS:-<observed from logs>}"
echo "  log_dir:        ${LOG_DIR}"
echo "  eval_count:     ${EVAL_COUNT}"
echo "  results_out:    ${RESULTS_OUT}"
echo "  plots_out_dir:  ${PLOTS_OUT_DIR}"
echo

python_exec scripts/aggregate_eval_results.py \
  --log-dir "${LOG_DIR}" \
  --out "${RESULTS_OUT}"

if [ "$TASK_PRESET" = "safety_case" ]; then
  echo
  echo "Skipping scorecard plots for safety_case; safety axes are reported in ${RESULTS_OUT}."
  echo "Bundle aggregation complete: ${BUNDLE_DIR}"
  exit 0
fi

plot_args=(
  scripts/plot_scorecard.py
  --log-dir "${LOG_DIR}"
  --out-dir "${PLOTS_OUT_DIR}"
  --task-preset "${TASK_PRESET}"
)

if [ -n "$MODELS" ]; then
  read -r -a MODEL_ARRAY <<< "$MODELS"
  plot_args+=(--models "${MODEL_ARRAY[@]}")
fi

python_exec "${plot_args[@]}"

echo
echo "Bundle aggregation complete: ${BUNDLE_DIR}"
