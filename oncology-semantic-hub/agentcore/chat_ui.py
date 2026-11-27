"""Oncology Semantic Hub — chat UI for the DEPLOYED AgentCore Runtime agents.

Talks to the live L3 (full hub: Neptune + Athena + OLS) and L1 (raw Athena lake, no map)
Runtime agents. Two modes:
  • Chat        — single layer (default L3), a normal assistant conversation.
  • Compare     — send the SAME prompt to L1 and L3 side-by-side; the headline
                  with/without-semantic-hub contrast, live.

AUTH: the runtimes were deployed by agentcore/deploy.py with NO authorizerConfiguration,
so they use AWS IAM (SigV4). This app therefore invokes them with the standard boto3
`bedrock-agentcore` client (invoke_agent_runtime) using your local AWS credentials —
the SAME path the eval scripts (run_l1_l3_compare.py / run_agentcore_eval.py) use. It does
NOT use the Cognito/OAuth bearer-token flow from agentcore_template/app_modules, which only
applies to runtimes deployed with a JWT authorizer.

Run:  ./.venv/bin/streamlit run agentcore/chat_ui.py
Prereq: agentcore/agent_config.json (L3) and agentcore/agent_config_l1.json (L1) present
        (written by deploy.py) + AWS credentials with bedrock-agentcore:InvokeAgentRuntime.
"""
from __future__ import annotations

import concurrent.futures
import json
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import boto3
import streamlit as st
from botocore.config import Config

_DIR = Path(__file__).parent
# real-time provenance metrics (compute + CloudWatch emit) live alongside this UI.
if str(_DIR) not in sys.path:
    sys.path.insert(0, str(_DIR))
from realtime_metrics import NAMESPACE, compute_realtime, emit_cloudwatch  # noqa: E402

# Layer -> config file. L3 = full semantic hub; L1 = raw data lake (no map).
_CONFIG_FILES = {
    "L3": _DIR / "agent_config.json",
    "L2": _DIR / "agent_config_l2.json",
    "L0-web": _DIR / "agent_config_l0-web.json",
    "L1": _DIR / "agent_config_l1.json",
}
_LAYER_DESC = {
    "L3": "Full semantic hub — Neptune KG + Athena lake + OLS ontology",
    "L2": "All raw data + KB — flat Athena (TCGA/cBioPortal/RODA/PrimeKG) + literature, no graph/OLS",
    "L0-web": "LLM + web search — AWS-managed Web Search Tool (no cohort data)",
    "L1": "Raw data lake — Athena SQL only, no semantic map",
    "L0": "Bare LLM — no tools/data, parametric knowledge only",
}

# L0 = bare LLM (no tools), same model as the hub, invoked directly via bedrock-runtime.
_L0_MODEL = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
_RESEARCH_DISCLAIMER = (
    "IMPORTANT — RESEARCH USE ONLY: You are a research and demonstration assistant operating on "
    "public, de-identified data (TCGA and curated open sources). Your output is NOT medical advice "
    "and must not be used for clinical diagnosis, treatment, or patient-care decisions. Do not "
    "infer the identity of any individual. Attribute facts to their source and do not fabricate "
    "data or citations.\n\n"
)
_L0_SYSTEM = _RESEARCH_DISCLAIMER + "You are an oncology research assistant. Answer the user's question."

# Clickable prompts = the EGFR/glioblastoma demo thread (docs/demo-golden-thread.md), in order.
# Bounded/comparable across L0·L1·L3; follow-ups rely on conversation memory.
_EXAMPLES = [  # 4 EGFR-GBM demo beats (v4 storyboard, 2026-08-06) — Q1-Q2: L2 vs L3, Q3-Q4: L0 vs L3
    "In our TCGA-GBM cohort, how many distinct genes are mutated? And separately, how many genes are known to be associated with glioblastoma as a disease? Give both numbers.",  # Q1 correctness: L2 166 vs L3 144 (MONDO)
    "How many distinct genes are associated with the type of cancer studied in the TCGA-GBM cohort?",  # Q2 reproducibility: L2 flips 166/12694, L3 stable 144
    "Is the co-occurrence of EGFR and PTEN mutations in TCGA-GBM statistically significant? Give the p-value.",  # Q3 groundedness: L0 fabricates vs L3 cohort table
    "EGFR is a key driver in glioblastoma. Which signaling pathways is EGFR part of, which OTHER genes in those pathways are also mutated in our TCGA-GBM cohort, and are any of them druggable? Cite sources.",  # Q4 multi-hop: L0 textbook vs L3 KB->KG->lake
]


@st.cache_resource
def _runtime_client(region: str):
    """One cached boto3 client per region (SigV4 via the local credential chain).

    Long read timeout: some L3 turns are multi-minute (e.g. the Q4 multi-hop traversal ~2 min,
    or hybrid recall→OLS→graph/SQL). The default 60s would time out mid-answer and the app-level
    retry (same session id) would then collide with the still-running request (ConcurrencyException).
    """
    return boto3.client("bedrock-agentcore", region_name=region,
                        config=Config(read_timeout=300, connect_timeout=15, retries={"max_attempts": 0}))


@st.cache_data
def _load_configs() -> dict:
    cfgs = {}
    for layer, path in _CONFIG_FILES.items():
        if path.exists():
            cfgs[layer] = json.loads(path.read_text())
    return cfgs


def _new_session_id() -> str:
    # AgentCore requires runtimeSessionId >= 33 chars.
    return uuid.uuid4().hex + uuid.uuid4().hex


def invoke_runtime(cfg: dict, prompt: str, session_id: str) -> str:
    """Invoke one deployed Runtime agent (SigV4) and return its text answer."""
    client = _runtime_client(cfg["region"])
    for attempt in range(4):
        try:
            r = client.invoke_agent_runtime(
                agentRuntimeArn=cfg["agent_arn"],
                runtimeSessionId=session_id,
                payload=json.dumps({"prompt": prompt}).encode(),
            )
            body = r["response"].read().decode() if hasattr(r["response"], "read") else r["response"]
            try:
                parsed = json.loads(body)
                if isinstance(parsed, str):
                    return parsed
                if isinstance(parsed, dict) and "answer" in parsed:
                    return parsed["answer"]
                return json.dumps(parsed, indent=2)
            except (json.JSONDecodeError, TypeError):
                return body
        except Exception as e:  # transient 500 / throttling — back off and retry
            if attempt == 3:
                return f"⚠️ Invocation failed after retries: {e}"
            time.sleep(3 * (attempt + 1))  # nosemgrep  (intentional sleep: external-API rate-limit/backoff or async-AWS poll)


@st.cache_resource
def _bedrock_runtime(region: str):
    return boto3.client("bedrock-runtime", region_name=region)


def invoke_l0(prompt: str, history: list, region: str) -> str:
    """L0 = bare LLM, no tools/data. Direct Bedrock converse; `history` gives conversation memory."""
    client = _bedrock_runtime(region)
    messages = list(history) + [{"role": "user", "content": [{"text": prompt}]}]
    try:
        r = client.converse(modelId=_L0_MODEL, system=[{"text": _L0_SYSTEM}], messages=messages,
                            inferenceConfig={"temperature": 0.0, "maxTokens": 800})
        return "".join(b.get("text", "") for b in r["output"]["message"]["content"]).strip()
    except Exception as e:  # noqa: BLE001
        return f"⚠️ L0 error: {e}"


def _render_metrics(answer: str, layer: str, region: str, *, emit: bool,
                    invoked_at: "datetime | None" = None, model: "str | None" = None) -> dict:
    """Compute + display the real-time provenance metrics for one answer, and optionally emit
    them to CloudWatch with the agent-invocation timestamp (mode='realtime').

    Two metrics, computed from the answer's provenance tags alone (no ground truth, no extra
    LLM call): provenance-faithfulness (attribution honesty) + grounding_rate (tool-backed share).
    Emission is best-effort — the display always renders even if CloudWatch is unavailable.
    """
    m = compute_realtime(answer, layer)
    if m["n_tags"] == 0:
        st.caption("🔎 No provenance tags in this answer — real-time metrics unauditable.")
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric(
            "Provenance-faithfulness", f"{m['provenance_faithfulness']:.2f}",
            help="Layer-aware attribution honesty: 1.0 = every source tag is one this layer's "
                 "tools can actually produce. Below 1.0 = fabricated grounding.")
        c2.metric(
            "Grounding rate", f"{m['grounding_rate']:.2f}",
            help="Fraction of tags that are tool-retrieved vs [Model knowledge]/[Recalled]. "
                 "Low is not unfaithful — honest use of model memory is fine.")
        c3.metric("Provenance tags", m["n_tags"])
        if m["fabricated"]:
            st.warning(
                f"⚠️ Fabricated grounding: answer claimed {', '.join(m['fabricated'])} — "
                f"not in {layer}'s tool inventory.")
    if emit and m["n_tags"] > 0:
        res = emit_cloudwatch(m, layer=layer, mode="realtime",
                              timestamp=invoked_at or datetime.now(timezone.utc),
                              region=region, model=model)
        if res.get("emitted"):
            st.caption(f"📈 Emitted {res['emitted']} metric(s) → CloudWatch · {NAMESPACE} · Mode=realtime")
        elif res.get("error"):
            st.caption(f"📈 CloudWatch emit skipped: {res['error']}")
    elif emit:
        st.caption("📈 CloudWatch emit skipped: no provenance tags (unauditable).")
    return m


def _init_state():
    if "session_id" not in st.session_state:
        st.session_state.session_id = _new_session_id()
    if "l0_history" not in st.session_state:
        st.session_state.l0_history = []  # L0 bare-LLM conversation memory (converse messages)
    if "compare_sids" not in st.session_state:
        # Persistent per-layer session ids so Compare mode keeps conversation memory across
        # questions (each layer chains its own context; L1 and L3 stay independent of each other).
        st.session_state.compare_sids = {"L0-web": _new_session_id(), "L1": _new_session_id(), "L2": _new_session_id(), "L3": _new_session_id()}
    if "messages" not in st.session_state:
        st.session_state.messages = []  # chat-mode history: [{role, content, layer, elapsed}]


def main():
    st.set_page_config(page_title="Oncology Semantic Hub", page_icon="🧬", layout="wide")
    _init_state()
    cfgs = _load_configs()

    st.title("🧬 Oncology Semantic Hub")
    st.caption("Chat with the deployed AgentCore Runtime agents (IAM/SigV4).")
    st.warning(
        "⚠️ **Research use only — not medical advice.** This demo runs on public, de-identified "
        "TCGA data for research and demonstration. Outputs (including any drug, evidence-level, or "
        "treatment-related answers) must not be used for clinical diagnosis, treatment, or "
        "patient-care decisions, and require qualified clinical review before informing any such "
        "decision. See the README's Known Limitations section for details.",
        icon="⚠️",
    )

    if not cfgs:
        st.error(
            "No agent config found. Deploy first:\n\n"
            "`python agentcore/deploy.py --layer L3` and `--layer L1`\n\n"
            "That writes `agentcore/agent_config.json` and `agentcore/agent_config_l1.json`."
        )
        st.stop()

    with st.sidebar:
        st.header("Settings")
        mode = st.radio(
            "Mode",
            ["Chat (single layer)", "Compare (L3 + toggles)"],
            help="Compare shows L3 always, with L0 and/or L1 beside it (pick two for a clean 2-up).",
        )

        available = list(cfgs.keys())
        include_l0 = include_l1 = include_l2 = include_l0web = False
        if mode.startswith("Chat"):
            layer = st.selectbox("Layer", available, index=available.index("L3") if "L3" in available else 0)
            st.caption(_LAYER_DESC.get(layer, ""))
        else:
            if "L3" not in cfgs:
                st.warning("Compare needs the L3 config (agent_config.json).")
            st.caption("**L3 is always shown.** Toggle a comparison column (two columns is best):")
            include_l0 = st.checkbox(
                "L0 — bare LLM (trust lens)", value=True,
                help="Same model, no tools/data — shows the grounding/trust value (L0 vs L3).")
            include_l0web = st.checkbox(
                "L0-web — LLM + web search (grounding lens)", value=False,
                help="Web-grounded but no cohort data — shows what web search alone can do vs the full hub.",
                disabled=("L0-web" not in cfgs))
            include_l1 = st.checkbox(
                "L1 — raw data lake (rigor lens)", value=False,
                help="Athena SQL only — shows the semantic-layer value (L1 vs L3).",
                disabled=("L1" not in cfgs))
            include_l2 = st.checkbox(
                "L2 — all raw data + KB (apples-to-apples lens)", value=True,
                help="Same data as L3 (flat TCGA/cBioPortal/RODA/PrimeKG + literature) but no graph/OLS — "
                     "isolates the semantic-layer value (L2 vs L3).",
                disabled=("L2" not in cfgs))

        st.divider()
        st.subheader("Live metrics")
        show_metrics = st.checkbox(
            "Show provenance metrics", value=True,
            help="Compute provenance-faithfulness + grounding_rate from each answer in real time "
                 "(no ground truth, no extra model call).")
        emit_cw = st.checkbox(
            "Emit to CloudWatch (real-time)", value=False,
            help="Publish each response's metrics to CloudWatch (AgentCore observability) with the "
                 "invocation timestamp. Needs cloudwatch:PutMetricData on your credentials.")

        st.divider()
        st.subheader("Example questions")
        for ex in _EXAMPLES:
            if st.button(ex, key=f"ex_{ex}", use_container_width=True):
                st.session_state.pending_prompt = ex

        st.divider()
        for layer_name, cfg in cfgs.items():
            st.caption(f"**{layer_name}** · `{cfg['agent_id']}` · {cfg['region']}")
        if st.button("🔄 New conversation", use_container_width=True):
            st.session_state.session_id = _new_session_id()
            st.session_state.compare_sids = {"L0-web": _new_session_id(), "L1": _new_session_id(), "L2": _new_session_id(), "L3": _new_session_id()}
            st.session_state.l0_history = []
            st.session_state.messages = []
            st.rerun()

    # replay history (chat mode)
    if mode.startswith("Chat"):
        for m in st.session_state.messages:
            with st.chat_message(m["role"]):
                st.markdown(m["content"])
                if m.get("elapsed") is not None:
                    st.caption(f"⏱️ {m['elapsed']:.1f}s · {m.get('layer','')}")

    prompt = st.chat_input("Ask about genes, drugs, diseases, ontology ids, or TCGA patient data…")
    if not prompt and "pending_prompt" in st.session_state:
        prompt = st.session_state.pop("pending_prompt")

    if not prompt:
        return

    if mode.startswith("Chat"):
        _handle_chat(cfgs[layer], layer, prompt, show_metrics=show_metrics, emit_cw=emit_cw)
    else:
        _handle_compare(cfgs, prompt, include_l0, include_l0web, include_l1, include_l2,
                        show_metrics=show_metrics, emit_cw=emit_cw)


def _handle_chat(cfg: dict, layer: str, prompt: str, *, show_metrics: bool = True, emit_cw: bool = False):
    st.session_state.messages.append({"role": "user", "content": prompt, "elapsed": None})
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        with st.spinner(f"Querying {layer} agent…"):
            invoked_at = datetime.now(timezone.utc)  # agent-invocation timestamp (real-time metric ts)
            t0 = time.time()
            answer = invoke_runtime(cfg, prompt, st.session_state.session_id)
            elapsed = time.time() - t0
        st.markdown(answer)
        st.caption(f"⏱️ {elapsed:.1f}s · {layer}")
        if show_metrics:
            _render_metrics(answer, layer, cfg.get("region", "us-west-2"),
                            emit=emit_cw, invoked_at=invoked_at, model=cfg.get("subject_model"))
    st.session_state.messages.append(
        {"role": "assistant", "content": answer, "layer": layer, "elapsed": elapsed}
    )


def _handle_compare(cfgs: dict, prompt: str, include_l0: bool = True, include_l0web: bool = False,
                    include_l1: bool = False, include_l2: bool = False, *,
                    show_metrics: bool = True, emit_cw: bool = False):
    if "L3" not in cfgs:
        st.error("Compare mode needs the L3 config (agent_config.json).")
        return
    st.markdown(f"**Question:** {prompt}")
    sids = st.session_state.compare_sids
    region = cfgs["L3"].get("region", "us-west-2")
    l0_hist = list(st.session_state.l0_history)

    layers = (["L0"] if include_l0 else []) + (["L0-web"] if (include_l0web and "L0-web" in cfgs) else []) + (["L1"] if (include_l1 and "L1" in cfgs) else []) + (["L2"] if (include_l2 and "L2" in cfgs) else []) + ["L3"]

    def run(layer):
        invoked_at = datetime.now(timezone.utc)
        t0 = time.time()
        if layer == "L0":
            ans = invoke_l0(prompt, l0_hist, region)
        else:
            ans = invoke_runtime(cfgs[layer], prompt, sids[layer])
        return ans, time.time() - t0, invoked_at

    with st.spinner(f"Querying {' · '.join(layers)} in parallel…"):
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(layers)) as ex:
            futs = {layer: ex.submit(run, layer) for layer in layers}
            results = {layer: f.result() for layer, f in futs.items()}

    if include_l0:
        st.session_state.l0_history.append({"role": "user", "content": [{"text": prompt}]})
        st.session_state.l0_history.append({"role": "assistant", "content": [{"text": results["L0"][0]}]})

    titles = {"L0": "L0 — bare LLM (no data)", "L0-web": "L0-web — LLM + web search", "L1": "L1 — raw data lake", "L2": "L2 — all raw data + KB", "L3": "L3 — full semantic hub"}
    cols = st.columns(len(layers))
    for col, layer in zip(cols, layers):
        with col:
            st.subheader(titles[layer])
            st.caption(_LAYER_DESC[layer])
            ans, el, invoked_at = results[layer]
            st.markdown(ans)
            st.caption(f"⏱️ {el:.1f}s")
            if show_metrics:
                model = None if layer == "L0" else cfgs.get(layer, {}).get("subject_model")
                _render_metrics(ans, layer, region, emit=emit_cw, invoked_at=invoked_at, model=model)


if __name__ == "__main__":
    main()
