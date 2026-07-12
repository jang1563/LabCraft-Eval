import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_dockerfile_copies_model_registry():
    dockerfile = (REPO_ROOT / "environments" / "Dockerfile").read_text(encoding="utf-8")
    assert "COPY config/ /workspace/config/" in dockerfile


def test_wheel_contains_registry_and_registers_model_info_outside_repo(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    for filename in ("pyproject.toml", "README.md"):
        shutil.copy2(REPO_ROOT / filename, project / filename)
    for directory in ("config", "data", "src", "task_data"):
        shutil.copytree(REPO_ROOT / directory, project / directory)

    wheel_dir = tmp_path / "wheel"
    uv = shutil.which("uv")
    if uv is not None:
        build_command = [
            uv,
            "build",
            "--wheel",
            "--no-build-logs",
            "--out-dir",
            str(wheel_dir),
            str(project),
        ]
    else:
        build_command = [
            sys.executable,
            "-m",
            "pip",
            "wheel",
            "--no-deps",
            "--wheel-dir",
            str(wheel_dir),
            str(project),
        ]
    build = subprocess.run(
        build_command,
        cwd=tmp_path,
        text=True,
        capture_output=True,
    )
    assert build.returncode == 0, build.stdout + build.stderr
    wheel_path = next(wheel_dir.glob("labcraft-*.whl"))
    with zipfile.ZipFile(wheel_path) as archive:
        names = set(archive.namelist())
    assert "config/model_matrix.toml" in names
    assert "src/model_registry.py" in names

    site = tmp_path / "site"
    with zipfile.ZipFile(wheel_path) as archive:
        archive.extractall(site)

    outside = tmp_path / "outside"
    outside.mkdir()
    code = r'''
import json
from pathlib import Path
import src
from inspect_ai.model import get_model_info
from src.model_registry import DEFAULT_REGISTRY_PATH

import src.inspect_task  # noqa: F401 -- wheel entry-point import is under test
info = get_model_info("openai/gpt-5.6-sol")
print(json.dumps({
    "src_file": str(Path(src.__file__).resolve()),
    "registry_path": str(DEFAULT_REGISTRY_PATH.resolve()),
    "registry_exists": DEFAULT_REGISTRY_PATH.is_file(),
    "context_length": info.context_length,
    "output_tokens": info.output_tokens,
    "knowledge_cutoff_date": info.knowledge_cutoff_date.isoformat(),
    "cost": info.cost,
}))
'''
    env = os.environ.copy()
    env["PYTHONPATH"] = str(site)
    smoke = subprocess.run(
        [sys.executable, "-c", code],
        cwd=outside,
        env=env,
        text=True,
        capture_output=True,
    )
    assert smoke.returncode == 0, smoke.stdout + smoke.stderr
    payload = json.loads(smoke.stdout)
    assert Path(payload["src_file"]).is_relative_to(site)
    assert Path(payload["registry_path"]).is_relative_to(site)
    assert payload["registry_exists"] is True
    assert payload["context_length"] == 1_050_000
    assert payload["output_tokens"] == 128_000
    assert payload["knowledge_cutoff_date"] == "2026-02-16"
    assert payload["cost"] is None
