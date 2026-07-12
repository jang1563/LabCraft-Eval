#!/usr/bin/env python3
"""Upload a validated LabCraft-Eval export bundle to a Hugging Face dataset repo.

Dry-run is the default. Pass --execute to perform network writes.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import sys

try:
    from validate_hf_export import load_json, resolve_bundle_path, validate_export
except ModuleNotFoundError:  # pragma: no cover - used when imported as scripts.upload_hf_dataset
    from scripts.validate_hf_export import load_json, resolve_bundle_path, validate_export


@dataclass(frozen=True)
class UploadFile:
    local_path: Path
    path_in_repo: str
    bytes: int


PRESERVED_REMOTE_PATHS = {".gitattributes"}


def build_upload_plan(export_dir: Path) -> list[UploadFile]:
    """Return manifest-backed files to upload, including release_manifest.json."""
    try:
        export_dir = export_dir.resolve()
    except (OSError, RuntimeError) as exc:
        raise ValueError("export directory cannot be resolved safely") from exc
    manifest_path = resolve_bundle_path(export_dir, "release_manifest.json")
    manifest = load_json(manifest_path)

    plan = [
        UploadFile(
            local_path=manifest_path,
            path_in_repo="release_manifest.json",
            bytes=manifest_path.stat().st_size,
        )
    ]
    seen = {"release_manifest.json"}
    for file_record in manifest["files"]:
        path_in_repo = file_record["path"]
        if path_in_repo in seen:
            raise ValueError("Duplicate upload path: {}".format(path_in_repo))
        seen.add(path_in_repo)
        local_path = resolve_bundle_path(export_dir, path_in_repo)
        plan.append(
            UploadFile(
                local_path=local_path,
                path_in_repo=path_in_repo,
                bytes=local_path.stat().st_size,
            )
        )
    return plan


def format_bytes(num_bytes: int) -> str:
    units = ("B", "KB", "MB", "GB")
    size = float(num_bytes)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return "{:.1f} {}".format(size, unit) if unit != "B" else "{} B".format(num_bytes)
        size /= 1024
    return "{} B".format(num_bytes)


def stale_remote_paths(remote_paths: list[str], plan: list[UploadFile]) -> list[str]:
    """Return remote files that are not part of the exact manifest-backed snapshot."""
    planned = {item.path_in_repo for item in plan}
    return sorted(
        path
        for path in remote_paths
        if path not in planned and path not in PRESERVED_REMOTE_PATHS
    )


def print_plan(export_dir: Path, repo_id: str, revision: str | None, plan: list[UploadFile]) -> None:
    total_bytes = sum(item.bytes for item in plan)
    print("HF dataset upload plan")
    print("- export_dir: {}".format(export_dir))
    print("- repo_id: {}".format(repo_id))
    print("- revision: {}".format(revision or "default"))
    print("- mode: exact manifest replacement (preserves .gitattributes)")
    print("- files: {} ({})".format(len(plan), format_bytes(total_bytes)))
    for item in plan:
        print("  - {} <- {} ({})".format(item.path_in_repo, item.local_path, format_bytes(item.bytes)))


def upload_plan(
    *,
    plan: list[UploadFile],
    repo_id: str,
    revision: str | None,
    commit_message: str,
    create_repo: bool,
    private: bool,
) -> tuple[str, list[str]]:
    try:
        from huggingface_hub import CommitOperationAdd, CommitOperationDelete, HfApi
    except ModuleNotFoundError as exc:  # pragma: no cover - optional dependency
        raise RuntimeError(
            "huggingface_hub is required for --execute. Install it in the active "
            "environment first, for example: "
            "uv pip install 'huggingface-hub>=0.36,<1.0'"
        ) from exc

    api = HfApi()
    if create_repo:
        api.create_repo(
            repo_id=repo_id,
            repo_type="dataset",
            private=private,
            exist_ok=True,
        )

    remote_paths = api.list_repo_files(
        repo_id=repo_id,
        repo_type="dataset",
        revision=revision,
    )
    stale_paths = stale_remote_paths(remote_paths, plan)
    operations = [CommitOperationDelete(path_in_repo=path) for path in stale_paths]
    operations.extend(
        [
            CommitOperationAdd(
                path_in_repo=item.path_in_repo,
                path_or_fileobj=str(item.local_path),
            )
            for item in plan
        ]
    )
    commit_info = api.create_commit(
        repo_id=repo_id,
        repo_type="dataset",
        operations=operations,
        commit_message=commit_message,
        revision=revision,
    )
    return str(getattr(commit_info, "commit_url", commit_info)), stale_paths


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("export_dir", help="Validated HF export directory.")
    parser.add_argument("--repo-id", required=True, help="HF dataset repo id, e.g. user/name.")
    parser.add_argument("--revision", default=None, help="Branch or revision to upload to.")
    parser.add_argument(
        "--commit-message",
        default="Upload LabCraft-Eval dataset export",
    )
    parser.add_argument("--create-repo", action="store_true")
    parser.add_argument("--private", action="store_true")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Perform the upload. Without this flag, only print a dry-run plan.",
    )
    args = parser.parse_args()

    export_dir = Path(args.export_dir).resolve()
    errors = validate_export(export_dir)
    if errors:
        print("Refusing to upload invalid HF export:", file=sys.stderr)
        for error in errors:
            print("- {}".format(error), file=sys.stderr)
        return 1

    plan = build_upload_plan(export_dir)
    print_plan(export_dir, args.repo_id, args.revision, plan)

    if not args.execute:
        print("Dry-run only. Re-run with --execute to upload.")
        return 0

    commit_url, deleted_paths = upload_plan(
        plan=plan,
        repo_id=args.repo_id,
        revision=args.revision,
        commit_message=args.commit_message,
        create_repo=args.create_repo,
        private=args.private,
    )
    if deleted_paths:
        print("Removed stale remote files: {}".format(", ".join(deleted_paths)))
    print("Upload complete: {}".format(commit_url))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
