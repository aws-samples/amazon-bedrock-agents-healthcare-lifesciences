import json
import re
import urllib.request
import urllib.parse
import logging
from strands import Agent, tool
from strands.models import BedrockModel

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert protein researcher specializing in protein analysis using UniProt database. Help users search for and analyze proteins by retrieving detailed information through the UniProt API tools.

You have access to the following tools:

- search_proteins: Search for proteins in the UniProt database using protein names, descriptions, or other search terms. Returns a list of matching proteins with their UniProt accession IDs.
- get_protein_details: Retrieve comprehensive information about a specific protein using its UniProtKB accession ID, including function, cellular location, amino acid sequence, and other metadata.

Analysis Process

1. Begin by understanding what protein information the user is seeking.
2. Use search_proteins to find relevant proteins based on the user's query (protein name, description, or related terms).
3. Present the search results and help the user identify the most relevant proteins.
4. Use get_protein_details to retrieve comprehensive information for specific proteins of interest.
5. Analyze and interpret the protein data to answer the user's questions about protein function, disease relationships, cellular location, etc.
6. Present findings in a clear, structured format with relevant biological context.

Response Guidelines

- Provide scientifically accurate information based on UniProt data
- Explain protein concepts in accessible language while maintaining scientific precision
- Include relevant details like protein function, subcellular localization, and sequence information
- Highlight connections between proteins and diseases when relevant
- Make appropriate biological interpretations of the data
- Acknowledge data limitations and suggest additional resources when needed
"""


@tool
def search_proteins(query: str, organism: str = "human", limit: int = 10) -> str:
    """Search for proteins in the UniProt database using protein names, descriptions, gene names, or other search terms.

    Args:
        query: Search query for proteins (e.g., protein name, gene name, function description, or disease name)
        organism: Optional organism filter (e.g., 'human', 'mouse', 'Homo sapiens'). Defaults to human.
        limit: Maximum number of results to return (default: 10, max: 50)
    """
    limit = min(int(limit), 50)
    if not query.strip():
        return "Error: Query parameter is required for protein search."

    search_query = _construct_search_query(query.strip(), organism.strip())
    return _search_uniprot_proteins(search_query, limit)


@tool
def get_protein_details(
    accession_id: str,
    include_sequence: bool = False,
    include_features: bool = True,
) -> str:
    """Retrieve comprehensive information about a specific protein using its UniProtKB accession ID, including function, cellular location, amino acid sequence, disease associations, and other metadata.

    Args:
        accession_id: UniProtKB accession ID (e.g., 'P04637' for p53 tumor suppressor)
        include_sequence: Whether to include the amino acid sequence in the response (default: false)
        include_features: Whether to include detailed protein features and annotations (default: true)
    """
    accession_id = accession_id.strip().upper()
    if not re.match(r"^[A-Z0-9]{6,10}$", accession_id):
        return f"Error: Invalid UniProt accession ID format: {accession_id}. Expected format: 6-10 alphanumeric characters (e.g., P04637)"

    return _get_protein_details(accession_id, include_sequence, include_features)


def create_agent() -> Agent:
    """Create and return the UniProt protein search agent."""
    model = BedrockModel(
        model_id="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
        streaming=True,
    )
    return Agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        tools=[search_proteins, get_protein_details],
    )


# --- Internal helpers ---


def _construct_search_query(query: str, organism: str) -> str:
    organism_lower = organism.lower()
    organism_map = {
        "human": "Homo sapiens",
        "homo sapiens": "Homo sapiens",
        "mouse": "Mus musculus",
        "mus musculus": "Mus musculus",
        "rat": "Rattus norvegicus",
        "rattus norvegicus": "Rattus norvegicus",
    }
    org_name = organism_map.get(organism_lower, organism)
    organism_filter = f'organism_name:"{org_name}"'

    terms = query.split()
    if len(terms) == 1:
        t = terms[0]
        search_terms = f'(protein_name:"{t}" OR gene:"{t}" OR cc_function:"{t}" OR cc_disease:"{t}" OR keyword:"{t}")'
    else:
        full = " ".join(terms)
        parts = [
            f'protein_name:"{full}"',
            f'cc_function:"{full}"',
            f'cc_disease:"{full}"',
            f'({" AND ".join(terms)})',
        ]
        for t in terms:
            parts.extend([f'protein_name:"{t}"', f'gene:"{t}"', f'keyword:"{t}"'])
        search_terms = f"({' OR '.join(parts)})"

    return f"{search_terms} AND {organism_filter}"


def _search_uniprot_proteins(query: str, limit: int) -> str:
    base_url = "https://rest.uniprot.org/uniprotkb/search"
    params = {
        "query": query,
        "format": "json",
        "size": str(limit),
        "fields": "accession,id,protein_name,gene_names,organism_name,length,cc_function",
    }
    url = f"{base_url}?{urllib.parse.urlencode(params)}"

    try:
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "AgentCore-UniProt-Agent/1.0")
        with urllib.request.urlopen(req, timeout=25) as response:
            data = json.loads(response.read().decode("utf-8"))
    except Exception as e:
        return f"Error accessing UniProt database: {e}"

    results = data.get("results", [])
    if not results:
        return f"No proteins found matching query: {query}"

    lines = [f"Found {len(results)} protein(s):\n"]
    for i, protein in enumerate(results, 1):
        accession = protein.get("primaryAccession", "N/A")
        name = (
            protein.get("proteinDescription", {})
            .get("recommendedName", {})
            .get("fullName", {})
            .get("value", "N/A")
        )
        genes = protein.get("genes", [])
        gene = genes[0].get("geneName", {}).get("value", "N/A") if genes else "N/A"
        org = protein.get("organism", {}).get("scientificName", "N/A")
        length = protein.get("sequence", {}).get("length", "N/A")

        func = "N/A"
        for c in protein.get("comments", []):
            if c.get("commentType") == "FUNCTION":
                texts = c.get("texts", [])
                if texts:
                    val = texts[0].get("value", "")
                    func = (val[:200] + "...") if len(val) > 200 else val
                break

        lines.append(
            f"{i}. {name}\n"
            f"   Accession: {accession} | Gene: {gene} | Organism: {org}\n"
            f"   Length: {length} aa | Function: {func}\n"
        )

    lines.append("Use get_protein_details with an accession ID for more information.")
    return "\n".join(lines)


def _get_protein_details(
    accession_id: str, include_sequence: bool, include_features: bool
) -> str:
    fields = [
        "accession", "id", "protein_name", "gene_names", "organism_name",
        "length", "cc_function", "cc_subcellular_location", "cc_disease",
        "ft_domain", "ft_region", "xref_pdb",
    ]
    if include_sequence:
        fields.append("sequence")

    params = {"format": "json", "fields": ",".join(fields)}
    url = f"https://rest.uniprot.org/uniprotkb/{accession_id}?{urllib.parse.urlencode(params)}"

    try:
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "AgentCore-UniProt-Agent/1.0")
        with urllib.request.urlopen(req, timeout=25) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return f"Protein '{accession_id}' not found in UniProt database."
        return f"Error accessing UniProt: HTTP {e.code}"
    except Exception as e:
        return f"Error accessing UniProt database: {e}"

    # Format output
    name = (
        data.get("proteinDescription", {})
        .get("recommendedName", {})
        .get("fullName", {})
        .get("value", "N/A")
    )
    genes = data.get("genes", [])
    gene = genes[0].get("geneName", {}).get("value", "N/A") if genes else "N/A"
    org = data.get("organism", {}).get("scientificName", "N/A")
    length = data.get("sequence", {}).get("length", "N/A")

    result = [
        f"Protein: {name}",
        f"Accession: {accession_id} | Gene: {gene} | Organism: {org} | Length: {length} aa",
        "",
    ]

    # Function
    for c in data.get("comments", []):
        if c.get("commentType") == "FUNCTION":
            texts = c.get("texts", [])
            if texts:
                result.extend(["FUNCTION:", texts[0].get("value", ""), ""])
            break

    # Subcellular location
    for c in data.get("comments", []):
        if c.get("commentType") == "SUBCELLULAR_LOCATION":
            locs = [
                loc.get("location", {}).get("value", "")
                for loc in c.get("subcellularLocations", [])
            ]
            locs = [l for l in locs if l]
            if locs:
                result.extend(["SUBCELLULAR LOCALIZATION:", ", ".join(locs), ""])
            break

    # Diseases
    diseases = []
    for c in data.get("comments", []):
        if c.get("commentType") == "DISEASE":
            d = c.get("disease", {})
            if d:
                did = d.get("diseaseId", "Unknown")
                texts = c.get("texts", [])
                desc = texts[0].get("value", "")[:200] if texts else ""
                diseases.append(f"- {did}: {desc}")
    if diseases:
        result.extend(["DISEASE ASSOCIATIONS:"] + diseases + [""])

    # Features
    if include_features:
        features = data.get("features", [])
        if features:
            feat_lines = ["PROTEIN FEATURES:"]
            for f in features[:10]:
                ftype = f.get("type", "Unknown")
                desc = f.get("description", "")
                loc = f.get("location", {})
                start = loc.get("start", {}).get("value", "")
                end = loc.get("end", {}).get("value", "")
                pos = f"{start}-{end}" if start and end else "?"
                feat_lines.append(f"  {ftype} ({pos}): {desc}")
            result.extend(feat_lines + [""])

    # PDB
    xrefs = data.get("uniProtKBCrossReferences", [])
    pdb_ids = [x.get("id", "") for x in xrefs if x.get("database") == "PDB"]
    if pdb_ids:
        result.extend([f"3D STRUCTURES: {', '.join(pdb_ids[:5])}", ""])

    # Sequence
    if include_sequence:
        seq = data.get("sequence", {}).get("value", "")
        if seq:
            seq_lines = [seq[i : i + 60] for i in range(0, len(seq), 60)]
            result.extend(["SEQUENCE:"] + seq_lines + [""])

    return "\n".join(result)
