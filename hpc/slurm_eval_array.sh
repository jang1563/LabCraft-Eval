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
REPO_ROOT=$(pwd -P)
export PYTHONPATH="${REPO_ROOT}${PYTHONPATH:+:${PYTHONPATH}}"

SNAPSHOT_TASKS="transform_01 growth_01 pcr_01 screen_01 clone_01"
CURRENT_TASKS="${SNAPSHOT_TASKS} golden_gate_01 gibson_01 miniprep_01 express_01 purify_01 followup_01"
DISCOVERY_TASKS="perturb_followup_01 target_prioritize_01 target_validate_01"
SAFETY_CASE_TASKS="safety_case_01"
P2B_DEVELOPMENT_TASKS="pcr_causal_reasoning_01"
ALL_TASKS="${CURRENT_TASKS} ${DISCOVERY_TASKS}"

: "${RUN_ID:=$(date -u +%Y%m%dT%H%M%SZ)}"
: "${TASK_PRESET:=current}"
: "${MODEL_MATRIX:=current_balanced}"
: "${SEEDS_TOTAL:=10}"
: "${SEED_START:=0}"
: "${VENV_DIR:=${HOME}/labcraft-py313}"
: "${BUNDLE_DIR:=${REPO_ROOT}/results/hpc/${RUN_ID}}"
: "${LOG_DIR:=${BUNDLE_DIR}/logs}"
: "${REQUIRE_MODEL_PROVENANCE:=1}"

if [ "${GENERATE_CONFIG_FILE+x}" = "x" ] || [ "${GENERATE_CONFIG_ARGS+x}" = "x" ]; then
  echo "HPC release cells require registry generation profiles." >&2
  echo "Unset GENERATE_CONFIG_FILE and GENERATE_CONFIG_ARGS; edit the registry deliberately." >&2
  exit 2
fi

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

RUNTIME_SOURCE_ROOT=$(
  python_exec -c \
    'from pathlib import Path; import src; print(Path(src.__file__).resolve().parents[1])'
) || {
  echo "Could not resolve the imported LabCraft source root." >&2
  exit 2
}
if [ "$RUNTIME_SOURCE_ROOT" != "$REPO_ROOT" ]; then
  echo "Runtime source mismatch: expected $REPO_ROOT, imported $RUNTIME_SOURCE_ROOT" >&2
  exit 2
fi

EXPECTED_INSPECT_VERSION=$(
  python_exec - <<'PY'
import tomllib
from pathlib import Path

with Path("pyproject.toml").open("rb") as handle:
    dependencies = tomllib.load(handle)["project"]["dependencies"]
pins = [
    dependency.split("==", 1)[1]
    for dependency in dependencies
    if dependency.lower().startswith("inspect-ai==")
]
if len(pins) != 1 or not pins[0]:
    raise SystemExit("project dependencies must contain one exact inspect-ai pin")
print(pins[0])
PY
)
ACTUAL_INSPECT_VERSION=$(python_exec -c \
  'from importlib.metadata import version; print(version("inspect-ai"))')
if [ "$ACTUAL_INSPECT_VERSION" != "$EXPECTED_INSPECT_VERSION" ]; then
  echo "Inspect version mismatch: expected $EXPECTED_INSPECT_VERSION, installed $ACTUAL_INSPECT_VERSION" >&2
  exit 2
fi

if [ "${MODELS+x}" != "x" ]; then
  MODELS=$(python_exec scripts/model_matrix.py matrix "$MODEL_MATRIX" --format space)
  MODEL_SOURCE="matrix:${MODEL_MATRIX}"
else
  MODEL_SOURCE="explicit"
fi

TASKS="${TASKS:-}"
if [ -z "$TASKS" ]; then
  TASK_SOURCE="preset:${TASK_PRESET}"
  case "$TASK_PRESET" in
    snapshot) TASKS="$SNAPSHOT_TASKS" ;;
    current) TASKS="$CURRENT_TASKS" ;;
    discovery) TASKS="$DISCOVERY_TASKS" ;;
    safety_case) TASKS="$SAFETY_CASE_TASKS" ;;
    all) TASKS="$ALL_TASKS" ;;
    p2b_dev) TASKS="$P2B_DEVELOPMENT_TASKS" ;;
    *)
      echo "Unknown TASK_PRESET: $TASK_PRESET" >&2
      exit 1
      ;;
  esac
else
  TASK_SOURCE="explicit"
fi

for requested_task in $TASKS; do
  if [ "$requested_task" = "pcr_causal_reasoning_01" ]; then
    P2B_EXTERNAL_AUTHORIZED=$(
      python_exec -c \
        'from src.p2b_contracts import load_p2b_contract; print(str(load_p2b_contract()["external_evaluation_authorized"]).lower())'
    ) || {
      echo "Could not read the P2b external-evaluation authorization gate." >&2
      exit 2
    }
    if [ "$P2B_EXTERNAL_AUTHORIZED" != "true" ]; then
      echo "P2b HPC execution is not authorized: $requested_task" >&2
      exit 2
    fi
  fi
done

TASK_ARRAY=()
MODEL_ARRAY=()
read -r -a TASK_ARRAY <<< "$TASKS" || true
read -r -a MODEL_ARRAY <<< "$MODELS" || true

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
MODEL_KEY=$(python_exec scripts/model_matrix.py field "$MODEL" key)
MODEL_PROVIDER=$(python_exec scripts/model_matrix.py field "$MODEL" provider)
EXPECTED_RESOLVED_MODEL=$(
  python_exec scripts/model_matrix.py field "$MODEL" expected_resolved_model
)
GENERATION_PROFILE_JSON=$(python_exec scripts/model_matrix.py generate-config "$MODEL")
INSPECT_EVAL_ARGS_VALUE="${INSPECT_EVAL_ARGS:-}"

if [ -z "${INSPECT_HOME:-}" ]; then
  export INSPECT_HOME="${TMPDIR:-/tmp}/inspect_ai_home/${SLURM_JOB_ID:-manual}/${ARRAY_ID}"
fi

COMMIT_SHA="$(git rev-parse HEAD)"
WORKTREE_STATUS=$(git status --porcelain --untracked-files=all)
if [ -n "$WORKTREE_STATUS" ]; then
  echo "Refusing API-backed HPC evaluation from a dirty worktree: $REPO_ROOT" >&2
  echo "$WORKTREE_STATUS" >&2
  exit 2
fi
WORKTREE_DIRTY=0
MODEL_REGISTRY_SHA256=$(python_exec -c \
  'import hashlib, pathlib; print(hashlib.sha256(pathlib.Path("config/model_matrix.toml").read_bytes()).hexdigest())')
MANIFEST_PATH="${BUNDLE_DIR}/manifests/cell_${ARRAY_ID}.json"

mkdir -p "$LOG_DIR" "${BUNDLE_DIR}/manifests" "${BUNDLE_DIR}/stdout" "${REPO_ROOT}/results/hpc/slurm"

python_exec - \
  "$MANIFEST_PATH" \
  "$RUN_ID" \
  "$ARRAY_ID" \
  "${SLURM_JOB_ID:-manual}" \
  "$COMMIT_SHA" \
  "$WORKTREE_DIRTY" \
  "$TASK_SOURCE" \
  "$TASK_PRESET" \
  "$TASK" \
  "$MODEL_SOURCE" \
  "$MODEL_MATRIX" \
  "$MODEL_KEY" \
  "$MODEL" \
  "$MODEL_PROVIDER" \
  "$EXPECTED_RESOLVED_MODEL" \
  "$GENERATION_PROFILE_JSON" \
  "$EXPECTED_INSPECT_VERSION" \
  "$INSPECT_EVAL_ARGS_VALUE" \
  "$MODEL_REGISTRY_SHA256" \
  "$RUNTIME_SOURCE_ROOT" \
  "$SEED" \
  "$SEEDS_TOTAL" \
  "$SEED_START" \
  "$LOG_DIR" \
  "$BUNDLE_DIR" <<'PY'
import json
import sys
from pathlib import Path

(
    manifest_path,
    run_id,
    array_id,
    slurm_job_id,
    commit_sha,
    worktree_dirty,
    task_source,
    task_preset,
    task,
    model_source,
    model_matrix,
    model_key,
    model,
    model_provider,
    expected_resolved_model,
    generation_profile_json,
    expected_inspect_version,
    inspect_eval_args,
    model_registry_sha256,
    runtime_source_root,
    seed,
    seeds_total,
    seed_start,
    log_dir,
    bundle_dir,
) = sys.argv[1:]

payload = {
    "schema_version": "1.2.0",
    "run_id": run_id,
    "array_id": int(array_id),
    "slurm_job_id": slurm_job_id,
    "commit_sha": commit_sha,
    "worktree_dirty": worktree_dirty == "1",
    "task_source": task_source,
    "task_preset": task_preset,
    "task": task,
    "model_source": model_source,
    "model_matrix": model_matrix if model_source.startswith("matrix:") else None,
    "model_key": model_key,
    "model": model,
    "requested_model": model,
    "provider": model_provider,
    "expected_resolved_model": expected_resolved_model,
    "generation_profile": json.loads(generation_profile_json),
    "expected_inspect_version": expected_inspect_version,
    "inspect_eval_args": inspect_eval_args,
    "model_registry_sha256": model_registry_sha256,
    "runtime_source_root": runtime_source_root,
    "seed": int(seed),
    "seeds_total": int(seeds_total),
    "seed_start": int(seed_start),
    "log_dir": log_dir,
    "bundle_dir": bundle_dir,
}
Path(manifest_path).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
PY

echo "LabCraft-Eval HPC eval cell"
echo "  run_id:      ${RUN_ID}"
echo "  array_id:    ${ARRAY_ID}/${TOTAL_CELLS}"
echo "  commit_sha:  ${COMMIT_SHA}"
echo "  dirty:       ${WORKTREE_DIRTY}"
echo "  task:        ${TASK}"
echo "  model source:${MODEL_SOURCE}"
echo "  model key:   ${MODEL_KEY}"
echo "  model:       ${MODEL}"
echo "  expected:    ${EXPECTED_RESOLVED_MODEL}"
echo "  profile:     ${GENERATION_PROFILE_JSON}"
echo "  inspect:     ${ACTUAL_INSPECT_VERSION}"
echo "  source root: ${RUNTIME_SOURCE_ROOT}"
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
PYTHON_BIN="$(python_exec -c 'import sys; print(sys.executable)')" \
  bash scripts/run_portfolio_eval.sh

if [ "${VALIDATE_EVAL_CELL:-1}" != "0" ]; then
  VALIDATE_ARGS=(
    scripts/validate_eval_cell.py
    --log-dir "${LOG_DIR}"
    --task "${TASK}"
    --model "${MODEL}"
    --seed "${SEED}"
    --expected-provider "${MODEL_PROVIDER}"
    --expected-resolved-model "${EXPECTED_RESOLVED_MODEL}"
    --expected-generation-config "${GENERATION_PROFILE_JSON}"
    --expected-inspect-version "${EXPECTED_INSPECT_VERSION}"
    --expected-revision-commit "${COMMIT_SHA}"
    --require-clean-revision
  )
  if [ "$REQUIRE_MODEL_PROVENANCE" != "0" ]; then
    VALIDATE_ARGS+=(--require-model-provenance)
  fi
  python_exec "${VALIDATE_ARGS[@]}"
fi
