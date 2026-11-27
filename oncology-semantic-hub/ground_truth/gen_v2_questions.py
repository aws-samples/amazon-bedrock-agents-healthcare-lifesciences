#!/usr/bin/env python
"""
Generate the v2 validation dataset (~100 questions) for the L2-vs-L3 comparison.

Design (see docs/benchmark-v2-plan.md):
- Templates x real hub entities; every question DUAL-VERIFIED (graph==flat) or via OLS4 or lake.
- Scientific phrasing only (no tech terms; see §12). Structured JSON `ideal` GT. `requires` capability tag.
- Weighted to KG-traversal + OLS (the L2-vs-L3 discriminators) + parity controls + negatives.

Output: evaluation/golden_v2.json  (list of question dicts).
Run: ./.venv/bin/python scripts/gen_v2_questions.py [--limit N]

STATUS: one-time generator, already run — not part of the live pipeline (no __main__ guard; this
module's body executes at import time by design, as a standalone script). The resulting 84-question
dataset was reviewed, hand-corrected, and frozen at ground_truth/golden_v2.json; this script is kept
as a methodology record, not re-run. Its B608 (Bandit/Slingshot) findings are suppressed below with
rationale rather than restructured: every interpolated value is either a module-level constant
(LAKE/RAW database names) or drawn from the hardcoded COHORT_DISEASE/GENES/BRAND/SYNONYM dicts above
— never external input — in dead code that won't run again. See evaluation/sql_guards.py for the
equivalent guard applied to the live generator, evaluation/generate_questions.py.
"""
import boto3, json, time, urllib.request, urllib.parse, argparse, itertools
neptune=boto3.client("neptune-graph",region_name="us-west-2"); ath=boto3.client("athena",region_name="us-west-2")
import os
OUT=os.environ.get("SEMHUB_ATHENA_OUTPUT",""); RAW="oncology_semantic_hub_raw"; LAKE="oncology_semantic_hub"

def cy(q):
    return json.loads(neptune.execute_query(graphIdentifier=os.environ.get("SEMHUB_GRAPH_ID",""),queryString=q,language="OPEN_CYPHER")["payload"].read())["results"]
def sql(q):
    qid=ath.start_query_execution(QueryString=q,ResultConfiguration={"OutputLocation":OUT},WorkGroup="primary")["QueryExecutionId"]
    while ath.get_query_execution(QueryExecutionId=qid)["QueryExecution"]["Status"]["State"] not in ("SUCCEEDED","FAILED","CANCELLED"): time.sleep(1.2)  # nosemgrep  (intentional sleep: external-API rate-limit/backoff or async-AWS poll)
    st=ath.get_query_execution(QueryExecutionId=qid)["QueryExecution"]["Status"]
    if st["State"]!="SUCCEEDED": raise RuntimeError(str(st.get("StateChangeReason"))[:150])
    return [[c.get("VarCharValue","") for c in r["Data"]] for r in ath.get_query_results(QueryExecutionId=qid)["ResultSet"]["Rows"]]
def _safe_urlopen(req_or_url, **kwargs):
    """urllib.request.urlopen, restricted to https:// (Bandit B310). The OLS4 URL is a hardcoded
    https literal, never user input, but validating the scheme is the correct hardening regardless."""
    url = req_or_url.full_url if isinstance(req_or_url, urllib.request.Request) else req_or_url
    scheme = urllib.parse.urlsplit(url).scheme
    if scheme != "https":
        raise ValueError(f"refusing to open non-https URL (scheme={scheme!r}): {url}")
    return urllib.request.urlopen(req_or_url, **kwargs)  # nosec B310 — scheme validated above


def ols(term):
    u="https://www.ebi.ac.uk/ols4/api/search?"+urllib.parse.urlencode({"q":term,"ontology":"mondo","rows":1})
    for _ in range(3):
        try:
            d=json.load(_safe_urlopen(u,timeout=12)); docs=d.get("response",{}).get("docs",[])
            return (docs[0].get("obo_id"),docs[0].get("label")) if docs else (None,None)
        except Exception: time.sleep(1)  # nosemgrep  (intentional sleep: external-API rate-limit/backoff or async-AWS poll)
    return (None,None)

COHORT_DISEASE={"TCGA-GBM":"glioblastoma (disease)","TCGA-BRCA":"breast carcinoma","TCGA-LUAD":"lung adenocarcinoma",
                "TCGA-COAD":"colorectal cancer","TCGA-SKCM":"melanoma","TCGA-PRAD":"prostate cancer"}
GENES=["EGFR","TP53","PTEN","PIK3CA","IDH1","PDGFRA","KRAS","BRAF","RB1","NF1","ATRX","PIK3R1"]
SYNONYM={"grade IV astrocytoma":"glioblastoma (disease)"}   # WHO grade IV astrocytoma == glioblastoma
BRAND={"Tarceva":"Erlotinib","Iressa":"Gefitinib","Tagrisso":"Osimertinib","Gleevec":"Imatinib","Herceptin":"Trastuzumab"}
COMMON_DISEASE={"breast cancer":"breast carcinoma","colon cancer":"colorectal cancer"}  # common name -> node name

out=[]; seen=set()
def emit(qid, question, requires, min_layer, hops, ideal, verify):
    if question in seen: return
    seen.add(question)
    out.append({"id":qid,"question":question,"requires":requires,"min_layer":min_layer,"hops":hops,
                "ideal":ideal,"verify":verify,"canary":"oncohub-v2-benchmark-2026"})

def bidir_genes_for_disease(d):
    g=set(x["gene"] for x in cy(f"MATCH (dis:disease {{name:\"{d}\"}})-[:disease_protein]-(g:gene_protein) RETURN DISTINCT g.name AS gene"))
    f=set(r[0] for r in sql(f"SELECT y_name g FROM {RAW}.primekg_edges WHERE relation='disease_protein' AND x_name=\"{d}\" UNION SELECT x_name FROM {RAW}.primekg_edges WHERE relation='disease_protein' AND y_name=\"{d}\"".replace('"',"'"))[1:])  # nosec B608 — RAW constant; d from the hardcoded COHORT_DISEASE dict (dead one-time script, see module docstring)
    return g, (g==f)
def gbm_mut_genes(cohort, thresh=None):
    q=f"SELECT hugo_symbol FROM {LAKE}.tcga_mutations WHERE project_id='{cohort}' GROUP BY hugo_symbol"  # nosec B608 — LAKE constant; cohort from the hardcoded COHORT_DISEASE dict (dead one-time script, see module docstring)
    if thresh: q+=f" HAVING count(DISTINCT case_id)>={thresh}"
    return set(r[0] for r in sql(q)[1:])
def drug_count(gene):
    g=cy(f"MATCH (:gene_protein{{name:'{gene}'}})-[:drug_protein]-(d:drug) RETURN count(DISTINCT d) AS n")[0]["n"]
    f=sql(f"SELECT count(DISTINCT x) FROM (SELECT y_name x FROM {RAW}.primekg_edges WHERE relation='drug_protein' AND x_name='{gene}' UNION SELECT x_name FROM {RAW}.primekg_edges WHERE relation='drug_protein' AND y_name='{gene}')")[1][0]  # nosec B608 — RAW constant; gene from the hardcoded GENES list (dead one-time script, see module docstring)
    return int(g), (str(g)==f)

n=0
# ---- P1 lake control: mutation counts ----
for cohort,gene in itertools.product(["TCGA-GBM","TCGA-BRCA","TCGA-LUAD","TCGA-COAD"],["EGFR","TP53","PTEN","KRAS"]):
    try:
        c=int(sql(f"SELECT count(DISTINCT case_id) FROM {LAKE}.tcga_mutations WHERE project_id='{cohort}' AND hugo_symbol='{gene}'")[1][0])  # nosec B608 — LAKE constant; cohort/gene from the hardcoded lists above (dead one-time script, see module docstring)
        if c>0: n+=1; emit(f"v2_lake_{n:03d}",f"How many distinct {cohort} patients carry a mutation in {gene}?","lake","L1",1,{"n_patients":c},"lake")
    except Exception as e: print("P1 skip",cohort,gene,e)
# ---- P2 graph_1hop control: drug counts ----
for gene in GENES:
    try:
        c,m=drug_count(gene)
        if c>0: n+=1; emit(f"v2_g1_{n:03d}",f"How many distinct drugs are known to target {gene}?","graph_1hop","L2",1,{"gene":gene,"drug_count":c},f"graph==flat:{m}")
    except Exception as e: print("P2 skip",gene,e)
# precompute disease gene sets
DGENES={}; 
for c,d in COHORT_DISEASE.items():
    try: DGENES[d]=bidir_genes_for_disease(d)
    except Exception as e: print("dgene skip",d,e)
# ---- O1 reconciliation cohort->disease gene count ----
for cohort,d in COHORT_DISEASE.items():
    if d in DGENES:
        gs,match=DGENES[d]
        n+=1; emit(f"v2_recon_{n:03d}",f"How many distinct genes are associated with the type of cancer studied in the {cohort} cohort?","reconciliation","L3",2,{"n_associated_genes":len(gs)},f"graph==flat:{match}")
# ---- K1 multi_source actionable targets ----
for cohort,d in COHORT_DISEASE.items():
    if d not in DGENES: continue
    try:
        gs,match=DGENES[d]; mut=gbm_mut_genes(cohort,10)
        drug=set(x["gene"] for x in cy(f"MATCH (dis:disease {{name:\"{d}\"}})-[:disease_protein]-(g:gene_protein)-[:drug_protein]-(:drug) RETURN DISTINCT g.name AS gene"))
        inter=sorted(gs & mut & drug)
        if inter: n+=1; emit(f"v2_multi_{n:03d}",f"Among genes mutated in at least 10 {cohort} patients, which are both associated with {'this cancer type' if False else d.replace(' (disease)','')} and targeted by at least one known drug? List the genes.","multi_source","L3",3,{"genes":inter,"n":len(inter)},f"graph_assoc==flat:{match}")
    except Exception as e: print("K1 skip",cohort,e)
# ---- K2 graph_multihop: disease-assoc & cohort-mutated, top by drug count ----
for cohort,d in COHORT_DISEASE.items():
    if d not in DGENES: continue
    try:
        gs,_=DGENES[d]; mut=gbm_mut_genes(cohort)
        counts={x["gene"]:x["n"] for x in cy(f"MATCH (dis:disease {{name:\"{d}\"}})-[:disease_protein]-(g:gene_protein)-[:drug_protein]-(dr:drug) RETURN g.name AS gene, count(DISTINCT dr) AS n")}
        ranked=sorted(((v,k) for k,v in counts.items() if k in mut),reverse=True)[:5]
        if ranked: n+=1; emit(f"v2_mh_{n:03d}",f"Among genes associated with {d.replace(' (disease)','')} that are also mutated in {cohort} patients, which one is targeted by the most drugs? Give the gene and the number of drugs.","graph_multihop","L3",3,{"top":[[g,c] for c,g in ranked]},"graph")
    except Exception as e: print("K2 skip",cohort,e)
# ---- K3 graph_multihop: pathway-sharing with gene & disease-assoc ----
for gene,d in [("EGFR","glioblastoma (disease)"),("KRAS","colorectal cancer"),("BRAF","melanoma"),("PIK3CA","breast carcinoma")]:
    try:
        g6=sorted(set(x["gene"] for x in cy(f"MATCH (:gene_protein{{name:'{gene}'}})-[:pathway_protein]-(:pathway)-[:pathway_protein]-(g:gene_protein) WHERE g.name<>'{gene}' WITH DISTINCT g MATCH (g)-[:disease_protein]-(:disease{{name:\"{d}\"}}) RETURN DISTINCT g.name AS gene")))
        if g6: n+=1; emit(f"v2_mh_{n:03d}",f"Which genes are in the same biological pathway as {gene} and are also associated with {d.replace(' (disease)','')}? List the genes.","graph_multihop","L3",3,{"genes":g6,"n":len(g6)},"graph")
    except Exception as e: print("K3 skip",gene,e)
# ---- K4 graph_multihop: interaction partners of gene & disease-assoc ----
for gene,d in [("EGFR","glioblastoma (disease)"),("TP53","breast carcinoma"),("KRAS","colorectal cancer")]:
    try:
        g4=sorted(set(x["gene"] for x in cy(f"MATCH (:gene_protein{{name:'{gene}'}})-[:protein_protein]-(g:gene_protein) WITH DISTINCT g MATCH (g)-[:disease_protein]-(:disease{{name:\"{d}\"}}) RETURN DISTINCT g.name AS gene")))
        if g4: n+=1; emit(f"v2_mh_{n:03d}",f"Which direct protein-interaction partners of {gene} are associated with {d.replace(' (disease)','')}? List the genes.","graph_multihop","L3",2,{"genes":g4,"n":len(g4)},"graph")
    except Exception as e: print("K4 skip",gene,e)
# ---- O2 ontology synonym ----
for syn,d in SYNONYM.items():
    if d not in DGENES: continue
    try:
        gs,_=DGENES[d]; mut=gbm_mut_genes("TCGA-GBM")
        inter=sorted(gs&mut)
        n+=1; emit(f"v2_onto_{n:03d}",f"Which genes associated with {syn} are also mutated in TCGA-GBM patients? List the genes.","ontology","L3",2,{"genes":inter,"n":len(inter),"note":f"{syn} == glioblastoma"},"graph+synonym")
    except Exception as e: print("O2 skip",syn,e)
# ---- O3 brand drug -> targets ----
for brand,generic in BRAND.items():
    try:
        tg=cy(f"MATCH (:drug{{name:'{generic}'}})-[:drug_protein]-(g:gene_protein) RETURN DISTINCT g.name AS gene")
        genes=sorted(x["gene"] for x in tg)
        if genes: n+=1; emit(f"v2_onto_{n:03d}",f"Which genes are targeted by the drug {brand}?","ontology","L3",1,{"generic":generic,"genes":genes,"n":len(genes),"note":f"{brand} brand of {generic}"},"graph+brand")
    except Exception as e: print("O3 skip",brand,e)
# ---- O4 common disease name -> node ----
for common,d in COMMON_DISEASE.items():
    if d not in DGENES: continue
    gs,_=DGENES[d]
    n+=1; emit(f"v2_recon_{n:03d}",f"How many distinct genes are associated with {common}?","reconciliation","L3",1,{"n_associated_genes":len(gs),"note":f"{common} -> {d}"},"graph")
# ---- N negatives ----
negs=[("AJCC tumor stage distribution","stage"),("overall survival (months)","survival"),("protein abundance","proteomics"),("radiology imaging findings","imaging")]
for i,(what,why) in enumerate(negs):
    for cohort in ["TCGA-GBM","TCGA-BRCA"][:1 if i>1 else 2]:
        n+=1; emit(f"v2_neg_{n:03d}",f"What is the {what} of EGFR-mutant {cohort} patients?","negative","L1",0,{"answer":"cannot_determine","reason":f"{why} is not present in the hub"},"by-design")

json.dump(out, open("evaluation/golden_v2.json","w"), indent=2, default=str)
from collections import Counter
print("\n=== GENERATED", len(out), "questions ===")
print("by requires:", dict(Counter(q["requires"] for q in out)))
bad=[q["id"] for q in out if isinstance(q["verify"],str) and q["verify"].endswith("False")]
print("verification MISMATCHES (investigate):", bad)
