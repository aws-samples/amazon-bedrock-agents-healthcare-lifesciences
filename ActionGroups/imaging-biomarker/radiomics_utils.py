import pandas as pd
import time
import numpy as np
from radiomics import featureextractor
import boto3
# import sagemaker
# from sagemaker.session import Session
# from sagemaker.feature_store.feature_group import FeatureGroup
# from sagemaker import get_execution_role

# sagemaker_session = sagemaker.Session()
# region = sagemaker_session.boto_region_name
# print('region is %s' % region)

# boto_session = boto3.Session(region_name=region)
# role = get_execution_role()
# print('role is %s' % role)

# sagemaker_client = boto3.client(service_name='sagemaker', region_name=region)
# featurestore_runtime = boto3.client('sagemaker-featurestore-runtime', region_name=region)

# feature_store_session = Session(
#     boto_session=boto_session,
#     sagemaker_client=sagemaker_client,
#     sagemaker_featurestore_runtime_client=featurestore_runtime
# )


def cast_object_to_string(data_frame):
    for label in data_frame.columns:
        if data_frame.dtypes[label] == 'object':
            data_frame[label] = data_frame[label].astype("str").astype("string")

            
def compute_features(imageName, maskName):
    extractor = featureextractor.RadiomicsFeatureExtractor()
    featureVector = extractor.execute(imageName, maskName)
    
    new_dict={}
    for featureName in featureVector.keys():
        print("Computed %s: %s" % (featureName, featureVector[featureName]))
        print(type(featureVector[featureName]))
        if isinstance(featureVector[featureName], np.ndarray):
            new_dict[featureName]=float(featureVector[featureName])
        else:
            new_dict[featureName]=featureVector[featureName]
            
    df=pd.DataFrame.from_dict(new_dict, orient='index').T
    df=df.convert_dtypes(convert_integer=False)
    df['imageName']=imageName
    df['maskName']=maskName

    return df
            
# def check_feature_group(feature_group_name):
#     feature_group = FeatureGroup(name=feature_group_name, sagemaker_session=feature_store_session)
#     status = None
#     try:
#         status = feature_group.describe()['FeatureGroupStatus']
#     except:
#         pass
    
#     if status == 'Created':
#         return feature_group
#     elif status is None:
#         return False
#     else:
#         wait_for_feature_group_creation_complete(feature_group)
#         return feature_group
        
    
    
# def create_feature_group(feature_group_name, dataframe, s3uri, record_id = 'Subject', event_time = 'EventTime', 
#                          enable_online_store = True):
#     print(feature_group_name)
#     print(feature_store_session)
#     feature_group = FeatureGroup(name=feature_group_name, sagemaker_session=feature_store_session)
#     feature_group.load_feature_definitions(data_frame=dataframe)
#     feature_group.create(s3_uri=s3uri,
#                          record_identifier_name=record_id,
#                          event_time_feature_name=event_time,
#                          role_arn=role,
#                          enable_online_store=enable_online_store)
#     wait_for_feature_group_creation_complete(feature_group)

#     return feature_group
    
    
# def wait_for_feature_group_creation_complete(feature_group):
#     status = feature_group.describe()['FeatureGroupStatus']
#     while status == "Creating":
#         print("Waiting for Feature Group Creation")
#         time.sleep(5)
#         status = feature_group.describe()['FeatureGroupStatus']
#     if status != "Created":
#         raise RuntimeError(f"Failed to create feature group {feature_group.name}")
#     print(f"FeatureGroup {feature_group.name} successfully created.")