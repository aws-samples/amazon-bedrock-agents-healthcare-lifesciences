# Medical imaging Agent

This agent is a collaborator agent used by a supervisor agent for Cancer biomarker discovery. You can find details of its deployment and usage in multi-agent collaboration mode in [Cancer Biomarker Discovery Example](../../multi_agent_collaboration/cancer_biomarker_discovery/README.md).

This agent analyzes Processes CT scans using asynchronous workflows. It Use Amazon SageMaker jobs to augment agents with the capability to trigger asynchronous jobs with an ephemeral cluster to process CT scan images.

## Features

- **Process imaging modality**: Processes medical imaging data corresponding to CT scan images
- **Trigger asyncrhonous jobs**: Triggers a long running SageMaker job to process CT scan images
- **Analyze and visualize results** : Analyzes the results including features of the tumor and visualizes the tumor segmentation

## Sample Database Overview

This example utilizes the  [Non-Small Cell Lung Cancer (NSCLC) Radiogenomics dataset](https://wiki.cancerimagingarchive.net/display/Public/NSCLC+Radiogenomics) that consists a cohort of early stage NSCLC patients referred for surgical treatment. Prior to surgical procedures, Computed Tomography (CT) and Positron Emission Tomography/CT (PET/CT) are performed. In this dataset, CT and PET/CT imaging sequences were acquired for patients prior to surgical procedures. Segmentation of tumor regions were annotated by two expert thoracic radiologists. 

Here are some example questions that can be answered by this agent.

    * Can you compute the imaging biomarkers for patient IDs R01-083 and R01-040?
    * What is the sphericity and elongation values for the tumors of these patients ?
    * Show me the tumor segmentation images of these patients ?


### Deployment

 Deploy the entire stack of collaborator agents for [Cancer Biomarker Discovery Example](../../multi_agent_collaboration/cancer_biomarker_discovery/README.md).

Step by step instructions of deploying and testing the agent are included in the notebook. 

## How to Test in AWS Console

1. Go to [Amazon Bedrock](https://console.aws.amazon.com/bedrock) and select **Agents.**

2. Select your  agent and test by asking questions in **Test** window on your right. 

## License

- [MIT-0](/LICENSE)