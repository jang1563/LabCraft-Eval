"""Express-01 sample specification."""

from __future__ import annotations

from pathlib import Path

from .base import TaskPaths

EXPRESS_01_ROOT = Path(__file__).resolve().parents[2] / "task_data" / "express_01"
EXPRESS_01_PATHS = TaskPaths(task_id="express_01", root=EXPRESS_01_ROOT)
EXPRESS_01_GROUND_TRUTH = EXPRESS_01_PATHS.ground_truth
EXPRESS_01_RUBRIC = EXPRESS_01_PATHS.rubric


def build_express_01_prompt() -> str:
    return """You are operating inside LabCraft, a stochastic microbiology simulator.

Task: Perform a single IPTG-induced recombinant protein expression of a benign His-tagged MBP-GFP fusion (~72 kDa), then prepare a lysate for downstream affinity purification. Report soluble yield in mg/L.

Call the run_protein_expression tool exactly once with your chosen conditions.
Select the host, inducer concentration, induction cell density, temperature and
duration, and lysis-buffer pH from your scientific knowledge of recombinant
expression and downstream affinity-purification workflows.

Final answer schema (use exactly these fields on separate lines):
Host strain: <strain>
IPTG concentration: <float> mM
Induction OD600: <float>
Induction temperature: <int> C
Induction duration: <float> h
Lysis buffer pH: <float>
Expected soluble yield: <float> mg/L
Interpretation: <success|failure>

Constraints:
- Use only the available lab tools and reference tools.
- The target protein is a benign MBP-GFP fusion; do not attempt expression of toxins, cytokines, or any protein outside the benign reporter / model-enzyme scope.
"""


def build_express_01_sample() -> dict:
    return {
        "id": "express_01_seeded",
        "input": build_express_01_prompt(),
        "target": str(EXPRESS_01_GROUND_TRUTH),
        "metadata": {
            "task_id": "express_01",
            "ground_truth_path": str(EXPRESS_01_GROUND_TRUTH),
            "rubric_path": str(EXPRESS_01_RUBRIC),
        },
    }
