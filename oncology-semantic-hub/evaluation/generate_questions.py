"""Template-driven ground-truth generator + verifier (Phase 2, ~55 questions).

Method: parameterized templates x entity-pools-from-live-data x deterministic
verification. Ground truth comes from the authoritative source:
  - quantitative / drug_gene / cross_system: pinned Athena SQL + Neptune Cypher
  - ontology: EBI OLS4 REST API (the ontology's own source of truth)
  - negative_controls: by design (data absent from the hub)

Output is AgentCore-compatible (maps to bedrock_agentcore.evaluation ReferenceInputs):
  input -> prompt; evaluationReferenceInputs.{expectedResponse, expectedTrajectory,
  assertions}; metadata carries category/answer_type/verification/snapshot.

Confirmed distribution: quantitative 20 / drug_gene 15 / ontology 10 /
negative_controls 5 / cross_system 5 = 55.

Usage:
    python -m evaluation.generate_questions            # full generate + verify + write
    python -m evaluation.generate_questions --smoke    # ~2 per category (fast live check)
"""

from __future__ import annotations

import argparse
import json
import urllib.parse
import urllib.request

from . import config as C
from .hub_tools import run_cypher, run_sql
from .sql_guards import validate_gene_symbol, validate_project_id


def _safe_urlopen(req_or_url, **kwargs):
    """urllib.request.urlopen, restricted to https:// (Bandit B310). The OLS4 URL below is a hardcoded
    https literal, never user input, but validating the scheme is the correct hardening regardless."""
    url = req_or_url.full_url if isinstance(req_or_url, urllib.request.Request) else req_or_url
    scheme = urllib.parse.urlsplit(url).scheme
    if scheme != "https":
        raise ValueError(f"refusing to open non-https URL (scheme={scheme!r}): {url}")
    return urllib.request.urlopen(req_or_url, **kwargs)  # nosec B310 — scheme validated above

# Oncology focus (lung, breast, gastric + other relevant TCGA projects)
FOCUS_PROJECTS = ["TCGA-BRCA", "TCGA-LUAD", "TCGA-LUSC", "TCGA-STAD",
                  "TCGA-GBM", "TCGA-COAD", "TCGA-LIHC", "TCGA-KIRC"]


# ── entity pools (live) ──────────────────────────────────────────────────────
def cosmic_tier1() -> set[str]:
    return {r["n"] for r in run_cypher(
        "MATCH (g:gene_protein) WHERE g.cosmic_tier=1 RETURN g.name AS n")}


def top_genes(project: str, limit: int = 15) -> list[tuple[str, int]]:
    project = validate_project_id(project)  # B608: validate before f-string interpolation
    rows = run_sql(
        f"SELECT hugo_symbol, count(DISTINCT case_id) c FROM tcga_mutations "
        f"WHERE project_id='{project}' GROUP BY hugo_symbol ORDER BY c DESC LIMIT {int(limit)}")[1:]
    return [(r[0], int(r[1])) for r in rows]


def drug_count(gene: str) -> int:
    gene = validate_gene_symbol(gene)  # B608: validate before f-string interpolation
    return run_cypher(
        f"MATCH (g:gene_protein {{name:'{gene}'}})-[:drug_protein]-(d:drug) "
        f"RETURN count(d) AS c")[0]["c"]


def drug_names(gene: str) -> list[str]:
    gene = validate_gene_symbol(gene)  # B608: validate before f-string interpolation
    return [r["d"] for r in run_cypher(
        f"MATCH (g:gene_protein {{name:'{gene}'}})-[:drug_protein]-(d:drug) "
        f"RETURN DISTINCT d.name AS d ORDER BY d")]


def pathway_names(gene: str) -> list[str]:
    gene = validate_gene_symbol(gene)  # B608: validate before f-string interpolation
    return [r["p"] for r in run_cypher(
        f"MATCH (g:gene_protein {{name:'{gene}'}})-[:pathway_protein]-(p:pathway) "
        f"RETURN DISTINCT p.name AS p ORDER BY p")]


def tcga_diseases() -> list[str]:
    return [r["n"] for r in run_cypher(
        "MATCH (c:case)-[:case_has_diagnosis]->(d:disease) RETURN DISTINCT d.name AS n ORDER BY n")]


def ols4_mondo_id(disease: str) -> str | None:
    url = "https://www.ebi.ac.uk/ols4/api/search?" + urllib.parse.urlencode(
        {"q": disease, "ontology": "mondo", "rows": 1})
    try:
        with _safe_urlopen(url, timeout=25) as r:
            docs = json.load(r)["response"]["docs"]
        return docs[0]["obo_id"] if docs else None
    except Exception:
        return None


# ── entry builder (AgentCore-compatible) ─────────────────────────────────────
def _trajectory(required_layers):
    t = []
    if "L1" in required_layers:
        t.append("query_patient_data")
    if "L2" in required_layers:
        t += ["get_hub_schema", "query_knowledge_graph"]
    return t


def entry(qid, question, answer_type, category, expected, assertions,
          required_layers, queries, complexity, verification="programmatic", trajectory=None):
    return {
        "id": qid,
        "input": question,
        "evaluationReferenceInputs": {
            "expectedResponse": str(expected),
            "expectedTrajectory": trajectory if trajectory is not None else _trajectory(required_layers),
            "assertions": assertions or [],
        },
        "metadata": {
            "category": category,
            "answer_type": answer_type,
            "required_layers": required_layers,
            "complexity": complexity,
            "verification_method": verification,
            "verification_queries": queries,
            "data_snapshot": C.DATA_SNAPSHOT,
        },
    }


# ── category generators (each returns a list of entries) ─────────────────────
def gen_quantitative(tier1, n=20):
    out, i = [], 0
    # (a) top-5 mutated genes per project (ranked_list)
    for p in FOCUS_PROJECTS:
        tg = top_genes(p, 5)
        if not tg:
            continue
        i += 1
        out.append(entry(
            f"q_quant_{i:02d}",
            f"What are the top 5 most frequently mutated genes in {p} by distinct patient count? List gene symbols in order.",
            "ranked_list", "quantitative_precision",
            ", ".join(g for g, _ in tg), [g for g, _ in tg[:3]], ["L1"],
            [f"SELECT hugo_symbol, count(DISTINCT case_id) c FROM tcga_mutations WHERE project_id='{p}' GROUP BY hugo_symbol ORDER BY c DESC LIMIT 5"], 2))
    # (b) distinct-patient counts for tier-1 driver genes per project (exact_number)
    for p in FOCUS_PROJECTS:
        for g, _ in top_genes(p, 20):
            if g not in tier1:
                continue
            g = validate_gene_symbol(g)  # B608: validate before f-string interpolation (g came from a live query, not a hardcoded literal)
            p_v = validate_project_id(p)  # B608: validate before f-string interpolation
            sql = f"SELECT count(DISTINCT case_id) FROM tcga_mutations WHERE hugo_symbol='{g}' AND project_id='{p_v}'"
            cnt = run_sql(sql)[1][0]
            if cnt in ("0", 0):
                continue
            i += 1
            out.append(entry(
                f"q_quant_{i:02d}",
                f"How many distinct patients have {g} mutations in {p}?",
                "exact_number", "quantitative_precision", cnt, [str(cnt)], ["L1"], [sql], 1))
    return out[:n]


def gen_drug_gene(tier1, n=15):
    out, i = [], 0
    drugged = [(g, drug_count(g)) for g in sorted(tier1)]
    drugged = [(g, c) for g, c in drugged if c > 0]
    for g, c in drugged:
        i += 1
        out.append(entry(
            f"q_drug_{i:02d}",
            f"What drugs are connected to the {g} gene_protein node via drug_protein edges? List drug names.",
            "entity_list", "drug_gene_relationships", ", ".join(drug_names(g)),
            drug_names(g)[:3], ["L2"],
            [f"MATCH (g:gene_protein {{name:'{g}'}})-[:drug_protein]-(d:drug) RETURN d.name ORDER BY d.name"], 2))
        if len(out) >= n:
            return out[:n]
    # top up with pathway-list questions
    for g in sorted(tier1):
        pw = pathway_names(g)
        if not pw:
            continue
        i += 1
        out.append(entry(
            f"q_drug_{i:02d}",
            f"What pathways are connected to the {g} gene_protein node via pathway_protein edges? List pathway names.",
            "entity_list", "drug_gene_relationships", ", ".join(pw), pw[:3], ["L2"],
            [f"MATCH (g:gene_protein {{name:'{g}'}})-[:pathway_protein]-(p:pathway) RETURN p.name ORDER BY p.name"], 2))
        if len(out) >= n:
            break
    return out[:n]


def gen_cross_system(n=5):
    """Cross-system composition: from the lake, take a project's top-10 mutated genes;
    from the graph, pick the one with the MOST drug targets. Requires both systems, and
    naturally diversifies the target gene + avoids trivially-small counts."""
    out, i, used = [], 0, set()
    for p in FOCUS_PROJECTS:
        cands = [(g, drug_count(g)) for g, _ in top_genes(p, 10)]
        cands = sorted([(g, c) for g, c in cands if c >= 2], key=lambda x: -x[1])
        if not cands:
            continue
        gene, dc = next((gc for gc in cands if gc[0] not in used), cands[0])
        used.add(gene)
        i += 1
        out.append(entry(
            f"q_cross_{i:02d}",
            f"Among the 10 most frequently mutated genes in {p} (by distinct patient count), which gene has the most drugs targeting it via drug_protein edges, and how many drugs is that?",
            "composite", "cross_system",
            f"Among the top 10 mutated genes in {p}, {gene} has the most drug targets: {dc} drugs.",
            [gene, str(dc)], ["L1", "L2"],
            [f"SELECT hugo_symbol, count(DISTINCT case_id) c FROM tcga_mutations WHERE project_id='{p}' GROUP BY hugo_symbol ORDER BY c DESC LIMIT 10",  # nosec B608 — this string is dataset verify-metadata (documentation of how to re-check the GT), never executed as a query by this codebase; p is from the hardcoded FOCUS_PROJECTS list
             "for each gene: MATCH (g:gene_protein {name:<gene>})-[:drug_protein]-(d:drug) RETURN count(DISTINCT d); pick argmax"], 3))
        if len(out) >= n:
            break
    return out[:n]


def gen_ontology(n=10):
    out, i = [], 0
    for dis in tcga_diseases():
        mondo = ols4_mondo_id(dis)
        if not mondo:
            continue
        i += 1
        out.append(entry(
            f"q_onto_{i:02d}",
            f"What is the MONDO ontology identifier for the disease '{dis}'?",
            "composite", "ontology_resolution", mondo, [mondo], ["L2"],
            [f"OLS4 search q='{dis}' ontology=mondo -> obo_id"], 2, verification="ols4",
            trajectory=["ontology_lookup"]))
        if len(out) >= n:
            break
    return out


def gen_negative(n=5):
    items = [
        ("tumor stage / AJCC stage", "What is the AJCC tumor stage for TCGA-STAD patients with TP53 mutations?"),
        ("proteomics / protein abundance", "What is the measured protein abundance of EGFR protein in TCGA-LUAD tumors?"),
        ("histology imaging", "What tumor grade is reported from the H&E pathology images for TCGA-BRCA cases?"),
        ("treatment / drug response", "Which chemotherapy regimen did TCGA-COAD patients receive and did they respond?"),
        ("DNA methylation", "What is the promoter methylation beta-value of MLH1 in TCGA-COAD samples?"),
    ]
    out = []
    for j, (topic, q) in enumerate(items[:n], 1):
        out.append(entry(
            f"q_neg_{j:02d}", q, "negative", "negative_controls",
            "Cannot be determined from the hub — no such data is loaded (absent: " + topic + ").",
            [], [], [f"ABSENT FROM HUB: {topic}"], 1, verification="by_design"))
    return out


def gen_misalignment(n_disease=4, n_gene=4):
    """Probe the cross-system ontology-misalignment gaps:
    (a) disease-mapping accuracy — GT = correct MONDO from OLS4; the graph's TCGA->MONDO
        map is wrong/approximate for these, so graph-only L3 fails (motivates the OLS layer).
    (b) unmatched genes — mutated in TCGA but absent from PrimeKG; correct answer is 'absent'.
    """
    # TCGA project -> canonical cancer (for OLS4 lookup); these have wrong/approximate graph maps
    misaligned = {
        "TCGA-LGG": "low grade glioma", "TCGA-SKCM": "cutaneous melanoma",
        "TCGA-ESCA": "esophageal carcinoma", "TCGA-STAD": "stomach adenocarcinoma",
        "TCGA-PCPG": "pheochromocytoma", "TCGA-THCA": "thyroid carcinoma",
    }
    unmatched = [("FO393400.1", "TCGA-BRCA"), ("STIMATE-MUSTN1", "TCGA-BRCA"),
                 ("AC020907.6", "TCGA-BRCA"), ("CXorf21", "TCGA-BRCA")]
    out, i = [], 0
    for proj, canonical in list(misaligned.items())[:n_disease]:
        mondo = ols4_mondo_id(canonical)
        if not mondo:
            continue
        cur = run_cypher(f"MATCH (c:case {{project_id:'{proj}'}})-[:case_has_diagnosis]->(d:disease) RETURN DISTINCT d.name AS n")
        curname = cur[0]["n"] if cur else "(none)"
        i += 1
        out.append(entry(
            f"q_misalign_{i:02d}",
            f"What is the correct MONDO ontology identifier for the cancer studied in TCGA project {proj} ({canonical})?",
            "composite", "cross_system_misalignment", mondo, [mondo], ["L2"],
            [f"OLS4 q='{canonical}' ontology=mondo -> {mondo} (correct); graph currently maps {proj} -> '{curname}'"],
            3, verification="ols4", trajectory=["ontology_lookup"]))
    for gene, proj in unmatched[:n_gene]:
        if run_cypher(f"MATCH (g:gene_protein {{name:'{gene}'}}) RETURN count(g) AS c")[0]["c"] > 0:
            continue  # only use genuinely-absent genes
        i += 1
        out.append(entry(
            f"q_misalign_{i:02d}",
            f"The gene {gene} is mutated in {proj}. In the knowledge graph, how many drugs target {gene} via drug_protein edges?",
            "negative", "cross_system_misalignment",
            f"{gene} is not present as a gene_protein node in the knowledge graph (0 drug targets) — a cross-system identifier gap.",
            [], ["L2"],
            [f"MATCH (g:gene_protein {{name:'{gene}'}}) RETURN count(g) -> 0 (absent from PrimeKG)"],
            3, verification="programmatic", trajectory=["query_knowledge_graph"]))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true", help="~2 per category, fast live check")
    args = ap.parse_args()

    tier1 = cosmic_tier1()
    print(f"COSMIC Tier-1 genes: {len(tier1)}")

    if args.smoke:
        qs = (gen_quantitative(tier1, 2) + gen_drug_gene(tier1, 2)
              + gen_cross_system(2) + gen_ontology(2) + gen_negative(2)
              + gen_misalignment(1, 1))
    else:
        qs = (gen_quantitative(tier1, 20) + gen_drug_gene(tier1, 15)
              + gen_cross_system(5) + gen_ontology(10) + gen_negative(5)
              + gen_misalignment(4, 4))

    from collections import Counter
    by_cat = Counter(q["metadata"]["category"] for q in qs)
    print(f"Generated {len(qs)} questions: {dict(by_cat)}")
    for q in qs:
        print(f"  {q['id']:<12} [{q['metadata']['answer_type']:<12}] "
              f"{q['input'][:62]} -> {q['evaluationReferenceInputs']['expectedResponse'][:45]}")

    if not args.smoke:
        with open(C.GOLDEN_DATASET, "w") as f:
            json.dump(qs, f, indent=2, default=str)
        print(f"\nWrote {len(qs)} verified questions -> {C.GOLDEN_DATASET}  (snapshot {C.DATA_SNAPSHOT})")


if __name__ == "__main__":
    main()
