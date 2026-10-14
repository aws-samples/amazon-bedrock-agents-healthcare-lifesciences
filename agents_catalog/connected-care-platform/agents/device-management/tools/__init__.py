"""Device Management Agent Tools"""

from .get_device_status import get_device_status
from .get_device_history import get_device_history
from .list_devices import list_devices
from .get_device_profile import get_device_profile
from .get_devices_by_patient import get_devices_by_patient
from .get_devices_by_type import get_devices_by_type
from .get_fleet_summary import get_fleet_summary
from .analyze_device_telemetry import analyze_device_telemetry
from .check_nearby_sensors import check_nearby_sensors
from .get_maintenance_history import get_maintenance_history
from .assign_device_to_patient import assign_device_to_patient
from .unassign_device_from_patient import unassign_device_from_patient
from .update_device_status import update_device_status
from .create_maintenance_work_order import create_maintenance_work_order
from .publish_device_event import publish_device_event
from .search_clinical_guidelines import search_clinical_guidelines
from .get_smart_bed_telemetry import get_smart_bed_telemetry
from .get_bed_event_history import get_bed_event_history

ALL_TOOLS = [
    get_device_status,
    get_device_history,
    list_devices,
    get_device_profile,
    get_devices_by_patient,
    get_devices_by_type,
    get_fleet_summary,
    analyze_device_telemetry,
    check_nearby_sensors,
    get_maintenance_history,
    assign_device_to_patient,
    unassign_device_from_patient,
    update_device_status,
    create_maintenance_work_order,
    publish_device_event,
    search_clinical_guidelines,
    get_smart_bed_telemetry,
    get_bed_event_history,
]
