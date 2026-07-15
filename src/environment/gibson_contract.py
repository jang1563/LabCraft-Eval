"""Shared deterministic contract for the Gibson-01 benchmark task."""

from __future__ import annotations

import re
from typing import Final

GIBSON_FRAGMENT_IDS: Final[frozenset[str]] = frozenset(
    {"gibson_backbone_linear", "gibson_insert_pcr"}
)
GIBSON_TEMPERATURE_C: Final[float] = 50.0
GIBSON_MIN_DURATION_MINUTES: Final[int] = 15
GIBSON_MAX_DURATION_MINUTES: Final[int] = 60
GIBSON_OVERLAP_LENGTH_BP: Final[int] = 20
GIBSON_AMPICILLIN_CONCENTRATION_UG_ML: Final[float] = 100.0
GIBSON_COUNTABLE_MIN: Final[int] = 25
GIBSON_COUNTABLE_MAX: Final[int] = 250

GIBSON_METHOD_CANONICAL: Final[str] = "Gibson"
GIBSON_MASTER_MIX_CANONICAL: Final[str] = "Gibson Assembly Master Mix"
NEBUILDER_HIFI_CANONICAL: Final[str] = "NEBuilder HiFi DNA Assembly Master Mix"
GIBSON_COMPONENT_MIX_CANONICAL: Final[str] = (
    "ISO buffer + T5 exonuclease + Phusion polymerase + Taq DNA ligase"
)


def normalize_gibson_master_mix(value: object) -> str:
    """Normalize only superficial spelling, spacing, and trademark differences."""
    return re.sub(r"[^a-z0-9]+", "", str(value or "").casefold())


_METHOD_ALIASES: Final[dict[str, str]] = {
    normalize_gibson_master_mix(alias): GIBSON_METHOD_CANONICAL
    for alias in (
        "Gibson",
        "Gibson Assembly",
        "Gibson isothermal assembly",
        "Gibson overlap assembly",
        "Gibson isothermal overlap assembly",
        "Isothermal Gibson assembly",
        "Isothermal Gibson overlap assembly",
    )
}


_MASTER_MIX_ALIASES: Final[dict[str, str]] = {
    normalize_gibson_master_mix(alias): canonical
    for canonical, aliases in {
        GIBSON_MASTER_MIX_CANONICAL: (
            "Gibson Assembly Master Mix",
            "Gibson Assembly Master Mix (2X)",
        ),
        NEBUILDER_HIFI_CANONICAL: (
            "NEBuilder HiFi",
            "NEBuilder HiFi DNA Assembly",
            "NEBuilder HiFi DNA Assembly Master Mix",
            "NEBuilder HiFi DNA Assembly Master Mix (2X)",
            "NEBuilder HiFi Assembly Master Mix",
        ),
        GIBSON_COMPONENT_MIX_CANONICAL: (
            "ISO buffer + T5 exo + Phusion + Taq ligase",
            "ISO buffer + T5 exo + Phusion DNA polymerase + Taq ligase",
            "ISO buffer + T5 exonuclease + Phusion polymerase + Taq DNA ligase",
            "ISO buffer + T5 exonuclease + Phusion DNA polymerase + Taq DNA ligase",
        ),
    }.items()
    for alias in aliases
}


def canonicalize_gibson_method(value: object) -> str | None:
    """Return the Gibson method for an explicit allowlisted report label."""
    return _METHOD_ALIASES.get(normalize_gibson_master_mix(value))


def canonicalize_gibson_master_mix(value: object) -> str | None:
    """Return a supported canonical mix name; reject partial or fuzzy matches."""
    return _MASTER_MIX_ALIASES.get(normalize_gibson_master_mix(value))


def gibson_master_mix_is_supported(value: object) -> bool:
    return canonicalize_gibson_master_mix(value) is not None
