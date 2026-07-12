import json
import os
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Dict


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = REPO_ROOT / "scripts" / "run_portfolio_eval.sh"
DISCOVERY_BUNDLE_PATH = REPO_ROOT / "scripts" / "run_discovery_bundle.sh"
HPC_RUNNER_PATH = REPO_ROOT / "hpc" / "slurm_eval_array.sh"


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


def _write_python_with_fake_cell_validator(tmp_path: Path) -> Path:
    fake_path = tmp_path / "python_with_fake_validator.sh"
    fake_path.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
if [ "${{1:-}}" = "scripts/validate_eval_cell.py" ]; then
  printf '%s\\0' "$@" > "$VALIDATOR_LOG"
  exit 0
fi
exec {python} "$@"
""".format(python=shlex.quote(sys.executable))
    )
    fake_path.chmod(0o755)
    return fake_path


def _write_python_with_stale_source_probe(tmp_path: Path) -> Path:
    fake_path = tmp_path / "python_with_stale_source_probe.sh"
    fake_path.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
if [ "${{1:-}}" = "-c" ] && [[ "${{2:-}}" == *"import src"* ]]; then
  printf '/stale/editable/checkout\n'
  exit 0
fi
exec {python} "$@"
""".format(python=shlex.quote(sys.executable))
    )
    fake_path.chmod(0o755)
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
    assert "--generate-config " in log_text
    profile_path = Path(log_text.split("--generate-config ", 1)[1].split()[0])
    assert json.loads(profile_path.read_text()) == {"max_tokens": 4096, "temperature": 0.0}


def test_run_portfolio_eval_defaults_to_current_matrix_and_per_model_profiles(tmp_path):
    fake_inspect = _write_fake_inspect(tmp_path)
    env = _runner_env(
        tmp_path,
        fake_inspect,
        TASKS="transform_01",
        SEEDS="1",
    )
    env.pop("MODELS", None)

    proc = subprocess.run(
        ["bash", str(RUNNER_PATH)],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
    )

    assert proc.returncode == 0, proc.stderr
    assert "Model source: matrix:current_balanced" in proc.stdout
    calls = [shlex.split(line) for line in Path(env["FAKE_INSPECT_LOG"]).read_text().splitlines()]
    assert [call[call.index("--model") + 1] for call in calls] == [
        "openai/gpt-5.6-sol",
        "openai/gpt-5.6-luna",
        "anthropic/claude-sonnet-5",
        "anthropic/claude-haiku-4-5-20251001",
    ]
    for call in calls:
        profile_path = Path(call[call.index("--generate-config") + 1])
        profile = json.loads(profile_path.read_text())
        assert profile["reasoning_effort"] == "medium"
        assert "temperature" not in profile


def test_run_portfolio_eval_forces_current_checkout_ahead_of_stale_pythonpath(tmp_path):
    fake_inspect = _write_fake_inspect(tmp_path)
    env = _runner_env(
        tmp_path,
        fake_inspect,
        TASKS="transform_01",
        MODELS="openai/gpt-4o-mini",
        SEEDS="1",
        PYTHONPATH=str(tmp_path / "stale_checkout"),
    )

    proc = subprocess.run(
        ["bash", str(RUNNER_PATH)],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
    )

    assert proc.returncode == 0, proc.stderr
    assert "Runtime source: {}".format(REPO_ROOT.resolve()) in proc.stdout


def test_run_portfolio_eval_rejects_mismatched_runtime_source(tmp_path):
    fake_inspect = _write_fake_inspect(tmp_path)
    fake_python = _write_python_with_stale_source_probe(tmp_path)
    env = _runner_env(
        tmp_path,
        fake_inspect,
        TASKS="transform_01",
        MODELS="openai/gpt-4o-mini",
        SEEDS="1",
        PYTHON_BIN=str(fake_python),
    )

    proc = subprocess.run(
        ["bash", str(RUNNER_PATH)],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
    )

    assert proc.returncode == 2
    assert "Runtime source mismatch" in proc.stderr
    assert not Path(env["FAKE_INSPECT_LOG"]).exists()


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


def test_run_portfolio_eval_help_and_positional_argument_rejection(tmp_path):
    help_proc = subprocess.run(
        ["bash", str(RUNNER_PATH), "--help"],
        cwd=str(REPO_ROOT),
        text=True,
        capture_output=True,
    )
    bad_proc = subprocess.run(
        ["bash", str(RUNNER_PATH), "unexpected"],
        cwd=str(REPO_ROOT),
        text=True,
        capture_output=True,
    )

    assert help_proc.returncode == 0
    assert "build/eval_runs/<RUN_ID>" in help_proc.stdout
    assert bad_proc.returncode == 2
    assert "Unexpected positional arguments: unexpected" in bad_proc.stderr


def test_run_portfolio_eval_defaults_to_new_build_bundle(tmp_path):
    fake_inspect = _write_fake_inspect(tmp_path)
    env = _runner_env(
        tmp_path,
        fake_inspect,
        TASKS="transform_01",
        MODELS="openai/gpt-4o-mini",
        RUN_ID="runner-default-test",
    )
    env.pop("LOG_DIR")

    proc = subprocess.run(
        ["bash", str(RUNNER_PATH)],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
    )

    expected_log_dir = REPO_ROOT / "build" / "eval_runs" / "runner-default-test"
    assert proc.returncode == 0
    assert "Logs:   {}".format(expected_log_dir) in proc.stdout
    assert "--log-dir {}".format(expected_log_dir) in Path(env["FAKE_INSPECT_LOG"]).read_text()


def test_run_portfolio_eval_requires_opt_in_for_frozen_log_dir(tmp_path):
    fake_inspect = _write_fake_inspect(tmp_path)
    env = _runner_env(
        tmp_path,
        fake_inspect,
        TASKS="transform_01",
        MODELS="openai/gpt-4o-mini",
        LOG_DIR=str(REPO_ROOT / "results" / "logs"),
        GENERATE_CONFIG_ARGS="--temperature 0 --max-tokens 4096",
    )

    rejected = subprocess.run(
        ["bash", str(RUNNER_PATH)],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
    )
    env["ALLOW_FROZEN_LOG_DIR"] = "1"
    allowed = subprocess.run(
        ["bash", str(RUNNER_PATH)],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
    )

    assert rejected.returncode == 2
    assert "Refusing to write into frozen log path" in rejected.stderr
    assert allowed.returncode == 0


def test_frozen_log_guard_rejects_traversal_and_symlink_aliases(tmp_path):
    fake_inspect = _write_fake_inspect(tmp_path)
    traversal_env = _runner_env(
        tmp_path,
        fake_inspect,
        LOG_DIR=str(REPO_ROOT / "build" / "eval_runs" / ".." / ".." / "results" / "logs"),
    )
    results_link = tmp_path / "results-link"
    results_link.symlink_to(REPO_ROOT / "results", target_is_directory=True)
    symlink_env = _runner_env(
        tmp_path,
        fake_inspect,
        LOG_DIR=str(results_link / "logs"),
    )

    for env in (traversal_env, symlink_env):
        result = subprocess.run(
            ["bash", str(RUNNER_PATH)],
            cwd=str(REPO_ROOT),
            env=env,
            text=True,
            capture_output=True,
        )
        assert result.returncode == 2
        assert "Refusing to write into frozen log path" in result.stderr


def test_run_portfolio_eval_rejects_invalid_seed_ranges_before_inspect(tmp_path):
    fake_inspect = _write_fake_inspect(tmp_path)
    zero_seed_env = _runner_env(tmp_path, fake_inspect, SEEDS="0")
    negative_start_env = _runner_env(tmp_path, fake_inspect, SEED_START="-1")

    zero_seed = subprocess.run(
        ["bash", str(RUNNER_PATH)],
        cwd=str(REPO_ROOT),
        env=zero_seed_env,
        text=True,
        capture_output=True,
    )
    negative_start = subprocess.run(
        ["bash", str(RUNNER_PATH)],
        cwd=str(REPO_ROOT),
        env=negative_start_env,
        text=True,
        capture_output=True,
    )

    assert zero_seed.returncode == 2
    assert "SEEDS must be a positive integer: 0" in zero_seed.stderr
    assert negative_start.returncode == 2
    assert "SEED_START must be a non-negative integer: -1" in negative_start.stderr
    assert not Path(zero_seed_env["FAKE_INSPECT_LOG"]).exists()


def test_run_portfolio_eval_rejects_empty_or_missing_generation_overrides(tmp_path):
    fake_inspect = _write_fake_inspect(tmp_path)
    empty_args_env = _runner_env(
        tmp_path,
        fake_inspect,
        GENERATE_CONFIG_ARGS="",
    )
    missing_config_env = _runner_env(
        tmp_path,
        fake_inspect,
        GENERATE_CONFIG_FILE=str(tmp_path / "missing.json"),
    )

    empty_args = subprocess.run(
        ["bash", str(RUNNER_PATH)],
        cwd=str(REPO_ROOT),
        env=empty_args_env,
        text=True,
        capture_output=True,
    )
    missing_config = subprocess.run(
        ["bash", str(RUNNER_PATH)],
        cwd=str(REPO_ROOT),
        env=missing_config_env,
        text=True,
        capture_output=True,
    )

    assert empty_args.returncode == 2
    assert "GENERATE_CONFIG_ARGS cannot be empty" in empty_args.stderr
    assert missing_config.returncode == 2
    assert "GENERATE_CONFIG_FILE is not readable" in missing_config.stderr


def test_run_portfolio_eval_rejects_unregistered_model_even_with_profile_override(tmp_path):
    fake_inspect = _write_fake_inspect(tmp_path)
    env = _runner_env(
        tmp_path,
        fake_inspect,
        TASKS="transform_01",
        MODELS="openai/not-registered",
        GENERATE_CONFIG_ARGS="--max-tokens 4096",
    )

    proc = subprocess.run(
        ["bash", str(RUNNER_PATH)],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
    )

    assert proc.returncode == 2
    assert "Unknown model 'openai/not-registered'" in proc.stderr
    assert not Path(env["FAKE_INSPECT_LOG"]).exists()


def test_hpc_runner_records_registered_model_provenance_and_profile(tmp_path):
    fake_inspect = _write_fake_inspect(tmp_path)
    fake_python = _write_python_with_fake_cell_validator(tmp_path)
    bundle_dir = tmp_path / "hpc_bundle"
    validator_log = tmp_path / "validator_args.log"
    env = os.environ.copy()
    env.update(
        {
            "HOME": str(tmp_path / "home"),
            "INSPECT_BIN": str(fake_inspect),
            "FAKE_INSPECT_LOG": str(tmp_path / "inspect_calls.log"),
            "PYTHON_BIN": str(fake_python),
            "VALIDATOR_LOG": str(validator_log),
            "TASKS": "transform_01",
            "SEEDS_TOTAL": "1",
            "SLURM_ARRAY_TASK_ID": "0",
            "RUN_ID": "hpc-registry-test",
            "BUNDLE_DIR": str(bundle_dir),
            "LOG_DIR": str(bundle_dir / "logs"),
        }
    )
    env.pop("MODELS", None)

    proc = subprocess.run(
        ["bash", str(HPC_RUNNER_PATH)],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
    )

    assert proc.returncode == 0, proc.stderr
    manifest = json.loads((bundle_dir / "manifests" / "cell_0.json").read_text())
    assert manifest["model_source"] == "matrix:current_balanced"
    assert manifest["model_matrix"] == "current_balanced"
    assert manifest["model_key"] == "gpt_5_6_sol"
    assert manifest["requested_model"] == "openai/gpt-5.6-sol"
    assert manifest["provider"] == "openai"
    assert manifest["expected_resolved_model"] == "gpt-5.6-sol"
    assert manifest["generation_profile"] == {
        "max_tokens": 16384,
        "reasoning_effort": "medium",
    }
    assert manifest["inspect_eval_args"] == ""
    assert manifest["schema_version"] == "1.2.0"
    assert manifest["runtime_source_root"] == str(REPO_ROOT.resolve())
    validator_args = [
        item.decode() for item in validator_log.read_bytes().split(b"\0") if item
    ]
    config_index = validator_args.index("--expected-generation-config") + 1
    assert json.loads(validator_args[config_index]) == manifest["generation_profile"]


def test_hpc_runner_rejects_generation_profile_overrides(tmp_path):
    fake_inspect = _write_fake_inspect(tmp_path)
    bundle_dir = tmp_path / "hpc_bundle"
    env = os.environ.copy()
    env.update(
        {
            "HOME": str(tmp_path / "home"),
            "INSPECT_BIN": str(fake_inspect),
            "FAKE_INSPECT_LOG": str(tmp_path / "inspect_calls.log"),
            "PYTHON_BIN": sys.executable,
            "TASKS": "transform_01",
            "SEEDS_TOTAL": "1",
            "BUNDLE_DIR": str(bundle_dir),
            "GENERATE_CONFIG_ARGS": "--max-tokens 4096",
        }
    )

    proc = subprocess.run(
        ["bash", str(HPC_RUNNER_PATH)],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
    )

    assert proc.returncode == 2
    assert "HPC release cells require registry generation profiles" in proc.stderr
    assert not (bundle_dir / "manifests").exists()
    assert not Path(env["FAKE_INSPECT_LOG"]).exists()


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
    assert "MODELS=openai/gpt-5.6-luna anthropic/claude-sonnet-5" in log_lines[0]
    assert "--log-dir {}".format(env["LOG_DIR"]) in log_lines[1]
    assert "--out {}".format(env["RESULTS_OUT"]) in log_lines[1]
    assert "--out-dir {}".format(env["PLOTS_OUT_DIR"]) in log_lines[2]
    assert "--task-preset discovery" in log_lines[2]
    assert "--models openai/gpt-5.6-luna anthropic/claude-sonnet-5" in log_lines[2]


def test_run_discovery_bundle_defaults_to_new_build_bundle(tmp_path):
    fake_runner = _write_fake_runner(tmp_path)
    fake_aggregate = _write_fake_python_script(tmp_path, "fake_aggregate.py", "aggregate")
    fake_plot = _write_fake_python_script(tmp_path, "fake_plot.py", "plot")
    call_log = tmp_path / "calls.log"
    bundle_dir = tmp_path / "new_bundle"
    env = os.environ.copy()
    env.update(
        {
            "CALL_LOG": str(call_log),
            "RUNNER_SCRIPT": str(fake_runner),
            "AGGREGATE_SCRIPT": str(fake_aggregate),
            "PLOT_SCRIPT": str(fake_plot),
            "PYTHON_BIN": sys.executable,
            "BUNDLE_DIR": str(bundle_dir),
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
    log_lines = call_log.read_text().strip().splitlines()
    assert "LOG_DIR={}".format(bundle_dir / "logs") in log_lines[0]
    assert "--out {}".format(bundle_dir / "results.md") in log_lines[1]
    assert "--out-dir {}".format(bundle_dir / "plots") in log_lines[2]


def test_run_discovery_bundle_protects_tracked_outputs(tmp_path):
    env = os.environ.copy()
    env.update(
        {
            "PYTHON_BIN": sys.executable,
            "LOG_DIR": str(REPO_ROOT / "results" / "discovery_logs"),
            "RESULTS_OUT": str(tmp_path / "results.md"),
            "PLOTS_OUT_DIR": str(tmp_path / "plots"),
        }
    )

    proc = subprocess.run(
        ["bash", str(DISCOVERY_BUNDLE_PATH)],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
    )

    assert proc.returncode == 2
    assert "Refusing to overwrite tracked discovery artifacts" in proc.stderr
