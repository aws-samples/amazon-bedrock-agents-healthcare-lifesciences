"""Tool: Assess contract renewal risk for hospital accounts."""

import os
from datetime import datetime
import boto3
from strands import tool

dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
sites_table = dynamodb.Table(os.environ.get("DYNAMODB_SITES_TABLE", "connected-care-sites"))
contracts_table = dynamodb.Table(os.environ.get("DYNAMODB_SERVICE_CONTRACTS_TABLE", "connected-care-service-contracts"))
visits_table = dynamodb.Table(os.environ.get("DYNAMODB_FIELD_SERVICE_VISITS_TABLE", "connected-care-field-service-visits"))


@tool
def get_contract_renewal_risk() -> dict:
    """Assess contract renewal risk for all hospital accounts.

    Evaluates contract expiry, service history, and account signals.

    Returns:
        Prioritized list of accounts by renewal risk with recommended actions.
    """
    sites_resp = sites_table.scan()
    sites = {s["site_id"]: s for s in sites_resp.get("Items", [])}

    contracts_resp = contracts_table.scan()
    contracts = contracts_resp.get("Items", [])

    visits_resp = visits_table.scan()
    all_visits = visits_resp.get("Items", [])

    results = []
    for contract in contracts:
        sid = contract.get("site_id")
        site = sites.get(sid, {})
        site_visits = [v for v in all_visits if v.get("site_id") == sid]

        if contract.get("status") == "expired":
            risk = "CRITICAL"
            days_to_renewal = -999
            action = "Immediate outreach required. Re-engage with contract proposal."
        elif contract.get("renewal_date"):
            try:
                renewal = datetime.strptime(contract["renewal_date"], "%Y-%m-%d")
                days_to_renewal = (renewal - datetime.now()).days
            except (ValueError, TypeError):
                days_to_renewal = 999

            corrective = len([v for v in site_visits if v.get("visit_type") == "corrective"])
            partial = len([v for v in site_visits if v.get("outcome") == "partial"])

            if days_to_renewal < 30:
                risk = "CRITICAL"
                action = "Schedule executive review immediately."
            elif days_to_renewal < 90 and (corrective > 0 or partial > 0):
                risk = "HIGH"
                action = "Schedule account review. Address open service issues before renewal."
            elif days_to_renewal < 90:
                risk = "MODERATE"
                action = "Begin renewal conversation. Prepare value summary."
            else:
                risk = "LOW"
                action = "Monitor. No immediate action needed."
        else:
            risk = "UNKNOWN"
            days_to_renewal = 0
            action = "Verify contract status."

        risk_factors = []
        if contract.get("status") == "expired":
            risk_factors.append("Contract expired")
        if contract.get("notes"):
            risk_factors.append(contract["notes"])
        if len([v for v in site_visits if v.get("outcome") == "partial"]) > 0:
            risk_factors.append("Incomplete service visits on record")

        results.append({
            "site_id": sid,
            "site_name": site.get("site_name", "Unknown"),
            "city": site.get("city", ""),
            "tier": site.get("tier", ""),
            "contract_type": contract.get("contract_type"),
            "annual_value": int(float(contract.get("annual_value", 0))),
            "renewal_date": contract.get("renewal_date", "N/A"),
            "days_to_renewal": days_to_renewal,
            "contract_status": contract.get("status"),
            "risk_level": risk,
            "risk_factors": risk_factors,
            "recommended_action": action,
        })

    risk_order = {"CRITICAL": 0, "HIGH": 1, "MODERATE": 2, "LOW": 3, "UNKNOWN": 4}
    results.sort(key=lambda x: risk_order.get(x["risk_level"], 5))

    return {
        "total_contracts": len(results),
        "at_risk": len([r for r in results if r["risk_level"] in ("CRITICAL", "HIGH")]),
        "total_annual_revenue": sum(r["annual_value"] for r in results),
        "at_risk_revenue": sum(r["annual_value"] for r in results if r["risk_level"] in ("CRITICAL", "HIGH")),
        "contracts": results,
    }
