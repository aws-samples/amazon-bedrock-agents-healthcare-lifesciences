"""Account Intelligence Agent — Configuration"""

import os

AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
DYNAMODB_SITES_TABLE = os.environ.get("DYNAMODB_SITES_TABLE", "connected-care-sites")
DYNAMODB_SERVICE_CONTRACTS_TABLE = os.environ.get("DYNAMODB_SERVICE_CONTRACTS_TABLE", "connected-care-service-contracts")
DYNAMODB_DEVICES_TABLE = os.environ.get("DYNAMODB_DEVICES_TABLE", "connected-care-devices")
DYNAMODB_DEVICE_TELEMETRY_TABLE = os.environ.get("DYNAMODB_DEVICE_TELEMETRY_TABLE", "connected-care-device-telemetry")
DYNAMODB_FIELD_SERVICE_VISITS_TABLE = os.environ.get("DYNAMODB_FIELD_SERVICE_VISITS_TABLE", "connected-care-field-service-visits")
DYNAMODB_INVENTORY_TABLE = os.environ.get("DYNAMODB_INVENTORY_TABLE", "connected-care-inventory")
DYNAMODB_INVENTORY_TRANSACTIONS_TABLE = os.environ.get("DYNAMODB_INVENTORY_TRANSACTIONS_TABLE", "connected-care-inventory-transactions")
EVENTBRIDGE_BUS_NAME = os.environ.get("EVENTBRIDGE_BUS_NAME", "connected-care-events")

AGENT_MODEL = os.environ.get("AGENT_MODEL", "us.anthropic.claude-opus-4-6-v1")
AGENT_NAME = "Account Intelligence Agent"
