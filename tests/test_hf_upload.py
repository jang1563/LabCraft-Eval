import subprocess
import sys

from scripts import export_hf_dataset
from scripts import upload_hf_dataset


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
