import json
import subprocess
import sys

import pytest

from scripts import export_hf_dataset
from scripts import upload_hf_dataset


@pytest.fixture(autouse=True)
def _clean_packaging_worktree(monkeypatch):
    monkeypatch.setattr(export_hf_dataset, "require_clean_packaging_worktree", lambda: None)


def test_build_upload_plan_includes_manifest_and_export_files(tmp_path):
    out_dir = tmp_path / "hf_export"
    export_hf_dataset.build_export(
        out_dir=out_dir,
        release_name="unit_metadata_only",
        log_dirs=[tmp_path / "missing_logs"],
        include_results=False,
    )

    plan = upload_hf_dataset.build_upload_plan(out_dir)
    paths = [item.path_in_repo for item in plan]

    assert paths[0] == "release_manifest.json"
    assert "README.md" in paths
    assert "tasks.jsonl" in paths
    assert "citations.jsonl" in paths
    assert len(paths) == len(set(paths))


def test_build_upload_plan_rejects_external_symlink(tmp_path):
    out_dir = tmp_path / "hf_export"
    export_hf_dataset.build_export(
        out_dir=out_dir,
        release_name="unit_metadata_only",
        log_dirs=[],
        include_results=False,
    )
    external_path = tmp_path / "outside.jsonl"
    external_path.write_text("{}\n")
    alias_path = out_dir / "external.jsonl"
    alias_path.symlink_to(external_path)

    manifest_path = out_dir / "release_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["files"].append(
        {
            "path": "external.jsonl",
            "sha256": export_hf_dataset.sha256_file(external_path),
            "bytes": external_path.stat().st_size,
            "record_count": 1,
        }
    )
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")

    with pytest.raises(ValueError, match="escapes export directory via symlink"):
        upload_hf_dataset.build_upload_plan(out_dir)


def test_stale_remote_paths_preserves_only_hf_attributes(tmp_path):
    plan = [
        upload_hf_dataset.UploadFile(
            local_path=tmp_path / "README.md",
            path_in_repo="README.md",
            bytes=1,
        )
    ]

    stale = upload_hf_dataset.stale_remote_paths(
        [".gitattributes", "README.md", "result_rows.jsonl", "plots/old.png"],
        plan,
    )

    assert stale == ["plots/old.png", "result_rows.jsonl"]


def test_upload_helper_dry_run_validates_and_prints_plan(tmp_path):
    out_dir = tmp_path / "hf_export"
    export_hf_dataset.build_export(
        out_dir=out_dir,
        release_name="unit_metadata_only",
        log_dirs=[tmp_path / "missing_logs"],
        include_results=False,
    )

    result = subprocess.run(
        [
            sys.executable,
            "scripts/upload_hf_dataset.py",
            str(out_dir),
            "--repo-id",
            "example/LabCraft-Eval",
        ],
        cwd=export_hf_dataset.REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "HF dataset upload plan" in result.stdout
    assert "Dry-run only" in result.stdout
    assert "release_manifest.json" in result.stdout


def test_upload_helper_rejects_invalid_export(tmp_path):
    out_dir = tmp_path / "not_an_export"
    out_dir.mkdir()

    result = subprocess.run(
        [
            sys.executable,
            "scripts/upload_hf_dataset.py",
            str(out_dir),
            "--repo-id",
            "example/LabCraft-Eval",
        ],
        cwd=export_hf_dataset.REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "Refusing to upload invalid HF export" in result.stderr
