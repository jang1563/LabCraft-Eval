"""Shared deterministic contract for the Miniprep-01 benchmark task."""

from __future__ import annotations

import re
from typing import Final

MINIPREP_SOURCE_CULTURE_ID: Final[str] = "miniprep_culture_high_copy_001"
MINIPREP_SOURCE_CULTURE_VOLUME_ML: Final[float] = 5.0
MINIPREP_CULTURE_VOLUME_MIN_ML: Final[float] = 1.0
MINIPREP_CULTURE_VOLUME_MAX_ML: Final[float] = 5.0
MINIPREP_LYSIS_DURATION_MIN_MINUTES: Final[int] = 1
MINIPREP_LYSIS_DURATION_MAX_MINUTES: Final[int] = 5
MINIPREP_ELUTION_VOLUME_UL: Final[float] = 50.0
MINIPREP_ELUTION_VOLUME_MAX_UL: Final[float] = 100.0
MINIPREP_NOMINAL_A260_A280: Final[float] = 1.8
MINIPREP_REFERENCE_YIELD_UG_AT_5_ML: Final[float] = 10.0

MINIPREP_BUFFER_SEQUENCE_CANONICAL: Final[str] = "P1,P2,N3"
MINIPREP_PURIFICATION_METHOD_CANONICAL: Final[str] = "QIAprep silica spin column"

MINIPREP_FAILURE_CULTURE_VOLUME: Final[str] = "culture_volume_out_of_range"
MINIPREP_FAILURE_WRONG_BUFFER: Final[str] = "wrong_buffer_sequence"
MINIPREP_FAILURE_OVERLYSIS: Final[str] = (
    "overlysis_irreversible_plasmid_denaturation"
)
MINIPREP_FAILURE_WRONG_METHOD: Final[str] = "wrong_purification_method"
MINIPREP_FAILURE_ELUTION: Final[str] = "elution_volume_out_of_range"


def normalize_miniprep_label(value: object) -> str:
    """Normalize superficial case, spacing, punctuation, and trademark marks."""
    return re.sub(r"[^a-z0-9]+", "", str(value or "").casefold())


_BUFFER_SEQUENCE_ALIASES: Final[dict[str, str]] = {
    normalize_miniprep_label(alias): MINIPREP_BUFFER_SEQUENCE_CANONICAL
    for alias in (
        "P1,P2,N3",
        "P1 -> P2 -> N3",
        "P1/P2/N3",
        "P1 P2 N3",
        "Buffer P1, Buffer P2, Buffer N3",
        "resuspension, lysis, neutralization",
        "resuspension buffer, lysis buffer, neutralization buffer",
        "P1 resuspension, P2 alkaline lysis, N3 neutralization",
        "P1 (resuspension), P2 (alkaline lysis), N3 (neutralization)",
    )
}


_PURIFICATION_METHOD_ALIASES: Final[dict[str, str]] = {
    normalize_miniprep_label(alias): MINIPREP_PURIFICATION_METHOD_CANONICAL
    for alias in (
        "QIAprep spin column",
        "QIAprep 2.0 spin column",
        "QIAprep 2.0 Spin Columns",
        "QIAprep silica spin column",
        "QIAprep silica-membrane spin column",
        "QIAprep 2.0 silica membrane spin column",
        "QIAprep 2.0 silica-membrane spin column",
        "QIAprep-compatible silica-membrane spin column",
    )
}


def canonicalize_miniprep_buffer_sequence(value: object) -> str | None:
    """Return the QIAprep buffer sequence for an explicit allowlisted label."""
    return _BUFFER_SEQUENCE_ALIASES.get(normalize_miniprep_label(value))


def canonicalize_miniprep_purification_method(value: object) -> str | None:
    """Return the silica-spin method for an explicit allowlisted label."""
    return _PURIFICATION_METHOD_ALIASES.get(normalize_miniprep_label(value))
