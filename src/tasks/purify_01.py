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

Task: Use the seeded clarified native lysate
`purification_lysate_his6_mbp_gfp_001`, which contains the benign His6-MBP-GFP
benchmark fusion (~72 kDa) from an accepted upstream expression. Purify it on
the fixed 4 mL Ni-NTA Superflow column and report the causal eluate observations.

Call the run_nta_purification tool exactly once with your chosen conditions.
Pass the lysate ID exactly as supplied. First retrieve the exact seeded benchmark
workflow by calling lookup_reagent with the lysate ID. Select the load, wash, and
elution imidazole concentrations and flow rate from that retrieved task
configuration. Do not substitute a valid alternative from another resin or
physical purification protocol: this task evaluates the declared simulator
contract. Recovery, eluate volume, purity, and band observations are synthetic
calibrations rather than universal biological claims. Copy the returned IDs and
observations; do not invent them.

Final answer schema (use exactly these fields on separate lines):
Lysate ID: <id>
Purification ID: <id>
Resin: <verbatim from tool>
Column bed volume: <float> mL
Load imidazole: <float> mM
Wash imidazole: <float> mM
Elute imidazole: <float> mM
Flow rate: <float> mL/min
Expected band size: <float> kDa
Recovered target mass: <float> mg
Eluate volume: <float> mL
Purified concentration: <float> mg/mL
SDS-PAGE result: <verbatim from tool>
Purity: <float>%
Interpretation: <success|failure>
Diagnosis: <none|concise diagnosis of every returned failure reason>

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
