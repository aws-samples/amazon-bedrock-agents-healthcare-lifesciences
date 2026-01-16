# Phase 2: Feature Definition (5 hours)

**Objective**: Create SiLA2 Feature definitions and generate code

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

Create `src/devices/features/TemperatureController.sila.xml` with the complete SiLA2 Feature definition including:
- SetTemperature command (Unobservable with IntermediateResponse)
- AbortExperiment command
- Observable properties: CurrentTemperature, TargetTemperature, HeatingStatus

See full XML in the original SILA2_MIGRATION_PLAN.md

---

## Step 3: DeviceManagement.sila.xml

Create `src/devices/features/DeviceManagement.sila.xml` with:
- ListDevices command
- GetDeviceInfo command
- GetDeviceStatus command

---

## Step 4: TaskManagement.sila.xml

Create `src/devices/features/TaskManagement.sila.xml` with:
- GetTaskStatus command
- GetTaskInfo command

---

## Step 5: Generate Code

```bash
cd src/devices

# Install sila2 with codegen
pip install 'sila2>=0.14.0' 'sila2[codegen]'

# Generate Python code
sila2-codegen generate-server features/ --output generated/

# Verify generation
ls generated/
# Should see: temperaturecontroller/, devicemanagement/, taskmanagement/

# Quick syntax check
python -m py_compile generated/**/*.py || echo "⚠️ Check generated code for errors"
```

---

## Validation

```bash
# Check XML files
test -f src/devices/features/TemperatureController.sila.xml && echo "✓ TemperatureController.sila.xml"
test -f src/devices/features/DeviceManagement.sila.xml && echo "✓ DeviceManagement.sila.xml"
test -f src/devices/features/TaskManagement.sila.xml && echo "✓ TaskManagement.sila.xml"

# Check generated code
test -d src/devices/generated/temperaturecontroller && echo "✓ Generated TemperatureController"
test -d src/devices/generated/devicemanagement && echo "✓ Generated DeviceManagement"
test -d src/devices/generated/taskmanagement && echo "✓ Generated TaskManagement"
```

---

## Next Step

→ [Phase 3: Devices](03_DEVICES.md)
