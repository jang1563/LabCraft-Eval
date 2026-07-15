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

Task: Use the seeded benign expression construct
`expression_construct_his6_mbp_gfp_001`, a pET-style T7lac plasmid encoding a
His6-MBP-GFP fusion (~72 kDa). Perform one IPTG-induced expression and prepare a
native lysate for downstream Ni-NTA affinity purification. The simulator uses a
fixed 500 mL culture. Report the observed soluble yield in mg/L.

Call the run_protein_expression tool exactly once with your chosen conditions.
Pass the construct ID exactly as supplied. First retrieve the exact seeded benchmark
workflow by calling lookup_reagent with the construct ID. Select the host, inducer
concentration, induction cell density, coupled temperature-duration schedule, and
lysis-buffer pH from that retrieved task configuration. Do not substitute a valid
alternative from another physical expression protocol: this task evaluates the
declared simulator contract, whose yield and solubility values are synthetic
calibrations rather than universal biological claims. Copy the returned expression
ID and observations; do not invent them.

Final answer schema (use exactly these fields on separate lines):
Construct ID: <id>
Expression ID: <id>
Host strain: <strain>
IPTG concentration: <float> mM
Induction OD600: <float>
Induction temperature: <float> C
Induction duration: <float> h
Lysis buffer pH: <float>
Observed soluble yield: <float> mg/L
Interpretation: <success|failure>
Diagnosis: <none|concise diagnosis of every returned failure reason>

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
