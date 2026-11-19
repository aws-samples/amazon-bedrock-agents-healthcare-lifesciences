#!/usr/bin/env python3
"""
Interactive UCLA Health Pre-Visit Questionnaire Demo
Allows real-time interaction with the agent
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.agents.pvq_agent import PVQStrandsAgent

def print_header():
    """Print demo header"""
    print("\n🏥 UCLA HEALTH PRE-VISIT QUESTIONNAIRE")
    print("🤖 Interactive Agent Demo")
    print("=" * 50)
    print("Commands:")
    print("  'progress' - Check completion status")
    print("  'categories' - Show medical categories")
    print("  'help' - Show this help")
    print("  'quit' - Save and exit")
    print("=" * 50)

def print_help():
    """Print help information"""
    print("\n📋 QUESTIONNAIRE SECTIONS:")
    print("1. Basic Info: name, address, phone, DOB, sex")
    print("2. Medical History: conditions, surgeries, hospitalizations")
    print("3. Medications: current medications and dosages")
    print("4. Allergies: drug allergies and reactions")
    print("5. Social History: living situation, family, lifestyle")
    print("6. Family History: family medical conditions")
    print("7. Recent Symptoms: symptoms in last 3 months")
    print("8. Health Concerns: specific concerns to discuss")
    print("9. Health Maintenance: exercise, screenings, etc.")
    print("\n💡 Example inputs:")
    print("  'My name is John Smith'")
    print("  'I have high blood pressure'")
    print("  'I take Lisinopril 10mg daily'")
    print("  'I'm allergic to penicillin'")

def run_interactive_demo():
    """Run interactive questionnaire demo"""
    
    print_header()
    
    # Initialize agent
    agent = PVQStrandsAgent()
    
    # Start conversation
    print("\n🤖 Hello! I'm here to help you complete your UCLA Health pre-visit questionnaire.")
    print("🤖 Let's start with your basic information. What is your full name?")
    
    while True:
        try:
            # Get user input
            user_input = input("\n💬 You: ").strip()
            
            if not user_input:
                continue
                
            # Handle special commands
            if user_input.lower() == 'help':
                print_help()
                continue
            elif user_input.lower() in ['exit', 'quit', 'done']:
                print("\n🤖 Saving your questionnaire...")
                response = agent.chat('done')
                print(f"🤖 {response}")
                break
            
            # Process through agent
            response = agent.chat(user_input)
            print(f"🤖 {response}")
            
        except KeyboardInterrupt:
            print("\n\n👋 Demo interrupted. Saving data...")
            agent.utilities.save_to_file()
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            print("💡 Type 'help' for guidance or 'quit' to exit")

def quick_demo():
    """Run a quick pre-filled demo"""
    print("\n🚀 QUICK DEMO MODE")
    print("Simulating rapid questionnaire completion...")
    
    agent = PVQStrandsAgent()
    
    # Quick responses
    responses = [
        "My name is Sarah Johnson",
        "I live at 123 Oak Street, Santa Monica, CA 90401", 
        "My phone is (310) 555-0199",
        "I was born on April 3, 1978",
        "I'm female",
        "I have high blood pressure and diabetes",
        "I take Metformin and Lisinopril",
        "I'm allergic to sulfa drugs",
        "My father had heart disease",
        "I've been having headaches lately",
        "progress"
    ]
    
    for i, response in enumerate(responses, 1):
        print(f"\n[{i:2d}] 💬 {response}")
        agent_response = agent.chat(response)
        print(f"     🤖 {agent_response}")
    
    print("\n✅ Quick demo completed!")

def main():
    """Main function with mode selection"""
    print("Select demo mode:")
    print("1. Interactive Demo (you type responses)")
    print("2. Quick Demo (pre-filled responses)")
    
    try:
        choice = input("\nEnter choice (1 or 2): ").strip()
        
        if choice == '1':
            run_interactive_demo()
        elif choice == '2':
            quick_demo()
        else:
            print("Invalid choice. Running interactive demo...")
            run_interactive_demo()
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()