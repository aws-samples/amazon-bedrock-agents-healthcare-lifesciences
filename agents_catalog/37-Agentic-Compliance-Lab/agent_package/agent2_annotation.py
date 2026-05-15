import boto3
import json
import uuid
import os
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from typing import Dict, List
from strands import Agent, tool
from strands.models import BedrockModel
from steering_hooks import AnnotationWorkflowPlugin

# AWS clients
region = boto3.Session().region_name
s3 = boto3.client('s3')
INCOMING_BUCKET = os.environ['INCOMING_BUCKET']
RESULTS_BUCKET = os.environ['RESULTS_BUCKET']
FRONTEND_BUCKET = os.environ['FRONTEND_BUCKET']

# Font paths
_FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fonts')

def _load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Load bundled Inter font at given size, falling back gracefully."""
    filename = 'Inter-SemiBold.ttf' if bold else 'Inter-Regular.ttf'
    font_path = os.path.join(_FONT_DIR, filename)
    try:
        return ImageFont.truetype(font_path, size)
    except (OSError, IOError):
        # Fallback: try common Linux paths (Lambda runtime)
        for fallback in ['/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
                         '/usr/share/fonts/dejavu/DejaVuSans.ttf']:
            try:
                return ImageFont.truetype(fallback, size)
            except (OSError, IOError):
                continue
        return ImageFont.load_default()

def _wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int, draw: ImageDraw.ImageDraw) -> List[str]:
    """Wrap text to fit within max_width pixels."""
    words = text.split()
    lines = []
    current_line = []
    
    for word in words:
        test_line = ' '.join(current_line + [word])
        bbox = draw.textbbox((0, 0), test_line, font=font)
        width = bbox[2] - bbox[0]
        
        if width <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(' '.join(current_line))
                current_line = [word]
            else:
                # Single word is too long
                lines.append(word)
    
    if current_line:
        lines.append(' '.join(current_line))
    
    return lines if lines else ['']

@tool
def load_s3_data(image_bucket: str, image_key: str, json_bucket: str, json_key: str) -> Dict:
    """Load compliance JSON from S3 including structured violations"""
    try:
        json_response = s3.get_object(Bucket=json_bucket, Key=json_key)
        compliance_data = json.loads(json_response['Body'].read().decode('utf-8'))
        
        return {
            'status': 'success',
            'compliance_report': compliance_data.get('compliance_report', ''),
            'violations': compliance_data.get('violations', []),
            'source_file': compliance_data.get('source_file', ''),
            'image_location': f"{image_bucket}/{image_key}"
        }
    except Exception as e:
        return {'status': 'error', 'error': str(e)}

@tool
def draw_annotations(image_bucket: str, image_key: str, annotations: List[Dict]) -> str:
    """Draw annotations on image and save to S3"""
    try:
        response = s3.get_object(Bucket=image_bucket, Key=image_key)
        original_image = Image.open(BytesIO(response['Body'].read()))
        
        # Expand canvas to add sidebar
        sidebar_width = 300
        new_width = original_image.width + sidebar_width
        expanded_image = Image.new('RGB', (new_width, original_image.height), 'white')
        expanded_image.paste(original_image, (0, 0))
        
        draw = ImageDraw.Draw(expanded_image)
        
        font = _load_font(13)
        title_font = _load_font(15, bold=True)
        
        colors = {
            'high': (255, 0, 0),
            'medium': (255, 140, 0),
            'low': (204, 204, 0)
        }
        
        # Check for compliant status
        is_compliant = False
        if not annotations:
            is_compliant = True
        elif len(annotations) == 1:
            label = annotations[0].get('label', '').lower()
            severity = annotations[0].get('severity', '').lower()
            if 'compliant' in label or severity == 'info':
                is_compliant = True
        
        if is_compliant:
            # Load compliant.png from S3 and paste on sidebar
            compliant_response = s3.get_object(
                Bucket=FRONTEND_BUCKET, 
                Key='compliant.png'
            )
            compliant_img = Image.open(BytesIO(compliant_response['Body'].read()))
            
            # Resize to fit sidebar
            max_size = min(sidebar_width - 20, original_image.height - 40)
            compliant_img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            
            # Center on sidebar
            sidebar_x = original_image.width + (sidebar_width - compliant_img.width) // 2
            sidebar_y = (original_image.height - compliant_img.height) // 2
            expanded_image.paste(compliant_img, (sidebar_x, sidebar_y))
            
            # Save and return
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            session_id = str(uuid.uuid4())[:8]
            output_key = f"annotated-{timestamp}-{session_id}.png"
            
            img_buffer = BytesIO()
            expanded_image.save(img_buffer, format='PNG')
            
            s3.put_object(
                Bucket=RESULTS_BUCKET,
                Key=output_key,
                Body=img_buffer.getvalue(),
                ContentType='image/png'
            )
            
            return f"s3://{RESULTS_BUCKET}/{output_key}"
        
        # Separate annotations: sidebar items have box [0,0,0,0], everything else goes on the image
        missing_sections = []
        image_annotations = []
        
        for ann in annotations:
            box = ann.get('box', [0, 0, 0, 0])
            if box == [0, 0, 0, 0]:
                missing_sections.append(ann)
            else:
                image_annotations.append(ann)
        
        # Draw image annotations
        CONTRAST_COLOR = (255, 255, 255)  # white outline for contrast
        CONTRAST_WIDTH = 5  # outer stroke width
        ANNOTATION_WIDTH = 3  # inner colored stroke width
        
        for ann in image_annotations:
            box = ann['box']
            padding = 10
            expanded_box = [
                max(0, box[0] - padding),
                max(0, box[1] - padding),
                min(original_image.width, box[2] + padding),
                min(original_image.height, box[3] + padding)
            ]
            
            color = colors.get(ann.get('severity', 'medium'), colors['medium'])
            
            # Outer contrasting border (white)
            draw.rectangle(expanded_box, outline=CONTRAST_COLOR, width=CONTRAST_WIDTH)
            # Inner colored border
            draw.rectangle(expanded_box, outline=color, width=ANNOTATION_WIDTH)
            
            label = ann['label']
            text_bbox = draw.textbbox((0, 0), label, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
            
            label_x = expanded_box[0]
            label_y = expanded_box[1] - text_height - 8
            label_box = [label_x, label_y,
                        label_x + text_width + 10, expanded_box[1]]
            # White outline behind label pill, then colored fill
            draw.rectangle(label_box, outline=CONTRAST_COLOR, width=2)
            draw.rectangle(label_box, fill=color)
            draw.text((label_x + 5, label_y + 3),
                     label, fill='white', font=font)
        
        # Draw missing sections in sidebar
        if missing_sections:
            sidebar_x = original_image.width + 10
            sidebar_y = 20
            max_text_width = sidebar_width - 50  # Leave room for indicator box + padding
            
            draw.text((sidebar_x, sidebar_y), "MISSING SECTIONS", fill='black', font=title_font)
            sidebar_y += 30
            
            for ann in missing_sections:
                color = colors.get(ann.get('severity', 'medium'), colors['medium'])
                indicator_box = [sidebar_x, sidebar_y, sidebar_x + 20, sidebar_y + 20]
                # Contrasting border on sidebar indicators too
                draw.rectangle(indicator_box, outline=CONTRAST_COLOR, width=2)
                draw.rectangle(indicator_box, fill=color, outline=(80, 80, 80), width=1)
                
                # Wrap text to fit sidebar width
                text_lines = _wrap_text(ann['label'], font, max_text_width, draw)
                text_x = sidebar_x + 30
                text_y = sidebar_y + 2
                
                for line in text_lines:
                    draw.text((text_x, text_y), line, fill='black', font=font)
                    text_y += 16  # Line height
                
                # Advance y position based on number of lines
                sidebar_y += max(35, len(text_lines) * 16 + 10)
        
        # Save annotated image
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_id = str(uuid.uuid4())[:8]
        output_key = f"annotated-{timestamp}-{session_id}.png"
        
        img_buffer = BytesIO()
        expanded_image.save(img_buffer, format='PNG')
        
        s3.put_object(
            Bucket=RESULTS_BUCKET,
            Key=output_key,
            Body=img_buffer.getvalue(),
            ContentType='image/png'
        )
        
        return f"s3://{RESULTS_BUCKET}/{output_key}"
        
    except Exception as e:
        raise Exception(f"Error drawing annotations: {str(e)}")

@tool
def get_text_regions(image_bucket: str, image_key: str) -> Dict:
    """Get precise text block coordinates using Textract"""
    textract = boto3.client('textract')
    
    response = textract.detect_document_text(
        Document={'S3Object': {'Bucket': image_bucket, 'Name': image_key}}
    )
    
    # Get image dimensions once
    img_response = s3.get_object(Bucket=image_bucket, Key=image_key)
    image = Image.open(BytesIO(img_response['Body'].read()))
    width, height = image.size
    
    text_blocks = []
    for block in response['Blocks']:
        if block['BlockType'] == 'LINE':
            bbox = block['Geometry']['BoundingBox']
            text_blocks.append({
                'text': block['Text'],
                'box': [
                    int(bbox['Left'] * width),
                    int(bbox['Top'] * height), 
                    int((bbox['Left'] + bbox['Width']) * width),
                    int((bbox['Top'] + bbox['Height']) * height)
                ]
            })
    
    return {'text_blocks': text_blocks}


annotation_tools = [load_s3_data, get_text_regions, draw_annotations]

agent_instructions = """You are a Visual Compliance Annotation Specialist for FDA medicine label compliance.

Your workflow: load the compliance data, get text regions from the image, then draw annotations. Tool ordering and annotation count validation are enforced automatically.

Create exactly one annotation per violation, so exactly all annotations must be annotated. Map each violation to the label image:

IMAGE ANNOTATIONS (on the label):
- For violations about EXISTING content that is wrong or non-compliant
- Use exact coordinates from matching text blocks

SIDEBAR ANNOTATIONS (missing items):
- For violations about something completely ABSENT from the label, or when no matching text region can be found
- Use coordinates [0, 0, 0, 0] — the tool handles sidebar placement automatically
- Prefix the label with "Missing" if the title doesn't already contain it

ANNOTATION STRUCTURE:
Each annotation must contain:
- "label": Use the violation's "title" field directly
- "box": [x1, y1, x2, y2] for image annotations, [0, 0, 0, 0] for sidebar
- "severity": Use the violation's "severity" field directly

If the violations array is empty (zero violations), pass an empty annotations list [] to draw_annotations. The tool will display the compliant badge automatically"""

def get_annotation_agent():
    model = BedrockModel(
        model_id="us.anthropic.claude-opus-4-7",
        region_name=region,
        streaming=False
    )
    
    agent = Agent(
        model=model,
        tools=annotation_tools,
        system_prompt=agent_instructions,
        plugins=[AnnotationWorkflowPlugin()]  # steering hooks
    )
    agent.name = "Visual_Compliance_Annotator_Agent"
    return agent
