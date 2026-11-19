from strands import Agent, tool
from strands_tools import use_aws, use_llm
import json 
import pandas as pd
import sys
import logging

# # Configure the root strands logger
# logging.getLogger("strands").setLevel(logging.DEBUG)

# # Add a handler to see the logs
# logging.basicConfig(
#     format="%(levelname)s | %(name)s | %(message)s", 
#     handlers=[logging.StreamHandler()]
# )

patient_file = sys.argv[1]

with open(patient_file, "r") as patient_fid:
    patient_data = json.load(patient_fid)
# convert json to string
patient_data = json.dumps(patient_data, indent=2)


with open("resources/hca_billing_guides_structured.json", "r") as fid:
    billing_data = json.load(fid)
specialties = billing_data["categories"]

@tool
def get_guidance_document_list(speciality: str) -> str:
    """
    Get the list of PDF document URLs from the dictionary for a given specialty as well
        as the latest fee schedule document.
    """
    try:
        if speciality in billing_data["categories"]:
            pdf_url_list = billing_data["categories"][speciality]["items"]
            return str(pdf_url_list) if pdf_url_list else "No documents found"
        else:
            available_specialties = list(billing_data["categories"].keys())
            return f"Specialty '{speciality}' not found. Available: {available_specialties}"
    except Exception as e:
        return f"Error retrieving PDF list: {str(e)}"

@tool
def download_appropriate_document(download_dict: dict) -> str:
    """
    Download the latest billing guide and fee schedule for the given specialty and parse it.
    """
    out_dir = "downloaded_files"
    import os
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)
        
    pdf_urls = download_dict['pdf_urls']
    print(pdf_urls)
    fee_schedule_url = download_dict['fee_schedule_url'] if 'fee_schedule_url' in download_dict else None
    
    downloaded_files = []
    import requests
    
    # download pdf from the URLs
    for url in pdf_urls:
        try:
            response = requests.get(url)
            response.raise_for_status()
            print(response.status_code)

            filename = url.split('/')[-1] or "document.pdf"

            with open(os.path.join(out_dir, filename), 'wb') as f:
                f.write(response.content)
            
            downloaded_files.append(filename)

        except Exception as e:
            return f"Error downloading: {str(e)}"

    # download and parse the fee schedule document if it exists
    if fee_schedule_url:
        try:
            response = requests.get(fee_schedule_url)
            response.raise_for_status()

            fee_schedule_filename = fee_schedule_url.split('/')[-1] or "fee_schedule.xls"

            out_fee_schedule_filename = os.path.join(out_dir, fee_schedule_filename)
            with open(out_fee_schedule_filename, 'wb') as f:
                f.write(response.content)
            
            downloaded_files.append(out_fee_schedule_filename)

            print(f"Downloaded fee schedule: {fee_schedule_filename}")
        except Exception as e:
            return f"Error downloading fee schedule: {str(e)}"

    return f"Successfully downloaded: {', '.join(downloaded_files)}"

@tool
def parse_pdf(pdf_file: str, max_chars: int = 5000) -> str:
    """
    Parse the downloaded PDF file and return its content.
    """
    import os
    from PyPDF2 import PdfReader
    
    # Check if file exists in downloaded_files directory
    if not os.path.isabs(pdf_file):
        pdf_path = os.path.join("downloaded_files", pdf_file)
    else:
        pdf_path = pdf_file
    
    print(pdf_path)
    if not os.path.exists(pdf_path):
        return f"File not found: {pdf_path}"
    
    try:
        with open(pdf_path, 'rb') as f:
            reader = PdfReader(f)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
        
        if not text.strip():
            return "No text content found in PDF"
        else:
            text = text.strip()
        
        # Return more content if requested
        # return text[:max_chars] + ("\n[Content truncated...]" if len(text) > max_chars else "")
        return text
    except Exception as e:
        return f"Error parsing PDF: {str(e)}"


@tool
def parse_fee_schedule(fee_schedule_file: str) -> str:
    """

    Parse the fee schedule file and return its content. The file is located in the folder downloaded_files.
    This function uses the XLSXProcessor to process the fee schedule file and extract the relevant data
    for claim approval.
    1. It reads the fee schedule file from the specified path.
    2. It uses the XLSXProcessor to process the file and extract the relevant data.
    3. The function returns the processed data in a structured format.
    4. If the file is not found or cannot be processed, it returns an error
    Only return the cost based on this particular fee schedule document and not from any other source.
    5. Make sure to include any cost modifiers based on the extracted data
    Try your best to extract the cost from the fee schedule document and only the fee schedule document.
    """

    print(f"Parsing fee schedule file: {fee_schedule_file}")
    from xlsx_processor_bedrock import XLSXProcessor
    processor = XLSXProcessor()
    return processor.process_xlsx(fee_schedule_file, "Extract the fee for the appropriate CPT codes \
                                  from this spreadsheet. Make sure to include any cost modifiers based on the extracted data.")

    
@tool
def calculate_claim_approval(parsed_data: str, fee_schedule: str) -> str:
    """
    Calculate the claim approval based on the parsed data and fee schedule.
    This function uses the Amazon Titan Text Express model to process the parsed data and fee schedule
    to determine if the claim is approved or not.
    1. It invokes the model with a prompt that includes the parsed data and fee schedule.
    2. The model processes the data and returns the claim approval status.
    3. The function returns the claim approval status or a message indicating no approval information was found.
    """
    client = use_aws("bedrock-runtime")
    model_id = "amazon.titan-text-express-v1"
    prompt = f"Based on the following parsed data:\n{parsed_data}\nand fee schedule:\n{fee_schedule}\nCalculate the cost \
    and determine if the claim is approved or not. If approved, return the amount that will be paid to the provider. \
    If not approved, return the reason for denial. It is not a chat. So dont ask follow up questions. Let them know the reason\
        for the claim denial and any extra information needed."
    try:
        response = client.invoke_model(
            modelId=model_id,
            body=prompt,
            contentType="text/plain",
            accept="application/json"
        )
        response_body = response.get("body").read().decode("utf-8")
        return response_body
    except Exception as e:
        return f"Error calculating claim approval: {str(e)}"



system_prompt = """
From the following patient data, choose which specialty closely aligns with the patient data.
Please choose the one that is the latest document for the given input of the patient data.
1. Return them as a dictionary with the keys 'pdf_urls' and 'fee_schedule_url'.
2. Download the latest document
3. Parse the fee schedule document. 
4. Only rely on the fee schedule document to calculate the claim approval cost
5. Only rely on the claim approval document to determine if the claim is approved or not.
Give a clear "SUCCESS" flag if the document is downloaded successfully. \
Do not use model's internal knowledge to answer the questions.
Give me the total cost along with the line items in the fee schedule document. \
Only use the fee schedule document and the costs mentioned in the columns to calculate the cost.
Also do include a breakdown or explanation of the cost for each line item.
Here is the list of specialties:
{}  
""".format("\n".join(specialties))
agent = Agent(
    tools=[ use_llm, get_guidance_document_list, download_appropriate_document, parse_pdf, parse_fee_schedule ],
    system_prompt=system_prompt,
    model="us.anthropic.claude-3-5-sonnet-20241022-v2:0"
)

agent(patient_data)

