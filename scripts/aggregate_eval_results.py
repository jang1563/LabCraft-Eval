#!/usr/bin/env python3
"""Aggregate an explicit Inspect .eval bundle into a new Markdown summary.

Scans every .eval archive in the requested log directories, pulls
model/task/status and per-axis scores out of each log's header.json and
samples/*.json, deduplicates repeated reruns by keeping the latest archive for
each (model, task, sample_id), then writes a human-readable Markdown summary
with per-(model, task) means and standard deviations.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_AXES = ("overall", "task_success", "decision_quality", "troubleshooting", "efficiency")
SAFETY_CASE_AXES = (
    "aggregate",
    "legitimate_helpfulness",
    "boundary_precision",
    "provenance_grounding",
    "monitor_coverage",
    "residual_risk_framing",
)
AXIS_ORDER = DEFAULT_AXES + SAFETY_CASE_AXES


def resolve_repo_path(path_str: str) -> Path:
    path = Path(path_str)
    if not path.is_absolute():
        path = REPO_ROOT / path
    return path.resolve()


def repo_relative_display_path(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _is_repo_relative_path(path: Path) -> bool:
    try:
        path.relative_to(REPO_ROOT)
        return True
    except ValueError:
        return False


def _format_log_dir_reference(log_dir: Path) -> str:
    rel = repo_relative_display_path(log_dir)
    if _is_repo_relative_path(log_dir):
        return "[{rel}](../{rel})".format(rel=rel)
    return "`{}`".format(rel)


def _parse_created_timestamp(value: object) -> datetime:
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


def _jsonable_mapping(value, *, fields: tuple[str, ...] | None = None) -> dict:
    if value is None:
        return {}
    if isinstance(value, dict):
        payload = dict(value)
    elif hasattr(value, "model_dump"):
        payload = value.model_dump(mode="json", exclude_none=True, exclude_unset=True)
    else:
        names = fields or tuple(vars(value))
        payload = {
            name: getattr(value, name)
            for name in names
            if getattr(value, name, None) is not None
        }
    if fields is not None:
        payload = {
            name: payload[name]
            for name in fields
            if name in payload and payload[name] is not None
        }
    else:
        payload = {name: item for name, item in payload.items() if item is not None}
    try:
        json.dumps(payload)
    except TypeError:
        payload = json.loads(json.dumps(payload, default=str))
    return payload


def _model_name(value: object) -> str:
    """Return a stable model identifier from Inspect model metadata."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        for field in ("model", "name", "id"):
            candidate = value.get(field)
            if isinstance(candidate, str) and candidate.strip():
                return candidate.strip()
    for field in ("model", "name", "id"):
        candidate = getattr(value, field, None)
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
    text = str(value).strip()
    return "" if text.startswith("<") and text.endswith(">") else text


def infer_provider(requested_model: str, resolved_model: str = "") -> str:
    """Infer the provider from an Inspect model id, preferring its API prefix."""
    requested_model = _model_name(requested_model)
    if "/" in requested_model:
        provider = requested_model.split("/", 1)[0].strip()
        if provider:
            return provider

    unqualified = _model_name(resolved_model) or requested_model
    provider_prefixes = {
        "anthropic": ("claude-",),
        "google": ("gemini-",),
        "openai": ("chatgpt-", "gpt-", "o1", "o3", "o4"),
        "xai": ("grok-",),
    }
    for provider, prefixes in provider_prefixes.items():
        if unqualified.startswith(prefixes):
            return provider
    return ""


def canonical_model_id(model: object, provider: str) -> str:
    """Normalize only the optional provider qualification of a model id."""
    model_name = _model_name(model)
    prefix = "{}/".format(provider)
    if provider and model_name.startswith(prefix):
        return model_name[len(prefix) :]
    return model_name


def sample_resolved_models(sample, provider: str = "") -> list[str]:
    """Read distinct provider-returned snapshots recorded for a sample."""
    candidates: set[str] = set()
    output = getattr(sample, "output", None)
    direct_model = _model_name(getattr(output, "model", None))
    if direct_model:
        candidates.add(direct_model)

    for choice in getattr(output, "choices", []) or []:
        message = getattr(choice, "message", None)
        candidate = _model_name(getattr(message, "model", None))
        if candidate:
            candidates.add(candidate)
    for message in getattr(sample, "messages", []) or []:
        candidate = _model_name(getattr(message, "model", None))
        if candidate:
            candidates.add(candidate)

    if not provider:
        qualified_providers = {
            candidate.split("/", 1)[0]
            for candidate in candidates
            if "/" in candidate
        }
        if len(qualified_providers) == 1:
            provider = next(iter(qualified_providers))

    raw_by_canonical: dict[str, set[str]] = defaultdict(set)
    for candidate in candidates:
        raw_by_canonical[canonical_model_id(candidate, provider)].add(candidate)

    resolved_models = []
    for canonical in sorted(raw_by_canonical):
        raw_values = raw_by_canonical[canonical]
        resolved_models.append(
            direct_model if direct_model in raw_values else sorted(raw_values)[0]
        )
    return resolved_models


def _sample_resolved_model(sample) -> str:
    """Return one snapshot only when a sample has an unambiguous resolution."""
    candidates = sample_resolved_models(sample)
    return candidates[0] if len(candidates) == 1 else ""


def _requested_model(row: dict) -> str:
    return (
        _model_name(row.get("requested_model"))
        or _model_name(row.get("model"))
        or "unknown"
    )


def _resolved_model(row: dict) -> str:
    return _model_name(row.get("resolved_model"))


def model_display_name(row: dict) -> str:
    """Display requested and resolved ids without merging rolling aliases."""
    requested = _requested_model(row)
    resolved = _resolved_model(row)
    if not resolved:
        return requested
    provider = _model_name(row.get("provider")) or infer_provider(requested, resolved)
    qualified_resolved = (
        resolved if "/" in resolved or not provider else "{}/{}".format(provider, resolved)
    )
    if qualified_resolved == requested:
        return requested
    return "{} → {}".format(requested, qualified_resolved)


def model_resolution_conflicts(rows) -> dict[str, list[str]]:
    """Return requested aliases that resolved to multiple provider snapshots."""
    resolved_by_request = defaultdict(set)
    for row in rows:
        requested = _requested_model(row)
        resolved = _resolved_model(row)
        if resolved:
            provider = _model_name(row.get("provider")) or infer_provider(
                requested, resolved
            )
            resolved_by_request[requested].add(
                canonical_model_id(resolved, provider)
            )
    return {
        requested: sorted(resolved)
        for requested, resolved in sorted(resolved_by_request.items())
        if len(resolved) > 1
    }


def _sample_tokens(sample, model: str) -> dict:
    usage_by_model = getattr(sample, "model_usage", {}) or {}
    if isinstance(usage_by_model, dict):
        token_stats = usage_by_model.get(model)
        if token_stats is None and len(usage_by_model) == 1:
            token_stats = next(iter(usage_by_model.values()))
    else:
        token_stats = usage_by_model
    if token_stats is None:
        return {}
    fields = {
        "input": "input_tokens",
        "output": "output_tokens",
        "total": "total_tokens",
        "input_cache_read": "input_tokens_cache_read",
    }

    def token_value(name):
        if isinstance(token_stats, dict):
            return token_stats.get(name)
        return getattr(token_stats, name, None)

    return {
        output_name: token_value(source_name)
        for output_name, source_name in fields.items()
        if token_value(source_name) is not None
    }


def extract_scores(eval_path: Path, *, strict: bool = True):
    """Return a list of per-sample dicts: {task, model, status, axis -> float, tokens}."""
    rows = []
    try:
        from inspect_ai.log import read_eval_log

        log = read_eval_log(str(eval_path))
    except Exception as exc:
        if strict:
            raise RuntimeError(
                "Failed to read Inspect eval log {}: {}".format(eval_path, exc)
            ) from exc
        return rows

    eval_metadata = getattr(log, "eval", None)
    model = _model_name(getattr(eval_metadata, "model", "unknown")) or "unknown"
    task = getattr(eval_metadata, "task", "unknown")
    raw_status = getattr(log, "status", "unknown")
    status = getattr(raw_status, "value", raw_status)
    if str(status).lower() != "success":
        message = "Inspect eval log {} has non-success status: {}".format(eval_path, status)
        if strict:
            raise RuntimeError(message)
        return []
    created = getattr(eval_metadata, "created", "") or ""
    eval_revision = _jsonable_mapping(
        getattr(eval_metadata, "revision", None),
        fields=("type", "origin", "commit", "dirty"),
    )
    model_generate_config = _jsonable_mapping(
        getattr(eval_metadata, "model_generate_config", None)
    )
    packages = _jsonable_mapping(getattr(eval_metadata, "packages", None))
    inspect_version = _model_name(
        packages.get("inspect_ai") or packages.get("inspect-ai")
    )

    for sample in getattr(log, "samples", []) or []:
        scores = getattr(sample, "scores", {}) or {}
        value_block = None
        for scorer_info in scores.values():
            candidate = getattr(scorer_info, "value", None)
            if isinstance(candidate, dict):
                value_block = candidate
                break
        if value_block is None:
            continue
        provider = infer_provider(model)
        resolved_model_candidates = sample_resolved_models(sample, provider)
        resolved_model = (
            resolved_model_candidates[0]
            if len(resolved_model_candidates) == 1
            else ""
        )
        provider = infer_provider(model, resolved_model)
        row = {
            "model": model,
            "requested_model": model,
            "resolved_model": resolved_model,
            "resolved_model_candidates": resolved_model_candidates,
            "provider": provider,
            "task": task,
            "status": status,
            "sample_id": getattr(sample, "id", eval_path.stem),
            "eval_log": eval_path.name,
            "eval_log_path": str(eval_path.resolve()),
            "created": created,
            "tokens": _sample_tokens(sample, model),
            "eval_revision": eval_revision,
            "model_generate_config": model_generate_config,
            "effective_generation_config": dict(model_generate_config),
            "inspect_version": inspect_version,
            "limit": _jsonable_mapping(getattr(sample, "limit", None)),
        }
        for axis, value in value_block.items():
            if isinstance(value, (int, float)):
                row[axis] = float(value)
        rows.append(row)
    return rows


def dedupe_rows(rows):
    """Keep the latest row per effective-model/task/sample identity.

    The resolved snapshot participates in the key whenever Inspect recorded it,
    so two snapshots reached through the same requested alias cannot silently
    overwrite one another.
    """
    latest_by_sample = {}
    for row in rows:
        key = (
            _requested_model(row),
            canonical_model_id(
                _resolved_model(row),
                _model_name(row.get("provider"))
                or infer_provider(_requested_model(row), _resolved_model(row)),
            )
            or "__unresolved__",
            row["task"],
            row["sample_id"],
        )
        current = latest_by_sample.get(key)
        row_order_key = (
            _parse_created_timestamp(row.get("created")),
            row.get("eval_log", ""),
            row.get("eval_log_path", ""),
        )
        if current is None:
            latest_by_sample[key] = row
            continue
        current_order_key = (
            _parse_created_timestamp(current.get("created")),
            current.get("eval_log", ""),
            current.get("eval_log_path", ""),
        )
        if row_order_key >= current_order_key:
            latest_by_sample[key] = row
    return sorted(
        latest_by_sample.values(),
        key=lambda row: (
            _requested_model(row),
            _resolved_model(row),
            row["task"],
            row["sample_id"],
            row.get("eval_log", ""),
        ),
    )


def discover_axes(rows):
    present = {key for row in rows for key, value in row.items() if isinstance(value, float)}
    ordered = [axis for axis in AXIS_ORDER if axis in present]
    ordered.extend(sorted(present - set(ordered)))
    return ordered


def aggregate(rows, axes):
    groups = defaultdict(list)
    for row in rows:
        groups[(model_display_name(row), row["task"])].append(row)
    summary = []
    for (model, task), cell_rows in sorted(groups.items()):
        entry = {
            "model": model,
            "task": task,
            "n": len(cell_rows),
        }
        for axis in axes:
            values = [row[axis] for row in cell_rows if axis in row]
            if not values:
                continue
            entry["{}_mean".format(axis)] = statistics.fmean(values)
            entry["{}_std".format(axis)] = (
                statistics.stdev(values) if len(values) > 1 else 0.0
            )
        summary.append(entry)
    return summary


def format_markdown(
    summary,
    per_sample_rows,
    out_path: Path,
    log_dirs: list[Path],
    deduped_count: int,
    axes=None,
):
    axes = axes or discover_axes(per_sample_rows)
    rel_links = [_format_log_dir_reference(log_dir) for log_dir in log_dirs]
    lines = [
        "# LabCraft-Eval Evaluation Results",
        "",
        "Automatically aggregated from Inspect AI `.eval` logs in {}.".format(
            ", ".join(rel_links)
        ),
        "",
    ]
    if deduped_count:
        lines.extend(
            [
                "Repeated reruns with the same `(model, task, sample_id)` are deduplicated by keeping the latest `.eval` archive. {} duplicate sample rows were ignored.".format(
                    deduped_count
                ),
                "",
            ]
        )
    lines.extend(
        [
        "## Per-model per-task summary",
        "",
        "Mean score across the seed-labelled samples run for each (model, task) cell. `n` is the number of samples in that cell.",
        "",
        "| Model | Task | n | {} |".format(" | ".join("{} (mean±std)".format(axis) for axis in axes)),
        "|---|---|---:|{}|".format("|".join("---:" for _ in axes)),
        ]
    )
    for entry in summary:
        cells = []
        for axis in axes:
            mean = entry.get("{}_mean".format(axis))
            std = entry.get("{}_std".format(axis))
            cells.append("n/a" if mean is None or std is None else "{:.3f} ± {:.3f}".format(mean, std))
        line = "| {model} | `{task}` | {n} | {cells} |".format(
            model=entry["model"],
            task=entry["task"],
            n=entry["n"],
            cells=" | ".join(cells),
        )
        lines.append(line)

    lines.extend(
        [
            "",
            "## Per-sample detail",
            "",
            "| Model | Task | Sample | {} |".format(" | ".join(axes)),
            "|---|---|---|{}|".format("|".join("---:" for _ in axes)),
        ]
    )
    for row in per_sample_rows:
        cells = [
            "" if row.get(axis) is None else "{:.3f}".format(row[axis])
            for axis in axes
        ]
        lines.append(
            "| {model} | `{task}` | `{sample}` | {cells} |".format(
                model=model_display_name(row),
                task=row["task"],
                sample=row["sample_id"],
                cells=" | ".join(cells),
            )
        )
    lines.append("")
    out_path.write_text("\n".join(lines))


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--log-dir",
        nargs="+",
        required=True,
        help="One or more directories containing Inspect .eval archives.",
    )
    parser.add_argument("--out", required=True, help="New Markdown summary path.")
    args = parser.parse_args(argv)

    log_dirs = [resolve_repo_path(path_str) for path_str in args.log_dir]
    out_path = resolve_repo_path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    eval_paths = []
    for log_dir in log_dirs:
        eval_paths.extend(sorted(log_dir.glob("*.eval")))
    if not eval_paths:
        print("No .eval files found in {}".format(", ".join(str(p) for p in log_dirs)), file=sys.stderr)
        return 1

    all_rows = []
    for path in eval_paths:
        try:
            all_rows.extend(extract_scores(path))
        except RuntimeError as exc:
            print(str(exc), file=sys.stderr)
            return 1
    if not all_rows:
        print("No scoreable samples found.", file=sys.stderr)
        return 1

    deduped_rows = dedupe_rows(all_rows)
    axes = discover_axes(deduped_rows)
    summary = aggregate(deduped_rows, axes)
    format_markdown(
        summary,
        deduped_rows,
        out_path,
        log_dirs,
        deduped_count=len(all_rows) - len(deduped_rows),
        axes=axes,
    )
    print("Wrote {} rows to {}".format(len(deduped_rows), out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
