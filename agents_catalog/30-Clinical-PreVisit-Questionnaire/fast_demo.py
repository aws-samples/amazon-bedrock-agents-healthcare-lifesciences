#!/usr/bin/env python3
"""
Fast UCLA Health Pre-Visit Questionnaire Demo
Optimized for speed and low latency
"""

import sys
import os
import time
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.agents.pvq_agent_fast import FastPVQAgent

def speed_test():
    """Test response speed"""
    print("⚡ FAST PVQ AGENT - SPEED TEST")
    print("=" * 40)
    
    agent = FastPVQAgent()
    
    test_inputs = [
        "My name is John Smith",
        "I live at 123 Main St, LA, CA 90210",
        "My phone is 555-123-4567", 
        "I was born 01/15/1980",
        "I'm male",
        "I have diabetes",
        "I take Metformin",
        "status"
    ]
    
    total_time = 0
    
    for i, msg in enumerate(test_inputs, 1):
        start_time = time.time()
        response = agent.chat(msg)
        end_time = time.time()
        
        response_time = end_time - start_time
        total_time += response_time
        
        print(f"[{i}] {msg}")
        print(f"    🤖 {response}")
        print(f"    ⏱️  {response_time:.2f}s")
        print()
    
    avg_time = total_time / len(test_inputs)
    print(f"📊 PERFORMANCE SUMMARY:")
    print(f"   Total time: {total_time:.2f}s")
    print(f"   Average response: {avg_time:.2f}s")
    print(f"   Responses/minute: {60/avg_time:.1f}")

def interactive_fast():
    """Fast interactive mode"""
    print("⚡ FAST INTERACTIVE MODE")
    print("Type 'quit' to exit, 'status' for progress")
    print("-" * 40)
    
    agent = FastPVQAgent()
    
    while True:
        try:
            user_input = input("\n💬 You: ").strip()
            if not user_input:
                continue
                
            start_time = time.time()
            response = agent.chat(user_input)
            response_time = time.time() - start_time
            
            print(f"🤖 Agent: {response}")
            print(f"⏱️  Response time: {response_time:.2f}s")
            
            if "Saved to" in response:
                break
                
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break

def main():
    """Main function"""
    print("Choose mode:")
    print("1. Speed Test")
    print("2. Interactive Fast Mode")
    
    choice = input("\nEnter choice (1 or 2): ").strip()
    
    if choice == '1':
        speed_test()
    elif choice == '2':
        interactive_fast()
    else:
        print("Running speed test...")
        speed_test()

if __name__ == "__main__":
    main()