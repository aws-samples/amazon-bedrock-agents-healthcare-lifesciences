import boto3
import base64
import pandas as pd
from typing import Dict, Any

class XLSXProcessor:
    def __init__(self, region_name: str = 'us-east-1'):
        self.bedrock_client = boto3.client('bedrock-runtime', region_name=region_name)

    def process_xlsx(self, file_path: str, prompt: str, model_id: str = 'anthropic.claude-3-sonnet-20240229-v1:0') -> str:
        """Process XLSX file using Bedrock document blocks"""
        # Convert Excel to CSV for better compatibility
        df = pd.read_excel(file_path)
        csv_content = df.to_csv(index=False)
        encoded_document = base64.b64encode(csv_content.encode('utf-8')).decode('utf-8')
        
        messages = [{
            "role": "user",
            "content": [{
                "document": {
                    "name": "data",
                    "format": "csv",
                    "source": {"bytes": encoded_document}
                }
            }, {
                "text": prompt
            }]
        }]
        
        response = self.bedrock_client.converse(
            modelId=model_id,
            messages=messages,
            inferenceConfig={"maxTokens": 4000, "temperature": 0.1}
        )
        
        return response['output']['message']['content'][0]['text']

# Usage
if __name__ == "__main__":
    processor = XLSXProcessor()
    result = processor.process_xlsx(
        "family.xlsx", 
        "Extract healthcare codes and costs from this spreadsheet"
    )
    print(result)