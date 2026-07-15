from __future__ import annotations

import copy
from pathlib import Path

import pytest

from src.environment.operations import run_gel, run_pcr
from src.environment.state import create_lab_state
from src.task_scorers.pcr_causal_reasoning_01 import (
    SCORER_VERSION,
    score_pcr_causal_reasoning_trajectory,
)


GROUND_TRUTH = (
    Path(__file__).resolve().parents[1]
    / "task_data"
    / "pcr_causal_reasoning_01"
    / "ground_truth.json"
)

PRIOR = {
    "case_a": {
        "polymerase_name": "Taq DNA polymerase",
        "additive": "DMSO",
        "extension_seconds": 50,
        "cycle_count": 32,
    },
    "case_b": {
        "polymerase_name": "Q5 High-Fidelity DNA polymerase",
        "additive": "DMSO",
        "extension_seconds": 50,
        "cycle_count": 45,
    },
}


def _events(*conditions: dict) -> list[dict]:
    state = create_lab_state("p2b-scorer-fixture", seed=0)
    transcript = []
    for index, condition in enumerate(conditions, start=1):
        reaction = run_pcr(state=state, **condition)
        transcript.append(
            {
                "type": "tool_call",
                "tool_name": "run_pcr",
                "arguments": dict(condition),
                "content": reaction,
                "call_id": "pcr-call-{}".format(index),
            }
        )
        gel_arguments = {
            "reaction_id": reaction["reaction_id"],
            "agarose_percent": 1.0,
            "ladder_name": "1 kb DNA Ladder",
        }
        gel = run_gel(state=state, **gel_arguments)
        transcript.append(
            {
                "type": "tool_call",
                "tool_name": "run_gel",
                "arguments": gel_arguments,
                "content": gel,
                "call_id": "gel-call-{}".format(index),
            }
        )
    return transcript


def _report(
    case_id: str,
    corrective_parameter: str,
    corrective_value: str | int,
    counterfactual_parameter: str,
    counterfactual_value: str | int,
    *,
    diagnosis: str | None = None,
    causal_parameter: str | None = None,
    prediction: str = "multiple_bands_or_smear",
    verification: str = "single_clean_target_band",
) -> str:
    defaults = {
        "case_a": ("low_fidelity_polymerase", "polymerase_name"),
        "case_b": ("overcycled_pcr", "cycle_count"),
    }
    expected_diagnosis, expected_parameter = defaults[case_id]
    return "\n".join(
        [
            "Case: {}".format(case_id),
            "Observed phenotype: multiple_bands_or_smear",
            "Primary diagnosis: {}".format(diagnosis or expected_diagnosis),
            "Causal parameter: {}".format(causal_parameter or expected_parameter),
            "Corrective setting: {}={}".format(
                corrective_parameter, corrective_value
            ),
            "Counterfactual setting: {}={}".format(
                counterfactual_parameter, counterfactual_value
            ),
            "Counterfactual prediction: {}".format(prediction),
            "Verification: {}".format(verification),
        ]
    )


def _score(case_id: str, answer: str, transcript: list[dict]) -> dict:
    return score_pcr_causal_reasoning_trajectory(
        final_answer=answer,
        transcript=transcript,
        ground_truth_path=str(GROUND_TRUTH),
        case_id=case_id,
    )


@pytest.mark.parametrize(
    ("case_id", "condition", "answer"),
    [
        (
            "case_a",
            {
                "polymerase_name": "Q5 High-Fidelity DNA polymerase",
                "additive": "DMSO",
                "extension_seconds": 50,
                "cycle_count": 32,
            },
            _report("case_a", "polymerase_name", "Q5", "cycle_count", 30),
        ),
        (
            "case_a",
            {
                "polymerase_name": "Phusion High-Fidelity DNA polymerase",
                "additive": "DMSO",
                "extension_seconds": 50,
                "cycle_count": 32,
            },
            _report(
                "case_a",
                "polymerase_name",
                "Phusion",
                "extension_seconds",
                60,
            ),
        ),
        (
            "case_b",
            {
                "polymerase_name": "Q5 High-Fidelity DNA polymerase",
                "additive": "DMSO",
                "extension_seconds": 50,
                "cycle_count": 30,
            },
            _report("case_b", "cycle_count", 30, "polymerase_name", "Phusion"),
        ),
        (
            "case_b",
            {
                "polymerase_name": "Q5 High-Fidelity DNA polymerase",
                "additive": "DMSO",
                "extension_seconds": 50,
                "cycle_count": 35,
            },
            _report("case_b", "cycle_count", 35, "additive", "Betaine"),
        ),
    ],
)
def test_valid_and_alternative_valid_paths_score_one(case_id, condition, answer):
    values = _score(case_id, answer, _events(condition))

    assert values["scorer_version"] == SCORER_VERSION == "0.1.0"
    assert values["overall"] == 1.0
    assert values["task_success"] == 1.0
    assert values["decision_quality"] == 1.0
    assert values["troubleshooting"] == 1.0
    assert values["efficiency"] == 1.0
    assert set(values["decision_scores"].values()) == {1.0}


@pytest.mark.parametrize("fixture_kind", ["request_only", "orphan_output", "partial"])
def test_incomplete_or_unlinked_evidence_fails_closed(fixture_kind):
    condition = {
        "polymerase_name": "Q5 High-Fidelity DNA polymerase",
        "additive": "DMSO",
        "extension_seconds": 50,
        "cycle_count": 32,
    }
    complete = _events(condition)
    if fixture_kind == "request_only":
        transcript = [{key: value for key, value in call.items() if key != "content"} for call in complete]
    elif fixture_kind == "orphan_output":
        transcript = [
            {
                "role": "tool",
                "name": call["tool_name"],
                "tool_call_id": call["call_id"],
                "content": call["content"],
            }
            for call in complete
        ]
    else:
        transcript = complete[:1]

    values = _score(
        "case_a",
        _report("case_a", "polymerase_name", "Q5", "cycle_count", 30),
        transcript,
    )

    assert values["overall"] == 0.0
    assert values["evidence_gate_passed"] is False
    assert set(values["decision_scores"].values()) == {0.0}


def test_output_fields_cannot_fall_back_to_request_arguments():
    transcript = _events(
        {
            "polymerase_name": "Q5 High-Fidelity DNA polymerase",
            "additive": "DMSO",
            "extension_seconds": 50,
            "cycle_count": 32,
        }
    )
    del transcript[0]["content"]["normalized_additive"]

    values = _score(
        "case_a",
        _report("case_a", "polymerase_name", "Q5", "cycle_count", 30),
        transcript,
    )

    assert values["overall"] == 0.0
    assert values["evidence_gate_passed"] is False


def test_contradictory_request_and_output_is_rejected():
    transcript = _events(
        {
            "polymerase_name": "Q5 High-Fidelity DNA polymerase",
            "additive": "DMSO",
            "extension_seconds": 50,
            "cycle_count": 32,
        }
    )
    transcript[0]["arguments"]["polymerase_name"] = "Taq DNA polymerase"

    values = _score(
        "case_a",
        _report("case_a", "polymerase_name", "Q5", "cycle_count", 30),
        transcript,
    )

    assert values["overall"] == 0.0
    assert values["evidence_gate_passed"] is False


@pytest.mark.parametrize("reversed_tool", ["run_pcr", "run_gel"])
def test_output_before_matching_request_is_rejected(reversed_tool):
    transcript = _events(
        {
            "polymerase_name": "Q5 High-Fidelity DNA polymerase",
            "additive": "DMSO",
            "extension_seconds": 50,
            "cycle_count": 32,
        }
    )
    event = next(item for item in transcript if item["tool_name"] == reversed_tool)
    replacement = [
        {
            "role": "tool",
            "name": event["tool_name"],
            "tool_call_id": event["call_id"],
            "content": event["content"],
        },
        {
            "tool_calls": [
                {
                    "id": event["call_id"],
                    "function": {
                        "name": event["tool_name"],
                        "arguments": event["arguments"],
                    },
                }
            ]
        },
    ]
    index = transcript.index(event)
    transcript[index : index + 1] = replacement

    values = _score(
        "case_a",
        _report("case_a", "polymerase_name", "Q5", "cycle_count", 30),
        transcript,
    )

    assert values["overall"] == 0.0
    assert values["evidence_gate_passed"] is False


def test_repeated_execution_with_duplicate_call_id_is_rejected():
    transcript = _events(
        {
            "polymerase_name": "Q5 High-Fidelity DNA polymerase",
            "additive": "DMSO",
            "extension_seconds": 50,
            "cycle_count": 32,
        }
    )
    transcript.insert(1, copy.deepcopy(transcript[0]))

    values = _score(
        "case_a",
        _report("case_a", "polymerase_name", "Q5", "cycle_count", 30),
        transcript,
    )

    assert values["overall"] == 0.0
    assert values["evidence_gate_passed"] is False


@pytest.mark.parametrize(
    ("event_index", "field", "value"),
    [
        (0, "status", "nonspecific_amplification"),
        (0, "visible_bands_bp", [850, 2000]),
        (0, "smear_present", True),
        (1, "visible_bands_bp", None),
        (1, "smear_present", "false"),
    ],
)
def test_contradictory_or_malformed_linked_outcomes_fail_closed(
    event_index, field, value
):
    transcript = _events(
        {
            "polymerase_name": "Q5 High-Fidelity DNA polymerase",
            "additive": "DMSO",
            "extension_seconds": 50,
            "cycle_count": 32,
        }
    )
    transcript[event_index]["content"][field] = value

    values = _score(
        "case_a",
        _report("case_a", "polymerase_name", "Q5", "cycle_count", 30),
        transcript,
    )

    assert values["overall"] == 0.0
    assert values["evidence_gate_passed"] is False


@pytest.mark.parametrize(
    "malformation", ["empty_reaction_id", "missing_gel_id", "null_targets"]
)
def test_malformed_link_identifiers_and_targets_fail_closed(malformation):
    transcript = _events(
        {
            "polymerase_name": "Q5 High-Fidelity DNA polymerase",
            "additive": "DMSO",
            "extension_seconds": 50,
            "cycle_count": 32,
        }
    )
    if malformation == "empty_reaction_id":
        transcript[0]["content"]["reaction_id"] = ""
        transcript[1]["arguments"]["reaction_id"] = ""
        transcript[1]["content"]["reaction_id"] = ""
    elif malformation == "missing_gel_id":
        transcript[1]["content"]["gel_id"] = None
    else:
        transcript[0]["content"]["target_size_bp"] = None
        transcript[1]["content"]["target_size_bp"] = None

    values = _score(
        "case_a",
        _report("case_a", "polymerase_name", "Q5", "cycle_count", 30),
        transcript,
    )

    assert values["overall"] == 0.0
    assert values["evidence_gate_passed"] is False


def test_expected_case_is_bound_outside_the_model_report():
    condition = {
        "polymerase_name": "Q5 High-Fidelity DNA polymerase",
        "additive": "DMSO",
        "extension_seconds": 50,
        "cycle_count": 32,
    }
    values = _score(
        "case_b",
        _report("case_a", "polymerase_name", "Q5", "cycle_count", 30),
        _events(condition),
    )

    assert values["task_success"] == 0.0
    assert values["decision_scores"]["case_specific_diagnosis"] == 0.0
    assert values["decision_scores"]["causal_parameter_identification"] == 0.0


def test_multi_parameter_recovery_gets_execution_but_not_causal_edit_credit():
    condition = {
        "polymerase_name": "Q5 High-Fidelity DNA polymerase",
        "additive": "Betaine",
        "extension_seconds": 50,
        "cycle_count": 32,
    }
    values = _score(
        "case_a",
        _report("case_a", "polymerase_name", "Q5", "cycle_count", 30),
        _events(condition),
    )

    assert values["task_success"] == 1.0
    assert values["decision_scores"]["one_variable_causal_correction"] == 0.0
    assert values["decision_quality"] == 0.75
    assert values["overall"] == pytest.approx(0.925)


def test_wrong_counterfactual_prediction_loses_troubleshooting_credit():
    condition = {
        "polymerase_name": "Q5 High-Fidelity DNA polymerase",
        "additive": "DMSO",
        "extension_seconds": 50,
        "cycle_count": 32,
    }
    answer = _report(
        "case_a",
        "polymerase_name",
        "Q5",
        "cycle_count",
        30,
        prediction="single_clean_target_band",
    )
    values = _score("case_a", answer, _events(condition))

    assert values["task_success"] == 1.0
    assert values["decision_quality"] == 1.0
    assert values["troubleshooting"] == 0.0
    assert values["overall"] == pytest.approx(0.8)


def test_rerunning_prior_condition_blocks_reasoning_and_efficiency_credit():
    corrected = {
        "polymerase_name": "Q5 High-Fidelity DNA polymerase",
        "additive": "DMSO",
        "extension_seconds": 50,
        "cycle_count": 32,
    }
    values = _score(
        "case_a",
        _report("case_a", "polymerase_name", "Q5", "cycle_count", 30),
        _events(PRIOR["case_a"], corrected),
    )

    assert values["task_success"] == 1.0
    assert values["decision_quality"] == 0.0
    assert values["troubleshooting"] == 0.0
    assert values["efficiency"] == 0.0
    assert values["overall"] == pytest.approx(0.4)


def test_executed_counterfactual_blocks_troubleshooting_and_efficiency():
    counterfactual = dict(PRIOR["case_a"], cycle_count=30)
    corrected = {
        "polymerase_name": "Q5 High-Fidelity DNA polymerase",
        "additive": "DMSO",
        "extension_seconds": 50,
        "cycle_count": 32,
    }
    values = _score(
        "case_a",
        _report("case_a", "polymerase_name", "Q5", "cycle_count", 30),
        _events(counterfactual, corrected),
    )

    assert values["task_success"] == 1.0
    assert values["decision_quality"] == 1.0
    assert values["troubleshooting"] == 0.0
    assert values["efficiency"] == 0.0
    assert values["overall"] == pytest.approx(0.7)


def test_report_must_be_exact_unique_and_free_of_extra_prose():
    condition = {
        "polymerase_name": "Q5 High-Fidelity DNA polymerase",
        "additive": "DMSO",
        "extension_seconds": 50,
        "cycle_count": 32,
    }
    answer = "Summary follows.\n" + _report(
        "case_a", "polymerase_name", "Q5", "cycle_count", 30
    )
    values = _score("case_a", answer, _events(condition))

    assert values["task_success"] == 0.0
    assert values["decision_quality"] == 0.0
    assert values["troubleshooting"] == 0.0
    assert values["efficiency"] == 1.0
    assert values["overall"] == pytest.approx(0.1)


def test_score_is_deterministic_and_does_not_mutate_transcript():
    condition = {
        "polymerase_name": "Q5 High-Fidelity DNA polymerase",
        "additive": "DMSO",
        "extension_seconds": 50,
        "cycle_count": 32,
    }
    transcript = _events(condition)
    original = copy.deepcopy(transcript)
    answer = _report("case_a", "polymerase_name", "Q5", "cycle_count", 30)

    first = _score("case_a", answer, transcript)
    second = _score("case_a", answer, transcript)

    assert first == second
    assert transcript == original
