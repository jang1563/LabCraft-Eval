"""Regression tests for answer-bearing agent prompts."""

from __future__ import annotations

import inspect
import json

import pytest

from src.solvers import (
    build_clone_solver,
    build_expression_solver,
    build_gibson_solver,
    build_golden_gate_solver,
    build_miniprep_solver,
    build_purification_solver,
)
from src.tasks.clone_01 import build_clone_01_prompt, build_clone_01_sample
from src.tasks.express_01 import build_express_01_prompt, build_express_01_sample
from src.tasks.followup_01 import build_followup_01_prompt
from src.tasks.gibson_01 import build_gibson_01_prompt, build_gibson_01_sample
from src.tasks.golden_gate_01 import build_golden_gate_01_prompt, build_golden_gate_01_sample
from src.tasks.growth_01 import build_growth_01_prompt
from src.tasks.miniprep_01 import build_miniprep_01_prompt, build_miniprep_01_sample
from src.tasks.purify_01 import (
    PURIFY_01_GROUND_TRUTH,
    build_purify_01_prompt,
    build_purify_01_sample,
)
from src.tools.lab_tools import (
    gibson_assembly_call,
    gibson_assembly_tool,
    golden_gate_assembly_call,
    golden_gate_assembly_tool,
    ligate_call,
    ligate_tool,
    perform_miniprep_tool,
    restriction_digest_call,
    restriction_digest_tool,
    run_pcr_tool,
    run_nta_purification_call,
    run_nta_purification_tool,
    run_protein_expression_tool,
    transform_assembly_call,
    transform_assembly_tool,
    transform_call,
    transform_gibson_call,
    transform_gibson_tool,
    transform_ligation_call,
    transform_ligation_tool,
    transform_tool,
)
from src.tools.discovery import lookup_target_profile_tool, run_validation_assay_tool
from scripts.run_human_baseline import GROWTH_TOOLS, TRANSFORM_TOOLS


TASK_PROMPT_BUILDERS = (
    (build_clone_01_prompt, build_clone_01_sample),
    (build_golden_gate_01_prompt, build_golden_gate_01_sample),
    (build_gibson_01_prompt, build_gibson_01_sample),
    (build_miniprep_01_prompt, build_miniprep_01_sample),
    (build_express_01_prompt, build_express_01_sample),
    (build_purify_01_prompt, build_purify_01_sample),
)

ANSWER_BEARING_PROMPT_FRAGMENTS = (
    "1:3 is canonical",
    "BsaI is canonical",
    "canonical 2-fragment Gibson condition",
    'canonical Birnboim-Doly alkaline lysis sequence is "P1,P2,P3"',
    "1 mM is textbook-standard",
    "OD600 = 0.6 is canonical",
    "250 mM is canonical",
    "Type IIS enzyme: BsaI",
    "Temperature: 50 C",
    "Lysis buffer sequence: P1,P2,P3",
    "Purification method: silica column",
    "Resin: Ni-NTA",
    "Expected band size: 72 kDa",
)


@pytest.mark.parametrize(("prompt_builder", "sample_builder"), TASK_PROMPT_BUILDERS)
def test_task_prompts_are_constructible_without_answer_bearing_guidance(
    prompt_builder, sample_builder
):
    prompt = prompt_builder()
    sample = sample_builder()

    assert len(prompt) > 300
    assert "Final answer schema" in prompt
    assert sample["input"] == prompt
    assert sample["metadata"]["task_id"]
    assert not [fragment for fragment in ANSWER_BEARING_PROMPT_FRAGMENTS if fragment in prompt]


def test_clone_prompt_requires_substrate_inspection_for_enzyme_choice():
    prompt = build_clone_01_prompt().casefold()
    assert "ecori" not in prompt
    assert "bamhi" not in prompt


def test_given_ni_nta_method_is_not_scored_as_a_decision():
    payload = json.loads(PURIFY_01_GROUND_TRUTH.read_text())
    decision_ids = {point["id"] for point in payload["decision_points"]}
    assert "ni-nta" in build_purify_01_prompt().casefold()
    assert "uses_ni_nta_resin" not in decision_ids


def test_expression_prompt_does_not_supply_t7_host_decision():
    prompt = build_express_01_prompt().casefold()
    assert "t7 expression host" not in prompt
    assert "ni-nta downstream" not in prompt


def test_growth_prompts_do_not_supply_scored_parameter_bounds():
    assert "15-minute" not in build_growth_01_prompt().casefold()
    assert "15-minute" not in build_followup_01_prompt().casefold()
    assert "0.05" not in build_growth_01_prompt().casefold()
    assert "10-minute" not in build_growth_01_prompt().casefold()
    assert "20-minute" not in build_growth_01_prompt().casefold()


def test_discovery_tool_docs_do_not_supply_exact_scored_identifiers():
    docs = "\n".join(
        inspect.getdoc(tool) or ""
        for tool in (lookup_target_profile_tool(), run_validation_assay_tool())
    ).casefold()
    assert "tgt_a" not in docs
    assert "asy_cytokine" not in docs


def test_human_baseline_examples_are_neutral_placeholders():
    arguments = [tool.example_arguments for tool in TRANSFORM_TOOLS + GROWTH_TOOLS]
    values = {
        str(value).casefold()
        for example_arguments in arguments
        for value in example_arguments.values()
    }
    for leaked_value in ("soc", "30", "60", "0.05", "15", "lb agar"):
        assert leaked_value not in values
    examples = json.dumps(arguments, sort_keys=True).casefold()
    assert "<choose" in examples
    assert "returned by" in examples


def test_human_transform_handler_requires_all_evaluated_choices():
    parameters = inspect.signature(transform_call).parameters

    for name in (
        "heat_shock_seconds",
        "recovery_minutes",
        "outgrowth_media",
        "shaking",
        "ice_incubation_minutes",
    ):
        assert parameters[name].default is inspect.Parameter.empty


@pytest.mark.parametrize(
    ("call", "evaluated_parameters"),
    (
        (restriction_digest_call, ("heat_inactivation_temperature_c",)),
        (ligate_call, ("buffer",)),
        (
            golden_gate_assembly_call,
            (
                "buffer",
                "cycle_count",
                "digest_temperature_c",
                "ligate_temperature_c",
                "final_digest_minutes",
                "heat_kill_temperature_c",
            ),
        ),
        (gibson_assembly_call, ("overlap_length_bp",)),
        (
            run_nta_purification_call,
            ("flow_rate_ml_per_min", "column_bed_volume_ml"),
        ),
        (
            transform_ligation_call,
            (
                "heat_shock_seconds",
                "recovery_minutes",
                "outgrowth_media",
                "shaking",
                "ice_incubation_minutes",
            ),
        ),
        (
            transform_assembly_call,
            (
                "heat_shock_seconds",
                "recovery_minutes",
                "outgrowth_media",
                "shaking",
                "ice_incubation_minutes",
            ),
        ),
        (
            transform_gibson_call,
            (
                "heat_shock_seconds",
                "recovery_minutes",
                "outgrowth_media",
                "shaking",
                "ice_incubation_minutes",
            ),
        ),
    ),
)
def test_low_level_handlers_do_not_default_evaluated_choices(call, evaluated_parameters):
    parameters = inspect.signature(call).parameters

    for name in evaluated_parameters:
        assert parameters[name].default is inspect.Parameter.empty


@pytest.mark.parametrize(
    "solver_builder",
    (
        build_clone_solver,
        build_golden_gate_solver,
        build_gibson_solver,
        build_miniprep_solver,
        build_expression_solver,
        build_purification_solver,
    ),
)
def test_solver_assistant_prompts_do_not_supply_protocol_answers(monkeypatch, solver_builder):
    import inspect_ai.agent

    monkeypatch.setattr(inspect_ai.agent, "react", lambda **kwargs: kwargs)
    solver_config = solver_builder()
    assistant_prompt = solver_config["prompt"].assistant_prompt

    assert assistant_prompt
    assert "report" in assistant_prompt.lower()
    assert not [
        fragment for fragment in ANSWER_BEARING_PROMPT_FRAGMENTS if fragment in assistant_prompt
    ]
    assert "0.1-1" not in assistant_prompt
    assert "10-20 mM" not in assistant_prompt
    assert "40-60 mM" not in assistant_prompt
    assert ">= 200 mM" not in assistant_prompt


@pytest.mark.parametrize(
    ("tool_builder", "evaluated_parameters"),
    (
        (restriction_digest_tool, ("heat_inactivation_temperature_c",)),
        (ligate_tool, ("buffer",)),
        (
            transform_tool,
            (
                "heat_shock_seconds",
                "recovery_minutes",
                "outgrowth_media",
                "shaking",
                "ice_incubation_minutes",
            ),
        ),
        (
            transform_ligation_tool,
            (
                "heat_shock_seconds",
                "recovery_minutes",
                "outgrowth_media",
                "shaking",
                "ice_incubation_minutes",
            ),
        ),
        (
            transform_assembly_tool,
            (
                "heat_shock_seconds",
                "recovery_minutes",
                "outgrowth_media",
                "shaking",
                "ice_incubation_minutes",
            ),
        ),
        (
            transform_gibson_tool,
            (
                "heat_shock_seconds",
                "recovery_minutes",
                "outgrowth_media",
                "shaking",
                "ice_incubation_minutes",
            ),
        ),
        (
            run_pcr_tool,
            ("polymerase_name", "additive", "extension_seconds", "cycle_count"),
        ),
        (
            golden_gate_assembly_tool,
            (
                "buffer",
                "cycle_count",
                "digest_temperature_c",
                "ligate_temperature_c",
                "final_digest_minutes",
                "heat_kill_temperature_c",
            ),
        ),
        (gibson_assembly_tool, ("overlap_length_bp",)),
        (
            perform_miniprep_tool,
            (
                "culture_volume_ml",
                "lysis_buffer_sequence",
                "lysis_duration_min",
                "purification_method",
                "elution_volume_ul",
            ),
        ),
        (
            run_protein_expression_tool,
            (
                "host_strain",
                "iptg_concentration_mm",
                "induction_od600",
                "induction_temperature_c",
                "induction_hours",
                "lysis_buffer_ph",
            ),
        ),
        (
            run_nta_purification_tool,
            (
                "resin_name",
                "load_imidazole_mm",
                "wash_imidazole_mm",
                "elute_imidazole_mm",
                "flow_rate_ml_per_min",
                "column_bed_volume_ml",
            ),
        ),
    ),
)
def test_tool_schemas_require_evaluated_protocol_choices(tool_builder, evaluated_parameters):
    tool = tool_builder()
    parameters = inspect.signature(tool).parameters

    for name in evaluated_parameters:
        assert parameters[name].default is inspect.Parameter.empty

    documentation = inspect.getdoc(tool) or ""
    assert "canonical" not in documentation.lower()
    assert "recommended" not in documentation.lower()
    assert "optimal" not in documentation.lower()


def test_transform_and_pcr_tool_docs_do_not_name_scored_answers():
    transform_docs = "\n".join(
        inspect.getdoc(tool) or ""
        for tool in (
            transform_tool(),
            transform_ligation_tool(),
            transform_assembly_tool(),
            transform_gibson_tool(),
        )
    ).casefold()
    pcr_docs = (inspect.getdoc(run_pcr_tool()) or "").casefold()
    assert "soc" not in transform_docs
    for leaked_value in ("q5", "phusion", "dmso", "betaine"):
        assert leaked_value not in pcr_docs
