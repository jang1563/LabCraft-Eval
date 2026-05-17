#!/usr/bin/env bash
# Portfolio evaluation runner: tasks x models x seeds
#
# Runs each LabCraft task across the configured model list using the
# `seeds` task parameter to expand into N stochastic samples per task.
#
# Usage:
#   ./scripts/run_portfolio_eval.sh                       # run the default snapshot task set
#   SEEDS=5 ./scripts/run_portfolio_eval.sh               # 5 seeds per task per model
#   SEEDS=2 SEED_START=3 ./scripts/run_portfolio_eval.sh  # run only seeds 03-04
#   MODELS="openai/gpt-4o-mini" ./scripts/run_portfolio_eval.sh
#   TASKS="transform_01 clone_01" ./scripts/run_portfolio_eval.sh
#   TASK_PRESET=current ./scripts/run_portfolio_eval.sh   # run the current implemented task set
#   TASK_PRESET=safety_case ./scripts/run_portfolio_eval.sh # run the safety-case track
#   TASK_PRESET=all ./scripts/run_portfolio_eval.sh       # run current + discovery tasks
set -euo pipefail

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
: "${LOG_DIR:=${REPO_ROOT}/results/logs}"
: "${INSPECT_EVAL_ARGS:=}"

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
  INSPECT_BIN=/tmp/labcraft-py311/bin/inspect
  if [ ! -x "$INSPECT_BIN" ]; then
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
fi

echo "Running portfolio eval"
echo "  Task source: $TASK_SOURCE"
echo "  Tasks:  $TASKS"
echo "  Models: $MODELS"
echo "  Seeds:  $SEEDS"
echo "  Seed start: $SEED_START"
echo "  Logs:   $LOG_DIR"
if [ -n "$INSPECT_EVAL_ARGS" ]; then
  echo "  Inspect args: $INSPECT_EVAL_ARGS"
fi
echo

read -r -a INSPECT_EVAL_ARGS_ARRAY <<< "$INSPECT_EVAL_ARGS"

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
      "${INSPECT_EVAL_ARGS_ARRAY[@]}" \
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
if [ "$LOG_DIR" = "${REPO_ROOT}/results/logs" ]; then
  echo "  python3 scripts/aggregate_eval_results.py"
else
  echo "  python3 scripts/aggregate_eval_results.py --log-dir \"$LOG_DIR\""
fi

if [ "$failed_runs" -gt 0 ]; then
  exit 1
fi
