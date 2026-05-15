#!/bin/bash
# Deploy all 16 Phase 2 agents to AgentCore
# Run: AWS_PROFILE=jrgaines+ct-sandbox01-Admin ./deploy_phase2.sh
# Answer "no" to OAuth and headers prompts when asked

REGION="us-east-1"
ACCOUNT_ID="864228002124"
ROLE="arn:aws:iam::${ACCOUNT_ID}:role/AmazonBedrockAgentCore-${REGION}-0affe73aa2c5"
ECR_BASE="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"
REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
START_TIME=$(date +%s)

echo "=== Phase 2 Batch Deployment — $(date) ==="

deploy_agent() {
  local DIR="$1"
  local NAME="$2"
  local T0=$(date +%s)
  
  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "  Deploying: $NAME"
  echo "  Dir: $DIR"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  
  aws ecr create-repository --repository-name "$NAME" --region "$REGION" 2>/dev/null || true
  
  cd "$REPO_ROOT/$DIR"
  
  agentcore configure \
    --entrypoint main.py \
    --name "$NAME" \
    --execution-role "$ROLE" \
    --ecr "${ECR_BASE}/${NAME}" \
    --disable-memory --disable-otel
  
  agentcore deploy --auto-update-on-conflict
  
  local T1=$(date +%s)
  echo "  ✅ $NAME done in $((T1 - T0))s"
}

deploy_agent "agents_catalog/10-SEC-10-K-agent/agentcore" "sec_10k_agent"
deploy_agent "agents_catalog/11-Tavily-web-search-agent/agentcore" "tavily_web_search"
deploy_agent "agents_catalog/12-JSL-analyze-medical-reports/agentcore" "jsl_medical_reports"
deploy_agent "agents_catalog/13-JSL-medical-reasoning/agentcore" "jsl_medical_reasoning"
deploy_agent "agents_catalog/14-USPTO-search/agentcore" "uspto_search"
deploy_agent "agents_catalog/15-clinical-study-research-agent/agentcore" "clinical_study_research"
deploy_agent "agents_catalog/16-Clinical-trial-protocol-generator-agent/agentcore" "protocol_generator"
deploy_agent "agents_catalog/18-Wiley-OA-life-sciences-agent/agentcore" "wiley_oa_search"
deploy_agent "agents_catalog/19-UniProt-protein-search-agent/agentcore" "uniprot_search"
deploy_agent "agents_catalog/20-single-cell-qc-agent/agentcore" "single_cell_qc"
deploy_agent "agents_catalog/21-invivo-study-scheduler-agent/agentcore" "invivo_scheduler"
deploy_agent "agents_catalog/22-Safety-Signal-Detection-Agent/agentcore" "safety_signal"
deploy_agent "agents_catalog/23-data-harmonisation-drug-dev-pipeline/agentcore" "data_harmonisation"
deploy_agent "agents_catalog/25-DMTA-orchestration-agent/agentcore" "dmta_orchestration"
deploy_agent "multi_agent_collaboration/competitive_intelligence/agentcore" "competitive_intel"
deploy_agent "multi_agent_collaboration/Clinical-Trial-Protocol-Assistant/agentcore" "protocol_assistant"

END_TIME=$(date +%s)
echo ""
echo "=== COMPLETE ==="
echo "Total time: $(( (END_TIME - START_TIME) / 60 ))m $(( (END_TIME - START_TIME) % 60 ))s"
echo "Agents deployed: 16"
