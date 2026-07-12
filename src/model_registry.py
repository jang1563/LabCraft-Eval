"""Validated access to LabCraft-Eval's packaged model registry."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
import tomllib
from typing import Any


# In a source checkout this resolves to <repo>/config/model_matrix.toml. Wheels
# install the config package beside src, so the same relative path remains
# valid without depending on the repository or current working directory.
DEFAULT_REGISTRY_PATH = Path(__file__).resolve().parents[1] / "config" / "model_matrix.toml"
MODEL_FIELDS = {
    "key",
    "inspect_id",
    "provider",
    "expected_resolved_model",
    "display_name",
    "short_name",
    "tier",
    "color",
}
ALLOWED_GENERATE_FIELDS = {
    "max_tokens",
    "reasoning_effort",
    "temperature",
}
ALLOWED_INSPECT_MODEL_INFO_FIELDS = {
    "organization",
    "model",
    "knowledge_cutoff_date",
    "context_length",
    "output_tokens",
    "reasoning",
    "reasoning_effort_default",
}


class RegistryError(ValueError):
    """Raised when the registry or a requested model reference is invalid."""


@dataclass(frozen=True)
class ModelSpec:
    key: str
    inspect_id: str
    provider: str
    expected_resolved_model: str
    display_name: str
    short_name: str
    tier: str
    color: str
    aliases: tuple[str, ...]
    generate: dict[str, Any]
    inspect_model_info: dict[str, Any]

    def field(self, name: str) -> str:
        if name not in MODEL_FIELDS:
            raise RegistryError(
                "Unknown model field {!r}; expected one of: {}".format(
                    name, ", ".join(sorted(MODEL_FIELDS))
                )
            )
        return str(getattr(self, name))


class ModelRegistry:
    def __init__(self, path: Path, raw: dict[str, Any]):
        self.path = path
        self.schema_version = raw.get("schema_version")
        self.default_matrix = raw.get("default_matrix")
        raw_models = raw.get("models")
        raw_matrices = raw.get("matrices")
        if self.schema_version != "1.0.0":
            raise RegistryError("Unsupported schema_version: {!r}".format(self.schema_version))
        if not isinstance(raw_models, dict) or not raw_models:
            raise RegistryError("Registry must define a non-empty [models] table.")
        if not isinstance(raw_matrices, dict) or not raw_matrices:
            raise RegistryError("Registry must define a non-empty [matrices] table.")

        self.models: dict[str, ModelSpec] = {}
        self._lookup: dict[str, ModelSpec] = {}
        for key, value in raw_models.items():
            self._add_model(key, value)

        self.matrices: dict[str, tuple[str, ...]] = {}
        for matrix_name, matrix_value in raw_matrices.items():
            if not isinstance(matrix_value, dict):
                raise RegistryError("Matrix {!r} must be a table.".format(matrix_name))
            keys = matrix_value.get("models")
            if not isinstance(keys, list) or not keys:
                raise RegistryError("Matrix {!r} must list at least one model.".format(matrix_name))
            if len(keys) != len(set(keys)):
                raise RegistryError("Matrix {!r} contains duplicate model keys.".format(matrix_name))
            missing = [key for key in keys if key not in self.models]
            if missing:
                raise RegistryError(
                    "Matrix {!r} references unknown models: {}".format(
                        matrix_name, ", ".join(missing)
                    )
                )
            self.matrices[matrix_name] = tuple(keys)

        if self.default_matrix not in self.matrices:
            raise RegistryError(
                "default_matrix {!r} is not defined.".format(self.default_matrix)
            )

    def _add_model(self, key: str, value: Any) -> None:
        if not isinstance(value, dict):
            raise RegistryError("Model {!r} must be a table.".format(key))
        required = (
            "inspect_id",
            "provider",
            "expected_resolved_model",
            "display_name",
            "short_name",
            "tier",
            "color",
            "generate",
        )
        missing = [name for name in required if name not in value]
        if missing:
            raise RegistryError(
                "Model {!r} is missing required fields: {}".format(key, ", ".join(missing))
            )
        aliases = value.get("aliases", [])
        generate = value["generate"]
        inspect_model_info = value.get("inspect_model_info", {})
        if not isinstance(aliases, list) or not all(isinstance(alias, str) for alias in aliases):
            raise RegistryError("Model {!r} aliases must be a list of strings.".format(key))
        if not isinstance(generate, dict) or not generate:
            raise RegistryError("Model {!r} must have a non-empty generate profile.".format(key))
        unknown_generate = sorted(set(generate) - ALLOWED_GENERATE_FIELDS)
        if unknown_generate:
            raise RegistryError(
                "Model {!r} has unsupported generate fields: {}".format(
                    key, ", ".join(unknown_generate)
                )
            )
        if not isinstance(generate.get("max_tokens"), int) or generate["max_tokens"] < 1:
            raise RegistryError("Model {!r} max_tokens must be a positive integer.".format(key))
        if "temperature" in generate and "reasoning_effort" in generate:
            raise RegistryError(
                "Model {!r} cannot set both temperature and reasoning_effort.".format(key)
            )
        if "reasoning_effort" in generate and not isinstance(
            generate["reasoning_effort"], str
        ):
            raise RegistryError("Model {!r} reasoning_effort must be a string.".format(key))
        if "temperature" in generate and not isinstance(generate["temperature"], (int, float)):
            raise RegistryError("Model {!r} temperature must be numeric.".format(key))
        inspect_model_info = self._validate_inspect_model_info(key, inspect_model_info)

        for field_name in required[:-1]:
            field_value = value[field_name]
            if not isinstance(field_value, str) or not field_value:
                raise RegistryError(
                    "Model {!r} field {!r} must be a non-empty string.".format(key, field_name)
                )
        identifiers = [key, value["inspect_id"], *aliases]
        if any(any(character.isspace() for character in identifier) for identifier in identifiers):
            raise RegistryError("Model keys, IDs, and aliases cannot contain whitespace.")
        if inspect_model_info and any("/" not in identifier for identifier in identifiers[1:]):
            raise RegistryError(
                "Model {!r} Inspect metadata can only register qualified provider/model IDs."
                .format(key)
            )

        spec = ModelSpec(
            key=key,
            inspect_id=value["inspect_id"],
            provider=value["provider"],
            expected_resolved_model=value["expected_resolved_model"],
            display_name=value["display_name"],
            short_name=value["short_name"],
            tier=value["tier"],
            color=value["color"],
            aliases=tuple(aliases),
            generate=dict(generate),
            inspect_model_info=inspect_model_info,
        )
        for identifier in identifiers:
            if identifier in self._lookup:
                raise RegistryError("Duplicate model identifier or alias: {!r}".format(identifier))
            self._lookup[identifier] = spec
        self.models[key] = spec

    @staticmethod
    def _validate_inspect_model_info(key: str, value: Any) -> dict[str, Any]:
        if value is None:
            return {}
        if not isinstance(value, dict):
            raise RegistryError("Model {!r} inspect_model_info must be a table.".format(key))
        unknown = sorted(set(value) - ALLOWED_INSPECT_MODEL_INFO_FIELDS)
        if unknown:
            raise RegistryError(
                "Model {!r} has unsupported inspect_model_info fields: {}".format(
                    key, ", ".join(unknown)
                )
            )
        if not value:
            return {}

        normalized = dict(value)
        for field_name in ("organization", "model", "reasoning_effort_default"):
            field_value = normalized.get(field_name)
            if field_value is not None and (
                not isinstance(field_value, str) or not field_value.strip()
            ):
                raise RegistryError(
                    "Model {!r} inspect_model_info.{} must be a non-empty string.".format(
                        key, field_name
                    )
                )
        cutoff = normalized.get("knowledge_cutoff_date")
        if cutoff is not None:
            if isinstance(cutoff, date):
                normalized["knowledge_cutoff_date"] = cutoff.isoformat()
            elif isinstance(cutoff, str):
                try:
                    date.fromisoformat(cutoff)
                except ValueError as exc:
                    raise RegistryError(
                        "Model {!r} knowledge_cutoff_date must be an ISO date.".format(key)
                    ) from exc
            else:
                raise RegistryError(
                    "Model {!r} knowledge_cutoff_date must be an ISO date.".format(key)
                )
        for field_name in ("context_length", "output_tokens"):
            field_value = normalized.get(field_name)
            if field_value is not None and (
                isinstance(field_value, bool)
                or not isinstance(field_value, int)
                or field_value < 1
            ):
                raise RegistryError(
                    "Model {!r} inspect_model_info.{} must be a positive integer.".format(
                        key, field_name
                    )
                )
        context_length = normalized.get("context_length")
        output_tokens = normalized.get("output_tokens")
        if context_length is not None and output_tokens is not None and output_tokens > context_length:
            raise RegistryError(
                "Model {!r} output_tokens cannot exceed context_length.".format(key)
            )
        reasoning = normalized.get("reasoning")
        if reasoning is not None and not isinstance(reasoning, bool):
            raise RegistryError(
                "Model {!r} inspect_model_info.reasoning must be boolean.".format(key)
            )
        if normalized.get("reasoning_effort_default") and reasoning is not True:
            raise RegistryError(
                "Model {!r} reasoning_effort_default requires reasoning=true.".format(key)
            )
        return normalized

    def resolve(self, identifier: str) -> ModelSpec:
        try:
            return self._lookup[identifier]
        except KeyError as exc:
            raise RegistryError(
                "Unknown model {!r}; add it to {} or choose a registered model.".format(
                    identifier, self.path
                )
            ) from exc

    def matrix_keys(self, matrix_name: str | None = None) -> tuple[str, ...]:
        name = matrix_name or self.default_matrix
        try:
            return self.matrices[name]
        except KeyError as exc:
            raise RegistryError(
                "Unknown matrix {!r}; expected one of: {}".format(
                    name, ", ".join(self.matrices)
                )
            ) from exc

    def matrix_ids(self, matrix_name: str | None = None) -> list[str]:
        return [self.models[key].inspect_id for key in self.matrix_keys(matrix_name)]

    def preferred_ids(self) -> list[str]:
        preferred: list[str] = []
        for matrix_name in self.matrices:
            for model_id in self.matrix_ids(matrix_name):
                if model_id not in preferred:
                    preferred.append(model_id)
        return preferred

    def plot_metadata(self) -> tuple[dict[str, str], dict[str, str]]:
        labels: dict[str, str] = {}
        colors: dict[str, str] = {}
        for spec in self.models.values():
            for identifier in (spec.inspect_id, *spec.aliases):
                labels[identifier] = spec.short_name
                colors[identifier] = spec.color
        return labels, colors


def load_registry(path: Path | str = DEFAULT_REGISTRY_PATH) -> ModelRegistry:
    registry_path = Path(path)
    try:
        with registry_path.open("rb") as handle:
            raw = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise RegistryError("Could not read model registry {}: {}".format(registry_path, exc)) from exc
    return ModelRegistry(registry_path, raw)
