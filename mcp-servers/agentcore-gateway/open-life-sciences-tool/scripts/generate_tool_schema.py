#!/usr/bin/env python3
"""
Tool Schema Generator for Open Life Sciences MCP server.

This script generates MCP tool schema JSON from MCP Tool definitions
across all life sciences database modules (genomics, proteomics, structural, etc.).

The generated schemas are used by AWS AgentCore Gateway to:
1. Validate incoming tool invocation requests
2. Enable AI assistants to discover available tools and their parameters
3. Provide structured documentation for the MCP endpoint

**Validates**: Requirements R6 (Tool Schema Generation), R12 (Parser and Tool Schema Round-Trip)
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, List


def generate_mcp_tool_schema(
    tools: List[Any],
    title: str = "MCP Tools",
    description: str = "MCP tool definitions"
) -> List[Dict[str, Any]]:
    """
    Convert MCP Tool definitions to AWS AgentCore Gateway tool schema format.
    
    This function transforms MCP Tool objects into the tool schema format expected
    by AWS AgentCore Gateway Lambda targets. The format is a direct array of tool
    definition objects (not wrapped in a "tools" key), matching the InlinePayload
    structure defined in AWS::BedrockAgentCore::GatewayTarget ToolSchema.
    
    When stored in S3 and referenced via ToolSchema.S3.Uri, the JSON file must
    contain the array directly at the root level.
    
    Args:
        tools: List of MCP Tool objects with name, description, and inputSchema attributes
        title: Schema title (for metadata only, not included in output)
        description: Schema description (for metadata only, not included in output)
    
    Returns:
        Array of tool definition dicts, each with name, description, and inputSchema
    
    **Validates**: R6.1, R6.2 (Define operations and parameters for each tool)
    """
    tool_list = []
    
    for tool in tools:
        # Each tool definition matches AWS::BedrockAgentCore::GatewayTarget ToolDefinition
        tool_obj = {
            "name": tool.name,
            "description": tool.description,
            "inputSchema": tool.inputSchema
        }
        tool_list.append(tool_obj)
    
    # Return array directly (not wrapped in "tools" key) for S3-based tool schema
    return tool_list


def validate_mcp_schema(schema: List[Dict[str, Any]]) -> bool:
    """
    Validate that the generated AWS AgentCore Gateway tool schema is well-formed.
    
    This function performs basic structural validation:
    1. Schema is a non-empty array of tool definitions
    2. Each tool has required fields (name, description, inputSchema)
    3. All tool names are unique (no duplicates)
    4. Input schemas are valid JSON Schema objects
    
    Args:
        schema: Array of tool definition dicts (AWS AgentCore Gateway format)
    
    Returns:
        True if validation passes
    
    Raises:
        ValueError: If validation fails with descriptive error message
    
    **Validates**: R6.6, R12.4 (Schema validation and error handling)
    """
    # Check schema is an array
    if not isinstance(schema, list):
        raise ValueError("Tool schema must be an array of tool definitions")
    
    if len(schema) == 0:
        raise ValueError("No tools defined in schema")
    
    # Track tool names to ensure uniqueness
    tool_names = set()
    
    # Validate each tool
    for i, tool in enumerate(schema):
        if not isinstance(tool, dict):
            raise ValueError(f"Tool at index {i} must be an object")
        
        # Check required tool fields
        required_fields = ['name', 'description', 'inputSchema']
        for field in required_fields:
            if field not in tool:
                raise ValueError(f"Tool at index {i} missing required field: {field}")
        
        # Check for duplicate tool names
        tool_name = tool['name']
        if tool_name in tool_names:
            raise ValueError(
                f"Duplicate tool name '{tool_name}' found. "
                f"All tool names must be unique."
            )
        tool_names.add(tool_name)
        
        # Validate inputSchema is an object
        input_schema = tool['inputSchema']
        if not isinstance(input_schema, dict):
            raise ValueError(f"Tool '{tool_name}' inputSchema must be an object")
        
        # Basic JSON Schema validation - check for 'type' field
        if 'type' not in input_schema:
            raise ValueError(f"Tool '{tool_name}' inputSchema missing 'type' field")
    
    print(f"✅ Schema validation passed: {len(schema)} tools validated, all tool names unique")
    return True


def parse_tool_schema(json_str: str) -> List[Dict[str, Any]]:
    """
    Parse a Tool Schema JSON string into a structured Python object.
    
    This function implements the parsing step of the round-trip requirement,
    converting JSON text into a Python list with validation.
    
    Args:
        json_str: JSON string representation of AWS AgentCore Gateway tool schema
    
    Returns:
        Parsed schema as Python list of tool definitions
    
    Raises:
        ValueError: If JSON is malformed or validation fails
    
    **Validates**: R12.1, R12.4 (Parser implementation and error handling)
    """
    try:
        schema = json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}")
    
    # Validate the parsed schema
    validate_mcp_schema(schema)
    
    return schema


def pretty_print_tool_schema(schema: List[Dict[str, Any]]) -> str:
    """
    Format a Tool Schema array as pretty-printed JSON.
    
    This function implements the serialization step of the round-trip requirement,
    converting a Python list back into formatted JSON with consistent
    indentation and field ordering for version control readability.
    
    Args:
        schema: Array of tool definition dicts (AWS AgentCore Gateway format)
    
    Returns:
        Formatted JSON string
    
    **Validates**: R12.2, R12.5 (Pretty printer with consistent formatting)
    """
    return json.dumps(schema, indent=2, sort_keys=False, ensure_ascii=False)


def round_trip_test(schema: List[Dict[str, Any]]) -> bool:
    """
    Test round-trip parsing and serialization of a Tool Schema.
    
    This function verifies that: parse(print(schema)) produces equivalent structure.
    
    Args:
        schema: Original AWS AgentCore Gateway tool schema (array of tool definitions)
    
    Returns:
        True if round-trip test passes
    
    Raises:
        AssertionError: If round-trip produces different structure
    
    **Validates**: R12.3 (Round-trip preservation)
    """
    # Serialize to JSON
    json_str = pretty_print_tool_schema(schema)
    
    # Parse back to list
    parsed_schema = parse_tool_schema(json_str)
    
    # Compare structures
    if schema != parsed_schema:
        raise AssertionError("Round-trip test failed: parsed schema differs from original")
    
    print("✅ Round-trip test passed")
    return True


def main():
    """
    Generate Tool Schema JSON files from MCP server TOOLS definitions.
    
    This script:
    1. Imports TOOLS lists from all 24 MCP server modules
    2. Converts each tool to MCP tool schema format
    3. Validates the generated schema
    4. Tests round-trip parsing/serialization
    5. Outputs formatted JSON files
    
    **Validates**: R6 (Tool Schema Generation), R12 (Round-trip parsing)
    """
    print("📝 Generating MCP Tool Schema specifications...")
    print()
    
    # Note: This is a standalone script that doesn't import the actual MCP server modules
    # In a real deployment, the database-lambda package would include all modules
    # For now, we create mock tool objects to demonstrate the schema generation
    
    # Mock Tool class (mimics mcp.types.Tool structure)
    class MockTool:
        def __init__(self, name: str, description: str, input_schema: Dict[str, Any]):
            self.name = name
            self.description = description
            self.inputSchema = input_schema
    
    # Create sample tools representing each category
    sample_tools = [
        # Proteomics
        MockTool(
            name="uniprot_search",
            description="Search UniProt by protein or gene name.",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Protein or gene name to search for."
                    },
                    "max_results": {
                        "type": "integer",
                        "default": 10,
                        "description": "Maximum results to return."
                    }
                },
                "required": ["query"]
            }
        ),
        MockTool(
            name="uniprot_fetch",
            description="Fetch a full protein record by UniProt accession.",
            input_schema={
                "type": "object",
                "properties": {
                    "accession": {
                        "type": "string",
                        "description": "UniProt accession (e.g. 'P04637')."
                    }
                },
                "required": ["accession"]
            }
        ),
        # Structural Biology
        MockTool(
            name="pdb_search",
            description="Search PDB structures by keyword.",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query string (e.g. 'hemoglobin', 'kinase')."
                    },
                    "max_results": {
                        "type": "integer",
                        "default": 10,
                        "description": "Maximum results to return."
                    }
                },
                "required": ["query"]
            }
        ),
        # Genomics
        MockTool(
            name="ncbi_search",
            description="Search any NCBI database via Entrez esearch.",
            input_schema={
                "type": "object",
                "properties": {
                    "database": {
                        "type": "string",
                        "description": "NCBI database name (e.g. 'gene', 'nucleotide', 'protein')."
                    },
                    "term": {
                        "type": "string",
                        "description": "Search query string."
                    },
                    "max_results": {
                        "type": "integer",
                        "default": 20,
                        "description": "Maximum results to return."
                    }
                },
                "required": ["database", "term"]
            }
        ),
        MockTool(
            name="clinvar_search",
            description="Search ClinVar by rsID, HGVS notation, or gene name.",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search term (rsID, HGVS, or gene name)."
                    },
                    "max_results": {
                        "type": "integer",
                        "default": 10,
                        "description": "Maximum results."
                    }
                },
                "required": ["query"]
            }
        ),
        # Cheminformatics
        MockTool(
            name="pubchem_search",
            description="Search PubChem compounds by name or SMILES.",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Compound name or SMILES string."
                    },
                    "max_results": {
                        "type": "integer",
                        "default": 10,
                        "description": "Maximum results to return."
                    }
                },
                "required": ["query"]
            }
        ),
        # Clinical
        MockTool(
            name="drugbank_search",
            description="Search DrugBank for drug information.",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Drug name or identifier."
                    }
                },
                "required": ["query"]
            }
        ),
    ]
    
    print(f"📊 Processing {len(sample_tools)} sample tools...")
    print("   (In production, this would import from all 24 MCP server modules)")
    print()
    
    # Generate AWS AgentCore Gateway tool schema (array format for S3 storage)
    database_schema = generate_mcp_tool_schema(
        tools=sample_tools,
        title="Open Life Sciences Database Tools",
        description=(
            "100+ life sciences database query tools across genomics, proteomics, "
            "structural biology, cheminformatics, pathways, clinical research, and more."
        )
    )
    
    # Validate schema
    try:
        validate_mcp_schema(database_schema)
    except ValueError as e:
        print(f"❌ Schema validation failed: {e}")
        sys.exit(1)
    
    # Test round-trip parsing
    try:
        round_trip_test(database_schema)
    except AssertionError as e:
        print(f"❌ Round-trip test failed: {e}")
        sys.exit(1)
    
    # Output schema to file
    output_file = "database-api-spec.json"
    with open(output_file, "w") as f:
        f.write(pretty_print_tool_schema(database_schema))
    
    print()
    print(f"✅ Generated: {output_file}")
    print(f"   Tools: {len(sample_tools)}")
    print(f"   Format: AWS AgentCore Gateway tool schema (array for S3 ToolSchema.S3.Uri)")
    print(f"   Size: {Path(output_file).stat().st_size:,} bytes")
    print()
    print("📝 Note: This is a demonstration with sample tools.")
    print("   In production deployment, this script will:")
    print("   - Import TOOLS from all 24 MCP server modules")
    print("   - Generate separate schemas for database and literature tools")
    print("   - Include 100+ tools across all categories")


if __name__ == "__main__":
    main()
