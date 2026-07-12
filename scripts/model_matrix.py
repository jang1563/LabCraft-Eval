#!/usr/bin/env python3
"""Inspect and materialize LabCraft-Eval's packaged model registry."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
from typing import Any


# Direct `python scripts/model_matrix.py` execution puts scripts/, not the
# repository root, on sys.path. Keep that documented no-install workflow while
# all parsing and validation remains in the wheel-installed src package.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.model_registry import (  # noqa: E402
    DEFAULT_REGISTRY_PATH,
    MODEL_FIELDS,
    ModelRegistry,
    ModelSpec,
    RegistryError,
    load_registry,
)

__all__ = [
    "DEFAULT_REGISTRY_PATH",
    "MODEL_FIELDS",
    "ModelRegistry",
    "ModelSpec",
    "RegistryError",
    "load_registry",
    "main",
]


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".{}-".format(path.name), suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(temporary_name, path)
    except BaseException:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--registry",
        default=str(DEFAULT_REGISTRY_PATH),
        help="Path to model_matrix.toml.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("validate", help="Validate the registry.")
    subparsers.add_parser("list-matrices", help="Print registered matrix names.")

    matrix_parser = subparsers.add_parser("matrix", help="Print model IDs for a matrix.")
    matrix_parser.add_argument("name", nargs="?", help="Defaults to default_matrix.")
    matrix_parser.add_argument(
        "--format", choices=("lines", "space", "json"), default="lines"
    )

    field_parser = subparsers.add_parser("field", help="Print one field for a model.")
    field_parser.add_argument("model", help="Stable key, Inspect ID, or registered alias.")
    field_parser.add_argument("field", choices=sorted(MODEL_FIELDS))

    config_parser = subparsers.add_parser(
        "generate-config", help="Print or atomically write an Inspect GenerateConfig JSON file."
    )
    config_parser.add_argument("model", help="Stable key, Inspect ID, or registered alias.")
    config_parser.add_argument("--out", help="Write JSON to this path instead of stdout.")

    info_parser = subparsers.add_parser(
        "model-info", help="Print optional Inspect ModelInfo metadata as JSON."
    )
    info_parser.add_argument("model", help="Stable key, Inspect ID, or registered alias.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        registry = load_registry(args.registry)
        if args.command == "validate":
            print(
                "Valid model registry: {} models, {} matrices, default={}".format(
                    len(registry.models), len(registry.matrices), registry.default_matrix
                )
            )
        elif args.command == "list-matrices":
            print("\n".join(registry.matrices))
        elif args.command == "matrix":
            model_ids = registry.matrix_ids(args.name)
            if args.format == "json":
                print(json.dumps(model_ids))
            elif args.format == "space":
                print(" ".join(model_ids))
            else:
                print("\n".join(model_ids))
        elif args.command == "field":
            print(registry.resolve(args.model).field(args.field))
        elif args.command == "generate-config":
            payload = registry.resolve(args.model).generate
            if args.out:
                _write_json_atomic(Path(args.out), payload)
            else:
                print(json.dumps(payload, indent=2, sort_keys=True))
        elif args.command == "model-info":
            print(
                json.dumps(
                    registry.resolve(args.model).inspect_model_info,
                    indent=2,
                    sort_keys=True,
                )
            )
        else:  # pragma: no cover - argparse requires a known command
            raise AssertionError("Unhandled command: {}".format(args.command))
    except RegistryError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
