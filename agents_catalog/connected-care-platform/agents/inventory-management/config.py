"""Inventory Management Agent — Configuration"""

import os

# AWS Configuration
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
DYNAMODB_INVENTORY_TABLE = os.environ.get("DYNAMODB_INVENTORY_TABLE", "connected-care-inventory")
DYNAMODB_INVENTORY_TRANSACTIONS_TABLE = os.environ.get("DYNAMODB_INVENTORY_TRANSACTIONS_TABLE", "connected-care-inventory-transactions")
EVENTBRIDGE_BUS_NAME = os.environ.get("EVENTBRIDGE_BUS_NAME", "connected-care-events")

# Agent Configuration
AGENT_MODEL = os.environ.get("AGENT_MODEL", "us.anthropic.claude-opus-4-6-v1")
AGENT_NAME = "Inventory Management Agent"

# Item Categories
ITEM_CATEGORIES = {
    "medication": {"label": "Medication", "unit": "doses"},
    "consumable": {"label": "Consumable Supply", "unit": "units"},
    "blood_product": {"label": "Blood Product", "unit": "units"},
    "surgical_supply": {"label": "Surgical Supply", "unit": "units"},
    "ppe": {"label": "Personal Protective Equipment", "unit": "units"},
    "nutrition": {"label": "Nutrition Supply", "unit": "units"},
    "wound_care": {"label": "Wound Care Supply", "unit": "units"},
    "iv_supply": {"label": "IV Supply", "unit": "sets"},
    "respiratory_supply": {"label": "Respiratory Supply", "unit": "units"},
}

# Stockout Risk Levels
STOCKOUT_RISK_LEVELS = {
    "CRITICAL": "Stock will deplete within 4 hours at current burn rate",
    "HIGH": "Stock will deplete within 12 hours at current burn rate",
    "MODERATE": "Stock will deplete within 24 hours at current burn rate",
    "LOW": "Stock sufficient for 24+ hours",
}

# Reorder Priority
REORDER_PRIORITIES = ["routine", "urgent", "emergency", "stat"]
