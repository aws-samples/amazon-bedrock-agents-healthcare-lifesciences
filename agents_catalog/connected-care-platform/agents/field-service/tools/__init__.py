"""Field Service Intelligence Agent Tools"""

from .get_installed_base import get_installed_base
from .get_device_performance_by_model import get_device_performance_by_model
from .predict_field_service_needs import predict_field_service_needs
from .compare_firmware_performance import compare_firmware_performance
from .get_service_history import get_service_history
from .create_service_dispatch import create_service_dispatch
from .publish_field_service_event import publish_field_service_event

ALL_TOOLS = [
    get_installed_base,
    get_device_performance_by_model,
    predict_field_service_needs,
    compare_firmware_performance,
    get_service_history,
    create_service_dispatch,
    publish_field_service_event,
]
