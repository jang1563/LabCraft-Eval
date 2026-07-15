"""Agent-facing lab-operation wrappers."""

from __future__ import annotations

import contextvars
from typing import Optional

from src.environment import get_or_create_lab_state
from src.environment.observations import render_observation
from src.environment.operations import (
    count_colonies,
    fit_growth_curve,
    gibson_assembly,
    golden_gate_assembly,
    incubate,
    inspect_screening_plate,
    inoculate_growth,
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
from src.environment.state import reset_lab_state

_ACTIVE_SAMPLE_ID = contextvars.ContextVar("labcraft_active_sample_id", default="transform_01_default")
_ACTIVE_SAMPLE_SEED = contextvars.ContextVar("labcraft_active_sample_seed", default=None)


def set_active_sample(sample_id: str, seed: Optional[int] = None):
    _ACTIVE_SAMPLE_ID.set(sample_id)
    _ACTIVE_SAMPLE_SEED.set(seed)
    reset_lab_state(sample_id)
    get_or_create_lab_state(sample_id, seed=seed)


def cleanup_sample(sample_id: str) -> None:
    reset_lab_state(sample_id)


def _current_state():
    sample_id = _ACTIVE_SAMPLE_ID.get()
    seed = _ACTIVE_SAMPLE_SEED.get()
    return get_or_create_lab_state(sample_id, seed=seed)


async def prepare_media_call(
    medium: str,
    antibiotic: str,
    antibiotic_concentration_ug_ml: float,
    plate_count: int = 1,
) -> str:
    state = _current_state()
    try:
        payload = prepare_media(
            state=state,
            medium=medium,
            antibiotic=antibiotic,
            antibiotic_concentration_ug_ml=antibiotic_concentration_ug_ml,
            plate_count=plate_count,
        )
    except (KeyError, ValueError) as exc:
        return _tool_error_observation("prepare_media", exc)
    return render_observation(payload)


async def transform_call(
    plasmid_mass_pg: float,
    heat_shock_seconds: int,
    recovery_minutes: int,
    outgrowth_media: str,
    shaking: bool,
    ice_incubation_minutes: int,
) -> str:
    state = _current_state()
    try:
        payload = transform(
            state=state,
            plasmid_mass_pg=plasmid_mass_pg,
            heat_shock_seconds=heat_shock_seconds,
            recovery_minutes=recovery_minutes,
            outgrowth_media=outgrowth_media,
            shaking=shaking,
            ice_incubation_minutes=ice_incubation_minutes,
        )
    except (KeyError, ValueError) as exc:
        return _tool_error_observation("transform", exc)
    return render_observation(payload)


async def plate_call(
    culture_id: str,
    plate_id: str,
    dilution_factor: float,
    volume_ul: float,
) -> str:
    state = _current_state()
    try:
        payload = plate(
            state=state,
            culture_id=culture_id,
            plate_id=plate_id,
            dilution_factor=dilution_factor,
            volume_ul=volume_ul,
        )
    except (KeyError, ValueError) as exc:
        return _tool_error_observation("plate", exc)
    return render_observation(payload)


async def count_colonies_call(plating_id: str) -> str:
    state = _current_state()
    try:
        payload = count_colonies(state=state, plating_id=plating_id)
    except (KeyError, ValueError) as exc:
        return _tool_error_observation("count_colonies", exc)
    return render_observation(payload)


async def inoculate_growth_call(condition: str, starting_od600: float) -> str:
    state = _current_state()
    try:
        payload = inoculate_growth(
            state=state,
            condition=condition,
            starting_od600=starting_od600,
        )
    except (KeyError, ValueError) as exc:
        return _tool_error_observation("inoculate_growth", exc)
    return render_observation(payload)


async def incubate_call(growth_id: str, duration_minutes: int) -> str:
    state = _current_state()
    try:
        payload = incubate(state=state, growth_id=growth_id, duration_minutes=duration_minutes)
    except (KeyError, ValueError) as exc:
        return _tool_error_observation("incubate", exc)
    return render_observation(payload)


async def measure_od600_call(growth_id: str, dilution_factor: float = 1.0) -> str:
    state = _current_state()
    try:
        payload = measure_od600(state=state, growth_id=growth_id, dilution_factor=dilution_factor)
    except (KeyError, ValueError) as exc:
        return _tool_error_observation("measure_od600", exc)
    return render_observation(payload)


async def fit_growth_curve_call(growth_id: str) -> str:
    state = _current_state()
    try:
        payload = fit_growth_curve(state=state, growth_id=growth_id)
    except (KeyError, ValueError) as exc:
        return _tool_error_observation("fit_growth_curve", exc)
    return render_observation(payload)


async def run_pcr_call(
    polymerase_name: str,
    additive: str,
    extension_seconds: int,
    cycle_count: int,
) -> str:
    state = _current_state()
    try:
        payload = run_pcr(
            state=state,
            polymerase_name=polymerase_name,
            additive=additive,
            extension_seconds=extension_seconds,
            cycle_count=cycle_count,
        )
    except (KeyError, ValueError) as exc:
        return _tool_error_observation("run_pcr", exc)
    return render_observation(payload)


async def run_gel_call(
    reaction_id: str,
    agarose_percent: float = 1.0,
    ladder_name: str = "1 kb DNA Ladder",
) -> str:
    state = _current_state()
    try:
        payload = run_gel(
            state=state,
            reaction_id=reaction_id,
            agarose_percent=agarose_percent,
            ladder_name=ladder_name,
        )
    except (KeyError, ValueError) as exc:
        return _tool_error_observation("run_gel", exc)
    return render_observation(payload)


async def inspect_screening_plate_call() -> str:
    state = _current_state()
    return render_observation(inspect_screening_plate(state=state))


async def run_colony_pcr_call(
    colony_ids: list[str],
    primer_pair: str = "M13/pUC flank primers",
) -> str:
    state = _current_state()
    try:
        payload = run_colony_pcr(
            state=state,
            colony_ids=colony_ids,
            primer_pair=primer_pair,
        )
    except (KeyError, ValueError) as exc:
        return _tool_error_observation("run_colony_pcr", exc)
    return render_observation(payload)


def _tool_error_observation(tool_name: str, exc: Exception) -> str:
    return render_observation(
        {
            "status": "tool_error",
            "tool_name": tool_name,
            "error_type": type(exc).__name__,
            "message": str(exc),
        }
    )


async def list_cloning_substrates_call() -> str:
    state = _current_state()
    return render_observation(list_cloning_substrates(state=state))


async def restriction_digest_call(
    fragment_id: str,
    enzyme_names: list[str],
    buffer: str,
    temperature_c: float,
    duration_minutes: int,
    heat_inactivate_after: bool,
    heat_inactivation_temperature_c: float,
) -> str:
    state = _current_state()
    try:
        payload = restriction_digest(
            state=state,
            fragment_id=fragment_id,
            enzyme_names=enzyme_names,
            buffer=buffer,
            temperature_c=temperature_c,
            duration_minutes=duration_minutes,
            heat_inactivate_after=heat_inactivate_after,
            heat_inactivation_temperature_c=heat_inactivation_temperature_c,
        )
    except (KeyError, ValueError) as exc:
        return _tool_error_observation("restriction_digest", exc)
    return render_observation(payload)


async def ligate_call(
    vector_fragment_id: str,
    insert_fragment_ids: list[str],
    ligase_name: str,
    vector_to_insert_molar_ratio: float,
    temperature_c: float,
    duration_minutes: int,
    buffer: str,
) -> str:
    state = _current_state()
    try:
        payload = ligate(
            state=state,
            vector_fragment_id=vector_fragment_id,
            insert_fragment_ids=insert_fragment_ids,
            ligase_name=ligase_name,
            vector_to_insert_molar_ratio=vector_to_insert_molar_ratio,
            temperature_c=temperature_c,
            duration_minutes=duration_minutes,
            buffer=buffer,
        )
    except (KeyError, ValueError) as exc:
        return _tool_error_observation("ligate", exc)
    return render_observation(payload)


async def transform_ligation_call(
    ligation_id: str,
    heat_shock_seconds: int,
    recovery_minutes: int,
    outgrowth_media: str,
    shaking: bool,
    ice_incubation_minutes: int,
) -> str:
    state = _current_state()
    try:
        payload = transform_ligation(
            state=state,
            ligation_id=ligation_id,
            heat_shock_seconds=heat_shock_seconds,
            recovery_minutes=recovery_minutes,
            outgrowth_media=outgrowth_media,
            shaking=shaking,
            ice_incubation_minutes=ice_incubation_minutes,
        )
    except (KeyError, ValueError) as exc:
        return _tool_error_observation("transform_ligation", exc)
    return render_observation(payload)


async def list_golden_gate_substrates_call() -> str:
    state = _current_state()
    return render_observation(list_golden_gate_substrates(state=state))


async def golden_gate_assembly_call(
    fragment_ids: list[str],
    enzyme_name: str,
    ligase_name: str,
    buffer: str,
    cycle_count: int,
    digest_temperature_c: float,
    ligate_temperature_c: float,
    final_digest_minutes: int,
    final_digest_temperature_c: float,
) -> str:
    state = _current_state()
    try:
        payload = golden_gate_assembly(
            state=state,
            fragment_ids=fragment_ids,
            enzyme_name=enzyme_name,
            ligase_name=ligase_name,
            buffer=buffer,
            cycle_count=cycle_count,
            digest_temperature_c=digest_temperature_c,
            ligate_temperature_c=ligate_temperature_c,
            final_digest_minutes=final_digest_minutes,
            final_digest_temperature_c=final_digest_temperature_c,
        )
    except (KeyError, ValueError) as exc:
        return _tool_error_observation("golden_gate_assembly", exc)
    return render_observation(payload)


async def transform_assembly_call(
    assembly_id: str,
    heat_shock_seconds: int,
    recovery_minutes: int,
    outgrowth_media: str,
    shaking: bool,
    ice_incubation_minutes: int,
) -> str:
    state = _current_state()
    try:
        payload = transform_assembly(
            state=state,
            assembly_id=assembly_id,
            heat_shock_seconds=heat_shock_seconds,
            recovery_minutes=recovery_minutes,
            outgrowth_media=outgrowth_media,
            shaking=shaking,
            ice_incubation_minutes=ice_incubation_minutes,
        )
    except (KeyError, ValueError) as exc:
        return _tool_error_observation("transform_assembly", exc)
    return render_observation(payload)


async def list_gibson_substrates_call() -> str:
    state = _current_state()
    return render_observation(list_gibson_substrates(state=state))


async def gibson_assembly_call(
    fragment_ids: list[str],
    master_mix_name: str,
    temperature_c: float,
    duration_minutes: int,
    overlap_length_bp: int,
) -> str:
    state = _current_state()
    try:
        payload = gibson_assembly(
            state=state,
            fragment_ids=fragment_ids,
            master_mix_name=master_mix_name,
            temperature_c=temperature_c,
            duration_minutes=duration_minutes,
            overlap_length_bp=overlap_length_bp,
        )
    except (KeyError, ValueError) as exc:
        return _tool_error_observation("gibson_assembly", exc)
    return render_observation(payload)


async def transform_gibson_call(
    gibson_id: str,
    heat_shock_seconds: int,
    recovery_minutes: int,
    outgrowth_media: str,
    shaking: bool,
    ice_incubation_minutes: int,
) -> str:
    state = _current_state()
    try:
        payload = transform_gibson(
            state=state,
            gibson_id=gibson_id,
            heat_shock_seconds=heat_shock_seconds,
            recovery_minutes=recovery_minutes,
            outgrowth_media=outgrowth_media,
            shaking=shaking,
            ice_incubation_minutes=ice_incubation_minutes,
        )
    except (KeyError, ValueError) as exc:
        return _tool_error_observation("transform_gibson", exc)
    return render_observation(payload)


async def perform_miniprep_call(
    culture_volume_ml: float,
    lysis_buffer_sequence: str,
    lysis_duration_min: int,
    purification_method: str,
    elution_volume_ul: float,
) -> str:
    state = _current_state()
    try:
        payload = perform_miniprep(
            state=state,
            culture_volume_ml=culture_volume_ml,
            lysis_buffer_sequence=lysis_buffer_sequence,
            lysis_duration_min=lysis_duration_min,
            purification_method=purification_method,
            elution_volume_ul=elution_volume_ul,
        )
    except (KeyError, ValueError) as exc:
        return _tool_error_observation("perform_miniprep", exc)
    return render_observation(payload)


async def run_protein_expression_call(
    host_strain: str,
    iptg_concentration_mm: float,
    induction_od600: float,
    induction_temperature_c: float,
    induction_hours: float,
    lysis_buffer_ph: float,
    culture_volume_ml: float = 500.0,
) -> str:
    state = _current_state()
    try:
        payload = run_protein_expression(
            state=state,
            host_strain=host_strain,
            iptg_concentration_mm=iptg_concentration_mm,
            induction_od600=induction_od600,
            induction_temperature_c=induction_temperature_c,
            induction_hours=induction_hours,
            lysis_buffer_ph=lysis_buffer_ph,
            culture_volume_ml=culture_volume_ml,
        )
    except (KeyError, ValueError) as exc:
        return _tool_error_observation("run_protein_expression", exc)
    return render_observation(payload)


async def run_nta_purification_call(
    resin_name: str,
    load_imidazole_mm: float,
    wash_imidazole_mm: float,
    elute_imidazole_mm: float,
    flow_rate_ml_per_min: float,
    column_bed_volume_ml: float,
    input_mass_mg: float = 18.0,
) -> str:
    state = _current_state()
    try:
        payload = run_nta_purification(
            state=state,
            resin_name=resin_name,
            load_imidazole_mm=load_imidazole_mm,
            wash_imidazole_mm=wash_imidazole_mm,
            elute_imidazole_mm=elute_imidazole_mm,
            flow_rate_ml_per_min=flow_rate_ml_per_min,
            column_bed_volume_ml=column_bed_volume_ml,
            input_mass_mg=input_mass_mg,
        )
    except (KeyError, ValueError) as exc:
        return _tool_error_observation("run_nta_purification", exc)
    return render_observation(payload)


def prepare_media_tool():
    from inspect_ai.tool import tool

    @tool(name="prepare_media")
    def prepare_media_tool_impl():
        """Prepare selection plates for a transformation experiment."""

        async def execute(
            medium: str,
            antibiotic: str,
            antibiotic_concentration_ug_ml: float,
            plate_count: int = 1,
        ) -> str:
            """Prepare one or more selection plates.

            Args:
                medium: Plate medium name, such as "LB agar".
                antibiotic: Selection antibiotic name.
                antibiotic_concentration_ug_ml: Working antibiotic concentration in ug/mL.
                plate_count: Number of plates to prepare.
            """
            return await prepare_media_call(
                medium=medium,
                antibiotic=antibiotic,
                antibiotic_concentration_ug_ml=antibiotic_concentration_ug_ml,
                plate_count=plate_count,
            )

        return execute

    return prepare_media_tool_impl()


def transform_tool():
    from inspect_ai.tool import tool

    @tool(name="transform")
    def transform_tool_impl():
        """Transform chemically competent E. coli with plasmid DNA."""

        async def execute(
            plasmid_mass_pg: float,
            heat_shock_seconds: int,
            recovery_minutes: int,
            outgrowth_media: str,
            shaking: bool,
            ice_incubation_minutes: int,
        ) -> str:
            """Run a chemical transformation.

            Args:
                plasmid_mass_pg: DNA mass in picograms.
                heat_shock_seconds: Heat shock duration in seconds.
                recovery_minutes: Outgrowth duration before plating.
                outgrowth_media: Recovery medium name.
                shaking: Whether the outgrowth is shaken.
                ice_incubation_minutes: Time spent on ice before heat shock.
            """
            return await transform_call(
                plasmid_mass_pg=plasmid_mass_pg,
                heat_shock_seconds=heat_shock_seconds,
                recovery_minutes=recovery_minutes,
                outgrowth_media=outgrowth_media,
                shaking=shaking,
                ice_incubation_minutes=ice_incubation_minutes,
            )

        return execute

    return transform_tool_impl()


def plate_tool():
    from inspect_ai.tool import tool

    @tool(name="plate")
    def plate_tool_impl():
        """Plate a transformed culture onto a prepared selection plate."""

        async def execute(
            culture_id: str,
            plate_id: str,
            dilution_factor: float,
            volume_ul: float,
        ) -> str:
            """Plate a transformed culture.

            Args:
                culture_id: Identifier returned by the transform tool.
                plate_id: Identifier returned by the prepare_media tool.
                dilution_factor: Dilution applied before plating.
                volume_ul: Plated volume in microliters.
            """
            return await plate_call(
                culture_id=culture_id,
                plate_id=plate_id,
                dilution_factor=dilution_factor,
                volume_ul=volume_ul,
            )

        return execute

    return plate_tool_impl()


def count_colonies_tool():
    from inspect_ai.tool import tool

    @tool(name="count_colonies")
    def count_colonies_tool_impl():
        """Count colonies on a plated transformation sample."""

        async def execute(plating_id: str) -> str:
            """Count colonies on a plated sample.

            Args:
                plating_id: Identifier returned by the plate tool.
            """
            return await count_colonies_call(plating_id=plating_id)

        return execute

    return count_colonies_tool_impl()


def inoculate_growth_tool():
    from inspect_ai.tool import tool

    @tool(name="inoculate_growth")
    def inoculate_growth_tool_impl():
        """Start one growth-characterization culture in a named condition."""

        async def execute(condition: str, starting_od600: float) -> str:
            """Inoculate a growth culture.

            Args:
                condition: One of "LB", "M9 + glucose", or "LB + chloramphenicol (1.8 uM)".
                starting_od600: Initial OD600 at inoculation.
            """
            return await inoculate_growth_call(condition=condition, starting_od600=starting_od600)

        return execute

    return inoculate_growth_tool_impl()


def incubate_tool():
    from inspect_ai.tool import tool

    @tool(name="incubate")
    def incubate_tool_impl():
        """Advance a growth culture by a specified incubation interval."""

        async def execute(growth_id: str, duration_minutes: int) -> str:
            """Advance a culture in time.

            Args:
                growth_id: Identifier returned by inoculate_growth.
                duration_minutes: Incubation duration in minutes.
            """
            return await incubate_call(growth_id=growth_id, duration_minutes=duration_minutes)

        return execute

    return incubate_tool_impl()


def measure_od600_tool():
    from inspect_ai.tool import tool

    @tool(name="measure_od600")
    def measure_od600_tool_impl():
        """Measure the OD600 of a growth culture."""

        async def execute(growth_id: str, dilution_factor: float = 1.0) -> str:
            """Record an OD600 measurement.

            Args:
                growth_id: Identifier returned by inoculate_growth.
                dilution_factor: Sample dilution applied before the OD600 reading.
            """
            return await measure_od600_call(growth_id=growth_id, dilution_factor=dilution_factor)

        return execute

    return measure_od600_tool_impl()


def fit_growth_curve_tool():
    from inspect_ai.tool import tool

    @tool(name="fit_growth_curve")
    def fit_growth_curve_tool_impl():
        """Estimate growth-rate parameters from collected OD600 measurements."""

        async def execute(growth_id: str) -> str:
            """Fit a simple growth curve summary.

            Args:
                growth_id: Identifier returned by inoculate_growth.
            """
            return await fit_growth_curve_call(growth_id=growth_id)

        return execute

    return fit_growth_curve_tool_impl()


def run_pcr_tool():
    from inspect_ai.tool import tool

    @tool(name="run_pcr")
    def run_pcr_tool_impl():
        """Run one PCR condition for the GC-rich PCR optimization task."""

        async def execute(
            polymerase_name: str,
            additive: str,
            extension_seconds: int,
            cycle_count: int,
        ) -> str:
            """Run a PCR reaction.

            Args:
                polymerase_name: Polymerase selected for the supplied template.
                additive: Additive selected for the supplied template.
                extension_seconds: Extension time per cycle in seconds.
                cycle_count: Total cycle count.

            Returns:
                A PCR result that includes a reaction_id such as "pcr_001". Save that
                exact reaction_id and reuse it when calling run_gel.
            """
            return await run_pcr_call(
                polymerase_name=polymerase_name,
                additive=additive,
                extension_seconds=extension_seconds,
                cycle_count=cycle_count,
            )

        return execute

    return run_pcr_tool_impl()


def run_gel_tool():
    from inspect_ai.tool import tool

    @tool(name="run_gel")
    def run_gel_tool_impl():
        """Visualize a PCR reaction on an agarose gel."""

        async def execute(
            reaction_id: str,
            agarose_percent: float = 1.0,
            ladder_name: str = "1 kb DNA Ladder",
        ) -> str:
            """Run a gel for a PCR reaction.

            Args:
                reaction_id: Reaction identifier returned by run_pcr, preferably reused
                    exactly as returned (for example "pcr_001").
                agarose_percent: Agarose concentration for the gel.
                ladder_name: DNA ladder used for size estimation.
            """
            return await run_gel_call(
                reaction_id=reaction_id,
                agarose_percent=agarose_percent,
                ladder_name=ladder_name,
            )

        return execute

    return run_gel_tool_impl()


def inspect_screening_plate_tool():
    from inspect_ai.tool import tool

    @tool(name="inspect_screening_plate")
    def inspect_screening_plate_tool_impl():
        """Inspect the blue-white screening plate used in Screen-01."""

        async def execute() -> str:
            """Return the plate composition and available colony identifiers."""
            return await inspect_screening_plate_call()

        return execute

    return inspect_screening_plate_tool_impl()


def run_colony_pcr_tool():
    from inspect_ai.tool import tool

    @tool(name="run_colony_pcr")
    def run_colony_pcr_tool_impl():
        """Run colony PCR on one or more candidate colonies from the screening plate."""

        async def execute(
            colony_ids: list[str],
            primer_pair: str = "M13/pUC flank primers",
        ) -> str:
            """Run colony PCR on selected colonies.

            Args:
                colony_ids: Colony identifiers returned by inspect_screening_plate.
                primer_pair: Primer pair label for the screening PCR.
            """
            return await run_colony_pcr_call(
                colony_ids=colony_ids,
                primer_pair=primer_pair,
            )

        return execute

    return run_colony_pcr_tool_impl()


def list_cloning_substrates_tool():
    from inspect_ai.tool import tool

    @tool(name="list_cloning_substrates")
    def list_cloning_substrates_tool_impl():
        """List the starting DNA fragments available for Clone-01."""

        async def execute() -> str:
            """Return the vector and insert fragments provided for the cloning task."""
            return await list_cloning_substrates_call()

        return execute

    return list_cloning_substrates_tool_impl()


def restriction_digest_tool():
    from inspect_ai.tool import tool

    @tool(name="restriction_digest")
    def restriction_digest_tool_impl():
        """Run a restriction digest on a DNA fragment for cloning."""

        async def execute(
            fragment_id: str,
            enzyme_names: list[str],
            buffer: str,
            temperature_c: float,
            duration_minutes: int,
            heat_inactivate_after: bool,
            heat_inactivation_temperature_c: float,
        ) -> str:
            """Digest a DNA fragment with one or more restriction enzymes.

            Args:
                fragment_id: Fragment to digest, as returned by list_cloning_substrates.
                enzyme_names: Restriction enzymes selected for the supplied fragment.
                buffer: Reaction buffer chosen for the enzyme combination.
                temperature_c: Incubation temperature in Celsius.
                duration_minutes: Incubation time in minutes.
                heat_inactivate_after: Whether to heat-inactivate the enzymes after digestion.
                heat_inactivation_temperature_c: Temperature used for heat inactivation if enabled.
            """
            return await restriction_digest_call(
                fragment_id=fragment_id,
                enzyme_names=enzyme_names,
                buffer=buffer,
                temperature_c=temperature_c,
                duration_minutes=duration_minutes,
                heat_inactivate_after=heat_inactivate_after,
                heat_inactivation_temperature_c=heat_inactivation_temperature_c,
            )

        return execute

    return restriction_digest_tool_impl()


def ligate_tool():
    from inspect_ai.tool import tool

    @tool(name="ligate")
    def ligate_tool_impl():
        """Set up a ligation reaction from a digested vector and one or more inserts."""

        async def execute(
            vector_fragment_id: str,
            insert_fragment_ids: list[str],
            ligase_name: str,
            vector_to_insert_molar_ratio: float,
            temperature_c: float,
            duration_minutes: int,
            buffer: str,
        ) -> str:
            """Ligate a digested vector with one or more digested inserts.

            Args:
                vector_fragment_id: Digested vector fragment id (output of restriction_digest).
                insert_fragment_ids: Digested insert fragment ids.
                ligase_name: Ligase selected for the digested DNA ends.
                vector_to_insert_molar_ratio: Insert excess over vector.
                temperature_c: Ligation temperature in Celsius.
                duration_minutes: Ligation duration in minutes.
                buffer: Ligation buffer label.
            """
            return await ligate_call(
                vector_fragment_id=vector_fragment_id,
                insert_fragment_ids=insert_fragment_ids,
                ligase_name=ligase_name,
                vector_to_insert_molar_ratio=vector_to_insert_molar_ratio,
                temperature_c=temperature_c,
                duration_minutes=duration_minutes,
                buffer=buffer,
            )

        return execute

    return ligate_tool_impl()


def transform_ligation_tool():
    from inspect_ai.tool import tool

    @tool(name="transform_ligation")
    def transform_ligation_tool_impl():
        """Transform a ligation reaction into competent E. coli and prepare a screening plate."""

        async def execute(
            ligation_id: str,
            heat_shock_seconds: int,
            recovery_minutes: int,
            outgrowth_media: str,
            shaking: bool,
            ice_incubation_minutes: int,
        ) -> str:
            """Transform a ligation into competent cells.

            Args:
                ligation_id: Ligation identifier returned by the ligate tool.
                heat_shock_seconds: Heat shock duration.
                recovery_minutes: Post-shock outgrowth duration in minutes.
                outgrowth_media: Outgrowth medium.
                shaking: Whether to shake during recovery.
                ice_incubation_minutes: Pre-shock ice incubation time.
            """
            return await transform_ligation_call(
                ligation_id=ligation_id,
                heat_shock_seconds=heat_shock_seconds,
                recovery_minutes=recovery_minutes,
                outgrowth_media=outgrowth_media,
                shaking=shaking,
                ice_incubation_minutes=ice_incubation_minutes,
            )

        return execute

    return transform_ligation_tool_impl()


def list_golden_gate_substrates_tool():
    from inspect_ai.tool import tool

    @tool(name="list_golden_gate_substrates")
    def list_golden_gate_substrates_tool_impl():
        """List the four starting DNA fragments for the Golden Gate task."""

        async def execute() -> str:
            """Return the backbone, inserts, and observed directional overhangs."""
            return await list_golden_gate_substrates_call()

        return execute

    return list_golden_gate_substrates_tool_impl()


def golden_gate_assembly_tool():
    from inspect_ai.tool import tool

    @tool(name="golden_gate_assembly")
    def golden_gate_assembly_tool_impl():
        """Run a one-pot Golden Gate / Type IIS assembly with thermal cycling."""

        async def execute(
            fragment_ids: list[str],
            enzyme_name: str,
            ligase_name: str,
            buffer: str,
            cycle_count: int,
            digest_temperature_c: float,
            ligate_temperature_c: float,
            final_digest_minutes: int,
            final_digest_temperature_c: float,
        ) -> str:
            """Run a Golden Gate assembly.

            Args:
                fragment_ids: Fragments to assemble (must be all four Golden Gate substrates).
                enzyme_name: Type IIS enzyme selected for the supplied substrates.
                ligase_name: Ligase selected for the cycling assembly.
                buffer: Reaction buffer.
                cycle_count: Number of digest/ligation cycles.
                digest_temperature_c: Digest-step temperature.
                ligate_temperature_c: Ligation-step temperature.
                final_digest_minutes: Final digest hold after cycling.
                final_digest_temperature_c: Temperature of the final digest hold.
            """
            return await golden_gate_assembly_call(
                fragment_ids=fragment_ids,
                enzyme_name=enzyme_name,
                ligase_name=ligase_name,
                buffer=buffer,
                cycle_count=cycle_count,
                digest_temperature_c=digest_temperature_c,
                ligate_temperature_c=ligate_temperature_c,
                final_digest_minutes=final_digest_minutes,
                final_digest_temperature_c=final_digest_temperature_c,
            )

        return execute

    return golden_gate_assembly_tool_impl()


def transform_assembly_tool():
    from inspect_ai.tool import tool

    @tool(name="transform_assembly")
    def transform_assembly_tool_impl():
        """Transform a Golden Gate assembled construct into competent E. coli."""

        async def execute(
            assembly_id: str,
            heat_shock_seconds: int,
            recovery_minutes: int,
            outgrowth_media: str,
            shaking: bool,
            ice_incubation_minutes: int,
        ) -> str:
            """Transform a Golden Gate assembly into competent cells.

            Args:
                assembly_id: Assembly identifier from golden_gate_assembly.
                heat_shock_seconds: Heat shock duration.
                recovery_minutes: Post-shock outgrowth duration.
                outgrowth_media: Outgrowth medium.
                shaking: Whether to shake during recovery.
                ice_incubation_minutes: Pre-shock ice incubation time.
            """
            return await transform_assembly_call(
                assembly_id=assembly_id,
                heat_shock_seconds=heat_shock_seconds,
                recovery_minutes=recovery_minutes,
                outgrowth_media=outgrowth_media,
                shaking=shaking,
                ice_incubation_minutes=ice_incubation_minutes,
            )

        return execute

    return transform_assembly_tool_impl()


def list_gibson_substrates_tool():
    from inspect_ai.tool import tool

    @tool(name="list_gibson_substrates")
    def list_gibson_substrates_tool_impl():
        """List the two Gibson starting fragments (linearised backbone + PCR insert)."""

        async def execute() -> str:
            """Return the two Gibson substrates and their homology overhang lengths."""
            return await list_gibson_substrates_call()

        return execute

    return list_gibson_substrates_tool_impl()


def gibson_assembly_tool():
    from inspect_ai.tool import tool

    @tool(name="gibson_assembly")
    def gibson_assembly_tool_impl():
        """Run a Gibson isothermal overlap assembly of two or more fragments."""

        async def execute(
            fragment_ids: list[str],
            master_mix_name: str,
            temperature_c: float,
            duration_minutes: int,
            overlap_length_bp: int,
        ) -> str:
            """Run a Gibson assembly.

            Args:
                fragment_ids: Fragments to assemble (backbone + insert).
                master_mix_name: Isothermal overlap-assembly mix name.
                temperature_c: Isothermal incubation temperature.
                duration_minutes: Incubation duration.
                overlap_length_bp: Observed homology-overlap length in bp.
            """
            return await gibson_assembly_call(
                fragment_ids=fragment_ids,
                master_mix_name=master_mix_name,
                temperature_c=temperature_c,
                duration_minutes=duration_minutes,
                overlap_length_bp=overlap_length_bp,
            )

        return execute

    return gibson_assembly_tool_impl()


def transform_gibson_tool():
    from inspect_ai.tool import tool

    @tool(name="transform_gibson")
    def transform_gibson_tool_impl():
        """Transform a Gibson-assembled construct into competent E. coli."""

        async def execute(
            gibson_id: str,
            heat_shock_seconds: int,
            recovery_minutes: int,
            outgrowth_media: str,
            shaking: bool,
            ice_incubation_minutes: int,
        ) -> str:
            """Transform a Gibson assembly into competent cells.

            Args:
                gibson_id: Gibson identifier from gibson_assembly.
                heat_shock_seconds: Heat shock duration.
                recovery_minutes: Post-shock outgrowth duration.
                outgrowth_media: Outgrowth medium.
                shaking: Whether to shake during recovery.
                ice_incubation_minutes: Pre-shock ice incubation time.
            """
            return await transform_gibson_call(
                gibson_id=gibson_id,
                heat_shock_seconds=heat_shock_seconds,
                recovery_minutes=recovery_minutes,
                outgrowth_media=outgrowth_media,
                shaking=shaking,
                ice_incubation_minutes=ice_incubation_minutes,
            )

        return execute

    return transform_gibson_tool_impl()


def perform_miniprep_tool():
    from inspect_ai.tool import tool

    @tool(name="perform_miniprep")
    def perform_miniprep_tool_impl():
        """Perform a single-pass alkaline-lysis plasmid miniprep."""

        async def execute(
            culture_volume_ml: float,
            lysis_buffer_sequence: str,
            lysis_duration_min: int,
            purification_method: str,
            elution_volume_ul: float,
        ) -> str:
            """Run an end-to-end plasmid miniprep.

            Args:
                culture_volume_ml: Overnight culture volume in mL.
                lysis_buffer_sequence: Ordered alkaline-lysis buffer labels.
                lysis_duration_min: Time in alkaline lysis before neutralisation.
                purification_method: Plasmid purification method.
                elution_volume_ul: Final elution volume in microlitres.
            """
            return await perform_miniprep_call(
                culture_volume_ml=culture_volume_ml,
                lysis_buffer_sequence=lysis_buffer_sequence,
                lysis_duration_min=lysis_duration_min,
                purification_method=purification_method,
                elution_volume_ul=elution_volume_ul,
            )

        return execute

    return perform_miniprep_tool_impl()


def run_protein_expression_tool():
    from inspect_ai.tool import tool

    @tool(name="run_protein_expression")
    def run_protein_expression_tool_impl():
        """Run a single IPTG-induced recombinant protein expression."""

        async def execute(
            host_strain: str,
            iptg_concentration_mm: float,
            induction_od600: float,
            induction_temperature_c: float,
            induction_hours: float,
            lysis_buffer_ph: float,
            culture_volume_ml: float = 500.0,
        ) -> str:
            """Run a protein expression experiment end-to-end.

            Args:
                host_strain: E. coli host selected for recombinant expression.
                iptg_concentration_mm: IPTG induction concentration in mM.
                induction_od600: OD600 at induction.
                induction_temperature_c: Induction temperature in Celsius.
                induction_hours: Induction duration in hours.
                lysis_buffer_ph: Lysis buffer pH.
                culture_volume_ml: Culture volume in mL (default 500).
            """
            return await run_protein_expression_call(
                host_strain=host_strain,
                iptg_concentration_mm=iptg_concentration_mm,
                induction_od600=induction_od600,
                induction_temperature_c=induction_temperature_c,
                induction_hours=induction_hours,
                lysis_buffer_ph=lysis_buffer_ph,
                culture_volume_ml=culture_volume_ml,
            )

        return execute

    return run_protein_expression_tool_impl()


def run_nta_purification_tool():
    from inspect_ai.tool import tool

    @tool(name="run_nta_purification")
    def run_nta_purification_tool_impl():
        """Run a single-pass Ni-NTA affinity purification with SDS-PAGE readout."""

        async def execute(
            resin_name: str,
            load_imidazole_mm: float,
            wash_imidazole_mm: float,
            elute_imidazole_mm: float,
            flow_rate_ml_per_min: float,
            column_bed_volume_ml: float,
            input_mass_mg: float = 18.0,
        ) -> str:
            """Purify a His-tagged benign protein over Ni-NTA.

            Args:
                resin_name: Immobilised-metal affinity resin name.
                load_imidazole_mm: Imidazole concentration in the load buffer.
                wash_imidazole_mm: Imidazole concentration in the wash buffer.
                elute_imidazole_mm: Imidazole concentration in the elution buffer.
                flow_rate_ml_per_min: Column flow rate in mL/min.
                column_bed_volume_ml: Column bed volume in mL.
                input_mass_mg: Mass of input soluble protein to load in mg.
            """
            return await run_nta_purification_call(
                resin_name=resin_name,
                load_imidazole_mm=load_imidazole_mm,
                wash_imidazole_mm=wash_imidazole_mm,
                elute_imidazole_mm=elute_imidazole_mm,
                flow_rate_ml_per_min=flow_rate_ml_per_min,
                column_bed_volume_ml=column_bed_volume_ml,
                input_mass_mg=input_mass_mg,
            )

        return execute

    return run_nta_purification_tool_impl()
