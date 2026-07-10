"""Discovery-track tool wrappers and deterministic assay logic."""

from __future__ import annotations

import contextvars
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List

_DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "discovery_track"
_TARGETS_PATH = _DATA_DIR / "targets.json"
_ASSAYS_PATH = _DATA_DIR / "assays.json"

_ACTIVE_DISCOVERY_SAMPLE_ID = contextvars.ContextVar(
    "discovery_active_sample_id",
    default="perturb_followup_01_seed_00",
)


def set_active_discovery_sample(sample_id: str) -> None:
    _ACTIVE_DISCOVERY_SAMPLE_ID.set(sample_id)


def cleanup_discovery_sample(sample_id: str | None = None) -> None:
    del sample_id
    _ACTIVE_DISCOVERY_SAMPLE_ID.set("perturb_followup_01_seed_00")


def _active_sample_id() -> str:
    return _ACTIVE_DISCOVERY_SAMPLE_ID.get()


def _load_json(path: Path) -> List[Dict[str, Any]]:
    with open(path) as handle:
        payload = json.load(handle)
    if isinstance(payload, list):
        return payload
    raise TypeError("Expected list payload in {}".format(path))


def load_target_catalog() -> Dict[str, Dict[str, Any]]:
    return {entry["target_id"]: entry for entry in _load_json(_TARGETS_PATH)}


def load_assay_catalog() -> Dict[str, Dict[str, Any]]:
    return {entry["assay_id"]: entry for entry in _load_json(_ASSAYS_PATH)}


def _target_profile_view(entry: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "target_id": entry["target_id"],
        "perturbation_score": entry["perturbation_score"],
        "viability_risk": entry["viability_risk"],
        "context_consistency": entry["context_consistency"],
        "genetic_support": entry["genetic_support"],
        "patient_signal": entry["patient_signal"],
        "literature_support": entry["literature_support"],
    }


def _candidate_summary_view(entry: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "target_id": entry["target_id"],
        "perturbation_score": entry["perturbation_score"],
        "viability_risk": entry["viability_risk"],
        "context_consistency": entry["context_consistency"],
    }


def _assay_view(entry: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "assay_id": entry["assay_id"],
        "name": entry["name"],
        "primary_readout": entry["primary_readout"],
        "description": entry["description"],
    }


def assay_primary_readout(assay_id: str) -> str | None:
    assay = load_assay_catalog().get(assay_id)
    if assay is None:
        return None
    return assay["primary_readout"]


def validation_result_label(result: Dict[str, Any]) -> str:
    if result.get("status") != "completed":
        return "fail"
    if result.get("qc_status") != "pass":
        return "fail"
    if result.get("interpretation_code") in {"validated_signal", "moderate_support"}:
        return "pass"
    return "fail"


def _effect_jitter(sample_id: str, target_id: str, assay_id: str) -> float:
    digest = hashlib.sha256(
        "{:s}|{:s}|{:s}".format(sample_id, target_id, assay_id).encode("utf-8")
    ).hexdigest()
    raw = int(digest[:8], 16) / float(0xFFFFFFFF)
    return round((raw - 0.5) * 0.08, 3)


def simulate_validation_assay(sample_id: str, target_id: str, assay_id: str) -> Dict[str, Any]:
    targets = load_target_catalog()
    assays = load_assay_catalog()
    if target_id not in targets:
        return {
            "status": "not_found",
            "target_id": target_id,
            "assay_id": assay_id,
            "effect_direction": "unknown",
            "effect_size": 0.0,
            "qc_status": "fail",
            "interpretation_code": "unknown_target",
        }
    if assay_id not in assays:
        return {
            "status": "not_found",
            "target_id": target_id,
            "assay_id": assay_id,
            "effect_direction": "unknown",
            "effect_size": 0.0,
            "qc_status": "fail",
            "interpretation_code": "unknown_assay",
        }

    matrix = targets[target_id]["validation_matrix"][assay_id]
    effect_size = round(float(matrix["base_effect_size"]) + _effect_jitter(sample_id, target_id, assay_id), 3)
    return {
        "status": "completed",
        "target_id": target_id,
        "assay_id": assay_id,
        "effect_direction": matrix["effect_direction"],
        "effect_size": effect_size,
        "qc_status": matrix["qc_status"],
        "interpretation_code": matrix["interpretation_code"],
    }


async def list_candidate_targets_call() -> str:
    targets = load_target_catalog()
    payload = {
        "targets": [_candidate_summary_view(targets[target_id]) for target_id in sorted(targets)]
    }
    return json.dumps(payload, sort_keys=True)


async def lookup_target_profile_call(target_id: str) -> str:
    profile = load_target_catalog().get(target_id)
    if profile is None:
        return json.dumps(
            {
                "status": "not_found",
                "target_id": target_id,
                "available_targets": sorted(load_target_catalog()),
            },
            sort_keys=True,
        )
    return json.dumps(_target_profile_view(profile), sort_keys=True)


async def list_validation_assays_call() -> str:
    assays = load_assay_catalog()
    payload = {
        "assays": [_assay_view(assays[assay_id]) for assay_id in sorted(assays)]
    }
    return json.dumps(payload, sort_keys=True)


async def run_validation_assay_call(target_id: str, assay_id: str) -> str:
    result = simulate_validation_assay(_active_sample_id(), target_id=target_id, assay_id=assay_id)
    return json.dumps(result, sort_keys=True)


def list_candidate_targets_tool():
    from inspect_ai.tool import tool

    @tool
    def list_candidate_targets():
        """List the synthetic target candidates for the current discovery task."""

        async def execute() -> str:
            """Return the current target shortlist."""
            return await list_candidate_targets_call()

        return execute

    return list_candidate_targets()


def lookup_target_profile_tool():
    from inspect_ai.tool import tool

    @tool
    def lookup_target_profile():
        """Inspect the full profile for one candidate target."""

        async def execute(target_id: str) -> str:
            """Look up one candidate target profile.

            Args:
                target_id: Target identifier returned by list_candidate_targets.
            """
            return await lookup_target_profile_call(target_id)

        return execute

    return lookup_target_profile()


def list_validation_assays_tool():
    from inspect_ai.tool import tool

    @tool
    def list_validation_assays():
        """List orthogonal validation assays available for the current task."""

        async def execute() -> str:
            """Return the validation assay menu."""
            return await list_validation_assays_call()

        return execute

    return list_validation_assays()


def run_validation_assay_tool():
    from inspect_ai.tool import tool

    @tool
    def run_validation_assay():
        """Run one deterministic validation assay for one target."""

        async def execute(target_id: str, assay_id: str) -> str:
            """Execute one validation assay.

            Args:
                target_id: Target identifier returned by list_candidate_targets.
                assay_id: Assay identifier returned by list_validation_assays.
            """
            return await run_validation_assay_call(target_id=target_id, assay_id=assay_id)

        return execute

    return run_validation_assay()
