#!/usr/bin/env python3
"""
UCLA Health Pre-Visit Questionnaire - Capabilities Demo
Demonstrates all agent features and tools
"""

from src.agents.pvq_agent import PVQStrandsAgent

def demo_basic_info(agent):
    print("🔹 BASIC INFORMATION")
    responses = [
        agent.basic_info.save_basic_info("name", "John Smith"),
        agent.basic_info.save_basic_info("address", "123 Main St, Los Angeles, CA 90210"),
        agent.basic_info.save_basic_info("phone", "(555) 123-4567"),
        agent.basic_info.save_basic_info("dob", "01/15/1980"),
        agent.basic_info.save_basic_info("sex", "Male")
    ]
    for r in responses: print(f"  {r}")

def demo_medical_history(agent):
    print("\n🔹 MEDICAL HISTORY")
    responses = [
        agent.medical_history.save_medical_condition("heart", "High blood pressure", "2020"),
        agent.medical_history.save_medical_condition("lung", "Asthma", "2015"),
        agent.medical_history.save_surgery("Appendectomy", "2018"),
        agent.medical_history.save_hospitalization("Pneumonia", "2022")
    ]
    for r in responses: print(f"  {r}")

def demo_medications(agent):
    print("\n🔹 MEDICATIONS & ALLERGIES")
    responses = [
        agent.medications.save_medication("Lisinopril", "10mg", "once daily"),
        agent.medications.save_medication("Albuterol", "90mcg", "as needed"),
        agent.medications.save_allergy("Penicillin", "Rash")
    ]
    for r in responses: print(f"  {r}")

def demo_social_history(agent):
    print("\n🔹 SOCIAL HISTORY")
    responses = [
        agent.social_history.save_social_history("marital", "Married"),
        agent.social_history.save_social_history("education", "College graduate"),
        agent.social_history.save_family_history("Diabetes", "Father"),
        agent.social_history.save_family_history("Heart disease", "Mother")
    ]
    for r in responses: print(f"  {r}")

def demo_health_maintenance(agent):
    print("\n🔹 HEALTH MAINTENANCE")
    responses = [
        agent.health_maintenance.save_healthcare_planning("rating", "Good"),
        agent.health_maintenance.save_health_maintenance("seatbelt", "Yes"),
        agent.health_maintenance.save_health_maintenance("exercise", "Walking 30min daily")
    ]
    for r in responses: print(f"  {r}")

def demo_symptoms(agent):
    print("\n🔹 SYMPTOMS & CONCERNS")
    responses = [
        agent.symptoms.save_recent_symptom("Occasional shortness of breath"),
        agent.symptoms.save_health_concern("Want to discuss blood pressure management")
    ]
    for r in responses: print(f"  {r}")

def demo_utilities(agent):
    print("\n🔹 UTILITIES")
    print("Progress Check:")
    print(agent.utilities.get_progress())
    
    print("\nMedical Categories:")
    print(agent.utilities.get_medical_categories())
    
    print("\nSaving to file:")
    print(agent.utilities.save_to_file())

def demo_chat_interface(agent):
    print("\n🔹 CHAT INTERFACE DEMO")
    
    # Simulate conversation
    messages = [
        "Hello, I need to complete my questionnaire",
        "My name is Jane Doe",
        "I live at 456 Oak Ave, Beverly Hills, CA 90210",
        "My phone is (555) 987-6543",
        "I was born on March 22, 1975",
        "I'm female",
        "I have diabetes since 2010",
        "I take Metformin 500mg twice daily",
        "progress",
        "done"
    ]
    
    for msg in messages:
        print(f"\n💬 User: {msg}")
        response = agent.chat(msg)
        print(f"🤖 Agent: {response}")

def main():
    print("🏥 UCLA HEALTH PRE-VISIT QUESTIONNAIRE")
    print("📋 Capabilities Demonstration")
    print("=" * 50)
    
    # Initialize agent
    agent = PVQStrandsAgent()
    
    # Demo all tool categories
    demo_basic_info(agent)
    demo_medical_history(agent)
    demo_medications(agent)
    demo_social_history(agent)
    demo_health_maintenance(agent)
    demo_symptoms(agent)
    demo_utilities(agent)
    
    print("\n" + "=" * 50)
    
    # Demo conversational interface
    demo_chat_interface(agent)
    
    print("\n✅ Demo completed successfully!")
    print("📄 Check data/ folder for saved questionnaire files")

if __name__ == "__main__":
    main()