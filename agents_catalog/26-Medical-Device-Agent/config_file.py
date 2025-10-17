"""
Configuration file for Medical Device Agent
"""
import os

# Authentication Configuration
ENABLE_AUTHENTICATION = os.getenv('ENABLE_AUTHENTICATION', 'true').lower() == 'true'

# Basic Auth Configuration
AUTH_TYPE = os.getenv('AUTH_TYPE', 'basic')
BASIC_AUTH_USERNAME = os.getenv('BASIC_AUTH_USERNAME')
BASIC_AUTH_PASSWORD = os.getenv('BASIC_AUTH_PASSWORD')
AWS_DEFAULT_REGION = "us-east-1"

# Application Configuration
APP_NAME = "Medical Device Management System"
SESSION_TIMEOUT_MINUTES = 30