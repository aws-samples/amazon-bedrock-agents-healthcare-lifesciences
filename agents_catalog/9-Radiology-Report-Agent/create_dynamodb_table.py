import os
import boto3

# create a dynamodb table with the name RadiologyReports. 
def create_dynamodb_table(tablename = "RadiologyReports", region="us-west-2"):
    dynamodb = boto3.resource("dynamodb", region_name=region)
    table = dynamodb.create_table(
        TableName=tablename,
        KeySchema=[
            {
                "AttributeName": "PatientID",
                "KeyType": "HASH"
            },
            {
                "AttributeName": "Report",
                "KeyType": "RANGE"
            }
        ],
        AttributeDefinitions=[
            {
                "AttributeName": "PatientID",
                "AttributeType": "S"
            },
            {
                "AttributeName": "Report",
                "AttributeType": "S"
            }
        ],
        ProvisionedThroughput={
            "ReadCapacityUnits": 5,
            "WriteCapacityUnits": 5
        }
    )
    return table

def enter_data_to_dynamodb(table, data):
    # enter data to the dynamodb table
    for item in data:
        table.put_item(
            Item={
                "PatientID": item["PatientID"],
                "Report": item["Report"]
            }
        )
    print("Data entered successfully")

if __name__ == "__main__":
    # check if the table already exists if not create it
    table_name = "RadiologyReports"
    try:
        table = boto3.resource("dynamodb", region_name="us-west-2").Table(table_name)
        table.load()
        print("Table already exists")
    except Exception as e:
        print("Creating table...")
        table = create_dynamodb_table()
        print("Table created successfully")
        
    sample_report_dir = "./sample_reports"
    
    for _filename in os.listdir(sample_report_dir):
        with open(os.path.join(sample_report_dir, _filename), "r") as f:
            report = f.read()
            patient_id = _filename.split(".")[0].split("_")[1]
            print(patient_id)
            data = {
                "PatientID": patient_id,
                "Report": report
            }
            enter_data_to_dynamodb(table, [data])
            