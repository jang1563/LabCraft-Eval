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
    task_ids = module.available_task_ids("snapshot")
    expected = ("transform_01", "growth_01", "pcr_01", "screen_01", "clone_01")
    if task_ids != expected:
        raise RuntimeError("Unexpected snapshot task ids: {}".format(task_ids))

    safety_task_ids = module.available_task_ids("safety_case")
    if safety_task_ids != ("safety_case_01",):
        raise RuntimeError("Unexpected safety-case task ids: {}".format(safety_task_ids))

    # Instantiating the task exercises packaged scenario data and the packaged
    # scope-exclusion keyword resource used by its scorer.
    safety_task = module.safety_case_01(seeds=1)
    if len(safety_task.dataset) != 30:
        raise RuntimeError(
            "Unexpected safety_case_01 sample count: {}".format(len(safety_task.dataset))
        )

    sample = module.build_transform_01_sample()
    for key in ("ground_truth_path", "rubric_path"):
        path = Path(sample["metadata"][key])
        if not path.exists():
            raise RuntimeError("Packaged task metadata path does not exist: {}".format(path))

    print(
        "labcraft {} package smoke passed with {} snapshot tasks and safety_case_01.".format(
            distribution.version,
            len(task_ids),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
