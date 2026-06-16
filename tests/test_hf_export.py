import json

import pytest

from scripts import export_hf_dataset
from scripts import validate_hf_export


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
    assert "release_manifest.json" in text
    assert "omitted from this metadata-only export" in text
    assert "`plots/`: omitted" in text
    assert "abc123" in text


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
    assert plot_entries[0]["source_path"] == str(plot_path)


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
