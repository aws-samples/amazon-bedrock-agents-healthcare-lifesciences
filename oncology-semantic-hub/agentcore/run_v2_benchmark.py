#!/usr/bin/env python
"""
Run the L2-vs-L3 benchmark on the v2 dataset (evaluation/golden_v2.json).

Scores each answer on TWO axes (per docs/benchmark-v2-plan.md):
  - correctness: structured-GT match (numeric value / gene-set coverage / top-gene / calibrated abstention)
  - groundedness: did the answer cite a tool/source (`[OLS]`/`[Graph]`/`[PrimeKG-flat]`/`[Lake]`/`[RODA]`) vs
    an ungrounded parametric claim ("from my general knowledge") — the L3-vs-L2 faithfulness axis.
Aggregates by `requires` tag and layer. Supports N runs (mean solve-count = expected correctness + reproducibility).

Usage: ./.venv/bin/python agentcore/run_v2_benchmark.py [--layers L2,L3] [--runs 1] [--workers 6] [--limit N] [--ids ...]
"""
import argparse, json, re, time, uuid, concurrent.futures, threading, sys as _sys
from pathlib import Path
import boto3
from botocore.config import Config
_sys.path.insert(0, str(Path(__file__).resolve().parent))  # allow `import realtime_metrics` under `python -m` too
from realtime_metrics import NAMESPACE, compute_realtime, emit_cloudwatch  # same metric defs as real-time
_DIR=Path(__file__).resolve().parent
GOLD=_DIR.parent/"ground_truth"/"golden_v2.json"
def _cfg_path(layer, suf):
    return _DIR/(f"agent_config_{layer.lower()}{suf}.json" if (layer!="L3" or suf) else "agent_config.json")
CFG={}; rt=None  # populated in main() once --layers/--suffix are known

def invoke(layer,prompt):
    sid=uuid.uuid4().hex+uuid.uuid4().hex
    try:
        r=rt.invoke_agent_runtime(agentRuntimeArn=CFG[layer]["agent_arn"],runtimeSessionId=sid,payload=json.dumps({"prompt":prompt}).encode())
        b=r["response"].read().decode()
        try: p=json.loads(b)
        except Exception: return b,{}
        if isinstance(p,dict) and "answer" in p:       # new structured response (answer + usage)
            return p["answer"],(p.get("usage") or {})
        return (p if isinstance(p,str) else json.dumps(p)),{}   # backward-compat: plain-string runtime
    except Exception as e: return f"INVOKE_ERROR:{e}",{}

def score_correct(ideal,ans):
    if not isinstance(ans,str): ans=str(ans)
    A=ans
    if ideal.get("answer")=="cannot_determine":
        return 1.0 if re.search(r"cannot|unable|not determine|does not have|no such|absent|no .*(evidence|actionability|data|record|entry|information|stage|survival|imaging|abundance|proteom)|not (present|available|found|recorded|captured|in the)|isn't (present|available)",A,re.I) else 0.0
    if "expect_terms" in ideal:
        ts=ideal["expect_terms"]
        return round(sum(1 for t in ts if re.search(re.escape(t),A,re.I))/len(ts),3) if ts else None
    if "correct_mondo" in ideal:
        return 1.0 if (ideal["correct_mondo"] in A or re.search(r"low[- ]grade glioma",A,re.I)) else 0.0
    if "cite_pmid_from" in ideal or any(k.endswith(("_connected","_associated")) for k in ideal):
        checks=[]
        for k,v in ideal.items():
            if k.endswith("_patients"): checks.append(str(v) in re.findall(r'\d+',A))
        pm=ideal.get("cite_pmid_from",[])
        if pm: checks.append(any(str(p) in A for p in pm))
        checks.append(bool(re.search(r"yes|associat|connect|linked|is a (known )?(mechanism|resistance)|confers",A,re.I)))
        return round(sum(1 for c in checks if c)/len(checks),3) if checks else None
    if "genes" in ideal:
        gt=[g for g in ideal["genes"]]
        if not gt: return 1.0 if re.search(r"none|no genes|not found|zero",A,re.I) else 0.0
        present=sum(1 for g in gt if re.search(r'\b'+re.escape(g)+r'\b',A,re.I))
        recall=present/len(gt)
        mentioned=set(re.findall(r'\b[A-Z][A-Z0-9]{1,7}\b',A))-{"TCGA","PMID","KB","OLS","SQL","GBM","BRCA","LUAD","COAD","SKCM","PRAD","LGG","LUSC","DNA","RNA","MONDO","HGNC","CIVIC","FDA","NCI","CNA","MRNA","AND","THE","FOR","WITH"}
        prec=(present/len(mentioned)) if mentioned else (1.0 if present else 0.0)
        return round(2*prec*recall/(prec+recall),3) if (prec+recall)>0 else 0.0
    if "top" in ideal and ideal["top"]:
        gene,cnt=str(ideal["top"][0][0]),str(ideal["top"][0][1])
        hasg=bool(re.search(r'\b'+re.escape(gene)+r'\b',A,re.I)); hasc=cnt in re.findall(r'\d+',A)
        return 1.0 if (hasg and hasc) else (0.5 if hasg else 0.0)
    for k in ("n_patients","drug_count","n_associated_genes","n_indications","n_genes_within_2_ppi_steps","n"):
        if k in ideal: return 1.0 if str(ideal[k]) in re.findall(r'\d+',A) else 0.0
    return None

def score_ground(ans):
    if not isinstance(ans,str): ans=str(ans)
    tags=[t.strip("[") for t in ["[OLS","[Graph]","[PrimeKG-flat","[Lake","[RODA","[KB"] if t in ans]
    ung=bool(re.search(r"general knowledge|from my (own )?knowledge|don't have (access|an ontology)|no ontology service|based on my knowledge",ans,re.I))
    return (1.0 if (tags and not ung) else (0.0 if ung else 0.3)), tags, ung

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--layers",default="L2,L3"); ap.add_argument("--runs",type=int,default=1)
    ap.add_argument("--workers",type=int,default=6); ap.add_argument("--limit",type=int); ap.add_argument("--ids",nargs="*")
    ap.add_argument("--requires",default=None,help="comma-separated requires tags to include")
    ap.add_argument("--suffix",default="",help="agent_config suffix to target (e.g. 'qwen' -> agent_config_l3_qwen.json)")
    ap.add_argument("--emit-metrics",action="store_true",help="emit per-layer batch metrics to CloudWatch (mode=batch, timestamp=batch-job time)")
    a=ap.parse_args(); LAYERS=tuple(a.layers.split(","))
    SUF=("_"+a.suffix) if a.suffix else ""
    global CFG, rt
    CFG={L:json.loads(_cfg_path(L,SUF).read_text()) for L in LAYERS if _cfg_path(L,SUF).exists()}
    missing=[L for L in LAYERS if L not in CFG]
    if missing: raise SystemExit(f"missing agent_config for {missing} (suffix={a.suffix!r}); deploy those layers first")
    rt=boto3.client("bedrock-agentcore",region_name=CFG[LAYERS[0]]["region"],config=Config(read_timeout=400,connect_timeout=15,retries={"max_attempts":0}))
    print(f"Layers: {LAYERS}  suffix: {a.suffix or '(none)'}  model-configs: {[_cfg_path(L,SUF).name for L in LAYERS]}")
    gold=json.loads(GOLD.read_text())
    if a.ids: gold=[q for q in gold if q["id"] in set(a.ids)]
    elif a.requires: gold=[q for q in gold if q["requires"] in set(a.requires.split(","))]
    elif a.limit: gold=gold[:a.limit]
    outp=_DIR/"v2_benchmark_results.json"; results=[]; lock=threading.Lock()
    def do(q):
        row={"id":q["id"],"requires":q["requires"],"question":q["question"],"layers":{}}
        for L in LAYERS:
            runs=[]; lat=[]; toks=[]
            for _ in range(a.runs):
                _t0=time.time(); ans,usage=invoke(L,q["question"]); lat.append(round((time.time()-_t0)*1000)); runs.append(ans); toks.append(usage or {})
            cs=[score_correct(q["ideal"],x) for x in runs]; cs=[c for c in cs if c is not None]
            gs=[score_ground(x) for x in runs]
            rt_m=[compute_realtime(x,L) for x in runs]  # canonical real-time metrics (== dashboard defs)
            pf=[r["provenance_faithfulness"] for r in rt_m if r["provenance_faithfulness"] is not None]  # skip unauditable
            gr=[r["grounding_rate"] for r in rt_m if r["grounding_rate"] is not None]
            solved=[1.0 if c>=0.8 else 0.0 for c in cs]
            _tt=[t.get("total_tokens") for t in toks if t.get("total_tokens") is not None]
            _it=[t.get("input_tokens") for t in toks if t.get("input_tokens") is not None]
            _ot=[t.get("output_tokens") for t in toks if t.get("output_tokens") is not None]
            row["layers"][L]={"mean_correct":round(sum(cs)/len(cs),3) if cs else None,
                              "mean_coverage":round(sum(cs)/len(cs),3) if cs else None,
                              "mean_ground":round(sum(g[0] for g in gs)/len(gs),3),  # legacy score_ground heuristic (kept for continuity)
                              "mean_provfaith":round(sum(pf)/len(pf),3) if pf else None,
                              "mean_grounding_rate":round(sum(gr)/len(gr),3) if gr else None,  # provenance-based (matches real-time)
                              "mean_latency_ms":round(sum(lat)/len(lat)) if lat else None,
                              "latency_ms":lat,
                              "mean_total_tokens":round(sum(_tt)/len(_tt)) if _tt else None,
                              "mean_input_tokens":round(sum(_it)/len(_it)) if _it else None,
                              "mean_output_tokens":round(sum(_ot)/len(_ot)) if _ot else None,
                              "tokens":toks,
                              "solve_count":f"{sum(solved):.0f}/{len(solved)}" if solved else "n/a",
                              "answers":runs}
        return row
    with concurrent.futures.ThreadPoolExecutor(max_workers=a.workers) as ex:
        futs={ex.submit(do,q):q for q in gold}
        for fut in concurrent.futures.as_completed(futs):
            r=fut.result()
            with lock:
                results.append(r); json.dump({"results":results},open(outp,"w"),indent=2,default=str)
                cells=" ".join(f"{L}[c={r['layers'][L]['mean_correct']} g={r['layers'][L]['mean_ground']}]" for L in LAYERS)
                print(f"[{len(results)}/{len(gold)}] {r['id']:<14} {r['requires']:<14} {cells}",flush=True)
    # aggregate by requires x layer
    from collections import defaultdict
    agg=defaultdict(lambda:{L:{"c":[],"g":[],"pf":[],"gr":[]} for L in LAYERS})
    for r in results:
        for L in LAYERS:
            d=r["layers"][L]
            if d["mean_correct"] is not None: agg[r["requires"]][L]["c"].append(d["mean_correct"])
            agg[r["requires"]][L]["g"].append(d["mean_ground"])
            if d.get("mean_provfaith") is not None: agg[r["requires"]][L]["pf"].append(d["mean_provfaith"])
            if d.get("mean_grounding_rate") is not None: agg[r["requires"]][L]["gr"].append(d["mean_grounding_rate"])
    print("\n=== correctness / groundedness / prov-faithfulness by requires (L2 -> L3) ===")
    def m(x): return round(sum(x)/len(x),3) if x else None
    tot={L:{"c":[],"g":[],"pf":[],"gr":[]} for L in LAYERS}
    for req,v in sorted(agg.items()):
        line=f"  {req:<16} "
        for L in LAYERS:
            line+=f"{L}: c={m(v[L]['c'])} g={m(v[L]['g'])} pf={m(v[L]['pf'])}   "
            tot[L]["c"]+=v[L]["c"]; tot[L]["g"]+=v[L]["g"]; tot[L]["pf"]+=v[L]["pf"]; tot[L]["gr"]+=v[L]["gr"]
        print(line)
    print("  "+"-"*60)
    print("  TOTAL            "+"   ".join(f"{L}: c={m(tot[L]['c'])} g={m(tot[L]['g'])} pf={m(tot[L]['pf'])}" for L in LAYERS))
    import datetime as _dt
    job_ts=_dt.datetime.now(_dt.timezone.utc)  # batch-job timestamp (used for run_meta AND CloudWatch emission)
    run_meta={"run_id":uuid.uuid4().hex[:12],
              "timestamp_utc":job_ts.isoformat(),
              "layers":list(LAYERS),"suffix":(a.suffix or None),"runs":a.runs,
              "n_questions":len(gold),"region":CFG[LAYERS[0]]["region"],
              "models":{L:CFG[L].get("subject_model") for L in LAYERS}}
    json.dump({"run":run_meta,
               "by_requires":{k:{L:{"correct":m(v[L]['c']),"ground":m(v[L]['g']),"grounding_rate":m(v[L]['gr']),"provenance_faithfulness":m(v[L]['pf'])} for L in LAYERS} for k,v in agg.items()},
               "total":{L:{"correct":m(tot[L]['c']),"ground":m(tot[L]['g']),"grounding_rate":m(tot[L]['gr']),"provenance_faithfulness":m(tot[L]['pf'])} for L in LAYERS},"results":results},open(outp,"w"),indent=2,default=str)
    print(f"\nWrote {outp}  [run {run_meta['run_id']} @ {run_meta['timestamp_utc']}  models={run_meta['models']}]")

    if a.emit_metrics:
        # Emit per-layer aggregate batch metrics to CloudWatch (AgentCore observability) with the
        # BATCH-JOB timestamp (contrast: the real-time path uses the invocation time). GroundingRate
        # is the provenance-based mean (identical definition to real-time), NOT the legacy score_ground
        # heuristic. RunId is intentionally NOT a dimension (it would explode metric cardinality); it
        # lives in run_meta / the results JSON instead.
        region=CFG[LAYERS[0]]["region"]; emitted=0
        for L in LAYERS:
            metrics={"correctness":m(tot[L]["c"]), "grounding_rate":m(tot[L]["gr"]),
                     "provenance_faithfulness":m(tot[L]["pf"])}
            res=emit_cloudwatch(metrics, layer=L, mode="batch", timestamp=job_ts, region=region,
                                model=CFG[L].get("subject_model"))
            emitted+=res.get("emitted",0)
            if res.get("error"): print(f"  [emit-metrics] {L}: {res['error']}")
        print(f"[emit-metrics] published {emitted} batch metric(s) to CloudWatch · {NAMESPACE} · Mode=batch · run={run_meta['run_id']} @ {job_ts.isoformat()}")

if __name__=="__main__": main()
