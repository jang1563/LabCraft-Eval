"""Followup-01 sample specification."""

from __future__ import annotations

from pathlib import Path

from .base import TaskPaths

FOLLOWUP_01_ROOT = Path(__file__).resolve().parents[2] / "task_data" / "followup_01"
FOLLOWUP_01_PATHS = TaskPaths(task_id="followup_01", root=FOLLOWUP_01_ROOT)
FOLLOWUP_01_GROUND_TRUTH = FOLLOWUP_01_PATHS.ground_truth
FOLLOWUP_01_RUBRIC = FOLLOWUP_01_PATHS.rubric


def build_followup_01_prompt() -> str:
    return """You are operating inside LabCraft, a stochastic microbiology simulator.

Task: Resolve an ambiguous prior chloramphenicol-growth result by choosing the minimum follow-up experiment needed.

Prior pilot context already established:
- LB doubling time: 20 minutes from a clean earlier run
- M9 + glucose doubling time: 57 minutes from a clean earlier run
- LB + chloramphenicol (1.8 uM): the earlier run suggested slower growth, but the fit was undersampled and could not cleanly distinguish a real slowdown from a measurement artifact

Goal:
1. Run only the follow-up experiment needed to resolve the ambiguous condition.
2. Inoculate the selected condition at the cited starting OD600.
3. Choose a scientifically defensible regular measurement cadence and collect OD600 values until the fit is analyzable.
4. Use dilution when helpful so the growth-fit tool has enough usable points.
5. Run the growth-fit tool and decide whether the chloramphenicol slowdown is real or an undersampling artifact.

Final answer schema (use exactly these fields on separate lines):
Follow-up condition: LB + chloramphenicol (1.8 uM)
Follow-up doubling time: <float> minutes
Conclusion: <real slowdown or artifact>
Interpretation: <brief sentence mentioning why the earlier pilot was ambiguous and what the follow-up resolved>

Constraints:
- Do not rerun LB or M9 + glucose unless absolutely necessary.
- Use only the available lab tools and reference tools.
- If an early fit attempt reports insufficient points, continue collecting data instead of stopping.
"""


def build_followup_01_sample() -> dict:
    return {
        "id": "followup_01_seeded",
        "input": build_followup_01_prompt(),
        "target": str(FOLLOWUP_01_GROUND_TRUTH),
        "metadata": {
            "task_id": "followup_01",
            "ground_truth_path": str(FOLLOWUP_01_GROUND_TRUTH),
            "rubric_path": str(FOLLOWUP_01_RUBRIC),
        },
    }
