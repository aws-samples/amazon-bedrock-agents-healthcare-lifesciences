## Create an agent for Validating Radiology Report 
Using Amazon Nova Micro, a multi-modal foundational model (FM) with document understanding capabilities, on Amazon Bedrock, a radiology report validation tool was created. First, we enable the large language model (LLM) to parse the guidance document, allowing it to understand the criteria for appropriate imaging. The radiology reports are contained in a dynamodb table and the guidance documents are stored in an S3 bucket. When the user asks a question about a certain report pertaining the patient id, the agent tries to identify the anatomical structure mentioned in the report and tries to find the closest matching guidance document. It then validates the report against the document. If a matching document is not found, the agent uses Nova's internal knowledge to validate the report. Two LLMs are used in this particular example, which are Claude's Sonnet 3.5v2 and Amazon's Nova Micro Lite. The Sonnet 3.5v2 model handles the agent interaction, while the Nova's Micro Lite model is used for validating the radiology report. Users are welcome to try different models which better suites their particular use cases.

*This is an example setup. Our implementation is flexible to accomodate specific user workflows.*

## Step 0: Manage IAM Permissions
If you are using an EC2 instance to create this code, create an IAM Role and assign the role to the EC2 instance (this is the recommended way). Alternatively, you can create a user and setup a user profile using `aws configure` as described [here](https://docs.aws.amazon.com/cli/v1/userguide/cli-configure-files.html).
Ensure that the role/user has the following permissions assigned to them 
- IAMFullAccess
- S3FullAccess
- BedRockFullAccess
- Lambda_FullAccess

The models used in this example are mentioned in `lambda_function.py` and can be changed in the same file.



## Step 1: Upload the guidance document
Run the following command which uploads the guidance documents contained in the folder ACRdocs to a s3 bucket. Assign a bucket name and a region. Here we choose  `radiology-report-agent-guidance-documents` as the bucket name and `us-west-2` as the region of choice
`python upload_guidance_document_to_s3.py --bucket-name radiology-report-agent-guidance-documents --region us-west-2`

Please note that the s3 bucket names share a global namespace. So if you get an error in this step you can try a different name or use [uuid](https://www.uuidgenerator.net/dev-corner/python) to generate a unique identifier. 

### Step 1.1 Populate the S3 bucket name
Open the file `lambda/lambda_function.py` and provide the s3 bucket name used in the previous step.

## Step 2: Create a DynamoDB table using the sample reports
`python create_dynamodb_table.py`
Now that we have the data prepared, we are ready to create an agent.py

## Step 3: Create an agent
Run all the cells in the python notebook `create_agent.ipynb`. Please go through the cell instructions carefully while executing the notebook.

## Test Case1: Chest Radiology Report
Q: Can you validate the radiology report for patient id 1489?

### Output
Based on the validator's assessment, the radiology report for patient 1489 adheres to the ACR guidelines for chest imaging. The report provides clear descriptions of the findings, including details on atelectasis, consolidation, pleural spaces, aorta, cardiac silhouette, and pulmonary edema. It covers all the relevant anatomical structures in a detailed manner.\n\nThe main area for improvement, as suggested by the validator, is to include a more specific assessment and management recommendation based on the described findings. While the report meets the core quality standards, adding an overall impression and next steps would make it more complete and actionable per ACR guidelines.\n\nOverall, with its comprehensive findings and adherence to guidelines, the report satisfies most of the key requirements. Incorporating a concluding assessment and recommendation would further enhance its quality and clinical value.

## Test Case 2: Abdominal Ultrasound
Q: Can you validate the radiology report for patient id 1143?

### Output
Based on the radiology report for patient 1143, it appears to be describing findings from an abdominal imaging study, likely an ultrasound or CT scan. The report covers key abdominal structures like the gallbladder, liver, spleen, pancreas, kidneys, and major blood vessels.\n\nStrengths:\n- The report is structured and organized, listing out the findings for each organ system.\n- It provides details on size measurements for organs like the kidneys.\n- It comments on the presence or absence of important findings like gallstones, hydronephrosis, masses etc.\n\nPotential areas for improvement:\n- The report could provide more details on imaging technique/modality used.\n- It doesn't mention any clinical indication or patient history.\n- There is no impression or conclusion summarizing the overall findings.\n\nWithout the specific ACR guidance document, it's difficult to validate if all required elements are present. However, the report covers many of the essential components expected in an abdominal imaging report. Adding details on technique, clinical context and a summary impression could further improve its completeness.

## Test Case 3: Transthoracic Echocardiogram
Q: Can you validate the radiology report for patient id 1179?

### Output
The radiology report for patient 1179 describes the findings from a transthoracic echocardiogram exam of the heart. While I could not validate it against a specific ACR guidance document for echocardiography, the report appears to meet general radiology reporting standards:\n\n- It provides details on the study quality and limitations upfront.\n- It systematically describes the size, dimensions, and function of the key cardiac structures like ventricles, atria, valves, etc.\n- It quantifies relevant measurements like ejection fraction, wall thickness, chamber sizes, etc.\n- It identifies and describes abnormal findings like concentric hypertrophy, valve calcifications, regurgitation, and stenosis.\n- It provides an overall impression/diagnosis of the key findings.\n\nThe report is comprehensive and detailed enough to convey the important findings and diagnoses from the echocardiogram exam. However, it could potentially be improved by including more clinical details like patient history, indications for the exam, and follow-up recommendations.\n\nOverall, while I could not validate against a specific guidance document, the report meets general radiology reporting standards for completeness and diagnostic quality.

## Test Case 4: Mammography
Q: Can you validate the radiology report for patient id 1236?

### Output
Based on the validator's feedback, the radiology report for patient 1236 adheres to the key ACR guidelines by covering important aspects like breast composition, findings, and comparison to prior exams. However, the report could be improved by providing more specific details in those areas, as well as including the patient's clinical history and information on other relevant imaging studies.\n\nThe report meets the overall quality standards but could benefit from being more comprehensive and detailed. The radiologist should consider incorporating the suggested improvements to enhance the report's completeness and diagnostic value.

## Cleanup
You should delete your agent, lambda function, s3 bucket and dynamodb table from your account to prevent any ongoing costs. You can do so by going to your AWS Console. 
- Deleting the agent: Go to Amazon Bedrock --> Builder Tools --> Agents, to see the list of agents and delete your agent
- Deleting the S3 bucket: Go to S3 Console page and delete the s3 buckets you created
- Delete the Lambda function: Similarly you can delete the lambda function by going to the Lambda function page
- Delete the DynamoDB table: Go to DynamoDB page and delete the DynamoDB table

For any reason, if you do not see your resources make sure you are in the correct region, this code is assigning all the resources in `us-west-2`. You can do so by checking the top right of the AWS console page.