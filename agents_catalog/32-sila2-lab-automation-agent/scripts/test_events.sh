#!/bin/bash
set -e

echo "=== Phase 6 Integration Test ==="

BRIDGE_URL="http://localhost:8080"
DEVICE_ID="hplc_001"

echo ""
echo "1. Testing Bridge Health..."
curl -s "$BRIDGE_URL/health" | jq .

echo ""
echo "2. Testing Device List..."
curl -s "$BRIDGE_URL/api/devices" | jq .

echo ""
echo "3. Testing Data History (5 minutes)..."
curl -s "$BRIDGE_URL/api/history/$DEVICE_ID?minutes=5" | jq '.count, .data[0]'

echo ""
echo "4. Waiting 10 seconds for data collection..."
sleep 10

echo ""
echo "5. Re-checking data count..."
curl -s "$BRIDGE_URL/api/history/$DEVICE_ID?minutes=5" | jq '.count'

echo ""
echo "✅ Phase 6 Bridge Server tests complete!"
