#!/usr/bin/env python3
"""Render scorecard + axis breakdown charts from Inspect .eval logs.

Reads results/logs/*.eval, aggregates per-(model, task) mean and stddev across
each of the four scoring axes, and writes two PNGs:

- results/scorecard.png   : grouped bar chart, overall score per model per task
- results/axis_heatmap.png : per-axis score matrix, models x (task, axis)

Repeated reruns with the same `(model, task, sample_id)` are deduplicated by
keeping the latest `.eval` archive before aggregation.

Both are PNGs at 150 dpi so they render crisply on GitHub's README.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import os
import statistics
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOG_DIR = REPO_ROOT / "results" / "logs"
DEFAULT_OUT_DIR = REPO_ROOT / "results"
DEFAULT_MPLCONFIGDIR = REPO_ROOT / ".matplotlib"

os.environ.setdefault("MPLBACKEND", "Agg")
os.environ.setdefault("MPLCONFIGDIR", str(DEFAULT_MPLCONFIGDIR))
DEFAULT_MPLCONFIGDIR.mkdir(parents=True, exist_ok=True)

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

SNAPSHOT_TASKS = ["transform_01", "growth_01", "pcr_01", "screen_01", "clone_01"]
CURRENT_TASKS = SNAPSHOT_TASKS + [
    "golden_gate_01",
    "gibson_01",
    "miniprep_01",
    "express_01",
    "purify_01",
    "followup_01",
]
DISCOVERY_TASKS = [
    "perturb_followup_01",
    "target_prioritize_01",
    "target_validate_01",
]
ALL_TASKS = CURRENT_TASKS + DISCOVERY_TASKS
PREFERRED_MODELS = [
    "openai/gpt-4o-mini",
    "openai/gpt-4o",
    "anthropic/claude-haiku-4-5",
    "anthropic/claude-sonnet-4-5",
]
AXES = ("task_success", "decision_quality", "troubleshooting", "efficiency", "overall")

MODEL_SHORT = {
    "openai/gpt-4o-mini": "gpt-4o-mini",
    "openai/gpt-4o": "gpt-4o",
    "anthropic/claude-haiku-4-5": "haiku-4-5",
    "anthropic/claude-sonnet-4-5": "sonnet-4-5",
}

MODEL_COLORS = {
    "openai/gpt-4o-mini": "#7fcf9f",
    "openai/gpt-4o": "#2ea572",
    "anthropic/claude-haiku-4-5": "#e09f7d",
    "anthropic/claude-sonnet-4-5": "#c05621",
}


def _parse_created_timestamp(value: object) -> datetime:
    if not isinstance(value, str) or not value.strip():
        return datetime.min.replace(tzinfo=timezone.utc)
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return datetime.min.replace(tzinfo=timezone.utc)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def extract_scores(eval_path: Path):
    rows = []
    try:
        from inspect_ai.log import read_eval_log

        log = read_eval_log(str(eval_path))
    except Exception:
        return rows

    model = getattr(getattr(log, "eval", None), "model", "unknown")
    task = getattr(getattr(log, "eval", None), "task", "unknown")
    created = getattr(getattr(log, "eval", None), "created", "") or ""

    for sample in getattr(log, "samples", []) or []:
        scores = getattr(sample, "scores", {}) or {}
        value_block = None
        for scorer_info in scores.values():
            candidate = getattr(scorer_info, "value", None)
            if isinstance(candidate, dict):
                value_block = candidate
                break
        if value_block is None:
            continue
        row = {
            "model": model,
            "task": task,
            "sample_id": getattr(sample, "id", eval_path.stem),
            "eval_log": eval_path.name,
            "eval_log_path": str(eval_path.resolve()),
            "created": created,
        }
        for axis in AXES:
            row[axis] = float(value_block.get(axis, 0.0))
        rows.append(row)
    return rows


def dedupe_rows(rows):
    """Keep only the latest archive for each (model, task, sample_id)."""
    latest_by_sample = {}
    for row in rows:
        key = (row["model"], row["task"], row["sample_id"])
        current = latest_by_sample.get(key)
        row_order_key = (
            _parse_created_timestamp(row.get("created")),
            row.get("eval_log", ""),
            row.get("eval_log_path", ""),
        )
        if current is None:
            latest_by_sample[key] = row
            continue
        current_order_key = (
            _parse_created_timestamp(current.get("created")),
            current.get("eval_log", ""),
            current.get("eval_log_path", ""),
        )
        if row_order_key >= current_order_key:
            latest_by_sample[key] = row
    return sorted(
        latest_by_sample.values(),
        key=lambda row: (
            row["model"],
            row["task"],
            row["sample_id"],
            row.get("eval_log", ""),
        ),
    )


def load_all_rows(log_dirs: list[Path]):
    rows = []
    for log_dir in log_dirs:
        for path in sorted(log_dir.glob("*.eval")):
            rows.extend(extract_scores(path))
    return dedupe_rows(rows)


def aggregate(rows):
    cells = defaultdict(list)
    for row in rows:
        cells[(row["model"], row["task"])].append(row)
    agg = {}
    for (model, task), cell_rows in cells.items():
        entry = {"n": len(cell_rows)}
        for axis in AXES:
            values = [r[axis] for r in cell_rows]
            entry["{}_mean".format(axis)] = statistics.fmean(values) if values else 0.0
            entry["{}_std".format(axis)] = statistics.stdev(values) if len(values) > 1 else 0.0
        agg[(model, task)] = entry
    return agg


def _ordered_subset(preferred: list[str], observed: set[str]) -> list[str]:
    ordered = [item for item in preferred if item in observed]
    extras = sorted(observed - set(ordered))
    return ordered + extras


def resolve_tasks(rows, task_preset: str, explicit_tasks: list[str] | None) -> list[str]:
    if explicit_tasks:
        return explicit_tasks
    if task_preset == "snapshot":
        return list(SNAPSHOT_TASKS)
    if task_preset == "current":
        return list(CURRENT_TASKS)
    if task_preset == "discovery":
        return list(DISCOVERY_TASKS)
    if task_preset == "all":
        return list(ALL_TASKS)
    if task_preset == "auto":
        return _ordered_subset(ALL_TASKS, {row["task"] for row in rows})
    raise ValueError("Unknown task preset: {}".format(task_preset))


def resolve_models(rows, explicit_models: list[str] | None) -> list[str]:
    if explicit_models:
        return explicit_models
    return _ordered_subset(PREFERRED_MODELS, {row["model"] for row in rows})


def _model_label(model: str) -> str:
    return MODEL_SHORT.get(model, model.split("/")[-1])


def _model_color(model: str, index: int):
    if model in MODEL_COLORS:
        return MODEL_COLORS[model]
    return plt.get_cmap("tab10")(index % 10)


def _n_label(agg, tasks: list[str], models: list[str]) -> str:
    counts = sorted(
        {
            agg[(model, task)]["n"]
            for model in models
            for task in tasks
            if (model, task) in agg
        }
    )
    if not counts:
        return "N=0"
    if len(counts) == 1:
        suffix = "seed" if counts[0] == 1 else "seeds"
        return "N={} {} per cell".format(counts[0], suffix)
    return "N varies by cell"


def plot_scorecard(agg, tasks: list[str], models: list[str], out_dir: Path):
    fig_width = max(11.0, 1.35 * len(tasks) + 3.0)
    fig, ax = plt.subplots(figsize=(fig_width, 5.5))
    n_models = len(models)
    bar_width = 0.18
    x_positions = np.arange(len(tasks))

    for i, model in enumerate(models):
        means = [agg.get((model, task), {}).get("overall_mean", 0.0) for task in tasks]
        stds = [agg.get((model, task), {}).get("overall_std", 0.0) for task in tasks]
        offsets = x_positions + (i - (n_models - 1) / 2) * bar_width
        ax.bar(
            offsets,
            means,
            bar_width,
            yerr=stds,
            capsize=3,
            color=_model_color(model, i),
            label=_model_label(model),
            edgecolor="#222",
            linewidth=0.4,
            error_kw={"elinewidth": 1.0, "ecolor": "#333"},
        )

    n_label = _n_label(agg, tasks, models)
    ax.set_xticks(x_positions)
    if len(tasks) > 8:
        ax.set_xticklabels(tasks, fontsize=10, rotation=25, ha="right")
    else:
        ax.set_xticklabels(tasks, fontsize=11)
    ax.set_ylabel("Overall score (mean \u00b1 std; {})".format(n_label), fontsize=11)
    ax.set_ylim(0, 1.05)
    ax.set_yticks(np.arange(0.0, 1.01, 0.2))
    ax.axhline(1.0, color="#aaa", linestyle=":", linewidth=0.8)
    ax.grid(axis="y", linestyle="--", linewidth=0.4, alpha=0.5)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.set_title(
        "LabCraft-Eval overall score by model and task ({})".format(n_label),
        fontsize=12,
        pad=12,
    )
    ax.legend(
        loc="lower left",
        frameon=False,
        ncol=min(4, max(1, len(models))),
        fontsize=10,
        bbox_to_anchor=(0.0, -0.22),
    )

    plt.tight_layout()
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "scorecard.png"
    plt.savefig(out_path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return out_path


def plot_axis_heatmap(agg, tasks: list[str], models: list[str], out_dir: Path):
    display_axes = ("task_success", "decision_quality", "troubleshooting", "efficiency")
    axis_labels = {
        "task_success": "task",
        "decision_quality": "decision",
        "troubleshooting": "trouble",
        "efficiency": "efficiency",
    }

    rows = len(models)
    cols = len(tasks) * len(display_axes)
    matrix = np.full((rows, cols), np.nan)
    col_labels = []
    for task in tasks:
        for axis in display_axes:
            col_labels.append(axis_labels[axis])

    for j, task in enumerate(tasks):
        for k, axis in enumerate(display_axes):
            col = j * len(display_axes) + k
            for i, model in enumerate(models):
                entry = agg.get((model, task), {})
                matrix[i, col] = entry.get("{}_mean".format(axis), np.nan)

    fig_width = max(14.0, 0.35 * cols + 4.0)
    fig, ax = plt.subplots(figsize=(fig_width, 5.5))
    im = ax.imshow(matrix, cmap="RdYlGn", vmin=0.0, vmax=1.0, aspect="auto")

    ax.set_yticks(np.arange(rows))
    ax.set_yticklabels([_model_label(model) for model in models], fontsize=11)
    ax.set_xticks(np.arange(cols))
    ax.set_xticklabels(col_labels, fontsize=9.5, rotation=35, ha="right")

    ax_top = ax.secondary_xaxis("top")
    task_centers = [
        j * len(display_axes) + (len(display_axes) - 1) / 2 for j in range(len(tasks))
    ]
    ax_top.set_xticks(task_centers)
    ax_top.set_xticklabels(tasks, fontsize=11.0, fontweight="bold")
    ax_top.tick_params(axis="x", which="both", length=0, pad=6)

    for j in range(1, len(tasks)):
        left = j * len(display_axes) - 0.5
        ax.axvline(left, color="#222", linewidth=1.0)

    for i in range(rows):
        for k in range(cols):
            val = matrix[i, k]
            if np.isnan(val):
                continue
            color = "#111" if val > 0.55 else "#f5f5f5"
            ax.text(
                k,
                i,
                "{:.2f}".format(val),
                ha="center",
                va="center",
                fontsize=9.5,
                color=color,
            )

    n_label = _n_label(agg, tasks, models)
    fig.suptitle(
        "Per-axis breakdown: mean score (0 - 1) across {}".format(n_label),
        fontsize=12.5,
        y=0.97,
    )
    cbar = fig.colorbar(im, ax=ax, shrink=0.82, pad=0.015)
    cbar.ax.tick_params(labelsize=9)
    plt.subplots_adjust(top=0.80, bottom=0.20, left=0.10, right=0.95)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "axis_heatmap.png"
    plt.savefig(out_path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return out_path


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--log-dir",
        nargs="+",
        default=[str(DEFAULT_LOG_DIR)],
        help="One or more directories containing Inspect .eval archives.",
    )
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument(
        "--task-preset",
        choices=("snapshot", "current", "all", "discovery", "auto"),
        default="snapshot",
        help="Task set to plot when --tasks is not provided.",
    )
    parser.add_argument(
        "--tasks",
        nargs="+",
        help="Explicit task ids to plot. Overrides --task-preset.",
    )
    parser.add_argument(
        "--models",
        nargs="+",
        help="Explicit model ids to plot. Defaults to the models found in the logs.",
    )
    args = parser.parse_args(argv)

    log_dirs = []
    for path_str in args.log_dir:
        path = Path(path_str)
        if not path.is_absolute():
            path = REPO_ROOT / path
        log_dirs.append(path.resolve())
    out_dir = Path(args.out_dir)
    if not out_dir.is_absolute():
        out_dir = (REPO_ROOT / out_dir).resolve()

    rows = load_all_rows(log_dirs)
    if not rows:
        print(
            "No .eval files found in {}".format(", ".join(str(path) for path in log_dirs)),
            file=sys.stderr,
        )
        return 1
    agg = aggregate(rows)
    tasks = resolve_tasks(rows, task_preset=args.task_preset, explicit_tasks=args.tasks)
    models = resolve_models(rows, explicit_models=args.models)
    if not tasks:
        print("No tasks selected for plotting.", file=sys.stderr)
        return 1
    if not models:
        print("No models selected for plotting.", file=sys.stderr)
        return 1
    if not any((model, task) in agg for model in models for task in tasks):
        print(
            "Selected tasks/models are not present in {}".format(
                ", ".join(str(path) for path in log_dirs)
            ),
            file=sys.stderr,
        )
        return 1

    scorecard_path = plot_scorecard(agg, tasks=tasks, models=models, out_dir=out_dir)
    heatmap_path = plot_axis_heatmap(agg, tasks=tasks, models=models, out_dir=out_dir)
    print("Wrote {} and {}".format(scorecard_path, heatmap_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
