import json
import subprocess
import sys
from pathlib import Path

import pytest

from src.model_registry import ModelRegistry, RegistryError, load_registry


REPO_ROOT = Path(__file__).resolve().parents[1]
MODEL_MATRIX_SCRIPT = REPO_ROOT / "scripts" / "model_matrix.py"


def test_current_balanced_matrix_uses_canonical_current_model_ids():
    registry = load_registry()

    assert registry.matrix_ids("current_balanced") == [
        "openai/gpt-5.6-sol",
        "openai/gpt-5.6-luna",
        "anthropic/claude-sonnet-5",
        "anthropic/claude-haiku-4-5-20251001",
    ]
    assert registry.resolve("openai/gpt-5.6").key == "gpt_5_6_sol"


def test_current_profiles_omit_temperature_and_pin_reasoning_effort():
    registry = load_registry()

    for model_id in registry.matrix_ids("current_balanced"):
        profile = registry.resolve(model_id).generate
        assert "temperature" not in profile
        assert profile["reasoning_effort"] == "medium"
        assert profile["max_tokens"] >= 8192


def test_pre_46_claude_reasoning_profile_exceeds_inspect_bridged_budget():
    registry = load_registry()
    haiku = registry.resolve("anthropic/claude-haiku-4-5-20251001")

    # Inspect 0.3.245 bridges medium effort to a 10,000-token manual thinking
    # budget for pre-4.6 Claude models; Anthropic requires budget < max_tokens.
    assert haiku.generate["reasoning_effort"] == "medium"
    assert haiku.generate["max_tokens"] > 10_000


def test_gpt56_entries_expose_official_structural_model_info_without_cost():
    registry = load_registry()

    for model_id in (
        "openai/gpt-5.6-sol",
        "openai/gpt-5.6-luna",
        "openai/gpt-5.6-terra",
    ):
        info = registry.resolve(model_id).inspect_model_info
        assert info["organization"] == "OpenAI"
        assert info["knowledge_cutoff_date"] == "2026-02-16"
        assert info["context_length"] == 1_050_000
        assert info["output_tokens"] == 128_000
        assert info["reasoning"] is True
        assert info["reasoning_effort_default"] == "medium"
        assert "cost" not in info

    assert registry.resolve("openai/gpt-5.6").inspect_model_info["model"] == "GPT-5.6 Sol"


def test_inspect_model_info_validation_rejects_cost_and_impossible_limits():
    with pytest.raises(RegistryError, match="unsupported inspect_model_info fields: cost"):
        ModelRegistry._validate_inspect_model_info("example", {"cost": {"input": 1.0}})
    with pytest.raises(RegistryError, match="output_tokens cannot exceed context_length"):
        ModelRegistry._validate_inspect_model_info(
            "example",
            {"context_length": 1_000, "output_tokens": 2_000},
        )


def test_legacy_matrix_preserves_requested_aliases_and_legacy_profile():
    registry = load_registry()

    assert registry.matrix_ids("legacy_2026q2") == [
        "openai/gpt-4o-mini",
        "openai/gpt-4o",
        "anthropic/claude-haiku-4-5",
        "anthropic/claude-sonnet-4-5",
    ]
    assert registry.resolve("openai/gpt-4o-mini").generate == {
        "max_tokens": 4096,
        "temperature": 0.0,
    }


def test_registry_rejects_unknown_model():
    registry = load_registry()

    with pytest.raises(RegistryError, match="Unknown model"):
        registry.resolve("openai/not-registered")


def test_generate_config_cli_writes_machine_readable_profile(tmp_path):
    output = tmp_path / "sol.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(MODEL_MATRIX_SCRIPT),
            "generate-config",
            "gpt_5_6_sol",
            "--out",
            str(output),
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
    )

    assert proc.returncode == 0, proc.stderr
    assert json.loads(output.read_text()) == {
        "max_tokens": 16384,
        "reasoning_effort": "medium",
    }


def test_model_info_cli_prints_machine_readable_metadata():
    proc = subprocess.run(
        [
            sys.executable,
            str(MODEL_MATRIX_SCRIPT),
            "model-info",
            "openai/gpt-5.6-terra",
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
    )

    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["model"] == "GPT-5.6 Terra"
    assert payload["context_length"] == 1_050_000
    assert "cost" not in payload


def test_direct_cli_invocation_works_outside_repository(tmp_path):
    proc = subprocess.run(
        [sys.executable, str(MODEL_MATRIX_SCRIPT), "validate"],
        cwd=tmp_path,
        text=True,
        capture_output=True,
    )

    assert proc.returncode == 0, proc.stderr
    assert "default=current_balanced" in proc.stdout
