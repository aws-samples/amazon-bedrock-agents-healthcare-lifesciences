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

### Example 1: Search for proteins related to Alzheimer's disease
```
User: "What proteins are associated with Alzheimer's disease?"
Agent: Uses search_proteins with query "Alzheimer's disease" to find relevant proteins, then uses get_protein_details to provide comprehensive information about key proteins like APP, PSEN1, PSEN2, and APOE.
```

### Example 2: Get detailed information about a specific protein
```
User: "Tell me about the p53 protein"
Agent: Uses search_proteins to find p53, then get_protein_details with the accession ID to provide detailed information about its tumor suppressor function, cellular location, and disease associations.
```

### Example 3: Find proteins in a specific cellular compartment
```
User: "What proteins are found in mitochondria?"
Agent: Uses search_proteins with query "mitochondria" or "mitochondrial" to find proteins localized to mitochondria, then provides details about their functions.
```
