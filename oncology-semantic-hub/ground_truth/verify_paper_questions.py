#!/usr/bin/env python
"""Verify + tech-free-rephrase the owner's 18 paper-derived questions, compute real GT from the hub,
and write evaluation/golden_v2_papers.json. Each keeps paper_reference (provenance) + _tech_note (original).

STATUS: one-time generator, already run — not part of the live pipeline (no __main__ guard; this
module's body executes at import time by design, as a standalone script). Kept as a methodology
record. Its B608 (Bandit/Slingshot) findings are suppressed below with rationale rather than
restructured, since every interpolated value here is a hardcoded literal or module-level config
constant (LAKE/RAW database names, fixed gene/drug names) — never external input — in dead code
that won't be re-run. See evaluation/sql_guards.py for the equivalent guard applied to the live
generator, evaluation/generate_questions.py."""
import boto3, json, time, re
neptune=boto3.client("neptune-graph",region_name="us-west-2"); ath=boto3.client("athena",region_name="us-west-2")
import os
OUT=os.environ.get("SEMHUB_ATHENA_OUTPUT",""); RAW="oncology_semantic_hub_raw"; LAKE="oncology_semantic_hub"
def cy(q): return json.loads(neptune.execute_query(graphIdentifier=os.environ.get("SEMHUB_GRAPH_ID",""),queryString=q,language="OPEN_CYPHER")["payload"].read())["results"]
def sql(q):
    qid=ath.start_query_execution(QueryString=q,ResultConfiguration={"OutputLocation":OUT},WorkGroup="primary")["QueryExecutionId"]
    while ath.get_query_execution(QueryExecutionId=qid)["QueryExecution"]["Status"]["State"] not in ("SUCCEEDED","FAILED","CANCELLED"): time.sleep(1.2)  # nosemgrep  (intentional sleep: external-API rate-limit/backoff or async-AWS poll)
    st=ath.get_query_execution(QueryExecutionId=qid)["QueryExecution"]["Status"]
    if st["State"]!="SUCCEEDED": raise RuntimeError(str(st.get("StateChangeReason"))[:150])
    return [[c.get("VarCharValue","") for c in r["Data"]] for r in ath.get_query_results(QueryExecutionId=qid)["ResultSet"]["Rows"]]
src={q["id"]:q for q in json.load(open("/Users/hpoonawa/Downloads/Paper-Derived Questions (18).json"))}
out=[]
def keep(qid, sci, requires, ideal, verify):
    o=dict(src[qid]); o["_tech_note"]=o.pop("input"); o["question"]=sci; o["requires"]=requires; o["ideal"]=ideal; o["verify"]=verify
    o.pop("expected_answer",None)
    out.append(o); print(f"[{qid}] {requires} verify={verify}\n   Q: {sci}\n   GT: {json.dumps(ideal)[:150]}")

def pathways_containing(sub):
    return [x["name"] for x in cy(f"MATCH (p:pathway) WHERE toLower(p.name) CONTAINS '{sub.lower()}' RETURN DISTINCT p.name AS name LIMIT 20")]

try:
    # discover pathway node names
    print("PI3K pathways:", pathways_containing("pi3k")[:6])
    print("Wnt pathways:", pathways_containing("wnt")[:6])
    print("EGFR pathways:", pathways_containing("egfr")[:6])

    # bailey_03 / liu_01 / liu_03 (lake)
    r=sql(f"SELECT project_id, count(DISTINCT case_id) c FROM {LAKE}.tcga_mutations WHERE hugo_symbol='TP53' GROUP BY project_id ORDER BY c DESC LIMIT 1")[1]  # nosec B608 — LAKE is a module constant; 'TP53' hardcoded (dead one-time script, see module docstring)
    keep("q_paper_bailey_03",f"Which TCGA cancer type has the most distinct patients with TP53 mutations, and how many?","quantitative",{"cohort":r[0],"n":int(r[1])},"lake")
    r=sql(f"SELECT count(DISTINCT case_id) FROM {LAKE}.tcga_mutations")[1][0]  # nosec B608 — LAKE is a module constant (dead one-time script, see module docstring)
    keep("q_paper_liu_01","How many distinct patients are in the TCGA mutation data across all projects?","lake",{"n_patients":int(r)},"lake")
    r=sql(f"SELECT hugo_symbol, count(DISTINCT project_id) n FROM {LAKE}.tcga_mutations GROUP BY hugo_symbol ORDER BY n DESC LIMIT 1")[1]  # nosec B608 — LAKE is a module constant (dead one-time script, see module docstring)
    keep("q_paper_liu_03","Which gene is mutated across the most TCGA cancer types, and in how many?","quantitative",{"gene":r[0],"n_cancer_types":int(r[1])},"lake")

    # bailey_01 adapted -> COSMIC Tier-1 druggable
    tier1=cy("MATCH (g:gene_protein) WHERE g.cosmic_tier=1 RETURN count(DISTINCT g) AS n")[0]["n"]
    drug1=cy("MATCH (g:gene_protein) WHERE g.cosmic_tier=1 MATCH (g)-[:drug_protein]-(:drug) RETURN count(DISTINCT g) AS n")[0]["n"]
    keep("q_paper_bailey_01","How many confirmed cancer-driver genes are targeted by at least one drug?","cross_system",{"n_druggable_drivers":int(drug1),"n_drivers_total":int(tier1),"note":"drivers = COSMIC Cancer Gene Census Tier-1"},"graph")

    # sanchezvega_01: pathways involving both EGFR and PIK3CA
    p=sorted(set(x["p"] for x in cy("MATCH (:gene_protein{name:'EGFR'})-[:pathway_protein]-(p:pathway)-[:pathway_protein]-(:gene_protein{name:'PIK3CA'}) RETURN DISTINCT p.name AS p")))
    keep("q_paper_sanchezvega_01","Which biological pathways involve both EGFR and PIK3CA?","graph_multihop",{"pathways":p,"n":len(p)},"graph")

    # primekg_01: indication edges count (flat) + graph
    fi=sql(f"SELECT count(*) FROM {RAW}.primekg_edges WHERE relation='indication'")[1][0]  # nosec B608 — RAW is a module constant (dead one-time script, see module docstring)
    keep("q_paper_primekg_01","How many drug–disease indication relationships are in the hub?","graph_1hop",{"n_indications":int(fi)},"flat(primekg)")

    # primekg_02: Crizotinib targets + indications
    tg=sorted(x["g"] for x in cy("MATCH (:drug{name:'Crizotinib'})-[:drug_protein]-(g:gene_protein) RETURN DISTINCT g.name AS g"))
    ind=sorted(x["d"] for x in cy("MATCH (:drug{name:'Crizotinib'})-[:indication]-(d:disease) RETURN DISTINCT d.name AS d"))
    keep("q_paper_primekg_02","Which genes does the drug Crizotinib target, and which diseases is it approved to treat?","multi_source",{"targets":tg,"indications":ind},"graph")

    # abbvie_02: LUAD top10 most-drugged
    top10=[r[0] for r in sql(f"SELECT hugo_symbol FROM {LAKE}.tcga_mutations WHERE project_id='TCGA-LUAD' GROUP BY hugo_symbol ORDER BY count(DISTINCT case_id) DESC LIMIT 10")[1:]]  # nosec B608 — LAKE constant + hardcoded project id (dead one-time script, see module docstring)
    best=None
    for g in top10:
        c=cy(f"MATCH (:gene_protein{{name:'{g}'}})-[:drug_protein]-(d:drug) RETURN count(DISTINCT d) AS n")[0]["n"]  # nosec B608 — g comes from the fixed TCGA-LUAD top-10 query above, not external input (dead one-time script)
        if best is None or c>best[1]: best=(g,c)
    keep("q_paper_abbvie_02","Among the 10 most frequently mutated genes in TCGA-LUAD, which is targeted by the most drugs, and how many?","graph_multihop",{"gene":best[0],"drug_count":int(best[1])},"graph+lake")

    # karim_01: glioblastoma-assoc & >10% GBM (>=37 of 371)
    D="glioblastoma (disease)"
    gset=set(x["g"] for x in cy(f"MATCH (:disease{{name:\"{D}\"}})-[:disease_protein]-(g:gene_protein) RETURN DISTINCT g.name AS g"))
    gbm=set(r[0] for r in sql(f"SELECT hugo_symbol FROM {LAKE}.tcga_mutations WHERE project_id='TCGA-GBM' GROUP BY hugo_symbol HAVING count(DISTINCT case_id)>=37")[1:])  # nosec B608 — LAKE constant; 'TCGA-GBM' hardcoded (dead one-time script, see module docstring)
    inter=sorted(gset&gbm)
    keep("q_paper_karim_01","Which genes associated with glioblastoma are mutated in more than 10% of TCGA-GBM patients?","multi_source",{"genes":inter,"n":len(inter)},"graph+lake")

    # karim_02: breast cancer disease-assoc genes by drug count (top5)
    rows=cy("MATCH (dis:disease)-[:disease_protein]-(g:gene_protein)-[:drug_protein]-(dr:drug) WHERE toLower(dis.name) CONTAINS 'breast' RETURN g.name AS g, count(DISTINCT dr) AS n ORDER BY n DESC, g LIMIT 5")
    keep("q_paper_karim_02","For breast cancer, which associated genes are targeted by the most drugs? Give the top few with counts.","graph_multihop",{"top":[[x["g"],x["n"]] for x in rows]},"graph")

    json.dump(out, open("evaluation/golden_v2_papers.json","w"), indent=2, default=str)
    print(f"\n=== verified + wrote {len(out)} paper-grounded questions ===")
    print("DEFERRED (need work): bailey_02/sanchezvega_02/03/liu_02/primekg_03/abbvie_01/03/karim_03 — pathway-name or heavy-aggregation or 2-hop; next pass.")
except Exception as e:
    import traceback; traceback.print_exc()
