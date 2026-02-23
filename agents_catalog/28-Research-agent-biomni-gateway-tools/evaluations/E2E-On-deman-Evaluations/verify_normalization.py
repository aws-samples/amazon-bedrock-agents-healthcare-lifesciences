"""Verify if timestamp normalization is working in the saved input files."""

import json
from pathlib import Path

# Check the most recent input file
input_file = Path("evaluation_input") / "input_eb81898a-9522-4a_20260213_124112.json"

with open(input_file, 'r') as f:
    spans = json.load(f)

print(f"Checking file: {input_file.name}")
print(f"Total entries: {len(spans)}")

# Check index 175 specifically
if len(spans) > 175:
    span_175 = spans[175]
    print(f"\nEntry at index 175:")
    print(f"  Has 'body': {'body' in span_175}")
    print(f"  Has 'startTimeUnixNano': {'startTimeUnixNano' in span_175}")
    print(f"  Has 'endTimeUnixNano': {'endTimeUnixNano' in span_175}")
    print(f"  Has 'timeUnixNano': {'timeUnixNano' in span_175}")
    print(f"  Has 'observedTimeUnixNano': {'observedTimeUnixNano' in span_175}")
    
    if 'startTimeUnixNano' in span_175:
        print(f"  startTimeUnixNano value: {span_175['startTimeUnixNano']}")
    if 'timeUnixNano' in span_175:
        print(f"  timeUnixNano value: {span_175['timeUnixNano']}")
    if 'observedTimeUnixNano' in span_175:
        print(f"  observedTimeUnixNano value: {span_175['observedTimeUnixNano']}")
    
    print(f"\n  ❌ NORMALIZATION NOT APPLIED - startTimeUnixNano is missing!" if 'startTimeUnixNano' not in span_175 else "  ✅ NORMALIZATION APPLIED")
else:
    print(f"File has only {len(spans)} entries, cannot check index 175")

# Count how many log events are missing timestamps
missing_count = 0
log_event_count = 0

for i, span in enumerate(spans):
    if 'body' in span:
        log_event_count += 1
        if 'startTimeUnixNano' not in span:
            missing_count += 1

print(f"\nLog events: {log_event_count}")
print(f"Log events missing startTimeUnixNano: {missing_count}")

if missing_count > 0:
    print(f"\n⚠️  The fix is NOT being applied. The notebook is using cached code.")
    print(f"   You need to restart the Jupyter kernel to reload the updated module.")
else:
    print(f"\n✅ All log events have been normalized with timestamps!")
