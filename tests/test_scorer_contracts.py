"""Cross-task schema, provenance, regression, and review-gate tests for P2a."""

from __future__ import annotations

import copy
import json
import math
from pathlib import Path
import subprocess
import sys

import pytest
from jsonschema import Draft202012Validator

import src.scorer_contracts as scorer_contracts
from src.scorer_contracts import (
    CONTRACT_ROOT,
    MANIFEST_PATH,
    P1_TASK_IDS,
    REQUIRED_FIXTURE_FAMILIES,
    SCORE_COMPONENTS,
    fixture_definition_sha256,
    load_review_manifest,
    load_scorer_contract_manifest,
    load_task_fixture_corpus,
    materialize_fixture,
    review_progress,
    run_scorer_regression,
    score_materialized_fixture,
    scorer_contract_metadata,
    sha256_file,
    validate_contract_bundle,
)
from src.tasks.express_01 import build_express_01_sample
from src.tasks.gibson_01 import build_gibson_01_sample
from src.tasks.golden_gate_01 import build_golden_gate_01_sample
from src.tasks.miniprep_01 import build_miniprep_01_sample
from src.tasks.purify_01 import build_purify_01_sample


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_REPORT_COUNTS = {
    "golden_gate_01": 8,
    "gibson_01": 8,
    "miniprep_01": 11,
    "express_01": 11,
    "purify_01": 16,
}
SAMPLE_BUILDERS = {
    "golden_gate_01": build_golden_gate_01_sample,
    "gibson_01": build_gibson_01_sample,
    "miniprep_01": build_miniprep_01_sample,
    "express_01": build_express_01_sample,
    "purify_01": build_purify_01_sample,
}


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _fixture_cases():
    for task_id in P1_TASK_IDS:
        corpus = load_task_fixture_corpus(task_id)
        for fixture in corpus["fixtures"]:
            yield pytest.param(task_id, corpus, fixture, id=fixture["fixture_id"])


def test_contract_bundle_is_structurally_valid_and_hash_bound():
    assert validate_contract_bundle() == []


def test_validator_cli_runs_directly_and_keeps_expert_gate_closed():
    command = [sys.executable, str(ROOT / "scripts" / "validate_scorer_contracts.py")]
    technical = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        check=False,
        text=True,
    )
    expert = subprocess.run(
        [*command, "--require-expert-approved"],
        cwd=ROOT,
        capture_output=True,
        check=False,
        text=True,
    )

    assert technical.returncode == 0
    assert "SCORER_CONTRACT_REGRESSION_OK fixtures=35" in technical.stdout
    assert expert.returncode == 2
    assert "EXPERT_REVIEW_GATE_CLOSED" in expert.stdout


def test_contract_artifacts_match_their_packaged_json_schemas():
    manifest = load_scorer_contract_manifest()
    manifest_schema = _load(CONTRACT_ROOT / "schemas" / "scorer_contract_manifest.schema.json")
    fixture_schema = _load(CONTRACT_ROOT / "schemas" / "trajectory_fixture_corpus.schema.json")
    review_schema = _load(CONTRACT_ROOT / "schemas" / "review_manifest.schema.json")

    Draft202012Validator(manifest_schema).validate(manifest)
    Draft202012Validator(review_schema).validate(load_review_manifest())
    for task_id in P1_TASK_IDS:
        Draft202012Validator(fixture_schema).validate(load_task_fixture_corpus(task_id))


def test_manifest_freezes_exact_p1_tasks_reports_and_fixture_families():
    manifest = load_scorer_contract_manifest()

    assert tuple(manifest["tasks"]) == P1_TASK_IDS
    assert manifest["required_fixture_families"] == list(REQUIRED_FIXTURE_FAMILIES)
    assert manifest["component_weights"] == {
        "task_success": 0.4,
        "decision_quality": 0.3,
        "troubleshooting": 0.2,
        "efficiency": 0.1,
    }
    for task_id, expected_count in EXPECTED_REPORT_COUNTS.items():
        task_contract = manifest["tasks"][task_id]
        assert task_contract["report_field_count"] == expected_count
        assert len(task_contract["report_fields"]) == expected_count
        assert task_contract["fixture_count"] == len(REQUIRED_FIXTURE_FAMILIES)
        assert task_contract["evidence_policy"]["request_and_output_required"] is True
        assert task_contract["evidence_policy"]["output_authoritative"] is True
        assert task_contract["evidence_policy"]["causal_order_required"] is True


@pytest.mark.parametrize("task_id,corpus,fixture", list(_fixture_cases()))
def test_each_fixture_matches_its_full_frozen_score_vector(task_id, corpus, fixture):
    trajectory = materialize_fixture(corpus, fixture)
    actual = score_materialized_fixture(task_id, trajectory)
    expected = fixture["expected_scores"]

    for component in SCORE_COMPONENTS:
        assert actual[component] == pytest.approx(expected[component], abs=1e-12)
    assert actual["decision_scores"] == pytest.approx(
        expected["decision_scores"],
        abs=1e-12,
    )


def test_regression_runner_is_deterministic():
    assert run_scorer_regression() == []
    assert run_scorer_regression() == []


def test_fixture_materialization_is_pure_and_review_hashes_are_unique():
    manifest = load_scorer_contract_manifest()
    hashes = set()
    for task_id in P1_TASK_IDS:
        corpus = load_task_fixture_corpus(task_id)
        original = copy.deepcopy(corpus)
        for fixture in corpus["fixtures"]:
            first = materialize_fixture(corpus, fixture)
            second = materialize_fixture(corpus, fixture)
            assert first == second
            hashes.add(fixture_definition_sha256(manifest, corpus, fixture))
        assert corpus == original
    assert len(hashes) == len(P1_TASK_IDS) * len(REQUIRED_FIXTURE_FAMILIES)


def test_review_hash_binds_materialized_trajectory_and_scorer_contract():
    manifest = copy.deepcopy(load_scorer_contract_manifest())
    corpus = copy.deepcopy(load_task_fixture_corpus(P1_TASK_IDS[0]))
    fixture = corpus["fixtures"][0]
    original_hash = fixture_definition_sha256(manifest, corpus, fixture)

    corpus["base_trajectory"]["final_answer"] += "\nchanged"
    assert fixture_definition_sha256(manifest, corpus, fixture) != original_hash

    corpus = copy.deepcopy(load_task_fixture_corpus(P1_TASK_IDS[0]))
    manifest["tasks"][P1_TASK_IDS[0]]["scorer_source_sha256"] = "0" * 64
    assert fixture_definition_sha256(manifest, corpus, fixture) != original_hash


def test_expected_overall_is_the_declared_weighted_sum():
    weights = load_scorer_contract_manifest()["component_weights"]
    for task_id in P1_TASK_IDS:
        for fixture in load_task_fixture_corpus(task_id)["fixtures"]:
            expected = fixture["expected_scores"]
            recomputed = sum(
                weights[component] * expected[component]
                for component in (
                    "task_success",
                    "decision_quality",
                    "troubleshooting",
                    "efficiency",
                )
            )
            assert math.isclose(recomputed, expected["overall"], abs_tol=1e-12)


def test_request_only_partial_and_orphan_families_fail_closed_across_all_tasks():
    for task_id in P1_TASK_IDS:
        corpus = load_task_fixture_corpus(task_id)
        by_family = {fixture["case_family"]: fixture for fixture in corpus["fixtures"]}
        for family in ("forged", "partial", "orphan"):
            actual = score_materialized_fixture(
                task_id,
                materialize_fixture(corpus, by_family[family]),
            )
            assert all(actual[component] == 0.0 for component in SCORE_COMPONENTS)
            assert all(value == 0.0 for value in actual["decision_scores"].values())


def test_draft_review_boundary_is_fail_closed():
    review = load_review_manifest()
    progress = review_progress()

    assert review["status"] == "pending_expert_review"
    assert review["approvals"] == []
    assert review["reviewer"] is None
    assert review["reviewed_at"] is None
    assert progress == {
        "contract_set": "p1_wet_lab",
        "required": 35,
        "approved": 0,
        "pending": 35,
        "promotion_ready": False,
    }


def test_fully_hash_bound_expert_review_state_validates(monkeypatch, tmp_path):
    manifest = copy.deepcopy(load_scorer_contract_manifest())
    review = copy.deepcopy(load_review_manifest())
    manifest.update(
        {
            "review_status": "expert_approved",
            "promotion_eligible": True,
        }
    )
    review.update(
        {
            "status": "expert_approved",
            "promotion_eligible": True,
            "reviewer": "JK",
            "reviewed_at": "2026-07-15T00:00:00+09:00",
        }
    )

    approvals = []
    fixture_paths = {}
    for task_id in P1_TASK_IDS:
        corpus = copy.deepcopy(load_task_fixture_corpus(task_id))
        corpus.update(
            {
                "review_status": "expert_approved",
                "promotion_eligible": True,
            }
        )
        for fixture in corpus["fixtures"]:
            fixture["annotation"].update(
                {
                    "label_status": "expert_approved",
                    "reviewer": "JK",
                    "reviewed_at": "2026-07-15T00:00:00+09:00",
                }
            )
            approvals.append(
                {
                    "fixture_id": fixture["fixture_id"],
                    "fixture_definition_sha256": fixture_definition_sha256(
                        manifest,
                        corpus,
                        fixture,
                    ),
                    "decision": "approved",
                    "reviewer": "JK",
                    "reviewed_at": "2026-07-15T00:00:00+09:00",
                }
            )
        path = tmp_path / f"{task_id}.json"
        path.write_text(json.dumps(corpus), encoding="utf-8")
        fixture_path = manifest["tasks"][task_id]["fixture_path"]
        fixture_paths[fixture_path] = path
        manifest["tasks"][task_id]["fixture_sha256"] = sha256_file(path)
    review["approvals"] = approvals

    original_repo_path = scorer_contracts._repo_path
    monkeypatch.setattr(
        scorer_contracts,
        "_repo_path",
        lambda path: fixture_paths.get(path, original_repo_path(path)),
    )
    monkeypatch.setattr(scorer_contracts, "load_scorer_contract_manifest", lambda: manifest)
    monkeypatch.setattr(scorer_contracts, "load_review_manifest", lambda: review)

    assert validate_contract_bundle() == []
    review["approvals"][0]["reviewer"] = "different reviewer"
    assert any(
        "provenance does not match" in error for error in validate_contract_bundle()
    )
    review["approvals"][0]["reviewer"] = "JK"
    review["approvals"][0]["reviewed_at"] = "yesterday"
    assert any(
        "RFC 3339 reviewed_at" in error for error in validate_contract_bundle()
    )


def test_missing_hash_bound_artifact_returns_validation_errors(monkeypatch):
    manifest = copy.deepcopy(load_scorer_contract_manifest())
    missing_path = "task_data/golden_gate_01/missing_ground_truth.json"
    manifest["tasks"]["golden_gate_01"]["ground_truth_path"] = missing_path
    monkeypatch.setattr(scorer_contracts, "load_scorer_contract_manifest", lambda: manifest)

    errors = validate_contract_bundle()

    assert any("golden_gate_01: ground_truth_path does not exist" in error for error in errors)


def test_review_progress_counts_only_current_hash_bound_expert_labels(monkeypatch):
    manifest = copy.deepcopy(load_scorer_contract_manifest())
    review = copy.deepcopy(load_review_manifest())
    corpora = {
        task_id: copy.deepcopy(load_task_fixture_corpus(task_id))
        for task_id in P1_TASK_IDS
    }
    fixture = corpora[P1_TASK_IDS[0]]["fixtures"][0]
    fixture["annotation"].update(
        {
            "label_status": "expert_approved",
            "reviewer": "JK",
            "reviewed_at": "2026-07-15T00:00:00+09:00",
        }
    )
    review["approvals"] = [
        {
            "fixture_id": fixture["fixture_id"],
            "fixture_definition_sha256": fixture_definition_sha256(
                manifest,
                corpora[P1_TASK_IDS[0]],
                fixture,
            ),
            "decision": "approved",
            "reviewer": "JK",
            "reviewed_at": "2026-07-15T00:00:00+09:00",
        }
    ]

    monkeypatch.setattr(scorer_contracts, "load_scorer_contract_manifest", lambda: manifest)
    monkeypatch.setattr(scorer_contracts, "load_review_manifest", lambda: review)
    monkeypatch.setattr(
        scorer_contracts,
        "load_task_fixture_corpus",
        lambda task_id: corpora[task_id],
    )

    assert review_progress()["approved"] == 1
    review["approvals"][0]["fixture_definition_sha256"] = "0" * 64
    assert review_progress()["approved"] == 0


@pytest.mark.parametrize("task_id", P1_TASK_IDS)
def test_sample_metadata_pins_the_scorer_contract(task_id):
    sample_metadata = SAMPLE_BUILDERS[task_id]()["metadata"]
    expected = scorer_contract_metadata(task_id)

    assert {key: sample_metadata[key] for key in expected} == expected
    assert sample_metadata["scorer_contract_set"] == "p1_wet_lab"
    assert sample_metadata["scorer_contract_version"] == "1.0.0"
    assert len(sample_metadata["scorer_contract_entry_sha256"]) == 64
    assert len(sample_metadata["scorer_contract_manifest_sha256"]) == 64


def test_manifest_and_fixture_paths_are_relative_and_packaged():
    manifest = load_scorer_contract_manifest()
    assert MANIFEST_PATH.is_file()
    for task_id in P1_TASK_IDS:
        task_contract = manifest["tasks"][task_id]
        for key in ("ground_truth_path", "rubric_path", "fixture_path"):
            path_value = task_contract[key]
            assert not Path(path_value).is_absolute()
            assert (ROOT / path_value).is_file()
