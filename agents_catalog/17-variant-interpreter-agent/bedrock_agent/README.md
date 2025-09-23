# This Repository demonstrates how to build an AI Agent for interpreting VEP-annotated VCF files for patient IDs

This repository showcases how to create an agent using Amazon Bedrock to support genomics tertiary analysis use-cases. The Agent has two capabilities:

* Analyzing existing VEP-annotated VCFs and providing meaningful interpretation summaries 
* Retrieving existing VEP-annotated reports and extracting information from parsed PDFs

# Prerequisite:

As a prerequisite, you need to have an annotated VCF file in your S3 bucket and a specific prefix to map with a patient ID (Ex: 3186764). The following prerequisite Healthomics workflows steps need to be run only when you don't have VEP annotated VCF file.

##### *******************************OPTIONAL********************************##############

## How to generate VEP-annotated VCF Files:

### Create an IAM role to run AWS Healthomics workflows

The following execution of python script will create an IAM role in your AWS account with a prefix tag of OmicsUnifiedServiceRole [Ex: OmicsUnifiedServiceRole-{ts}]. Please note that this role has broader access to your S3 buckets and container registry. We recommen to modify the IAM policies in the script to meet least-privilege permissions 

```bash
python3 workflows/omics_wf_role.py
```

### Bring the VEP container to your Amazon Elastic Container Registry (ECR)
```bash
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --output text --query "Account")
AWS_REGION=$(aws configure get region)
aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com 
aws ecr create-repository \
    --repository-name ensemblorg/ensembl-vep \
    --image-scanning-configuration scanOnPush=true \
    --region ${AWS_REGION} 
docker pull ensemblorg/ensembl-vep:release_113.4
docker tag ensemblorg/ensembl-vep:release_113.4 ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/ensemblorg/ensembl-vep:release_113.4
docker push ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/ensemblorg/ensembl-vep:release_113.4
```

### Build VEP workflow in AWS Healthomics environment

```python
definition_uri = "workflows/vep-healthomics.zip"
parameters = {
   "vcf": {
                  "description": "input VCF"
         },
         "vep_cache": {
                  "description": "cache directory to use"
         },
         "vep_cache_version": {
                  "description": "Use a different cache version than the assumed default (the VEP version)."
         },
         "vep_species": {
                  "description": "Species for your data. This can be the latin name e.g. homo_sapiens or any Ensembl alias e.g. mouse"
         },
         "ecr_registry": {
                  "description": "Amazon ECR registry for container images (e.g. '<account-id>.dkr.ecr.<region>.amazonaws.com')",
                  "optional": false
         },
         "vep_genome": {
                  "description": "Reference Assembly and version for the species, e.g. GRCh38"
         },
         "id": {
                  "description": "Raw input data as a string. May be used, for example, to input a single rsID or HGVS notation quickly to vep. Default: null",
                  "optional": true
         }
}

response = omics.create_workflow(
    name="ensembl-vep-nf",
    description="VEP annotation workflow",
    definitionUri=definition_uri,  
    main="main.nf",
    parameterTemplate=parameters,
)

workflow_vep = response

print(f"waiting for workflow {workflow_vep['id']} to become ACTIVE")
workflow_gatk = omics.get_workflow(id=workflow_vep['id'])
while workflow_vep['status'] in ('CREATING', 'UPDATING'):
    time.sleep(5)
    workflow_vep = omics.get_workflow(id=workflow_vep['id'])

if workflow_vep['status'] == 'ACTIVE':
    print(f"workflow {workflow_vep['id']} ready for use")
else:
    print(f"workflow {workflow_vep['id']} {workflow_vep['status']}")
```

### Running VEP workflow
```python
sample_name='<sample_id>'
response = omics.start_run(
    workflowId=workflow_vep['id'],
    name=f"VEP annotated vcf - {sample_name}",
    roleArn=OMICS_JOB_ROLE_ARN,
    parameters={
        "vcf": "s3://<INPUT_BUCKET>/omics/HCC1395T.mutect2.vcf.gz",
         "vep_species": "homo_sapiens",
         "vep_cache": "s3://<INPUT_BUCKET>/omics/sarek/vep_cache/",
         "vep_cache_version": "113",
         "ecr_registry": "<AWS_ACCOUNT_ID>.dkr.ecr.<AWS_REGION>.amazonaws.com",
         "vep_genome": "GRCh38",
         "id": "HCC1395T"
   },
    outputUri=f's3://<OMICS_OUTPUT_BUCKET>/output/vep/',
)

run_vep = response
response
```

This process may take about 20 minutes to generate VEP annotated VCF file and summary html available in output bucket defined in 'Running VEP workflow'
##### ******************Github repo reference******************************************###############
This Github repositoty [https://github.com/aws-samples/aws-healthomics-eventbridge-integration] includes VEP modules for deployment, you may directly deploy this CDK to setup your VEP workflow 

This blog has some detailed event-driven architecture [https://github.com/aws-samples/aws-healthomics-eventbridge-integration] including Healthomics Ready2Run workflow triggers by event and VEP automation for your reference 

##### *******************************END OF VEP WORKFLOW********************************##############

## Agent features 

This agent recognizes and understands VEP-annotated VCF files. For a given patient ID, the agent reads and interprets queries related to:

   - Variants per chromosome
   - Impact distribution
   - Consequence types
   - Biotypes
   - Gene-specific impacts
   - High-impact variants with details

and in the context of the following:

1. Provides detailed categorization of variants:
   - Coding variants (missense, nonsense, frameshift, etc.)
   - Splice variants
   - Regulatory variants
   - Non-coding variants

2. Tracks gene-level impacts:
   - Counts variants by impact level per gene
   - Stores specific variant details for each gene

3. Includes comprehensive consequence analysis:
   - Breaks down compound consequences
   - Tracks frequency of each consequence type

4. Provides detailed biotype analysis:
   - Tracks different transcript biotypes affected
   - Useful for understanding impact on different types of genes

5. Includes detailed variant information for high and moderate impact variants:
   - Complete location information
   - HGVS notation (both coding and protein level)
   - Exon/Intron information
   - Biotype information

6. Creates a summary section with the most relevant information:
   - Total variant counts
   - Impact distribution
   - Most affected genes
   - Most common consequences

To illustrate this use-case, we use the publicly available HCC1395 breast cancer cell line somatic mutation data detected by the mutect2 tool. We performed VEP analysis to annotate this VCF file and uploaded it to an S3 bucket under a specific patient ID prefix. While annotated VCF files are generally complex and contain detailed insights that are often difficult to extract clinically relevant information from, the agent simplifies the understanding of annotated VCF and responds to clinician and researcher queries.

# Step 0 - Setup the VEP annotated data as described earlier  and upload to S3

Pick a unique `S3_BUCKET_NAME` and upload your VEP-annotated VCF into a folder with a specific ID using AWS CLI:

```bash
aws s3 cp my_vep_annotated_file.vcf.gz s3://my_bucket/my_id/
```

# Step 1 - Deploy the Agent

Follow the `create_agent.ipynb` protocol to deploy your agent

# Step 2 - Test your agent

**Sample Questions:**

```
1. Which chromosome shows the highest number of high-impact variants?
2. What are the top 5 genes with the highest frequency of high-impact variants
3. How are variants distributed by impact type across chromosome 5?
4. What is the total count of splice region variants in the STAT3 gene?
5. Which gene exhibits the highest number of stop-gain or stop-loss variants?
6. Which gene contains the highest frequency of non-coding RNA variants?
7. Based on protein function loss, which three genes should be prioritized for this patient's analysis?
```

# LICENSE
- [MIT-0](/LICENSE)
The codebase relies on external models such as [Anthropic claude 3 sonnet](https://www.anthropic.com/news/claude-3-5-sonnet) subject to Licensing Agreements. The VCF data was generated from raw fastq files from the Registry of Open Data (https://registry.opendata.aws/aws-igenomes/) and can be found [here](s3://ngi-igenomes/test-data/sarek/)