#!/usr/bin/env python3
"""
UCLA Health Pre-Visit Questionnaire - Main Application
Complete workflow with Strands agent and PDF generation
"""

import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.agents.pvq_agent import PVQStrandsAgent
from src.utils.pdf_generator import generate_pdf_from_json

def main():
    """Run the complete PVQ workflow"""
    print("🏥 UCLA Health Pre-Visit Questionnaire")
    print("📋 Powered by Amazon Strands")
    print("=" * 50)
    
    print("\nI'll help you complete your pre-visit questionnaire.")
    print("After completion, I can generate a filled PDF form.")
    print("\nCommands:")
    print("• 'progress' - check completion status")
    print("• 'categories' - show medical condition categories")
    print("• 'quit' - save and exit")
    print("• 'pdf' - generate PDF from current data")
    print("\nLet's begin...")
    
    # Initialize agent
    agent = PVQStrandsAgent()
    json_filename = None
    
    # Start conversation
    response = agent.chat("Hello, I need to complete my UCLA Health pre-visit questionnaire.")
    print(f"\n🤖 Assistant: {response}")
    
    # Main conversation loop
    while True:
        try:
            user_input = input("\n💬 You: ").strip()
            if not user_input:
                continue
            
            # Handle PDF generation
            if user_input.lower() == 'pdf':
                if not json_filename:
                    # Save current data first
                    save_response = agent.save_to_file()
                    print(f"\n🤖 Assistant: {save_response}")
                    
                    # Extract filename
                    if "Saved to" in save_response:
                        json_filename = save_response.split("Saved to ")[1]
                
                if json_filename and os.path.exists(json_filename):
                    try:
                        pdf_file = generate_pdf_from_json(json_filename)
                        print(f"\n📄 PDF generated: {pdf_file}")
                    except Exception as e:
                        print(f"\n❌ PDF generation failed: {e}")
                else:
                    print("\n❌ No data file found. Complete more of the questionnaire first.")
                continue
            
            # Process through agent
            response = agent.chat(user_input)
            print(f"\n🤖 Assistant: {response}")
            
            # Track saved files
            if "Saved to" in response and not json_filename:
                json_filename = response.split("Saved to ")[1].split()[0]
            
            # Exit condition
            if "Thank you" in response and "saved" in response.lower():
                break
                
        except KeyboardInterrupt:
            print("\n\n💾 Saving progress...")
            save_response = agent.save_to_file()
            print(save_response)
            
            # Offer PDF generation
            if "Saved to" in save_response:
                json_filename = save_response.split("Saved to ")[1]
                try:
                    generate_pdf = input("\nGenerate PDF? (y/n): ").lower().startswith('y')
                    if generate_pdf:
                        pdf_file = generate_pdf_from_json(json_filename)
                        print(f"📄 PDF generated: {pdf_file}")
                except Exception as e:
                    print(f"PDF generation error: {e}")
            
            print("👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
    
    # Final summary
    if json_filename and os.path.exists(json_filename):
        print(f"\n📋 Data saved: {json_filename}")
        print("💡 Generate PDF anytime with:")
        print(f"   python -c \"from src.utils.pdf_generator import generate_pdf_from_json; generate_pdf_from_json('{json_filename}')\"")

if __name__ == "__main__":
    main()