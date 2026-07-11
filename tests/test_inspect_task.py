from types import SimpleNamespace

import pytest

from src.inspect_task import _expand_seeds
import src.inspect_task as inspect_task
from src.solvers import _configure_lab_sample_state
from src.tasks.target_prioritize_01 import build_target_prioritize_01_prompt


def test_expand_seeds_defaults_to_zero_start():
    base_sample = {
        "id": "purify_01_seeded",
        "input": "prompt",
        "target": "target",
        "metadata": {"task_id": "purify_01"},
    }

    expanded = _expand_seeds(base_sample, seeds=3)

    assert [sample["id"] for sample in expanded] == [
        "purify_01_seeded_seed_00",
        "purify_01_seeded_seed_01",
        "purify_01_seeded_seed_02",
    ]
    assert [sample["metadata"]["seed_index"] for sample in expanded] == [0, 1, 2]


def test_expand_seeds_supports_nonzero_seed_start():
    base_sample = {
        "id": "purify_01_seeded",
        "input": "prompt",
        "target": "target",
        "metadata": {"task_id": "purify_01"},
    }

    expanded = _expand_seeds(base_sample, seeds=2, seed_start=3)

    assert [sample["id"] for sample in expanded] == [
        "purify_01_seeded_seed_03",
        "purify_01_seeded_seed_04",
    ]
    assert [sample["metadata"]["seed_index"] for sample in expanded] == [3, 4]


def test_expand_single_seed_with_nonzero_seed_start_gets_suffix():
    base_sample = {
        "id": "purify_01_seeded",
        "input": "prompt",
        "target": "target",
        "metadata": {"task_id": "purify_01"},
    }

    expanded = _expand_seeds(base_sample, seeds=1, seed_start=4)

    assert len(expanded) == 1
    assert expanded[0]["id"] == "purify_01_seeded_seed_04"
    assert expanded[0]["metadata"]["seed_index"] == 4


def test_expand_single_seed_zero_matches_first_multi_seed_identity():
    base_sample = {
        "id": "transform_01_seeded",
        "input": "prompt",
        "target": "target",
        "metadata": {"task_id": "transform_01"},
    }

    single = _expand_seeds(base_sample, seeds=1, seed_start=0)[0]
    multi_first = _expand_seeds(base_sample, seeds=3, seed_start=0)[0]

    assert single["id"] == multi_first["id"] == "transform_01_seeded_seed_00"
    assert single["metadata"]["seed_index"] == multi_first["metadata"]["seed_index"] == 0


@pytest.mark.parametrize(
    ("seeds", "seed_start", "message"),
    [
        (0, 0, "seeds must be a positive integer"),
        (-1, 0, "seeds must be a positive integer"),
        (True, 0, "seeds must be a positive integer"),
        (1, -1, "seed_start must be a non-negative integer"),
        (1, True, "seed_start must be a non-negative integer"),
    ],
)
def test_expand_seeds_rejects_invalid_ranges(seeds, seed_start, message):
    with pytest.raises(ValueError, match=message):
        _expand_seeds(
            {"id": "sample", "input": "prompt", "target": "target", "metadata": {}},
            seeds=seeds,
            seed_start=seed_start,
        )


def test_configure_lab_sample_uses_explicit_seed_metadata(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "src.solvers.set_active_sample",
        lambda sample_id, seed=None: calls.append((sample_id, seed)),
    )

    _configure_lab_sample_state(
        SimpleNamespace(sample_id="transform_01_seeded_seed_04", metadata={"seed_index": 4})
    )

    assert calls == [("transform_01_seeded_seed_04", 4)]


def test_discovery_tasks_are_registered():
    assert "perturb_followup_01" in inspect_task.__all__
    assert "target_prioritize_01" in inspect_task.__all__
    assert "target_validate_01" in inspect_task.__all__


def test_task_inventory_constants_are_consistent():
    assert inspect_task.SNAPSHOT_TASKS == (
        "transform_01",
        "growth_01",
        "pcr_01",
        "screen_01",
        "clone_01",
    )
    assert inspect_task.DISCOVERY_TASKS == (
        "perturb_followup_01",
        "target_prioritize_01",
        "target_validate_01",
    )
    assert inspect_task.ALL_TASKS == inspect_task.CURRENT_TASKS + inspect_task.DISCOVERY_TASKS
    assert inspect_task.TASK_PRESETS["all"] == inspect_task.ALL_TASKS
    assert set(inspect_task.ALL_TASKS).issubset(set(inspect_task.__all__))


def test_growth_task_separates_turn_and_message_limits():
    assert inspect_task.GROWTH_TURN_LIMIT == 40
    assert inspect_task.GROWTH_MESSAGE_LIMIT == 160
    assert inspect_task.GROWTH_MESSAGE_LIMIT > inspect_task.GROWTH_TURN_LIMIT


def test_available_task_ids_returns_named_preset():
    assert inspect_task.available_task_ids("discovery") == inspect_task.DISCOVERY_TASKS


def test_available_task_ids_rejects_unknown_preset():
    with pytest.raises(ValueError, match="Unknown task preset"):
        inspect_task.available_task_ids("unknown")


def test_target_prioritize_prompt_clarifies_immediate_no_go_vs_followup():
    prompt = build_target_prioritize_01_prompt()

    assert "clearest immediate no-go" in prompt
    assert "better handled by follow-up" in prompt
    assert "remaining risk for the top target" in prompt
