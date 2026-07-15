"""Golden Gate-01 sample specification."""

from __future__ import annotations

from pathlib import Path

from src.scorer_contracts import scorer_contract_metadata

from .base import TaskPaths

GOLDEN_GATE_01_ROOT = Path(__file__).resolve().parents[2] / "task_data" / "golden_gate_01"
GOLDEN_GATE_01_PATHS = TaskPaths(task_id="golden_gate_01", root=GOLDEN_GATE_01_ROOT)
GOLDEN_GATE_01_GROUND_TRUTH = GOLDEN_GATE_01_PATHS.ground_truth
GOLDEN_GATE_01_RUBRIC = GOLDEN_GATE_01_PATHS.rubric


def build_golden_gate_01_prompt() -> str:
    return """You are operating inside LabCraft, a stochastic microbiology simulator.

Task: Assemble a four-fragment construct using Golden Gate one-pot Type IIS cloning, transform it into E. coli, plate on ampicillin selection, and report the outcome.

Starting substrates (call list_golden_gate_substrates to inspect):
- gg_backbone: linear Golden Gate destination vector
- gg_insert_promoter: promoter insert
- gg_insert_cds: coding-sequence insert
- gg_insert_terminator: terminator insert

Workflow guidance:
1. Inspect the substrates and use reference evidence to choose a compatible Type IIS enzyme, ligase, one-pot buffer, and thermal cycling program.
2. Run enough digest/ligation cycles for the supplied four-fragment assembly and use the cited terminal digest step.
3. Transform the assembled construct into competent E. coli using transform_assembly.
4. Prepare an appropriate ampicillin selection plate and plate a defensible volume.
5. Count transformants.

Final answer schema (use exactly these fields on separate lines):
Type IIS enzyme: <enzyme name>
Ligase: <ligase name>
Digest temperature: <float> C
Ligate temperature: <float> C
Cycle count: <int>
Fragment count: <int>
Transformants observed: <int>
Interpretation: <success|failure>

Constraints:
- Use only the available lab tools and reference tools.
- Do not attempt any task outside BSL-1/2 benign molecular microbiology.
"""


def build_golden_gate_01_sample() -> dict:
    return {
        "id": "golden_gate_01_seeded",
        "input": build_golden_gate_01_prompt(),
        "target": str(GOLDEN_GATE_01_GROUND_TRUTH),
        "metadata": {
            **scorer_contract_metadata("golden_gate_01"),
            "task_id": "golden_gate_01",
            "ground_truth_path": str(GOLDEN_GATE_01_GROUND_TRUTH),
            "rubric_path": str(GOLDEN_GATE_01_RUBRIC),
        },
    }
