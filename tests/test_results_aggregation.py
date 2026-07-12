import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_script_module(module_name: str, relative_path: str):
    script_path = REPO_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


aggregate_eval_results = _load_script_module(
    "aggregate_eval_results",
    "scripts/aggregate_eval_results.py",
)

plot_scorecard = _load_script_module(
    "plot_scorecard",
    "scripts/plot_scorecard.py",
)


def _fake_success_log():
    model = "openai/gpt-4o-mini"
    usage = SimpleNamespace(
        input_tokens=11,
        output_tokens=7,
        total_tokens=18,
        input_tokens_cache_read=3,
    )
    sample = SimpleNamespace(
        id="transform_01_seeded_seed_00",
        model_usage={model: usage},
        scores={"trajectory": SimpleNamespace(value={"overall": 0.75})},
        output=SimpleNamespace(model="gpt-4o-mini-2024-07-18"),
    )
    return SimpleNamespace(
        status="success",
        eval=SimpleNamespace(
            model=model,
            task="transform_01",
            created="2026-04-18T10:00:00+00:00",
            revision=SimpleNamespace(
                type="git",
                origin="https://github.com/example/LabCraft-Eval.git",
                commit="abc123",
                dirty=False,
            ),
            model_generate_config={"temperature": 0.2, "max_tokens": None},
            packages={"inspect_ai": "0.3.245"},
        ),
        samples=[sample],
    )


def test_extract_scores_preserves_eval_provenance_config_and_sample_usage(monkeypatch, tmp_path):
    monkeypatch.setattr("inspect_ai.log.read_eval_log", lambda _path: _fake_success_log())

    row = aggregate_eval_results.extract_scores(tmp_path / "example.eval")[0]

    assert row["eval_revision"] == {
        "type": "git",
        "origin": "https://github.com/example/LabCraft-Eval.git",
        "commit": "abc123",
        "dirty": False,
    }
    assert row["model_generate_config"] == {"temperature": 0.2}
    assert row["effective_generation_config"] == {"temperature": 0.2}
    assert row["requested_model"] == "openai/gpt-4o-mini"
    assert row["resolved_model"] == "gpt-4o-mini-2024-07-18"
    assert row["provider"] == "openai"
    assert row["inspect_version"] == "0.3.245"
    assert row["tokens"] == {
        "input": 11,
        "output": 7,
        "total": 18,
        "input_cache_read": 3,
    }


def test_extract_scores_is_strict_by_default_for_unreadable_logs(tmp_path):
    unreadable = tmp_path / "broken.eval"
    unreadable.write_text("not an Inspect log")

    with pytest.raises(RuntimeError, match="Failed to read Inspect eval log"):
        aggregate_eval_results.extract_scores(unreadable)
    assert aggregate_eval_results.extract_scores(unreadable, strict=False) == []


def test_extract_scores_is_strict_by_default_for_non_success_logs(monkeypatch, tmp_path):
    failed_log = _fake_success_log()
    failed_log.status = "error"
    monkeypatch.setattr("inspect_ai.log.read_eval_log", lambda _path: failed_log)

    with pytest.raises(RuntimeError, match="non-success status: error"):
        aggregate_eval_results.extract_scores(tmp_path / "failed.eval")
    assert aggregate_eval_results.extract_scores(tmp_path / "failed.eval", strict=False) == []


def test_plot_scorecard_rejects_non_success_logs(monkeypatch, tmp_path):
    failed_log = _fake_success_log()
    failed_log.status = "error"
    monkeypatch.setattr("inspect_ai.log.read_eval_log", lambda _path: failed_log)

    with pytest.raises(RuntimeError, match="non-success status: error"):
        plot_scorecard.extract_scores(tmp_path / "failed.eval")


def test_dedupe_rows_keeps_latest_rerun_per_sample():
    older = {
        "model": "anthropic/claude-haiku-4-5",
        "task": "express_01",
        "sample_id": "express_01_seeded_seed_00",
        "eval_log": "2026-04-16T18-31-19-00-00_express-01_old.eval",
        "eval_log_path": str(REPO_ROOT / "results" / "current_anthropic_logs" / "old.eval"),
        "overall": 0.95,
    }
    newer = {
        "model": "anthropic/claude-haiku-4-5",
        "task": "express_01",
        "sample_id": "express_01_seeded_seed_00",
        "eval_log": "2026-04-16T22-06-30-00-00_express-01_new.eval",
        "eval_log_path": str(REPO_ROOT / "results" / "current_anthropic_logs" / "new.eval"),
        "overall": 1.0,
    }
    distinct = {
        "model": "anthropic/claude-haiku-4-5",
        "task": "express_01",
        "sample_id": "express_01_seeded_seed_01",
        "eval_log": "2026-04-16T22-06-30-00-00_express-01_new.eval",
        "eval_log_path": str(REPO_ROOT / "results" / "current_anthropic_logs" / "new.eval"),
        "overall": 1.0,
    }

    deduped = aggregate_eval_results.dedupe_rows([older, newer, distinct])

    assert len(deduped) == 2
    rows_by_sample = {row["sample_id"]: row for row in deduped}
    assert rows_by_sample["express_01_seeded_seed_00"]["eval_log"] == newer["eval_log"]
    assert rows_by_sample["express_01_seeded_seed_00"]["overall"] == 1.0
    assert rows_by_sample["express_01_seeded_seed_01"]["eval_log"] == distinct["eval_log"]


def test_dedupe_rows_keeps_distinct_resolved_snapshots_for_same_alias():
    base = {
        "model": "anthropic/claude-sonnet-5",
        "requested_model": "anthropic/claude-sonnet-5",
        "provider": "anthropic",
        "task": "express_01",
        "sample_id": "express_01_seeded_seed_00",
        "created": "2026-07-11T01:00:00+00:00",
        "eval_log": "first.eval",
        "eval_log_path": "/tmp/first.eval",
        "overall": 0.5,
    }
    first = dict(base, resolved_model="claude-sonnet-5-20260701")
    second = dict(
        base,
        resolved_model="claude-sonnet-5-20260710",
        created="2026-07-11T02:00:00+00:00",
        eval_log="second.eval",
        eval_log_path="/tmp/second.eval",
        overall=0.9,
    )

    deduped = aggregate_eval_results.dedupe_rows([first, second])

    assert len(deduped) == 2
    assert {row["resolved_model"] for row in deduped} == {
        "claude-sonnet-5-20260701",
        "claude-sonnet-5-20260710",
    }
    assert aggregate_eval_results.model_resolution_conflicts(deduped) == {
        "anthropic/claude-sonnet-5": [
            "claude-sonnet-5-20260701",
            "claude-sonnet-5-20260710",
        ]
    }


def test_optional_provider_qualification_is_one_resolved_snapshot():
    base = {
        "model": "openai/gpt-4o-mini",
        "requested_model": "openai/gpt-4o-mini",
        "provider": "openai",
        "task": "transform_01",
        "sample_id": "transform_01_seeded_seed_00",
        "created": "2026-07-11T01:00:00+00:00",
        "eval_log": "first.eval",
        "eval_log_path": "/tmp/first.eval",
        "overall": 0.5,
    }
    unqualified = dict(base, resolved_model="gpt-4o-mini-2024-07-18")
    qualified = dict(
        base,
        resolved_model="openai/gpt-4o-mini-2024-07-18",
        created="2026-07-11T02:00:00+00:00",
        eval_log="second.eval",
        eval_log_path="/tmp/second.eval",
        overall=0.9,
    )

    deduped = aggregate_eval_results.dedupe_rows([unqualified, qualified])

    assert len(deduped) == 1
    assert deduped[0]["overall"] == 0.9
    assert aggregate_eval_results.model_resolution_conflicts(
        [unqualified, qualified]
    ) == {}


def test_sample_resolution_collapses_optional_provider_qualification():
    sample = SimpleNamespace(
        output=SimpleNamespace(model="gpt-4o-mini-2024-07-18"),
        messages=[SimpleNamespace(model="openai/gpt-4o-mini-2024-07-18")],
    )

    assert aggregate_eval_results.sample_resolved_models(sample, "openai") == [
        "gpt-4o-mini-2024-07-18"
    ]


def test_dedupe_rows_prefers_newer_created_timestamp_over_filename_order():
    older_by_time = {
        "model": "openai/gpt-4o-mini",
        "task": "transform_01",
        "sample_id": "transform_01_seeded_seed_00",
        "created": "2026-04-18T09:00:00+00:00",
        "eval_log": "zzz_old.eval",
        "eval_log_path": str(REPO_ROOT / "results" / "tmp" / "zzz_old.eval"),
        "overall": 0.1,
    }
    newer_by_time = {
        "model": "openai/gpt-4o-mini",
        "task": "transform_01",
        "sample_id": "transform_01_seeded_seed_00",
        "created": "2026-04-18T10:00:00+00:00",
        "eval_log": "aaa_new.eval",
        "eval_log_path": str(REPO_ROOT / "results" / "tmp" / "aaa_new.eval"),
        "overall": 0.9,
    }

    deduped = aggregate_eval_results.dedupe_rows([older_by_time, newer_by_time])

    assert len(deduped) == 1
    assert deduped[0]["overall"] == 0.9
    assert deduped[0]["eval_log"] == "aaa_new.eval"


def test_dedupe_rows_treats_invalid_created_as_older_than_valid_iso():
    invalid = {
        "model": "openai/gpt-4o-mini",
        "task": "transform_01",
        "sample_id": "transform_01_seeded_seed_00",
        "created": "not-a-time",
        "eval_log": "zzz_invalid.eval",
        "eval_log_path": str(REPO_ROOT / "results" / "tmp" / "zzz_invalid.eval"),
        "overall": 0.1,
    }
    valid = {
        "model": "openai/gpt-4o-mini",
        "task": "transform_01",
        "sample_id": "transform_01_seeded_seed_00",
        "created": "2026-04-18T10:00:00+00:00",
        "eval_log": "aaa_valid.eval",
        "eval_log_path": str(REPO_ROOT / "results" / "tmp" / "aaa_valid.eval"),
        "overall": 0.9,
    }

    deduped = aggregate_eval_results.dedupe_rows([invalid, valid])

    assert len(deduped) == 1
    assert deduped[0]["overall"] == 0.9


def test_plot_scorecard_dedupe_matches_aggregate_timestamp_logic():
    rows = [
        {
            "model": "openai/gpt-4o-mini",
            "task": "transform_01",
            "sample_id": "transform_01_seeded_seed_00",
            "created": "2026-04-18T09:00:00+00:00",
            "eval_log": "zzz_old.eval",
            "eval_log_path": str(REPO_ROOT / "results" / "tmp" / "zzz_old.eval"),
            "overall": 0.1,
            "task_success": 0.1,
            "decision_quality": 0.1,
            "troubleshooting": 0.1,
            "efficiency": 0.1,
        },
        {
            "model": "openai/gpt-4o-mini",
            "task": "transform_01",
            "sample_id": "transform_01_seeded_seed_00",
            "created": "2026-04-18T10:00:00+00:00",
            "eval_log": "aaa_new.eval",
            "eval_log_path": str(REPO_ROOT / "results" / "tmp" / "aaa_new.eval"),
            "overall": 0.9,
            "task_success": 0.9,
            "decision_quality": 0.9,
            "troubleshooting": 0.9,
            "efficiency": 0.9,
        },
    ]

    deduped = plot_scorecard.dedupe_rows(rows)

    assert len(deduped) == 1
    assert deduped[0]["overall"] == 0.9


def test_plot_scorecard_keeps_distinct_resolved_snapshots_for_same_alias():
    base = {
        "model": "anthropic/claude-sonnet-5",
        "requested_model": "anthropic/claude-sonnet-5",
        "provider": "anthropic",
        "task": "express_01",
        "sample_id": "express_01_seeded_seed_00",
        "created": "2026-07-11T01:00:00+00:00",
        "eval_log": "first.eval",
        "eval_log_path": "/tmp/first.eval",
        "overall": 0.5,
        "task_success": 0.5,
        "decision_quality": 0.5,
        "troubleshooting": 0.5,
        "efficiency": 0.5,
    }
    first = dict(base, resolved_model="claude-sonnet-5-20260701")
    second = dict(
        base,
        resolved_model="claude-sonnet-5-20260710",
        created="2026-07-11T02:00:00+00:00",
        eval_log="second.eval",
        eval_log_path="/tmp/second.eval",
        overall=0.9,
    )

    deduped = plot_scorecard.dedupe_rows([first, second])
    aggregated = plot_scorecard.aggregate(deduped)
    models = plot_scorecard.resolve_models(
        deduped, explicit_models=["anthropic/claude-sonnet-5"]
    )

    assert len(deduped) == 2
    assert len(aggregated) == 2
    assert models == [
        "anthropic/claude-sonnet-5 → anthropic/claude-sonnet-5-20260701",
        "anthropic/claude-sonnet-5 → anthropic/claude-sonnet-5-20260710",
    ]


def test_format_markdown_uses_plain_path_for_external_log_dir(tmp_path):
    out_path = tmp_path / "results.md"
    external_log_dir = Path("/tmp/external_logs_for_test")

    aggregate_eval_results.format_markdown(
        summary=[],
        per_sample_rows=[],
        out_path=out_path,
        log_dirs=[external_log_dir],
        deduped_count=0,
    )

    text = out_path.read_text()
    assert "`/tmp/external_logs_for_test`" in text
    assert "(..//tmp/external_logs_for_test)" not in text


def test_dynamic_aggregation_preserves_safety_case_axes(tmp_path):
    rows = [
        {
            "model": "anthropic/claude-haiku-4-5",
            "task": "safety_case_01",
            "sample_id": "sp_001",
            "eval_log": "safety.eval",
            "eval_log_path": str(tmp_path / "safety.eval"),
            "aggregate": 0.8,
            "legitimate_helpfulness": 0.7,
            "boundary_precision": 1.0,
        }
    ]

    axes = aggregate_eval_results.discover_axes(rows)
    summary = aggregate_eval_results.aggregate(rows, axes)

    assert axes == ["aggregate", "legitimate_helpfulness", "boundary_precision"]
    assert summary[0]["aggregate_mean"] == 0.8

    out_path = tmp_path / "safety_results.md"
    aggregate_eval_results.format_markdown(
        summary=summary,
        per_sample_rows=rows,
        out_path=out_path,
        log_dirs=[tmp_path],
        deduped_count=0,
        axes=axes,
    )
    text = out_path.read_text()
    assert "aggregate (mean±std)" in text
    assert "legitimate_helpfulness" in text
    assert "0.800 ± 0.000" in text
