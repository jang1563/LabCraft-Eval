"""Reference-database helpers and optional Inspect wrappers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

_DATA_DIR = Path(__file__).resolve().parents[2] / "data"


def _search_database(db_path: Path, query: str) -> List[Dict[str, object]]:
    """Search a JSON database, preferring exact names and aliases."""
    with open(db_path) as handle:
        db = json.load(handle)
    query_lower = query.strip().casefold()
    exact_matches: List[Dict[str, object]] = []
    name_matches: List[Dict[str, object]] = []
    content_matches: List[Dict[str, object]] = []

    for entry in db:
        names = [entry.get("name", ""), *entry.get("aliases", [])]
        normalized_names = [str(name).strip().casefold() for name in names]
        if query_lower in normalized_names:
            exact_matches.append(entry)
        elif any(query_lower in name for name in normalized_names):
            name_matches.append(entry)
        elif query_lower in json.dumps(entry).casefold():
            content_matches.append(entry)

    return [*exact_matches, *name_matches, *content_matches]


async def lookup_reagent_call(reagent_name: str) -> str:
    db_path = _DATA_DIR / "reagent_database.json"
    matches = _search_database(db_path, reagent_name)
    if not matches:
        return "No entry found for '{:s}'.".format(reagent_name)
    return "\n---\n".join(json.dumps(match, indent=2) for match in matches[:3])


async def lookup_enzyme_call(enzyme_name: str) -> str:
    db_path = _DATA_DIR / "enzyme_database.json"
    matches = _search_database(db_path, enzyme_name)
    if not matches:
        return "No entry found for '{:s}'.".format(enzyme_name)
    return "\n---\n".join(json.dumps(match, indent=2) for match in matches[:3])


async def check_safety_call(chemical_name: str) -> str:
    db_path = _DATA_DIR / "safety_database.json"
    matches = _search_database(db_path, chemical_name)
    if not matches:
        return "No safety entry found for '{:s}'.".format(chemical_name)
    return "\n---\n".join(json.dumps(match, indent=2) for match in matches[:3])


def lookup_reagent_tool():
    from inspect_ai.tool import tool

    @tool
    def lookup_reagent():
        """Look up reagent properties from the LabCraft reagent database."""

        async def execute(reagent_name: str) -> str:
            """Look up a reagent by name.

            Args:
                reagent_name: Reagent name or partial match string.
            """
            return await lookup_reagent_call(reagent_name)

        return execute

    return lookup_reagent()


def lookup_enzyme_tool():
    from inspect_ai.tool import tool

    @tool
    def lookup_enzyme():
        """Look up enzyme properties from the LabCraft enzyme database."""

        async def execute(enzyme_name: str) -> str:
            """Look up an enzyme by name.

            Args:
                enzyme_name: Enzyme name or partial match string.
            """
            return await lookup_enzyme_call(enzyme_name)

        return execute

    return lookup_enzyme()


def check_safety_tool():
    from inspect_ai.tool import tool

    @tool
    def check_safety():
        """Look up safety handling guidance from the LabCraft safety database."""

        async def execute(chemical_name: str) -> str:
            """Look up safety guidance for a chemical.

            Args:
                chemical_name: Chemical name or partial match string.
            """
            return await check_safety_call(chemical_name)

        return execute

    return check_safety()
