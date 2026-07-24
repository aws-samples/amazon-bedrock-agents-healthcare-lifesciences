#!/usr/bin/env python3
"""
Speed Comparison: Regular vs Fast vs Ultra-Fast PVQ Agents
"""

import sys
import os
import time
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.agents.pvq_agent import PVQStrandsAgent
from src.agents.pvq_agent_fast import FastPVQAgent
from src.agents.pvq_agent_ultra_fast import UltraFastPVQAgent

def benchmark_agent(agent, agent_name, test_inputs):
    """Benchmark an agent with test inputs"""
    print(f"\n🧪 Testing {agent_name}")
    print("-" * 30)
    
    times = []
    
    for i, msg in enumerate(test_inputs, 1):
        start = time.time()
        response = agent.chat(msg)
        end = time.time()
        
        response_time = end - start
        times.append(response_time)
        
        print(f"[{i}] {msg[:30]}...")
        print(f"    ⏱️  {response_time:.3f}s")
    
    avg_time = sum(times) / len(times)
    total_time = sum(times)
    
    print(f"\n📊 {agent_name} Results:")
    print(f"   Average: {avg_time:.3f}s")
    print(f"   Total: {total_time:.3f}s")
    print(f"   Fastest: {min(times):.3f}s")
    print(f"   Slowest: {max(times):.3f}s")
    
    return avg_time, total_time

def run_comparison():
    """Run speed comparison between all agents"""
    print("⚡ PVQ AGENT SPEED COMPARISON")
    print("=" * 50)
    
    # Test inputs
    test_inputs = [
        "My name is Sarah Johnson",
        "I live at 456 Oak Street, Santa Monica, CA",
        "My phone is 310-555-0123",
        "I was born on April 15, 1975",
        "I'm female",
        "I have high blood pressure and diabetes",
        "I take Lisinopril and Metformin",
        "status"
    ]
    
    # Initialize agents
    agents = [
        (PVQStrandsAgent(), "Regular Agent (Claude Sonnet)"),
        (FastPVQAgent(), "Fast Agent (Claude Haiku)"),
        (UltraFastPVQAgent(), "Ultra-Fast Agent (Rule-based)")
    ]
    
    results = []
    
    # Benchmark each agent
    for agent, name in agents:
        try:
            avg_time, total_time = benchmark_agent(agent, name, test_inputs)
            results.append((name, avg_time, total_time))
        except Exception as e:
            print(f"❌ {name} failed: {e}")
            results.append((name, float('inf'), float('inf')))
    
    # Summary comparison
    print("\n🏆 SPEED COMPARISON SUMMARY")
    print("=" * 50)
    
    # Sort by average response time
    results.sort(key=lambda x: x[1])
    
    for i, (name, avg_time, total_time) in enumerate(results, 1):
        if avg_time == float('inf'):
            print(f"{i}. {name}: FAILED")
        else:
            speedup = results[-1][1] / avg_time if avg_time > 0 else 0
            print(f"{i}. {name}")
            print(f"   Average: {avg_time:.3f}s")
            print(f"   Speedup: {speedup:.1f}x faster than slowest")
            print(f"   Throughput: {60/avg_time:.1f} responses/minute")
    
    # Recommendations
    print(f"\n💡 RECOMMENDATIONS:")
    print(f"   🚀 Fastest: {results[0][0]}")
    print(f"   ⚖️  Balanced: {results[1][0] if len(results) > 1 else 'N/A'}")
    print(f"   🎯 Most Accurate: Regular Agent (slowest but most comprehensive)")

def interactive_comparison():
    """Interactive comparison mode"""
    print("\n🎮 INTERACTIVE COMPARISON MODE")
    print("Type the same message to all agents and compare speeds")
    print("Type 'quit' to exit")
    print("-" * 50)
    
    agents = [
        (PVQStrandsAgent(), "Regular"),
        (FastPVQAgent(), "Fast"), 
        (UltraFastPVQAgent(), "Ultra-Fast")
    ]
    
    while True:
        try:
            user_input = input("\n💬 Enter message: ").strip()
            if not user_input or user_input.lower() == 'quit':
                break
            
            print(f"\n📤 Testing: '{user_input}'")
            
            for agent, name in agents:
                try:
                    start = time.time()
                    response = agent.chat(user_input)
                    end = time.time()
                    
                    print(f"\n{name} ({end-start:.3f}s):")
                    print(f"   {response[:100]}...")
                except Exception as e:
                    print(f"\n{name}: ❌ Error - {e}")
        
        except KeyboardInterrupt:
            break
    
    print("\n👋 Comparison complete!")

def main():
    """Main function"""
    print("Choose comparison mode:")
    print("1. Automated Benchmark")
    print("2. Interactive Comparison")
    
    choice = input("\nEnter choice (1 or 2): ").strip()
    
    if choice == '1':
        run_comparison()
    elif choice == '2':
        interactive_comparison()
    else:
        print("Running automated benchmark...")
        run_comparison()

if __name__ == "__main__":
    main()