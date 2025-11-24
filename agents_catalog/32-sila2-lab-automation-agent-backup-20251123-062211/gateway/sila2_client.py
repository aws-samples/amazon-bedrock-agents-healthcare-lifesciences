"""
SiLA2 Client - デモ向け最小実装（プロトコルシミュレーション版）
"""
import json
import logging
from typing import Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)

class SiLA2Client:
    """基本SiLA2クライアント - デモ向け最小構成（プロトコルシミュレーション版）"""
    
    def __init__(self, config_file: str = "sila2_devices_config.json"):
        self.devices = self._load_device_config(config_file)
        self.connections = {}
    
    def _load_device_config(self, config_file: str) -> Dict[str, Any]:
        """固定デバイス設定を読み込み"""
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
            return {device['id']: device for device in config['devices']}
        except Exception as e:
            logger.error(f"Config load error: {e}")
            return {}
    
    def discover_devices(self) -> List[Dict[str, Any]]:
        """デバイス発見 - 固定エンドポイント使用"""
        return list(self.devices.values())
    
    def connect_device(self, device_id: str) -> bool:
        """デバイス接続 - シンプルな同期接続"""
        if device_id in self.devices:
            self.connections[device_id] = {
                'connected': True,
                'timestamp': datetime.now().isoformat()
            }
            return True
        return False
    
    def get_device_status(self, device_id: str) -> Dict[str, Any]:
        """デバイス状態取得"""
        if device_id not in self.devices:
            return {'error': f'Device {device_id} not found'}
        
        device = self.devices[device_id]
        return {
            'device_id': device_id,
            'status': device['status'],
            'type': device['type'],
            'location': device['location'],
            'temperature': '25.0°C',
            'protocol': 'SiLA2',
            'timestamp': datetime.now().isoformat()
        }
    
    def start_operation(self, device_id: str, operation: str = 'analysis') -> Dict[str, Any]:
        """操作開始"""
        if device_id not in self.devices:
            return {'error': f'Device {device_id} not found'}
        
        if self.devices[device_id]['status'] != 'ready':
            return {'error': f'Device {device_id} not ready'}
        
        self.devices[device_id]['status'] = 'running'
        return {
            'device_id': device_id,
            'operation': operation,
            'status': 'started',
            'operation_id': f'OP-{device_id}-{datetime.now().strftime("%H%M%S")}',
            'estimated_duration': '30 minutes'
        }
    
    def stop_operation(self, device_id: str, operation_id: str) -> Dict[str, Any]:
        """操作停止"""
        if device_id not in self.devices:
            return {'error': f'Device {device_id} not found'}
        
        self.devices[device_id]['status'] = 'ready'
        return {
            'device_id': device_id,
            'operation_id': operation_id,
            'status': 'stopped',
            'timestamp': datetime.now().isoformat()
        }