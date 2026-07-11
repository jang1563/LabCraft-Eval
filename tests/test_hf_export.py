import json
import sys

import pytest

from scripts import export_hf_dataset
from scripts import validate_hf_export

_REAL_REQUIRE_CLEAN_PACKAGING_WORKTREE = export_hf_dataset.require_clean_packaging_worktree


@pytest.fixture(autouse=True)
def _clean_packaging_worktree(monkeypatch):
    monkeypatch.setattr(export_hf_dataset, "require_clean_packaging_worktree", lambda: None)


def _result_row(eval_path, *, dirty=False):
    return {
        "model": "openai/gpt-4o-mini",
        "requested_model": "openai/gpt-4o-mini",
        "resolved_model": "gpt-4o-mini-2024-07-18",
        "provider": "openai",
        "task": "transform_01",
        "status": "success",
        "sample_id": "transform_01_seed_00",
        "created": "2026-07-10T00:00:00+00:00",
        "eval_log": eval_path.name,
        "eval_log_path": str(eval_path),
        "tokens": {"input": 10, "output": 5, "total": 15},
        "overall": 0.75,
        "task_success": 1.0,
        "eval_revision": {
            "type": "git",
            "origin": "https://github.com/jang1563/LabCraft-Eval.git",
            "commit": "abc123",
            "dirty": dirty,
        },
        "model_generate_config": {"temperature": 0.0},
        "effective_generation_config": {"temperature": 0.0},
        "inspect_version": "0.3.245",
    }


def _refresh_manifest_file(out_dir, path_value):
    path = out_dir / path_value
    manifest_path = out_dir / "release_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    for item in manifest["files"]:
        if item["path"] == path_value:
            item["sha256"] = export_hf_dataset.sha256_file(path)
            item["bytes"] = path.stat().st_size
            if path.suffix == ".jsonl":
                item["record_count"] = len(path.read_text().splitlines())
            break
    else:  # pragma: no cover - test helper guard
        raise AssertionError("manifest has no file entry for {}".format(path_value))
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")


def test_packaging_worktree_check_rejects_dirty_status(monkeypatch):
    class Completed:
        stdout = " M scripts/export_hf_dataset.py\n"

    monkeypatch.setattr(export_hf_dataset.subprocess, "run", lambda *_args, **_kwargs: Completed())

    with pytest.raises(ValueError, match="dirty packaging worktree"):
        _REAL_REQUIRE_CLEAN_PACKAGING_WORKTREE()


def test_classify_task_tracks_known_surfaces():
    assert export_hf_dataset.classify_task("transform_01") == "snapshot"
    assert export_hf_dataset.classify_task("golden_gate_01") == "current_wet_lab"
    assert export_hf_dataset.classify_task("followup_01") == "followup"
    assert export_hf_dataset.classify_task("target_validate_01") == "discovery"
    assert export_hf_dataset.classify_task("safety_case_01") == "safety_case"
    assert export_hf_dataset.classify_task("unknown_task") == "other"


def test_dataset_card_text_includes_hf_metadata_and_manifest_pointers():
    text = export_hf_dataset.dataset_card_text(
        release_name="unit_test",
        commit="abc123",
        repository="https://github.com/jang1563/LabCraft-Eval.git",
        task_count=14,
        citation_count=178,
        result_count=0,
        plot_count=0,
        include_results=False,
        include_plots=False,
    )

    assert text.startswith("---\n")
    assert "pretty_name: LabCraft-Eval" in text
    assert "license: cc-by-nc-4.0" in text
    assert "- inspect-ai" in text
    assert "configs:" in text
    assert "config_name: tasks" in text
    assert "config_name: eval_log_manifest" in text
    assert "config_name: result_rows" not in text
    assert "release_manifest.json" in text
    assert "## Dataset Viewer" in text
    assert "## Provenance and Verification" in text
    assert "## Data Fields" in text
    assert "## Known Limitations" in text
    assert "## Contact" in text
    assert "`result_rows.jsonl` | one row per deduplicated scored sample" in text
    assert "omitted from this metadata-only export" in text
    assert 'intentionally has no "result_rows.jsonl"' in text
    assert "results = [" not in text
    assert "`plots/`: omitted" in text
    assert "metadata license field reflects the uploaded benchmark-content" in text
    assert "abc123" in text


def test_dataset_card_text_includes_result_viewer_config_when_results_present():
    text = export_hf_dataset.dataset_card_text(
        release_name="unit_test",
        commit="abc123",
        repository="https://github.com/jang1563/LabCraft-Eval.git",
        task_count=14,
        citation_count=178,
        result_count=100,
        plot_count=2,
        include_results=True,
        include_plots=True,
    )

    assert "config_name: result_rows" in text
    assert "path: result_rows.jsonl" in text
    assert "Exported result rows: 100" in text
    assert "`eval_logs/`: raw Inspect `.eval` evidence" in text
    assert "`plots/`: copied PNG plot files" in text


def test_build_export_metadata_only_writes_card_jsonl_and_manifest(tmp_path):
    out_dir = tmp_path / "hf_export"
    manifest = export_hf_dataset.build_export(
        out_dir=out_dir,
        release_name="unit_metadata_only",
        log_dirs=[tmp_path / "missing_logs"],
        include_results=False,
    )

    assert (out_dir / "README.md").exists()
    assert (out_dir / "tasks.jsonl").exists()
    assert (out_dir / "release_manifest.json").exists()
    assert not (out_dir / "result_rows.jsonl").exists()

    task_lines = (out_dir / "tasks.jsonl").read_text().splitlines()
    citation_lines = (out_dir / "citations.jsonl").read_text().splitlines()
    assert len(task_lines) == 14
    assert len(citation_lines) >= 1

    manifest_payload = json.loads((out_dir / "release_manifest.json").read_text())
    assert manifest_payload["release_name"] == "unit_metadata_only"
    assert manifest_payload["files"] == manifest["files"]
    assert {item["path"] for item in manifest_payload["files"]} == {
        "README.md",
        "tasks.jsonl",
        "rubrics.jsonl",
        "ground_truth.jsonl",
        "citations.jsonl",
        "eval_log_manifest.jsonl",
    }


def test_build_export_can_copy_plot_assets(tmp_path):
    plot_path = tmp_path / "scorecard.png"
    plot_path.write_bytes(b"fake-png")
    out_dir = tmp_path / "hf_export_with_plot"

    manifest = export_hf_dataset.build_export(
        out_dir=out_dir,
        release_name="unit_plot_export",
        log_dirs=[tmp_path / "missing_logs"],
        include_results=False,
        copy_plots=True,
        plot_paths=[plot_path],
    )

    exported_plot = out_dir / "plots" / "scorecard.png"
    assert exported_plot.read_bytes() == b"fake-png"

    readme = (out_dir / "README.md").read_text()
    assert "Exported plot files: 1" in readme
    assert "`plots/`: copied PNG plot files" in readme

    plot_entries = [
        item for item in manifest["files"] if item["path"].endswith("plots/scorecard.png")
    ]
    assert len(plot_entries) == 1
    assert plot_entries[0]["path"] == "plots/scorecard.png"
    assert plot_entries[0]["source_path"] == plot_path.name


def test_result_records_fails_for_missing_log_dir(tmp_path):
    with pytest.raises(FileNotFoundError, match="Result log directory does not exist"):
        export_hf_dataset.result_records("abc123", [tmp_path / "missing_logs"])


def test_result_records_fails_for_empty_log_dir(tmp_path):
    log_dir = tmp_path / "logs"
    log_dir.mkdir()

    with pytest.raises(ValueError, match="No .eval logs found"):
        export_hf_dataset.result_records("abc123", [log_dir])


def test_result_records_fails_when_eval_log_has_no_scores(tmp_path, monkeypatch):
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    eval_path = log_dir / "empty.eval"
    eval_path.write_text("not a real inspect log")
    monkeypatch.setattr(export_hf_dataset, "extract_scores", lambda *_args, **_kwargs: [])

    with pytest.raises(ValueError, match="No scored samples found"):
        export_hf_dataset.result_records("abc123", [log_dir])


def test_result_records_rejects_dirty_evaluation_revision(tmp_path, monkeypatch):
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    eval_path = log_dir / "dirty.eval"
    eval_path.write_text("fixture")
    monkeypatch.setattr(
        export_hf_dataset,
        "extract_scores",
        lambda *_args, **_kwargs: [_result_row(eval_path, dirty=True)],
    )

    with pytest.raises(ValueError, match="dirty evaluation revision"):
        export_hf_dataset.result_records("packaging123", [log_dir])


def test_result_records_rejects_empty_generation_config(tmp_path, monkeypatch):
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    eval_path = log_dir / "unconfigured.eval"
    eval_path.write_text("fixture")
    row = _result_row(eval_path)
    row["model_generate_config"] = {}
    monkeypatch.setattr(
        export_hf_dataset,
        "extract_scores",
        lambda *_args, **_kwargs: [row],
    )

    with pytest.raises(ValueError, match="no pinned model generation config"):
        export_hf_dataset.result_records("packaging123", [log_dir])


def test_result_records_preserves_native_evaluation_revision(tmp_path, monkeypatch):
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    eval_path = log_dir / "clean.eval"
    eval_path.write_text("fixture")
    monkeypatch.setattr(
        export_hf_dataset,
        "extract_scores",
        lambda *_args, **_kwargs: [_result_row(eval_path)],
    )

    records = export_hf_dataset.result_records("packaging123", [log_dir])

    assert records[0]["source_commit"] == "packaging123"
    assert records[0]["evaluation_revision"] == {
        "type": "git",
        "origin": "https://github.com/jang1563/LabCraft-Eval.git",
        "commit": "abc123",
        "dirty": False,
    }
    assert records[0]["model_generate_config"] == {"temperature": 0.0}
    assert records[0]["effective_generation_config"] == {"temperature": 0.0}
    assert records[0]["requested_model"] == "openai/gpt-4o-mini"
    assert records[0]["resolved_model"] == "gpt-4o-mini-2024-07-18"
    assert records[0]["provider"] == "openai"
    assert records[0]["inspect_version"] == "0.3.245"
    assert records[0]["tokens"] == {"input": 10, "output": 5, "total": 15}


def test_result_schema_keeps_0_2_records_backward_compatible():
    legacy = {
        "schema_version": "0.2.0",
        "source_commit": "abc123",
        "evaluation_revision": {
            "type": "git",
            "origin": "https://github.com/jang1563/LabCraft-Eval.git",
            "commit": "abc123",
            "dirty": False,
        },
        "model_generate_config": {"temperature": 0.0},
        "model": "openai/gpt-4o-mini",
        "task": "transform_01",
        "track": "snapshot",
        "sample_id": "transform_01_seeded_seed_00",
        "eval_log": "example.eval",
        "eval_log_path": "eval_logs/example.eval",
        "status": "success",
        "created": "2026-04-18T10:00:00Z",
        "tokens": {"input": 10, "output": 5, "total": 15},
        "scores": {"overall": 0.75},
    }

    assert validate_hf_export.validate_json_schema(
        legacy,
        "hf_result_record.schema.json",
        "legacy result",
    ) == []

    current_without_model_provenance = dict(legacy, schema_version="0.3.0")
    errors = validate_hf_export.validate_json_schema(
        current_without_model_provenance,
        "hf_result_record.schema.json",
        "current result",
    )
    assert any("requested_model" in error for error in errors)


def test_result_records_rejects_registry_resolution_mismatch(tmp_path, monkeypatch):
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    eval_path = log_dir / "wrong_snapshot.eval"
    eval_path.write_text("fixture")
    row = _result_row(eval_path)
    row["resolved_model"] = "gpt-4o-mini-wrong"
    monkeypatch.setattr(
        export_hf_dataset,
        "extract_scores",
        lambda *_args, **_kwargs: [row],
    )

    with pytest.raises(ValueError, match="resolved model disagrees with model registry"):
        export_hf_dataset.result_records("packaging123", [log_dir])


def test_result_records_rejects_limit_exhausted_samples(tmp_path, monkeypatch):
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    eval_path = log_dir / "message_limit.eval"
    eval_path.write_text("fixture")
    row = _result_row(eval_path)
    row["limit"] = {"type": "message", "limit": 80}
    monkeypatch.setattr(
        export_hf_dataset,
        "extract_scores",
        lambda *_args, **_kwargs: [row],
    )

    with pytest.raises(ValueError, match="limit-exhausted Inspect sample"):
        export_hf_dataset.result_records("packaging123", [log_dir])


def test_eval_manifest_schema_keeps_0_2_records_backward_compatible():
    legacy = {
        "schema_version": "0.2.0",
        "source_commit": "abc123",
        "path": "eval_logs/example.eval",
        "source_path": "results/logs/example.eval",
        "log_dir": "results/logs",
        "filename": "example.eval",
        "sha256": "a" * 64,
        "bytes": 7,
        "status": "success",
        "evaluation_revision": {
            "type": "git",
            "origin": "https://github.com/jang1563/LabCraft-Eval.git",
            "commit": "abc123",
            "dirty": False,
        },
        "model_generate_config": {"temperature": 0.0},
        "sample_count": 1,
    }

    assert validate_hf_export.validate_json_schema(
        legacy,
        "hf_eval_log_manifest_record.schema.json",
        "legacy eval manifest",
    ) == []

    current_without_model_provenance = dict(legacy, schema_version="0.3.0")
    errors = validate_hf_export.validate_json_schema(
        current_without_model_provenance,
        "hf_eval_log_manifest_record.schema.json",
        "current eval manifest",
    )
    assert any("requested_model" in error for error in errors)


def test_clean_result_export_validates_with_native_provenance(tmp_path, monkeypatch):
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    eval_path = log_dir / "clean.eval"
    eval_path.write_text("fixture")
    monkeypatch.setattr(
        export_hf_dataset,
        "extract_scores",
        lambda *_args, **_kwargs: [_result_row(eval_path)],
    )
    out_dir = tmp_path / "hf_export"

    manifest = export_hf_dataset.build_export(
        out_dir=out_dir,
        release_name="clean_fixture",
        log_dirs=[log_dir],
    )

    assert manifest["evaluation_provenance"] == {
        "policy": "clean-evaluation-revisions-required",
        "log_count": 1,
        "dirty_log_count": 0,
        "revision_commits": ["abc123"],
    }
    eval_records = [
        json.loads(line) for line in (out_dir / "eval_log_manifest.jsonl").read_text().splitlines()
    ]
    assert len(eval_records) == 1
    bundled_eval = out_dir / eval_records[0]["path"]
    assert bundled_eval.read_text() == "fixture"
    assert eval_records[0]["path"] in {item["path"] for item in manifest["files"]}
    assert eval_records[0]["requested_model"] == "openai/gpt-4o-mini"
    assert eval_records[0]["resolved_model"] == "gpt-4o-mini-2024-07-18"
    assert eval_records[0]["provider"] == "openai"
    assert eval_records[0]["effective_generation_config"] == {"temperature": 0.0}
    assert eval_records[0]["inspect_version"] == "0.3.245"
    assert validate_hf_export.validate_export(out_dir) == []


def test_result_validator_enforces_model_identity_contract():
    record = {
        "schema_version": "0.3.0",
        "source_commit": "abc123",
        "model": "openai/gpt-4o-mini",
        "requested_model": "openai/gpt-4o-mini",
        "resolved_model": "gpt-4o-mini-2024-07-18",
        "provider": "openai",
        "effective_generation_config": {"temperature": 0.0},
        "inspect_version": "0.3.245",
        "model_generate_config": {"temperature": 0.0},
        "task": "transform_01",
        "sample_id": "transform_01_seeded_seed_00",
        "eval_log": "example.eval",
        "scores": {"overall": 0.75},
    }
    registry = export_hf_dataset.MODEL_REGISTRY

    assert validate_hf_export.validate_result_records(
        [record],
        require_model_provenance=True,
        model_registry=registry,
    ) == []

    model_mismatch = dict(record, model="openai/gpt-4o")
    errors = validate_hf_export.validate_result_records(
        [model_mismatch],
        require_model_provenance=True,
        model_registry=registry,
    )
    assert any("model differs from requested_model" in error for error in errors)

    provider_mismatch = dict(record, provider="anthropic")
    errors = validate_hf_export.validate_result_records(
        [provider_mismatch],
        require_model_provenance=True,
        model_registry=registry,
    )
    assert any(
        "provider differs from requested_model qualifier" in error for error in errors
    )

    config_mismatch = dict(
        record,
        effective_generation_config={"temperature": 0.7},
    )
    errors = validate_hf_export.validate_result_records(
        [config_mismatch],
        require_model_provenance=True,
        model_registry=registry,
    )
    assert any(
        "effective_generation_config differs from model_generate_config" in error
        for error in errors
    )

    unknown_request = dict(
        record,
        model="openai/unknown-model",
        requested_model="openai/unknown-model",
    )
    errors = validate_hf_export.validate_result_records(
        [unknown_request],
        require_model_provenance=True,
        model_registry=registry,
    )
    assert any("requested_model is not registered" in error for error in errors)

    wrong_snapshot = dict(record, resolved_model="gpt-4o-mini-wrong")
    errors = validate_hf_export.validate_result_records(
        [wrong_snapshot],
        require_model_provenance=True,
        model_registry=registry,
    )
    assert any(
        "resolved_model differs from model registry expectation" in error
        for error in errors
    )


def test_result_validator_rejects_alias_with_multiple_resolutions():
    base = {
        "schema_version": "0.3.0",
        "source_commit": "abc123",
        "model": "example/model",
        "requested_model": "example/model",
        "resolved_model": "model-snapshot-a",
        "provider": "example",
        "effective_generation_config": {"temperature": 0.0},
        "inspect_version": "0.3.245",
        "model_generate_config": {"temperature": 0.0},
        "task": "transform_01",
        "sample_id": "sample-a",
        "eval_log": "first.eval",
        "scores": {"overall": 0.75},
    }
    second = dict(
        base,
        resolved_model="model-snapshot-b",
        sample_id="sample-b",
        eval_log="second.eval",
    )

    errors = validate_hf_export.validate_result_records(
        [base, second],
        require_model_provenance=True,
    )

    assert any("resolves to multiple snapshots" in error for error in errors)


def test_validator_cross_checks_result_model_identity_with_eval_manifest(
    tmp_path, monkeypatch
):
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    eval_path = log_dir / "clean.eval"
    eval_path.write_text("fixture")
    monkeypatch.setattr(
        export_hf_dataset,
        "extract_scores",
        lambda *_args, **_kwargs: [_result_row(eval_path)],
    )
    out_dir = tmp_path / "hf_export"
    export_hf_dataset.build_export(
        out_dir=out_dir,
        release_name="clean_fixture",
        log_dirs=[log_dir],
    )
    manifest_path = out_dir / "eval_log_manifest.jsonl"
    manifest_record = json.loads(manifest_path.read_text())
    manifest_record["inspect_version"] = "0.3.999"
    manifest_path.write_text(json.dumps(manifest_record, sort_keys=True) + "\n")
    _refresh_manifest_file(out_dir, "eval_log_manifest.jsonl")

    errors = validate_hf_export.validate_export(out_dir)

    assert any("inspect_version differs from log manifest" in error for error in errors)


def test_validator_rejects_consistent_but_unregistered_resolved_snapshot(
    tmp_path, monkeypatch
):
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    eval_path = log_dir / "clean.eval"
    eval_path.write_text("fixture")
    monkeypatch.setattr(
        export_hf_dataset,
        "extract_scores",
        lambda *_args, **_kwargs: [_result_row(eval_path)],
    )
    out_dir = tmp_path / "hf_export"
    export_hf_dataset.build_export(
        out_dir=out_dir,
        release_name="clean_fixture",
        log_dirs=[log_dir],
    )
    for path_value in ("result_rows.jsonl", "eval_log_manifest.jsonl"):
        path = out_dir / path_value
        record = json.loads(path.read_text())
        record["resolved_model"] = "gpt-4o-mini-wrong"
        path.write_text(json.dumps(record, sort_keys=True) + "\n")
        _refresh_manifest_file(out_dir, path_value)

    errors = validate_hf_export.validate_export(out_dir)

    assert sum(
        "resolved_model differs from model registry expectation" in error
        for error in errors
    ) == 2


def test_validator_cross_checks_result_generation_config(tmp_path, monkeypatch):
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    eval_path = log_dir / "clean.eval"
    eval_path.write_text("fixture")
    monkeypatch.setattr(
        export_hf_dataset,
        "extract_scores",
        lambda *_args, **_kwargs: [_result_row(eval_path)],
    )
    out_dir = tmp_path / "hf_export"
    export_hf_dataset.build_export(
        out_dir=out_dir,
        release_name="clean_fixture",
        log_dirs=[log_dir],
    )
    result_path = out_dir / "result_rows.jsonl"
    result = json.loads(result_path.read_text())
    result["model_generate_config"] = {"temperature": 0.7}
    result_path.write_text(json.dumps(result, sort_keys=True) + "\n")
    manifest_path = out_dir / "release_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    for item in manifest["files"]:
        if item["path"] == "result_rows.jsonl":
            item["sha256"] = export_hf_dataset.sha256_file(result_path)
            item["bytes"] = result_path.stat().st_size
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")

    errors = validate_hf_export.validate_export(out_dir)
    assert any("generation config differs from log manifest" in error for error in errors)


def test_scored_export_requires_explicit_matching_plots(tmp_path, monkeypatch):
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    eval_path = log_dir / "clean.eval"
    eval_path.write_text("fixture")
    monkeypatch.setattr(
        export_hf_dataset,
        "extract_scores",
        lambda *_args, **_kwargs: [_result_row(eval_path)],
    )

    with pytest.raises(ValueError, match="require explicit --plot"):
        export_hf_dataset.build_export(
            out_dir=tmp_path / "hf_export",
            release_name="scored",
            log_dirs=[log_dir],
            copy_plots=True,
        )


def test_copy_plot_files_fails_for_missing_plot(tmp_path):
    with pytest.raises(FileNotFoundError, match="Plot file does not exist"):
        export_hf_dataset.copy_plot_files(tmp_path / "out", [tmp_path / "missing.png"])


def test_validate_export_accepts_metadata_only_bundle(tmp_path):
    out_dir = tmp_path / "hf_export"
    export_hf_dataset.build_export(
        out_dir=out_dir,
        release_name="unit_metadata_only",
        log_dirs=[tmp_path / "missing_logs"],
        include_results=False,
    )

    assert validate_hf_export.validate_export(out_dir) == []


def test_schema_0_2_export_requires_eval_log_manifest(tmp_path):
    out_dir = tmp_path / "hf_export"
    export_hf_dataset.build_export(
        out_dir=out_dir,
        release_name="unit_metadata_only",
        log_dirs=[],
        include_results=False,
    )
    (out_dir / "eval_log_manifest.jsonl").unlink()
    manifest_path = out_dir / "release_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["files"] = [
        item for item in manifest["files"] if item["path"] != "eval_log_manifest.jsonl"
    ]
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")

    errors = validate_hf_export.validate_export(out_dir)
    assert "eval_log_manifest.jsonl is required for schema 0.2.0+ exports" in errors


def test_build_export_refuses_stale_output_unless_clean_is_explicit(tmp_path, monkeypatch):
    monkeypatch.setattr(export_hf_dataset, "SAFE_CLEAN_ROOT", tmp_path)
    out_dir = tmp_path / "hf_export"
    export_hf_dataset.build_export(
        out_dir=out_dir,
        release_name="first",
        log_dirs=[],
        include_results=False,
    )
    stale_path = out_dir / "plots" / "stale.txt"
    stale_path.parent.mkdir()
    stale_path.write_text("stale")

    with pytest.raises(ValueError, match="Export directory is not empty"):
        export_hf_dataset.build_export(
            out_dir=out_dir,
            release_name="second",
            log_dirs=[],
            include_results=False,
        )

    export_hf_dataset.build_export(
        out_dir=out_dir,
        release_name="second",
        log_dirs=[],
        include_results=False,
        clean_output=True,
    )
    assert not stale_path.exists()


def test_clean_output_refuses_directory_outside_safe_build_root(tmp_path, monkeypatch):
    safe_root = tmp_path / "safe_build"
    unsafe_out = tmp_path / "unsafe_export"
    unsafe_out.mkdir()
    (unsafe_out / "stale.txt").write_text("stale")
    monkeypatch.setattr(export_hf_dataset, "SAFE_CLEAN_ROOT", safe_root)

    with pytest.raises(ValueError, match="restricted to a child"):
        export_hf_dataset.prepare_output_directory(unsafe_out, clean=True)


def test_validate_export_rejects_unmanifested_files(tmp_path):
    out_dir = tmp_path / "hf_export"
    export_hf_dataset.build_export(
        out_dir=out_dir,
        release_name="unit_metadata_only",
        log_dirs=[],
        include_results=False,
    )
    (out_dir / "stale.jsonl").write_text("{}\n")

    errors = validate_hf_export.validate_export(out_dir)
    assert "unmanifested file in export bundle: stale.jsonl" in errors


def test_validate_export_rejects_reserved_jsonl_alias_without_shadowing_root(tmp_path):
    out_dir = tmp_path / "hf_export"
    export_hf_dataset.build_export(
        out_dir=out_dir,
        release_name="unit_metadata_only",
        log_dirs=[],
        include_results=False,
    )

    canonical_path = out_dir / "tasks.jsonl"
    valid_text = canonical_path.read_text()
    tampered_records = valid_text.splitlines()
    first = json.loads(tampered_records[0])
    first["track"] = "not-a-real-track"
    tampered_records[0] = json.dumps(first, sort_keys=True)
    canonical_path.write_text("\n".join(tampered_records) + "\n")

    alias_path = out_dir / "shadow" / "tasks.jsonl"
    alias_path.parent.mkdir()
    alias_path.write_text(valid_text)

    manifest_path = out_dir / "release_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    for file_record in manifest["files"]:
        if file_record["path"] == "tasks.jsonl":
            file_record["sha256"] = export_hf_dataset.sha256_file(canonical_path)
            file_record["bytes"] = canonical_path.stat().st_size
    manifest["files"].append(
        {
            "path": "shadow/tasks.jsonl",
            "sha256": export_hf_dataset.sha256_file(alias_path),
            "bytes": alias_path.stat().st_size,
            "record_count": len(valid_text.splitlines()),
        }
    )
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")

    errors = validate_hf_export.validate_export(out_dir)

    assert any(
        "reserved JSONL basename must use its canonical root path: shadow/tasks.jsonl"
        in error
        for error in errors
    )
    assert any("tasks.jsonl record 1 schema error at track" in error for error in errors)


@pytest.mark.parametrize("escape_kind", ["absolute", "parent"])
def test_validate_export_rejects_lexical_path_escape_without_reading(
    tmp_path, monkeypatch, escape_kind
):
    case_dir = tmp_path / escape_kind
    out_dir = case_dir / "hf_export"
    export_hf_dataset.build_export(
        out_dir=out_dir,
        release_name="unit_metadata_only",
        log_dirs=[],
        include_results=False,
    )
    external_path = case_dir / "outside.jsonl"
    external_path.write_text("{}\n")
    path_value = str(external_path) if escape_kind == "absolute" else "../outside.jsonl"

    manifest_path = out_dir / "release_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["files"].append(
        {
            "path": path_value,
            "sha256": export_hf_dataset.sha256_file(external_path),
            "bytes": external_path.stat().st_size,
            "record_count": 1,
        }
    )
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")

    real_sha256_file = validate_hf_export.sha256_file

    def reject_external_read(path):
        assert path.resolve() != external_path.resolve()
        return real_sha256_file(path)

    monkeypatch.setattr(validate_hf_export, "sha256_file", reject_external_read)

    errors = validate_hf_export.validate_export(out_dir)

    assert any("unsafe manifest file path" in error for error in errors)


def test_validate_export_rejects_symlink_escape_without_reading(tmp_path, monkeypatch):
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

    real_sha256_file = validate_hf_export.sha256_file

    def reject_external_read(path):
        assert path.resolve() != external_path.resolve()
        return real_sha256_file(path)

    monkeypatch.setattr(validate_hf_export, "sha256_file", reject_external_read)

    errors = validate_hf_export.validate_export(out_dir)

    assert any("escapes export directory via symlink" in error for error in errors)


def test_export_cli_reports_fail_closed_error_without_traceback(monkeypatch, capsys, tmp_path):
    def fail_export(**_kwargs):
        raise ValueError("dirty evaluation revision")

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "export_hf_dataset.py",
            "--out-dir",
            str(tmp_path / "export"),
            "--no-results",
        ],
    )
    monkeypatch.setattr(export_hf_dataset, "build_export", fail_export)

    assert export_hf_dataset.main() == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "HF export refused: dirty evaluation revision\n"


def test_validate_export_rejects_tampered_file(tmp_path):
    out_dir = tmp_path / "hf_export"
    export_hf_dataset.build_export(
        out_dir=out_dir,
        release_name="unit_metadata_only",
        log_dirs=[tmp_path / "missing_logs"],
        include_results=False,
    )
    with (out_dir / "tasks.jsonl").open("a", encoding="utf-8") as handle:
        handle.write("{}\n")

    errors = validate_hf_export.validate_export(out_dir)
    assert any("sha256 mismatch" in error for error in errors)
    assert any("record_count mismatch" in error for error in errors)


def test_validate_export_rejects_source_commit_mismatch(tmp_path):
    out_dir = tmp_path / "hf_export"
    export_hf_dataset.build_export(
        out_dir=out_dir,
        release_name="unit_metadata_only",
        log_dirs=[tmp_path / "missing_logs"],
        include_results=False,
    )
    task_records = (out_dir / "tasks.jsonl").read_text().splitlines()
    first = json.loads(task_records[0])
    first["source_commit"] = "different"
    task_records[0] = json.dumps(first, sort_keys=True)
    (out_dir / "tasks.jsonl").write_text("\n".join(task_records) + "\n")

    manifest_path = out_dir / "release_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    for file_record in manifest["files"]:
        if file_record["path"] == "tasks.jsonl":
            file_record["sha256"] = export_hf_dataset.sha256_file(out_dir / "tasks.jsonl")
            file_record["bytes"] = (out_dir / "tasks.jsonl").stat().st_size
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")

    errors = validate_hf_export.validate_export(out_dir)
    assert any("source_commit mismatch" in error for error in errors)


def test_validate_export_applies_executable_task_schema(tmp_path):
    out_dir = tmp_path / "hf_export"
    export_hf_dataset.build_export(
        out_dir=out_dir,
        release_name="unit_metadata_only",
        log_dirs=[],
        include_results=False,
    )
    task_path = out_dir / "tasks.jsonl"
    task_records = task_path.read_text().splitlines()
    first = json.loads(task_records[0])
    first["track"] = "not-a-real-track"
    task_records[0] = json.dumps(first, sort_keys=True)
    task_path.write_text("\n".join(task_records) + "\n")

    manifest_path = out_dir / "release_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    for file_record in manifest["files"]:
        if file_record["path"] == "tasks.jsonl":
            file_record["sha256"] = export_hf_dataset.sha256_file(task_path)
            file_record["bytes"] = task_path.stat().st_size
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")

    errors = validate_hf_export.validate_export(out_dir)
    assert any(
        "tasks.jsonl record 1 schema error at track" in error
        and "not one of" in error
        for error in errors
    )
