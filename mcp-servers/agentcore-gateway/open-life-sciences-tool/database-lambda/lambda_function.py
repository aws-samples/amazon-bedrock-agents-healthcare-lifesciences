"""
Lambda handler for Open Life Sciences database tools.

This Lambda function routes MCP tool invocations to the appropriate
life sciences database MCP server modules (genomics, proteomics, etc.).

The handler implements a dynamic tool registry that:
1. Discovers tools from MCP server modules at initialization
2. Routes incoming tool invocations to the appropriate server instance
3. Handles errors with appropriate HTTP status codes
4. Retrieves credentials from SSM Parameter Store when needed
"""

import asyncio
import importlib
import json
import logging
import os
from functools import lru_cache
from typing import Any

import boto3

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# SSM client for credential retrieval
ssm = boto3.client('ssm')
APP_NAME = os.environ.get('APP_NAME', 'open-life-sciences-tool')


# ---------------------------------------------------------------------------
# Credential Management
# ---------------------------------------------------------------------------


@lru_cache(maxsize=128)
def get_credential(key_name: str, required: bool = False) -> str | None:
    """
    Retrieve credential from SSM Parameter Store with caching.
    
    Args:
        key_name: Name of the credential key (e.g., 'ncbi_api_key')
        required: If True, raises ValueError when credential is missing
    
    Returns:
        Credential value or None if not found and not required
    
    Raises:
        ValueError: If required=True and credential is not found
    """
    param_name = f'/app/{APP_NAME}/credentials/{key_name}'
    
    try:
        response = ssm.get_parameter(Name=param_name, WithDecryption=True)
        return response['Parameter']['Value']
    except ssm.exceptions.ParameterNotFound:
        if required:
            raise ValueError(
                f"Required credential {key_name} not found. "
                f"Set it with: aws ssm put-parameter --name '{param_name}' "
                f"--value 'YOUR_KEY' --type SecureString"
            )
        return None
    except Exception as e:
        logger.error(f"Error retrieving credential {key_name}: {e}")
        if required:
            raise
        return None


# ---------------------------------------------------------------------------
# Tool Registry
# ---------------------------------------------------------------------------


class ToolRegistry:
    """
    Dynamic tool registry built from enabled MCP server modules.
    
    The registry imports server modules at initialization, instantiates
    server classes, and builds a mapping from tool names to server instances.
    This allows flexible deployment with subsets of available modules.
    """
    
    # Configuration: which modules to include in this deployment
    # This can be customized for selective deployment
    ENABLED_MODULES = [
        'life_sciences_genomics',
        'life_sciences_proteomics',
        'life_sciences_structural',
        'life_sciences_cheminformatics',
        'life_sciences_pathways',
        'life_sciences_ontologies',
        'life_sciences_clinical',
        'life_sciences_agriculture',
        'life_sciences_aiml',
        'life_sciences_biobanking',
        'life_sciences_cellbiology',
        'life_sciences_cloud',
        'life_sciences_datastandards',
        'life_sciences_ecology',
        'life_sciences_epigenomics',
        'life_sciences_healthcare',
        'life_sciences_imaging',
        'life_sciences_immunology',
        'life_sciences_metabolomics',
        'life_sciences_microbiology',
        'life_sciences_model_organisms',
        'life_sciences_molbio',
        'life_sciences_neuroscience',
        'life_sciences_pipelines',
    ]
    
    def __init__(self):
        """Initialize the tool registry by loading enabled modules."""
        self.servers = {}
        self.tool_to_server = {}
        self._initialize()
        
        logger.info(
            f"Tool registry initialized with {len(self.tool_to_server)} tools "
            f"from {len(self.servers)} server modules"
        )
    
    def _initialize(self) -> None:
        """Import enabled modules and build tool → server mapping."""
        for module_name in self.ENABLED_MODULES:
            try:
                self._load_module(module_name)
            except Exception as e:
                logger.warning(f"Failed to load module {module_name}: {e}")
    
    def _load_module(self, module_name: str) -> None:
        """
        Load a single MCP server module and register its tools.
        
        Args:
            module_name: Python module name (e.g., 'life_sciences_genomics')
        """
        # Import server module
        server_module = importlib.import_module(f'{module_name}.server')
        
        # Get server class name (e.g., life_sciences_genomics → GenomicsServer)
        server_class_name = self._get_server_class_name(module_name)
        server_class = getattr(server_module, server_class_name)
        
        # Instantiate server
        server_instance = server_class()
        self.servers[module_name] = server_instance
        
        # Register tools from this server
        tools = server_module.TOOLS
        for tool in tools:
            self.tool_to_server[tool.name] = server_instance
        
        logger.info(f"Loaded module {module_name} with {len(tools)} tools")
    
    @staticmethod
    def _get_server_class_name(module_name: str) -> str:
        """
        Convert module name to server class name.
        
        Examples:
            life_sciences_genomics → GenomicsServer
            life_sciences_proteomics → ProteomicsServer
        
        Args:
            module_name: Module name with underscores
        
        Returns:
            PascalCase server class name
        """
        # Remove 'life_sciences_' prefix
        parts = module_name.replace('life_sciences_', '').split('_')
        # Capitalize each part and join
        return ''.join(p.capitalize() for p in parts) + 'Server'
    
    def get_server(self, tool_name: str):
        """
        Retrieve server instance for given tool name.
        
        Args:
            tool_name: Name of the MCP tool
        
        Returns:
            Server instance or None if tool not found
        """
        return self.tool_to_server.get(tool_name)
    
    def list_tools(self) -> list[str]:
        """
        Get list of all available tool names.
        
        Returns:
            List of tool names
        """
        return list(self.tool_to_server.keys())


# ---------------------------------------------------------------------------
# Global Registry
# ---------------------------------------------------------------------------

# Initialize registry at Lambda cold start
# This happens once per container and is reused across invocations
try:
    REGISTRY = ToolRegistry()
    logger.info("Tool registry initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize tool registry: {e}")
    REGISTRY = None


# ---------------------------------------------------------------------------
# Lambda Handler
# ---------------------------------------------------------------------------


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """
    Handle MCP tool invocation from AgentCore Gateway.
    
    This handler:
    1. Extracts tool name and arguments from the event
    2. Routes the request to the appropriate MCP server instance
    3. Executes the tool asynchronously
    4. Returns results in JSON format
    5. Handles errors with appropriate HTTP status codes
    
    Args:
        event: Lambda event containing:
            - toolName: Name of the MCP tool to invoke
            - arguments: Tool-specific parameters
        context: Lambda context object
    
    Returns:
        Response dict with:
            - statusCode: HTTP status code (200, 400, 404, 500, etc.)
            - body: JSON-encoded response or error message
    
    Error Status Codes:
        - 404: Unknown tool name
        - 401: Missing required credential
        - 400: Invalid parameters
        - 500: Internal server error
        - 503: Database timeout or network error
    """
    # Check if registry initialization failed
    if REGISTRY is None:
        logger.error("Tool registry not initialized")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Tool registry initialization failed'
            })
        }
    
    # Extract tool name and arguments
    tool_name = event.get('toolName')
    arguments = event.get('arguments', {})
    
    logger.info(f"Invoking tool: {tool_name} with arguments: {arguments}")
    
    # Validate tool name
    if not tool_name:
        return {
            'statusCode': 400,
            'body': json.dumps({
                'error': 'Missing required field: toolName'
            })
        }
    
    # Get server instance for this tool
    server = REGISTRY.get_server(tool_name)
    if server is None:
        available_tools = REGISTRY.list_tools()
        logger.warning(
            f"Unknown tool: {tool_name}. "
            f"Available tools: {', '.join(available_tools[:10])}..."
        )
        return {
            'statusCode': 404,
            'body': json.dumps({
                'error': f'Unknown tool: {tool_name}',
                'available_tools_count': len(available_tools)
            })
        }
    
    # Execute tool asynchronously
    try:
        result = asyncio.run(_call_tool(server, tool_name, arguments))
        
        return {
            'statusCode': 200,
            'body': json.dumps(result, default=str)
        }
        
    except ValueError as e:
        # Credential or validation errors
        logger.error(f"Validation error for {tool_name}: {e}")
        return {
            'statusCode': 401 if 'credential' in str(e).lower() else 400,
            'body': json.dumps({
                'error': str(e)
            })
        }
        
    except TimeoutError as e:
        logger.error(f"Timeout error for {tool_name}: {e}")
        return {
            'statusCode': 503,
            'body': json.dumps({
                'error': f'Database timeout: {str(e)}'
            })
        }
        
    except Exception as e:
        logger.error(f"Error executing {tool_name}: {e}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': f'Internal error: {str(e)}'
            })
        }


async def _call_tool(server, tool_name: str, arguments: dict[str, Any]) -> Any:
    """
    Execute a tool on the given server instance.
    
    This is a wrapper to properly handle async tool execution.
    
    Args:
        server: MCP server instance
        tool_name: Name of the tool to call
        arguments: Tool parameters
    
    Returns:
        Tool execution result
    """
    # Get the dispatch table from the server
    if not hasattr(server, '_dispatch'):
        raise ValueError(f"Server for {tool_name} does not have dispatch table")
    
    dispatch = server._dispatch
    
    if tool_name not in dispatch:
        raise ValueError(f"Tool {tool_name} not found in server dispatch table")
    
    # Call the tool handler
    tool_handler = dispatch[tool_name]
    result = await tool_handler(arguments)
    
    return result
