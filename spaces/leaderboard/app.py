"""Read-only LabCraft-Eval leaderboard Space.

The data-loading helpers intentionally use only the Python standard library so
they can be tested without installing the Space runtime dependencies. Gradio is
imported lazily when the app is launched in a Space.
"""

from __future__ import annotations

from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import statistics
from urllib.request import urlretrieve

DATASET_ID = "jang1563/LabCraft-Eval"
RELEASES = {
    "v0.1.2": {
        "dataset_revision": "b320a569a74986110c5a4aba32c970d406f4ae08",
        "expected_source_commit": "189aacc5314647f106ca9a902b025f23377ff5ab",
        "expected_schema_version": "0.3.0",
        "selector_label": "v0.1.2 — Current metadata and task contracts (no scores)",
        "evidence_label": "Current · metadata-only",
        "score_bearing": False,
        "description": (
            "This is the current public task, schema, citation, and manifest contract. "
            "It intentionally publishes no benchmark scores or raw evaluation logs."
        ),
    },
    "v0.1.1": {
        "dataset_revision": "309e32dacc063bf016416a517c17648a343662fc",
        "expected_source_commit": "d04dadd135dc62c6223d0f992c8a5949bcb72a46",
        "expected_schema_version": "0.1.0",
        "selector_label": "v0.1.1 — Historical provisional scores",
        "evidence_label": "Historical · provisional score-bearing",
        "score_bearing": True,
        "description": (
            "These frozen development scores predate the current clean-evaluation "
            "contract. They are historical evidence, not a current model comparison."
        ),
    },
}
DEFAULT_REVISION = "v0.1.2"
DEFAULT_RELEASE_LABEL = RELEASES[DEFAULT_REVISION]["selector_label"]
REVISION_BY_LABEL = {
    config["selector_label"]: revision for revision, config in RELEASES.items()
}
DEFAULT_SNAPSHOT_DIR = Path("data/labcraft_eval")
REQUIRED_FILES = (
    "release_manifest.json",
    "tasks.jsonl",
)
OPTIONAL_JSONL_FILES = ("result_rows.jsonl", "eval_log_manifest.jsonl")
PLOT_FILES = ("plots/scorecard.png", "plots/axis_heatmap.png")
DOWNLOADABLE_FILES = REQUIRED_FILES + OPTIONAL_JSONL_FILES + PLOT_FILES
AXES = ("overall", "decision_quality", "task_success", "troubleshooting", "efficiency")
TRACK_LABELS = {
    "snapshot": "Frozen simulator snapshot",
    "current_wet_lab": "Current wet-lab tasks",
    "followup": "Follow-up decision task",
    "discovery": "Discovery Decision Track",
    "safety_case": "Safety Case Track",
    "other": "Other",
}


def read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def read_jsonl(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def release_config(revision: str) -> dict:
    try:
        return RELEASES[revision]
    except KeyError as exc:
        raise ValueError("Unsupported leaderboard revision: {}".format(revision)) from exc


def resolve_url(path: str, revision: str = DEFAULT_REVISION) -> str:
    config = release_config(revision)
    if path not in DOWNLOADABLE_FILES:
        raise ValueError("Unsupported leaderboard file: {}".format(path))
    return "https://huggingface.co/datasets/{}/resolve/{}/{}".format(
        DATASET_ID,
        config["dataset_revision"],
        path,
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _download_atomic(url: str, target: Path) -> None:
    temporary = target.with_name(target.name + ".download")
    try:
        urlretrieve(url, temporary)
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)


def _requires_resolved_model_provenance(schema_version: object) -> bool:
    if not isinstance(schema_version, str):
        return False
    try:
        major, minor, *_rest = (
            int(part) for part in schema_version.split(".")
        )
    except (TypeError, ValueError):
        return False
    return (major, minor) >= (0, 3)


def validate_model_provenance(manifest: dict, results: list[dict]) -> list[str]:
    """Fail closed for current snapshots while retaining legacy read support."""
    if not _requires_resolved_model_provenance(manifest.get("schema_version")):
        return []

    errors = []
    resolutions: dict[str, set[str]] = defaultdict(set)
    required = {
        "requested_model",
        "resolved_model",
        "provider",
        "effective_generation_config",
        "inspect_version",
    }
    for index, row in enumerate(results, start=1):
        missing = sorted(
            field for field in required if row.get(field) in (None, "", {})
        )
        if missing:
            errors.append(
                "result row {} missing model provenance: {}".format(
                    index, ", ".join(missing)
                )
            )
            continue
        if row.get("model") != row.get("requested_model"):
            errors.append(
                "result row {} model differs from requested_model".format(index)
            )
        if row.get("model_generate_config") != row.get(
            "effective_generation_config"
        ):
            errors.append(
                "result row {} generation configs disagree".format(index)
            )
        resolutions[str(row["requested_model"])].add(str(row["resolved_model"]))

    for requested, resolved in sorted(resolutions.items()):
        if len(resolved) > 1:
            errors.append(
                "requested model {} resolves to multiple snapshots: {}".format(
                    requested, ", ".join(sorted(resolved))
                )
            )
    return errors


def validate_score_evidence(results: list[dict], logs: list[dict]) -> list[str]:
    """Validate the minimum invariants required to display score-bearing evidence."""
    errors = []
    if not results:
        errors.append("score-bearing release has zero result rows")
    if not logs:
        errors.append("score-bearing release has zero eval-log rows")

    log_paths = {
        row.get("path")
        for row in logs
        if isinstance(row, dict) and isinstance(row.get("path"), str)
    }
    sample_keys = set()
    for index, row in enumerate(results, start=1):
        if not isinstance(row, dict):
            errors.append("result row {} is not an object".format(index))
            continue
        missing = sorted(
            field
            for field in (
                "model",
                "task",
                "track",
                "sample_id",
                "eval_log_path",
                "scores",
            )
            if row.get(field) in (None, "", {})
        )
        if missing:
            errors.append(
                "result row {} missing required fields: {}".format(index, ", ".join(missing))
            )
        key = (row.get("model"), row.get("task"), row.get("sample_id"))
        if key in sample_keys:
            errors.append("duplicate model/task/sample_id in result row {}".format(index))
        sample_keys.add(key)
        if row.get("eval_log_path") not in log_paths:
            errors.append("result row {} eval log is absent from log manifest".format(index))

        scores = row.get("scores")
        if not isinstance(scores, dict) or "overall" not in scores:
            errors.append("result row {} scores missing overall".format(index))
            continue
        for axis, value in scores.items():
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(float(value))
                or not 0.0 <= float(value) <= 1.0
            ):
                errors.append(
                    "result row {} score {} must be finite and within [0, 1]".format(
                        index, axis
                    )
                )
    return errors


def manifest_entries(manifest: dict) -> dict[str, dict]:
    return {
        entry.get("path"): entry
        for entry in manifest.get("files", [])
        if isinstance(entry, dict) and isinstance(entry.get("path"), str)
    }


def snapshot_download_paths(manifest: dict) -> tuple[str, ...]:
    """Return only files used by the app and declared by the pinned manifest."""
    entries = manifest_entries(manifest)
    paths = ["tasks.jsonl"]
    for relative in OPTIONAL_JSONL_FILES:
        if relative in entries:
            paths.append(relative)
    if "result_rows.jsonl" in entries:
        paths.extend(relative for relative in PLOT_FILES if relative in entries)
    return tuple(paths)


def validate_snapshot(snapshot_dir: Path, revision: str | None = None) -> None:
    manifest = read_json(snapshot_dir / "release_manifest.json")
    entries = manifest_entries(manifest)
    errors = []
    manifest_paths = [
        entry.get("path")
        for entry in manifest.get("files", [])
        if isinstance(entry, dict) and isinstance(entry.get("path"), str)
    ]
    duplicate_paths = sorted(
        {relative for relative in manifest_paths if manifest_paths.count(relative) > 1}
    )
    if duplicate_paths:
        errors.append("manifest has duplicate paths: {}".format(", ".join(duplicate_paths)))

    if revision is not None:
        config = release_config(revision)
        release_name = manifest.get("release_name")
        if release_name != revision:
            errors.append(
                "release name {} does not match pinned revision {}".format(
                    release_name or "unknown", revision
                )
            )
        if manifest.get("source_commit") != config["expected_source_commit"]:
            errors.append("source commit does not match pinned revision {}".format(revision))
        if manifest.get("schema_version") != config["expected_schema_version"]:
            errors.append("schema version does not match pinned revision {}".format(revision))
        score_bearing = "result_rows.jsonl" in entries
        if score_bearing != config["score_bearing"]:
            errors.append(
                "release evidence contract does not match pinned revision {}".format(revision)
            )
        if config["score_bearing"] and "eval_log_manifest.jsonl" not in entries:
            errors.append("score-bearing release is missing eval_log_manifest.jsonl")

    for relative, entry in entries.items():
        record_count = entry.get("record_count")
        if isinstance(record_count, bool) or not isinstance(record_count, int) or record_count < 0:
            errors.append("manifest has invalid or missing record_count for {}".format(relative))

    for relative in snapshot_download_paths(manifest):
        entry = entries.get(relative)
        path = snapshot_dir / relative
        if entry is None:
            errors.append("manifest missing {}".format(relative))
            continue
        if not path.exists():
            errors.append("snapshot missing {}".format(relative))
            continue
        if entry.get("bytes") != path.stat().st_size:
            errors.append("byte count mismatch for {}".format(relative))
        if entry.get("sha256") != sha256_file(path):
            errors.append("sha256 mismatch for {}".format(relative))
        if path.suffix == ".jsonl":
            record_count = len(read_jsonl(path))
            if entry.get("record_count") != record_count:
                errors.append("record count mismatch for {}".format(relative))
    result_path = snapshot_dir / "result_rows.jsonl"
    log_path = snapshot_dir / "eval_log_manifest.jsonl"
    if "result_rows.jsonl" in entries and result_path.exists():
        results = read_jsonl(result_path)
        logs = (
            read_jsonl(log_path)
            if "eval_log_manifest.jsonl" in entries and log_path.exists()
            else []
        )
        errors.extend(validate_score_evidence(results, logs))
        errors.extend(validate_model_provenance(manifest, results))
    elif revision is not None and not release_config(revision)["score_bearing"]:
        logs = (
            read_jsonl(log_path)
            if "eval_log_manifest.jsonl" in entries and log_path.exists()
            else []
        )
        if logs:
            errors.append("metadata-only release has eval-log rows")
    if errors:
        raise RuntimeError("Invalid leaderboard snapshot: {}".format("; ".join(errors)))


def ensure_snapshot(
    snapshot_dir: Path | None = None,
    revision: str = DEFAULT_REVISION,
) -> Path:
    release_config(revision)
    if snapshot_dir is None:
        snapshot_dir = DEFAULT_SNAPSHOT_DIR / revision
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    try:
        validate_snapshot(snapshot_dir, revision=revision)
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError):
        pass
    else:
        return snapshot_dir
    manifest_path = snapshot_dir / "release_manifest.json"
    _download_atomic(resolve_url("release_manifest.json", revision=revision), manifest_path)
    manifest = read_json(manifest_path)
    if "tasks.jsonl" not in manifest_entries(manifest):
        raise RuntimeError("Invalid leaderboard snapshot: manifest missing tasks.jsonl")
    download_paths = snapshot_download_paths(manifest)

    for path in OPTIONAL_JSONL_FILES + PLOT_FILES:
        if path not in download_paths:
            (snapshot_dir / path).unlink(missing_ok=True)
    for path in download_paths:
        target = snapshot_dir / path
        target.parent.mkdir(parents=True, exist_ok=True)
        _download_atomic(resolve_url(path, revision=revision), target)
    validate_snapshot(snapshot_dir, revision=revision)
    return snapshot_dir


def load_snapshot(
    snapshot_dir: Path,
    revision: str | None = None,
) -> tuple[dict, list[dict], list[dict], list[dict]]:
    validate_snapshot(snapshot_dir, revision=revision)
    manifest = read_json(snapshot_dir / "release_manifest.json")
    entries = manifest_entries(manifest)
    tasks = read_jsonl(snapshot_dir / "tasks.jsonl")
    results = (
        read_jsonl(snapshot_dir / "result_rows.jsonl")
        if "result_rows.jsonl" in entries
        else []
    )
    logs = (
        read_jsonl(snapshot_dir / "eval_log_manifest.jsonl")
        if "eval_log_manifest.jsonl" in entries
        else []
    )
    return manifest, tasks, results, logs


def available_tracks(tasks: list[dict], results: list[dict]) -> list[str]:
    tracks = {
        value if isinstance(value, str) and value else "other"
        for value in [
            *(task.get("track") for task in tasks),
            *(row.get("track") for row in results),
        ]
    }
    ordered = ["snapshot", "current_wet_lab", "followup", "discovery", "safety_case", "other"]
    return [track for track in ordered if track in tracks] + sorted(tracks - set(ordered))


def numeric_score(row: dict, axis: str) -> float | None:
    scores = row.get("scores", {})
    value = scores.get(axis)
    if not isinstance(value, bool) and isinstance(value, int | float) and math.isfinite(value):
        return float(value)
    return None


def model_label(row: dict) -> str:
    """Prefer provider-resolved identity while keeping legacy rows readable."""
    requested = row.get("requested_model") or row.get("model", "unknown")
    resolved = row.get("resolved_model")
    provider = row.get("provider")
    if not isinstance(resolved, str) or not resolved:
        return str(requested)
    qualified = (
        resolved
        if "/" in resolved or not provider
        else "{}/{}".format(provider, resolved)
    )
    if qualified == requested:
        return str(requested)
    return "{} → {}".format(requested, qualified)


def summarize_scores(results: list[dict], track: str) -> list[dict]:
    grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in results:
        if row.get("track") == track:
            grouped[(model_label(row), row.get("task", "unknown"))].append(row)

    summary = []
    for (model, task), rows in sorted(grouped.items()):
        overall = [numeric_score(row, "overall") for row in rows]
        overall_values = [value for value in overall if value is not None]
        if not overall_values:
            continue
        item = {
            "model": model,
            "task": task,
            "n": len(overall_values),
            "overall_mean": statistics.fmean(overall_values),
            "overall_std": statistics.stdev(overall_values) if len(overall_values) > 1 else 0.0,
        }
        for axis in AXES[1:]:
            values = [numeric_score(row, axis) for row in rows]
            values = [value for value in values if value is not None]
            if values:
                item[axis] = statistics.fmean(values)
        summary.append(item)
    return summary


def summarize_axes(results: list[dict], track: str) -> list[dict]:
    grouped: dict[tuple[str, str], list[float]] = defaultdict(list)
    for row in results:
        if row.get("track") != track:
            continue
        model = model_label(row)
        for axis in AXES:
            value = numeric_score(row, axis)
            if value is not None:
                grouped[(model, axis)].append(value)

    return [
        {
            "model": model,
            "axis": axis,
            "mean": statistics.fmean(values),
            "n": len(values),
        }
        for (model, axis), values in sorted(grouped.items())
    ]


def task_inventory(tasks: list[dict], track: str) -> list[dict]:
    return [
        {
            "task_id": task.get("task_id", ""),
            "title": task.get("task_title", ""),
            "domain": task.get("domain", ""),
            "objective": task.get("objective", ""),
        }
        for task in sorted(tasks, key=lambda item: item.get("task_id", ""))
        if task.get("track") == track
    ]


def provenance_markdown(
    manifest: dict,
    tasks: list[dict],
    results: list[dict],
    logs: list[dict],
    revision: str,
) -> str:
    config = release_config(revision)
    return "\n".join(
        [
            "### Provenance",
            "",
            "| Field | Value |",
            "| --- | --- |",
            "| Release | `{}` |".format(manifest.get("release_name", "unknown")),
            "| Evidence tier | {} |".format(config["evidence_label"]),
            "| Pinned revision | `{}` |".format(revision),
            "| Immutable dataset commit | `{}` |".format(config["dataset_revision"]),
            "| Source commit | `{}` |".format(manifest.get("source_commit", "unknown")),
            "| Schema version | `{}` |".format(manifest.get("schema_version", "unknown")),
            "| Task rows | {} |".format(len(tasks)),
            "| Result rows | {} |".format(len(results)),
            "| Eval logs | {} |".format(len(logs)),
            "| Manifest files | {} |".format(len(manifest.get("files", []))),
            "",
            "Pinned dataset: [{} @ {}](https://huggingface.co/datasets/{}/tree/{})".format(
                DATASET_ID, revision, DATASET_ID, config["dataset_revision"]
            ),
            "Manifest: [release_manifest.json]({})".format(
                resolve_url("release_manifest.json", revision=revision)
            ),
        ]
    )


def evidence_markdown(revision: str, manifest: dict, results: list[dict]) -> str:
    config = release_config(revision)
    result_note = (
        "This snapshot contains **{} result rows**.".format(len(results))
        if results
        else "This snapshot contains **no published result rows**."
    )
    return "\n".join(
        [
            "## Evidence tier: {}".format(config["evidence_label"]),
            "",
            "**{}**".format(config["description"]),
            "{} Release `{}`; schema `{}`; source commit `{}`.".format(
                result_note,
                manifest.get("release_name", "unknown"),
                manifest.get("schema_version", "unknown"),
                manifest.get("source_commit", "unknown"),
            ),
        ]
    )


def no_score_markdown(revision: str, track: str) -> str:
    config = release_config(revision)
    if not config["score_bearing"]:
        return (
            "_No score-bearing evidence is published for this release. "
            "Use the Inventory and Provenance tab to inspect current task contracts._"
        )
    return "_No historical provisional score rows are available for track `{}`._".format(track)


def plot_view(
    snapshot_dir: Path,
    manifest: dict,
    results: list[dict],
) -> tuple[str, str | None, str | None]:
    if not results:
        return (
            "_No score-bearing plots are shown for this metadata-only release. "
            "Copied historical plot assets, if present upstream, are intentionally hidden._",
            None,
            None,
        )

    entries = manifest_entries(manifest)
    paths = [
        str(snapshot_dir / relative)
        if relative in entries and (snapshot_dir / relative).exists()
        else None
        for relative in PLOT_FILES
    ]
    available = sum(path is not None for path in paths)
    if not available:
        note = "_No plot artifacts were published for this score-bearing release._"
    elif available < len(PLOT_FILES):
        note = "_Only the manifest-backed plot artifacts published with this release are shown._"
    else:
        note = "_Plots are manifest-backed artifacts from the selected historical release._"
    return note, paths[0], paths[1]


def markdown_table(rows: list[dict], columns: list[tuple[str, str]], precision: int = 3) -> str:
    if not rows:
        return "_No rows for this track._"
    header = "| " + " | ".join(label for label, _key in columns) + " |"
    divider = "| " + " | ".join("---" for _label, _key in columns) + " |"
    body = []
    for row in rows:
        values = []
        for _label, key in columns:
            value = row.get(key, "")
            if isinstance(value, float):
                values.append("{:.{}f}".format(value, precision))
            else:
                values.append(str(value))
        body.append("| " + " | ".join(values) + " |")
    return "\n".join([header, divider] + body)


def render_track(
    track: str,
    manifest: dict,
    tasks: list[dict],
    results: list[dict],
    logs: list[dict],
    revision: str = DEFAULT_REVISION,
) -> tuple[str, str, str, str]:
    title = "## {}".format(TRACK_LABELS.get(track, track))
    score_rows = summarize_scores(results, track)
    axis_rows = summarize_axes(results, track)
    score_table = (
        markdown_table(
            score_rows,
            [
                ("Model", "model"),
                ("Task", "task"),
                ("n", "n"),
                ("Overall", "overall_mean"),
                ("Std", "overall_std"),
                ("Decision", "decision_quality"),
                ("Success", "task_success"),
                ("Troubleshooting", "troubleshooting"),
                ("Efficiency", "efficiency"),
            ],
        )
        if score_rows
        else no_score_markdown(revision, track)
    )
    axis_table = (
        markdown_table(
            axis_rows,
            [("Model", "model"), ("Axis", "axis"), ("Mean", "mean"), ("n", "n")],
        )
        if axis_rows
        else no_score_markdown(revision, track)
    )
    inventory_table = markdown_table(
        task_inventory(tasks, track),
        [
            ("Task", "task_id"),
            ("Title", "title"),
            ("Domain", "domain"),
            ("Objective", "objective"),
        ],
    )
    provenance = provenance_markdown(manifest, tasks, results, logs, revision)
    return title, score_table, axis_table, inventory_table + "\n\n" + provenance


def get_release_snapshot(snapshots: dict, revision: str):
    """Load a release on first use and memoize its validated immutable snapshot."""
    if revision not in snapshots:
        snapshot_dir = ensure_snapshot(revision=revision)
        manifest, tasks, results, logs = load_snapshot(snapshot_dir, revision=revision)
        snapshots[revision] = (snapshot_dir, manifest, tasks, results, logs)
    return snapshots[revision]


def build_demo():
    import gradio as gr

    snapshots = {}
    _snapshot_dir, _manifest, default_tasks, default_results, _logs = (
        get_release_snapshot(snapshots, DEFAULT_REVISION)
    )
    tracks = available_tracks(default_tasks, default_results)
    if not tracks:
        tracks = ["other"]
    default_track = "snapshot" if "snapshot" in tracks else tracks[0]

    def update(release_label: str, track: str):
        try:
            revision = REVISION_BY_LABEL[release_label]
        except KeyError as exc:
            raise ValueError("Unsupported release selection") from exc
        snapshot_dir, manifest, tasks, results, logs = get_release_snapshot(
            snapshots, revision
        )
        title, scorecard, axes, inventory = render_track(
            track,
            manifest,
            tasks,
            results,
            logs,
            revision=revision,
        )
        plot_note, score_plot, axis_plot = plot_view(snapshot_dir, manifest, results)
        return (
            evidence_markdown(revision, manifest, results),
            title,
            scorecard,
            axes,
            inventory,
            plot_note,
            score_plot,
            axis_plot,
        )

    with gr.Blocks(title="LabCraft-Eval Leaderboard") as demo:
        gr.Markdown(
            "# LabCraft-Eval Leaderboard\n"
            "Manifest-backed read-only view of pinned public Hugging Face releases."
        )
        release = gr.Dropdown(
            choices=list(REVISION_BY_LABEL),
            value=DEFAULT_RELEASE_LABEL,
            label="Release and evidence tier",
        )
        evidence = gr.Markdown()
        track = gr.Dropdown(
            choices=tracks,
            value=default_track,
            label="Benchmark track",
        )
        title = gr.Markdown()
        with gr.Tab("Scorecard"):
            scorecard = gr.Markdown()
        with gr.Tab("Axes"):
            axes = gr.Markdown()
        with gr.Tab("Inventory and Provenance"):
            inventory = gr.Markdown()
        with gr.Tab("Plots"):
            plot_note = gr.Markdown()
            score_plot = gr.Image(label="Scorecard", interactive=False)
            axis_plot = gr.Image(label="Axis heatmap", interactive=False)

        outputs = [
            evidence,
            title,
            scorecard,
            axes,
            inventory,
            plot_note,
            score_plot,
            axis_plot,
        ]
        inputs = [release, track]
        release.change(update, inputs=inputs, outputs=outputs)
        track.change(update, inputs=inputs, outputs=outputs)
        demo.load(
            lambda: update(DEFAULT_RELEASE_LABEL, default_track),
            outputs=outputs,
        )
    return demo


if __name__ == "__main__":
    build_demo().launch()
