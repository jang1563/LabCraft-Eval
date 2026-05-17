import os
import subprocess
import sys
from pathlib import Path
from typing import Dict


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = REPO_ROOT / "scripts" / "run_portfolio_eval.sh"
DISCOVERY_BUNDLE_PATH = REPO_ROOT / "scripts" / "run_discovery_bundle.sh"


def _write_fake_inspect(tmp_path: Path) -> Path:
    fake_path = tmp_path / "fake_inspect.sh"
    fake_path.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
printf '%s\\n' "$*" >> "$FAKE_INSPECT_LOG"
for arg in "$@"; do
  if [ -n "${FAIL_MODEL:-}" ] && [ "$arg" = "$FAIL_MODEL" ]; then
    exit 1
  fi
done
exit 0
"""
    )
    fake_path.chmod(0o755)
    return fake_path


def _runner_env(tmp_path: Path, fake_inspect: Path, **overrides: str) -> Dict[str, str]:
    env = os.environ.copy()
    env.update(
        {
            "HOME": str(tmp_path / "home"),
            "INSPECT_BIN": str(fake_inspect),
            "FAKE_INSPECT_LOG": str(tmp_path / "inspect_calls.log"),
            "LOG_DIR": str(tmp_path / "logs"),
        }
    )
    env.update(overrides)
    return env


def _write_fake_runner(tmp_path: Path) -> Path:
    fake_path = tmp_path / "fake_runner.sh"
    fake_path.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
printf 'runner|TASK_PRESET=%s|LOG_DIR=%s|MODELS=%s|SEEDS=%s|SEED_START=%s\\n' \
  "${TASK_PRESET:-}" "${LOG_DIR:-}" "${MODELS:-}" "${SEEDS:-}" "${SEED_START:-}" >> "$CALL_LOG"
"""
    )
    fake_path.chmod(0o755)
    return fake_path


def _write_fake_python_script(tmp_path: Path, name: str, label: str) -> Path:
    fake_path = tmp_path / name
    fake_path.write_text(
        """import os
import sys
from pathlib import Path

Path(os.environ["CALL_LOG"]).open("a").write("{label}|" + " ".join(sys.argv[1:]) + "\\n")
""".format(label=label)
    )
    return fake_path


def test_run_portfolio_eval_passes_seed_parameters_and_succeeds(tmp_path):
    fake_inspect = _write_fake_inspect(tmp_path)
    env = _runner_env(
        tmp_path,
        fake_inspect,
        TASKS="transform_01",
        MODELS="openai/gpt-4o-mini",
        SEEDS="2",
        SEED_START="3",
    )

    proc = subprocess.run(
        ["bash", str(RUNNER_PATH)],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
    )

    assert proc.returncode == 0
    assert "Summary: 1/1 succeeded." in proc.stdout
    log_text = Path(env["FAKE_INSPECT_LOG"]).read_text()
    assert "src/inspect_task.py@transform_01" in log_text
    assert "--model openai/gpt-4o-mini" in log_text
    assert "seeds=2" in log_text
    assert "seed_start=3" in log_text


def test_run_portfolio_eval_exits_nonzero_after_partial_failures(tmp_path):
    fake_inspect = _write_fake_inspect(tmp_path)
    env = _runner_env(
        tmp_path,
        fake_inspect,
        TASKS="transform_01 growth_01",
        MODELS="openai/gpt-4o-mini anthropic/claude-haiku-4-5",
        FAIL_MODEL="anthropic/claude-haiku-4-5",
    )

    proc = subprocess.run(
        ["bash", str(RUNNER_PATH)],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
    )

    assert proc.returncode == 1
    assert "Summary: 2/4 succeeded." in proc.stdout
    assert "Failed cells (2):" in proc.stderr
    assert "task=transform_01 model=anthropic/claude-haiku-4-5" in proc.stderr
    assert "task=growth_01 model=anthropic/claude-haiku-4-5" in proc.stderr
    logged_calls = Path(env["FAKE_INSPECT_LOG"]).read_text().strip().splitlines()
    assert len(logged_calls) == 4


def test_run_portfolio_eval_fails_fast_when_inspect_binary_is_missing(tmp_path):
    missing_inspect = tmp_path / "missing_inspect"
    env = _runner_env(
        tmp_path,
        missing_inspect,
        TASKS="transform_01",
        MODELS="openai/gpt-4o-mini",
        PATH="/usr/bin:/bin",
    )

    proc = subprocess.run(
        ["bash", str(RUNNER_PATH)],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
    )

    assert proc.returncode == 127
    assert "Could not find an executable Inspect binary." in proc.stderr
    assert "Summary:" not in proc.stdout


def test_run_portfolio_eval_supports_discovery_preset(tmp_path):
    fake_inspect = _write_fake_inspect(tmp_path)
    env = _runner_env(
        tmp_path,
        fake_inspect,
        TASK_PRESET="discovery",
        MODELS="openai/gpt-4o-mini",
    )

    proc = subprocess.run(
        ["bash", str(RUNNER_PATH)],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
    )

    assert proc.returncode == 0
    log_text = Path(env["FAKE_INSPECT_LOG"]).read_text()
    assert "src/inspect_task.py@perturb_followup_01" in log_text
    assert "src/inspect_task.py@target_prioritize_01" in log_text
    assert "src/inspect_task.py@target_validate_01" in log_text


def test_run_portfolio_eval_passes_extra_inspect_args(tmp_path):
    fake_inspect = _write_fake_inspect(tmp_path)
    env = _runner_env(
        tmp_path,
        fake_inspect,
        TASKS="safety_case_01",
        MODELS="anthropic/claude-haiku-4-5",
        INSPECT_EVAL_ARGS="--max-samples 2 --max-connections 2",
    )

    proc = subprocess.run(
        ["bash", str(RUNNER_PATH)],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
    )

    assert proc.returncode == 0
    assert "Inspect args: --max-samples 2 --max-connections 2" in proc.stdout
    log_text = Path(env["FAKE_INSPECT_LOG"]).read_text()
    assert "--max-samples 2 --max-connections 2" in log_text


def test_run_discovery_bundle_wires_runner_aggregation_and_plotting(tmp_path):
    fake_runner = _write_fake_runner(tmp_path)
    fake_aggregate = _write_fake_python_script(tmp_path, "fake_aggregate.py", "aggregate")
    fake_plot = _write_fake_python_script(tmp_path, "fake_plot.py", "plot")
    call_log = tmp_path / "calls.log"

    env = os.environ.copy()
    env.update(
        {
            "CALL_LOG": str(call_log),
            "RUNNER_SCRIPT": str(fake_runner),
            "AGGREGATE_SCRIPT": str(fake_aggregate),
            "PLOT_SCRIPT": str(fake_plot),
            "PYTHON_BIN": sys.executable,
            "LOG_DIR": str(tmp_path / "discovery_logs"),
            "RESULTS_OUT": str(tmp_path / "discovery_track_results.md"),
            "PLOTS_OUT_DIR": str(tmp_path / "discovery_track_plots"),
        }
    )

    proc = subprocess.run(
        ["bash", str(DISCOVERY_BUNDLE_PATH)],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
    )

    assert proc.returncode == 0
    assert "Running Discovery decision bundle" in proc.stdout
    log_lines = call_log.read_text().strip().splitlines()
    assert "runner|TASK_PRESET=discovery" in log_lines[0]
    assert "MODELS=openai/gpt-4o-mini anthropic/claude-sonnet-4-5" in log_lines[0]
    assert "--log-dir {}".format(env["LOG_DIR"]) in log_lines[1]
    assert "--out {}".format(env["RESULTS_OUT"]) in log_lines[1]
    assert "--out-dir {}".format(env["PLOTS_OUT_DIR"]) in log_lines[2]
    assert "--task-preset discovery" in log_lines[2]
    assert "--models openai/gpt-4o-mini anthropic/claude-sonnet-4-5" in log_lines[2]
