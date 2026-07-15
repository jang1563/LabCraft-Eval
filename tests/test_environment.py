"""Environment tests for Transform-01."""

from __future__ import annotations

import asyncio
import copy
import json

import pytest

from pathlib import Path

from src.environment.gibson_contract import canonicalize_gibson_master_mix
from src.environment.expression_contract import (
    EXPRESSION_CONSTRUCT_ID,
    EXPRESSION_FAILURE_HOST,
    EXPRESSION_FAILURE_IPTG,
    EXPRESSION_FAILURE_LYSIS_PH,
    EXPRESSION_FAILURE_OD600,
    EXPRESSION_FAILURE_SCHEDULE,
    EXPRESSION_SUCCESS_STATUS,
    canonicalize_expression_host,
)
from src.environment.miniprep_contract import (
    MINIPREP_BUFFER_SEQUENCE_CANONICAL,
    MINIPREP_ELUTION_VOLUME_UL,
    MINIPREP_FAILURE_CULTURE_VOLUME,
    MINIPREP_FAILURE_ELUTION,
    MINIPREP_FAILURE_OVERLYSIS,
    MINIPREP_FAILURE_WRONG_BUFFER,
    MINIPREP_FAILURE_WRONG_METHOD,
    MINIPREP_PURIFICATION_METHOD_CANONICAL,
    MINIPREP_SOURCE_CULTURE_ID,
    canonicalize_miniprep_buffer_sequence,
    canonicalize_miniprep_purification_method,
)
from src.environment.operations import (
    count_colonies,
    fit_growth_curve,
    gibson_assembly,
    golden_gate_assembly,
    incubate,
    initialize_expression_construct,
    inoculate_growth,
    inspect_screening_plate,
    initialize_miniprep_source_culture,
    ligate,
    list_cloning_substrates,
    list_gibson_substrates,
    list_golden_gate_substrates,
    measure_od600,
    perform_miniprep,
    plate,
    prepare_media,
    restriction_digest,
    run_colony_pcr,
    run_gel,
    run_nta_purification,
    run_pcr,
    run_protein_expression,
    transform,
    transform_assembly,
    transform_gibson,
    transform_ligation,
)
from src.environment.state import GrowthMeasurement, create_lab_state
from src.environment.stochastic import (
    load_cloning_parameters,
    load_expression_parameters,
    load_gibson_parameters,
    load_golden_gate_parameters,
    load_miniprep_parameters,
    load_purification_parameters,
    load_screening_parameters,
)
from src.tools.lab_tools import (
    cleanup_sample,
    count_colonies_call,
    fit_growth_curve_call,
    incubate_call,
    inoculate_growth_call,
    inspect_screening_plate_call,
    initialize_expression_sample,
    measure_od600_call,
    plate_call,
    prepare_media_call,
    run_colony_pcr_call,
    run_gel_call,
    run_pcr_call,
    run_protein_expression_call,
    set_active_sample,
    transform_call,
)


def _run_transform_sequence(sample_id, seed):
    state = create_lab_state(sample_id=sample_id, seed=seed)
    prepared = prepare_media(
        state=state,
        medium="LB agar",
        antibiotic="ampicillin",
        antibiotic_concentration_ug_ml=100,
        plate_count=1,
    )
    plate_id = prepared["plates"][0]["plate_id"]
    transformed = transform(
        state=state,
        plasmid_mass_pg=1000,
        heat_shock_seconds=30,
        recovery_minutes=60,
        outgrowth_media="SOC",
        shaking=True,
    )
    plated = plate(
        state=state,
        culture_id=transformed["culture_id"],
        plate_id=plate_id,
        dilution_factor=10000,
        volume_ul=100,
    )
    counted = count_colonies(state=state, plating_id=plated["plating_id"])
    return {
        "prepared": prepared,
        "transformed": transformed,
        "plated": plated,
        "counted": counted,
    }


def _run_growth_sequence(sample_id, seed):
    state = create_lab_state(sample_id=sample_id, seed=seed)
    cultures = []
    for condition in ("LB", "M9 + glucose", "LB + chloramphenicol (1.8 uM)"):
        inoculated = inoculate_growth(state=state, condition=condition, starting_od600=0.05)
        growth_id = inoculated["growth_id"]
        measure_od600(state=state, growth_id=growth_id, dilution_factor=1.0)
        for minute in range(15, 121, 15):
            incubate(state=state, growth_id=growth_id, duration_minutes=15)
            dilution = 10.0 if condition == "LB" and minute >= 75 else 1.0
            measure_od600(state=state, growth_id=growth_id, dilution_factor=dilution)
        cultures.append(fit_growth_curve(state=state, growth_id=growth_id))
    return cultures


def _run_pcr_sequence(sample_id, seed):
    state = create_lab_state(sample_id=sample_id, seed=seed)
    reaction = run_pcr(
        state=state,
        polymerase_name="Q5 High-Fidelity DNA polymerase",
        additive="DMSO",
        extension_seconds=60,
        cycle_count=32,
    )
    gel = run_gel(state=state, reaction_id=reaction["reaction_id"], agarose_percent=1.0)
    return {"reaction": reaction, "gel": gel}


def test_same_seed_same_trajectory_is_deterministic():
    first = _run_transform_sequence("transform-seed", seed=12345)
    second = _run_transform_sequence("transform-seed-repeat", seed=12345)
    assert first == second


def test_different_seed_changes_outcome():
    first = _run_transform_sequence("transform-seed-a", seed=12345)
    second = _run_transform_sequence("transform-seed-b", seed=67890)
    assert first["counted"]["observed_colonies"] != second["counted"]["observed_colonies"]


def test_growth_sequence_is_deterministic():
    first = _run_growth_sequence("growth-seed-a", seed=12345)
    second = _run_growth_sequence("growth-seed-b", seed=12345)
    assert first == second


def test_growth_truth_is_observed_from_measurements_not_inoculation():
    state = create_lab_state(sample_id="growth-no-answer-leak", seed=12345)
    inoculated = inoculate_growth(state=state, condition="LB", starting_od600=0.05)

    assert "doubling_time_minutes" not in inoculated

    growth_id = inoculated["growth_id"]
    measure_od600(state=state, growth_id=growth_id, dilution_factor=1.0)
    for _ in range(8):
        incubate(state=state, growth_id=growth_id, duration_minutes=15)
        measure_od600(state=state, growth_id=growth_id, dilution_factor=1.0)

    fitted = fit_growth_curve(state=state, growth_id=growth_id)
    assert fitted["status"] == "analyzable"
    assert fitted["estimated_doubling_time_minutes"] == pytest.approx(20.0)


def test_pcr_sequence_is_deterministic():
    first = _run_pcr_sequence("pcr-seed-a", seed=12345)
    second = _run_pcr_sequence("pcr-seed-b", seed=12345)
    assert first == second


def test_good_pcr_condition_yields_clean_target_band():
    state = create_lab_state(sample_id="pcr-good", seed=7)
    reaction = run_pcr(
        state=state,
        polymerase_name="Q5 High-Fidelity DNA polymerase",
        additive="DMSO",
        extension_seconds=60,
        cycle_count=32,
    )
    gel = run_gel(state=state, reaction_id=reaction["reaction_id"], agarose_percent=1.0)
    assert reaction["status"] == "clean_target_band"
    assert gel["status"] == "single_clean_target_band"
    assert gel["visible_bands_bp"] == [2000]


@pytest.mark.parametrize(
    ("polymerase_name", "expected_canonical"),
    [
        ("Q5", "Q5 High-Fidelity DNA polymerase"),
        ("Q5 High-Fidelity Polymerase", "Q5 High-Fidelity DNA polymerase"),
        ("Phusion High-Fidelity Polymerase", "Phusion High-Fidelity DNA polymerase"),
    ],
)
def test_pcr_polymerase_aliases_use_canonical_simulator_behavior(
    polymerase_name, expected_canonical
):
    state = create_lab_state(sample_id="pcr-alias-{}".format(polymerase_name), seed=7)
    reaction = run_pcr(
        state=state,
        polymerase_name=polymerase_name,
        additive="DMSO",
        extension_seconds=60,
        cycle_count=32,
    )

    assert reaction["status"] == "clean_target_band"
    assert reaction["normalized_polymerase_name"] == expected_canonical
    assert reaction["notes"] == []


def test_pcr_unsupported_polymerase_note_does_not_misstate_proofreading_status():
    state = create_lab_state(sample_id="pcr-unsupported-pfu", seed=7)
    reaction = run_pcr(
        state=state,
        polymerase_name="Pfu DNA Polymerase",
        additive="DMSO",
        extension_seconds=60,
        cycle_count=32,
    )

    assert reaction["status"] == "nonspecific_amplification"
    assert "supported high-fidelity choices" in reaction["notes"][0]
    assert "non-proofreading" not in reaction["notes"][0]


def test_pcr_without_gc_additive_fails_clean_amplification():
    state = create_lab_state(sample_id="pcr-no-additive", seed=7)
    reaction = run_pcr(
        state=state,
        polymerase_name="Q5 High-Fidelity DNA polymerase",
        additive="none",
        extension_seconds=60,
        cycle_count=32,
    )
    gel = run_gel(state=state, reaction_id=reaction["reaction_id"], agarose_percent=1.0)
    assert reaction["status"] == "gc_rich_failure"
    assert gel["status"] == "no_visible_product"
    assert gel["visible_bands_bp"] == []


def test_run_gel_accepts_numeric_reaction_suffix():
    state = create_lab_state(sample_id="pcr-gel-suffix", seed=7)
    reaction = run_pcr(
        state=state,
        polymerase_name="Q5 High-Fidelity DNA polymerase",
        additive="DMSO",
        extension_seconds=60,
        cycle_count=32,
    )
    gel = run_gel(state=state, reaction_id="1", agarose_percent=1.0)
    assert reaction["reaction_id"] == "pcr_001"
    assert gel["reaction_id"] == "pcr_001"
    assert gel["status"] == "single_clean_target_band"


def test_run_gel_unknown_reaction_id_raises_clear_error():
    state = create_lab_state(sample_id="pcr-gel-missing", seed=7)
    run_pcr(
        state=state,
        polymerase_name="Q5 High-Fidelity DNA polymerase",
        additive="DMSO",
        extension_seconds=60,
        cycle_count=32,
    )
    with pytest.raises(ValueError, match="Available reaction IDs: pcr_001"):
        run_gel(state=state, reaction_id="7", agarose_percent=1.0)


def test_plate_selection_failure_is_reported():
    state = create_lab_state(sample_id="selection-failure", seed=101)
    prepared = prepare_media(
        state=state,
        medium="LB agar",
        antibiotic="ampicillin",
        antibiotic_concentration_ug_ml=50,
        plate_count=1,
    )
    transformed = transform(
        state=state,
        plasmid_mass_pg=1000,
        heat_shock_seconds=30,
        recovery_minutes=60,
    )
    plated = plate(
        state=state,
        culture_id=transformed["culture_id"],
        plate_id=prepared["plates"][0]["plate_id"],
        dilution_factor=1000,
        volume_ul=100,
    )
    counted = count_colonies(state=state, plating_id=plated["plating_id"])
    assert counted["status"] == "selection_failed"
    assert counted["observed_colonies"] is None


def test_plate_out_of_countable_range_is_reported():
    state = create_lab_state(sample_id="count-out-of-range", seed=123)
    prepared = prepare_media(
        state=state,
        medium="LB agar",
        antibiotic="ampicillin",
        antibiotic_concentration_ug_ml=100,
        plate_count=1,
    )
    transformed = transform(
        state=state,
        plasmid_mass_pg=10000,
        heat_shock_seconds=30,
        recovery_minutes=60,
    )
    plated = plate(
        state=state,
        culture_id=transformed["culture_id"],
        plate_id=prepared["plates"][0]["plate_id"],
        dilution_factor=1000,
        volume_ul=100,
    )
    counted = count_colonies(state=state, plating_id=plated["plating_id"])
    assert counted["status"] == "count_out_of_range"
    assert counted["observed_colonies"] > 250
    assert "25-250 colonies per plate" in counted["warnings"][0]


def test_plate_rejects_nonpositive_dilution_factor():
    state = create_lab_state(sample_id="plate-bad-dilution", seed=101)
    prepared = prepare_media(
        state=state,
        medium="LB agar",
        antibiotic="ampicillin",
        antibiotic_concentration_ug_ml=100,
        plate_count=1,
    )
    transformed = transform(
        state=state,
        plasmid_mass_pg=1000,
        heat_shock_seconds=30,
        recovery_minutes=60,
    )
    with pytest.raises(ValueError, match="dilution_factor must be positive"):
        plate(
            state=state,
            culture_id=transformed["culture_id"],
            plate_id=prepared["plates"][0]["plate_id"],
            dilution_factor=0,
            volume_ul=100,
        )


def test_plate_rejects_nonpositive_volume():
    state = create_lab_state(sample_id="plate-bad-volume", seed=101)
    prepared = prepare_media(
        state=state,
        medium="LB agar",
        antibiotic="ampicillin",
        antibiotic_concentration_ug_ml=100,
        plate_count=1,
    )
    transformed = transform(
        state=state,
        plasmid_mass_pg=1000,
        heat_shock_seconds=30,
        recovery_minutes=60,
    )
    with pytest.raises(ValueError, match="volume_ul must be positive"):
        plate(
            state=state,
            culture_id=transformed["culture_id"],
            plate_id=prepared["plates"][0]["plate_id"],
            dilution_factor=1000,
            volume_ul=0,
        )


def test_prepare_media_rejects_nonpositive_plate_count_and_antibiotic_concentration():
    state = create_lab_state(sample_id="prepare-media-validation", seed=101)
    with pytest.raises(ValueError, match="plate_count must be positive"):
        prepare_media(
            state=state,
            medium="LB agar",
            antibiotic="ampicillin",
            antibiotic_concentration_ug_ml=100,
            plate_count=0,
        )
    with pytest.raises(ValueError, match="antibiotic_concentration_ug_ml must be positive"):
        prepare_media(
            state=state,
            medium="LB agar",
            antibiotic="ampicillin",
            antibiotic_concentration_ug_ml=0,
            plate_count=1,
        )


def test_transform_rejects_nonpositive_or_negative_protocol_inputs():
    state = create_lab_state(sample_id="transform-validation", seed=101)
    with pytest.raises(ValueError, match="plasmid_mass_pg must be positive"):
        transform(state=state, plasmid_mass_pg=0, heat_shock_seconds=30, recovery_minutes=60)
    with pytest.raises(ValueError, match="heat_shock_seconds must be positive"):
        transform(state=state, plasmid_mass_pg=1000, heat_shock_seconds=0, recovery_minutes=60)
    with pytest.raises(ValueError, match="recovery_minutes must be non-negative"):
        transform(state=state, plasmid_mass_pg=1000, heat_shock_seconds=30, recovery_minutes=-1)
    with pytest.raises(ValueError, match="ice_incubation_minutes must be non-negative"):
        transform(
            state=state,
            plasmid_mass_pg=1000,
            heat_shock_seconds=30,
            recovery_minutes=60,
            ice_incubation_minutes=-1,
        )


def test_growth_operations_reject_nonpositive_inputs():
    state = create_lab_state(sample_id="growth-validation", seed=101)
    with pytest.raises(ValueError, match="starting_od600 must be positive"):
        inoculate_growth(state=state, condition="LB", starting_od600=0)

    inoculated = inoculate_growth(state=state, condition="LB", starting_od600=0.05)
    growth_id = inoculated["growth_id"]
    with pytest.raises(ValueError, match="duration_minutes must be positive"):
        incubate(state=state, growth_id=growth_id, duration_minutes=-15)
    with pytest.raises(ValueError, match="dilution_factor must be positive"):
        measure_od600(state=state, growth_id=growth_id, dilution_factor=0)


def test_fit_growth_curve_handles_qualifying_points_without_time_span():
    state = create_lab_state(sample_id="growth-zero-span", seed=101)
    inoculated = inoculate_growth(state=state, condition="LB", starting_od600=0.05)
    growth_id = inoculated["growth_id"]
    culture = state.growth_cultures[growth_id]
    culture.measurements.extend(
        [
            GrowthMeasurement(30, 1.0, 0.05, 0.05),
            GrowthMeasurement(30, 1.0, 0.06, 0.06),
            GrowthMeasurement(30, 1.0, 0.07, 0.07),
            GrowthMeasurement(30, 1.0, 0.10, 0.10),
        ]
    )

    fit = fit_growth_curve(state=state, growth_id=growth_id)

    assert fit["status"] == "insufficient_points"
    assert fit["qualifying_points"] == 3
    assert any("positive elapsed time" in warning for warning in fit["warnings"])


def test_tool_wrappers_report_validation_errors_as_tool_errors():
    async def run_bad_calls():
        sample_id = "tool-validation-errors"
        set_active_sample(sample_id, seed=101)
        try:
            bad_prepare = json.loads(await prepare_media_call("LB agar", "ampicillin", 0, 1))
            bad_transform = json.loads(await transform_call(0, 30, 60, "SOC", True, 30))
            inoculated = json.loads(await inoculate_growth_call("LB", 0.05))
            bad_incubate = json.loads(await incubate_call(inoculated["growth_id"], -15))
            bad_measure = json.loads(await measure_od600_call(inoculated["growth_id"], 0))
            return bad_prepare, bad_transform, bad_incubate, bad_measure
        finally:
            cleanup_sample(sample_id)

    bad_prepare, bad_transform, bad_incubate, bad_measure = asyncio.run(run_bad_calls())
    assert bad_prepare["status"] == "tool_error"
    assert bad_prepare["tool_name"] == "prepare_media"
    assert bad_transform["status"] == "tool_error"
    assert bad_transform["tool_name"] == "transform"
    assert bad_incubate["status"] == "tool_error"
    assert bad_incubate["tool_name"] == "incubate"
    assert bad_measure["status"] == "tool_error"
    assert bad_measure["tool_name"] == "measure_od600"


def test_plate_tool_reports_nonpositive_dilution_as_tool_error():
    async def run_bad_plate():
        sample_id = "plate-tool-bad-dilution"
        set_active_sample(sample_id, seed=101)
        try:
            prepared = json.loads(await prepare_media_call("LB agar", "ampicillin", 100, 1))
            transformed = json.loads(
                await transform_call(1000, 30, 60, "SOC", True, 30)
            )
            return json.loads(
                await plate_call(
                    culture_id=transformed["culture_id"],
                    plate_id=prepared["plates"][0]["plate_id"],
                    dilution_factor=0,
                    volume_ul=100,
                )
            )
        finally:
            cleanup_sample(sample_id)

    payload = asyncio.run(run_bad_plate())
    assert payload["status"] == "tool_error"
    assert payload["tool_name"] == "plate"
    assert "dilution_factor must be positive" in payload["message"]


def test_tool_wrappers_report_invalid_ids_and_pcr_values_as_tool_errors():
    async def run_bad_calls():
        sample_id = "tool-invalid-identifiers"
        set_active_sample(sample_id, seed=101)
        try:
            return (
                json.loads(await count_colonies_call("missing_plating")),
                json.loads(await fit_growth_curve_call("missing_growth")),
                json.loads(await run_gel_call("missing_reaction")),
                json.loads(await run_pcr_call("Q5", "none", "not-a-number", 30)),
            )
        finally:
            cleanup_sample(sample_id)

    bad_count, bad_fit, bad_gel, bad_pcr = asyncio.run(run_bad_calls())
    for payload, tool_name in (
        (bad_count, "count_colonies"),
        (bad_fit, "fit_growth_curve"),
        (bad_gel, "run_gel"),
        (bad_pcr, "run_pcr"),
    ):
        assert payload["status"] == "tool_error"
        assert payload["tool_name"] == tool_name
        assert payload["message"]


def test_concurrent_sample_isolation():
    async def run_pair():
        loop = asyncio.get_running_loop()
        return await asyncio.gather(
            loop.run_in_executor(None, _run_transform_sequence, "concurrent-a", 11),
            loop.run_in_executor(None, _run_transform_sequence, "concurrent-b", 22),
        )

    concurrent_a, concurrent_b = asyncio.run(run_pair())
    sequential_a = _run_transform_sequence("sequential-a", 11)
    sequential_b = _run_transform_sequence("sequential-b", 22)
    assert concurrent_a == sequential_a
    assert concurrent_b == sequential_b


async def _run_tool_sequence(sample_id, seed):
    set_active_sample(sample_id, seed=seed)
    try:
        prepared = json.loads(await prepare_media_call("LB agar", "ampicillin", 100, 1))
        transformed = json.loads(
            await transform_call(
                1000,
                30,
                60,
                outgrowth_media="SOC",
                shaking=True,
                ice_incubation_minutes=30,
            )
        )
        plated = json.loads(
            await plate_call(
                culture_id=transformed["culture_id"],
                plate_id=prepared["plates"][0]["plate_id"],
                dilution_factor=10000,
                volume_ul=100,
            )
        )
        counted = json.loads(await count_colonies_call(plated["plating_id"]))
        return {
            "prepared": prepared,
            "transformed": transformed,
            "plated": plated,
            "counted": counted,
        }
    finally:
        cleanup_sample(sample_id)


async def _run_growth_tool_sequence(sample_id, seed):
    set_active_sample(sample_id, seed=seed)
    try:
        fits = []
        for condition in ("LB", "M9 + glucose", "LB + chloramphenicol (1.8 uM)"):
            inoculated = json.loads(await inoculate_growth_call(condition, 0.05))
            growth_id = inoculated["growth_id"]
            json.loads(await measure_od600_call(growth_id, 1.0))
            for minute in range(15, 121, 15):
                json.loads(await incubate_call(growth_id, 15))
                dilution = 10.0 if condition == "LB" and minute >= 75 else 1.0
                json.loads(await measure_od600_call(growth_id, dilution))
            fits.append(json.loads(await fit_growth_curve_call(growth_id)))
        return fits
    finally:
        cleanup_sample(sample_id)


async def _run_pcr_tool_sequence(sample_id, seed):
    set_active_sample(sample_id, seed=seed)
    try:
        reaction = json.loads(
            await run_pcr_call(
                polymerase_name="Q5 High-Fidelity DNA polymerase",
                additive="DMSO",
                extension_seconds=60,
                cycle_count=32,
            )
        )
        gel = json.loads(await run_gel_call(reaction_id=reaction["reaction_id"], agarose_percent=1.0))
        return {"reaction": reaction, "gel": gel}
    finally:
        cleanup_sample(sample_id)


def test_tool_wrapper_concurrent_sample_isolation():
    async def run_pair():
        return await asyncio.gather(
            _run_tool_sequence("tool-concurrent-a", 11),
            _run_tool_sequence("tool-concurrent-b", 22),
        )

    concurrent_a, concurrent_b = asyncio.run(run_pair())
    sequential_a = asyncio.run(_run_tool_sequence("tool-sequential-a", 11))
    sequential_b = asyncio.run(_run_tool_sequence("tool-sequential-b", 22))
    assert concurrent_a == sequential_a
    assert concurrent_b == sequential_b


def test_growth_tool_wrapper_concurrent_sample_isolation():
    async def run_pair():
        return await asyncio.gather(
            _run_growth_tool_sequence("growth-tool-concurrent-a", 31),
            _run_growth_tool_sequence("growth-tool-concurrent-b", 42),
        )

    concurrent_a, concurrent_b = asyncio.run(run_pair())
    sequential_a = asyncio.run(_run_growth_tool_sequence("growth-tool-sequential-a", 31))
    sequential_b = asyncio.run(_run_growth_tool_sequence("growth-tool-sequential-b", 42))
    assert concurrent_a == sequential_a
    assert concurrent_b == sequential_b


def test_pcr_tool_wrapper_concurrent_sample_isolation():
    async def run_pair():
        return await asyncio.gather(
            _run_pcr_tool_sequence("pcr-tool-concurrent-a", 51),
            _run_pcr_tool_sequence("pcr-tool-concurrent-b", 62),
        )

    concurrent_a, concurrent_b = asyncio.run(run_pair())
    sequential_a = asyncio.run(_run_pcr_tool_sequence("pcr-tool-sequential-a", 51))
    sequential_b = asyncio.run(_run_pcr_tool_sequence("pcr-tool-sequential-b", 62))
    assert concurrent_a == sequential_a
    assert concurrent_b == sequential_b


SCREENING_PARAMETERS_PATH = (
    Path(__file__).resolve().parents[1] / "data" / "parameters" / "screening.json"
)


def test_screening_parameter_bundle_exposes_required_values():
    bundle = load_screening_parameters(SCREENING_PARAMETERS_PATH)
    assert bundle.value("historical_positive_rate_among_white_colonies") == pytest.approx(0.4)
    assert bundle.value("screening_target_confidence") == pytest.approx(0.95)
    assert bundle.integer("minimum_white_colonies_for_40pct_hit_rate_at_95pct_confidence") == 6
    assert bundle.integer("screening_recombinant_colony_pcr_band_bp") == 1200
    assert bundle.integer("screening_empty_vector_colony_pcr_band_bp") == 250


def test_inspect_screening_plate_reports_expected_composition():
    state = create_lab_state(sample_id="screen-inspect", seed=1)
    observation = inspect_screening_plate(state=state)
    assert observation["status"] == "screening_plate_ready"
    assert observation["white_colony_count"] == 12
    assert observation["blue_colony_count"] == 18
    assert observation["recombinant_band_bp"] == 1200
    assert observation["empty_vector_band_bp"] == 250
    assert observation["historical_positive_rate_among_white"] == pytest.approx(0.4)
    assert observation["target_confidence"] == pytest.approx(0.95)


def test_run_colony_pcr_on_six_white_colonies_hits_confidence_target():
    state = create_lab_state(sample_id="screen-six-whites", seed=1)
    inspect_screening_plate(state=state)
    result = run_colony_pcr(
        state=state,
        colony_ids=[
            "white_001",
            "white_002",
            "white_003",
            "white_004",
            "white_005",
            "white_006",
        ],
    )
    assert result["status"] == "screened"
    assert result["screening_strategy"] == "white_only"
    assert result["cumulative_screened_white_colony_count"] == 6
    assert result["cumulative_confidence_pct"] >= 95.0
    assert set(result["confirmed_recombinant_ids_cumulative"]).issuperset({"white_002", "white_005"})


def test_run_colony_pcr_flags_blue_colony_as_includes_blue():
    state = create_lab_state(sample_id="screen-blue", seed=1)
    inspect_screening_plate(state=state)
    result = run_colony_pcr(state=state, colony_ids=["blue_001"])
    assert result["screening_strategy"] == "includes_blue"
    assert result["confirmed_recombinant_ids_in_batch"] == []
    assert result["cumulative_screened_white_colony_count"] == 0


def test_run_colony_pcr_is_deterministic_on_same_seed():
    first_state = create_lab_state(sample_id="screen-det-a", seed=42)
    second_state = create_lab_state(sample_id="screen-det-b", seed=42)
    inspect_screening_plate(state=first_state)
    inspect_screening_plate(state=second_state)
    first = run_colony_pcr(state=first_state, colony_ids=["white_002", "white_005"])
    second = run_colony_pcr(state=second_state, colony_ids=["white_002", "white_005"])
    assert first == second


async def _run_screen_tool_sequence(sample_id, seed):
    set_active_sample(sample_id, seed=seed)
    try:
        plate_info = json.loads(await inspect_screening_plate_call())
        white_ids = plate_info["white_colony_ids"][:6]
        screening = json.loads(await run_colony_pcr_call(white_ids))
        return {"plate_info": plate_info, "screening": screening}
    finally:
        cleanup_sample(sample_id)


def test_screen_tool_wrapper_concurrent_sample_isolation():
    async def run_pair():
        return await asyncio.gather(
            _run_screen_tool_sequence("screen-tool-concurrent-a", 71),
            _run_screen_tool_sequence("screen-tool-concurrent-b", 82),
        )

    concurrent_a, concurrent_b = asyncio.run(run_pair())
    sequential_a = asyncio.run(_run_screen_tool_sequence("screen-tool-sequential-a", 71))
    sequential_b = asyncio.run(_run_screen_tool_sequence("screen-tool-sequential-b", 82))
    assert concurrent_a == sequential_a
    assert concurrent_b == sequential_b


CLONING_PARAMETERS_PATH = (
    Path(__file__).resolve().parents[1] / "data" / "parameters" / "cloning.json"
)


def test_cloning_parameter_bundle_exposes_required_values():
    bundle = load_cloning_parameters(CLONING_PARAMETERS_PATH)
    assert bundle.integer("vector_plasmid_length_bp") == 2686
    assert bundle.integer("insert_length_bp") == 950
    assert bundle.value("optimal_vector_to_insert_molar_ratio") == pytest.approx(3.0)
    assert "CutSmart" in bundle.choices("compatible_double_digest_buffers")
    assert bundle.text("preferred_ligase_name") == "T4 DNA ligase"
    assert bundle.integer("digest_minimum_duration_minutes") == 60
    assert 16.0 in [float(t) for t in bundle.choices("acceptable_ligation_temperatures_c")]


def test_list_cloning_substrates_creates_vector_and_insert():
    state = create_lab_state(sample_id="clone-substrates", seed=1)
    observation = list_cloning_substrates(state=state)
    fragment_ids = {f["fragment_id"] for f in observation["fragments"]}
    assert {"puc19_vector", "insert_raw"} <= fragment_ids
    assert observation["status"] == "cloning_substrates_ready"


def _run_good_clone_core(sample_id: str, seed: int):
    state = create_lab_state(sample_id=sample_id, seed=seed)
    list_cloning_substrates(state=state)
    vector_digest = restriction_digest(
        state=state,
        fragment_id="puc19_vector",
        enzyme_names=["EcoRI", "BamHI"],
        buffer="CutSmart",
        temperature_c=37.0,
        duration_minutes=60,
        heat_inactivate_after=True,
    )
    insert_digest = restriction_digest(
        state=state,
        fragment_id="insert_raw",
        enzyme_names=["EcoRI", "BamHI"],
        buffer="CutSmart",
        temperature_c=37.0,
        duration_minutes=60,
        heat_inactivate_after=True,
    )
    ligation = ligate(
        state=state,
        vector_fragment_id=vector_digest["output_fragment_ids"][0],
        insert_fragment_ids=[insert_digest["output_fragment_ids"][0]],
        ligase_name="T4 DNA ligase",
        vector_to_insert_molar_ratio=3.0,
        temperature_c=16.0,
        duration_minutes=960,
    )
    transform_result = transform_ligation(
        state=state,
        ligation_id=ligation["ligation_id"],
    )
    return state, vector_digest, insert_digest, ligation, transform_result


def test_restriction_digest_ecori_bamhi_linearizes_vector():
    state, vector_digest, _, _, _ = _run_good_clone_core("clone-good-digest", 1)
    assert vector_digest["status"] == "digested"
    assert vector_digest["enzymes_key"] == "bamhi+ecori"
    assert vector_digest["buffer_normalized"] == "cutsmart"
    assert vector_digest["output_fragment_ids"]


def test_restriction_digest_wrong_buffer_is_flagged():
    state = create_lab_state(sample_id="clone-wrong-buffer", seed=1)
    list_cloning_substrates(state=state)
    result = restriction_digest(
        state=state,
        fragment_id="puc19_vector",
        enzyme_names=["EcoRI", "BamHI"],
        buffer="NEB 1.1",
        temperature_c=37.0,
        duration_minutes=60,
        heat_inactivate_after=True,
    )
    assert result["status"] == "wrong_buffer"


def test_ligate_with_t4_yields_ligated_status():
    _, _, _, ligation, _ = _run_good_clone_core("clone-good-ligate", 1)
    assert ligation["status"] == "ligated"
    assert ligation["ligase_normalized"] == "t4 dna ligase"


def test_ligate_with_wrong_ligase_reports_wrong_ligase():
    state, vector_digest, insert_digest, _, _ = _run_good_clone_core("clone-wrong-ligase", 1)
    bad_ligation = ligate(
        state=state,
        vector_fragment_id=vector_digest["output_fragment_ids"][0],
        insert_fragment_ids=[insert_digest["output_fragment_ids"][0]],
        ligase_name="E. coli DNA ligase",
        vector_to_insert_molar_ratio=3.0,
        temperature_c=16.0,
        duration_minutes=960,
    )
    assert bad_ligation["status"] == "wrong_ligase"


def test_ligate_warns_when_only_one_parent_digest_was_heat_inactivated():
    state = create_lab_state(sample_id="clone-partial-heat-kill", seed=1)
    list_cloning_substrates(state=state)
    vector_digest = restriction_digest(
        state=state,
        fragment_id="puc19_vector",
        enzyme_names=["EcoRI", "BamHI"],
        buffer="CutSmart",
        temperature_c=37.0,
        duration_minutes=60,
        heat_inactivate_after=True,
    )
    insert_digest = restriction_digest(
        state=state,
        fragment_id="insert_raw",
        enzyme_names=["EcoRI", "BamHI"],
        buffer="CutSmart",
        temperature_c=37.0,
        duration_minutes=60,
        heat_inactivate_after=False,
    )
    ligation = ligate(
        state=state,
        vector_fragment_id=vector_digest["output_fragment_ids"][0],
        insert_fragment_ids=[insert_digest["output_fragment_ids"][0]],
        ligase_name="T4 DNA ligase",
        vector_to_insert_molar_ratio=3.0,
        temperature_c=16.0,
        duration_minutes=960,
    )
    assert ligation["status"] == "ligated"
    assert any("not heat-inactivated" in note for note in ligation["notes"])


def test_ligate_tracks_heat_inactivation_per_output_digest_not_parent_substrate():
    state = create_lab_state(sample_id="clone-digest-provenance", seed=1)
    list_cloning_substrates(state=state)
    restriction_digest(
        state=state,
        fragment_id="puc19_vector",
        enzyme_names=["EcoRI", "BamHI"],
        buffer="CutSmart",
        temperature_c=37.0,
        duration_minutes=60,
        heat_inactivate_after=True,
    )
    vector_digest_without_heat = restriction_digest(
        state=state,
        fragment_id="puc19_vector",
        enzyme_names=["EcoRI", "BamHI"],
        buffer="CutSmart",
        temperature_c=37.0,
        duration_minutes=60,
        heat_inactivate_after=False,
    )
    insert_digest = restriction_digest(
        state=state,
        fragment_id="insert_raw",
        enzyme_names=["EcoRI", "BamHI"],
        buffer="CutSmart",
        temperature_c=37.0,
        duration_minutes=60,
        heat_inactivate_after=True,
    )

    ligation = ligate(
        state=state,
        vector_fragment_id=vector_digest_without_heat["output_fragment_ids"][0],
        insert_fragment_ids=[insert_digest["output_fragment_ids"][0]],
        ligase_name="T4 DNA ligase",
        vector_to_insert_molar_ratio=3.0,
        temperature_c=16.0,
        duration_minutes=960,
    )

    assert ligation["status"] == "ligated"
    assert ligation["source_digest_ids"] == [
        vector_digest_without_heat["digest_id"],
        insert_digest["digest_id"],
    ]
    assert any("not heat-inactivated" in note for note in ligation["notes"])


def test_transform_ligation_produces_culture_and_screening_plate():
    state, _, _, ligation, transform_result = _run_good_clone_core("clone-good-transform", 1)
    assert transform_result["status"] == "transformed"
    assert transform_result["ligation_id"] == ligation["ligation_id"]
    assert state.screening_plates
    plate_id = next(iter(state.screening_plates))
    plate = state.screening_plates[plate_id]
    assert len([c for c in plate.colonies.values() if c.color == "white"]) == 12
    assert len([c for c in plate.colonies.values() if c.color == "blue"]) == 18


def test_clone_workflow_is_deterministic_on_same_seed():
    state_a, _, _, ligation_a, transform_a = _run_good_clone_core("clone-det-a", 42)
    state_b, _, _, ligation_b, transform_b = _run_good_clone_core("clone-det-b", 42)
    assert transform_a == transform_b
    recombinants_a = sorted(
        c.colony_id
        for c in next(iter(state_a.screening_plates.values())).colonies.values()
        if c.is_recombinant
    )
    recombinants_b = sorted(
        c.colony_id
        for c in next(iter(state_b.screening_plates.values())).colonies.values()
        if c.is_recombinant
    )
    assert recombinants_a == recombinants_b


GOLDEN_GATE_PARAMETERS_PATH = (
    Path(__file__).resolve().parents[1] / "data" / "parameters" / "golden_gate.json"
)


def _run_good_golden_gate_core(sample_id: str, seed: int):
    state = create_lab_state(sample_id=sample_id, seed=seed)
    list_golden_gate_substrates(state=state)
    assembly = golden_gate_assembly(
        state=state,
        fragment_ids=[
            "gg_backbone",
            "gg_insert_promoter",
            "gg_insert_cds",
            "gg_insert_terminator",
        ],
        enzyme_name="BsaI",
        ligase_name="T4 DNA ligase",
        cycle_count=30,
        digest_temperature_c=37.0,
        ligate_temperature_c=16.0,
    )
    return state, assembly


def test_golden_gate_parameter_bundle_exposes_required_values():
    bundle = load_golden_gate_parameters(GOLDEN_GATE_PARAMETERS_PATH)
    assert bundle.value("digest_cycling_temperature_c") == pytest.approx(37.0)
    assert bundle.value("ligate_cycling_temperature_c") == pytest.approx(16.0)
    assert bundle.integer("required_cycle_count") == 30
    assert bundle.integer("fragment_count") == 4
    assert set(bundle.choices("accepted_type_iis_enzymes")) == {"BsaI", "BsaI-HFv2"}
    assert "T4 DNA ligase buffer" in bundle.choices("accepted_one_pot_buffers")
    assert bundle.text("preferred_ligase_name") == "T4 DNA ligase"
    assert bundle.value("final_digest_temperature_c") == pytest.approx(60.0)
    assert bundle.integer("final_digest_duration_minutes") == 5


def test_list_golden_gate_substrates_returns_four_fragments():
    state = create_lab_state(sample_id="gg-list", seed=1)
    observation = list_golden_gate_substrates(state=state)
    assert observation["status"] == "golden_gate_substrates_ready"
    fragment_ids = {f["fragment_id"] for f in observation["fragments"]}
    assert {"gg_backbone", "gg_insert_promoter", "gg_insert_cds", "gg_insert_terminator"} == fragment_ids
    assert all(fragment["recognition_sites"] == ["BsaI"] for fragment in observation["fragments"])


def test_golden_gate_assembly_happy_path_status():
    _, assembly = _run_good_golden_gate_core("gg-happy", 1)
    assert assembly["status"] == "assembled"
    assert assembly["enzyme_normalized"] == "bsai"
    assert assembly["ligase_normalized"] == "t4 dna ligase"
    assert assembly["fragment_count"] == 4
    assert assembly["output_fragment_id"] is not None
    assert assembly["final_digest_temperature_c"] == pytest.approx(60.0)


def test_golden_gate_bsai_hfv2_is_compatible_with_bsai_flanked_substrates():
    state = create_lab_state(sample_id="gg-bsai-hfv2", seed=1)
    list_golden_gate_substrates(state=state)
    result = golden_gate_assembly(
        state=state,
        fragment_ids=[
            "gg_backbone",
            "gg_insert_promoter",
            "gg_insert_cds",
            "gg_insert_terminator",
        ],
        enzyme_name="BsaI-HFv2",
        ligase_name="T4 DNA ligase",
    )

    assert result["status"] == "assembled"
    assert result["enzyme_normalized"] == "bsai"
    assert result["output_fragment_id"] is not None


def test_golden_gate_wrong_enzyme_is_flagged():
    state = create_lab_state(sample_id="gg-wrong-enzyme", seed=1)
    list_golden_gate_substrates(state=state)
    result = golden_gate_assembly(
        state=state,
        fragment_ids=[
            "gg_backbone",
            "gg_insert_promoter",
            "gg_insert_cds",
            "gg_insert_terminator",
        ],
        enzyme_name="EcoRI",
        ligase_name="T4 DNA ligase",
    )
    assert result["status"] == "wrong_enzyme"


@pytest.mark.parametrize("enzyme_name", ("BsmBI", "BsmBI-v2"))
def test_golden_gate_rejects_other_type_iis_sites_for_bsai_flanked_substrates(enzyme_name):
    state = create_lab_state(sample_id="gg-incompatible-site", seed=1)
    list_golden_gate_substrates(state=state)
    result = golden_gate_assembly(
        state=state,
        fragment_ids=[
            "gg_backbone",
            "gg_insert_promoter",
            "gg_insert_cds",
            "gg_insert_terminator",
        ],
        enzyme_name=enzyme_name,
        ligase_name="T4 DNA ligase",
    )

    assert result["status"] == "wrong_enzyme"
    assert result["output_fragment_id"] is None


@pytest.mark.parametrize("enzyme_name", ("BsaI-v2", "BsaI-HF", "BsaI-HFv3"))
def test_golden_gate_rejects_undeclared_bsai_variants(enzyme_name):
    state = create_lab_state(sample_id="gg-undeclared-enzyme", seed=1)
    list_golden_gate_substrates(state=state)
    result = golden_gate_assembly(
        state=state,
        fragment_ids=[
            "gg_backbone",
            "gg_insert_promoter",
            "gg_insert_cds",
            "gg_insert_terminator",
        ],
        enzyme_name=enzyme_name,
        ligase_name="T4 DNA ligase",
    )

    assert result["status"] == "wrong_enzyme"
    assert result["output_fragment_id"] is None


def test_golden_gate_requires_every_fragment_to_match_the_selected_enzyme():
    state = create_lab_state(sample_id="gg-mixed-sites", seed=1)
    list_golden_gate_substrates(state=state)
    state.dna_fragments["gg_insert_cds"].recognition_sites = ["BsmBI"]
    result = golden_gate_assembly(
        state=state,
        fragment_ids=[
            "gg_backbone",
            "gg_insert_promoter",
            "gg_insert_cds",
            "gg_insert_terminator",
        ],
        enzyme_name="BsaI",
        ligase_name="T4 DNA ligase",
    )

    assert result["status"] == "wrong_enzyme"
    assert result["output_fragment_id"] is None


@pytest.mark.parametrize(
    "buffer",
    ("water", "rCutSmart Buffer", "NEBuffer r3.1", "T4 DNA Ligase buffer (water)"),
)
def test_golden_gate_rejects_buffers_without_the_one_pot_ligation_contract(buffer):
    state = create_lab_state(sample_id="gg-wrong-buffer", seed=1)
    list_golden_gate_substrates(state=state)
    result = golden_gate_assembly(
        state=state,
        fragment_ids=[
            "gg_backbone",
            "gg_insert_promoter",
            "gg_insert_cds",
            "gg_insert_terminator",
        ],
        enzyme_name="BsaI",
        ligase_name="T4 DNA ligase",
        buffer=buffer,
    )

    assert result["status"] == "wrong_buffer"
    assert result["output_fragment_id"] is None


@pytest.mark.parametrize(
    "buffer",
    (
        "T4 DNA Ligase Buffer (10X)",
        "1X T4 DNA Ligase Reaction Buffer",
        "ATP-containing T4 DNA ligase buffer",
    ),
)
def test_golden_gate_accepts_agent_visible_t4_buffer_aliases(buffer):
    state = create_lab_state(sample_id="gg-buffer-alias", seed=1)
    list_golden_gate_substrates(state=state)
    result = golden_gate_assembly(
        state=state,
        fragment_ids=[
            "gg_backbone",
            "gg_insert_promoter",
            "gg_insert_cds",
            "gg_insert_terminator",
        ],
        enzyme_name="BsaI",
        ligase_name="T4 DNA ligase",
        buffer=buffer,
    )

    assert result["status"] == "assembled"
    assert result["output_fragment_id"] is not None


def test_golden_gate_accepts_exact_agent_visible_t4_buffer_reference():
    database_path = Path(__file__).resolve().parents[1] / "data" / "enzyme_database.json"
    database = json.loads(database_path.read_text())
    t4_ligase = next(entry for entry in database if entry["name"] == "T4 DNA ligase")

    state = create_lab_state(sample_id="gg-reference-buffer", seed=1)
    list_golden_gate_substrates(state=state)
    result = golden_gate_assembly(
        state=state,
        fragment_ids=[
            "gg_backbone",
            "gg_insert_promoter",
            "gg_insert_cds",
            "gg_insert_terminator",
        ],
        enzyme_name="BsaI",
        ligase_name="T4 DNA ligase",
        buffer=t4_ligase["buffer"],
    )

    assert result["status"] == "assembled"
    assert result["output_fragment_id"] is not None


@pytest.mark.parametrize(
    "terminal_kwargs",
    (
        {"final_digest_minutes": 0},
        {"final_digest_minutes": -5},
        {"final_digest_minutes": 10},
        {"final_digest_temperature_c": 0.0},
        {"final_digest_temperature_c": 80.0},
    ),
)
def test_golden_gate_rejects_wrong_terminal_digest(terminal_kwargs):
    state = create_lab_state(sample_id="gg-wrong-terminal", seed=1)
    list_golden_gate_substrates(state=state)
    result = golden_gate_assembly(
        state=state,
        fragment_ids=[
            "gg_backbone",
            "gg_insert_promoter",
            "gg_insert_cds",
            "gg_insert_terminator",
        ],
        enzyme_name="BsaI",
        ligase_name="T4 DNA ligase",
        **terminal_kwargs,
    )

    assert result["status"] == "wrong_terminal_digest"
    assert result["output_fragment_id"] is None


@pytest.mark.parametrize(
    "thermal_kwargs",
    (
        {"cycle_count": -1},
        {"cycle_count": 0},
        {"cycle_count": 25},
        {"cycle_count": 999},
        {"digest_temperature_c": 0.0},
        {"digest_temperature_c": 35.0},
        {"digest_temperature_c": 39.0},
        {"ligate_temperature_c": 14.0},
        {"ligate_temperature_c": 20.0},
        {"ligate_temperature_c": 99.0},
    ),
)
def test_golden_gate_rejects_noncanonical_thermal_program(thermal_kwargs):
    state = create_lab_state(sample_id="gg-wrong-thermal", seed=1)
    list_golden_gate_substrates(state=state)
    result = golden_gate_assembly(
        state=state,
        fragment_ids=[
            "gg_backbone",
            "gg_insert_promoter",
            "gg_insert_cds",
            "gg_insert_terminator",
        ],
        enzyme_name="BsaI",
        ligase_name="T4 DNA ligase",
        **thermal_kwargs,
    )

    assert result["status"] == "wrong_thermal_program"
    assert result["output_fragment_id"] is None


def test_golden_gate_wrong_ligase_is_flagged():
    state = create_lab_state(sample_id="gg-wrong-ligase", seed=1)
    list_golden_gate_substrates(state=state)
    result = golden_gate_assembly(
        state=state,
        fragment_ids=[
            "gg_backbone",
            "gg_insert_promoter",
            "gg_insert_cds",
            "gg_insert_terminator",
        ],
        enzyme_name="BsaI",
        ligase_name="E. coli DNA ligase",
    )
    assert result["status"] == "wrong_ligase"


def test_golden_gate_duplicate_fragment_is_flagged_even_with_four_inputs():
    state = create_lab_state(sample_id="gg-duplicate-fragment", seed=1)
    list_golden_gate_substrates(state=state)
    result = golden_gate_assembly(
        state=state,
        fragment_ids=[
            "gg_backbone",
            "gg_insert_promoter",
            "gg_insert_cds",
            "gg_insert_cds",
        ],
        enzyme_name="BsaI",
        ligase_name="T4 DNA ligase",
    )
    assert result["status"] == "wrong_fragment_count"
    assert result["output_fragment_id"] is None


def test_transform_assembly_produces_culture():
    state, assembly = _run_good_golden_gate_core("gg-transform", 42)
    result = transform_assembly(state=state, assembly_id=assembly["assembly_id"])
    assert result["status"] == "transformed"
    assert result["assembly_id"] == assembly["assembly_id"]
    assert result["effective_assembly_efficiency"] > 0.5


GIBSON_PARAMETERS_PATH = (
    Path(__file__).resolve().parents[1] / "data" / "parameters" / "gibson.json"
)


def test_gibson_parameter_bundle_exposes_required_values():
    bundle = load_gibson_parameters(GIBSON_PARAMETERS_PATH)
    assert bundle.value("optimal_temperature_c") == pytest.approx(50.0)
    assert bundle.integer("minimum_duration_minutes_two_fragments") == 15
    assert bundle.integer("maximum_duration_minutes_two_fragments") == 60
    assert bundle.integer("task_overlap_length_bp") == 20
    assert bundle.integer("fragment_count") == 2
    assert all(
        canonicalize_gibson_master_mix(mix) is not None
        for mix in bundle.choices("accepted_master_mixes")
    )


def test_list_gibson_substrates_returns_two_fragments():
    state = create_lab_state(sample_id="gibson-list", seed=1)
    observation = list_gibson_substrates(state=state)
    assert observation["status"] == "gibson_substrates_ready"
    fragment_ids = {f["fragment_id"] for f in observation["fragments"]}
    assert {"gibson_backbone_linear", "gibson_insert_pcr"} == fragment_ids


def test_gibson_assembly_happy_path():
    state = create_lab_state(sample_id="gibson-happy", seed=1)
    list_gibson_substrates(state=state)
    result = gibson_assembly(
        state=state,
        fragment_ids=["gibson_backbone_linear", "gibson_insert_pcr"],
        master_mix_name="Gibson Assembly Master Mix",
        temperature_c=50.0,
        duration_minutes=15,
        overlap_length_bp=20,
    )
    assert result["status"] == "assembled"
    assert result["output_fragment_id"] is not None


@pytest.mark.parametrize(
    "master_mix_name",
    (
        "Gibson Assembly Master Mix",
        "Gibson® Assembly Master Mix",
        "NEBuilder HiFi",
        "NEBuilder HiFi DNA Assembly Master Mix",
        "NEBuilder HiFi DNA Assembly Master Mix (2X)",
        "NEBuilder® HiFi DNA Assembly Master Mix",
        "ISO buffer + T5 exo + Phusion + Taq ligase",
        "ISO buffer + T5 exo + Phusion DNA polymerase + Taq ligase",
        "ISO buffer + T5 exonuclease + Phusion polymerase + Taq DNA ligase",
        "ISO buffer + T5 exonuclease + Phusion DNA polymerase + Taq DNA ligase",
    ),
)
def test_gibson_accepts_only_canonical_master_mix_aliases(master_mix_name):
    state = create_lab_state(sample_id="gibson-valid-mix", seed=1)
    list_gibson_substrates(state=state)
    result = gibson_assembly(
        state=state,
        fragment_ids=["gibson_backbone_linear", "gibson_insert_pcr"],
        master_mix_name=master_mix_name,
        temperature_c=50.0,
        duration_minutes=15,
        overlap_length_bp=20,
    )
    assert result["status"] == "assembled"
    assert result["output_fragment_id"] is not None


@pytest.mark.parametrize(
    "master_mix_name",
    (
        "",
        "a",
        "mix",
        "HiFi",
        "HiFi Assembly",
        "T5 exo",
        "not Gibson Assembly Master Mix",
        "water plus NEBuilder HiFi but no enzymes",
    ),
)
def test_gibson_rejects_partial_or_adversarial_master_mix_substrings(master_mix_name):
    state = create_lab_state(sample_id="gibson-adversarial-mix", seed=1)
    list_gibson_substrates(state=state)
    result = gibson_assembly(
        state=state,
        fragment_ids=["gibson_backbone_linear", "gibson_insert_pcr"],
        master_mix_name=master_mix_name,
        temperature_c=50.0,
        duration_minutes=15,
        overlap_length_bp=20,
    )
    assert result["status"] == "wrong_master_mix"
    assert result["output_fragment_id"] is None


@pytest.mark.parametrize(
    "overrides",
    (
        {"temperature_c": 0.0},
        {"temperature_c": -273.0},
        {"duration_minutes": 0},
        {"duration_minutes": -1},
        {"overlap_length_bp": 0},
        {"overlap_length_bp": -20},
    ),
    ids=(
        "zero-temperature",
        "negative-temperature",
        "zero-duration",
        "negative-duration",
        "zero-overlap",
        "negative-overlap",
    ),
)
def test_gibson_rejects_nonpositive_physical_inputs(overrides):
    state = create_lab_state(sample_id="gibson-nonpositive", seed=1)
    list_gibson_substrates(state=state)
    arguments = {
        "fragment_ids": ["gibson_backbone_linear", "gibson_insert_pcr"],
        "master_mix_name": "Gibson Assembly Master Mix",
        "temperature_c": 50.0,
        "duration_minutes": 15,
        "overlap_length_bp": 20,
    }
    arguments.update(overrides)
    with pytest.raises(ValueError):
        gibson_assembly(state=state, **arguments)


@pytest.mark.parametrize(
    "overrides",
    (
        {"temperature_c": 1.0},
        {"temperature_c": 48.0},
        {"temperature_c": 52.0},
        {"duration_minutes": 14},
        {"duration_minutes": 61},
        {"overlap_length_bp": 19},
        {"overlap_length_bp": 80},
    ),
    ids=(
        "wrong-positive-temperature",
        "low-temperature-boundary",
        "high-temperature-boundary",
        "short-duration-boundary",
        "long-duration-boundary",
        "short-overlap-boundary",
        "wrong-supplied-overlap",
    ),
)
def test_gibson_invalid_contract_never_produces_assembled_output(overrides):
    state = create_lab_state(sample_id="gibson-invalid-contract", seed=1)
    list_gibson_substrates(state=state)
    arguments = {
        "fragment_ids": ["gibson_backbone_linear", "gibson_insert_pcr"],
        "master_mix_name": "Gibson Assembly Master Mix",
        "temperature_c": 50.0,
        "duration_minutes": 15,
        "overlap_length_bp": 20,
    }
    arguments.update(overrides)
    result = gibson_assembly(state=state, **arguments)
    assert result["status"] != "assembled"
    assert result["output_fragment_id"] is None


def test_gibson_wrong_master_mix_is_flagged():
    state = create_lab_state(sample_id="gibson-wrong-mix", seed=1)
    list_gibson_substrates(state=state)
    result = gibson_assembly(
        state=state,
        fragment_ids=["gibson_backbone_linear", "gibson_insert_pcr"],
        master_mix_name="T4 DNA ligase buffer",
        temperature_c=50.0,
        duration_minutes=15,
        overlap_length_bp=20,
    )
    assert result["status"] == "wrong_master_mix"


def test_gibson_duplicate_fragment_is_flagged_even_with_two_inputs():
    state = create_lab_state(sample_id="gibson-duplicate-fragment", seed=1)
    list_gibson_substrates(state=state)
    result = gibson_assembly(
        state=state,
        fragment_ids=["gibson_backbone_linear", "gibson_backbone_linear"],
        master_mix_name="Gibson Assembly Master Mix",
        temperature_c=50.0,
        duration_minutes=15,
        overlap_length_bp=20,
    )
    assert result["status"] == "wrong_fragment_count"
    assert result["output_fragment_id"] is None


def _assembled_gibson_for_transform_validation(sample_id):
    state = create_lab_state(sample_id=sample_id, seed=42)
    list_gibson_substrates(state=state)
    assembly = gibson_assembly(
        state=state,
        fragment_ids=["gibson_backbone_linear", "gibson_insert_pcr"],
        master_mix_name="Gibson Assembly Master Mix",
        temperature_c=50.0,
        duration_minutes=15,
        overlap_length_bp=20,
    )
    assert assembly["status"] == "assembled"
    return state, assembly


@pytest.mark.parametrize(
    "overrides",
    (
        {"heat_shock_seconds": 0},
        {"heat_shock_seconds": -1},
        {"recovery_minutes": -1},
        {"ice_incubation_minutes": -1},
        {"outgrowth_media": ""},
        {"outgrowth_media": "   "},
    ),
    ids=(
        "zero-heat-shock",
        "negative-heat-shock",
        "negative-recovery",
        "negative-ice-incubation",
        "empty-outgrowth",
        "whitespace-outgrowth",
    ),
)
def test_transform_gibson_rejects_invalid_inputs(overrides):
    state, assembly = _assembled_gibson_for_transform_validation("gibson-invalid-transform")
    with pytest.raises(ValueError):
        transform_gibson(state=state, gibson_id=assembly["gibson_id"], **overrides)


def test_transform_gibson_fails_closed_for_unsupported_outgrowth():
    state, assembly = _assembled_gibson_for_transform_validation(
        "gibson-unsupported-outgrowth"
    )
    result = transform_gibson(
        state=state,
        gibson_id=assembly["gibson_id"],
        outgrowth_media="water",
    )
    assert result["status"] == "invalid_outgrowth_media"
    assert result["expected_transformants"] == 0.0


def test_transform_gibson_produces_culture():
    state = create_lab_state(sample_id="gibson-transform", seed=42)
    list_gibson_substrates(state=state)
    result = gibson_assembly(
        state=state,
        fragment_ids=["gibson_backbone_linear", "gibson_insert_pcr"],
        master_mix_name="NEBuilder HiFi",
        temperature_c=50.0,
        duration_minutes=30,
        overlap_length_bp=20,
    )
    tx = transform_gibson(state=state, gibson_id=result["gibson_id"])
    assert tx["status"] == "transformed"
    assert tx["gibson_id"] == result["gibson_id"]


MINIPREP_PARAMETERS_PATH = (
    Path(__file__).resolve().parents[1] / "data" / "parameters" / "miniprep.json"
)


def test_miniprep_parameter_bundle_exposes_required_values():
    bundle = load_miniprep_parameters(MINIPREP_PARAMETERS_PATH)
    assert bundle.text("canonical_lysis_buffer_sequence") == "P1,P2,N3"
    assert bundle.value("culture_volume_ml_optimal") == pytest.approx(5.0)
    assert bundle.integer("lysis_duration_minutes_max") == 5
    assert bundle.integer("elution_volume_ul_min") == 50
    assert bundle.integer("elution_volume_ul_max") == 100
    accepted_methods = bundle.choices("accepted_purification_methods")
    assert accepted_methods
    assert all("qiaprep" in method.casefold() for method in accepted_methods)
    assert all(
        canonicalize_miniprep_purification_method(method)
        == MINIPREP_PURIFICATION_METHOD_CANONICAL
        for method in accepted_methods
    )


def _new_miniprep_state(sample_id="miniprep-test"):
    state = create_lab_state(sample_id=sample_id, seed=1)
    initialize_miniprep_source_culture(state)
    return state


def _perform_standard_miniprep(state, **overrides):
    arguments = {
        "culture_id": MINIPREP_SOURCE_CULTURE_ID,
        "culture_volume_ml": 5.0,
        "lysis_buffer_sequence": "P1,P2,N3",
        "lysis_duration_min": 3,
        "purification_method": "QIAprep silica spin column",
        "elution_volume_ul": 50.0,
    }
    arguments.update(overrides)
    return perform_miniprep(state=state, **arguments)


def _miniprep_mutation_snapshot(state):
    return {
        "counter": state.miniprep_counter,
        "samples": copy.deepcopy(state.miniprep_samples),
        "cultures": copy.deepcopy(state.miniprep_cultures),
        "events": copy.deepcopy(state.event_log),
        "rng": state.rng.getstate(),
    }


def test_miniprep_happy_path():
    state = _new_miniprep_state("miniprep-happy")
    result = _perform_standard_miniprep(state)

    assert result["status"] == "prepared"
    assert result["preparation_accepted"] is True
    assert result["failure_reasons"] == []
    assert result["culture_id"] == MINIPREP_SOURCE_CULTURE_ID
    assert result["miniprep_id"] == "miniprep_001"
    assert result["lysis_buffer_sequence_canonical"] == MINIPREP_BUFFER_SEQUENCE_CANONICAL
    assert result["purification_method_canonical"] == MINIPREP_PURIFICATION_METHOD_CANONICAL
    assert result["elution_volume_ul"] == MINIPREP_ELUTION_VOLUME_UL
    assert result["a260_a280_ratio"] == pytest.approx(1.8)
    assert result["total_yield_ug"] == pytest.approx(10.0)
    assert result["final_concentration_ng_ul"] == pytest.approx(200.0)
    assert result["source_culture_remaining_volume_ml"] == pytest.approx(0.0)
    assert state.miniprep_samples[result["miniprep_id"]].culture_id == MINIPREP_SOURCE_CULTURE_ID


@pytest.mark.parametrize(
    "label",
    (
        "P1,P2,N3",
        "P1 -> P2 -> N3",
        "P1/P2/N3",
        "Buffer P1 -> Buffer P2 -> Buffer N3",
        "resuspension, lysis, neutralization",
        "P1 (resuspension), P2 (alkaline lysis), N3 (neutralization)",
    ),
)
def test_miniprep_buffer_allowlist_accepts_explicit_equivalent_labels(label):
    assert canonicalize_miniprep_buffer_sequence(label) == MINIPREP_BUFFER_SEQUENCE_CANONICAL


@pytest.mark.parametrize(
    "label",
    (
        "P1,P2,P3",
        "P1,P2,N3,N3",
        "P1 then lysis then N3",
        "standard alkaline lysis buffers",
        "not P1/P2/N3",
    ),
)
def test_miniprep_buffer_allowlist_rejects_near_misses(label):
    assert canonicalize_miniprep_buffer_sequence(label) is None


@pytest.mark.parametrize(
    "label",
    (
        "QIAprep spin column",
        "QIAprep 2.0 spin column",
        "QIAprep 2.0 Spin Columns",
        "QIAprep 2.0 silica-membrane spin column",
        "QIAprep-compatible silica-membrane spin column",
    ),
)
def test_miniprep_method_allowlist_accepts_explicit_silica_spin_aliases(label):
    assert canonicalize_miniprep_purification_method(label) == MINIPREP_PURIFICATION_METHOD_CANONICAL


@pytest.mark.parametrize(
    "label",
    (
        "QIAGEN column",
        "anion exchange column",
        "silica column",
        "silica spin column",
        "silica membrane column",
        "silica-membrane spin column",
        "silica beads",
        "spin column",
        "not a silica column",
    ),
)
def test_miniprep_method_allowlist_rejects_near_misses(label):
    assert canonicalize_miniprep_purification_method(label) is None


def test_miniprep_operation_accepts_functional_buffer_and_silica_spin_aliases():
    state = _new_miniprep_state("miniprep-functional-aliases")
    result = _perform_standard_miniprep(
        state,
        lysis_buffer_sequence="resuspension, lysis, neutralization",
        purification_method="QIAprep 2.0 spin column",
    )

    assert result["status"] == "prepared"
    assert result["lysis_buffer_sequence_canonical"] == MINIPREP_BUFFER_SEQUENCE_CANONICAL
    assert result["purification_method_canonical"] == MINIPREP_PURIFICATION_METHOD_CANONICAL


def test_miniprep_accepts_supported_100_ul_elution_with_lower_concentration():
    state = _new_miniprep_state("miniprep-100-ul-elution")
    result = _perform_standard_miniprep(state, elution_volume_ul=100.0)

    assert result["status"] == "prepared"
    assert result["preparation_accepted"] is True
    assert result["total_yield_ug"] == pytest.approx(10.0)
    assert result["final_concentration_ng_ul"] == pytest.approx(100.0)


def test_miniprep_operation_rejects_generic_qiagen_column_near_miss():
    state = _new_miniprep_state("miniprep-method-near-miss")
    result = _perform_standard_miniprep(state, purification_method="QIAGEN column")

    assert result["status"] == MINIPREP_FAILURE_WRONG_METHOD
    assert result["failure_reasons"] == [MINIPREP_FAILURE_WRONG_METHOD]


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("culture_volume_ml", 0.0),
        ("culture_volume_ml", -1.0),
        ("culture_volume_ml", float("nan")),
        ("culture_volume_ml", float("inf")),
        ("culture_volume_ml", True),
        ("lysis_duration_min", 0),
        ("lysis_duration_min", -1),
        ("lysis_duration_min", 1.5),
        ("lysis_duration_min", float("nan")),
        ("lysis_duration_min", float("inf")),
        ("lysis_duration_min", True),
        ("elution_volume_ul", 0.0),
        ("elution_volume_ul", -1.0),
        ("elution_volume_ul", float("nan")),
        ("elution_volume_ul", float("inf")),
        ("elution_volume_ul", True),
    ),
)
def test_miniprep_rejects_malformed_numeric_inputs_without_mutating_state(field, value):
    state = _new_miniprep_state("miniprep-invalid-{}-{}".format(field, value))
    before = _miniprep_mutation_snapshot(state)

    with pytest.raises(ValueError):
        _perform_standard_miniprep(state, **{field: value})

    assert _miniprep_mutation_snapshot(state) == before


@pytest.mark.parametrize(
    ("overrides", "expected_failure"),
    (
        ({"culture_volume_ml": 0.5}, MINIPREP_FAILURE_CULTURE_VOLUME),
        ({"culture_volume_ml": 5.1}, MINIPREP_FAILURE_CULTURE_VOLUME),
        ({"lysis_duration_min": 6}, MINIPREP_FAILURE_OVERLYSIS),
        ({"elution_volume_ul": 30.0}, MINIPREP_FAILURE_ELUTION),
        ({"elution_volume_ul": 101.0}, MINIPREP_FAILURE_ELUTION),
    ),
)
def test_miniprep_finite_out_of_contract_values_emit_explicit_failure(overrides, expected_failure):
    state = _new_miniprep_state("miniprep-contract-failure")
    result = _perform_standard_miniprep(state, **overrides)

    assert result["preparation_accepted"] is False
    assert expected_failure in result["failure_reasons"]
    assert result["status"] == result["failure_reasons"][0]


def test_miniprep_wrong_buffer_sequence_flagged():
    state = _new_miniprep_state("miniprep-wrong-buffer")
    result = _perform_standard_miniprep(state, lysis_buffer_sequence="P3,P2,P1")
    assert result["status"] == "wrong_buffer_sequence"
    assert result["failure_reasons"] == [MINIPREP_FAILURE_WRONG_BUFFER]


def test_miniprep_overlysis_flagged():
    state = _new_miniprep_state("miniprep-overlysis")
    result = _perform_standard_miniprep(state, lysis_duration_min=15)
    assert result["status"] == MINIPREP_FAILURE_OVERLYSIS
    assert result["failure_reasons"] == [MINIPREP_FAILURE_OVERLYSIS]


def test_miniprep_reports_every_simultaneous_contract_failure_in_stable_order():
    state = _new_miniprep_state("miniprep-multiple-failures")
    result = _perform_standard_miniprep(
        state,
        culture_volume_ml=0.5,
        lysis_buffer_sequence="P1,P2,P3",
        lysis_duration_min=6,
        purification_method="anion exchange column",
        elution_volume_ul=30.0,
    )

    assert result["failure_reasons"] == [
        MINIPREP_FAILURE_CULTURE_VOLUME,
        MINIPREP_FAILURE_WRONG_BUFFER,
        MINIPREP_FAILURE_OVERLYSIS,
        MINIPREP_FAILURE_WRONG_METHOD,
        MINIPREP_FAILURE_ELUTION,
    ]
    assert result["status"] == MINIPREP_FAILURE_CULTURE_VOLUME
    assert result["preparation_accepted"] is False


@pytest.mark.parametrize(
    "mutation",
    ("unknown", "non_overnight", "wrong_plasmid", "depleted"),
)
def test_miniprep_rejects_invalid_source_cultures_without_mutating_state(mutation):
    state = _new_miniprep_state("miniprep-invalid-culture-{}".format(mutation))
    arguments = {}
    source = state.miniprep_cultures[MINIPREP_SOURCE_CULTURE_ID]
    if mutation == "unknown":
        arguments["culture_id"] = "missing_miniprep_culture"
    elif mutation == "non_overnight":
        source.is_overnight = False
    elif mutation == "wrong_plasmid":
        source.is_plasmid_bearing = False
    elif mutation == "depleted":
        source.available_volume_ml = 0.0
        source.consumed_volume_ml = 5.0
    before = _miniprep_mutation_snapshot(state)

    with pytest.raises(ValueError):
        _perform_standard_miniprep(state, **arguments)

    assert _miniprep_mutation_snapshot(state) == before


EXPRESSION_PARAMETERS_PATH = (
    Path(__file__).resolve().parents[1] / "data" / "parameters" / "expression.json"
)


def test_expression_parameter_bundle_exposes_required_values():
    bundle = load_expression_parameters(EXPRESSION_PARAMETERS_PATH)
    assert "BL21(DE3)" in bundle.choices("accepted_host_strains")
    assert bundle.number_list("iptg_concentration_mm_acceptable_range") == [0.5, 1.0]
    assert bundle.number_list("induction_od600_range") == [0.5, 0.8]
    assert "low_temperature_extended" in bundle.choices("induction_schedule_profiles")
    assert "37c_standard" in bundle.choices("induction_schedule_profiles")
    assert bundle.value("culture_volume_ml") == pytest.approx(500.0)


def _run_standard_expression(state, **updates):
    initialize_expression_construct(state)
    arguments = {
        "construct_id": EXPRESSION_CONSTRUCT_ID,
        "host_strain": "BL21(DE3)",
        "iptg_concentration_mm": 1.0,
        "induction_od600": 0.6,
        "induction_temperature_c": 18.0,
        "induction_hours": 16.0,
        "lysis_buffer_ph": 8.0,
    }
    arguments.update(updates)
    return run_protein_expression(state=state, **arguments)


def test_initialize_expression_construct_seeds_causal_benign_fixture():
    state = create_lab_state(sample_id="express-seed", seed=1)

    construct = initialize_expression_construct(state)

    assert construct.construct_id == EXPRESSION_CONSTRUCT_ID
    assert construct.promoter == "T7lac"
    assert construct.target_protein_name == "His6-MBP-GFP fusion"
    assert construct.is_benign is True
    assert construct.culture_volume_ml == pytest.approx(500.0)
    assert construct.usage_count == 0
    assert initialize_expression_construct(state) is construct


def test_run_protein_expression_happy_path():
    state = create_lab_state(sample_id="express-happy", seed=1)
    result = _run_standard_expression(state)

    assert result["status"] == EXPRESSION_SUCCESS_STATUS
    assert result["expression_accepted"] is True
    assert result["failure_reasons"] == []
    assert result["construct_id"] == EXPRESSION_CONSTRUCT_ID
    assert result["construct_usage_count"] == 1
    assert result["induction_schedule_profile"] == "low_temperature_extended"
    assert result["soluble_yield_mg_per_l"] == pytest.approx(36.8)
    assert result["total_soluble_mg"] == pytest.approx(18.4)
    assert result["lysate_prepared"] is True
    assert result["notes"] == []
    assert state.protein_expressions[result["expression_id"]].construct_id == EXPRESSION_CONSTRUCT_ID


def test_run_protein_expression_wrong_host_flagged():
    state = create_lab_state(sample_id="express-wrong-host", seed=1)
    result = _run_standard_expression(
        state,
        host_strain="not-BL21(DE3)-no-T7",
        induction_temperature_c=37.0,
        induction_hours=4.0,
    )

    assert result["status"] == EXPRESSION_FAILURE_HOST
    assert result["failure_reasons"] == [EXPRESSION_FAILURE_HOST]
    assert result["expression_accepted"] is False
    assert result["soluble_yield_mg_per_l"] == 0.0
    assert result["lysate_prepared"] is False


def test_run_protein_expression_wrong_ph_flagged():
    state = create_lab_state(sample_id="express-wrong-ph", seed=1)
    result = _run_standard_expression(
        state,
        induction_temperature_c=37.0,
        induction_hours=4.0,
        lysis_buffer_ph=5.0,
    )

    assert result["status"] == EXPRESSION_FAILURE_LYSIS_PH
    assert result["failure_reasons"] == [EXPRESSION_FAILURE_LYSIS_PH]


@pytest.mark.parametrize(
    ("label", "canonical"),
    (
        ("BL21 (DE3)", "BL21(DE3)"),
        ("BL21 Star™(DE3)", "BL21 Star(DE3)"),
        ("BL21(DE3)pLysS", "BL21(DE3) pLysS"),
        ("Rosetta (DE3)", "Rosetta(DE3)"),
    ),
)
def test_expression_host_canonicalizer_accepts_only_explicit_aliases(label, canonical):
    assert canonicalize_expression_host(label) == canonical


@pytest.mark.parametrize(
    "label",
    ("not BL21(DE3)", "BL21", "DE3", "BL21(DE3) and DH5alpha", ""),
)
def test_expression_host_canonicalizer_rejects_substring_and_ambiguous_labels(label):
    assert canonicalize_expression_host(label) is None


def test_run_protein_expression_records_all_failures_in_contract_order():
    state = create_lab_state(sample_id="express-all-failures", seed=1)

    result = _run_standard_expression(
        state,
        host_strain="DH5alpha",
        iptg_concentration_mm=1.5,
        induction_od600=2.0,
        induction_temperature_c=18.0,
        induction_hours=1.0,
        lysis_buffer_ph=5.0,
    )

    assert result["failure_reasons"] == [
        EXPRESSION_FAILURE_HOST,
        EXPRESSION_FAILURE_IPTG,
        EXPRESSION_FAILURE_OD600,
        EXPRESSION_FAILURE_SCHEDULE,
        EXPRESSION_FAILURE_LYSIS_PH,
    ]
    assert result["status"] == EXPRESSION_FAILURE_HOST
    assert len(result["notes"]) == 5
    assert result["soluble_yield_mg_per_l"] == 0.0


def _expression_mutation_snapshot(state):
    return {
        "expression_counter": state.expression_counter,
        "expressions": copy.deepcopy(state.protein_expressions),
        "constructs": copy.deepcopy(state.expression_constructs),
        "events": copy.deepcopy(state.event_log),
    }


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("iptg_concentration_mm", float("nan")),
        ("induction_od600", float("inf")),
        ("induction_temperature_c", True),
        ("induction_hours", "not-a-number"),
        ("lysis_buffer_ph", float("-inf")),
    ),
)
def test_run_protein_expression_rejects_malformed_scalars_without_mutation(field, value):
    state = create_lab_state(sample_id="express-invalid-{}".format(field), seed=1)
    initialize_expression_construct(state)
    before = _expression_mutation_snapshot(state)

    with pytest.raises(ValueError):
        _run_standard_expression(state, **{field: value})

    assert _expression_mutation_snapshot(state) == before


def test_run_protein_expression_requires_seeded_known_construct_without_mutation():
    state = create_lab_state(sample_id="express-unknown-construct", seed=1)
    before = _expression_mutation_snapshot(state)

    with pytest.raises(ValueError):
        run_protein_expression(
            state=state,
            construct_id="unknown_construct",
            host_strain="BL21(DE3)",
            iptg_concentration_mm=1.0,
            induction_od600=0.6,
            induction_temperature_c=18.0,
            induction_hours=16.0,
            lysis_buffer_ph=8.0,
        )

    assert _expression_mutation_snapshot(state) == before


def test_expression_tool_wrapper_uses_seeded_active_sample():
    sample_id = "express-wrapper"
    set_active_sample(sample_id, seed=1)
    initialize_expression_sample()

    observation = asyncio.run(
        run_protein_expression_call(
            construct_id=EXPRESSION_CONSTRUCT_ID,
            host_strain="BL21(DE3)",
            iptg_concentration_mm=1.0,
            induction_od600=0.6,
            induction_temperature_c=18.0,
            induction_hours=16.0,
            lysis_buffer_ph=8.0,
        )
    )
    result = json.loads(observation)

    assert result["status"] == EXPRESSION_SUCCESS_STATUS
    assert result["construct_id"] == EXPRESSION_CONSTRUCT_ID
    assert result["expression_id"] == "expression_001"
    cleanup_sample(sample_id)


PURIFICATION_PARAMETERS_PATH = (
    Path(__file__).resolve().parents[1] / "data" / "parameters" / "purification.json"
)


def test_purification_parameter_bundle_exposes_required_values():
    bundle = load_purification_parameters(PURIFICATION_PARAMETERS_PATH)
    assert "Ni-NTA" in bundle.choices("accepted_resins")
    load_range = bundle.number_list("load_imidazole_mm_range")
    assert load_range == [10.0, 20.0]
    assert bundle.value("elute_imidazole_mm_min") == pytest.approx(200.0)


def test_run_nta_purification_happy_path():
    state = create_lab_state(sample_id="purify-happy", seed=1)
    result = run_nta_purification(
        state=state,
        resin_name="Ni-NTA",
        load_imidazole_mm=20.0,
        wash_imidazole_mm=50.0,
        elute_imidazole_mm=250.0,
    )
    assert result["status"] == "purified"
    assert result["purity_percent"] >= 90.0
    assert "single_clean_band" in result["sds_page_result"]


def test_run_nta_purification_wrong_resin_flagged():
    state = create_lab_state(sample_id="purify-wrong-resin", seed=1)
    result = run_nta_purification(
        state=state,
        resin_name="glutathione agarose",
        load_imidazole_mm=20.0,
        wash_imidazole_mm=50.0,
        elute_imidazole_mm=250.0,
    )
    assert result["status"] == "wrong_resin"


def test_run_nta_purification_weak_elution_flagged():
    state = create_lab_state(sample_id="purify-weak-elution", seed=1)
    result = run_nta_purification(
        state=state,
        resin_name="Ni-NTA",
        load_imidazole_mm=20.0,
        wash_imidazole_mm=50.0,
        elute_imidazole_mm=100.0,
    )
    assert result["status"] == "weak_elution"
