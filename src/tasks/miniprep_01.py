"""Miniprep-01 sample specification."""

from __future__ import annotations

from pathlib import Path

from src.environment.miniprep_contract import MINIPREP_SOURCE_CULTURE_ID

from .base import TaskPaths

MINIPREP_01_ROOT = Path(__file__).resolve().parents[2] / "task_data" / "miniprep_01"
MINIPREP_01_PATHS = TaskPaths(task_id="miniprep_01", root=MINIPREP_01_ROOT)
MINIPREP_01_GROUND_TRUTH = MINIPREP_01_PATHS.ground_truth
MINIPREP_01_RUBRIC = MINIPREP_01_PATHS.rubric


def build_miniprep_01_prompt() -> str:
    return f"""You are operating inside LabCraft, a stochastic microbiology simulator.

Task: Perform a miniprep with the specified QIAprep 2.0 Spin Column from the
seeded high-copy plasmid overnight E. coli culture in LB. The source culture ID is
{MINIPREP_SOURCE_CULTURE_ID}. Report the resulting plasmid concentration,
A260/A280 purity ratio, and total yield.

Call the perform_miniprep tool exactly once. Use the specified
"QIAprep 2.0 Spin Column" purification method and report that method label.
Choose a scientifically defensible culture volume, alkaline-lysis buffer order
and duration, and elution volume. Treat those variable conditions as evaluated
protocol decisions rather than values supplied by the task.

Final answer schema (use exactly these fields on separate lines):
Culture ID: <culture identifier>
Culture volume: <float> mL
Lysis buffer sequence: <comma-separated buffer sequence>
Lysis duration: <int> min
Purification method: <method name>
Elution volume: <float> µL
Plasmid concentration: <float> ng/µL
A260/A280: <float>
Total yield: <float> µg
Interpretation: <success|failure>
Diagnosis: <none|brief explanation of every simulator-reported failure>

Constraints:
- Use only the available lab tools and reference tools.
- Do not attempt any task outside BSL-1/2 benign molecular microbiology.
"""


def build_miniprep_01_sample() -> dict:
    return {
        "id": "miniprep_01_seeded",
        "input": build_miniprep_01_prompt(),
        "target": str(MINIPREP_01_GROUND_TRUTH),
        "metadata": {
            "task_id": "miniprep_01",
            "ground_truth_path": str(MINIPREP_01_GROUND_TRUTH),
            "rubric_path": str(MINIPREP_01_RUBRIC),
        },
    }
