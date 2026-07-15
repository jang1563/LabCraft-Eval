"""Trajectory-scorer tests for Transform-01."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from src.environment.miniprep_contract import (
    MINIPREP_FAILURE_OVERLYSIS,
    MINIPREP_FAILURE_WRONG_BUFFER,
    MINIPREP_FAILURE_WRONG_METHOD,
    MINIPREP_SOURCE_CULTURE_ID,
)
from src.environment.operations import (
    count_colonies,
    gibson_assembly,
    initialize_miniprep_source_culture,
    list_gibson_substrates,
    plate,
    perform_miniprep,
    prepare_media,
    transform_gibson,
)
from src.environment.state import create_lab_state
from src.trajectory_scorer import (
    score_clone_task_success,
    score_clone_trajectory,
    score_express_trajectory,
    score_followup_task_success,
    score_followup_trajectory,
    score_gibson_task_success,
    score_gibson_trajectory,
    score_golden_gate_task_success,
    score_golden_gate_trajectory,
    score_growth_task_success,
    score_growth_trajectory,
    score_miniprep_trajectory,
    score_pcr_task_success,
    score_pcr_trajectory,
    score_perturb_followup_task_success,
    score_perturb_followup_trajectory,
    score_purify_trajectory,
    score_screen_task_success,
    score_screen_trajectory,
    score_task_success,
    score_target_prioritize_task_success,
    score_target_prioritize_trajectory,
    score_target_validate_task_success,
    score_target_validate_trajectory,
    score_transform_trajectory,
)


TRANSFORM_GROUND_TRUTH_PATH = Path(__file__).resolve().parents[1] / "task_data" / "transform_01" / "ground_truth.json"
GROWTH_GROUND_TRUTH_PATH = Path(__file__).resolve().parents[1] / "task_data" / "growth_01" / "ground_truth.json"
FOLLOWUP_GROUND_TRUTH_PATH = Path(__file__).resolve().parents[1] / "task_data" / "followup_01" / "ground_truth.json"
PCR_GROUND_TRUTH_PATH = Path(__file__).resolve().parents[1] / "task_data" / "pcr_01" / "ground_truth.json"
SCREEN_GROUND_TRUTH_PATH = Path(__file__).resolve().parents[1] / "task_data" / "screen_01" / "ground_truth.json"
CLONE_GROUND_TRUTH_PATH = Path(__file__).resolve().parents[1] / "task_data" / "clone_01" / "ground_truth.json"
GOLDEN_GATE_GROUND_TRUTH_PATH = (
    Path(__file__).resolve().parents[1] / "task_data" / "golden_gate_01" / "ground_truth.json"
)
GIBSON_GROUND_TRUTH_PATH = (
    Path(__file__).resolve().parents[1] / "task_data" / "gibson_01" / "ground_truth.json"
)
MINIPREP_GROUND_TRUTH_PATH = (
    Path(__file__).resolve().parents[1] / "task_data" / "miniprep_01" / "ground_truth.json"
)
EXPRESS_GROUND_TRUTH_PATH = (
    Path(__file__).resolve().parents[1] / "task_data" / "express_01" / "ground_truth.json"
)
PURIFY_GROUND_TRUTH_PATH = (
    Path(__file__).resolve().parents[1] / "task_data" / "purify_01" / "ground_truth.json"
)
PERTURB_FOLLOWUP_GROUND_TRUTH_PATH = (
    Path(__file__).resolve().parents[1] / "task_data" / "perturb_followup_01" / "ground_truth.json"
)
TARGET_PRIORITIZE_GROUND_TRUTH_PATH = (
    Path(__file__).resolve().parents[1] / "task_data" / "target_prioritize_01" / "ground_truth.json"
)
TARGET_VALIDATE_GROUND_TRUTH_PATH = (
    Path(__file__).resolve().parents[1] / "task_data" / "target_validate_01" / "ground_truth.json"
)
TARGET_MASSES = [10, 100, 1000, 10000]


def test_empty_transcript_has_zero_floor_across_tasks():
    scorer_specs = [
        (score_transform_trajectory, TRANSFORM_GROUND_TRUTH_PATH),
        (score_growth_trajectory, GROWTH_GROUND_TRUTH_PATH),
        (score_followup_trajectory, FOLLOWUP_GROUND_TRUTH_PATH),
        (score_pcr_trajectory, PCR_GROUND_TRUTH_PATH),
        (score_screen_trajectory, SCREEN_GROUND_TRUTH_PATH),
        (score_clone_trajectory, CLONE_GROUND_TRUTH_PATH),
        (score_golden_gate_trajectory, GOLDEN_GATE_GROUND_TRUTH_PATH),
        (score_gibson_trajectory, GIBSON_GROUND_TRUTH_PATH),
        (score_miniprep_trajectory, MINIPREP_GROUND_TRUTH_PATH),
        (score_express_trajectory, EXPRESS_GROUND_TRUTH_PATH),
        (score_purify_trajectory, PURIFY_GROUND_TRUTH_PATH),
        (score_perturb_followup_trajectory, PERTURB_FOLLOWUP_GROUND_TRUTH_PATH),
        (score_target_prioritize_trajectory, TARGET_PRIORITIZE_GROUND_TRUTH_PATH),
        (score_target_validate_trajectory, TARGET_VALIDATE_GROUND_TRUTH_PATH),
    ]

    for scorer, ground_truth_path in scorer_specs:
        scores = scorer(
            final_answer="",
            transcript=[],
            ground_truth_path=str(ground_truth_path),
        )

        assert scores["overall"] == 0.0
        assert scores["efficiency"] == 0.0


def test_irrelevant_single_tool_call_gets_no_efficiency_or_troubleshooting_credit():
    scores = score_transform_trajectory(
        final_answer="",
        transcript=[
            {
                "type": "tool_call",
                "tool_name": "lookup_reagent",
                "arguments": {"reagent_name": "SOC"},
                "content": '{"status": "found"}',
            }
        ],
        ground_truth_path=str(TRANSFORM_GROUND_TRUTH_PATH),
    )

    assert scores["decision_quality"] == 0.0
    assert scores["task_success"] == 0.0
    assert scores["troubleshooting"] == 0.0
    assert scores["efficiency"] == 0.0
    assert scores["overall"] == 0.0


def _good_transcript():
    transcript = [
        {
            "type": "tool_call",
            "tool_name": "prepare_media",
            "arguments": {
                "medium": "LB agar",
                "antibiotic": "ampicillin",
                "antibiotic_concentration_ug_ml": 100,
                "plate_count": 4,
            },
        }
    ]
    for idx, mass in enumerate(TARGET_MASSES, start=1):
        culture_id = "culture_{:03d}".format(idx)
        plate_id = "plate_{:03d}".format(idx)
        plating_id = "plating_{:03d}".format(idx)
        dilution_factor = mass
        transcript.extend(
            [
                {
                    "type": "tool_call",
                    "tool_name": "transform",
                    "arguments": {
                        "culture_id": culture_id,
                        "plasmid_mass_pg": mass,
                        "heat_shock_seconds": 30,
                        "recovery_minutes": 60,
                        "outgrowth_media": "SOC",
                        "shaking": True,
                    },
                },
                {
                    "type": "tool_call",
                    "tool_name": "plate",
                    "arguments": {
                        "culture_id": culture_id,
                        "plate_id": plate_id,
                        "plating_id": plating_id,
                        "dilution_factor": dilution_factor,
                        "volume_ul": 100,
                        "status": "plated",
                        "warnings": [],
                    },
                },
                {
                    "type": "tool_call",
                    "tool_name": "count_colonies",
                    "arguments": {
                        "plating_id": plating_id,
                        "observed_colonies": 100,
                        "dilution_factor": dilution_factor,
                        "volume_ul": 100,
                        "status": "plated",
                        "warnings": [],
                    },
                },
            ]
        )
    return transcript


def _good_answer(with_commas: bool = True) -> str:
    thousand = "1,000" if with_commas else "1000"
    ten_thousand = "10,000" if with_commas else "10000"
    return (
        "10 pg: 1.0e9 CFU/ug; "
        "100 pg: 1.0e9 CFU/ug; "
        "{:s} pg: 1.0e9 CFU/ug; "
        "{:s} pg: 1.0e9 CFU/ug. "
        "The runs were internally consistent."
    ).format(thousand, ten_thousand)


def test_good_trajectory_scores_high():
    scores = score_transform_trajectory(
        final_answer=_good_answer(),
        transcript=_good_transcript(),
        ground_truth_path=str(TRANSFORM_GROUND_TRUTH_PATH),
    )
    assert scores["decision_quality"] == 1.0
    assert scores["task_success"] == 1.0
    assert scores["overall"] > 0.9


def test_wrong_heat_shock_reduces_decision_score():
    transcript = _good_transcript()
    transcript[1]["arguments"]["heat_shock_seconds"] = 45
    scores = score_transform_trajectory(
        final_answer=_good_answer(),
        transcript=transcript,
        ground_truth_path=str(TRANSFORM_GROUND_TRUTH_PATH),
    )
    assert scores["decision_scores"]["heat_shock_duration_seconds"] == 0.0
    assert scores["decision_quality"] < 1.0


def test_task_success_requires_numeric_values_matching_transcript():
    answer = (
        "10 pg: reported CFU/ug; 100 pg: reported CFU/ug; 1,000 pg: reported CFU/ug; "
        "10,000 pg: reported CFU/ug. The runs were internally consistent."
    )
    assert score_task_success(answer, _good_transcript()) == 0.0


def test_task_success_accepts_uncommaed_mass_labels():
    assert score_task_success(_good_answer(with_commas=False), _good_transcript()) == 1.0


def test_task_success_accepts_ordered_respectively_report():
    answer = (
        "This gives 1.0e9, 1.0e9, 1.0e9, and 1.0e9 CFU/ug for "
        "10, 100, 1,000, and 10,000 pg, respectively. "
        "The runs were internally consistent."
    )

    assert score_task_success(answer, _good_transcript()) == 1.0


def test_task_success_accepts_internal_consistency_noun():
    answer = _good_answer().replace(
        "The runs were internally consistent.", "The values show good internal consistency."
    )

    assert score_task_success(answer, _good_transcript()) == 1.0


def test_task_success_accepts_unicode_superscript_scientific_notation():
    answer = (
        "10 pg: 1.0 × 10⁹ CFU/ug; 100 pg: 1.0 × 10⁹ CFU/ug; "
        "1,000 pg: 1.0 × 10⁹ CFU/ug; 10,000 pg: 1.0 × 10⁹ CFU/ug. "
        "The runs show good internal consistency."
    )

    assert score_task_success(answer, _good_transcript()) == 1.0


def test_transform_decisions_use_only_cultures_with_usable_counts():
    abandoned = []
    for index, mass in enumerate(TARGET_MASSES, start=10):
        abandoned.append(
            {
                "type": "tool_call",
                "tool_name": "transform",
                "arguments": {
                    "culture_id": "culture_{:03d}".format(index),
                    "plasmid_mass_pg": mass,
                    "heat_shock_seconds": 45,
                    "recovery_minutes": 60,
                    "outgrowth_media": "LB",
                },
            }
        )

    scores = score_transform_trajectory(
        final_answer=_good_answer(),
        transcript=abandoned + _good_transcript(),
        ground_truth_path=str(TRANSFORM_GROUND_TRUTH_PATH),
    )

    assert scores["decision_scores"]["heat_shock_duration_seconds"] == 1.0
    assert scores["decision_scores"]["soc_outgrowth"] == 1.0


def test_transform_efficiency_allows_one_full_dilution_retry_with_lookups():
    lookup_calls = [
        {
            "type": "tool_call",
            "tool_name": "lookup_reagent",
            "arguments": {"reagent_name": "reference_{:02d}".format(index)},
        }
        for index in range(11)
    ]
    scores = score_transform_trajectory(
        final_answer=_good_answer(),
        transcript=_good_transcript() + lookup_calls,
        ground_truth_path=str(TRANSFORM_GROUND_TRUTH_PATH),
    )

    assert scores["efficiency"] == 0.5


def test_uncountable_counts_zero_out_task_success_and_countability_decision():
    transcript = _good_transcript()
    transcript[-1]["arguments"]["observed_colonies"] = 1200
    transcript[-1]["arguments"]["status"] = "count_out_of_range"
    transcript[-1]["arguments"]["warnings"] = [
        "Observed colonies fall outside the cited countable range of 25-250 colonies per plate."
    ]

    scores = score_transform_trajectory(
        final_answer=_good_answer(),
        transcript=transcript,
        ground_truth_path=str(TRANSFORM_GROUND_TRUTH_PATH),
    )

    assert scores["task_success"] == 0.0
    assert scores["decision_scores"]["countable_colony_range"] == 0.0


def test_inspect_style_tool_messages_score_soc_default_correctly():
    transcript = [
        {
            "role": "assistant",
            "tool_calls": [
                {
                    "id": "call_prepare",
                    "function": "prepare_media",
                    "arguments": {
                        "medium": "LB agar",
                        "antibiotic": "ampicillin",
                        "antibiotic_concentration_ug_ml": 100,
                        "plate_count": 4,
                    },
                }
            ],
        }
    ]
    for idx, mass in enumerate(TARGET_MASSES, start=1):
        transcript.append(
            {
                "role": "assistant",
                "tool_calls": [
                    {
                        "id": "call_transform_{:d}".format(idx),
                        "function": "transform",
                        "arguments": {
                            "plasmid_mass_pg": mass,
                            "heat_shock_seconds": 30,
                            "recovery_minutes": 60,
                        },
                    }
                ],
            }
        )
        transcript.append(
            {
                "role": "tool",
                "tool_call_id": "call_transform_{:d}".format(idx),
                "function": "transform",
                "content": json.dumps(
                    {
                        "culture_id": "culture_{:03d}".format(idx),
                        "heat_shock_seconds": 30,
                        "recovery_minutes": 60,
                        "outgrowth_media": "SOC",
                    }
                ),
            }
        )

    scores = score_transform_trajectory(
        final_answer=_good_answer(),
        transcript=transcript,
        ground_truth_path=str(TRANSFORM_GROUND_TRUTH_PATH),
    )

    assert scores["decision_scores"]["soc_outgrowth"] == 1.0


def _good_growth_transcript():
    transcript = []
    expected_doubling_times = {
        "LB": 20.0,
        "M9 + glucose": 57.0,
        "LB + chloramphenicol (1.8 uM)": 40.0,
    }
    for condition, doubling_time in expected_doubling_times.items():
        growth_id = "growth_" + condition.lower().replace(" ", "_").replace("+", "plus").replace("(", "").replace(")", "").replace(".", "")
        transcript.append(
            {
                "type": "tool_call",
                "tool_name": "inoculate_growth",
                "arguments": {
                    "growth_id": growth_id,
                    "condition": condition,
                    "starting_od600": 0.05,
                },
            }
        )
        od_values = {
            "LB": [0.05, 0.084, 0.141, 0.237, 0.4, 0.672, 1.131, 1.902, 3.2],
            "M9 + glucose": [0.05, 0.06, 0.072, 0.086, 0.104, 0.124, 0.149, 0.179, 0.214],
            "LB + chloramphenicol (1.8 uM)": [0.05, 0.065, 0.084, 0.109, 0.141, 0.183, 0.237, 0.308, 0.4],
        }[condition]
        for idx, value in enumerate(od_values):
            if idx > 0:
                transcript.append(
                    {
                        "type": "tool_call",
                        "tool_name": "incubate",
                        "arguments": {
                            "growth_id": growth_id,
                            "condition": condition,
                            "duration_minutes": 15,
                            "elapsed_minutes": idx * 15,
                        },
                    }
                )
            dilution = 10.0 if condition == "LB" and idx >= 6 else 1.0
            transcript.append(
                {
                    "type": "tool_call",
                    "tool_name": "measure_od600",
                    "arguments": {
                        "growth_id": growth_id,
                        "condition": condition,
                        "elapsed_minutes": idx * 15,
                        "dilution_factor": dilution,
                        "observed_od600": value / dilution,
                        "estimated_undiluted_od600": value,
                    },
                }
            )
        transcript.append(
            {
                "type": "tool_call",
                "tool_name": "fit_growth_curve",
                "arguments": {
                    "growth_id": growth_id,
                    "condition": condition,
                    "status": "analyzable",
                    "qualifying_points": 4,
                    "estimated_doubling_time_minutes": doubling_time,
                },
            }
        )
    return transcript


def _good_growth_answer() -> str:
    return (
        "LB: 20 minutes; "
        "M9 + glucose: 57 minutes; "
        "LB + chloramphenicol (1.8 uM): 40 minutes. "
        "Fastest to slowest: LB, LB + chloramphenicol (1.8 uM), M9 + glucose."
    )


def test_good_growth_trajectory_scores_high():
    scores = score_growth_trajectory(
        final_answer=_good_growth_answer(),
        transcript=_good_growth_transcript(),
        ground_truth_path=str(GROWTH_GROUND_TRUTH_PATH),
    )
    assert scores["decision_quality"] == 1.0
    assert scores["task_success"] == 1.0
    assert scores["overall"] > 0.9


def test_growth_decision_quality_accepts_defensible_non_exact_parameters():
    transcript = _good_growth_transcript()
    for call in transcript:
        if call["tool_name"] == "inoculate_growth":
            call["arguments"]["starting_od600"] = 0.01
        elif call["tool_name"] == "incubate":
            call["arguments"]["duration_minutes"] = 20

    scores = score_growth_trajectory(
        final_answer=_good_growth_answer(),
        transcript=transcript,
        ground_truth_path=str(GROWTH_GROUND_TRUTH_PATH),
    )

    assert scores["decision_scores"]["growth_starting_od600"] == 1.0
    assert scores["decision_scores"]["growth_measurement_interval"] == 1.0


@pytest.mark.parametrize("starting_od600", [0.009, 0.11])
def test_growth_decision_quality_rejects_out_of_range_parameters(starting_od600):
    transcript = _good_growth_transcript()
    for call in transcript:
        if call["tool_name"] == "inoculate_growth":
            call["arguments"]["starting_od600"] = starting_od600
        elif call["tool_name"] == "incubate":
            call["arguments"]["duration_minutes"] = 30

    scores = score_growth_trajectory(
        final_answer=_good_growth_answer(),
        transcript=transcript,
        ground_truth_path=str(GROWTH_GROUND_TRUTH_PATH),
    )

    assert scores["decision_scores"]["growth_starting_od600"] == 0.0
    assert scores["decision_scores"]["growth_measurement_interval"] == 0.0


def test_growth_decision_quality_requires_consistent_parameters():
    transcript = _good_growth_transcript()
    inoculations = [
        call for call in transcript if call["tool_name"] == "inoculate_growth"
    ]
    incubations = [call for call in transcript if call["tool_name"] == "incubate"]
    inoculations[-1]["arguments"]["starting_od600"] = 0.08
    incubations[-1]["arguments"]["duration_minutes"] = 20

    scores = score_growth_trajectory(
        final_answer=_good_growth_answer(),
        transcript=transcript,
        ground_truth_path=str(GROWTH_GROUND_TRUTH_PATH),
    )

    assert scores["decision_scores"]["growth_starting_od600"] == 0.0
    assert scores["decision_scores"]["growth_measurement_interval"] == 0.0


def test_growth_task_success_requires_matching_doubling_times():
    answer = (
        "LB: about 20 minutes; M9 + glucose: about 30 minutes; "
        "LB + chloramphenicol (1.8 uM): about 40 minutes."
    )
    assert score_growth_task_success(answer, _good_growth_transcript()) == 0.0


@pytest.mark.parametrize(
    "answer",
    [
        (
            "LB — 20.0 min; "
            "LB + chloramphenicol (1.8 uM) — 40.0 min; "
            "M9 + glucose — 57.0 min."
        ),
        (
            "| Condition | Doubling time |\n"
            "|---|---|\n"
            "| **LB** | 20.0 minutes |\n"
            "| **LB + chloramphenicol (1.8 uM)** | 40.0 minutes |\n"
            "| **M9 + glucose** | 57.0 minutes |"
        ),
    ],
)
def test_growth_task_success_accepts_common_report_separators(answer):
    assert score_growth_task_success(answer, _good_growth_transcript()) == 1.0


def test_growth_fit_failure_reduces_decision_quality_and_task_success():
    transcript = _good_growth_transcript()
    transcript[-1]["arguments"]["status"] = "insufficient_points"
    transcript[-1]["arguments"]["qualifying_points"] = 2
    transcript[-1]["arguments"].pop("estimated_doubling_time_minutes")
    scores = score_growth_trajectory(
        final_answer=_good_growth_answer(),
        transcript=transcript,
        ground_truth_path=str(GROWTH_GROUND_TRUTH_PATH),
    )
    assert scores["task_success"] == 0.0
    assert scores["decision_scores"]["growth_curve_analyzable"] == 0.0


def _good_followup_transcript():
    growth_id = "growth_001"
    transcript = [
        {
            "type": "tool_call",
            "tool_name": "inoculate_growth",
            "arguments": {
                "growth_id": growth_id,
                "condition": "LB + chloramphenicol (1.8 uM)",
                "starting_od600": 0.05,
            },
        }
    ]
    measurements = [
        (15, 0.065),
        (30, 0.085),
        (45, 0.110),
        (60, 0.145),
        (75, 0.185),
    ]
    for elapsed_minutes, estimated_od600 in measurements:
        transcript.extend(
            [
                {
                    "type": "tool_call",
                    "tool_name": "incubate",
                    "arguments": {
                        "growth_id": growth_id,
                        "condition": "LB + chloramphenicol (1.8 uM)",
                        "duration_minutes": 15,
                        "elapsed_minutes": elapsed_minutes,
                    },
                },
                {
                    "type": "tool_call",
                    "tool_name": "measure_od600",
                    "arguments": {
                        "growth_id": growth_id,
                        "condition": "LB + chloramphenicol (1.8 uM)",
                        "elapsed_minutes": elapsed_minutes,
                        "dilution_factor": 1.0,
                        "observed_od600": estimated_od600,
                        "estimated_undiluted_od600": estimated_od600,
                    },
                },
            ]
        )
    transcript.append(
        {
            "type": "tool_call",
            "tool_name": "fit_growth_curve",
            "arguments": {
                "growth_id": growth_id,
                "condition": "LB + chloramphenicol (1.8 uM)",
                "status": "analyzable",
                "qualifying_points": 4,
                "estimated_doubling_time_minutes": 40.0,
                "warnings": [],
            },
        }
    )
    return transcript


def _good_followup_answer() -> str:
    return (
        "Follow-up condition: LB + chloramphenicol (1.8 uM)\n"
        "Follow-up doubling time: 40 minutes\n"
        "Conclusion: real slowdown\n"
        "Interpretation: The earlier pilot was ambiguous because the chloramphenicol fit was undersampled, and this focused follow-up shows the slowdown is real rather than an artifact."
    )


def test_good_followup_trajectory_scores_high():
    scores = score_followup_trajectory(
        final_answer=_good_followup_answer(),
        transcript=_good_followup_transcript(),
        ground_truth_path=str(FOLLOWUP_GROUND_TRUTH_PATH),
    )
    assert scores["task_success"] == 1.0
    assert scores["decision_quality"] == 1.0
    assert scores["troubleshooting"] == 1.0
    assert scores["efficiency"] == 1.0
    assert scores["overall"] > 0.99


def test_followup_task_success_requires_real_slowdown_conclusion():
    answer = (
        "Follow-up condition: LB + chloramphenicol (1.8 uM)\n"
        "Follow-up doubling time: 40 minutes\n"
        "Conclusion: artifact\n"
        "Interpretation: The pilot was ambiguous."
    )
    assert score_followup_task_success(answer, _good_followup_transcript()) == 0.0


def test_followup_undersampled_without_diagnosis_scores_zero_troubleshooting():
    transcript = _good_followup_transcript()
    transcript[-1]["arguments"]["status"] = "insufficient_points"
    transcript[-1]["arguments"]["qualifying_points"] = 2
    transcript[-1]["arguments"].pop("estimated_doubling_time_minutes")

    answer = (
        "Follow-up condition: LB + chloramphenicol (1.8 uM)\n"
        "Follow-up doubling time: 40 minutes\n"
        "Conclusion: real slowdown\n"
        "Interpretation: Follow-up run attempted."
    )
    scores = score_followup_trajectory(
        final_answer=answer,
        transcript=transcript,
        ground_truth_path=str(FOLLOWUP_GROUND_TRUTH_PATH),
    )
    assert scores["task_success"] == 0.0
    assert scores["decision_scores"]["followup_curve_analyzable"] == 0.0
    assert scores["troubleshooting"] == 0.0


def test_followup_rerun_everything_loses_focus_and_efficiency_credit():
    transcript = _good_followup_transcript()
    for condition in ("LB", "M9 + glucose"):
        growth_id = "growth_extra_{}".format(condition.lower().replace(" ", "_").replace("+", "plus"))
        transcript.insert(
            0,
            {
                "type": "tool_call",
                "tool_name": "inoculate_growth",
                "arguments": {
                    "growth_id": growth_id,
                    "condition": condition,
                    "starting_od600": 0.05,
                },
            },
        )
        for idx in range(5):
            elapsed_minutes = 15 * (idx + 1)
            transcript.extend(
                [
                    {
                        "type": "tool_call",
                        "tool_name": "incubate",
                        "arguments": {
                            "growth_id": growth_id,
                            "condition": condition,
                            "duration_minutes": 15,
                            "elapsed_minutes": elapsed_minutes,
                        },
                    },
                    {
                        "type": "tool_call",
                        "tool_name": "measure_od600",
                        "arguments": {
                            "growth_id": growth_id,
                            "condition": condition,
                            "elapsed_minutes": elapsed_minutes,
                            "dilution_factor": 1.0,
                            "observed_od600": 0.08 + (0.03 * idx),
                            "estimated_undiluted_od600": 0.08 + (0.03 * idx),
                        },
                    },
                ]
            )
        transcript.append(
            {
                "type": "tool_call",
                "tool_name": "fit_growth_curve",
                "arguments": {
                    "growth_id": growth_id,
                    "condition": condition,
                    "status": "analyzable",
                    "qualifying_points": 4,
                    "estimated_doubling_time_minutes": 20.0 if condition == "LB" else 57.0,
                    "warnings": [],
                },
            }
        )

    scores = score_followup_trajectory(
        final_answer=_good_followup_answer(),
        transcript=transcript,
        ground_truth_path=str(FOLLOWUP_GROUND_TRUTH_PATH),
    )
    assert scores["task_success"] == 1.0
    assert scores["decision_scores"]["followup_targets_ambiguous_condition"] == 0.0
    assert scores["decision_quality"] < 1.0
    assert scores["efficiency"] == 0.0


def _good_pcr_transcript():
    return [
        {
            "type": "tool_call",
            "tool_name": "run_pcr",
            "arguments": {
                "reaction_id": "pcr_001",
                "polymerase_name": "Q5 High-Fidelity DNA polymerase",
                "normalized_polymerase_name": "Q5 High-Fidelity DNA polymerase",
                "additive": "DMSO",
                "normalized_additive": "DMSO",
                "extension_seconds": 60,
                "cycle_count": 32,
                "target_size_bp": 2000,
                "status": "clean_target_band",
                "visible_bands_bp": [2000],
                "smear_present": False,
            },
        },
        {
            "type": "tool_call",
            "tool_name": "run_gel",
            "arguments": {
                "gel_id": "gel_001",
                "reaction_id": "pcr_001",
                "polymerase_name": "Q5 High-Fidelity DNA polymerase",
                "normalized_polymerase_name": "Q5 High-Fidelity DNA polymerase",
                "additive": "DMSO",
                "normalized_additive": "DMSO",
                "extension_seconds": 60,
                "cycle_count": 32,
                "target_size_bp": 2000,
                "status": "single_clean_target_band",
                "visible_bands_bp": [2000],
                "smear_present": False,
            },
        },
    ]


def _good_pcr_answer() -> str:
    return (
        "Polymerase: Q5 High-Fidelity DNA polymerase\n"
        "Additive: DMSO\n"
        "Extension: 60 seconds\n"
        "Cycles: 32\n"
        "Result: single clean 2 kb band"
    )


def test_good_pcr_trajectory_scores_high():
    scores = score_pcr_trajectory(
        final_answer=_good_pcr_answer(),
        transcript=_good_pcr_transcript(),
        ground_truth_path=str(PCR_GROUND_TRUTH_PATH),
    )
    assert scores["decision_quality"] == 1.0
    assert scores["task_success"] == 1.0
    assert scores["overall"] > 0.9


def test_pcr_task_success_requires_matching_reported_condition():
    answer = (
        "Polymerase: Phusion High-Fidelity DNA polymerase\n"
        "Additive: DMSO\n"
        "Extension: 60 seconds\n"
        "Cycles: 32\n"
        "Result: single clean 2 kb band"
    )
    assert score_pcr_task_success(answer, _good_pcr_transcript()) == 0.0


def test_pcr_decision_quality_uses_successful_condition_not_failed_attempt_mix():
    failed = _good_pcr_transcript()[0]
    failed["arguments"].update(
        {
            "reaction_id": "pcr_001",
            "status": "gc_rich_failure",
            "visible_bands_bp": [],
        }
    )
    successful, gel = _good_pcr_transcript()
    successful["arguments"].update(
        {
            "reaction_id": "pcr_002",
            "extension_seconds": 75,
        }
    )
    gel["arguments"].update(
        {
            "reaction_id": "pcr_002",
            "extension_seconds": 75,
        }
    )
    answer = (
        "Polymerase: Q5 High-Fidelity DNA polymerase\n"
        "Additive: DMSO\n"
        "Extension: 75 seconds\n"
        "Cycles: 32\n"
        "Result: single clean 2 kb band"
    )

    scores = score_pcr_trajectory(
        final_answer=answer,
        transcript=[failed, successful, gel],
        ground_truth_path=str(PCR_GROUND_TRUTH_PATH),
    )

    assert scores["task_success"] == 1.0
    assert scores["decision_scores"]["gc_rich_polymerase_choice"] == 1.0
    assert scores["decision_scores"]["gc_rich_additive_choice"] == 1.0
    assert scores["decision_scores"]["gc_rich_extension_time"] == 0.0
    assert scores["decision_scores"]["genomic_pcr_cycle_count"] == 1.0


def test_failed_pcr_requires_troubleshooting_for_credit():
    transcript = [
        {
            "type": "tool_call",
            "tool_name": "run_pcr",
            "arguments": {
                "reaction_id": "pcr_002",
                "polymerase_name": "Q5 High-Fidelity DNA polymerase",
                "normalized_polymerase_name": "Q5 High-Fidelity DNA polymerase",
                "additive": "none",
                "normalized_additive": "none",
                "extension_seconds": 60,
                "cycle_count": 32,
                "target_size_bp": 2000,
                "status": "gc_rich_failure",
                "visible_bands_bp": [],
                "smear_present": False,
            },
        },
        {
            "type": "tool_call",
            "tool_name": "run_gel",
            "arguments": {
                "gel_id": "gel_002",
                "reaction_id": "pcr_002",
                "polymerase_name": "Q5 High-Fidelity DNA polymerase",
                "normalized_polymerase_name": "Q5 High-Fidelity DNA polymerase",
                "additive": "none",
                "normalized_additive": "none",
                "extension_seconds": 60,
                "cycle_count": 32,
                "target_size_bp": 2000,
                "status": "no_visible_product",
                "visible_bands_bp": [],
                "smear_present": False,
            },
        },
    ]
    scores = score_pcr_trajectory(
        final_answer=(
            "Polymerase: Q5 High-Fidelity DNA polymerase\n"
            "Additive: none\n"
            "Extension: 60 seconds\n"
            "Cycles: 32\n"
            "Result: not achieved"
        ),
        transcript=transcript,
        ground_truth_path=str(PCR_GROUND_TRUTH_PATH),
    )
    assert scores["task_success"] == 0.0
    assert scores["troubleshooting"] == 0.0


def _good_screen_transcript():
    return [
        {
            "type": "tool_call",
            "tool_name": "inspect_screening_plate",
            "arguments": {
                "status": "screening_plate_ready",
                "plate_id": "screen_plate_001",
                "white_colony_count": 12,
                "blue_colony_count": 18,
            },
        },
        {
            "type": "tool_call",
            "tool_name": "run_colony_pcr",
            "arguments": {
                "plate_id": "screen_plate_001",
                "primer_pair": "M13/pUC flank primers",
                "screened_colony_ids": [
                    "white_001",
                    "white_002",
                    "white_003",
                    "white_004",
                    "white_005",
                    "white_006",
                ],
                "screened_colony_count": 6,
                "screening_strategy": "white_only",
                "cumulative_screened_white_colony_count": 6,
                "cumulative_confidence_pct": 95.3,
                "confirmed_recombinant_ids_cumulative": ["white_002", "white_005"],
                "confirmed_recombinant_ids_in_batch": ["white_002", "white_005"],
            },
        },
    ]


def _good_screen_answer() -> str:
    return (
        "White colonies screened: 6\n"
        "Confirmed recombinant colonies: white_002, white_005\n"
        "Confidence achieved: 95.3%\n"
        "Interpretation: Two recombinant colonies confirmed from six white candidates."
    )


def test_good_screen_trajectory_scores_high():
    scores = score_screen_trajectory(
        final_answer=_good_screen_answer(),
        transcript=_good_screen_transcript(),
        ground_truth_path=str(SCREEN_GROUND_TRUTH_PATH),
    )
    assert scores["task_success"] == 1.0
    assert scores["decision_quality"] == 1.0
    assert scores["troubleshooting"] == 1.0
    assert scores["efficiency"] == 1.0
    assert scores["overall"] >= 0.999


def test_screen_task_success_requires_matching_screened_count():
    mismatch = (
        "White colonies screened: 8\n"
        "Confirmed recombinant colonies: white_002, white_005\n"
        "Confidence achieved: 95.3%\n"
        "Interpretation: Two recombinant colonies confirmed."
    )
    assert score_screen_task_success(mismatch, _good_screen_transcript()) == 0.0


def test_screen_task_success_accepts_screened_colony_id_list():
    answer = (
        "White colonies screened: white_001, white_002, white_003, "
        "white_004, white_005, white_006\n"
        "Confirmed recombinant colonies: white_002, white_005\n"
        "Confidence achieved: 95.3%\n"
        "Interpretation: Two recombinant colonies confirmed."
    )
    assert score_screen_task_success(answer, _good_screen_transcript()) == 1.0


def test_screen_task_success_requires_interpretation_keyword():
    answer = (
        "White colonies screened: 6\n"
        "Confirmed recombinant colonies: white_002, white_005\n"
        "Confidence achieved: 95.3%\n"
        "Interpretation: Two positive clones confirmed."
    )
    assert score_screen_task_success(answer, _good_screen_transcript()) == 0.0


def test_screen_includes_blue_colony_fails_decision_quality():
    transcript = _good_screen_transcript()
    transcript.append(
        {
            "type": "tool_call",
            "tool_name": "run_colony_pcr",
            "arguments": {
                "plate_id": "screen_plate_001",
                "primer_pair": "M13/pUC flank primers",
                "screened_colony_ids": ["blue_001"],
                "screened_colony_count": 1,
                "screening_strategy": "includes_blue",
                "cumulative_screened_white_colony_count": 6,
                "cumulative_confidence_pct": 95.3,
                "confirmed_recombinant_ids_cumulative": ["white_002", "white_005"],
                "confirmed_recombinant_ids_in_batch": [],
            },
        }
    )
    scores = score_screen_trajectory(
        final_answer=_good_screen_answer(),
        transcript=transcript,
        ground_truth_path=str(SCREEN_GROUND_TRUTH_PATH),
    )
    assert scores["decision_scores"]["screens_only_white_colonies"] == 0.0


def test_screen_blue_colony_without_recombinants_requires_diagnosis_for_credit():
    transcript = [
        {
            "type": "tool_call",
            "tool_name": "inspect_screening_plate",
            "arguments": {
                "status": "screening_plate_ready",
                "plate_id": "screen_plate_001",
            },
        },
        {
            "type": "tool_call",
            "tool_name": "run_colony_pcr",
            "arguments": {
                "plate_id": "screen_plate_001",
                "primer_pair": "M13/pUC flank primers",
                "screened_colony_ids": ["blue_001", "blue_002"],
                "screened_colony_count": 2,
                "screening_strategy": "includes_blue",
                "cumulative_screened_white_colony_count": 0,
                "cumulative_confidence_pct": 0.0,
                "confirmed_recombinant_ids_cumulative": [],
                "confirmed_recombinant_ids_in_batch": [],
            },
        },
    ]
    bare_answer = (
        "White colonies screened: 0\n"
        "Confirmed recombinant colonies: None\n"
        "Confidence achieved: 0.0%\n"
        "Interpretation: No recombinant colonies confirmed."
    )
    scores_without_diagnosis = score_screen_trajectory(
        final_answer=bare_answer,
        transcript=transcript,
        ground_truth_path=str(SCREEN_GROUND_TRUTH_PATH),
    )
    assert scores_without_diagnosis["troubleshooting"] == 0.0

    diagnosed_answer = bare_answer + (
        "\nBlue colonies should not have been screened because they are empty-vector "
        "background."
    )
    scores_with_diagnosis = score_screen_trajectory(
        final_answer=diagnosed_answer,
        transcript=transcript,
        ground_truth_path=str(SCREEN_GROUND_TRUTH_PATH),
    )
    assert scores_with_diagnosis["troubleshooting"] > 0.0


def _good_clone_transcript():
    digest_vector = {
        "type": "tool_call",
        "tool_name": "restriction_digest",
        "arguments": {
            "digest_id": "digest_001",
            "substrate_fragment_id": "puc19_vector",
            "enzyme_names": ["EcoRI", "BamHI"],
            "enzymes_key": "bamhi+ecori",
            "buffer": "CutSmart",
            "buffer_normalized": "cutsmart",
            "temperature_c": 37.0,
            "duration_minutes": 60,
            "heat_inactivate_after": True,
            "output_fragment_ids": ["fragment_003"],
            "status": "digested",
        },
    }
    digest_insert = dict(digest_vector)
    digest_insert = {
        "type": "tool_call",
        "tool_name": "restriction_digest",
        "arguments": {
            "digest_id": "digest_002",
            "substrate_fragment_id": "insert_raw",
            "enzyme_names": ["EcoRI", "BamHI"],
            "enzymes_key": "bamhi+ecori",
            "buffer": "CutSmart",
            "buffer_normalized": "cutsmart",
            "temperature_c": 37.0,
            "duration_minutes": 60,
            "heat_inactivate_after": True,
            "output_fragment_ids": ["fragment_004"],
            "status": "digested",
        },
    }
    ligation = {
        "type": "tool_call",
        "tool_name": "ligate",
        "arguments": {
            "ligation_id": "ligation_001",
            "vector_fragment_id": "fragment_003",
            "insert_fragment_ids": ["fragment_004"],
            "ligase_name": "T4 DNA ligase",
            "ligase_normalized": "t4 dna ligase",
            "vector_to_insert_molar_ratio": 3.0,
            "temperature_c": 16.0,
            "duration_minutes": 960,
            "status": "ligated",
        },
    }
    prepare = {
        "type": "tool_call",
        "tool_name": "prepare_media",
        "arguments": {
            "medium": "LB agar",
            "antibiotic": "ampicillin",
            "antibiotic_concentration_ug_ml": 100,
            "plate_count": 1,
        },
    }
    transform_call = {
        "type": "tool_call",
        "tool_name": "transform_ligation",
        "arguments": {
            "ligation_id": "ligation_001",
            "culture_id": "culture_001",
            "heat_shock_seconds": 30,
            "recovery_minutes": 60,
            "outgrowth_media": "SOC",
            "status": "transformed",
            "expected_transformants": 400.0,
        },
    }
    plate_call = {
        "type": "tool_call",
        "tool_name": "plate",
        "arguments": {
            "culture_id": "culture_001",
            "plate_id": "plate_001",
            "plating_id": "plating_001",
            "dilution_factor": 1.0,
            "volume_ul": 100,
        },
    }
    count = {
        "type": "tool_call",
        "tool_name": "count_colonies",
        "arguments": {
            "plating_id": "plating_001",
            "observed_colonies": 200,
            "status": "plated",
        },
    }
    inspect_plate = {
        "type": "tool_call",
        "tool_name": "inspect_screening_plate",
        "arguments": {
            "status": "screening_plate_ready",
            "plate_id": "screen_plate_001",
            "white_colony_count": 12,
            "blue_colony_count": 18,
        },
    }
    colony_pcr = {
        "type": "tool_call",
        "tool_name": "run_colony_pcr",
        "arguments": {
            "plate_id": "screen_plate_001",
            "primer_pair": "M13/pUC flank primers",
            "screened_colony_ids": [
                "white_001",
                "white_002",
                "white_003",
                "white_004",
                "white_005",
                "white_006",
            ],
            "screened_colony_count": 6,
            "screening_strategy": "white_only",
            "cumulative_screened_white_colony_count": 6,
            "cumulative_confidence_pct": 95.3,
            "confirmed_recombinant_ids_cumulative": ["white_002", "white_005"],
            "confirmed_recombinant_ids_in_batch": ["white_002", "white_005"],
        },
    }
    return [
        digest_vector,
        digest_insert,
        ligation,
        prepare,
        transform_call,
        plate_call,
        count,
        inspect_plate,
        colony_pcr,
    ]


def _good_clone_answer() -> str:
    return (
        "Digest enzymes: EcoRI, BamHI\n"
        "Digest buffer: CutSmart\n"
        "Ligase: T4 DNA ligase\n"
        "Vector:insert molar ratio: 1:3\n"
        "Ligation temperature: 16 C\n"
        "Transformants observed: 200\n"
        "White colonies screened: 6\n"
        "Confirmed recombinant colonies: white_002, white_005\n"
        "Confidence achieved: 95.3%\n"
        "Interpretation: Two recombinant colonies confirmed; cloning succeeded."
    )


def test_good_clone_trajectory_scores_high():
    scores = score_clone_trajectory(
        final_answer=_good_clone_answer(),
        transcript=_good_clone_transcript(),
        ground_truth_path=str(CLONE_GROUND_TRUTH_PATH),
    )
    assert scores["task_success"] == 1.0
    assert scores["decision_quality"] == 1.0
    assert scores["troubleshooting"] == 1.0
    assert scores["efficiency"] >= 0.5
    assert scores["overall"] >= 0.9


def test_clone_wrong_buffer_fails_decision_quality():
    transcript = _good_clone_transcript()
    transcript[0]["arguments"]["buffer_normalized"] = "neb1.1"
    transcript[0]["arguments"]["status"] = "wrong_buffer"
    scores = score_clone_trajectory(
        final_answer=_good_clone_answer(),
        transcript=transcript,
        ground_truth_path=str(CLONE_GROUND_TRUTH_PATH),
    )
    assert scores["decision_scores"]["digest_uses_compatible_buffer"] == 0.0
    assert scores["troubleshooting"] < 1.0


def test_clone_successful_retry_controls_decisions_and_troubleshooting():
    transcript = _good_clone_transcript()
    failed_vector = {
        "type": "tool_call",
        "tool_name": "restriction_digest",
        "arguments": {
            **transcript[0]["arguments"],
            "digest_id": "digest_failed",
            "buffer_normalized": "neb1.1",
            "duration_minutes": 30,
            "status": "incomplete_digest",
        },
    }
    transcript.insert(0, failed_vector)

    scores = score_clone_trajectory(
        final_answer=_good_clone_answer(),
        transcript=transcript,
        ground_truth_path=str(CLONE_GROUND_TRUTH_PATH),
    )

    assert scores["decision_scores"]["digest_sufficient_duration"] == 1.0
    assert scores["decision_scores"]["digest_uses_compatible_buffer"] == 1.0
    assert scores["troubleshooting"] == 1.0


def test_clone_filters_casefold_equivalent_reagent_names():
    transcript = _good_clone_transcript()
    transcript[3]["arguments"]["antibiotic"] = "Ampicillin"

    scores = score_clone_trajectory(
        final_answer=_good_clone_answer(),
        transcript=transcript,
        ground_truth_path=str(CLONE_GROUND_TRUTH_PATH),
    )

    assert scores["decision_scores"]["ampicillin_selection_100"] == 1.0


def test_clone_ignores_incomplete_ligate_call_for_successful_ligation_decisions():
    transcript = _good_clone_transcript()
    incomplete_call = {
        "type": "tool_call",
        "tool_name": "ligate",
        "arguments": {
            "vector_to_insert_molar_ratio": 3.0,
            "temperature_c": 16.0,
        },
    }
    transcript.insert(2, incomplete_call)

    scores = score_clone_trajectory(
        final_answer=_good_clone_answer(),
        transcript=transcript,
        ground_truth_path=str(CLONE_GROUND_TRUTH_PATH),
    )

    assert scores["decision_scores"]["uses_t4_dna_ligase"] == 1.0


def test_clone_wrong_ligase_fails_decision_quality():
    transcript = _good_clone_transcript()
    transcript[2]["arguments"]["ligase_normalized"] = "e. coli dna ligase"
    transcript[2]["arguments"]["status"] = "wrong_ligase"
    answer = _good_clone_answer().replace("T4 DNA ligase", "E. coli DNA ligase")
    scores = score_clone_trajectory(
        final_answer=answer,
        transcript=transcript,
        ground_truth_path=str(CLONE_GROUND_TRUTH_PATH),
    )
    assert scores["decision_scores"]["uses_t4_dna_ligase"] == 0.0
    assert score_clone_task_success(answer, transcript) == 0.0


def test_clone_task_success_requires_successful_reactions_and_matching_transformants():
    failed_digest = _good_clone_transcript()
    failed_digest[0]["arguments"]["status"] = "wrong_buffer"
    assert score_clone_task_success(_good_clone_answer(), failed_digest) == 0.0

    fabricated_count = _good_clone_transcript()
    fabricated_answer = _good_clone_answer().replace(
        "Transformants observed: 200", "Transformants observed: 201"
    )
    assert score_clone_task_success(fabricated_answer, fabricated_count) == 0.0


def test_clone_task_success_accepts_same_dilution_plate_sum_only():
    same_dilution = _good_clone_transcript()
    same_dilution.insert(
        6,
        {
            "type": "tool_call",
            "tool_name": "plate",
            "arguments": {
                "culture_id": "culture_001",
                "plate_id": "plate_002",
                "plating_id": "plating_002",
                "dilution_factor": 1.0,
                "volume_ul": 100,
            },
        },
    )
    same_dilution.insert(
        8,
        {
            "type": "tool_call",
            "tool_name": "count_colonies",
            "arguments": {
                "plating_id": "plating_002",
                "observed_colonies": 47,
                "status": "plated",
            },
        },
    )
    summed_answer = _good_clone_answer().replace(
        "Transformants observed: 200", "Transformants observed: 247"
    )
    assert score_clone_task_success(summed_answer, same_dilution) == 1.0

    same_dilution[6]["arguments"]["dilution_factor"] = 10.0
    assert score_clone_task_success(summed_answer, same_dilution) == 0.0


def test_clone_extreme_ratio_without_diagnosis_fails_troubleshooting():
    transcript = _good_clone_transcript()
    transcript[2]["arguments"]["vector_to_insert_molar_ratio"] = 50.0
    transcript[2]["arguments"]["status"] = "wrong_ratio"
    scores = score_clone_trajectory(
        final_answer=_good_clone_answer(),
        transcript=transcript,
        ground_truth_path=str(CLONE_GROUND_TRUTH_PATH),
    )
    assert scores["decision_scores"]["uses_reasonable_molar_ratio"] == 0.0
    assert scores["troubleshooting"] == 0.0


def test_screen_undersampling_without_diagnosis_scores_zero_troubleshooting():
    transcript = [
        {
            "type": "tool_call",
            "tool_name": "inspect_screening_plate",
            "arguments": {
                "status": "screening_plate_ready",
                "plate_id": "screen_plate_001",
            },
        },
        {
            "type": "tool_call",
            "tool_name": "run_colony_pcr",
            "arguments": {
                "plate_id": "screen_plate_001",
                "primer_pair": "M13/pUC flank primers",
                "screened_colony_ids": ["white_001", "white_003", "white_004"],
                "screened_colony_count": 3,
                "screening_strategy": "white_only",
                "cumulative_screened_white_colony_count": 3,
                "cumulative_confidence_pct": 78.4,
                "confirmed_recombinant_ids_cumulative": [],
                "confirmed_recombinant_ids_in_batch": [],
            },
        },
    ]
    answer = (
        "White colonies screened: 3\n"
        "Confirmed recombinant colonies: None\n"
        "Confidence achieved: 78.4%\n"
        "Interpretation: No recombinant colonies confirmed in this batch."
    )
    scores = score_screen_trajectory(
        final_answer=answer,
        transcript=transcript,
        ground_truth_path=str(SCREEN_GROUND_TRUTH_PATH),
    )
    assert scores["task_success"] == 0.0
    assert scores["decision_scores"]["reaches_confidence_threshold"] == 0.0
    assert scores["decision_scores"]["screens_at_least_six_white_colonies"] == 0.0
    assert scores["troubleshooting"] == 0.0


def _good_golden_gate_transcript():
    assembly_call = {
        "type": "tool_call",
        "tool_name": "golden_gate_assembly",
        "arguments": {
            "assembly_id": "assembly_001",
            "fragment_ids": [
                "gg_backbone",
                "gg_insert_promoter",
                "gg_insert_cds",
                "gg_insert_terminator",
            ],
            "fragment_count": 4,
            "enzyme_name": "BsaI",
            "enzyme_normalized": "bsai",
            "ligase_name": "T4 DNA ligase",
            "ligase_normalized": "t4 dna ligase",
            "buffer": "T4 DNA ligase buffer",
            "cycle_count": 30,
            "digest_temperature_c": 37.0,
            "ligate_temperature_c": 16.0,
            "final_digest_minutes": 5,
            "final_digest_temperature_c": 60.0,
            "output_fragment_id": "fragment_010",
            "status": "assembled",
            "effective_assembly_efficiency": 0.85,
            "expected_transformant_yield": 600.0,
        },
    }
    prepare = {
        "type": "tool_call",
        "tool_name": "prepare_media",
        "arguments": {
            "medium": "LB agar",
            "antibiotic": "ampicillin",
            "antibiotic_concentration_ug_ml": 100,
            "plate_count": 1,
            "plates": [
                {
                    "plate_id": "plate_001",
                    "medium": "LB agar",
                    "antibiotic": "ampicillin",
                    "antibiotic_concentration_ug_ml": 100,
                }
            ],
            "status": "prepared",
        },
    }
    transform_call = {
        "type": "tool_call",
        "tool_name": "transform_assembly",
        "arguments": {
            "assembly_id": "assembly_001",
            "culture_id": "culture_001",
            "status": "transformed",
            "assembly_status": "assembled",
            "effective_assembly_efficiency": 0.85,
        },
    }
    plate_call = {
        "type": "tool_call",
        "tool_name": "plate",
        "arguments": {
            "culture_id": "culture_001",
            "plate_id": "plate_001",
            "plating_id": "plating_001",
            "dilution_factor": 1.0,
            "volume_ul": 100,
            "observed_colonies": 120,
            "status": "plated",
            "countable_range_colonies": {"min": 25, "max": 250},
        },
    }
    count = {
        "type": "tool_call",
        "tool_name": "count_colonies",
        "arguments": {
            "plating_id": "plating_001",
            "observed_colonies": 120,
            "status": "plated",
            "countable_range_colonies": {"min": 25, "max": 250},
        },
    }
    return [assembly_call, prepare, transform_call, plate_call, count]


def _good_golden_gate_answer() -> str:
    return (
        "Type IIS enzyme: BsaI\n"
        "Ligase: T4 DNA ligase\n"
        "Digest temperature: 37 C\n"
        "Ligate temperature: 16 C\n"
        "Cycle count: 30\n"
        "Fragment count: 4\n"
        "Transformants observed: 120\n"
        "Interpretation: success"
    )


def test_good_golden_gate_trajectory_scores_high():
    scores = score_golden_gate_trajectory(
        final_answer=_good_golden_gate_answer(),
        transcript=_good_golden_gate_transcript(),
        ground_truth_path=str(GOLDEN_GATE_GROUND_TRUTH_PATH),
    )
    assert scores["task_success"] == 1.0
    assert scores["decision_quality"] == 1.0
    assert scores["troubleshooting"] == 1.0
    assert scores["overall"] >= 0.9


def test_golden_gate_wrong_enzyme_fails_decision_quality():
    transcript = _good_golden_gate_transcript()
    transcript[0]["arguments"]["enzyme_normalized"] = "ecori"
    transcript[0]["arguments"]["status"] = "wrong_enzyme"
    scores = score_golden_gate_trajectory(
        final_answer=_good_golden_gate_answer(),
        transcript=transcript,
        ground_truth_path=str(GOLDEN_GATE_GROUND_TRUTH_PATH),
    )
    assert scores["decision_scores"]["uses_type_iis_enzyme"] == 0.0
    assert scores["task_success"] == 0.0


def test_golden_gate_wrong_ligase_fails_decision_quality():
    transcript = _good_golden_gate_transcript()
    transcript[0]["arguments"]["ligase_normalized"] = "e. coli dna ligase"
    transcript[0]["arguments"]["status"] = "wrong_ligase"
    answer = _good_golden_gate_answer().replace("T4 DNA ligase", "E. coli DNA ligase")
    assert score_golden_gate_task_success(answer, transcript) == 0.0
    scores = score_golden_gate_trajectory(
        final_answer=answer,
        transcript=transcript,
        ground_truth_path=str(GOLDEN_GATE_GROUND_TRUTH_PATH),
    )
    assert scores["decision_scores"]["uses_t4_dna_ligase"] == 0.0


@pytest.mark.parametrize("keep_calls", (3, 4))
def test_golden_gate_requires_a_linked_plate_and_count_call(keep_calls):
    transcript = _good_golden_gate_transcript()[:keep_calls]
    answer = _good_golden_gate_answer().replace(
        "Transformants observed: 120",
        "Transformants observed: 0",
    )

    assert score_golden_gate_task_success(answer, transcript) == 0.0


@pytest.mark.parametrize(
    "replacement",
    (
        ("Type IIS enzyme: BsaI", "Type IIS enzyme: BsmBI"),
        ("Type IIS enzyme: BsaI", "Type IIS enzyme: BsaI-v2"),
        ("Type IIS enzyme: BsaI", "Type IIS enzyme: BsaI-HF"),
        ("Type IIS enzyme: BsaI", "Type IIS enzyme: BsaI-HFv3"),
        ("Ligase: T4 DNA ligase", "Ligase: T4 RNA ligase"),
        ("Digest temperature: 37 C", "Digest temperature: 0 C"),
        ("Ligate temperature: 16 C", "Ligate temperature: 99 C"),
        ("Cycle count: 30", "Cycle count: 999"),
        ("Fragment count: 4", "Fragment count: 3"),
        ("Transformants observed: 120", "Transformants observed: 121"),
        ("Interpretation: success", "Interpretation: failure"),
    ),
)
def test_golden_gate_rejects_report_fields_inconsistent_with_completed_path(replacement):
    old, new = replacement
    answer = _good_golden_gate_answer().replace(old, new)

    assert score_golden_gate_task_success(answer, _good_golden_gate_transcript()) == 0.0


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("buffer", "water"),
        ("buffer", "T4 DNA Ligase buffer (water)"),
        ("digest_temperature_c", 0.0),
        ("ligate_temperature_c", 99.0),
        ("cycle_count", 0),
        ("cycle_count", 999),
        ("final_digest_temperature_c", 80.0),
        ("final_digest_minutes", 0),
        ("output_fragment_id", None),
        ("enzyme_normalized", "bsmbi"),
        ("ligase_normalized", "t4 rna ligase"),
    ),
)
def test_golden_gate_scorer_independently_rejects_invalid_assembly_contract(
    field, value
):
    transcript = copy.deepcopy(_good_golden_gate_transcript())
    transcript[0]["arguments"][field] = value

    assert score_golden_gate_task_success(_good_golden_gate_answer(), transcript) == 0.0


def test_golden_gate_scorer_requires_transform_to_confirm_assembled_input():
    transcript = copy.deepcopy(_good_golden_gate_transcript())
    transcript[2]["arguments"]["assembly_status"] = "wrong_thermal_program"

    assert score_golden_gate_task_success(_good_golden_gate_answer(), transcript) == 0.0


@pytest.mark.parametrize(
    "buffer",
    (
        "T4 DNA Ligase Buffer (10X)",
        "1X T4 DNA Ligase Reaction Buffer",
        "ATP-containing T4 DNA ligase buffer",
    ),
)
def test_golden_gate_scorer_accepts_agent_visible_t4_buffer_aliases(buffer):
    transcript = copy.deepcopy(_good_golden_gate_transcript())
    transcript[0]["arguments"]["buffer"] = buffer

    assert score_golden_gate_task_success(_good_golden_gate_answer(), transcript) == 1.0


def test_golden_gate_scorer_accepts_exact_agent_visible_t4_buffer_reference():
    database_path = Path(__file__).resolve().parents[1] / "data" / "enzyme_database.json"
    database = json.loads(database_path.read_text())
    t4_ligase = next(entry for entry in database if entry["name"] == "T4 DNA ligase")
    transcript = copy.deepcopy(_good_golden_gate_transcript())
    transcript[0]["arguments"]["buffer"] = t4_ligase["buffer"]

    assert score_golden_gate_task_success(_good_golden_gate_answer(), transcript) == 1.0


def test_golden_gate_rejects_fractional_colony_counts_in_transcript():
    transcript = copy.deepcopy(_good_golden_gate_transcript())
    transcript[4]["arguments"]["observed_colonies"] = 120.4

    assert score_golden_gate_task_success(_good_golden_gate_answer(), transcript) == 0.0


@pytest.mark.parametrize(
    ("call_index", "field", "value"),
    (
        (2, "assembly_id", "assembly_unrelated"),
        (3, "culture_id", "culture_unrelated"),
        (4, "plating_id", "plating_unrelated"),
    ),
)
def test_golden_gate_rejects_unlinked_execution_paths(call_index, field, value):
    transcript = copy.deepcopy(_good_golden_gate_transcript())
    transcript[call_index]["arguments"][field] = value

    assert score_golden_gate_task_success(_good_golden_gate_answer(), transcript) == 0.0


@pytest.mark.parametrize("status", ("count_out_of_range", "selection_failed"))
def test_golden_gate_rejects_non_countable_plate_status(status):
    transcript = copy.deepcopy(_good_golden_gate_transcript())
    transcript[3]["arguments"]["status"] = status
    transcript[4]["arguments"]["status"] = status

    assert score_golden_gate_task_success(_good_golden_gate_answer(), transcript) == 0.0


def test_golden_gate_accepts_bsai_hfv2_report_for_bsai_family_path():
    transcript = copy.deepcopy(_good_golden_gate_transcript())
    transcript[0]["arguments"]["enzyme_name"] = "BsaI-HFv2"
    transcript[0]["arguments"]["enzyme_normalized"] = "bsai"
    answer = _good_golden_gate_answer().replace(
        "Type IIS enzyme: BsaI",
        "Type IIS enzyme: BsaI-HFv2",
    )

    assert score_golden_gate_task_success(answer, transcript) == 1.0


@pytest.mark.parametrize(
    ("executed_enzyme", "reported_enzyme"),
    (("BsaI", "BsaI-HFv2"), ("BsaI-HFv2", "BsaI")),
)
def test_golden_gate_report_must_match_the_executed_bsai_variant(
    executed_enzyme, reported_enzyme
):
    transcript = copy.deepcopy(_good_golden_gate_transcript())
    transcript[0]["arguments"]["enzyme_name"] = executed_enzyme
    answer = _good_golden_gate_answer().replace(
        "Type IIS enzyme: BsaI",
        f"Type IIS enzyme: {reported_enzyme}",
    )

    assert score_golden_gate_task_success(answer, transcript) == 0.0


def test_golden_gate_simulator_result_overrides_transform_input_alias():
    transcript = copy.deepcopy(_good_golden_gate_transcript())
    transform = transcript[2]
    transform["content"] = json.dumps(transform["arguments"])
    transform["arguments"] = {
        "assembly_id": "1",
        "heat_shock_seconds": 30,
        "recovery_minutes": 60,
        "outgrowth_media": "SOC",
    }

    assert score_golden_gate_task_success(_good_golden_gate_answer(), transcript) == 1.0


def test_golden_gate_rejects_reversed_causal_order():
    transcript = list(reversed(copy.deepcopy(_good_golden_gate_transcript())))

    assert score_golden_gate_task_success(_good_golden_gate_answer(), transcript) == 0.0


@pytest.mark.parametrize("observed_colonies", (0, 24, 251, 500))
def test_golden_gate_rejects_counts_outside_the_canonical_countable_range(
    observed_colonies,
):
    transcript = copy.deepcopy(_good_golden_gate_transcript())
    transcript[4]["arguments"]["observed_colonies"] = observed_colonies
    answer = _good_golden_gate_answer().replace(
        "Transformants observed: 120",
        f"Transformants observed: {observed_colonies}",
    )

    assert score_golden_gate_task_success(answer, transcript) == 0.0


@pytest.mark.parametrize(("call_index", "value"), ((3, None), (4, None), (4, {"min": 0, "max": 500})))
def test_golden_gate_rejects_missing_or_noncanonical_countable_ranges(call_index, value):
    transcript = copy.deepcopy(_good_golden_gate_transcript())
    if value is None:
        transcript[call_index]["arguments"].pop("countable_range_colonies")
    else:
        transcript[call_index]["arguments"]["countable_range_colonies"] = value

    assert score_golden_gate_task_success(_good_golden_gate_answer(), transcript) == 0.0


@pytest.mark.parametrize("observed_colonies", (25, 250))
def test_golden_gate_accepts_canonical_countable_range_boundaries(observed_colonies):
    transcript = copy.deepcopy(_good_golden_gate_transcript())
    transcript[4]["arguments"]["observed_colonies"] = observed_colonies
    answer = _good_golden_gate_answer().replace(
        "Transformants observed: 120",
        f"Transformants observed: {observed_colonies}",
    )

    assert score_golden_gate_task_success(answer, transcript) == 1.0


@pytest.mark.parametrize("bad_first", (True, False))
def test_golden_gate_ampicillin_retry_policy_is_order_independent(bad_first):
    transcript = copy.deepcopy(_good_golden_gate_transcript())
    good_prepare = transcript[1]
    bad_prepare = copy.deepcopy(good_prepare)
    bad_prepare["arguments"]["antibiotic_concentration_ug_ml"] = 50
    bad_prepare["arguments"]["plates"][0]["antibiotic_concentration_ug_ml"] = 50
    bad_prepare["arguments"]["plates"][0]["plate_id"] = "plate_002"
    prepares = [bad_prepare, good_prepare] if bad_first else [good_prepare, bad_prepare]
    transcript = [transcript[0], *prepares, *transcript[2:]]

    scores = score_golden_gate_trajectory(
        final_answer=_good_golden_gate_answer(),
        transcript=transcript,
        ground_truth_path=str(GOLDEN_GATE_GROUND_TRUTH_PATH),
    )

    assert scores["decision_scores"]["ampicillin_selection_100"] == 0.0


def test_golden_gate_completed_path_survives_a_later_untransformed_failed_retry():
    transcript = copy.deepcopy(_good_golden_gate_transcript())
    failed_retry = copy.deepcopy(transcript[0])
    failed_retry["arguments"].update(
        {
            "assembly_id": "assembly_002",
            "enzyme_name": "BsmBI-v2",
            "enzyme_normalized": "bsmbi",
            "status": "wrong_enzyme",
        }
    )
    transcript.append(failed_retry)

    scores = score_golden_gate_trajectory(
        final_answer=_good_golden_gate_answer(),
        transcript=transcript,
        ground_truth_path=str(GOLDEN_GATE_GROUND_TRUTH_PATH),
    )

    assert scores["task_success"] == 1.0
    assert scores["decision_quality"] < 1.0


@pytest.mark.parametrize(
    ("reference_calls", "expected_efficiency"),
    ((3, 1.0), (10, 0.5), (11, 0.0)),
)
def test_golden_gate_efficiency_budget_includes_required_reference_calls(
    reference_calls, expected_efficiency
):
    lookup = {
        "type": "tool_call",
        "tool_name": "lookup_enzyme",
        "arguments": {"enzyme_name": "BsaI"},
    }
    transcript = [copy.deepcopy(lookup) for _ in range(reference_calls)]
    transcript.extend(_good_golden_gate_transcript())
    scores = score_golden_gate_trajectory(
        final_answer=_good_golden_gate_answer(),
        transcript=transcript,
        ground_truth_path=str(GOLDEN_GATE_GROUND_TRUTH_PATH),
    )

    assert scores["efficiency"] == expected_efficiency


def _good_gibson_transcript():
    gibson_call = {
        "type": "tool_call",
        "tool_name": "gibson_assembly",
        "arguments": {
            "fragment_ids": ["gibson_backbone_linear", "gibson_insert_pcr"],
            "master_mix_name": "Gibson Assembly Master Mix",
            "temperature_c": 50.0,
            "duration_minutes": 15,
            "overlap_length_bp": 20,
        },
        "content": json.dumps(
            {
                "gibson_id": "gibson_001",
                "fragment_ids": ["gibson_backbone_linear", "gibson_insert_pcr"],
                "fragment_count": 2,
                "master_mix_name": "Gibson Assembly Master Mix",
                "master_mix_normalized": "gibson assembly master mix",
                "master_mix_canonical": "Gibson Assembly Master Mix",
                "temperature_c": 50.0,
                "duration_minutes": 15,
                "overlap_length_bp": 20,
                "output_fragment_id": "fragment_020",
                "status": "assembled",
                "effective_assembly_efficiency": 0.80,
                "expected_transformant_yield": 500.0,
            }
        ),
    }
    transform_call = {
        "type": "tool_call",
        "tool_name": "transform_gibson",
        "arguments": {
            "gibson_id": "gibson_001",
            "heat_shock_seconds": 30,
            "recovery_minutes": 60,
            "outgrowth_media": "SOC",
            "shaking": True,
            "ice_incubation_minutes": 30,
        },
        "content": json.dumps(
            {
                "gibson_id": "gibson_001",
                "culture_id": "culture_001",
                "gibson_status": "assembled",
                "output_fragment_id": "fragment_020",
                "status": "transformed",
                "effective_assembly_efficiency": 0.80,
                "expected_transformant_yield": 500.0,
                "heat_shock_seconds": 30,
                "recovery_minutes": 60,
                "outgrowth_media": "SOC",
                "shaking": True,
                "ice_incubation_minutes": 30,
            }
        ),
    }
    prepare = {
        "type": "tool_call",
        "tool_name": "prepare_media",
        "arguments": {
            "medium": "LB agar",
            "antibiotic": "ampicillin",
            "antibiotic_concentration_ug_ml": 100,
            "plate_count": 1,
        },
        "content": json.dumps(
            {
                "status": "prepared",
                "media_id": "media_001",
                "medium": "LB agar",
                "antibiotic": "ampicillin",
                "antibiotic_concentration_ug_ml": 100,
                "plate_count": 1,
                "plates": [
                    {
                        "plate_id": "plate_001",
                        "medium": "LB agar",
                        "antibiotic": "ampicillin",
                        "antibiotic_concentration_ug_ml": 100,
                    }
                ],
            }
        ),
    }
    plate_call = {
        "type": "tool_call",
        "tool_name": "plate",
        "arguments": {
            "culture_id": "culture_001",
            "plate_id": "plate_001",
            "dilution_factor": 1.0,
            "volume_ul": 100,
        },
        "content": json.dumps(
            {
                "plating_id": "plating_001",
                "culture_id": "culture_001",
                "plate_id": "plate_001",
                "dilution_factor": 1.0,
                "volume_ul": 100,
                "status": "plated",
                "countable_range_colonies": {"min": 25, "max": 250},
                "warnings": [],
            }
        ),
    }
    count = {
        "type": "tool_call",
        "tool_name": "count_colonies",
        "arguments": {"plating_id": "plating_001"},
        "content": json.dumps(
            {
                "plating_id": "plating_001",
                "observed_colonies": 120,
                "status": "plated",
                "dilution_factor": 1.0,
                "volume_ul": 100,
                "countable_range_colonies": {"min": 25, "max": 250},
                "warnings": [],
            }
        ),
    }
    return [gibson_call, transform_call, prepare, plate_call, count]


def _gibson_observation(call):
    return json.loads(call["content"])


def _update_gibson_observation(call, **updates):
    observation = _gibson_observation(call)
    observation.update(updates)
    call["content"] = json.dumps(observation)


def _good_gibson_answer(*, transformants=120) -> str:
    return (
        "Assembly method: Gibson\n"
        "Master mix: Gibson Assembly Master Mix\n"
        "Temperature: 50 C\n"
        "Duration: 15 min\n"
        "Fragment count: 2\n"
        "Overlap length: 20 bp\n"
        f"Transformants observed: {transformants}\n"
        "Interpretation: success"
    )


def _score_gibson_task(transcript, final_answer=None):
    calls = transcript
    return score_gibson_task_success(final_answer or _good_gibson_answer(), calls)


def test_good_gibson_trajectory_scores_high():
    scores = score_gibson_trajectory(
        final_answer=_good_gibson_answer(),
        transcript=_good_gibson_transcript(),
        ground_truth_path=str(GIBSON_GROUND_TRUTH_PATH),
    )
    assert scores["task_success"] == 1.0
    assert scores["decision_quality"] == 1.0
    assert scores["overall"] >= 0.9


@pytest.mark.parametrize(
    "method",
    (
        "Gibson",
        "Gibson Assembly",
        "Gibson isothermal assembly",
        "Gibson overlap assembly",
        "Gibson isothermal overlap assembly",
        "Isothermal Gibson assembly",
        "Isothermal Gibson overlap assembly",
    ),
)
def test_gibson_report_accepts_explicit_method_aliases(method):
    answer = _good_gibson_answer().replace("Assembly method: Gibson", f"Assembly method: {method}")

    assert _score_gibson_task(_good_gibson_transcript(), answer) == 1.0


@pytest.mark.parametrize(
    "method",
    (
        "not Gibson",
        "not Gibson Assembly",
        "Gibson Assembly failed",
        "Gibson Assembly Master Mix",
        "isothermal overlap assembly",
        "Golden Gate",
    ),
)
def test_gibson_report_rejects_unallowlisted_or_negated_method_labels(method):
    answer = _good_gibson_answer().replace("Assembly method: Gibson", f"Assembly method: {method}")

    assert _score_gibson_task(_good_gibson_transcript(), answer) == 0.0


def test_gibson_real_simulator_payload_completes_the_scorer_contract():
    state = create_lab_state(sample_id="gibson-scorer-integration", seed=1)
    substrates = list_gibson_substrates(state=state)
    assembly_arguments = {
        "fragment_ids": ["gibson_backbone_linear", "gibson_insert_pcr"],
        "master_mix_name": "Gibson Assembly Master Mix",
        "temperature_c": 50.0,
        "duration_minutes": 15,
        "overlap_length_bp": 20,
    }
    assembly = gibson_assembly(state=state, **assembly_arguments)
    transform_arguments = {
        "gibson_id": assembly["gibson_id"],
        "heat_shock_seconds": 30,
        "recovery_minutes": 60,
        "outgrowth_media": "SOC",
        "shaking": True,
        "ice_incubation_minutes": 30,
    }
    transformed = transform_gibson(state=state, **transform_arguments)
    prepare_arguments = {
        "medium": "LB agar",
        "antibiotic": "ampicillin",
        "antibiotic_concentration_ug_ml": 100,
        "plate_count": 1,
    }
    prepared = prepare_media(state=state, **prepare_arguments)
    plate_arguments = {
        "culture_id": transformed["culture_id"],
        "plate_id": prepared["plates"][0]["plate_id"],
        "dilution_factor": 1.0,
        "volume_ul": 100.0,
    }
    plated = plate(state=state, **plate_arguments)
    count_arguments = {"plating_id": plated["plating_id"]}
    counted = count_colonies(state=state, **count_arguments)

    transcript = [
        {
            "type": "tool_call",
            "tool_name": name,
            "arguments": arguments,
            "content": json.dumps(observation),
        }
        for name, arguments, observation in (
            ("list_gibson_substrates", {}, substrates),
            ("gibson_assembly", assembly_arguments, assembly),
            ("transform_gibson", transform_arguments, transformed),
            ("prepare_media", prepare_arguments, prepared),
            ("plate", plate_arguments, plated),
            ("count_colonies", count_arguments, counted),
        )
    ]
    answer = _good_gibson_answer(transformants=counted["observed_colonies"])

    assert score_gibson_task_success(answer, transcript) == 1.0


def test_gibson_wrong_master_mix_triggers_troubleshooting_requirement():
    transcript = _good_gibson_transcript()
    _update_gibson_observation(
        transcript[0],
        master_mix_name="T4 DNA ligase buffer",
        master_mix_normalized="t4 dna ligase buffer",
        status="wrong_master_mix",
        output_fragment_id=None,
    )
    scores = score_gibson_trajectory(
        final_answer=_good_gibson_answer(),
        transcript=transcript,
        ground_truth_path=str(GIBSON_GROUND_TRUTH_PATH),
    )
    assert scores["troubleshooting"] < 1.0
    assert scores["task_success"] == 0.0


def test_gibson_troubleshooting_scores_every_triggered_failure_reason():
    transcript = _good_gibson_transcript()
    _update_gibson_observation(
        transcript[0],
        master_mix_name="water",
        master_mix_canonical=None,
        temperature_c=48.0,
        duration_minutes=14,
        overlap_length_bp=19,
        status="wrong_master_mix",
        output_fragment_id=None,
        failure_reasons=[
            "wrong_master_mix",
            "wrong_temperature",
            "wrong_duration",
            "wrong_overlap_length",
        ],
    )
    answer = (
        f"{_good_gibson_answer()}\n"
        "The master mix name is unsupported; use Gibson Assembly Master Mix, "
        "NEBuilder HiFi DNA Assembly Master Mix, or the exact ISO buffer + T5 "
        "exonuclease + Phusion polymerase + Taq DNA ligase formulation."
    )
    scores = score_gibson_trajectory(
        final_answer=answer,
        transcript=transcript,
        ground_truth_path=str(GIBSON_GROUND_TRUTH_PATH),
    )

    assert scores["task_success"] == 0.0
    assert scores["troubleshooting"] == pytest.approx(0.25)


@pytest.mark.parametrize(
    ("missing_index", "reported_transformants"),
    (
        (0, 120),
        (1, 120),
        (2, 120),
        (3, 120),
        (4, 0),
    ),
    ids=("assembly", "transform", "prepared-plate", "plating", "count"),
)
def test_gibson_rejects_incomplete_causal_paths(missing_index, reported_transformants):
    transcript = _good_gibson_transcript()
    transcript.pop(missing_index)
    answer = _good_gibson_answer(transformants=reported_transformants)
    assert _score_gibson_task(transcript, answer) == 0.0


@pytest.mark.parametrize(
    ("call_index", "field", "unrelated_id"),
    (
        (1, "gibson_id", "gibson_unrelated"),
        (1, "output_fragment_id", "fragment_unrelated"),
        (3, "culture_id", "culture_unrelated"),
        (3, "plate_id", "plate_unrelated"),
        (4, "plating_id", "plating_unrelated"),
    ),
    ids=(
        "transform-to-assembly",
        "transform-to-output",
        "plate-to-culture",
        "plate-to-media",
        "count-to-plating",
    ),
)
def test_gibson_rejects_unlinked_causal_paths(call_index, field, unrelated_id):
    transcript = _good_gibson_transcript()
    transcript[call_index]["arguments"][field] = unrelated_id
    _update_gibson_observation(transcript[call_index], **{field: unrelated_id})
    assert _score_gibson_task(transcript) == 0.0


def test_gibson_rejects_reversed_causal_path():
    transcript = list(reversed(_good_gibson_transcript()))
    assert _score_gibson_task(transcript) == 0.0


@pytest.mark.parametrize(
    ("call_index", "status"),
    (
        (1, "error"),
        (1, "selection_failed"),
        (2, "error"),
        (3, "selection_failed"),
        (4, "selection_failed"),
        (4, "count_out_of_range"),
    ),
    ids=(
        "transform-error",
        "transform-selection-failed",
        "prepare-error",
        "plate-selection-failed",
        "count-selection-failed",
        "count-out-of-range",
    ),
)
def test_gibson_rejects_error_statuses_in_causal_path(call_index, status):
    transcript = _good_gibson_transcript()
    _update_gibson_observation(transcript[call_index], status=status)
    assert _score_gibson_task(transcript) == 0.0


def test_gibson_rejects_transform_of_failed_assembly():
    transcript = _good_gibson_transcript()
    _update_gibson_observation(transcript[1], gibson_status="wrong_master_mix")
    assert _score_gibson_task(transcript) == 0.0


def test_gibson_uses_result_id_over_transform_input_alias():
    transcript = _good_gibson_transcript()
    transcript[1]["arguments"]["gibson_id"] = "1"
    assert _score_gibson_task(transcript) == 1.0


def test_gibson_result_failure_overrides_forged_success_arguments():
    transcript = _good_gibson_transcript()
    transcript[0]["arguments"].update(
        {
            "status": "assembled",
            "gibson_id": "gibson_001",
            "output_fragment_id": "fragment_forged",
        }
    )
    _update_gibson_observation(
        transcript[0],
        status="wrong_master_mix",
        output_fragment_id=None,
    )
    assert _score_gibson_task(transcript) == 0.0


def test_gibson_prepare_result_error_overrides_valid_input_arguments():
    transcript = _good_gibson_transcript()
    _update_gibson_observation(transcript[2], status="error", plates=[])
    assert _score_gibson_task(transcript) == 0.0


@pytest.mark.parametrize(
    "updates",
    (
        {"fragment_ids": ["gibson_backbone_linear", "gibson_backbone_linear"]},
        {"fragment_count": 3},
        {"master_mix_name": "water", "master_mix_normalized": "water"},
        {"temperature_c": 0.0},
        {"duration_minutes": 0},
        {"overlap_length_bp": 80},
        {"output_fragment_id": None},
    ),
    ids=(
        "duplicate-fragment-ids",
        "wrong-fragment-count",
        "wrong-master-mix",
        "wrong-temperature",
        "wrong-duration",
        "wrong-overlap",
        "missing-output-product",
    ),
)
def test_gibson_rejects_invalid_assembly_result_contract(updates):
    transcript = _good_gibson_transcript()
    _update_gibson_observation(transcript[0], **updates)
    assert _score_gibson_task(transcript) == 0.0


@pytest.mark.parametrize(
    ("old", "new"),
    (
        ("Assembly method: Gibson", "Assembly method: Golden Gate"),
        ("Master mix: Gibson Assembly Master Mix", "Master mix: water"),
        ("Temperature: 50 C", "Temperature: 0 C"),
        ("Duration: 15 min", "Duration: 999 min"),
        ("Fragment count: 2", "Fragment count: 3"),
        ("Overlap length: 20 bp", "Overlap length: 80 bp"),
        ("Transformants observed: 120", "Transformants observed: 121"),
        (
            "Interpretation: success",
            "Interpretation: No assembly succeeded; the reaction failed.",
        ),
    ),
    ids=(
        "method",
        "master-mix",
        "temperature",
        "duration",
        "fragment-count",
        "overlap",
        "transformants",
        "negated-interpretation",
    ),
)
def test_gibson_report_must_bind_to_completed_path(old, new):
    answer = _good_gibson_answer().replace(old, new)
    assert _score_gibson_task(_good_gibson_transcript(), answer) == 0.0


def test_gibson_report_requires_assembly_method_field():
    answer = _good_gibson_answer().replace("Assembly method: Gibson\n", "")
    assert _score_gibson_task(_good_gibson_transcript(), answer) == 0.0


def test_gibson_report_rejects_fractional_colony_count():
    answer = _good_gibson_answer().replace(
        "Transformants observed: 120", "Transformants observed: 120.5"
    )
    assert _score_gibson_task(_good_gibson_transcript(), answer) == 0.0


@pytest.mark.parametrize(
    "duplicate_line",
    (
        "Assembly method: Golden Gate",
        "Master mix: water",
        "Temperature: 0 C",
        "Duration: 999 min",
        "Fragment count: 3",
        "Overlap length: 80 bp",
        "Transformants observed: 121",
        "Interpretation: No assembly succeeded; the reaction failed.",
    ),
)
def test_gibson_report_rejects_contradictory_duplicate_fields(duplicate_line):
    answer = f"{_good_gibson_answer()}\n{duplicate_line}"
    assert _score_gibson_task(_good_gibson_transcript(), answer) == 0.0


@pytest.mark.parametrize("observed_colonies", (0, 24, 251, 500))
def test_gibson_rejects_out_of_range_colony_counts(observed_colonies):
    transcript = _good_gibson_transcript()
    _update_gibson_observation(
        transcript[4], observed_colonies=observed_colonies, status="count_out_of_range"
    )
    answer = _good_gibson_answer(transformants=observed_colonies)
    assert _score_gibson_task(transcript, answer) == 0.0


@pytest.mark.parametrize("observed_colonies", (25, 250))
def test_gibson_accepts_inclusive_colony_count_boundaries(observed_colonies):
    transcript = _good_gibson_transcript()
    _update_gibson_observation(transcript[4], observed_colonies=observed_colonies)
    answer = _good_gibson_answer(transformants=observed_colonies)
    assert _score_gibson_task(transcript, answer) == 1.0


@pytest.mark.parametrize("call_index", (3, 4), ids=("plating", "count"))
def test_gibson_requires_canonical_countable_range_metadata(call_index):
    transcript = _good_gibson_transcript()
    _update_gibson_observation(
        transcript[call_index], countable_range_colonies={"min": 1, "max": 999}
    )
    assert _score_gibson_task(transcript) == 0.0


@pytest.mark.parametrize("call_index", (3, 4), ids=("plating", "count"))
def test_gibson_requires_countable_range_metadata(call_index):
    transcript = _good_gibson_transcript()
    observation = _gibson_observation(transcript[call_index])
    observation.pop("countable_range_colonies")
    transcript[call_index]["content"] = json.dumps(observation)
    assert _score_gibson_task(transcript) == 0.0


def test_gibson_rejects_fractional_observed_colony_count():
    transcript = _good_gibson_transcript()
    _update_gibson_observation(transcript[4], observed_colonies=120.4)
    assert _score_gibson_task(transcript) == 0.0


def test_gibson_completed_path_survives_later_failed_retry():
    transcript = _good_gibson_transcript()
    failed_retry = copy.deepcopy(transcript[0])
    failed_retry["arguments"]["master_mix_name"] = "water"
    _update_gibson_observation(
        failed_retry,
        gibson_id="gibson_002",
        master_mix_name="water",
        master_mix_normalized="water",
        status="wrong_master_mix",
        output_fragment_id=None,
    )
    transcript.append(failed_retry)
    assert _score_gibson_task(transcript) == 1.0


def test_gibson_unrelated_later_count_does_not_contaminate_completed_path():
    transcript = _good_gibson_transcript()
    unrelated_count = copy.deepcopy(transcript[4])
    unrelated_count["arguments"]["plating_id"] = "plating_unrelated"
    _update_gibson_observation(
        unrelated_count,
        plating_id="plating_unrelated",
        observed_colonies=500,
        status="count_out_of_range",
    )
    transcript.append(unrelated_count)
    assert _score_gibson_task(transcript) == 1.0
    assert _score_gibson_task(transcript, _good_gibson_answer(transformants=500)) == 0.0


def test_gibson_report_does_not_hybridize_with_untransformed_retry():
    transcript = _good_gibson_transcript()
    untransformed_retry = copy.deepcopy(transcript[0])
    untransformed_retry["arguments"].update(
        {
            "master_mix_name": "NEBuilder HiFi",
            "duration_minutes": 30,
        }
    )
    _update_gibson_observation(
        untransformed_retry,
        gibson_id="gibson_002",
        master_mix_name="NEBuilder HiFi",
        master_mix_normalized="nebuilder hifi",
        master_mix_canonical="NEBuilder HiFi DNA Assembly Master Mix",
        duration_minutes=30,
        output_fragment_id="fragment_021",
    )
    transcript.append(untransformed_retry)

    answer = (
        _good_gibson_answer()
        .replace("Master mix: Gibson Assembly Master Mix", "Master mix: NEBuilder HiFi")
        .replace("Duration: 15 min", "Duration: 30 min")
    )
    assert _score_gibson_task(transcript, answer) == 0.0
    assert _score_gibson_task(transcript) == 1.0


@pytest.mark.parametrize("bad_prepare_first", (False, True), ids=("good-then-bad", "bad-then-good"))
def test_gibson_ampicillin_decision_audits_all_attempts_order_independently(bad_prepare_first):
    transcript = _good_gibson_transcript()
    bad_prepare = copy.deepcopy(transcript[2])
    bad_prepare["arguments"]["antibiotic_concentration_ug_ml"] = 50
    _update_gibson_observation(
        bad_prepare,
        media_id="media_bad",
        antibiotic_concentration_ug_ml=50,
        plates=[
            {
                "plate_id": "plate_bad",
                "medium": "LB agar",
                "antibiotic": "ampicillin",
                "antibiotic_concentration_ug_ml": 50,
            }
        ],
    )
    insert_at = 2 if bad_prepare_first else 3
    transcript.insert(insert_at, bad_prepare)
    scores = score_gibson_trajectory(
        final_answer=_good_gibson_answer(),
        transcript=transcript,
        ground_truth_path=str(GIBSON_GROUND_TRUTH_PATH),
    )
    assert scores["task_success"] == 1.0
    assert scores["decision_scores"]["gibson_ampicillin_selection_100"] == 0.0


def _good_miniprep_arguments(**updates):
    arguments = {
        "culture_id": MINIPREP_SOURCE_CULTURE_ID,
        "culture_volume_ml": 5.0,
        "lysis_buffer_sequence": "P1,P2,N3",
        "lysis_duration_min": 3,
        "purification_method": "QIAprep silica spin column",
        "elution_volume_ul": 50.0,
    }
    arguments.update(updates)
    return arguments


def _good_miniprep_observation(**updates):
    observation = {
        "status": "prepared",
        "preparation_accepted": True,
        "failure_reasons": [],
        "miniprep_id": "miniprep_001",
        "culture_id": MINIPREP_SOURCE_CULTURE_ID,
        "culture_volume_ml": 5.0,
        "lysis_buffer_sequence": "P1,P2,N3",
        "lysis_buffer_sequence_canonical": "P1,P2,N3",
        "lysis_duration_min": 3,
        "purification_method": "QIAprep silica spin column",
        "purification_method_canonical": "QIAprep silica spin column",
        "elution_volume_ul": 50.0,
        "final_concentration_ng_ul": 200.0,
        "a260_a280_ratio": 1.8,
        "total_yield_ug": 10.0,
        "source_culture_remaining_volume_ml": 0.0,
    }
    observation.update(updates)
    return observation


def _miniprep_call_pair(*, arguments=None, observation=None, call_id="call_miniprep"):
    if arguments is None:
        arguments = _good_miniprep_arguments()
    if observation is None:
        observation = _good_miniprep_observation()
    return [
        {
            "role": "assistant",
            "tool_calls": [
                {
                    "id": call_id,
                    "function": "perform_miniprep",
                    "arguments": copy.deepcopy(arguments),
                }
            ],
        },
        {
            "role": "tool",
            "tool_call_id": call_id,
            "function": "perform_miniprep",
            "content": json.dumps(observation),
        },
    ]


def _good_miniprep_transcript():
    return _miniprep_call_pair()


def _good_miniprep_answer() -> str:
    return (
        "Culture ID: miniprep_culture_high_copy_001\n"
        "Culture volume: 5 mL\n"
        "Lysis buffer sequence: P1,P2,N3\n"
        "Lysis duration: 3 min\n"
        "Purification method: QIAprep silica spin column\n"
        "Elution volume: 50 uL\n"
        "Plasmid concentration: 200.0 ng/uL\n"
        "A260/A280: 1.80\n"
        "Total yield: 10.0 ug\n"
        "Interpretation: success\n"
        "Diagnosis: none"
    )


def _replace_report_line(answer: str, prefix: str, replacement: str) -> str:
    return "\n".join(
        replacement if line.startswith(prefix) else line
        for line in answer.splitlines()
    )


def test_good_miniprep_trajectory_scores_high():
    scores = score_miniprep_trajectory(
        final_answer=_good_miniprep_answer(),
        transcript=_good_miniprep_transcript(),
        ground_truth_path=str(MINIPREP_GROUND_TRUTH_PATH),
    )
    assert scores["task_success"] == 1.0
    assert scores["decision_quality"] == 1.0
    assert scores["overall"] >= 0.9


def test_real_miniprep_output_in_paired_transcript_scores_high():
    state = create_lab_state(sample_id="miniprep-real-output", seed=1)
    initialize_miniprep_source_culture(state)
    arguments = _good_miniprep_arguments()
    observation = perform_miniprep(state=state, **arguments)

    scores = _score_miniprep(
        _good_miniprep_answer(),
        _miniprep_call_pair(arguments=arguments, observation=observation),
    )

    assert scores["task_success"] == 1.0
    assert scores["decision_quality"] == 1.0


def test_miniprep_accepts_supported_100_ul_elution_but_reserves_optimal_decision_credit():
    arguments = _good_miniprep_arguments(elution_volume_ul=100.0)
    observation = _good_miniprep_observation(
        elution_volume_ul=100.0,
        final_concentration_ng_ul=100.0,
    )
    answer = _replace_report_line(
        _good_miniprep_answer(), "Elution volume:", "Elution volume: 100 uL"
    )
    answer = _replace_report_line(
        answer,
        "Plasmid concentration:",
        "Plasmid concentration: 100.0 ng/uL",
    )

    scores = _score_miniprep(
        answer,
        _miniprep_call_pair(arguments=arguments, observation=observation),
    )

    assert scores["task_success"] == 1.0
    assert scores["decision_quality"] == pytest.approx(0.75)


def test_miniprep_requires_exact_report_of_submitted_culture_volume():
    arguments = _good_miniprep_arguments(culture_volume_ml=1.0)
    observation = _good_miniprep_observation(
        culture_volume_ml=1.0,
        total_yield_ug=2.0,
        final_concentration_ng_ul=40.0,
        source_culture_remaining_volume_ml=4.0,
    )
    answer = _replace_report_line(
        _good_miniprep_answer(), "Culture volume:", "Culture volume: 0.9 mL"
    )
    answer = _replace_report_line(
        answer,
        "Plasmid concentration:",
        "Plasmid concentration: 40.0 ng/uL",
    )
    answer = _replace_report_line(answer, "Total yield:", "Total yield: 2.0 ug")

    scores = _score_miniprep(
        answer,
        _miniprep_call_pair(arguments=arguments, observation=observation),
    )

    assert scores["task_success"] == 0.0


def test_miniprep_requires_exact_report_of_submitted_elution_volume():
    answer = _replace_report_line(
        _good_miniprep_answer(), "Elution volume:", "Elution volume: 49.9 uL"
    )

    scores = _score_miniprep(answer, _good_miniprep_transcript())

    assert scores["task_success"] == 0.0


def _score_miniprep(answer, transcript):
    return score_miniprep_trajectory(
        final_answer=answer,
        transcript=transcript,
        ground_truth_path=str(MINIPREP_GROUND_TRUTH_PATH),
    )


def test_miniprep_rejects_each_inconsistent_or_nonsensical_report_field():
    replacements = {
        "Culture ID:": "Culture ID: unknown_culture",
        "Culture volume:": "Culture volume: 999 mL",
        "Lysis buffer sequence:": "Lysis buffer sequence: P1,P2,P3",
        "Lysis duration:": "Lysis duration: 999 min",
        "Purification method:": "Purification method: boiling",
        "Elution volume:": "Elution volume: 1 uL",
        "Plasmid concentration:": "Plasmid concentration: 999 ng/uL",
        "A260/A280:": "A260/A280: 9.99",
        "Total yield:": "Total yield: 999 ug",
        "Interpretation:": "Interpretation: No plasmid was prepared.",
        "Diagnosis:": "Diagnosis: wrong buffer sequence",
    }
    for prefix, replacement in replacements.items():
        scores = _score_miniprep(
            _replace_report_line(_good_miniprep_answer(), prefix, replacement),
            _good_miniprep_transcript(),
        )
        assert scores["task_success"] == 0.0, prefix


def test_miniprep_accepts_equivalent_punctuation_and_spacing():
    answer = _replace_report_line(
        _good_miniprep_answer(),
        "Lysis buffer sequence:",
        "Lysis buffer sequence: P1 -> P2 -> N3",
    )
    answer = _replace_report_line(
        answer,
        "Purification method:",
        "Purification method: QIAprep 2.0 silica-membrane spin-column",
    )
    scores = _score_miniprep(answer, _good_miniprep_transcript())
    assert scores["task_success"] == 1.0


def test_miniprep_rejects_unqualified_generic_silica_method_report():
    answer = _replace_report_line(
        _good_miniprep_answer(),
        "Purification method:",
        "Purification method: silica column",
    )

    scores = _score_miniprep(answer, _good_miniprep_transcript())

    assert scores["task_success"] == 0.0


@pytest.mark.parametrize("micro", ("µ", "μ"))
def test_miniprep_accepts_unicode_micro_symbols(micro):
    answer = _good_miniprep_answer().replace("uL", "{}L".format(micro))
    answer = answer.replace("ug", "{}g".format(micro))

    scores = _score_miniprep(answer, _good_miniprep_transcript())

    assert scores["task_success"] == 1.0


def test_miniprep_rejects_success_label_with_contradictory_interpretation():
    answer = _replace_report_line(
        _good_miniprep_answer(),
        "Interpretation:",
        "Interpretation: success; the plasmid is not pure and the preparation did not succeed.",
    )
    scores = _score_miniprep(answer, _good_miniprep_transcript())
    assert scores["task_success"] == 0.0


@pytest.mark.parametrize(
    "duplicate",
    (
        "Culture ID: another_culture",
        "Culture volume: 4 mL",
        "Lysis buffer sequence: P1,P2,P3",
        "Lysis duration: 4 min",
        "Purification method: anion exchange column",
        "Elution volume: 100 uL",
        "Plasmid concentration: 100 ng/uL",
        "A260/A280: 2.10",
        "Total yield: 5 ug",
        "Interpretation: failure",
        "Diagnosis: wrong buffer sequence",
    ),
)
def test_miniprep_rejects_duplicate_or_contradictory_report_fields(duplicate):
    scores = _score_miniprep(
        _good_miniprep_answer() + "\n" + duplicate,
        _good_miniprep_transcript(),
    )

    assert scores["task_success"] == 0.0


@pytest.mark.parametrize(
    ("prefix", "replacement"),
    (
        ("Culture ID:", "Culture ID: miniprep_culture_high_copy_001 trailing"),
        ("Culture volume:", "Culture volume: 5 mL trailing"),
        ("Lysis buffer sequence:", "Lysis buffer sequence: P1,P2,N3 trailing"),
        ("Lysis duration:", "Lysis duration: 3 min trailing"),
        ("Purification method:", "Purification method: QIAprep silica spin column trailing"),
        ("Elution volume:", "Elution volume: 50 uL trailing"),
        ("Plasmid concentration:", "Plasmid concentration: 200 ng/uL trailing"),
        ("A260/A280:", "A260/A280: 1.8 trailing"),
        ("Total yield:", "Total yield: 10 ug trailing"),
        ("Interpretation:", "Interpretation: success trailing"),
        ("Diagnosis:", "Diagnosis: none trailing"),
    ),
)
def test_miniprep_rejects_trailing_junk_on_every_schema_field(prefix, replacement):
    scores = _score_miniprep(
        _replace_report_line(_good_miniprep_answer(), prefix, replacement),
        _good_miniprep_transcript(),
    )

    assert scores["task_success"] == 0.0


def test_miniprep_output_overrides_forged_result_fields_in_arguments():
    forged_arguments = _good_miniprep_arguments(
        miniprep_id="miniprep_001",
        status="prepared",
        preparation_accepted=True,
        failure_reasons=[],
        final_concentration_ng_ul=200.0,
        a260_a280_ratio=1.8,
        total_yield_ug=10.0,
        lysis_buffer_sequence_canonical="P1,P2,N3",
        purification_method_canonical="QIAprep silica spin column",
    )
    failed_output = _good_miniprep_observation(
        status=MINIPREP_FAILURE_WRONG_BUFFER,
        preparation_accepted=False,
        failure_reasons=[MINIPREP_FAILURE_WRONG_BUFFER],
        final_concentration_ng_ul=80.0,
        a260_a280_ratio=1.4,
        total_yield_ug=4.0,
    )

    scores = _score_miniprep(
        _good_miniprep_answer(),
        _miniprep_call_pair(arguments=forged_arguments, observation=failed_output),
    )

    assert scores["task_success"] == 0.0


def test_miniprep_missing_output_field_cannot_fall_back_to_request_arguments():
    observation = _good_miniprep_observation()
    observation.pop("lysis_duration_min")

    scores = _score_miniprep(
        _good_miniprep_answer(),
        _miniprep_call_pair(observation=observation),
    )

    assert scores["task_success"] == 0.0
    assert scores["decision_quality"] == 0.0
    assert scores["efficiency"] == 0.0
    assert scores["overall"] == 0.0


@pytest.mark.parametrize(
    ("updates", "answer_replacements"),
    (
        (
            {"total_yield_ug": 1.0, "final_concentration_ng_ul": 20.0},
            (
                ("Plasmid concentration:", "Plasmid concentration: 20.0 ng/uL"),
                ("Total yield:", "Total yield: 1.0 ug"),
            ),
        ),
        ({"source_culture_remaining_volume_ml": 5.0}, ()),
    ),
)
def test_miniprep_rejects_impossible_yield_or_causal_remaining_volume(
    updates, answer_replacements
):
    impossible = _good_miniprep_observation(**updates)
    answer = _good_miniprep_answer()
    for prefix, replacement in answer_replacements:
        answer = _replace_report_line(answer, prefix, replacement)

    scores = _score_miniprep(answer, _miniprep_call_pair(observation=impossible))

    assert scores["task_success"] == 0.0


def test_miniprep_rejects_arguments_only_fake_observation():
    fake = {
        "type": "tool_call",
        "tool_name": "perform_miniprep",
        "arguments": {**_good_miniprep_arguments(), **_good_miniprep_observation()},
    }

    assert _score_miniprep(_good_miniprep_answer(), [fake])["task_success"] == 0.0


def test_miniprep_rejects_standalone_tool_output_without_a_request():
    standalone_output = {
        "role": "tool",
        "tool_call_id": "orphan_miniprep_output",
        "function": "perform_miniprep",
        "content": json.dumps(_good_miniprep_observation()),
    }

    scores = _score_miniprep(_good_miniprep_answer(), [standalone_output])

    assert scores["task_success"] == 0.0
    assert scores["decision_quality"] == 0.0
    assert scores["overall"] == 0.0


@pytest.mark.parametrize(
    "failure_mode",
    (
        "missing_output",
        "missing_miniprep_id",
        "missing_culture_id",
        "tool_error",
        "rejected_preparation",
        "hidden_failure_reason",
    ),
)
def test_miniprep_fails_closed_on_missing_or_error_tool_output(failure_mode):
    if failure_mode == "missing_output":
        observation = {}
    elif failure_mode == "missing_miniprep_id":
        observation = _good_miniprep_observation()
        observation.pop("miniprep_id")
    elif failure_mode == "missing_culture_id":
        observation = _good_miniprep_observation()
        observation.pop("culture_id")
    elif failure_mode == "tool_error":
        observation = _good_miniprep_observation(
            status="tool_error",
            preparation_accepted=False,
            failure_reasons=["tool_error"],
            error="simulated tool failure",
        )
    elif failure_mode == "rejected_preparation":
        observation = _good_miniprep_observation(preparation_accepted=False)
    else:
        observation = _good_miniprep_observation(
            failure_reasons=[MINIPREP_FAILURE_WRONG_BUFFER]
        )

    scores = _score_miniprep(
        _good_miniprep_answer(),
        _miniprep_call_pair(observation=observation),
    )

    assert scores["task_success"] == 0.0


@pytest.mark.parametrize("terminal_status", (None, "garbage", "Tool_Error"))
def test_miniprep_unknown_or_error_status_has_no_result_credit(terminal_status):
    observation = _good_miniprep_observation()
    if terminal_status is None:
        observation.pop("status")
    else:
        observation["status"] = terminal_status

    scores = _score_miniprep(
        _good_miniprep_answer(),
        _miniprep_call_pair(observation=observation),
    )

    assert scores["task_success"] == 0.0
    assert scores["decision_quality"] == 0.0
    assert scores["troubleshooting"] == 0.0
    assert scores["efficiency"] == 0.0
    assert scores["overall"] == 0.0


@pytest.mark.parametrize("good_first", (True, False), ids=("good-then-bad", "bad-then-good"))
def test_miniprep_requires_exactly_one_call_across_attempts(good_first):
    good = _miniprep_call_pair(call_id="call_miniprep_good")
    bad = _miniprep_call_pair(
        call_id="call_miniprep_bad",
        arguments=_good_miniprep_arguments(lysis_buffer_sequence="P1,P2,P3"),
        observation=_good_miniprep_observation(
            miniprep_id="miniprep_002",
            status=MINIPREP_FAILURE_WRONG_BUFFER,
            preparation_accepted=False,
            failure_reasons=[MINIPREP_FAILURE_WRONG_BUFFER],
            lysis_buffer_sequence="P1,P2,P3",
            lysis_buffer_sequence_canonical=None,
            final_concentration_ng_ul=80.0,
            a260_a280_ratio=1.4,
            total_yield_ug=4.0,
        ),
    )
    transcript = [*(good if good_first else bad), *(bad if good_first else good)]

    scores = _score_miniprep(_good_miniprep_answer(), transcript)

    assert scores["task_success"] == 0.0


def test_miniprep_cross_attempt_field_splicing_cannot_pass():
    first = _miniprep_call_pair(
        call_id="call_miniprep_first",
        observation=_good_miniprep_observation(
            miniprep_id="miniprep_001",
            final_concentration_ng_ul=100.0,
            total_yield_ug=5.0,
        ),
    )
    second = _miniprep_call_pair(
        call_id="call_miniprep_second",
        observation=_good_miniprep_observation(miniprep_id="miniprep_002"),
    )

    assert _score_miniprep(_good_miniprep_answer(), [*first, *second])["task_success"] == 0.0


def test_miniprep_multi_failure_requires_each_diagnosis_for_full_credit():
    failure_reasons = [
        MINIPREP_FAILURE_WRONG_BUFFER,
        MINIPREP_FAILURE_OVERLYSIS,
        MINIPREP_FAILURE_WRONG_METHOD,
    ]
    with open(MINIPREP_GROUND_TRUTH_PATH) as handle:
        ground_truth = json.load(handle)
    one_diagnosis = ground_truth["failure_diagnosis_map"][MINIPREP_FAILURE_WRONG_BUFFER][
        "canonical_diagnosis"
    ]
    answer = _replace_report_line(_good_miniprep_answer(), "Interpretation:", "Interpretation: failure")
    answer = _replace_report_line(answer, "Diagnosis:", "Diagnosis: " + one_diagnosis)
    observation = _good_miniprep_observation(
        status=failure_reasons[0],
        preparation_accepted=False,
        failure_reasons=failure_reasons,
    )

    scores = _score_miniprep(answer, _miniprep_call_pair(observation=observation))

    assert scores["task_success"] == 0.0
    assert scores["troubleshooting"] == pytest.approx(1.0 / 3.0)


def test_miniprep_no_tool_oracle_answer_scores_zero():
    scores = _score_miniprep(_good_miniprep_answer(), [])

    assert scores["task_success"] == 0.0
    assert scores["overall"] == 0.0


def _good_express_transcript():
    return [
        {
            "type": "tool_call",
            "tool_name": "run_protein_expression",
            "arguments": {
                "expression_id": "expression_001",
                "host_strain": "BL21(DE3)",
                "host_strain_normalized": "bl21(de3)",
                "protein_name": "MBP-GFP fusion",
                "expected_molecular_weight_kda": 72.0,
                "iptg_concentration_mm": 1.0,
                "induction_od600": 0.6,
                "induction_temperature_c": 18,
                "induction_hours": 16,
                "lysis_buffer_ph": 8.0,
                "culture_volume_ml": 500.0,
                "soluble_yield_mg_per_l": 36.8,
                "insoluble_fraction": 0.08,
                "total_soluble_mg": 18.4,
                "status": "induced",
            },
        }
    ]


def _good_express_answer() -> str:
    return (
        "Host strain: BL21(DE3)\n"
        "IPTG concentration: 1.0 mM\n"
        "Induction OD600: 0.6\n"
        "Induction temperature: 18 C\n"
        "Induction duration: 16 h\n"
        "Lysis buffer pH: 8.0\n"
        "Expected soluble yield: 36.8 mg/L\n"
        "Interpretation: success"
    )


def test_good_express_trajectory_scores_high():
    scores = score_express_trajectory(
        final_answer=_good_express_answer(),
        transcript=_good_express_transcript(),
        ground_truth_path=str(EXPRESS_GROUND_TRUTH_PATH),
    )
    assert scores["task_success"] == 1.0
    assert scores["decision_quality"] == 1.0
    assert scores["overall"] >= 0.9


def test_express_rejects_each_inconsistent_or_nonsensical_report_field():
    replacements = {
        "Host strain:": "Host strain: DH5alpha",
        "IPTG concentration:": "IPTG concentration: 99 mM",
        "Induction OD600:": "Induction OD600: 9.9",
        "Induction temperature:": "Induction temperature: 99 C",
        "Induction duration:": "Induction duration: 99 h",
        "Lysis buffer pH:": "Lysis buffer pH: 1.0",
        "Expected soluble yield:": "Expected soluble yield: 999 mg/L",
        "Interpretation:": "Interpretation: Expression failed.",
    }
    for prefix, replacement in replacements.items():
        scores = score_express_trajectory(
            final_answer=_replace_report_line(_good_express_answer(), prefix, replacement),
            transcript=_good_express_transcript(),
            ground_truth_path=str(EXPRESS_GROUND_TRUTH_PATH),
        )
        assert scores["task_success"] == 0.0, prefix


def test_express_accepts_equivalent_host_punctuation_and_spacing():
    answer = _replace_report_line(
        _good_express_answer(),
        "Host strain:",
        "Host strain: BL21 (DE3)",
    )
    scores = score_express_trajectory(
        final_answer=answer,
        transcript=_good_express_transcript(),
        ground_truth_path=str(EXPRESS_GROUND_TRUTH_PATH),
    )
    assert scores["task_success"] == 1.0


def test_express_rejects_success_label_with_contradictory_interpretation():
    answer = _replace_report_line(
        _good_express_answer(),
        "Interpretation:",
        "Interpretation: success; protein expression did not work.",
    )
    scores = score_express_trajectory(
        final_answer=answer,
        transcript=_good_express_transcript(),
        ground_truth_path=str(EXPRESS_GROUND_TRUTH_PATH),
    )
    assert scores["task_success"] == 0.0


def test_express_wrong_host_triggers_troubleshooting():
    transcript = _good_express_transcript()
    transcript[0]["arguments"]["host_strain_normalized"] = "dh5alpha"
    transcript[0]["arguments"]["status"] = "wrong_host_strain"
    scores = score_express_trajectory(
        final_answer=_good_express_answer(),
        transcript=transcript,
        ground_truth_path=str(EXPRESS_GROUND_TRUTH_PATH),
    )
    assert scores["troubleshooting"] < 1.0
    assert scores["decision_scores"]["uses_t7_expression_host"] == 0.0


def _good_purify_transcript():
    return [
        {
            "type": "tool_call",
            "tool_name": "run_nta_purification",
            "arguments": {
                "purification_id": "purification_001",
                "resin_name": "Ni-NTA",
                "resin_normalized": "ni-nta",
                "load_imidazole_mm": 20.0,
                "wash_imidazole_mm": 50.0,
                "elute_imidazole_mm": 250.0,
                "flow_rate_ml_per_min": 1.0,
                "column_bed_volume_ml": 1.0,
                "target_protein_name": "MBP-GFP fusion",
                "expected_band_kda": 72.0,
                "purified_concentration_mg_per_ml": 6.12,
                "purity_percent": 95.0,
                "sds_page_result": "single_clean_band_at_72_kDa",
                "eluate_volume_ml": 2.5,
                "status": "purified",
            },
        }
    ]


def _good_purify_answer() -> str:
    return (
        "Resin: Ni-NTA\n"
        "Load imidazole: 20 mM\n"
        "Wash imidazole: 50 mM\n"
        "Elute imidazole: 250 mM\n"
        "Expected band size: 72 kDa\n"
        "Purified concentration: 6.12 mg/mL\n"
        "SDS-PAGE result: single_clean_band_at_72_kDa\n"
        "Purity: 95.0%\n"
        "Interpretation: success"
    )


def test_good_purify_trajectory_scores_high():
    scores = score_purify_trajectory(
        final_answer=_good_purify_answer(),
        transcript=_good_purify_transcript(),
        ground_truth_path=str(PURIFY_GROUND_TRUTH_PATH),
    )
    assert scores["task_success"] == 1.0
    assert scores["decision_quality"] == 1.0
    assert scores["overall"] >= 0.9


def test_purify_rejects_each_inconsistent_or_nonsensical_report_field():
    replacements = {
        "Resin:": "Resin: glutathione agarose",
        "Load imidazole:": "Load imidazole: 999 mM",
        "Wash imidazole:": "Wash imidazole: 999 mM",
        "Elute imidazole:": "Elute imidazole: 999 mM",
        "Expected band size:": "Expected band size: 999 kDa",
        "Purified concentration:": "Purified concentration: 999 mg/mL",
        "SDS-PAGE result:": "SDS-PAGE result: no_target_band_detected",
        "Purity:": "Purity: 1.0%",
        "Interpretation:": "Interpretation: Purification failed; no target band was detected.",
    }
    for prefix, replacement in replacements.items():
        scores = score_purify_trajectory(
            final_answer=_replace_report_line(_good_purify_answer(), prefix, replacement),
            transcript=_good_purify_transcript(),
            ground_truth_path=str(PURIFY_GROUND_TRUTH_PATH),
        )
        assert scores["task_success"] == 0.0, prefix


def test_purify_accepts_equivalent_resin_and_sds_page_punctuation():
    answer = _replace_report_line(
        _good_purify_answer(),
        "Resin:",
        "Resin: Ni NTA",
    )
    answer = _replace_report_line(
        answer,
        "SDS-PAGE result:",
        "SDS-PAGE result: single clean band at 72 kDa",
    )
    scores = score_purify_trajectory(
        final_answer=answer,
        transcript=_good_purify_transcript(),
        ground_truth_path=str(PURIFY_GROUND_TRUTH_PATH),
    )
    assert scores["task_success"] == 1.0


def test_purify_rejects_success_label_with_contradictory_interpretation():
    answer = _replace_report_line(
        _good_purify_answer(),
        "Interpretation:",
        "Interpretation: success; the protein is impure and purification did not work.",
    )
    scores = score_purify_trajectory(
        final_answer=answer,
        transcript=_good_purify_transcript(),
        ground_truth_path=str(PURIFY_GROUND_TRUTH_PATH),
    )
    assert scores["task_success"] == 0.0


def test_purify_wrong_resin_triggers_troubleshooting():
    transcript = _good_purify_transcript()
    transcript[0]["arguments"]["resin_normalized"] = "glutathione agarose"
    transcript[0]["arguments"]["status"] = "wrong_resin"
    scores = score_purify_trajectory(
        final_answer=_good_purify_answer(),
        transcript=transcript,
        ground_truth_path=str(PURIFY_GROUND_TRUTH_PATH),
    )
    assert "uses_ni_nta_resin" not in scores["decision_scores"]
    assert scores["task_success"] == 0.0
    assert scores["troubleshooting"] < 1.0


def _good_perturb_followup_transcript():
    return [
        {
            "type": "tool_call",
            "tool_name": "list_candidate_targets",
            "arguments": {},
        },
        {
            "type": "tool_call",
            "tool_name": "lookup_target_profile",
            "arguments": {"target_id": "TGT_C"},
        },
        {
            "type": "tool_call",
            "tool_name": "list_validation_assays",
            "arguments": {},
        },
        {
            "type": "tool_call",
            "tool_name": "run_validation_assay",
            "arguments": {
                "target_id": "TGT_C",
                "assay_id": "ASY_PATHWAY",
                "status": "completed",
                "effect_direction": "not_supported",
                "effect_size": -0.181,
                "qc_status": "pass",
                "interpretation_code": "qc_artifact_not_supported",
            },
        },
    ]


def _good_perturb_followup_answer() -> str:
    return (
        "Chosen target: TGT_C\n"
        "Follow-up assay: ASY_PATHWAY\n"
        "Result: fail\n"
        "Decision: drop\n"
        "Interpretation: The hit was ambiguous because the primary screen and QC disagreed, and the orthogonal assay did not support it."
    )


def test_good_perturb_followup_trajectory_scores_high():
    scores = score_perturb_followup_trajectory(
        final_answer=_good_perturb_followup_answer(),
        transcript=_good_perturb_followup_transcript(),
        ground_truth_path=str(PERTURB_FOLLOWUP_GROUND_TRUTH_PATH),
    )
    assert score_perturb_followup_task_success(
        _good_perturb_followup_answer(),
        _good_perturb_followup_transcript(),
        json.loads(PERTURB_FOLLOWUP_GROUND_TRUTH_PATH.read_text()),
    ) == 1.0
    assert scores["task_success"] == 1.0
    assert scores["decision_quality"] == 1.0
    assert scores["overall"] >= 0.9


def test_wrong_perturb_followup_assay_reduces_score():
    transcript = _good_perturb_followup_transcript()
    transcript[-1]["arguments"]["assay_id"] = "ASY_CYTOKINE"
    scores = score_perturb_followup_trajectory(
        final_answer=_good_perturb_followup_answer(),
        transcript=transcript,
        ground_truth_path=str(PERTURB_FOLLOWUP_GROUND_TRUTH_PATH),
    )
    assert scores["task_success"] == 0.0
    assert scores["decision_scores"]["orthogonal_assay_choice"] == 0.0


def _good_target_prioritize_transcript():
    transcript = [
        {
            "type": "tool_call",
            "tool_name": "list_candidate_targets",
            "arguments": {},
        }
    ]
    for target_id in ("TGT_A", "TGT_B", "TGT_C", "TGT_D"):
        transcript.append(
            {
                "type": "tool_call",
                "tool_name": "lookup_target_profile",
                "arguments": {"target_id": target_id},
            }
        )
    return transcript


def _good_target_prioritize_answer() -> str:
    return (
        "Top target: TGT_A\n"
        "Do-not-advance target: TGT_B\n"
        "Advance reason: TGT_A has the most balanced signal, the strongest patient relevance, and low viability risk.\n"
        "Main risk: The remaining risk is whether its context consistency and translational support hold up across broader settings."
    )


def test_good_target_prioritize_trajectory_scores_high():
    scores = score_target_prioritize_trajectory(
        final_answer=_good_target_prioritize_answer(),
        transcript=_good_target_prioritize_transcript(),
        ground_truth_path=str(TARGET_PRIORITIZE_GROUND_TRUTH_PATH),
    )
    assert score_target_prioritize_task_success(
        _good_target_prioritize_answer(),
        _good_target_prioritize_transcript(),
        json.loads(TARGET_PRIORITIZE_GROUND_TRUTH_PATH.read_text()),
    ) == 1.0
    assert scores["task_success"] == 1.0
    assert scores["decision_quality"] == 1.0
    assert scores["overall"] >= 0.9


def test_missing_target_profile_coverage_reduces_prioritize_score():
    transcript = _good_target_prioritize_transcript()[:-1]
    scores = score_target_prioritize_trajectory(
        final_answer=_good_target_prioritize_answer(),
        transcript=transcript,
        ground_truth_path=str(TARGET_PRIORITIZE_GROUND_TRUTH_PATH),
    )
    assert scores["task_success"] == 0.0
    assert scores["decision_scores"]["full_profile_coverage"] == 0.0
    assert scores["decision_quality"] < 1.0


def test_target_prioritize_oracle_answer_without_tools_does_not_get_task_success():
    scores = score_target_prioritize_trajectory(
        final_answer=_good_target_prioritize_answer(),
        transcript=[],
        ground_truth_path=str(TARGET_PRIORITIZE_GROUND_TRUTH_PATH),
    )

    assert scores["task_success"] == 0.0
    assert scores["decision_quality"] == 0.5
    assert scores["overall"] < 0.35


def test_target_prioritize_task_success_accepts_signal_context_and_liability_reasoning():
    answer = (
        "Top target: TGT_A\n"
        "Do-not-advance target: TGT_B\n"
        "Advance reason: TGT_A has the strongest perturbation score, high context consistency, and low viability risk.\n"
        "Main risk: The remaining risk is that the mechanistic and translational picture may not generalize across broader settings."
    )

    assert (
        score_target_prioritize_task_success(
            answer,
            _good_target_prioritize_transcript(),
            json.loads(TARGET_PRIORITIZE_GROUND_TRUTH_PATH.read_text()),
        )
        == 1.0
    )


def test_target_prioritize_risk_statement_must_not_focus_on_do_not_advance_target():
    answer = (
        "Top target: TGT_A\n"
        "Do-not-advance target: TGT_B\n"
        "Advance reason: TGT_A has the strongest perturbation score, high context consistency, and low viability risk.\n"
        "Main risk: TGT_B still carries major literature uncertainty on top of its viability liability."
    )
    scores = score_target_prioritize_trajectory(
        final_answer=answer,
        transcript=_good_target_prioritize_transcript(),
        ground_truth_path=str(TARGET_PRIORITIZE_GROUND_TRUTH_PATH),
    )

    assert scores["task_success"] == 0.0
    assert scores["troubleshooting"] == 0.0


def _good_target_validate_transcript():
    return [
        {
            "type": "tool_call",
            "tool_name": "lookup_target_profile",
            "arguments": {"target_id": "TGT_A"},
        },
        {
            "type": "tool_call",
            "tool_name": "list_validation_assays",
            "arguments": {},
        },
        {
            "type": "tool_call",
            "tool_name": "run_validation_assay",
            "arguments": {
                "target_id": "TGT_A",
                "assay_id": "ASY_CYTOKINE",
                "status": "completed",
                "effect_direction": "supportive",
                "effect_size": 0.821,
                "qc_status": "pass",
                "interpretation_code": "validated_signal",
            },
        },
    ]


def _good_target_validate_answer() -> str:
    return (
        "Validation assay: ASY_CYTOKINE\n"
        "Primary readout: change in inflammatory cytokine program\n"
        "Decision: advance\n"
        "Interpretation: The orthogonal validation assay supports the target strongly enough to advance."
    )


def test_good_target_validate_trajectory_scores_high():
    scores = score_target_validate_trajectory(
        final_answer=_good_target_validate_answer(),
        transcript=_good_target_validate_transcript(),
        ground_truth_path=str(TARGET_VALIDATE_GROUND_TRUTH_PATH),
    )
    assert score_target_validate_task_success(
        _good_target_validate_answer(),
        _good_target_validate_transcript(),
        json.loads(TARGET_VALIDATE_GROUND_TRUTH_PATH.read_text()),
    ) == 1.0
    assert scores["task_success"] == 1.0
    assert scores["decision_quality"] == 1.0
    assert scores["overall"] >= 0.9


def test_multiple_validation_runs_reduce_target_validate_score():
    transcript = _good_target_validate_transcript() + [
        {
            "type": "tool_call",
            "tool_name": "run_validation_assay",
            "arguments": {
                "target_id": "TGT_A",
                "assay_id": "ASY_PATHWAY",
                "status": "completed",
                "effect_direction": "supportive",
                "effect_size": 0.544,
                "qc_status": "pass",
                "interpretation_code": "moderate_support",
            },
        }
    ]
    scores = score_target_validate_trajectory(
        final_answer=_good_target_validate_answer(),
        transcript=transcript,
        ground_truth_path=str(TARGET_VALIDATE_GROUND_TRUTH_PATH),
    )
    assert scores["task_success"] == 0.0
    assert scores["decision_scores"]["single_validation_run"] == 0.0
