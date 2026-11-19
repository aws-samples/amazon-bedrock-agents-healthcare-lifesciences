#!/usr/bin/env python3
"""
Test suite for PVQ Strands Agent
"""

import sys
import os
from pathlib import Path

# Add project root and src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'src'))

try:
    from src.agents.pvq_agent import PVQStrandsAgent
    from src.models.patient_data import PVQData
    from src.utils.validators import validate_phone, validate_date
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("💡 Make sure you're running from the project root directory")
    print("💡 Make sure strands is installed: pip install strands")
    sys.exit(1)

def test_data_model():
    """Test PVQData model"""
    print("🧪 Testing PVQData model...")
    
    data = PVQData()
    assert data.patient_name == ""
    assert isinstance(data.current_medications, list)
    assert len(data.current_medications) == 0
    
    # Test completion status
    status = data.get_completion_status()
    assert not status['basic_info']
    assert not status['has_medical_history']
    
    print("✅ PVQData model tests passed")

def test_validators():
    """Test validation functions"""
    print("🧪 Testing validators...")
    
    # Phone validation
    assert validate_phone("555-123-4567")
    assert validate_phone("(555) 123-4567")
    assert validate_phone("5551234567")
    assert not validate_phone("123")
    assert not validate_phone("")
    
    # Date validation
    assert validate_date("01/15/1990")
    assert validate_date("12/31/2000")
    assert not validate_date("13/01/1990")  # Invalid month
    assert not validate_date("01/32/1990")  # Invalid day
    assert not validate_date("invalid")
    
    print("✅ Validator tests passed")

def test_agent_basic():
    """Test basic agent functionality"""
    print("🧪 Testing PVQ agent...")
    
    try:
        agent = PVQStrandsAgent()
        print("   ✅ Agent initialized")

        
        # Test basic info saving through tools
        response = agent.basic_info.save_basic_info("name", "John Smith")
        print(f"   Basic info response: {response}")
        assert "✅" in response
        assert agent.pvq_data.patient_name == "John Smith"
        print("   ✅ Basic info test passed")
        
        # Test medical condition saving through tools
        response = agent.medical_history.save_medical_condition("heart", "High blood pressure", "2020")
        print(f"   Medical condition response: {response}")
        assert "✅" in response
        assert len(agent.pvq_data.heart_conditions) == 1
        print("   ✅ Medical condition test passed")
        
        # Test medication saving through tools
        response = agent.medications.save_medication("Lisinopril", "10mg", "once daily")
        print(f"   Medication response: {response}")
        assert "✅" in response
        assert len(agent.pvq_data.current_medications) == 1
        print("   ✅ Medication test passed")
        
        # Test progress check through utilities
        progress = agent.utilities.get_progress()
        print(f"   Progress response: {progress}")
        assert "Progress:" in progress
        print("   ✅ Progress test passed")
        
        print("✅ Agent basic tests passed")
        
    except Exception as e:
        print(f"   ❌ Agent test failed: {e}")
        import traceback
        traceback.print_exc()
        raise

def test_agent_conversation():
    """Test agent conversation flow"""
    print("🧪 Testing agent conversation...")
    
    agent = PVQStrandsAgent()
    
    # Test conversation responses
    response = agent.chat("My name is Jane Doe")
    assert isinstance(response, str)
    assert len(response) > 0
    
    response = agent.chat("progress")
    assert "Progress:" in response
    
    print("✅ Agent conversation tests passed")

def run_all_tests():
    """Run all tests"""
    print("🧪 Running UCLA Health PVQ Agent Tests")
    print("=" * 50)
    
    try:
        test_data_model()
        test_validators()
        test_agent_basic()
        test_agent_conversation()
        
        print("\n🎉 All tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)