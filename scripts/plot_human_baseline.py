#!/usr/bin/env python3
"""Render human-baseline pilot coverage and frozen same-label context plots."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT = REPO_ROOT / "results" / "human_baseline_pilot.json"
DEFAULT_OUT_DIR = REPO_ROOT / "results" / "human_baseline_plots"
DEFAULT_MPLCONFIGDIR = REPO_ROOT / ".matplotlib"

os.environ.setdefault("MPLBACKEND", "Agg")
os.environ.setdefault("MPLCONFIGDIR", str(DEFAULT_MPLCONFIGDIR))
DEFAULT_MPLCONFIGDIR.mkdir(parents=True, exist_ok=True)

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

MODEL_ORDER = [
    "gpt-4o-mini",
    "gpt-4o",
    "claude-haiku-4-5",
    "claude-sonnet-4-5",
]

MODEL_COLORS = {
    "gpt-4o-mini": "#7fcf9f",
    "gpt-4o": "#2ea572",
    "claude-haiku-4-5": "#e09f7d",
    "claude-sonnet-4-5": "#c05621",
}

HUMAN_PROMPT_MARKERS = {
    "baseline": "o",
    "verbose_troubleshoot": "D",
}


def resolve_repo_path(path_str: str) -> Path:
    path = Path(path_str)
    if not path.is_absolute():
        path = REPO_ROOT / path
    return path.resolve()


def load_report(report_path: Path) -> dict:
    return json.loads(report_path.read_text())


def _seed_label(entry: dict) -> str:
    return "{}\nseed {:02d}".format(entry["task_id"], int(entry["seed_index"]))


def _prompt_breakdown_label(entry: dict) -> str:
    breakdown = entry.get("human_sessions_by_prompt", {})
    if not isinstance(breakdown, dict) or not breakdown:
        return ""
    abbreviations = {
        "baseline": "base",
        "verbose_troubleshoot": "verb",
    }
    parts = []
    for prompt_variant, count in sorted(breakdown.items()):
        parts.append("{}:{}".format(abbreviations.get(prompt_variant, prompt_variant), count))
    return " | ".join(parts)


def plot_coverage(report: dict, out_dir: Path) -> Path:
    coverage = report.get("coverage", [])
    labels = [_seed_label(entry) for entry in coverage]
    counts = [int(entry.get("human_sessions", 0)) for entry in coverage]
    ranges = [entry.get("snapshot_range_display", "-") for entry in coverage]
    prompt_breakdowns = [_prompt_breakdown_label(entry) for entry in coverage]
    colors = ["#2ea572" if count > 0 else "#cbd5e1" for count in counts]

    fig_width = max(9.5, 1.25 * len(labels) + 2.0)
    fig, ax = plt.subplots(figsize=(fig_width, 4.8))
    x_positions = np.arange(len(labels))
    bars = ax.bar(x_positions, counts, color=colors, edgecolor="#334155", linewidth=0.6)

    y_top = max(counts) if counts else 0
    ax.set_ylim(0, max(1.2, y_top + 1.0))
    ax.set_ylabel("Completed human sessions", fontsize=11)
    ax.set_xticks(x_positions)
    ax.set_xticklabels(labels, fontsize=10)
    ax.set_title(
        "Human baseline pilot coverage\n(frozen same-label overall range annotated)",
        fontsize=12,
        pad=12,
    )
    ax.grid(axis="y", linestyle="--", linewidth=0.4, alpha=0.5)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    for bar, count, score_range, prompt_breakdown in zip(bars, counts, ranges, prompt_breakdowns):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            count + 0.03,
            str(count),
            ha="center",
            va="bottom",
            fontsize=10,
            color="#111827",
        )
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            max(0.08, count + 0.22),
            score_range,
            ha="center",
            va="bottom",
            fontsize=8,
            rotation=90,
            color="#475569",
        )
        if prompt_breakdown:
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                max(0.08, count * 0.55 if count > 0 else 0.14),
                prompt_breakdown,
                ha="center",
                va="bottom",
                fontsize=7,
                color="#1f2937",
            )

    plt.tight_layout()
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "coverage.png"
    plt.savefig(out_path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return out_path


def plot_seed_context(report: dict, out_dir: Path) -> Path:
    coverage = report.get("coverage", [])
    labels = [_seed_label(entry) for entry in coverage]
    x_positions = np.arange(len(labels))
    n_models = len(MODEL_ORDER)
    bar_width = 0.18

    fig_width = max(10.5, 1.35 * len(labels) + 3.5)
    fig, ax = plt.subplots(figsize=(fig_width, 5.4))

    for i, model_name in enumerate(MODEL_ORDER):
        means = [
            float(entry.get("snapshot_scores_by_model", {}).get(model_name, np.nan))
            if entry.get("snapshot_scores_by_model", {}).get(model_name) is not None
            else np.nan
            for entry in coverage
        ]
        offsets = x_positions + (i - (n_models - 1) / 2) * bar_width
        ax.bar(
            offsets,
            means,
            bar_width,
            color=MODEL_COLORS[model_name],
            label=model_name,
            edgecolor="#222",
            linewidth=0.4,
        )

    sessions_by_seed: dict[tuple[str, int], list[dict]] = {}
    for session in report.get("sessions", []):
        key = (session["task_id"], int(session["seed_index"]))
        sessions_by_seed.setdefault(key, []).append(session)

    human_labels_added: set[str] = set()
    for idx, entry in enumerate(coverage):
        seed_key = (entry["task_id"], int(entry["seed_index"]))
        sessions = sessions_by_seed.get(seed_key, [])
        if not sessions:
            continue
        jitter_offsets = np.linspace(-0.08, 0.08, num=len(sessions)) if len(sessions) > 1 else [0.0]
        for jitter, session in zip(jitter_offsets, sessions):
            prompt_variant = session.get("prompt_variant", "baseline")
            marker = HUMAN_PROMPT_MARKERS.get(prompt_variant, "o")
            legend_label = "human ({})".format(prompt_variant)
            ax.scatter(
                x_positions[idx] + jitter,
                float(session["overall"]),
                color="#111827",
                edgecolor="white",
                linewidth=0.6,
                s=44,
                zorder=4,
                marker=marker,
                label=legend_label if legend_label not in human_labels_added else None,
            )
            human_labels_added.add(legend_label)

    ax.set_xticks(x_positions)
    ax.set_xticklabels(labels, fontsize=10)
    ax.set_ylabel("Overall score", fontsize=11)
    ax.set_ylim(0, 1.05)
    ax.set_yticks(np.arange(0.0, 1.01, 0.2))
    ax.axhline(1.0, color="#94a3b8", linestyle=":", linewidth=0.8)
    ax.grid(axis="y", linestyle="--", linewidth=0.4, alpha=0.5)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.set_title(
        "Pilot label context: historical model scores with current human overlays",
        fontsize=12,
        pad=12,
    )
    ax.legend(
        loc="lower left",
        frameon=False,
        ncol=min(6, len(MODEL_ORDER) + len(human_labels_added)),
        fontsize=9,
        bbox_to_anchor=(0.0, -0.24),
    )

    plt.tight_layout()
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "seed_context.png"
    plt.savefig(out_path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return out_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--report",
        default=str(DEFAULT_REPORT),
        help="Structured JSON report generated by scripts/aggregate_human_baseline.py.",
    )
    parser.add_argument(
        "--out-dir",
        default=str(DEFAULT_OUT_DIR),
        help="Output directory for PNG plots.",
    )
    args = parser.parse_args(argv)

    report_path = resolve_repo_path(args.report)
    out_dir = resolve_repo_path(args.out_dir)
    report = load_report(report_path)

    coverage_path = plot_coverage(report, out_dir)
    context_path = plot_seed_context(report, out_dir)
    print("Wrote {} and {}".format(coverage_path, context_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
