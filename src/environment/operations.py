"""Minimal LabCraft operations for the Transform-01 task."""

from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Dict, List

from .gibson_contract import (
    GIBSON_FRAGMENT_IDS,
    GIBSON_MAX_DURATION_MINUTES,
    GIBSON_MIN_DURATION_MINUTES,
    GIBSON_OVERLAP_LENGTH_BP,
    GIBSON_TEMPERATURE_C,
    canonicalize_gibson_master_mix,
    normalize_gibson_master_mix,
)
from .expression_contract import (
    EXPRESSION_AFFINITY_TAG,
    EXPRESSION_CONSTRUCT_ID,
    EXPRESSION_CULTURE_VOLUME_ML,
    EXPRESSION_FAILURE_HOST,
    EXPRESSION_FAILURE_IPTG,
    EXPRESSION_FAILURE_LYSIS_PH,
    EXPRESSION_FAILURE_OD600,
    EXPRESSION_FAILURE_SCHEDULE,
    EXPRESSION_IPTG_MAX_MM,
    EXPRESSION_IPTG_MIN_MM,
    EXPRESSION_LYSIS_PH_MAX,
    EXPRESSION_LYSIS_PH_MIN,
    EXPRESSION_OD600_MAX,
    EXPRESSION_OD600_MIN,
    EXPRESSION_PLASMID_NAME,
    EXPRESSION_PROMOTER,
    EXPRESSION_SUCCESS_STATUS,
    EXPRESSION_TARGET_PROTEIN_KDA,
    EXPRESSION_TARGET_PROTEIN_NAME,
    EXPRESSION_TOTAL_TARGET_YIELD_MG_PER_L,
    canonicalize_expression_host,
    match_expression_schedule,
    normalize_expression_label,
)
from .miniprep_contract import (
    MINIPREP_CULTURE_VOLUME_MAX_ML,
    MINIPREP_CULTURE_VOLUME_MIN_ML,
    MINIPREP_ELUTION_VOLUME_MAX_UL,
    MINIPREP_ELUTION_VOLUME_UL,
    MINIPREP_FAILURE_CULTURE_VOLUME,
    MINIPREP_FAILURE_ELUTION,
    MINIPREP_FAILURE_OVERLYSIS,
    MINIPREP_FAILURE_WRONG_BUFFER,
    MINIPREP_FAILURE_WRONG_METHOD,
    MINIPREP_LYSIS_DURATION_MAX_MINUTES,
    MINIPREP_LYSIS_DURATION_MIN_MINUTES,
    MINIPREP_NOMINAL_A260_A280,
    MINIPREP_REFERENCE_YIELD_UG_AT_5_ML,
    MINIPREP_SOURCE_CULTURE_ID,
    MINIPREP_SOURCE_CULTURE_VOLUME_ML,
    canonicalize_miniprep_buffer_sequence,
    canonicalize_miniprep_purification_method,
    normalize_miniprep_label,
)
from .purification_contract import (
    PURIFICATION_AFFINITY_TAG,
    PURIFICATION_COLUMN_BED_VOLUME_ML,
    PURIFICATION_COLUMN_CAPACITY_MIN_MG_PER_ML,
    PURIFICATION_CONSTRUCT_ID,
    PURIFICATION_ELUATE_COLUMN_VOLUMES,
    PURIFICATION_ELUTION_IMIDAZOLE_MAX_MM,
    PURIFICATION_ELUTION_IMIDAZOLE_MIN_MM,
    PURIFICATION_FAILURE_ELUTION,
    PURIFICATION_FAILURE_FLOW,
    PURIFICATION_FAILURE_LOAD,
    PURIFICATION_FAILURE_SDS_PAGE_RESULT,
    PURIFICATION_FAILURE_WASH,
    PURIFICATION_FLOW_RATE_MAX_ML_PER_MIN,
    PURIFICATION_FLOW_RATE_MIN_ML_PER_MIN,
    PURIFICATION_INPUT_TARGET_MASS_MG,
    PURIFICATION_LOAD_IMIDAZOLE_MAX_MM,
    PURIFICATION_LOAD_IMIDAZOLE_MIN_MM,
    PURIFICATION_LYSATE_ID,
    PURIFICATION_LYSATE_NACL_MM,
    PURIFICATION_LYSATE_PH,
    PURIFICATION_LYSATE_PHOSPHATE_MM,
    PURIFICATION_PURITY_PERCENT,
    PURIFICATION_RECOVERY_FRACTION,
    PURIFICATION_RESIN_NAME,
    PURIFICATION_SDS_PAGE_RESULT,
    PURIFICATION_SOURCE_EXPRESSION_ID,
    PURIFICATION_SUCCESS_STATUS,
    PURIFICATION_TARGET_PROTEIN_KDA,
    PURIFICATION_TARGET_PROTEIN_NAME,
    PURIFICATION_WASH_IMIDAZOLE_MAX_MM,
    PURIFICATION_WASH_IMIDAZOLE_MIN_MM,
    normalize_purification_label,
)
from .state import (
    AssemblyReaction,
    DigestReaction,
    DnaFragment,
    ExpressionConstruct,
    GelRun,
    GibsonReaction,
    GrowthCulture,
    GrowthMeasurement,
    LabState,
    LigationReaction,
    MiniprepCulture,
    MiniprepSample,
    NtaPurification,
    PcrReaction,
    PlatedSample,
    PreparedPlate,
    ProteinExpression,
    PurificationLysate,
    ScreeningColony,
    ScreeningPlate,
    TransformationCulture,
)
from .stochastic import (
    load_cloning_parameters,
    load_gibson_parameters,
    load_golden_gate_parameters,
    load_growth_parameters,
    load_miniprep_parameters,
    load_pcr_parameters,
    load_screening_parameters,
    sample_poisson,
)

_GROWTH_PARAMETERS_PATH = Path(__file__).resolve().parents[2] / "data" / "parameters" / "growth.json"
_GROWTH_BUNDLE = None
_PCR_PARAMETERS_PATH = Path(__file__).resolve().parents[2] / "data" / "parameters" / "pcr.json"
_PCR_BUNDLE = None
_SCREENING_PARAMETERS_PATH = Path(__file__).resolve().parents[2] / "data" / "parameters" / "screening.json"
_SCREENING_BUNDLE = None
_CLONING_PARAMETERS_PATH = Path(__file__).resolve().parents[2] / "data" / "parameters" / "cloning.json"
_CLONING_BUNDLE = None
_GOLDEN_GATE_PARAMETERS_PATH = Path(__file__).resolve().parents[2] / "data" / "parameters" / "golden_gate.json"
_GOLDEN_GATE_BUNDLE = None
_GIBSON_PARAMETERS_PATH = Path(__file__).resolve().parents[2] / "data" / "parameters" / "gibson.json"
_GIBSON_BUNDLE = None
_MINIPREP_PARAMETERS_PATH = Path(__file__).resolve().parents[2] / "data" / "parameters" / "miniprep.json"
_MINIPREP_BUNDLE = None


def _require_finite_float(value: object, field_name: str) -> float:
    if isinstance(value, bool):
        raise ValueError("{} must be numeric.".format(field_name))
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("{} must be numeric.".format(field_name)) from exc
    if not math.isfinite(parsed):
        raise ValueError("{} must be finite.".format(field_name))
    return parsed


def _require_positive_float(value: object, field_name: str) -> float:
    parsed = _require_finite_float(value, field_name)
    if parsed <= 0.0:
        raise ValueError("{} must be positive.".format(field_name))
    return parsed


def _require_integer(value: object, field_name: str) -> int:
    if isinstance(value, bool):
        raise ValueError("{} must be an integer.".format(field_name))
    try:
        parsed_float = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("{} must be an integer.".format(field_name)) from exc
    if not math.isfinite(parsed_float) or not parsed_float.is_integer():
        raise ValueError("{} must be an integer.".format(field_name))
    return int(parsed_float)


def _require_positive_integer(value: object, field_name: str) -> int:
    parsed = _require_integer(value, field_name)
    if parsed <= 0:
        raise ValueError("{} must be positive.".format(field_name))
    return parsed


def _require_nonnegative_integer(value: object, field_name: str) -> int:
    parsed = _require_integer(value, field_name)
    if parsed < 0:
        raise ValueError("{} must be non-negative.".format(field_name))
    return parsed


def _growth_bundle():
    global _GROWTH_BUNDLE
    if _GROWTH_BUNDLE is None:
        _GROWTH_BUNDLE = load_growth_parameters(_GROWTH_PARAMETERS_PATH)
    return _GROWTH_BUNDLE


def _pcr_bundle():
    global _PCR_BUNDLE
    if _PCR_BUNDLE is None:
        _PCR_BUNDLE = load_pcr_parameters(_PCR_PARAMETERS_PATH)
    return _PCR_BUNDLE


def _screening_bundle():
    global _SCREENING_BUNDLE
    if _SCREENING_BUNDLE is None:
        _SCREENING_BUNDLE = load_screening_parameters(_SCREENING_PARAMETERS_PATH)
    return _SCREENING_BUNDLE


def _cloning_bundle():
    global _CLONING_BUNDLE
    if _CLONING_BUNDLE is None:
        _CLONING_BUNDLE = load_cloning_parameters(_CLONING_PARAMETERS_PATH)
    return _CLONING_BUNDLE


def _golden_gate_bundle():
    global _GOLDEN_GATE_BUNDLE
    if _GOLDEN_GATE_BUNDLE is None:
        _GOLDEN_GATE_BUNDLE = load_golden_gate_parameters(_GOLDEN_GATE_PARAMETERS_PATH)
    return _GOLDEN_GATE_BUNDLE


def _gibson_bundle():
    global _GIBSON_BUNDLE
    if _GIBSON_BUNDLE is None:
        _GIBSON_BUNDLE = load_gibson_parameters(_GIBSON_PARAMETERS_PATH)
    return _GIBSON_BUNDLE


def _miniprep_bundle():
    global _MINIPREP_BUNDLE
    if _MINIPREP_BUNDLE is None:
        _MINIPREP_BUNDLE = load_miniprep_parameters(_MINIPREP_PARAMETERS_PATH)
    return _MINIPREP_BUNDLE


def _normalize_choice(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().lower()


def _normalize_type_iis_enzyme(value: str) -> str:
    token = re.sub(r"[^a-z0-9]+", "", str(value).casefold())
    aliases = {
        "bsai": "bsai",
        "bsaihfv2": "bsai",
        "bsmbi": "bsmbi",
        "bsmbiv2": "bsmbi",
    }
    return aliases.get(token, token)


def _normalize_golden_gate_buffer(value: str) -> str:
    token = re.sub(r"[^a-z0-9]+", "", str(value).casefold())
    aliases = {
        "t4dnaligasebuffer": "t4dnaligasebuffer",
        "t4dnaligasereactionbuffer": "t4dnaligasebuffer",
        "t4dnaligasebuffer10x": "t4dnaligasebuffer",
        "t4dnaligasereactionbuffer10x": "t4dnaligasebuffer",
        "1xt4dnaligasebuffer": "t4dnaligasebuffer",
        "1xt4dnaligasereactionbuffer": "t4dnaligasebuffer",
        "10xt4dnaligasebuffer": "t4dnaligasebuffer",
        "10xt4dnaligasereactionbuffer": "t4dnaligasebuffer",
        "atpcontainingt4dnaligasebuffer": "t4dnaligasebuffer",
        "atpcontainingt4dnaligasereactionbuffer": "t4dnaligasebuffer",
        "t4dnaligasebuffer50mmtrishclph7510mmmgcl21mmatp10mmdtt": (
            "t4dnaligasebuffer"
        ),
    }
    return aliases.get(token, token)


def _canonical_pcr_polymerase_name(value: str) -> str:
    """Map common PCR polymerase labels to the names used by task parameters."""
    normalized = _normalize_choice(value)
    if re.search(r"\bq5\b", normalized):
        return "Q5 High-Fidelity DNA polymerase"
    if "phusion" in normalized:
        return "Phusion High-Fidelity DNA polymerase"
    if re.search(r"\btaq\b", normalized):
        return "Taq DNA polymerase"
    return str(value).strip()


def _resolve_pcr_reaction_id(state: LabState, reaction_id: str) -> str:
    """Resolve exact or shorthand PCR reaction identifiers to a canonical id."""
    requested = str(reaction_id).strip()
    if requested in state.pcr_reactions:
        return requested

    candidates: List[str] = []
    normalized_requested = _normalize_choice(requested)
    if normalized_requested:
        candidates.extend(
            existing_id
            for existing_id in state.pcr_reactions
            if _normalize_choice(existing_id) == normalized_requested
        )

    suffix_match = re.search(r"(\d+)$", requested)
    if suffix_match:
        suffix = int(suffix_match.group(1))
        canonical = "pcr_{:03d}".format(suffix)
        if canonical in state.pcr_reactions and canonical not in candidates:
            candidates.append(canonical)

    if len(candidates) == 1:
        return candidates[0]

    available = sorted(state.pcr_reactions)
    if not candidates:
        raise ValueError(
            "Unknown reaction_id '{:s}'. Available reaction IDs: {:s}".format(
                requested,
                ", ".join(available) if available else "none",
            )
        )
    raise ValueError(
        "Ambiguous reaction_id '{:s}'. Matching reaction IDs: {:s}".format(
            requested,
            ", ".join(sorted(candidates)),
        )
    )


def _ensure_screening_plate(state: LabState) -> ScreeningPlate:
    existing = next(iter(state.screening_plates.values()), None)
    if existing is not None:
        return existing

    bundle = _screening_bundle()
    plate_id = state.next_screening_plate_id()
    recombinant_band_bp = bundle.integer("screening_recombinant_colony_pcr_band_bp")
    empty_vector_band_bp = bundle.integer("screening_empty_vector_colony_pcr_band_bp")
    plate = ScreeningPlate(
        plate_id=plate_id,
        historical_positive_rate_among_white=bundle.value("historical_positive_rate_among_white_colonies"),
        target_confidence=bundle.value("screening_target_confidence"),
        recombinant_band_bp=recombinant_band_bp,
        empty_vector_band_bp=empty_vector_band_bp,
    )

    recombinant_white_ids = {"white_002", "white_005", "white_006", "white_011"}
    for idx in range(1, 13):
        colony_id = "white_{:03d}".format(idx)
        is_recombinant = colony_id in recombinant_white_ids
        plate.colonies[colony_id] = ScreeningColony(
            colony_id=colony_id,
            color="white",
            is_recombinant=is_recombinant,
            expected_band_bp=recombinant_band_bp if is_recombinant else empty_vector_band_bp,
            notes=[
                "White colony from blue-white screening.",
                "Expected insert-positive band near {:d} bp.".format(recombinant_band_bp)
                if is_recombinant
                else "White false positive with empty-vector-like colony PCR band.",
            ],
        )
    for idx in range(1, 19):
        colony_id = "blue_{:03d}".format(idx)
        plate.colonies[colony_id] = ScreeningColony(
            colony_id=colony_id,
            color="blue",
            is_recombinant=False,
            expected_band_bp=empty_vector_band_bp,
            notes=["Blue colony retaining lacZ alpha activity; treat as vector-only background."],
        )

    state.screening_plates[plate_id] = plate
    return plate


def prepare_media(
    state: LabState,
    medium: str,
    antibiotic: str,
    antibiotic_concentration_ug_ml: float,
    plate_count: int = 1,
) -> Dict[str, object]:
    """Prepare one or more selection plates."""
    antibiotic_concentration = _require_positive_float(
        antibiotic_concentration_ug_ml,
        "antibiotic_concentration_ug_ml",
    )
    plate_count_int = _require_positive_integer(plate_count, "plate_count")
    plates = []
    for _ in range(plate_count_int):
        plate_id = state.next_plate_id()
        plate = PreparedPlate(
            plate_id=plate_id,
            medium=medium,
            antibiotic=antibiotic,
            antibiotic_concentration_ug_ml=antibiotic_concentration,
        )
        state.prepared_plates[plate_id] = plate
        plates.append(
            {
                "plate_id": plate_id,
                "medium": medium,
                "antibiotic": antibiotic,
                "antibiotic_concentration_ug_ml": antibiotic_concentration,
            }
        )
    payload = {
        "status": "prepared",
        "plates": plates,
    }
    state.log_event("prepare_media", payload)
    return payload


def transform(
    state: LabState,
    plasmid_mass_pg: float,
    heat_shock_seconds: int,
    recovery_minutes: int,
    outgrowth_media: str = "SOC",
    shaking: bool = True,
    ice_incubation_minutes: int = 30,
) -> Dict[str, object]:
    """Simulate a chemical transformation and return a culture identifier."""
    plasmid_mass = _require_positive_float(plasmid_mass_pg, "plasmid_mass_pg")
    heat_shock = _require_positive_integer(heat_shock_seconds, "heat_shock_seconds")
    recovery = _require_nonnegative_integer(recovery_minutes, "recovery_minutes")
    ice_incubation = _require_nonnegative_integer(
        ice_incubation_minutes,
        "ice_incubation_minutes",
    )
    notes: List[str] = []
    efficiency = state.base_efficiency_cfu_per_ug
    efficiency *= state.parameters.ice_incubation_penalty(ice_incubation)
    efficiency *= state.parameters.recovery_penalty(recovery)
    if outgrowth_media.upper() == "SOC":
        efficiency *= state.parameters.soc_multiplier()
    else:
        efficiency *= state.parameters.lb_multiplier()
        notes.append("SOC was not used for outgrowth.")
    if shaking:
        efficiency *= state.parameters.shaking_multiplier()
    else:
        efficiency *= state.parameters.static_multiplier()
        notes.append("Outgrowth was not shaken.")
    if heat_shock != int(state.parameters.get("heat_shock_duration_seconds")["parameters"]["optimal"]):
        notes.append("Heat shock duration deviated from the protocol optimum.")

    expected_total_transformants = efficiency * (plasmid_mass / 1_000_000.0)
    culture_id = state.next_culture_id()
    culture = TransformationCulture(
        culture_id=culture_id,
        plasmid_mass_pg=plasmid_mass,
        base_efficiency_cfu_per_ug=state.base_efficiency_cfu_per_ug,
        adjusted_efficiency_cfu_per_ug=efficiency,
        recovery_minutes=recovery,
        outgrowth_media=outgrowth_media,
        shaking=bool(shaking),
        heat_shock_seconds=heat_shock,
        ice_incubation_minutes=ice_incubation,
        expected_total_transformants=expected_total_transformants,
        notes=notes,
    )
    state.cultures[culture_id] = culture
    payload = {
        "status": "transformed",
        "culture_id": culture_id,
        "plasmid_mass_pg": plasmid_mass,
        "heat_shock_seconds": heat_shock,
        "recovery_minutes": recovery,
        "outgrowth_media": outgrowth_media,
        "notes": notes,
    }
    state.log_event("transform", payload)
    return payload


def plate(
    state: LabState,
    culture_id: str,
    plate_id: str,
    dilution_factor: float,
    volume_ul: float,
) -> Dict[str, object]:
    """Plate a transformed culture onto a prepared plate."""
    culture = state.cultures[culture_id]
    prepared_plate = state.prepared_plates[plate_id]
    dilution = float(dilution_factor)
    volume = float(volume_ul)
    if dilution <= 0.0:
        raise ValueError("dilution_factor must be positive.")
    if volume <= 0.0:
        raise ValueError("volume_ul must be positive.")

    warnings: List[str] = []
    countable_min, countable_max = state.parameters.countable_colony_range()
    recommended = state.parameters.recommended_antibiotic_concentration(prepared_plate.antibiotic or "")
    if recommended is None:
        status = "plated_without_reference"
        expected = culture.expected_total_transformants * (volume / 1000.0) / dilution
        observed = sample_poisson(state.rng, expected)
    elif float(prepared_plate.antibiotic_concentration_ug_ml) != float(recommended):
        status = "selection_failed"
        expected = None
        observed = None
        warnings.append("Selection plate concentration does not match the cited working concentration.")
    else:
        status = "plated"
        expected = culture.expected_total_transformants * (volume / 1000.0) / dilution
        observed = sample_poisson(state.rng, expected)
        if observed < countable_min or observed > countable_max:
            status = "count_out_of_range"
            warnings.append(
                "Observed colonies fall outside the cited countable range of "
                "{:d}-{:d} colonies per plate.".format(countable_min, countable_max)
            )

    plating_id = state.next_plating_id()
    plated_sample = PlatedSample(
        plating_id=plating_id,
        culture_id=culture_id,
        plate_id=plate_id,
        dilution_factor=dilution,
        volume_ul=volume,
        expected_colonies=expected,
        observed_colonies=observed,
        status=status,
        warnings=warnings,
    )
    state.plated_samples[plating_id] = plated_sample
    payload = {
        "status": status,
        "plating_id": plating_id,
        "plate_id": plate_id,
        "culture_id": culture_id,
        "dilution_factor": dilution,
        "volume_ul": volume,
        "countable_range_colonies": {"min": countable_min, "max": countable_max},
        "warnings": warnings,
    }
    state.log_event("plate", payload)
    return payload


def count_colonies(state: LabState, plating_id: str) -> Dict[str, object]:
    """Return the observed colony count for a plated sample."""
    plated_sample = state.plated_samples[plating_id]
    countable_min, countable_max = state.parameters.countable_colony_range()
    payload = {
        "status": plated_sample.status,
        "plating_id": plating_id,
        "observed_colonies": plated_sample.observed_colonies,
        "dilution_factor": plated_sample.dilution_factor,
        "volume_ul": plated_sample.volume_ul,
        "countable_range_colonies": {"min": countable_min, "max": countable_max},
        "warnings": plated_sample.warnings,
    }
    state.log_event("count_colonies", payload)
    return payload


def inoculate_growth(
    state: LabState,
    condition: str,
    starting_od600: float,
) -> Dict[str, object]:
    """Start a growth-characterization culture under a named condition."""
    bundle = _growth_bundle()
    doubling_time_map = {
        "LB": bundle.value("lb_doubling_time_minutes"),
        "M9 + glucose": bundle.value("m9_glucose_doubling_time_minutes"),
        "LB + chloramphenicol (1.8 uM)": (
            bundle.value("lb_doubling_time_minutes")
            / bundle.fraction("chloramphenicol_1_8uM_relative_growth_rate")
        ),
    }
    medium_map = {
        "LB": "LB",
        "M9 + glucose": "M9 + glucose",
        "LB + chloramphenicol (1.8 uM)": "LB + chloramphenicol (1.8 uM)",
    }
    if condition not in doubling_time_map:
        raise ValueError("Unknown growth condition: {:s}".format(condition))
    starting_od = _require_positive_float(starting_od600, "starting_od600")

    growth_id = state.next_growth_id()
    culture = GrowthCulture(
        growth_id=growth_id,
        condition=condition,
        medium=medium_map[condition],
        starting_od600=starting_od,
        doubling_time_minutes=float(doubling_time_map[condition]),
    )
    state.growth_cultures[growth_id] = culture
    payload = {
        "status": "inoculated",
        "growth_id": growth_id,
        "condition": condition,
        "starting_od600": starting_od,
    }
    state.log_event("inoculate_growth", payload)
    return payload


def incubate(
    state: LabState,
    growth_id: str,
    duration_minutes: int,
) -> Dict[str, object]:
    """Advance a growth culture in time."""
    culture = state.growth_cultures[growth_id]
    duration = _require_positive_integer(duration_minutes, "duration_minutes")
    culture.current_time_minutes += duration
    payload = {
        "status": "incubated",
        "growth_id": growth_id,
        "condition": culture.condition,
        "duration_minutes": duration,
        "elapsed_minutes": int(culture.current_time_minutes),
    }
    state.log_event("incubate", payload)
    return payload


def _true_growth_od600(culture: GrowthCulture) -> float:
    return culture.starting_od600 * math.pow(2.0, culture.current_time_minutes / culture.doubling_time_minutes)


def measure_od600(
    state: LabState,
    growth_id: str,
    dilution_factor: float = 1.0,
) -> Dict[str, object]:
    """Measure OD600 for a growth culture, optionally after dilution."""
    culture = state.growth_cultures[growth_id]
    dilution = _require_positive_float(dilution_factor, "dilution_factor")
    true_od600 = _true_growth_od600(culture)
    observed_od600 = true_od600 / dilution
    measurement = GrowthMeasurement(
        elapsed_minutes=int(culture.current_time_minutes),
        dilution_factor=dilution,
        observed_od600=float(observed_od600),
        estimated_undiluted_od600=float(observed_od600 * dilution),
    )
    culture.measurements.append(measurement)
    payload = {
        "status": "measured",
        "growth_id": growth_id,
        "condition": culture.condition,
        "elapsed_minutes": int(culture.current_time_minutes),
        "dilution_factor": dilution,
        "observed_od600": float(observed_od600),
        "estimated_undiluted_od600": float(measurement.estimated_undiluted_od600),
    }
    state.log_event("measure_od600", payload)
    return payload


def fit_growth_curve(
    state: LabState,
    growth_id: str,
) -> Dict[str, object]:
    """Estimate doubling time from the measured OD600 trajectory."""
    bundle = _growth_bundle()
    culture = state.growth_cultures[growth_id]
    lower_fraction = bundle.fraction("growth_fit_lower_fraction_of_max_observed_od600")
    upper_fraction = bundle.fraction("growth_fit_upper_fraction_of_max_observed_od600")
    if not culture.measurements:
        payload = {
            "status": "insufficient_points",
            "growth_id": growth_id,
            "condition": culture.condition,
            "qualifying_points": 0,
            "warnings": ["No OD600 measurements were collected before attempting the fit."],
        }
        state.log_event("fit_growth_curve", payload)
        return payload

    max_observed = max(m.estimated_undiluted_od600 for m in culture.measurements)
    lower_bound = lower_fraction * max_observed
    upper_bound = upper_fraction * max_observed
    qualifying = [
        m for m in culture.measurements if lower_bound <= m.estimated_undiluted_od600 <= upper_bound
    ]

    if len(qualifying) < 3:
        payload = {
            "status": "insufficient_points",
            "growth_id": growth_id,
            "condition": culture.condition,
            "qualifying_points": len(qualifying),
            "lower_bound_od600": float(lower_bound),
            "upper_bound_od600": float(upper_bound),
            "warnings": [
                "Fewer than three OD600 measurements fell inside the cited fitting window."
            ],
        }
        state.log_event("fit_growth_curve", payload)
        return payload

    first = qualifying[0]
    last = qualifying[-1]
    elapsed_span = last.elapsed_minutes - first.elapsed_minutes
    if elapsed_span <= 0:
        payload = {
            "status": "insufficient_points",
            "growth_id": growth_id,
            "condition": culture.condition,
            "qualifying_points": len(qualifying),
            "lower_bound_od600": float(lower_bound),
            "upper_bound_od600": float(upper_bound),
            "warnings": [
                "Qualifying OD600 measurements did not span positive elapsed time."
            ],
        }
        state.log_event("fit_growth_curve", payload)
        return payload
    slope_per_minute = (
        math.log(last.estimated_undiluted_od600) - math.log(first.estimated_undiluted_od600)
    ) / float(elapsed_span)
    if slope_per_minute <= 0.0:
        payload = {
            "status": "insufficient_points",
            "growth_id": growth_id,
            "condition": culture.condition,
            "qualifying_points": len(qualifying),
            "lower_bound_od600": float(lower_bound),
            "upper_bound_od600": float(upper_bound),
            "warnings": [
                "Qualifying OD600 measurements did not show positive exponential growth."
            ],
        }
        state.log_event("fit_growth_curve", payload)
        return payload
    estimated_doubling_time = math.log(2.0) / slope_per_minute
    payload = {
        "status": "analyzable",
        "growth_id": growth_id,
        "condition": culture.condition,
        "qualifying_points": len(qualifying),
        "lower_bound_od600": float(lower_bound),
        "upper_bound_od600": float(upper_bound),
        "estimated_doubling_time_minutes": float(estimated_doubling_time),
        "max_observed_od600": float(max_observed),
        "warnings": [],
    }
    state.log_event("fit_growth_curve", payload)
    return payload


def run_pcr(
    state: LabState,
    polymerase_name: str,
    additive: str,
    extension_seconds: int,
    cycle_count: int,
) -> Dict[str, object]:
    """Run a single PCR attempt for the GC-rich LabCraft PCR task."""
    bundle = _pcr_bundle()
    target_size_bp = 2000
    high_fidelity_polymerases = {
        _normalize_choice(name) for name in bundle.values("gc_rich_high_fidelity_polymerases")
    }
    helpful_additives = {_normalize_choice(name) for name in bundle.values("gc_rich_additives")}
    extension_min, extension_max = bundle.range("gc_rich_extension_seconds_for_2kb_amplicon")
    cycles_min, cycles_max = bundle.range("genomic_pcr_cycle_count_range")

    canonical_polymerase = _canonical_pcr_polymerase_name(polymerase_name)
    normalized_polymerase = _normalize_choice(canonical_polymerase)
    normalized_additive = _normalize_choice(additive)
    status = "clean_target_band"
    visible_bands_bp = [target_size_bp]
    smear_present = False
    notes: List[str] = []

    if normalized_polymerase not in high_fidelity_polymerases:
        status = "nonspecific_amplification"
        visible_bands_bp = [850, target_size_bp]
        smear_present = True
        notes.append(
            "The selected polymerase was not one of the supported high-fidelity "
            "choices for this GC-rich assay."
        )
    elif normalized_additive not in helpful_additives:
        status = "gc_rich_failure"
        visible_bands_bp = []
        notes.append("No GC-resolving additive was used for the GC-rich template.")
    elif float(extension_seconds) < extension_min:
        status = "truncated_product"
        visible_bands_bp = [1200]
        notes.append("Extension time was shorter than the cited range for a 2 kb amplicon.")
    elif float(cycle_count) < cycles_min:
        status = "low_yield_target_band"
        visible_bands_bp = [target_size_bp]
        notes.append("Cycle count was below the recommended range for genomic PCR.")
    elif float(cycle_count) > cycles_max:
        status = "nonspecific_amplification"
        visible_bands_bp = [1400, target_size_bp]
        smear_present = True
        notes.append("Cycle count exceeded the recommended range for genomic PCR.")
    elif float(extension_seconds) > extension_max * 2.0:
        status = "nonspecific_amplification"
        visible_bands_bp = [target_size_bp]
        smear_present = True
        notes.append("Extension time was excessively long for the 2 kb target.")

    reaction_id = state.next_pcr_id()
    reaction = PcrReaction(
        reaction_id=reaction_id,
        polymerase_name=polymerase_name,
        additive=additive,
        extension_seconds=int(extension_seconds),
        cycle_count=int(cycle_count),
        target_size_bp=target_size_bp,
        status=status,
        visible_bands_bp=visible_bands_bp,
        smear_present=smear_present,
        notes=notes,
    )
    state.pcr_reactions[reaction_id] = reaction
    payload = {
        "status": status,
        "reaction_id": reaction_id,
        "polymerase_name": polymerase_name,
        "normalized_polymerase_name": canonical_polymerase,
        "additive": additive,
        "normalized_additive": (
            "DMSO"
            if "dmso" in normalized_additive
            else "Betaine"
            if "betaine" in normalized_additive
            else "none"
            if normalized_additive in {"none", "no additive", "not used"}
            else additive
        ),
        "extension_seconds": int(extension_seconds),
        "cycle_count": int(cycle_count),
        "target_size_bp": target_size_bp,
        "visible_bands_bp": visible_bands_bp,
        "smear_present": smear_present,
        "notes": notes,
    }
    state.log_event("run_pcr", payload)
    return payload


def run_gel(
    state: LabState,
    reaction_id: str,
    agarose_percent: float = 1.0,
    ladder_name: str = "1 kb DNA Ladder",
) -> Dict[str, object]:
    """Run a simple agarose-gel readout for a PCR reaction."""
    canonical_reaction_id = _resolve_pcr_reaction_id(state, reaction_id)
    reaction = state.pcr_reactions[canonical_reaction_id]
    status_map = {
        "clean_target_band": "single_clean_target_band",
        "low_yield_target_band": "faint_target_band",
        "truncated_product": "wrong_size_band",
        "gc_rich_failure": "no_visible_product",
        "nonspecific_amplification": "multiple_bands_or_smear",
    }
    status = status_map[reaction.status]
    notes = list(reaction.notes)
    if reaction.status == "clean_target_band":
        notes.append("A single strong band is visible near 2 kb.")
    elif reaction.status == "low_yield_target_band":
        notes.append("A faint band is visible near 2 kb.")
    elif reaction.status == "truncated_product":
        notes.append("A shorter-than-expected band is visible.")
    elif reaction.status == "gc_rich_failure":
        notes.append("No visible PCR product is present.")
    elif reaction.status == "nonspecific_amplification":
        notes.append("Multiple bands and/or smear are visible.")

    gel_id = state.next_gel_id()
    gel = GelRun(
        gel_id=gel_id,
        reaction_id=canonical_reaction_id,
        ladder_name=ladder_name,
        agarose_percent=float(agarose_percent),
        status=status,
        visible_bands_bp=list(reaction.visible_bands_bp),
        smear_present=bool(reaction.smear_present),
        notes=notes,
    )
    state.gel_runs[gel_id] = gel
    payload = {
        "status": status,
        "gel_id": gel_id,
        "reaction_id": canonical_reaction_id,
        "polymerase_name": reaction.polymerase_name,
        "normalized_polymerase_name": (
            "Q5 High-Fidelity DNA polymerase"
            if "q5" in _normalize_choice(reaction.polymerase_name)
            else "Phusion High-Fidelity DNA polymerase"
            if "phusion" in _normalize_choice(reaction.polymerase_name)
            else "Taq DNA polymerase"
            if "taq" in _normalize_choice(reaction.polymerase_name)
            else reaction.polymerase_name
        ),
        "additive": reaction.additive,
        "normalized_additive": (
            "DMSO"
            if "dmso" in _normalize_choice(reaction.additive)
            else "Betaine"
            if "betaine" in _normalize_choice(reaction.additive)
            else "none"
            if _normalize_choice(reaction.additive) in {"none", "no additive", "not used"}
            else reaction.additive
        ),
        "extension_seconds": int(reaction.extension_seconds),
        "cycle_count": int(reaction.cycle_count),
        "target_size_bp": int(reaction.target_size_bp),
        "visible_bands_bp": list(reaction.visible_bands_bp),
        "smear_present": bool(reaction.smear_present),
        "agarose_percent": float(agarose_percent),
        "ladder_name": ladder_name,
        "notes": notes,
    }
    state.log_event("run_gel", payload)
    return payload


def inspect_screening_plate(state: LabState) -> Dict[str, object]:
    """Return the fixed blue-white screening plate for Screen-01."""
    plate = _ensure_screening_plate(state)
    white_ids = sorted(colony_id for colony_id, colony in plate.colonies.items() if colony.color == "white")
    blue_ids = sorted(colony_id for colony_id, colony in plate.colonies.items() if colony.color == "blue")
    payload = {
        "status": "screening_plate_ready",
        "plate_id": plate.plate_id,
        "white_colony_ids": white_ids,
        "blue_colony_ids": blue_ids,
        "white_colony_count": len(white_ids),
        "blue_colony_count": len(blue_ids),
        "historical_positive_rate_among_white": float(plate.historical_positive_rate_among_white),
        "target_confidence": float(plate.target_confidence),
        "recombinant_band_bp": int(plate.recombinant_band_bp),
        "empty_vector_band_bp": int(plate.empty_vector_band_bp),
        "notes": [
            "White colonies are enriched for inserts but may include false positives.",
            "Blue colonies should be treated as vector-only background in this task.",
        ],
    }
    state.log_event("inspect_screening_plate", payload)
    return payload


def run_colony_pcr(
    state: LabState,
    colony_ids: List[str],
    primer_pair: str = "M13/pUC flank primers",
) -> Dict[str, object]:
    """Run colony PCR on the requested blue-white screening colonies."""
    if not colony_ids:
        raise ValueError("run_colony_pcr requires at least one colony_id.")

    plate = _ensure_screening_plate(state)
    results = []
    batch_screening_strategy = "white_only"
    batch_confirmed = []
    for colony_id in colony_ids:
        if colony_id not in plate.colonies:
            raise ValueError(
                "Unknown colony_id '{:s}'. Available colony IDs: {:s}".format(
                    colony_id,
                    ", ".join(sorted(plate.colonies)),
                )
            )
        colony = plate.colonies[colony_id]
        if colony.color != "white":
            batch_screening_strategy = "includes_blue"
        if colony_id not in plate.screened_colony_ids:
            plate.screened_colony_ids.append(colony_id)
        result = {
            "colony_id": colony.colony_id,
            "color": colony.color,
            "status": "recombinant_positive" if colony.is_recombinant else "empty_vector_or_background",
            "visible_bands_bp": [int(colony.expected_band_bp)],
            "notes": list(colony.notes),
        }
        results.append(result)
        if colony.is_recombinant:
            batch_confirmed.append(colony.colony_id)

    cumulative_white_ids = [
        colony_id
        for colony_id in plate.screened_colony_ids
        if plate.colonies[colony_id].color == "white"
    ]
    confidence = 1.0 - math.pow(
        1.0 - float(plate.historical_positive_rate_among_white),
        len(cumulative_white_ids),
    )
    cumulative_confirmed = sorted(
        colony_id
        for colony_id in plate.screened_colony_ids
        if plate.colonies[colony_id].is_recombinant
    )
    payload = {
        "status": "screened",
        "plate_id": plate.plate_id,
        "primer_pair": primer_pair,
        "screened_colony_ids": list(colony_ids),
        "screened_colony_count": len(colony_ids),
        "screening_strategy": batch_screening_strategy,
        "colony_pcr_used": True,
        "results": results,
        "confirmed_recombinant_ids_in_batch": sorted(batch_confirmed),
        "confirmed_recombinant_ids_cumulative": cumulative_confirmed,
        "cumulative_screened_white_colony_count": len(cumulative_white_ids),
        "cumulative_confidence_pct": round(confidence * 100.0, 1),
        "recombinant_band_bp": int(plate.recombinant_band_bp),
        "empty_vector_band_bp": int(plate.empty_vector_band_bp),
    }
    state.log_event("run_colony_pcr", payload)
    return payload


def _normalize_enzyme_pair(enzyme_names: List[str]) -> List[str]:
    return sorted(_normalize_choice(name).replace(" ", "").lower() for name in enzyme_names)


def _ensure_cloning_substrates(state: LabState) -> None:
    if state.cloning_substrates_initialized:
        return
    bundle = _cloning_bundle()
    vector = DnaFragment(
        fragment_id="puc19_vector",
        name="pUC19 vector",
        length_bp=bundle.integer("vector_plasmid_length_bp"),
        concentration_ng_ul=50.0,
        is_circular=True,
        end_5_prime="circular",
        end_3_prime="circular",
        recognition_sites=["EcoRI", "BamHI", "HindIII"],
        notes=["Circular pUC19 cloning vector with EcoRI, BamHI, and HindIII sites in the MCS."],
    )
    insert = DnaFragment(
        fragment_id="insert_raw",
        name="Benign 950 bp PCR insert",
        length_bp=bundle.integer("insert_length_bp"),
        concentration_ng_ul=20.0,
        is_circular=False,
        end_5_prime="flanking_EcoRI_site",
        end_3_prime="flanking_BamHI_site",
        recognition_sites=["EcoRI", "BamHI"],
        notes=[
            "Linear PCR product with EcoRI and BamHI recognition sequences in the flanking primers."
        ],
    )
    state.dna_fragments[vector.fragment_id] = vector
    state.dna_fragments[insert.fragment_id] = insert
    state.cloning_substrates_initialized = True


def list_cloning_substrates(state: LabState) -> Dict[str, object]:
    _ensure_cloning_substrates(state)
    fragments = [
        {
            "fragment_id": fragment.fragment_id,
            "name": fragment.name,
            "length_bp": int(fragment.length_bp),
            "concentration_ng_ul": float(fragment.concentration_ng_ul),
            "is_circular": bool(fragment.is_circular),
            "end_5_prime": fragment.end_5_prime,
            "end_3_prime": fragment.end_3_prime,
            "recognition_sites": list(fragment.recognition_sites),
        }
        for fragment in state.dna_fragments.values()
    ]
    payload = {
        "status": "cloning_substrates_ready",
        "fragments": fragments,
    }
    state.log_event("list_cloning_substrates", payload)
    return payload


def restriction_digest(
    state: LabState,
    fragment_id: str,
    enzyme_names: List[str],
    buffer: str,
    temperature_c: float,
    duration_minutes: int,
    heat_inactivate_after: bool,
    heat_inactivation_temperature_c: float = 65.0,
) -> Dict[str, object]:
    """Simulate a restriction digest on a DNA fragment."""
    _ensure_cloning_substrates(state)
    if fragment_id not in state.dna_fragments:
        raise ValueError(
            "Unknown fragment_id '{:s}'. Available fragment IDs: {:s}".format(
                fragment_id, ", ".join(sorted(state.dna_fragments))
            )
        )
    bundle = _cloning_bundle()
    substrate = state.dna_fragments[fragment_id]
    compatible_buffers = {b.lower() for b in bundle.choices("compatible_double_digest_buffers")}
    normalized_enzymes = _normalize_enzyme_pair(enzyme_names)
    optimal_duration = bundle.integer("digest_minimum_duration_minutes")
    optimal_temperature = bundle.value("digest_temperature_c")
    heat_inactivation_target = bundle.value("digest_heat_inactivation_temperature_c")

    notes: List[str] = []
    status = "digested"

    if len(enzyme_names) != 2 or normalized_enzymes != ["bamhi", "ecori"]:
        status = "wrong_enzyme_pair"
        notes.append(
            "Digest did not use the EcoRI + BamHI pair required for this directional cloning workflow."
        )
    if buffer.lower() not in compatible_buffers:
        status = "wrong_buffer"
        notes.append("Digest buffer is not compatible with simultaneous EcoRI + BamHI activity.")
    if abs(float(temperature_c) - optimal_temperature) > 2.0:
        notes.append("Digest temperature deviated from the 37 C optimum.")
    if int(duration_minutes) < optimal_duration:
        notes.append(
            "Digest duration was shorter than the {} min minimum recommended for complete plasmid digestion.".format(
                optimal_duration
            )
        )
        if status == "digested":
            status = "incomplete_digest"

    if heat_inactivate_after and abs(float(heat_inactivation_temperature_c) - heat_inactivation_target) > 2.0:
        notes.append(
            "Heat inactivation temperature deviated from the {:.0f} C recommendation.".format(
                heat_inactivation_target
            )
        )

    digest_id = state.next_digest_id()
    output_fragment_ids: List[str] = []
    if status in {"digested", "incomplete_digest"}:
        output_id = state.next_fragment_id()
        is_vector = substrate.is_circular
        end_5 = "EcoRI_overhang"
        end_3 = "BamHI_overhang"
        length_bp = substrate.length_bp
        if is_vector:
            length_bp = substrate.length_bp
        output_fragment = DnaFragment(
            fragment_id=output_id,
            name="{} (EcoRI+BamHI digested)".format(substrate.name),
            length_bp=int(length_bp),
            concentration_ng_ul=float(substrate.concentration_ng_ul) * 0.9,
            is_circular=False,
            end_5_prime=end_5,
            end_3_prime=end_3,
            recognition_sites=["EcoRI", "BamHI"],
            parent_fragment_id=substrate.fragment_id,
            source_digest_id=digest_id,
            notes=[
                "Linearized fragment with compatible EcoRI (5' overhang: AATT) and BamHI (5' overhang: GATC) ends."
            ],
        )
        state.dna_fragments[output_id] = output_fragment
        output_fragment_ids.append(output_id)

    reaction = DigestReaction(
        digest_id=digest_id,
        substrate_fragment_id=fragment_id,
        enzyme_names=list(enzyme_names),
        buffer=buffer,
        temperature_c=float(temperature_c),
        duration_minutes=int(duration_minutes),
        heat_inactivate_after=bool(heat_inactivate_after),
        status=status,
        output_fragment_ids=list(output_fragment_ids),
        notes=list(notes),
    )
    state.digest_reactions[digest_id] = reaction
    enzymes_key = "+".join(normalized_enzymes)
    payload = {
        "status": status,
        "digest_id": digest_id,
        "substrate_fragment_id": fragment_id,
        "enzyme_names": list(enzyme_names),
        "enzymes_key": enzymes_key,
        "buffer": buffer,
        "buffer_normalized": _normalize_choice(buffer).replace(" ", "").lower(),
        "temperature_c": float(temperature_c),
        "duration_minutes": int(duration_minutes),
        "heat_inactivate_after": bool(heat_inactivate_after),
        "output_fragment_ids": list(output_fragment_ids),
        "notes": list(notes),
    }
    state.log_event("restriction_digest", payload)
    return payload


def _resolve_ligation_fragment_id(state: LabState, fragment_id: str) -> str:
    """Resolve a fragment reference that may be a fragment_id or a digest_id shorthand."""
    requested = str(fragment_id).strip()
    if requested in state.dna_fragments:
        return requested
    if requested in state.digest_reactions:
        outputs = state.digest_reactions[requested].output_fragment_ids
        if outputs:
            return outputs[0]
    suffix_match = re.search(r"(\d+)$", requested)
    if suffix_match:
        canonical_digest = "digest_{:03d}".format(int(suffix_match.group(1)))
        if canonical_digest in state.digest_reactions:
            outputs = state.digest_reactions[canonical_digest].output_fragment_ids
            if outputs:
                return outputs[0]
        canonical_fragment = "fragment_{:03d}".format(int(suffix_match.group(1)))
        if canonical_fragment in state.dna_fragments:
            return canonical_fragment
    available_frags = sorted(state.dna_fragments)
    available_digests = sorted(state.digest_reactions)
    raise ValueError(
        "Unknown fragment reference '{:s}'. Available fragment IDs: {:s}. Available digest IDs: {:s}.".format(
            requested,
            ", ".join(available_frags) if available_frags else "none",
            ", ".join(available_digests) if available_digests else "none",
        )
    )


def _source_digest_id_for_fragment(state: LabState, fragment_id: str) -> str | None:
    fragment = state.dna_fragments[fragment_id]
    if fragment.source_digest_id and fragment.source_digest_id in state.digest_reactions:
        return fragment.source_digest_id
    for digest_id, reaction in state.digest_reactions.items():
        if fragment_id in reaction.output_fragment_ids:
            return digest_id
    return None


def ligate(
    state: LabState,
    vector_fragment_id: str,
    insert_fragment_ids: List[str],
    ligase_name: str,
    vector_to_insert_molar_ratio: float,
    temperature_c: float,
    duration_minutes: int,
    buffer: str = "T4 DNA ligase buffer",
) -> Dict[str, object]:
    """Simulate a ligation reaction and return a ligation id."""
    _ensure_cloning_substrates(state)
    vector_fragment_id = _resolve_ligation_fragment_id(state, vector_fragment_id)
    insert_fragment_ids = [
        _resolve_ligation_fragment_id(state, insert_id) for insert_id in insert_fragment_ids
    ]

    bundle = _cloning_bundle()
    required_ligase = bundle.text("preferred_ligase_name")
    acceptable_temps = [float(t) for t in bundle.choices("acceptable_ligation_temperatures_c")]
    minimum_duration = bundle.integer("acceptable_ligation_duration_minutes_min")
    base_fraction = bundle.value("base_recombinant_fraction_among_white_colonies")

    vector = state.dna_fragments[vector_fragment_id]
    inserts = [state.dna_fragments[i] for i in insert_fragment_ids]

    notes: List[str] = []
    status = "ligated"
    effective_fraction = base_fraction

    if _normalize_choice(ligase_name) != _normalize_choice(required_ligase):
        status = "wrong_ligase"
        notes.append(
            "Non-T4 ligase used; T4 DNA ligase is required for ATP-dependent cohesive-end ligation in this workflow."
        )
        effective_fraction *= 0.10

    if vector.end_5_prime == "circular" or vector.end_3_prime == "circular":
        notes.append("Vector appears to be an uncut circular plasmid; digest it before ligation.")
        if status == "ligated":
            status = "incompatible_ends"
        effective_fraction *= 0.05

    for insert in inserts:
        if insert.end_5_prime in {"flanking_EcoRI_site", "flanking_BamHI_site", "blunt", "circular"}:
            notes.append(
                "Insert {} has unprocessed ends and may not ligate efficiently without digestion.".format(
                    insert.fragment_id
                )
            )
            if status == "ligated":
                status = "incompatible_ends"
            effective_fraction *= 0.10

    ratio = float(vector_to_insert_molar_ratio)
    if ratio <= 0:
        notes.append("Vector:insert molar ratio must be positive.")
        status = "wrong_ratio"
        effective_fraction *= 0.0
    elif ratio < 0.1 or ratio > 10.0:
        notes.append("Vector:insert molar ratio is outside the standard 1:10 - 10:1 range.")
        if status == "ligated":
            status = "wrong_ratio"
        effective_fraction *= 0.5

    if not any(abs(float(temperature_c) - t) <= 1.0 for t in acceptable_temps):
        notes.append(
            "Ligation temperature {:.1f} C is outside the acceptable set {}.".format(
                float(temperature_c), acceptable_temps
            )
        )
        effective_fraction *= 0.5

    if int(duration_minutes) < minimum_duration:
        notes.append(
            "Ligation duration was shorter than the {} min minimum.".format(minimum_duration)
        )
        effective_fraction *= 0.5

    source_digest_ids = [
        digest_id
        for fragment_id in [vector_fragment_id] + list(insert_fragment_ids)
        if (digest_id := _source_digest_id_for_fragment(state, fragment_id)) is not None
    ]
    digest_heat_inactivated = {
        digest_id: bool(state.digest_reactions[digest_id].heat_inactivate_after)
        for digest_id in source_digest_ids
    }
    if digest_heat_inactivated and not all(digest_heat_inactivated.values()):
        notes.append(
            "Digests feeding this ligation were not heat-inactivated; residual nuclease may degrade the ligation."
        )
        effective_fraction *= 0.30

    effective_fraction = max(0.0, min(1.0, float(effective_fraction)))

    yield_multiplier = 1.0 if status == "ligated" else 0.25
    expected_transformant_yield = 400.0 * yield_multiplier * (effective_fraction / base_fraction + 0.1)

    ligation_id = state.next_ligation_id()
    reaction = LigationReaction(
        ligation_id=ligation_id,
        vector_fragment_id=vector_fragment_id,
        insert_fragment_ids=list(insert_fragment_ids),
        ligase_name=ligase_name,
        vector_to_insert_molar_ratio=float(ratio),
        temperature_c=float(temperature_c),
        duration_minutes=int(duration_minutes),
        status=status,
        effective_recombinant_fraction=float(effective_fraction),
        expected_transformant_yield=float(expected_transformant_yield),
        notes=list(notes),
    )
    state.ligation_reactions[ligation_id] = reaction
    payload = {
        "status": status,
        "ligation_id": ligation_id,
        "vector_fragment_id": vector_fragment_id,
        "insert_fragment_ids": list(insert_fragment_ids),
        "ligase_name": ligase_name,
        "ligase_normalized": _normalize_choice(ligase_name),
        "vector_to_insert_molar_ratio": float(ratio),
        "temperature_c": float(temperature_c),
        "duration_minutes": int(duration_minutes),
        "buffer": buffer,
        "source_digest_ids": list(source_digest_ids),
        "notes": list(notes),
    }
    state.log_event("ligate", payload)
    return payload


def _resolve_ligation_id(state: LabState, ligation_id: str) -> str:
    requested = str(ligation_id).strip()
    if requested in state.ligation_reactions:
        return requested
    suffix_match = re.search(r"(\d+)$", requested)
    if suffix_match:
        canonical = "ligation_{:03d}".format(int(suffix_match.group(1)))
        if canonical in state.ligation_reactions:
            return canonical
    available = sorted(state.ligation_reactions)
    raise ValueError(
        "Unknown ligation_id '{:s}'. Available ligation IDs: {:s}".format(
            requested, ", ".join(available) if available else "none"
        )
    )


def transform_ligation(
    state: LabState,
    ligation_id: str,
    heat_shock_seconds: int = 30,
    recovery_minutes: int = 60,
    outgrowth_media: str = "SOC",
    shaking: bool = True,
    ice_incubation_minutes: int = 30,
) -> Dict[str, object]:
    """Transform a ligation reaction into competent E. coli and prepare a screening plate."""
    resolved_id = _resolve_ligation_id(state, ligation_id)
    ligation = state.ligation_reactions[resolved_id]
    screening_bundle = _screening_bundle()

    expected_yield = float(ligation.expected_transformant_yield)
    if int(heat_shock_seconds) != int(
        state.parameters.get("heat_shock_duration_seconds")["parameters"]["optimal"]
    ):
        expected_yield *= 0.5
    if outgrowth_media.upper() != "SOC":
        expected_yield *= 0.5
    if not shaking:
        expected_yield *= 0.7

    culture_id = state.next_culture_id()
    notes = list(ligation.notes)
    culture = TransformationCulture(
        culture_id=culture_id,
        plasmid_mass_pg=float(expected_yield * 1000.0),
        base_efficiency_cfu_per_ug=state.base_efficiency_cfu_per_ug,
        adjusted_efficiency_cfu_per_ug=state.base_efficiency_cfu_per_ug,
        recovery_minutes=int(recovery_minutes),
        outgrowth_media=outgrowth_media,
        shaking=bool(shaking),
        heat_shock_seconds=int(heat_shock_seconds),
        ice_incubation_minutes=int(ice_incubation_minutes),
        expected_total_transformants=expected_yield,
        notes=notes,
    )
    state.cultures[culture_id] = culture

    if not state.screening_plates:
        plate_id = state.next_screening_plate_id()
        recombinant_band_bp = screening_bundle.integer("screening_recombinant_colony_pcr_band_bp")
        empty_vector_band_bp = screening_bundle.integer("screening_empty_vector_colony_pcr_band_bp")
        plate = ScreeningPlate(
            plate_id=plate_id,
            historical_positive_rate_among_white=float(ligation.effective_recombinant_fraction),
            target_confidence=screening_bundle.value("screening_target_confidence"),
            recombinant_band_bp=recombinant_band_bp,
            empty_vector_band_bp=empty_vector_band_bp,
        )
        recombinant_whites: set = set()
        for idx in range(1, 13):
            if state.rng.random() < ligation.effective_recombinant_fraction:
                recombinant_whites.add("white_{:03d}".format(idx))
        for idx in range(1, 13):
            colony_id = "white_{:03d}".format(idx)
            is_recombinant = colony_id in recombinant_whites
            plate.colonies[colony_id] = ScreeningColony(
                colony_id=colony_id,
                color="white",
                is_recombinant=is_recombinant,
                expected_band_bp=recombinant_band_bp if is_recombinant else empty_vector_band_bp,
                notes=[
                    "White colony from Clone-01 transformation.",
                    "Expected insert-positive band near {:d} bp.".format(recombinant_band_bp)
                    if is_recombinant
                    else "White false positive with empty-vector-like colony PCR band.",
                ],
            )
        for idx in range(1, 19):
            colony_id = "blue_{:03d}".format(idx)
            plate.colonies[colony_id] = ScreeningColony(
                colony_id=colony_id,
                color="blue",
                is_recombinant=False,
                expected_band_bp=empty_vector_band_bp,
                notes=["Blue colony retaining lacZ alpha activity; treat as vector-only background."],
            )
        state.screening_plates[plate_id] = plate

    payload = {
        "status": "transformed",
        "culture_id": culture_id,
        "ligation_id": resolved_id,
        "ligation_status": ligation.status,
        "expected_transformants": float(expected_yield),
        "heat_shock_seconds": int(heat_shock_seconds),
        "recovery_minutes": int(recovery_minutes),
        "outgrowth_media": outgrowth_media,
        "notes": notes,
    }
    state.log_event("transform_ligation", payload)
    return payload


def _ensure_golden_gate_substrates(state: LabState) -> None:
    """Seed the four Golden Gate fragments (1 backbone + 3 inserts) the agent starts with."""
    if state.golden_gate_substrates_initialized:
        return
    bundle = _golden_gate_bundle()
    backbone = DnaFragment(
        fragment_id="gg_backbone",
        name="pGG_backbone (BsaI-flanked destination vector)",
        length_bp=2900,
        concentration_ng_ul=40.0,
        is_circular=False,
        end_5_prime="BsaI_overhang_A",
        end_3_prime="BsaI_overhang_D",
        recognition_sites=["BsaI"],
        notes=["Pre-linearised Golden Gate destination vector with BsaI-cut ends A and D."],
    )
    fragments = [backbone]
    for idx, (name, size, ends) in enumerate(
        [
            ("gg_insert_promoter", 380, ("BsaI_overhang_A", "BsaI_overhang_B")),
            ("gg_insert_cds", 740, ("BsaI_overhang_B", "BsaI_overhang_C")),
            ("gg_insert_terminator", 290, ("BsaI_overhang_C", "BsaI_overhang_D")),
        ],
        start=1,
    ):
        fragments.append(
            DnaFragment(
                fragment_id=name,
                name="{} (BsaI-flanked insert)".format(name),
                length_bp=size,
                concentration_ng_ul=20.0,
                is_circular=False,
                end_5_prime=ends[0],
                end_3_prime=ends[1],
                recognition_sites=["BsaI"],
                notes=["Golden Gate insert with directional BsaI overhangs."],
            )
        )
    for fragment in fragments:
        state.dna_fragments[fragment.fragment_id] = fragment
    state.golden_gate_substrates_initialized = True
    # Expose accepted-enzyme list on the bundle so downstream ops can read it without re-loading.
    _ = bundle


def list_golden_gate_substrates(state: LabState) -> Dict[str, object]:
    """Return the four Golden Gate starting fragments."""
    _ensure_golden_gate_substrates(state)
    fragments = [
        {
            "fragment_id": fragment.fragment_id,
            "name": fragment.name,
            "length_bp": int(fragment.length_bp),
            "concentration_ng_ul": float(fragment.concentration_ng_ul),
            "end_5_prime": fragment.end_5_prime,
            "end_3_prime": fragment.end_3_prime,
            "recognition_sites": list(fragment.recognition_sites),
        }
        for fragment in state.dna_fragments.values()
        if fragment.fragment_id.startswith("gg_")
    ]
    payload = {
        "status": "golden_gate_substrates_ready",
        "fragments": fragments,
        "expected_fragment_count": 4,
        "assembly_order_hint": "Overhangs chain A -> B -> C -> D for directional assembly.",
    }
    state.log_event("list_golden_gate_substrates", payload)
    return payload


def golden_gate_assembly(
    state: LabState,
    fragment_ids: List[str],
    enzyme_name: str,
    ligase_name: str,
    buffer: str = "T4 DNA ligase buffer",
    cycle_count: int = 30,
    digest_temperature_c: float = 37.0,
    ligate_temperature_c: float = 16.0,
    final_digest_minutes: int = 5,
    final_digest_temperature_c: float = 60.0,
) -> Dict[str, object]:
    """Simulate a Golden Gate / Type IIS one-pot assembly."""
    _ensure_golden_gate_substrates(state)
    bundle = _golden_gate_bundle()
    accepted_enzymes = {
        _normalize_type_iis_enzyme(enzyme)
        for enzyme in bundle.choices("accepted_type_iis_enzymes")
    }
    accepted_buffers = {
        _normalize_golden_gate_buffer(buffer_name)
        for buffer_name in bundle.choices("accepted_one_pot_buffers")
    }
    required_ligase = bundle.text("preferred_ligase_name")
    optimal_digest_c = bundle.value("digest_cycling_temperature_c")
    optimal_ligate_c = bundle.value("ligate_cycling_temperature_c")
    final_digest_c = bundle.value("final_digest_temperature_c")
    final_digest_duration = bundle.integer("final_digest_duration_minutes")
    required_cycles = bundle.integer("required_cycle_count")
    base_efficiency = bundle.value("base_assembly_efficiency")
    expected_fragment_count = bundle.integer("fragment_count")

    notes: List[str] = []
    failure_statuses: List[str] = []

    for fragment_id in fragment_ids:
        if fragment_id not in state.dna_fragments:
            raise ValueError(
                "Unknown fragment_id '{:s}'. Available: {:s}".format(
                    fragment_id, ", ".join(sorted(state.dna_fragments))
                )
            )

    if len(fragment_ids) != expected_fragment_count:
        failure_statuses.append("wrong_fragment_count")
        notes.append(
            "Golden Gate-01 requires exactly {:d} fragments; received {:d}.".format(
                expected_fragment_count, len(fragment_ids)
            )
        )
    else:
        expected_fragment_ids = {
            "gg_backbone",
            "gg_insert_promoter",
            "gg_insert_cds",
            "gg_insert_terminator",
        }
        if set(fragment_ids) != expected_fragment_ids:
            failure_statuses.append("wrong_fragment_count")
            notes.append(
                "Golden Gate-01 requires each expected backbone/promoter/CDS/terminator fragment exactly once."
            )

    enzyme_normalized = _normalize_type_iis_enzyme(enzyme_name)
    substrates_match_enzyme = all(
        enzyme_normalized
        in {
            _normalize_type_iis_enzyme(site)
            for site in state.dna_fragments[fragment_id].recognition_sites
        }
        for fragment_id in fragment_ids
    )
    if enzyme_normalized not in accepted_enzymes or not substrates_match_enzyme:
        failure_statuses.append("wrong_enzyme")
        notes.append(
            "Enzyme '{}' is not compatible with the BsaI-flanked Golden Gate-01 substrates.".format(enzyme_name)
        )

    if _normalize_choice(ligase_name) != _normalize_choice(required_ligase):
        failure_statuses.append("wrong_ligase")
        notes.append(
            "Non-T4 ligase used; Golden Gate cycling requires T4 DNA ligase co-incubation."
        )

    if _normalize_golden_gate_buffer(buffer) not in accepted_buffers:
        failure_statuses.append("wrong_buffer")
        notes.append(
            "Golden Gate-01 requires an ATP-containing T4 DNA ligase reaction buffer."
        )

    if not math.isclose(
        float(final_digest_temperature_c),
        final_digest_c,
        rel_tol=0.0,
        abs_tol=1e-9,
    ) or not math.isclose(
        float(final_digest_minutes),
        float(final_digest_duration),
        rel_tol=0.0,
        abs_tol=1e-9,
    ):
        failure_statuses.append("wrong_terminal_digest")
        notes.append(
            "Golden Gate-01 requires the cited {:.0f} C, {:d}-minute terminal digest.".format(
                final_digest_c,
                final_digest_duration,
            )
        )

    cycle_count_value = float(cycle_count)
    thermal_program_valid = (
        math.isfinite(float(digest_temperature_c))
        and math.isclose(
            float(digest_temperature_c),
            optimal_digest_c,
            rel_tol=0.0,
            abs_tol=1e-9,
        )
        and math.isfinite(float(ligate_temperature_c))
        and math.isclose(
            float(ligate_temperature_c),
            optimal_ligate_c,
            rel_tol=0.0,
            abs_tol=1e-9,
        )
        and math.isfinite(cycle_count_value)
        and cycle_count_value.is_integer()
        and int(cycle_count_value) == required_cycles
    )
    if not thermal_program_valid:
        failure_statuses.append("wrong_thermal_program")
        notes.append(
            "Golden Gate-01 requires {:d} cycles of {:.0f} C digestion and {:.0f} C ligation.".format(
                required_cycles,
                optimal_digest_c,
                optimal_ligate_c,
            )
        )

    efficiency_multiplier = 1.0
    status = failure_statuses[0] if failure_statuses else "assembled"
    if status == "assembled":
        effective_efficiency = base_efficiency * efficiency_multiplier
    elif status == "wrong_enzyme":
        effective_efficiency = 0.02
    elif status == "wrong_ligase":
        effective_efficiency = 0.05
    else:
        effective_efficiency = base_efficiency * 0.10

    effective_efficiency = max(0.0, min(1.0, float(effective_efficiency)))
    expected_transformant_yield = 600.0 * efficiency_multiplier if status == "assembled" else 60.0

    assembly_id = state.next_assembly_id()
    output_fragment_id = None
    if status in {"assembled"}:
        output_fragment_id = state.next_fragment_id()
        total_length = sum(state.dna_fragments[f].length_bp for f in fragment_ids)
        output_fragment = DnaFragment(
            fragment_id=output_fragment_id,
            name="Golden Gate assembled construct ({})".format(assembly_id),
            length_bp=int(total_length),
            concentration_ng_ul=15.0,
            is_circular=True,
            end_5_prime="circular",
            end_3_prime="circular",
            recognition_sites=[],
            notes=["Circular assembled Golden Gate construct."],
        )
        state.dna_fragments[output_fragment_id] = output_fragment

    reaction = AssemblyReaction(
        assembly_id=assembly_id,
        fragment_ids=list(fragment_ids),
        enzyme_name=enzyme_name,
        ligase_name=ligase_name,
        buffer=buffer,
        cycle_count=int(cycle_count),
        digest_temperature_c=float(digest_temperature_c),
        ligate_temperature_c=float(ligate_temperature_c),
        final_digest_minutes=int(final_digest_minutes),
        final_digest_temperature_c=float(final_digest_temperature_c),
        status=status,
        effective_assembly_efficiency=float(effective_efficiency),
        expected_transformant_yield=float(expected_transformant_yield),
        output_fragment_id=output_fragment_id,
        notes=list(notes),
    )
    state.assembly_reactions[assembly_id] = reaction
    payload = {
        "status": status,
        "assembly_id": assembly_id,
        "fragment_ids": list(fragment_ids),
        "fragment_count": len(fragment_ids),
        "enzyme_name": enzyme_name,
        "enzyme_normalized": enzyme_normalized,
        "ligase_name": ligase_name,
        "ligase_normalized": _normalize_choice(ligase_name),
        "buffer": buffer,
        "cycle_count": int(cycle_count),
        "digest_temperature_c": float(digest_temperature_c),
        "ligate_temperature_c": float(ligate_temperature_c),
        "final_digest_minutes": int(final_digest_minutes),
        "final_digest_temperature_c": float(final_digest_temperature_c),
        "output_fragment_id": output_fragment_id,
        "effective_assembly_efficiency": float(effective_efficiency),
        "expected_transformant_yield": float(expected_transformant_yield),
        "notes": list(notes),
    }
    state.log_event("golden_gate_assembly", payload)
    return payload


def _resolve_assembly_id(state: LabState, assembly_id: str) -> str:
    """Accept full or suffix-based Golden Gate assembly ids."""
    requested = str(assembly_id).strip()
    if requested in state.assembly_reactions:
        return requested
    suffix_match = re.search(r"(\d+)$", requested)
    if suffix_match:
        canonical = "assembly_{:03d}".format(int(suffix_match.group(1)))
        if canonical in state.assembly_reactions:
            return canonical
    available = sorted(state.assembly_reactions)
    raise ValueError(
        "Unknown assembly_id '{:s}'. Available assembly IDs: {:s}".format(
            requested, ", ".join(available) if available else "none"
        )
    )


def transform_assembly(
    state: LabState,
    assembly_id: str,
    heat_shock_seconds: int = 30,
    recovery_minutes: int = 60,
    outgrowth_media: str = "SOC",
    shaking: bool = True,
    ice_incubation_minutes: int = 30,
) -> Dict[str, object]:
    """Transform a Golden Gate assembled construct into competent E. coli."""
    resolved_id = _resolve_assembly_id(state, assembly_id)
    assembly = state.assembly_reactions[resolved_id]

    expected_yield = float(assembly.expected_transformant_yield)
    if int(heat_shock_seconds) != int(
        state.parameters.get("heat_shock_duration_seconds")["parameters"]["optimal"]
    ):
        expected_yield *= 0.5
    if outgrowth_media.upper() != "SOC":
        expected_yield *= 0.5
    if not shaking:
        expected_yield *= 0.7

    culture_id = state.next_culture_id()
    notes = list(assembly.notes)
    culture = TransformationCulture(
        culture_id=culture_id,
        plasmid_mass_pg=float(expected_yield * 1000.0),
        base_efficiency_cfu_per_ug=state.base_efficiency_cfu_per_ug,
        adjusted_efficiency_cfu_per_ug=state.base_efficiency_cfu_per_ug,
        recovery_minutes=int(recovery_minutes),
        outgrowth_media=outgrowth_media,
        shaking=bool(shaking),
        heat_shock_seconds=int(heat_shock_seconds),
        ice_incubation_minutes=int(ice_incubation_minutes),
        expected_total_transformants=expected_yield,
        notes=notes,
    )
    state.cultures[culture_id] = culture
    payload = {
        "status": "transformed",
        "culture_id": culture_id,
        "assembly_id": resolved_id,
        "assembly_status": assembly.status,
        "effective_assembly_efficiency": float(assembly.effective_assembly_efficiency),
        "expected_transformants": float(expected_yield),
        "heat_shock_seconds": int(heat_shock_seconds),
        "recovery_minutes": int(recovery_minutes),
        "outgrowth_media": outgrowth_media,
        "notes": notes,
    }
    state.log_event("transform_assembly", payload)
    return payload


def _ensure_gibson_substrates(state: LabState) -> None:
    """Seed the two Gibson fragments (linearised backbone + PCR insert) with homology overlaps."""
    if state.gibson_substrates_initialized:
        return
    bundle = _gibson_bundle()
    insert_length = bundle.integer("insert_length_bp")
    overlap = bundle.integer("task_overlap_length_bp")
    backbone = DnaFragment(
        fragment_id="gibson_backbone_linear",
        name="Linearised Gibson destination vector (20 bp homology overhangs)",
        length_bp=3200,
        concentration_ng_ul=40.0,
        is_circular=False,
        end_5_prime="homology_overlap_upstream_{}bp".format(overlap),
        end_3_prime="homology_overlap_downstream_{}bp".format(overlap),
        recognition_sites=[],
        notes=["Linear vector with {} bp homology overhangs at each end.".format(overlap)],
    )
    insert = DnaFragment(
        fragment_id="gibson_insert_pcr",
        name="PCR insert with 20 bp Gibson homology overhangs",
        length_bp=insert_length,
        concentration_ng_ul=20.0,
        is_circular=False,
        end_5_prime="homology_overlap_upstream_{}bp".format(overlap),
        end_3_prime="homology_overlap_downstream_{}bp".format(overlap),
        recognition_sites=[],
        notes=["PCR product with {} bp homology overhangs matching the linearised backbone.".format(overlap)],
    )
    state.dna_fragments[backbone.fragment_id] = backbone
    state.dna_fragments[insert.fragment_id] = insert
    state.gibson_substrates_initialized = True


def list_gibson_substrates(state: LabState) -> Dict[str, object]:
    """Return the two Gibson starting fragments."""
    _ensure_gibson_substrates(state)
    fragments = [
        {
            "fragment_id": fragment.fragment_id,
            "name": fragment.name,
            "length_bp": int(fragment.length_bp),
            "concentration_ng_ul": float(fragment.concentration_ng_ul),
            "end_5_prime": fragment.end_5_prime,
            "end_3_prime": fragment.end_3_prime,
        }
        for fragment in state.dna_fragments.values()
        if fragment.fragment_id.startswith("gibson_")
    ]
    payload = {
        "status": "gibson_substrates_ready",
        "fragments": fragments,
        "expected_fragment_count": 2,
    }
    state.log_event("list_gibson_substrates", payload)
    return payload


def gibson_assembly(
    state: LabState,
    fragment_ids: List[str],
    master_mix_name: str,
    temperature_c: float,
    duration_minutes: int,
    overlap_length_bp: int = 20,
) -> Dict[str, object]:
    """Simulate a Gibson isothermal overlap assembly."""
    _ensure_gibson_substrates(state)
    bundle = _gibson_bundle()
    base_efficiency = bundle.value("base_assembly_efficiency")

    temperature = _require_positive_float(temperature_c, "temperature_c")
    duration = _require_positive_integer(duration_minutes, "duration_minutes")
    overlap = _require_positive_integer(overlap_length_bp, "overlap_length_bp")

    for fragment_id in fragment_ids:
        if fragment_id not in state.dna_fragments:
            raise ValueError(
                "Unknown fragment_id '{:s}'. Available: {:s}".format(
                    fragment_id, ", ".join(sorted(state.dna_fragments))
                )
            )

    notes: List[str] = []
    failure_markers: List[str] = []
    if len(fragment_ids) != len(GIBSON_FRAGMENT_IDS) or set(fragment_ids) != GIBSON_FRAGMENT_IDS:
        failure_markers.append("wrong_fragment_count")
        notes.append("Gibson-01 requires the linear backbone and PCR insert exactly once.")

    canonical_mix = canonicalize_gibson_master_mix(master_mix_name)
    if canonical_mix is None:
        failure_markers.append("wrong_master_mix")
        notes.append(
            "Master mix '{}' is not a supported Gibson-compatible isothermal assembly mix.".format(
                master_mix_name
            )
        )

    if temperature != GIBSON_TEMPERATURE_C:
        failure_markers.append("wrong_temperature")
        notes.append("Gibson-01 requires the cited 50 C isothermal incubation.")
    if not GIBSON_MIN_DURATION_MINUTES <= duration <= GIBSON_MAX_DURATION_MINUTES:
        failure_markers.append("wrong_duration")
        notes.append(
            "Gibson-01 requires a {:d}-{:d} minute incubation for this two-fragment reaction.".format(
                GIBSON_MIN_DURATION_MINUTES,
                GIBSON_MAX_DURATION_MINUTES,
            )
        )
    if overlap != GIBSON_OVERLAP_LENGTH_BP:
        failure_markers.append("wrong_overlap_length")
        notes.append(
            "Submitted overlap length {:d} bp does not match the supplied {:d} bp homology overlaps.".format(
                overlap,
                GIBSON_OVERLAP_LENGTH_BP,
            )
        )

    status = failure_markers[0] if failure_markers else "assembled"
    if status == "assembled":
        effective_efficiency = base_efficiency
    else:
        effective_efficiency = base_efficiency * 0.08

    effective_efficiency = max(0.0, min(1.0, float(effective_efficiency)))
    expected_transformant_yield = 500.0 if status == "assembled" else 40.0

    gibson_id = state.next_gibson_id()
    output_fragment_id = None
    if status == "assembled":
        output_fragment_id = state.next_fragment_id()
        total_length = sum(state.dna_fragments[f].length_bp for f in fragment_ids)
        output = DnaFragment(
            fragment_id=output_fragment_id,
            name="Gibson assembled construct ({})".format(gibson_id),
            length_bp=int(total_length),
            concentration_ng_ul=15.0,
            is_circular=True,
            end_5_prime="circular",
            end_3_prime="circular",
            recognition_sites=[],
            notes=["Circular Gibson-assembled construct."],
        )
        state.dna_fragments[output_fragment_id] = output

    reaction = GibsonReaction(
        gibson_id=gibson_id,
        fragment_ids=list(fragment_ids),
        master_mix_name=master_mix_name,
        temperature_c=temperature,
        duration_minutes=duration,
        overlap_length_bp=overlap,
        status=status,
        effective_assembly_efficiency=float(effective_efficiency),
        expected_transformant_yield=float(expected_transformant_yield),
        output_fragment_id=output_fragment_id,
        notes=list(notes),
    )
    state.gibson_reactions[gibson_id] = reaction
    payload = {
        "status": status,
        "gibson_id": gibson_id,
        "fragment_ids": list(fragment_ids),
        "fragment_count": len(fragment_ids),
        "master_mix_name": master_mix_name,
        "master_mix_normalized": normalize_gibson_master_mix(master_mix_name),
        "master_mix_canonical": canonical_mix,
        "temperature_c": temperature,
        "duration_minutes": duration,
        "overlap_length_bp": overlap,
        "output_fragment_id": output_fragment_id,
        "effective_assembly_efficiency": float(effective_efficiency),
        "expected_transformant_yield": float(expected_transformant_yield),
        "failure_reasons": failure_markers,
        "notes": list(notes),
    }
    state.log_event("gibson_assembly", payload)
    return payload


def _resolve_gibson_id(state: LabState, gibson_id: str) -> str:
    requested = str(gibson_id).strip()
    if requested in state.gibson_reactions:
        return requested
    suffix_match = re.search(r"(\d+)$", requested)
    if suffix_match:
        canonical = "gibson_{:03d}".format(int(suffix_match.group(1)))
        if canonical in state.gibson_reactions:
            return canonical
    available = sorted(state.gibson_reactions)
    raise ValueError(
        "Unknown gibson_id '{:s}'. Available: {:s}".format(
            requested, ", ".join(available) if available else "none"
        )
    )


def transform_gibson(
    state: LabState,
    gibson_id: str,
    heat_shock_seconds: int = 30,
    recovery_minutes: int = 60,
    outgrowth_media: str = "SOC",
    shaking: bool = True,
    ice_incubation_minutes: int = 30,
) -> Dict[str, object]:
    """Transform a Gibson-assembled construct into competent E. coli."""
    resolved_id = _resolve_gibson_id(state, gibson_id)
    gibson = state.gibson_reactions[resolved_id]
    heat_shock = _require_positive_integer(heat_shock_seconds, "heat_shock_seconds")
    recovery = _require_nonnegative_integer(recovery_minutes, "recovery_minutes")
    ice_incubation = _require_nonnegative_integer(
        ice_incubation_minutes,
        "ice_incubation_minutes",
    )
    outgrowth = str(outgrowth_media).strip()
    if not outgrowth:
        raise ValueError("outgrowth_media must be non-empty.")

    expected_yield = float(gibson.expected_transformant_yield)
    if heat_shock != int(
        state.parameters.get("heat_shock_duration_seconds")["parameters"]["optimal"]
    ):
        expected_yield *= 0.5
    if outgrowth.upper() not in {"SOC", "LB"}:
        expected_yield = 0.0
    elif outgrowth.upper() != "SOC":
        expected_yield *= 0.5
    if not shaking:
        expected_yield *= 0.7

    status = "transformed" if outgrowth.upper() in {"SOC", "LB"} else "invalid_outgrowth_media"

    culture_id = state.next_culture_id()
    notes = list(gibson.notes)
    if status != "transformed":
        notes.append("Outgrowth medium must be SOC or LB for the Gibson-01 transformation.")
    culture = TransformationCulture(
        culture_id=culture_id,
        plasmid_mass_pg=float(expected_yield * 1000.0),
        base_efficiency_cfu_per_ug=state.base_efficiency_cfu_per_ug,
        adjusted_efficiency_cfu_per_ug=state.base_efficiency_cfu_per_ug,
        recovery_minutes=recovery,
        outgrowth_media=outgrowth,
        shaking=bool(shaking),
        heat_shock_seconds=heat_shock,
        ice_incubation_minutes=ice_incubation,
        expected_total_transformants=expected_yield,
        notes=notes,
    )
    state.cultures[culture_id] = culture
    payload = {
        "status": status,
        "culture_id": culture_id,
        "gibson_id": resolved_id,
        "gibson_status": gibson.status,
        "output_fragment_id": gibson.output_fragment_id,
        "effective_assembly_efficiency": float(gibson.effective_assembly_efficiency),
        "expected_transformants": float(expected_yield),
        "heat_shock_seconds": heat_shock,
        "recovery_minutes": recovery,
        "outgrowth_media": outgrowth,
        "notes": notes,
    }
    state.log_event("transform_gibson", payload)
    return payload


def initialize_miniprep_source_culture(state: LabState) -> MiniprepCulture:
    """Seed the task's explicit high-copy, plasmid-bearing overnight culture."""
    existing = state.miniprep_cultures.get(MINIPREP_SOURCE_CULTURE_ID)
    if existing is not None:
        return existing
    culture = MiniprepCulture(
        culture_id=MINIPREP_SOURCE_CULTURE_ID,
        plasmid_name="pUC19-derived high-copy plasmid",
        medium="LB",
        is_overnight=True,
        is_plasmid_bearing=True,
        copy_number_class="high-copy",
        available_volume_ml=MINIPREP_SOURCE_CULTURE_VOLUME_ML,
    )
    state.miniprep_cultures[culture.culture_id] = culture
    return culture


def perform_miniprep(
    state: LabState,
    culture_id: str,
    culture_volume_ml: float,
    lysis_buffer_sequence: str,
    lysis_duration_min: int,
    purification_method: str,
    elution_volume_ul: float,
) -> Dict[str, object]:
    """Simulate one QIAprep-style alkaline-lysis silica-spin miniprep."""
    source_id = str(culture_id or "").strip()
    culture_volume = _require_positive_float(culture_volume_ml, "culture_volume_ml")
    lysis_duration = _require_positive_integer(lysis_duration_min, "lysis_duration_min")
    elution_volume = _require_positive_float(elution_volume_ul, "elution_volume_ul")

    culture = state.miniprep_cultures.get(source_id)
    if culture is None:
        raise ValueError("Unknown miniprep culture_id '{}'.".format(source_id))
    if not culture.is_overnight:
        raise ValueError("culture_id '{}' is not an overnight culture.".format(source_id))
    if not culture.is_plasmid_bearing:
        raise ValueError("culture_id '{}' is not plasmid-bearing.".format(source_id))
    if culture.copy_number_class.strip().casefold() != "high-copy":
        raise ValueError("culture_id '{}' is not a high-copy plasmid culture.".format(source_id))
    culture_volume_in_contract = (
        MINIPREP_CULTURE_VOLUME_MIN_ML
        <= culture_volume
        <= MINIPREP_CULTURE_VOLUME_MAX_ML
    )
    if culture_volume_in_contract and culture.available_volume_ml + 1e-12 < culture_volume:
        raise ValueError(
            "culture_id '{}' has only {:.1f} mL remaining.".format(
                source_id, culture.available_volume_ml
            )
        )

    canonical_buffers = canonicalize_miniprep_buffer_sequence(lysis_buffer_sequence)
    canonical_method = canonicalize_miniprep_purification_method(purification_method)
    failure_reasons: List[str] = []
    notes: List[str] = []

    if not culture_volume_in_contract:
        failure_reasons.append(MINIPREP_FAILURE_CULTURE_VOLUME)
        notes.append(
            "Culture volume {:.1f} mL is outside the 1-5 mL high-copy QIAprep range.".format(
                culture_volume
            )
        )
    if canonical_buffers is None:
        failure_reasons.append(MINIPREP_FAILURE_WRONG_BUFFER)
        notes.append(
            "Lysis buffer sequence '{}' does not match the QIAprep P1/P2/N3 order.".format(
                lysis_buffer_sequence
            )
        )
    if not MINIPREP_LYSIS_DURATION_MIN_MINUTES <= lysis_duration <= MINIPREP_LYSIS_DURATION_MAX_MINUTES:
        failure_reasons.append(MINIPREP_FAILURE_OVERLYSIS)
        notes.append(
            "Lysis duration {} min exceeds the 5 min maximum; irreversible plasmid denaturation is likely.".format(
                lysis_duration
            )
        )
    if canonical_method is None:
        failure_reasons.append(MINIPREP_FAILURE_WRONG_METHOD)
        notes.append(
            "Purification method '{}' is not an accepted QIAprep silica-spin method.".format(
                purification_method
            )
        )
    if not MINIPREP_ELUTION_VOLUME_UL <= elution_volume <= MINIPREP_ELUTION_VOLUME_MAX_UL:
        failure_reasons.append(MINIPREP_FAILURE_ELUTION)
        notes.append(
            "Elution volume {:.0f} uL is outside the supported 50-100 uL QIAprep range.".format(
                elution_volume
            )
        )

    preparation_accepted = not failure_reasons
    status = "prepared" if preparation_accepted else failure_reasons[0]
    if preparation_accepted:
        total_yield_ug = MINIPREP_REFERENCE_YIELD_UG_AT_5_ML * (
            culture_volume / MINIPREP_CULTURE_VOLUME_MAX_ML
        )
        final_concentration_ng_ul = (total_yield_ug * 1000.0) / elution_volume
        a260_a280_ratio = MINIPREP_NOMINAL_A260_A280
    else:
        total_yield_ug = 0.0
        final_concentration_ng_ul = 0.0
        a260_a280_ratio = 0.0

    miniprep_id = state.next_miniprep_id()
    if preparation_accepted:
        culture.available_volume_ml -= culture_volume
        culture.consumed_volume_ml += culture_volume
    sample = MiniprepSample(
        miniprep_id=miniprep_id,
        culture_id=source_id,
        culture_volume_ml=culture_volume,
        lysis_buffer_sequence=lysis_buffer_sequence,
        lysis_duration_min=lysis_duration,
        purification_method=purification_method,
        elution_volume_ul=elution_volume,
        final_concentration_ng_ul=float(final_concentration_ng_ul),
        a260_a280_ratio=float(a260_a280_ratio),
        total_yield_ug=float(total_yield_ug),
        status=status,
        failure_reasons=list(failure_reasons),
        notes=list(notes),
    )
    state.miniprep_samples[miniprep_id] = sample
    payload = {
        "status": status,
        "preparation_accepted": preparation_accepted,
        "failure_reasons": list(failure_reasons),
        "miniprep_id": miniprep_id,
        "culture_id": source_id,
        "culture_volume_ml": culture_volume,
        "source_culture_remaining_volume_ml": round(culture.available_volume_ml, 3),
        "lysis_buffer_sequence": lysis_buffer_sequence,
        "lysis_buffer_sequence_normalized": (
            canonical_buffers or normalize_miniprep_label(lysis_buffer_sequence)
        ),
        "lysis_buffer_sequence_canonical": canonical_buffers,
        "lysis_duration_min": lysis_duration,
        "purification_method": purification_method,
        "purification_method_normalized": (
            canonical_method or normalize_miniprep_label(purification_method)
        ),
        "purification_method_canonical": canonical_method,
        "elution_volume_ul": elution_volume,
        "final_concentration_ng_ul": round(float(final_concentration_ng_ul), 1),
        "a260_a280_ratio": round(float(a260_a280_ratio), 2),
        "total_yield_ug": round(float(total_yield_ug), 1),
        "notes": list(notes),
    }
    state.log_event("perform_miniprep", payload)
    return payload


def initialize_expression_construct(state: LabState) -> ExpressionConstruct:
    """Seed the fixed benign T7lac construct used by Express-01."""
    existing = state.expression_constructs.get(EXPRESSION_CONSTRUCT_ID)
    if existing is not None:
        return existing
    construct = ExpressionConstruct(
        construct_id=EXPRESSION_CONSTRUCT_ID,
        plasmid_name=EXPRESSION_PLASMID_NAME,
        promoter=EXPRESSION_PROMOTER,
        target_protein_name=EXPRESSION_TARGET_PROTEIN_NAME,
        expected_molecular_weight_kda=EXPRESSION_TARGET_PROTEIN_KDA,
        affinity_tag=EXPRESSION_AFFINITY_TAG,
        is_benign=True,
        culture_volume_ml=EXPRESSION_CULTURE_VOLUME_ML,
    )
    state.expression_constructs[construct.construct_id] = construct
    return construct


def run_protein_expression(
    state: LabState,
    construct_id: str,
    host_strain: str,
    iptg_concentration_mm: float,
    induction_od600: float,
    induction_temperature_c: float,
    induction_hours: float,
    lysis_buffer_ph: float,
) -> Dict[str, object]:
    """Run one causal T7lac expression and native-lysate preparation attempt."""
    source_id = str(construct_id or "").strip()
    iptg = _require_finite_float(iptg_concentration_mm, "iptg_concentration_mm")
    induction_od = _require_finite_float(induction_od600, "induction_od600")
    induction_temperature = _require_finite_float(
        induction_temperature_c, "induction_temperature_c"
    )
    induction_duration = _require_finite_float(induction_hours, "induction_hours")
    lysis_ph = _require_finite_float(lysis_buffer_ph, "lysis_buffer_ph")

    construct = state.expression_constructs.get(source_id)
    if construct is None:
        raise ValueError("Unknown expression construct_id '{}'.".format(source_id))
    if not construct.is_benign:
        raise ValueError("construct_id '{}' is not a benign task construct.".format(source_id))
    if construct.promoter != EXPRESSION_PROMOTER:
        raise ValueError("construct_id '{}' is not driven by T7lac.".format(source_id))

    canonical_host = canonicalize_expression_host(host_strain)
    schedule = match_expression_schedule(induction_temperature, induction_duration)
    failure_reasons: List[str] = []
    notes: List[str] = []

    if canonical_host is None:
        failure_reasons.append(EXPRESSION_FAILURE_HOST)
        notes.append(
            "Host strain '{}' is not an allowlisted (DE3) T7 expression host.".format(
                host_strain
            )
        )
    if not EXPRESSION_IPTG_MIN_MM <= iptg <= EXPRESSION_IPTG_MAX_MM:
        failure_reasons.append(EXPRESSION_FAILURE_IPTG)
        notes.append(
            "IPTG concentration {:.2f} mM is outside the supported {:.1f}-{:.1f} mM pET range.".format(
                iptg, EXPRESSION_IPTG_MIN_MM, EXPRESSION_IPTG_MAX_MM
            )
        )
    if not EXPRESSION_OD600_MIN <= induction_od <= EXPRESSION_OD600_MAX:
        failure_reasons.append(EXPRESSION_FAILURE_OD600)
        notes.append(
            "Induction OD600 {:.2f} is outside the supported {:.1f}-{:.1f} mid-log window.".format(
                induction_od, EXPRESSION_OD600_MIN, EXPRESSION_OD600_MAX
            )
        )
    if schedule is None:
        failure_reasons.append(EXPRESSION_FAILURE_SCHEDULE)
        notes.append(
            "Induction at {:.1f} C for {:.1f} h does not match a supported coupled temperature-duration profile.".format(
                induction_temperature, induction_duration
            )
        )
    if not EXPRESSION_LYSIS_PH_MIN <= lysis_ph <= EXPRESSION_LYSIS_PH_MAX:
        failure_reasons.append(EXPRESSION_FAILURE_LYSIS_PH)
        notes.append(
            "Lysis buffer pH {:.2f} is outside the supported {:.1f}-{:.1f} native Ni-NTA window.".format(
                lysis_ph, EXPRESSION_LYSIS_PH_MIN, EXPRESSION_LYSIS_PH_MAX
            )
        )

    expression_accepted = not failure_reasons
    status = EXPRESSION_SUCCESS_STATUS if expression_accepted else failure_reasons[0]
    insoluble_fraction = schedule.insoluble_fraction if expression_accepted and schedule else 0.0
    soluble_yield = (
        EXPRESSION_TOTAL_TARGET_YIELD_MG_PER_L * (1.0 - insoluble_fraction)
        if expression_accepted
        else 0.0
    )
    total_soluble_mg = soluble_yield * construct.culture_volume_ml / 1000.0
    lysate_prepared = expression_accepted

    expression_id = state.next_expression_id()
    construct.usage_count += 1
    record = ProteinExpression(
        expression_id=expression_id,
        construct_id=source_id,
        host_strain=str(host_strain),
        host_strain_canonical=canonical_host,
        protein_name=construct.target_protein_name,
        expected_molecular_weight_kda=construct.expected_molecular_weight_kda,
        iptg_concentration_mm=iptg,
        induction_od600=induction_od,
        induction_temperature_c=induction_temperature,
        induction_hours=induction_duration,
        lysis_buffer_ph=lysis_ph,
        culture_volume_ml=construct.culture_volume_ml,
        status=status,
        expression_accepted=expression_accepted,
        failure_reasons=list(failure_reasons),
        induction_schedule_profile=schedule.name if schedule else None,
        soluble_yield_mg_per_l=soluble_yield,
        insoluble_fraction=insoluble_fraction,
        total_soluble_mg=total_soluble_mg,
        lysate_prepared=lysate_prepared,
        notes=list(notes),
    )
    state.protein_expressions[expression_id] = record
    payload = {
        "status": status,
        "expression_accepted": expression_accepted,
        "failure_reasons": list(failure_reasons),
        "expression_id": expression_id,
        "construct_id": source_id,
        "construct_usage_count": construct.usage_count,
        "plasmid_name": construct.plasmid_name,
        "promoter": construct.promoter,
        "affinity_tag": construct.affinity_tag,
        "is_benign": construct.is_benign,
        "host_strain": str(host_strain),
        "host_strain_normalized": normalize_expression_label(host_strain),
        "host_strain_canonical": canonical_host,
        "protein_name": construct.target_protein_name,
        "expected_molecular_weight_kda": construct.expected_molecular_weight_kda,
        "iptg_concentration_mm": iptg,
        "induction_od600": induction_od,
        "induction_temperature_c": induction_temperature,
        "induction_hours": induction_duration,
        "induction_schedule_profile": schedule.name if schedule else None,
        "lysis_buffer_ph": lysis_ph,
        "culture_volume_ml": construct.culture_volume_ml,
        "soluble_yield_mg_per_l": round(soluble_yield, 2),
        "insoluble_fraction": round(insoluble_fraction, 2),
        "total_soluble_mg": round(total_soluble_mg, 2),
        "lysate_prepared": lysate_prepared,
        "notes": list(notes),
    }
    state.log_event("run_protein_expression", payload)
    return payload


def initialize_purification_lysate(state: LabState) -> PurificationLysate:
    """Seed the fixed clarified native lysate used by Purify-01."""
    if (
        PURIFICATION_INPUT_TARGET_MASS_MG
        > PURIFICATION_COLUMN_BED_VOLUME_ML
        * PURIFICATION_COLUMN_CAPACITY_MIN_MG_PER_ML
    ):
        raise RuntimeError("Purify-01 fixture exceeds the conservative column capacity.")
    existing = state.purification_lysates.get(PURIFICATION_LYSATE_ID)
    if existing is not None:
        return existing
    lysate = PurificationLysate(
        lysate_id=PURIFICATION_LYSATE_ID,
        source_expression_id=PURIFICATION_SOURCE_EXPRESSION_ID,
        construct_id=PURIFICATION_CONSTRUCT_ID,
        target_protein_name=PURIFICATION_TARGET_PROTEIN_NAME,
        expected_band_kda=PURIFICATION_TARGET_PROTEIN_KDA,
        affinity_tag=PURIFICATION_AFFINITY_TAG,
        is_benign=True,
        is_clarified=True,
        is_native=True,
        lysis_buffer_ph=PURIFICATION_LYSATE_PH,
        phosphate_mm=PURIFICATION_LYSATE_PHOSPHATE_MM,
        sodium_chloride_mm=PURIFICATION_LYSATE_NACL_MM,
        is_chelator_free=True,
        total_target_mass_mg=PURIFICATION_INPUT_TARGET_MASS_MG,
        available_target_mass_mg=PURIFICATION_INPUT_TARGET_MASS_MG,
    )
    state.purification_lysates[lysate.lysate_id] = lysate
    return lysate


def run_nta_purification(
    state: LabState,
    lysate_id: str,
    load_imidazole_mm: float,
    wash_imidazole_mm: float,
    elute_imidazole_mm: float,
    flow_rate_ml_per_min: float,
) -> Dict[str, object]:
    """Run one causal native Ni-NTA Superflow purification attempt."""
    source_id = str(lysate_id or "").strip()
    load_imidazole = _require_finite_float(
        load_imidazole_mm, "load_imidazole_mm"
    )
    wash_imidazole = _require_finite_float(
        wash_imidazole_mm, "wash_imidazole_mm"
    )
    elute_imidazole = _require_finite_float(
        elute_imidazole_mm, "elute_imidazole_mm"
    )
    flow_rate = _require_finite_float(
        flow_rate_ml_per_min, "flow_rate_ml_per_min"
    )

    if source_id != PURIFICATION_LYSATE_ID:
        raise ValueError("Unknown purification lysate_id '{}'.".format(source_id))
    lysate = state.purification_lysates.get(source_id)
    if lysate is None:
        raise ValueError("Unknown purification lysate_id '{}'.".format(source_id))
    if lysate.is_benign is not True:
        raise ValueError("lysate_id '{}' is not a benign task input.".format(source_id))
    if (
        lysate.is_clarified is not True
        or lysate.is_native is not True
        or lysate.is_chelator_free is not True
    ):
        raise ValueError(
            "lysate_id '{}' is not a clarified native lysate.".format(source_id)
        )
    if (
        lysate.source_expression_id != PURIFICATION_SOURCE_EXPRESSION_ID
        or lysate.construct_id != PURIFICATION_CONSTRUCT_ID
        or lysate.target_protein_name != PURIFICATION_TARGET_PROTEIN_NAME
        or lysate.affinity_tag != PURIFICATION_AFFINITY_TAG
    ):
        raise ValueError(
            "lysate_id '{}' does not match the required expression fixture.".format(
                source_id
            )
        )

    expected_band_kda = _require_finite_float(
        lysate.expected_band_kda, "lysate expected_band_kda"
    )
    lysis_buffer_ph = _require_finite_float(
        lysate.lysis_buffer_ph, "lysate lysis_buffer_ph"
    )
    phosphate_mm = _require_finite_float(
        lysate.phosphate_mm, "lysate phosphate_mm"
    )
    sodium_chloride_mm = _require_finite_float(
        lysate.sodium_chloride_mm, "lysate sodium_chloride_mm"
    )
    total_target_mass_mg = _require_finite_float(
        lysate.total_target_mass_mg, "lysate total_target_mass_mg"
    )
    available_target_mass_mg = _require_finite_float(
        lysate.available_target_mass_mg, "lysate available_target_mass_mg"
    )
    consumed_target_mass_mg = _require_finite_float(
        lysate.consumed_target_mass_mg, "lysate consumed_target_mass_mg"
    )
    if (
        expected_band_kda != PURIFICATION_TARGET_PROTEIN_KDA
        or lysis_buffer_ph != PURIFICATION_LYSATE_PH
        or phosphate_mm != PURIFICATION_LYSATE_PHOSPHATE_MM
        or sodium_chloride_mm != PURIFICATION_LYSATE_NACL_MM
    ):
        raise ValueError(
            "lysate_id '{}' does not match the native Ni-NTA buffer fixture.".format(
                source_id
            )
        )
    if (
        total_target_mass_mg != PURIFICATION_INPUT_TARGET_MASS_MG
        or available_target_mass_mg != PURIFICATION_INPUT_TARGET_MASS_MG
        or consumed_target_mass_mg != 0.0
        or isinstance(lysate.usage_count, bool)
        or lysate.usage_count != 0
    ):
        raise ValueError("lysate_id '{}' has already been consumed.".format(source_id))

    failure_reasons: List[str] = []
    notes: List[str] = []
    if not (
        PURIFICATION_LOAD_IMIDAZOLE_MIN_MM
        <= load_imidazole
        <= PURIFICATION_LOAD_IMIDAZOLE_MAX_MM
    ):
        failure_reasons.append(PURIFICATION_FAILURE_LOAD)
        notes.append(
            "Load imidazole {:.1f} mM is outside the supported {:.0f}-{:.0f} mM range.".format(
                load_imidazole,
                PURIFICATION_LOAD_IMIDAZOLE_MIN_MM,
                PURIFICATION_LOAD_IMIDAZOLE_MAX_MM,
            )
        )
    if not (
        PURIFICATION_WASH_IMIDAZOLE_MIN_MM
        <= wash_imidazole
        <= PURIFICATION_WASH_IMIDAZOLE_MAX_MM
    ):
        failure_reasons.append(PURIFICATION_FAILURE_WASH)
        notes.append(
            "Wash imidazole {:.1f} mM does not match the supported {:.0f} mM native workflow.".format(
                wash_imidazole, PURIFICATION_WASH_IMIDAZOLE_MIN_MM
            )
        )
    if not (
        PURIFICATION_ELUTION_IMIDAZOLE_MIN_MM
        <= elute_imidazole
        <= PURIFICATION_ELUTION_IMIDAZOLE_MAX_MM
    ):
        failure_reasons.append(PURIFICATION_FAILURE_ELUTION)
        notes.append(
            "Elution imidazole {:.1f} mM does not match the supported {:.0f} mM native workflow.".format(
                elute_imidazole, PURIFICATION_ELUTION_IMIDAZOLE_MIN_MM
            )
        )
    if not (
        PURIFICATION_FLOW_RATE_MIN_ML_PER_MIN
        <= flow_rate
        <= PURIFICATION_FLOW_RATE_MAX_ML_PER_MIN
    ):
        failure_reasons.append(PURIFICATION_FAILURE_FLOW)
        notes.append(
            "Flow rate {:.2f} mL/min is outside the supported {:.1f}-{:.1f} mL/min range.".format(
                flow_rate,
                PURIFICATION_FLOW_RATE_MIN_ML_PER_MIN,
                PURIFICATION_FLOW_RATE_MAX_ML_PER_MIN,
            )
        )

    input_target_mass = available_target_mass_mg
    lysate.available_target_mass_mg = 0.0
    lysate.consumed_target_mass_mg += input_target_mass
    lysate.usage_count += 1

    purification_accepted = not failure_reasons
    status = (
        PURIFICATION_SUCCESS_STATUS if purification_accepted else failure_reasons[0]
    )
    recovery_fraction = (
        PURIFICATION_RECOVERY_FRACTION if purification_accepted else 0.0
    )
    recovered_target_mass = input_target_mass * recovery_fraction
    eluate_volume = (
        PURIFICATION_COLUMN_BED_VOLUME_ML * PURIFICATION_ELUATE_COLUMN_VOLUMES
        if purification_accepted
        else 0.0
    )
    purified_concentration = (
        recovered_target_mass / eluate_volume if eluate_volume > 0.0 else 0.0
    )
    purity_percent = PURIFICATION_PURITY_PERCENT if purification_accepted else 0.0
    sds_page_result = (
        PURIFICATION_SDS_PAGE_RESULT
        if purification_accepted
        else PURIFICATION_FAILURE_SDS_PAGE_RESULT
    )
    eluate_prepared = purification_accepted

    purification_id = state.next_nta_purification_id()
    record = NtaPurification(
        purification_id=purification_id,
        lysate_id=source_id,
        source_expression_id=lysate.source_expression_id,
        construct_id=lysate.construct_id,
        resin_name=PURIFICATION_RESIN_NAME,
        load_imidazole_mm=load_imidazole,
        wash_imidazole_mm=wash_imidazole,
        elute_imidazole_mm=elute_imidazole,
        flow_rate_ml_per_min=flow_rate,
        column_bed_volume_ml=PURIFICATION_COLUMN_BED_VOLUME_ML,
        target_protein_name=lysate.target_protein_name,
        expected_band_kda=lysate.expected_band_kda,
        status=status,
        purification_accepted=purification_accepted,
        failure_reasons=list(failure_reasons),
        input_target_mass_mg=input_target_mass,
        recovery_fraction=recovery_fraction,
        recovered_target_mass_mg=recovered_target_mass,
        eluate_volume_ml=eluate_volume,
        purified_concentration_mg_per_ml=purified_concentration,
        purity_percent=purity_percent,
        sds_page_result=sds_page_result,
        eluate_prepared=eluate_prepared,
        notes=list(notes),
    )
    state.nta_purifications[purification_id] = record
    payload = {
        "status": status,
        "purification_accepted": purification_accepted,
        "failure_reasons": list(failure_reasons),
        "purification_id": purification_id,
        "lysate_id": source_id,
        "source_expression_id": lysate.source_expression_id,
        "construct_id": lysate.construct_id,
        "lysate_usage_count": lysate.usage_count,
        "input_lysate_consumed": True,
        "lysate_remaining_target_mass_mg": round(
            lysate.available_target_mass_mg, 2
        ),
        "resin_name": PURIFICATION_RESIN_NAME,
        "resin_normalized": normalize_purification_label(PURIFICATION_RESIN_NAME),
        "load_imidazole_mm": load_imidazole,
        "wash_imidazole_mm": wash_imidazole,
        "elute_imidazole_mm": elute_imidazole,
        "flow_rate_ml_per_min": flow_rate,
        "column_bed_volume_ml": PURIFICATION_COLUMN_BED_VOLUME_ML,
        "target_protein_name": lysate.target_protein_name,
        "expected_band_kda": lysate.expected_band_kda,
        "affinity_tag": lysate.affinity_tag,
        "is_benign": lysate.is_benign,
        "lysate_is_clarified": lysate.is_clarified,
        "lysate_is_native": lysate.is_native,
        "lysis_buffer_ph": lysate.lysis_buffer_ph,
        "lysis_buffer_phosphate_mm": lysate.phosphate_mm,
        "lysis_buffer_sodium_chloride_mm": lysate.sodium_chloride_mm,
        "lysis_buffer_is_chelator_free": lysate.is_chelator_free,
        "input_target_mass_mg": round(input_target_mass, 2),
        "recovery_fraction": recovery_fraction,
        "recovered_target_mass_mg": round(recovered_target_mass, 2),
        "eluate_volume_column_volumes": (
            PURIFICATION_ELUATE_COLUMN_VOLUMES if purification_accepted else 0.0
        ),
        "eluate_volume_ml": round(eluate_volume, 2),
        "purified_concentration_mg_per_ml": round(purified_concentration, 2),
        "purity_percent": round(purity_percent, 1),
        "sds_page_result": sds_page_result,
        "eluate_prepared": eluate_prepared,
        "notes": list(notes),
    }
    state.log_event("run_nta_purification", payload)
    return payload
