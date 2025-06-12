# UniProt Protein Search Agent

## 1. Summary

Search and retrieve detailed information about proteins from the UniProt database. This agent helps scientists find proteins by name or description and retrieve comprehensive protein data including function, cellular location, amino acid sequences, and other metadata to answer questions like "Which protein might be the cause of a disease?"

## 2. Agent Details

### 2.1. Instructions

> You are an expert protein researcher specializing in protein analysis using UniProt database. Help users search for and analyze proteins by retrieving detailed information through the UniProt API tools.
>
> You have access to the following tools:
>
> - search_proteins: Search for proteins in the UniProt database using protein names, descriptions, or other search terms. Returns a list of matching proteins with their UniProt accession IDs.
> - get_protein_details: Retrieve comprehensive information about a specific protein using its UniProtKB accession ID, including function, cellular location, amino acid sequence, and other metadata.
>
> Analysis Process
>
> 1. Begin by understanding what protein information the user is seeking.
> 2. Use search_proteins to find relevant proteins based on the user's query (protein name, description, or related terms).
> 3. Present the search results and help the user identify the most relevant proteins.
> 4. Use get_protein_details to retrieve comprehensive information for specific proteins of interest.
> 5. Analyze and interpret the protein data to answer the user's questions about protein function, disease relationships, cellular location, etc.
> 6. Present findings in a clear, structured format with relevant biological context.
>
> Response Guidelines
>
> - Provide scientifically accurate information based on UniProt data
> - Explain protein concepts in accessible language while maintaining scientific precision
> - Include relevant details like protein function, subcellular localization, and sequence information
> - Highlight connections between proteins and diseases when relevant
> - Make appropriate biological interpretations of the data
> - Acknowledge data limitations and suggest additional resources when needed

### 2.2. Guardrails

| Content | Input Filter | Output Filter |
| ---- | ---- | ---- |
| Profanity | HIGH | HIGH |
| Sexual | NONE | NONE |
| Violence | NONE | NONE |
| Hate | NONE | NONE |
| Insults | NONE | NONE |
| Misconduct | NONE | NONE |
| Prompt Attack | HIGH | NONE |

### 2.3. Tools

```json
{
  name: "search_proteins",
  description: "Search for proteins in the UniProt database using protein names, descriptions, gene names, or other search terms. Returns a list of matching proteins with their UniProt accession IDs and basic information.",
  inputSchema: {
    type: "object",
    properties: {
      query: { type: "string", description: "Search query for proteins (e.g., protein name, gene name, function description, or disease name)"},
      organism: { type: "string", description: "Optional organism filter (e.g., 'human', 'mouse', 'Homo sapiens'). Defaults to human if not specified."},
      limit: { type: "integer", description: "Maximum number of results to return (default: 10, max: 50)"}
    },
    required: ["query"]
  }
},
{
  name: "get_protein_details",
  description: "Retrieve comprehensive information about a specific protein using its UniProtKB accession ID, including function, cellular location, amino acid sequence, disease associations, and other metadata.",
  inputSchema: {
    type: "object",
    properties: {
      accession_id: { type: "string", description: "UniProtKB accession ID (e.g., 'P04637' for p53 tumor suppressor)"},
      include_sequence: { type: "boolean", description: "Whether to include the amino acid sequence in the response (default: false)"},
      include_features: { type: "boolean", description: "Whether to include detailed protein features and annotations (default: true)"}
    },
    required: ["accession_id"]
  }
}
```

## 3. Installation

1. (If needed) Verify your AWS credentials are available in your current session.

`aws sts get-caller-identity`

2. (If needed) Create a Amazon S3 bucket to store the agent template.

`aws s3 mb s3://YOUR_S3_BUCKET_NAME`

3. Navigate to the `UniProt-protein-search-agent` folder

`cd agents_catalog/19-UniProt-protein-search-agent`

4. Package and deploy the agent template

```bash
export BUCKET_NAME="<REPLACE>"
export NAME="<REPLACE>"
export REGION="<REPLACE>"
export BEDROCK_AGENT_SERVICE_ROLE_ARM="<REPLACE>"

aws cloudformation package --template-file "uniprot-protein-search-agent-cfn.yaml" \
  --s3-bucket $BUCKET_NAME \
  --output-template-file "uniprot-protein-search-agent-cfn-packaged.yaml"
aws cloudformation deploy --template-file "uniprot-protein-search-agent-cfn-packaged.yaml" \
  --capabilities CAPABILITY_IAM \
  --stack-name $NAME \
  --region $REGION \
  --parameter-overrides \
  AgentAliasName="Latest" \
  AgentIAMRoleArn=$BEDROCK_AGENT_SERVICE_ROLE_ARM
rm uniprot-protein-search-agent-cfn-packaged.yaml
```

## 4. Usage Examples

### Example 1: Search for proteins related to a specific research tool
**User Query:** "Please search UniProt for information about green fluorescent protein"

**Agent Response:**
```
Green Fluorescent Protein (GFP) is a 238-amino acid protein originally discovered in the jellyfish Aequorea victoria. Its main function is to act as an energy-transfer acceptor that converts blue chemiluminescence from another protein (aequorin) into green fluorescent light. GFP has become one of the most important tools in molecular biology and cell biology for its ability to serve as a fluorescent marker.

The protein has been extensively studied and has multiple known 3D structures. The original wild-type GFP (UniProt ID: P42212) naturally fluoresces green when exposed to blue light, making it an invaluable tool for researchers to track protein expression, localization, and movement in living cells.

Several variants of GFP exist in the database, but the canonical form is the best characterized. This discovery was so significant that it led to the 2008 Nobel Prize in Chemistry for its discovery and development as a research tool.
```

### Example 2: Get specific protein sequence information
**User Query:** "What is the amino acid sequence of human insulin?"

**Agent Response:**
```
The amino acid sequence of human insulin preproprotein is:
MALWMRLLPLLALLALWGPDPAAAFVNQHLCGSHLVEALYLVCGERGFFYTPKTRREAEDLQVGQVELGGGPGAGSLQPLALEGSLQKRGIVEQCCTSICSLYQLENYCN

This sequence represents the complete preproprotein (110 amino acids) which includes:
- Signal peptide (first 24 amino acids)
- B chain (30 amino acids)
- C-peptide (connecting peptide)
- A chain (21 amino acids)

The mature insulin hormone is formed after removal of the signal peptide and C-peptide, leaving two chains (A and B) connected by disulfide bonds.
```

### Example 3: Search for disease-related proteins
**User Query:** "What proteins are associated with Alzheimer's disease?"

**Agent Response:**
```
Found 3 protein(s) matching your search:

1. Amyloid-beta precursor protein
   - Accession ID: P05067
   - Gene: APP
   - Organism: Homo sapiens
   - Length: 770 amino acids
   - Function: Functions as a cell surface receptor and performs physiological functions on the surface of neurons relevant to neurite growth, neuronal adhesion and axonogenesis...

2. Collagen alpha-1(XXV) chain
   - Accession ID: Q9BXS0
   - Gene: COL25A1
   - Organism: Homo sapiens
   - Length: 654 amino acids
   - Function: Inhibits fibrillization of amyloid-beta peptide during the elongation phase...

3. Cathepsin D
   - Accession ID: P07339
   - Gene: CTSD
   - Organism: Homo sapiens
   - Length: 412 amino acids
   - Function: Acid protease active in intracellular protein breakdown. Plays a role in APP processing...
```

### Example 4: Get detailed information about a specific protein
**User Query:** "Tell me about protein P04637"

**Agent Response:**
```
Detailed Information for Protein P04637
==================================================
Protein Name: Cellular tumor antigen p53
Primary Gene: TP53
Organism: Homo sapiens
Length: 393 amino acids

FUNCTION:
Acts as a tumor suppressor in many tumor types; induces growth arrest or apoptosis depending on the physiological circumstances and cell type. Plays a role in cell cycle regulation as a trans-activator that acts to negatively regulate cell division by controlling a set of genes required for this process...

SUBCELLULAR LOCALIZATION:
Cytoplasm. Nucleus. Nucleus, PML body. Endoplasmic reticulum...

DISEASE ASSOCIATIONS:
- Li-Fraumeni syndrome: Autosomal dominant familial cancer predisposition syndrome...
- Hereditary cancer-predisposing syndrome: Germline mutations in TP53 cause various hereditary cancer syndromes...

PROTEIN FEATURES:
- Domain:
  94-292: DNA-binding
  319-393: Tetramerization
- Region:
  1-42: Transactivation (acidic)
  363-393: Regulatory
```

### Example 5: Search for proteins in specific cellular locations
**User Query:** "Find proteins located in mitochondria"

**Agent Response:**
```
Found 5 protein(s) matching your search:

1. Cytochrome c oxidase subunit 1
   - Accession ID: P00395
   - Gene: MT-CO1
   - Organism: Homo sapiens
   - Length: 513 amino acids
   - Function: Cytochrome c oxidase is the component of the respiratory chain that catalyzes the reduction of oxygen to water...

2. ATP synthase subunit alpha, mitochondrial
   - Accession ID: P25705
   - Gene: ATP5F1A
   - Organism: Homo sapiens
   - Length: 553 amino acids
   - Function: Mitochondrial membrane ATP synthase produces ATP from ADP in the presence of a proton gradient...
```

### Example 6: Multi-word search queries
**User Query:** "Search for human insulin receptor"

**Agent Response:**
```
Found 5 protein(s) matching your search:

1. Insulin receptor
   - Accession ID: P06213
   - Gene: INSR
   - Organism: Homo sapiens
   - Length: 1382 amino acids
   - Function: Receptor tyrosine kinase which mediates the pleiotropic actions of insulin...

2. Insulin receptor substrate 1
   - Accession ID: P35568
   - Gene: IRS1
   - Organism: Homo sapiens
   - Length: 1242 amino acids
   - Function: Signaling adapter protein that participates in the signal transduction...
```

### Example 7: Cross-species protein search
**User Query:** "Find insulin proteins in mouse"

**Agent Response:**
```
Found 3 protein(s) matching your search:

1. Insulin-1
   - Accession ID: P01326
   - Gene: Ins1
   - Organism: Mus musculus
   - Length: 110 amino acids
   - Function: Insulin decreases blood glucose concentration...

2. Insulin-2
   - Accession ID: P01325
   - Gene: Ins2
   - Organism: Mus musculus
   - Length: 110 amino acids
   - Function: Insulin decreases blood glucose concentration...
```

## Common Use Cases

### For Disease Research
- "What proteins are involved in [disease name]?"
- "Find proteins associated with cancer"
- "Search for diabetes-related proteins"

### For Protein Function Analysis
- "What does protein [accession ID] do?"
- "Tell me about the function of [protein name]"
- "Where is [protein name] located in the cell?"

### For Sequence Analysis
- "What is the amino acid sequence of [protein name]?"
- "Show me the sequence for protein [accession ID]"
- "Get the full sequence including features for [protein name]"

### For Comparative Studies
- "Find [protein name] in different organisms"
- "Compare insulin across species"
- "Search for homologous proteins in mouse"

### For Structural Biology
- "What 3D structures are available for [protein name]?"
- "Find proteins with known PDB structures"
- "Tell me about the domains in [protein name]"

## 5. Troubleshooting

### Common Issues and Solutions

#### Issue: "No proteins found matching query"
**Possible Causes:**
- Query terms are too specific or contain typos
- Organism filter is too restrictive
- Protein doesn't exist in UniProt database

**Solutions:**
- Try broader search terms (e.g., "insulin" instead of "human insulin receptor")
- Check spelling of protein names and gene symbols
- Try searching without organism filter first
- Use alternative protein names or gene symbols

#### Issue: "Invalid UniProt accession ID format"
**Possible Causes:**
- Accession ID contains invalid characters
- Accession ID is too short or too long
- Using outdated or incorrect accession ID

**Solutions:**
- Ensure accession ID is 6-10 alphanumeric characters (e.g., P04637)
- Use uppercase letters for accession IDs
- Verify accession ID exists in UniProt database
- Check for recent updates to protein entries

#### Issue: "Network error accessing UniProt database"
**Possible Causes:**
- UniProt API is temporarily unavailable
- Network connectivity issues
- API rate limiting

**Solutions:**
- Wait a few minutes and try again
- Check UniProt service status at https://www.uniprot.org/
- Reduce query frequency if making many requests
- Contact support if issue persists

#### Issue: "Error parsing UniProt response"
**Possible Causes:**
- UniProt API response format changed
- Corrupted response data
- Timeout during data retrieval

**Solutions:**
- Try the query again
- Use smaller result limits for large searches
- Report persistent parsing errors to support

### Performance Tips

- **Use specific search terms** when possible to get more relevant results
- **Limit result size** for broad searches to improve response time
- **Search incrementally** - start with broad terms, then narrow down
- **Use accession IDs** when you know them for fastest retrieval

## 6. API Rate Limiting and Best Practices

### UniProt API Guidelines

The UniProt REST API has usage guidelines to ensure fair access for all users:

#### Rate Limiting
- **Recommended**: No more than 1 request per second
- **Maximum burst**: Up to 10 requests in quick succession
- **Courtesy delay**: Wait 100ms between requests when possible
- **Large datasets**: Use batch requests or contact UniProt for bulk access

#### Best Practices

**Search Optimization:**
- Use specific field searches when possible (e.g., `gene:"INS"` instead of just `INS`)
- Combine terms with AND/OR operators for precise results
- Limit result size with the `size` parameter (default: 25, max: 500)
- Use `fields` parameter to retrieve only needed data

**Responsible Usage:**
- Include a descriptive User-Agent header (automatically handled by this agent)
- Cache results locally when appropriate
- Avoid unnecessary repeated requests for the same data
- Monitor response times and adjust request frequency accordingly

**Error Handling:**
- Implement exponential backoff for failed requests
- Handle HTTP 429 (Too Many Requests) responses gracefully
- Check HTTP status codes before processing responses
- Log errors for debugging but avoid excessive logging

#### Supported Search Fields

**Protein Information:**
- `protein_name`: Protein names and synonyms
- `gene`: Gene names and symbols
- `organism_name`: Scientific organism names
- `taxonomy_id`: NCBI taxonomy identifiers

**Functional Annotation:**
- `cc_function`: Protein function descriptions
- `cc_subcellular_location`: Cellular localization
- `cc_disease`: Disease associations
- `keyword`: Functional keywords

**Structural Information:**
- `ft_domain`: Protein domains
- `ft_region`: Functional regions
- `xref_pdb`: PDB structure cross-references

**Identifiers:**
- `accession`: UniProt accession numbers
- `id`: UniProt entry names
- `xref_*`: Cross-references to other databases

### Data Usage and Attribution

When using data retrieved through this agent:

1. **Cite UniProt**: Include appropriate citations to the UniProt database
2. **Respect licensing**: UniProt data is freely available under CC BY 4.0 license
3. **Acknowledge sources**: Mention the use of UniProt REST API in publications
4. **Stay updated**: Check for data updates regularly as protein information evolves

### Recommended Citation

```
UniProt Consortium. UniProt: the Universal Protein Knowledgebase in 2023. 
Nucleic Acids Res. 2023 Jan 6;51(D1):D523-D531. doi: 10.1093/nar/gkac1052.
```

For more information, visit: https://www.uniprot.org/help/api
