"""State management for LabCraft's stochastic lab environment."""

from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .stochastic import TransformationParameterBundle, load_transformation_parameters

_PARAMETERS_PATH = Path(__file__).resolve().parents[2] / "data" / "parameters" / "transformation.json"
_STATE_REGISTRY: Dict[str, "LabState"] = {}


def stable_seed_from_sample(sample_id: str) -> int:
    """Derive a reproducible seed from the sample identifier."""
    digest = hashlib.sha256(sample_id.encode("utf-8")).hexdigest()
    return int(digest[:16], 16)


@dataclass
class PreparedPlate:
    plate_id: str
    medium: str
    antibiotic: Optional[str]
    antibiotic_concentration_ug_ml: Optional[float]


@dataclass
class TransformationCulture:
    culture_id: str
    plasmid_mass_pg: float
    base_efficiency_cfu_per_ug: float
    adjusted_efficiency_cfu_per_ug: float
    recovery_minutes: int
    outgrowth_media: str
    shaking: bool
    heat_shock_seconds: int
    ice_incubation_minutes: int
    expected_total_transformants: float
    notes: List[str] = field(default_factory=list)


@dataclass
class PlatedSample:
    plating_id: str
    culture_id: str
    plate_id: str
    dilution_factor: float
    volume_ul: float
    expected_colonies: Optional[float]
    observed_colonies: Optional[int]
    status: str
    warnings: List[str] = field(default_factory=list)


@dataclass
class GrowthMeasurement:
    elapsed_minutes: int
    dilution_factor: float
    observed_od600: float
    estimated_undiluted_od600: float


@dataclass
class GrowthCulture:
    growth_id: str
    condition: str
    medium: str
    starting_od600: float
    doubling_time_minutes: float
    current_time_minutes: int = 0
    measurements: List[GrowthMeasurement] = field(default_factory=list)


@dataclass
class PcrReaction:
    reaction_id: str
    polymerase_name: str
    additive: str
    extension_seconds: int
    cycle_count: int
    target_size_bp: int
    status: str
    visible_bands_bp: List[int] = field(default_factory=list)
    smear_present: bool = False
    notes: List[str] = field(default_factory=list)


@dataclass
class GelRun:
    gel_id: str
    reaction_id: str
    ladder_name: str
    agarose_percent: float
    status: str
    visible_bands_bp: List[int] = field(default_factory=list)
    smear_present: bool = False
    notes: List[str] = field(default_factory=list)


@dataclass
class ScreeningColony:
    colony_id: str
    color: str
    is_recombinant: bool
    expected_band_bp: int
    notes: List[str] = field(default_factory=list)


@dataclass
class ScreeningPlate:
    plate_id: str
    historical_positive_rate_among_white: float
    target_confidence: float
    recombinant_band_bp: int
    empty_vector_band_bp: int
    colonies: Dict[str, ScreeningColony] = field(default_factory=dict)
    screened_colony_ids: List[str] = field(default_factory=list)


@dataclass
class DnaFragment:
    fragment_id: str
    name: str
    length_bp: int
    concentration_ng_ul: float
    is_circular: bool
    end_5_prime: str
    end_3_prime: str
    recognition_sites: List[str] = field(default_factory=list)
    parent_fragment_id: Optional[str] = None
    source_digest_id: Optional[str] = None
    notes: List[str] = field(default_factory=list)


@dataclass
class DigestReaction:
    digest_id: str
    substrate_fragment_id: str
    enzyme_names: List[str]
    buffer: str
    temperature_c: float
    duration_minutes: int
    heat_inactivate_after: bool
    status: str
    output_fragment_ids: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)


@dataclass
class LigationReaction:
    ligation_id: str
    vector_fragment_id: str
    insert_fragment_ids: List[str]
    ligase_name: str
    vector_to_insert_molar_ratio: float
    temperature_c: float
    duration_minutes: int
    status: str
    effective_recombinant_fraction: float
    expected_transformant_yield: float
    notes: List[str] = field(default_factory=list)


@dataclass
class AssemblyReaction:
    """Golden Gate / Type IIS one-pot assembly reaction."""

    assembly_id: str
    fragment_ids: List[str]
    enzyme_name: str
    ligase_name: str
    buffer: str
    cycle_count: int
    digest_temperature_c: float
    ligate_temperature_c: float
    final_digest_minutes: int
    final_digest_temperature_c: float
    status: str
    effective_assembly_efficiency: float
    expected_transformant_yield: float
    output_fragment_id: Optional[str] = None
    notes: List[str] = field(default_factory=list)


@dataclass
class GibsonReaction:
    """Gibson isothermal overlap-based assembly reaction."""

    gibson_id: str
    fragment_ids: List[str]
    master_mix_name: str
    temperature_c: float
    duration_minutes: int
    overlap_length_bp: int
    status: str
    effective_assembly_efficiency: float
    expected_transformant_yield: float
    output_fragment_id: Optional[str] = None
    notes: List[str] = field(default_factory=list)


@dataclass
class MiniprepCulture:
    """Seeded high-copy plasmid culture available to Miniprep-01."""

    culture_id: str
    plasmid_name: str
    medium: str
    is_overnight: bool
    is_plasmid_bearing: bool
    copy_number_class: str
    available_volume_ml: float
    consumed_volume_ml: float = 0.0


@dataclass
class MiniprepSample:
    """Plasmid miniprep result (QIAprep alkaline lysis + silica-spin workflow)."""

    miniprep_id: str
    culture_id: str
    culture_volume_ml: float
    lysis_buffer_sequence: str
    lysis_duration_min: int
    purification_method: str
    elution_volume_ul: float
    final_concentration_ng_ul: float
    a260_a280_ratio: float
    total_yield_ug: float
    status: str
    failure_reasons: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)


@dataclass
class ExpressionConstruct:
    """Seeded benign expression construct available to an Express-01 sample."""

    construct_id: str
    plasmid_name: str
    promoter: str
    target_protein_name: str
    expected_molecular_weight_kda: float
    affinity_tag: str
    is_benign: bool
    culture_volume_ml: float
    usage_count: int = 0


@dataclass
class ProteinExpression:
    """Causal recombinant-protein expression and lysate-preparation run."""

    expression_id: str
    construct_id: str
    host_strain: str
    host_strain_canonical: Optional[str]
    protein_name: str
    expected_molecular_weight_kda: float
    iptg_concentration_mm: float
    induction_od600: float
    induction_temperature_c: float
    induction_hours: float
    lysis_buffer_ph: float
    culture_volume_ml: float
    status: str
    expression_accepted: bool
    failure_reasons: List[str]
    induction_schedule_profile: Optional[str]
    soluble_yield_mg_per_l: float
    insoluble_fraction: float
    total_soluble_mg: float
    lysate_prepared: bool
    notes: List[str] = field(default_factory=list)


@dataclass
class NtaPurification:
    """Ni-NTA affinity purification of a His-tagged benign protein."""

    purification_id: str
    resin_name: str
    load_imidazole_mm: float
    wash_imidazole_mm: float
    elute_imidazole_mm: float
    flow_rate_ml_per_min: float
    column_bed_volume_ml: float
    target_protein_name: str
    expected_band_kda: float
    status: str
    purified_concentration_mg_per_ml: float
    purity_percent: float
    sds_page_result: str
    notes: List[str] = field(default_factory=list)


@dataclass
class LabState:
    sample_id: str
    seed: int
    rng: random.Random
    parameters: TransformationParameterBundle
    base_efficiency_cfu_per_ug: float
    prepared_plates: Dict[str, PreparedPlate] = field(default_factory=dict)
    cultures: Dict[str, TransformationCulture] = field(default_factory=dict)
    plated_samples: Dict[str, PlatedSample] = field(default_factory=dict)
    growth_cultures: Dict[str, GrowthCulture] = field(default_factory=dict)
    pcr_reactions: Dict[str, PcrReaction] = field(default_factory=dict)
    gel_runs: Dict[str, GelRun] = field(default_factory=dict)
    screening_plates: Dict[str, ScreeningPlate] = field(default_factory=dict)
    dna_fragments: Dict[str, DnaFragment] = field(default_factory=dict)
    digest_reactions: Dict[str, DigestReaction] = field(default_factory=dict)
    ligation_reactions: Dict[str, LigationReaction] = field(default_factory=dict)
    assembly_reactions: Dict[str, AssemblyReaction] = field(default_factory=dict)
    gibson_reactions: Dict[str, GibsonReaction] = field(default_factory=dict)
    miniprep_cultures: Dict[str, MiniprepCulture] = field(default_factory=dict)
    miniprep_samples: Dict[str, MiniprepSample] = field(default_factory=dict)
    expression_constructs: Dict[str, ExpressionConstruct] = field(default_factory=dict)
    protein_expressions: Dict[str, ProteinExpression] = field(default_factory=dict)
    nta_purifications: Dict[str, NtaPurification] = field(default_factory=dict)
    event_log: List[Dict[str, Any]] = field(default_factory=list)
    plate_counter: int = 0
    culture_counter: int = 0
    plating_counter: int = 0
    growth_counter: int = 0
    pcr_counter: int = 0
    gel_counter: int = 0
    screening_plate_counter: int = 0
    fragment_counter: int = 0
    digest_counter: int = 0
    ligation_counter: int = 0
    assembly_counter: int = 0
    gibson_counter: int = 0
    miniprep_counter: int = 0
    expression_counter: int = 0
    nta_purification_counter: int = 0
    cloning_substrates_initialized: bool = False
    golden_gate_substrates_initialized: bool = False
    gibson_substrates_initialized: bool = False

    def next_plate_id(self) -> str:
        self.plate_counter += 1
        return "plate_{:03d}".format(self.plate_counter)

    def next_culture_id(self) -> str:
        self.culture_counter += 1
        return "culture_{:03d}".format(self.culture_counter)

    def next_plating_id(self) -> str:
        self.plating_counter += 1
        return "plating_{:03d}".format(self.plating_counter)

    def next_growth_id(self) -> str:
        self.growth_counter += 1
        return "growth_{:03d}".format(self.growth_counter)

    def next_pcr_id(self) -> str:
        self.pcr_counter += 1
        return "pcr_{:03d}".format(self.pcr_counter)

    def next_gel_id(self) -> str:
        self.gel_counter += 1
        return "gel_{:03d}".format(self.gel_counter)

    def next_screening_plate_id(self) -> str:
        self.screening_plate_counter += 1
        return "screen_plate_{:03d}".format(self.screening_plate_counter)

    def next_fragment_id(self) -> str:
        self.fragment_counter += 1
        return "fragment_{:03d}".format(self.fragment_counter)

    def next_digest_id(self) -> str:
        self.digest_counter += 1
        return "digest_{:03d}".format(self.digest_counter)

    def next_ligation_id(self) -> str:
        self.ligation_counter += 1
        return "ligation_{:03d}".format(self.ligation_counter)

    def next_assembly_id(self) -> str:
        self.assembly_counter += 1
        return "assembly_{:03d}".format(self.assembly_counter)

    def next_gibson_id(self) -> str:
        self.gibson_counter += 1
        return "gibson_{:03d}".format(self.gibson_counter)

    def next_miniprep_id(self) -> str:
        self.miniprep_counter += 1
        return "miniprep_{:03d}".format(self.miniprep_counter)

    def next_expression_id(self) -> str:
        self.expression_counter += 1
        return "expression_{:03d}".format(self.expression_counter)

    def next_nta_purification_id(self) -> str:
        self.nta_purification_counter += 1
        return "purification_{:03d}".format(self.nta_purification_counter)

    def log_event(self, kind: str, payload: Dict[str, Any]) -> None:
        self.event_log.append({"kind": kind, "payload": payload})


def create_lab_state(
    sample_id: str,
    seed: Optional[int] = None,
    parameter_path: Optional[Path] = None,
) -> LabState:
    """Create a fresh sample-scoped lab state."""
    effective_seed = stable_seed_from_sample(sample_id) if seed is None else seed
    rng = random.Random(effective_seed)
    bundle = load_transformation_parameters(parameter_path or _PARAMETERS_PATH)
    base_efficiency = bundle.sample_base_efficiency(rng)
    return LabState(
        sample_id=sample_id,
        seed=effective_seed,
        rng=rng,
        parameters=bundle,
        base_efficiency_cfu_per_ug=base_efficiency,
    )


def get_or_create_lab_state(
    sample_id: str,
    seed: Optional[int] = None,
    parameter_path: Optional[Path] = None,
) -> LabState:
    """Fetch a sample state from the fallback registry or create it."""
    state = _STATE_REGISTRY.get(sample_id)
    if state is None:
        state = create_lab_state(sample_id=sample_id, seed=seed, parameter_path=parameter_path)
        _STATE_REGISTRY[sample_id] = state
    return state


def reset_lab_state(sample_id: str) -> None:
    """Drop any cached state for a sample id."""
    _STATE_REGISTRY.pop(sample_id, None)
