# Statistician Agent

This agent is a collaborator agent used by a supervisor agent for Cancer biomarker discovery. You can find details of its deployment and usage in multi-agent collaboration mode in [Cancer Biomarker Discovery Example](../../multi_agent_collaboration/cancer_biomarker_discovery/README.md).

This agent Performs survival regression and creates Kaplan-Meier and descriptive plots using python lifelines library.

## Features

- **Survival regression**: Survival regression using the lifelines library 
- **Bar plot charts**: Visualize bar charts
- **Kaplan Meier charts** : Kaplan Meier charts for survival analysis

Here are some example questions that can be answered by this agent.

    * Create me a bar chart for the top 5 gene biomarkers (e.g.,TP53, BRCA1, EGFR, KRAS, MYC)
with respect to their prognostic significance in chemotherapy-treated patients.
The Y-axis should represent –log10(p-value) from a Cox proportional hazards model assessing association with overall survival. Y-axis values are: 8.3, 6.7, 5.9, 4.2, 3.8
    * For other questions, refer the multi-agent collaboration setup


### Deployment

 Deploy the entire stack of collaborator agents for [Cancer Biomarker Discovery Example](../../multi_agent_collaboration/cancer_biomarker_discovery/README.md).

Step by step instructions of deploying and testing the agent are included in the notebook. 

## How to Test in AWS Console

1. Go to [Amazon Bedrock](https://console.aws.amazon.com/bedrock) and select **Agents.**

2. Select your  agent and test by asking questions in **Test** window on your right. 

## License

- [MIT-0](/LICENSE)