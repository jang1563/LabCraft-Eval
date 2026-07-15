"""Shared deterministic contract for the Express-01 benchmark task."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final

EXPRESSION_CONSTRUCT_ID: Final[str] = "expression_construct_his6_mbp_gfp_001"
EXPRESSION_PLASMID_NAME: Final[str] = "pET-T7lac-His6-MBP-GFP benchmark construct"
EXPRESSION_PROMOTER: Final[str] = "T7lac"
EXPRESSION_TARGET_PROTEIN_NAME: Final[str] = "His6-MBP-GFP fusion"
EXPRESSION_TARGET_PROTEIN_KDA: Final[float] = 72.0
EXPRESSION_AFFINITY_TAG: Final[str] = "His6"
EXPRESSION_CULTURE_VOLUME_ML: Final[float] = 500.0

EXPRESSION_IPTG_MIN_MM: Final[float] = 0.5
EXPRESSION_IPTG_MAX_MM: Final[float] = 1.0
EXPRESSION_OD600_MIN: Final[float] = 0.5
EXPRESSION_OD600_MAX: Final[float] = 0.8
EXPRESSION_LYSIS_PH_MIN: Final[float] = 7.5
EXPRESSION_LYSIS_PH_MAX: Final[float] = 8.0

# The yield and schedule-specific insoluble fractions below are explicit synthetic
# simulator calibrations. They are not empirical performance claims for the seeded
# fixture or universal values for His6-MBP-GFP constructs. Likewise, an attempted
# condition outside the supported contract deterministically produces no lysate in
# this benchmark; that result must not be interpreted as a biological zero-yield
# claim for a corresponding physical experiment.
EXPRESSION_TOTAL_TARGET_YIELD_MG_PER_L: Final[float] = 40.0

EXPRESSION_SUCCESS_STATUS: Final[str] = "lysate_prepared"
EXPRESSION_FAILURE_HOST: Final[str] = "wrong_host_strain"
EXPRESSION_FAILURE_IPTG: Final[str] = "iptg_concentration_out_of_range"
EXPRESSION_FAILURE_OD600: Final[str] = "induction_od600_out_of_range"
EXPRESSION_FAILURE_SCHEDULE: Final[str] = "unsupported_induction_schedule"
EXPRESSION_FAILURE_LYSIS_PH: Final[str] = "lysis_buffer_ph_out_of_range"


@dataclass(frozen=True)
class ExpressionScheduleProfile:
    """A coupled induction temperature-duration window."""

    name: str
    temperature_min_c: float
    temperature_max_c: float
    duration_min_h: float
    duration_max_h: float
    insoluble_fraction: float

    def matches(self, temperature_c: float, duration_h: float) -> bool:
        return (
            self.temperature_min_c <= temperature_c <= self.temperature_max_c
            and self.duration_min_h <= duration_h <= self.duration_max_h
        )


EXPRESSION_SCHEDULE_PROFILES: Final[tuple[ExpressionScheduleProfile, ...]] = (
    ExpressionScheduleProfile(
        name="low_temperature_extended",
        temperature_min_c=15.0,
        temperature_max_c=25.0,
        duration_min_h=12.0,
        duration_max_h=20.0,
        insoluble_fraction=0.08,
    ),
    ExpressionScheduleProfile(
        name="room_temperature_intermediate",
        temperature_min_c=20.0,
        temperature_max_c=25.0,
        duration_min_h=6.0,
        duration_max_h=8.0,
        insoluble_fraction=0.12,
    ),
    ExpressionScheduleProfile(
        name="30c_moderate",
        temperature_min_c=29.0,
        temperature_max_c=31.0,
        duration_min_h=4.0,
        duration_max_h=6.0,
        insoluble_fraction=0.18,
    ),
    ExpressionScheduleProfile(
        name="37c_standard",
        temperature_min_c=36.0,
        temperature_max_c=38.0,
        duration_min_h=4.0,
        duration_max_h=6.0,
        insoluble_fraction=0.25,
    ),
)
EXPRESSION_SCHEDULE_PROFILE_NAMES: Final[tuple[str, ...]] = tuple(
    profile.name for profile in EXPRESSION_SCHEDULE_PROFILES
)


def normalize_expression_label(value: object) -> str:
    """Normalize superficial spacing, punctuation, and trademark marks."""
    return re.sub(r"[^a-z0-9]+", "", str(value or "").casefold())


_HOST_ALIASES: Final[dict[str, str]] = {
    normalize_expression_label(alias): canonical
    for canonical, aliases in {
        "BL21(DE3)": (
            "BL21(DE3)",
            "BL21 (DE3)",
            "E. coli BL21(DE3)",
            "E coli BL21 (DE3)",
        ),
        "BL21 Star(DE3)": (
            "BL21 Star(DE3)",
            "BL21 Star (DE3)",
            "BL21 Star™(DE3)",
            "E. coli BL21 Star(DE3)",
        ),
        "BL21(DE3) pLysS": (
            "BL21(DE3) pLysS",
            "BL21(DE3)pLysS",
            "BL21 (DE3) pLysS",
        ),
        "BL21 Star(DE3) pLysS": (
            "BL21 Star(DE3) pLysS",
            "BL21 Star(DE3)pLysS",
            "BL21 Star (DE3) pLysS",
            "BL21 Star™(DE3)pLysS",
        ),
        "Rosetta(DE3)": (
            "Rosetta(DE3)",
            "Rosetta (DE3)",
            "E. coli Rosetta(DE3)",
        ),
        "C41(DE3)": ("C41(DE3)", "C41 (DE3)", "E. coli C41(DE3)"),
        "C43(DE3)": ("C43(DE3)", "C43 (DE3)", "E. coli C43(DE3)"),
    }.items()
    for alias in aliases
}


def canonicalize_expression_host(value: object) -> str | None:
    """Return an allowlisted T7 expression host without substring matching."""
    return _HOST_ALIASES.get(normalize_expression_label(value))


def match_expression_schedule(
    temperature_c: float, duration_h: float
) -> ExpressionScheduleProfile | None:
    """Return the first supported coupled temperature-duration profile."""
    for profile in EXPRESSION_SCHEDULE_PROFILES:
        if profile.matches(temperature_c, duration_h):
            return profile
    return None
