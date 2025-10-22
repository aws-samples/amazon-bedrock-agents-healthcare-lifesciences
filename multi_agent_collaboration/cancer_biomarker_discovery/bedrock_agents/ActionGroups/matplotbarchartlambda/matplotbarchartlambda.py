import os
os.environ['MPLCONFIGDIR'] = '/tmp'
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import io
import boto3
import ast


s3_bucket = os.environ['S3_BUCKET']

def bar_chart(title, x_values, y_values, x_label, y_label):
    
    try:
        # Try parsing as Python literal
        x_values_parsed= ast.literal_eval(x_values)
    except (ValueError, SyntaxError):
        # Fall back to simple string splitting
        x_values_parsed =  [id.strip() for id in x_values.strip('[]').split(',')]

    print(x_values_parsed)
    try:
        # Try parsing as Python literal
        y_values_parsed= ast.literal_eval(y_values)
    except (ValueError, SyntaxError):
        # Fall back to simple string splitting
        y_values_parsed =  [id.strip() for id in y_values.strip('[]').split(',')]
    print(y_values_parsed)
    fig, ax = plt.subplots(figsize=(10, 6))  
    ax.bar(x_values_parsed, y_values_parsed, color='blue')
    ax.set_title(title)
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    
    output_name=f"{title}.png"
    
    img_data = io.BytesIO()
    fig.savefig(img_data, format='png')
    img_data.seek(0)
    s3 = boto3.resource('s3')
    bucket = s3.Bucket(s3_bucket)
    KEY = 'graphs/' + str(output_name)
    bucket.put_object(Body=img_data, ContentType='image/png', Key=KEY)

    try:
        s3_client = boto3.client('s3')
        print(s3_bucket)
        print(KEY)
        presigned_url = s3_client.generate_presigned_url('get_object',
                Params={'Bucket': s3_bucket, 'Key': KEY},
                ExpiresIn=3600
            )
        print(presigned_url)
    except Exception as e:
        return {
                'statusCode': 500,
                'body': json.dumps({'error': str(e)})
        }    
    
    result = f'Your bar chart named {title} is saved to your s3 bucket'
    print(result)
    return presigned_url

def handler(event, context):
    # TODO implement
    agent = event['agent']
    actionGroup = event['actionGroup']
    function = event['function']
    parameters = event.get('parameters', [])
    try:
        if function == "bar_chart":
            print(parameters)
            for param in parameters:
                if param["name"] == "title":
                    title = param["value"]
                if param["name"] == "x_values":
                    x_values = param["value"]
                if param["name"] == "y_values":
                    y_values = param["value"]
                if param["name"] == "x_label":
                    x_label = param["value"]
                if param["name"] == "y_label":
                    y_label = param["value"]
                
        # Execute your business logic here. For more information, refer to: https://docs.aws.amazon.com/bedrock/latest/userguide/agents-lambda.html
        presigned_url = bar_chart(title,x_values, y_values, x_label, y_label)
        print('successfully finished')
        responseBody = {
            "TEXT": {
                "body": f"Bar chart saved at the following URL: {presigned_url}"
            }
        }
    except Exception as e:
        responseBody = {
            "TEXT": {
                "body": "An error occurred: {}".format(str(e))
            }
        }
    
    action_response = {
        'actionGroup': actionGroup,
        'function': function,
        'functionResponse': {
            'responseBody': responseBody
        }

    }

    dummy_function_response = {'response': action_response, 'messageVersion': event['messageVersion']}
    print("Response: {}".format(dummy_function_response))

    return dummy_function_response
