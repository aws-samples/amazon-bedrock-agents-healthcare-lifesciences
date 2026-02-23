# Evaluation Dashboard Fix Summary

## Issues Found

### Issue 1: Empty Dashboard with Validation Errors
**Symptom:** All evaluations returning `None` with validation errors about missing `start_time` and `end_time` fields.

**Root Cause:** Log events in the OpenTelemetry data have different timestamp fields than spans:
- **Spans** have: `startTimeUnixNano` and `endTimeUnixNano`
- **Log events** have: `timeUnixNano` and `observedTimeUnixNano`
- Some log events have `timeUnixNano: 0` (invalid)

The AgentCore Evaluation API requires all entries to have `startTimeUnixNano` and `endTimeUnixNano`.

**Fix Applied:** Modified `_filter_relevant_spans()` in `utils/evaluation_client.py` to:
1. Normalize log events by adding `startTimeUnixNano` and `endTimeUnixNano` fields
2. Use `timeUnixNano` if available and non-zero
3. Fall back to `observedTimeUnixNano` if `timeUnixNano` is 0 or missing
4. Skip log events that have no valid timestamps

### Issue 2: Span-Scoped Evaluators Failing
**Symptom:** `Builtin.ToolSelectionAccuracy` and `Builtin.ToolParameterAccuracy` failing with error: "Member must have length less than or equal to 10"

**Root Cause:** The session had more than 10 tool execution spans, but the API has a limit of 10 span IDs per evaluation request.

**Fix Applied:** Modified `evaluate_session()` in `utils/evaluation_client.py` to:
- Limit span IDs to maximum of 10 (most recent)
- Add warning message when truncating

## How to Apply the Fix

### Option 1: Restart Jupyter Kernel (Recommended)
1. In the Jupyter notebook, click **Kernel** → **Restart Kernel**
2. Re-run all cells from the beginning
3. The updated `utils/evaluation_client.py` will be loaded

### Option 2: Reload the Module
Add this cell at the top of your notebook and run it:
```python
import importlib
import sys

# Remove cached modules
if 'utils.evaluation_client' in sys.modules:
    del sys.modules['utils.evaluation_client']
if 'utils' in sys.modules:
    del sys.modules['utils']

# Reimport
from utils import EvaluationClient
```

## Testing the Fix

After applying the fix, run your evaluation again. You should see:
1. ✅ No validation errors about missing timestamps
2. ✅ Actual evaluation scores (not `None`)
3. ✅ Dashboard populated with evaluation results
4. ⚠️ Warning if >10 tool spans (they'll be limited to 10)

## Files Modified

1. `evaluations/E2E-On-deman-Evaluations/utils/evaluation_client.py`
   - `_filter_relevant_spans()` method: Added timestamp normalization logic
   - `evaluate_session()` method: Added span ID limit (max 10)

## Expected Output After Fix

```
Found 621 spans across X traces in session
Found 15 tool execution spans for evaluation
Warning: Found 15 tool execution spans, limiting to 10 most recent (API limit)
Collecting most recent 200 relevant items
Sending 200 items (147 spans [X with gen_ai attrs], 53 log events) to evaluation API

Completed: 10 evaluations
  Builtin.Correctness: 0.85 - Mostly Correct
  Builtin.Faithfulness: 1.0 - Completely Yes
  Builtin.Helpfulness: 0.75 - Mostly Helpful
  ...
```

## Additional Notes

- The fix preserves all original span data
- Log events are only modified in-memory (not saved back to files)
- The dashboard will automatically regenerate when `auto_create_dashboard=True`
- Old evaluation output files with errors can be deleted if desired
