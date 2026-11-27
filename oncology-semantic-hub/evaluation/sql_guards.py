"""Identifier-shape validation for f-string-built SQL/Cypher query helpers.

`evaluation/generate_questions.py` builds SQL/Cypher by interpolating TCGA project IDs and HUGO
gene symbols directly into an f-string (flagged B608 by Bandit/Slingshot: "possible SQL injection
vector through string-based query construction").

Every current call site passes a hardcoded literal from this same codebase (TCGA project
codes, gene symbols) — never external/untrusted input — so there is no live injection path
today. These guards exist so that stays true: they validate the *shape* of an identifier
before it reaches an f-string, so a future caller can't accidentally (or maliciously) pass
something that breaks out of the intended slot. This is deliberately a allowlist-shape check,
not a parameterized query, because these are DDL-like identifiers (project ids, gene symbols)
rather than query *data* — Athena/openCypher don't support parameter binding for identifiers
the way they do for literal values.

(ground_truth/gen_v2_questions.py and ground_truth/verify_paper_questions.py have the same
f-string B608 pattern but are one-time, no-longer-run generators whose output was already
produced and frozen — their findings are suppressed with a rationale comment instead, not
wired to this guard; see the comments at each site.)
"""
from __future__ import annotations

import re

# TCGA project IDs: "TCGA-" + 2-6 uppercase letters (e.g. TCGA-GBM, TCGA-LUAD).
_PROJECT_RE = re.compile(r"^TCGA-[A-Z]{2,6}$")
# HUGO gene symbols: letters/digits, optionally with a hyphen or dot (e.g. EGFR, HLA-A, C9orf72).
_GENE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.\-]{0,19}$")
# Free-text search terms (e.g. "pi3k", "wnt signaling"): letters/digits/spaces/hyphens only —
# blocks quotes, backslashes, and Cypher/SQL metacharacters that could break out of the literal.
_SEARCH_TERM_RE = re.compile(r"^[A-Za-z0-9 \-]{1,80}$")


class InvalidIdentifier(ValueError):
    """Raised when a value destined for f-string SQL/Cypher interpolation fails shape validation."""


def validate_project_id(project: str) -> str:
    """Validate a TCGA project id (e.g. 'TCGA-GBM') before interpolating it into a query."""
    if not isinstance(project, str) or not _PROJECT_RE.match(project):
        raise InvalidIdentifier(f"not a valid TCGA project id: {project!r}")
    return project


def validate_gene_symbol(gene: str) -> str:
    """Validate a HUGO gene symbol before interpolating it into a query."""
    if not isinstance(gene, str) or not _GENE_RE.match(gene):
        raise InvalidIdentifier(f"not a valid gene symbol: {gene!r}")
    return gene


def validate_search_term(term: str) -> str:
    """Validate a free-text search term (e.g. a pathway-name substring) before interpolating it
    into a query. Narrower than an identifier check — this is query DATA, not an identifier, so
    it only needs to be safe to embed in a single-quoted literal (no quote/backslash chars)."""
    if not isinstance(term, str) or not _SEARCH_TERM_RE.match(term):
        raise InvalidIdentifier(f"search term contains disallowed characters: {term!r}")
    return term
