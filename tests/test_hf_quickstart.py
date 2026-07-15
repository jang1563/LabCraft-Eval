import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from examples import hf_quickstart


BASE_URL = "https://example.invalid/datasets/LabCraft-Eval/resolve/main"
TASKS = [
    {"task_id": "transform_01", "track": "wet_lab"},
    {"task_id": "followup_01", "track": "decision"},
]


def _write_jsonl(path: Path, records: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(record, sort_keys=True) + "\n" for record in records),
        encoding="utf-8",
    )


def _file_entry(path: Path) -> dict:
    return {
        "path": path.name,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "bytes": path.stat().st_size,
        "record_count": len(path.read_text(encoding="utf-8").splitlines()),
    }


def _write_remote_snapshot(
    remote_dir: Path,
    *,
    source_commit: str,
    release_name: str,
    results: list[dict] | None,
) -> None:
    remote_dir.mkdir(parents=True, exist_ok=True)
    tasks_path = remote_dir / "tasks.jsonl"
    results_path = remote_dir / "result_rows.jsonl"
    _write_jsonl(tasks_path, TASKS)
    files = [_file_entry(tasks_path)]
    if results is None:
        results_path.unlink(missing_ok=True)
    else:
        _write_jsonl(results_path, results)
        files.append(_file_entry(results_path))
    manifest = {
        "source_commit": source_commit,
        "release_name": release_name,
        "files": files,
    }
    (remote_dir / "release_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


class LocalDownloader:
    def __init__(self, remote_dir: Path):
        self.remote_dir = remote_dir
        self.calls: list[str] = []

    def __call__(self, url: str, target: str) -> object:
        filename = url.rsplit("/", 1)[-1]
        self.calls.append(filename)
        shutil.copyfile(self.remote_dir / filename, target)
        return target, None


def test_downloads_metadata_only_snapshot_from_manifest(tmp_path, capsys):
    remote_dir = tmp_path / "remote"
    commit = "a" * 40
    _write_remote_snapshot(
        remote_dir,
        source_commit=commit,
        release_name="v0.1.2",
        results=None,
    )
    downloader = LocalDownloader(remote_dir)

    snapshot_dir = hf_quickstart.ensure_snapshot(
        None,
        BASE_URL,
        cache_dir=tmp_path / "cache",
        downloader=downloader,
    )
    hf_quickstart.summarize(snapshot_dir)

    output = capsys.readouterr().out
    assert not (snapshot_dir / "result_rows.jsonl").exists()
    assert (
        hf_quickstart.read_json(snapshot_dir / "release_manifest.json")["source_commit"] == commit
    )
    assert downloader.calls == ["release_manifest.json", "tasks.jsonl"]
    assert "tasks: 2" in output
    assert "result_rows: 0" in output
    assert "evaluation_data: metadata-only" in output


def test_downloads_and_summarizes_scored_snapshot(tmp_path, capsys):
    remote_dir = tmp_path / "remote"
    _write_remote_snapshot(
        remote_dir,
        source_commit="b" * 40,
        release_name="v0.2.0",
        results=[
            {"model": "openai/model-a", "score": 0.9},
            {"model": "provider/model-b", "score": 0.8},
        ],
    )

    snapshot_dir = hf_quickstart.ensure_snapshot(
        None,
        BASE_URL,
        cache_dir=tmp_path / "cache",
        downloader=LocalDownloader(remote_dir),
    )
    hf_quickstart.summarize(snapshot_dir)

    output = capsys.readouterr().out
    assert "result_rows: 2" in output
    assert "openai/model-a" in output
    assert "provider/model-b" in output
    assert "metadata-only" not in output


def test_mutable_revision_selects_new_source_commit_instead_of_stale_cache(tmp_path, capsys):
    remote_dir = tmp_path / "remote"
    cache_dir = tmp_path / "cache"
    downloader = LocalDownloader(remote_dir)
    _write_remote_snapshot(
        remote_dir,
        source_commit="1" * 40,
        release_name="v0.1.1",
        results=[{"model": "stale/model", "score": 1.0}],
    )
    stale_snapshot = hf_quickstart.ensure_snapshot(
        None,
        BASE_URL,
        cache_dir=cache_dir,
        downloader=downloader,
    )

    _write_remote_snapshot(
        remote_dir,
        source_commit="2" * 40,
        release_name="v0.1.2",
        results=None,
    )
    current_snapshot = hf_quickstart.ensure_snapshot(
        None,
        BASE_URL,
        cache_dir=cache_dir,
        downloader=downloader,
    )
    hf_quickstart.summarize(current_snapshot)

    output = capsys.readouterr().out
    assert current_snapshot != stale_snapshot
    assert (stale_snapshot / "result_rows.jsonl").exists()
    assert not (current_snapshot / "result_rows.jsonl").exists()
    assert "source_commit: " + "2" * 40 in output
    assert "result_rows: 0" in output
    assert "stale/model" not in output
    assert downloader.calls.count("release_manifest.json") == 2


def test_corrupt_cached_file_is_refreshed_against_current_manifest(tmp_path):
    remote_dir = tmp_path / "remote"
    cache_dir = tmp_path / "cache"
    downloader = LocalDownloader(remote_dir)
    _write_remote_snapshot(
        remote_dir,
        source_commit="c" * 40,
        release_name="v0.1.2",
        results=None,
    )
    snapshot_dir = hf_quickstart.ensure_snapshot(
        None,
        BASE_URL,
        cache_dir=cache_dir,
        downloader=downloader,
    )
    expected_tasks = (remote_dir / "tasks.jsonl").read_bytes()
    (snapshot_dir / "tasks.jsonl").write_bytes(b"corrupt cache\n")

    refreshed_dir = hf_quickstart.ensure_snapshot(
        None,
        BASE_URL,
        cache_dir=cache_dir,
        downloader=downloader,
    )

    assert refreshed_dir == snapshot_dir
    assert (refreshed_dir / "tasks.jsonl").read_bytes() == expected_tasks
    assert downloader.calls.count("tasks.jsonl") == 2


def test_rejects_download_whose_checksum_disagrees_with_manifest(tmp_path):
    remote_dir = tmp_path / "remote"
    _write_remote_snapshot(
        remote_dir,
        source_commit="d" * 40,
        release_name="v0.1.2",
        results=None,
    )
    manifest_path = remote_dir / "release_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files"][0]["sha256"] = "0" * 64
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(hf_quickstart.QuickstartError, match="tasks.jsonl sha256 mismatch"):
        hf_quickstart.ensure_snapshot(
            None,
            BASE_URL,
            cache_dir=tmp_path / "cache",
            downloader=LocalDownloader(remote_dir),
        )


def test_rejects_download_whose_record_count_disagrees_with_manifest(tmp_path):
    remote_dir = tmp_path / "remote"
    _write_remote_snapshot(
        remote_dir,
        source_commit="e" * 40,
        release_name="v0.1.2",
        results=None,
    )
    manifest_path = remote_dir / "release_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files"][0]["record_count"] += 1
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(hf_quickstart.QuickstartError, match="tasks.jsonl record count mismatch"):
        hf_quickstart.ensure_snapshot(
            None,
            BASE_URL,
            cache_dir=tmp_path / "cache",
            downloader=LocalDownloader(remote_dir),
        )


def test_existing_local_snapshot_does_not_use_network(tmp_path):
    snapshot_dir = tmp_path / "local_snapshot"
    _write_remote_snapshot(
        snapshot_dir,
        source_commit="f" * 40,
        release_name="local",
        results=None,
    )

    def unexpected_download(url: str, target: str) -> object:
        raise AssertionError(f"unexpected network request: {url} -> {target}")

    resolved = hf_quickstart.ensure_snapshot(
        snapshot_dir,
        BASE_URL,
        cache_dir=tmp_path / "cache",
        downloader=unexpected_download,
    )

    assert resolved == snapshot_dir


def test_cli_reports_snapshot_errors_without_a_traceback(tmp_path):
    missing_snapshot = tmp_path / "missing"
    result = subprocess.run(
        [
            sys.executable,
            "examples/hf_quickstart.py",
            "--snapshot-dir",
            str(missing_snapshot),
        ],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert result.stderr.startswith("error: missing required file:")
    assert "Traceback" not in result.stderr
