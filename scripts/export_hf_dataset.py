#!/usr/bin/env python3
"""Export LabCraft-Eval metadata into Hugging Face-friendly JSONL files."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from typing import Any

try:
    from aggregate_eval_results import dedupe_rows, extract_scores
except ModuleNotFoundError:  # pragma: no cover - used when imported as scripts.export_hf_dataset
    from scripts.aggregate_eval_results import dedupe_rows, extract_scores

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = "0.1.0"
DEFAULT_OUT_DIR = REPO_ROOT / "build" / "hf_dataset"
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
        "source_path": repo_path(source),
        "sha256": sha256_file(destination),
        "bytes": destination.stat().st_size,
        "record_count": 1,
    }


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
    result_line = (
        "- `result_rows.jsonl`: one row per deduplicated scored sample.\n"
        if include_results
        else "- `result_rows.jsonl`: omitted from this metadata-only export.\n"
    )
    plot_line = (
        "- `plots/`: copied PNG plot files for quick visual review.\n"
        if include_plots
        else "- `plots/`: omitted from this export.\n"
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
---

# LabCraft-Eval

LabCraft-Eval is an Inspect AI evaluation environment for measuring how well AI
agents execute benign molecular-microbiology protocols inside a seeded
stochastic laboratory simulator. It pairs task prompts and tool-accessible lab
operations with deterministic, multi-axis trajectory scoring.

This Hugging Face dataset export is generated from the GitHub repository:
{repository}

## Release

- Release name: `{release_name}`
- Source commit: `{commit}`
- Schema version: `{SCHEMA_VERSION}`
- Exported tasks: {task_count}
- Exported citation records: {citation_count}
- Exported result rows: {result_count}
- Exported plot files: {plot_count}

## Files

- `release_manifest.json`: source commit, exporter, file checksums, and record
  counts.
- `tasks.jsonl`: one row per task with track, title, domain, objective, and
  source paths.
- `rubrics.jsonl`: full checked-in rubric JSON by task.
- `ground_truth.jsonl`: full checked-in ground-truth JSON by task.
- `citations.jsonl`: extracted citation objects from task and parameter files.
- `eval_log_manifest.jsonl`: checksums and sizes for included `.eval` logs.
{result_line}{plot_line}
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

## Quickstart

Load the full public snapshot with `huggingface_hub` and parse the JSONL files:

```python
import json
from pathlib import Path

from huggingface_hub import snapshot_download

snapshot_dir = Path(snapshot_download("jang1563/LabCraft-Eval", repo_type="dataset"))
tasks = [json.loads(line) for line in (snapshot_dir / "tasks.jsonl").open()]
results = [json.loads(line) for line in (snapshot_dir / "result_rows.jsonl").open()]
```

## Out-of-Scope Use

LabCraft-Eval is not a real wet-lab capability benchmark, not a harmful-biology
capability benchmark, and not a substitute for physical validation. The
benchmark is intentionally limited to benign BSL-1/BSL-2 scope as defined in
the repository `SAFETY.md`.

## Licensing

The project uses a license split:

- Source code: Apache-2.0.
- Benchmark content under `task_data/` and `data/`: CC BY-NC 4.0.

The Hugging Face metadata lists both licenses, but users should follow the
repository `LICENSE`, `LICENSE-DATA`, and `NOTICE` files for the exact split.

## Citation

If you use LabCraft-Eval, cite the repository URL, source commit SHA, and result
bundle or release manifest used.
"""


def eval_log_manifest_records(commit: str, log_dirs: list[Path]) -> list[dict[str, Any]]:
    records = []
    for log_dir in log_dirs:
        if not log_dir.exists():
            continue
        for path in sorted(log_dir.glob("*.eval")):
            records.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "source_commit": commit,
                    "path": repo_path(path),
                    "log_dir": repo_path(log_dir),
                    "filename": path.name,
                    "sha256": sha256_file(path),
                    "bytes": path.stat().st_size,
                }
            )
    return records


def result_records(commit: str, log_dirs: list[Path]) -> list[dict[str, Any]]:
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
            log_rows = extract_scores(eval_path, strict=True)
            if not log_rows:
                raise ValueError(
                    "No scored samples found in Inspect eval log: {}".format(eval_path)
                )
            rows.extend(log_rows)
    deduped = dedupe_rows(rows)
    if not deduped:
        raise ValueError("No scored result rows were exported.")
    records = []
    for row in deduped:
        scores = {
            key: value
            for key, value in row.items()
            if isinstance(value, float)
        }
        records.append(
            {
                "schema_version": SCHEMA_VERSION,
                "source_commit": commit,
                "model": row.get("model", "unknown"),
                "task": row.get("task", "unknown"),
                "track": classify_task(str(row.get("task", ""))),
                "status": row.get("status", "unknown"),
                "sample_id": str(row.get("sample_id", "")),
                "eval_log": row.get("eval_log", ""),
                "eval_log_path": repo_path(Path(str(row.get("eval_log_path", "")))),
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
) -> dict[str, Any]:
    commit = source_commit()
    out_dir.mkdir(parents=True, exist_ok=True)

    repository = source_repository()
    task_rows = task_records(commit)
    rubric_rows = rubric_records(commit)
    ground_truth_rows = ground_truth_records(commit)
    citation_rows = citation_records(commit)
    eval_log_rows = eval_log_manifest_records(commit, log_dirs)
    result_rows = result_records(commit, log_dirs) if include_results else []
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
    files.extend(plot_files)

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source_commit": commit,
        "source_repository": repository,
        "exporter": repo_path(Path(__file__)),
        "release_name": release_name,
        "result_sources": [repo_path(log_dir) for log_dir in log_dirs],
        "files": files,
    }
    write_json(out_dir / "release_manifest.json", manifest, out_dir)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
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
    manifest = build_export(
        out_dir=resolve_repo_path(args.out_dir),
        release_name=args.release_name,
        log_dirs=log_dirs,
        include_results=not args.no_results,
        copy_plots=args.copy_plots or bool(args.plot),
        plot_paths=plot_paths,
    )
    print(
        "Wrote LabCraft-Eval HF export to {} with {} files.".format(
            resolve_repo_path(args.out_dir),
            len(manifest["files"]),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
