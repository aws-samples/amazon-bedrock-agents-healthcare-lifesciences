# Health Pre-Visit Questionnaire Strands Agent

A conversational AI agent built with Amazon Strands for completing Health Pre-Visit Questionnaire PDF forms.

## Project Structure

```
previsit/
├── src/                          # Source code
│   ├── agents/                   # Strands agents
│   │   ├── tools/                # Agent tools
│   │   │   ├── basic_info.py     # Basic information tools
│   │   │   ├── medical_history.py # Medical history tools
│   │   │   ├── medications.py    # Medication tools
│   │   │   ├── social_history.py # Social history tools
│   │   │   ├── health_maintenance.py # Health maintenance tools
│   │   │   ├── symptoms.py       # Symptom tools
│   │   │   └── utilities.py      # Utility tools
│   │   ├── __init__.py
│   │   ├── pvq_agent.py         # Main PVQ agent (Claude Sonnet)
│   │   ├── pvq_agent_fast.py    # Fast agent (Claude Haiku)
│   │   └── pvq_agent_ultra_fast.py # Ultra-fast agent (Rule-based)
│   ├── models/                   # Data models
│   │   ├── __init__.py
│   │   └── patient_data.py      # Patient data structures
│   ├── utils/                    # Utilities
│   │   ├── __init__.py
│   │   ├── validators.py        # Data validation
│   │   └── pdf_generator.py     # PDF generation
│   └── __init__.py
├── tests/                        # Test suite
│   └── test_agent.py            # Agent tests
├── config/                       # Configuration
│   └── requirements.txt         # Dependencies
├── data/                         # Data storage (JSON files)
├── output/                       # Generated PDFs
├── main.py                       # Main application
├── run_demo.py                   # Demo selector
├── demo_capabilities.py          # Capabilities demo
├── fast_demo.py                  # Fast agent demo
├── full_questionnaire_demo.py    # Complete questionnaire demo
├── interactive_demo.py           # Interactive demo
├── speed_comparison.py           # Agent speed comparison
├── pvq.pdf                       # Original PDF form
└── README.md                     # This file
```

## Features

### 🤖 Conversational Agent
- Natural language interaction using Amazon Strands
- Systematic data collection through all questionnaire sections
- Real-time progress tracking and validation
- Intelligent conversation flow management

### 📋 Comprehensive Data Collection
- **Basic Information**: Name, address, phone, DOB, sex
- **Medical History**: Conditions organized by category
  - Eye & Ear, Heart, Gastrointestinal, Lung
  - Diabetes & Thyroid, Neurological, Bone & Joint, Cancer
- **Current Medications**: Name, strength, frequency, purpose
- **Drug Allergies**: Drug name, reaction type, severity
- **Current Symptoms**: Description, duration, severity

### 📄 PDF Generation
- Professional PDF output matching original form
- Structured layout with proper formatting
- Includes all collected patient data
- Metadata and completion timestamps

### 🛡️ Data Validation
- Phone number format validation
- Date format validation (MM/DD/YYYY)
- Required field checking
- Data type validation

### 🧹 Recent Cleanup
- Removed unused PDF analyzer functionality
- Cleaned up unnecessary dependencies (boto3)
- Removed unused demo data files
- Optimized project structure

## Setup

### Prerequisites
- Python 3.8+
- Conda environment with Strands installed

### Installation

1. **Activate Strands Environment**:
```bash
conda create -n strands python=3.11 -y
conda activate strands
```

2. **Install Dependencies**:
```bash
pip install -r config/requirements.txt
```

**Core Dependencies:**
- `strands>=0.1.0` - Amazon Strands framework
- `reportlab>=3.6.0` - PDF generation
- `pydantic>=2.0.0` - Data validation and models
- `python-dateutil>=2.8.2` - Date handling utilities
- `typing-extensions>=4.0.0` - Type hints support

3. **Verify Installation**:
```bash
python tests/test_agent.py
```

## Usage

### Quick Start
```bash
# Run main application
python main.py

# Or run unified demo selector
python run_demo.py
```

### Demo Modes

#### 1. Interactive Demo
```bash
python interactive_demo.py
```
- Real-time conversation with the agent
- Type your responses naturally
- Built-in help system with examples
- Commands: `help`, `progress`, `quit`

#### 2. Speed Comparison
```bash
python speed_comparison.py
```
- Benchmark all agent variants
- Compare Regular vs Fast vs Ultra-Fast agents
- Performance metrics and recommendations
- Interactive testing mode

#### 3. Full Questionnaire Demo
```bash
python full_questionnaire_demo.py
```
- Complete patient journey simulation
- 25+ interactions covering all sections
- Realistic medical scenario
- Progress tracking demonstration

#### 4. Fast Agent Demo
```bash
python fast_demo.py
```
- Speed-optimized agent (1-2 second responses)
- Performance timing for each interaction
- Choose between speed test or interactive mode

#### 5. Capabilities Demo
```bash
python demo_capabilities.py
```
- Showcase all agent features
- Tool-by-tool demonstration
- Data model examples

### Agent Variants

#### Standard Agent (pvq_agent_refactored.py)
- **Model**: Claude Sonnet (most accurate)
- **Response Time**: 3-8 seconds
- **Use Case**: Complex medical scenarios

#### Fast Agent (pvq_agent_fast.py)
- **Model**: Claude Haiku (balanced)
- **Response Time**: 1-2 seconds
- **Use Case**: General questionnaire completion

#### Ultra-Fast Agent (pvq_agent_ultra_fast.py)
- **Model**: Rule-based processing
- **Response Time**: 0.1-0.3 seconds
- **Use Case**: High-volume, simple data collection

### Available Commands During Conversation
- `progress` - Check completion status
- `categories` - Show medical condition categories  
- `quit` - Save data and exit
- `help` - Show guidance (in interactive demos)

### Example Conversation Flow

```
🏥 UCLA Health Pre-Visit Questionnaire
📋 Powered by Amazon Strands
==================================================

🤖 Assistant: Hello! I'm here to help you complete your UCLA Health 
pre-visit questionnaire. Let's start with your basic information. 
What is your full name?

💬 You: My name is John Smith

🤖 Assistant: ✅ Saved name: John Smith. Thank you! Now, could you 
please provide your complete home address?

💬 You: 123 Main Street, Los Angeles, CA 90210

🤖 Assistant: ✅ Saved address: 123 Main Street, Los Angeles, CA 90210. 
Great! What's your phone number?

💬 You: 555-123-4567

🤖 Assistant: ✅ Saved phone: 555-123-4567. Perfect! What is your 
date of birth? Please use MM/DD/YYYY format.

💬 You: progress

🤖 Assistant: 📋 Progress:
Basic Info: ❌
Medical History: ❌  
Medications: 0 recorded
Allergies: 0 recorded
Symptoms: 0 recorded
```

### Speed Performance Comparison

| Agent Type | Model | Avg Response | Use Case |
|------------|-------|--------------|----------|
| Standard | Claude Sonnet | 3-8 seconds | Complex medical scenarios |
| Fast | Claude Haiku | 1-2 seconds | General questionnaire |
| Ultra-Fast | Rule-based | 0.1-0.3 seconds | High-volume data collection |

### Demo Selection Menu

```bash
python run_demo.py

🏥 UCLA HEALTH PVQ DEMO SELECTOR
========================================
1. Full Questionnaire Demo
2. Interactive Demo
3. Fast Agent Demo
4. Speed Comparison
5. Capabilities Demo

Select demo (1-5):
```

## API Reference

### PVQStrandsAgent

Main agent class for questionnaire completion.

#### Methods

- `chat(message: str) -> str`: Process user message
- `save_basic_info(field: str, value: str) -> str`: Save basic information
- `save_medical_condition(category: str, condition: str, year: str) -> str`: Save medical condition
- `save_medication(name: str, strength: str, frequency: str) -> str`: Save medication
- `save_allergy(drug: str, reaction: str) -> str`: Save drug allergy
- `get_progress() -> str`: Get completion progress

### PVQData

Data model for patient information.

#### Fields

- Basic: `patient_name`, `home_address`, `phone`, `date_of_birth`, `sex`
- Medical: `heart_conditions`, `lung_conditions`, etc.
- Medications: `current_medications`
- Allergies: `drug_allergies`
- Symptoms: `current_symptoms`

## File Outputs

### JSON Data File
```json
{
  "patient_name": "John Smith",
  "home_address": "123 Main St, Los Angeles, CA 90210",
  "phone": "555-123-4567",
  "date_of_birth": "01/15/1980",
  "sex": "Male",
  "heart_conditions": ["High blood pressure (2020)"],
  "current_medications": [
    {
      "name": "Lisinopril",
      "strength": "10mg", 
      "frequency": "once daily"
    }
  ],
  "completion_timestamp": "2024-01-15T10:30:00",
  "form_version": "UCLA Health PVQ v1.0"
}
```

### Generated PDF
- Professional medical document format
- All sections properly organized
- Patient data clearly presented
- Completion metadata included

## Testing

Run the test suite:
```bash
python tests/test_agent.py
```

Tests cover:
- Data model functionality
- Validation functions
- Agent tool operations
- Conversation flow

## Integration

### Healthcare Systems
- EHR integration via JSON output
- FHIR compatibility (future enhancement)
- Patient portal integration

### Workflow Integration
```python
from src.agents.pvq_agent import PVQStrandsAgent
from src.utils.pdf_generator import generate_pdf_from_json

# Initialize agent
agent = PVQStrandsAgent()

# Process patient interaction
response = agent.chat("My name is John Smith")

# Generate PDF
pdf_file = generate_pdf_from_json("data/pvq_john_smith_20240115.json")
```

## Architecture

### Components
- **Strands Agent**: Conversational AI with specialized tools
- **Data Models**: Structured patient information storage
- **Validators**: Input validation and formatting
- **PDF Generator**: Professional document creation
- **Test Suite**: Comprehensive functionality testing

### Design Principles
- **Modular**: Clear separation of concerns
- **Extensible**: Easy to add new features
- **Testable**: Comprehensive test coverage
- **User-Friendly**: Natural conversation flow
- **Professional**: Medical-grade output quality

## Contributing

1. Follow the existing code structure
2. Add tests for new features
3. Update documentation
4. Ensure PDF output quality
5. Remove unused code and dependencies
6. Keep the project lean and focused

## Recent Updates

- ✅ Removed unused PDF analyzer functionality
- ✅ Cleaned up boto3 dependency (no longer needed)
- ✅ Removed unused demo data files
- ✅ Fixed test file to use correct agent methods
- ✅ Optimized project structure and dependencies
