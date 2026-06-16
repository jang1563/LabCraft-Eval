#!/usr/bin/env python3
"""Inspect the public LabCraft-Eval Hugging Face export.

This example intentionally uses only the Python standard library. It can read a
local export directory or download the small public JSON files from Hugging Face.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from urllib.request import urlretrieve


DEFAULT_BASE_URL = "https://huggingface.co/datasets/jang1563/LabCraft-Eval/resolve/main"
DEFAULT_CACHE_DIR = Path("build/hf_quickstart")
REQUIRED_FILES = ("release_manifest.json", "tasks.jsonl", "result_rows.jsonl")


def read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def read_jsonl(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def ensure_snapshot(snapshot_dir: Path | None, base_url: str) -> Path:
    if snapshot_dir is not None:
        return snapshot_dir

    DEFAULT_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    for filename in REQUIRED_FILES:
        target = DEFAULT_CACHE_DIR / filename
        if not target.exists():
            urlretrieve(f"{base_url.rstrip('/')}/{filename}", target)
    return DEFAULT_CACHE_DIR


def summarize(snapshot_dir: Path) -> None:
    manifest = read_json(snapshot_dir / "release_manifest.json")
    tasks = read_jsonl(snapshot_dir / "tasks.jsonl")
    results_path = snapshot_dir / "result_rows.jsonl"
    results = read_jsonl(results_path) if results_path.exists() else []

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
    snapshot_dir = ensure_snapshot(args.snapshot_dir, args.base_url)
    summarize(snapshot_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
