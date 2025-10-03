#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Mar  2 19:44:16 2023

@author: sandanar
"""

import json
import boto3
from datetime import datetime

dt_fmt = '%Y%m%dT%H%M%S'
ts = datetime.now().strftime(dt_fmt)

iam = boto3.client('iam')
role = iam.create_role(
    RoleName=f"OmicsUnifiedServiceRole-{ts}",
    AssumeRolePolicyDocument=json.dumps({
        "Version": "2012-10-17",
        "Statement": [{
            "Principal": {
                "Service": "omics.amazonaws.com"
            },
            "Effect": "Allow",
            "Action": "sts:AssumeRole"
        }]
    }),
    Description="Omics service role",
)

AWS_ACCOUNT_ID = boto3.client('sts').get_caller_identity()['Account']

policy_s3 = iam.create_policy(
    PolicyName=f"omics-s3-access-{ts}",
    PolicyDocument=json.dumps({
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "s3:PutObject",
                    "s3:Get*",
                    "s3:List*",
                ],
                "Resource": [
                    "arn:aws:s3:::*/*",
                    "arn:aws:s3:::*"
                ]
            }
        ]
    })
)

policy_logs = iam.create_policy(
    PolicyName=f"omics-logs-access-{ts}",
    PolicyDocument=json.dumps({
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "logs:CreateLogGroup"
                ],
                "Resource": [
                    f"arn:aws:logs:*:{AWS_ACCOUNT_ID}:log-group:/aws/omics/WorkflowLog:*"
                ]
            },
            {
                "Effect": "Allow",
                "Action": [
                    "logs:DescribeLogStreams",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents",
                ],
                "Resource": [
                    f"arn:aws:logs:*:{AWS_ACCOUNT_ID}:log-group:/aws/omics/WorkflowLog:log-stream:*"
                ]
            }
        ]
    })
)

policy_ecr = iam.create_policy(
    PolicyName=f"omics-ecr-access-{ts}",
    PolicyDocument=json.dumps({
        "Version": "2012-10-17",
        "Statement": [
            {
            "Effect": "Allow",
            "Action": [
                "ecr:BatchGetImage",
                "ecr:BatchCheckLayerAvailability",
                "ecr:CompleteLayerUpload",
                "ecr:GetDownloadUrlForLayer",
                "ecr:InitiateLayerUpload",
                "ecr:PutImage",
                "ecr:UploadLayerPart"
            ],
            "Resource": [
                    "arn:aws:ecr:ap-southeast-1:735766051544:repository/*"
                ]                
            }
        ]
    })
)
for policy in (policy_s3, policy_logs,policy_ecr):
    _ = iam.attach_role_policy(
        RoleName=role['Role']['RoleName'],
        PolicyArn=policy['Policy']['Arn']
    )