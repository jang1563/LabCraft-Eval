#!/usr/bin/env bash
# Portfolio evaluation runner: tasks x models x seeds
#
# Runs each LabCraft task across the configured model list using the
# `seeds` task parameter to expand into N seed-labelled samples per task.
#
# Usage:
#   ./scripts/run_portfolio_eval.sh                       # snapshot tasks, new build/eval_runs bundle
#   SEEDS=5 ./scripts/run_portfolio_eval.sh               # 5 seeds per task per model
#   SEEDS=2 SEED_START=3 ./scripts/run_portfolio_eval.sh  # run only seeds 03-04
#   MODEL_MATRIX=current_balanced ./scripts/run_portfolio_eval.sh
#   MODELS="openai/gpt-5.6-sol" ./scripts/run_portfolio_eval.sh
#   TASKS="transform_01 clone_01" ./scripts/run_portfolio_eval.sh
#   TASK_PRESET=current ./scripts/run_portfolio_eval.sh   # run the current implemented task set
#   TASK_PRESET=safety_case ./scripts/run_portfolio_eval.sh # run the safety-case track
#   TASK_PRESET=all ./scripts/run_portfolio_eval.sh       # run current + discovery tasks
#   TASK_PRESET=p2b_dev ./scripts/run_portfolio_eval.sh   # reserved; blocked until authorized
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: ./scripts/run_portfolio_eval.sh [--help]

Run a task-by-model LabCraft-Eval portfolio. Configuration is supplied through
environment variables rather than positional arguments:

  TASK_PRESET  snapshot | current | discovery | safety_case | all | p2b_dev
  TASKS        explicit whitespace-separated task IDs (overrides TASK_PRESET)
  MODEL_MATRIX registered matrix name (default: current_balanced)
  MODELS       whitespace-separated registered Inspect model IDs;
               overrides MODEL_MATRIX
  SEEDS        samples per task/model cell (default: 3)
  SEED_START   first seed index (default: 0)
  RUN_ID       output bundle name (default: current UTC timestamp)
  LOG_DIR      Inspect log directory (default: build/eval_runs/<RUN_ID>)
  GENERATE_CONFIG_FILE  explicit Inspect GenerateConfig JSON/YAML; overrides
                        the registered per-model profile
  GENERATE_CONFIG_ARGS  legacy whitespace-separated generation arguments;
                        overrides the registered per-model profile

The historical results/logs directory is frozen. Setting LOG_DIR to that path,
or a child path, requires the explicit opt-in ALLOW_FROZEN_LOG_DIR=1.
EOF
}

if [ "$#" -gt 0 ]; then
  if [ "$#" -eq 1 ] && { [ "$1" = "--help" ] || [ "$1" = "-h" ]; }; then
    usage
    exit 0
  fi
  echo "Unexpected positional arguments: $*" >&2
  usage >&2
  exit 2
fi

REPO_ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$REPO_ROOT"
# Console-script entry points put their own bin directory ahead of the current
# working directory. Prefix this checkout explicitly so a reused editable venv
# cannot import LabCraft from a different repository clone.
export PYTHONPATH="${REPO_ROOT}${PYTHONPATH:+:${PYTHONPATH}}"

SNAPSHOT_TASKS="transform_01 growth_01 pcr_01 screen_01 clone_01"
CURRENT_TASKS="${SNAPSHOT_TASKS} golden_gate_01 gibson_01 miniprep_01 express_01 purify_01"
CURRENT_TASKS="${CURRENT_TASKS} followup_01"
DISCOVERY_TASKS="perturb_followup_01 target_prioritize_01 target_validate_01"
SAFETY_CASE_TASKS="safety_case_01"
P2B_DEVELOPMENT_TASKS="pcr_causal_reasoning_01"
ALL_TASKS="${CURRENT_TASKS} ${DISCOVERY_TASKS}"

: "${SEEDS:=3}"
: "${SEED_START:=0}"
: "${TASK_PRESET:=snapshot}"
: "${MODEL_MATRIX:=current_balanced}"
: "${RUN_ID:=$(date -u +%Y%m%dT%H%M%SZ)}"
: "${LOG_DIR:=${REPO_ROOT}/build/eval_runs/${RUN_ID}}"
: "${ALLOW_FROZEN_LOG_DIR:=0}"
: "${GENERATE_CONFIG_FILE:=}"
: "${INSPECT_EVAL_ARGS:=}"

GENERATE_CONFIG_ARGS_WAS_SET=0
if [ "${GENERATE_CONFIG_ARGS+x}" = "x" ]; then
  GENERATE_CONFIG_ARGS_WAS_SET=1
fi
if [ -n "$GENERATE_CONFIG_FILE" ] && [ "$GENERATE_CONFIG_ARGS_WAS_SET" = "1" ]; then
  echo "Set only one of GENERATE_CONFIG_FILE or GENERATE_CONFIG_ARGS." >&2
  exit 2
fi
if [ "$GENERATE_CONFIG_ARGS_WAS_SET" = "1" ] && [ -z "${GENERATE_CONFIG_ARGS:-}" ]; then
  echo "GENERATE_CONFIG_ARGS cannot be empty; use a registered profile or explicit config file." >&2
  exit 2
fi
if [ -n "$GENERATE_CONFIG_FILE" ] && [ ! -r "$GENERATE_CONFIG_FILE" ]; then
  echo "GENERATE_CONFIG_FILE is not readable: $GENERATE_CONFIG_FILE" >&2
  exit 2
fi

case "$SEEDS" in
  ''|*[!0-9]*)
    echo "SEEDS must be a positive integer: $SEEDS" >&2
    exit 2
    ;;
esac
if [ "$SEEDS" -lt 1 ]; then
  echo "SEEDS must be a positive integer: $SEEDS" >&2
  exit 2
fi
case "$SEED_START" in
  ''|*[!0-9]*)
    echo "SEED_START must be a non-negative integer: $SEED_START" >&2
    exit 2
    ;;
esac

if [ "${LOG_DIR#/}" = "$LOG_DIR" ]; then
  LOG_DIR="${REPO_ROOT}/${LOG_DIR#./}"
fi
LOG_DIR="${LOG_DIR%/}"
if [ -n "${PYTHON_BIN:-}" ]; then
  PATH_PYTHON="$PYTHON_BIN"
elif [ -n "${VENV_DIR:-}" ] && [ -x "${VENV_DIR}/bin/python" ]; then
  PATH_PYTHON="${VENV_DIR}/bin/python"
elif [ -n "${VIRTUAL_ENV:-}" ] && [ -x "${VIRTUAL_ENV}/bin/python" ]; then
  PATH_PYTHON="${VIRTUAL_ENV}/bin/python"
elif [ -x "${REPO_ROOT}/.venv/bin/python" ]; then
  PATH_PYTHON="${REPO_ROOT}/.venv/bin/python"
else
  PATH_PYTHON=python3
fi
if ! command -v "$PATH_PYTHON" >/dev/null 2>&1 && [ ! -x "$PATH_PYTHON" ]; then
  echo "Python is required to canonicalize LOG_DIR safely: $PATH_PYTHON" >&2
  exit 127
fi
RUNTIME_SOURCE_ROOT=$(
  "$PATH_PYTHON" -c \
    'from pathlib import Path; import src; print(Path(src.__file__).resolve().parents[1])'
) || {
  echo "Could not resolve the imported LabCraft source root." >&2
  exit 2
}
if [ "$RUNTIME_SOURCE_ROOT" != "$REPO_ROOT" ]; then
  echo "Runtime source mismatch: expected $REPO_ROOT, imported $RUNTIME_SOURCE_ROOT" >&2
  exit 2
fi
LOG_DIR=$("$PATH_PYTHON" -c 'from pathlib import Path; import sys; print(Path(sys.argv[1]).resolve())' "$LOG_DIR")
FROZEN_LOG_DIR=$("$PATH_PYTHON" -c 'from pathlib import Path; import sys; print(Path(sys.argv[1]).resolve())' "${REPO_ROOT}/results/logs")
case "$LOG_DIR" in
  "$FROZEN_LOG_DIR"|"$FROZEN_LOG_DIR"/*)
    if [ "$ALLOW_FROZEN_LOG_DIR" != "1" ]; then
      echo "Refusing to write into frozen log path: $LOG_DIR" >&2
      echo "Use a new LOG_DIR, or set ALLOW_FROZEN_LOG_DIR=1 for intentional maintenance." >&2
      exit 2
    fi
    ;;
esac

MODEL_MATRIX_TOOL="${REPO_ROOT}/scripts/model_matrix.py"
if [ "${MODELS+x}" != "x" ]; then
  if ! MODELS=$("$PATH_PYTHON" "$MODEL_MATRIX_TOOL" matrix "$MODEL_MATRIX" --format space); then
    exit 2
  fi
  MODEL_SOURCE="matrix:${MODEL_MATRIX}"
else
  MODEL_SOURCE="explicit"
fi

TASKS="${TASKS:-}"
if [ -z "$TASKS" ]; then
  case "$TASK_PRESET" in
    snapshot)
      TASKS="$SNAPSHOT_TASKS"
      ;;
    current)
      TASKS="$CURRENT_TASKS"
      ;;
    discovery)
      TASKS="$DISCOVERY_TASKS"
      ;;
    safety_case)
      TASKS="$SAFETY_CASE_TASKS"
      ;;
    all)
      TASKS="$ALL_TASKS"
      ;;
    p2b_dev)
      TASKS="$P2B_DEVELOPMENT_TASKS"
      ;;
    *)
      echo "Unknown TASK_PRESET: $TASK_PRESET" >&2
      echo "Expected one of: snapshot, current, discovery, safety_case, all, p2b_dev" >&2
      exit 1
      ;;
  esac
  TASK_SOURCE="preset:${TASK_PRESET}"
else
  TASK_SOURCE="explicit"
fi

for requested_task in $TASKS; do
  if [ "$requested_task" = "pcr_causal_reasoning_01" ]; then
    P2B_EXTERNAL_AUTHORIZED=$(
      "$PATH_PYTHON" -c \
        'from src.p2b_contracts import load_p2b_contract; print(str(load_p2b_contract()["external_evaluation_authorized"]).lower())'
    ) || {
      echo "Could not read the P2b external-evaluation authorization gate." >&2
      exit 2
    }
    if [ "$P2B_EXTERNAL_AUTHORIZED" != "true" ]; then
      echo "P2b external model execution is not authorized: $requested_task" >&2
      echo "Run scripts/validate_p2b_contracts.py for local scorer validation instead." >&2
      exit 2
    fi
  fi
done

# Pull API keys from the user's standard dotfile (ANTHROPIC_API_KEY, OPENAI_API_KEY).
if [ -f "$HOME/.api_keys" ]; then
  # shellcheck disable=SC1091
  source "$HOME/.api_keys" >/dev/null 2>&1
fi

if [ -n "${INSPECT_HOME:-}" ]; then
  :
elif [ -n "${SLURM_JOB_ID:-}" ]; then
  INSPECT_HOME="${TMPDIR:-/tmp}/inspect_ai_home/${SLURM_JOB_ID}/${SLURM_ARRAY_TASK_ID:-0}"
else
  INSPECT_HOME=/tmp/inspect_ai_home
fi

export HOME="$INSPECT_HOME"
export XDG_DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
export XDG_CACHE_HOME="${XDG_CACHE_HOME:-$HOME/.cache}"
mkdir -p "$XDG_DATA_HOME" "$XDG_CACHE_HOME" "$LOG_DIR"

if [ -n "${INSPECT_BIN:-}" ]; then
  if [ ! -x "$INSPECT_BIN" ]; then
    echo "Could not find an executable Inspect binary." >&2
    echo "Set INSPECT_BIN=/path/to/inspect or install inspect into PATH." >&2
    exit 127
  fi
else
  if [ -x "${REPO_ROOT}/.venv/bin/inspect" ]; then
    INSPECT_BIN="${REPO_ROOT}/.venv/bin/inspect"
  elif command -v inspect >/dev/null 2>&1; then
    INSPECT_BIN=$(command -v inspect)
  else
    echo "Could not find an executable Inspect binary." >&2
    echo "Set INSPECT_BIN=/path/to/inspect or install inspect into PATH." >&2
    exit 127
  fi
fi

echo "Running portfolio eval"
echo "  Task source: $TASK_SOURCE"
echo "  Tasks:  $TASKS"
echo "  Model source: $MODEL_SOURCE"
echo "  Models: $MODELS"
echo "  Seeds:  $SEEDS"
echo "  Seed start: $SEED_START"
echo "  Logs:   $LOG_DIR"
echo "  Runtime source: $RUNTIME_SOURCE_ROOT"
if [ -n "$GENERATE_CONFIG_FILE" ]; then
  echo "  Generate config: $GENERATE_CONFIG_FILE"
elif [ "$GENERATE_CONFIG_ARGS_WAS_SET" = "1" ]; then
  echo "  Generate config: ${GENERATE_CONFIG_ARGS:-<none>} (legacy override)"
else
  echo "  Generate config: registered per-model profiles"
fi
if [ -n "$INSPECT_EVAL_ARGS" ]; then
  echo "  Inspect args: $INSPECT_EVAL_ARGS"
fi
echo

read -r -a INSPECT_EVAL_ARGS_ARRAY <<< "$INSPECT_EVAL_ARGS"
TASK_ARRAY=()
MODEL_ARRAY=()
read -r -a TASK_ARRAY <<< "$TASKS" || true
read -r -a MODEL_ARRAY <<< "$MODELS" || true

if [ "${#TASK_ARRAY[@]}" -eq 0 ] || [ "${#MODEL_ARRAY[@]}" -eq 0 ]; then
  echo "TASKS and MODELS must both be non-empty." >&2
  exit 2
fi
for model in "${MODEL_ARRAY[@]}"; do
  "$PATH_PYTHON" "$MODEL_MATRIX_TOOL" field "$model" key >/dev/null || exit 2
done

attempted_runs=0
failed_runs=0
failed_cells=()

for task in "${TASK_ARRAY[@]}"; do
  for model in "${MODEL_ARRAY[@]}"; do
    attempted_runs=$((attempted_runs + 1))
    echo "=== task=$task model=$model seeds=$SEEDS seed_start=$SEED_START ==="
    GENERATE_CONFIG_ARGS_ARRAY=()
    if [ -n "$GENERATE_CONFIG_FILE" ]; then
      GENERATE_CONFIG_ARGS_ARRAY=(--generate-config "$GENERATE_CONFIG_FILE")
    elif [ "$GENERATE_CONFIG_ARGS_WAS_SET" = "1" ]; then
      read -r -a GENERATE_CONFIG_ARGS_ARRAY <<< "${GENERATE_CONFIG_ARGS:-}"
    else
      MODEL_KEY=$("$PATH_PYTHON" "$MODEL_MATRIX_TOOL" field "$model" key) || exit 2
      MODEL_CONFIG_PATH="${LOG_DIR}/model_configs/${MODEL_KEY}.json"
      "$PATH_PYTHON" "$MODEL_MATRIX_TOOL" generate-config "$model" --out "$MODEL_CONFIG_PATH" || exit 2
      GENERATE_CONFIG_ARGS_ARRAY=(--generate-config "$MODEL_CONFIG_PATH")
      echo "  Model profile: $MODEL_KEY ($MODEL_CONFIG_PATH)"
    fi
    if "$INSPECT_BIN" eval "src/inspect_task.py@${task}" \
      --model "$model" \
      -T "seeds=${SEEDS}" \
      -T "seed_start=${SEED_START}" \
      "${GENERATE_CONFIG_ARGS_ARRAY[@]}" \
      "${INSPECT_EVAL_ARGS_ARRAY[@]+"${INSPECT_EVAL_ARGS_ARRAY[@]}"}" \
      --log-dir "$LOG_DIR"; then
      :
    else
      failed_runs=$((failed_runs + 1))
      failed_cells+=("task=${task} model=${model}")
      echo "!! run failed: task=$task model=$model" >&2
    fi
  done
done

succeeded_runs=$((attempted_runs - failed_runs))

echo
echo "All runs attempted. Summary: ${succeeded_runs}/${attempted_runs} succeeded."
if [ "$failed_runs" -gt 0 ]; then
  echo "Failed cells (${failed_runs}):" >&2
  for cell in "${failed_cells[@]}"; do
    echo "  ${cell}" >&2
  done
fi
echo "Aggregate with:"
echo "  python3 scripts/aggregate_eval_results.py --log-dir \"$LOG_DIR\" --out \"$LOG_DIR/results.md\""

if [ "$failed_runs" -gt 0 ]; then
  exit 1
fi
