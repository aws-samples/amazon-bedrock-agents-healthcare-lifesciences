# Phase 2: Feature Definition (5 hours)

**Status**: ✅ COMPLETED (2026-01-16)

**Objective**: Create SiLA2 Feature definitions and generate code

---

## Completion Summary

✅ All tasks completed successfully
✅ 3 SiLA2 Feature definitions created
✅ Python code generated from all features
✅ All validation checks passed

**Key Changes**:
- SetTemperature changed to Observable=Yes (supports IntermediateResponse)
- Generated code in `src/devices/generated/lab_devices/`
- Used `sila2-codegen new-package` command (not `generate-server`)

---

## Tasks

1. Create features directory (5min)
2. Write TemperatureController.sila.xml (2h)
3. Write DeviceManagement.sila.xml (1h)
4. Write TaskManagement.sila.xml (1h)
5. Generate Python code (1h)

---

## Step 1: Create Directory

```bash
mkdir -p src/devices/features
```

---

## Step 2: TemperatureController.sila.xml

✅ **COMPLETED**

Created `src/devices/features/TemperatureController.sila.xml` with:
- SetTemperature command (**Observable=Yes** with IntermediateResponse for progress streaming)
- AbortExperiment command
- Observable properties: CurrentTemperature, TargetTemperature, HeatingStatus

**Important**: Changed from Observable=No to Observable=Yes to support IntermediateResponse streaming.

---

## Step 3: DeviceManagement.sila.xml

✅ **COMPLETED**

Created `src/devices/features/DeviceManagement.sila.xml` with:
- ListDevices command (returns list of device IDs)
- GetDeviceInfo command (returns device metadata)
- GetDeviceStatus command (returns current device status)

---

## Step 4: TaskManagement.sila.xml

✅ **COMPLETED**

Created `src/devices/features/TaskManagement.sila.xml` with:
- GetTaskStatus command (returns task status and progress)
- GetTaskInfo command (returns detailed task information)

---

## Step 5: Generate Code

✅ **COMPLETED**

```bash
cd src/devices

# Install sila2 with codegen
python3 -m pip install 'sila2>=0.14.0' 'sila2[codegen]'

# Generate Python code (UPDATED COMMAND)
sila2-codegen new-package -n lab_devices -o generated features/*.sila.xml

# Verify generation
ls generated/lab_devices/generated/
# Output: temperaturecontroller/, devicemanagement/, taskmanagement/

# Quick syntax check
python3 -m py_compile generated/lab_devices/generated/**/*.py
```

**Generated Structure**:
```
generated/
└── lab_devices/
    ├── __main__.py
    ├── pyproject.toml
    └── generated/
        ├── temperaturecontroller/
        ├── devicemanagement/
        └── taskmanagement/
```

---

## Validation

✅ **ALL CHECKS PASSED**

```bash
# Check XML files
test -f src/devices/features/TemperatureController.sila.xml && echo "✓ TemperatureController.sila.xml"
test -f src/devices/features/DeviceManagement.sila.xml && echo "✓ DeviceManagement.sila.xml"
test -f src/devices/features/TaskManagement.sila.xml && echo "✓ TaskManagement.sila.xml"

# Check generated code (UPDATED PATHS)
test -d src/devices/generated/lab_devices/generated/temperaturecontroller && echo "✓ Generated TemperatureController"
test -d src/devices/generated/lab_devices/generated/devicemanagement && echo "✓ Generated DeviceManagement"
test -d src/devices/generated/lab_devices/generated/taskmanagement && echo "✓ Generated TaskManagement"
```

**Results**:
```
✓ TemperatureController.sila.xml
✓ DeviceManagement.sila.xml
✓ TaskManagement.sila.xml
✓ Generated TemperatureController
✓ Generated DeviceManagement
✓ Generated TaskManagement
```

---

## Lessons Learned

1. **Command Type Selection**: Observable=Yes commands support IntermediateResponse for streaming, but cannot have a final Response element
2. **Code Generation Tool**: Use `sila2-codegen new-package` instead of deprecated `generate-server` command
3. **Python Version**: Ensure using Python 3.10+ with `python3 -m pip` for correct pip version
4. **Package Structure**: Generated code is nested under `lab_devices/generated/` directory

---

## Next Step

→ [Phase 3: Devices](03_DEVICES.md)
