"""
Phase 3 Enhanced Test Suite
AgentCore Runtime → Gateway → Protocol Bridge → Mock Devices
"""
import json
import sys
import os
import requests
from datetime import datetime

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

class TestPhase3:
    """Phase 3 コンポーネントテスト"""
    
    def __init__(self):
        self.test_results = []
        # API Gateway URL (環境変数から取得予定)
        self.api_gateway_url = os.environ.get('MOCK_DEVICE_API_URL', 'http://localhost:3000')
    
    def log_test(self, test_name: str, success: bool, message: str = ""):
        """Test result logging"""
        status = "PASS" if success else "FAIL"
        result = {
            "test": test_name,
            "status": status,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        print(f"[{status}] {test_name}: {message}")
    
    def test_gateway_tools_simplified(self):
        """Gateway Tools Simplified テスト"""
        try:
            from gateway.sila2_gateway_tools_simplified import SiLA2GatewayToolsSimplified
            
            tools = SiLA2GatewayToolsSimplified()
            
            # Device list test
            result = tools.list_available_devices()
            success = result.get('success', False) and len(result.get('devices', [])) > 0
            self.log_test("Gateway Tools - Device List", success, f"Found {len(result.get('devices', []))} devices")
            
            # Device status test
            result = tools.get_device_status("HPLC-01")
            success = result.get('success', False) and result.get('device_id') == "HPLC-01"
            self.log_test("Gateway Tools - Device Status", success, f"Status: {result.get('status')}")
            
            # Device operation test
            result = tools.start_device_operation("HPLC-01", "start_analysis", {"method": "test"})
            success = result.get('success', False)
            self.log_test("Gateway Tools - Device Operation", success, f"Operation: {result.get('operation')}")
            
        except Exception as e:
            self.log_test("Gateway Tools Simplified", False, str(e))
    
    def test_protocol_bridge(self):
        """Protocol Bridge テスト"""
        try:
            from protocol_bridge_lambda import ProtocolBridgeLambda, DeviceRegistry
            
            bridge = ProtocolBridgeLambda()
            
            # Device registry test
            devices = DeviceRegistry.list_all_devices()
            success = len(devices) > 0
            self.log_test("Protocol Bridge - Device Registry", success, f"Registered {len(devices)} devices")
            
            # Device list test
            result = bridge.handle_device_list()
            success = result.get('success', False) and len(result.get('devices', [])) > 0
            self.log_test("Protocol Bridge - Device List", success, f"Listed {result.get('count')} devices")
            
            # Device request test
            result = bridge.handle_device_request("HPLC-01", "GET")
            success = result.get('success', False)
            self.log_test("Protocol Bridge - Device Request", success, f"Device: {result.get('device_id', 'N/A')}")
            
        except Exception as e:
            self.log_test("Protocol Bridge", False, str(e))
    
    def test_mock_device_enhanced(self):
        """Mock Device Enhanced テスト"""
        try:
            from gateway.mock_device_lambda_enhanced import MockDeviceLambdaEnhanced
            
            mock_device = MockDeviceLambdaEnhanced()
            
            # Device list test
            result = mock_device.handle_list_devices()
            success = result.get('success', False) and len(result.get('devices', [])) > 0
            self.log_test("Mock Device - Device List", success, f"Found {result.get('count')} devices")
            
            # Device status test
            result = mock_device.handle_device_status("HPLC-01")
            success = result.get('success', False) and result.get('device_id') == "HPLC-01"
            self.log_test("Mock Device - Device Status", success, f"Type: {result.get('type')}")
            
            # Device operation test
            result = mock_device.handle_device_operation("HPLC-01", "start_analysis", {"method": "test"})
            success = result.get('success', False)
            self.log_test("Mock Device - Device Operation", success, f"Operation: {result.get('operation', 'N/A')}")
            
        except Exception as e:
            self.log_test("Mock Device Enhanced", False, str(e))
    
    def test_http_integration(self):
        """HTTP統合テスト"""
        try:
            # HTTPエンドポイントテスト (ローカルまたはAPI Gateway)
            if self.api_gateway_url and self.api_gateway_url != 'http://localhost:3000':
                try:
                    # Device list endpoint
                    response = requests.get(f"{self.api_gateway_url}/devices", timeout=10)
                    success = response.status_code == 200
                    self.log_test("HTTP Integration - Device List", success, f"Status: {response.status_code}")
                    
                    # Device status endpoint
                    response = requests.get(f"{self.api_gateway_url}/device/HPLC-01", timeout=10)
                    success = response.status_code == 200
                    self.log_test("HTTP Integration - Device Status", success, f"Status: {response.status_code}")
                    
                except requests.RequestException as e:
                    self.log_test("HTTP Integration", False, f"Request error: {e}")
            else:
                self.log_test("HTTP Integration", True, "Skipped - No API Gateway URL configured")
                
        except Exception as e:
            self.log_test("HTTP Integration", False, str(e))
    
    def test_api_gateway_grpc_integration(self):
        """API Gateway gRPC統合テスト"""
        try:
            # API Gateway gRPCエンドポイントテスト
            if self.api_gateway_url and self.api_gateway_url != 'http://localhost:3000':
                try:
                    grpc_url = self.api_gateway_url + '/grpc'
                    
                    # gRPC Device list endpoint
                    response = requests.get(f"{grpc_url}/devices", timeout=10)
                    success = response.status_code == 200
                    self.log_test("API Gateway gRPC - Device List", success, f"Status: {response.status_code}")
                    
                    # gRPC Device status endpoint
                    response = requests.get(f"{grpc_url}/device/HPLC-01", timeout=10)
                    success = response.status_code == 200
                    self.log_test("API Gateway gRPC - Device Status", success, f"Status: {response.status_code}")
                    
                    # gRPC Device operation endpoint
                    response = requests.post(f"{grpc_url}/device/HPLC-01", 
                                           json={"operation": "start_analysis", "parameters": {"method": "test"}}, 
                                           timeout=10)
                    success = response.status_code == 200
                    self.log_test("API Gateway gRPC - Device Operation", success, f"Status: {response.status_code}")
                    
                except requests.RequestException as e:
                    self.log_test("API Gateway gRPC Integration", False, f"Request error: {e}")
            else:
                self.log_test("API Gateway gRPC Integration", True, "Skipped - No API Gateway URL configured")
                
        except Exception as e:
            self.log_test("API Gateway gRPC Integration", False, str(e))
    
    def test_lambda_grpc_handler(self):
        """Lambda gRPC Handler テスト"""
        try:
            from lambda_grpc_device_handler import LambdaGRPCDeviceHandler
            
            handler = LambdaGRPCDeviceHandler()
            
            # Device list test
            result = handler.handle_list_devices()
            success = result.get('success', False) and len(result.get('devices', [])) > 0
            source = result.get('source', 'unknown')
            self.log_test("Lambda gRPC Handler - Device List", success, f"Source: {source}, Count: {result.get('count', 0)}")
            
            # Device info test
            result = handler.handle_get_device_info("HPLC-01")
            success = result.get('success', False)
            source = result.get('source', 'unknown')
            self.log_test("Lambda gRPC Handler - Device Info", success, f"Source: {source}, Device: HPLC-01")
            
            # Command execution test
            result = handler.handle_execute_command("HPLC-01", "start_analysis", {"method": "test"})
            success = result.get('success', False)
            source = result.get('source', 'unknown')
            self.log_test("Lambda gRPC Handler - Command Execution", success, f"Source: {source}, Operation: start_analysis")
            
        except Exception as e:
            self.log_test("Lambda gRPC Handler", False, str(e))
    
    def test_sila2_client_basic(self):
        """SiLA2 Client Basic テスト"""
        try:
            from sila2_client import SiLA2Client
            
            client = SiLA2Client()
            
            # Device discovery test
            devices = client.discover_devices()
            success = len(devices) > 0
            self.log_test("SiLA2 Client - Device Discovery", success, f"Found {len(devices)} devices")
            
            # Device connection test
            if devices:
                device_id = devices[0]['id']
                connected = client.connect_device(device_id)
                self.log_test("SiLA2 Client - Device Connection", connected, f"Device: {device_id}")
            
        except Exception as e:
            self.log_test("SiLA2 Client Basic", False, str(e))
    
    def test_grpc_server(self):
        """gRPC Server テスト"""
        try:
            from grpc_mock_device_server import start_grpc_server_background
            from grpc_test_client import SiLA2GRPCClient
            import time
            
            # Start gRPC server in background
            server_manager = start_grpc_server_background(50051)
            time.sleep(1)  # Wait for server to start
            
            # Test gRPC client
            client = SiLA2GRPCClient("localhost:50051")
            if client.connect():
                # Test device list
                result = client.list_devices()
                success = result.get('success', False) and len(result.get('devices', [])) > 0
                self.log_test("gRPC Server - Device List", success, f"Found {result.get('count', 0)} devices")
                
                if success and result.get('devices'):
                    device_id = result['devices'][0]['device_id']
                    
                    # Test device info
                    result = client.get_device_info(device_id)
                    success = result.get('success', False)
                    self.log_test("gRPC Server - Device Info", success, f"Device: {device_id}")
                    
                    # Test command execution
                    result = client.execute_command(device_id, "start_analysis", {"method": "test"})
                    success = result.get('success', False)
                    self.log_test("gRPC Server - Command Execution", success, f"Operation: start_analysis")
                
                client.disconnect()
            else:
                self.log_test("gRPC Server", False, "Failed to connect to gRPC server")
            
            # Stop server
            server_manager.stop()
            
        except Exception as e:
            self.log_test("gRPC Server", False, str(e))
    
    def test_protocol_bridge_grpc(self):
        """Protocol Bridge with gRPC テスト"""
        try:
            from protocol_bridge_lambda_grpc import ProtocolBridgeLambdaGRPC
            
            bridge = ProtocolBridgeLambdaGRPC()
            
            # Device list test
            result = bridge.handle_device_list()
            success = result.get('success', False) and len(result.get('devices', [])) > 0
            source = result.get('source', 'unknown')
            self.log_test("Protocol Bridge gRPC - Device List", success, f"Source: {source}, Count: {result.get('count', 0)}")
            
            # Device request test
            result = bridge.handle_device_request("HPLC-01", "GET")
            success = result.get('success', False)
            self.log_test("Protocol Bridge gRPC - Device Request", success, f"Device: HPLC-01")
            
        except Exception as e:
            self.log_test("Protocol Bridge gRPC", False, str(e))
    
    def test_integration_enhanced(self):
        """Enhanced integration test"""
        try:
            # Simulate end-to-end flow: AgentCore Runtime → Gateway → Protocol Bridge → Mock Devices
            from gateway.sila2_gateway_tools_simplified import SiLA2GatewayToolsSimplified
            from protocol_bridge_lambda_grpc import ProtocolBridgeLambdaGRPC
            from gateway.mock_device_lambda_enhanced import MockDeviceLambdaEnhanced
            
            # Initialize components
            gateway = SiLA2GatewayToolsSimplified()
            bridge = ProtocolBridgeLambdaGRPC()
            mock_device = MockDeviceLambdaEnhanced()
            
            # Test flow: Gateway → Protocol Bridge → Mock Device
            devices_result = gateway.list_available_devices()
            if devices_result.get('success') and devices_result.get('devices'):
                device_id = devices_result['devices'][0]['device_id']
                
                # Protocol Bridge device list
                bridge_devices = bridge.handle_device_list()
                bridge_success = bridge_devices.get('success', False)
                bridge_source = bridge_devices.get('source', 'unknown')
                
                # Protocol Bridge device request
                bridge_request = bridge.handle_device_request(device_id, "GET")
                request_success = bridge_request.get('success', False)
                
                # Mock Device direct test
                mock_status = mock_device.handle_device_status(device_id)
                mock_success = mock_status.get('success', False)
                
                overall_success = bridge_success and request_success and mock_success
                self.log_test("Integration - Enhanced End-to-End with gRPC", overall_success, 
                            f"Bridge: {bridge_success} ({bridge_source}), Request: {request_success}, Mock: {mock_success}")
            else:
                self.log_test("Integration - Enhanced End-to-End with gRPC", False, "No devices available")
                
        except Exception as e:
            self.log_test("Integration Enhanced with gRPC", False, str(e))
    
    def run_all_tests(self):
        """All tests execution"""
        print("=== Phase 3 Enhanced Test Suite ===")
        print(f"Start time: {datetime.now().isoformat()}")
        print(f"API Gateway URL: {self.api_gateway_url}")
        print()
        
        # Component tests
        self.test_gateway_tools_simplified()
        self.test_protocol_bridge()
        self.test_mock_device_enhanced()
        self.test_http_integration()
        self.test_sila2_client_basic()
        
        # gRPC tests
        self.test_grpc_server()
        self.test_protocol_bridge_grpc()
        self.test_api_gateway_grpc_integration()
        self.test_lambda_grpc_handler()
        self.test_integration_enhanced()
        
        # Results summary
        print()
        print("=== Test Results Summary ===")
        passed = sum(1 for r in self.test_results if r['status'] == 'PASS')
        failed = sum(1 for r in self.test_results if r['status'] == 'FAIL')
        total = len(self.test_results)
        
        print(f"Total: {total}, Passed: {passed}, Failed: {failed}")
        print(f"Success Rate: {(passed/total*100):.1f}%" if total > 0 else "No tests run")
        
        if failed > 0:
            print("\nFailed Tests:")
            for result in self.test_results:
                if result['status'] == 'FAIL':
                    print(f"  - {result['test']}: {result['message']}")
        
        return passed, failed

if __name__ == "__main__":
    test_suite = TestPhase3()
    passed, failed = test_suite.run_all_tests()
    
    # Save test results
    results_file = "phase3_test_results.json"
    try:
        with open(results_file, 'w') as f:
            json.dump({
                "summary": {"passed": passed, "failed": failed, "total": passed + failed},
                "results": test_suite.test_results,
                "timestamp": datetime.now().isoformat()
            }, f, indent=2)
        print(f"\nTest results saved to: {results_file}")
    except Exception as e:
        print(f"Failed to save test results: {e}")
    
    # Exit with appropriate code
    exit_code = 0 if failed == 0 else 1
    print(f"\nExiting with code: {exit_code}")
    sys.exit(exit_code)