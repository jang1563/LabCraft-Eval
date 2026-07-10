"""Always-on safety/scope compliance scanner.

Scans every task-surface file (src/, data/, task_data/, docs/) for
case-insensitive matches of the exclusion keywords defined in
tests/scope_exclusion_keywords.txt. Any non-guardrail match fails the suite.

Files that legitimately discuss excluded content (this test, the keyword list itself,
SAFETY.md, README.md, and the analysis/positioning writeups) are allowlisted below
and excluded from the scan.

Rationale: we surfaced two latent infrastructure bugs during the Phase 3 portfolio
eval by adversarial seed exploration. This test closes the analogous loop for scope:
it ensures that new task content added in future phases cannot silently drift
out-of-scope, because the test trips immediately on any keyword appearance.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
KEYWORDS_FILE = ROOT / "tests" / "scope_exclusion_keywords.txt"
PACKAGED_KEYWORDS_FILE = ROOT / "src" / "resources" / "scope_exclusion_keywords.txt"

# Directories / files that are scanned for exclusion keywords.
SCAN_ROOTS = (
    ROOT / "src",
    ROOT / "data",
    ROOT / "task_data",
    ROOT / "docs",
)
SCAN_INDIVIDUAL_FILES: tuple[Path, ...] = ()

# File extensions we actually scan (skip binaries, .eval zips, images).
SCANNABLE_SUFFIXES = {".py", ".md", ".json", ".bib", ".txt", ".yaml", ".yml", ".toml"}

# Files that legitimately discuss excluded content and are allowlisted.
ALLOWLIST = {
    ROOT / "SAFETY.md",
    ROOT / "tests" / "test_scope_compliance.py",
    ROOT / "tests" / "scope_exclusion_keywords.txt",
    # Packaged policy data intentionally contains every excluded term.
    PACKAGED_KEYWORDS_FILE,
    ROOT / "results" / "positioning.md",
    ROOT / "results" / "analysis.md",
    ROOT / "README.md",
}

# A task prompt may include a short negative guardrail such as "do not attempt
# expression of toxins". Keep those lines visible to reviewers without forcing
# task authors to remove the guardrail wording itself.
NEGATIVE_GUARDRAIL_PATTERN = re.compile(
    r"(?i)\b(do not|don't|never|must not|out-of-scope|out of scope|excluded)\b"
)


def _load_keywords(path: Path = KEYWORDS_FILE) -> list[str]:
    keywords: list[str] = []
    for line in path.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        keywords.append(stripped)
    return keywords


def _compile_pattern(keywords: list[str]) -> re.Pattern:
    # Whole-word, case-insensitive. Keywords with hyphens / spaces are matched literally.
    escaped = [re.escape(k) for k in keywords]
    return re.compile(r"(?i)\b(" + "|".join(escaped) + r")\b")


def _iter_scan_files():
    seen: set[Path] = set()
    for root in SCAN_ROOTS:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.is_file() and path.suffix in SCANNABLE_SUFFIXES and path not in ALLOWLIST:
                if path not in seen:
                    seen.add(path)
                    yield path
    for path in SCAN_INDIVIDUAL_FILES:
        if path.exists() and path not in ALLOWLIST and path not in seen:
            seen.add(path)
            yield path


def test_keyword_list_is_nonempty():
    keywords = _load_keywords()
    assert keywords, "scope_exclusion_keywords.txt must contain at least one keyword"


def test_packaged_keyword_terms_match_test_policy_terms():
    assert set(_load_keywords(PACKAGED_KEYWORDS_FILE)) == set(_load_keywords(KEYWORDS_FILE))


def test_scan_roots_exist():
    for root in SCAN_ROOTS:
        assert root.exists(), "scan root missing: {}".format(root)


def test_no_exclusion_keywords_in_task_surface():
    keywords = _load_keywords()
    pattern = _compile_pattern(keywords)

    violations: list[tuple[Path, int, str, str]] = []
    for path in _iter_scan_files():
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for line_no, line in enumerate(text.splitlines(), start=1):
            match = pattern.search(line)
            if match:
                if NEGATIVE_GUARDRAIL_PATTERN.search(line):
                    continue
                violations.append((path, line_no, match.group(1), line.strip()[:160]))

    if violations:
        formatted = "\n".join(
            "  {}:{} — '{}' in: {}".format(p.relative_to(ROOT), ln, kw, excerpt)
            for p, ln, kw, excerpt in violations
        )
        pytest.fail(
            "Found {} exclusion-keyword match(es) in task-surface files. "
            "Either remove the offending content or, if it is legitimately discussing "
            "scope (not using excluded content), add the file to the ALLOWLIST in "
            "tests/test_scope_compliance.py with a rationale.\n{}".format(
                len(violations), formatted
            )
        )


def test_allowlisted_files_exist_or_are_future_files():
    # SAFETY.md, the test file, and the keyword file must always exist.
    must_exist = {
        ROOT / "SAFETY.md",
        ROOT / "tests" / "test_scope_compliance.py",
        ROOT / "tests" / "scope_exclusion_keywords.txt",
        PACKAGED_KEYWORDS_FILE,
    }
    for path in must_exist:
        assert path.exists(), "required allowlist file missing: {}".format(path)
