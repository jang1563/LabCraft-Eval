from types import SimpleNamespace

from scripts.validate_eval_cell import expected_sample_id, latest_row, score_value


def test_expected_sample_id_uses_baseline_name_for_seed_zero():
    assert expected_sample_id("growth_01", 0) == "growth_01_seeded"


def test_expected_sample_id_zero_pads_single_digit_nonzero_seeds():
    assert expected_sample_id("growth_01", 3) == "growth_01_seeded_seed_03"
    assert expected_sample_id("growth_01", 12) == "growth_01_seeded_seed_12"


def test_score_value_returns_first_dict_score_value():
    sample = SimpleNamespace(
        scores={
            "empty": SimpleNamespace(value="not-a-dict"),
            "trajectory": SimpleNamespace(value={"overall": 0.75}),
        }
    )

    assert score_value(sample) == {"overall": 0.75}


def test_latest_row_prefers_created_then_path_name():
    rows = [
        {"created": "2026-05-17T01:00:00Z", "eval_path": "b.eval"},
        {"created": "2026-05-17T02:00:00Z", "eval_path": "a.eval"},
    ]

    assert latest_row(rows)["eval_path"] == "a.eval"
