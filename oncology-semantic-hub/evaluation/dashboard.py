"""Semantic Hub Validation Framework — results dashboard.

Run: streamlit run evaluation/dashboard.py
"""
import glob
import json
import os

import pandas as pd
import streamlit as st

RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
DEFAULT_FILE = "pilot_results.json"

st.set_page_config(page_title="Semantic Hub Validation", layout="wide")


@st.cache_data(show_spinner=False)
def load_results(path):
    with open(path) as f:
        return json.load(f)


def pct(v):
    """Summary stores fractions in [0,1]; render as a percentage."""
    return "-" if v is None else f"{float(v) * 100:.1f}%"


def list_result_files():
    files = sorted(glob.glob(os.path.join(RESULTS_DIR, "*.json")))
    return [os.path.basename(p) for p in files]


# ---------------------------------------------------------------- sidebar
st.sidebar.title("Semantic Hub Validation")
available = list_result_files()
options = available or [DEFAULT_FILE]
default_idx = options.index(DEFAULT_FILE) if DEFAULT_FILE in options else 0
chosen = st.sidebar.selectbox("Results file", options, index=default_idx)
chosen_path = os.path.join(RESULTS_DIR, chosen)

if not os.path.exists(chosen_path):
    st.error(f"Results file not found: {chosen_path}")
    st.stop()

data = load_results(chosen_path)
questions = data.get("questions", [])
summary = data.get("summary", {})
layers = list(summary.keys()) or ["L0", "L3"]

# ---------------------------------------------------------------- filters
cats = sorted({q.get("category", "?") for q in questions})
atypes = sorted({q.get("answer_type", "?") for q in questions})
sel_cats = st.sidebar.multiselect("Category", cats, default=cats)
sel_atypes = st.sidebar.multiselect("Answer type", atypes, default=atypes)

fq = [
    q for q in questions
    if q.get("category") in sel_cats and q.get("answer_type") in sel_atypes
]

# ---------------------------------------------------------------- header
st.title("Validation Results")
st.caption(f"{os.path.basename(chosen_path)} — {len(fq)} of {len(questions)} questions shown")

meta = data.get("meta", {})
if meta:
    with st.expander("Run metadata"):
        st.json(meta)

# ---------------------------------------------------------------- (1) cards
st.subheader("Headline metrics")
cols = st.columns(max(len(layers), 1))
for col, layer in zip(cols, layers):
    s = summary.get(layer, {})
    col.metric(f"{layer} Correctness", pct(s.get("correctness_pct")))
    col.metric(f"{layer} Reproducibility", pct(s.get("reproducibility_pct")))
    col.metric(f"{layer} Mean latency", f"{s.get('mean_elapsed_sec', 0):.2f}s")

# ---------------------------------------------------------------- 2x2 grid
st.subheader("Correctness vs Reproducibility by layer")
grid = pd.DataFrame(
    {
        "Correctness %": [100 * summary.get(l, {}).get("correctness_pct", 0) for l in layers],
        "Reproducibility %": [100 * summary.get(l, {}).get("reproducibility_pct", 0) for l in layers],
    },
    index=layers,
)
st.dataframe(grid.style.format("{:.1f}"), width="stretch")
st.bar_chart(grid)

# ---------------------------------------------------------------- (2) per-category
st.subheader("Per-category correctness")
cat_rows = []
for cat in sorted({q.get("category", "?") for q in fq}):
    row = {"category": cat}
    for layer in layers:
        qs = [q for q in fq if q.get("category") == cat and layer in q.get("layers", {})]
        if qs:
            correct = sum(1 for q in qs if q["layers"][layer].get("is_correct"))
            row[layer] = round(100.0 * correct / len(qs), 1)
        else:
            row[layer] = 0.0
    cat_rows.append(row)

if cat_rows:
    cat_df = pd.DataFrame(cat_rows).set_index("category")
    st.bar_chart(cat_df)
else:
    st.info("No questions match the current filters.")

# ---------------------------------------------------------------- (3) drill-down
st.subheader("Per-question drill-down")

table_rows = []
for q in fq:
    row = {
        "id": q.get("id"),
        "category": q.get("category"),
        "answer_type": q.get("answer_type"),
        "complexity": q.get("complexity"),
    }
    for layer in layers:
        ld = q.get("layers", {}).get(layer, {})
        row[f"{layer} correct"] = "✅" if ld.get("is_correct") else "❌"
        row[f"{layer} score"] = ld.get("correctness_run", {}).get("score")
    table_rows.append(row)

if table_rows:
    st.dataframe(pd.DataFrame(table_rows), width="stretch", hide_index=True)

for q in fq:
    with st.expander(f"{q.get('id')} — {q.get('input', '')}"):
        st.markdown(f"**Expected:** {q.get('expected')}")
        st.markdown(
            f"**Category:** {q.get('category')} · **Answer type:** {q.get('answer_type')} "
            f"· **Complexity:** {q.get('complexity')} · **Required layers:** "
            f"{', '.join(q.get('required_layers', []))}"
        )
        lcols = st.columns(max(len(layers), 1))
        for lcol, layer in zip(lcols, layers):
            ld = q.get("layers", {}).get(layer)
            with lcol:
                st.markdown(f"### {layer}")
                if not ld:
                    st.info("Not evaluated.")
                    continue
                cr = ld.get("correctness_run", {})
                st.markdown("**Answer:**")
                st.write(cr.get("answer", ""))
                st.markdown(
                    f"**Tools trajectory:** {' → '.join(cr.get('tools_called', [])) or '(none)'}"
                )
                st.markdown(
                    f"**Score:** {cr.get('score')} · **Elapsed:** {cr.get('elapsed_sec')}s "
                    f"· **Refused:** {cr.get('refused')} · "
                    f"**Correct:** {'✅' if ld.get('is_correct') else '❌'}"
                )

                runs = ld.get("reproducibility_runs", [])
                if runs:
                    st.markdown("**Reproducibility runs:**")
                    st.dataframe(
                        pd.DataFrame(
                            [
                                {
                                    "score": r.get("score"),
                                    "refused": r.get("refused"),
                                    "elapsed_sec": r.get("elapsed_sec"),
                                    "tools": " → ".join(r.get("tools_called", [])) or "(none)",
                                    "answer": r.get("answer"),
                                }
                                for r in runs
                            ]
                        ),
                        width="stretch",
                        hide_index=True,
                    )

                rep = ld.get("reproducibility", {})
                if rep:
                    st.markdown("**Reproducibility breakdown:**")
                    st.json(rep)
