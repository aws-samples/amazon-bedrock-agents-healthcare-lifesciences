from collections import deque
from threading import Lock
from datetime import datetime, timedelta
from typing import List, Dict, Optional

class DataBuffer:
    """Thread-safe in-memory buffer for temperature data"""
    
    def __init__(self, max_minutes: int = 5):
        self.buffer = deque(maxlen=max_minutes * 12)
        self.lock = Lock()
        
    def add_data(self, device_id: str, temperature_data: Dict) -> None:
        with self.lock:
            self.buffer.append({
                'device_id': device_id,
                'timestamp': datetime.now().isoformat(),
                'temperature': temperature_data['current_temp'],
                'target_temperature': temperature_data['target_temp'],
                'scenario_mode': temperature_data.get('scenario_mode', 'unknown'),
                'elapsed_seconds': temperature_data.get('elapsed_seconds', 0)
            })
    
    def get_history(
        self, 
        device_id: Optional[str] = None, 
        minutes: int = 5
    ) -> List[Dict]:
        with self.lock:
            cutoff = datetime.now() - timedelta(minutes=minutes)
            recent_data = [
                d for d in self.buffer 
                if datetime.fromisoformat(d['timestamp']) > cutoff
            ]
            if device_id:
                recent_data = [d for d in recent_data if d['device_id'] == device_id]
            return recent_data
    
    def get_devices(self) -> List[str]:
        with self.lock:
            return list(set(d['device_id'] for d in self.buffer))
