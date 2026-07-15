#!/usr/bin/env python3
"""Validate that one Inspect eval cell produced a scored success log."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import re
import sys
from pathlib import Path
from typing import Any

try:
    from aggregate_eval_results import infer_provider, sample_resolved_models
except ModuleNotFoundError:  # pragma: no cover - imported as scripts.validate_eval_cell
    from scripts.aggregate_eval_results import infer_provider, sample_resolved_models

_SAMPLE_SEED_RE = re.compile(r"_seed_(\d+)$")


def expected_sample_id(task: str, seed: int) -> str:
    return "{}_seeded_seed_{:02d}".format(task, seed)


def sample_id_matches_seed(sample_id: str, seed: int) -> bool:
    match = _SAMPLE_SEED_RE.search(sample_id)
    return match is not None and int(match.group(1)) == seed


def parse_created_timestamp(value: object) -> datetime:
    if not isinstance(value, str) or not value.strip():
        return datetime.min.replace(tzinfo=timezone.utc)
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return datetime.min.replace(tzinfo=timezone.utc)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def score_value(sample: Any) -> dict[str, Any] | None:
    scores = getattr(sample, "scores", {}) or {}
    for scorer_info in scores.values():
        candidate = getattr(scorer_info, "value", None)
        if isinstance(candidate, dict):
            return candidate
    return None


def output_completion(sample: Any) -> str:
    output = getattr(sample, "output", None)
    completion = getattr(output, "completion", "")
    if isinstance(completion, str):
        return completion
    return ""


def resolved_model(sample: Any) -> str:
    candidates = sample_resolved_models(sample)
    return candidates[0] if len(candidates) == 1 else ""


def json_mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return {key: item for key, item in value.items() if item is not None}
    if value is None:
        return {}
    if hasattr(value, "model_dump"):
        payload = value.model_dump(mode="json", exclude_none=True, exclude_unset=True)
        return payload if isinstance(payload, dict) else {}
    try:
        names = vars(value)
    except TypeError:
        return {}
    return {
        name: item
        for name, item in names.items()
        if item is not None and not name.startswith("_")
    }


def model_ids_match(expected: str, actual: str, provider: str) -> bool:
    if expected == actual:
        return True
    return expected == "{}/{}".format(provider, actual) or actual == "{}/{}".format(
        provider, expected
    )


def parse_expected_generation_config(value: str) -> dict[str, Any]:
    stripped = value.strip()
    try:
        if stripped.startswith("{"):
            payload = json.loads(stripped)
        else:
            with Path(stripped).open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise argparse.ArgumentTypeError(
            "expected generation config must be a JSON object or readable JSON file"
        ) from exc
    if not isinstance(payload, dict) or not payload:
        raise argparse.ArgumentTypeError(
            "expected generation config must be a non-empty JSON object"
        )
    return payload


def task_requires_nonempty_completion(task: str) -> bool:
    return task == "safety_case_01"


def error_message(log: Any) -> str:
    err = getattr(log, "error", None)
    if err is None:
        return ""
    message = getattr(err, "message", None)
    if isinstance(message, str):
        return message
    return str(err)


def matching_logs(log_dir: Path, task: str, model: str, seed: int) -> tuple[list[dict[str, Any]], list[str]]:
    from inspect_ai.log import read_eval_log

    rows: list[dict[str, Any]] = []
    read_errors: list[str] = []
    for eval_path in sorted(log_dir.glob("*.eval")):
        try:
            log = read_eval_log(str(eval_path))
        except Exception as exc:  # pragma: no cover - defensive for corrupt archives
            read_errors.append("{}: {}".format(eval_path.name, exc))
            continue

        log_eval = getattr(log, "eval", None)
        if getattr(log_eval, "model", None) != model:
            continue
        if getattr(log_eval, "task", None) != task:
            continue

        samples = list(getattr(log, "samples", []) or [])
        if not samples:
            continue
        sample_ids = [str(getattr(sample, "id", "")) for sample in samples]
        if not all(sample_id_matches_seed(sample_id, seed) for sample_id in sample_ids):
            continue
        scores_by_sample = [
            (sample_id, score_value(sample))
            for sample_id, sample in zip(sample_ids, samples)
        ]
        unscored_sample_ids = [
            sample_id for sample_id, score in scores_by_sample if score is None
        ]
        limit_exceeded_samples = [
            {
                "sample_id": sample_id,
                "limit": str(getattr(sample, "limit", "")),
            }
            for sample_id, sample in zip(sample_ids, samples)
            if getattr(sample, "limit", None) is not None
        ]
        empty_completion_sample_ids: list[str] = []
        if task_requires_nonempty_completion(task):
            empty_completion_sample_ids = [
                sample_id
                for sample_id, sample in zip(sample_ids, samples)
                if not output_completion(sample).strip()
            ]
        requested_model = str(getattr(log_eval, "model", "") or "")
        request_provider = infer_provider(requested_model)
        resolved_by_sample = {
            sample_id: sample_resolved_models(sample, request_provider)
            for sample_id, sample in zip(sample_ids, samples)
        }
        resolved_models = sorted(
            {
                value
                for values in resolved_by_sample.values()
                for value in values
                if value
            }
        )
        missing_resolved_sample_ids = [
            sample_id
            for sample_id, values in resolved_by_sample.items()
            if not values
        ]
        provider = infer_provider(
            requested_model, resolved_models[0] if len(resolved_models) == 1 else ""
        )
        packages = json_mapping(getattr(log_eval, "packages", None))
        rows.append(
            {
                "eval_path": eval_path,
                "created": getattr(log_eval, "created", "") or "",
                "status": getattr(log, "status", "unknown"),
                "sample_count": len(samples),
                "scored_count": len(samples) - len(unscored_sample_ids),
                "unscored_sample_ids": unscored_sample_ids,
                "limit_exceeded_samples": limit_exceeded_samples,
                "empty_completion_sample_ids": empty_completion_sample_ids,
                "error": error_message(log),
                "requested_model": requested_model,
                "resolved_models": resolved_models,
                "missing_resolved_sample_ids": missing_resolved_sample_ids,
                "provider": provider,
                "effective_generation_config": json_mapping(
                    getattr(log_eval, "model_generate_config", None)
                ),
                "inspect_version": str(
                    packages.get("inspect_ai") or packages.get("inspect-ai") or ""
                ),
                "evaluation_revision": json_mapping(
                    getattr(log_eval, "revision", None)
                ),
            }
        )
    return rows, read_errors


def latest_row(rows: list[dict[str, Any]]) -> dict[str, Any]:
    def eval_path_sort_key(row: dict[str, Any]) -> tuple[datetime, str, str]:
        eval_path = Path(row.get("eval_path", ""))
        return (
            parse_created_timestamp(row.get("created")),
            eval_path.name,
            str(eval_path),
        )

    return max(
        rows,
        key=eval_path_sort_key,
    )


def validate_cell(
    log_dir: Path,
    task: str,
    model: str,
    seed: int,
    *,
    expected_resolved_model: str | None = None,
    expected_provider: str | None = None,
    expected_generation_config: dict[str, Any] | None = None,
    expected_inspect_version: str | None = None,
    require_model_provenance: bool = False,
    require_clean_revision: bool = False,
) -> int:
    rows, read_errors = matching_logs(log_dir, task, model, seed)
    if not rows:
        print(
            "No Inspect eval log found for task={} model={} seed={} in {}".format(
                task, model, seed, log_dir
            ),
            file=sys.stderr,
        )
        for err in read_errors[:10]:
            print("Read error: {}".format(err), file=sys.stderr)
        return 1

    row = latest_row(rows)
    if row["status"] != "success":
        print(
            "Inspect eval log has status={} for task={} model={} seed={} ({})".format(
                row["status"], task, model, seed, row["eval_path"]
            ),
            file=sys.stderr,
        )
        if row["error"]:
            print(row["error"], file=sys.stderr)
        return 1

    if row["scored_count"] != row["sample_count"]:
        print(
            "Inspect eval log scored {}/{} samples for task={} model={} seed={} ({})".format(
                row["scored_count"],
                row["sample_count"],
                task,
                model,
                seed,
                row["eval_path"],
            ),
            file=sys.stderr,
        )
        for sample_id in row["unscored_sample_ids"][:10]:
            print("Unscored sample: {}".format(sample_id), file=sys.stderr)
        return 1

    if row["limit_exceeded_samples"]:
        print(
            "Inspect eval log exceeded an evaluation limit for task={} model={} "
            "seed={} ({})".format(task, model, seed, row["eval_path"]),
            file=sys.stderr,
        )
        for item in row["limit_exceeded_samples"][:10]:
            print(
                "Limit exceeded: {} ({})".format(item["sample_id"], item["limit"]),
                file=sys.stderr,
            )
        return 1

    if row["empty_completion_sample_ids"]:
        print(
            "Inspect eval log has {} empty model completions for task={} model={} seed={} ({})".format(
                len(row["empty_completion_sample_ids"]),
                task,
                model,
                seed,
                row["eval_path"],
            ),
            file=sys.stderr,
        )
        for sample_id in row["empty_completion_sample_ids"][:10]:
            print("Empty completion sample: {}".format(sample_id), file=sys.stderr)
        return 1

    if len(row["resolved_models"]) > 1:
        print(
            "Inspect eval log mixes provider-resolved model snapshots for "
            "task={} model={} seed={}: {} ({})".format(
                task,
                model,
                seed,
                ", ".join(row["resolved_models"]),
                row["eval_path"],
            ),
            file=sys.stderr,
        )
        return 1

    provenance_required = bool(
        require_model_provenance
        or expected_resolved_model
        or expected_provider
        or expected_generation_config is not None
    )
    if provenance_required:
        if row["missing_resolved_sample_ids"] or not row["resolved_models"]:
            print(
                "Inspect eval log is missing provider-resolved model ids for "
                "task={} model={} seed={} ({})".format(
                    task, model, seed, row["eval_path"]
                ),
                file=sys.stderr,
            )
            for sample_id in row["missing_resolved_sample_ids"][:10]:
                print("Missing resolved model: {}".format(sample_id), file=sys.stderr)
            return 1
        if not row["provider"]:
            print(
                "Inspect eval log is missing model provider provenance ({})".format(
                    row["eval_path"]
                ),
                file=sys.stderr,
            )
            return 1
        if not row["effective_generation_config"]:
            print(
                "Inspect eval log is missing effective generation config ({})".format(
                    row["eval_path"]
                ),
                file=sys.stderr,
            )
            return 1
        if not row["inspect_version"]:
            print(
                "Inspect eval log is missing Inspect version metadata ({})".format(
                    row["eval_path"]
                ),
                file=sys.stderr,
            )
            return 1
    if require_clean_revision:
        revision = row["evaluation_revision"]
        if (
            not revision.get("commit")
            or revision.get("commit") == "unknown"
            or revision.get("dirty") is not False
        ):
            print(
                "Inspect eval log has no clean evaluation revision ({})".format(
                    row["eval_path"]
                ),
                file=sys.stderr,
            )
            return 1

    resolved = row["resolved_models"][0] if row["resolved_models"] else ""
    if expected_provider and row["provider"] != expected_provider:
        print(
            "Inspect eval log provider mismatch: expected={} actual={} ({})".format(
                expected_provider, row["provider"] or "unknown", row["eval_path"]
            ),
            file=sys.stderr,
        )
        return 1
    if expected_resolved_model and not model_ids_match(
        expected_resolved_model, resolved, row["provider"]
    ):
        print(
            "Inspect eval log resolved model mismatch: expected={} actual={} ({})".format(
                expected_resolved_model, resolved or "unknown", row["eval_path"]
            ),
            file=sys.stderr,
        )
        return 1
    if (
        expected_generation_config is not None
        and row["effective_generation_config"] != expected_generation_config
    ):
        print(
            "Inspect eval log generation config mismatch: expected={} actual={} ({})".format(
                json.dumps(expected_generation_config, sort_keys=True),
                json.dumps(row["effective_generation_config"], sort_keys=True),
                row["eval_path"],
            ),
            file=sys.stderr,
        )
        return 1
    if expected_inspect_version and row["inspect_version"] != expected_inspect_version:
        print(
            "Inspect version mismatch: expected={} actual={} ({})".format(
                expected_inspect_version,
                row["inspect_version"] or "unknown",
                row["eval_path"],
            ),
            file=sys.stderr,
        )
        return 1

    print(
        "Validated eval cell: task={} requested_model={} resolved_model={} "
        "provider={} seed={} samples={} inspect={} log={}".format(
            task,
            model,
            resolved or "unavailable",
            row["provider"] or "unknown",
            seed,
            row["sample_count"],
            row["inspect_version"] or "unknown",
            row["eval_path"],
        )
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log-dir", required=True)
    parser.add_argument("--task", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--seed", required=True, type=int)
    parser.add_argument("--expected-resolved-model")
    parser.add_argument("--expected-provider")
    parser.add_argument("--expected-inspect-version")
    parser.add_argument(
        "--expected-generation-config",
        type=parse_expected_generation_config,
        help="Expected GenerateConfig as a JSON object or path to a JSON file.",
    )
    parser.add_argument("--require-model-provenance", action="store_true")
    parser.add_argument("--require-clean-revision", action="store_true")
    args = parser.parse_args()

    return validate_cell(
        log_dir=Path(args.log_dir),
        task=args.task,
        model=args.model,
        seed=args.seed,
        expected_resolved_model=args.expected_resolved_model,
        expected_provider=args.expected_provider,
        expected_generation_config=args.expected_generation_config,
        expected_inspect_version=args.expected_inspect_version,
        require_model_provenance=args.require_model_provenance,
        require_clean_revision=args.require_clean_revision,
    )


if __name__ == "__main__":
    raise SystemExit(main())
