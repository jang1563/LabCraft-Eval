"""Tests for discovery-decision tools."""

from __future__ import annotations

import asyncio
import json

from src.tools.discovery import (
    assay_primary_readout,
    list_candidate_targets_call,
    list_validation_assays_call,
    load_assay_catalog,
    load_target_catalog,
    lookup_target_profile_call,
    simulate_validation_assay,
    validation_result_label,
)


def test_list_candidate_targets_returns_all_targets():
    payload = json.loads(asyncio.run(list_candidate_targets_call()))

    assert sorted(target["target_id"] for target in payload["targets"]) == [
        "TGT_A",
        "TGT_B",
        "TGT_C",
        "TGT_D",
    ]


def test_lookup_target_profile_returns_expected_public_fields():
    payload = json.loads(asyncio.run(lookup_target_profile_call("TGT_A")))

    assert set(payload) == {
        "target_id",
        "perturbation_score",
        "viability_risk",
        "context_consistency",
        "genetic_support",
        "patient_signal",
        "literature_support",
    }
    assert payload["target_id"] == "TGT_A"


def test_discovery_views_expose_evidence_without_recommendation_labels():
    candidates = json.loads(asyncio.run(list_candidate_targets_call()))["targets"]
    profile = json.loads(asyncio.run(lookup_target_profile_call("TGT_C")))
    assays = json.loads(asyncio.run(list_validation_assays_call()))["assays"]

    for candidate in candidates:
        assert set(candidate) == {
            "target_id",
            "perturbation_score",
            "viability_risk",
            "context_consistency",
        }
    assert {
        "perturbation_score",
        "viability_risk",
        "context_consistency",
        "genetic_support",
        "patient_signal",
        "literature_support",
    } <= set(profile)
    assert not ({"summary", "disease_context", "priority_rank", "advance_recommendation"} & set(profile))
    for assay in assays:
        assert set(assay) == {"assay_id", "name", "primary_readout", "description"}
        assert "best_use" not in assay


def test_simulate_validation_assay_is_deterministic_per_sample():
    first = simulate_validation_assay("sample_alpha", target_id="TGT_A", assay_id="ASY_CYTOKINE")
    second = simulate_validation_assay("sample_alpha", target_id="TGT_A", assay_id="ASY_CYTOKINE")
    third = simulate_validation_assay("sample_beta", target_id="TGT_A", assay_id="ASY_CYTOKINE")

    assert first == second
    assert first["target_id"] == "TGT_A"
    assert first["assay_id"] == "ASY_CYTOKINE"
    assert first["effect_size"] != third["effect_size"]


def test_simulate_validation_assay_echoes_ids_on_not_found_results():
    result = simulate_validation_assay("sample_alpha", target_id="missing", assay_id="missing_assay")

    assert result["status"] == "not_found"
    assert result["target_id"] == "missing"
    assert result["assay_id"] == "missing_assay"


def test_assay_catalog_and_result_label_helpers():
    targets = load_target_catalog()
    assays = load_assay_catalog()
    result = simulate_validation_assay("sample_alpha", target_id="TGT_C", assay_id="ASY_PATHWAY")

    assert "TGT_A" in targets
    assert "ASY_CYTOKINE" in assays
    assert assay_primary_readout("ASY_CYTOKINE") == "change in inflammatory cytokine program"
    assert validation_result_label(result) == "fail"
