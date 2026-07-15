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
            "eval_log_path": "logs/s0.eval",
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
            "eval_log_path": "logs/s1.eval",
            "scores": {
                "overall": 1.0,
                "decision_quality": 1.0,
                "task_success": 1.0,
                "troubleshooting": 1.0,
                "efficiency": 1.0,
            },
        },
    ]


def sample_logs():
    return [{"path": "logs/s0.eval"}, {"path": "logs/s1.eval"}]


def write_snapshot_manifest(
    app,
    snapshot_dir: Path,
    *,
    release_name: str,
    schema_version: str,
    relative_paths: list[str],
):
    files = []
    for relative in relative_paths:
        path = snapshot_dir / relative
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
    manifest = {
        "release_name": release_name,
        "source_commit": app.RELEASES[release_name]["expected_source_commit"],
        "schema_version": schema_version,
        "files": files,
    }
    (snapshot_dir / "release_manifest.json").write_text(json.dumps(manifest))
    return manifest


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


def test_default_release_is_current_metadata_only():
    app = load_space_app()

    assert app.DEFAULT_REVISION == "v0.1.2"
    assert "Current metadata" in app.DEFAULT_RELEASE_LABEL
    assert app.RELEASES["v0.1.2"]["score_bearing"] is False
    assert "Historical provisional" in app.RELEASES["v0.1.1"]["selector_label"]


def test_metadata_only_snapshot_loads_without_results_logs_or_plots(tmp_path):
    app = load_space_app()
    (tmp_path / "tasks.jsonl").write_text(
        '{"task_id":"transform_01","track":"snapshot"}\n'
    )
    manifest = write_snapshot_manifest(
        app,
        tmp_path,
        release_name="v0.1.2",
        schema_version="0.3.0",
        relative_paths=["tasks.jsonl"],
    )

    loaded_manifest, tasks, results, logs = app.load_snapshot(
        tmp_path,
        revision="v0.1.2",
    )
    plot_note, score_plot, axis_plot = app.plot_view(tmp_path, manifest, results)

    assert loaded_manifest == manifest
    assert len(tasks) == 1
    assert results == []
    assert logs == []
    assert "No score-bearing plots" in plot_note
    assert score_plot is None
    assert axis_plot is None


def test_current_evidence_banner_and_empty_score_view_are_explicit():
    app = load_space_app()
    manifest = {
        "release_name": "v0.1.2",
        "source_commit": "abc123",
        "schema_version": "0.3.0",
        "files": [{"path": "tasks.jsonl"}],
    }

    evidence = app.evidence_markdown("v0.1.2", manifest, [])
    _title, scores, axes, inventory = app.render_track(
        "snapshot",
        manifest,
        sample_tasks(),
        [],
        [],
        revision="v0.1.2",
    )

    assert "Evidence tier: Current · metadata-only" in evidence
    assert "no published result rows" in evidence
    assert "No score-bearing evidence" in scores
    assert "No score-bearing evidence" in axes
    assert "Pinned revision | `v0.1.2`" in inventory


def test_snapshot_validation_checks_manifest_hashes_and_counts(tmp_path):
    app = load_space_app()
    payloads = {
        "tasks.jsonl": '{"task_id":"transform_01"}\n',
        "result_rows.jsonl": json.dumps(sample_results()[0]) + "\n",
        "eval_log_manifest.jsonl": json.dumps(sample_logs()[0]) + "\n",
    }
    for relative, content in payloads.items():
        path = tmp_path / relative
        path.write_text(content)
    for relative in app.PLOT_FILES:
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"plot")

    write_snapshot_manifest(
        app,
        tmp_path,
        release_name="v0.1.1",
        schema_version="0.1.0",
        relative_paths=list(payloads) + list(app.PLOT_FILES),
    )

    app.validate_snapshot(tmp_path, revision="v0.1.1")
    (tmp_path / "result_rows.jsonl").write_text('{"sample_id":"tampered"}\n')

    with pytest.raises(RuntimeError, match="sha256 mismatch for result_rows.jsonl"):
        app.validate_snapshot(tmp_path, revision="v0.1.1")


def test_score_bearing_snapshot_can_omit_plots_gracefully(tmp_path):
    app = load_space_app()
    (tmp_path / "tasks.jsonl").write_text(
        '{"task_id":"transform_01","track":"snapshot"}\n'
    )
    (tmp_path / "result_rows.jsonl").write_text(
        json.dumps(sample_results()[0]) + "\n"
    )
    (tmp_path / "eval_log_manifest.jsonl").write_text(
        json.dumps(sample_logs()[0]) + "\n"
    )
    manifest = write_snapshot_manifest(
        app,
        tmp_path,
        release_name="v0.1.1",
        schema_version="0.1.0",
        relative_paths=[
            "tasks.jsonl",
            "result_rows.jsonl",
            "eval_log_manifest.jsonl",
        ],
    )

    _manifest, _tasks, results, _logs = app.load_snapshot(
        tmp_path,
        revision="v0.1.1",
    )
    plot_note, score_plot, axis_plot = app.plot_view(tmp_path, manifest, results)

    assert "No plot artifacts" in plot_note
    assert score_plot is None
    assert axis_plot is None


def test_revision_and_download_paths_are_allowlisted():
    app = load_space_app()
    manifest = {
        "files": [
            {"path": "tasks.jsonl"},
            {"path": "eval_log_manifest.jsonl"},
            {"path": "plots/scorecard.png"},
        ]
    }

    assert app.resolve_url("tasks.jsonl", revision="v0.1.2").endswith(
        "/resolve/b320a569a74986110c5a4aba32c970d406f4ae08/tasks.jsonl"
    )
    assert app.snapshot_download_paths(manifest) == (
        "tasks.jsonl",
        "eval_log_manifest.jsonl",
    )
    with pytest.raises(ValueError, match="Unsupported leaderboard revision"):
        app.resolve_url("tasks.jsonl", revision="main")
    with pytest.raises(ValueError, match="Unsupported leaderboard file"):
        app.resolve_url("../secrets", revision="v0.1.2")


def test_snapshot_identity_is_bound_to_expected_source_commit(tmp_path):
    app = load_space_app()
    (tmp_path / "tasks.jsonl").write_text(
        '{"task_id":"transform_01","track":"snapshot"}\n'
    )
    manifest = write_snapshot_manifest(
        app,
        tmp_path,
        release_name="v0.1.2",
        schema_version="0.3.0",
        relative_paths=["tasks.jsonl"],
    )
    manifest["source_commit"] = "moved-tag"
    (tmp_path / "release_manifest.json").write_text(json.dumps(manifest))

    with pytest.raises(RuntimeError, match="source commit does not match"):
        app.validate_snapshot(tmp_path, revision="v0.1.2")


def test_snapshot_rejects_missing_record_count(tmp_path):
    app = load_space_app()
    (tmp_path / "tasks.jsonl").write_text(
        '{"task_id":"transform_01","track":"snapshot"}\n'
    )
    manifest = write_snapshot_manifest(
        app,
        tmp_path,
        release_name="v0.1.2",
        schema_version="0.3.0",
        relative_paths=["tasks.jsonl"],
    )
    manifest["files"][0].pop("record_count")
    (tmp_path / "release_manifest.json").write_text(json.dumps(manifest))

    with pytest.raises(RuntimeError, match="invalid or missing record_count"):
        app.validate_snapshot(tmp_path, revision="v0.1.2")


def test_score_evidence_rejects_invalid_scores_duplicates_and_missing_logs():
    app = load_space_app()
    rows = sample_results()
    rows[0]["scores"]["overall"] = True
    rows.append(dict(rows[1]))

    errors = app.validate_score_evidence(rows, sample_logs())

    assert any("finite and within" in error for error in errors)
    assert any("duplicate model/task/sample_id" in error for error in errors)
    assert any("zero eval-log rows" in error for error in app.validate_score_evidence(rows, []))


def test_available_tracks_retains_unknown_tracks():
    app = load_space_app()

    tracks = app.available_tracks(
        [{"track": "snapshot"}, {"track": "future_track"}],
        [{"track": "another_track"}],
    )

    assert tracks == ["snapshot", "another_track", "future_track"]


def test_valid_immutable_cache_is_reused_without_network(tmp_path, monkeypatch):
    app = load_space_app()
    (tmp_path / "tasks.jsonl").write_text(
        '{"task_id":"transform_01","track":"snapshot"}\n'
    )
    write_snapshot_manifest(
        app,
        tmp_path,
        release_name="v0.1.2",
        schema_version="0.3.0",
        relative_paths=["tasks.jsonl"],
    )

    def fail_download(*_args, **_kwargs):
        raise AssertionError("network should not be used for a valid immutable cache")

    monkeypatch.setattr(app, "_download_atomic", fail_download)

    assert app.ensure_snapshot(tmp_path, revision="v0.1.2") == tmp_path


def test_release_snapshot_loads_historical_only_on_first_selection(monkeypatch):
    app = load_space_app()
    calls = []

    def fake_ensure(*, revision):
        calls.append(revision)
        return Path(revision)

    def fake_load(path, *, revision):
        return ({"release_name": revision}, [], [], [])

    monkeypatch.setattr(app, "ensure_snapshot", fake_ensure)
    monkeypatch.setattr(app, "load_snapshot", fake_load)
    snapshots = {}

    app.get_release_snapshot(snapshots, "v0.1.2")
    app.get_release_snapshot(snapshots, "v0.1.2")
    assert calls == ["v0.1.2"]

    app.get_release_snapshot(snapshots, "v0.1.1")
    assert calls == ["v0.1.2", "v0.1.1"]


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
        revision="v0.1.1",
    )

    assert "Frozen simulator snapshot" in title
    assert "model-a" in scores
    assert "overall" in axes
    assert "abc123" in inventory
    assert "transform_01" in inventory
    assert "Historical · provisional score-bearing" in inventory


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
