#!/usr/bin/env python3
"""Validate that one Inspect eval cell produced a scored success log."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import sys
from pathlib import Path
from typing import Any


def expected_sample_id(task: str, seed: int) -> str:
    if seed == 0:
        return "{}_seeded".format(task)
    return "{}_seeded_seed_{:02d}".format(task, seed)


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


def error_message(log: Any) -> str:
    err = getattr(log, "error", None)
    if err is None:
        return ""
    message = getattr(err, "message", None)
    if isinstance(message, str):
        return message
    return str(err)


def matching_rows(log_dir: Path, task: str, model: str, sample_id: str) -> tuple[list[dict[str, Any]], list[str]]:
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

        for sample in getattr(log, "samples", []) or []:
            if getattr(sample, "id", None) != sample_id:
                continue
            rows.append(
                {
                    "eval_path": eval_path,
                    "created": getattr(log_eval, "created", "") or "",
                    "status": getattr(log, "status", "unknown"),
                    "score": score_value(sample),
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
    sample_id = expected_sample_id(task, seed)
    rows, read_errors = matching_rows(log_dir, task, model, sample_id)
    if not rows:
        print(
            "No Inspect eval log found for task={} model={} sample_id={} in {}".format(
                task, model, sample_id, log_dir
            ),
            file=sys.stderr,
        )
        for err in read_errors[:10]:
            print("Read error: {}".format(err), file=sys.stderr)
        return 1

    row = latest_row(rows)
    if row["status"] != "success":
        print(
            "Inspect eval log has status={} for task={} model={} sample_id={} ({})".format(
                row["status"], task, model, sample_id, row["eval_path"]
            ),
            file=sys.stderr,
        )
        if row["error"]:
            print(row["error"], file=sys.stderr)
        return 1

    if row["score"] is None:
        print(
            "Inspect eval log has no scored sample for task={} model={} sample_id={} ({})".format(
                task, model, sample_id, row["eval_path"]
            ),
            file=sys.stderr,
        )
        return 1

    print(
        "Validated eval cell: task={} model={} sample_id={} log={}".format(
            task, model, sample_id, row["eval_path"]
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
