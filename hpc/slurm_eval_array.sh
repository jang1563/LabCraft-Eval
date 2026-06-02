#!/usr/bin/env bash
#SBATCH --job-name=bpb-eval
#SBATCH --output=results/hpc/slurm/%x_%A_%a.out
#SBATCH --error=results/hpc/slurm/%x_%A_%a.err
#SBATCH --time=02:00:00
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G

set -euo pipefail

REPO_ROOT="${REPO_ROOT:-${SLURM_SUBMIT_DIR:-$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)}}"
cd "$REPO_ROOT"

SNAPSHOT_TASKS="transform_01 growth_01 pcr_01 screen_01 clone_01"
CURRENT_TASKS="${SNAPSHOT_TASKS} golden_gate_01 gibson_01 miniprep_01 express_01 purify_01 followup_01"
DISCOVERY_TASKS="perturb_followup_01 target_prioritize_01 target_validate_01"
SAFETY_CASE_TASKS="safety_case_01"
ALL_TASKS="${CURRENT_TASKS} ${DISCOVERY_TASKS}"

: "${RUN_ID:=$(date -u +%Y%m%dT%H%M%SZ)}"
: "${TASK_PRESET:=current}"
: "${MODELS:=openai/gpt-4o-mini openai/gpt-4o anthropic/claude-haiku-4-5 anthropic/claude-sonnet-4-5}"
: "${SEEDS_TOTAL:=10}"
: "${SEED_START:=0}"
: "${VENV_DIR:=/home/fs01/jak4013/labcraft-py313}"
: "${BUNDLE_DIR:=${REPO_ROOT}/results/hpc/${RUN_ID}}"
: "${LOG_DIR:=${BUNDLE_DIR}/logs}"

if [ -z "${INSPECT_BIN:-}" ] && [ -x "${VENV_DIR}/bin/inspect" ]; then
  export INSPECT_BIN="${VENV_DIR}/bin/inspect"
fi

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
  python3 "$@"
}

TASKS="${TASKS:-}"
if [ -z "$TASKS" ]; then
  TASK_SOURCE="preset:${TASK_PRESET}"
  case "$TASK_PRESET" in
    snapshot) TASKS="$SNAPSHOT_TASKS" ;;
    current) TASKS="$CURRENT_TASKS" ;;
    discovery) TASKS="$DISCOVERY_TASKS" ;;
    safety_case) TASKS="$SAFETY_CASE_TASKS" ;;
    all) TASKS="$ALL_TASKS" ;;
    *)
      echo "Unknown TASK_PRESET: $TASK_PRESET" >&2
      exit 1
      ;;
  esac
else
  TASK_SOURCE="explicit"
fi

read -r -a TASK_ARRAY <<< "$TASKS"
read -r -a MODEL_ARRAY <<< "$MODELS"

if [ "${#TASK_ARRAY[@]}" -eq 0 ] || [ "${#MODEL_ARRAY[@]}" -eq 0 ]; then
  echo "TASKS and MODELS must both be non-empty." >&2
  exit 1
fi

TOTAL_CELLS=$((${#TASK_ARRAY[@]} * ${#MODEL_ARRAY[@]} * SEEDS_TOTAL))
ARRAY_ID="${SLURM_ARRAY_TASK_ID:-0}"

if [ "$ARRAY_ID" -ge "$TOTAL_CELLS" ]; then
  echo "Array id ${ARRAY_ID} is outside total cell count ${TOTAL_CELLS}; exiting."
  exit 0
fi

SEED_OFFSET=$((ARRAY_ID % SEEDS_TOTAL))
MODEL_INDEX=$(((ARRAY_ID / SEEDS_TOTAL) % ${#MODEL_ARRAY[@]}))
TASK_INDEX=$((ARRAY_ID / (SEEDS_TOTAL * ${#MODEL_ARRAY[@]})))

TASK="${TASK_ARRAY[$TASK_INDEX]}"
MODEL="${MODEL_ARRAY[$MODEL_INDEX]}"
SEED=$((SEED_START + SEED_OFFSET))

mkdir -p "$LOG_DIR" "${BUNDLE_DIR}/manifests" "${BUNDLE_DIR}/stdout" "${REPO_ROOT}/results/hpc/slurm"

if [ -z "${INSPECT_HOME:-}" ]; then
  export INSPECT_HOME="${TMPDIR:-/tmp}/inspect_ai_home/${SLURM_JOB_ID:-manual}/${ARRAY_ID}"
fi

COMMIT_SHA="$(git rev-parse HEAD)"
MANIFEST_PATH="${BUNDLE_DIR}/manifests/cell_${ARRAY_ID}.json"

cat > "$MANIFEST_PATH" <<EOF
{
  "schema_version": "1.0.0",
  "run_id": "${RUN_ID}",
  "array_id": ${ARRAY_ID},
  "slurm_job_id": "${SLURM_JOB_ID:-manual}",
  "commit_sha": "${COMMIT_SHA}",
  "task_source": "${TASK_SOURCE}",
  "task_preset": "${TASK_PRESET}",
  "task": "${TASK}",
  "model": "${MODEL}",
  "seed": ${SEED},
  "seeds_total": ${SEEDS_TOTAL},
  "seed_start": ${SEED_START},
  "log_dir": "${LOG_DIR}",
  "bundle_dir": "${BUNDLE_DIR}"
}
EOF

echo "LabCraft-Eval HPC eval cell"
echo "  run_id:      ${RUN_ID}"
echo "  array_id:    ${ARRAY_ID}/${TOTAL_CELLS}"
echo "  commit_sha:  ${COMMIT_SHA}"
echo "  task:        ${TASK}"
echo "  model:       ${MODEL}"
echo "  seed:        ${SEED}"
echo "  log_dir:     ${LOG_DIR}"
echo "  manifest:    ${MANIFEST_PATH}"
echo

TASKS="${TASK}" \
MODELS="${MODEL}" \
SEEDS=1 \
SEED_START="${SEED}" \
LOG_DIR="${LOG_DIR}" \
INSPECT_HOME="${INSPECT_HOME}" \
  bash scripts/run_portfolio_eval.sh

if [ "${VALIDATE_EVAL_CELL:-1}" != "0" ]; then
  python_exec scripts/validate_eval_cell.py \
    --log-dir "${LOG_DIR}" \
    --task "${TASK}" \
    --model "${MODEL}" \
    --seed "${SEED}"
fi
