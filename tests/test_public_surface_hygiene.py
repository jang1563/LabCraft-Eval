import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PUBLIC_TEXT_PATHS = [
    REPO_ROOT / "README.md",
    *sorted((REPO_ROOT / "docs").rglob("*.md")),
    *sorted((REPO_ROOT / "results").glob("*.md")),
    *sorted((REPO_ROOT / "task_data").rglob("*.md")),
    REPO_ROOT / "hpc" / "README.md",
    *sorted((REPO_ROOT / "hpc").glob("*.sh")),
]
FORBIDDEN_LITERALS = (
    "recruiter-readable demonstration",
    "Recommended framing for a portfolio reviewer",
    "If the user wanted to strengthen the portfolio",
    "Company Brief Template",
    "company-specific positioning",
)
PERSONAL_PATH = re.compile(
    r"/(?:Users|home)/(?:[^/\s`]+/){1,2}(?:Dropbox|codex_runs|labcraft-py313)"
)
SCHEDULER_ID = re.compile(r"\b(?:job|array)\s+`?\d{7,}(?:_\d+)?`?", re.IGNORECASE)


def test_public_surface_omits_internal_breadcrumbs():
    violations = []
    for path in PUBLIC_TEXT_PATHS:
        text = path.read_text(encoding="utf-8")
        relative_path = path.relative_to(REPO_ROOT)
        for literal in FORBIDDEN_LITERALS:
            if literal in text:
                violations.append(f"{relative_path}: forbidden literal {literal!r}")
        for match in PERSONAL_PATH.finditer(text):
            violations.append(f"{relative_path}: personal path {match.group(0)!r}")
        for match in SCHEDULER_ID.finditer(text):
            violations.append(
                f"{relative_path}: exact scheduler identifier {match.group(0)!r}"
            )

    assert not violations, "\n".join(violations)
