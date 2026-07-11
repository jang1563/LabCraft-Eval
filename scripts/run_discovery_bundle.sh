#!/usr/bin/env bash
# Convenience wrapper for the recommended discovery-decision bundle.
#
# Runs the discovery preset through the portfolio runner, then writes a new
# aggregate table and plots under a timestamped build/eval_runs bundle.
set -euo pipefail

REPO_ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)

RUNNER_SCRIPT="${RUNNER_SCRIPT:-${REPO_ROOT}/scripts/run_portfolio_eval.sh}"
AGGREGATE_SCRIPT="${AGGREGATE_SCRIPT:-${REPO_ROOT}/scripts/aggregate_eval_results.py}"
PLOT_SCRIPT="${PLOT_SCRIPT:-${REPO_ROOT}/scripts/plot_scorecard.py}"

: "${MODEL_MATRIX:=discovery_current}"
: "${SEEDS:=3}"
: "${SEED_START:=0}"
: "${RUN_ID:=discovery_$(date -u +%Y%m%dT%H%M%SZ)}"
: "${BUNDLE_DIR:=${REPO_ROOT}/build/eval_runs/${RUN_ID}}"
: "${LOG_DIR:=${BUNDLE_DIR}/logs}"
: "${RESULTS_OUT:=${BUNDLE_DIR}/results.md}"
: "${PLOTS_OUT_DIR:=${BUNDLE_DIR}/plots}"
: "${ALLOW_TRACKED_DISCOVERY_OUTPUT:=0}"

TASK_PRESET="discovery"

run_python() {
  if [ -n "${PYTHON_BIN:-}" ]; then
    "${PYTHON_BIN}" "$@"
    return
  fi
  if [ -n "${VENV_DIR:-}" ] && [ -x "${VENV_DIR}/bin/python" ]; then
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

if [ "${MODELS+x}" != "x" ]; then
  MODELS=$(run_python "${REPO_ROOT}/scripts/model_matrix.py" matrix "$MODEL_MATRIX" --format space)
  MODEL_SOURCE="matrix:${MODEL_MATRIX}"
else
  MODEL_SOURCE="explicit"
fi
if [ -z "$MODELS" ]; then
  echo "MODELS cannot be empty." >&2
  exit 2
fi

canonical_path() {
  run_python -c 'from pathlib import Path; import sys; print(Path(sys.argv[1]).resolve())' "$1"
}

if [ "$ALLOW_TRACKED_DISCOVERY_OUTPUT" != "1" ]; then
  canonical_log_dir=$(canonical_path "$LOG_DIR")
  canonical_results_out=$(canonical_path "$RESULTS_OUT")
  canonical_plots_out=$(canonical_path "$PLOTS_OUT_DIR")
  tracked_log_dir=$(canonical_path "${REPO_ROOT}/results/discovery_logs")
  tracked_results_out=$(canonical_path "${REPO_ROOT}/results/discovery_track_results.md")
  tracked_plots_out=$(canonical_path "${REPO_ROOT}/results/discovery_track_plots")
  if [ "$canonical_log_dir" = "$tracked_log_dir" ] || \
     [ "$canonical_results_out" = "$tracked_results_out" ] || \
     [ "$canonical_plots_out" = "$tracked_plots_out" ]; then
    echo "Refusing to overwrite tracked discovery artifacts." >&2
    echo "Use a new bundle path or set ALLOW_TRACKED_DISCOVERY_OUTPUT=1." >&2
    exit 2
  fi
fi

mkdir -p "${LOG_DIR}" "$(dirname "${RESULTS_OUT}")" "${PLOTS_OUT_DIR}"

echo "Running Discovery decision bundle"
echo "  Model source: ${MODEL_SOURCE}"
echo "  Models: ${MODELS}"
echo "  Seeds: ${SEEDS}"
echo "  Seed start: ${SEED_START}"
echo "  Logs: ${LOG_DIR}"
echo "  Results: ${RESULTS_OUT}"
echo "  Plots: ${PLOTS_OUT_DIR}"
echo

TASK_PRESET="${TASK_PRESET}" \
LOG_DIR="${LOG_DIR}" \
MODELS="${MODELS}" \
SEEDS="${SEEDS}" \
SEED_START="${SEED_START}" \
  bash "${RUNNER_SCRIPT}"

run_python "${AGGREGATE_SCRIPT}" \
  --log-dir "${LOG_DIR}" \
  --out "${RESULTS_OUT}"

plot_models=()
read -r -a plot_models <<< "$MODELS"

run_python "${PLOT_SCRIPT}" \
  --log-dir "${LOG_DIR}" \
  --out-dir "${PLOTS_OUT_DIR}" \
  --task-preset discovery \
  --models "${plot_models[@]}"

echo
echo "Discovery bundle complete."
