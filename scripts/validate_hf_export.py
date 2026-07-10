#!/usr/bin/env python3
"""Validate a generated LabCraft-Eval Hugging Face export bundle."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any

SCHEMA_DIR = Path(__file__).resolve().parents[1] / "schemas"

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
REQUIRED_RESULT_PROVENANCE_KEYS = {
    "track",
    "status",
    "eval_log_path",
    "created",
    "tokens",
    "evaluation_revision",
    "model_generate_config",
}
REQUIRED_EVAL_LOG_KEYS = {
    "schema_version",
    "source_commit",
    "path",
    "source_path",
    "log_dir",
    "filename",
    "sha256",
    "bytes",
    "status",
    "evaluation_revision",
    "model_generate_config",
    "sample_count",
}
RESERVED_ROOT_JSONL_PATHS = {
    "tasks.jsonl",
    "rubrics.jsonl",
    "ground_truth.jsonl",
    "citations.jsonl",
    "result_rows.jsonl",
    "eval_log_manifest.jsonl",
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
    try:
        export_root = export_dir.resolve()
    except (OSError, RuntimeError) as exc:
        raise ValueError("export directory cannot be resolved safely") from exc
    path = Path(path_value)
    if path.is_absolute():
        raise ValueError("bundle path must be relative: {}".format(path_value))
    if ".." in path.parts:
        raise ValueError("bundle path must not contain '..': {}".format(path_value))
    try:
        resolved = (export_root / path).resolve()
    except (OSError, RuntimeError) as exc:
        raise ValueError(
            "bundle path cannot be resolved safely: {}".format(path_value)
        ) from exc
    try:
        resolved.relative_to(export_root)
    except ValueError as exc:
        raise ValueError(
            "bundle path escapes export directory via symlink: {}".format(path_value)
        ) from exc
    return resolved


def is_hugging_face_local_bookkeeping(path_value: str) -> bool:
    path = Path(path_value)
    return path_value == ".gitattributes" or path.parts[:2] == (".cache", "huggingface")


def require_keys(record: dict[str, Any], required: set[str], label: str) -> list[str]:
    missing = sorted(required - set(record))
    return ["{} missing required keys: {}".format(label, ", ".join(missing))] if missing else []


def validate_json_schema(payload: Any, schema_name: str, label: str) -> list[str]:
    try:
        from jsonschema import Draft202012Validator
    except ModuleNotFoundError:
        return ["jsonschema is required to validate schema 0.2.0 exports"]
    schema = load_json(SCHEMA_DIR / schema_name)
    validator = Draft202012Validator(schema)
    errors = []
    for error in sorted(
        validator.iter_errors(payload),
        key=lambda item: tuple(str(part) for part in item.path),
    ):
        location = ".".join(str(part) for part in error.path) or "$"
        errors.append("{} schema error at {}: {}".format(label, location, error.message))
    return errors


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


def validate_result_records(
    records: list[Any],
    *,
    require_evaluation_provenance: bool = False,
) -> list[str]:
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
        if require_evaluation_provenance:
            errors.extend(
                require_keys(
                    record,
                    REQUIRED_RESULT_PROVENANCE_KEYS,
                    "result_rows.jsonl record {}".format(index),
                )
            )
            if record.get("status") != "success":
                errors.append(
                    "result_rows.jsonl record {} status must be success".format(index)
                )
            revision = record.get("evaluation_revision")
            if not isinstance(revision, dict):
                errors.append(
                    "result_rows.jsonl record {} evaluation_revision must be an object".format(
                        index
                    )
                )
            else:
                missing_revision = {"type", "origin", "commit", "dirty"} - set(revision)
                if missing_revision:
                    errors.append(
                        "result_rows.jsonl record {} evaluation_revision missing: {}".format(
                            index, ", ".join(sorted(missing_revision))
                        )
                    )
                if revision.get("commit") in (None, "", "unknown"):
                    errors.append(
                        "result_rows.jsonl record {} evaluation revision commit is missing".format(
                            index
                        )
                    )
                if revision.get("dirty") is not False:
                    errors.append(
                        "result_rows.jsonl record {} comes from a dirty evaluation revision".format(
                            index
                        )
                    )
            if not isinstance(record.get("model_generate_config"), dict) or not record[
                "model_generate_config"
            ]:
                errors.append(
                    "result_rows.jsonl record {} model_generate_config must be a "
                    "non-empty object".format(index)
                )
            tokens = record.get("tokens")
            if not isinstance(tokens, dict):
                errors.append(
                    "result_rows.jsonl record {} tokens must be an object".format(index)
                )
            elif any(
                isinstance(value, bool) or not isinstance(value, int) or value < 0
                for value in tokens.values()
            ):
                errors.append(
                    "result_rows.jsonl record {} tokens must be non-negative integers".format(
                        index
                    )
                )
        scores = record.get("scores")
        if not isinstance(scores, dict) or not scores:
            errors.append("result_rows.jsonl record {} has empty scores".format(index))
        elif require_evaluation_provenance:
            if "overall" not in scores:
                errors.append(
                    "result_rows.jsonl record {} scores missing overall".format(index)
                )
            for axis, value in scores.items():
                if (
                    isinstance(value, bool)
                    or not isinstance(value, (int, float))
                    or not math.isfinite(float(value))
                    or not 0.0 <= float(value) <= 1.0
                ):
                    errors.append(
                        "result_rows.jsonl record {} score {} must be finite and within [0, 1]".format(
                            index, axis
                        )
                    )
        key = (record.get("model"), record.get("task"), record.get("sample_id"))
        if key in sample_keys:
            errors.append("result_rows.jsonl duplicate model/task/sample_id: {}".format(key))
        sample_keys.add(key)
    return errors


def validate_export(export_dir: Path) -> list[str]:
    errors: list[str] = []
    try:
        export_dir = export_dir.resolve()
    except (OSError, RuntimeError):
        return ["Unsafe export directory: path cannot be resolved safely"]
    try:
        manifest_path = resolve_bundle_path(export_dir, "release_manifest.json")
    except ValueError as exc:
        return ["Unsafe release_manifest.json path: {}".format(exc)]
    if not manifest_path.exists():
        return ["Missing release_manifest.json in {}".format(export_dir)]

    manifest = load_json(manifest_path)
    if not isinstance(manifest, dict):
        return ["release_manifest.json must contain an object"]
    errors.extend(require_keys(manifest, REQUIRED_MANIFEST_KEYS, "release_manifest.json"))
    strict_provenance = manifest.get("schema_version") != "0.1.0"
    if strict_provenance and not isinstance(manifest.get("evaluation_provenance"), dict):
        errors.append("release_manifest.json evaluation_provenance must be an object")

    if manifest.get("source_commit") in (None, "", "unknown"):
        errors.append("release_manifest.json source_commit must be populated")
    if manifest.get("source_repository") in (None, "", "unknown"):
        errors.append("release_manifest.json source_repository must be populated")
    if strict_provenance and manifest.get("packaging_worktree_dirty") is not False:
        errors.append("release_manifest.json packaging_worktree_dirty must be false")

    files = manifest.get("files")
    if not isinstance(files, list) or not files:
        errors.append("release_manifest.json files must be a non-empty list")
        return errors

    seen_paths = set()
    jsonl_records_by_path: dict[str, list[Any]] = {}
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
        if (
            entry_path.name in RESERVED_ROOT_JSONL_PATHS
            and path_value != entry_path.name
        ):
            errors.append(
                "reserved JSONL basename must use its canonical root path: {} "
                "(expected {})".format(path_value, entry_path.name)
            )
        if path_value in seen_paths:
            errors.append("duplicate manifest file path: {}".format(path_value))
        seen_paths.add(path_value)

        try:
            file_path = resolve_bundle_path(export_dir, path_value)
        except ValueError as exc:
            errors.append("unsafe manifest file path {}: {}".format(path_value, exc))
            continue
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
            jsonl_records_by_path[path_value] = records
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

    actual_paths = {
        path.relative_to(export_dir).as_posix()
        for path in export_dir.rglob("*")
        if path.is_symlink() or path.is_file()
    }
    expected_paths = set(seen_paths) | {"release_manifest.json"}
    for unexpected in sorted(
        path
        for path in actual_paths - expected_paths
        if not is_hugging_face_local_bookkeeping(path)
    ):
        errors.append("unmanifested file in export bundle: {}".format(unexpected))

    if "tasks.jsonl" in jsonl_records_by_path:
        errors.extend(validate_task_records(jsonl_records_by_path["tasks.jsonl"]))
    else:
        errors.append("tasks.jsonl is missing from manifest")

    if "result_rows.jsonl" in jsonl_records_by_path:
        errors.extend(
            validate_result_records(
                jsonl_records_by_path["result_rows.jsonl"],
                require_evaluation_provenance=strict_provenance,
            )
        )

    if strict_provenance and "eval_log_manifest.jsonl" not in jsonl_records_by_path:
        errors.append("eval_log_manifest.jsonl is required for schema 0.2.0 exports")

    if strict_provenance and "eval_log_manifest.jsonl" in jsonl_records_by_path:
        eval_records = jsonl_records_by_path["eval_log_manifest.jsonl"]
        eval_by_path = {}
        revision_commits = set()
        for index, record in enumerate(eval_records, start=1):
            if not isinstance(record, dict):
                errors.append(
                    "eval_log_manifest.jsonl record {} is not an object".format(index)
                )
                continue
            errors.extend(
                require_keys(
                    record,
                    REQUIRED_EVAL_LOG_KEYS,
                    "eval_log_manifest.jsonl record {}".format(index),
                )
            )
            if not isinstance(record, dict):
                continue
            if record.get("status") != "success":
                errors.append(
                    "eval_log_manifest.jsonl record {} status must be success".format(index)
                )
            revision = record.get("evaluation_revision")
            if not isinstance(revision, dict) or revision.get("dirty") is not False:
                errors.append(
                    "eval_log_manifest.jsonl record {} must have a clean evaluation revision".format(
                        index
                    )
                )
            elif revision.get("commit") in (None, "", "unknown"):
                errors.append(
                    "eval_log_manifest.jsonl record {} evaluation commit is missing".format(
                        index
                    )
                )
            else:
                revision_commits.add(revision["commit"])
            if not isinstance(record.get("model_generate_config"), dict) or not record[
                "model_generate_config"
            ]:
                errors.append(
                    "eval_log_manifest.jsonl record {} model_generate_config must be a "
                    "non-empty object".format(index)
                )
            sample_count = record.get("sample_count")
            if not isinstance(sample_count, int) or isinstance(sample_count, bool) or sample_count < 1:
                errors.append(
                    "eval_log_manifest.jsonl record {} sample_count must be positive".format(
                        index
                    )
                )
            if isinstance(record.get("path"), str):
                eval_by_path[record["path"]] = record
                if record["path"] not in seen_paths:
                    errors.append(
                        "eval_log_manifest.jsonl record {} raw eval path is absent from "
                        "release manifest".format(index)
                    )
                file_record = next(
                    (
                        item
                        for item in files
                        if isinstance(item, dict) and item.get("path") == record["path"]
                    ),
                    None,
                )
                if isinstance(file_record, dict):
                    if file_record.get("sha256") != record.get("sha256"):
                        errors.append(
                            "eval_log_manifest.jsonl record {} sha256 differs from "
                            "release manifest".format(index)
                        )
                    if file_record.get("bytes") != record.get("bytes"):
                        errors.append(
                            "eval_log_manifest.jsonl record {} bytes differ from release "
                            "manifest".format(index)
                        )

        provenance = manifest.get("evaluation_provenance")
        if isinstance(provenance, dict):
            if provenance.get("policy") != "clean-evaluation-revisions-required":
                errors.append("release_manifest.json evaluation provenance policy is invalid")
            if provenance.get("dirty_log_count") != 0:
                errors.append("release_manifest.json dirty_log_count must be zero")
            if provenance.get("log_count") != len(eval_records):
                errors.append(
                    "release_manifest.json evaluation log_count mismatch: manifest={} actual={}".format(
                        provenance.get("log_count"), len(eval_records)
                    )
                )
            if provenance.get("revision_commits") != sorted(revision_commits):
                errors.append(
                    "release_manifest.json evaluation revision_commits do not match log records"
                )

        for index, result in enumerate(
            jsonl_records_by_path.get("result_rows.jsonl", []), start=1
        ):
            if not isinstance(result, dict):
                continue
            log_record = eval_by_path.get(result.get("eval_log_path"))
            if log_record is None:
                errors.append(
                    "result_rows.jsonl record {} eval_log_path is absent from log manifest".format(
                        index
                    )
                )
            elif result.get("evaluation_revision") != log_record.get("evaluation_revision"):
                errors.append(
                    "result_rows.jsonl record {} evaluation revision differs from log manifest".format(
                        index
                    )
                )
            elif result.get("model_generate_config") != log_record.get(
                "model_generate_config"
            ):
                errors.append(
                    "result_rows.jsonl record {} generation config differs from log "
                    "manifest".format(index)
                )

        if "result_rows.jsonl" in jsonl_records_by_path and not eval_records:
            errors.append(
                "eval_log_manifest.jsonl must be non-empty when result_rows.jsonl is present"
            )

    if strict_provenance:
        errors.extend(
            validate_json_schema(
                manifest,
                "release_manifest.schema.json",
                "release_manifest.json",
            )
        )
        schema_tables = {
            "tasks.jsonl": "hf_task_record.schema.json",
            "result_rows.jsonl": "hf_result_record.schema.json",
            "eval_log_manifest.jsonl": "hf_eval_log_manifest_record.schema.json",
        }
        for filename, schema_name in schema_tables.items():
            for index, record in enumerate(jsonl_records_by_path.get(filename, []), start=1):
                errors.extend(
                    validate_json_schema(
                        record,
                        schema_name,
                        "{} record {}".format(filename, index),
                    )
                )

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
