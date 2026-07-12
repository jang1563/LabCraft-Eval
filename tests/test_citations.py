"""Citation-policy enforcement tests for LabCraft."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PARAMETER_FILES = sorted((ROOT / "data" / "parameters").glob("*.json"))
GROUND_TRUTH_FILES = sorted((ROOT / "task_data").glob("*/ground_truth.json"))
ALLOWED_TIERS = {"Gold", "Silver", "Bronze", "Copper"}
TIER_RANK = {"Copper": 1, "Bronze": 2, "Silver": 3, "Gold": 4}


def _load_json(path: Path):
    with open(path) as handle:
        return json.load(handle)


def _assert_citation_shape(citation):
    assert citation["tier"] in ALLOWED_TIERS
    assert citation["tier_justification"].strip()
    assert citation.get("doi") or citation.get("canonical_url")
    if citation["tier"] == "Gold":
        assert citation.get("citation_count_approx", 0) >= 100


def _tier_satisfies(citation, minimum_tier_required):
    return TIER_RANK[citation["tier"]] >= TIER_RANK[minimum_tier_required]


def _iter_ground_truth_citation_blocks(payload):
    yield from payload.get("decision_points", [])
    yield from payload.get("failure_diagnosis_map", {}).values()


def _source_reference_tokens(citation):
    tokens = []
    doi = citation.get("doi")
    if doi:
        normalized = doi.lower().strip()
        normalized = normalized.removeprefix("https://doi.org/")
        normalized = normalized.removeprefix("http://doi.org/")
        tokens.extend([normalized, "doi.org/{}".format(normalized)])
    canonical_url = citation.get("canonical_url")
    if canonical_url:
        normalized = canonical_url.lower().strip().rstrip("/")
        tokens.append(normalized)
        tokens.append(normalized.removeprefix("https://").removeprefix("http://"))
    return [token for token in tokens if token]


def _iter_nested_citations(value):
    if isinstance(value, dict):
        citations = value.get("citations")
        if isinstance(citations, list):
            yield from citations
        for child in value.values():
            yield from _iter_nested_citations(child)
    elif isinstance(value, list):
        for child in value:
            yield from _iter_nested_citations(child)


def _normalized_doi(value):
    return (
        str(value)
        .strip()
        .lower()
        .removeprefix("https://doi.org/")
        .removeprefix("http://doi.org/")
    )


def _bib_entry_doi(bib_text, entry_key):
    match = re.search(
        r"@[^{]+\{" + re.escape(entry_key) + r",(?P<body>.*?)\n\}",
        bib_text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    assert match, "Missing BibTeX entry {}".format(entry_key)
    doi_match = re.search(r"\bdoi\s*=\s*\{([^}]+)\}", match.group("body"), re.IGNORECASE)
    assert doi_match, "BibTeX entry {} is missing a DOI".format(entry_key)
    return _normalized_doi(doi_match.group(1))


def test_parameter_files_exist():
    assert PARAMETER_FILES


def test_parameter_records_have_valid_citations():
    for path in PARAMETER_FILES:
        payload = _load_json(path)
        for parameter in payload.get("parameters", []):
            citations = parameter.get("citations", [])
            assert citations, "{} missing citations".format(parameter["parameter_name"])
            for citation in citations:
                _assert_citation_shape(citation)
            minimum = parameter["minimum_tier_required"]
            assert any(_tier_satisfies(citation, minimum) for citation in citations)
            assert parameter.get("tier_satisfied") is True


def test_ground_truth_decision_points_have_citations():
    assert GROUND_TRUTH_FILES
    for path in GROUND_TRUTH_FILES:
        payload = _load_json(path)
        for decision_point in payload.get("decision_points", []):
            citations = decision_point.get("citations", [])
            assert citations, "{} missing citations".format(decision_point["id"])
            for citation in citations:
                _assert_citation_shape(citation)
            minimum = decision_point["minimum_tier_required"]
            assert any(_tier_satisfies(citation, minimum) for citation in citations)


def test_failure_maps_have_citations():
    for path in GROUND_TRUTH_FILES:
        payload = _load_json(path)
        for failure_id, failure_item in payload.get("failure_diagnosis_map", {}).items():
            citations = failure_item.get("citations", [])
            assert citations, "{} missing citations".format(failure_id)
            for citation in citations:
                _assert_citation_shape(citation)


def test_sources_file_documents_rejected_sources():
    for task_dir in sorted((ROOT / "task_data").glob("*")):
        sources_path = task_dir / "SOURCES.md"
        assert sources_path.exists()
        content = sources_path.read_text()
        assert "Rejected Sources" in content


def test_ground_truth_citations_are_documented_in_sources_files():
    for path in GROUND_TRUTH_FILES:
        sources_path = path.parent / "SOURCES.md"
        sources_text = sources_path.read_text().lower()
        payload = _load_json(path)
        for block in _iter_ground_truth_citation_blocks(payload):
            for citation in block.get("citations", []):
                tokens = _source_reference_tokens(citation)
                assert tokens, "{} citation needs a DOI or canonical URL".format(
                    citation.get("title", "<untitled>")
                )
                assert any(token in sources_text for token in tokens), (
                    "{} citation is not documented in {}".format(
                        citation.get("title", "<untitled>"),
                        sources_path.relative_to(ROOT),
                    )
                )


def test_corrected_dois_match_parameter_json_sources_and_bibliography():
    """Keep corrected source identifiers identical across the public citation surfaces."""
    bib_text = (ROOT / "data" / "parameters" / "references.bib").read_text()
    cases = (
        {
            "title": "The Growth of Bacterial Cultures",
            "doi": "10.1146/annurev.mi.03.100149.002103",
            "bib_key": "monod1949",
            "json_paths": (ROOT / "data" / "parameters" / "growth.json",),
            "source_paths": (
                ROOT / "task_data" / "growth_01" / "SOURCES.md",
                ROOT / "task_data" / "followup_01" / "SOURCES.md",
            ),
        },
        {
            "title": "Colony PCR",
            "doi": "10.1016/B978-0-12-418687-3.00025-2",
            "bib_key": "bergkessel2013",
            "json_paths": (ROOT / "data" / "parameters" / "screening.json",),
            "source_paths": (ROOT / "task_data" / "screen_01" / "SOURCES.md",),
        },
    )

    for case in cases:
        expected = _normalized_doi(case["doi"])
        json_dois = set()
        for path in case["json_paths"]:
            payload = _load_json(path)
            json_dois.update(
                _normalized_doi(citation["doi"])
                for citation in _iter_nested_citations(payload)
                if citation.get("title") == case["title"] and citation.get("doi")
            )
        assert json_dois == {expected}

        for path in case["source_paths"]:
            assert expected in path.read_text().lower()

        assert _bib_entry_doi(bib_text, case["bib_key"]) == expected
