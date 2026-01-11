#!/usr/bin/env python3
"""Phase 4 Integration Tests - AgentCore + ECS"""
import subprocess
import sys
import os

def run_agentcore_test(query: str, expected_keywords: list) -> bool:
    """Run AgentCore invoke and check for expected keywords"""
    try:
        # Find agentcore executable
        import glob
        agentcore_paths = glob.glob(os.path.expanduser("~/.pyenv/versions/3.10.*/bin/agentcore"))
        if not agentcore_paths:
            agentcore_path = "agentcore"  # Try system path
        else:
            agentcore_path = agentcore_paths[0]
        
        result = subprocess.run(
            [agentcore_path, "invoke", query],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            print(f"❌ AgentCore invoke failed: {result.stderr}")
            return False
        
        output = result.stdout.lower()
        for keyword in expected_keywords:
            if keyword.lower() not in output:
                print(f"❌ Expected keyword '{keyword}' not found in output")
                return False
        
        return True
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def main():
    print("=== Phase 4 Integration Tests ===\n")
    
    tests = [
        {
            "name": "List Devices",
            "query": "List all available SiLA2 devices",
            "keywords": ["hplc", "centrifuge", "pipette"]
        },
        {
            "name": "Device Status",
            "query": "Get status of hplc device",
            "keywords": ["hplc", "status", "ready"]
        },
        {
            "name": "Start Task",
            "query": "Start a temperature control task on hplc to 25 degrees",
            "keywords": ["task", "started", "hplc"]
        }
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        print(f"Running: {test['name']}...")
        if run_agentcore_test(test['query'], test['keywords']):
            print(f"✅ {test['name']}: PASSED\n")
            passed += 1
        else:
            print(f"❌ {test['name']}: FAILED\n")
            failed += 1
    
    print(f"\n=== Test Results ===")
    print(f"Passed: {passed}/{len(tests)}")
    print(f"Failed: {failed}/{len(tests)}")
    
    if failed == 0:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n❌ {failed} test(s) failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
