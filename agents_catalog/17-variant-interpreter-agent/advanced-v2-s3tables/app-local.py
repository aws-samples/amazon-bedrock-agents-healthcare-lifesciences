"""Streamlit UI for S3 Tables Variant Interpreter Agent - Local Mode."""

import os
import sys
import time

os.environ["BYPASS_TOOL_CONSENT"] = "true"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'agent'))

import streamlit as st
from strands import Agent
from strands.models import BedrockModel
from agent.tools.schema_tool import get_table_schema
from agent.tools.query_tool import execute_query, get_cohort_summary

st.set_page_config(page_title="Genomics Variant Analysis (Local)", page_icon="🧬", layout="wide")
st.markdown("<style>.stAppDeployButton{display:none;}#MainMenu{visibility:hidden;}</style>", unsafe_allow_html=True)

SYSTEM_PROMPT = """You are a genomics variant interpretation assistant. You query genomic variant data stored in S3 Tables via Amazon Athena.

WORKFLOW:
1. ALWAYS call get_table_schema first to understand the table structure
2. Generate SQL queries based on the schema and user question
3. Execute queries with execute_query
4. Interpret results with clinical genomics expertise

TABLE: variant_db_3.genomic_variants_fixed
PARTITION KEYS: sample_name, chrom
QUALITY FILTER: WHERE qual > 30 AND filter = 'PASS'
VEP CSQ in info['CSQ'] is pipe-delimited: Allele|Consequence|IMPACT|SYMBOL|Gene|...
"""


@st.cache_resource
def get_agent():
    model = BedrockModel(
        model_id=os.environ.get('BEDROCK_MODEL_ID', 'us.anthropic.claude-opus-4-6-v1'),
        region_name=os.environ.get('AWS_REGION', 'us-west-2'),
        streaming=True
    )
    return Agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        tools=[get_table_schema, execute_query, get_cohort_summary]
    )


def main():
    st.title("🧬 Genomics Variant Analysis (Local)")

    with st.sidebar:
        required = ['AWS_REGION', 'ATHENA_DATABASE', 'ATHENA_CATALOG', 'VEP_OUTPUT_BUCKET']
        missing = [v for v in required if not os.environ.get(v)]
        if missing:
            st.error(f"Missing: {', '.join(missing)}\nRun: `source .agent-config`")
        else:
            st.success("✅ Config loaded")
        st.caption(f"Region: {os.environ.get('AWS_REGION', 'N/A')}")
        st.caption(f"DB: {os.environ.get('ATHENA_DATABASE', 'N/A')}")

        if st.button("🗑️ Clear Chat"):
            st.session_state.messages = []
            st.rerun()

        st.divider()
        st.subheader("💡 Sample Questions")
        for i, q in enumerate([
            "How many samples are in the cohort?",
            "Show me PASS variants on chromosome 22",
            "What is the quality distribution?",
            "Show variants for sample HG00096 on chr22",
        ]):
            if st.button(f"📝 {q}", key=f"s_{i}", use_container_width=True):
                st.session_state["selected"] = q

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"], avatar="🧑‍⚕️" if msg["role"] == "user" else "🤖"):
            st.markdown(msg["content"])

    if "selected" in st.session_state:
        prompt = st.session_state.pop("selected")
        _process(prompt)
        st.rerun()

    if prompt := st.chat_input("Ask about genomic variants..."):
        _process(prompt)


def _process(prompt):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="🧑‍⚕️"):
        st.markdown(prompt)

    with st.chat_message("assistant", avatar="🤖"):
        placeholder = st.empty()
        start = time.time()
        try:
            agent = get_agent()
            with st.spinner("🔧 Thinking..."):
                result = agent(prompt)
            response = str(result)
        except Exception as e:
            response = f"❌ Error: {e}"
        placeholder.markdown(response)
        st.caption(f"⏱️ {time.time() - start:.1f}s")

    st.session_state.messages.append({"role": "assistant", "content": response})


if __name__ == "__main__":
    main()
