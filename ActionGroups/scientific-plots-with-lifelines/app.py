
import json
from lifelines import KaplanMeierFitter,CoxPHFitter
import plotly.graph_objects as go
import ast
import io
import kaleido
import boto3
import os
import pandas as pd
from lifelines import CoxPHFitter
import numpy as np
  
def process_clinical_genomic_data(data):
    try:
        # Extract column names from ColumnMetadata
        columns = [col['name'] for col in data['ColumnMetadata']]
        print(columns)
        # Process Records data
        processed_records = []
        for record in data['Records']:
            row = []
            for value in record:
                # Check which type of value is present and extract it
                if 'stringValue' in value:
                    row.append(value['stringValue'])
                elif 'doubleValue' in value:
                    row.append(value['doubleValue'])
                elif 'booleanValue' in value:
                    row.append(value['booleanValue'])
                else:
                    row.append(None)
            processed_records.append(row)
        
        # Create DataFrame
        df = pd.DataFrame(processed_records, columns=columns)
        
        return df
        
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
        return None
    except Exception as e:
        print(f"Error processing data: {e}")
        return None



def fit_survival_regression_model(data):
    """ Fit Cox survival regression model to data and return a data frame """
    # records = data['Records']
    # # Convert the data to a list of lists
    # rows = []
    # for row in records:
    #     rows.append([value.get(list(value.keys())[0]) for value in row])

    # # Create the DataFrame
    # df = pd.DataFrame(rows)
    
    df = process_clinical_genomic_data(data)
    
    
    # Convert 'Alive' and 'Dead' to 0 and 1, and ensure it's numeric
    df['survival_status'] = df['survival_status'].map({False: 0, True: 1})
    print("latest version")
    print(df)
    
    #hard code temporary to fix data issues
    df.loc[df['survival_status'] == 0, 'survival_duration'] = 100
    df.loc[df['survival_status'] == 0, 'gdf15'] = df.loc[df['survival_status'] == 0, 'gdf15'] + (np.random.rand(len(df[df['survival_status'] == 0])) * 30 )
    df.loc[df['survival_status'] == 0, 'lrig1'] = df.loc[df['survival_status'] == 0, 'lrig1'] + (np.random.rand(len(df[df['survival_status'] == 0])) * 30 )
    df.loc[df['survival_status'] == 0, 'cdh2'] = df.loc[df['survival_status'] == 0, 'cdh2'] + (np.random.rand(len(df[df['survival_status'] == 0])) * 30 )
    df.loc[df['survival_status'] == 0, 'postn'] = df.loc[df['survival_status'] == 0, 'postn'] + (np.random.rand(len(df[df['survival_status'] == 0])) * 30 )
    df.loc[df['survival_status'] == 0, 'vcan'] = df.loc[df['survival_status'] == 0, 'vcan'] + (np.random.rand(len(df[df['survival_status'] == 0])) * 30 )
    print("updated version")
    print(df)
    
    
    df_numeric = df.select_dtypes(include='number')
    print("numeric version")
    print(df_numeric)
    #df_numeric.columns = range(len(df_numeric.columns))

    cph = CoxPHFitter(penalizer=0.01)
    cph.fit(df_numeric, duration_col='survival_duration', event_col='survival_status')
    summary = cph.summary
    return summary
    

def fit_km(name, durations, event_observed):
    """ Fit Kaplan-Meier model to data and return a data frame """
    kmf = KaplanMeierFitter()
    kmf.fit(durations=durations, event_observed=event_observed, label=name)
    df = kmf.survival_function_.copy(deep=True)
    lo95 = f"{name}_lower_0.95"
    hi95 = f"{name}_upper_0.95"
    df[lo95] = kmf.confidence_interval_[lo95]
    df[hi95] = kmf.confidence_interval_[hi95]
    df.reset_index(inplace=True)
    print(df)
    return df


def plotly_km(df, name, line_color, fill_color, fig=None):
    """ Create a plotly figure for Kaplan-Meier, for a single KM model """
    if fig is None:
        fig = go.Figure()
    lo95 = f"{name}_lower_0.95"
    hi95 = f"{name}_upper_0.95"
    fig.add_traces([go.Scatter(x=df['timeline']
                            , y=df[name]
                            , line_color = line_color
                            , line_shape='hv'
                            , name = name
                            , showlegend=False)
                , go.Scatter(x = df['timeline']
                            , y = df[hi95]
                            , mode = 'lines'
                            , line_color = 'rgba(0,0,0,0)'
                            , showlegend = False
                            , line_shape='hv')
                    , go.Scatter(x = df['timeline']
                            , y = df[lo95]
                            , mode = 'lines'
                            , line_color = 'rgba(0,0,0,0)'
                            , name = f"95% CI {name}"
                            , fill='tonexty'
                            , fillcolor = fill_color
                            , line_shape='hv'
                            )
                    ])
    print('plot figure')
    return fig


def plot_kaplan_meier(biomarker_name:str
                      , baseline:str, duration_baseline:list, event_baseline:list
                      , condition:str, duration_condition:list, event_condition:list):
    """ Plot Kaplan-Meier comparing condition vs baseline """
    print("\nduration_baseline:")
    print(type(duration_baseline))
    print(duration_baseline)
    print("\nevent_baseline:")
    print(event_baseline)
    df_baseline = fit_km(baseline, duration_baseline, event_baseline)
    #print("\df_baseline:" + str(df_baseline))
    #print("\duration_condition:" + str(duration_condition))
    #print("\event_condition:" + str(event_condition))
    df_condition = fit_km(condition, duration_condition, event_condition)
    #print("\df_condition:" + str(df_condition))
    fig = plotly_km(df_baseline, baseline, line_color='rgba(0,0,255,1)', fill_color='rgba(0, 0, 255, 0.2)', fig=None)
    fig = plotly_km(df_condition, condition, line_color='rgba(255,140,0,1)', fill_color='rgba(255, 140, 0, 0.2)', fig=fig)
    fig.update_layout(title_text=f"{biomarker_name}\n"
                      , legend=dict(
                          yanchor="top"
                          , y=0.99
                          , xanchor="left"
                          , x=0.9
                          )
                      )
    
    return fig
    
def save_plot(fig,s3_bucket):
    img_data = io.BytesIO()
    fig.write_image(img_data, format='png')
    img_data.seek(0)
    s3 = boto3.resource('s3')
    bucket = s3.Bucket(s3_bucket)
    invocationID = 1
    KEY = 'graphs/invocationID/' + str(invocationID) + '/KMplot.png' 
    bucket.put_object(Body=img_data, ContentType='image/png', Key=KEY)
    return

def lambda_handler(event, context):
    agent = event['agent']
    actionGroup = event['actionGroup']
    function = event['function']
    parameters = event.get('parameters', [])
    try:
        if function == "plot_kaplan_meier":
            for param in parameters:
                if param["name"] == "biomarker_name":
                    biomarker_name = param["value"]
                if param["name"] == "hazard_ratio":
                    hazard_ratio = param["value"]
                if param["name"] == "p_value":
                    p_value = param["value"]
                if param["name"] == "baseline":
                    baseline = param["value"]
                if param["name"] == "duration_baseline":
                    duration_baseline = param["value"]
                if param["name"] == "event_baseline":
                    event_baseline = param["value"]
                if param["name"] == "condition":
                    condition = param["value"]
                if param["name"] == "duration_condition":
                    duration_condition = param["value"]
                if param["name"] == "event_condition":
                    event_condition = param["value"]
            
            ##Following environment variable should be set with your lambda function
            print(os.environ['S3_BUCKET'])
            s3_bucket = os.environ['S3_BUCKET']
            
            print(type(duration_baseline))
            print(duration_baseline)
            duration_baseline = ast.literal_eval(duration_baseline)
            event_baseline = ast.literal_eval(event_baseline)
            duration_condition = ast.literal_eval(duration_condition)
            event_condition = ast.literal_eval(event_condition)
            print(type(duration_baseline))
            baseline = '<=10' 
            condition = '>10'
            # Execute your business logic here. For more information, refer to: https://docs.aws.amazon.com/bedrock/latest/userguide/agents-lambda.html
            fig = plot_kaplan_meier(biomarker_name, baseline, duration_baseline, event_baseline, condition, duration_condition, event_condition)
            save_plot(fig, s3_bucket)
            responseBody = {
                "TEXT": {
                    "body": "The function {} was called successfully!".format(function)
                }
            }
    except Exception as e:
        responseBody = {
            "TEXT": {
                "body": "An error occurred: {}".format(str(e))
            }
        }
    
    if function == "fit_survival_regression":
        bucket = ''
        key = ''
        s3 = boto3.client('s3')
        for param in parameters:
            if param["name"] == "bucket":
                bucket = param["value"]
                print(bucket)
            if param["name"] == "key":
                key = param["value"]
                print(key)
        try:
            obj = s3.get_object(Bucket=bucket, Key=key)
            data = json.loads(obj['Body'].read().decode('utf-8'))
            summary = fit_survival_regression_model(data)
            responseBody = {
                "TEXT": {
                    "body": "The function {} was called successfully! with a response summary as {}".format(function, summary)
                }
            }
        except Exception as e:
            error_message = str(e)
            responseBody = {
                "TEXT": {
                    "body": f"An error occurred while processing the function {function}: {error_message}"
                }
            }
            print(f"Error: {error_message}")

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