# Design for UniProt Protein Search Agent

## Architecture Overview

The UniProt Protein Search Agent follows the standard AWS Healthcare and Life Sciences Agent Toolkit pattern with:

- **Amazon Bedrock Agent**: Core conversational AI using Claude 3.5 Sonnet v2
- **Action Groups**: Lambda functions that interface with UniProt APIs
- **CloudFormation Template**: Infrastructure as Code for deployment
- **IAM Roles**: Secure access management

## Component Design

### 1. Bedrock Agent Configuration

**Model**: `anthropic.claude-3-5-sonnet-20241022-v2:0` (Claude 3.5 Sonnet v2)

**Instructions**: Specialized prompt for protein research and UniProt data interpretation

**Action Groups**:
- `UniProtSearch`: Handles protein search functionality
- `UniProtDetails`: Handles detailed protein information retrieval

### 2. Action Group: UniProtSearch

**Purpose**: Search for proteins in the UniProt database

**Lambda Function**: `uniprot-search-function`

**API Schema**:
```json
{
  "name": "search_proteins",
  "description": "Search for proteins in the UniProt database",
  "inputSchema": {
    "type": "object",
    "properties": {
      "query": { "type": "string", "description": "Search query for proteins" },
      "organism": { "type": "string", "description": "Optional organism filter" },
      "limit": { "type": "integer", "description": "Maximum results (default: 10, max: 50)" }
    },
    "required": ["query"]
  }
}
```

**UniProt API Integration**:
- Endpoint: `https://rest.uniprot.org/uniprotkb/search`
- Parameters: 
  - `query`: Constructed search query
  - `format`: json
  - `size`: Result limit
  - `fields`: accession,id,protein_name,gene_names,organism_name,length

### 3. Action Group: UniProtDetails

**Purpose**: Retrieve detailed information for specific proteins

**Lambda Function**: `uniprot-details-function`

**API Schema**:
```json
{
  "name": "get_protein_details",
  "description": "Get comprehensive protein information by accession ID",
  "inputSchema": {
    "type": "object",
    "properties": {
      "accession_id": { "type": "string", "description": "UniProtKB accession ID" },
      "include_sequence": { "type": "boolean", "description": "Include amino acid sequence" },
      "include_features": { "type": "boolean", "description": "Include protein features" }
    },
    "required": ["accession_id"]
  }
}
```

**UniProt API Integration**:
- Endpoint: `https://rest.uniprot.org/uniprotkb/{accession_id}`
- Parameters:
  - `format`: json
  - `fields`: Comprehensive field list based on request parameters

## Data Flow

### Search Flow
1. User asks about proteins (e.g., "proteins associated with diabetes")
2. Bedrock Agent processes natural language query
3. Agent calls `search_proteins` action with appropriate search terms
4. Lambda function constructs UniProt API query
5. UniProt API returns search results
6. Lambda function processes and formats results
7. Agent presents results to user with accession IDs and basic info

### Detail Retrieval Flow
1. User requests details for specific protein or agent identifies protein of interest
2. Agent calls `get_protein_details` with accession ID
3. Lambda function queries UniProt API for comprehensive protein data
4. UniProt API returns detailed protein information
5. Lambda function processes and structures the data
6. Agent presents formatted protein information to user

## API Integration Details

### UniProt REST API Endpoints

**Search Endpoint**:
```
GET https://rest.uniprot.org/uniprotkb/search
Parameters:
- query: Search terms (protein name, gene, disease, etc.)
- format: json
- size: Number of results
- fields: Comma-separated list of fields to return
```

**Entry Endpoint**:
```
GET https://rest.uniprot.org/uniprotkb/{accession}
Parameters:
- format: json
- fields: Comma-separated list of fields to return
```

### Query Construction

**Search Queries**:
- Basic protein name: `protein_name:"insulin"`
- Disease association: `cc_disease:"diabetes"`
- Organism filter: `organism_name:"Homo sapiens"`
- Combined: `(protein_name:"insulin" OR gene:"INS") AND organism_name:"Homo sapiens"`

**Field Selection**:
- Basic fields: `accession,id,protein_name,gene_names,organism_name,length`
- Detailed fields: `accession,id,protein_name,gene_names,organism_name,length,cc_function,cc_subcellular_location,cc_disease,ft_domain,sequence`

## Error Handling

### API Error Scenarios
1. **Invalid Accession ID**: Return user-friendly error message
2. **Network Timeout**: Implement retry logic with exponential backoff
3. **Rate Limiting**: Handle 429 responses with appropriate delays
4. **API Unavailable**: Graceful degradation with informative messages

### Validation
- Accession ID format validation (UniProt format: [A-Z0-9]{6,10})
- Search query sanitization
- Parameter bounds checking (limit values)

## Security Considerations

### IAM Permissions
- Lambda execution role with minimal required permissions
- CloudWatch Logs access for monitoring
- No additional AWS service permissions needed (external API only)

### Data Handling
- No sensitive data storage (UniProt is public)
- Standard HTTPS for API communications
- No user data persistence

## Performance Considerations

### Caching Strategy
- Consider implementing response caching for frequently requested proteins
- Cache search results for common queries
- TTL-based cache invalidation

### Rate Limiting
- Respect UniProt API rate limits
- Implement client-side rate limiting if needed
- Use appropriate User-Agent headers

### Optimization
- Efficient field selection to minimize response size
- Parallel requests for multiple protein details when appropriate
- Connection pooling for HTTP requests

## Monitoring and Logging

### CloudWatch Metrics
- Lambda function duration and errors
- API call success/failure rates
- User interaction patterns

### Logging Strategy
- Structured logging with correlation IDs
- API request/response logging (excluding large sequences)
- Error tracking and alerting

## Deployment Architecture

### CloudFormation Resources
- `AWS::Bedrock::Agent`: Main agent configuration
- `AWS::Bedrock::AgentAlias`: Agent alias for versioning
- `AWS::Lambda::Function`: Two functions for action groups
- `AWS::IAM::Role`: Lambda execution roles
- `AWS::Logs::LogGroup`: CloudWatch log groups

### Parameters
- `AgentName`: Name for the Bedrock agent
- `AgentAliasName`: Alias name (default: "Latest")
- `AgentIAMRoleArn`: IAM role for Bedrock agent
- `S3CodeBucket`: S3 bucket for Lambda code storage

## Future Enhancements

### Potential Improvements
1. **Protein Structure Integration**: Add PDB structure information
2. **Pathway Analysis**: Integrate with pathway databases
3. **Sequence Analysis**: Add sequence similarity search
4. **Visualization**: Generate protein domain diagrams
5. **Cross-Database Search**: Integrate with other protein databases
