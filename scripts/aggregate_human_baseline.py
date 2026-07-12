#!/usr/bin/env python3
"""Aggregate completed human baseline session JSONs into a markdown summary."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.trajectory_scorer import score_growth_trajectory, score_transform_trajectory  # noqa: E402

DEFAULT_SESSION_DIR = REPO_ROOT / "results" / "human_baseline_sessions"
DEFAULT_OUT = REPO_ROOT / "results" / "human_baseline_pilot.md"
DEFAULT_JSON_OUT = REPO_ROOT / "results" / "human_baseline_pilot.json"
DEFAULT_SNAPSHOT_RESULTS = REPO_ROOT / "results" / "results.md"
DEFAULT_SEED_PLAN = REPO_ROOT / "results" / "human_baseline_seed_plan.json"
AXES = ("overall", "task_success", "decision_quality", "troubleshooting", "efficiency")
TASK_SCORERS = {
    "transform_01": score_transform_trajectory,
    "growth_01": score_growth_trajectory,
}
MODEL_DISPLAY = {
    "openai/gpt-4o-mini": "gpt-4o-mini",
    "openai/gpt-4o": "gpt-4o",
    "anthropic/claude-haiku-4-5": "claude-haiku-4-5",
    "anthropic/claude-sonnet-4-5": "claude-sonnet-4-5",
}
FALLBACK_PILOT_PLAN = {
    "transform_01": (0, 2, 4),
    "growth_01": (1, 2, 3),
}


def resolve_repo_path(path_str: str) -> Path:
    path = Path(path_str)
    if not path.is_absolute():
        path = REPO_ROOT / path
    return path.resolve()


def repo_relative_display_path(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def resolve_stored_repo_path(path_str: str) -> Path:
    path = Path(path_str)
    if path.is_absolute():
        return path
    return (REPO_ROOT / path).resolve()


def _parse_updated_at(value: object) -> datetime:
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


def _strip_markdown_code(value: str) -> str:
    return value.strip().strip("`")


def load_seed_plan(seed_plan_path: Path) -> list[dict]:
    if seed_plan_path.exists():
        payload = json.loads(seed_plan_path.read_text())
        if isinstance(payload, dict) and isinstance(payload.get("pilot_entries"), list):
            entries = []
            for entry in payload["pilot_entries"]:
                if not isinstance(entry, dict):
                    continue
                task_id = entry.get("task_id")
                seed_index = entry.get("seed_index")
                if not isinstance(task_id, str) or not isinstance(seed_index, int):
                    continue
                entries.append(entry)
            if entries:
                return entries

    fallback_entries: list[dict] = []
    for task_id, seed_indices in FALLBACK_PILOT_PLAN.items():
        for seed_index in seed_indices:
            fallback_entries.append({"task_id": task_id, "seed_index": seed_index})
    return fallback_entries


def load_completed_sessions(session_dir: Path) -> list[dict]:
    rows: list[dict] = []
    if not session_dir.exists():
        return rows
    for session_path in sorted(session_dir.glob("*.json")):
        try:
            payload = json.loads(session_path.read_text())
        except Exception:
            continue
        if payload.get("status") != "completed":
            continue
        score = _score_session_payload(payload)
        if not isinstance(score, dict):
            continue
        row = {
            "task_id": payload.get("task_id", "unknown"),
            "seed_index": payload.get("seed_index"),
            "sample_id": payload.get("sample_id", session_path.stem),
            "operator_id": payload.get("operator_id", "anonymous"),
            "prompt_variant": payload.get("prompt_variant", "baseline"),
            "updated_at": payload.get("updated_at", ""),
            "session_path": session_path,
            "final_answer": payload.get("final_answer", ""),
            "score_source": payload.get("_score_source", "stored"),
        }
        for axis in AXES:
            row[axis] = float(score.get(axis, 0.0))
        rows.append(row)
    return rows


def _score_session_payload(payload: dict) -> dict | None:
    task_id = payload.get("task_id")
    scorer = TASK_SCORERS.get(task_id)
    final_answer = payload.get("final_answer")
    transcript = payload.get("transcript")
    ground_truth_path = payload.get("ground_truth_path")

    if (
        scorer is not None
        and isinstance(final_answer, str)
        and isinstance(transcript, list)
        and isinstance(ground_truth_path, str)
    ):
        candidate_paths = [resolve_stored_repo_path(ground_truth_path)]
        if isinstance(task_id, str):
            candidate_paths.append(REPO_ROOT / "task_data" / task_id / "ground_truth.json")
        for candidate_path in candidate_paths:
            if not candidate_path.exists():
                continue
            try:
                payload["_score_source"] = "rescored"
                return scorer(final_answer, transcript, str(candidate_path))
            except Exception:
                continue

    stored = payload.get("score")
    if isinstance(stored, dict):
        payload["_score_source"] = "stored_fallback" if scorer is not None else "stored"
        return stored
    return None


def dedupe_sessions(rows: list[dict]) -> list[dict]:
    latest_by_key: dict[tuple[str, str, str, str], dict] = {}
    for row in rows:
        key = (
            row["operator_id"],
            row["task_id"],
            row.get("prompt_variant", "baseline"),
            row["sample_id"],
        )
        current = latest_by_key.get(key)
        if current is None or _parse_updated_at(row.get("updated_at")) >= _parse_updated_at(current.get("updated_at")):
            latest_by_key[key] = row
    return sorted(
        latest_by_key.values(),
        key=lambda row: (
            row["operator_id"],
            row["task_id"],
            row.get("prompt_variant", "baseline"),
            str(row.get("seed_index", "")),
            row["sample_id"],
        ),
    )


def aggregate_by_operator_task(rows: list[dict]) -> list[dict]:
    groups: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    for row in rows:
        groups[(row["operator_id"], row["task_id"], row.get("prompt_variant", "baseline"))].append(row)

    summary: list[dict] = []
    for (operator_id, task_id, prompt_variant), cell_rows in sorted(groups.items()):
        entry = {
            "operator_id": operator_id,
            "task_id": task_id,
            "prompt_variant": prompt_variant,
            "n": len(cell_rows),
        }
        for axis in AXES:
            values = [row[axis] for row in cell_rows]
            entry[f"{axis}_mean"] = statistics.fmean(values) if values else 0.0
            entry[f"{axis}_std"] = statistics.stdev(values) if len(values) > 1 else 0.0
        summary.append(entry)
    return summary


def seeded_sample_id(task_id: str, seed_index: int) -> str:
    return "{}_seeded_seed_{:02d}".format(task_id, seed_index)


def load_snapshot_sample_scores(results_path: Path) -> dict[tuple[str, str], dict[str, dict]]:
    sample_scores: dict[tuple[str, str], dict[str, dict]] = {}
    if not results_path.exists():
        return sample_scores

    in_per_sample_table = False
    for raw_line in results_path.read_text().splitlines():
        line = raw_line.strip()
        if line == "## Per-sample detail":
            in_per_sample_table = True
            continue
        if not in_per_sample_table or not line.startswith("|"):
            continue

        cells = [_strip_markdown_code(cell) for cell in line.strip("|").split("|")]
        if len(cells) != 8 or cells[0] == "Model" or cells[0].startswith("---"):
            continue

        model, task_id, sample_id = (cell.strip() for cell in cells[:3])
        try:
            sample_scores.setdefault((task_id, sample_id), {})[model] = {
                "overall": float(cells[3].strip()),
                "task_success": float(cells[4].strip()),
                "decision_quality": float(cells[5].strip()),
                "troubleshooting": float(cells[6].strip()),
                "efficiency": float(cells[7].strip()),
            }
        except ValueError:
            continue

    return sample_scores


def summarize_snapshot_models(model_scores: dict[str, dict]) -> dict[str, object]:
    if not model_scores:
        return {
            "mean_overall": None,
            "best_model": "-",
            "best_overall": None,
            "range_display": "-",
            "scores_by_model": {},
        }

    overall_values = [row["overall"] for row in model_scores.values()]
    best_model = max(
        model_scores.items(),
        key=lambda item: (item[1]["overall"], MODEL_DISPLAY.get(item[0], item[0])),
    )[0]
    return {
        "mean_overall": statistics.fmean(overall_values),
        "best_model": MODEL_DISPLAY.get(best_model, best_model),
        "best_overall": model_scores[best_model]["overall"],
        "range_display": "{:.3f}-{:.3f}".format(min(overall_values), max(overall_values)),
        "scores_by_model": {
            MODEL_DISPLAY.get(model_name, model_name): row["overall"]
            for model_name, row in model_scores.items()
        },
    }


def build_pilot_coverage(
    rows: list[dict],
    snapshot_scores: dict[tuple[str, str], dict[str, dict]],
    seed_plan: list[dict],
) -> list[dict]:
    rows_by_key: dict[tuple[str, int], list[dict]] = defaultdict(list)
    for row in rows:
        seed_index = row.get("seed_index")
        if isinstance(seed_index, int):
            rows_by_key[(row["task_id"], seed_index)].append(row)

    coverage: list[dict] = []
    for plan_entry in seed_plan:
        task_id = plan_entry["task_id"]
        seed_index = plan_entry["seed_index"]
        sample_id = seeded_sample_id(task_id, seed_index)
        session_rows = rows_by_key.get((task_id, seed_index), [])
        operator_ids = sorted({row["operator_id"] for row in session_rows})
        prompt_groups: dict[str, list[dict]] = defaultdict(list)
        for row in session_rows:
            prompt_groups[row.get("prompt_variant", "baseline")].append(row)
        human_sessions_by_prompt = {
            prompt_variant: len(prompt_rows)
            for prompt_variant, prompt_rows in sorted(prompt_groups.items())
        }
        operators_by_prompt = {
            prompt_variant: sorted({row["operator_id"] for row in prompt_rows})
            for prompt_variant, prompt_rows in sorted(prompt_groups.items())
        }
        prompt_breakdown_display = (
            "; ".join(
                "{}: {}".format(prompt_variant, count)
                for prompt_variant, count in human_sessions_by_prompt.items()
            )
            if human_sessions_by_prompt
            else "-"
        )
        snapshot_summary = summarize_snapshot_models(snapshot_scores.get((task_id, sample_id), {}))
        coverage.append(
            {
                "task_id": task_id,
                "seed_index": seed_index,
                "sample_id": sample_id,
                "human_sessions": len(session_rows),
                "operators": ", ".join(operator_ids) if operator_ids else "-",
                "human_sessions_by_prompt": human_sessions_by_prompt,
                "operators_by_prompt": operators_by_prompt,
                "prompt_breakdown_display": prompt_breakdown_display,
                "snapshot_mean_overall": snapshot_summary["mean_overall"],
                "snapshot_best_model": snapshot_summary["best_model"],
                "snapshot_best_overall": snapshot_summary["best_overall"],
                "snapshot_range_display": snapshot_summary["range_display"],
                "selection_rationale": plan_entry.get("selection_rationale", ""),
                "snapshot_scores_by_model": snapshot_summary["scores_by_model"],
            }
        )
    return coverage


def build_human_vs_snapshot_rows(
    rows: list[dict], snapshot_scores: dict[tuple[str, str], dict[str, dict]]
) -> list[dict]:
    comparison_rows: list[dict] = []
    for row in rows:
        snapshot_summary = summarize_snapshot_models(
            snapshot_scores.get((row["task_id"], row["sample_id"]), {})
        )
        scores_by_model = snapshot_summary["scores_by_model"]
        comparison_rows.append(
            {
                "task_id": row["task_id"],
                "seed_index": row["seed_index"],
                "sample_id": row["sample_id"],
                "operator_id": row["operator_id"],
                "prompt_variant": row["prompt_variant"],
                "updated_at": row["updated_at"],
                "session_path": repo_relative_display_path(row["session_path"]),
                "score_source": row["score_source"],
                **{axis: row[axis] for axis in AXES},
                "snapshot_mean_overall": snapshot_summary["mean_overall"],
                "snapshot_best_model": snapshot_summary["best_model"],
                "snapshot_best_overall": snapshot_summary["best_overall"],
                "delta_vs_snapshot_mean": (
                    row["overall"] - snapshot_summary["mean_overall"]
                    if snapshot_summary["mean_overall"] is not None
                    else None
                ),
                "gpt_4o_mini_overall": scores_by_model.get("gpt-4o-mini"),
                "gpt_4o_overall": scores_by_model.get("gpt-4o"),
                "claude_haiku_overall": scores_by_model.get("claude-haiku-4-5"),
                "claude_sonnet_overall": scores_by_model.get("claude-sonnet-4-5"),
            }
        )
    return comparison_rows


def build_report_payload(
    session_dir: Path,
    rows: list[dict],
    deduped_count: int,
    snapshot_scores: dict[tuple[str, str], dict[str, dict]],
    seed_plan: list[dict],
    snapshot_results_path: Path,
    seed_plan_path: Path,
) -> dict[str, object]:
    coverage_rows = build_pilot_coverage(rows, snapshot_scores, seed_plan)
    summary_rows = aggregate_by_operator_task(rows) if rows else []
    comparison_rows = build_human_vs_snapshot_rows(rows, snapshot_scores) if rows else []

    serializable_sessions: list[dict[str, object]] = []
    for row in rows:
        session_rel = repo_relative_display_path(row["session_path"])
        serializable_sessions.append(
            {
                "task_id": row["task_id"],
                "seed_index": row["seed_index"],
                "sample_id": row["sample_id"],
                "operator_id": row["operator_id"],
                "prompt_variant": row["prompt_variant"],
                "updated_at": row["updated_at"],
                "session_path": session_rel,
                "score_source": row["score_source"],
                **{axis: row[axis] for axis in AXES},
            }
        )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "session_dir": repo_relative_display_path(session_dir),
        "snapshot_results_path": repo_relative_display_path(snapshot_results_path),
        "seed_plan_path": repo_relative_display_path(seed_plan_path),
        "deduped_older_session_count": deduped_count,
        "completed_session_count": len(rows),
        "has_completed_sessions": bool(rows),
        "coverage": coverage_rows,
        "summary": summary_rows,
        "human_vs_snapshot": comparison_rows,
        "sessions": serializable_sessions,
    }


def write_json_report(out_path: Path, payload: dict[str, object]) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True))


def _format_optional_score(value: float | None) -> str:
    if value is None:
        return "-"
    return "{:.3f}".format(value)


def format_markdown(
    session_dir: Path,
    rows: list[dict],
    out_path: Path,
    deduped_count: int,
    snapshot_scores: dict[tuple[str, str], dict[str, dict]],
    seed_plan: list[dict],
) -> None:
    session_dir_rel = repo_relative_display_path(session_dir)
    coverage_rows = build_pilot_coverage(rows, snapshot_scores, seed_plan)
    lines = [
        "# Human Baseline Pilot",
        "",
        "Manual baseline sessions aggregated from [{}](../{}).".format(session_dir_rel, session_dir_rel),
        "",
        "These sessions are intentionally separate from the frozen model-only portfolio snapshot. They provide early human context under the current prompt, scorer, and explicit-seed convention. Frozen same-label model rows are contextual only: they used an earlier seed convention and are not matched simulator instances.",
        "",
    ]

    if not rows:
        lines.extend(
            [
                "## Status",
                "",
                "No completed human baseline sessions have been checked in yet.",
                "",
                "The recommended first-pass collection set is documented in [results/human_baseline_seed_plan.md](../results/human_baseline_seed_plan.md).",
                "",
                "## Planned coverage",
                "",
                "| Task | Seed | Human sessions | Prompt split | Operators | Snapshot overall range | Snapshot best |",
                "|---|---:|---:|---|---|---:|---|",
            ]
        )
        for entry in coverage_rows:
            best_display = (
                "{} ({})".format(
                    _format_optional_score(entry["snapshot_best_overall"]),
                    entry["snapshot_best_model"],
                )
                if entry["snapshot_best_overall"] is not None
                else "-"
            )
            lines.append(
                "| `{task}` | {seed} | {human_sessions} | {prompt_breakdown} | {operators} | {score_range} | {best_display} |".format(
                    task=entry["task_id"],
                    seed=entry["seed_index"],
                    human_sessions=entry["human_sessions"],
                    prompt_breakdown=entry["prompt_breakdown_display"],
                    operators=entry["operators"],
                    score_range=entry["snapshot_range_display"],
                    best_display=best_display,
                )
            )
        lines.extend(
            [
                "",
                "## Next step",
                "",
                "Use [docs/human_baseline.md](../docs/human_baseline.md) together with the seed plan above, collect 1-3 expert sessions on `transform_01` and `growth_01`, then rerun:",
                "",
                "```bash",
                "python3 scripts/aggregate_human_baseline.py",
                "```",
                "",
                "The aggregator also writes a structured JSON sidecar for downstream plotting and comparison scripts.",
                "",
            ]
        )
        out_path.write_text("\n".join(lines))
        return

    if deduped_count:
        lines.extend(
            [
                "Repeated sessions with the same `(operator_id, task_id, prompt_variant, sample_id)` are deduplicated by keeping the latest JSON artifact. {} older session file(s) were ignored.".format(
                    deduped_count
                ),
                "",
            ]
        )

    summary = aggregate_by_operator_task(rows)
    lines.extend(
        [
            "## Summary",
            "",
            "| Operator | Task | Prompt | n | overall (mean±std) | task_success | decision_quality | troubleshooting | efficiency |",
            "|---|---|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for entry in summary:
        lines.append(
            "| {operator} | `{task}` | `{prompt}` | {n} | {ov_mean:.3f} ± {ov_std:.3f} | {ts_mean:.3f} ± {ts_std:.3f} | {dq_mean:.3f} ± {dq_std:.3f} | {tr_mean:.3f} ± {tr_std:.3f} | {ef_mean:.3f} ± {ef_std:.3f} |".format(
                operator=entry["operator_id"],
                task=entry["task_id"],
                prompt=entry["prompt_variant"],
                n=entry["n"],
                ov_mean=entry["overall_mean"],
                ov_std=entry["overall_std"],
                ts_mean=entry["task_success_mean"],
                ts_std=entry["task_success_std"],
                dq_mean=entry["decision_quality_mean"],
                dq_std=entry["decision_quality_std"],
                tr_mean=entry["troubleshooting_mean"],
                tr_std=entry["troubleshooting_std"],
                ef_mean=entry["efficiency_mean"],
                ef_std=entry["efficiency_std"],
            )
        )

    lines.extend(
        [
            "",
            "## Planned coverage",
            "",
            "| Task | Seed | Human sessions | Prompt split | Operators | Snapshot overall range | Snapshot best |",
            "|---|---:|---:|---|---|---:|---|",
        ]
    )
    for entry in coverage_rows:
        best_display = (
            "{} ({})".format(
                _format_optional_score(entry["snapshot_best_overall"]),
                entry["snapshot_best_model"],
            )
            if entry["snapshot_best_overall"] is not None
            else "-"
        )
        lines.append(
            "| `{task}` | {seed} | {human_sessions} | {prompt_breakdown} | {operators} | {score_range} | {best_display} |".format(
                task=entry["task_id"],
                seed=entry["seed_index"],
                human_sessions=entry["human_sessions"],
                prompt_breakdown=entry["prompt_breakdown_display"],
                operators=entry["operators"],
                score_range=entry["snapshot_range_display"],
                best_display=best_display,
            )
        )

    lines.extend(
        [
            "",
            "## Human vs snapshot models",
            "",
            "| Operator | Task | Prompt | Seed | Human overall | Vs snapshot mean | Snapshot best | gpt-4o-mini | gpt-4o | haiku | sonnet |",
            "|---|---|---|---:|---:|---:|---|---:|---:|---:|---:|",
        ]
    )
    for entry in build_human_vs_snapshot_rows(rows, snapshot_scores):
        snapshot_best = (
            "{} ({})".format(
                _format_optional_score(entry["snapshot_best_overall"]),
                entry["snapshot_best_model"],
            )
            if entry["snapshot_best_overall"] is not None
            else "-"
        )
        lines.append(
            "| {operator} | `{task}` | `{prompt}` | {seed} | {human:.3f} | {delta} | {snapshot_best} | {mini} | {gpt4o} | {haiku} | {sonnet} |".format(
                operator=entry["operator_id"],
                task=entry["task_id"],
                prompt=entry["prompt_variant"],
                seed=entry["seed_index"],
                human=entry["overall"],
                delta=_format_optional_score(entry["delta_vs_snapshot_mean"]),
                snapshot_best=snapshot_best,
                mini=_format_optional_score(entry["gpt_4o_mini_overall"]),
                gpt4o=_format_optional_score(entry["gpt_4o_overall"]),
                haiku=_format_optional_score(entry["claude_haiku_overall"]),
                sonnet=_format_optional_score(entry["claude_sonnet_overall"]),
            )
        )

    lines.extend(
        [
            "",
            "## Per-session detail",
            "",
            "| Operator | Task | Seed | Prompt | overall | task | decision | trouble | efficiency | Session |",
            "|---|---|---:|---|---:|---:|---:|---:|---:|---|",
        ]
    )
    for row in rows:
        session_rel = repo_relative_display_path(row["session_path"])
        lines.append(
            "| {operator} | `{task}` | {seed} | `{prompt}` | {overall:.3f} | {task_success:.3f} | {decision_quality:.3f} | {troubleshooting:.3f} | {efficiency:.3f} | [{label}](../{target}) |".format(
                operator=row["operator_id"],
                task=row["task_id"],
                seed=row["seed_index"],
                prompt=row["prompt_variant"],
                overall=row["overall"],
                task_success=row["task_success"],
                decision_quality=row["decision_quality"],
                troubleshooting=row["troubleshooting"],
                efficiency=row["efficiency"],
                label=row["session_path"].name,
                target=session_rel,
            )
        )

    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- Sessions are rescored during aggregation when a supported deterministic scorer and a resolvable ground-truth path are available; otherwise the stored session score is used as a fallback.",
            "- Final-answer template compliance still matters for humans, because task success is regex- and value-based rather than judge-model-based.",
            "- The aggregator also writes a structured JSON sidecar for downstream plotting and comparison scripts.",
            "",
        ]
    )
    out_path.write_text("\n".join(lines))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--session-dir",
        default=str(DEFAULT_SESSION_DIR),
        help="Directory containing saved human baseline session JSON files.",
    )
    parser.add_argument(
        "--out",
        default=str(DEFAULT_OUT),
        help="Markdown output path.",
    )
    parser.add_argument(
        "--json-out",
        default=str(DEFAULT_JSON_OUT),
        help="Structured JSON output path for downstream analysis and plotting.",
    )
    parser.add_argument(
        "--snapshot-results",
        default=str(DEFAULT_SNAPSHOT_RESULTS),
        help="Path to the frozen snapshot table used as a same-label historical reference.",
    )
    parser.add_argument(
        "--seed-plan",
        default=str(DEFAULT_SEED_PLAN),
        help="Machine-readable pilot seed plan JSON.",
    )
    args = parser.parse_args(argv)

    session_dir = resolve_repo_path(args.session_dir)
    out_path = resolve_repo_path(args.out)
    json_out_path = resolve_repo_path(args.json_out)
    snapshot_results_path = resolve_repo_path(args.snapshot_results)
    seed_plan_path = resolve_repo_path(args.seed_plan)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    rows = load_completed_sessions(session_dir)
    deduped_rows = dedupe_sessions(rows)
    snapshot_scores = load_snapshot_sample_scores(snapshot_results_path)
    seed_plan = load_seed_plan(seed_plan_path)
    report_payload = build_report_payload(
        session_dir=session_dir,
        rows=deduped_rows,
        deduped_count=len(rows) - len(deduped_rows),
        snapshot_scores=snapshot_scores,
        seed_plan=seed_plan,
        snapshot_results_path=snapshot_results_path,
        seed_plan_path=seed_plan_path,
    )
    format_markdown(
        session_dir=session_dir,
        rows=deduped_rows,
        out_path=out_path,
        deduped_count=len(rows) - len(deduped_rows),
        snapshot_scores=snapshot_scores,
        seed_plan=seed_plan,
    )
    write_json_report(json_out_path, report_payload)
    print(
        "Wrote {} completed session(s) to {} and {}".format(
            len(deduped_rows),
            out_path,
            json_out_path,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
