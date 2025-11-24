"""
統一Mock Device Lambda - Phase 3実装
"""
import json
import logging
from typing import Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class DeviceSimulator:
    """基本デバイスシミュレーター"""
    
    def handle_request(self, action: str, device_id: str, event: dict) -> Dict[str, Any]:
        method = getattr(self, f"handle_{action}", None)
        if not method:
            return {'error': f'Unsupported action: {action}'}
        return method(device_id, event)

class HPLCSimulator(DeviceSimulator):
    """HPLC シミュレーター"""
    
    def handle_get_status(self, device_id: str, event: dict) -> Dict[str, Any]:
        return {
            'device_id': device_id,
            'status': 'ready',
            'temperature': 25.0,
            'pressure': 150.0,
            'flow_rate': 1.0,
            'type': 'HPLC'
        }
    
    def handle_start_analysis(self, device_id: str, event: dict) -> Dict[str, Any]:
        return {
            'device_id': device_id,
            'operation': 'analysis_started',
            'estimated_time': 1800,
            'status': 'running'
        }

class CentrifugeSimulator(DeviceSimulator):
    """遠心分離機シミュレーター"""
    
    def handle_get_status(self, device_id: str, event: dict) -> Dict[str, Any]:
        return {
            'device_id': device_id,
            'status': 'busy',
            'rpm': 3000,
            'temperature': 4.0,
            'remaining_time': 600,
            'type': 'Centrifuge'
        }
    
    def handle_start_spin(self, device_id: str, event: dict) -> Dict[str, Any]:
        return {
            'device_id': device_id,
            'operation': 'spin_started',
            'rpm': event.get('rpm', 3000),
            'duration': event.get('duration', 600)
        }

class PipetteSimulator(DeviceSimulator):
    """ピペットシミュレーター"""
    
    def handle_get_status(self, device_id: str, event: dict) -> Dict[str, Any]:
        return {
            'device_id': device_id,
            'status': 'ready',
            'tip_attached': True,
            'volume_range': '0.1-1000μL',
            'type': 'Pipette'
        }
    
    def handle_aspirate(self, device_id: str, event: dict) -> Dict[str, Any]:
        return {
            'device_id': device_id,
            'operation': 'aspirate_completed',
            'volume': event.get('volume', 100),
            'position': event.get('position', 'A1')
        }

class UnifiedMockDeviceLambda:
    """統一Mock Device Lambda"""
    
    def __init__(self):
        self.device_simulators = {
            'hplc': HPLCSimulator(),
            'centrifuge': CentrifugeSimulator(),
            'pipette': PipetteSimulator()
        }
    
    def lambda_handler(self, event, context):
        """Lambda エントリーポイント"""
        try:
            # パラメータ抽出
            if 'pathParameters' in event:
                device_type = event['pathParameters'].get('device_type')
                device_id = event['pathParameters'].get('device_id')
                action = event['pathParameters'].get('action')
            else:
                # 直接呼び出しの場合
                device_type = event.get('device_type')
                device_id = event.get('device_id')
                action = event.get('action')
            
            if not all([device_type, device_id, action]):
                return {
                    'statusCode': 400,
                    'body': json.dumps({'error': 'Missing required parameters'})
                }
            
            # デバイスシミュレーター取得
            simulator = self.device_simulators.get(device_type.lower())
            if not simulator:
                return {
                    'statusCode': 404,
                    'body': json.dumps({'error': f'Device type {device_type} not supported'})
                }
            
            # リクエスト処理
            result = simulator.handle_request(action, device_id, event)
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'success': True,
                    'result': result,
                    'timestamp': datetime.now().isoformat()
                })
            }
            
        except Exception as e:
            logger.error(f"Lambda handler error: {e}")
            return {
                'statusCode': 500,
                'body': json.dumps({'error': str(e)})
            }

# Lambda handler
unified_lambda = UnifiedMockDeviceLambda()
lambda_handler = unified_lambda.lambda_handler