"""
PDF generation utilities for UCLA Health Pre-Visit Questionnaire
"""

import json
import datetime
from typing import Dict, List, Any
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

class PVQPDFGenerator:
    """Generate filled PDF from PVQ data"""
    
    def __init__(self, data: Dict[str, Any]):
        self.data = data
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Setup custom paragraph styles"""
        self.title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=16,
            spaceAfter=30,
            alignment=1  # Center
        )
        
        self.section_style = ParagraphStyle(
            'SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=12,
            spaceBefore=20,
            spaceAfter=10,
            textColor=colors.darkblue
        )
    
    def generate_pdf(self, output_path: str) -> str:
        """Generate the complete PDF"""
        doc = SimpleDocTemplate(output_path, pagesize=letter)
        story = []
        
        # Header
        story.extend(self._create_header())
        
        # Basic Information
        story.extend(self._create_basic_info_section())
        
        # Medical History
        story.extend(self._create_medical_history_section())
        
        # Medications
        story.extend(self._create_medications_section())
        
        # Allergies
        story.extend(self._create_allergies_section())
        
        # Current Symptoms
        story.extend(self._create_symptoms_section())
        
        # Family History
        story.extend(self._create_family_history_section())
        
        # Footer
        story.extend(self._create_footer())
        
        # Build PDF
        doc.build(story)
        return output_path
    
    def _create_header(self) -> List:
        """Create PDF header"""
        elements = []
        
        elements.append(Paragraph("Pre-Visit Questionnaire", self.title_style))
        elements.append(Paragraph("Division of Geriatric Medicine", self.styles['Normal']))
        elements.append(Paragraph("UCLA Healthcare", self.styles['Normal']))
        elements.append(Spacer(1, 20))
        
        return elements
    
    def _create_basic_info_section(self) -> List:
        """Create basic information section"""
        elements = []
        
        elements.append(Paragraph("BASIC INFORMATION", self.section_style))
        
        basic_info = [
            ['Date form completed:', self.data.get('date_completed', '')],
            ['Name of patient:', self.data.get('patient_name', '')],
            ['Home Address:', self.data.get('home_address', '')],
            ['Phone:', self.data.get('phone', '')],
            ['Date of birth:', self.data.get('date_of_birth', '')],
            ['Sex:', self.data.get('sex', '')]
        ]
        
        table = Table(basic_info, colWidths=[2*inch, 4*inch])
        table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 20))
        
        return elements
    
    def _create_medical_history_section(self) -> List:
        """Create medical history section"""
        elements = []
        
        elements.append(Paragraph("PAST MEDICAL HISTORY", self.section_style))
        
        medical_categories = [
            ('EYE & EAR', 'eye_ear_conditions'),
            ('HEART', 'heart_conditions'),
            ('GASTROINTESTINAL TRACT', 'gastrointestinal_conditions'),
            ('LUNGS', 'lung_conditions'),
            ('DIABETES & THYROID', 'diabetes_thyroid'),
            ('NEUROLOGICAL', 'neurological_conditions'),
            ('BONE & JOINT', 'bone_joint_conditions'),
            ('CANCER', 'cancer_history')
        ]
        
        for category_name, field_name in medical_categories:
            conditions = self.data.get(field_name, [])
            if conditions:
                elements.append(Paragraph(f"<b>{category_name}:</b>", self.styles['Normal']))
                for condition in conditions:
                    elements.append(Paragraph(f"• {condition}", self.styles['Normal']))
                elements.append(Spacer(1, 10))
        
        return elements
    
    def _create_medications_section(self) -> List:
        """Create medications section"""
        elements = []
        
        medications = self.data.get('current_medications', [])
        if medications:
            elements.append(Paragraph("CURRENT MEDICATIONS", self.section_style))
            
            med_data = [['Medication', 'Strength', 'Frequency', 'Purpose']]
            for med in medications:
                med_data.append([
                    med.get('name', ''),
                    med.get('strength', ''),
                    med.get('frequency', ''),
                    med.get('purpose', '')
                ])
            
            table = Table(med_data, colWidths=[2*inch, 1*inch, 1.5*inch, 1.5*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ]))
            
            elements.append(table)
            elements.append(Spacer(1, 20))
        
        return elements
    
    def _create_allergies_section(self) -> List:
        """Create allergies section"""
        elements = []
        
        allergies = self.data.get('drug_allergies', [])
        if allergies:
            elements.append(Paragraph("DRUG ALLERGIES", self.section_style))
            
            allergy_data = [['Drug', 'Reaction', 'Severity']]
            for allergy in allergies:
                allergy_data.append([
                    allergy.get('drug', ''),
                    allergy.get('reaction', ''),
                    allergy.get('severity', '')
                ])
            
            table = Table(allergy_data, colWidths=[2*inch, 2*inch, 2*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ]))
            
            elements.append(table)
            elements.append(Spacer(1, 20))
        
        return elements
    
    def _create_symptoms_section(self) -> List:
        """Create current symptoms section"""
        elements = []
        
        symptoms = self.data.get('current_symptoms', [])
        if symptoms:
            elements.append(Paragraph("CURRENT SYMPTOMS", self.section_style))
            for symptom in symptoms:
                elements.append(Paragraph(f"• {symptom}", self.styles['Normal']))
            elements.append(Spacer(1, 20))
        
        return elements
    
    def _create_family_history_section(self) -> List:
        """Create family history section"""
        elements = []
        
        family_history = self.data.get('family_history', [])
        if family_history:
            elements.append(Paragraph("FAMILY HISTORY", self.section_style))
            for condition in family_history:
                elements.append(Paragraph(f"• {condition}", self.styles['Normal']))
            elements.append(Spacer(1, 20))
        
        return elements
    
    def _create_footer(self) -> List:
        """Create PDF footer"""
        elements = []
        
        elements.append(Spacer(1, 30))
        
        # Completion info
        completion_time = self.data.get('completion_timestamp', datetime.datetime.now().isoformat())
        elements.append(Paragraph(f"<i>Completed: {completion_time}</i>", self.styles['Normal']))
        elements.append(Paragraph("<i>Generated by UCLA Health PVQ Strands Agent</i>", self.styles['Normal']))
        
        return elements

def generate_pdf_from_json(json_file: str, output_pdf: str = None) -> str:
    """Generate PDF from JSON data file"""
    with open(json_file, 'r') as f:
        data = json.load(f)
    
    if not output_pdf:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_pdf = f"output/completed_pvq_{timestamp}.pdf"
    
    generator = PVQPDFGenerator(data)
    return generator.generate_pdf(output_pdf)