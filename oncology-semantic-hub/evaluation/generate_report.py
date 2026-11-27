#!/usr/bin/env python3
"""Report generator for the Semantic Hub Validation Framework.

Reads a pilot results JSON and writes:
  - docs/BENCHMARK_REPORT_V2.md
  - evaluation/reports/headline_2x2.png

Layer-generic: the baseline is the first layer in meta.layers and the treatment is
the last. No AWS calls are made.
"""
import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_RESULTS = ROOT / "evaluation" / "results" / "pilot_results.json"
REPORT_MD = ROOT / "docs" / "BENCHMARK_REPORT_V2.md"
CHART_PNG = ROOT / "evaluation" / "reports" / "headline_2x2.png"
PROVENANCE = "docs/data-provenance.md"

LAYER_LABELS = {
    "L0": "Bare LLM (no data)",
    "L1": "Raw data lake — no map",
    "L2": "Knowledge graph only",
    "L3": "Semantic hub — with map",
}


def label_for(layer):
    return f"{layer} — {LAYER_LABELS.get(layer, layer)}"


def pct(num, denom):
    return 100.0 * num / denom if denom else 0.0


def compute_layer_stats(questions, layer):
    n = correct = repro = 0
    for q in questions:
        ld = q["layers"].get(layer)
        if not ld:
            continue
        n += 1
        correct += 1 if ld["is_correct"] else 0
        repro += 1 if ld["reproducibility"]["reproducible_correct"] else 0
    return n, pct(correct, n), pct(repro, n)


def per_category(questions, layer):
    cats = {}
    for q in questions:
        ld = q["layers"].get(layer)
        if not ld:
            continue
        c = cats.setdefault(q["category"], [0, 0])
        c[0] += 1
        c[1] += 1 if ld["is_correct"] else 0
    return cats


def render_chart(base_stats, treat_stats, base_label, treat_label):
    metrics = ["Correctness %", "Reproducibility %"]
    base_vals = [base_stats[1], base_stats[2]]
    treat_vals = [treat_stats[1], treat_stats[2]]
    x = range(len(metrics))
    width = 0.35

    fig, ax = plt.subplots(figsize=(8, 5))
    b0 = ax.bar([i - width / 2 for i in x], base_vals, width, label=base_label, color="#c0504d")
    b3 = ax.bar([i + width / 2 for i in x], treat_vals, width, label=treat_label, color="#4f81bd")
    ax.set_ylabel("Percent")
    ax.set_ylim(0, 105)
    ax.set_title("Semantic Hub Validation")
    ax.set_xticks(list(x))
    ax.set_xticklabels(metrics)
    ax.legend()
    for bars in (b0, b3):
        for bar in bars:
            ax.annotate(f"{bar.get_height():.0f}%",
                        (bar.get_x() + bar.get_width() / 2, bar.get_height()),
                        ha="center", va="bottom", fontsize=9)
    fig.tight_layout()
    CHART_PNG.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(CHART_PNG, dpi=120)
    plt.close(fig)


def resolve_meta(meta):
    def first(*keys, default="n/a"):
        for k in keys:
            if k in meta and meta[k] is not None:
                return meta[k]
        return default

    return {
        "snapshot": first("snapshot", "data_snapshot"),
        "subject_model": first("subject_model", "model"),
        "layers": first("layers", "layers_evaluated", default=["L1", "L3"]),
        "n_reproducibility_runs": first("n_reproducibility_runs", "reproducibility_n"),
        "correctness_temperature": first("correctness_temperature", default=0.0),
        "reproducibility_temperature": first("reproducibility_temperature", default=0.7),
        "threshold": first("threshold", default=0.8),
        "timestamp": first("timestamp", "run_id"),
    }


def render_markdown(data, base, treat, base_stats, treat_stats):
    meta = resolve_meta(data["meta"])
    questions = data["questions"]
    chart_rel = CHART_PNG.relative_to(ROOT).as_posix()
    bl, tl = label_for(base), label_for(treat)
    L = []
    L.append("# Benchmark Report V2 — Semantic Hub Validation Framework")
    L.append("")
    L.append(f"- Snapshot: `{meta['snapshot']}`")
    L.append(f"- Subject model: `{meta['subject_model']}` (held constant across layers)")
    L.append(f"- Comparison: **{bl}** vs **{tl}**")
    L.append(f"- Reproducibility runs per question: {meta['n_reproducibility_runs']}")
    L.append(f"- Scoring threshold: {meta['threshold']}")
    L.append(f"- Generated from: `{meta['timestamp']}`")
    L.append("")

    L.append("## Headline Results")
    L.append("")
    L.append("| | Correctness % | Reproducibility % |")
    L.append("|---|---|---|")
    L.append(f"| {bl} | {base_stats[1]:.1f} | {base_stats[2]:.1f} |")
    L.append(f"| {tl} | {treat_stats[1]:.1f} | {treat_stats[2]:.1f} |")
    L.append("")
    L.append(f"![Headline 2x2]({chart_rel})")
    L.append("")

    L.append(f"## Per-Category Correctness ({base} vs {treat})")
    L.append("")
    L.append(f"| Category | {base} Correct/n | {base} % | {treat} Correct/n | {treat} % |")
    L.append("|---|---|---|---|---|")
    catsB = per_category(questions, base)
    catsT = per_category(questions, treat)
    for cat in sorted(set(catsB) | set(catsT)):
        nB, cB = catsB.get(cat, [0, 0])
        nT, cT = catsT.get(cat, [0, 0])
        L.append(f"| {cat} | {cB}/{nB} | {pct(cB, nB):.1f} | {cT}/{nT} | {pct(cT, nT):.1f} |")
    L.append("")

    L.append("## Per-Question Results")
    L.append("")
    L.append(f"| ID | Category | {base} correct | {base} repro | {treat} correct | {treat} repro |")
    L.append("|---|---|---|---|---|---|")
    for q in questions:
        bq = q["layers"].get(base, {})
        tq = q["layers"].get(treat, {})

        def cell(ld, key):
            if not ld:
                return "—"
            ok = ld["is_correct"] if key == "correct" else ld["reproducibility"]["reproducible_correct"]
            return "✅" if ok else "❌"

        L.append(f"| {q['id']} | {q['category']} | {cell(bq,'correct')} | {cell(bq,'repro')} "
                 f"| {cell(tq,'correct')} | {cell(tq,'repro')} |")
    L.append("")

    L.append("## Methodology")
    L.append("")
    L.append(f"- **Correctness**: single deterministic run at temperature = {meta['correctness_temperature']}.")
    L.append(f"- **Reproducibility**: {meta['n_reproducibility_runs']} runs at temperature = "
             f"{meta['reproducibility_temperature']}; *reproducible-correct* = every run scores "
             f"≥ {meta['threshold']} and agrees.")
    L.append("- Scoring is **deterministic** (fixed rubric vs. expected value), no LLM-as-judge.")
    L.append(f"- **{base}** is a naive connection to the raw data lake (Athena SQL, no semantic "
             f"map); **{treat}** adds the semantic hub retrieval map (knowledge graph + ontology).")
    L.append("- Expect parity on lake-native questions and a gap on relationship / graph / "
             "cross-system questions — that gap is the value of the semantic map.")
    L.append("")

    L.append("## Data Provenance")
    L.append("")
    L.append(f"Source datasets, versions, and licensing are documented in [{PROVENANCE}]({PROVENANCE}).")
    L.append("")

    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD.write_text("\n".join(L))


def main():
    ap = argparse.ArgumentParser(description="Generate the Semantic Hub benchmark report.")
    ap.add_argument("--results", default=str(DEFAULT_RESULTS))
    args = ap.parse_args()

    results_path = Path(args.results)
    if not results_path.is_absolute():
        results_path = ROOT / results_path
    data = json.loads(results_path.read_text())

    layers = resolve_meta(data["meta"])["layers"]
    base, treat = layers[0], layers[-1]
    questions = data["questions"]
    base_stats = compute_layer_stats(questions, base)
    treat_stats = compute_layer_stats(questions, treat)

    render_chart(base_stats, treat_stats, label_for(base), label_for(treat))
    render_markdown(data, base, treat, base_stats, treat_stats)

    print(f"Read results:   {results_path}")
    print(f"Wrote report:   {REPORT_MD}")
    print(f"Wrote chart:    {CHART_PNG}")
    print(f"{base}: correctness={base_stats[1]:.1f}%  reproducibility={base_stats[2]:.1f}%")
    print(f"{treat}: correctness={treat_stats[1]:.1f}%  reproducibility={treat_stats[2]:.1f}%")


if __name__ == "__main__":
    main()
