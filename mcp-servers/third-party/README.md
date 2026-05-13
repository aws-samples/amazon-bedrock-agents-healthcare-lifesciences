# Third-Party MCP Servers

Public MCP servers from life sciences tool providers. These require no deployment — configure them in your AI assistant to get immediate access to biomedical databases, literature, and domain tools.

## Available Servers

| Server | Provider | What it provides |
|--------|----------|------------------|
| [pubmed](pubmed/) | U.S. National Library of Medicine | Biomedical literature search (35M+ articles) |
| [open-targets](open-targets/) | Open Targets | Gene-disease associations, drug targets, evidence |
| [chembl](chembl/) | deepsense.ai | Chemical compound data, bioactivity, drug-likeness |
| [clinical-trials](clinical-trials/) | deepsense.ai | ClinicalTrials.gov search and filtering |
| [biorxiv](biorxiv/) | deepsense.ai | Preprint biology/medicine literature |
| [synapse](synapse/) | Sage Bionetworks | Collaborative research data platform |
| [biorender](biorender/) | BioRender | Scientific figure and diagram creation |
| [consensus](consensus/) | Consensus | Evidence-based answers from research papers |
| [cortellis](cortellis/) | Clarivate | Regulatory intelligence, drug approvals |
| [adisinsight](adisinsight/) | Springer Nature | Drug development pipeline intelligence |
| [medidata](medidata/) | Medidata Solutions | Clinical trial data management |
| [wiley](wiley/) | Wiley | Academic literature (Scholar Gateway) |
| [owkin](owkin/) | Owkin | AI-powered biomarker discovery |
| [10x-genomics](10x-genomics/) | 10x Genomics | Single-cell and spatial genomics (local binary) |
| [tooluniverse](tooluniverse/) | MIMS Harvard | Bioinformatics tool discovery (local binary) |

## Configuration

Each server folder contains a `.mcp.json` file. To use a server, add its config to your assistant:

**Claude Code** — merge into your project's `.mcp.json` or reference the file  
**Kiro** — add to `.kiro/settings/mcp.json`  
**Q Desktop** — Settings → Capabilities → Add MCP Server → paste the URL  
**Cursor** — add to `.cursor/mcp.json`

## Source

These servers are sourced from the [Anthropic Life Sciences](https://github.com/anthropics/life-sciences) plugin marketplace. They are independently maintained by their respective providers.
