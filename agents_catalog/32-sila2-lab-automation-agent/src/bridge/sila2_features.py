"""
SiLA2 Feature Mapping
Simple tool grouping for SiLA2 standard compliance
"""

FEATURES = {
    "DeviceManagement": ["list_devices", "get_device_status"],
    "TemperatureController": ["set_temperature", "get_temperature"],
    "PumpFluidDosingService": ["dose_volume", "get_flow_rate"]
}

def get_feature(tool_name: str) -> str:
    """Get feature name for a given tool"""
    for feature, tools in FEATURES.items():
        if tool_name in tools:
            return feature
    return "DeviceManagement"

def get_tools_by_feature(feature_name: str) -> list:
    """Get all tools for a given feature"""
    return FEATURES.get(feature_name, [])

def list_features() -> list:
    """List all available features"""
    return list(FEATURES.keys())
