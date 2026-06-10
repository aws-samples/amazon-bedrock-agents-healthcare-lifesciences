# Open Life Sciences Tools — AgentCore Gateway MCP Server

100+ life sciences database tools deployed as an MCP endpoint via Amazon Bedrock AgentCore Gateway.

## Overview

This MCP server provides comprehensive access to life sciences databases across genomics, proteomics, structural biology, pathways, clinical research, model organisms, cheminformatics, and more. The deployment follows the AgentCore Gateway pattern, enabling secure OAuth2-authenticated access to specialized research tools through AWS Lambda functions.

The integration adapts 24 modular MCP servers from the kiro-life-sciences collection, preserving the modular architecture while providing enterprise-grade deployment on AWS infrastructure.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    AI Assistant Clients                              │
│          (Claude Code, Kiro, Amazon Quick, Python SDK)               │
└───────────────────────────────┬─────────────────────────────────────┘
                                │ HTTPS + OAuth2 JWT
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│              Amazon Bedrock AgentCore Gateway                        │
│                  (CUSTOM_JWT Authorizer)                             │
└───────────────────────────────┬─────────────────────────────────────┘
                                │ Lambda Invocation
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      AWS Lambda Functions                            │
│                    (Database Tools Handler)                          │
│       24 MCP Server Modules • 100+ Tools                            │
└───────────────────────────────┬─────────────────────────────────────┘
                                │ HTTPS API calls
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│              External Life Sciences Databases                        │
│  UniProt · PDB · ClinVar · Ensembl · KEGG · Reactome · OMIM ...     │
└─────────────────────────────────────────────────────────────────────┘
```

The Gateway routes requests to Lambda functions containing modular MCP server implementations. Each server module maintains its own tool definitions and database client logic, allowing independent updates without full redeployment.

## Prerequisites

| Requirement | Details |
|-------------|---------|
| AWS CLI | Configured with appropriate credentials |
| Python 3.12+ | For Lambda runtime and local development |
| AWS Account | Permissions: CloudFormation, Lambda, Cognito, S3, IAM, AgentCore |
| Region | `us-east-1` or `us-west-2` (AgentCore availability) |

**Required IAM Permissions**:
- CloudFormation: `CreateStack`, `UpdateStack`, `DescribeStacks`
- Lambda: `CreateFunction`, `UpdateFunctionCode`, `InvokeFunction`
- Cognito: `CreateUserPool`, `CreateUserPoolClient`
- S3: `CreateBucket`, `PutObject`, `GetObject`
- IAM: `CreateRole`, `AttachRolePolicy`, `PassRole`
- SSM Parameter Store: `PutParameter`, `GetParameter`
- Bedrock AgentCore: `CreateGateway`, `CreateGatewayTarget`

## MCP Server Modules

The deployment includes 24 modular MCP servers providing 100+ tools across diverse life sciences domains:

### Core Domains

| Module | Tools | Databases Covered |
|--------|-------|------------------|
| **genomics** | 18 | NCBI, Ensembl, ClinVar, gnomAD, dbSNP, GEO, SRA, COSMIC, 1000 Genomes, DDBJ, ENCODE |
| **proteomics** | 8 | UniProt, InterPro, Pfam, STRING, PRIDE, neXtProt |
| **structural** | 6 | PDB, AlphaFold DB, CATH, SCOP |
| **pathways** | 7 | KEGG, Reactome, BioCyc, WikiPathways, IntAct, PathBank, Pathway Commons |
| **clinical** | 10 | OMIM, DrugBank, ChEMBL, PharmGKB, OpenTargets, ClinicalTrials.gov, FDA, BindingDB |
| **ontologies** | 6 | Gene Ontology, HPO, Disease Ontology, ChEBI, Uberon, Cell Ontology |

### Specialized Domains

| Module | Tools | Focus Area |
|--------|-------|------------|
| **cheminformatics** | 8 | PubChem, ChemSpider, ZINC, RDKit descriptors, docking, ADMET |
| **molbio** | 9 | GenBank, RefSeq, BLAST, primer design, restriction analysis |
| **model_organisms** | 5 | FlyBase, WormBase, SGD, ZFIN, MGI |
| **microbiology** | 8 | NCBI Taxonomy, BacDive, PATRIC, ViralZone, IMG |
| **immunology** | 4 | IEDB, VDJdb, IPD-IMGT/HLA, PIRD |
| **metabolomics** | 4 | HMDB, MetaboLights, METLIN, MassBank |
| **epigenomics** | 3 | ENCODE, Roadmap Epigenomics, MethBase |
| **neuroscience** | 5 | Allen Brain Atlas, NeuroMorpho, BrainSpan, NIF |
| **imaging** | 7 | Cell Image Library, IDR, EMDB, BioImage Archive |
| **ecology** | 7 | GBIF, BOLD, WoRMS, FishBase, PBDB |
| **agriculture** | 4 | Gramene, Sol Genomics, PlantGDB, AgBioData |
| **cellbiology** | 4 | CellMiner, CCLE, Cell Cycle DB, Organelle DB |
| **healthcare** | 8 | MedlinePlus, RxNorm, SNOMED CT, ICD codes, LOINC |
| **biobanking** | 6 | Biobank directories, sample tracking, consent management |
| **pipelines** | 8 | Galaxy, nf-core, WDL workflows, Snakemake |
| **datastandards** | 7 | FHIR, GA4GH schemas, MIAME, MAGE-TAB |
| **cloud** | 7 | AWS HealthOmics, Terra, DNAnexus, Seven Bridges |
| **aiml** | 6 | Model repositories, benchmarks, AutoML for omics |

**Total: 155 tools across 24 modules**

All tools accept natural language queries and automatically construct appropriate API calls to external databases.

## Deployment

### Step 1: Clone and Navigate

```bash
git clone https://github.com/aws-samples/amazon-bedrock-agents-healthcare-lifesciences.git
cd amazon-bedrock-agents-healthcare-lifesciences/mcp-servers/agentcore-gateway/open-life-sciences-tool
```

### Step 2: Configure AWS Credentials

```bash
# Option 1: Default profile
aws configure

# Option 2: Named profile
export AWS_PROFILE=my-profile

# Option 3: Specify region
export AWS_REGION=us-west-2
```

### Step 3: Deploy

```bash
./deploy.sh
```

Or specify a custom application name:

```bash
./deploy.sh my-lifesci-app
```

### Step 4: Expected Output

```
========================================
Open Life Sciences MCP Server Deploy
========================================
Region:   us-west-2
Account:  123456789012
App Name: open-life-sciences-tool
Bucket:   open-life-sciences-tool-us-west-2-123456789012
Stacks:   open-life-sciences-tool-infra, open-life-sciences-tool-cognito, open-life-sciences-tool-agentcore
========================================

🪣 Creating S3 bucket: open-life-sciences-tool-us-west-2-123456789012
✅ Bucket created successfully

📦 Packaging Lambda deployment package...
  Installing dependencies...
  Creating ZIP archive...
✅ Lambda package created: database-function.zip

🔧 Generating tool schemas...
✅ Tool schemas generated

☁️  Uploading artifacts to S3...
  ✅ Uploaded Lambda package
  ✅ Uploaded API spec
✅ All artifacts uploaded

🚀 Deploying: open-life-sciences-tool-infra
✅ open-life-sciences-tool-infra deployed successfully

🚀 Deploying: open-life-sciences-tool-cognito
✅ open-life-sciences-tool-cognito deployed successfully

🚀 Deploying: open-life-sciences-tool-agentcore
✅ open-life-sciences-tool-agentcore deployed successfully

========================================
✅ Deployment Complete!
========================================

Gateway URL: https://abc123.agentcore.us-west-2.amazonaws.com

Next steps:
  1. Get OAuth2 token:
     source get-token.sh open-life-sciences-tool
```

## Authentication

### Get OAuth2 Token

The MCP Gateway uses OAuth2 client credentials flow for machine-to-machine authentication:

```bash
source get-token.sh
```

This sets two environment variables in your shell:
- `MCP_TOKEN`: Access token valid for 60 minutes
- `GATEWAY_URL`: Gateway MCP endpoint URL

**Example output:**

```
🔑 Fetching OAuth2 token for open-life-sciences-tool...
✅ Token obtained successfully

Gateway URL: https://abc123.agentcore.us-west-2.amazonaws.com
Token expires in: 60 minutes
```

### Token Refresh

Tokens expire after 60 minutes. Re-run `get-token.sh` to obtain a fresh token:

```bash
source get-token.sh
```

### Optional API Keys

Some databases require API keys for full access or higher rate limits. Configure them after deployment:

#### NCBI E-utilities

Required for some NCBI queries; provides higher rate limits:

```bash
aws ssm put-parameter \
  --name '/app/open-life-sciences-tool/ncbi_api_key' \
  --value 'YOUR_NCBI_KEY' \
  --type 'SecureString' \
  --overwrite

aws ssm put-parameter \
  --name '/app/open-life-sciences-tool/ncbi_email' \
  --value 'your.email@example.com' \
  --type 'String' \
  --overwrite
```

Get an API key: https://www.ncbi.nlm.nih.gov/account/

#### COSMIC (Cancer Mutation Data)

Required for COSMIC database access:

```bash
aws ssm put-parameter \
  --name '/app/open-life-sciences-tool/cosmic_api_key' \
  --value 'YOUR_COSMIC_KEY' \
  --type 'SecureString' \
  --overwrite
```

Get an API key: https://cancer.sanger.ac.uk/cosmic/download

#### ChemSpider (Chemical Search)

Required for ChemSpider queries:

```bash
aws ssm put-parameter \
  --name '/app/open-life-sciences-tool/chemspider_api_key' \
  --value 'YOUR_CHEMSPIDER_KEY' \
  --type 'SecureString' \
  --overwrite
```

Get an API key: http://www.chemspider.com/AboutServices.aspx

## MCP Tools

The server provides 155 tools across 24 modules. Below are representative tools from each major category.

### Proteomics Tools

| Tool | Database | Description | Parameters | Example |
|------|----------|-------------|------------|---------|
| `uniprot_search` | UniProt | Search proteins by name or gene | `query` (str), `max_results` (int) | `{"query": "BRCA1", "max_results": 10}` |
| `uniprot_fetch` | UniProt | Get full protein record by accession | `accession` (str) | `{"accession": "P04637"}` |
| `uniprot_sequence` | UniProt | Get FASTA sequence | `accession` (str) | `{"accession": "P04637"}` |
| `interpro_lookup` | InterPro | Query protein domains | `accession` (str) | `{"accession": "IPR000719"}` |
| `pfam_family` | Pfam | Get domain family info | `family_id` (str) | `{"family_id": "PF00069"}` |
| `string_interactions` | STRING | Get protein-protein interactions | `protein` (str), `species` (int) | `{"protein": "TP53", "species": 9606}` |
| `pride_search` | PRIDE | Search proteomics projects | `keyword` (str) | `{"keyword": "breast cancer"}` |
| `nextprot_entry` | neXtProt | Get human protein entry | `gene_name` (str) | `{"gene_name": "TP53"}` |

### Structural Biology Tools

| Tool | Database | Description | Parameters | Example |
|------|----------|-------------|------------|---------|
| `pdb_search` | PDB | Search protein structures | `query` (str), `max_results` (int) | `{"query": "hemoglobin"}` |
| `pdb_fetch` | PDB | Get structure metadata | `pdb_id` (str) | `{"pdb_id": "1HHO"}` |
| `pdb_download` | PDB | Download structure file | `pdb_id` (str), `format` (str) | `{"pdb_id": "1HHO", "format": "pdb"}` |
| `alphafold_lookup` | AlphaFold DB | Get predicted structure | `uniprot_accession` (str) | `{"uniprot_accession": "P04637"}` |
| `cath_classify` | CATH | Get domain classification | `domain_id` (str) | `{"domain_id": "1cukA01"}` |
| `scop_classify` | SCOP | Get structural classification | `pdb_id` (str) | `{"pdb_id": "1HHO"}` |

### Genomics Tools

| Tool | Database | Description | Parameters | Example |
|------|----------|-------------|------------|---------|
| `ncbi_search` | NCBI | Search any NCBI database | `database` (str), `term` (str) | `{"database": "gene", "term": "BRCA2"}` |
| `ncbi_fetch_sequence` | NCBI | Fetch nucleotide sequence | `accession` (str), `format` (str) | `{"accession": "NM_000059", "format": "fasta"}` |
| `ncbi_pubmed_search` | PubMed | Search literature | `term` (str), `max_results` (int) | `{"term": "CRISPR gene editing"}` |
| `ensembl_gene_lookup` | Ensembl | Lookup gene by symbol | `symbol` (str), `species` (str) | `{"symbol": "BRCA2", "species": "homo_sapiens"}` |
| `ensembl_variants` | Ensembl | Get variants in region | `region` (str), `species` (str) | `{"region": "7:140424943-140624564"}` |
| `ensembl_sequence` | Ensembl | Get genomic sequence | `region` (str), `species` (str) | `{"region": "7:140424943-140624564"}` |
| `clinvar_search` | ClinVar | Search variants | `query` (str) | `{"query": "rs328"}` |
| `clinvar_get_variation` | ClinVar | Get variation record | `variation_id` (str) | `{"variation_id": "123456"}` |
| `gnomad_variant` | gnomAD | Get allele frequency | `variant_id` (str) | `{"variant_id": "1-55516888-G-A"}` |
| `dbsnp_lookup` | dbSNP | Lookup variant by rsID | `rsid` (str) | `{"rsid": "rs328"}` |

### Pathways Tools

| Tool | Database | Description | Parameters | Example |
|------|----------|-------------|------------|---------|
| `kegg_pathway_search` | KEGG | Search pathways | `query` (str) | `{"query": "glycolysis"}` |
| `kegg_pathway_get` | KEGG | Get pathway details | `pathway_id` (str) | `{"pathway_id": "hsa00010"}` |
| `reactome_search` | Reactome | Search pathways | `query` (str) | `{"query": "apoptosis"}` |
| `reactome_pathway` | Reactome | Get pathway by ID | `pathway_id` (str) | `{"pathway_id": "R-HSA-109581"}` |
| `wikipathways_search` | WikiPathways | Search pathways | `query` (str) | `{"query": "insulin"}` |
| `intact_interactions` | IntAct | Get molecular interactions | `query` (str) | `{"query": "TP53"}` |
| `pathbank_search` | PathBank | Search metabolic pathways | `query` (str) | `{"query": "amino acid"}` |

### Clinical Tools

| Tool | Database | Description | Parameters | Example |
|------|----------|-------------|------------|---------|
| `omim_search` | OMIM | Search genetic disorders | `query` (str) | `{"query": "breast cancer"}` |
| `drugbank_search` | DrugBank | Search drugs | `query` (str) | `{"query": "metformin"}` |
| `chembl_search` | ChEMBL | Search bioactive molecules | `query` (str) | `{"query": "kinase inhibitor"}` |
| `pharmgkb_gene` | PharmGKB | Get pharmacogenomics data | `gene` (str) | `{"gene": "CYP2D6"}` |
| `opentargets_disease` | OpenTargets | Get disease targets | `disease_id` (str) | `{"disease_id": "EFO_0000249"}` |
| `clinicaltrials_search` | ClinicalTrials.gov | Search clinical trials | `query` (str) | `{"query": "immunotherapy"}` |
| `fda_drug_label` | FDA | Get drug label info | `drug_name` (str) | `{"drug_name": "aspirin"}` |
| `bindingdb_search` | BindingDB | Search binding affinities | `target` (str) | `{"target": "kinase"}` |

### Cheminformatics Tools

| Tool | Database | Description | Parameters | Example |
|------|----------|-------------|------------|---------|
| `pubchem_search` | PubChem | Search compounds | `query` (str) | `{"query": "caffeine"}` |
| `pubchem_properties` | PubChem | Get compound properties | `cid` (str) | `{"cid": "2519"}` |
| `chemspider_search` | ChemSpider | Search compounds | `query` (str) | `{"query": "aspirin"}` |
| `zinc_search` | ZINC | Search purchasable compounds | `smiles` (str) | `{"smiles": "CC(=O)OC1=CC=CC=C1C(=O)O"}` |
| `rdkit_descriptors` | RDKit | Compute molecular descriptors | `smiles` (str) | `{"smiles": "CC(=O)OC1=CC=CC=C1C(=O)O"}` |
| `rdkit_substructure` | RDKit | Search substructure | `smarts` (str), `molecules` (list) | `{"smarts": "c1ccccc1", "molecules": ["...", "..."]}` |
| `docking_submit` | SwissDock | Submit docking job | `receptor_pdb` (str), `ligand_smiles` (str) | `{"receptor_pdb": "1HHO", "ligand_smiles": "..."}` |
| `admet_predict` | ADMET | Predict drug properties | `smiles` (str) | `{"smiles": "CC(=O)OC1=CC=CC=C1C(=O)O"}` |

### Ontologies Tools

| Tool | Database | Description | Parameters | Example |
|------|----------|-------------|------------|---------|
| `go_term_lookup` | Gene Ontology | Lookup GO term | `term_id` (str) | `{"term_id": "GO:0008150"}` |
| `go_search` | Gene Ontology | Search GO terms | `query` (str) | `{"query": "apoptosis"}` |
| `hpo_term_lookup` | HPO | Lookup phenotype term | `term_id` (str) | `{"term_id": "HP:0001250"}` |
| `disease_ontology_search` | Disease Ontology | Search diseases | `query` (str) | `{"query": "diabetes"}` |
| `chebi_search` | ChEBI | Search chemical entities | `query` (str) | `{"query": "glucose"}` |
| `uberon_search` | Uberon | Search anatomical terms | `query` (str) | `{"query": "heart"}` |

### Model Organisms Tools

| Tool | Database | Description | Parameters | Example |
|------|----------|-------------|------------|---------|
| `flybase_gene` | FlyBase | Get Drosophila gene | `gene_symbol` (str) | `{"gene_symbol": "w"}` |
| `wormbase_gene` | WormBase | Get C. elegans gene | `gene_name` (str) | `{"gene_name": "daf-2"}` |
| `sgd_gene` | SGD | Get yeast gene | `gene_name` (str) | `{"gene_name": "YAL001C"}` |
| `zfin_gene` | ZFIN | Get zebrafish gene | `gene_symbol` (str) | `{"gene_symbol": "tp53"}` |
| `mgi_gene` | MGI | Get mouse gene | `gene_symbol` (str) | `{"gene_symbol": "Brca1"}` |

For a complete list of all 155 tools, see the [Tool Schema](scripts/database-api-spec.json).

## Client Configuration

### Claude Code

After obtaining a token, register the MCP server:

```bash
source get-token.sh
claude mcp add --transport http open-life-sciences "$GATEWAY_URL" --header "Authorization: Bearer $MCP_TOKEN"
```

Or manually edit `~/.config/claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "open-life-sciences": {
      "type": "http",
      "url": "https://abc123.agentcore.us-west-2.amazonaws.com",
      "headers": {
        "Authorization": "Bearer eyJraWQiOiJ..."
      }
    }
  }
}
```

**Note**: Tokens expire after 60 minutes. Update the `Authorization` header when the token expires.

### Kiro

Add to `.kiro/config/mcp.json`:

```json
{
  "mcpServers": {
    "open-life-sciences": {
      "type": "http",
      "url": "https://abc123.agentcore.us-west-2.amazonaws.com",
      "headers": {
        "Authorization": "Bearer ${MCP_TOKEN}"
      }
    }
  }
}
```

Set the environment variable before launching Kiro:

```bash
source get-token.sh
kiro
```

### Amazon Quick MCP Client

Create a configuration file `mcp-config.json`:

```json
{
  "servers": {
    "open-life-sciences": {
      "url": "https://abc123.agentcore.us-west-2.amazonaws.com",
      "headers": {
        "Authorization": "Bearer eyJraWQiOiJ..."
      }
    }
  }
}
```

Run the client:

```bash
quick-mcp --config mcp-config.json
```

### Programmatic Python Client

Install the `mcp` library:

```bash
pip install mcp
```

Example usage:

```python
import asyncio
from mcp.client import MCPClient

async def main():
    # Create client
    client = MCPClient(
        url="https://abc123.agentcore.us-west-2.amazonaws.com",
        headers={
            "Authorization": "Bearer eyJraWQiOiJ..."
        }
    )
    
    # Connect
    await client.connect()
    
    # List available tools
    tools = await client.list_tools()
    print(f"Available tools: {len(tools)}")
    
    # Call a tool
    result = await client.call_tool(
        "uniprot_search",
        {
            "query": "BRCA1",
            "max_results": 5
        }
    )
    print(result)
    
    # Disconnect
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
```

**Token refresh example:**

```python
import boto3
import requests

def get_token(app_name: str, region: str) -> str:
    """Fetch OAuth2 token from Cognito."""
    ssm = boto3.client('ssm', region_name=region)
    
    # Retrieve config
    client_id = ssm.get_parameter(
        Name=f'/app/{app_name}/agentcore/machine_client_id'
    )['Parameter']['Value']
    
    client_secret = ssm.get_parameter(
        Name=f'/app/{app_name}/agentcore/cognito_secret',
        WithDecryption=True
    )['Parameter']['Value']
    
    cognito_domain = ssm.get_parameter(
        Name=f'/app/{app_name}/agentcore/cognito_domain'
    )['Parameter']['Value']
    
    auth_scope = ssm.get_parameter(
        Name=f'/app/{app_name}/agentcore/cognito_auth_scope'
    )['Parameter']['Value']
    
    # Request token
    response = requests.post(
        f"{cognito_domain}/oauth2/token",
        data={
            'grant_type': 'client_credentials',
            'client_id': client_id,
            'client_secret': client_secret,
            'scope': auth_scope
        }
    )
    
    return response.json()['access_token']

# Usage
token = get_token('open-life-sciences-tool', 'us-west-2')
```

## Cleanup

To delete all deployed resources:

### Step 1: Delete CloudFormation Stacks

Delete in reverse order of deployment:

```bash
# Replace with your app name if you used a custom name
APP_NAME="open-life-sciences-tool"
REGION="us-west-2"

# Delete AgentCore stack first
aws cloudformation delete-stack \
  --stack-name "${APP_NAME}-agentcore" \
  --region "$REGION"

aws cloudformation wait stack-delete-complete \
  --stack-name "${APP_NAME}-agentcore" \
  --region "$REGION"

# Delete Cognito stack
aws cloudformation delete-stack \
  --stack-name "${APP_NAME}-cognito" \
  --region "$REGION"

aws cloudformation wait stack-delete-complete \
  --stack-name "${APP_NAME}-cognito" \
  --region "$REGION"

# Delete Infrastructure stack
aws cloudformation delete-stack \
  --stack-name "${APP_NAME}-infra" \
  --region "$REGION"

aws cloudformation wait stack-delete-complete \
  --stack-name "${APP_NAME}-infra" \
  --region "$REGION"
```

### Step 2: Delete S3 Bucket

Empty and delete the S3 bucket:

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
BUCKET_NAME="${APP_NAME}-${REGION}-${ACCOUNT_ID}"

# Empty bucket
aws s3 rm "s3://${BUCKET_NAME}" --recursive --region "$REGION"

# Delete bucket
aws s3 rb "s3://${BUCKET_NAME}" --region "$REGION"
```

### Step 3: Delete SSM Parameters (Optional)

If you created optional API key parameters:

```bash
aws ssm delete-parameter --name "/app/${APP_NAME}/ncbi_api_key" --region "$REGION" 2>/dev/null || true
aws ssm delete-parameter --name "/app/${APP_NAME}/ncbi_email" --region "$REGION" 2>/dev/null || true
aws ssm delete-parameter --name "/app/${APP_NAME}/cosmic_api_key" --region "$REGION" 2>/dev/null || true
aws ssm delete-parameter --name "/app/${APP_NAME}/chemspider_api_key" --region "$REGION" 2>/dev/null || true
```

## Troubleshooting

### Missing AWS Credentials

**Error:**
```
❌ Error: Unable to determine AWS account ID. Please configure AWS CLI.
```

**Solution:**
```bash
aws configure
# Or set environment variables:
export AWS_ACCESS_KEY_ID="..."
export AWS_SECRET_ACCESS_KEY="..."
export AWS_REGION="us-west-2"
```

### Token Expired

**Error:**
```
401 Unauthorized
```

**Solution:**

Tokens expire after 60 minutes. Get a fresh token:

```bash
source get-token.sh
# Update your MCP client configuration with the new token
```

### CloudFormation Stack Failure

**Error:**
```
❌ Error deploying open-life-sciences-tool-infra:
CREATE_FAILED: Lambda execution role
```

**Solution:**

Check IAM permissions. The deploying user/role needs:
- `cloudformation:*`
- `lambda:*`
- `iam:CreateRole`, `iam:AttachRolePolicy`, `iam:PassRole`
- `s3:*`
- `ssm:PutParameter`, `ssm:GetParameter`
- `cognito-idp:*`
- `bedrock:*`

View detailed stack errors:

```bash
aws cloudformation describe-stack-events \
  --stack-name open-life-sciences-tool-infra \
  --region us-west-2 \
  --max-items 20
```

### Lambda Timeout

**Error:**
```
Task timed out after 300.00 seconds
```

**Solution:**

Some database queries (especially BLAST, large genomic regions) may exceed the 300-second timeout. Options:

1. Reduce the query scope (fewer results, smaller regions)
2. Increase Lambda timeout in `cfn/infrastructure.yaml`:
   ```yaml
   Timeout: 600  # Increase to 10 minutes
   ```
3. Redeploy:
   ```bash
   ./deploy.sh
   ```

### Missing API Key

**Error:**
```
{"error": "Missing NCBI_API_KEY"}
```

**Solution:**

Some databases require API keys. Configure them:

```bash
aws ssm put-parameter \
  --name '/app/open-life-sciences-tool/ncbi_api_key' \
  --value 'YOUR_KEY' \
  --type 'SecureString' \
  --overwrite
```

See the [Optional API Keys](#optional-api-keys) section for all supported keys.

### AgentCore Gateway Not Available in Region

**Error:**
```
AgentCore service is not available in region
```

**Solution:**

Deploy in a supported region:
- `us-east-1`
- `us-west-2`

Set the region before deploying:

```bash
export AWS_REGION=us-west-2
./deploy.sh
```

### Tool Schema Validation Error

**Error:**
```
Invalid OpenAPI schema
```

**Solution:**

Regenerate tool schemas:

```bash
cd scripts
python3 generate_tool_schema.py
cd ..
./deploy.sh
```

## FAQ

### Q: How much does this cost?

**A:** Costs depend on usage. Main components:
- **Lambda invocations**: $0.20 per 1M requests + $0.0000166667 per GB-second
- **Cognito**: First 50,000 MAUs free, then $0.0055 per MAU
- **AgentCore Gateway**: Contact AWS for pricing
- **S3 storage**: $0.023 per GB-month (minimal for code/schemas)
- **External API costs**: Some databases (COSMIC, DrugBank) require paid subscriptions

Typical usage (100 queries/day, 5-second average Lambda execution): **~$5-10/month**

### Q: Can I deploy multiple instances?

**A:** Yes. Use different app names:

```bash
./deploy.sh dev-lifesci-app
./deploy.sh prod-lifesci-app
```

Each instance has isolated resources (S3 bucket, Cognito, Gateway endpoint).

### Q: How do I update Lambda code?

**A:** Redeploy with the same app name:

```bash
./deploy.sh
```

CloudFormation will update existing stacks. The hash-based S3 key ensures Lambda picks up new code.

### Q: Can I add custom tools?

**A:** Yes. Two approaches:

1. **Add to existing Lambda**: Edit `database-lambda/lambda_function.py` and add tool definitions
2. **Create new Lambda**: Follow the pattern in `cfn/infrastructure.yaml` to add a third Lambda function

After changes, redeploy:

```bash
./deploy.sh
```

### Q: Which databases don't require API keys?

**A:** Most databases are free to query:
- UniProt, PDB, Ensembl, ClinVar, gnomAD, dbSNP
- KEGG, Reactome, WikiPathways
- PubChem, AlphaFold DB
- Gene Ontology, HPO, Disease Ontology

**Require API keys**:
- NCBI (optional, higher rate limits)
- COSMIC (cancer mutations)
- ChemSpider (chemistry)
- DrugBank (full access)
- OMIM (full access)

### Q: How do I monitor usage?

**A:** Use CloudWatch Logs and Metrics:

```bash
# View Lambda logs
aws logs tail /aws/lambda/open-life-sciences-tool-database --follow

# View Lambda metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value=open-life-sciences-tool-database \
  --start-time 2024-01-01T00:00:00Z \
  --end-time 2024-01-02T00:00:00Z \
  --period 3600 \
  --statistics Sum
```

### Q: Can I use this with non-AWS AI assistants?

**A:** Yes. The MCP Gateway is a standard HTTP endpoint. Any client that can:
1. Obtain an OAuth2 token from Cognito
2. Send HTTP requests with `Authorization` header
3. Parse JSON responses

...can use this server. Examples: custom Python scripts, LangChain agents, browser-based UIs.

### Q: How do I contribute improvements?

**A:** This integration follows the patterns in [amazon-bedrock-agents-healthcare-lifesciences](https://github.com/aws-samples/amazon-bedrock-agents-healthcare-lifesciences). Contributions welcome via pull requests.

### Q: What if a database API changes?

**A:** The underlying MCP server implementations are maintained in the [kiro-life-sciences](https://github.com/kiro-mcp/kiro-life-sciences) repository. Database client updates are synced from there. To update:

1. Pull latest kiro-life-sciences code
2. Copy updated server modules to `database-lambda/`
3. Redeploy: `./deploy.sh`

### Q: Can I disable specific tools?

**A:** Yes. Edit `database-lambda/lambda_function.py` and comment out the server module import:

```python
# from life_sciences_cosmic.server import COSMICServer  # Disable COSMIC
```

Regenerate tool schemas:

```bash
cd scripts
python3 generate_tool_schema.py
cd ..
./deploy.sh
```

The disabled tools will no longer appear in the Gateway target.

