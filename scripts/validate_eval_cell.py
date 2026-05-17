#!/usr/bin/env python3
"""Validate that one Inspect eval cell produced a scored success log."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import re
import sys
from pathlib import Path
from typing import Any

_SAMPLE_SEED_RE = re.compile(r"_seed_(\d+)$")


def expected_sample_id(task: str, seed: int) -> str:
    if seed == 0:
        return "{}_seeded".format(task)
    return "{}_seeded_seed_{:02d}".format(task, seed)


def sample_id_matches_seed(sample_id: str, seed: int) -> bool:
    match = _SAMPLE_SEED_RE.search(sample_id)
    if seed == 0:
        return match is None or int(match.group(1)) == 0
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
        empty_completion_sample_ids: list[str] = []
        if task_requires_nonempty_completion(task):
            empty_completion_sample_ids = [
                sample_id
                for sample_id, sample in zip(sample_ids, samples)
                if not output_completion(sample).strip()
            ]
        rows.append(
            {
                "eval_path": eval_path,
                "created": getattr(log_eval, "created", "") or "",
                "status": getattr(log, "status", "unknown"),
                "sample_count": len(samples),
                "scored_count": len(samples) - len(unscored_sample_ids),
                "unscored_sample_ids": unscored_sample_ids,
                "empty_completion_sample_ids": empty_completion_sample_ids,
                "error": error_message(log),
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


def validate_cell(log_dir: Path, task: str, model: str, seed: int) -> int:
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

    print(
        "Validated eval cell: task={} model={} seed={} samples={} log={}".format(
            task, model, seed, row["sample_count"], row["eval_path"]
        )
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log-dir", required=True)
    parser.add_argument("--task", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--seed", required=True, type=int)
    args = parser.parse_args()

    return validate_cell(
        log_dir=Path(args.log_dir),
        task=args.task,
        model=args.model,
        seed=args.seed,
    )


if __name__ == "__main__":
    raise SystemExit(main())
