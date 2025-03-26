import boto3
import json
import os
import pandas as pd
import sqlite3
import uuid
import zipfile
from botocore.exceptions import ClientError
from pathlib import Path
import time
import joblib


# S3 Bucket Creation and Setup
def create_s3_bucket(bucket_name, region):
    s3_client = boto3.client('s3')
    s3 = boto3.resource('s3')
    
    try:

        if region == 'us-east-1':
            # For us-east-1, don't specify LocationConstraint
            s3_client.create_bucket(Bucket=bucket_name)
            print(f"Created bucket: {bucket_name}")
        else:
            s3_client.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={'LocationConstraint': region}
            )
            print(f"Created bucket: {bucket_name}")

        return bucket_name

    except ClientError as e:
        print(f"Error: {e}")
        return None

# Data Processing Functions
def create_and_unzip(first_zip, new_directory, second_zip):
    notebook_dir = Path.cwd()
    new_dir = Path(new_directory)
    new_dir.mkdir(parents=True, exist_ok=True)
    print(f"Created directory: {new_dir}")
    
    with zipfile.ZipFile(first_zip, 'r') as zip_ref:
        zip_ref.extractall(new_directory)
    print(f"Unzipped {first_zip} to {new_directory}")
    
    subdirs = [d for d in new_dir.iterdir() if d.is_dir()]

    if subdirs:
        auto_found_dir = subdirs[0]
        print(f"Found directory: {auto_found_dir}")
        second_zip_path = auto_found_dir / second_zip
        print(second_zip_path)
        if second_zip_path.exists():
            with zipfile.ZipFile(second_zip_path, 'r') as zip_ref:
                zip_ref.extractall(notebook_dir)
            print(f"Unzipped {second_zip} in {notebook_dir}")
        else:
            print(f"Could not find {second_zip} in {auto_found_dir}")
    else:
        print(f"No directories found in {new_dir}")

def process_database_and_upload(database_folder, bucket_name):
    folder_path = Path(database_folder)
    database_name = folder_path.name
    
    sqlite_files = list(folder_path.glob('*.db')) + list(folder_path.glob('*.sqlite'))
    if not sqlite_files:
        print(f"No SQLite file found in {database_folder}")
        return
    
    sqlite_file = sqlite_files[0]
    print(f"\nProcessing database: {database_name}")
    print(f"SQLite file: {sqlite_file}")
    
    try:
        conn = sqlite3.connect(sqlite_file)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        s3_client = boto3.client('s3')
        
        for table in tables:
            table_name = table[0]
            print(f"\nProcessing table: {table_name}")
            
            try:
                df = pd.read_sql_query(f'SELECT * FROM "{table_name}"', conn)
                parquet_filename = f"{table_name}.parquet"
                local_parquet_path = folder_path / parquet_filename
                df.to_parquet(local_parquet_path, index=False)
                
                s3_key = f"{database_name}/{parquet_filename}"
                s3_client.upload_file(
                    str(local_parquet_path),
                    bucket_name,
                    s3_key
                )
                print(f"Uploaded to s3://{bucket_name}/{s3_key}")
                os.remove(local_parquet_path)
                
            except Exception as e:
                print(f"Error processing table {table_name}: {str(e)}")
                continue
        
        conn.close()
        
    except Exception as e:
        print(f"Error processing database {database_name}: {str(e)}")
        return

def set_athena_result_location(result_bucket):
    try:
        athena_client = boto3.client('athena')
        s3_output_location = f's3://{result_bucket}/athena-results/'
        
        response = athena_client.update_work_group(
            WorkGroup='primary',
            ConfigurationUpdates={
                'ResultConfigurationUpdates': {
                    'OutputLocation': s3_output_location
                },
                'EnforceWorkGroupConfiguration': True
            }
        )
        
        print(f"Successfully set Athena query result location to: {s3_output_location}")
        return True
        
    except Exception as e:
        print(f"Error setting result location: {e}")
        return False

def list_s3_folders_and_files(bucket_name):
    """Get all database folders and their parquet files"""
    s3_client = boto3.client('s3')
    
    try:
        # Get all objects in bucket
        paginator = s3_client.get_paginator('list_objects_v2')
        database_tables = {}
        
        for page in paginator.paginate(Bucket=bucket_name):
            if 'Contents' not in page:
                continue
                
            for obj in page['Contents']:
                # Split the key into parts
                parts = obj['Key'].split('/')
                
                # Check if it's a parquet file
                if len(parts) >= 2 and parts[-1].endswith('.parquet'):
                    database_name = parts[0]
                    table_name = parts[-1].replace('.parquet', '')
                    
                    if database_name not in database_tables:
                        database_tables[database_name] = []
                    database_tables[database_name].append(table_name)
        
        return database_tables
    
    except ClientError as e:
        print(f"Error listing S3 contents: {e}")
        return None


def generate_and_create_table(results_bucket_name, parquet_bucket_name, database_name, table_name):
    """Generate and create a single table"""
    try:
        # Generate DDL
        s3_path = f's3://{parquet_bucket_name}/{database_name}/{table_name}.parquet'
        df = pd.read_parquet(s3_path)
        
        # Map pandas types to Athena types
        type_mapping = {
            'object': 'string',
            'int64': 'int',
            'float64': 'double',
            'bool': 'boolean',
            'datetime64[ns]': 'timestamp'
        }
        
        # Generate column definitions
        columns = []
        for col, dtype in df.dtypes.items():
            athena_type = type_mapping.get(str(dtype), 'string')
            columns.append(f"`{col}` {athena_type}")
        
        # Create DDL statement
        column_definitions = ',\n    '.join(columns)
        s3_location = f's3://{parquet_bucket_name}/{database_name}/'
        
        ddl = f"""CREATE EXTERNAL TABLE IF NOT EXISTS {database_name}.{table_name} (
        {column_definitions}
    )
    STORED AS PARQUET
    LOCATION '{s3_location}';"""
        
        print(f"\nGenerating table: {database_name}.{table_name}")
        
        # Execute DDL
        athena_client = boto3.client('athena')
        
        # Create table
        response = athena_client.start_query_execution(
            QueryString=ddl,
            QueryExecutionContext={
                'Database': database_name
            },
            ResultConfiguration={
                'OutputLocation': f's3://{results_bucket_name}/athena-results/'
            }
        )
        
        # Wait for table creation
        query_execution_id = response['QueryExecutionId']
        while True:
            response = athena_client.get_query_execution(QueryExecutionId=query_execution_id)
            state = response['QueryExecution']['Status']['State']
            if state in ['SUCCEEDED', 'FAILED', 'CANCELLED']:
                break
            time.sleep(1)
        
        if state == 'SUCCEEDED':
            print(f"Created table: {database_name}.{table_name}")
            return True
        else:
            print(f"Failed to create table {database_name}.{table_name}: {state}")
            return False
            
    except Exception as e:
        print(f"Error creating table {database_name}.{table_name}: {e}")
        return False

def create_all_databases_and_tables(results_bucket_name, parquet_bucket_name):
    """Create all databases and tables from S3 bucket structure"""
    try:
        # Get database and table structure from S3
        database_tables = list_s3_folders_and_files(parquet_bucket_name)
        if not database_tables:
            print("No databases/tables found in S3")
            return False
            
        athena_client = boto3.client('athena')
        
        # Process each database
        for database_name, tables in database_tables.items():
            print(f"\nProcessing database: {database_name}")
            
            # Create database
            create_database = f"CREATE DATABASE IF NOT EXISTS {database_name}"
            response = athena_client.start_query_execution(
                QueryString=create_database,
                ResultConfiguration={
                    'OutputLocation': f's3://{results_bucket_name}/athena-results/'
                }
            )
            
            # Wait for database creation
            query_execution_id = response['QueryExecutionId']
            while True:
                response = athena_client.get_query_execution(QueryExecutionId=query_execution_id)
                state = response['QueryExecution']['Status']['State']
                if state in ['SUCCEEDED', 'FAILED', 'CANCELLED']:
                    break
                time.sleep(1)
            
            if state == 'SUCCEEDED':
                print(f"Created database: {database_name}")
                
                # Create each table in the database
                for table_name in tables:
                    generate_and_create_table(
                        results_bucket_name,
                        parquet_bucket_name,
                        database_name,
                        table_name
                    )
            else:
                print(f"Failed to create database {database_name}: {state}")
                continue
        
        return True
        
    except Exception as e:
        print(f"Error in create_all_databases_and_tables: {e}")
        return False

def filter_on_db(input_file, output_file, db_name):
    # Read the input JSON file
    with open(input_file, 'r') as f:
        data = json.load(f)
    
    # Filter entries where db_id is "california_schools"
    filtered_data = [entry for entry in data if entry.get('db_id') == db_name]
    
    # Write the filtered data to output file
    with open(output_file, 'w') as f:
        json.dump(filtered_data, f, indent=2)

def main():
    # Configuration
    REGION = os.environ.get('REGION')
    BASE_BUCKET_NAME = os.environ.get('BASE_BUCKET_NAME')
    ATHENA_RESULTS_BUCKET_NAME = os.environ.get('ATHENA_RESULTS_BUCKET_NAME')
    BASE_DIR = os.environ.get('BASE_DIR')
    DATABASE_NAME = os.environ.get('DATABASE_NAME')


    # Step 1: Unzip files
    create_and_unzip(
        first_zip='dev.zip',
        new_directory='unzipped_dev',
        second_zip='dev_databases.zip'
    )

    # Step 2: Create buckets
    main_bucket = create_s3_bucket(BASE_BUCKET_NAME, REGION)
    athena_results_bucket = create_s3_bucket(ATHENA_RESULTS_BUCKET_NAME, REGION)

    if not all([main_bucket, athena_results_bucket]):
        print("Failed to create required buckets")
        return

    # Step 3: Process and upload database
    base_path = Path(BASE_DIR)
    target_folder = base_path/DATABASE_NAME  # Create path to specific database folder

    if target_folder.exists() and target_folder.is_dir():
        process_database_and_upload(target_folder, main_bucket)
    else:
        print(f"Database folder '{DATABASE_NAME}' not found in {BASE_DIR}")

    # Step 4: Setup Athena configurations
    set_athena_result_location(athena_results_bucket)

    # Step 5: Create Athena databases and tables
    success = create_all_databases_and_tables(athena_results_bucket, main_bucket)
    if success:
        print("\nCompleted creating all databases and tables in Athena!")

    # Step 6: Generate birdsql.json
    filter_on_db('unzipped_dev/dev_20240627/dev.json','birdsql_data.json',DATABASE_NAME)
    print("Created birdsql_data.json for agent")


if __name__ == "__main__":
    main()
