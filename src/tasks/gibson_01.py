"""Gibson-01 sample specification."""

from __future__ import annotations

from pathlib import Path

from .base import TaskPaths

GIBSON_01_ROOT = Path(__file__).resolve().parents[2] / "task_data" / "gibson_01"
GIBSON_01_PATHS = TaskPaths(task_id="gibson_01", root=GIBSON_01_ROOT)
GIBSON_01_GROUND_TRUTH = GIBSON_01_PATHS.ground_truth
GIBSON_01_RUBRIC = GIBSON_01_PATHS.rubric


def build_gibson_01_prompt() -> str:
    return """You are operating inside LabCraft, a stochastic microbiology simulator.

Task: Assemble a two-fragment construct using Gibson isothermal overlap assembly, transform it into E. coli, plate on ampicillin, and report the outcome.

Starting substrates (call list_gibson_substrates to inspect):
- gibson_backbone_linear: linearised destination vector with a homology overhang
- gibson_insert_pcr: PCR insert with a matching homology overhang

Workflow guidance:
1. Inspect the substrates and choose a compatible isothermal overlap-assembly mix.
2. Choose an incubation temperature and duration appropriate for the observed fragment count and overlap length.
3. Transform the assembled construct into competent E. coli via transform_gibson.
4. Prepare an appropriate ampicillin selection plate and plate a defensible volume.
5. Count transformants.

Final answer schema (use exactly these fields on separate lines):
Assembly method: <method name>
Master mix: <name>
Temperature: <float> C
Duration: <int> min
Fragment count: <int>
Overlap length: <int> bp
Transformants observed: <int>
Interpretation: <success|failure>

Constraints:
- Use only the available lab tools and reference tools.
- Do not attempt any task outside BSL-1/2 benign molecular microbiology.
"""


def build_gibson_01_sample() -> dict:
    return {
        "id": "gibson_01_seeded",
        "input": build_gibson_01_prompt(),
        "target": str(GIBSON_01_GROUND_TRUTH),
        "metadata": {
            "task_id": "gibson_01",
            "ground_truth_path": str(GIBSON_01_GROUND_TRUTH),
            "rubric_path": str(GIBSON_01_RUBRIC),
        },
    }
