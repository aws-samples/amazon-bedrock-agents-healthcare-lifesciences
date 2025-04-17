#!/usr/bin/env python3
"""
Example script demonstrating how to query the HCPData DynamoDB table.
This script shows how to:
1. Query by primary key (HcpId)
2. Find by FullName using scan with filter
3. Scan the table with filters
"""

import boto3
from boto3.dynamodb.conditions import Key, Attr
import json
from pprint import pprint

# Initialize DynamoDB resource
# boto_session = boto3.Session(profile_name='ujjwalr-directs+hcls-agent-dev-Admin')
dynamodb = boto3.resource('dynamodb')
table_name = 'HCPIntelligenceTable'  # Replace with your actual table name if different
table = dynamodb.Table(table_name)

def query_by_id(Id):
    """
    Query the table using the primary key (Id)
    """
    print(f"\n=== Querying by Id: {Id} ===")
    
    response = table.get_item(
        Key={
            'Id': Id
        }
    )
    
    if 'Item' in response:
        print("HCP found:")
        pprint(response['Item'])
        return response['Item']
    else:
        print(f"No HCP found with ID: {Id}")
        return None

def query_by_full_name(full_name):
    """
    Find items by FullName using a scan operation with a filter
    Note: Without a GSI, this requires a full table scan which is less efficient
    """
    print(f"\n=== Finding by FullName: {full_name} ===")
    
    response = table.scan(
        FilterExpression=Attr('FullName').eq(full_name)
    )
    
    if response['Items']:
        print(f"Found {len(response['Items'])} HCP(s):")
        for item in response['Items']:
            pprint(item)
        return response['Items']
    else:
        print(f"No HCP found with name: {full_name}")
        return []

def scan_by_specialty(specialty):
    """
    Scan the table with a filter on Specialty
    Note: Scans are less efficient than queries but allow filtering on non-key attributes
    """
    print(f"\n=== Scanning for HCPs with Specialty: {specialty} ===")
    
    response = table.scan(
        FilterExpression=Attr('Specialty').eq(specialty)
    )
    
    if response['Items']:
        print(f"Found {len(response['Items'])} HCP(s) with specialty {specialty}:")
        for item in response['Items']:
            print(f"- {item['FullName']} (ID: {item['Id']})")
        return response['Items']
    else:
        print(f"No HCPs found with specialty: {specialty}")
        return []

def list_all_hcps(limit=10):
    """
    List all HCPs in the table (with an optional limit)
    """
    print(f"\n=== Listing all HCPs (limit: {limit}) ===")
    
    response = table.scan(Limit=limit)
    
    if response['Items']:
        print(f"Found {len(response['Items'])} HCP(s):")
        for item in response['Items']:
            print(f"- {item['FullName']} (Specialty: {item.get('Specialty', 'N/A')})")
        
        if 'LastEvaluatedKey' in response:
            print("Note: More results available. Increase the limit or implement pagination.")
            
        return response['Items']
    else:
        print("No HCPs found in the table.")
        return []

def advanced_query_example():
    """
    Demonstrates a more complex query using scan with multiple filter conditions
    """
    print("\n=== Advanced Query: Neurologists with 8+ years experience ===")
    
    # Scan for neurologists with filter conditions
    response = table.scan(
        FilterExpression=Attr('Specialty').eq('Neurology') & Attr('YearsExperience').gte(8)
    )
    
    if response['Items']:
        print(f"Found {len(response['Items'])} neurologist(s) with 8+ years experience:")
        for item in response['Items']:
            print(f"- {item['FullName']} ({item['YearsExperience']} years experience)")
            print(f"  Topics of interest: {', '.join(item.get('TopicsOfInterest', ['None']))}")
        return response['Items']
    else:
        print("No neurologists found with 8+ years experience.")
        return []

if __name__ == "__main__":
    # Example usage
    print("DynamoDB HCPData Query Examples")
    print("===============================")
    
    # Example Id from the mock data
    example_id = "d1f2539a-0fb2-4fb6-9f6d-fc3299dc589f"  # Sarah Johnson
    query_by_id(example_id)
    
    # Find by name using scan with filter
    query_by_full_name("Michael Chen")
    
    # Scan for HCPs by specialty
    scan_by_specialty("Cardiology")
    
    # List all HCPs (limited to 5)
    list_all_hcps(limit=5)
    
    # Advanced query example
    advanced_query_example()
    
    print("\nDone!")
