"""Register registry-backed structural metadata missing from Inspect's catalog."""
from __future__ import annotations


def register_inspect_model_info() -> tuple[str, ...]:
    """Register qualified model IDs with optional ``inspect_model_info`` data.

    Repeating this call is safe: Inspect replaces the same custom entries and
    clears its model-info cache. Cost is intentionally absent from the registry
    because a flat ``ModelCost`` cannot encode GPT-5.6 long-context surcharges.
    """
    try:
        from inspect_ai.model import ModelInfo, set_model_info
    except ImportError:  # pragma: no cover - task module remains importable without Inspect.
        return ()

    from src.model_registry import load_registry

    registry = load_registry()
    registered = []
    for spec in registry.models.values():
        if not spec.inspect_model_info:
            continue
        identifiers = (spec.inspect_id, *spec.aliases)
        for identifier in identifiers:
            set_model_info(identifier, ModelInfo(**spec.inspect_model_info))
            registered.append(identifier)
    return tuple(registered)
