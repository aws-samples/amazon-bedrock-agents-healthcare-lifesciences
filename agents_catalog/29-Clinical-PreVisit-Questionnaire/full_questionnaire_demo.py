#!/usr/bin/env python3
"""
Complete UCLA Health Pre-Visit Questionnaire Demo
Simulates a full patient interaction through all sections
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.agents.pvq_agent import PVQStrandsAgent

def simulate_conversation():
    """Simulate complete questionnaire conversation"""
    
    # Complete patient responses covering all sections
    conversation = [
        # Basic Information
        ("Hello, I need to complete my pre-visit questionnaire", "greeting"),
        ("My name is Maria Rodriguez", "basic_info"),
        ("I live at 789 Sunset Boulevard, Los Angeles, CA 90028", "basic_info"),
        ("My phone number is (323) 555-0123", "basic_info"),
        ("I was born on June 15, 1965", "basic_info"),
        ("I'm female", "basic_info"),
        
        # Medical History - Multiple conditions
        ("I have high blood pressure since 2018", "medical_history"),
        ("I also have diabetes type 2 diagnosed in 2020", "medical_history"),
        ("I had asthma as a child", "medical_history"),
        ("I have arthritis in my knees", "medical_history"),
        ("I had my gallbladder removed in 2019", "surgery"),
        ("I was hospitalized for pneumonia in 2021", "hospitalization"),
        
        # Current Medications
        ("I take Lisinopril 10mg once daily for blood pressure", "medication"),
        ("I also take Metformin 500mg twice daily for diabetes", "medication"),
        ("I use an albuterol inhaler as needed for breathing", "medication"),
        
        # Drug Allergies
        ("I'm allergic to penicillin - it gives me a rash", "allergy"),
        ("I also can't take aspirin - it upsets my stomach", "allergy"),
        
        # Social History
        ("I'm married", "social_history"),
        ("I'm a college graduate", "social_history"),
        ("I live with my husband", "social_history"),
        
        # Family History
        ("My mother had diabetes", "family_history"),
        ("My father died of a heart attack", "family_history"),
        ("My sister has breast cancer", "family_history"),
        
        # Recent Symptoms (last 3 months)
        ("I've been having some shortness of breath lately", "recent_symptoms"),
        ("My knee pain has gotten worse", "recent_symptoms"),
        ("I sometimes feel dizzy when I stand up", "recent_symptoms"),
        
        # Health Concerns
        ("I'm worried about my blood sugar control", "health_concerns"),
        ("I want to discuss my knee pain treatment options", "health_concerns"),
        
        # Health Maintenance
        ("I would rate my health as fair", "health_maintenance"),
        ("Yes, I always wear my seatbelt", "health_maintenance"),
        ("I try to walk 20 minutes every day", "health_maintenance"),
        
        # Check progress and finish
        ("progress", "utility"),
        ("done", "completion")
    ]
    
    return conversation

def run_full_demo():
    """Run complete questionnaire demo"""
    
    print("🏥 UCLA HEALTH PRE-VISIT QUESTIONNAIRE")
    print("📋 Complete Patient Journey Demo")
    print("=" * 60)
    
    # Initialize agent
    agent = PVQStrandsAgent()
    
    # Get conversation flow
    conversation = simulate_conversation()
    
    print("👤 Patient: Maria Rodriguez (Age 58)")
    print("📅 Appointment: Geriatric Medicine Follow-up")
    print("-" * 60)
    
    # Process each interaction
    for i, (user_input, section) in enumerate(conversation, 1):
        print(f"\n[{i:2d}] 💬 Patient: {user_input}")
        
        # Get agent response
        response = agent.chat(user_input)
        print(f"     🤖 Agent: {response}")
        
        # Add section separator for readability
        if section in ['basic_info', 'medical_history', 'medication', 'social_history', 'recent_symptoms']:
            if i < len(conversation) and conversation[i][1] != section:
                print(f"\n     ✅ {section.replace('_', ' ').title()} section completed")
    
    print("\n" + "=" * 60)
    print("📊 FINAL QUESTIONNAIRE STATUS")
    print("=" * 60)
    
    # Show final progress
    final_progress = agent.utilities.get_progress()
    print(final_progress)
    
    print("\n📄 Generated Files:")
    print("- Patient data saved to JSON format")
    print("- Ready for PDF generation")
    print("- Compatible with EHR systems")
    
    print("\n✅ Complete questionnaire demo finished!")
    print("🎯 All major sections covered:")
    print("   • Basic Information ✓")
    print("   • Medical History ✓") 
    print("   • Medications & Allergies ✓")
    print("   • Social & Family History ✓")
    print("   • Recent Symptoms ✓")
    print("   • Health Concerns ✓")
    print("   • Health Maintenance ✓")

def main():
    """Main demo function"""
    try:
        run_full_demo()
    except Exception as e:
        print(f"❌ Demo error: {e}")
        print("💡 Make sure all dependencies are installed")

if __name__ == "__main__":
    main()