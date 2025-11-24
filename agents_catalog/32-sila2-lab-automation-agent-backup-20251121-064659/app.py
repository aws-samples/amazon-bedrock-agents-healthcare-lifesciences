#!/usr/bin/env python3
"""
AgentCore Runtime Entry Point for SiLA2 Lab Automation Agent
"""
import json
import os
import sys
from typing import Dict, Any

# SiLA2エージェントをインポート
from main_agentcore_phase3 import SiLA2AgentPhase3

def main():
    """AgentCore Runtime main entry point"""
    print("Starting SiLA2 Lab Automation Agent Runtime...")
    
    # 環境変数の確認
    print(f"Environment: {os.environ.get('ENVIRONMENT', 'dev')}")
    print(f"Phase: {os.environ.get('PHASE', '3')}")
    print(f"API Gateway URL: {os.environ.get('API_GATEWAY_URL', 'Not set')}")
    
    # エージェントインスタンス作成
    agent = SiLA2AgentPhase3()
    
    # ヘルスチェック
    try:
        devices = agent.list_devices()
        print(f"Agent initialized successfully. Found {devices['total_count']} devices.")
        return True
    except Exception as e:
        print(f"Agent initialization failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)