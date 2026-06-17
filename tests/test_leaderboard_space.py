import importlib.util
from pathlib import Path
import subprocess
import sys

from scripts import upload_hf_space


ROOT = Path(__file__).resolve().parents[1]
APP_PATH = ROOT / "spaces" / "leaderboard" / "app.py"


def load_space_app():
    spec = importlib.util.spec_from_file_location("labcraft_leaderboard_app", APP_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def sample_tasks():
    return [
        {
            "task_id": "transform_01",
            "track": "snapshot",
            "task_title": "Transformation",
            "domain": "Transformation",
            "objective": "Measure CFU.",
        },
        {
            "task_id": "target_validate_01",
            "track": "discovery",
            "task_title": "Target validation",
            "domain": "Discovery",
            "objective": "Choose assay.",
        },
    ]


def sample_results():
    return [
        {
            "model": "model-a",
            "task": "transform_01",
            "track": "snapshot",
            "sample_id": "s0",
            "scores": {
                "overall": 0.5,
                "decision_quality": 0.5,
                "task_success": 0.5,
                "troubleshooting": 0.5,
                "efficiency": 0.5,
            },
        },
        {
            "model": "model-a",
            "task": "transform_01",
            "track": "snapshot",
            "sample_id": "s1",
            "scores": {
                "overall": 1.0,
                "decision_quality": 1.0,
                "task_success": 1.0,
                "troubleshooting": 1.0,
                "efficiency": 1.0,
            },
        },
    ]


def test_score_summary_groups_by_model_task_and_track():
    app = load_space_app()

    rows = app.summarize_scores(sample_results(), "snapshot")

    assert len(rows) == 1
    assert rows[0]["model"] == "model-a"
    assert rows[0]["task"] == "transform_01"
    assert rows[0]["n"] == 2
    assert rows[0]["overall_mean"] == 0.75
    assert rows[0]["decision_quality"] == 0.75


def test_render_track_includes_tables_and_provenance():
    app = load_space_app()
    manifest = {
        "release_name": "unit",
        "source_commit": "abc123",
        "schema_version": "0.1.0",
        "files": [{"path": "result_rows.jsonl"}],
    }

    title, scores, axes, inventory = app.render_track(
        "snapshot",
        manifest,
        sample_tasks(),
        sample_results(),
        [{"path": "logs/example.eval"}],
    )

    assert "Frozen simulator snapshot" in title
    assert "model-a" in scores
    assert "overall" in axes
    assert "abc123" in inventory
    assert "transform_01" in inventory


def test_space_upload_plan_includes_required_files():
    plan = upload_hf_space.build_space_plan(ROOT / "spaces" / "leaderboard")
    paths = [item.path_in_repo for item in plan]

    assert paths == sorted(paths)
    assert "README.md" in paths
    assert "app.py" in paths
    assert "requirements.txt" in paths


def test_space_upload_helper_dry_run_prints_plan():
    result = subprocess.run(
        [
            sys.executable,
            "scripts/upload_hf_space.py",
            "--repo-id",
            "example/LabCraft-Eval-Leaderboard",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "HF Space upload plan" in result.stdout
    assert "Dry-run only" in result.stdout
    assert "app.py" in result.stdout
