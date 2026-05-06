"""Inventory Management Agent Tools"""

from .get_floor_inventory import get_floor_inventory
from .get_item_status import get_item_status
from .get_item_usage_history import get_item_usage_history
from .check_stockout_risk import check_stockout_risk
from .get_patients_affected_by_shortage import get_patients_affected_by_shortage
from .get_substitute_items import get_substitute_items
from .get_supply_chain_status import get_supply_chain_status
from .create_reorder_request import create_reorder_request
from .publish_inventory_event import publish_inventory_event

ALL_TOOLS = [
    get_floor_inventory,
    get_item_status,
    get_item_usage_history,
    check_stockout_risk,
    get_patients_affected_by_shortage,
    get_substitute_items,
    get_supply_chain_status,
    create_reorder_request,
    publish_inventory_event,
]
