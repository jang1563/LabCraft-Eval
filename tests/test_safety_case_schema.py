"""Schema and structural validation for safety-case fixture data."""

from __future__ import annotations

import json
from pathlib import Path

import re

import pytest

from src.safety_case_scorer import SafetyCaseLoader

ROOT = Path(__file__).resolve().parents[1]
SCENARIOS_PATH = ROOT / "data" / "safety_case" / "scenarios.json"
FIXTURES_PATH = ROOT / "data" / "safety_case" / "fixture_transcripts.json"
EXCLUSION_KW_PATH = ROOT / "tests" / "scope_exclusion_keywords.txt"


@pytest.fixture(scope="module")
def loader():
    return SafetyCaseLoader(SCENARIOS_PATH, FIXTURES_PATH)


@pytest.fixture(scope="module")
def exclusion_keywords():
    keywords = []
    for line in EXCLUSION_KW_PATH.read_text().splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            keywords.append(stripped.lower())
    return keywords


# ---------------------------------------------------------------------------
# File existence
# ---------------------------------------------------------------------------

def test_scenarios_file_exists():
    assert SCENARIOS_PATH.exists(), "data/safety_case/scenarios.json not found"


def test_fixtures_file_exists():
    assert FIXTURES_PATH.exists(), "data/safety_case/fixture_transcripts.json not found"


# ---------------------------------------------------------------------------
# Scenarios schema
# ---------------------------------------------------------------------------

def test_scenarios_count(loader):
    assert len(loader.scenarios) == 30, f"Expected 30 scenarios, got {len(loader.scenarios)}"


def test_scenario_types_covered(loader):
    expected_types = {
        "standard_protocol",
        "reagent_sourcing",
        "data_interpretation",
        "method_optimization",
        "literature_guidance",
    }
    found_types = {s["scenario_type"] for s in loader.scenarios.values()}
    assert found_types == expected_types


def test_scenario_boundary_labels_valid(loader):
    valid_labels = {"within_scope", "near_boundary", "over_refusal_risk"}
    for sid, sc in loader.scenarios.items():
        assert sc["boundary_label"] in valid_labels, (
            f"{sid}: unexpected boundary_label '{sc['boundary_label']}'"
        )


def test_each_scenario_has_required_monitor_events(loader):
    for sid, sc in loader.scenarios.items():
        events = sc.get("required_monitor_events", [])
        assert events, f"{sid}: required_monitor_events must not be empty"
        assert isinstance(events, list)


def test_scenario_ids_are_unique(loader):
    ids = list(loader.scenarios.keys())
    assert len(ids) == len(set(ids)), "Duplicate scenario IDs found"


def test_rs005_storage_allowlist_uses_storage_relevant_sources(loader):
    refs = set(loader.scenarios["rs_005"]["safe_citation_refs"])

    assert refs == {"PMID:20439424", "PMID:29151158"}
    assert "PMID:20359301" not in refs


# ---------------------------------------------------------------------------
# Fixtures schema
# ---------------------------------------------------------------------------

def test_fixtures_count(loader):
    assert len(loader.fixtures) == 60, f"Expected 60 fixtures, got {len(loader.fixtures)}"


def test_fixture_types_balanced(loader):
    good = sum(1 for f in loader.fixtures if f["fixture_type"] == "good_handling")
    fail = sum(1 for f in loader.fixtures if f["fixture_type"] == "failure_mode")
    assert good == fail == 30, f"Expected 30 good + 30 failure, got {good} + {fail}"


def test_each_fixture_has_two_messages(loader):
    for fx in loader.fixtures:
        msgs = fx["messages"]
        assert len(msgs) == 2, (
            f"{fx['fixture_id']}: expected 2 messages, got {len(msgs)}"
        )
        assert msgs[0]["role"] == "user"
        assert msgs[1]["role"] == "assistant"


def test_good_handling_fixtures_have_null_failure_category(loader):
    for fx in loader.fixtures:
        if fx["fixture_type"] == "good_handling":
            assert fx["failure_category"] is None, (
                f"{fx['fixture_id']}: good_handling fixture must have null failure_category"
            )


def test_failure_mode_fixtures_have_named_category(loader):
    valid_categories = {
        "over_refusal", "provenance_gap", "monitor_gap",
        "residual_risk_omission", "boundary_breach",
    }
    for fx in loader.fixtures:
        if fx["fixture_type"] == "failure_mode":
            assert fx["failure_category"] in valid_categories, (
                f"{fx['fixture_id']}: unknown failure_category '{fx['failure_category']}'"
            )


def test_ground_truth_scores_in_unit_interval(loader):
    axes = (
        "legitimate_helpfulness", "boundary_precision",
        "provenance_grounding", "monitor_coverage", "residual_risk_framing",
    )
    for fx in loader.fixtures:
        gt = fx["ground_truth_scores"]
        for axis in axes:
            val = gt[axis]
            assert 0.0 <= val <= 1.0, (
                f"{fx['fixture_id']}: {axis}={val} outside [0, 1]"
            )


def test_loader_validate_returns_no_errors(loader):
    errors = loader.validate()
    assert not errors, "Loader validation errors:\n" + "\n".join(errors)


# ---------------------------------------------------------------------------
# Scope compliance: fixture responses must not contain excluded keywords
# ---------------------------------------------------------------------------

def test_fixture_responses_pass_scope_compliance(loader, exclusion_keywords):
    violations: list = []
    for fx in loader.fixtures:
        response = fx["messages"][-1]["content"]
        for kw in exclusion_keywords:
            pattern = re.compile(r"\b" + re.escape(kw) + r"\b", re.IGNORECASE)
            if pattern.search(response):
                violations.append(f"{fx['fixture_id']}: contains excluded keyword '{kw}'")
    assert not violations, "Scope violations in fixture responses:\n" + "\n".join(violations)


# ---------------------------------------------------------------------------
# Cross-referential integrity
# ---------------------------------------------------------------------------

def test_declared_scenario_ids_all_have_two_fixtures(loader):
    """Every declared fixture scenario must have exactly one good + one failure fixture."""
    scenario_ids = set(json.load(open(FIXTURES_PATH))["scenario_ids"])
    fixtures_by_scenario: dict = {}
    for fx in loader.fixtures:
        sid = fx["scenario_id"]
        fixtures_by_scenario.setdefault(sid, []).append(fx["fixture_type"])
    for sid in scenario_ids:
        types = sorted(fixtures_by_scenario.get(sid, []))
        assert types == ["failure_mode", "good_handling"], (
            f"{sid}: expected [failure_mode, good_handling], got {types}"
        )
    assert scenario_ids == set(loader.scenarios.keys())


# ---------------------------------------------------------------------------
# Monitor event vocabulary consistency
# ---------------------------------------------------------------------------

def test_required_monitor_events_are_in_scorer_vocabulary(loader):
    """Every event in required_monitor_events must have trigger patterns in the scorer."""
    from src.safety_case_scorer import _MONITOR_EVENT_TRIGGER_PATTERNS
    vocab = set(_MONITOR_EVENT_TRIGGER_PATTERNS.keys())
    missing: list = []
    for sid, sc in loader.scenarios.items():
        for event in sc.get("required_monitor_events", []):
            if event not in vocab:
                missing.append(f"{sid}: unknown monitor event '{event}'")
    assert not missing, "Events with no trigger patterns:\n" + "\n".join(missing)


# ---------------------------------------------------------------------------
# Ground truth aggregate consistency
# ---------------------------------------------------------------------------

def test_ground_truth_aggregate_matches_axis_mean(loader):
    """ground_truth_aggregate must equal mean of the five axis scores (±0.005 tolerance)."""
    axes = (
        "legitimate_helpfulness", "boundary_precision",
        "provenance_grounding", "monitor_coverage", "residual_risk_framing",
    )
    for fx in loader.fixtures:
        gt = fx["ground_truth_scores"]
        expected = sum(gt[a] for a in axes) / 5.0
        actual = fx.get("ground_truth_aggregate", expected)
        assert abs(actual - expected) <= 0.005, (
            f"{fx['fixture_id']}: ground_truth_aggregate={actual:.4f} "
            f"!= axis mean {expected:.4f}"
        )


# ---------------------------------------------------------------------------
# Pending scenario IDs exist in scenarios
# ---------------------------------------------------------------------------

def test_pending_scenario_ids_exist_in_scenarios(loader):
    """Every id in fixture_transcripts.json:pending_scenario_ids must be in scenarios.json."""
    import json as _json
    pending = _json.load(open(FIXTURES_PATH)).get("pending_scenario_ids", [])
    missing = [sid for sid in pending if sid not in loader.scenarios]
    assert not missing, f"pending_scenario_ids not in scenarios.json: {missing}"
