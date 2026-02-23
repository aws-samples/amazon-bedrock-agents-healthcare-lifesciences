# How to Reload the Fixed Module

The Jupyter notebook is using a cached version of the `utils` module. You have two options:

## Option 1: Restart Kernel (Recommended)

1. In Jupyter, click **Kernel** → **Restart Kernel**
2. Re-run all cells from the beginning

## Option 2: Force Reload Without Restart

Add this cell **at the very top** of your notebook (before any other imports) and run it:

```python
# Force reload the utils module to pick up fixes
import sys
import importlib

# Remove all cached utils modules
modules_to_remove = [key for key in sys.modules.keys() if key.startswith('utils')]
for module in modules_to_remove:
    del sys.modules[module]

print("✅ Cleared cached modules:", modules_to_remove)
```

Then re-run the cell that imports `EvaluationClient`:

```python
from utils import EvaluationClient
```

## Verify the Fix is Loaded

After reloading, you can verify the fix is active by checking the method:

```python
import inspect
from utils.evaluation_client import EvaluationClient

# Check if the fix is present
source = inspect.getsource(EvaluationClient._filter_relevant_spans)
if 'observedTimeUnixNano' in source:
    print("✅ Fix is loaded!")
else:
    print("❌ Still using old code - try restarting kernel")
```

## What Should Happen After Fix

Once the fix is properly loaded, you should see:
- No validation errors about missing timestamps
- Actual evaluation scores instead of `None`
- Dashboard populated with results
- Warning messages if there are >10 tool spans
