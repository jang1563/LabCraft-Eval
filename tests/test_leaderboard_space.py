import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

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
    assert rows[0]["overall_std"] == pytest.approx(0.3535533906)
    assert rows[0]["decision_quality"] == 0.75


def test_score_summary_displays_resolved_model_for_current_rows():
    app = load_space_app()
    rows = sample_results()
    for row in rows:
        row.update(
            {
                "model": "anthropic/claude-sonnet-5",
                "requested_model": "anthropic/claude-sonnet-5",
                "resolved_model": "claude-sonnet-5-20260701",
                "provider": "anthropic",
            }
        )

    summary = app.summarize_scores(rows, "snapshot")

    assert summary[0]["model"] == (
        "anthropic/claude-sonnet-5 → anthropic/claude-sonnet-5-20260701"
    )


def test_current_snapshot_model_provenance_fails_closed_on_mixed_resolution():
    app = load_space_app()
    rows = sample_results()
    for index, row in enumerate(rows):
        row.update(
            {
                "model": "anthropic/claude-sonnet-5",
                "requested_model": "anthropic/claude-sonnet-5",
                "resolved_model": "claude-sonnet-5-202607{:02d}".format(index + 1),
                "provider": "anthropic",
                "model_generate_config": {"max_tokens": 8192},
                "effective_generation_config": {"max_tokens": 8192},
                "inspect_version": "0.3.245",
            }
        )

    errors = app.validate_model_provenance({"schema_version": "0.3.0"}, rows)

    assert any("resolves to multiple snapshots" in error for error in errors)


def test_legacy_snapshot_model_provenance_remains_readable():
    app = load_space_app()

    assert app.validate_model_provenance(
        {"schema_version": "0.2.0"}, sample_results()
    ) == []


def test_snapshot_validation_checks_manifest_hashes_and_counts(tmp_path):
    app = load_space_app()
    payloads = {
        "tasks.jsonl": '{"task_id":"transform_01"}\n',
        "result_rows.jsonl": '{"sample_id":"s0"}\n',
        "eval_log_manifest.jsonl": '{"path":"logs/example.eval"}\n',
    }
    for relative, content in payloads.items():
        path = tmp_path / relative
        path.write_text(content)
    for relative in app.PLOT_FILES:
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"plot")

    files = []
    for relative in app.REQUIRED_FILES[1:] + app.PLOT_FILES:
        path = tmp_path / relative
        files.append(
            {
                "path": relative,
                "sha256": app.sha256_file(path),
                "bytes": path.stat().st_size,
                "record_count": (
                    len(app.read_jsonl(path)) if path.suffix == ".jsonl" else 1
                ),
            }
        )
    (tmp_path / "release_manifest.json").write_text(json.dumps({"files": files}))

    app.validate_snapshot(tmp_path)
    (tmp_path / "result_rows.jsonl").write_text('{"sample_id":"tampered"}\n')

    with pytest.raises(RuntimeError, match="sha256 mismatch for result_rows.jsonl"):
        app.validate_snapshot(tmp_path)


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
