"""Safety-case-01 dataset builder: 30 scenarios as Inspect Sample dicts."""

from __future__ import annotations

import json
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_SCENARIOS_PATH = _ROOT / "data" / "safety_case" / "scenarios.json"


def _goal_to_prompt(scenario: dict) -> str:
    """Convert a scenario dict into a first-person researcher prompt."""
    sc_type = scenario["scenario_type"].replace("_", " ")
    goal = scenario["benign_goal"]
    allowed = scenario["allowed_help"]
    help_items = ", ".join(allowed) if isinstance(allowed, list) else str(allowed)
    return (
        f"I'm working on a {sc_type} experiment. {goal}.\n\n"
        f"Could you help me with the following: {help_items}?"
    )


def build_safety_case_01_samples() -> list:
    """Return one Sample dict per scenario (30 total)."""
    with open(_SCENARIOS_PATH) as fh:
        raw = json.load(fh)

    samples = []
    for scenario in raw["scenarios"]:
        samples.append(
            {
                "id": scenario["id"],
                "input": _goal_to_prompt(scenario),
                "target": scenario["id"],
                "metadata": {
                    "task_id": "safety_case_01",
                    "scenario_id": scenario["id"],
                    "scenario_type": scenario["scenario_type"],
                    "boundary_label": scenario["boundary_label"],
                    "required_monitor_events": scenario["required_monitor_events"],
                    "benign_goal": scenario["benign_goal"],
                    "allowed_help": scenario["allowed_help"],
                    "expected_outcome": scenario.get("expected_outcome", ""),
                    "safe_citation_refs": scenario.get("safe_citation_refs", []),
                },
            }
        )
    return samples
