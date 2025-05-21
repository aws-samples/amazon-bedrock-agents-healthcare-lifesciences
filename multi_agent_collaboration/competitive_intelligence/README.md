# Perform Competitive Intelligence Analysis

## Overview

Supervisor agent for analyzing public financial information and news about companies.

## Deployment

1. Deploy the agents in the `agents_catalog/SEC-10-K-agent` and `agents_catalog/Tavily-web-search-agent` folders according to the instructuctions in each `README.md` file.

2. Run the following to deploy the CloudFormation stack.

```bash

export BUCKET_NAME="<REPLACE>"
export NAME="<REPLACE>"
export REGION="<REPLACE>"
export S3CodeKey="<REPLACE>"
export BEDROCK_AGENT_SERVICE_ROLE_ARM="<REPLACE>"
export WEB_SEARCH_AGENT_ALIAS_ARN="<REPLACE>"
export SEC_10_K_SEARCH_AGENT_ALIAS_ARN="<REPLACE>"

aws cloudformation deploy --template-file "competitive-intelligence-agent-cfn" \
  --capabilities CAPABILITY_IAM \
  --stack-name $NAME \
  --region $REGION \
  --parameter-overrides \
  AgentAliasName="Latest" \
  AgentIAMRoleArn=$BEDROCK_AGENT_SERVICE_ROLE_ARM \
  WebSearchAgentAliasArn=$WEB_SEARCH_AGENT_ALIAS_ARN \
  SEC10kAgentAliasArn=$SEC_10_K_SEARCH_AGENT_ALIAS_ARN

```

## Chain of thought reasoning example

Question: Please write a competitive intelligence report on Amazon, focusing on the 5-year trend in overall earnings per share and also recentnews about Amazone Web Services.

Answer:

Here's your competitive intelligence report on Amazon:

EARNINGS PER SHARE (EPS) 5-YEAR TREND
--------------------------------

2018: $20.14
2019: $23.01
2020: $41.83
2021: $3.24
2022: -$0.27
2023: $2.90

Key EPS Insights:

• Strong Growth Phase (2018-2020): Peak performance in 2020 with $41.83 EPS
• Significant Decline (2021): 92% decrease to $3.24
• Bottom Point (2022): Negative EPS (-$0.27) due to Rivian investment loss
• Recovery (2023): Rebounded to $2.90, supported by $30.4B net income

AMAZON WEB SERVICES (AWS) RECENT DEVELOPMENTS
-------------------------------------------

1. AI Innovation & Growth

• Launched Amazon Nova Models at re:Invent 2024
• Stock jumped 7.67% to $227 following AI announcements
• Strategic positioning as primary host for future AI applications

2. Enterprise Expansion

• Major partnership with Commonwealth Bank of Australia
• Complete data migration to AWS expected by May 2025

3. Market Position

• Continued leadership in cloud computing sector
• Strong focus on AI integration and infrastructure
• Positive investor confidence in growth strategy

The report indicates that while Amazon's EPS has been volatile over the past five years, AWS continues to be a strong growth driver for the company, particularly with its strategic focus on AI and cloud computing integration.

## License

This project is licensed under the MIT License. The open-souce packages used in this project are under these [licenses](https://sagemaker-solutions-prod-us-east-2.s3-us-east-2.amazonaws.com/sagemaker-lung-cancer-survival-prediction/1.0.0/LICENSE.txt).
