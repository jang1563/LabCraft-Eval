"""Versioned local conformance contracts for the five P1 wet-lab scorers.

The checked-in fixture labels are an AI-assisted draft until the review manifest
records an expert decision for every fixture. Technical regression can pass while
the promotion gate remains closed.
"""

from __future__ import annotations

import copy
from datetime import datetime
import hashlib
import importlib
import inspect
import json
import math
import re
from pathlib import Path
from typing import Any, Callable, Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_ROOT = REPO_ROOT / "task_data" / "scorer_validity"
MANIFEST_PATH = CONTRACT_ROOT / "scorer_contract_manifest.json"
REVIEW_MANIFEST_PATH = CONTRACT_ROOT / "review_manifest.json"

P1_TASK_IDS = (
    "golden_gate_01",
    "gibson_01",
    "miniprep_01",
    "express_01",
    "purify_01",
)
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
REQUIRED_FIXTURE_FAMILIES = (
    "canonical_valid",
    "alternative_valid",
    "forged",
    "partial",
    "orphan",
    "contradictory",
    "retry",
)
PENDING_REVIEW_STATUS = "pending_expert_review"
APPROVED_REVIEW_STATUS = "expert_approved"
REVIEW_TASK_CONTRACT_KEYS = (
    "scorer_version",
    "scorer_callable",
    "inspect_builder",
    "scorer_source_path",
    "scorer_source_sha256",
    "ground_truth_sha256",
    "rubric_sha256",
    "report_field_count",
    "report_fields",
    "decision_point_ids",
    "evidence_policy",
)
ALLOWED_MUTATION_OPERATIONS = {
    "append",
    "append_text",
    "filter_equal",
    "remove",
    "replace",
    "slice",
}
_SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
_REVIEW_TIMESTAMP = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"
)
_PERSONAL_PATH = re.compile(
    r"/(?:Users|home)/(?:[^/\s`]+/){1,2}(?:Dropbox|codex_runs|labcraft-py313)"
)
_SCHEDULER_ID = re.compile(r"\b(?:job|array)\s+`?\d{7,}(?:_\d+)?`?", re.IGNORECASE)
_SECRET = re.compile(r"\b(?:sk-[A-Za-z0-9_-]{16,}|api[_-]?key\s*[:=])", re.IGNORECASE)


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"Expected a JSON object at {path}.")
    return payload


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_sha256(payload: Any) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _is_review_identity(value: Any) -> bool:
    return isinstance(value, str) and bool(value) and value == value.strip()


def _is_review_timestamp(value: Any) -> bool:
    if not isinstance(value, str) or not _REVIEW_TIMESTAMP.fullmatch(value):
        return False
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


def load_scorer_contract_manifest() -> dict[str, Any]:
    return _load_json(MANIFEST_PATH)


def load_review_manifest() -> dict[str, Any]:
    return _load_json(REVIEW_MANIFEST_PATH)


def _repo_path(relative_path: str) -> Path:
    candidate = (REPO_ROOT / relative_path).resolve()
    try:
        candidate.relative_to(REPO_ROOT.resolve())
    except ValueError as exc:
        raise ValueError(f"Contract path escapes repository root: {relative_path}") from exc
    return candidate


def load_task_fixture_corpus(task_id: str) -> dict[str, Any]:
    manifest = load_scorer_contract_manifest()
    try:
        relative_path = manifest["tasks"][task_id]["fixture_path"]
    except KeyError as exc:
        raise KeyError(f"Unknown scorer-contract task: {task_id}") from exc
    return _load_json(_repo_path(relative_path))


def scorer_contract_metadata(task_id: str) -> dict[str, str]:
    """Return stable metadata for task samples and future Inspect logs."""
    manifest = load_scorer_contract_manifest()
    try:
        task_contract = manifest["tasks"][task_id]
    except KeyError as exc:
        raise KeyError(f"Unknown scorer-contract task: {task_id}") from exc
    return {
        "scorer_contract_set": str(manifest["contract_set"]),
        "scorer_contract_schema_version": str(manifest["contract_schema_version"]),
        "scorer_contract_version": str(task_contract["scorer_version"]),
        "scorer_contract_entry_sha256": canonical_sha256(task_contract),
        "scorer_contract_manifest_sha256": sha256_file(MANIFEST_PATH),
    }


def _decode_pointer(path: str) -> list[str]:
    if not isinstance(path, str) or not path.startswith("/"):
        raise ValueError(f"Mutation path must be a JSON pointer: {path!r}")
    return [part.replace("~1", "/").replace("~0", "~") for part in path[1:].split("/")]


def _resolve_pointer(document: Any, path: str) -> Any:
    current = document
    for part in _decode_pointer(path):
        if isinstance(current, list):
            current = current[int(part)]
        elif isinstance(current, dict):
            current = current[part]
        else:
            raise ValueError(f"Cannot traverse mutation path {path!r} through a scalar.")
    return current


def _resolve_parent(document: Any, path: str) -> tuple[Any, str]:
    parts = _decode_pointer(path)
    if not parts:
        raise ValueError("Mutation cannot replace the document root.")
    parent = document
    for part in parts[:-1]:
        if isinstance(parent, list):
            parent = parent[int(part)]
        elif isinstance(parent, dict):
            parent = parent[part]
        else:
            raise ValueError(f"Cannot traverse mutation path {path!r} through a scalar.")
    return parent, parts[-1]


def _apply_mutation(document: dict[str, Any], mutation: dict[str, Any]) -> None:
    operation = mutation.get("op")
    path = mutation.get("path")
    if operation not in ALLOWED_MUTATION_OPERATIONS:
        raise ValueError(f"Unsupported mutation operation: {operation!r}")
    if not isinstance(path, str):
        raise ValueError("Mutation path must be a string.")

    if operation == "append":
        target = _resolve_pointer(document, path)
        if not isinstance(target, list):
            raise ValueError(f"append target is not a list: {path}")
        target.append(copy.deepcopy(mutation.get("value")))
        return
    if operation == "append_text":
        parent, key = _resolve_parent(document, path)
        value = mutation.get("value")
        if not isinstance(parent, dict) or not isinstance(parent.get(key), str):
            raise ValueError(f"append_text target is not a string: {path}")
        if not isinstance(value, str):
            raise ValueError("append_text value must be a string.")
        parent[key] += value
        return
    if operation == "filter_equal":
        target = _resolve_pointer(document, path)
        if not isinstance(target, list):
            raise ValueError(f"filter_equal target is not a list: {path}")
        key = mutation.get("key")
        if not isinstance(key, str):
            raise ValueError("filter_equal key must be a string.")
        expected = mutation.get("value")
        target[:] = [
            item for item in target if isinstance(item, dict) and item.get(key) == expected
        ]
        return
    if operation == "slice":
        target = _resolve_pointer(document, path)
        if not isinstance(target, list):
            raise ValueError(f"slice target is not a list: {path}")
        start = mutation.get("start", 0)
        stop = mutation.get("stop")
        if isinstance(start, bool) or not isinstance(start, int):
            raise ValueError("slice start must be an integer.")
        if stop is not None and (isinstance(stop, bool) or not isinstance(stop, int)):
            raise ValueError("slice stop must be an integer or null.")
        target[:] = target[start:stop]
        return

    parent, key = _resolve_parent(document, path)
    if isinstance(parent, list):
        index = int(key)
        if operation == "remove":
            parent.pop(index)
        elif operation == "replace":
            parent[index] = copy.deepcopy(mutation.get("value"))
        else:
            raise ValueError(f"Operation {operation!r} is invalid for a list item.")
        return
    if not isinstance(parent, dict):
        raise ValueError(f"Mutation parent is not an object or array: {path}")
    if operation == "remove":
        if key not in parent:
            raise ValueError(f"remove path does not exist: {path}")
        del parent[key]
    elif operation == "replace":
        if key not in parent:
            raise ValueError(f"replace path does not exist: {path}")
        parent[key] = copy.deepcopy(mutation.get("value"))


def materialize_fixture(corpus: dict[str, Any], fixture: dict[str, Any]) -> dict[str, Any]:
    trajectory = copy.deepcopy(corpus["base_trajectory"])
    for mutation in fixture.get("mutations", []):
        _apply_mutation(trajectory, mutation)
    return trajectory


def fixture_definition_sha256(
    manifest: dict[str, Any],
    corpus: dict[str, Any],
    fixture: dict[str, Any],
) -> str:
    """Hash the exact effective review unit, not only its compact mutation."""
    task_id = corpus["task_id"]
    task_contract = manifest["tasks"][task_id]
    review_contract = {
        key: task_contract[key] for key in REVIEW_TASK_CONTRACT_KEYS
    }
    return canonical_sha256(
        {
            "contract_set": manifest["contract_set"],
            "contract_set_version": manifest["contract_set_version"],
            "component_weights": manifest["component_weights"],
            "task_id": task_id,
            "fixture_schema_version": corpus["fixture_schema_version"],
            "corpus_scorer_version": corpus["scorer_version"],
            "corpus_ground_truth_sha256": corpus["ground_truth_sha256"],
            "task_contract": review_contract,
            "materialized_trajectory": materialize_fixture(corpus, fixture),
            "fixture": fixture,
        }
    )


def _import_callable(specification: str) -> Callable[..., Any]:
    if not isinstance(specification, str) or ":" not in specification:
        raise ValueError(f"Invalid callable specification: {specification!r}")
    module_name, attribute_name = specification.split(":", 1)
    module = importlib.import_module(module_name)
    candidate = getattr(module, attribute_name)
    if not callable(candidate):
        raise TypeError(f"Contract target is not callable: {specification}")
    return candidate


def score_materialized_fixture(
    task_id: str,
    trajectory: dict[str, Any],
    *,
    manifest: dict[str, Any] | None = None,
) -> dict[str, Any]:
    manifest = manifest or load_scorer_contract_manifest()
    task_contract = manifest["tasks"][task_id]
    score_function = _import_callable(task_contract["scorer_callable"])
    return score_function(
        final_answer=trajectory["final_answer"],
        transcript=trajectory["transcript"],
        ground_truth_path=str(_repo_path(task_contract["ground_truth_path"])),
    )


def _walk_strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for nested in value.values():
            yield from _walk_strings(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _walk_strings(nested)


def _rubric_component_weights(rubric: dict[str, Any]) -> dict[str, float]:
    weights: dict[str, float] = {}
    for component in rubric.get("rubric", {}).get("children", []):
        children = component.get("children", [])
        categories = {
            child.get("category") for child in children if isinstance(child, dict)
        }
        if len(categories) == 1:
            category = next(iter(categories))
            if isinstance(category, str):
                weights[category] = float(component["weight"])
    return weights


def validate_contract_bundle() -> list[str]:
    """Validate structure, hashes, bindings, labels, and hygiene without jsonschema."""
    errors: list[str] = []
    try:
        manifest = load_scorer_contract_manifest()
    except Exception as exc:
        return [f"manifest load failed: {exc}"]

    if not _SEMVER.fullmatch(str(manifest.get("contract_schema_version", ""))):
        errors.append("manifest contract_schema_version must be SemVer")
    if not _SEMVER.fullmatch(str(manifest.get("contract_set_version", ""))):
        errors.append("manifest contract_set_version must be SemVer")
    if manifest.get("contract_set") != "p1_wet_lab":
        errors.append("manifest contract_set must be p1_wet_lab")
    if manifest.get("status") != "development_scorer_conformance":
        errors.append("manifest status must be development_scorer_conformance")
    review_status = manifest.get("review_status")
    if review_status not in {PENDING_REVIEW_STATUS, APPROVED_REVIEW_STATUS}:
        errors.append("manifest review_status is invalid")
    contract_is_approved = review_status == APPROVED_REVIEW_STATUS
    if manifest.get("promotion_eligible") is not contract_is_approved:
        errors.append("manifest promotion_eligible must match review_status")

    weights = manifest.get("component_weights")
    if not isinstance(weights, dict) or set(weights) != set(WEIGHTED_COMPONENTS):
        errors.append("manifest component_weights has the wrong keys")
        weights = {}
    elif not math.isclose(sum(float(weights[key]) for key in weights), 1.0, abs_tol=1e-12):
        errors.append("manifest component_weights must sum to 1")

    families = manifest.get("required_fixture_families")
    if families != list(REQUIRED_FIXTURE_FAMILIES):
        errors.append("manifest required_fixture_families is not the frozen P2a sequence")
    tasks = manifest.get("tasks")
    if not isinstance(tasks, dict) or tuple(tasks) != P1_TASK_IDS:
        errors.append("manifest tasks must contain the five ordered P1 task ids")
        return errors

    fixture_ids: set[str] = set()
    fixture_hashes: dict[str, str] = {}
    fixture_review_metadata: dict[str, tuple[str, Any, Any]] = {}
    for task_id in P1_TASK_IDS:
        task_contract = tasks[task_id]
        prefix = f"{task_id}: "
        if not _SEMVER.fullmatch(str(task_contract.get("scorer_version", ""))):
            errors.append(prefix + "scorer_version must be SemVer")
        if task_contract.get("report_field_count") != len(
            task_contract.get("report_fields", [])
        ):
            errors.append(prefix + "report_field_count does not match report_fields")
        policy = task_contract.get("evidence_policy", {})
        for key in (
            "request_and_output_required",
            "output_authoritative",
            "causal_order_required",
        ):
            if policy.get(key) is not True:
                errors.append(prefix + f"evidence_policy.{key} must be true")

        for callable_key, required_parameters in (
            ("scorer_callable", {"final_answer", "transcript", "ground_truth_path"}),
            ("inspect_builder", set()),
        ):
            try:
                callable_object = _import_callable(task_contract[callable_key])
                parameters = set(inspect.signature(callable_object).parameters)
                if not required_parameters <= parameters:
                    errors.append(prefix + f"{callable_key} has an incompatible signature")
            except Exception as exc:
                errors.append(prefix + f"{callable_key} import failed: {exc}")

        artifact_paths: dict[str, Path] = {}
        for artifact in ("scorer_source", "ground_truth", "rubric", "fixture"):
            try:
                artifact_path = _repo_path(task_contract[f"{artifact}_path"])
                if not artifact_path.is_file():
                    errors.append(prefix + f"{artifact}_path does not exist")
                    continue
                artifact_paths[artifact] = artifact_path
                if sha256_file(artifact_path) != task_contract.get(f"{artifact}_sha256"):
                    errors.append(prefix + f"{artifact}_sha256 mismatch")
            except Exception as exc:
                errors.append(prefix + f"{artifact}_path invalid: {exc}")

        if "ground_truth" not in artifact_paths or "rubric" not in artifact_paths:
            continue
        try:
            ground_truth = _load_json(artifact_paths["ground_truth"])
            rubric = _load_json(artifact_paths["rubric"])
        except Exception as exc:
            errors.append(prefix + f"ground truth or rubric load failed: {exc}")
            continue
        if ground_truth.get("task_id") != task_id or rubric.get("task_id") != task_id:
            errors.append(prefix + "task_id mismatch in ground truth or rubric")
        decision_ids = [point.get("id") for point in ground_truth.get("decision_points", [])]
        if decision_ids != task_contract.get("decision_point_ids"):
            errors.append(prefix + "decision_point_ids do not match ground truth")
        if weights and _rubric_component_weights(rubric) != weights:
            errors.append(prefix + "rubric component weights do not match manifest")

        if "fixture" not in artifact_paths:
            continue
        try:
            corpus = _load_json(artifact_paths["fixture"])
        except Exception as exc:
            errors.append(prefix + f"fixture corpus load failed: {exc}")
            continue
        if corpus.get("task_id") != task_id:
            errors.append(prefix + "fixture task_id mismatch")
        if corpus.get("scorer_version") != task_contract.get("scorer_version"):
            errors.append(prefix + "fixture scorer_version mismatch")
        if corpus.get("ground_truth_sha256") != task_contract.get("ground_truth_sha256"):
            errors.append(prefix + "fixture ground_truth_sha256 mismatch")
        if corpus.get("review_status") != review_status:
            errors.append(prefix + "fixture corpus review_status must match manifest")
        if corpus.get("promotion_eligible") is not contract_is_approved:
            errors.append(prefix + "fixture corpus promotion state must match manifest")
        if not isinstance(corpus.get("base_trajectory"), dict):
            errors.append(prefix + "base_trajectory is missing")

        task_fixtures = corpus.get("fixtures")
        if not isinstance(task_fixtures, list):
            errors.append(prefix + "fixtures must be a list")
            continue
        if len(task_fixtures) != task_contract.get("fixture_count"):
            errors.append(prefix + "fixture_count mismatch")
        if [fixture.get("case_family") for fixture in task_fixtures] != list(
            REQUIRED_FIXTURE_FAMILIES
        ):
            errors.append(prefix + "fixture families are incomplete or out of order")

        decision_id_set = set(decision_ids)
        for fixture in task_fixtures:
            fixture_id = fixture.get("fixture_id")
            fixture_prefix = prefix + f"{fixture_id}: "
            if not isinstance(fixture_id, str) or not fixture_id.startswith(task_id + "."):
                errors.append(fixture_prefix + "invalid fixture_id")
            elif fixture_id in fixture_ids:
                errors.append(fixture_prefix + "duplicate fixture_id")
            else:
                fixture_ids.add(fixture_id)
                try:
                    fixture_hashes[fixture_id] = fixture_definition_sha256(
                        manifest,
                        corpus,
                        fixture,
                    )
                except Exception as exc:
                    errors.append(fixture_prefix + f"review hash failed: {exc}")
            if fixture.get("task_id") != task_id:
                errors.append(fixture_prefix + "task_id mismatch")
            expected_validity = fixture.get("expected_validity")
            if expected_validity not in {"valid", "invalid"}:
                errors.append(fixture_prefix + "expected_validity must be valid or invalid")
            if fixture.get("case_family") in {"canonical_valid", "alternative_valid"}:
                if expected_validity != "valid":
                    errors.append(fixture_prefix + "valid family must be labelled valid")
            elif fixture.get("case_family") != "retry" and expected_validity != "invalid":
                errors.append(fixture_prefix + "invalid family must be labelled invalid")

            annotation = fixture.get("annotation", {})
            label_status = annotation.get("label_status")
            reviewer = annotation.get("reviewer")
            reviewed_at = annotation.get("reviewed_at")
            if annotation.get("origin") != "ai_assisted_draft":
                errors.append(fixture_prefix + "annotation origin must remain ai_assisted_draft")
            if label_status not in {PENDING_REVIEW_STATUS, APPROVED_REVIEW_STATUS}:
                errors.append(fixture_prefix + "annotation label_status is invalid")
            elif isinstance(fixture_id, str):
                fixture_review_metadata[fixture_id] = (
                    label_status,
                    reviewer,
                    reviewed_at,
                )
            if label_status == PENDING_REVIEW_STATUS:
                if reviewer is not None or reviewed_at is not None:
                    errors.append(fixture_prefix + "pending annotation names a reviewer or date")
            elif not _is_review_identity(reviewer) or not _is_review_timestamp(
                reviewed_at
            ):
                errors.append(
                    fixture_prefix
                    + "approved annotation needs a reviewer and RFC 3339 timestamp"
                )
            if contract_is_approved and label_status != APPROVED_REVIEW_STATUS:
                errors.append(fixture_prefix + "promoted corpus contains a pending annotation")
            if not str(annotation.get("rationale", "")).strip():
                errors.append(fixture_prefix + "annotation rationale is required")

            mutations = fixture.get("mutations")
            if not isinstance(mutations, list):
                errors.append(fixture_prefix + "mutations must be a list")
                continue
            for mutation in mutations:
                if not isinstance(mutation, dict) or mutation.get("op") not in ALLOWED_MUTATION_OPERATIONS:
                    errors.append(fixture_prefix + "contains an invalid mutation")
            expected = fixture.get("expected_scores")
            if not isinstance(expected, dict) or set(expected) != set(SCORE_COMPONENTS) | {
                "decision_scores"
            }:
                errors.append(fixture_prefix + "expected_scores has the wrong keys")
                continue
            if set(expected.get("decision_scores", {})) != decision_id_set:
                errors.append(fixture_prefix + "expected decision score keys mismatch")
            numeric_values = [expected.get(key) for key in SCORE_COMPONENTS]
            numeric_values.extend(expected.get("decision_scores", {}).values())
            if any(
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(float(value))
                or not 0.0 <= float(value) <= 1.0
                for value in numeric_values
            ):
                errors.append(fixture_prefix + "expected scores must be finite values in [0,1]")
                continue
            recomputed = sum(
                float(weights[component]) * float(expected[component])
                for component in WEIGHTED_COMPONENTS
            )
            if not math.isclose(recomputed, float(expected["overall"]), abs_tol=1e-12):
                errors.append(fixture_prefix + "overall does not match component weights")
            if expected_validity == "valid" and float(expected["task_success"]) != 1.0:
                errors.append(fixture_prefix + "valid fixture must have task_success=1")
            if fixture.get("case_family") in {"forged", "partial", "orphan"} and any(
                float(expected[key]) != 0.0 for key in SCORE_COMPONENTS
            ):
                errors.append(fixture_prefix + "forged/partial/orphan fixture must fail closed")
            try:
                materialize_fixture(corpus, fixture)
            except Exception as exc:
                errors.append(fixture_prefix + f"materialization failed: {exc}")

        for value in _walk_strings(corpus):
            if _PERSONAL_PATH.search(value):
                errors.append(prefix + "fixture corpus contains a personal path")
            if _SCHEDULER_ID.search(value):
                errors.append(prefix + "fixture corpus contains a scheduler identifier")
            if _SECRET.search(value):
                errors.append(prefix + "fixture corpus contains a possible secret")

    expected_fixture_count = len(P1_TASK_IDS) * len(REQUIRED_FIXTURE_FAMILIES)
    if len(fixture_ids) != expected_fixture_count:
        errors.append(
            f"contract set has {len(fixture_ids)} unique fixtures; expected {expected_fixture_count}"
        )

    try:
        review = load_review_manifest()
    except Exception as exc:
        errors.append(f"review manifest load failed: {exc}")
    else:
        if review.get("contract_set") != manifest.get("contract_set"):
            errors.append("review manifest contract_set mismatch")
        if not _SEMVER.fullmatch(str(review.get("review_schema_version", ""))):
            errors.append("review manifest review_schema_version must be SemVer")
        if review.get("status") != review_status:
            errors.append("review manifest status must match contract manifest")
        if review.get("promotion_eligible") is not contract_is_approved:
            errors.append("review manifest promotion state must match contract manifest")
        if review.get("required_fixture_count") != expected_fixture_count:
            errors.append("review manifest required_fixture_count mismatch")
        review_reviewer = review.get("reviewer")
        review_date = review.get("reviewed_at")
        if contract_is_approved:
            if not _is_review_identity(review_reviewer) or not _is_review_timestamp(
                review_date
            ):
                errors.append(
                    "approved review manifest needs a reviewer and RFC 3339 timestamp"
                )
        elif review_reviewer is not None or review_date is not None:
            errors.append("pending review manifest must not name a final reviewer or date")

        approvals = review.get("approvals")
        approval_decisions: dict[str, str] = {}
        if not isinstance(approvals, list):
            errors.append("review manifest approvals must be a list")
            approvals = []
        for index, approval in enumerate(approvals):
            approval_prefix = f"review approval {index}: "
            if not isinstance(approval, dict):
                errors.append(approval_prefix + "entry must be an object")
                continue
            fixture_id = approval.get("fixture_id")
            if not isinstance(fixture_id, str) or fixture_id not in fixture_hashes:
                errors.append(approval_prefix + "fixture_id is not in the contract corpus")
                continue
            if fixture_id in approval_decisions:
                errors.append(approval_prefix + "fixture_id is duplicated")
                continue
            decision = approval.get("decision")
            if decision not in {"approved", "rejected"}:
                errors.append(approval_prefix + "decision must be approved or rejected")
                continue
            approval_decisions[fixture_id] = decision
            if approval.get("fixture_definition_sha256") != fixture_hashes[fixture_id]:
                errors.append(approval_prefix + "fixture definition hash is stale or invalid")
            approval_reviewer = approval.get("reviewer")
            approval_date = approval.get("reviewed_at")
            if not _is_review_identity(approval_reviewer) or not _is_review_timestamp(
                approval_date
            ):
                errors.append(
                    approval_prefix
                    + "reviewer and RFC 3339 reviewed_at are required"
                )
            label_status, annotation_reviewer, annotation_date = (
                fixture_review_metadata.get(fixture_id, (None, None, None))
            )
            if decision == "approved" and label_status != APPROVED_REVIEW_STATUS:
                errors.append(approval_prefix + "approved decision has a pending fixture label")
            if decision == "approved" and (
                approval_reviewer != annotation_reviewer
                or approval_date != annotation_date
            ):
                errors.append(
                    approval_prefix + "provenance does not match the approved annotation"
                )
            if decision == "rejected" and label_status == APPROVED_REVIEW_STATUS:
                errors.append(approval_prefix + "rejected decision has an approved fixture label")
            if contract_is_approved and (
                approval_reviewer != review_reviewer or approval_date != review_date
            ):
                errors.append(
                    approval_prefix + "provenance does not match the final review manifest"
                )

        for fixture_id, (label_status, _, _) in fixture_review_metadata.items():
            if (
                label_status == APPROVED_REVIEW_STATUS
                and approval_decisions.get(fixture_id) != "approved"
            ):
                errors.append(f"{fixture_id}: approved label lacks a hash-bound approval")
        if contract_is_approved and (
            set(approval_decisions) != fixture_ids
            or any(decision != "approved" for decision in approval_decisions.values())
        ):
            errors.append("promoted contract requires one current approval per fixture")

    for schema_path in manifest.get("schema_paths", {}).values():
        try:
            _load_json(_repo_path(schema_path))
        except Exception as exc:
            errors.append(f"schema path invalid: {schema_path}: {exc}")
    return errors


def run_scorer_regression(*, tolerance: float = 1e-12) -> list[str]:
    """Run all checked-in fixture vectors against their pinned scorer callables."""
    errors = validate_contract_bundle()
    if errors:
        return errors
    manifest = load_scorer_contract_manifest()
    for task_id in P1_TASK_IDS:
        corpus = load_task_fixture_corpus(task_id)
        for fixture in corpus["fixtures"]:
            fixture_id = fixture["fixture_id"]
            trajectory = materialize_fixture(corpus, fixture)
            actual = score_materialized_fixture(task_id, trajectory, manifest=manifest)
            expected = fixture["expected_scores"]
            for component in SCORE_COMPONENTS:
                if not math.isclose(
                    float(actual[component]),
                    float(expected[component]),
                    abs_tol=tolerance,
                ):
                    errors.append(
                        f"{fixture_id}: {component}={actual[component]!r}; "
                        f"expected {expected[component]!r}"
                    )
            actual_decisions = actual.get("decision_scores", {})
            for decision_id, expected_value in expected["decision_scores"].items():
                actual_value = actual_decisions.get(decision_id)
                if actual_value is None or not math.isclose(
                    float(actual_value),
                    float(expected_value),
                    abs_tol=tolerance,
                ):
                    errors.append(
                        f"{fixture_id}: decision {decision_id}={actual_value!r}; "
                        f"expected {expected_value!r}"
                    )
    return errors


def review_progress() -> dict[str, Any]:
    manifest = load_scorer_contract_manifest()
    review = load_review_manifest()
    required = len(P1_TASK_IDS) * len(REQUIRED_FIXTURE_FAMILIES)
    approvals = review.get("approvals", [])
    fixture_state: dict[str, tuple[str, Any, Any, Any]] = {}
    corpora_are_approved = True
    for task_id in P1_TASK_IDS:
        corpus = load_task_fixture_corpus(task_id)
        corpora_are_approved = bool(
            corpora_are_approved
            and corpus.get("review_status") == APPROVED_REVIEW_STATUS
            and corpus.get("promotion_eligible") is True
        )
        for fixture in corpus.get("fixtures", []):
            fixture_id = fixture.get("fixture_id")
            if isinstance(fixture_id, str):
                fixture_state[fixture_id] = (
                    fixture_definition_sha256(manifest, corpus, fixture),
                    fixture.get("annotation", {}).get("label_status"),
                    fixture.get("annotation", {}).get("reviewer"),
                    fixture.get("annotation", {}).get("reviewed_at"),
                )

    valid_approvals: set[str] = set()
    seen_approval_ids: set[str] = set()
    if isinstance(approvals, list):
        for approval in approvals:
            if not isinstance(approval, dict):
                continue
            fixture_id = approval.get("fixture_id")
            if not isinstance(fixture_id, str) or fixture_id in seen_approval_ids:
                continue
            seen_approval_ids.add(fixture_id)
            expected_state = fixture_state.get(fixture_id)
            if expected_state is None:
                continue
            expected_hash, label_status, annotation_reviewer, annotation_date = (
                expected_state
            )
            if (
                approval.get("decision") == "approved"
                and approval.get("fixture_definition_sha256") == expected_hash
                and label_status == APPROVED_REVIEW_STATUS
                and _is_review_identity(approval.get("reviewer"))
                and _is_review_timestamp(approval.get("reviewed_at"))
                and approval.get("reviewer") == annotation_reviewer
                and approval.get("reviewed_at") == annotation_date
            ):
                valid_approvals.add(fixture_id)
    final_reviewer = review.get("reviewer")
    final_reviewed_at = review.get("reviewed_at")
    final_provenance_matches = bool(
        _is_review_identity(final_reviewer)
        and _is_review_timestamp(final_reviewed_at)
        and isinstance(approvals, list)
        and all(
            isinstance(approval, dict)
            and approval.get("reviewer") == final_reviewer
            and approval.get("reviewed_at") == final_reviewed_at
            for approval in approvals
        )
    )
    return {
        "contract_set": manifest["contract_set"],
        "required": required,
        "approved": len(valid_approvals),
        "pending": required - len(valid_approvals),
        "promotion_ready": bool(
            manifest.get("promotion_eligible") is True
            and manifest.get("review_status") == APPROVED_REVIEW_STATUS
            and review.get("promotion_eligible") is True
            and review.get("status") == APPROVED_REVIEW_STATUS
            and final_provenance_matches
            and corpora_are_approved
            and len(fixture_state) == required
            and len(valid_approvals) == required
        ),
    }
