import boto3
import json

# Cognito設定
USER_POOL_ID = "us-west-2_nS2VRVQua"
CLIENT_ID = "2faf353j7nl9gh1ond7a5ehlem"
REGION = "us-west-2"

# ユーザー名とパスワードを入力
username = input("Cognito Username: ")
password = input("Cognito Password: ")

client = boto3.client('cognito-idp', region_name=REGION)

try:
    response = client.initiate_auth(
        ClientId=CLIENT_ID,
        AuthFlow='USER_PASSWORD_AUTH',
        AuthParameters={
            'USERNAME': username,
            'PASSWORD': password
        }
    )
    
    access_token = response['AuthenticationResult']['AccessToken']
    print("\n✅ Access Token取得成功:")
    print(access_token)
    
except Exception as e:
    print(f"\n❌ エラー: {e}")
