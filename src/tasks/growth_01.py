"""Growth-01 sample specification."""

from __future__ import annotations

import os
from pathlib import Path

from .base import TaskPaths

GROWTH_01_ROOT = Path(__file__).resolve().parents[2] / "task_data" / "growth_01"
GROWTH_01_PATHS = TaskPaths(task_id="growth_01", root=GROWTH_01_ROOT)
GROWTH_01_GROUND_TRUTH = GROWTH_01_PATHS.ground_truth
GROWTH_01_RUBRIC = GROWTH_01_PATHS.rubric

_BASELINE_PROMPT = """You are operating inside LabCraft, a stochastic microbiology simulator.

Task: Characterize early exponential E. coli growth across three conditions using OD600 measurements.

Conditions to test:
- LB
- M9 + glucose
- LB + chloramphenicol (1.8 uM)

Goal:
1. Choose a scientifically defensible early-exponential starting OD600 and use it for all three conditions.
2. Choose a scientifically defensible regular measurement cadence, no slower than the fastest expected doubling time, and collect OD600 values until each condition has enough usable points for an analyzable fit.
3. Use dilution when helpful so the growth-fit tool has enough usable OD600 points.
4. Run the growth-fit tool for each condition.
5. In your final answer, report the estimated doubling time for each condition and rank them from fastest to slowest.

Important constraints:
- Use the labels exactly as written above in the final answer.
- Use only the available lab tools and reference tools.
- The fit tool needs enough OD600 measurements in the cited fitting window to return an analyzable result.
- Batch tool calls across conditions whenever practical to avoid unnecessary turns.
- Do not stop to summarize after each interval; keep moving through the required tool batches until all conditions have analyzable fits.
"""

_VERBOSE_TROUBLESHOOT_PROMPT = """You are operating inside LabCraft, a stochastic microbiology simulator.

Task: Characterize early exponential E. coli growth across three conditions using OD600 measurements.

Conditions to test:
- LB
- M9 + glucose
- LB + chloramphenicol (1.8 uM)

Goal:
1. Choose a scientifically defensible early-exponential starting OD600 and use it for all three conditions.
2. Choose a scientifically defensible regular measurement cadence, no slower than the fastest expected doubling time, and collect OD600 values until each condition has enough usable points for an analyzable fit.
3. Use dilution when helpful so the growth-fit tool has enough usable OD600 points.
4. Run the growth-fit tool for each condition.
5. In your final answer, for each condition report the estimated doubling time, then rank them from fastest to slowest. IMPORTANT: if any of the fit_growth_curve calls returned status "insufficient_points" or warned that not enough OD600 measurements were in the usable fitting range, you must briefly explain which condition was affected and that the fit was undersampled before giving the final ranking.

Important constraints:
- Use the labels exactly as written above in the final answer.
- Use only the available lab tools and reference tools.
- The fit tool needs enough OD600 measurements in the cited fitting window to return an analyzable result.
- Batch tool calls across conditions whenever practical to avoid unnecessary turns.
- Do not stop to summarize after each interval; keep moving through the required tool batches until all conditions have analyzable fits.
"""

_PROMPT_VARIANTS = {
    "baseline": _BASELINE_PROMPT,
    "verbose_troubleshoot": _VERBOSE_TROUBLESHOOT_PROMPT,
}


def build_growth_01_prompt() -> str:
    variant = os.environ.get("LABCRAFT_GROWTH_PROMPT_VARIANT", "baseline")
    return _PROMPT_VARIANTS.get(variant, _BASELINE_PROMPT)


def build_growth_01_sample() -> dict:
    return {
        "id": "growth_01_seeded",
        "input": build_growth_01_prompt(),
        "target": str(GROWTH_01_GROUND_TRUTH),
        "metadata": {
            "task_id": "growth_01",
            "ground_truth_path": str(GROWTH_01_GROUND_TRUTH),
            "rubric_path": str(GROWTH_01_RUBRIC),
        },
    }
