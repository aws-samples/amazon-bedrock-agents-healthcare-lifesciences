# Verification Steps for Jupyter Notebook

Run these cells in your notebook to verify the fix is loaded:

## Step 1: Check if fix is in the loaded module

```python
import inspect
from utils.evaluation_client import EvaluationClient

# Get the source code of the method
source = inspect.getsource(EvaluationClient._filter_relevant_spans)

# Check for the fix
if 'observedTimeUnixNano' in source:
    print("✅ FIX IS LOADED!")
    print("The timestamp normalization code is present.")
else:
    print("❌ FIX NOT LOADED!")
    print("The old code is still being used.")
    print("\nTry this:")
    print("1. Kernel → Restart Kernel")
    print("2. Re-run all cells")
```

## Step 2: Check for debug output

When you run the evaluation, you should now see these messages:

```
✅ Timestamp normalization applied: XXX log events normalized
```

If you DON'T see this message, the fix isn't being executed.

## Step 3: Manual module reload (if restart doesn't work)

If restarting the kernel doesn't work, try this cell:

```python
import sys
import importlib

# Remove ALL utils modules from cache
modules_to_remove = [key for key in list(sys.modules.keys()) if 'utils' in key]
for module in modules_to_remove:
    print(f"Removing: {module}")
    del sys.modules[module]

# Now re-import
from utils import EvaluationClient
print("✅ Modules reloaded")
```

## Step 4: Verify the normalization works

```python
# Create a test log event
test_event = {
    "timeUnixNano": 0,
    "observedTimeUnixNano": 1234567890,
    "body": {"output": {"messages": []}},
    "attributes": {}
}

# Test normalization
client = EvaluationClient(region="us-east-1")
result = client._filter_relevant_spans([test_event])

if result and 'startTimeUnixNano' in result[0]:
    print(f"✅ Normalization works!")
    print(f"   startTimeUnixNano: {result[0]['startTimeUnixNano']}")
else:
    print(f"❌ Normalization failed!")
```

## What to look for when running evaluation

After the fix is properly loaded, you should see output like:

```
Found 621 spans across 3 traces in session
Collecting most recent 200 relevant items
✅ Timestamp normalization applied: 446 log events normalized
Sending 200 items (147 spans [X with gen_ai attrs], 53 log events) to evaluation API

Completed: 10 evaluations
  Builtin.Correctness: 0.85 - Mostly Correct
  ...
```

The key indicator is the "✅ Timestamp normalization applied" message.

## If nothing works

If you've tried everything and it still doesn't work, there might be:

1. **Multiple Python environments**: Check if your notebook is using a different Python environment than where the code is
2. **File system sync issue**: If using a cloud/network drive, files might not be syncing
3. **Permissions issue**: Check if the file is actually being saved with your edits

Run this to check your Python path:

```python
import sys
print("Python executable:", sys.executable)
print("\nPython path:")
for p in sys.path:
    print(f"  {p}")
```
