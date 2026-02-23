# ============================================
# ADD THIS CELL AT THE TOP OF YOUR NOTEBOOK
# Run this cell, then re-run your imports
# ============================================

import sys
import importlib

# Remove all cached utils modules
modules_to_remove = [key for key in sys.modules.keys() if key.startswith('utils')]
for module in modules_to_remove:
    del sys.modules[module]

print("✅ Cleared cached modules:", modules_to_remove)
print("Now re-run the cell that imports EvaluationClient")

# ============================================
# VERIFICATION CELL (optional)
# Run this after importing EvaluationClient
# ============================================

import inspect
from utils.evaluation_client import EvaluationClient

# Check if the fix is present
source = inspect.getsource(EvaluationClient._filter_relevant_spans)
if 'observedTimeUnixNano' in source:
    print("✅ Fix is loaded! The timestamp normalization code is present.")
    print("You can now run your evaluations.")
else:
    print("❌ Still using old code!")
    print("Please restart the Jupyter kernel: Kernel → Restart Kernel")
