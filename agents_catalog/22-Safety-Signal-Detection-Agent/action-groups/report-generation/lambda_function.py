import json
import logging
import os
import boto3
from datetime import datetime

# Configure logging
logger = logging.getLogger()
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))

def generate_text_report(analysis_results, evidence_data):
    """
    Generate text report
    """
    report_lines = []
    
    # Analysis Summary
    report_lines.extend([
        "Safety Signal Detection Report",
        "===========================\n",
        f"Product: {analysis_results['product_name']}",
        f"Analysis Period: {analysis_results['analysis_period']['start']} to {analysis_results['analysis_period']['end']}",
        f"Total Reports: {analysis_results['total_reports']}" + (
            f" (analyzed from {analysis_results['total_available']} available reports)" if 'total_available' in analysis_results else ""
        ) + "\n",
    ])
    
    # Signal Detection Results
    report_lines.append("Signal Detection Results")
    report_lines.append("----------------------")
    for signal in analysis_results['signals']:
        ci = signal['confidence_interval']
        ci_text = f" (95% CI: {ci['lower']}-{ci['upper']})" if ci else ""
        report_lines.append(
            f"- {signal['event']}: PRR={signal['prr']}, Reports={signal['count']}{ci_text}"
        )
    report_lines.append("")
    
    # Trend Analysis
    if analysis_results['trends']['daily_counts']:
        dates = sorted(analysis_results['trends']['daily_counts'].keys())
        report_lines.extend([
            "Trend Analysis",
            "--------------",
            f"Report dates: {dates[0]} to {dates[-1]}",
            f"Peak daily reports: {max(analysis_results['trends']['daily_counts'].values())}\n"
        ])
    
    # Evidence Assessment
    report_lines.extend([
        "Evidence Assessment",
        "------------------"
    ])
    
    # Literature Evidence
    literature = evidence_data.get('literature', [])
    if literature:
        report_lines.append("\nLiterature Evidence:")
        for article in literature:
            report_lines.extend([
                f"- {article['title']} ({article['year']}, PMID: {article['pmid']})",
                f"  Abstract: {article['abstract'][:300]}..."
            ])
    else:
        report_lines.append("\nNo relevant literature evidence found.")
    
    # Label Information
    label_info = evidence_data.get('label_info', {})
    if label_info:
        report_lines.append("\nFDA Label Information:")
        for category, items in label_info.items():
            if items:
                report_lines.extend([
                    f"{category.title()}:",
                    f"{items[0][:300]}..."
                ])
    else:
        report_lines.append("\nNo FDA label information found.")
    
    # Causality Assessment
    causality = evidence_data.get('causality_assessment', {})
    if causality:
        report_lines.extend([
            "\nCausality Assessment:",
            f"Evidence Level: {causality.get('evidence_level', 'Unknown')}",
            f"Causality Score: {causality.get('causality_score', 0)}",
            f"Assessment Date: {causality.get('assessment_date', 'Unknown')}"
        ])
    
    return "\n".join(report_lines)

def upload_to_s3(report_text, bucket_name, product_name):
    """
    Upload report to S3 bucket
    """
    s3 = boto3.client('s3')
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    key = f"reports/{product_name}/signal_detection_{timestamp}.txt"

    try:
        s3.put_object(
            Bucket=bucket_name,
            Key=key,
            Body=report_text,
            ContentType='text/plain'
        )
        return f"s3://{bucket_name}/{key}"
    except Exception as e:
        logger.error(f"Error uploading to S3: {str(e)}")
        raise

def parse_parameters(event):
    """
    Parse parameters from Bedrock event
    """
    logger.info(f"Parsing parameters from event: {json.dumps(event)}")
    
    parameters = {}
    if 'parameters' in event:
        for param in event['parameters']:
            name = param.get('name')
            value = param.get('value')
            if name and value is not None:
                parameters[name] = value
    
    analysis_results = json.loads(parameters.get('analysis_results', '{}'))
    evidence_data = json.loads(parameters.get('evidence_data', '{}'))
    
    if not analysis_results or not evidence_data:
        raise ValueError("Analysis results and evidence data are required")
    
    return analysis_results, evidence_data

def lambda_handler(event, context):
    """
    Lambda handler for report generation
    """
    try:
        logger.info(f"Received event: {json.dumps(event)}")
        
        try:
            analysis_results, evidence_data = parse_parameters(event)
        except ValueError as e:
            return {
                "response": {
                    "actionGroup": event["actionGroup"],
                    "function": event["function"],
                    "functionResponse": {
                        "responseBody": {
                            "TEXT": {
                                "body": str(e)
                            }
                        }
                    }
                }
            }
        
        report_text = generate_text_report(analysis_results, evidence_data)
        
        bucket_name = os.environ.get('REPORT_BUCKET_NAME')
        if not bucket_name:
            return {
                "response": {
                    "actionGroup": event["actionGroup"],
                    "function": event["function"],
                    "functionResponse": {
                        "responseBody": {
                            "TEXT": {
                                "body": "S3 bucket name not configured"
                            }
                        }
                    }
                }
            }
        
        report_url = upload_to_s3(
            report_text,
            bucket_name,
            analysis_results['product_name']
        )
        
        return {
            "response": {
                "actionGroup": event["actionGroup"],
                "function": event["function"],
                "functionResponse": {
                    "responseBody": {
                        "TEXT": {
                            "body": f"Report generated and uploaded to {report_url}"
                        }
                    }
                }
            }
        }
        
    except Exception as e:
        return {
            "response": {
                "actionGroup": event["actionGroup"],
                "function": event["function"],
                "functionResponse": {
                    "responseBody": {
                        "TEXT": {
                            "body": f"An error occurred while generating report: {str(e)}"
                        }
                    }
                }
            }
        }
