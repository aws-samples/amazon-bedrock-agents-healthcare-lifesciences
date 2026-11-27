#!/usr/bin/env python3
"""Re-runnable verification for the hybrid-search capability.

Independent of the agent's own claims: it checks the deployed L3 runtime end-to-end and asserts the
answers are grounded. Two guarantees are tested:
  * NO FABRICATION — every cited PubMed PMID / TCGA project id is a real document in the ingested
    corpus (set membership against the local metadata sidecars).
  * GROUNDED IN RECALL — for the evidence question, a majority of the cited PMIDs also appear in a
    direct `Retrieve` for that question (i.e. the model cited what recall surfaced, not memory).

Rebuild the corpus + KB first if stale: `build_corpus.py` then `create_kb.py`.

Usage: python agentcore/kb/hybrid_check.py    (exit 0 = all pass, 1 = a failure)
"""
import json
import re
import sys
import time
import uuid
from pathlib import Path

import boto3
from botocore.config import Config

_DIR = Path(__file__).parent
_CORPUS = _DIR / "corpus"
_CFG = json.loads((_DIR.parent / "agent_config.json").read_text())
_REGION = _CFG["region"]
# Long read timeout: some L3 turns are multi-minute; the default 60s would time out and the retry
# would collide with the still-running request (ConcurrencyException). Retries off (we retry in-code).
_rtcfg = Config(read_timeout=300, connect_timeout=15, retries={"max_attempts": 0})
_rt = boto3.client("bedrock-agentcore", region_name=_REGION, config=_rtcfg)
_kbrt = boto3.client("bedrock-agent-runtime", region_name=_REGION)
_ssm = boto3.client("ssm", region_name=_REGION)

# "PMID:12345", "PMID 12345", and URL form pubmed.ncbi.nlm.nih.gov/12345
PMID_RE = re.compile(r"(?:PMID[:\s]*|pubmed\.ncbi\.nlm\.nih\.gov/)(\d+)", re.IGNORECASE)
# Project ids only (avoid TCGA barcodes like TCGA-AB-2802): no trailing '-'.
TCGA_RE = re.compile(r"\bTCGA-[A-Z]{2,5}\b(?!-)")


def corpus_ids():
    pmids, projects = set(), set()
    for meta in _CORPUS.glob("*.metadata.json"):
        attrs = json.loads(meta.read_text()).get("metadataAttributes", {})
        if attrs.get("source") == "PubMed" and attrs.get("pmid"):
            pmids.add(str(attrs["pmid"]))
        elif attrs.get("source") == "TCGA" and attrs.get("project_id"):
            projects.add(attrs["project_id"])
    return pmids, projects


def retrieve_pmids(query, k=20):
    """PMIDs a direct KB Retrieve surfaces for a query (grounding reference)."""
    kb_id = _ssm.get_parameter(Name="/app/oncology-hub/knowledge_base/kb_id")["Parameter"]["Value"]
    resp = _kbrt.retrieve(knowledgeBaseId=kb_id, retrievalQuery={"text": query},
                          retrievalConfiguration={"vectorSearchConfiguration": {"numberOfResults": k}})
    out = set()
    for it in resp.get("retrievalResults", []):
        md = it.get("metadata", {}) or {}
        if md.get("source") == "PubMed" and md.get("pmid"):
            out.add(str(md["pmid"]))
    return out


def invoke(prompt, sid=None):
    sid = sid or (uuid.uuid4().hex + uuid.uuid4().hex)
    for attempt in range(4):
        try:
            r = _rt.invoke_agent_runtime(
                agentRuntimeArn=_CFG["agent_arn"], runtimeSessionId=sid,
                payload=json.dumps({"prompt": prompt}).encode())
            b = r["response"].read().decode() if hasattr(r["response"], "read") else r["response"]
            try:
                t = json.loads(b)
                return t if isinstance(t, str) else json.dumps(t)
            except (json.JSONDecodeError, TypeError):
                return b
        except Exception as e:  # noqa: BLE001
            if attempt == 3:
                return f"INVOKE_ERROR: {e}"
            time.sleep(3 * (attempt + 1))  # nosemgrep  (intentional sleep: external-API rate-limit/backoff or async-AWS poll)


def _answered(ans):
    """A usable answer (not a transport error)."""
    return bool(ans) and not ans.startswith("INVOKE_ERROR")


def main():
    if not _CORPUS.exists() or not list(_CORPUS.glob("*.metadata.json")):
        print("ERROR: local corpus metadata missing — run build_corpus.py first.", file=sys.stderr)
        sys.exit(1)
    pmids, projects = corpus_ids()
    print(f"Corpus ground truth: {len(pmids)} PubMed PMIDs, {len(projects)} TCGA projects")
    print(f"Runtime: {_CFG['agent_arn']}\n")

    results = []  # (name, passed, detail)

    # 1. Study discovery over TCGA descriptions → expect GBM + LGG, only real projects.
    a1 = invoke("I'm researching EGFR-driven glioma and resistance. Which of our TCGA cohorts are "
                "most relevant? Use the knowledge base.")
    if not _answered(a1):
        results.append(("study-discovery invoked", False, "INVOKE_ERROR"))
    else:
        cited = set(TCGA_RE.findall(a1))
        results.append(("study-discovery surfaces TCGA-GBM & TCGA-LGG",
                        {"TCGA-GBM", "TCGA-LGG"} <= cited, f"cited={sorted(cited)}"))
        results.append(("study-discovery cites only real TCGA projects",
                        bool(cited) and not (cited - projects), f"bogus={sorted(cited - projects)}"))

    # 2. Evidence question → cited PMIDs real AND grounded in recall (fresh session).
    q_evi = "What is the published evidence on resistance to EGFR-targeted therapy in glioblastoma? Cite specific PMIDs."
    a2 = invoke(q_evi)
    if not _answered(a2):
        results.append(("evidence answer invoked", False, "INVOKE_ERROR"))
    else:
        cited = set(PMID_RE.findall(a2))
        results.append(("evidence answer cites >=3 PMIDs", len(cited) >= 3, f"n={len(cited)}"))
        results.append(("all cited PMIDs exist in corpus (no fabrication)",
                        bool(cited) and not (cited - pmids), f"fabricated={sorted(cited - pmids)}"))
        retrieved = retrieve_pmids(q_evi, k=20)
        overlap = len(cited & retrieved)
        results.append(("majority of cited PMIDs are grounded in KB recall",
                        bool(cited) and overlap >= (len(cited) + 1) // 2,
                        f"{overlap}/{len(cited)} in top-20 retrieve"))

    # 3. Checkpoint-resistance recall → cited PMIDs real (fresh session).
    a3 = invoke("Summarize evidence on immune-checkpoint inhibitor resistance and cite PMIDs.")
    if not _answered(a3):
        results.append(("checkpoint-resistance invoked", False, "INVOKE_ERROR"))
    else:
        c3 = set(PMID_RE.findall(a3))
        results.append(("checkpoint-resistance cites >=1 real PMID, none fabricated",
                        bool(c3) and not (c3 - pmids), f"n={len(c3)} fabricated={sorted(c3 - pmids)}"))

    # 4. Grounded refusal → no fabricated citation for an off-corpus topic (fresh session).
    a4 = invoke("What does our knowledge base say about CAR-T therapy for pediatric neuroblastoma? "
                "Cite PMIDs only if present.")
    if not _answered(a4):
        results.append(("off-topic query invoked", False, "INVOKE_ERROR"))
    else:
        c4 = set(PMID_RE.findall(a4))
        results.append(("off-topic query fabricates no PMIDs", not (c4 - pmids),
                        f"cited={sorted(c4)} fabricated={sorted(c4 - pmids)}"))

    print("── Checks ──")
    ok = True
    for name, passed, detail in results:
        print(f"  [{'PASS' if passed else 'FAIL'}] {name}  ({detail})")
        ok = ok and passed
    print(f"\n{'ALL PASS' if ok else 'FAILURES PRESENT'}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
