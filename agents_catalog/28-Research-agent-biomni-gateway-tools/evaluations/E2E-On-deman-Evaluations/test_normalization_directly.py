"""Test the normalization logic directly to verify it works."""

import sys
import json
from pathlib import Path

# Force fresh import
for key in list(sys.modules.keys()):
    if key.startswith('utils'):
        del sys.modules[key]

# Import fresh
from utils.evaluation_client import EvaluationClient

# Create a test log event like the ones causing issues
test_log_event = {
    "resource": {"attributes": {}},
    "scope": {"name": "test"},
    "timeUnixNano": 0,  # This is the problem - it's 0
    "observedTimeUnixNano": 1770983779379445988,  # This should be used instead
    "severityNumber": 9,
    "body": {
        "output": {
            "messages": [{"content": "test"}]
        }
    },
    "attributes": {}
}

# Create client and test the method
client = EvaluationClient(region="us-east-1")

print("Testing normalization with a log event that has timeUnixNano=0...")
print(f"Input log event:")
print(f"  timeUnixNano: {test_log_event['timeUnixNano']}")
print(f"  observedTimeUnixNano: {test_log_event['observedTimeUnixNano']}")
print(f"  Has startTimeUnixNano: {'startTimeUnixNano' in test_log_event}")

# Call the filter method
result = client._filter_relevant_spans([test_log_event])

print(f"\nAfter normalization:")
if result:
    normalized = result[0]
    print(f"  Has startTimeUnixNano: {'startTimeUnixNano' in normalized}")
    print(f"  Has endTimeUnixNano: {'endTimeUnixNano' in normalized}")
    if 'startTimeUnixNano' in normalized:
        print(f"  startTimeUnixNano value: {normalized['startTimeUnixNano']}")
        print(f"  endTimeUnixNano value: {normalized['endTimeUnixNano']}")
        
        if normalized['startTimeUnixNano'] == test_log_event['observedTimeUnixNano']:
            print(f"\n✅ SUCCESS! Used observedTimeUnixNano as fallback")
        else:
            print(f"\n❌ FAIL! Wrong timestamp value")
    else:
        print(f"\n❌ FAIL! Timestamps not added")
else:
    print(f"  ❌ FAIL! Log event was filtered out")

# Now test with a real file
print("\n" + "="*70)
print("Testing with actual input file...")
input_dir = Path("evaluation_input")
if input_dir.exists():
    input_files = sorted(input_dir.glob("input_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if input_files:
        latest = input_files[0]
        print(f"Loading: {latest.name}")
        
        with open(latest, 'r') as f:
            spans = json.load(f)
        
        # Find log events with timeUnixNano=0
        problem_spans = []
        for i, span in enumerate(spans):
            if 'body' in span and span.get('timeUnixNano') == 0:
                problem_spans.append((i, span))
        
        if problem_spans:
            print(f"Found {len(problem_spans)} log events with timeUnixNano=0")
            
            # Test normalization on first few
            test_spans = [span for _, span in problem_spans[:5]]
            normalized = client._filter_relevant_spans(test_spans)
            
            print(f"\nNormalized {len(normalized)} out of {len(test_spans)} problem spans")
            
            if normalized:
                first = normalized[0]
                if 'startTimeUnixNano' in first and first['startTimeUnixNano'] > 0:
                    print(f"✅ Normalization working! First span has startTimeUnixNano={first['startTimeUnixNano']}")
                else:
                    print(f"❌ Normalization failed!")
        else:
            print("No problem spans found (all have valid timeUnixNano)")
