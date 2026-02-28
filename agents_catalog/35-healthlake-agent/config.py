"""
Configuration module for NLQ Member Services Assistant.
Loads configuration from environment variables.
"""

import os
from dataclasses import dataclass
from typing import List
from dotenv import load_dotenv

# Load environment variables from .env file (for local development)
# In AgentCore container runtime, environment variables are already set
load_dotenv()

def get_env(key: str, default: str = '') -> str:
    """
    Get environment variable with fallback.
    Prioritizes os.environ (container runtime) over os.getenv (.env file).
    """
    return os.environ.get(key) or os.getenv(key, default)


@dataclass
class HealthLakeConfig:
    """HealthLake configuration"""
    datastore_id: str
    region: str
    endpoint: str
    max_retries: int = 3
    timeout_ms: int = 30000


@dataclass
class BedrockConfig:
    """Bedrock configuration"""
    model_id: str
    region: str
    max_tokens: int = 4096
    temperature: float = 0.7


@dataclass
class StrandsConfig:
    """Strands Agent configuration"""
    bedrock_config: BedrockConfig
    healthlake_config: HealthLakeConfig
    system_prompt: str
    enable_telemetry: bool = True
    telemetry_exporters: List[str] = None

    def __post_init__(self):
        if self.telemetry_exporters is None:
            self.telemetry_exporters = ['cloudwatch', 'xray', 'stdout']


@dataclass
class CacheConfig:
    """Cache configuration"""
    session_duration_minutes: int = 60
    patient_cache_ttl_minutes: int = 5
    max_cache_size: int = 1000


@dataclass
class AgentCoreConfig:
    """
    AgentCore Runtime configuration.
    
    Validates: Requirements 1.1, 3.1
    
    Configuration:
    - runtime_name: "nlq-member-services"
    - timeout_seconds: 300 (5 minutes for complex queries)
    - memory_mb: 2048 (2GB for LLM operations)
    - enable_streaming: True (for real-time response streaming)
    - enable_async: True (for asynchronous processing)
    - max_concurrent_sessions: 100 (concurrent user sessions)
    """
    runtime_name: str
    timeout_seconds: int = 300
    memory_mb: int = 2048
    enable_streaming: bool = True
    enable_async: bool = True
    max_concurrent_sessions: int = 100


# Load configuration from environment variables
def load_config() -> dict:
    """Load configuration from environment variables"""
    
    # AWS Region - prioritize container environment
    aws_region = get_env('AWS_REGION', 'us-east-1')
    
    # HealthLake Configuration
    healthlake_config = HealthLakeConfig(
        datastore_id=get_env('HEALTHLAKE_DATASTORE_ID', '61ca59304e77c5cebe78aabe9476bccf'),
        region=aws_region,
        endpoint=f"https://healthlake.{aws_region}.amazonaws.com"
    )
    
    # Bedrock Configuration
    bedrock_config = BedrockConfig(
        model_id=get_env('BEDROCK_MODEL_ID', 'us.anthropic.claude-3-5-sonnet-20241022-v2:0'),
        region=aws_region,
        max_tokens=int(get_env('BEDROCK_MAX_TOKENS', '4096')),
        temperature=float(get_env('BEDROCK_TEMPERATURE', '0.7'))
    )
    
    # AgentCore Configuration
    agentcore_config = AgentCoreConfig(
        runtime_name=get_env('AGENTCORE_RUNTIME_NAME', 'healthlake-agent'),
        timeout_seconds=int(get_env('AGENTCORE_TIMEOUT_SECONDS', '300')),
        memory_mb=int(get_env('AGENTCORE_MEMORY_MB', '2048'))
    )
    
    # Cache Configuration
    cache_config = CacheConfig()
    
    # Debug mode
    debug = get_env('DEBUG', 'false').lower() == 'true'
    
    # IAM Role ARNs
    healthlake_access_role_arn = get_env('HEALTHLAKE_ACCESS_ROLE_ARN', '')
    
    return {
        'healthlake': healthlake_config,
        'bedrock': bedrock_config,
        'agentcore': agentcore_config,
        'cache': cache_config,
        'debug': debug,
        'aws_region': aws_region,
        'healthlake_access_role_arn': healthlake_access_role_arn,
        'dynamodb_table': get_env('DYNAMODB_INTERACTION_LOGS_TABLE', 'nlq-interaction-logs'),
        'log_level': get_env('LOG_LEVEL', 'INFO')
    }


# Global configuration instance
CONFIG = load_config()
