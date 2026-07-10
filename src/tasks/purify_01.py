"""Purify-01 sample specification."""

from __future__ import annotations

from pathlib import Path

from .base import TaskPaths

PURIFY_01_ROOT = Path(__file__).resolve().parents[2] / "task_data" / "purify_01"
PURIFY_01_PATHS = TaskPaths(task_id="purify_01", root=PURIFY_01_ROOT)
PURIFY_01_GROUND_TRUTH = PURIFY_01_PATHS.ground_truth
PURIFY_01_RUBRIC = PURIFY_01_PATHS.rubric


def build_purify_01_prompt() -> str:
    return """You are operating inside LabCraft, a stochastic microbiology simulator.

Task: Purify a His-tagged benign MBP-GFP fusion (~72 kDa) from a clarified E. coli lysate by Ni-NTA affinity chromatography, then report the purified concentration, SDS-PAGE band result, and purity percentage.

Call the run_nta_purification tool exactly once with your chosen conditions.
Select a compatible affinity resin, load/wash/elution imidazole concentrations,
flow rate, and bed volume from your scientific knowledge of the stated His-tag
purification workflow.

Final answer schema (use exactly these fields on separate lines):
Resin: <resin name>
Load imidazole: <int> mM
Wash imidazole: <int> mM
Elute imidazole: <int> mM
Expected band size: <float> kDa
Purified concentration: <float> mg/mL
SDS-PAGE result: <verbatim from tool>
Purity: <float>%
Interpretation: <success|failure>

Constraints:
- Use only the available lab tools and reference tools.
- The target protein is a benign MBP-GFP fusion; do not attempt purification of toxins, cytokines, or any out-of-scope protein.
"""


def build_purify_01_sample() -> dict:
    return {
        "id": "purify_01_seeded",
        "input": build_purify_01_prompt(),
        "target": str(PURIFY_01_GROUND_TRUTH),
        "metadata": {
            "task_id": "purify_01",
            "ground_truth_path": str(PURIFY_01_GROUND_TRUTH),
            "rubric_path": str(PURIFY_01_RUBRIC),
        },
    }
