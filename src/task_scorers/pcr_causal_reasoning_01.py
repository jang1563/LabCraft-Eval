"""Strict, versioned scorer for the P2b PCR causal-reasoning task."""

from __future__ import annotations

import json
import math
from pathlib import Path
import re
from typing import Any, Iterable

from src.environment.operations import run_gel, run_pcr
from src.environment.state import create_lab_state


SCORER_VERSION = "0.1.0"
SCORER_NAME = "pcr_causal_reasoning_01"
REPORT_FIELDS = (
    "Case",
    "Observed phenotype",
    "Primary diagnosis",
    "Causal parameter",
    "Corrective setting",
    "Counterfactual setting",
    "Counterfactual prediction",
    "Verification",
)
DECISION_IDS = (
    "case_specific_diagnosis",
    "causal_parameter_identification",
    "one_variable_causal_correction",
    "accepted_corrective_setting",
)
EXPERIMENTAL_TOOLS = {"run_pcr", "run_gel"}
CONFIG_FIELDS = (
    "polymerase_name",
    "additive",
    "extension_seconds",
    "cycle_count",
)
PCR_REQUIRED_OUTPUT_FIELDS = {
    "status",
    "reaction_id",
    "normalized_polymerase_name",
    "normalized_additive",
    "extension_seconds",
    "cycle_count",
    "target_size_bp",
    "visible_bands_bp",
    "smear_present",
}
GEL_REQUIRED_OUTPUT_FIELDS = PCR_REQUIRED_OUTPUT_FIELDS | {"gel_id"}
PCR_TO_GEL_STATUS = {
    "clean_target_band": "single_clean_target_band",
    "low_yield_target_band": "faint_target_band",
    "truncated_product": "wrong_size_band",
    "gc_rich_failure": "no_visible_product",
    "nonspecific_amplification": "multiple_bands_or_smear",
}


def _tool_name(value: Any) -> str:
    if value is None:
        return ""
    name = str(value)
    if name.endswith("_tool_impl"):
        name = name[: -len("_tool_impl")]
    return name


def _dict_value(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except Exception:
            return {}
        return dict(parsed) if isinstance(parsed, dict) else {}
    return {}


def _call_name_and_arguments(call: Any) -> tuple[str, dict[str, Any]]:
    if isinstance(call, dict):
        function = call.get("function")
        if isinstance(function, dict):
            return _tool_name(function.get("name")), _dict_value(function.get("arguments"))
        return _tool_name(function or call.get("name")), _dict_value(call.get("arguments"))
    function = getattr(call, "function", None)
    if function is not None and not isinstance(function, str):
        return _tool_name(getattr(function, "name", None)), _dict_value(
            getattr(function, "arguments", None)
        )
    return _tool_name(function or getattr(call, "name", None)), _dict_value(
        getattr(call, "arguments", None)
    )


def _normalize_calls(transcript: Iterable[Any]) -> list[dict[str, Any]]:
    """Preserve request/output separation and causal event order."""
    calls: list[dict[str, Any]] = []
    by_id: dict[str, dict[str, Any]] = {}
    event_index = 0

    def merge(event: dict[str, Any]) -> None:
        call_id = event.get("call_id")
        record = by_id.get(call_id) if isinstance(call_id, str) and call_id else None
        if record is None:
            record = {
                "tool_name": event.get("tool_name", ""),
                "call_id": call_id,
                "request_arguments": {},
                "output": {},
                "request_observed": False,
                "output_observed": False,
                "request_count": 0,
                "output_count": 0,
                "request_order": None,
                "output_order": None,
            }
            calls.append(record)
            if isinstance(call_id, str) and call_id:
                by_id[call_id] = record
        if event.get("tool_name"):
            record["tool_name"] = _tool_name(event["tool_name"])
        if event.get("request_observed"):
            record["request_count"] += 1
            record["request_observed"] = True
            record["request_arguments"] = _dict_value(event.get("request_arguments"))
            if record["request_order"] is None:
                record["request_order"] = event["order"]
        if event.get("output_observed"):
            record["output_count"] += 1
            record["output_observed"] = True
            record["output"] = _dict_value(event.get("output"))
            record["output_order"] = event["order"]

    for item in transcript:
        if isinstance(item, dict) and item.get("type") == "tool_call":
            has_content = item.get("content") is not None
            merge(
                {
                    "tool_name": item.get("tool_name") or item.get("function"),
                    "call_id": item.get("call_id") or item.get("id"),
                    "request_observed": True,
                    "request_arguments": item.get("arguments"),
                    "output_observed": has_content,
                    "output": item.get("content"),
                    "order": event_index,
                }
            )
            event_index += 1
            continue

        if isinstance(item, dict) and item.get("tool_calls"):
            for call in item.get("tool_calls", []):
                name, arguments = _call_name_and_arguments(call)
                merge(
                    {
                        "tool_name": name,
                        "call_id": call.get("id") if isinstance(call, dict) else None,
                        "request_observed": True,
                        "request_arguments": arguments,
                        "output_observed": False,
                        "order": event_index,
                    }
                )
                event_index += 1
            continue

        if isinstance(item, dict) and item.get("role") == "tool":
            merge(
                {
                    "tool_name": item.get("function") or item.get("name"),
                    "call_id": item.get("tool_call_id"),
                    "request_observed": False,
                    "output_observed": True,
                    "output": item.get("content"),
                    "order": event_index,
                }
            )
            event_index += 1
            continue

        role = getattr(item, "role", None)
        if role == "tool":
            merge(
                {
                    "tool_name": getattr(item, "function", None)
                    or getattr(item, "name", None),
                    "call_id": getattr(item, "tool_call_id", None),
                    "request_observed": False,
                    "output_observed": True,
                    "output": getattr(item, "content", None),
                    "order": event_index,
                }
            )
            event_index += 1
            continue

        tool_calls = getattr(item, "tool_calls", None)
        if tool_calls:
            for call in tool_calls:
                name, arguments = _call_name_and_arguments(call)
                merge(
                    {
                        "tool_name": name,
                        "call_id": getattr(call, "id", None),
                        "request_observed": True,
                        "request_arguments": arguments,
                        "output_observed": False,
                        "order": event_index,
                    }
                )
                event_index += 1
    return calls


def _parse_report(final_answer: str) -> dict[str, str] | None:
    if not isinstance(final_answer, str):
        return None
    normalized = final_answer.rstrip("\r\n")
    lines = normalized.splitlines()
    if len(lines) != len(REPORT_FIELDS):
        return None
    parsed: dict[str, str] = {}
    for line, field in zip(lines, REPORT_FIELDS):
        prefix = field + ": "
        if not line.startswith(prefix):
            return None
        value = line[len(prefix) :]
        if not value or value != value.strip():
            return None
        parsed[field] = value
    return parsed


def _parse_setting(value: str) -> tuple[str, str] | None:
    match = re.fullmatch(r"([a-z_]+)=([^=]+)", value)
    if not match:
        return None
    parameter = match.group(1)
    setting = match.group(2).strip()
    if parameter not in CONFIG_FIELDS or not setting:
        return None
    return parameter, setting


def _canonical_polymerase(value: Any) -> str:
    text = str(value or "").strip()
    normalized = re.sub(r"[^a-z0-9]+", " ", text.casefold()).strip()
    if "q5" in normalized:
        return "Q5 High-Fidelity DNA polymerase"
    if "phusion" in normalized:
        return "Phusion High-Fidelity DNA polymerase"
    if re.search(r"\btaq\b", normalized):
        return "Taq DNA polymerase"
    return text


def _canonical_additive(value: Any) -> str:
    text = str(value or "").strip()
    normalized = text.casefold()
    if "dmso" in normalized:
        return "DMSO"
    if "betaine" in normalized:
        return "Betaine"
    if normalized in {"none", "no additive", "not used"}:
        return "none"
    return text


def _integer(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        converted = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(converted) or not converted.is_integer():
        return None
    return int(converted)


def _nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _normalize_configuration(output: dict[str, Any]) -> dict[str, Any] | None:
    if not PCR_REQUIRED_OUTPUT_FIELDS <= set(output):
        return None
    extension = _integer(output.get("extension_seconds"))
    cycles = _integer(output.get("cycle_count"))
    if extension is None or cycles is None:
        return None
    return {
        "polymerase_name": _canonical_polymerase(output.get("normalized_polymerase_name")),
        "additive": _canonical_additive(output.get("normalized_additive")),
        "extension_seconds": extension,
        "cycle_count": cycles,
    }


def _normalize_setting(parameter: str, value: Any) -> Any:
    if parameter == "polymerase_name":
        return _canonical_polymerase(value)
    if parameter == "additive":
        return _canonical_additive(value)
    return _integer(value)


def _normalize_bands(value: Any) -> list[int] | None:
    if not isinstance(value, list):
        return None
    bands = [_integer(item) for item in value]
    if any(item is None for item in bands):
        return None
    return [int(item) for item in bands]


def _complete_linked_call(call: dict[str, Any], required: set[str]) -> bool:
    request_order = call.get("request_order")
    output_order = call.get("output_order")
    return (
        call.get("request_observed") is True
        and call.get("output_observed") is True
        and call.get("request_count") == 1
        and call.get("output_count") == 1
        and required <= set(call.get("output", {}))
        and request_order is not None
        and output_order is not None
        and int(request_order) <= int(output_order)
    )


def _pcr_request_matches_output(call: dict[str, Any]) -> bool:
    output_configuration = _normalize_configuration(call.get("output", {}))
    arguments = call.get("request_arguments", {})
    if output_configuration is None or not set(CONFIG_FIELDS) <= set(arguments):
        return False
    request_configuration = {
        "polymerase_name": _canonical_polymerase(arguments.get("polymerase_name")),
        "additive": _canonical_additive(arguments.get("additive")),
        "extension_seconds": _integer(arguments.get("extension_seconds")),
        "cycle_count": _integer(arguments.get("cycle_count")),
    }
    return request_configuration == output_configuration


def _gel_request_matches_output(call: dict[str, Any]) -> bool:
    requested_id = call.get("request_arguments", {}).get("reaction_id")
    return _nonempty_string(requested_id) and requested_id == call.get("output", {}).get(
        "reaction_id"
    )


def _select_final_causal_pair(
    calls: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    pcr_calls = [
        call
        for call in calls
        if _tool_name(call.get("tool_name")) == "run_pcr"
        and _complete_linked_call(call, PCR_REQUIRED_OUTPUT_FIELDS)
        and _nonempty_string(call["output"].get("reaction_id"))
        and _normalize_configuration(call["output"]) is not None
        and _pcr_request_matches_output(call)
    ]
    gels = [
        call
        for call in calls
        if _tool_name(call.get("tool_name")) == "run_gel"
        and _complete_linked_call(call, GEL_REQUIRED_OUTPUT_FIELDS)
        and _nonempty_string(call["output"].get("gel_id"))
        and _normalize_configuration(call["output"]) is not None
        and _gel_request_matches_output(call)
    ]
    for gel in sorted(gels, key=lambda call: int(call["output_order"]), reverse=True):
        reaction_id = gel["output"].get("reaction_id")
        candidates = [
            call
            for call in pcr_calls
            if call["output"].get("reaction_id") == reaction_id
            and int(call["output_order"]) < int(gel["request_order"])
        ]
        if len(candidates) == 1:
            return candidates[0], gel
    return None


def _same_condition_evidence(pcr_output: dict[str, Any], gel_output: dict[str, Any]) -> bool:
    reaction_id = pcr_output.get("reaction_id")
    pcr_target = _integer(pcr_output.get("target_size_bp"))
    gel_target = _integer(gel_output.get("target_size_bp"))
    pcr_status = pcr_output.get("status")
    pcr_bands = _normalize_bands(pcr_output.get("visible_bands_bp"))
    gel_bands = _normalize_bands(gel_output.get("visible_bands_bp"))
    pcr_smear = pcr_output.get("smear_present")
    gel_smear = gel_output.get("smear_present")
    return (
        _nonempty_string(reaction_id)
        and reaction_id == gel_output.get("reaction_id")
        and _normalize_configuration(pcr_output) == _normalize_configuration(gel_output)
        and pcr_target is not None
        and pcr_target == gel_target
        and PCR_TO_GEL_STATUS.get(pcr_status) == gel_output.get("status")
        and pcr_bands is not None
        and pcr_bands == gel_bands
        and isinstance(pcr_smear, bool)
        and pcr_smear == gel_smear
    )


def _clean_recovery(pcr_output: dict[str, Any], gel_output: dict[str, Any]) -> bool:
    bands = _normalize_bands(gel_output.get("visible_bands_bp"))
    return (
        pcr_output.get("status") == "clean_target_band"
        and gel_output.get("status") == "single_clean_target_band"
        and _integer(gel_output.get("target_size_bp")) == 2000
        and bands == [2000]
        and gel_output.get("smear_present") is False
        and _same_condition_evidence(pcr_output, gel_output)
    )


def _setting_matches_configuration(
    setting: tuple[str, str] | None,
    configuration: dict[str, Any],
) -> bool:
    if setting is None:
        return False
    parameter, raw_value = setting
    return _normalize_setting(parameter, raw_value) == configuration.get(parameter)


def _simulate_counterfactual(configuration: dict[str, Any]) -> str:
    state = create_lab_state("pcr-causal-reasoning-counterfactual", seed=0)
    reaction = run_pcr(
        state=state,
        polymerase_name=str(configuration["polymerase_name"]),
        additive=str(configuration["additive"]),
        extension_seconds=int(configuration["extension_seconds"]),
        cycle_count=int(configuration["cycle_count"]),
    )
    gel = run_gel(state=state, reaction_id=str(reaction["reaction_id"]))
    return str(gel["status"])


def _empty_score(case_id: str | None, *, evidence_gate_passed: bool = False) -> dict[str, Any]:
    return {
        "overall": 0.0,
        "task_success": 0.0,
        "decision_quality": 0.0,
        "troubleshooting": 0.0,
        "efficiency": 0.0,
        "decision_scores": {decision_id: 0.0 for decision_id in DECISION_IDS},
        "scorer_name": SCORER_NAME,
        "scorer_version": SCORER_VERSION,
        "case_id": case_id,
        "evidence_gate_passed": evidence_gate_passed,
        "promotion_eligible": False,
    }


def score_pcr_causal_reasoning_trajectory(
    final_answer: str,
    transcript: Iterable[Any],
    ground_truth_path: str,
    case_id: str,
) -> dict[str, Any]:
    """Score one case with its identity bound outside the model report."""
    with Path(ground_truth_path).open(encoding="utf-8") as handle:
        ground_truth = json.load(handle)
    case = ground_truth.get("cases", {}).get(case_id)
    if not isinstance(case, dict):
        return _empty_score(case_id)

    calls = _normalize_calls(transcript)
    pair = _select_final_causal_pair(calls)
    if pair is None:
        return _empty_score(case_id)
    pcr_call, gel_call = pair
    pcr_output = pcr_call["output"]
    gel_output = gel_call["output"]
    configuration = _normalize_configuration(pcr_output)
    if configuration is None or not _same_condition_evidence(pcr_output, gel_output):
        return _empty_score(case_id)

    report = _parse_report(final_answer)
    corrective_setting = (
        _parse_setting(report["Corrective setting"]) if report is not None else None
    )
    counterfactual_setting = (
        _parse_setting(report["Counterfactual setting"]) if report is not None else None
    )
    report_case_matches = report is not None and report["Case"] == case_id

    task_success = float(
        report_case_matches
        and report["Observed phenotype"] == case["prior_observation"]["status"]
        and report["Verification"] == gel_output.get("status")
        and _setting_matches_configuration(corrective_setting, configuration)
        and _clean_recovery(pcr_output, gel_output)
    )

    diagnosis_score = float(
        report_case_matches and report["Primary diagnosis"] == case["primary_diagnosis"]
    )
    causal_parameter_score = float(
        report_case_matches and report["Causal parameter"] == case["causal_parameter"]
    )
    prior_configuration = dict(case["prior_configuration"])
    changed_fields = [
        field
        for field in CONFIG_FIELDS
        if configuration.get(field) != prior_configuration.get(field)
    ]
    one_variable_score = float(
        report_case_matches and changed_fields == [case["causal_parameter"]]
    )
    accepted_values = {
        _normalize_setting(case["causal_parameter"], value)
        for value in case["acceptable_corrective_values"]
    }
    accepted_setting_score = float(
        corrective_setting is not None
        and corrective_setting[0] == case["causal_parameter"]
        and _setting_matches_configuration(corrective_setting, configuration)
        and configuration[case["causal_parameter"]] in accepted_values
    )
    decision_scores = {
        "case_specific_diagnosis": diagnosis_score,
        "causal_parameter_identification": causal_parameter_score,
        "one_variable_causal_correction": one_variable_score,
        "accepted_corrective_setting": accepted_setting_score,
    }

    experimental_calls = [
        call for call in calls if _tool_name(call.get("tool_name")) in EXPERIMENTAL_TOOLS
    ]
    pcr_calls = [
        call for call in experimental_calls if _tool_name(call.get("tool_name")) == "run_pcr"
    ]
    gel_calls = [
        call for call in experimental_calls if _tool_name(call.get("tool_name")) == "run_gel"
    ]
    prior_rerun = any(
        _normalize_configuration(call.get("output", {})) == prior_configuration
        for call in pcr_calls
        if call.get("output_observed") is True
    )

    troubleshooting = 0.0
    counterfactual_configuration: dict[str, Any] | None = None
    allowed_counterfactuals = case.get("acceptable_counterfactual_values", {})
    if report_case_matches and counterfactual_setting is not None:
        parameter, raw_value = counterfactual_setting
        normalized_value = _normalize_setting(parameter, raw_value)
        allowed_values = {
            _normalize_setting(parameter, value)
            for value in allowed_counterfactuals.get(parameter, [])
        }
        if (
            parameter != case["causal_parameter"]
            and normalized_value in allowed_values
            and normalized_value != prior_configuration.get(parameter)
        ):
            counterfactual_configuration = dict(prior_configuration)
            counterfactual_configuration[parameter] = normalized_value
            simulated_status = _simulate_counterfactual(counterfactual_configuration)
            troubleshooting = float(
                report["Counterfactual prediction"] == simulated_status
                and simulated_status == case["counterfactual_gel_status"]
            )

    counterfactual_executed = (
        counterfactual_configuration is not None
        and any(
            _normalize_configuration(call.get("output", {})) == counterfactual_configuration
            for call in pcr_calls
            if call.get("output_observed") is True
        )
    )
    if prior_rerun:
        decision_scores = {decision_id: 0.0 for decision_id in DECISION_IDS}
        troubleshooting = 0.0
    elif counterfactual_executed:
        troubleshooting = 0.0

    decision_quality = sum(decision_scores.values()) / float(len(DECISION_IDS))
    efficiency = float(
        len(experimental_calls) == 2
        and len(pcr_calls) == 1
        and len(gel_calls) == 1
        and pcr_calls[0] is pcr_call
        and gel_calls[0] is gel_call
    )
    overall = round(
        0.4 * task_success
        + 0.3 * decision_quality
        + 0.2 * troubleshooting
        + 0.1 * efficiency,
        12,
    )
    return {
        "overall": overall,
        "task_success": task_success,
        "decision_quality": decision_quality,
        "troubleshooting": troubleshooting,
        "efficiency": efficiency,
        "decision_scores": decision_scores,
        "scorer_name": SCORER_NAME,
        "scorer_version": SCORER_VERSION,
        "case_id": case_id,
        "evidence_gate_passed": True,
        "selected_reaction_id": pcr_output.get("reaction_id"),
        "promotion_eligible": False,
    }


def build_pcr_causal_reasoning_trajectory_scorer():
    """Build the Inspect scorer while preserving case identity from sample metadata."""
    from inspect_ai.scorer import Score, Target, mean, scorer

    @scorer(
        metrics={
            "overall": [mean()],
            "task_success": [mean()],
            "decision_quality": [mean()],
            "troubleshooting": [mean()],
            "efficiency": [mean()],
        }
    )
    def _scorer():
        async def score(state, target: Target):
            final_answer = ""
            if getattr(state, "output", None) is not None:
                final_answer = getattr(state.output, "completion", "") or ""
            metadata = getattr(state, "metadata", {}) or {}
            values = score_pcr_causal_reasoning_trajectory(
                final_answer=final_answer,
                transcript=getattr(state, "messages", []),
                ground_truth_path=target.text,
                case_id=str(metadata.get("case_id", "")),
            )
            return Score(
                value={
                    "overall": values["overall"],
                    "task_success": values["task_success"],
                    "decision_quality": values["decision_quality"],
                    "troubleshooting": values["troubleshooting"],
                    "efficiency": values["efficiency"],
                },
                answer=final_answer[:500],
                explanation=json.dumps(
                    values["decision_scores"], indent=2, sort_keys=True
                ),
                metadata=values,
            )

        return score

    return _scorer()
