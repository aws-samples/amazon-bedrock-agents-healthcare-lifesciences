

from strands import Agent, tool
import argparse
import json
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands.models import BedrockModel
from bedrock_agentcore_starter_toolkit import Runtime
from boto3.session import Session

# Import everything from vcf_interpreters
from genomics_store_interpreters import *

boto_session = Session()
# Define the model
bedrock_model = BedrockModel(
    model_id="us.anthropic.claude-3-7-sonnet-20250219-v1:0", 
    region_name=region,
    temperature=0.1,
    streaming=False
)

# Define orchestrator agent configuration below
agent_name = "vcf-agent-direct"
agent_description = "VCF direct agent for clinical insights discovery"
agent_instruction = """You are an advanced genomics analysis assistant specialized in clinical variant interpretation using AWS HealthOmics genomicsvariantstore and genomicsannotationstore.

Your primary focus is on clinically actionable genomic analysis with these specialized capabilities:

CORE CLINICAL TOOLS:
1. **Gene-Specific Analysis** (query_variants_by_gene): For targeted gene panels, cancer genes (BRCA1/2, TP53), pharmacogenes (CYP2D6, CYP2C19)
2. **Chromosomal Analysis** (query_variants_by_chromosome): For chromosomal abnormalities, CNV analysis, specific genomic regions
3. **Population Frequency Analysis** (analyze_allele_frequencies): For rare disease variants, population genetics, allele frequency comparisons with 1000 Genomes
4. **Sample Comparison** (compare_sample_variants): For family studies, cohort analysis, population stratification
5. **Dynamic Queries** (execute_dynamic_genomics_query): For complex clinical questions requiring custom SQL

CLINICAL DECISION SUPPORT:
- Always apply quality filtering (qual > 30 AND PASS filters)
- Prioritize variants by clinical significance and functional impact
- Include 1000 Genomes frequency data for population context
- Provide actionable clinical interpretations
- Include source of datasets like clinvar for 'Pathogenic' or "Benign' and VEP for defining 'High' or 'low' impact variants 


TOOL SELECTION STRATEGY:
1. **For specific genes**: Use query_variants_by_gene (e.g., "BRCA1 variants", "CYP2D6 pharmacogenomics")
2. **For chromosomal regions**: Use query_variants_by_chromosome (e.g., "chromosome 17 variants", "chr13:32000000-33000000")
3. **For frequency analysis**: Use analyze_allele_frequencies (e.g., "rare variants", "population frequencies", allele frequency comparisons with 1000 Genomes)
4. **For cohort studies**: Use compare_sample_variants (e.g., "compare samples", "family analysis")
5. **For complex queries**: Use execute_dynamic_genomics_query

EXECUTION FLOW:
1. Understand the user query
2. Select the MOST APPROPRIATE single tool
3. Call the tool with proper parameters
4. Present the results immediately
5. DO NOT call multiple tools unless user explicitly requests for detailed analysis

Remember: Focus on clinically actionable insights that can inform patient care, genetic counseling, and treatment decisions.
"""

# Create the direct agent with genomics tools
try:
    direct_agent = Agent(
        model=bedrock_model,
        system_prompt=agent_instruction,
        tools=genomics_store_agent_tools
    )
    print("✅ Direct agent created successfully")
except Exception as e:
    print(f"❌ Error creating direct agent: {e}")
    direct_agent = None

app = BedrockAgentCoreApp()

@app.entrypoint
async def strands_agent_bedrock_streaming(payload):
    """
    Invoke the agent with streaming capabilities
    """
    user_input = payload.get("prompt")
    
    if direct_agent is None:
        yield "Error: Direct agent not initialized"
        return
    
    try:
        tool_name = None
        async for event in direct_agent.stream_async(user_input):
            if (
                "current_tool_use" in event
                and event["current_tool_use"].get("name") != tool_name
            ):
                tool_name = event["current_tool_use"]["name"]
                yield f"\n\n🔧 Using tool: {tool_name}\n\n"
            
            if "data" in event:
                yield event["data"]
                
    except Exception as e:
        error_response = {"error": str(e), "type": "stream_error"}
        print(f"Streaming error: {error_response}")
        yield error_response

if __name__ == "__main__":
    app.run()
