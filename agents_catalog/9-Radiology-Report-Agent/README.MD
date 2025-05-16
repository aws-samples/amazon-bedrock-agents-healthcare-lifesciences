## Create an agent for Validating Radiology Report 
Using Amazon Nova Micro, a multi-modal foundational model (FM) with document understanding capabilities, on Amazon Bedrock, a radiology report validation tool was created. First, we enable the large language model to parse the guidance document, allowing it to understand the criteria for appropriate imaging. The radiology reports are contained in a dynamodb table and the guidance documents are stored in an S3 bucket. When the user asks a question about a certain report pertaining the patient id, the agent tries to identify the anatomical structure mentioned in the report and tries to find the closest matching guidance document. It then validates the report against the document. If a matching document is not found, the agent uses Nova's internal knowledge to validate the report.

*This is an example setup. Our implementation is flexible to accomodate specific user workflows.*

## Step 0: Manage IAM Permissions
If you are using an EC2 instance to create this code, create an IAM Role and assign the role to the EC2 instance (this is the recommended way). Alternatively, you can create a user and setup a user profile using `aws configure` as described [here](https://docs.aws.amazon.com/cli/v1/userguide/cli-configure-files.html).
Ensure that the role/user has the following permissions assigned to them 
- IAMFullAccess
- S3FullAccess
- BedRockFullAccess
- Lambda_FullAccess


## Step 1: Upload the guidance document
Run the following command which uploads the guidance documents contained in the folder ACRdocs to a s3 bucket
`python upload_guidance_document_to_s3.py`

## Step 2: Create a DynamoDB table using the sample reports
`python create_dynamodb_table.py`
Now that we have the data prepared, we are ready to create an agent.py

## Step 3: Create an agent
Run all the cells in the python notebook `create_agent.ipynb`. Please go through the cell instructions carefully while executing the notebook.

## Test Case1: Chest Radiology Report
Q: Can you validate the radiology report for patient id 1489?

### Output
Based on the validation results, the radiology report for patient 1489 does not fully adhere to the ACR guidelines:\n\n- It lacks specific details and a clear diagnosis, only mentioning key findings without elaborating on their clinical significance.\n- The report is missing important details about the lung parenchyma.\n- Overall, it does not meet the quality standards set by the ACR guidelines for chest radiology reports.\n\nTo improve the report, the radiologist should provide more detailed descriptions, a clear diagnosis or impression, and ensure all relevant anatomical structures are covered as per the ACR guidance.

## Test Case 2: Abdominal Ultrasound
Q: Can you validate the radiology report for patient id 1143?

### Output
The radiology report appears to be for an abdominal ultrasound, as it describes findings related to the gallbladder, liver, spleen, kidneys, and other abdominal structures. The report is detailed and provides relevant information about the visualized structures. However, without the specific ACR guidance document for abdominal ultrasound reporting, it is difficult to definitively assess if all required elements are present per the guidelines.\n\nSome potential areas for improvement:\n\n- The report could provide more details on the technique/patient positioning used for the ultrasound.\n- It does not mention if any limitations were encountered during the exam.\n- There is no impression/conclusion summarizing the overall findings.\n\nOverall, while the report covers key abdominal structures in reasonable detail, adhering to ACR guidance would likely require some additional sections/elements to meet best practice reporting standards. But the core findings and descriptions seem appropriate for an abdominal ultrasound exam.

## Test Case 3: Transthoracic Echocardiogram
Q: Can you validate the radiology report for patient id 1179?

### Output
The radiology report for patient 1179 is a detailed echocardiogram report providing a diagnosis of severe aortic stenosis and mitral stenosis. However, it does not adhere to the ACR guidelines for chest imaging, as it is focused on evaluating the heart structures and function rather than the lungs, airways and other chest anatomy covered by those guidelines.\n\nThe report meets the standards for an echocardiogram report in terms of detailing the cardiac anatomy, function and pathologies. But it does not cover the key anatomical structures evaluated in chest imaging like the lungs, airways, etc. that are required by the ACR chest imaging guidelines.\n\nSo in summary, while it is a high quality echocardiogram report, it does not meet the specific quality standards of the ACR guidelines for chest imaging reports. The report is appropriate for evaluating cardiac pathologies but not chest pathologies.