"""Inspect AI task entry points for LabCraft-Eval/LabCraft.

Each public task is registered separately so Inspect can attach the task-specific
setup hook, solver, scorer, and cleanup hook. Multi-task suites are orchestrated
by ``scripts/run_portfolio_eval.sh`` presets rather than by a single Inspect Task.
"""

from __future__ import annotations

try:
    from inspect_ai import Task, task
    from inspect_ai.dataset import MemoryDataset, Sample
except ImportError:  # pragma: no cover - keeps local imports working before Inspect is installed.
    Task = None
    MemoryDataset = None
    Sample = None

    def task(func):
        return func

from src.model_metadata import register_inspect_model_info
from src.solvers import (
    build_clone_solver,
    build_discovery_solver,
    build_expression_solver,
    build_followup_solver,
    build_gibson_solver,
    build_golden_gate_solver,
    build_growth_solver,
    build_labcraft_solver,
    build_miniprep_solver,
    build_pcr_solver,
    build_purification_solver,
    build_screen_solver,
    configure_clone_sample,
    configure_discovery_sample,
    configure_expression_sample,
    configure_gibson_sample,
    configure_golden_gate_sample,
    configure_growth_sample,
    configure_miniprep_sample,
    configure_pcr_sample,
    configure_purification_sample,
    configure_screen_sample,
    configure_transform_sample,
)
from src.tasks.safety_case_01 import build_safety_case_01_samples
from src.tasks.clone_01 import build_clone_01_sample
from src.tasks.express_01 import build_express_01_sample
from src.tasks.followup_01 import build_followup_01_sample
from src.tasks.gibson_01 import build_gibson_01_sample
from src.tasks.golden_gate_01 import build_golden_gate_01_sample
from src.tasks.growth_01 import build_growth_01_sample
from src.tasks.miniprep_01 import build_miniprep_01_sample
from src.tasks.pcr_01 import build_pcr_01_sample
from src.tasks.perturb_followup_01 import build_perturb_followup_01_sample
from src.tasks.purify_01 import build_purify_01_sample
from src.tasks.screen_01 import build_screen_01_sample
from src.tasks.target_prioritize_01 import build_target_prioritize_01_sample
from src.tasks.target_validate_01 import build_target_validate_01_sample
from src.tasks.transform_01 import build_transform_01_sample
from src.tools.discovery import cleanup_discovery_sample
from src.tools.lab_tools import cleanup_sample
from src.trajectory_scorer import (
    build_clone_trajectory_scorer,
    build_express_trajectory_scorer,
    build_followup_trajectory_scorer,
    build_gibson_trajectory_scorer,
    build_golden_gate_trajectory_scorer,
    build_growth_trajectory_scorer,
    build_miniprep_trajectory_scorer,
    build_pcr_trajectory_scorer,
    build_perturb_followup_trajectory_scorer,
    build_purify_trajectory_scorer,
    build_screen_trajectory_scorer,
    build_target_prioritize_trajectory_scorer,
    build_target_validate_trajectory_scorer,
    build_transform_trajectory_scorer,
)

# Inspect 0.3.245 instantiates the provider before loading this task module, but
# consults ModelInfo dynamically at first generation/compaction. Register the
# structural GPT-5.6 metadata before any task can start generating.
register_inspect_model_info()

SNAPSHOT_TASKS = ("transform_01", "growth_01", "pcr_01", "screen_01", "clone_01")
CURRENT_TASKS = SNAPSHOT_TASKS + (
    "golden_gate_01",
    "gibson_01",
    "miniprep_01",
    "express_01",
    "purify_01",
    "followup_01",
)
DISCOVERY_TASKS = ("perturb_followup_01", "target_prioritize_01", "target_validate_01")
SAFETY_CASE_TASKS = ("safety_case_01",)
ALL_TASKS = CURRENT_TASKS + DISCOVERY_TASKS
TASK_PRESETS = {
    "snapshot": SNAPSHOT_TASKS,
    "current": CURRENT_TASKS,
    "discovery": DISCOVERY_TASKS,
    "safety_case": SAFETY_CASE_TASKS,
    "all": ALL_TASKS,
}

# Transform and growth trajectories batch tool calls across several conditions.
# Inspect counts each parallel tool result as a separate message, so a
# message-only cap can terminate a scientifically valid run between a batched
# call and its results. Bound actual agent iterations separately and retain a
# hard message ceiling for provider-neutral runaway protection.
TRANSFORM_TURN_LIMIT = 40
TRANSFORM_MESSAGE_LIMIT = 160
GROWTH_TURN_LIMIT = 40
GROWTH_MESSAGE_LIMIT = 160


def available_task_ids(preset: str = "all") -> tuple[str, ...]:
    """Return the task ids included in a named portfolio preset."""
    try:
        return TASK_PRESETS[preset]
    except KeyError as exc:
        raise ValueError("Unknown task preset: {}".format(preset)) from exc


async def _cleanup_transform_sample(state):
    cleanup_sample(state.sample_id)


async def _cleanup_discovery_state(state):
    cleanup_discovery_sample(state.sample_id)


def _expand_seeds(base_sample: dict, seeds: int, seed_start: int = 0):
    if isinstance(seeds, bool) or not isinstance(seeds, int) or seeds < 1:
        raise ValueError("seeds must be a positive integer")
    if isinstance(seed_start, bool) or not isinstance(seed_start, int) or seed_start < 0:
        raise ValueError("seed_start must be a non-negative integer")
    expanded = []
    for idx in range(seed_start, seed_start + seeds):
        suffix = "_seed_{:02d}".format(idx)
        cloned = dict(base_sample)
        cloned["id"] = base_sample["id"] + suffix
        cloned["metadata"] = dict(base_sample.get("metadata", {}))
        cloned["metadata"]["seed_index"] = idx
        expanded.append(cloned)
    return expanded


def _samples(base_sample: dict, seeds: int, seed_start: int = 0):
    return [
        Sample(
            input=s["input"],
            target=s["target"],
            id=s["id"],
            metadata=s["metadata"],
        )
        for s in _expand_seeds(base_sample, seeds, seed_start=seed_start)
    ]


@task
def transform_01(seeds: int = 1, seed_start: int = 0):
    if Task is None or MemoryDataset is None or Sample is None:
        raise ImportError("inspect_ai is required to instantiate LabCraft tasks.")
    return Task(
        dataset=MemoryDataset(
            samples=_samples(build_transform_01_sample(), seeds, seed_start=seed_start)
        ),
        setup=configure_transform_sample(),
        solver=build_labcraft_solver(),
        scorer=build_transform_trajectory_scorer(),
        cleanup=_cleanup_transform_sample,
        turn_limit=TRANSFORM_TURN_LIMIT,
        message_limit=TRANSFORM_MESSAGE_LIMIT,
    )


@task
def growth_01(seeds: int = 1, seed_start: int = 0):
    if Task is None or MemoryDataset is None or Sample is None:
        raise ImportError("inspect_ai is required to instantiate LabCraft tasks.")
    return Task(
        dataset=MemoryDataset(
            samples=_samples(build_growth_01_sample(), seeds, seed_start=seed_start)
        ),
        setup=configure_growth_sample(),
        solver=build_growth_solver(),
        scorer=build_growth_trajectory_scorer(),
        cleanup=_cleanup_transform_sample,
        turn_limit=GROWTH_TURN_LIMIT,
        message_limit=GROWTH_MESSAGE_LIMIT,
    )


@task
def followup_01(seeds: int = 1, seed_start: int = 0):
    if Task is None or MemoryDataset is None or Sample is None:
        raise ImportError("inspect_ai is required to instantiate LabCraft tasks.")
    return Task(
        dataset=MemoryDataset(
            samples=_samples(build_followup_01_sample(), seeds, seed_start=seed_start)
        ),
        setup=configure_growth_sample(),
        solver=build_followup_solver(),
        scorer=build_followup_trajectory_scorer(),
        cleanup=_cleanup_transform_sample,
        message_limit=60,
    )


@task
def perturb_followup_01(seeds: int = 1, seed_start: int = 0):
    if Task is None or MemoryDataset is None or Sample is None:
        raise ImportError("inspect_ai is required to instantiate LabCraft tasks.")
    return Task(
        dataset=MemoryDataset(
            samples=_samples(build_perturb_followup_01_sample(), seeds, seed_start=seed_start)
        ),
        setup=configure_discovery_sample(),
        solver=build_discovery_solver(),
        scorer=build_perturb_followup_trajectory_scorer(),
        cleanup=_cleanup_discovery_state,
        message_limit=50,
    )


@task
def target_prioritize_01(seeds: int = 1, seed_start: int = 0):
    if Task is None or MemoryDataset is None or Sample is None:
        raise ImportError("inspect_ai is required to instantiate LabCraft tasks.")
    return Task(
        dataset=MemoryDataset(
            samples=_samples(build_target_prioritize_01_sample(), seeds, seed_start=seed_start)
        ),
        setup=configure_discovery_sample(),
        solver=build_discovery_solver(),
        scorer=build_target_prioritize_trajectory_scorer(),
        cleanup=_cleanup_discovery_state,
        message_limit=50,
    )


@task
def target_validate_01(seeds: int = 1, seed_start: int = 0):
    if Task is None or MemoryDataset is None or Sample is None:
        raise ImportError("inspect_ai is required to instantiate LabCraft tasks.")
    return Task(
        dataset=MemoryDataset(
            samples=_samples(build_target_validate_01_sample(), seeds, seed_start=seed_start)
        ),
        setup=configure_discovery_sample(),
        solver=build_discovery_solver(),
        scorer=build_target_validate_trajectory_scorer(),
        cleanup=_cleanup_discovery_state,
        message_limit=50,
    )


@task
def pcr_01(seeds: int = 1, seed_start: int = 0):
    if Task is None or MemoryDataset is None or Sample is None:
        raise ImportError("inspect_ai is required to instantiate LabCraft tasks.")
    return Task(
        dataset=MemoryDataset(
            samples=_samples(build_pcr_01_sample(), seeds, seed_start=seed_start)
        ),
        setup=configure_pcr_sample(),
        solver=build_pcr_solver(),
        scorer=build_pcr_trajectory_scorer(),
        cleanup=_cleanup_transform_sample,
        message_limit=60,
    )


@task
def screen_01(seeds: int = 1, seed_start: int = 0):
    if Task is None or MemoryDataset is None or Sample is None:
        raise ImportError("inspect_ai is required to instantiate LabCraft tasks.")
    return Task(
        dataset=MemoryDataset(
            samples=_samples(build_screen_01_sample(), seeds, seed_start=seed_start)
        ),
        setup=configure_screen_sample(),
        solver=build_screen_solver(),
        scorer=build_screen_trajectory_scorer(),
        cleanup=_cleanup_transform_sample,
        message_limit=50,
    )


@task
def clone_01(seeds: int = 1, seed_start: int = 0):
    if Task is None or MemoryDataset is None or Sample is None:
        raise ImportError("inspect_ai is required to instantiate LabCraft tasks.")
    return Task(
        dataset=MemoryDataset(
            samples=_samples(build_clone_01_sample(), seeds, seed_start=seed_start)
        ),
        setup=configure_clone_sample(),
        solver=build_clone_solver(),
        scorer=build_clone_trajectory_scorer(),
        cleanup=_cleanup_transform_sample,
        message_limit=80,
    )


@task
def golden_gate_01(seeds: int = 1, seed_start: int = 0):
    if Task is None or MemoryDataset is None or Sample is None:
        raise ImportError("inspect_ai is required to instantiate LabCraft tasks.")
    return Task(
        dataset=MemoryDataset(
            samples=_samples(
                build_golden_gate_01_sample(),
                seeds,
                seed_start=seed_start,
            )
        ),
        setup=configure_golden_gate_sample(),
        solver=build_golden_gate_solver(),
        scorer=build_golden_gate_trajectory_scorer(),
        cleanup=_cleanup_transform_sample,
        message_limit=60,
    )


@task
def gibson_01(seeds: int = 1, seed_start: int = 0):
    if Task is None or MemoryDataset is None or Sample is None:
        raise ImportError("inspect_ai is required to instantiate LabCraft tasks.")
    return Task(
        dataset=MemoryDataset(
            samples=_samples(build_gibson_01_sample(), seeds, seed_start=seed_start)
        ),
        setup=configure_gibson_sample(),
        solver=build_gibson_solver(),
        scorer=build_gibson_trajectory_scorer(),
        cleanup=_cleanup_transform_sample,
        message_limit=60,
    )


@task
def miniprep_01(seeds: int = 1, seed_start: int = 0):
    if Task is None or MemoryDataset is None or Sample is None:
        raise ImportError("inspect_ai is required to instantiate LabCraft tasks.")
    return Task(
        dataset=MemoryDataset(
            samples=_samples(build_miniprep_01_sample(), seeds, seed_start=seed_start)
        ),
        setup=configure_miniprep_sample(),
        solver=build_miniprep_solver(),
        scorer=build_miniprep_trajectory_scorer(),
        cleanup=_cleanup_transform_sample,
        message_limit=40,
    )


@task
def express_01(seeds: int = 1, seed_start: int = 0):
    if Task is None or MemoryDataset is None or Sample is None:
        raise ImportError("inspect_ai is required to instantiate LabCraft tasks.")
    return Task(
        dataset=MemoryDataset(
            samples=_samples(build_express_01_sample(), seeds, seed_start=seed_start)
        ),
        setup=configure_expression_sample(),
        solver=build_expression_solver(),
        scorer=build_express_trajectory_scorer(),
        cleanup=_cleanup_transform_sample,
        message_limit=40,
    )


@task
def purify_01(seeds: int = 1, seed_start: int = 0):
    if Task is None or MemoryDataset is None or Sample is None:
        raise ImportError("inspect_ai is required to instantiate LabCraft tasks.")
    return Task(
        dataset=MemoryDataset(
            samples=_samples(build_purify_01_sample(), seeds, seed_start=seed_start)
        ),
        setup=configure_purification_sample(),
        solver=build_purification_solver(),
        scorer=build_purify_trajectory_scorer(),
        cleanup=_cleanup_transform_sample,
        message_limit=40,
    )


@task
def safety_case_01(seeds: int = 1, seed_start: int = 0):
    """Safety-case evaluation: 30 legitimate bio-research scenarios × seeds runs.

    No simulated environment — single-turn conversational QA scored on five axes:
    legitimate_helpfulness, boundary_precision, provenance_grounding,
    monitor_coverage, residual_risk_framing.
    """
    if Task is None or MemoryDataset is None or Sample is None:
        raise ImportError("inspect_ai is required to instantiate LabCraft tasks.")
    from inspect_ai.solver import chain, generate, system_message

    from src.safety_case_inspect_scorer import _SYSTEM_PROMPT, build_safety_case_scorer

    raw_samples = build_safety_case_01_samples()
    all_samples = []
    for base_sample in raw_samples:
        for seeded_sample in _expand_seeds(base_sample, seeds, seed_start=seed_start):
            all_samples.append(
                Sample(
                    input=seeded_sample["input"],
                    target=seeded_sample["target"],
                    id=seeded_sample["id"],
                    metadata=seeded_sample["metadata"],
                )
            )

    return Task(
        dataset=MemoryDataset(samples=all_samples),
        solver=chain([system_message(_SYSTEM_PROMPT), generate()]),
        scorer=build_safety_case_scorer(),
        message_limit=3,
    )


@task
def labcraft_suite(seeds: int = 1, seed_start: int = 0):
    """Backward-compatible single-task smoke entry point.

    Heterogeneous LabCraft-Eval suites need different setup, solver, scorer,
    and cleanup contracts per task. Use ``scripts/run_portfolio_eval.sh`` with
    ``TASK_PRESET=snapshot``, ``current``, ``discovery``, or ``all`` for real
    portfolio runs.
    """
    if Task is None:
        raise ImportError("inspect_ai is required to instantiate LabCraft tasks.")
    return transform_01(seeds=seeds, seed_start=seed_start)


__all__ = [
    "SNAPSHOT_TASKS",
    "CURRENT_TASKS",
    "DISCOVERY_TASKS",
    "SAFETY_CASE_TASKS",
    "ALL_TASKS",
    "TASK_PRESETS",
    "available_task_ids",
    "transform_01",
    "growth_01",
    "followup_01",
    "perturb_followup_01",
    "pcr_01",
    "screen_01",
    "clone_01",
    "golden_gate_01",
    "gibson_01",
    "miniprep_01",
    "express_01",
    "purify_01",
    "target_prioritize_01",
    "target_validate_01",
    "safety_case_01",
    "labcraft_suite",
]
