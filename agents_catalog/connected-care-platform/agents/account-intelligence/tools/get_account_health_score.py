"""Tool: Calculate account health scores for hospital customers."""

import os
from datetime import datetime
import boto3
from strands import tool
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
sites_table = dynamodb.Table(os.environ.get("DYNAMODB_SITES_TABLE", "connected-care-sites"))
contracts_table = dynamodb.Table(os.environ.get("DYNAMODB_SERVICE_CONTRACTS_TABLE", "connected-care-service-contracts"))
devices_table = dynamodb.Table(os.environ.get("DYNAMODB_DEVICES_TABLE", "connected-care-devices"))
telemetry_table = dynamodb.Table(os.environ.get("DYNAMODB_DEVICE_TELEMETRY_TABLE", "connected-care-device-telemetry"))
visits_table = dynamodb.Table(os.environ.get("DYNAMODB_FIELD_SERVICE_VISITS_TABLE", "connected-care-field-service-visits"))


@tool
def get_account_health_score(site_id: str = "") -> dict:
    """Calculate composite health scores for hospital customer accounts.

    Factors: device utilization, service trend, consumable attach rate, contract status.

    Args:
        site_id: Optional site filter. If empty, scores all accounts.

    Returns:
        Health scores per account with factor breakdown and risk level.
    """
    sites_resp = sites_table.scan()
    all_sites = sites_resp.get("Items", [])
    if site_id:
        all_sites = [s for s in all_sites if s.get("site_id") == site_id]

    contracts_resp = contracts_table.scan()
    contracts = {c["site_id"]: c for c in contracts_resp.get("Items", [])}

    devices_resp = devices_table.scan()
    all_devices = devices_resp.get("Items", [])
    for d in all_devices:
        if "site_id" not in d:
            d["site_id"] = "site-001"

    visits_resp = visits_table.scan()
    all_visits = visits_resp.get("Items", [])

    results = []
    chart_data = []

    for site in all_sites:
        sid = site["site_id"]
        contract = contracts.get(sid, {})
        site_devices = [d for d in all_devices if d.get("site_id") == sid]
        site_visits = [v for v in all_visits if v.get("site_id") == sid]

        # Device utilization score (0-100)
        total = len(site_devices)
        if total > 0:
            active = len([d for d in site_devices if d.get("status") == "active"])
            critical = len([d for d in site_devices if d.get("risk_profile") == "critical"])
            utilization_score = max(0, min(100, int((active / total) * 100 - critical * 15)))
        else:
            utilization_score = 0

        # Service trend score (0-100)
        corrective = len([v for v in site_visits if v.get("visit_type") == "corrective"])
        partial = len([v for v in site_visits if v.get("outcome") == "partial"])
        service_score = max(0, min(100, 100 - corrective * 20 - partial * 15))

        # Contract status score (0-100)
        if contract.get("status") == "expired":
            contract_score = 10
        elif contract.get("renewal_date"):
            try:
                renewal = datetime.strptime(contract["renewal_date"], "%Y-%m-%d")
                days_to_renewal = (renewal - datetime.now()).days
                if days_to_renewal < 30:
                    contract_score = 20
                elif days_to_renewal < 90:
                    contract_score = 50
                elif days_to_renewal < 180:
                    contract_score = 75
                else:
                    contract_score = 95
            except (ValueError, TypeError):
                contract_score = 50
        else:
            contract_score = 50

        # Firmware compliance score (0-100)
        if total > 0:
            current_fw = len([d for d in site_devices if d.get("firmware_version") == d.get("latest_firmware")])
            firmware_score = int((current_fw / total) * 100)
        else:
            firmware_score = 0

        # Composite score
        health_score = int(utilization_score * 0.3 + service_score * 0.25 + contract_score * 0.25 + firmware_score * 0.2)

        if health_score >= 75:
            risk_level = "HEALTHY"
        elif health_score >= 50:
            risk_level = "MODERATE"
        elif health_score >= 30:
            risk_level = "AT RISK"
        else:
            risk_level = "CRITICAL"

        account = {
            "site_id": sid,
            "site_name": site.get("site_name"),
            "city": site.get("city"),
            "state": site.get("state"),
            "tier": site.get("tier"),
            "health_score": health_score,
            "risk_level": risk_level,
            "device_count": total,
            "contract_type": contract.get("contract_type", "None"),
            "contract_value": int(float(contract.get("annual_value", 0))),
            "renewal_date": contract.get("renewal_date", "N/A"),
            "contract_status": contract.get("status", "none"),
            "factors": {
                "device_utilization": {"score": utilization_score, "detail": f"{total} devices, {len([d for d in site_devices if d.get('risk_profile') == 'critical'])} critical"},
                "service_trend": {"score": service_score, "detail": f"{len(site_visits)} visits, {corrective} corrective"},
                "contract_status": {"score": contract_score, "detail": contract.get("status", "none")},
                "firmware_compliance": {"score": firmware_score, "detail": f"{len([d for d in site_devices if d.get('firmware_version') == d.get('latest_firmware')])}/{total} current"},
            },
        }
        results.append(account)
        chart_data.append({
            "site_name": site.get("site_name"),
            "health_score": health_score,
            "risk_level": risk_level,
            "contract_value": int(float(contract.get("annual_value", 0))),
            "device_count": total,
            "renewal_date": contract.get("renewal_date", "N/A"),
        })

    results.sort(key=lambda x: x["health_score"])

    return {
        "total_accounts": len(results),
        "at_risk_count": len([r for r in results if r["risk_level"] in ("AT RISK", "CRITICAL")]),
        "accounts": results,
        "chart_type": "account_health",
        "chart_data": chart_data,
    }
