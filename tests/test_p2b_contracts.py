from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from src.p2b_contracts import (
    CONTRACT_PATH,
    DECISION_IDS,
    FIXTURE_PATH,
    load_p2b_contract,
    load_p2b_fixtures,
    materialize_p2b_fixture,
    p2b_contract_metadata,
    promotion_blockers,
    score_p2b_fixture,
    sha256_file,
    validate_p2b_contract,
)


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "validate_p2b_contracts.py"


def test_p2b_contract_is_structurally_and_numerically_valid():
    assert validate_p2b_contract() == []


def test_p2b_contract_stays_explicitly_unreviewed_and_non_promotable():
    contract = load_p2b_contract()

    assert contract["validation_tier"] == "development_unreviewed"
    assert contract["expert_review_status"] == "skipped"
    assert contract["fixture_label_source"] == "ai_assisted_test_oracle"
    assert contract["scientific_validity_status"] == "unassessed"
    assert contract["promotion_eligible"] is False
    assert contract["evaluation_policy_ready"] is False
    assert contract["external_evaluation_authorized"] is False
    assert contract["public_export_eligible"] is False
    assert promotion_blockers(contract) == [
        "expert_review_skipped",
        "evaluation_policy_not_ready",
        "external_evaluation_not_authorized",
        "scientific_validity_unassessed",
    ]


def test_p2b_artifact_hashes_bind_scorer_and_task_contract():
    contract = load_p2b_contract()
    bindings = contract["artifact_bindings"]

    for artifact in (
        "task_source",
        "scorer_source",
        "simulator_source",
        "pcr_parameters",
        "ground_truth",
        "rubric",
        "fixture",
    ):
        path = ROOT / bindings[artifact + "_path"]
        assert path.is_file()
        assert sha256_file(path) == bindings[artifact + "_sha256"]

    metadata = p2b_contract_metadata()
    assert metadata["p2b_contract_sha256"] == sha256_file(CONTRACT_PATH)
    assert metadata["promotion_eligible"] is False


def test_p2b_fixture_inventory_covers_both_cases_and_adversarial_families():
    contract = load_p2b_contract()
    corpus = load_p2b_fixtures()
    fixtures = corpus["fixtures"]

    assert len(fixtures) == contract["fixture_count"] == 19
    assert [fixture["case_family"] for fixture in fixtures] == contract[
        "required_fixture_families"
    ]
    valid_cases = {
        materialize_p2b_fixture(corpus, fixture)["case_id"]
        for fixture in fixtures
        if fixture["expected_validity"] == "valid"
    }
    assert valid_cases == {"case_a", "case_b"}
    assert {
        "forged_request_only",
        "orphan_output_only",
        "partial_missing_gel",
        "contradictory_request_output",
        "duplicate_call_id",
        "contradictory_linked_outputs",
        "malformed_output",
        "prior_rerun_shortcut",
        "executed_counterfactual",
        "phenotype_shortcut",
    }.issubset({fixture["case_family"] for fixture in fixtures})


def test_each_p2b_fixture_repeats_the_exact_frozen_score_vector():
    contract = load_p2b_contract()
    corpus = load_p2b_fixtures()

    for fixture in corpus["fixtures"]:
        first = score_p2b_fixture(corpus, fixture, contract)
        second = score_p2b_fixture(corpus, fixture, contract)
        expected = fixture["expected_scores"]
        assert first == second
        assert {key: first[key] for key in expected if key != "decision_scores"} == {
            key: expected[key] for key in expected if key != "decision_scores"
        }
        assert first["decision_scores"] == expected["decision_scores"]
        assert set(first["decision_scores"]) == set(DECISION_IDS)
        assert first["promotion_eligible"] is False


def test_orphan_fixture_materializes_as_output_only_messages():
    corpus = load_p2b_fixtures()
    fixture = next(
        item for item in corpus["fixtures"] if item["case_family"] == "orphan_output_only"
    )
    trajectory = materialize_p2b_fixture(corpus, fixture)

    assert [message["role"] for message in trajectory["transcript"]] == ["tool", "tool"]
    assert all("arguments" not in message for message in trajectory["transcript"])


def test_validator_cli_passes_technical_gate_but_blocks_promotion():
    technical = subprocess.run(
        [sys.executable, str(VALIDATOR)],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert technical.returncode == 0, technical.stdout + technical.stderr
    assert "P2B_DEVELOPMENT_REGRESSION_OK fixtures=19" in technical.stdout
    assert "promotion_eligible=false" in technical.stdout

    promotion = subprocess.run(
        [sys.executable, str(VALIDATOR), "--require-promotable", "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert promotion.returncode == 2
    payload = json.loads(promotion.stdout)
    assert payload["status"] == "development_regression_ok"
    assert payload["promotion_eligible"] is False
    assert "expert_review_skipped" in promotion.stderr
    assert "evaluation_policy_not_ready" in promotion.stderr
    assert "external_evaluation_not_authorized" in promotion.stderr


def test_contract_files_are_under_the_task_directory():
    assert CONTRACT_PATH.parent == FIXTURE_PATH.parent
    assert CONTRACT_PATH.parent == ROOT / "task_data" / "pcr_causal_reasoning_01"
