"""Read-only LabCraft-Eval leaderboard Space.

The helper functions intentionally use only the Python standard library so they
can be tested without installing the Space runtime dependencies. Gradio and
huggingface_hub are imported lazily when the app is launched in a Space.
"""

from __future__ import annotations

from collections import defaultdict
import hashlib
import json
from pathlib import Path
import statistics
from urllib.request import urlretrieve

DATASET_ID = "jang1563/LabCraft-Eval"
DEFAULT_REVISION = "v0.1.1"
DEFAULT_SNAPSHOT_DIR = Path("data/labcraft_eval")
REQUIRED_FILES = (
    "release_manifest.json",
    "tasks.jsonl",
    "result_rows.jsonl",
    "eval_log_manifest.jsonl",
)
PLOT_FILES = ("plots/scorecard.png", "plots/axis_heatmap.png")
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


def resolve_url(path: str, revision: str = DEFAULT_REVISION) -> str:
    return "https://huggingface.co/datasets/{}/resolve/{}/{}".format(
        DATASET_ID,
        revision,
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


def validate_snapshot(snapshot_dir: Path) -> None:
    manifest = read_json(snapshot_dir / "release_manifest.json")
    entries = {
        entry.get("path"): entry
        for entry in manifest.get("files", [])
        if isinstance(entry, dict) and isinstance(entry.get("path"), str)
    }
    errors = []
    for relative in REQUIRED_FILES[1:] + PLOT_FILES:
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
    if errors:
        raise RuntimeError("Invalid leaderboard snapshot: {}".format("; ".join(errors)))


def ensure_snapshot(snapshot_dir: Path = DEFAULT_SNAPSHOT_DIR, revision: str = DEFAULT_REVISION) -> Path:
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    for path in REQUIRED_FILES + PLOT_FILES:
        target = snapshot_dir / path
        target.parent.mkdir(parents=True, exist_ok=True)
        _download_atomic(resolve_url(path, revision=revision), target)
    validate_snapshot(snapshot_dir)
    return snapshot_dir


def load_snapshot(snapshot_dir: Path) -> tuple[dict, list[dict], list[dict], list[dict]]:
    validate_snapshot(snapshot_dir)
    manifest = read_json(snapshot_dir / "release_manifest.json")
    tasks = read_jsonl(snapshot_dir / "tasks.jsonl")
    results = read_jsonl(snapshot_dir / "result_rows.jsonl")
    logs = read_jsonl(snapshot_dir / "eval_log_manifest.jsonl")
    return manifest, tasks, results, logs


def available_tracks(tasks: list[dict], results: list[dict]) -> list[str]:
    tracks = {task.get("track", "other") for task in tasks}
    tracks.update(row.get("track", "other") for row in results)
    ordered = ["snapshot", "current_wet_lab", "followup", "discovery", "safety_case", "other"]
    return [track for track in ordered if track in tracks]


def numeric_score(row: dict, axis: str) -> float | None:
    scores = row.get("scores", {})
    value = scores.get(axis)
    if isinstance(value, int | float):
        return float(value)
    return None


def summarize_scores(results: list[dict], track: str) -> list[dict]:
    grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in results:
        if row.get("track") == track:
            grouped[(row.get("model", "unknown"), row.get("task", "unknown"))].append(row)

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
        model = row.get("model", "unknown")
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
) -> str:
    return "\n".join(
        [
            "### Provenance",
            "",
            "| Field | Value |",
            "| --- | --- |",
            "| Release | `{}` |".format(manifest.get("release_name", "unknown")),
            "| Source commit | `{}` |".format(manifest.get("source_commit", "unknown")),
            "| Schema version | `{}` |".format(manifest.get("schema_version", "unknown")),
            "| Task rows | {} |".format(len(tasks)),
            "| Result rows | {} |".format(len(results)),
            "| Eval logs | {} |".format(len(logs)),
            "| Manifest files | {} |".format(len(manifest.get("files", []))),
            "",
            "Pinned dataset: [{} @ {}](https://huggingface.co/datasets/{}/tree/{})".format(
                DATASET_ID, DEFAULT_REVISION, DATASET_ID, DEFAULT_REVISION
            ),
            "Manifest: [release_manifest.json]({})".format(
                resolve_url("release_manifest.json")
            ),
        ]
    )


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
) -> tuple[str, str, str, str]:
    title = "## {}".format(TRACK_LABELS.get(track, track))
    score_table = markdown_table(
        summarize_scores(results, track),
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
    axis_table = markdown_table(
        summarize_axes(results, track),
        [("Model", "model"), ("Axis", "axis"), ("Mean", "mean"), ("n", "n")],
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
    provenance = provenance_markdown(manifest, tasks, results, logs)
    return title, score_table, axis_table, inventory_table + "\n\n" + provenance


def build_demo():
    import gradio as gr

    snapshot_dir = ensure_snapshot()
    manifest, tasks, results, logs = load_snapshot(snapshot_dir)
    tracks = available_tracks(tasks, results)
    default_track = "snapshot" if "snapshot" in tracks else tracks[0]

    def update(track: str):
        return render_track(track, manifest, tasks, results, logs)

    with gr.Blocks(title="LabCraft-Eval Leaderboard") as demo:
        gr.Markdown(
            "# LabCraft-Eval Leaderboard\n"
            "Manifest-backed read-only view of the public Hugging Face dataset export."
        )
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
            gr.Image(str(snapshot_dir / "plots" / "scorecard.png"), label="Scorecard")
            gr.Image(str(snapshot_dir / "plots" / "axis_heatmap.png"), label="Axis heatmap")

        outputs = [title, scorecard, axes, inventory]
        track.change(update, inputs=track, outputs=outputs)
        demo.load(lambda: update(default_track), outputs=outputs)
    return demo


if __name__ == "__main__":
    build_demo().launch()
