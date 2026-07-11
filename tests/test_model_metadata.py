import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_inspect_task_import_replaces_stale_gpt56_model_info_before_generation():
    code = r'''
import json
from inspect_ai.model import get_model_info

before = get_model_info("openai/gpt-5.6-sol")
import src.inspect_task  # noqa: F401 -- import-time plugin registration is under test
from src.model_metadata import register_inspect_model_info

after = get_model_info("openai/gpt-5.6-sol")
alias = get_model_info("openai/gpt-5.6")
registered_again = register_inspect_model_info()
payload = {
    "before_context": before.context_length,
    "after": {
        "organization": after.organization,
        "model": after.model,
        "knowledge_cutoff_date": after.knowledge_cutoff_date.isoformat(),
        "context_length": after.context_length,
        "output_tokens": after.output_tokens,
        "reasoning": after.reasoning,
        "reasoning_effort_default": after.reasoning_effort_default,
        "cost": after.cost,
    },
    "alias_context": alias.context_length,
    "registered_again": registered_again,
}
print(json.dumps(payload))
'''
    proc = subprocess.run(
        [sys.executable, "-c", code],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
    )

    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["before_context"] == 400_000
    assert payload["after"] == {
        "organization": "OpenAI",
        "model": "GPT-5.6 Sol",
        "knowledge_cutoff_date": "2026-02-16",
        "context_length": 1_050_000,
        "output_tokens": 128_000,
        "reasoning": True,
        "reasoning_effort_default": "medium",
        "cost": None,
    }
    assert payload["alias_context"] == 1_050_000
    assert payload["registered_again"] == [
        "openai/gpt-5.6-sol",
        "openai/gpt-5.6",
        "openai/gpt-5.6-luna",
        "openai/gpt-5.6-terra",
    ]
