# This Repository showcases how to build an AI Agent to support Pathology workflows

This repository showcases how to create an agent using Amazon Bedrock to support Pathology use-cases. The Agent has two capabilities:

* Retrieve existing pathology reports and extract information from the parsed PDFs
* Augment existing pathology reports findings using biomarker task-specific fine-tuned ML models

To illustrate this use-case, we rely on the TCGA-COAD dataset: For a given patient, we first look at the pathology reports to extract the tumor stage and microsatellite (MSI) status: The MSI status is useful, since the MSI status is a useful predictor of response to immunotherapy. Since a lot of pathology reports ommit the MSI status reports in the TCGA report, we train and deploy a Machine Learning Whole Slide Image (WSI) classifier. We leverage a foundation model (HOptimus0) to extract patch-level features and a Multiple-Instance-Learning (MIL) feature aggregator in our Classification Model.  

# Step 0 - Download the data from TCGA and code articafts and upload it to S3

For this, pick a unique `S3_BUCKET_NAME` and configure your `AWS_PROFLE` and execute the `./prepare_data AWS_PROFILE S3_BUCKET_NAME` command. 

# Step 1 - Deploy the infrastucture 

Deploy the cloud formation template. Make sure to use your `AWS PROFILE` and your `S3_BUCKET_NAME` from before. You will aslo need to retrieve the Default VPC subnets and Security group to provision the Batch Compute Environment. 

```aws cloudformation deploy --template-file infra/infra.yml --stack-name Agent --profile=AWS_PROFILE --parameter-overrides ArtifactsBucket=S3_BUCKET_NAME DefaultSubnets=DEFAULT_SUBNETS DefaultSecurityGroupID=SECURITY_GROUP --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM```

Note: This CloudFormation template triggers a CodeBuild that takes approximately 20 minutes to build. You can check on the progress of that build in the AWS CodeBuild Console before moving to the next step. 

# Step 2 - Deploy the Agent

Follow the `create_agent.ipynb` protocol to deploy your agent

# Step 3 - Test your agent. 

**Sample Questions:**:

```
    1. What is the pathology report of patient "TCGA-3L"?
    2. Was the MSI status mentioned in the report of patient "TCGA-4N"?
    3. Can you run the MSI classification for patient "TCHA-5M"?
    4. What is the status of the job classification? 
```


