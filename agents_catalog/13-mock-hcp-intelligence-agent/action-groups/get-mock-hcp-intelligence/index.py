# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import boto3
from datetime import datetime
import decimal
import json
import logging
import os
from typing import Dict

log_level = os.environ.get("LOG_LEVEL", "INFO").strip().upper()
logging.basicConfig(
    format="[%(asctime)s] p%(process)s {%(filename)s:%(lineno)d} %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)
logger.setLevel(log_level)

session = boto3.session.Session()
dynamodb = session.resource("dynamodb")
table_name = os.environ["TABLE_NAME"]
table = dynamodb.Table(table_name)


def query_by_full_name(full_name):
    """
    Find items by FullName using a query operation on the FullName GSI
    This is much more efficient than a full table scan
    """
    logger.debug(f"\n=== Finding by FullName: {full_name} ===")

    response = table.query(
        IndexName="FullName",
        KeyConditionExpression="FullName = :name",
        ExpressionAttributeValues={":name": full_name},
    )

    if response["Items"]:
        logger.debug(f"Found {len(response['Items'])} HCP(s):")
        return response["Items"]
    else:
        logger.info(f"No HCP found with name: {full_name}")
        return []


def epoch_to_human_readable(epoch_time):
    # Convert Decimal to float for datetime processing
    if isinstance(epoch_time, decimal.Decimal):
        epoch_time = float(epoch_time)

    # If epoch time is in milliseconds, divide by 1000
    if len(str(int(epoch_time))) > 10:
        epoch_time = epoch_time / 1000

    dt = datetime.fromtimestamp(epoch_time)
    # Format as desired
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def get_mock_content_preferences(full_name: str) -> Dict:
    """
    Get mock content preferences for a given full name
    """

    logger.info(f"get_mock_content_preferences: {full_name=}")

    query_results = query_by_full_name(full_name)

    if query_results:
        filtered_results = {
            "channel_preference": query_results[0].get("ChannelPreference", {}),
            "content_preference": query_results[0].get("ContentPreference", {}),
            "topics_of_interested": ", ".join(
                query_results[0].get("TopicsOfInterest", {})
            ),
        }
        return filtered_results

    else:
        return query_results


def get_mock_engagement_data(full_name: str) -> Dict:
    """
    Get mock engagement data preferences for a given full name
    """

    logger.info(f"get_mock_engagement_data: {full_name=}")

    query_results = query_by_full_name(full_name)

    if query_results:
        field_interaction_notes = query_results[0].get("FieldInteractionNotes", {})
        if field_interaction_notes:
            processed_field_interaction_notes = [
                f"({epoch_to_human_readable(note['Timestamp'])}) {note['Note']}"
                for note in field_interaction_notes
            ]
        medical_information_requests = query_results[0].get(
            "MedicalInformationRequests", {}
        )
        if medical_information_requests:
            processed_medical_information_requests = [
                f"({epoch_to_human_readable(request['Timestamp'])}) {request['Request']}"
                for request in medical_information_requests
            ]
        filtered_results = {
            "field_interaction_notes": processed_field_interaction_notes,
            "medical_information_requests": processed_medical_information_requests,
            "website_opt_in": str(query_results[0].get("WebSiteOptIn", {})),
        }
        return filtered_results

    else:
        return query_results


def get_mock_public_profile(full_name: str) -> Dict:
    """
    Get mock public publications and social posts for a given full name
    """

    logger.info(f"get_mock_public_profile: {full_name=}")

    query_results = query_by_full_name(full_name)

    if query_results:
        publications = query_results[0].get("Publications", {})
        if publications:
            processed_publications = [
                {
                    "Title": pub.get("Title", ""),
                    "Authors": ", ".join(pub.get("Authors", [])),
                    "Journal": pub.get("Journal", ""),
                    "Url": pub.get("Url", ""),
                    "PublicationDate": epoch_to_human_readable(
                        pub.get("PublicationDate", "")
                    ),
                }
                for pub in publications
            ]
        social_posts = query_results[0].get("SocialPosts", {})
        if social_posts:
            processed_social_posts = [
                {
                    "Platform": post.get("Platform", ""),
                    "Content": post.get("Content", ""),
                    "Timestamp": epoch_to_human_readable(post.get("Timestamp", "")),
                }
                for post in social_posts
            ]

        filtered_results = {
            "publications": processed_publications,
            "social_posts": processed_social_posts,
        }
        return filtered_results

    else:
        return query_results


def lambda_handler(event, context):
    logging.debug(f"{event=}")

    agent = event["agent"]
    actionGroup = event["actionGroup"]
    function = event["function"]
    parameters = event.get("parameters", [])
    responseBody = {"TEXT": {"body": "Error, no function was called"}}

    logger.info(f"{agent=}\n{actionGroup=}\n{function=}")

    for param in parameters:
        if param["name"] == "full_name":
            full_name = param["value"]

    if not full_name:
        responseBody = {"TEXT": {"body": "Missing mandatory parameter: full_name"}}
    else:
        if function == "get_mock_content_preferences":
            results = get_mock_content_preferences(full_name)
        elif function == "get_mock_engagement_data":
            results = get_mock_engagement_data(full_name)
        elif function == "get_mock_public_profile":
            results = get_mock_public_profile(full_name)
        else:
            responseBody = {"TEXT": {"body": f"Error, unknown function: {function}"}}

        results = json.dumps(results, separators=(",", ":"))

        responseBody = {
            "TEXT": {
                "body": f"Here are the results from the {function} function:\n{results} "
            }
        }

    action_response = {
        "actionGroup": actionGroup,
        "function": function,
        "functionResponse": {"responseBody": responseBody},
    }

    function_response = {
        "response": action_response,
        "messageVersion": event["messageVersion"],
    }

    logger.debug(f"lambda_handler: {function_response=}")

    return function_response


if __name__ == "__main__":
    event = {
        "messageVersion": "1.0",
        "agent": {
            "name": "test",
            "id": "ABCDEF",
            "alias": "123456",
            "version": "1",
        },
        "sessionId": "123456789",
        "actionGroup": "GetMockHCPIntelligence",
        "function": "get_mock_content_preferences",
        "parameters": [
            {
                "name": "full_name",
                "value": "Alejandro Rosalez",
            }
        ],
    }
    response = lambda_handler(event, None)
    logger.info(response)

    event = {
        "messageVersion": "1.0",
        "agent": {
            "name": "test",
            "id": "ABCDEF",
            "alias": "123456",
            "version": "1",
        },
        "sessionId": "123456789",
        "actionGroup": "GetMockHCPIntelligence",
        "function": "get_mock_engagement_data",
        "parameters": [
            {
                "name": "full_name",
                "value": "Alejandro Rosalez",
            }
        ],
    }
    response = lambda_handler(event, None)
    logger.info(response)

    event = {
        "messageVersion": "1.0",
        "agent": {
            "name": "test",
            "id": "ABCDEF",
            "alias": "123456",
            "version": "1",
        },
        "sessionId": "123456789",
        "actionGroup": "GetMockHCPIntelligence",
        "function": "get_mock_public_profile",
        "parameters": [
            {
                "name": "full_name",
                "value": "Alejandro Rosalez",
            }
        ],
    }
    response = lambda_handler(event, None)
    logger.info(response)
