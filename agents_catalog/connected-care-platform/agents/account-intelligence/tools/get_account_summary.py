"""Tool: Get comprehensive account summary for a hospital site."""

import os
import boto3
from strands import tool

dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
sites_table = dynamodb.Table(os.environ.get("DYNAMODB_SITES_TABLE", "connected-care-sites"))
contracts_table = dynamodb.Table(os.environ.get("DYNAMODB_SERVICE_CONTRACTS_TABLE", "connected-care-service-contracts"))
devices_table = dynamodb.Table(os.environ.get("DYNAMODB_DEVICES_TABLE", "connected-care-devices"))
visits_table = dynamodb.Table(os.environ.get("DYNAMODB_FIELD_SERVICE_VISITS_TABLE", "connected-care-field-service-visits"))


@tool
def get_account_summary(site_id: str) -> dict:
    """Get a comprehensive account summary for a specific hospital site.

    Includes site info, installed devices, contract status, and service history.

    Args:
        site_id: Hospital site ID (e.g., site-001, site-002, site-003)

    Returns:
        Complete account profile for meeting preparation.
    """
    site_resp = sites_table.get_item(Key={"site_id": site_id})
    site = site_resp.get("Item")
    if not site:
        return {"error": f"Site {site_id} not found"}

    contracts_resp = contracts_table.scan()
    contract = next((c for c in contracts_resp.get("Items", []) if c.get("site_id") == site_id), {})

    devices_resp = devices_table.scan()
    all_devices = devices_resp.get("Items", [])
    for d in all_devices:
        if "site_id" not in d:
            d["site_id"] = "site-001"
    site_devices = [d for d in all_devices if d.get("site_id") == site_id]

    visits_resp = visits_table.scan()
    site_visits = sorted(
        [v for v in visits_resp.get("Items", []) if v.get("site_id") == site_id],
        key=lambda v: v.get("visit_date", ""), reverse=True,
    )

    by_risk = {"critical": 0, "moderate": 0, "healthy": 0}
    by_type = {}
    for d in site_devices:
        risk = d.get("risk_profile", "unknown")
        if risk in by_risk:
            by_risk[risk] += 1
        dtype = d.get("device_type", "unknown")
        by_type[dtype] = by_type.get(dtype, 0) + 1

    return {
        "site_id": site_id,
        "site_name": site.get("site_name"),
        "city": site.get("city"),
        "state": site.get("state"),
        "bed_count": int(float(site.get("bed_count", 0))),
        "tier": site.get("tier"),
        "account_manager": site.get("account_manager"),
        "go_live_date": site.get("go_live_date"),
        "contract": {
            "type": contract.get("contract_type", "None"),
            "annual_value": int(float(contract.get("annual_value", 0))),
            "renewal_date": contract.get("renewal_date", "N/A"),
            "status": contract.get("status", "none"),
            "sla_hours": int(float(contract.get("sla_response_hours", 0))),
            "includes_parts": contract.get("includes_parts", False),
            "includes_firmware": contract.get("includes_firmware", False),
        },
        "devices": {
            "total": len(site_devices),
            "by_risk": by_risk,
            "by_type": by_type,
        },
        "service_history": {
            "total_visits": len(site_visits),
            "recent_visits": [
                {
                    "visit_id": v.get("visit_id"),
                    "date": v.get("visit_date"),
                    "type": v.get("visit_type"),
                    "devices": v.get("devices_serviced", []),
                    "outcome": v.get("outcome"),
                }
                for v in site_visits[:5]
            ],
        },
    }
