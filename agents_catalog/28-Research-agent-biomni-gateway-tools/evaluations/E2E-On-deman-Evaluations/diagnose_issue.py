"""Comprehensive diagnostic to identify the root cause of the evaluation issue."""

import json
import sys
import inspect
from pathlib import Path

print("=" * 70)
print("EVALUATION ISSUE DIAGNOSTIC")
print("=" * 70)

# Check 1: Is the fix in the source file?
print("\n1. Checking source file for fix...")
source_file = Path("utils/evaluation_client.py")
if source_file.exists():
    with open(source_file, 'r') as f:
        source_content = f.read()
    
    if 'observedTimeUnixNano' in source_content:
        print("   ✅ Fix IS present in source file")
    else:
        print("   ❌ Fix NOT present in source file")
else:
    print("   ❌ Source file not found")

# Check 2: Is the module loaded?
print("\n2. Checking if utils module is loaded...")
if 'utils.evaluation_client' in sys.modules:
    print("   ✅ Module is loaded in memory")
    
    # Check 3: Does the loaded module have the fix?
    print("\n3. Checking if loaded module has the fix...")
    try:
        from utils.evaluation_client import EvaluationClient
        method_source = inspect.getsource(EvaluationClient._filter_relevant_spans)
        
        if 'observedTimeUnixNano' in method_source:
            print("   ✅ Fix IS present in loaded module")
        else:
            print("   ❌ Fix NOT present in loaded module")
            print("   ⚠️  MODULE NEEDS TO BE RELOADED!")
    except Exception as e:
        print(f"   ❌ Error checking loaded module: {e}")
else:
    print("   ⚠️  Module not yet loaded")

# Check 4: Verify most recent input file
print("\n4. Checking most recent input file...")
input_dir = Path("evaluation_input")
if input_dir.exists():
    input_files = sorted(input_dir.glob("input_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if input_files:
        latest_input = input_files[0]
        print(f"   Latest: {latest_input.name}")
        
        with open(latest_input, 'r') as f:
            spans = json.load(f)
        
        # Check index 175
        if len(spans) > 175:
            span_175 = spans[175]
            has_start = 'startTimeUnixNano' in span_175
            has_body = 'body' in span_175
            
            if has_body and not has_start:
                print(f"   ❌ Index 175 is a log event WITHOUT normalized timestamps")
                print(f"   ⚠️  This confirms the fix was NOT applied when this file was created")
            elif has_body and has_start:
                print(f"   ✅ Index 175 has normalized timestamps")
            else:
                print(f"   ℹ️  Index 175 is not a log event")
    else:
        print("   ⚠️  No input files found")
else:
    print("   ⚠️  evaluation_input directory not found")

# Check 5: Verify most recent output file
print("\n5. Checking most recent output file...")
output_dir = Path("evaluation_output")
if output_dir.exists():
    output_files = sorted(output_dir.glob("output_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if output_files:
        latest_output = output_files[0]
        print(f"   Latest: {latest_output.name}")
        
        with open(latest_output, 'r') as f:
            output_data = json.load(f)
        
        results = output_data.get('results', [])
        if results:
            first_result = results[0]
            error = first_result.get('error', '')
            
            if 'start_time' in error and 'required but got None' in error:
                print(f"   ❌ API validation error about missing timestamps")
                print(f"   ⚠️  The API received spans without proper timestamps")
            elif first_result.get('value') is not None:
                print(f"   ✅ Evaluation succeeded with value: {first_result.get('value')}")
            else:
                print(f"   ⚠️  Evaluation returned None (check explanation)")
    else:
        print("   ⚠️  No output files found")
else:
    print("   ⚠️  evaluation_output directory not found")

# Summary and recommendations
print("\n" + "=" * 70)
print("DIAGNOSIS SUMMARY")
print("=" * 70)

print("\nMost likely cause:")
print("  The Jupyter notebook is using a CACHED version of the utils module.")
print("  Even though the fix is in the source file, Python hasn't reloaded it.")

print("\nRECOMMENDED ACTIONS:")
print("  1. In Jupyter: Kernel → Restart Kernel")
print("  2. Re-run all cells from the beginning")
print("  3. Run this diagnostic again to verify the fix is loaded")

print("\nAlternative (without restart):")
print("  Add this cell at the top of your notebook:")
print("  ```python")
print("  import sys")
print("  for key in list(sys.modules.keys()):")
print("      if key.startswith('utils'):")
print("          del sys.modules[key]")
print("  ```")
print("  Then re-import: from utils import EvaluationClient")

print("\n" + "=" * 70)
