#!/usr/bin/env python3
"""
Script to populate the HCP Intelligence DynamoDB table with sample data.
"""

import boto3
import uuid
import time
from datetime import datetime, timedelta

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb', region_name='us-west-2')

# Reference the table
table_name = 'HCPIntelligenceTable'
table = dynamodb.Table(table_name)

# Calculate expiration time (30 days from now)
expiration_time = int((datetime.now() + timedelta(days=30)).timestamp())

# Sample healthcare provider data
hcp_data = [
    {
        'HcpId': str(uuid.uuid4()),
        'FullName': 'Sarah Johnson',
        'Specialty': 'Cardiology',
        'Hospital': 'Memorial Hospital',
        'YearsExperience': 15,
        'Certifications': ['Board Certified', 'FACC'],
        'ContactInfo': {
            'Email': 'sjohnson@example.com',
            'Phone': '555-123-4567'
        },
        'ExpirationTime': expiration_time
    },
    {
        'HcpId': str(uuid.uuid4()),
        'FullName': 'Michael Chen',
        'Specialty': 'Neurology',
        'Hospital': 'University Medical Center',
        'YearsExperience': 8,
        'Certifications': ['Board Certified', 'AAN Member'],
        'ContactInfo': {
            'Email': 'mchen@example.com',
            'Phone': '555-234-5678'
        },
        'ExpirationTime': expiration_time
    },
    {
        'HcpId': str(uuid.uuid4()),
        'FullName': 'Emily Rodriguez',
        'Specialty': 'Pediatrics',
        'Hospital': 'Children\'s Hospital',
        'YearsExperience': 12,
        'Certifications': ['Board Certified', 'AAP Fellow'],
        'ContactInfo': {
            'Email': 'erodriguez@example.com',
            'Phone': '555-345-6789'
        },
        'ExpirationTime': expiration_time
    },
    {
        'HcpId': str(uuid.uuid4()),
        'FullName': 'David Wilson',
        'Specialty': 'Oncology',
        'Hospital': 'Cancer Treatment Center',
        'YearsExperience': 20,
        'Certifications': ['Board Certified', 'ASCO Member'],
        'ContactInfo': {
            'Email': 'dwilson@example.com',
            'Phone': '555-456-7890'
        },
        'ExpirationTime': expiration_time
    },
    {
        'HcpId': str(uuid.uuid4()),
        'FullName': 'Jennifer Lee',
        'Specialty': 'Dermatology',
        'Hospital': 'Skin Health Clinic',
        'YearsExperience': 10,
        'Certifications': ['Board Certified', 'AAD Member'],
        'ContactInfo': {
            'Email': 'jlee@example.com',
            'Phone': '555-567-8901'
        },
        'ExpirationTime': expiration_time
    }
]

def add_items_to_table():
    """Add sample items to the DynamoDB table."""
    print(f"Adding {len(hcp_data)} items to {table_name}...")
    
    for item in hcp_data:
        try:
            response = table.put_item(Item=item)
            print(f"Added HCP: {item['FullName']} (ID: {item['HcpId']})")
            # Small delay to avoid throttling
            time.sleep(0.1)
        except Exception as e:
            print(f"Error adding {item['FullName']}: {str(e)}")
    
    print("Data population complete!")

def query_by_full_name(full_name):
    """Query the table by full name using the GSI."""
    print(f"\nQuerying for HCP with name: {full_name}")
    
    try:
        response = table.query(
            IndexName='FullNameIndex',
            KeyConditionExpression=boto3.dynamodb.conditions.Key('FullName').eq(full_name)
        )
        
        if response['Items']:
            for item in response['Items']:
                print(f"Found: {item['FullName']} (ID: {item['HcpId']})")
                print(f"  Specialty: {item['Specialty']}")
                print(f"  Hospital: {item['Hospital']}")
                print(f"  Experience: {item['YearsExperience']} years")
        else:
            print(f"No HCP found with name: {full_name}")
            
    except Exception as e:
        print(f"Error querying: {str(e)}")

def get_item_by_id(hcp_id):
    """Get an item directly by its HcpId (primary key)."""
    print(f"\nGetting HCP with ID: {hcp_id}")
    
    try:
        response = table.get_item(Key={'HcpId': hcp_id})
        
        if 'Item' in response:
            item = response['Item']
            print(f"Found: {item['FullName']} (ID: {item['HcpId']})")
            print(f"  Specialty: {item['Specialty']}")
            print(f"  Hospital: {item['Hospital']}")
            print(f"  Experience: {item['YearsExperience']} years")
        else:
            print(f"No HCP found with ID: {hcp_id}")
            
    except Exception as e:
        print(f"Error getting item: {str(e)}")

if __name__ == "__main__":
    # Add items to the table
    add_items_to_table()
    
    # Demonstrate querying by full name (using GSI)
    query_by_full_name("Sarah Johnson")
    
    # Demonstrate getting an item by ID (using primary key)
    # Get the first HCP's ID from our sample data
    first_hcp_id = hcp_data[0]['HcpId']
    get_item_by_id(first_hcp_id)