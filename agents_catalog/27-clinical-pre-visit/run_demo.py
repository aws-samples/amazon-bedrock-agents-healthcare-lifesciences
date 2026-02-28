#!/usr/bin/env python3
"""
UCLA Health PVQ Demo Runner
Quick access to all demo modes
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def run_demo():
    """Main demo selector"""
    print("🏥 UCLA HEALTH PVQ DEMO SELECTOR")
    print("=" * 40)
    print("1. Full Questionnaire Demo")
    print("2. Interactive Demo") 
    print("3. Fast Agent Demo")
    print("4. Speed Comparison")
    print("5. Capabilities Demo")
    
    choice = input("\nSelect demo (1-5): ").strip()
    
    try:
        if choice == '1':
            from full_questionnaire_demo import main
            main()
        elif choice == '2':
            from interactive_demo import main
            main()
        elif choice == '3':
            from fast_demo import main
            main()
        elif choice == '4':
            from speed_comparison import main
            main()
        elif choice == '5':
            from demo_capabilities import main
            main()
        else:
            print("Invalid choice. Running interactive demo...")
            from interactive_demo import main
            main()
    except ImportError as e:
        print(f"❌ Demo not found: {e}")
    except Exception as e:
        print(f"❌ Demo error: {e}")

if __name__ == "__main__":
    run_demo()