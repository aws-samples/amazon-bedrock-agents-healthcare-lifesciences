# Research agents for LifeSciences with Amazon Bedrock Agents

Explore the following components in the repository:
## Agents catalog
Library of specialized agents for different R&D workflows
## Multi-agent collaboration
Framework for agent collaboration and knowledge sharing. End to end example for cancer biomarker discovery
## Deployment
One-click deployment of infrastructure and interactive interface for human-agent chat
## Evaluation
Methods for assessing agent performance and result quality. End to end example for cancer biomarker discovery


# Multi-agent collaboration example: Accelerate analysis and discovery of cancer biomarkers with Agents for Bedrock

**Note: Biomarker Agents can now be deployed with Bedrock multi-agent collaboration in your AWS account!

Read more about these agents here:
https://aws.amazon.com/blogs/machine-learning/accelerate-analysis-and-discovery-of-cancer-biomarkers-with-amazon-bedrock-agents/

Multi-Agent Guidelines:
- As of now, the primary way to deploy the Bedrock multi-agent setup is to follow the notebooks located in multi_agent_development/
- An infrastructure deployment is needed to create AWS resources before going through the notebooks

Multi-Agent Notebook Deployment Steps:

Step 1: Click the 'Launch Stack' button located in the [Deployment](#deployment) section to deploy the underlying AWS infrastructure

Step 2: Go to a SageMaker Notebook instance in your AWS account and clone this repository in a terminal

```bash
git clone https://github.com/aws-samples/amazon-bedrock-agents-cancer-biomarker-discovery.git
```

Step 3: Navigate to the multi-agent-collaboration branch within the repository
```bash
cd amazon-bedrock-agents-cancer-biomarker-discovery
```
```bash
git checkout multi-agent-collaboration
```

Step 4: Navigate to agents_catalog/0-Notebook-environment/ and go to setup_environment.ipynb, use the Python 3 (ipykernel)

Step 5: Proceed to build each agent using the notebooks

Step 6: If you are interested in deploying the Biomarker Supervisor Agent that leverages the Bedrock multi-agent collaboration feature, go to the multi_agent_orchestration/ folder of this repository and follow instructions there

## Overview
The success rate for Phase I oncology clinical trials is significantly low. According to a study published in Nature Reviews Drug Discovery, the overall success rate for oncology drugs from Phase I to approval is around 5%, indicating a high failure rate of approximately 95%. 

According to the National Cancer Institute, cancer biomarkers, also known as tumor markers, are biological molecules found in blood, other body fluids, or tissues that indicate the presence of cancer.  Biomarkers for patient stratification can improve the probability of success in clinical development; the average is between double and triple, but it can be as high as five-fold. 

In this solution, we show you how agentic workflows with LLMs from Amazon Bedrock leverage planning, tool-use, and self-reflection to transform complex oncology research queries into actionable insights. We define an example analysis pipeline, specifically for lung cancer survival with clinical, genomics and radiology modalities of biomarkers. We showcase a variety of tools including database retrieval with Text2SQL, statistical models and visual charts with scientific libraries, biomedical literature search with public APIs and internal evidence, and medical image processing with Amazon SageMaker jobs. We demonstrate advanced capabilities of agents for self-review and planning that help build trust with end users by breaking down complex tasks into a series of question and answers and showing the chain of thought to generate the final answer.

## Biomarker analysis workflow
The biomarker analysis workflow is illustrated below that incorporates multimodal data, including clinical, genomic, and CT scan imaging data. We augment this pipeline with Agents for Amazon Bedrock.
![architecture](images/biomarker_analysis_workflow.jpg)


## Architecture Overview
The solution architecture is illustrated below. 
![architecture](images/architecture.jpg)
Agents for Amazon Bedrock enable generative AI applications to execute multistep tasks across company systems and data sources. We define our solution to include planning and reasoning with multiple tools including
-	Biomarker query engine:  Convert natural language questions to SQL statements and execute on an Amazon Redshift database of biomarkers. 
-	Scientific analysis and plotting engine: Use lifelines library with clinical and genomics data to build survival regression models like COX proportional hazard model and visualization like Kaplan Meier charts for survival analysis. 
-	External data API: Use PubMed apis to search biomedical literature for specific evidence. 
-	Internal literature: Use Knowledge Bases for Bedrock to give agents contextual information from internal literature evidence for RAG to deliver more relevant, accurate, and customized responses 
-	Medical imaging: Use Amazon SageMaker Jobs to augment agents with the capability to trigger asynchronous jobs with an ephemeral cluster to process CT scan images that include 2D slices to 3D volumes conversion, CT and segmentation masks alignment, radiomic feature extraction within the tumor region.
![architecture](images/architecture_details.jpg)


### What Does the Input Data Look Like?
We reuse the multimodal data analysis pipeline from this solution(https://github.com/aws-samples/machine-learning-pipelines-for-multimodal-health-data/tree/sagemaker-soln-lcsp) for Non-Small Cell Lung Cancer (NSCLC). 
The [Non-Small Cell Lung Cancer (NSCLC) Radiogenomics dataset](https://wiki.cancerimagingarchive.net/display/Public/NSCLC+Radiogenomics) consists a cohort of early stage NSCLC patients referred for surgical treatment. Prior to surgical procedures, Computed Tomography (CT) and Positron Emission Tomography/CT (PET/CT) are performed. Samples of tumor tissues were used to obtain mutation data and gene expresssion data by RNA sequencing technology. Clinical and demographic information were recorded for the patients as well. Each data modality (imaging, genomic, clincal) presents different view of a patient.

Details for each modality is described below.

#### Genomic 
Total RNA was extracted from the tumor tissue and analyzed with RNA sequencing technology. 
The dataset file that is available from the source was pre-processed using open-source tools including STAR v.2.3 for alignment and Cufflinks v.2.0.2 for expression calls. Further details can be found in [3]. The original dataset (GSE103584_R01_NSCLC_RNAseq.txt.gz) is also available in https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE103584.

While the original data contains more than 22,000 genes, we keep 21 genes from 10 highly coexpressed gene clusters (metagenes) that were identified, validated in publicly available gene-expression cohorts, and correlated with prognosis [3]. These are genes corresponding to Metagenes 19, 10, 9, 4, 3, 21 in Table 2 in [3]. 

After gene selection from the source data, the dataset looks like

| Case_ID   |    LRIG1 |    HPGD |     GDF15 |    CDH2 |    POSTN |  ......  |
|:----------|---------:|--------:|----------:|--------:|---------:|---------:|
| R01-024   | 26.7037  | 3.12635 | 13.0269   | 0       | 36.4332  |  ......  |
| R01-153   | 15.2133  | 5.0693  |  0.908663 | 0       | 32.8595  |  ......  |
| R01-031   |  5.54082 | 1.23083 | 29.8832   | 1.13549 | 34.8544  |  ......  |
| R01-032   | 12.8391  | 7.21931 | 12.0701   | 0       |  7.77297 |  ......  |
| R01-033   | 33.7975  | 3.19058 |  5.43418  | 0       |  9.84029 |  ......  |

The values denote expression level for each gene per patient. A higher number means that that specific gene is highly expressed in that specific tumor sample.

#### Clinical record
The clinical records are stored in CSV format. Each row corresponds to a patient and the columns represent information about the patients, including demographics, tumor stage, and survival status. 

| Case ID   | Survival Status   |  Age at Histological Diagnosis | Weight (lbs)   | Smoking status   | Pack Years    |   Quit Smoking Year | Chemotherapy   | Adjuvant Treatment   | EGFR mutation status   |  ......  | 
|:----------|--------------------------------:|:---------------|:-----------------|:--------------|--------------------:|:---------------|:---------------------|:-----------------------|:---------|:------------------|
| R01-005   | Dead              |                             84 | 145            | Former           | 20            |                1951 | No             | No                   | Wildtype               |  ......  | 
| R01-006   | Alive             |                           62 | Not Collected  | Former           | Not Collected |                 nan | No             | No                   | Wildtype               |  ......  | 
| R01-007   | Dead              |                            68 | Not Collected  | Former           | 15            |                1968 | Yes            | Yes                  | Wildtype               |  ......  | 
| R01-008   | Alive             |                           73 | 102            | Nonsmoker        | nan           |                 nan | No             | No                   | Wildtype               |  ......  | 
| R01-009   | Dead              |                             59 | 133            | Current          | 100           |                 nan | No             | No                   | Wildtype               |  ......  |


#### Medical imaging
Medical imaging biomarkers of cancer promise improvements in patient care through advances in precision medicine. Compared to genomic biomarkers, imaging biomarkers provide the advantages of being non-invasive, and characterizing a heterogeneous tumor in its entirety, as opposed to limited tissue available via biopsy [2]. In this dataset, CT and PET/CT imaging sequences were acquired for patients prior to surgical procedures. Segmentation of tumor regions were annotated by two expert thoracic radiologists. Below is an example overlay of a tumor segmentation onto a lung CT scan (case R01-093).

![ortho-view](https://sagemaker-solutions-prod-us-east-2.s3-us-east-2.amazonaws.com/sagemaker-lung-cancer-survival-prediction/1.0.0/docs/R01-093_06-22-1994_ortho-view.png)

## Chain of thought reasoning example
Here is an example chain of thought sequence with the agent. 11 questions are listed in the image with their expected responses.  
![architecture](images/question_sequence_example.jpg)

## Deployment

> [!IMPORTANT]  
> Access to Amazon Bedrock foundation models (not granted by default). To gain access, follow the [official documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/model-access.html).


1. Upload the `Infra_cfn.yaml` file from the [amazon-bedrock-agents-cancer-biomarker-discovery](https://github.com/aws-samples/amazon-bedrock-agents-cancer-biomarker-discovery) repository to AWS CloudFormation. This template will set up:
> [!WARNING]  
> Launching this stack will create 2 VPCs (Infrastructure and UI).

   - Networking infrastructure (VPC, Subnets, etc.)
   - Amazon Redshift database
   - Bedrock Agent with Actions
   - Knowledgebase
   - Streamlit UI frontend

2. Deploy the `Infra_cfn.yaml` template:
   - Default parameter values can remain unchanged
   - Parameter descriptions:
     - `BedrockModelId`: ID of the Foundation Model for the Agent (permissions scoped to Anthropic Claude 3 Sonnet model)
     - `EnvironmentName`: Differentiates the application if launched in the same AWS account (lowercase, one number, max 5 characters)
     - `RedshiftDatabaseName`: Name for the Redshift database
     - `RedshiftUserName`: Username for Redshift database login
     - `RedshiftPassword`: Password for Redshift database login
     - `GithubLink`: Default repository for the Agent (do not change)
     - `ImageTag`: Tag of the Docker image for Streamlit UI deployment

> [!NOTE]  
> Full deployment takes approximately 10-15 minutes. Stack can also be launched in us-east-1 or us-west-2 by clicking launch stack below

|   Region   | Infra_cfn.yaml |
| ---------- | ----------------- |
| us-east-1  | [![launch-stack](https://s3.amazonaws.com/cloudformation-examples/cloudformation-launch-stack.png)](https://console.aws.amazon.com/cloudformation/home?region=us-east-1#/stacks/new?stackName=biomakeragent&templateURL=https://aws-blogs-artifacts-public.s3.amazonaws.com/artifacts/ML-16901/Infra_cfn.yaml)|
| us-west-2  | [![launch-stack](https://s3.amazonaws.com/cloudformation-examples/cloudformation-launch-stack.png)](https://console.aws.amazon.com/cloudformation/home?region=us-west-2#/stacks/new?stackName=biomakeragent&templateURL=https://aws-blogs-artifacts-public.s3.amazonaws.com/artifacts/ML-16901/Infra_cfn.yaml)|

3. After stack launch is successful manually sync the Knowledgebase:
   1. Navigate to the Bedrock dashboard via AWS Console search
   2. Click the option icon (top left) to open the navigation bar
   3. Select "Knowledge bases" under the "Builder tools" tab
   4. Choose the Knowledgebase created by the CloudFormation template
   5. Scroll to the "Data Source" option box
   6. Select the data source (radio button) and click "Sync"

4. Access the UI:
   1. Navigate to AWS CloudFormation via AWS Console search
   2. Click the Streamlit nested stack (format: `<stackname>-StreamlitBuildNestedStack-<123ABCXXXX>`)
   3. In the Outputs tab, find and click the StreamlitAppURL link


## Contributing Guidelines

### Setting Up Your Development Environment

1. Fork the repository to your GitHub account. Ensure the fork remains public during development and testing.

2. Clone your forked repository to your local machine.

3. Update the GitHub URL in the following configuration files to point to your forked repository:
   - `infra_cfn.yaml`
   - `agent_build.yaml`
   - `streamlit_build.yaml`

4. For testing purposes, deploy the `infra_cfn.yaml` template to AWS CloudFormation.

### Submitting a Pull Request

1. Ensure you have forked the main repository: [amazon-bedrock-agents-cancer-biomarker-discovery](https://github.com/aws-samples/amazon-bedrock-agents-cancer-biomarker-discovery/tree/main)

2. Create a new branch in your forked repository for your changes.

3. Implement your changes, following the project's coding standards and guidelines.

4. Commit your changes with clear, concise commit messages.

5. Push your branch to your forked repository on GitHub.

6. Open a pull request from your branch to the main repository's `main` branch.

7. Provide a clear description of your changes in the pull request, including any relevant issue numbers.

8. Be prepared to address any feedback or questions during the code review process.



## License
This project is licensed under the MIT License. The open-souce packages used in this project are under these [licenses](https://sagemaker-solutions-prod-us-east-2.s3-us-east-2.amazonaws.com/sagemaker-lung-cancer-survival-prediction/1.0.0/LICENSE.txt).

Users of the dataset must abide by [TCIA's Data Usage Policy](https://wiki.cancerimagingarchive.net/display/Public/Data+Usage+Policies+and+Restrictions) and the [Creative Commons Attribution 3.0 Unported License](https://creativecommons.org/licenses/by/3.0/) under which it has been published.

## Citation
We reuse the multimodal data analysis pipeline from this solution(https://github.com/aws-samples/machine-learning-pipelines-for-multimodal-health-data/tree/sagemaker-soln-lcsp)

## Legal Notes
**<span style="color:RED">Important</span>**: This solution is for demonstrative purposes only. It is not for clinical use and is not a substitute for professional medical advice, diagnosis, or treatment. **The associated notebooks, including the trained model and sample data, are not intended for production.** It is each customers’ responsibility to determine whether they are subject to HIPAA, and if so, how best to comply with HIPAA and its implementing regulations. Before using AWS in connection with protected health information, customers must enter an AWS Business Associate Addendum (BAA) and follow its configuration requirements.
