"""Clone-01 sample specification."""

from __future__ import annotations

from pathlib import Path

from .base import TaskPaths

CLONE_01_ROOT = Path(__file__).resolve().parents[2] / "task_data" / "clone_01"
CLONE_01_PATHS = TaskPaths(task_id="clone_01", root=CLONE_01_ROOT)
CLONE_01_GROUND_TRUTH = CLONE_01_PATHS.ground_truth
CLONE_01_RUBRIC = CLONE_01_PATHS.rubric


def build_clone_01_prompt() -> str:
    return """You are operating inside LabCraft, a stochastic microbiology simulator.

Task: Clone a benign 950 bp PCR insert into the pUC19 vector by directional restriction cloning, transform the ligation into competent E. coli on ampicillin selection, and verify recombinants by colony PCR.

Starting substrates:
- Call list_cloning_substrates to inspect the vector and insert, including their
  compatible restriction sites, concentrations, and selection features.

Workflow guidance:
1. Inspect the substrates and use the reference tools to choose a compatible double-digest buffer, incubation, and inactivation step.
2. Choose compatible ligation conditions and a defensible vector:insert molar ratio, then ligate the digested products.
3. Prepare an appropriate ampicillin selection plate, then transform the ligation with transform_ligation.
4. Plate a defensible volume on the selection plate and count colonies.
5. Inspect the resulting blue-white screening plate and run colony PCR on enough white colonies to reach >= 95% cumulative confidence.

Final answer schema (use exactly these fields on separate lines):
Digest enzymes: <comma-separated enzyme names>
Digest buffer: <buffer name>
Ligase: <ligase name>
Vector:insert molar ratio: 1:<n>
Ligation temperature: <float> C
Transformants observed: <int>
White colonies screened: <int>
Confirmed recombinant colonies: <colony_ids or None>
Confidence achieved: <float>%
Interpretation: <sentence mentioning 'recombinant'>

Constraints:
- Use only the available lab tools and reference tools.
- Do not attempt any task outside BSL-1/2 benign molecular microbiology.
"""


def build_clone_01_sample() -> dict:
    return {
        "id": "clone_01_seeded",
        "input": build_clone_01_prompt(),
        "target": str(CLONE_01_GROUND_TRUTH),
        "metadata": {
            "task_id": "clone_01",
            "ground_truth_path": str(CLONE_01_GROUND_TRUTH),
            "rubric_path": str(CLONE_01_RUBRIC),
        },
    }
