import importlib.util
import json
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_script_module(module_name: str, relative_path: str):
    script_path = REPO_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


human_baseline = _load_script_module(
    "run_human_baseline",
    "scripts/run_human_baseline.py",
)


def test_seeded_sample_id_matches_multi_seed_naming():
    assert human_baseline._seeded_sample_id("transform_01_seeded", 0) == "transform_01_seeded_seed_00"
    assert human_baseline._seeded_sample_id("growth_01_seeded", 4) == "growth_01_seeded_seed_04"


def test_build_task_session_for_growth_verbose_variant():
    session = human_baseline.build_task_session(
        task_id="growth_01",
        seed_index=2,
        growth_prompt_variant="verbose_troubleshoot",
    )

    assert session.task_id == "growth_01"
    assert session.seed_index == 2
    assert session.sample_id == "growth_01_seeded_seed_02"
    assert session.prompt_variant == "verbose_troubleshoot"
    assert "IMPORTANT" in session.prompt
    assert session.ground_truth_path.endswith("task_data/growth_01/ground_truth.json")


def test_default_session_path_includes_operator_and_sanitizes_filename():
    path = human_baseline._default_session_path_for_operator(
        task_id="growth_01",
        seed_index=3,
        operator_id="Expert A / pilot",
    )

    assert path.name == "expert_a_pilot__growth_01_seed_03.json"


def test_growth_variant_session_path_gets_variant_suffix():
    path = human_baseline._default_session_path_for_operator(
        task_id="growth_01",
        seed_index=2,
        operator_id="expert_a",
        prompt_variant="verbose_troubleshoot",
    )

    assert path.name == "expert_a__growth_01__verbose_troubleshoot_seed_02.json"


def test_write_session_stores_repo_relative_metadata_paths(tmp_path):
    session = human_baseline.build_task_session(
        task_id="transform_01",
        seed_index=0,
        operator_id="expert_a",
    )
    session_path = tmp_path / "session.json"

    human_baseline._write_session(session_path, session, transcript=[])
    payload = json.loads(session_path.read_text())

    assert payload["ground_truth_path"] == "task_data/transform_01/ground_truth.json"
    assert payload["rubric_path"] == "task_data/transform_01/rubric.json"


def test_saved_session_status_detects_pending_in_progress_and_completed(tmp_path):
    session_path = tmp_path / "expert_a__transform_01_seed_00.json"

    assert human_baseline.saved_session_status(session_path) == "pending"

    session_path.write_text(json.dumps({"status": "in_progress", "transcript": []}))
    assert human_baseline.saved_session_status(session_path) == "in_progress"

    session_path.write_text(json.dumps({"status": "completed", "transcript": []}))
    assert human_baseline.saved_session_status(session_path) == "completed"


def test_validate_saved_session_payload_rejects_mismatched_operator():
    session = human_baseline.build_task_session(
        task_id="transform_01",
        seed_index=0,
        operator_id="expert_a",
    )

    with pytest.raises(ValueError):
        human_baseline._validate_saved_session_payload(
            {
                "task_id": "transform_01",
                "seed_index": 0,
                "sample_id": "transform_01_seeded_seed_00",
                "operator_id": "expert_b",
            },
            session,
        )


def test_transform_final_answer_feedback_flags_missing_consistent_and_lines():
    session = human_baseline.build_task_session(
        task_id="transform_01",
        seed_index=0,
    )

    feedback = human_baseline._summarize_final_answer_feedback(
        session=session,
        final_answer="10 pg: 1e9 CFU/ug\n100 pg: 1e9 CFU/ug",
        transcript=[],
        score={"task_success": 0.0},
    )

    assert any("10,000 pg" in note for note in feedback)
    assert any("consistent" in note.lower() for note in feedback)
    assert any("task success is currently 0.0" in note.lower() for note in feedback)


def test_growth_final_answer_feedback_flags_missing_condition_and_troubleshooting_note():
    session = human_baseline.build_task_session(
        task_id="growth_01",
        seed_index=2,
    )
    transcript = [
        {
            "type": "tool_call",
            "tool_name": "fit_growth_curve",
            "arguments": {"growth_id": "growth_001"},
            "content": "{\"status\": \"insufficient_points\"}",
        }
    ]

    feedback = human_baseline._summarize_final_answer_feedback(
        session=session,
        final_answer="LB: 30 minutes\nM9 + glucose: 45 minutes\nRanking: LB > M9 + glucose > LB + chloramphenicol",
        transcript=transcript,
        score={"task_success": 0.0},
    )

    assert any("LB + chloramphenicol" in note for note in feedback)
    assert any("insufficient points" in note.lower() for note in feedback)


def test_missing_growth_labels_requires_standalone_lb_line():
    missing = human_baseline._missing_growth_labels(
        "LB + chloramphenicol (1.8 uM): 80 minutes\nM9 + glucose: 45 minutes"
    )

    assert "LB" in missing


def test_parse_tool_command_requires_json_object():
    tool_name, arguments = human_baseline._parse_tool_command(
        'prepare_media {"medium": "LB agar", "plate_count": 2}'
    )

    assert tool_name == "prepare_media"
    assert arguments == {"medium": "LB agar", "plate_count": 2}


def test_help_uses_placeholders_instead_of_scored_protocol_values(capsys):
    human_baseline._print_help()
    help_text = capsys.readouterr().out.casefold()

    assert "<choose medium>" in help_text
    for leaked_value in ('"lb agar"', '"soc"', ": 100", ": 30", ": 60"):
        assert leaked_value not in help_text


def test_human_baseline_binds_same_explicit_seed_as_agent_eval(monkeypatch, tmp_path):
    session = human_baseline.build_task_session(
        task_id="transform_01",
        seed_index=4,
        operator_id="expert_a",
    )
    seed_calls = []

    monkeypatch.setattr(
        human_baseline,
        "set_active_sample",
        lambda sample_id, seed=None: seed_calls.append((sample_id, seed)),
    )
    monkeypatch.setattr(human_baseline, "cleanup_sample", lambda sample_id: None)

    def raise_eof(_prompt):
        raise EOFError

    monkeypatch.setattr("builtins.input", raise_eof)

    exit_code = human_baseline.run_human_baseline(session, tmp_path / "session.json")

    assert exit_code == 0
    assert seed_calls == [("transform_01_seeded_seed_04", 4)]
