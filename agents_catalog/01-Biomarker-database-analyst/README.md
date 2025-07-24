# Biomarker Database analyst Agent

This agent is a collaborator agent used by a supervisor agent for Cancer biomarker discovery. You can find details of its deployment and usage in multi-agent collaboration mode in [Cancer Biomarker Discovery Example](../../multi_agent_collaboration/cancer_biomarker_discovery/README.md).

This agent analyzes structured clinical and RNA-seq data. It convert natural language questions to SQL statements and execute on an Amazon Redshift database of biomarkers.

## Features

- **Dynamic Schema Dicovery**: Adapts to database schema defined in Amazon Redshift database
- **Natrual language processing**: Manages the entire workflow from natural language query to SQL statement to insights
- **Error handling and self-correction** : Performs a self-optimize step to improve the SQL statement before execution and also handles retries and error handling after execution

## Sample Database Overview

This example utilizes the  [Non-Small Cell Lung Cancer (NSCLC) Radiogenomics dataset](https://wiki.cancerimagingarchive.net/display/Public/NSCLC+Radiogenomics) that consists a cohort of early stage NSCLC patients referred for surgical treatment. Prior to surgical procedures, Computed Tomography (CT) and Positron Emission Tomography/CT (PET/CT) are performed. Samples of tumor tissues were used to obtain mutation data and gene expresssion data by RNA sequencing technology. Clinical and demographic information were recorded for the patients as well.  

Here are some example questions that can be answered by this agent.

    * What is the average age of patients diagnosed with Adenocarcinoma?
    * What is the most common pathological T stage for squamous cell carcinoma?
    * What percentage of patients in the database have EGFR mutations?


### Deployment

 Deploy the entire stack of collaborator agents for [Cancer Biomarker Discovery Example](../../multi_agent_collaboration/cancer_biomarker_discovery/README.md).

Step by step instructions of deploying and testing the agent are included in the notebook. 

## How to Test in AWS Console

1. Go to [Amazon Bedrock](https://console.aws.amazon.com/bedrock) and select **Agents.**

2. Select your  agent and test by asking questions in **Test** window on your right. 

## License

- [MIT-0](/LICENSE)