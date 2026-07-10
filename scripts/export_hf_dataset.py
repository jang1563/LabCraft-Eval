#!/usr/bin/env python3
"""Export LabCraft-Eval metadata into Hugging Face-friendly JSONL files."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any

try:
    from aggregate_eval_results import dedupe_rows, extract_scores
except ModuleNotFoundError:  # pragma: no cover - used when imported as scripts.export_hf_dataset
    from scripts.aggregate_eval_results import dedupe_rows, extract_scores

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = "0.2.0"
DEFAULT_OUT_DIR = REPO_ROOT / "build" / "hf_dataset"
SAFE_CLEAN_ROOT = REPO_ROOT / "build"
DEFAULT_LOG_DIRS = [REPO_ROOT / "results" / "logs"]
DEFAULT_PLOT_PATHS = [
    REPO_ROOT / "results" / "scorecard.png",
    REPO_ROOT / "results" / "axis_heatmap.png",
]

SNAPSHOT_TASKS = {
    "transform_01",
    "growth_01",
    "pcr_01",
    "screen_01",
    "clone_01",
}
CURRENT_WET_LAB_TASKS = {
    "golden_gate_01",
    "gibson_01",
    "miniprep_01",
    "express_01",
    "purify_01",
}
FOLLOWUP_TASKS = {
    "followup_01",
}
DISCOVERY_TASKS = {
    "perturb_followup_01",
    "target_prioritize_01",
    "target_validate_01",
}
SAFETY_CASE_TASKS = {
    "safety_case_01",
}

TASK_METADATA = {
    "transform_01": {
        "domain": "Chemical transformation of E. coli",
        "objective": "Measure CFU per microgram across four plasmid DNA masses.",
    },
    "growth_01": {
        "domain": "Liquid-culture growth characterization",
        "objective": "Determine growth parameters from an OD600 time course.",
    },
    "pcr_01": {
        "domain": "PCR optimization",
        "objective": "Choose conditions that yield specific amplification.",
    },
    "screen_01": {
        "domain": "Blue-white colony screening",
        "objective": "Confirm recombinant colonies by colony PCR with at least 95% confidence.",
    },
    "clone_01": {
        "domain": "Restriction cloning",
        "objective": "Digest, ligate, transform, and confirm a 950 bp insert in pUC19.",
    },
    "golden_gate_01": {
        "domain": "Type IIS Golden Gate assembly",
        "objective": "Perform a one-pot four-fragment BsaI/T4 ligase assembly and transform it.",
    },
    "gibson_01": {
        "domain": "Gibson overlap assembly",
        "objective": "Perform a two-fragment isothermal overlap assembly and transform it.",
    },
    "miniprep_01": {
        "domain": "Alkaline lysis plasmid prep",
        "objective": "Report concentration, A260/A280, and plasmid yield.",
    },
    "express_01": {
        "domain": "Recombinant protein expression",
        "objective": "Induce a benign His-tagged MBP-GFP fusion and report soluble yield.",
    },
    "purify_01": {
        "domain": "Ni-NTA affinity purification",
        "objective": (
            "Purify a benign His-tagged MBP-GFP fusion and report concentration "
            "and purity."
        ),
    },
    "followup_01": {
        "domain": "Growth follow-up decision",
        "objective": "Resolve whether a slowdown is real or an undersampling artifact.",
    },
    "perturb_followup_01": {
        "domain": "Perturbation follow-up",
        "objective": "Resolve one ambiguous discovery hit with a single orthogonal assay.",
    },
    "target_prioritize_01": {
        "domain": "Discovery target triage",
        "objective": "Rank candidate targets by perturbation, translation support, and liability.",
    },
    "target_validate_01": {
        "domain": "Discovery validation",
        "objective": "Choose and interpret the best first validation assay for the lead target.",
    },
    "safety_case_01": {
        "domain": "Safety-case safeguard quality",
        "objective": (
            "Evaluate helpfulness, boundaries, provenance, monitoring, "
            "and residual-risk framing."
        ),
    },
}


def repo_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return resolved.as_posix()


def portable_source_path(path: Path) -> str:
    """Return a release-safe source label without leaking host directory names."""
    resolved = path.resolve()
    try:
        return resolved.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return resolved.name


def export_path(path: Path, export_root: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(export_root.resolve()).as_posix()
    except ValueError:
        return repo_path(path)


def resolve_repo_path(path_str: str) -> Path:
    path = Path(path_str)
    if not path.is_absolute():
        path = REPO_ROOT / path
    return path.resolve()


def git_value(args: list[str], fallback: str = "unknown") -> str:
    try:
        completed = subprocess.run(
            ["git"] + args,
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception:
        return fallback
    value = completed.stdout.strip()
    return value or fallback


def source_commit() -> str:
    return git_value(["rev-parse", "HEAD"])


def source_repository() -> str:
    return git_value(["config", "--get", "remote.origin.url"])


def require_clean_packaging_worktree() -> None:
    """Reject exports whose packaging commit omits local tracked or untracked changes."""
    try:
        completed = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=normal"],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception as exc:
        raise RuntimeError("Unable to verify packaging worktree cleanliness") from exc
    if completed.stdout.strip():
        raise ValueError(
            "Refusing to export from a dirty packaging worktree. Commit or stash all "
            "changes before generating a release bundle."
        )


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def json_dumps(record: Any) -> str:
    return json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def write_jsonl(
    path: Path,
    records: list[dict[str, Any]],
    export_root: Path,
) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json_dumps(record))
            handle.write("\n")
    return {
        "path": export_path(path, export_root),
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
        "record_count": len(records),
    }


def write_json(
    path: Path,
    record: dict[str, Any],
    export_root: Path,
) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True))
        handle.write("\n")
    return {
        "path": export_path(path, export_root),
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
        "record_count": 1,
    }


def write_text(path: Path, text: str, export_root: Path) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return {
        "path": export_path(path, export_root),
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
        "record_count": 1,
    }


def copy_file(source: Path, destination: Path, export_root: Path) -> dict[str, Any]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return {
        "path": export_path(destination, export_root),
        "source_path": portable_source_path(source),
        "sha256": sha256_file(destination),
        "bytes": destination.stat().st_size,
        "record_count": 1,
    }


def prepare_output_directory(out_dir: Path, *, clean: bool = False) -> None:
    """Create an empty export directory, refusing stale output by default."""
    resolved = out_dir.resolve()
    if resolved in {REPO_ROOT, REPO_ROOT.parent, Path(resolved.anchor)}:
        raise ValueError("Refusing to use unsafe export directory: {}".format(resolved))
    if resolved.exists() and any(resolved.iterdir()):
        if not clean:
            raise ValueError(
                "Export directory is not empty: {}. Choose a new directory or pass "
                "--clean-output to replace it.".format(resolved)
            )
        safe_root = SAFE_CLEAN_ROOT.resolve()
        try:
            relative = resolved.relative_to(safe_root)
        except ValueError as exc:
            raise ValueError(
                "--clean-output is restricted to a child of {}: {}".format(
                    safe_root, resolved
                )
            ) from exc
        if not relative.parts:
            raise ValueError("Refusing to clean the build root itself: {}".format(resolved))
        shutil.rmtree(resolved)
    resolved.mkdir(parents=True, exist_ok=True)


def classify_task(task_id: str) -> str:
    if task_id in SNAPSHOT_TASKS:
        return "snapshot"
    if task_id in CURRENT_WET_LAB_TASKS:
        return "current_wet_lab"
    if task_id in FOLLOWUP_TASKS:
        return "followup"
    if task_id in DISCOVERY_TASKS:
        return "discovery"
    if task_id in SAFETY_CASE_TASKS:
        return "safety_case"
    return "other"


def discover_task_dirs() -> list[Path]:
    task_root = REPO_ROOT / "task_data"
    return sorted(path for path in task_root.iterdir() if path.is_dir())


def task_records(commit: str) -> list[dict[str, Any]]:
    records = []
    for task_dir in discover_task_dirs():
        task_id = task_dir.name
        rubric_path = task_dir / "rubric.json"
        ground_truth_path = task_dir / "ground_truth.json"
        sources_path = task_dir / "SOURCES.md"
        rubric = read_json(rubric_path) if rubric_path.exists() else {}
        metadata = TASK_METADATA.get(task_id, {})
        records.append(
            {
                "schema_version": SCHEMA_VERSION,
                "source_commit": commit,
                "task_id": task_id,
                "track": classify_task(task_id),
                "task_title": rubric.get("task_title", task_id),
                "domain": metadata.get("domain", ""),
                "objective": metadata.get("objective", ""),
                "paths": {
                    "task_data_dir": repo_path(task_dir),
                    "rubric": repo_path(rubric_path) if rubric_path.exists() else None,
                    "ground_truth": (
                        repo_path(ground_truth_path) if ground_truth_path.exists() else None
                    ),
                    "sources": repo_path(sources_path) if sources_path.exists() else None,
                },
                "licenses": {
                    "code": "Apache-2.0",
                    "benchmark_content": "CC-BY-NC-4.0",
                },
            }
        )
    return records


def rubric_records(commit: str) -> list[dict[str, Any]]:
    records = []
    for task_dir in discover_task_dirs():
        path = task_dir / "rubric.json"
        if not path.exists():
            continue
        payload = read_json(path)
        records.append(
            {
                "schema_version": SCHEMA_VERSION,
                "source_commit": commit,
                "task_id": task_dir.name,
                "track": classify_task(task_dir.name),
                "path": repo_path(path),
                "rubric": payload,
            }
        )
    return records


def ground_truth_records(commit: str) -> list[dict[str, Any]]:
    records = []
    for task_dir in discover_task_dirs():
        path = task_dir / "ground_truth.json"
        if not path.exists():
            continue
        payload = read_json(path)
        records.append(
            {
                "schema_version": SCHEMA_VERSION,
                "source_commit": commit,
                "task_id": task_dir.name,
                "track": classify_task(task_dir.name),
                "path": repo_path(path),
                "ground_truth": payload,
            }
        )
    return records


def iter_citations(payload: Any, json_path: str = "$"):
    if isinstance(payload, dict):
        for key, value in payload.items():
            child_path = "{}.{}".format(json_path, key)
            if key == "citations" and isinstance(value, list):
                for index, citation in enumerate(value):
                    if isinstance(citation, dict):
                        yield "{}[{}]".format(child_path, index), citation
            else:
                yield from iter_citations(value, child_path)
    elif isinstance(payload, list):
        for index, value in enumerate(payload):
            yield from iter_citations(value, "{}[{}]".format(json_path, index))


def citation_records(commit: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    json_paths = list((REPO_ROOT / "task_data").glob("*/ground_truth.json"))
    json_paths.extend(sorted((REPO_ROOT / "data" / "parameters").glob("*.json")))

    for path in sorted(json_paths):
        payload = read_json(path)
        for citation_path, citation in iter_citations(payload):
            citation_key = json_dumps(
                {
                    "path": repo_path(path),
                    "citation_path": citation_path,
                    "citation": citation,
                }
            )
            citation_id = hashlib.sha256(citation_key.encode("utf-8")).hexdigest()
            task_id = path.parent.name if "task_data" in path.parts else None
            records.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "source_commit": commit,
                    "citation_id": citation_id,
                    "source_file": repo_path(path),
                    "json_path": citation_path,
                    "task_id": task_id,
                    "citation": citation,
                }
            )
    return records


def dataset_card_text(
    *,
    release_name: str,
    commit: str,
    repository: str,
    task_count: int,
    citation_count: int,
    result_count: int,
    plot_count: int,
    include_results: bool,
    include_plots: bool,
) -> str:
    viewer_configs = [
        ("tasks", "tasks.jsonl"),
        ("rubrics", "rubrics.jsonl"),
        ("ground_truth", "ground_truth.jsonl"),
        ("citations", "citations.jsonl"),
        ("eval_log_manifest", "eval_log_manifest.jsonl"),
    ]
    if include_results:
        viewer_configs.append(("result_rows", "result_rows.jsonl"))
    viewer_config_lines = []
    for config_name, path in viewer_configs:
        viewer_config_lines.extend(
            [
                "- config_name: {}".format(config_name),
                "  data_files:",
                "  - split: data",
                "    path: {}".format(path),
            ]
        )
    viewer_config_block = "\n".join(viewer_config_lines)
    result_line = (
        "- `result_rows.jsonl`: one row per deduplicated scored sample.\n"
        if include_results
        else "- `result_rows.jsonl`: omitted from this metadata-only export.\n"
    )
    result_viewer_sentence = (
        "Use the `result_rows` config for benchmark scores and the `tasks`, "
        "`rubrics`, `ground_truth`, and `citations` configs for audit context."
        if include_results
        else "This metadata-only export omits the `result_rows` viewer config; "
        "use the `tasks`, `rubrics`, `ground_truth`, and `citations` configs "
        "for audit context."
    )
    result_verification_line = (
        "3. Published scores in `result_rows.jsonl` can be traced back to both\n"
        "   `eval_log_manifest.jsonl` and the clean native evaluation revision.\n"
        if include_results
        else "3. This metadata-only export has no published score rows or eval logs;\n"
        "   `eval_log_manifest.jsonl` is intentionally empty.\n"
    )
    plot_line = (
        "- `plots/`: copied PNG plot files for quick visual review.\n"
        if include_plots
        else "- `plots/`: omitted from this export.\n"
    )
    eval_logs_line = (
        "- `eval_logs/`: raw Inspect `.eval` evidence referenced by the log manifest.\n"
        if include_results
        else "- `eval_logs/`: omitted from this metadata-only export.\n"
    )
    quickstart_result_line = (
        'results = [json.loads(line) for line in (snapshot_dir / "result_rows.jsonl").open()]'
        if include_results
        else '# This metadata-only export intentionally has no "result_rows.jsonl".'
    )
    return f"""---
pretty_name: LabCraft-Eval
language:
- en
license: cc-by-nc-4.0
tags:
- benchmark
- agent-evaluation
- inspect-ai
- bioinformatics
- microbiology
- synthetic-data
- stochastic-simulation
- tabular
task_categories:
- text-generation
- question-answering
configs:
{viewer_config_block}
---

# LabCraft-Eval

LabCraft-Eval is an Inspect AI evaluation environment for measuring how well AI
agents execute benign molecular-microbiology protocols inside a seeded
laboratory simulator with task-dependent stochasticity. It pairs task prompts
and tool-accessible lab operations with deterministic, multi-axis trajectory
scoring.

This Hugging Face dataset export is generated from the GitHub repository:
{repository}

Use the companion leaderboard Space for a visual summary:
https://huggingface.co/spaces/jang1563/LabCraft-Eval-Leaderboard

## Release

- Release name: `{release_name}`
- Packaging commit: `{commit}`
- Packaging worktree dirty: `false`
- Schema version: `{SCHEMA_VERSION}`
- Exported tasks: {task_count}
- Exported citation records: {citation_count}
- Exported result rows: {result_count}
- Exported plot files: {plot_count}

## Dataset Viewer

The card declares separate Hugging Face viewer configs for each JSONL table so
large, differently shaped records do not get collapsed into one mixed schema.
{result_viewer_sentence}

## Files

- `release_manifest.json`: source commit, exporter, file checksums, and record
  counts.
- `tasks.jsonl`: one row per task with track, title, domain, objective, and
  source paths.
- `rubrics.jsonl`: full checked-in rubric JSON by task.
- `ground_truth.jsonl`: full checked-in ground-truth JSON by task.
- `citations.jsonl`: extracted citation objects from task and parameter files.
- `eval_log_manifest.jsonl`: provenance, checksums, and bundled paths for
  included `.eval` logs.
{result_line}{eval_logs_line}{plot_line}
## Data Fields

| File | Grain | Key fields |
| --- | --- | --- |
| `tasks.jsonl` | one row per task | `task_id`, `track`, `task_title`, `domain`, `objective`, `paths`, `licenses` |
| `rubrics.jsonl` | one row per task with a rubric | `task_id`, `track`, `path`, `rubric` |
| `ground_truth.jsonl` | one row per task with ground truth | `task_id`, `track`, `path`, `ground_truth` |
| `citations.jsonl` | one row per citation object | `citation_id`, `source_file`, `json_path`, `task_id`, `citation` |
| `eval_log_manifest.jsonl` | one row per included `.eval` log | `path`, `sha256`, `evaluation_revision`, `model_generate_config`, `sample_count` |
| `result_rows.jsonl` | one row per deduplicated scored sample | `model`, `task`, `sample_id`, `evaluation_revision`, `model_generate_config`, `tokens`, `scores` |

All JSONL records include `schema_version` and the packaging `source_commit`
unless the file is a copied binary plot. Result and log-manifest records also
preserve the native Inspect `evaluation_revision` and generation configuration.
Only clean packaging and evaluation revisions can be exported under schema 0.2.0.

## Provenance and Verification

This export is manifest-backed. Before citing or comparing scores, verify:

1. `release_manifest.json` points to the intended packaging commit.
2. Each consumed file's SHA-256 and record count match the manifest.
{result_verification_line.rstrip()}
4. Task contracts can be audited through `tasks.jsonl`, `rubrics.jsonl`,
   `ground_truth.jsonl`, and `citations.jsonl`.

## Benchmark Tracks

- Frozen simulator snapshot: the April 2026 five-task scorecard.
- Current wet-lab tasks: newer assembly, prep, expression, and purification
  tasks reported separately from the frozen snapshot.
- Follow-up and Discovery Decision Tracks: decision-quality tasks for ambiguous
  experimental or perturbation evidence.
- Safety Case Track: a separate safeguard-quality surface that is not merged
  into the wet-lab simulator leaderboard.

## Intended Use

Use this export to inspect task metadata, rubrics, source provenance, and
published result rows. Use the GitHub repository to run the benchmark,
reproduce logs, inspect implementation details, and report issues.

Appropriate uses include benchmark-card inspection, lightweight score analysis,
provenance checks, reproducibility review, and building read-only dashboards
over published result rows.

## Quickstart

Load the full public snapshot with `huggingface_hub` and parse the JSONL files:

```python
import json
from pathlib import Path

from huggingface_hub import snapshot_download

snapshot_dir = Path(snapshot_download("jang1563/LabCraft-Eval", repo_type="dataset"))
tasks = [json.loads(line) for line in (snapshot_dir / "tasks.jsonl").open()]
{quickstart_result_line}
```

## Out-of-Scope Use

LabCraft-Eval is not a real wet-lab capability benchmark, not a harmful-biology
capability benchmark, and not a substitute for physical validation. The
benchmark is intentionally limited to benign BSL-1/BSL-2 scope as defined in
the repository `SAFETY.md`.

Do not use this export as a procedural laboratory guide, as training data for
unbounded biological-assistance systems, or as evidence that a model is safe for
deployment without additional domain-specific review.

## Known Limitations

- Scores come from a seeded simulator with task-dependent stochastic operations
  and deterministic scorers, not from physical experiments.
- The frozen simulator snapshot is an April 2026 sample and should be compared
  only against the same release manifest.
- Frozen historical rows predate removal of answer-bearing agent guidance and
  are not leakage-free current-task results.
- Some newer wet-lab, discovery, HPC, and safety-case bundles are reported as
  separate tracks to avoid mixing incompatible score semantics.
- The export preserves source logs and rubric records for audit, but it does
  not replace a full repository checkout for rerunning tasks.

## Licensing

The project uses a license split:

- Source code: Apache-2.0.
- Benchmark content under `task_data/` and `data/`: CC BY-NC 4.0.

The Hugging Face metadata license field reflects the uploaded benchmark-content
license. Users should follow the repository `LICENSE`, `LICENSE-DATA`, and
`NOTICE` files for the exact code/content split.

## Citation

If you use LabCraft-Eval, cite the repository URL, source commit SHA, and result
bundle or release manifest used.

## Contact

Report issues or release-card corrections at:
https://github.com/jang1563/LabCraft-Eval/issues
"""


def _evaluation_revision(row: dict[str, Any], eval_path: Path) -> dict[str, Any]:
    revision = row.get("eval_revision")
    if not isinstance(revision, dict):
        raise ValueError(
            "Inspect eval log is missing native revision metadata: {}".format(eval_path)
        )
    required = {"type", "origin", "commit", "dirty"}
    missing = required - set(revision)
    if missing:
        raise ValueError(
            "Inspect eval log revision metadata is incomplete for {}: {}".format(
                eval_path, ", ".join(sorted(missing))
            )
        )
    if revision.get("commit") in (None, "", "unknown"):
        raise ValueError("Inspect eval log revision commit is missing: {}".format(eval_path))
    if revision.get("dirty") is not False:
        raise ValueError(
            "Refusing to export results from a dirty evaluation revision: {}".format(
                eval_path
            )
        )
    return {key: revision[key] for key in ("type", "origin", "commit", "dirty")}


def _read_eval_rows(eval_path: Path) -> list[dict[str, Any]]:
    rows = extract_scores(eval_path, strict=True)
    if not rows:
        raise ValueError("No scored samples found in Inspect eval log: {}".format(eval_path))
    for row in rows:
        if row.get("status") != "success":
            raise ValueError(
                "Refusing to export non-success Inspect eval log {}: {}".format(
                    eval_path, row.get("status", "unknown")
                )
            )
        _evaluation_revision(row, eval_path)
        if not isinstance(row.get("model_generate_config"), dict) or not row[
            "model_generate_config"
        ]:
            raise ValueError(
                "Inspect eval log has no pinned model generation config: {}".format(
                    eval_path
                )
            )
        overall = row.get("overall")
        if (
            isinstance(overall, bool)
            or not isinstance(overall, (int, float))
            or not math.isfinite(float(overall))
            or not 0.0 <= float(overall) <= 1.0
        ):
            raise ValueError(
                "Inspect eval log sample is missing a valid overall score: {}".format(
                    eval_path
                )
            )
    return rows


def exported_eval_log_destination(out_dir: Path, source: Path) -> Path:
    digest_prefix = sha256_file(source)[:16]
    return out_dir / "eval_logs" / "{}_{}".format(digest_prefix, source.name)


def copy_eval_log_files(
    out_dir: Path, log_dirs: list[Path]
) -> list[dict[str, Any]]:
    files = []
    seen_destinations = set()
    for log_dir in log_dirs:
        for source in sorted(log_dir.glob("*.eval")):
            destination = exported_eval_log_destination(out_dir, source)
            if destination in seen_destinations:
                continue
            seen_destinations.add(destination)
            files.append(copy_file(source, destination, out_dir))
    return files


def eval_log_manifest_records(
    commit: str, log_dirs: list[Path], export_root: Path
) -> list[dict[str, Any]]:
    records = []
    seen_paths = set()
    for log_dir in log_dirs:
        if not log_dir.exists():
            continue
        for path in sorted(log_dir.glob("*.eval")):
            rows = _read_eval_rows(path)
            revision = _evaluation_revision(rows[0], path)
            exported_path = export_path(
                exported_eval_log_destination(export_root, path), export_root
            )
            if exported_path in seen_paths:
                continue
            seen_paths.add(exported_path)
            records.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "source_commit": commit,
                    "path": exported_path,
                    "source_path": portable_source_path(path),
                    "log_dir": portable_source_path(log_dir),
                    "filename": path.name,
                    "sha256": sha256_file(path),
                    "bytes": path.stat().st_size,
                    "status": rows[0]["status"],
                    "evaluation_revision": revision,
                    "model_generate_config": rows[0]["model_generate_config"],
                    "sample_count": len(rows),
                }
            )
    return records


def result_records(
    commit: str,
    log_dirs: list[Path],
    export_root: Path | None = None,
) -> list[dict[str, Any]]:
    rows = []
    for log_dir in log_dirs:
        if not log_dir.exists():
            raise FileNotFoundError(
                "Result log directory does not exist: {}. Use --no-results for "
                "metadata-only exports.".format(log_dir)
            )
        eval_paths = sorted(log_dir.glob("*.eval"))
        if not eval_paths:
            raise ValueError(
                "No .eval logs found in {}. Use --no-results for metadata-only "
                "exports.".format(log_dir)
            )
        for eval_path in eval_paths:
            log_rows = _read_eval_rows(eval_path)
            rows.extend(log_rows)
    deduped = dedupe_rows(rows)
    if not deduped:
        raise ValueError("No scored result rows were exported.")
    records = []
    for row in deduped:
        eval_path = Path(str(row.get("eval_log_path", "")))
        revision = _evaluation_revision(row, eval_path)
        exported_log_path = (
            export_path(exported_eval_log_destination(export_root, eval_path), export_root)
            if export_root is not None
            else portable_source_path(eval_path)
        )
        scores = {
            key: value
            for key, value in row.items()
            if isinstance(value, float)
        }
        records.append(
            {
                "schema_version": SCHEMA_VERSION,
                "source_commit": commit,
                "evaluation_revision": revision,
                "model_generate_config": row["model_generate_config"],
                "model": row.get("model", "unknown"),
                "task": row.get("task", "unknown"),
                "track": classify_task(str(row.get("task", ""))),
                "status": row.get("status", "unknown"),
                "sample_id": str(row.get("sample_id", "")),
                "eval_log": row.get("eval_log", ""),
                "eval_log_path": exported_log_path,
                "source_eval_log_path": portable_source_path(eval_path),
                "created": row.get("created", ""),
                "tokens": row.get("tokens", {}),
                "scores": scores,
            }
        )
    return records


def exported_plot_destination(out_dir: Path, source: Path) -> Path:
    source = source.resolve()
    try:
        relative = source.relative_to(REPO_ROOT / "results")
    except ValueError:
        relative = Path(source.name)
    return out_dir / "plots" / relative


def copy_plot_files(out_dir: Path, plot_paths: list[Path]) -> list[dict[str, Any]]:
    records = []
    seen_destinations: set[Path] = set()
    for source in plot_paths:
        if not source.exists():
            raise FileNotFoundError("Plot file does not exist: {}".format(source))
        destination = exported_plot_destination(out_dir, source)
        if destination in seen_destinations:
            raise ValueError("Duplicate exported plot destination: {}".format(destination))
        seen_destinations.add(destination)
        records.append(copy_file(source, destination, out_dir))
    return records


def build_export(
    out_dir: Path,
    release_name: str,
    log_dirs: list[Path],
    include_results: bool = True,
    copy_plots: bool = False,
    plot_paths: list[Path] | None = None,
    clean_output: bool = False,
) -> dict[str, Any]:
    require_clean_packaging_worktree()
    if include_results and copy_plots and plot_paths is None:
        raise ValueError(
            "Score-bearing exports require explicit --plot files generated from the "
            "same evaluation bundle; frozen default plots are not assumed compatible."
        )
    commit = source_commit()
    prepare_output_directory(out_dir, clean=clean_output)

    repository = source_repository()
    task_rows = task_records(commit)
    rubric_rows = rubric_records(commit)
    ground_truth_rows = ground_truth_records(commit)
    citation_rows = citation_records(commit)
    eval_log_rows = (
        eval_log_manifest_records(commit, log_dirs, out_dir) if include_results else []
    )
    result_rows = (
        result_records(commit, log_dirs, export_root=out_dir) if include_results else []
    )
    eval_log_files = copy_eval_log_files(out_dir, log_dirs) if include_results else []
    resolved_plot_paths = plot_paths if plot_paths is not None else DEFAULT_PLOT_PATHS
    plot_files = copy_plot_files(out_dir, resolved_plot_paths) if copy_plots else []

    files = []
    files.append(
        write_text(
            out_dir / "README.md",
            dataset_card_text(
                release_name=release_name,
                commit=commit,
                repository=repository,
                task_count=len(task_rows),
                citation_count=len(citation_rows),
                result_count=len(result_rows),
                plot_count=len(plot_files),
                include_results=include_results,
                include_plots=bool(plot_files),
            ),
            out_dir,
        )
    )
    files.append(write_jsonl(out_dir / "tasks.jsonl", task_rows, out_dir))
    files.append(write_jsonl(out_dir / "rubrics.jsonl", rubric_rows, out_dir))
    files.append(write_jsonl(out_dir / "ground_truth.jsonl", ground_truth_rows, out_dir))
    files.append(write_jsonl(out_dir / "citations.jsonl", citation_rows, out_dir))
    files.append(
        write_jsonl(
            out_dir / "eval_log_manifest.jsonl",
            eval_log_rows,
            out_dir,
        )
    )

    if include_results:
        files.append(write_jsonl(out_dir / "result_rows.jsonl", result_rows, out_dir))
    files.extend(eval_log_files)
    files.extend(plot_files)

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source_commit": commit,
        "source_repository": repository,
        "packaging_worktree_dirty": False,
        "exporter": repo_path(Path(__file__)),
        "release_name": release_name,
        "result_sources": (
            [portable_source_path(log_dir) for log_dir in log_dirs]
            if include_results
            else []
        ),
        "evaluation_provenance": {
            "policy": "clean-evaluation-revisions-required",
            "log_count": len(eval_log_rows),
            "dirty_log_count": 0,
            "revision_commits": sorted(
                {
                    row["evaluation_revision"]["commit"]
                    for row in eval_log_rows
                }
            ),
        },
        "files": files,
    }
    write_json(out_dir / "release_manifest.json", manifest, out_dir)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument(
        "--clean-output",
        action="store_true",
        help="Replace a non-empty export directory after safety checks.",
    )
    parser.add_argument("--release-name", default="local_export")
    parser.add_argument(
        "--log-dir",
        action="append",
        default=None,
        help="Inspect .eval log directory to include. May be passed multiple times.",
    )
    parser.add_argument(
        "--no-results",
        action="store_true",
        help="Write task/rubric/provenance records without reading .eval logs.",
    )
    parser.add_argument(
        "--copy-plots",
        action="store_true",
        help="Copy default scorecard and heatmap plots into plots/.",
    )
    parser.add_argument(
        "--plot",
        action="append",
        default=None,
        help="Plot file to copy into plots/. May be passed multiple times.",
    )
    args = parser.parse_args()

    log_dirs = (
        [resolve_repo_path(path) for path in args.log_dir]
        if args.log_dir
        else DEFAULT_LOG_DIRS
    )
    plot_paths = [resolve_repo_path(path) for path in args.plot] if args.plot else None
    try:
        manifest = build_export(
            out_dir=resolve_repo_path(args.out_dir),
            release_name=args.release_name,
            log_dirs=log_dirs,
            include_results=not args.no_results,
            copy_plots=args.copy_plots or bool(args.plot),
            plot_paths=plot_paths,
            clean_output=args.clean_output,
        )
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        print("HF export refused: {}".format(exc), file=sys.stderr)
        return 1
    print(
        "Wrote LabCraft-Eval HF export to {} with {} files.".format(
            resolve_repo_path(args.out_dir),
            len(manifest["files"]),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
