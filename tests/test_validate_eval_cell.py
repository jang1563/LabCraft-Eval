import argparse
import json
from types import SimpleNamespace

import pytest

from scripts.validate_eval_cell import (
    expected_sample_id,
    latest_row,
    model_ids_match,
    output_completion,
    parse_expected_generation_config,
    resolved_model,
    sample_id_matches_seed,
    score_value,
    task_requires_nonempty_completion,
    validate_cell,
)


def test_expected_sample_id_uses_explicit_suffix_for_seed_zero():
    assert expected_sample_id("growth_01", 0) == "growth_01_seeded_seed_00"


def test_expected_sample_id_zero_pads_single_digit_nonzero_seeds():
    assert expected_sample_id("growth_01", 3) == "growth_01_seeded_seed_03"
    assert expected_sample_id("growth_01", 12) == "growth_01_seeded_seed_12"


def test_sample_id_matches_only_explicit_seed_ids():
    assert sample_id_matches_seed("growth_01_seeded_seed_00", 0)
    assert sample_id_matches_seed("sp_001_seed_00", 0)
    assert sample_id_matches_seed("sp_001_seed_03", 3)
    assert sample_id_matches_seed("growth_01_seeded_seed_03", 3)
    assert not sample_id_matches_seed("sp_001_seed_03", 4)
    assert not sample_id_matches_seed("growth_01_seeded", 0)
    assert not sample_id_matches_seed("sp_001", 0)
    assert not sample_id_matches_seed("sp_001", 4)


def test_score_value_returns_first_dict_score_value():
    sample = SimpleNamespace(
        scores={
            "empty": SimpleNamespace(value="not-a-dict"),
            "trajectory": SimpleNamespace(value={"overall": 0.75}),
        }
    )

    assert score_value(sample) == {"overall": 0.75}


def test_output_completion_returns_string_completion():
    sample = SimpleNamespace(output=SimpleNamespace(completion="answer"))

    assert output_completion(sample) == "answer"


def test_output_completion_handles_missing_output():
    assert output_completion(SimpleNamespace()) == ""


def test_resolved_model_reads_provider_returned_output_model():
    sample = SimpleNamespace(output=SimpleNamespace(model="gpt-5.6-sol-20260701"))

    assert resolved_model(sample) == "gpt-5.6-sol-20260701"


def test_model_ids_match_accepts_optional_provider_qualification():
    assert model_ids_match("gpt-5.6-sol", "gpt-5.6-sol", "openai")
    assert model_ids_match("openai/gpt-5.6-sol", "gpt-5.6-sol", "openai")
    assert not model_ids_match("gpt-5.6-sol", "gpt-5.6-terra", "openai")


def test_parse_expected_generation_config_accepts_json_and_file(tmp_path):
    expected = {"max_tokens": 8192, "reasoning_effort": "medium"}
    assert parse_expected_generation_config(json.dumps(expected)) == expected

    path = tmp_path / "generate.json"
    path.write_text(json.dumps(expected))
    assert parse_expected_generation_config(str(path)) == expected

    with pytest.raises(argparse.ArgumentTypeError, match="non-empty JSON object"):
        parse_expected_generation_config("{}")


def test_only_safety_case_requires_nonempty_completion():
    assert task_requires_nonempty_completion("safety_case_01")
    assert not task_requires_nonempty_completion("growth_01")


def test_latest_row_prefers_created_then_path_name():
    rows = [
        {"created": "2026-05-17T01:00:00Z", "eval_path": "b.eval"},
        {"created": "2026-05-17T02:00:00Z", "eval_path": "a.eval"},
    ]

    assert latest_row(rows)["eval_path"] == "a.eval"


def test_validate_cell_checks_model_provenance_but_allows_dirty_smoke(
    monkeypatch, tmp_path
):
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    (log_dir / "cell.eval").write_text("fixture")
    sample = SimpleNamespace(
        id="growth_01_seeded_seed_00",
        scores={"trajectory": SimpleNamespace(value={"overall": 0.75})},
        output=SimpleNamespace(model="gpt-5.6-sol-20260701", completion="answer"),
    )
    log = SimpleNamespace(
        status="success",
        error=None,
        eval=SimpleNamespace(
            model="openai/gpt-5.6-sol",
            task="growth_01",
            created="2026-07-11T01:00:00Z",
            model_generate_config={"max_tokens": 8192},
            packages={"inspect_ai": "0.3.245"},
            revision={"commit": "abc123", "dirty": True},
        ),
        samples=[sample],
    )
    monkeypatch.setattr("inspect_ai.log.read_eval_log", lambda _path: log)

    assert (
        validate_cell(
            log_dir,
            "growth_01",
            "openai/gpt-5.6-sol",
            0,
            expected_resolved_model="gpt-5.6-sol-20260701",
            expected_provider="openai",
            expected_generation_config={"max_tokens": 8192},
            expected_inspect_version="0.3.245",
            require_model_provenance=True,
        )
        == 0
    )

    sample.limit = SimpleNamespace(type="message", limit=80)
    assert (
        validate_cell(
            log_dir,
            "growth_01",
            "openai/gpt-5.6-sol",
            0,
            expected_generation_config={"max_tokens": 8192},
        )
        == 1
    )
    del sample.limit

    assert (
        validate_cell(
            log_dir,
            "growth_01",
            "openai/gpt-5.6-sol",
            0,
            expected_generation_config={"max_tokens": 4096},
        )
        == 1
    )

    assert (
        validate_cell(
            log_dir,
            "growth_01",
            "openai/gpt-5.6-sol",
            0,
            expected_inspect_version="0.3.999",
        )
        == 1
    )


def test_validate_cell_rejects_resolved_model_mismatch(monkeypatch, tmp_path):
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    (log_dir / "cell.eval").write_text("fixture")
    sample = SimpleNamespace(
        id="growth_01_seeded_seed_00",
        scores={"trajectory": SimpleNamespace(value={"overall": 0.75})},
        output=SimpleNamespace(model="gpt-5.6-terra", completion="answer"),
    )
    log = SimpleNamespace(
        status="success",
        error=None,
        eval=SimpleNamespace(
            model="openai/gpt-5.6-sol",
            task="growth_01",
            created="2026-07-11T01:00:00Z",
            model_generate_config={"max_tokens": 8192},
            packages={"inspect_ai": "0.3.245"},
            revision={"commit": "abc123", "dirty": False},
        ),
        samples=[sample],
    )
    monkeypatch.setattr("inspect_ai.log.read_eval_log", lambda _path: log)

    assert (
        validate_cell(
            log_dir,
            "growth_01",
            "openai/gpt-5.6-sol",
            0,
            expected_resolved_model="gpt-5.6-sol",
        )
        == 1
    )
