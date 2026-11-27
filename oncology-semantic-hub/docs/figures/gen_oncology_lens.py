"""Generate the Semantic Hub oncology-lens architecture figure (docs/semantic-hub-oncology-lens.png).

Renders the 4-lane reference architecture (Data -> Context -> Agentic Access -> Consumption) with a
color legend distinguishing GENERIC (shared) boxes, ONCOLOGY-LENS overlays, and NET-NEW overlays that the
generic design lacks. No AWS calls; pure matplotlib. Regenerate:  python docs/figures/gen_oncology_lens.py
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from pathlib import Path

GENERIC = "#e6eefc"; GENERIC_E = "#3b6fb5"
OVERLAY = "#ffe9c7"; OVERLAY_E = "#e08a00"
NETNEW = "#ffd6d6"; NETNEW_E = "#c40000"

fig, ax = plt.subplots(figsize=(16, 9))
ax.set_xlim(0, 16); ax.set_ylim(0, 9); ax.axis("off")

ax.text(8, 8.6, "Semantic Hub — the Oncology / Research Lens", ha="center", fontsize=20, fontweight="bold")
ax.text(8, 8.15, "build on the generic AWS semantic-hub architecture · add the therapeutic-area lens",
        ha="center", fontsize=11, style="italic", color="#444")

# value gradient bar
ax.text(8, 7.55, "Value gradient:  raw omics  →  harmonized / ontology-linked graph  →  provenance-grounded agent answers",
        ha="center", fontsize=10.5, color="#0a6b3b", fontweight="bold")

lanes = [("Data", 0.4), ("Context", 4.3), ("Agentic Access", 8.2), ("Consumption", 12.1)]
for name, x in lanes:
    ax.add_patch(FancyBboxPatch((x, 1.5), 3.5, 5.4, boxstyle="round,pad=0.05",
                                fc="#f7f9fc", ec="#c8d2e0", lw=1.5))
    ax.text(x + 1.75, 6.6, name, ha="center", fontsize=13, fontweight="bold", color="#22334d")

def box(x, y, w, h, text, kind):
    fc, ec = {"g": (GENERIC, GENERIC_E), "o": (OVERLAY, OVERLAY_E), "n": (NETNEW, NETNEW_E)}[kind]
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.03", fc=fc, ec=ec, lw=1.8))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=8.2)

# Data lane
box(0.6, 5.5, 3.1, 0.85, "S3 Data Lake\nTCGA · cBioPortal · RODA · BYOD", "o")
box(0.6, 4.5, 3.1, 0.8, "Glue Data Catalog\nclinical/molecular/expression", "g")
box(0.6, 3.5, 3.1, 0.8, "Athena\nsurvival · mutation freq", "g")
box(0.6, 2.5, 3.1, 0.8, "Lake Formation\nPHI / consent governance", "o")

# Context lane
box(4.5, 5.5, 3.1, 0.85, "Neptune graph\nPrimeKG+TCGA+CIViC/ClinVar/\nCOSMIC/MONDO", "o")
box(4.5, 4.5, 3.1, 0.8, "Neptune Analytics\ntarget/biomarker discovery", "g")
box(4.5, 3.5, 3.1, 0.8, "Bedrock KB\nPubMed · guidelines · labels", "o")
box(4.5, 2.5, 3.1, 0.8, "OLS ontology service\nHGNC/Ensembl/MONDO/HPO", "n")

# Agentic Access lane
box(8.4, 5.5, 3.1, 0.85, "AgentCore Runtime\noncology agent L0-L3", "g")
box(8.4, 4.5, 3.1, 0.8, "Governed tools\ngraph · variant-annot · search", "o")
box(8.4, 3.5, 3.1, 0.8, "MCP-OLS · MCP-RODA ·\nMCP-HealthOmics", "n")
box(8.4, 2.5, 3.1, 0.8, "Governed per-user access\nassume-role · audit", "n")

# Consumption lane
box(12.3, 5.5, 3.1, 0.85, "QuickSuite Q&A\nEGFR-GBM persona", "o")
box(12.3, 4.5, 3.1, 0.8, "Dashboards\nbiomarker · survival", "g")
box(12.3, 3.5, 3.1, 0.8, "Researchers · oncologists\nbioinformaticians", "g")

# flow arrows between lanes
for x0 in (3.7, 7.6, 11.5):
    ax.add_patch(FancyArrowPatch((x0, 4.4), (x0 + 0.8, 4.4), arrowstyle="-|>",
                                 mutation_scale=18, lw=2, color="#22334d"))

# bottom band: Cognito + A2
box(0.6, 0.5, 7.0, 0.75, "Amazon Cognito · OAuth 2.0 / JWT — consent-scoped per-researcher cohort access + audit", "o")
box(8.4, 0.5, 7.0, 0.75, "A2 Benchmark / Eval quality gate — tier ladder · grounding/provenance-faithfulness · context-poisoning  (net-new)", "n")

# legend
ly = 1.75
for i, (c, e, lbl) in enumerate([(GENERIC, GENERIC_E, "Generic (shared) box"),
                                  (OVERLAY, OVERLAY_E, "Oncology-lens overlay"),
                                  (NETNEW, NETNEW_E, "Net-new (absent in generic design)")]):
    ax.add_patch(FancyBboxPatch((0.6 + i * 5.0, ly), 0.4, 0.28, boxstyle="round,pad=0.02", fc=c, ec=e, lw=1.6))
    ax.text(1.1 + i * 5.0, ly + 0.14, lbl, va="center", fontsize=9)

out = Path(__file__).resolve().parents[1] / "semantic-hub-oncology-lens.png"
fig.savefig(out, dpi=150, bbox_inches="tight")
print(f"wrote {out}")
