## Create an agent for Validating Radiology Report 
Using Amazon Nova Micro, a multi-modal foundational model (FM) with document understanding capabilities, on Amazon Bedrock, a radiology report validation tool was created. First, we enable the large language model to parse the guidance document, allowing it to understand the criteria for appropriate imaging. A prompt is then passed to the FM along with the radiology report for validation, assessing ACR guideline adherence, diagnostic completeness, and missing anatomical structures.

## Step 0: Manage IAM Permissions


## Step 1: Upload the guidance document
Run the following command which uploads the guidance documents contained in the folder ACRdocs to a s3 bucket
`python upload_guidance_document_to_s3.py`

## Step 2: Create a DynamoDB table using the sample reports
`python create_dynamodb_table.py`
Now that we have the data prepared, we are ready to create an agent.py

## Step 3: Create an agent
Run all the cells in the python notebook `create_agent.ipynb`. A point to note that 

## Test Case1: Chest Radiology Report
Here is the radiology report: FINAL REPORT EXAMINATION : CHEST ( PORTABLE AP ) INDICATION : History :___ F with ett placement TECHNIQUE : Upright AP view of the chest COMPARISON : None . Patient is currently listed as EU critical . 
FINDINGS : Endotracheal tube tip terminates approximately a 4.6 cm from the carina . Enteric tube tip terminates within the distal esophagus and should be advanced by at least 11 cm .Heart size is normal . Gaseous distension of the stomach is noted "

### Output
In this case the agent downloads the ACR guidance criteria from an S3 bucket. It then validates the report against the same criteria

## Test Case 2: Transthoracic Ultrasound Report
Transthoracic echocardiogram was performed of technically limited quality. The left ventricle was normal in size and dimensions with normal LV function. Ejection fraction was 50% to 55%. Concentric hypertrophy noted with interventricular septum measuring 1.6 cm, posterior wall measuring 1.2 cm. Left atrium is enlarged, measuring 4.42 cm. Right-sided chambers are normal in size and dimensions. Aortic root has normal diameter. Mitral and tricuspid valve reveals annular calcification. Fibrocalcific valve leaflets noted with adequate excursion. Similar findings noted on the aortic valve as well with significantly adequate excursion of valve leaflets. Atrial and ventricular septum are intact.Pericardium is intact without any effusion. No obvious intracardiac mass or thrombi noted. Doppler study reveals mild-to-moderate mitral regurgitation. Severe aortic stenosis with peak velocity of 2.76 with calculated ejection fraction 50% to 55% with severe aortic stenosis. There is also mitral stenosis."

### Output
In this case, the agent cannot find the guidance document, so it provides its own report based on the inherent knowledge in the absence of any specific guidance criteria.
