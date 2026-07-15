#!/usr/bin/env python3
"""Inspect the public LabCraft-Eval Hugging Face export.

This example intentionally uses only the Python standard library. It can read a
local export directory or download the small public JSON files from Hugging Face.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import tempfile
from collections import Counter
from collections.abc import Callable
from pathlib import Path
from urllib.request import urlretrieve


DEFAULT_BASE_URL = "https://huggingface.co/datasets/jang1563/LabCraft-Eval/resolve/main"
DEFAULT_CACHE_DIR = Path("build/hf_quickstart")
MANIFEST_FILE = "release_manifest.json"
REQUIRED_DATA_FILES = ("tasks.jsonl",)
OPTIONAL_DATA_FILES = ("result_rows.jsonl",)
Downloader = Callable[[str, str], object]


class QuickstartError(RuntimeError):
    """A snapshot could not be downloaded, verified, or read safely."""


def read_json(path: Path) -> dict:
    try:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except FileNotFoundError as exc:
        raise QuickstartError(f"missing required file: {path}") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise QuickstartError(f"could not read JSON file {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise QuickstartError(f"expected a JSON object in {path}")
    return payload


def read_jsonl(path: Path, *, label: str | None = None) -> list[dict]:
    records = []
    display_name = label or str(path)
    try:
        with path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise QuickstartError(
                        f"invalid JSON in {display_name} at line {line_number}: {exc.msg}"
                    ) from exc
                if not isinstance(record, dict):
                    raise QuickstartError(
                        f"expected a JSON object in {display_name} at line {line_number}"
                    )
                records.append(record)
    except FileNotFoundError as exc:
        raise QuickstartError(f"missing required file: {display_name}") from exc
    except OSError as exc:
        raise QuickstartError(f"could not read {display_name}: {exc}") from exc
    return records


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise QuickstartError(f"could not hash {path}: {exc}") from exc
    return digest.hexdigest()


def manifest_entries(manifest: dict) -> dict[str, dict]:
    source_commit = manifest.get("source_commit")
    if not isinstance(source_commit, str) or not source_commit.strip():
        raise QuickstartError("release manifest has no usable source_commit")

    raw_entries = manifest.get("files")
    if not isinstance(raw_entries, list):
        raise QuickstartError("release manifest field 'files' must be a list")

    entries: dict[str, dict] = {}
    for index, entry in enumerate(raw_entries):
        if not isinstance(entry, dict):
            raise QuickstartError(f"release manifest file entry {index} is not an object")
        relative = entry.get("path")
        if not isinstance(relative, str) or not relative:
            raise QuickstartError(f"release manifest file entry {index} has no valid path")
        if relative in entries:
            raise QuickstartError(f"release manifest contains duplicate path: {relative}")

        expected_sha = entry.get("sha256")
        expected_bytes = entry.get("bytes")
        expected_records = entry.get("record_count")
        if not isinstance(expected_sha, str) or re.fullmatch(r"[0-9a-f]{64}", expected_sha) is None:
            raise QuickstartError(f"release manifest has an invalid sha256 for {relative}")
        if (
            not isinstance(expected_bytes, int)
            or isinstance(expected_bytes, bool)
            or expected_bytes < 0
        ):
            raise QuickstartError(f"release manifest has an invalid byte count for {relative}")
        if (
            not isinstance(expected_records, int)
            or isinstance(expected_records, bool)
            or expected_records < 0
        ):
            raise QuickstartError(f"release manifest has an invalid record count for {relative}")
        entries[relative] = entry

    for relative in REQUIRED_DATA_FILES:
        if relative not in entries:
            raise QuickstartError(f"release manifest is missing required file entry: {relative}")
    return entries


def validate_file(path: Path, entry: dict, *, label: str) -> None:
    if not path.exists():
        raise QuickstartError(f"snapshot is missing manifest-declared file: {label}")
    try:
        actual_bytes = path.stat().st_size
    except OSError as exc:
        raise QuickstartError(f"could not inspect {label}: {exc}") from exc
    if actual_bytes != entry["bytes"]:
        raise QuickstartError(
            f"{label} byte count mismatch: manifest={entry['bytes']} actual={actual_bytes}"
        )
    actual_sha = sha256_file(path)
    if actual_sha != entry["sha256"]:
        raise QuickstartError(
            f"{label} sha256 mismatch: manifest={entry['sha256']} actual={actual_sha}"
        )
    actual_records = len(read_jsonl(path, label=label))
    if actual_records != entry["record_count"]:
        raise QuickstartError(
            f"{label} record count mismatch: "
            f"manifest={entry['record_count']} actual={actual_records}"
        )


def validate_snapshot(snapshot_dir: Path) -> tuple[dict, dict[str, dict]]:
    manifest = read_json(snapshot_dir / MANIFEST_FILE)
    entries = manifest_entries(manifest)

    for relative in REQUIRED_DATA_FILES + OPTIONAL_DATA_FILES:
        path = snapshot_dir / relative
        entry = entries.get(relative)
        if entry is not None:
            validate_file(path, entry, label=relative)
        elif path.exists():
            raise QuickstartError(
                f"snapshot contains unmanifested {relative}; remove it to avoid stale data"
            )
    return manifest, entries


def _download_to_temporary_file(url: str, directory: Path, downloader: Downloader) -> Path:
    try:
        directory.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            prefix=".download-", suffix=".tmp", dir=directory, delete=False
        ) as tmp:
            temporary_path = Path(tmp.name)
    except OSError as exc:
        raise QuickstartError(f"could not create a temporary download file: {exc}") from exc
    try:
        downloader(url, str(temporary_path))
    except Exception as exc:
        temporary_path.unlink(missing_ok=True)
        raise QuickstartError(f"download failed for {url}: {exc}") from exc
    return temporary_path


def _cache_component(value: str, *, prefix_length: int = 24) -> str:
    readable = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-.") or "snapshot"
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]
    return f"{readable[:prefix_length]}-{digest}"


def _ensure_cached_file(
    *,
    snapshot_dir: Path,
    relative: str,
    entry: dict,
    base_url: str,
    downloader: Downloader,
) -> None:
    target = snapshot_dir / relative
    if target.exists():
        try:
            validate_file(target, entry, label=relative)
            return
        except QuickstartError:
            pass

    temporary_path = _download_to_temporary_file(
        f"{base_url}/{relative}", target.parent, downloader
    )
    try:
        validate_file(temporary_path, entry, label=relative)
        try:
            temporary_path.replace(target)
        except OSError as exc:
            raise QuickstartError(f"could not update cached {relative}: {exc}") from exc
    finally:
        temporary_path.unlink(missing_ok=True)


def ensure_snapshot(
    snapshot_dir: Path | None,
    base_url: str,
    *,
    cache_dir: Path | None = None,
    downloader: Downloader | None = None,
) -> Path:
    if snapshot_dir is not None:
        validate_snapshot(snapshot_dir)
        return snapshot_dir

    normalized_base_url = base_url.rstrip("/")
    active_cache_dir = cache_dir or DEFAULT_CACHE_DIR
    active_downloader = downloader or urlretrieve
    endpoint_dir = active_cache_dir / _cache_component(normalized_base_url, prefix_length=12)

    # Always refresh the manifest. It is the authoritative pointer from a mutable
    # revision such as `main` to an immutable packaging source commit.
    temporary_manifest = _download_to_temporary_file(
        f"{normalized_base_url}/{MANIFEST_FILE}", endpoint_dir, active_downloader
    )
    try:
        manifest = read_json(temporary_manifest)
        entries = manifest_entries(manifest)
        source_commit = manifest["source_commit"].strip()
        commit_dir = endpoint_dir / _cache_component(source_commit)
        try:
            commit_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise QuickstartError(f"could not create cache directory {commit_dir}: {exc}") from exc

        for relative in REQUIRED_DATA_FILES + OPTIONAL_DATA_FILES:
            entry = entries.get(relative)
            target = commit_dir / relative
            if entry is None:
                try:
                    target.unlink(missing_ok=True)
                except OSError as exc:
                    raise QuickstartError(
                        f"could not remove stale cached {relative}: {exc}"
                    ) from exc
                continue
            _ensure_cached_file(
                snapshot_dir=commit_dir,
                relative=relative,
                entry=entry,
                base_url=normalized_base_url,
                downloader=active_downloader,
            )

        try:
            temporary_manifest.replace(commit_dir / MANIFEST_FILE)
        except OSError as exc:
            raise QuickstartError(f"could not update cached {MANIFEST_FILE}: {exc}") from exc
        validate_snapshot(commit_dir)
        return commit_dir
    finally:
        temporary_manifest.unlink(missing_ok=True)


def summarize(snapshot_dir: Path) -> None:
    manifest, entries = validate_snapshot(snapshot_dir)
    tasks = read_jsonl(snapshot_dir / "tasks.jsonl", label="tasks.jsonl")
    results = (
        read_jsonl(snapshot_dir / "result_rows.jsonl", label="result_rows.jsonl")
        if "result_rows.jsonl" in entries
        else []
    )

    tracks = Counter(task.get("track", "unknown") for task in tasks)
    models = sorted({row.get("model", "unknown") for row in results})

    print("LabCraft-Eval Hugging Face snapshot")
    print(f"source_commit: {manifest.get('source_commit')}")
    print(f"release_name: {manifest.get('release_name')}")
    print(f"tasks: {len(tasks)}")
    print("tracks:")
    for track, count in sorted(tracks.items()):
        print(f"  {track}: {count}")
    print(f"result_rows: {len(results)}")
    if "result_rows.jsonl" not in entries:
        print("evaluation_data: metadata-only")
    if models:
        print("models:")
        for model in models:
            print(f"  {model}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--snapshot-dir",
        type=Path,
        help="Existing local HF export directory. If omitted, downloads public JSON files.",
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help="Base URL for raw Hugging Face files.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        snapshot_dir = ensure_snapshot(args.snapshot_dir, args.base_url)
        summarize(snapshot_dir)
    except QuickstartError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
