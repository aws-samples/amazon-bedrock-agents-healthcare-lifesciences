"""Account Intelligence Agent — no separate seed needed.

This agent reads from tables seeded by the Field Service agent (sites, contracts, visits)
and the existing Device Management agent (devices, telemetry).
"""

import json


def handler(event, context):
    return {
        "statusCode": 200,
        "body": json.dumps({"message": "Account Intelligence uses shared tables — no separate seed required."}),
    }
