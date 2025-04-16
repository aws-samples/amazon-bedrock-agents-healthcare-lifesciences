#!/usr/bin/env python3
"""
Examples of different ways to query the HCP Intelligence DynamoDB table.
"""

import boto3
from boto3.dynamodb.conditions import Key, Attr

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb', region_name='us-west-2')

# Reference the table
table_name = 'HCPIntelligenceTable'
table = dynamodb.Table(table_name)

def query_by_full_name(full_name):
    """
    Query for HCPs by full name using the GSI.
    This is efficient because we're using the FullNameIndex GSI.
    """
    print(f"\nSearching for HCP with name: {full_name}")
    
    try:
        response = table.query(
            IndexName='FullNameIndex',
            KeyConditionExpression=Key('FullName').eq(full_name)
        )
        
        if response['Items']:
            print(f"Found {len(response['Items'])} HCPs with name '{full_name}':")
            for item in response['Items']:
                print(f"  ID: {item['HcpId']}")
                print(f"  Specialty: {item.get('Specialty', 'N/A')}")
                print(f"  Hospital: {item.get('Hospital', 'N/A')}")
                print(f"  Experience: {item.get('YearsExperience', 'N/A')} years")
                if 'ContactInfo' in item:
                    print(f"  Contact: {item['ContactInfo'].get('Email', 'N/A')}, {item['ContactInfo'].get('Phone', 'N/A')}")
                print()
        else:
            print(f"No HCP found with name: {full_name}")
            
    except Exception as e:
        print(f"Error querying: {str(e)}")

def query_by_specialty(specialty):
    """
    Query for HCPs by specialty using a scan with filter.
    Note: This is less efficient than using a GSI but works for attributes 
    that don't have an index.
    """
    print(f"\nFinding HCPs with specialty: {specialty}")
    
    try:
        response = table.scan(
            FilterExpression=Attr('Specialty').eq(specialty)
        )
        
        if response['Items']:
            print(f"Found {len(response['Items'])} HCPs with specialty {specialty}:")
            for item in response['Items']:
                print(f"  {item['FullName']} at {item['Hospital']}")
        else:
            print(f"No HCPs found with specialty: {specialty}")
            
    except Exception as e:
        print(f"Error scanning: {str(e)}")

def query_by_experience(min_years):
    """
    Query for HCPs with at least the specified years of experience.
    """
    print(f"\nFinding HCPs with {min_years}+ years of experience")
    
    try:
        response = table.scan(
            FilterExpression=Attr('YearsExperience').gte(min_years)
        )
        
        if response['Items']:
            # Sort results by years of experience (descending)
            sorted_items = sorted(
                response['Items'], 
                key=lambda x: x['YearsExperience'], 
                reverse=True
            )
            
            print(f"Found {len(sorted_items)} HCPs with {min_years}+ years of experience:")
            for item in sorted_items:
                print(f"  {item['FullName']}: {item['YearsExperience']} years, {item['Specialty']}")
        else:
            print(f"No HCPs found with {min_years}+ years of experience")
            
    except Exception as e:
        print(f"Error scanning: {str(e)}")

def update_hcp_information(hcp_id, update_data):
    """
    Update specific attributes for an HCP record.
    """
    print(f"\nUpdating information for HCP ID: {hcp_id}")
    
    # First, check if the item exists and what attributes it has
    try:
        response = table.get_item(Key={'HcpId': hcp_id})
        item_exists = 'Item' in response
        existing_item = response.get('Item', {})
    except Exception as e:
        print(f"Error checking item: {str(e)}")
        return
    
    if not item_exists:
        print(f"No item found with HcpId: {hcp_id}")
        return
    
    # Process updates based on existing data
    updates_to_apply = {}
    for key, value in update_data.items():
        if '.' in key:
            # For nested attributes, we need to handle parent maps
            parts = key.split('.')
            parent_map = parts[0]
            child_attr = parts[1]
            
            # If parent map doesn't exist, create it
            if parent_map not in existing_item:
                updates_to_apply[parent_map] = {child_attr: value}
            else:
                # If parent exists, just update the nested attribute
                if isinstance(existing_item[parent_map], dict):
                    updates_to_apply[f"{parent_map}.{child_attr}"] = value
                else:
                    # Parent exists but is not a map, replace it
                    updates_to_apply[parent_map] = {child_attr: value}
        else:
            # Simple top-level attribute
            updates_to_apply[key] = value
    
    # Build the update expression
    update_expression = "SET "
    expression_values = {}
    expression_names = {}
    
    for key, value in updates_to_apply.items():
        if '.' in key:
            # Handle nested attributes that already have parent maps
            parts = key.split('.')
            attr_path = '#' + parts[0]
            for i in range(1, len(parts)):
                attr_path += '.#' + parts[i]
            
            # Add each part to expression attribute names
            for i, part in enumerate(parts):
                expression_names[f'#{part}'] = part
                
            update_expression += f"{attr_path} = :val{len(expression_values)}, "
            expression_values[f":val{len(expression_values)}"] = value
        else:
            # Handle top-level attributes
            expression_names[f'#{key}'] = key
            update_expression += f"#{key} = :val{len(expression_values)}, "
            expression_values[f":val{len(expression_values)}"] = value
    
    # Remove trailing comma and space
    update_expression = update_expression[:-2]
    
    try:
        update_args = {
            'Key': {'HcpId': hcp_id},
            'UpdateExpression': update_expression,
            'ExpressionAttributeValues': expression_values,
            'ExpressionAttributeNames': expression_names,
            'ReturnValues': "UPDATED_NEW"
        }
            
        response = table.update_item(**update_args)
        print(f"Updated attributes: {response.get('Attributes', {})}")
        
    except Exception as e:
        print(f"Error updating item: {str(e)}")

def batch_write_example():
    """
    Example of using batch_writer for efficient multiple writes.
    """
    print("\nPerforming batch write operation...")
    
    # Sample data for batch write
    new_hcps = [
        {
            'HcpId': '101',
            'FullName': 'Robert Thompson',
            'Specialty': 'Orthopedics',
            'Hospital': 'Sports Medicine Center',
            'YearsExperience': 7
        },
        {
            'HcpId': '102',
            'FullName': 'Lisa Garcia',
            'Specialty': 'Endocrinology',
            'Hospital': 'Diabetes Care Clinic',
            'YearsExperience': 9
        },
        {
            'HcpId': '103',
            'FullName': 'James Wilson',
            'Specialty': 'Cardiology',
            'Hospital': 'Heart Center',
            'YearsExperience': 12
        }
    ]
    
    try:
        with table.batch_writer() as batch:
            for hcp in new_hcps:
                batch.put_item(Item=hcp)
                
        print(f"Successfully added {len(new_hcps)} HCPs in batch operation")
        
    except Exception as e:
        print(f"Error in batch write: {str(e)}")

if __name__ == "__main__":
    # Example queries
    query_by_full_name("Robert Thompson")  # Search by full name using GSI
    query_by_specialty("Cardiology")
    query_by_experience(10)
    
    # Example update - updating both a simple attribute and a nested attribute
    update_data = {
        'Hospital': 'New Medical Center',
        'ContactInfo': {'Email': 'updated@example.com', 'Phone': '555-987-6543'}  # Creating/updating the entire ContactInfo map
    }
    update_hcp_information('101', update_data)
    
    # Example batch write
    batch_write_example()