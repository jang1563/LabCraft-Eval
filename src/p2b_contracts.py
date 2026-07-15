"""Development-only contract and regression gate for the first P2b task.

This module is intentionally separate from ``src.scorer_contracts``. The P1
contract pins exactly five scorers and 35 fixtures; P2b must not mutate that
historical validation surface.
"""

from __future__ import annotations

import copy
import hashlib
import importlib
import inspect
import json
import math
from pathlib import Path
import re
from typing import Any, Callable, Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]
P2B_TASK_ID = "pcr_causal_reasoning_01"
CONTRACT_ROOT = REPO_ROOT / "task_data" / P2B_TASK_ID
CONTRACT_PATH = CONTRACT_ROOT / "development_contract.json"
FIXTURE_PATH = CONTRACT_ROOT / "development_fixtures.json"

SCORE_COMPONENTS = (
    "overall",
    "task_success",
    "decision_quality",
    "troubleshooting",
    "efficiency",
)
WEIGHTED_COMPONENTS = (
    "task_success",
    "decision_quality",
    "troubleshooting",
    "efficiency",
)
DECISION_IDS = (
    "case_specific_diagnosis",
    "causal_parameter_identification",
    "one_variable_causal_correction",
    "accepted_corrective_setting",
)
ALLOWED_MUTATIONS = {
    "append",
    "append_fragment",
    "append_text",
    "prepend_fragment",
    "remove",
    "replace",
    "replace_text",
    "to_output_only",
}
FAIL_CLOSED_FAMILIES = {
    "forged_request_only",
    "orphan_output_only",
    "partial_missing_gel",
    "contradictory_request_output",
    "duplicate_call_id",
    "contradictory_linked_outputs",
    "malformed_output",
}
_SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
_PERSONAL_PATH = re.compile(r"/(?:Users|home)/(?:[^/\s`]+/){1,2}(?:Dropbox|codex_runs)")
_SECRET = re.compile(r"\b(?:sk-[A-Za-z0-9_-]{16,}|api[_-]?key\s*[:=])", re.IGNORECASE)


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError("Expected a JSON object at {}".format(path))
    return payload


def load_p2b_contract() -> dict[str, Any]:
    return _load_json(CONTRACT_PATH)


def load_p2b_fixtures() -> dict[str, Any]:
    return _load_json(FIXTURE_PATH)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _repo_path(relative_path: str) -> Path:
    path = (REPO_ROOT / relative_path).resolve()
    try:
        path.relative_to(REPO_ROOT.resolve())
    except ValueError as exc:
        raise ValueError("P2b contract path escapes the repository: {}".format(relative_path)) from exc
    return path


def _import_callable(specification: str) -> Callable[..., Any]:
    if not isinstance(specification, str) or ":" not in specification:
        raise ValueError("Invalid callable specification: {!r}".format(specification))
    module_name, attribute_name = specification.split(":", 1)
    module = importlib.import_module(module_name)
    value = getattr(module, attribute_name)
    if not callable(value):
        raise TypeError("P2b contract target is not callable: {}".format(specification))
    return value


def _decode_pointer(path: str) -> list[str]:
    if not isinstance(path, str) or not path.startswith("/"):
        raise ValueError("Mutation path must be a JSON pointer: {!r}".format(path))
    return [part.replace("~1", "/").replace("~0", "~") for part in path[1:].split("/")]


def _resolve_pointer(document: Any, path: str) -> Any:
    current = document
    for part in _decode_pointer(path):
        current = current[int(part)] if isinstance(current, list) else current[part]
    return current


def _resolve_parent(document: Any, path: str) -> tuple[Any, str]:
    parts = _decode_pointer(path)
    if not parts:
        raise ValueError("Mutation cannot replace the document root.")
    parent = document
    for part in parts[:-1]:
        parent = parent[int(part)] if isinstance(parent, list) else parent[part]
    return parent, parts[-1]


def _assign(parent: Any, key: str, value: Any) -> None:
    if isinstance(parent, list):
        parent[int(key)] = value
    else:
        parent[key] = value


def _apply_mutation(
    trajectory: dict[str, Any],
    mutation: dict[str, Any],
    corpus: dict[str, Any],
) -> None:
    operation = mutation.get("op")
    path = mutation.get("path")
    if operation not in ALLOWED_MUTATIONS:
        raise ValueError("Unsupported P2b mutation operation: {!r}".format(operation))
    if not isinstance(path, str):
        raise ValueError("P2b mutation path must be a string.")

    if operation == "append":
        target = _resolve_pointer(trajectory, path)
        if not isinstance(target, list):
            raise ValueError("append target is not a list: {}".format(path))
        target.append(copy.deepcopy(mutation.get("value")))
        return
    if operation in {"prepend_fragment", "append_fragment"}:
        target = _resolve_pointer(trajectory, path)
        if not isinstance(target, list):
            raise ValueError("fragment target is not a list: {}".format(path))
        fragment_name = mutation.get("fragment")
        fragments = corpus.get("event_fragments", {})
        if fragment_name not in fragments or not isinstance(fragments[fragment_name], list):
            raise ValueError("Unknown event fragment: {!r}".format(fragment_name))
        values = copy.deepcopy(fragments[fragment_name])
        if operation == "prepend_fragment":
            target[0:0] = values
        else:
            target.extend(values)
        return
    if operation == "append_text":
        parent, key = _resolve_parent(trajectory, path)
        current = parent[int(key)] if isinstance(parent, list) else parent.get(key)
        if not isinstance(current, str) or not isinstance(mutation.get("value"), str):
            raise ValueError("append_text needs string target and value: {}".format(path))
        _assign(parent, key, current + mutation["value"])
        return
    if operation == "replace_text":
        parent, key = _resolve_parent(trajectory, path)
        current = parent[int(key)] if isinstance(parent, list) else parent.get(key)
        old = mutation.get("old")
        value = mutation.get("value")
        if not all(isinstance(item, str) for item in (current, old, value)):
            raise ValueError("replace_text needs string target, old, and value.")
        if current.count(old) != 1:
            raise ValueError("replace_text old value must occur exactly once: {}".format(path))
        _assign(parent, key, current.replace(old, value, 1))
        return
    if operation == "to_output_only":
        parent, key = _resolve_parent(trajectory, path)
        event = parent[int(key)] if isinstance(parent, list) else parent.get(key)
        if not isinstance(event, dict) or "content" not in event:
            raise ValueError("to_output_only target is not a combined tool event.")
        replacement = {
            "role": "tool",
            "name": event.get("tool_name"),
            "tool_call_id": event.get("call_id"),
            "content": copy.deepcopy(event.get("content")),
        }
        _assign(parent, key, replacement)
        return

    parent, key = _resolve_parent(trajectory, path)
    if operation == "remove":
        if isinstance(parent, list):
            parent.pop(int(key))
        else:
            if key not in parent:
                raise ValueError("remove path does not exist: {}".format(path))
            del parent[key]
        return
    if operation == "replace":
        _assign(parent, key, copy.deepcopy(mutation.get("value")))


def materialize_p2b_fixture(
    corpus: dict[str, Any], fixture: dict[str, Any]
) -> dict[str, Any]:
    base_name = fixture.get("base_trajectory")
    try:
        trajectory = copy.deepcopy(corpus["base_trajectories"][base_name])
    except KeyError as exc:
        raise ValueError("Unknown P2b base trajectory: {!r}".format(base_name)) from exc
    for mutation in fixture.get("mutations", []):
        _apply_mutation(trajectory, mutation, corpus)
    return trajectory


def score_p2b_fixture(
    corpus: dict[str, Any],
    fixture: dict[str, Any],
    contract: dict[str, Any] | None = None,
) -> dict[str, Any]:
    contract = contract or load_p2b_contract()
    trajectory = materialize_p2b_fixture(corpus, fixture)
    scorer = _import_callable(contract["scorer_callable"])
    ground_truth_path = _repo_path(contract["artifact_bindings"]["ground_truth_path"])
    return scorer(
        final_answer=trajectory["final_answer"],
        transcript=trajectory["transcript"],
        ground_truth_path=str(ground_truth_path),
        case_id=trajectory["case_id"],
    )


def _walk_strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from _walk_strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_strings(child)


def _score_projection(values: dict[str, Any]) -> dict[str, Any]:
    projected = {key: values.get(key) for key in SCORE_COMPONENTS}
    projected["decision_scores"] = values.get("decision_scores")
    return projected


def _scores_equal(observed: dict[str, Any], expected: dict[str, Any]) -> bool:
    if set(observed) != set(expected):
        return False
    for key in SCORE_COMPONENTS:
        if not math.isclose(float(observed[key]), float(expected[key]), abs_tol=1e-12):
            return False
    if set(observed["decision_scores"]) != set(expected["decision_scores"]):
        return False
    return all(
        math.isclose(
            float(observed["decision_scores"][decision_id]),
            float(expected["decision_scores"][decision_id]),
            abs_tol=1e-12,
        )
        for decision_id in observed["decision_scores"]
    )


def promotion_blockers(contract: dict[str, Any] | None = None) -> list[str]:
    contract = contract or load_p2b_contract()
    blockers: list[str] = []
    if contract.get("expert_review_status") != "approved":
        blockers.append("expert_review_skipped")
    if contract.get("evaluation_policy_ready") is not True:
        blockers.append("evaluation_policy_not_ready")
    if contract.get("external_evaluation_authorized") is not True:
        blockers.append("external_evaluation_not_authorized")
    if contract.get("scientific_validity_status") != "assessed":
        blockers.append("scientific_validity_unassessed")
    return blockers


def p2b_contract_metadata() -> dict[str, Any]:
    contract = load_p2b_contract()
    return {
        "p2b_contract_set": contract["contract_set"],
        "p2b_contract_version": contract["contract_set_version"],
        "p2b_contract_sha256": sha256_file(CONTRACT_PATH),
        "scorer_version": contract["scorer_version"],
        "validation_tier": contract["validation_tier"],
        "promotion_eligible": contract["promotion_eligible"],
        "evaluation_policy_ready": contract["evaluation_policy_ready"],
        "external_evaluation_authorized": contract["external_evaluation_authorized"],
    }


def validate_p2b_contract() -> list[str]:
    """Validate P2b structure, bindings, vectors, determinism, and blockers."""
    errors: list[str] = []
    try:
        contract = load_p2b_contract()
        corpus = load_p2b_fixtures()
    except Exception as exc:
        return ["P2b contract load failed: {}".format(exc)]

    for key in ("contract_schema_version", "contract_set_version"):
        if not _SEMVER.fullmatch(str(contract.get(key, ""))):
            errors.append("{} must be SemVer".format(key))
    if contract.get("contract_set") != "p2b_causal_reasoning_dev":
        errors.append("contract_set must be p2b_causal_reasoning_dev")
    if contract.get("task_id") != P2B_TASK_ID or corpus.get("task_id") != P2B_TASK_ID:
        errors.append("P2b task_id mismatch")
    if contract.get("validation_tier") != "development_unreviewed":
        errors.append("validation_tier must be development_unreviewed")
    if contract.get("expert_review_status") != "skipped":
        errors.append("expert_review_status must remain skipped for this local scope")
    if contract.get("fixture_label_source") != "ai_assisted_test_oracle":
        errors.append("fixture_label_source must be ai_assisted_test_oracle")
    if contract.get("scientific_validity_status") != "unassessed":
        errors.append("scientific_validity_status must remain unassessed")
    for key in (
        "promotion_eligible",
        "evaluation_policy_ready",
        "external_evaluation_authorized",
        "public_export_eligible",
    ):
        if contract.get(key) is not False:
            errors.append("{} must remain false".format(key))
    if corpus.get("validation_tier") != contract.get("validation_tier"):
        errors.append("fixture validation_tier mismatch")
    if corpus.get("expert_review_status") != contract.get("expert_review_status"):
        errors.append("fixture expert_review_status mismatch")
    if corpus.get("promotion_eligible") is not False:
        errors.append("fixture promotion_eligible must remain false")

    weights = contract.get("component_weights", {})
    if set(weights) != set(WEIGHTED_COMPONENTS) or not math.isclose(
        sum(float(value) for value in weights.values()), 1.0, abs_tol=1e-12
    ):
        errors.append("component_weights must contain the four standard axes and sum to 1")
    if tuple(contract.get("decision_point_ids", [])) != DECISION_IDS:
        errors.append("decision_point_ids mismatch")

    bindings = contract.get("artifact_bindings", {})
    artifact_paths: dict[str, Path] = {}
    for artifact in (
        "task_source",
        "scorer_source",
        "simulator_source",
        "pcr_parameters",
        "ground_truth",
        "rubric",
        "fixture",
    ):
        try:
            path = _repo_path(bindings[artifact + "_path"])
            artifact_paths[artifact] = path
            if not path.is_file():
                errors.append("{} path does not exist".format(artifact))
            elif sha256_file(path) != bindings.get(artifact + "_sha256"):
                errors.append("{} SHA-256 mismatch".format(artifact))
        except Exception as exc:
            errors.append("{} binding is invalid: {}".format(artifact, exc))

    try:
        scorer = _import_callable(contract["scorer_callable"])
        required = {"final_answer", "transcript", "ground_truth_path", "case_id"}
        if not required <= set(inspect.signature(scorer).parameters):
            errors.append("scorer callable has an incompatible signature")
        module = importlib.import_module(scorer.__module__)
        if getattr(module, "SCORER_VERSION", None) != contract.get("scorer_version"):
            errors.append("scorer module version mismatch")
        _import_callable(contract["inspect_builder"])
    except Exception as exc:
        errors.append("P2b callable import failed: {}".format(exc))

    try:
        ground_truth = _load_json(artifact_paths["ground_truth"])
        rubric = _load_json(artifact_paths["rubric"])
    except Exception as exc:
        errors.append("ground truth or rubric load failed: {}".format(exc))
    else:
        if ground_truth.get("task_id") != P2B_TASK_ID or rubric.get("task_id") != P2B_TASK_ID:
            errors.append("ground truth or rubric task_id mismatch")
        decision_ids = tuple(
            point.get("id") for point in ground_truth.get("decision_points", [])
        )
        if decision_ids != DECISION_IDS:
            errors.append("ground-truth decision order mismatch")
        if ground_truth.get("report_fields") != contract.get("report_fields"):
            errors.append("report field contract mismatch")
        if tuple(ground_truth.get("cases", {})) != tuple(contract.get("cases", [])):
            errors.append("case inventory mismatch")

    fixtures = corpus.get("fixtures")
    if not isinstance(fixtures, list):
        return errors + ["fixtures must be a list"]
    families = [fixture.get("case_family") for fixture in fixtures]
    if families != contract.get("required_fixture_families"):
        errors.append("required fixture family order mismatch")
    if len(fixtures) != contract.get("fixture_count"):
        errors.append("fixture_count mismatch")
    if corpus.get("scorer_version") != contract.get("scorer_version"):
        errors.append("fixture scorer_version mismatch")

    seen_fixture_ids: set[str] = set()
    valid_cases: set[str] = set()
    for fixture in fixtures:
        fixture_id = fixture.get("fixture_id")
        prefix = "{}: ".format(fixture_id)
        if not isinstance(fixture_id, str) or not fixture_id.startswith(P2B_TASK_ID + "."):
            errors.append(prefix + "invalid fixture_id")
        elif fixture_id in seen_fixture_ids:
            errors.append(prefix + "duplicate fixture_id")
        else:
            seen_fixture_ids.add(fixture_id)
        if fixture.get("expected_validity") not in {"valid", "invalid"}:
            errors.append(prefix + "expected_validity must be valid or invalid")
        annotation = fixture.get("annotation", {})
        if annotation.get("origin") != "ai_assisted_test_oracle":
            errors.append(prefix + "annotation origin mismatch")
        if annotation.get("label_status") != "development_unreviewed":
            errors.append(prefix + "annotation label_status mismatch")
        if annotation.get("reviewer") is not None or annotation.get("reviewed_at") is not None:
            errors.append(prefix + "unreviewed annotation must not name reviewer or date")
        if not str(annotation.get("rationale", "")).strip():
            errors.append(prefix + "annotation rationale is required")

        mutations = fixture.get("mutations")
        if not isinstance(mutations, list) or any(
            not isinstance(mutation, dict)
            or mutation.get("op") not in ALLOWED_MUTATIONS
            for mutation in mutations
        ):
            errors.append(prefix + "invalid mutation list")
            continue
        try:
            trajectory = materialize_p2b_fixture(corpus, fixture)
        except Exception as exc:
            errors.append(prefix + "materialization failed: {}".format(exc))
            continue
        if fixture.get("expected_validity") == "valid":
            valid_cases.add(str(trajectory.get("case_id")))

        expected = fixture.get("expected_scores")
        if not isinstance(expected, dict) or set(expected) != set(SCORE_COMPONENTS) | {
            "decision_scores"
        }:
            errors.append(prefix + "expected score keys mismatch")
            continue
        if set(expected.get("decision_scores", {})) != set(DECISION_IDS):
            errors.append(prefix + "expected decision score keys mismatch")
            continue
        numeric = [expected[key] for key in SCORE_COMPONENTS]
        numeric.extend(expected["decision_scores"].values())
        if any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(float(value))
            or not 0.0 <= float(value) <= 1.0
            for value in numeric
        ):
            errors.append(prefix + "expected scores must be finite values in [0,1]")
            continue
        recomputed = sum(
            float(weights[component]) * float(expected[component])
            for component in WEIGHTED_COMPONENTS
        )
        if not math.isclose(recomputed, float(expected["overall"]), abs_tol=1e-12):
            errors.append(prefix + "overall does not match component weights")
        if fixture.get("expected_validity") == "valid" and any(
            not math.isclose(float(expected[key]), 1.0, abs_tol=1e-12)
            for key in SCORE_COMPONENTS
        ):
            errors.append(prefix + "valid fixture must have full component scores")
        if fixture.get("case_family") in FAIL_CLOSED_FAMILIES and any(
            not math.isclose(float(expected[key]), 0.0, abs_tol=1e-12)
            for key in SCORE_COMPONENTS
        ):
            errors.append(prefix + "evidence-forgery family must fail closed")

        try:
            first = _score_projection(score_p2b_fixture(corpus, fixture, contract))
            second = _score_projection(score_p2b_fixture(corpus, fixture, contract))
        except Exception as exc:
            errors.append(prefix + "scoring failed: {}".format(exc))
            continue
        if not _scores_equal(first, second):
            errors.append(prefix + "scorer is not deterministic across two runs")
        if not _scores_equal(first, expected):
            errors.append(prefix + "computed vector differs from expected vector")

    if valid_cases != set(contract.get("cases", [])):
        errors.append("valid fixtures must cover both bound cases")
    for value in _walk_strings(corpus):
        if _PERSONAL_PATH.search(value):
            errors.append("fixture corpus contains a personal path")
        if _SECRET.search(value):
            errors.append("fixture corpus contains a possible secret")

    blockers = promotion_blockers(contract)
    if blockers != contract.get("promotion_blockers"):
        errors.append("declared promotion blockers do not match contract state")
    if contract.get("promotion_eligible") is (len(blockers) > 0):
        errors.append("promotion_eligible is inconsistent with promotion blockers")
    return errors
