#!/usr/bin/env python3
"""Validate a generated LabCraft-Eval Hugging Face export bundle."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

REQUIRED_MANIFEST_KEYS = {
    "schema_version",
    "generated_at",
    "source_commit",
    "source_repository",
    "exporter",
    "files",
}
REQUIRED_FILE_KEYS = {"path", "sha256", "bytes", "record_count"}
REQUIRED_TASK_KEYS = {
    "schema_version",
    "source_commit",
    "task_id",
    "track",
    "task_title",
    "domain",
    "objective",
    "paths",
}
REQUIRED_RESULT_KEYS = {
    "schema_version",
    "source_commit",
    "model",
    "task",
    "sample_id",
    "eval_log",
    "scores",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_jsonl(path: Path) -> list[Any]:
    records = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                records.append(json.loads(stripped))
            except json.JSONDecodeError as exc:
                raise ValueError(
                    "{}:{} is not valid JSON: {}".format(path, line_number, exc)
                ) from exc
    return records


def resolve_bundle_path(export_dir: Path, path_value: str) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        return path
    return export_dir / path


def require_keys(record: dict[str, Any], required: set[str], label: str) -> list[str]:
    missing = sorted(required - set(record))
    return ["{} missing required keys: {}".format(label, ", ".join(missing))] if missing else []


def validate_task_records(records: list[Any]) -> list[str]:
    errors = []
    task_ids = set()
    for index, record in enumerate(records, start=1):
        if not isinstance(record, dict):
            errors.append("tasks.jsonl record {} is not an object".format(index))
            continue
        errors.extend(require_keys(record, REQUIRED_TASK_KEYS, "tasks.jsonl record {}".format(index)))
        task_id = record.get("task_id")
        if task_id in task_ids:
            errors.append("tasks.jsonl duplicate task_id: {}".format(task_id))
        if isinstance(task_id, str):
            task_ids.add(task_id)
        if not isinstance(record.get("paths"), dict):
            errors.append("tasks.jsonl record {} paths must be an object".format(index))
    return errors


def validate_record_source_commits(
    filename: str,
    records: list[Any],
    expected_commit: str,
) -> list[str]:
    errors = []
    for index, record in enumerate(records, start=1):
        if not isinstance(record, dict):
            continue
        record_commit = record.get("source_commit")
        if record_commit != expected_commit:
            errors.append(
                "{} record {} source_commit mismatch: manifest={} record={}".format(
                    filename, index, expected_commit, record_commit
                )
            )
    return errors


def validate_result_records(records: list[Any]) -> list[str]:
    errors = []
    if not records:
        return ["result_rows.jsonl has zero records"]
    sample_keys = set()
    for index, record in enumerate(records, start=1):
        if not isinstance(record, dict):
            errors.append("result_rows.jsonl record {} is not an object".format(index))
            continue
        errors.extend(
            require_keys(record, REQUIRED_RESULT_KEYS, "result_rows.jsonl record {}".format(index))
        )
        scores = record.get("scores")
        if not isinstance(scores, dict) or not scores:
            errors.append("result_rows.jsonl record {} has empty scores".format(index))
        key = (record.get("model"), record.get("task"), record.get("sample_id"))
        if key in sample_keys:
            errors.append("result_rows.jsonl duplicate model/task/sample_id: {}".format(key))
        sample_keys.add(key)
    return errors


def validate_export(export_dir: Path) -> list[str]:
    errors: list[str] = []
    manifest_path = export_dir / "release_manifest.json"
    if not manifest_path.exists():
        return ["Missing release_manifest.json in {}".format(export_dir)]

    manifest = load_json(manifest_path)
    if not isinstance(manifest, dict):
        return ["release_manifest.json must contain an object"]
    errors.extend(require_keys(manifest, REQUIRED_MANIFEST_KEYS, "release_manifest.json"))

    if manifest.get("source_commit") in (None, "", "unknown"):
        errors.append("release_manifest.json source_commit must be populated")
    if manifest.get("source_repository") in (None, "", "unknown"):
        errors.append("release_manifest.json source_repository must be populated")

    files = manifest.get("files")
    if not isinstance(files, list) or not files:
        errors.append("release_manifest.json files must be a non-empty list")
        return errors

    seen_paths = set()
    jsonl_records_by_name: dict[str, list[Any]] = {}
    for index, file_record in enumerate(files, start=1):
        if not isinstance(file_record, dict):
            errors.append("manifest file entry {} is not an object".format(index))
            continue
        errors.extend(require_keys(file_record, REQUIRED_FILE_KEYS, "manifest file entry {}".format(index)))
        path_value = file_record.get("path")
        if not isinstance(path_value, str) or not path_value:
            errors.append("manifest file entry {} path must be a non-empty string".format(index))
            continue
        entry_path = Path(path_value)
        if entry_path.is_absolute():
            errors.append("manifest file path must be relative: {}".format(path_value))
        if ".." in entry_path.parts:
            errors.append("manifest file path must not escape export dir: {}".format(path_value))
        if path_value in seen_paths:
            errors.append("duplicate manifest file path: {}".format(path_value))
        seen_paths.add(path_value)

        file_path = resolve_bundle_path(export_dir, path_value)
        if not file_path.exists():
            errors.append("manifest file does not exist: {}".format(path_value))
            continue
        expected_bytes = file_record.get("bytes")
        if expected_bytes != file_path.stat().st_size:
            errors.append(
                "{} byte count mismatch: manifest={} actual={}".format(
                    path_value, expected_bytes, file_path.stat().st_size
                )
            )
        expected_sha = file_record.get("sha256")
        actual_sha = sha256_file(file_path)
        if expected_sha != actual_sha:
            errors.append("{} sha256 mismatch".format(path_value))

        if file_path.suffix == ".jsonl":
            records = load_jsonl(file_path)
            jsonl_records_by_name[file_path.name] = records
            errors.extend(
                validate_record_source_commits(
                    file_path.name,
                    records,
                    str(manifest.get("source_commit")),
                )
            )
            if file_record.get("record_count") != len(records):
                errors.append(
                    "{} record_count mismatch: manifest={} actual={}".format(
                        path_value, file_record.get("record_count"), len(records)
                    )
                )
        elif file_path.name == "README.md":
            text = file_path.read_text(encoding="utf-8")
            if not text.startswith("---\n"):
                errors.append("README.md must start with Hugging Face YAML metadata")
            if "license:" not in text:
                errors.append("README.md metadata must include license")

    if "tasks.jsonl" in jsonl_records_by_name:
        errors.extend(validate_task_records(jsonl_records_by_name["tasks.jsonl"]))
    else:
        errors.append("tasks.jsonl is missing from manifest")

    if "result_rows.jsonl" in jsonl_records_by_name:
        errors.extend(validate_result_records(jsonl_records_by_name["result_rows.jsonl"]))

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("export_dir", help="Path to a generated HF export directory.")
    args = parser.parse_args()

    export_dir = Path(args.export_dir).resolve()
    errors = validate_export(export_dir)
    if errors:
        print("HF export validation failed:", file=sys.stderr)
        for error in errors:
            print("- {}".format(error), file=sys.stderr)
        return 1
    print("HF export validation passed: {}".format(export_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
