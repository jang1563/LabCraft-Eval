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
#   MODELS="openai/gpt-4o-mini" ./scripts/run_portfolio_eval.sh
#   TASKS="transform_01 clone_01" ./scripts/run_portfolio_eval.sh
#   TASK_PRESET=current ./scripts/run_portfolio_eval.sh   # run the current implemented task set
#   TASK_PRESET=safety_case ./scripts/run_portfolio_eval.sh # run the safety-case track
#   TASK_PRESET=all ./scripts/run_portfolio_eval.sh       # run current + discovery tasks
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: ./scripts/run_portfolio_eval.sh [--help]

Run a task-by-model LabCraft-Eval portfolio. Configuration is supplied through
environment variables rather than positional arguments:

  TASK_PRESET  snapshot | current | discovery | safety_case | all
  TASKS        explicit whitespace-separated task IDs (overrides TASK_PRESET)
  MODELS       whitespace-separated Inspect model IDs
  SEEDS        samples per task/model cell (default: 3)
  SEED_START   first seed index (default: 0)
  RUN_ID       output bundle name (default: current UTC timestamp)
  LOG_DIR      Inspect log directory (default: build/eval_runs/<RUN_ID>)
  GENERATE_CONFIG_ARGS  pinned Inspect generation arguments
                        (default: --temperature 0 --max-tokens 4096)

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

REPO_ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$REPO_ROOT"

SNAPSHOT_TASKS="transform_01 growth_01 pcr_01 screen_01 clone_01"
CURRENT_TASKS="${SNAPSHOT_TASKS} golden_gate_01 gibson_01 miniprep_01 express_01 purify_01"
CURRENT_TASKS="${CURRENT_TASKS} followup_01"
DISCOVERY_TASKS="perturb_followup_01 target_prioritize_01 target_validate_01"
SAFETY_CASE_TASKS="safety_case_01"
ALL_TASKS="${CURRENT_TASKS} ${DISCOVERY_TASKS}"

: "${SEEDS:=3}"
: "${SEED_START:=0}"
: "${TASK_PRESET:=snapshot}"
: "${MODELS:=openai/gpt-4o-mini openai/gpt-4o anthropic/claude-haiku-4-5}"
: "${RUN_ID:=$(date -u +%Y%m%dT%H%M%SZ)}"
: "${LOG_DIR:=${REPO_ROOT}/build/eval_runs/${RUN_ID}}"
: "${ALLOW_FROZEN_LOG_DIR:=0}"
: "${GENERATE_CONFIG_ARGS:=--temperature 0 --max-tokens 4096}"
: "${INSPECT_EVAL_ARGS:=}"

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
PATH_PYTHON="${PYTHON_BIN:-python3}"
if ! command -v "$PATH_PYTHON" >/dev/null 2>&1 && [ ! -x "$PATH_PYTHON" ]; then
  echo "Python is required to canonicalize LOG_DIR safely: $PATH_PYTHON" >&2
  exit 127
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
    *)
      echo "Unknown TASK_PRESET: $TASK_PRESET" >&2
      echo "Expected one of: snapshot, current, discovery, safety_case, all" >&2
      exit 1
      ;;
  esac
  TASK_SOURCE="preset:${TASK_PRESET}"
else
  TASK_SOURCE="explicit"
fi

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
echo "  Models: $MODELS"
echo "  Seeds:  $SEEDS"
echo "  Seed start: $SEED_START"
echo "  Logs:   $LOG_DIR"
echo "  Generate config: $GENERATE_CONFIG_ARGS"
if [ -n "$INSPECT_EVAL_ARGS" ]; then
  echo "  Inspect args: $INSPECT_EVAL_ARGS"
fi
echo

read -r -a INSPECT_EVAL_ARGS_ARRAY <<< "$INSPECT_EVAL_ARGS"
read -r -a GENERATE_CONFIG_ARGS_ARRAY <<< "$GENERATE_CONFIG_ARGS"

attempted_runs=0
failed_runs=0
failed_cells=()

for task in $TASKS; do
  for model in $MODELS; do
    attempted_runs=$((attempted_runs + 1))
    echo "=== task=$task model=$model seeds=$SEEDS seed_start=$SEED_START ==="
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
