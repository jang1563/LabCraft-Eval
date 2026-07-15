"""Development-only P2b causal PCR reasoning task."""

from __future__ import annotations

from pathlib import Path

from src.p2b_contracts import p2b_contract_metadata
from src.task_scorers.pcr_causal_reasoning_01 import SCORER_VERSION

from .base import TaskPaths


PCR_CAUSAL_REASONING_01_ROOT = (
    Path(__file__).resolve().parents[2] / "task_data" / "pcr_causal_reasoning_01"
)
PCR_CAUSAL_REASONING_01_PATHS = TaskPaths(
    task_id="pcr_causal_reasoning_01",
    root=PCR_CAUSAL_REASONING_01_ROOT,
)
PCR_CAUSAL_REASONING_01_GROUND_TRUTH = PCR_CAUSAL_REASONING_01_PATHS.ground_truth
PCR_CAUSAL_REASONING_01_RUBRIC = PCR_CAUSAL_REASONING_01_PATHS.rubric
PCR_CAUSAL_REASONING_01_CONTRACT = (
    PCR_CAUSAL_REASONING_01_ROOT / "development_contract.json"
)

_CASE_RECORDS = {
    "case_a": {
        "polymerase_name": "Taq DNA polymerase",
        "additive": "DMSO",
        "extension_seconds": 50,
        "cycle_count": 32,
    },
    "case_b": {
        "polymerase_name": "Q5 High-Fidelity DNA polymerase",
        "additive": "DMSO",
        "extension_seconds": 50,
        "cycle_count": 45,
    },
}


def build_pcr_causal_reasoning_01_prompt(case_id: str) -> str:
    """Build one opaque prior-record case without causal simulator notes."""
    try:
        record = _CASE_RECORDS[case_id]
    except KeyError as exc:
        raise ValueError("Unknown PCR causal-reasoning case: {}".format(case_id)) from exc

    return """You are operating inside LabCraft, a molecular-biology simulator.

Task: diagnose and recover one prior failure for a benign, GC-rich E. coli genomic PCR.

Target:
- Expected amplicon: approximately 2 kb
- Template GC content: approximately 70%

Read-only prior record:
- Case: {case_id}
- Polymerase: {polymerase_name}
- Additive: {additive}
- Extension: {extension_seconds} seconds
- Cycles: {cycle_count}
- Gel status: multiple_bands_or_smear
- Smear present: true

The prior record intentionally withholds simulator diagnosis notes and detailed band
positions. Both benchmark cases share the same coarse gel phenotype.

Requirements:
1. Diagnose the single primary failure as either low_fidelity_polymerase or
   overcycled_pcr, and name its causal parameter as polymerase_name or cycle_count.
2. Run exactly one corrective PCR. Change exactly the diagnosed causal parameter;
   preserve the other three prior settings.
3. Run exactly one gel using the exact reaction_id returned by that corrective PCR.
4. Specify one non-executed counterfactual. Starting from the prior record, change
   exactly one different, non-causal parameter to another scientifically valid setting,
   retain the diagnosed causal fault, and predict the resulting gel status.
5. Do not execute the counterfactual and do not rerun the prior failed condition.
6. Use reference tools only if needed. Report only values supported by the supplied
   record and linked tool outputs.

Final answer schema (exactly eight lines, no bullets, Markdown, or extra prose):
Case: <case_a|case_b>
Observed phenotype: multiple_bands_or_smear
Primary diagnosis: <low_fidelity_polymerase|overcycled_pcr>
Causal parameter: <polymerase_name|cycle_count>
Corrective setting: <parameter_name>=<value>
Counterfactual setting: <different_parameter_name>=<value>
Counterfactual prediction: <gel_status>
Verification: <gel_status>
""".format(case_id=case_id, **record)


def build_pcr_causal_reasoning_01_samples() -> list[dict]:
    """Return the two opaque cases in a stable order."""
    contract_metadata = p2b_contract_metadata()
    samples = []
    for case_id in ("case_a", "case_b"):
        samples.append(
            {
                "id": "pcr_causal_reasoning_01_{}_seeded".format(case_id),
                "input": build_pcr_causal_reasoning_01_prompt(case_id),
                "target": str(PCR_CAUSAL_REASONING_01_GROUND_TRUTH),
                "metadata": {
                    "task_id": "pcr_causal_reasoning_01",
                    "case_id": case_id,
                    "ground_truth_path": str(PCR_CAUSAL_REASONING_01_GROUND_TRUTH),
                    "rubric_path": str(PCR_CAUSAL_REASONING_01_RUBRIC),
                    "scorer_version": SCORER_VERSION,
                    "scorer_contract_path": str(PCR_CAUSAL_REASONING_01_CONTRACT),
                    "scorer_contract_sha256": contract_metadata[
                        "p2b_contract_sha256"
                    ],
                    "validation_tier": "development_unreviewed",
                    "expert_review_status": "skipped",
                    "promotion_eligible": False,
                    "evaluation_policy_ready": False,
                    "external_evaluation_authorized": False,
                    **contract_metadata,
                },
            }
        )
    return samples
