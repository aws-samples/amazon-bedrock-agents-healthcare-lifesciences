import html
import sqlite3
from strands import tool
import threading

# Thread-local storage for database connections
_local = threading.local()

def get_db_connection():
    if not hasattr(_local, 'connection'):
        _local.connection = sqlite3.connect("medical_devices.db", check_same_thread=False)
        _local.connection.execute("PRAGMA journal_mode=WAL")
        _local.connection.execute("PRAGMA synchronous=NORMAL")
    return _local.connection

@tool
def get_device_status(device_id: str) -> str:
    """
    Get the current status of a medical device.

    Args:
        device_id (str): The unique identifier of the medical device.

    Returns:
        str: Current status and details of the medical device.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Create the devices table if it doesn't exist
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS devices (
        id TEXT PRIMARY KEY,
        name TEXT,
        type TEXT,
        status TEXT,
        location TEXT,
        last_maintenance TEXT,
        next_maintenance TEXT
    )
    """
    )

    # Insert sample data if table is empty
    cursor.execute("SELECT COUNT(*) FROM devices")
    if cursor.fetchone()[0] == 0:
        sample_devices = [
            ("DEV001", "MRI Scanner", "Imaging", "Operational", "Room 101", "2024-01-15", "2024-04-15"),
            ("DEV002", "Ventilator", "Life Support", "Maintenance Required", "ICU-A", "2023-12-01", "2024-03-01"),
            ("DEV003", "X-Ray Machine", "Imaging", "Operational", "Room 205", "2024-02-01", "2024-05-01"),
        ]
        cursor.executemany(
            "INSERT INTO devices (id, name, type, status, location, last_maintenance, next_maintenance) VALUES (?, ?, ?, ?, ?, ?, ?)",
            sample_devices
        )
        conn.commit()

    # Sanitize input to prevent XSS
    sanitized_device_id = html.escape(device_id.strip())
    cursor.execute("SELECT * FROM devices WHERE id = ?", (sanitized_device_id,))
    device = cursor.fetchone()
    
    if device:
        return f"Device {device[0]}: {device[1]} ({device[2]}) - Status: {device[3]}, Location: {device[4]}, Last Maintenance: {device[5]}, Next Maintenance: {device[6]}"
    else:
        return f"Device {device_id} not found"

@tool
def list_all_devices() -> str:
    """
    List all medical devices in the system.

    Returns:
        str: List of all medical devices with their current status.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS devices (
        id TEXT PRIMARY KEY,
        name TEXT,
        type TEXT,
        status TEXT,
        location TEXT,
        last_maintenance TEXT,
        next_maintenance TEXT
    )
    """
    )

    cursor.execute("SELECT COUNT(*) FROM devices")
    if cursor.fetchone()[0] == 0:
        sample_devices = [
            ("DEV001", "MRI Scanner", "Imaging", "Operational", "Room 101", "2024-01-15", "2024-04-15"),
            ("DEV002", "Ventilator", "Life Support", "Maintenance Required", "ICU-A", "2023-12-01", "2024-03-01"),
            ("DEV003", "X-Ray Machine", "Imaging", "Operational", "Room 205", "2024-02-01", "2024-05-01"),
        ]
        cursor.executemany(
            "INSERT INTO devices (id, name, type, status, location, last_maintenance, next_maintenance) VALUES (?, ?, ?, ?, ?, ?, ?)",
            sample_devices
        )
        conn.commit()

    cursor.execute("SELECT * FROM devices ORDER BY id")
    devices = cursor.fetchall()
    
    if devices:
        device_list = []
        for device in devices:
            device_list.append(f"ID: {device[0]}, Name: {device[1]}, Type: {device[2]}, Status: {device[3]}, Location: {device[4]}")
        return "\n".join(device_list)
    else:
        return "No devices found in the system"