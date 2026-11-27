#!/usr/bin/env python3
"""Build the hybrid-search corpus for the Oncology Semantic Hub knowledge base.

Produces a flat local corpus directory of `<doc>.txt` documents, each paired with a
`<doc>.txt.metadata.json` sidecar (`{"metadataAttributes": {...}}`) that Bedrock Knowledge Bases
reads to attach filterable metadata to the ingested chunks.

Two public sources (v1, per docs/hybrid-search-design.md):
  A. TCGA project descriptions — all 33 TCGA projects from the GDC projects API.
     metadata: source=TCGA, project_id, disease, primary_site (+ mondo best-effort).
  B. PubMed abstracts — query-driven around the demo thread (glioblastoma/EGFR + immune-checkpoint
     resistance) via NCBI E-utilities (esearch + efetch).
     metadata: source=PubMed, pmid, title, journal, year.

Stdlib only (urllib/xml) so it runs anywhere without extra deps. Re-runnable: the output dir is
cleared of generated corpus files each run (idempotent).

Usage:
    python agentcore/kb/build_corpus.py [--out DIR] [--max-pubmed N] [--per-query K]
"""
import argparse
import glob
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
# XXE-safe XML parsing via defusedxml (disables external entities / entity expansion). The XML source
# is the trusted NCBI eutils API, but we harden regardless (bandit B314/B405, semgrep use-defused-xml).
# The vulnerable stdlib parser is intentionally NOT imported.
from defusedxml.ElementTree import fromstring as _safe_fromstring
from pathlib import Path

GDC_PROJECTS = "https://api.gdc.cancer.gov/projects"
EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
# NCBI etiquette: identify the tool + a contact. Placeholder contact (not real PII).
NCBI_TOOL = "oncology-semantic-hub"
NCBI_EMAIL = "oncology-semantic-hub@example.com"
UA = {"User-Agent": f"{NCBI_TOOL}/1.0 (+{NCBI_EMAIL})"}

# PubMed queries scoped to the demo thread + light pan-oncology (design decision #3).
PUBMED_QUERIES = [
    "glioblastoma EGFR resistance",
    "glioblastoma EGFR targeted therapy resistance",
    "EGFR tyrosine kinase inhibitor resistance mechanism",
    "immune checkpoint inhibitor resistance glioblastoma",
    "immune checkpoint inhibitor resistance cancer mechanism",
    "glioblastoma temozolomide resistance",
    "anti-PD-1 PD-L1 resistance mechanism cancer",
    "tumor mutational burden immunotherapy response",
]


def _get(url: str, params: dict, *, retries: int = 3, sleep: float = 0.4) -> bytes:
    """HTTP GET with polite retry/backoff; returns raw bytes."""
    qs = urllib.parse.urlencode(params, doseq=True)
    full = f"{url}?{qs}"
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(full, headers=UA)
            with urllib.request.urlopen(req, timeout=60) as r:  # nosec B310 (https literal)
                data = r.read()
            time.sleep(sleep)  # rate-limit courtesy  # nosemgrep  (intentional sleep: external-API rate-limit/backoff or async-AWS poll)
            return data
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(1.5 * (attempt + 1))  # nosemgrep  (intentional sleep: external-API rate-limit/backoff or async-AWS poll)
    raise RuntimeError(f"GET failed after {retries} tries: {full}\n{last}")


def _slug(text: str, maxlen: int = 60) -> str:
    s = re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_").lower()
    return s[:maxlen] or "doc"


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()


# ── A. TCGA project descriptions (GDC) ─────────────────────────────────────────
def fetch_tcga_projects() -> list[dict]:
    """Return all TCGA project records from the GDC projects API."""
    filters = {
        "op": "in",
        "content": {"field": "program.name", "value": ["TCGA"]},
    }
    params = {
        "filters": json.dumps(filters),
        "fields": "project_id,name,disease_type,primary_site,summary.case_count,summary.file_count",
        "size": "100",
        "format": "json",
    }
    data = json.loads(_get(GDC_PROJECTS, params))
    hits = (data.get("data") or {}).get("hits")
    if not hits:
        raise RuntimeError(f"GDC returned no TCGA projects (unexpected response: {str(data)[:200]})")
    hits.sort(key=lambda h: h.get("project_id", ""))
    return hits


def _load_mondo_map() -> dict:
    """Best-effort TCGA project_id -> MONDO CURIE map from any local mapping artifact.

    Optional: if not found, MONDO metadata is simply omitted (the L3 agent resolves disease terms
    to MONDO via the OLS tool at query time, per design decision #5)."""
    candidates = []
    for pat in ("data/**/*mondo*.json", "data/**/*project*mondo*.csv", "data/mappings/*.json"):
        candidates += glob.glob(pat, recursive=True)
    for path in candidates:
        try:
            if path.endswith(".json"):
                obj = json.loads(Path(path).read_text())
                # accept {project_id: mondo} or {"...": {"mondo": ...}}
                out = {}
                for k, v in (obj.items() if isinstance(obj, dict) else []):
                    if isinstance(v, str) and v.startswith("MONDO"):
                        out[k] = v
                    elif isinstance(v, dict) and str(v.get("mondo", "")).startswith("MONDO"):
                        out[k] = v["mondo"]
                if out:
                    return out
        except Exception:  # noqa: BLE001
            continue
    return {}


def write_tcga_docs(projects: list[dict], outdir: Path) -> int:
    mondo_map = _load_mondo_map()
    n = 0
    for p in projects:
        pid = p.get("project_id")
        if not pid:
            continue
        name = _clean(p.get("name", pid))
        disease_types = [_clean(d) for d in (p.get("disease_type") or []) if _clean(d)]
        sites = [_clean(s) for s in (p.get("primary_site") or []) if _clean(s)]
        cases = (p.get("summary") or {}).get("case_count")
        files = (p.get("summary") or {}).get("file_count")

        lines = [
            f"TCGA project {pid}: {name}.",
            "Program: The Cancer Genome Atlas (TCGA).",
        ]
        if sites:
            lines.append(f"Primary site(s): {', '.join(sites)}.")
        if disease_types:
            lines.append(f"Disease type(s): {', '.join(disease_types)}.")
        if cases is not None:
            lines.append(f"Cases: {cases}." + (f" Files: {files}." if files is not None else ""))
        lines.append("")
        lines.append(
            f"This TCGA cohort ({pid}) provides molecular and clinical data for {name}"
            + (f" (primary site: {', '.join(sites)}" if sites else "")
            + (f"; disease type: {', '.join(disease_types)}" if disease_types else "")
            + ("). " if (sites or disease_types) else ". ")
            + "It supports biomarker, mutation, expression, and copy-number analyses in oncology research."
        )
        text = "\n".join(lines).strip() + "\n"

        meta_attrs = {"source": "TCGA", "project_id": pid, "disease": name}
        if sites:
            meta_attrs["primary_site"] = "; ".join(sites)[:250]
        if pid in mondo_map:
            meta_attrs["mondo"] = mondo_map[pid]

        stem = f"tcga_{_slug(pid)}"
        (outdir / f"{stem}.txt").write_text(text, encoding="utf-8")
        (outdir / f"{stem}.txt.metadata.json").write_text(
            json.dumps({"metadataAttributes": meta_attrs}, indent=2), encoding="utf-8")
        n += 1
    return n


# ── B. PubMed abstracts (E-utilities) ──────────────────────────────────────────
def pubmed_search(term: str, retmax: int) -> list[str]:
    params = {"db": "pubmed", "term": term, "retmax": str(retmax), "retmode": "json",
              "sort": "relevance", "tool": NCBI_TOOL, "email": NCBI_EMAIL}
    data = json.loads(_get(f"{EUTILS}/esearch.fcgi", params))
    return data.get("esearchresult", {}).get("idlist", [])


def _text_of(elem) -> str:
    """Flatten an XML element's text (drops inner markup tags like <i>/<sup>)."""
    return _clean("".join(elem.itertext())) if elem is not None else ""


def pubmed_fetch(pmids: list[str]) -> list[dict]:
    if not pmids:
        return []
    params = {"db": "pubmed", "id": ",".join(pmids), "retmode": "xml",
              "tool": NCBI_TOOL, "email": NCBI_EMAIL}
    xml = _get(f"{EUTILS}/efetch.fcgi", params)
    root = _safe_fromstring(xml)
    out = []
    for art in root.findall(".//PubmedArticle"):
        pmid = _text_of(art.find(".//MedlineCitation/PMID"))
        title = _text_of(art.find(".//Article/ArticleTitle"))
        # Abstract may be split into labeled sections.
        sections = []
        for ab in art.findall(".//Article/Abstract/AbstractText"):
            label = ab.get("Label")
            body = _text_of(ab)
            if body:
                sections.append(f"{label}: {body}" if label else body)
        abstract = "\n".join(sections)
        journal = _text_of(art.find(".//Journal/Title"))
        year = _text_of(art.find(".//Journal/JournalIssue/PubDate/Year"))
        if not year:
            medline = _text_of(art.find(".//Journal/JournalIssue/PubDate/MedlineDate"))
            m = re.search(r"\d{4}", medline)
            year = m.group(0) if m else ""
        if pmid and title and abstract:
            out.append({"pmid": pmid, "title": title, "abstract": abstract,
                        "journal": journal, "year": year})
    return out


def write_pubmed_docs(records: list[dict], outdir: Path) -> int:
    n = 0
    for r in records:
        text = f"{r['title']}\n\n{r['abstract']}\n"
        meta_attrs = {"source": "PubMed", "pmid": r["pmid"], "title": r["title"][:250]}
        if r.get("journal"):
            meta_attrs["journal"] = r["journal"][:120]
        if r.get("year"):
            try:
                meta_attrs["year"] = int(r["year"])  # numeric → supports min_year filter
            except ValueError:
                pass
        stem = f"pmid_{r['pmid']}"
        (outdir / f"{stem}.txt").write_text(text, encoding="utf-8")
        (outdir / f"{stem}.txt.metadata.json").write_text(
            json.dumps({"metadataAttributes": meta_attrs}, indent=2), encoding="utf-8")
        n += 1
    return n


def collect_pubmed(max_pubmed: int, per_query: int) -> list[dict]:
    seen: dict[str, dict] = {}
    for q in PUBMED_QUERIES:
        ids = pubmed_search(q, per_query)
        for rec in pubmed_fetch(ids):
            seen.setdefault(rec["pmid"], rec)
        if len(seen) >= max_pubmed:
            break
    return list(seen.values())[:max_pubmed]


def _reset_outdir(outdir: Path):
    outdir.mkdir(parents=True, exist_ok=True)
    for f in outdir.glob("*.txt"):
        f.unlink()
    for f in outdir.glob("*.txt.metadata.json"):
        f.unlink()


def main():
    ap = argparse.ArgumentParser(description="Build the hybrid-search KB corpus (TCGA + PubMed).")
    ap.add_argument("--out", default=str(Path(__file__).parent / "corpus"))
    ap.add_argument("--max-pubmed", type=int, default=60)
    ap.add_argument("--per-query", type=int, default=12)
    ap.add_argument("--skip-tcga", action="store_true")
    ap.add_argument("--skip-pubmed", action="store_true")
    args = ap.parse_args()

    outdir = Path(args.out)
    _reset_outdir(outdir)
    print(f"Corpus output: {outdir}")

    tcga_n = pubmed_n = 0
    if not args.skip_tcga:
        print("[A] Fetching TCGA project descriptions from GDC ...")
        projects = fetch_tcga_projects()
        tcga_n = write_tcga_docs(projects, outdir)
        print(f"    wrote {tcga_n} TCGA project docs")
    if not args.skip_pubmed:
        print("[B] Fetching PubMed abstracts (E-utilities) ...")
        records = collect_pubmed(args.max_pubmed, args.per_query)
        pubmed_n = write_pubmed_docs(records, outdir)
        print(f"    wrote {pubmed_n} PubMed abstract docs")

    total_txt = len(list(outdir.glob("*.txt")))
    print(f"\nDone. {tcga_n} TCGA + {pubmed_n} PubMed = {total_txt} documents in {outdir}")
    if total_txt == 0:
        print("ERROR: no documents produced", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
