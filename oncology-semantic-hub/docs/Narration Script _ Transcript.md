# Narration Script — Oncology Semantic Hub Demo (3:23)

## Scene 1 — Quick Desktop: Full-Hub Orchestration (0:00–1:50)

**[0:00–0:10]** We open with a complex oncology research question — and a preview of everything it takes to answer it. In glioblastoma, do EGFR and PTEN mutations co-occur across the patient cohort, is that association statistically significant, do the genes share a pathway, and what are the treatment implications? The summary card shows the tool chain the agent will use — data lake, code execution, knowledge graph, and clinical evidence — and the trust scores it earns: 77% grounded, zero fabricated. No single database can answer this alone.

**[0:10–0:45]** Here's the environment. We're in Amazon Quick Desktop — a no-code research frontend. The oncology semantic hub analysis skill is loaded, connecting the agent to its tools through MCP servers: Amazon Neptune for the knowledge graph, Amazon Athena for the patient data lake, the Ontology Lookup Service for canonical identifiers, and the RODA variant annotation database for clinical evidence. The agent chooses which tools to use on its own — there are no hints in the question.

**[0:45–1:05]** Now we ask the question. The agent begins by retrieving mutation counts from the patient data lake — EGFR in 82 patients, PTEN in 116, both in 30, out of 371 total — calling the lake query tool several times, then reaching into the knowledge graph.

**[1:05–1:30]** It computes a real Fisher's exact test using code execution: odds ratio 1.36, p-value 0.30 — not statistically significant. This is a real computed statistic from your cohort's actual data, not an estimate from memory. It then traverses the knowledge graph for shared signaling pathways and EGFR drug targets, and queries CIViC for clinical actionability evidence with cited PMIDs.

**[1:30–1:50]** The answer synthesizes it all — the co-occurrence statistic, the shared PI3K/AKT pathway, the druggable targets, and the clinical interpretation that PTEN loss predicts resistance to EGFR-targeted therapy. Every claim is tagged to its source: Lake, Compute, Graph, RODA, or Model knowledge. The grounding rate is 0.77 — 10 of 13 claims tool-backed and verifiable; provenance-faithfulness is 1.0 — zero fabricated sources. The model-knowledge claims are honest clinical interpretation, clearly labeled.

## Scene 2 — Compare UI: Correctness + Reproducibility (1:50–2:50)

**[1:50–2:10]** Now let's isolate the value of semantic organization. This is the Compare UI — L2 on the left, L3 on the right. L2 has all the same data as L3, but organized as flat tables — no graph, no ontology. Same model, same data; only the organization differs. The question: how many genes are mutated in our GBM cohort, and how many are known to be associated with glioblastoma as a disease? Both nail the first part — 12,694 mutated genes from the patient lake. That's the parity floor — L2 is no strawman.

**[2:10–2:30]** But on disease-associated genes they diverge. L3 resolves glioblastoma to its canonical MONDO identifier and returns 144 genes — the correct answer. L2 name-matches against the flat table, sweeps in subtypes — including astrocytoma, which is definitionally not glioblastoma — and inflates to 166. The flat table contains the right answer; L2 just can't reliably select it without canonical resolution.

**[2:30–2:50]** Reproducibility comes from the same mechanism. Ask the question again and L3 returns 144 every time — it's anchored to the canonical MONDO node. L2 flips between 166 and 12,694 across runs, interpreting the ambiguous question differently each time. One mechanism — canonical anchoring versus flat name matching — drives both the correctness gap and the reproducibility gap.

## Scene 3 — Compare UI: Groundedness (2:50–3:23)

**[2:50–3:05]** Finally, what happens with no data at all? L0 — a bare LLM with no tools — versus L3, the full semantic hub. The question: is the co-occurrence of EGFR and PTEN mutations in TCGA-GBM statistically significant? Give the p-value.

**[3:05–3:15]** L0 answers confidently — p-values typically less than 0.001 to 0.01, statistically significant — and cites the original TCGA GBM study. It sounds authoritative. But the p-value is fabricated from training memory, and the conclusion is wrong.

**[3:15–3:23]** L3 retrieves the real two-by-two contingency table from the patient lake — 30 co-mutated of 371 — and computes Fisher's exact test: p equals 0.37, not statistically significant. The correct conclusion, grounded in your cohort's actual data. Same model throughout. The infrastructure — not the model — is what makes the agent correct, reproducible, and trustworthy.
