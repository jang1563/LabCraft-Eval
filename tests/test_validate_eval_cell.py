from types import SimpleNamespace

from scripts.validate_eval_cell import (
    expected_sample_id,
    latest_row,
    output_completion,
    sample_id_matches_seed,
    score_value,
    task_requires_nonempty_completion,
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


def test_only_safety_case_requires_nonempty_completion():
    assert task_requires_nonempty_completion("safety_case_01")
    assert not task_requires_nonempty_completion("growth_01")


def test_latest_row_prefers_created_then_path_name():
    rows = [
        {"created": "2026-05-17T01:00:00Z", "eval_path": "b.eval"},
        {"created": "2026-05-17T02:00:00Z", "eval_path": "a.eval"},
    ]

    assert latest_row(rows)["eval_path"] == "a.eval"
