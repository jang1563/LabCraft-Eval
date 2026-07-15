#!/usr/bin/env python3
"""Smoke test a built LabCraft wheel from outside the source checkout."""

from __future__ import annotations

from importlib import metadata
from pathlib import Path


def main() -> int:
    distribution = metadata.distribution("labcraft")
    if not distribution.version:
        raise RuntimeError("Installed labcraft distribution has no version.")

    entry_points = metadata.entry_points(group="inspect_ai")
    matches = [entry for entry in entry_points if entry.name == "labcraft"]
    if not matches:
        raise RuntimeError("Missing inspect_ai entry point named 'labcraft'.")

    entry_point = matches[0]
    if entry_point.value != "src.inspect_task":
        raise RuntimeError(
            "Unexpected labcraft entry point target: {}".format(entry_point.value)
        )

    module = entry_point.load()
    from inspect_ai.model import get_model_info

    gpt_56_info = get_model_info("openai/gpt-5.6-sol")
    if (
        gpt_56_info is None
        or gpt_56_info.context_length != 1_050_000
        or gpt_56_info.output_tokens != 128_000
    ):
        raise RuntimeError("Packaged GPT-5.6 ModelInfo registration is missing or stale.")

    task_ids = module.available_task_ids("snapshot")
    expected = ("transform_01", "growth_01", "pcr_01", "screen_01", "clone_01")
    if task_ids != expected:
        raise RuntimeError("Unexpected snapshot task ids: {}".format(task_ids))

    safety_task_ids = module.available_task_ids("safety_case")
    if safety_task_ids != ("safety_case_01",):
        raise RuntimeError("Unexpected safety-case task ids: {}".format(safety_task_ids))

    p2b_task_ids = module.available_task_ids("p2b_dev")
    if p2b_task_ids != ("pcr_causal_reasoning_01",):
        raise RuntimeError("Unexpected P2b development task ids: {}".format(p2b_task_ids))

    # Instantiating the task exercises packaged scenario data and the packaged
    # scope-exclusion keyword resource used by its scorer.
    safety_task = module.safety_case_01(seeds=1)
    if len(safety_task.dataset) != 30:
        raise RuntimeError(
            "Unexpected safety_case_01 sample count: {}".format(len(safety_task.dataset))
        )

    p2b_task = module.pcr_causal_reasoning_01(seeds=1)
    if len(p2b_task.dataset) != 2:
        raise RuntimeError(
            "Unexpected pcr_causal_reasoning_01 sample count: {}".format(
                len(p2b_task.dataset)
            )
        )

    sample = module.build_transform_01_sample()
    for key in ("ground_truth_path", "rubric_path"):
        path = Path(sample["metadata"][key])
        if not path.exists():
            raise RuntimeError("Packaged task metadata path does not exist: {}".format(path))

    from src.p2b_contracts import promotion_blockers, validate_p2b_contract
    from src.scorer_contracts import review_progress, run_scorer_regression

    scorer_errors = run_scorer_regression()
    if scorer_errors:
        raise RuntimeError(
            "Packaged P1 scorer regression failed:\n{}".format("\n".join(scorer_errors))
        )
    scorer_review = review_progress()
    if (
        scorer_review["required"] != 35
        or scorer_review["approved"] < 0
        or scorer_review["pending"] < 0
        or scorer_review["approved"] + scorer_review["pending"]
        != scorer_review["required"]
        or (
            scorer_review["promotion_ready"]
            and scorer_review["approved"] != scorer_review["required"]
        )
    ):
        raise RuntimeError(
            "Inconsistent packaged scorer review state: {}".format(scorer_review)
        )

    p2b_errors = validate_p2b_contract()
    if p2b_errors:
        raise RuntimeError(
            "Packaged P2b scorer regression failed:\n{}".format("\n".join(p2b_errors))
        )
    expected_p2b_blockers = {
        "expert_review_skipped",
        "evaluation_policy_not_ready",
        "external_evaluation_not_authorized",
        "scientific_validity_unassessed",
    }
    if set(promotion_blockers()) != expected_p2b_blockers:
        raise RuntimeError("Packaged P2b promotion blockers are missing or stale.")

    print(
        "labcraft {} package smoke passed with {} snapshot tasks, safety_case_01, "
        "{} P1 scorer fixtures, and a non-promotable P2b contract.".format(
            distribution.version,
            len(task_ids),
            scorer_review["required"],
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
