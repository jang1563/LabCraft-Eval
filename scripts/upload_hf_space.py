#!/usr/bin/env python3
"""Upload the LabCraft-Eval leaderboard app to a Hugging Face Space.

Dry-run is the default. Pass --execute to perform network writes.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SPACE_DIR = REPO_ROOT / "spaces" / "leaderboard"
DEFAULT_REPO_ID = "jang1563/LabCraft-Eval-Leaderboard"
REQUIRED_FILES = ("README.md", "app.py", "requirements.txt")
SKIP_DIRS = {"__pycache__"}
SKIP_SUFFIXES = {".pyc", ".pyo"}


@dataclass(frozen=True)
class SpaceFile:
    local_path: Path
    path_in_repo: str
    bytes: int


def build_space_plan(space_dir: Path) -> list[SpaceFile]:
    missing = [filename for filename in REQUIRED_FILES if not (space_dir / filename).exists()]
    if missing:
        raise FileNotFoundError("Space directory missing required files: {}".format(", ".join(missing)))

    plan = []
    for path in sorted(space_dir.rglob("*")):
        if any(part in SKIP_DIRS for part in path.relative_to(space_dir).parts):
            continue
        if path.suffix in SKIP_SUFFIXES:
            continue
        if path.is_file():
            plan.append(
                SpaceFile(
                    local_path=path,
                    path_in_repo=path.relative_to(space_dir).as_posix(),
                    bytes=path.stat().st_size,
                )
            )
    return plan


def format_bytes(num_bytes: int) -> str:
    units = ("B", "KB", "MB")
    size = float(num_bytes)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return "{:.1f} {}".format(size, unit) if unit != "B" else "{} B".format(num_bytes)
        size /= 1024
    return "{} B".format(num_bytes)


def print_plan(space_dir: Path, repo_id: str, plan: list[SpaceFile]) -> None:
    total_bytes = sum(item.bytes for item in plan)
    print("HF Space upload plan")
    print("- space_dir: {}".format(space_dir))
    print("- repo_id: {}".format(repo_id))
    print("- files: {} ({})".format(len(plan), format_bytes(total_bytes)))
    for item in plan:
        print("  - {} <- {} ({})".format(item.path_in_repo, item.local_path, format_bytes(item.bytes)))


def upload_space(
    *,
    plan: list[SpaceFile],
    repo_id: str,
    commit_message: str,
    private: bool,
) -> str:
    try:
        from huggingface_hub import CommitOperationAdd, HfApi
    except ModuleNotFoundError as exc:  # pragma: no cover - optional dependency
        raise RuntimeError(
            "huggingface_hub is required for --execute. Install it first, for example: "
            "uv pip install 'huggingface-hub>=0.36,<1.0'"
        ) from exc

    api = HfApi()
    api.create_repo(
        repo_id=repo_id,
        repo_type="space",
        space_sdk="gradio",
        private=private,
        exist_ok=True,
    )
    operations = [
        CommitOperationAdd(
            path_in_repo=item.path_in_repo,
            path_or_fileobj=str(item.local_path),
        )
        for item in plan
    ]
    commit_info = api.create_commit(
        repo_id=repo_id,
        repo_type="space",
        operations=operations,
        commit_message=commit_message,
    )
    return str(getattr(commit_info, "commit_url", commit_info))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--space-dir", type=Path, default=DEFAULT_SPACE_DIR)
    parser.add_argument("--repo-id", default=DEFAULT_REPO_ID)
    parser.add_argument("--commit-message", default="Upload LabCraft-Eval leaderboard Space")
    parser.add_argument("--private", action="store_true")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()

    space_dir = args.space_dir.resolve()
    try:
        plan = build_space_plan(space_dir)
    except Exception as exc:
        print("Refusing to upload invalid Space directory: {}".format(exc), file=sys.stderr)
        return 1

    print_plan(space_dir, args.repo_id, plan)
    if not args.execute:
        print("Dry-run only. Re-run with --execute to upload.")
        return 0

    commit_url = upload_space(
        plan=plan,
        repo_id=args.repo_id,
        commit_message=args.commit_message,
        private=args.private,
    )
    print("Upload complete: {}".format(commit_url))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
