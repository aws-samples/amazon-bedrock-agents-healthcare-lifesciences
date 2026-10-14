"""
AgentCore Proxy — IAM-authenticated Lambda Function URL with async execution and trace polling.

Auth: Cognito User Pool → Identity Pool → temporary IAM credentials → SigV4-signed requests.
The Function URL has authType=AWS_IAM, so AWS rejects unsigned requests before they reach this code.

POST {"agent": "...", "prompt": "..."} → Returns {"request_id": "..."} immediately
GET ?request_id=... → Returns trace events and final response when ready
"""

import json
import os
import uuid
import time
import threading
import boto3

from botocore.config import Config as BotoConfig

agentcore_client = boto3.client("bedrock-agentcore",
    region_name=os.environ.get("AWS_REGION_OVERRIDE", os.environ.get("AWS_REGION", "us-east-1")),
    config=BotoConfig(read_timeout=400, connect_timeout=10, retries={'max_attempts': 0}))
dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION_OVERRIDE", os.environ.get("AWS_REGION", "us-east-1")))
traces_table = dynamodb.Table(os.environ.get("TRACES_TABLE", "connected-care-agent-traces"))

RUNTIME_ARNS = {
    "patient-monitoring": os.environ.get("PM_RUNTIME_ARN", ""),
    "device-management": os.environ.get("DM_RUNTIME_ARN", ""),
    "patient-engagement": os.environ.get("PE_RUNTIME_ARN", ""),
    "inventory-management": os.environ.get("IM_RUNTIME_ARN", ""),
    "field-service": os.environ.get("FS_RUNTIME_ARN", ""),
    "account-intelligence": os.environ.get("AI_RUNTIME_ARN", ""),
    "orchestrator": os.environ.get("ORCH_RUNTIME_ARN", ""),
}

CORS_HEADERS = {
    "Content-Type": "application/json",
}


def invoke_agent(agent_id, prompt, session_id, request_id, actor_email=""):
    """Invoke an AgentCore runtime and write trace events to DynamoDB."""
    runtime_arn = RUNTIME_ARNS.get(agent_id, "")
    if not runtime_arn:
        return {"error": f"Runtime not configured for {agent_id}"}

    start = time.time()

    # Write "in_progress" trace
    traces_table.put_item(Item={
        "request_id": request_id,
        "sort_key": f"trace#{int(start * 1000)}",
        "type": "trace",
        "agent": agent_id,
        "status": "in_progress",
        "timestamp": int(start * 1000),
    })

    try:
        # Use a unique runtimeSessionId per invocation to avoid corrupted state.
        # AgentCore Memory handles conversation continuity — we don't need
        # the runtime's built-in session replay (which breaks on tool failures).
        invocation_session_id = f"{session_id}-{uuid.uuid4().hex[:8]}"

        response = agentcore_client.invoke_agent_runtime(
            agentRuntimeArn=runtime_arn,
            runtimeSessionId=invocation_session_id,
            payload=json.dumps({
                "prompt": prompt,
                "request_id": request_id,
                "session_id": session_id,
                "actor_id": "system",
                "actor_email": actor_email,
            }).encode(),
            qualifier="DEFAULT",
        )

        duration_ms = int((time.time() - start) * 1000)
        response_body = response["response"].read().decode()
        response_data = json.loads(response_body)

        # Extract text
        agent_response = ""
        if "response" in response_data:
            resp = response_data["response"]
            if isinstance(resp, str):
                agent_response = resp
            elif isinstance(resp, dict):
                content = resp.get("content", [])
                if content and isinstance(content, list):
                    agent_response = content[0].get("text", str(resp))

        # Write "completed" trace
        traces_table.put_item(Item={
            "request_id": request_id,
            "sort_key": f"trace#{int(time.time() * 1000)}",
            "type": "trace",
            "agent": agent_id,
            "status": "completed",
            "duration_ms": duration_ms,
            "response_preview": agent_response[:300],
            "timestamp": int(time.time() * 1000),
        })

        # Extract memory context if present
        memory_ctx = response_data.get("memory", None)

        return {"response": agent_response, "duration_ms": duration_ms, "memory": memory_ctx}

    except Exception as e:
        duration_ms = int((time.time() - start) * 1000)
        traces_table.put_item(Item={
            "request_id": request_id,
            "sort_key": f"trace#{int(time.time() * 1000)}",
            "type": "trace",
            "agent": agent_id,
            "status": "failed",
            "duration_ms": duration_ms,
            "error": str(e),
            "timestamp": int(time.time() * 1000),
        })
        return {"error": str(e), "duration_ms": duration_ms}


def process_request(agent_id, prompt, session_id, request_id, actor_email=""):
    """Process the agent request and write the final result to DynamoDB."""
    result = invoke_agent(agent_id, prompt, session_id, request_id, actor_email)

    # Write final response
    traces_table.put_item(Item={
        "request_id": request_id,
        "sort_key": "result",
        "type": "result",
        "agent": agent_id,
        "response": result.get("response", result.get("error", "No response")),
        "duration_ms": result.get("duration_ms", 0),
        "status": "error" if "error" in result else "completed",
        "timestamp": int(time.time() * 1000),
    })


bedrock_runtime = boto3.client("bedrock-runtime",
    region_name=os.environ.get("AWS_REGION_OVERRIDE", os.environ.get("AWS_REGION", "us-east-1")))


def summarize_for_voice(text):
    """Use Haiku to compress any agent response into 3-4 warm, professional spoken sentences."""
    try:
        prompt = (
            "You are a calm, supportive clinical assistant speaking to a doctor or nurse. "
            "Summarize this clinical data in 3 to 4 short sentences.\n\n"
            "STRICT RULES:\n"
            "- Warm, professional tone — like a trusted colleague giving a brief update\n"
            "- Plain spoken English — NO markdown, NO tables, NO pipes, NO asterisks, NO headers, NO lists\n"
            "- NO numbers unless they indicate an immediately life-threatening value\n"
            "- Use phrases like 'I noticed', 'You may want to check', 'It looks like'\n"
            "- Last sentence: a gentle follow-up question starting with 'Would you like me to' or 'Should I'\n"
            "- Output ONLY the sentences, nothing else\n\n"
            f"{text[:2000]}"
        )

        response = bedrock_runtime.converse(
            modelId="us.anthropic.claude-haiku-4-20250514-v1:0",
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            inferenceConfig={"maxTokens": 120, "temperature": 0.3},
        )

        summary = response["output"]["message"]["content"][0]["text"].strip()
        if summary and len(summary) > 20:
            return summary
    except Exception as e:
        print(f"Voice summarization failed: {e}")

    return None


def handler(event, context):
    # Auth is handled by IAM at the Function URL level — if we're here, the request is authenticated.
    # The caller's identity is in event.requestContext.authorizer.iam (if needed for audit logging).

    method = event.get("requestContext", {}).get("http", {}).get("method", "POST")

    # Health check
    if method == "GET":
        qs = event.get("queryStringParameters") or {}
        request_id = qs.get("request_id")
        patient_memory_id = qs.get("patient_memory")

        # Patient memory timeline endpoint
        if patient_memory_id:
            actor_email = qs.get("actor_email", "")
            # Check care team access — always enforce, deny if no email or not in team
            try:
                care_team_tbl = dynamodb.Table("connected-care-care-team")
                if not actor_email:
                    return {
                        "statusCode": 200,
                        "headers": CORS_HEADERS,
                        "body": json.dumps({
                            "patient_id": patient_memory_id,
                            "total_entries": 0,
                            "entries": [],
                            "phi_access_denied": True,
                        }),
                    }
                ct_resp = care_team_tbl.get_item(Key={"patient_id": patient_memory_id})
                ct_item = ct_resp.get("Item")
                if not ct_item or actor_email not in ct_item.get("team_members", []):
                    return {
                        "statusCode": 200,
                        "headers": CORS_HEADERS,
                        "body": json.dumps({
                            "patient_id": patient_memory_id,
                            "total_entries": 0,
                            "entries": [],
                            "phi_access_denied": True,
                        }),
                    }
            except Exception:
                return {
                    "statusCode": 200,
                    "headers": CORS_HEADERS,
                    "body": json.dumps({
                        "patient_id": patient_memory_id,
                        "total_entries": 0,
                        "entries": [],
                        "phi_access_denied": True,
                    }),
                }

            try:
                memory_tbl = dynamodb.Table("connected-care-patient-memory")
                mem_resp = memory_tbl.query(
                    KeyConditionExpression=boto3.dynamodb.conditions.Key("patient_id").eq(patient_memory_id),
                    ScanIndexForward=True,
                )
                entries = mem_resp.get("Items", [])
                timeline = [{
                    "timestamp": e.get("timestamp"),
                    "entry_type": e.get("entry_type"),
                    "category": e.get("category"),
                    "summary": e.get("summary"),
                    "recorded_by": e.get("recorded_by"),
                } for e in entries]
                return {
                    "statusCode": 200,
                    "headers": CORS_HEADERS,
                    "body": json.dumps({
                        "patient_id": patient_memory_id,
                        "total_entries": len(timeline),
                        "entries": timeline,
                    }),
                }
            except Exception as e:
                return {"statusCode": 200, "headers": CORS_HEADERS, "body": json.dumps({"patient_id": patient_memory_id, "entries": [], "error": str(e)})}

        # Device Digital Twin endpoint
        device_twin_id = qs.get("device_twin")
        if device_twin_id:
            try:
                devices_tbl = dynamodb.Table("connected-care-devices")
                telemetry_tbl = dynamodb.Table("connected-care-device-telemetry")
                visits_tbl = dynamodb.Table("connected-care-field-service-visits")
                sites_tbl = dynamodb.Table("connected-care-sites")

                # Device profile
                dev_resp = devices_tbl.get_item(Key={"device_id": device_twin_id})
                device = dev_resp.get("Item", {})
                if not device:
                    return {"statusCode": 200, "headers": CORS_HEADERS, "body": json.dumps({"error": f"Device {device_twin_id} not found"})}

                # Convert Decimal to float for JSON
                import decimal
                def dec_default(obj):
                    if isinstance(obj, decimal.Decimal):
                        return float(obj)
                    raise TypeError

                # Latest telemetry
                tel_resp = telemetry_tbl.query(
                    KeyConditionExpression=boto3.dynamodb.conditions.Key("device_id").eq(device_twin_id),
                    ScanIndexForward=False, Limit=1,
                )
                telemetry = tel_resp["Items"][0].get("telemetry", {}) if tel_resp.get("Items") else {}

                # Telemetry history (last 20 readings for sparklines)
                tel_hist_resp = telemetry_tbl.query(
                    KeyConditionExpression=boto3.dynamodb.conditions.Key("device_id").eq(device_twin_id),
                    ScanIndexForward=False, Limit=20,
                )
                telemetry_history = []
                for t in reversed(tel_hist_resp.get("Items", [])):
                    tel = t.get("telemetry", {})
                    telemetry_history.append({
                        "timestamp": t.get("timestamp"),
                        "battery_level": float(tel.get("battery_level", 0)),
                        "error_count": int(tel.get("error_count", 0)),
                        "sensor_accuracy": float(tel.get("sensor_accuracy", 0)),
                        "calibration_drift": float(tel.get("calibration_drift", 0)),
                    })

                # Service history
                visits_resp = visits_tbl.scan()
                service_history = sorted(
                    [v for v in visits_resp.get("Items", []) if device_twin_id in v.get("devices_serviced", [])],
                    key=lambda v: v.get("visit_date", ""), reverse=True,
                )
                service_visits = [{
                    "visit_id": v.get("visit_id"),
                    "date": v.get("visit_date"),
                    "type": v.get("visit_type"),
                    "engineer": v.get("engineer"),
                    "parts_used": v.get("parts_used", []),
                    "outcome": v.get("outcome"),
                    "notes": v.get("notes"),
                    "duration_hours": int(float(v.get("duration_hours", 0))),
                } for v in service_history[:10]]

                # Site info
                site_id = device.get("site_id", "site-001")
                site_resp = sites_tbl.get_item(Key={"site_id": site_id})
                site = site_resp.get("Item", {})

                # Patient assignment history
                assignments_tbl = dynamodb.Table("connected-care-device-assignments")
                try:
                    assign_resp = assignments_tbl.get_item(Key={"device_id": device_twin_id})
                    assignment = assign_resp.get("Item", {})
                    patient_assignment = {
                        "patient_id": assignment.get("patient_id"),
                        "assigned_date": assignment.get("assigned_date"),
                    } if assignment.get("patient_id") else None
                except Exception:
                    patient_assignment = None

                # Also check device seed data for assigned_patient_id
                if not patient_assignment and device.get("assigned_patient_id"):
                    patient_assignment = {
                        "patient_id": device.get("assigned_patient_id"),
                        "assigned_date": device.get("installation_date"),
                    }

                # Peer devices (same model across all sites)
                all_devices_resp = devices_tbl.scan()
                all_devs = all_devices_resp.get("Items", [])
                model = device.get("model")
                peers = []
                for d in all_devs:
                    if d.get("model") == model and d.get("device_id") != device_twin_id:
                        d_site_id = d.get("site_id", "site-001")
                        d_site = sites_tbl.get_item(Key={"site_id": d_site_id}).get("Item", {}) if d_site_id != site_id else site
                        # Get peer telemetry
                        p_tel_resp = telemetry_tbl.query(
                            KeyConditionExpression=boto3.dynamodb.conditions.Key("device_id").eq(d["device_id"]),
                            ScanIndexForward=False, Limit=1,
                        )
                        p_tel = p_tel_resp["Items"][0].get("telemetry", {}) if p_tel_resp.get("Items") else {}
                        peers.append({
                            "device_id": d.get("device_id"),
                            "site_name": d_site.get("site_name", "Unknown"),
                            "location": d.get("location"),
                            "firmware_version": d.get("firmware_version"),
                            "risk_profile": d.get("risk_profile"),
                            "error_count": int(p_tel.get("error_count", 0)),
                            "sensor_accuracy": float(p_tel.get("sensor_accuracy", 0)),
                            "calibration_drift": float(p_tel.get("calibration_drift", 0)),
                            "battery_level": float(p_tel.get("battery_level", 0)),
                        })

                # Predictive failure estimate
                battery = float(telemetry.get("battery_level", 100))
                errors = int(telemetry.get("error_count", 0))
                drift = float(telemetry.get("calibration_drift", 0))
                accuracy = float(telemetry.get("sensor_accuracy", 100))

                # Simple heuristic: estimate days until service needed
                issues = []
                days_estimate = 999
                if battery < 20:
                    est = max(1, int(battery / 2))
                    issues.append(f"Battery at {battery}% — estimated {est} days")
                    days_estimate = min(days_estimate, est)
                if errors > 50:
                    est = max(1, int((100 - errors) / 5))
                    issues.append(f"Error count {errors} — estimated {est} days")
                    days_estimate = min(days_estimate, est)
                if drift > 3.0:
                    est = max(1, int((10 - drift) / 0.5))
                    issues.append(f"Calibration drift {drift}% — estimated {est} days")
                    days_estimate = min(days_estimate, est)
                if accuracy < 90:
                    est = max(1, int((accuracy - 80) / 2))
                    issues.append(f"Sensor accuracy {accuracy}% — estimated {est} days")
                    days_estimate = min(days_estimate, est)
                if not device.get("firmware_version") == device.get("latest_firmware"):
                    issues.append(f"Firmware outdated: {device.get('firmware_version')} → {device.get('latest_firmware')}")

                prediction = {
                    "days_until_service": days_estimate if days_estimate < 999 else None,
                    "urgency": "CRITICAL" if days_estimate <= 3 else "HIGH" if days_estimate <= 7 else "MODERATE" if days_estimate <= 14 else "LOW",
                    "issues": issues,
                }

                twin_data = {
                    "device_id": device_twin_id,
                    "model": device.get("model"),
                    "device_type": device.get("device_type"),
                    "serial_number": device.get("serial_number"),
                    "location": device.get("location"),
                    "floor": device.get("floor"),
                    "status": device.get("status"),
                    "risk_profile": device.get("risk_profile"),
                    "firmware_version": device.get("firmware_version"),
                    "latest_firmware": device.get("latest_firmware"),
                    "firmware_current": device.get("firmware_version") == device.get("latest_firmware"),
                    "installation_date": device.get("installation_date"),
                    "last_maintenance_date": device.get("last_maintenance_date"),
                    "notes": device.get("notes"),
                    "site": {
                        "site_id": site_id,
                        "site_name": site.get("site_name", "Memorial General Hospital"),
                        "city": site.get("city", "Boston"),
                        "state": site.get("state", "MA"),
                    },
                    "telemetry": {k: float(v) if isinstance(v, (int, float, decimal.Decimal)) else v for k, v in telemetry.items()},
                    "telemetry_history": telemetry_history,
                    "service_history": service_visits,
                    "patient_assignment": patient_assignment,
                    "peer_devices": peers,
                    "prediction": prediction,
                }

                return {
                    "statusCode": 200,
                    "headers": CORS_HEADERS,
                    "body": json.dumps(twin_data, default=dec_default),
                }
            except Exception as e:
                import traceback
                return {"statusCode": 200, "headers": CORS_HEADERS, "body": json.dumps({"error": str(e)})}

        if request_id:
            # Poll for trace events and result
            response = traces_table.query(
                KeyConditionExpression=boto3.dynamodb.conditions.Key("request_id").eq(request_id),
            )
            items = response.get("Items", [])

            traces = [i for i in items if i.get("type") == "trace"]
            result = next((i for i in items if i.get("type") == "result"), None)

            return {
                "statusCode": 200,
                "headers": CORS_HEADERS,
                "body": json.dumps({
                    "request_id": request_id,
                    "traces": [{
                        "agent": t.get("agent"),
                        "status": t.get("status"),
                        "duration_ms": int(t["duration_ms"]) if "duration_ms" in t else None,
                        "response_preview": t.get("response_preview"),
                        "error": t.get("error"),
                        "tool_calls": json.loads(t["tool_calls"]) if "tool_calls" in t else None,
                    } for t in sorted(traces, key=lambda x: x.get("timestamp", 0))],
                    "result": {
                        "response": result.get("response"),
                        "duration_ms": int(result["duration_ms"]) if result and "duration_ms" in result else None,
                        "status": result.get("status"),
                    } if result else None,
                    "completed": result is not None,
                }),
            }

        # Proactive alerts polling endpoint
        alerts_poll = qs.get("proactive_alerts")
        if alerts_poll == "unacknowledged":
            try:
                alerts_tbl = dynamodb.Table("connected-care-proactive-alerts")
                # Scan for unacknowledged alerts (small table, scan is fine for PoC)
                resp = alerts_tbl.scan(
                    FilterExpression=boto3.dynamodb.conditions.Attr("acknowledged").eq(False),
                )
                items = resp.get("Items", [])
                import decimal
                def dec_ser(obj):
                    if isinstance(obj, decimal.Decimal):
                        return float(obj)
                    raise TypeError
                alerts = sorted(items, key=lambda x: x.get("timestamp", ""), reverse=True)[:10]
                return {
                    "statusCode": 200,
                    "headers": CORS_HEADERS,
                    "body": json.dumps({"alerts": alerts}, default=dec_ser),
                }
            except Exception as e:
                return {"statusCode": 200, "headers": CORS_HEADERS, "body": json.dumps({"alerts": [], "error": str(e)})}

        # Acknowledge alert endpoint
        ack_alert = qs.get("acknowledge_alert")
        if ack_alert:
            try:
                alerts_tbl = dynamodb.Table("connected-care-proactive-alerts")
                # Find and update the alert
                resp = alerts_tbl.scan(FilterExpression=boto3.dynamodb.conditions.Attr("alert_id").eq(ack_alert))
                for item in resp.get("Items", []):
                    alerts_tbl.update_item(
                        Key={"alert_type": item["alert_type"], "timestamp": item["timestamp"]},
                        UpdateExpression="SET acknowledged = :val",
                        ExpressionAttributeValues={":val": True},
                    )
                return {"statusCode": 200, "headers": CORS_HEADERS, "body": json.dumps({"status": "acknowledged", "alert_id": ack_alert})}
            except Exception as e:
                return {"statusCode": 200, "headers": CORS_HEADERS, "body": json.dumps({"error": str(e)})}

        return {"statusCode": 200, "headers": CORS_HEADERS, "body": json.dumps({"status": "healthy"})}

    # POST
    try:
        body_str = event.get("body", "{}")
        if event.get("isBase64Encoded"):
            import base64
            body_str = base64.b64decode(body_str).decode("utf-8")

        body = json.loads(body_str)

        # Care team management endpoints
        care_action = body.get("care_team_action")
        if care_action:
            care_team_tbl = dynamodb.Table("connected-care-care-team")
            patient_id = body.get("patient_id", "")
            email = body.get("actor_email", "")

            if care_action == "join" and patient_id and email:
                # Get existing team or create new
                try:
                    resp = care_team_tbl.get_item(Key={"patient_id": patient_id})
                    item = resp.get("Item", {"patient_id": patient_id, "team_members": []})
                except Exception:
                    item = {"patient_id": patient_id, "team_members": []}

                members = item.get("team_members", [])
                if email not in members:
                    members.append(email)
                item["team_members"] = members
                care_team_tbl.put_item(Item=item)
                return {"statusCode": 200, "headers": CORS_HEADERS, "body": json.dumps({"status": "joined", "patient_id": patient_id, "email": email, "team_members": members})}

            if care_action == "check" and patient_id and email:
                try:
                    resp = care_team_tbl.get_item(Key={"patient_id": patient_id})
                    members = resp.get("Item", {}).get("team_members", [])
                    return {"statusCode": 200, "headers": CORS_HEADERS, "body": json.dumps({"authorized": email in members, "patient_id": patient_id, "team_members": members})}
                except Exception:
                    return {"statusCode": 200, "headers": CORS_HEADERS, "body": json.dumps({"authorized": False, "patient_id": patient_id, "team_members": []})}

            if care_action == "list" and patient_id:
                try:
                    resp = care_team_tbl.get_item(Key={"patient_id": patient_id})
                    members = resp.get("Item", {}).get("team_members", [])
                    return {"statusCode": 200, "headers": CORS_HEADERS, "body": json.dumps({"patient_id": patient_id, "team_members": members})}
                except Exception:
                    return {"statusCode": 200, "headers": CORS_HEADERS, "body": json.dumps({"patient_id": patient_id, "team_members": []})}

            if care_action == "leave" and patient_id and email:
                try:
                    resp = care_team_tbl.get_item(Key={"patient_id": patient_id})
                    item = resp.get("Item", {"patient_id": patient_id, "team_members": []})
                    members = item.get("team_members", [])
                    if email in members:
                        members.remove(email)
                    item["team_members"] = members
                    care_team_tbl.put_item(Item=item)
                    return {"statusCode": 200, "headers": CORS_HEADERS, "body": json.dumps({"status": "left", "patient_id": patient_id, "email": email})}
                except Exception as e:
                    return {"statusCode": 200, "headers": CORS_HEADERS, "body": json.dumps({"error": str(e)})}

            return {"statusCode": 400, "headers": CORS_HEADERS, "body": json.dumps({"error": "Invalid care_team_action"})}

        # Scenario injector — writes abnormal data to trigger the threshold evaluator
        simulate_scenario = body.get("simulate_scenario")
        if simulate_scenario:
            from datetime import datetime as dt, timezone as tz
            from decimal import Decimal as D
            now = dt.now(tz.utc).isoformat()

            scenarios = {
                "pressure_injury": {
                    "table": "connected-care-device-telemetry",
                    "key": {"device_id": "D-7001", "timestamp": now},
                    "data": {
                        "device_id": "D-7001", "timestamp": now, "patient_id": "P-10001",
                        "telemetry": {
                            "bed_position": "supine", "head_of_bed_angle": D("30"),
                            "rail_status": "both_up", "brake_status": "locked",
                            "bed_exit_alarm": "armed", "last_bed_exit": "2026-03-30T02:14:00Z",
                            "last_repositioned": now.replace(now[11:13], str(int(now[11:13])-4).zfill(2)) if int(now[11:13]) >= 4 else now,
                            "hours_since_reposition": D("4.1"),
                            "restlessness_score": D("3.5"), "weight_kg": D("58.5"),
                            "pressure_zones": {
                                "sacrum": {"pressure_mmhg": D("52"), "duration_minutes": D("246"), "status": "critical"},
                                "left_heel": {"pressure_mmhg": D("22"), "duration_minutes": D("246"), "status": "normal"},
                                "right_shoulder": {"pressure_mmhg": D("35"), "duration_minutes": D("246"), "status": "elevated"},
                            },
                            "braden_score": {"total": D("12"), "risk_level": "HIGH"},
                            "battery_level": D("90"), "connectivity_status": "connected",
                        },
                    },
                },
                "deterioration": {
                    "table": "connected-care-vitals",
                    "key": {"patient_id": "P-10001", "timestamp": now},
                    "data": {
                        "patient_id": "P-10001", "timestamp": now,
                        "heart_rate": D("118"), "blood_pressure_systolic": D("82"),
                        "blood_pressure_diastolic": D("48"), "spo2": D("87"),
                        "respiratory_rate": D("28"), "temperature": D("101.8"),
                        "blood_glucose": D("195"),
                    },
                },
                "fall_risk": {
                    "table": "connected-care-device-telemetry",
                    "key": {"device_id": "D-7001", "timestamp": now},
                    "data": {
                        "device_id": "D-7001", "timestamp": now, "patient_id": "P-10001",
                        "telemetry": {
                            "bed_position": "upright", "head_of_bed_angle": D("65"),
                            "rail_status": "none", "brake_status": "locked",
                            "bed_exit_alarm": "triggered", "last_bed_exit": now,
                            "last_repositioned": now, "hours_since_reposition": D("0"),
                            "restlessness_score": D("8.5"), "weight_kg": D("58.5"),
                            "pressure_zones": {"sacrum": {"pressure_mmhg": D("15"), "status": "normal"}},
                            "battery_level": D("90"), "connectivity_status": "connected",
                        },
                    },
                },
            }

            scenario = scenarios.get(simulate_scenario)
            if scenario:
                tbl = dynamodb.Table(scenario["table"])
                tbl.put_item(Item=scenario["data"])

                # Clear cooldown for this scenario so the evaluator can fire
                alerts_tbl = dynamodb.Table("connected-care-proactive-alerts")
                try:
                    # Scan and delete ALL entries for this scenario type
                    scan_resp = alerts_tbl.scan()
                    for item in scan_resp.get("Items", []):
                        if item.get("alert_type", "").startswith(simulate_scenario):
                            alerts_tbl.delete_item(Key={"alert_type": item["alert_type"], "timestamp": item["timestamp"]})
                except Exception:
                    pass

                # Invoke the threshold evaluator SYNCHRONOUSLY so it runs before the scheduled one
                try:
                    lambda_client = boto3.client("lambda", region_name=os.environ.get("AWS_REGION_OVERRIDE", os.environ.get("AWS_REGION", "us-east-1")))
                    lambda_client.invoke(
                        FunctionName=os.environ.get("THRESHOLD_EVALUATOR_FUNCTION_NAME", "connected-care-threshold-evaluator"),
                        InvocationType="RequestResponse",
                        Payload=b"{}",
                    )
                except Exception:
                    pass
                return {"statusCode": 200, "headers": CORS_HEADERS, "body": json.dumps({"status": "simulated", "scenario": simulate_scenario})}
            return {"statusCode": 400, "headers": CORS_HEADERS, "body": json.dumps({"error": f"Unknown scenario: {simulate_scenario}"})}

        # Agent invocation
        agent_id = body.get("agent", "")
        prompt = body.get("prompt", "")
        session_id = body.get("session_id", "")
        actor_email = body.get("actor_email", "")
        sync = body.get("sync", False)
        voice_mode = body.get("voice_mode", False)

        if not agent_id or agent_id not in RUNTIME_ARNS:
            return {"statusCode": 400, "headers": CORS_HEADERS, "body": json.dumps({"error": f"Invalid agent"})}
        if not prompt:
            return {"statusCode": 400, "headers": CORS_HEADERS, "body": json.dumps({"error": "Missing prompt"})}

        if not session_id or len(session_id) < 33:
            session_id = f"cc-{agent_id}-{uuid.uuid4().hex}"

        # PHI Access Check — enforce at proxy level before invoking any agent
        if agent_id in ("patient-monitoring", "orchestrator"):
            import re
            patient_ids = re.findall(r'P-\d{5}', prompt, re.IGNORECASE)
            if patient_ids:
                if not actor_email:
                    # No email = can't verify identity = deny access
                    pid = patient_ids[0].upper()
                    return {
                        "statusCode": 200,
                        "headers": CORS_HEADERS,
                        "body": json.dumps({
                            "response": f"Access denied. Unable to verify your identity for patient {pid}. Please sign out and sign back in.",
                            "phi_access_denied": True,
                            "patient_id": pid,
                            "session_id": session_id,
                            "agent": agent_id,
                        }),
                    }
                care_team_tbl = dynamodb.Table("connected-care-care-team")
                for pid in set(p.upper() for p in patient_ids):
                    try:
                        ct_resp = care_team_tbl.get_item(Key={"patient_id": pid})
                        ct_item = ct_resp.get("Item")
                        if not ct_item or actor_email not in ct_item.get("team_members", []):
                            return {
                                "statusCode": 200,
                                "headers": CORS_HEADERS,
                                "body": json.dumps({
                                    "response": f"Access denied. You are not on the care team for patient {pid}. Use the 'Join Care Team' button to request access.",
                                    "phi_access_denied": True,
                                    "patient_id": pid,
                                    "session_id": session_id,
                                    "agent": agent_id,
                                }),
                            }
                    except Exception:
                        pass

        # For domain agents (not orchestrator), respond synchronously — they're fast enough
        if agent_id != "orchestrator" or sync:
            # Voice mode: modify prompt to get concise response directly from agent
            actual_prompt = prompt
            if voice_mode:
                actual_prompt = (
                    "[VOICE MODE — respond in exactly 2 short sentences. "
                    "Sentence 1: the single most important clinical finding. "
                    "Sentence 2: a follow-up question starting with 'Would you like' or 'Should I'. "
                    "No markdown, no tables, no lists, no headers. Plain spoken English only.]\n\n"
                    + prompt
                )

            result = invoke_agent(agent_id, actual_prompt, session_id, f"sync-{uuid.uuid4().hex[:8]}", actor_email)
            agent_response = result.get("response", result.get("error", "No response"))

            # Voice mode: always summarize to 3-4 sentences via Haiku
            voice_summary = None
            if voice_mode and agent_response and "error" not in result:
                voice_summary = summarize_for_voice(agent_response)

            return {
                "statusCode": 200,
                "headers": CORS_HEADERS,
                "body": json.dumps({
                    "response": voice_summary or agent_response,
                    "voice_summary": voice_summary,
                    "session_id": session_id,
                    "agent": agent_id,
                    "duration_ms": result.get("duration_ms", 0),
                    "memory": result.get("memory"),
                }),
            }

        # For orchestrator, use async mode with trace polling
        request_id = f"req-{uuid.uuid4().hex}"

        # Start processing in a background thread
        thread = threading.Thread(target=process_request, args=(agent_id, prompt, session_id, request_id, actor_email))
        thread.start()

        # Return request_id immediately
        return {
            "statusCode": 202,
            "headers": CORS_HEADERS,
            "body": json.dumps({
                "request_id": request_id,
                "agent": agent_id,
                "status": "processing",
                "poll_url": f"?request_id={request_id}",
            }),
        }

    except Exception as e:
        import traceback
        return {"statusCode": 500, "headers": CORS_HEADERS, "body": json.dumps({"error": str(e)})}
