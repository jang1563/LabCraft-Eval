"""Shared deterministic contract for the Purify-01 benchmark task."""

from __future__ import annotations

import re
from typing import Final

from .expression_contract import (
    EXPRESSION_AFFINITY_TAG,
    EXPRESSION_CONSTRUCT_ID,
    EXPRESSION_TARGET_PROTEIN_KDA,
    EXPRESSION_TARGET_PROTEIN_NAME,
)

PURIFICATION_LYSATE_ID: Final[str] = "purification_lysate_his6_mbp_gfp_001"
PURIFICATION_SOURCE_EXPRESSION_ID: Final[str] = "expression_seeded_for_purify_001"
PURIFICATION_CONSTRUCT_ID: Final[str] = EXPRESSION_CONSTRUCT_ID
PURIFICATION_TARGET_PROTEIN_NAME: Final[str] = EXPRESSION_TARGET_PROTEIN_NAME
PURIFICATION_TARGET_PROTEIN_KDA: Final[float] = EXPRESSION_TARGET_PROTEIN_KDA
PURIFICATION_AFFINITY_TAG: Final[str] = EXPRESSION_AFFINITY_TAG
PURIFICATION_LYSATE_PH: Final[float] = 8.0
PURIFICATION_LYSATE_PHOSPHATE_MM: Final[float] = 50.0
PURIFICATION_LYSATE_NACL_MM: Final[float] = 300.0
PURIFICATION_INPUT_TARGET_MASS_MG: Final[float] = 18.4

PURIFICATION_RESIN_NAME: Final[str] = "Ni-NTA Superflow"
PURIFICATION_COLUMN_BED_VOLUME_ML: Final[float] = 4.0
PURIFICATION_COLUMN_CAPACITY_MIN_MG_PER_ML: Final[float] = 5.0

PURIFICATION_LOAD_IMIDAZOLE_MIN_MM: Final[float] = 10.0
PURIFICATION_LOAD_IMIDAZOLE_MAX_MM: Final[float] = 20.0
PURIFICATION_WASH_IMIDAZOLE_MIN_MM: Final[float] = 20.0
PURIFICATION_WASH_IMIDAZOLE_MAX_MM: Final[float] = 20.0
PURIFICATION_ELUTION_IMIDAZOLE_MIN_MM: Final[float] = 250.0
PURIFICATION_ELUTION_IMIDAZOLE_MAX_MM: Final[float] = 250.0
PURIFICATION_FLOW_RATE_MIN_ML_PER_MIN: Final[float] = 0.5
PURIFICATION_FLOW_RATE_MAX_ML_PER_MIN: Final[float] = 1.0

# These values are explicit synthetic simulator calibrations. They are not
# empirical performance claims for the seeded fixture or universal Ni-NTA
# outcomes. An out-of-contract attempt consumes the seeded input but produces
# no prepared eluate in this benchmark; that state transition is not a claim
# that a corresponding physical experiment must have zero recovery.
PURIFICATION_RECOVERY_FRACTION: Final[float] = 0.85
PURIFICATION_ELUATE_COLUMN_VOLUMES: Final[float] = 2.5
PURIFICATION_PURITY_PERCENT: Final[float] = 95.0
PURIFICATION_SDS_PAGE_RESULT: Final[str] = "predominant_target_band_at_72_kDa"
PURIFICATION_FAILURE_SDS_PAGE_RESULT: Final[str] = "purification_not_completed"

PURIFICATION_SUCCESS_STATUS: Final[str] = "purified_eluate_prepared"
PURIFICATION_FAILURE_LOAD: Final[str] = "load_imidazole_out_of_range"
PURIFICATION_FAILURE_WASH: Final[str] = "wash_imidazole_out_of_range"
PURIFICATION_FAILURE_ELUTION: Final[str] = "elution_imidazole_out_of_range"
PURIFICATION_FAILURE_FLOW: Final[str] = "flow_rate_out_of_range"


def normalize_purification_label(value: object) -> str:
    """Normalize superficial spacing, punctuation, and trademark marks."""
    return re.sub(r"[^a-z0-9]+", "", str(value or "").casefold())


_RESIN_ALIASES: Final[set[str]] = {
    normalize_purification_label(alias)
    for alias in (
        PURIFICATION_RESIN_NAME,
        "Ni NTA Superflow",
        "QIAGEN Ni-NTA Superflow",
        "QIAGEN Ni NTA Superflow resin",
    )
}


def canonicalize_purification_resin(value: object) -> str | None:
    """Return the fixed benchmark resin without substring matching."""
    if normalize_purification_label(value) in _RESIN_ALIASES:
        return PURIFICATION_RESIN_NAME
    return None
