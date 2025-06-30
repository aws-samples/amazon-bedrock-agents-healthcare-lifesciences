import json
import logging
import os
import boto3
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import io
import base64

# Configure logging
logger = logging.getLogger()
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))

# Configure matplotlib for non-interactive backend
plt.switch_backend('agg')

def create_time_series_plot(trends):
    """
    Create time series plot of adverse event trends
    """
    plt.figure(figsize=(12, 6))
    
    dates = pd.to_datetime(list(trends['daily_counts'].keys()))
    counts = list(trends['daily_counts'].values())
    ma = list(trends['moving_average'].values())
    
    plt.plot(dates, counts, label='Daily Reports', alpha=0.5)
    plt.plot(dates, ma, label='7-day Moving Average', linewidth=2)
    
    plt.title('Adverse Event Reports Over Time')
    plt.xlabel('Date')
    plt.ylabel('Number of Reports')
    plt.legend()
    plt.grid(True)
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    # Convert plot to base64 string
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    image_png = buffer.getvalue()
    buffer.close()
    plt.close()
    
    return base64.b64encode(image_png).decode()

def create_signal_bar_chart(signals):
    """
    Create bar chart of top adverse events by PRR
    """
    plt.figure(figsize=(12, 6))
    
    events = [s['event'] for s in signals]
    prrs = [s['prr'] for s in signals]
    
    plt.barh(events, prrs)
    plt.title('Top Adverse Events by PRR')
    plt.xlabel('PRR Value')
    plt.ylabel('Adverse Event')
    plt.grid(True)
    plt.tight_layout()
    
    # Convert plot to base64 string
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    image_png = buffer.getvalue()
    buffer.close()
    plt.close()
    
    return base64.b64encode(image_png).decode()

def create_signal_heatmap(signals):
    """
    Create heatmap of signal strength
    """
    plt.figure(figsize=(12, 8))
    
    # Create matrix of signal data
    data = {
        'event': [s['event'] for s in signals],
        'count': [s['count'] for s in signals],
        'prr': [s['prr'] for s in signals]
    }
    df = pd.DataFrame(data)
    
    # Pivot data for heatmap
    pivot_data = df.pivot_table(
        values=['count', 'prr'],
        index='event',
        aggfunc='first'
    )
    
    # Create heatmap
    sns.heatmap(
        pivot_data,
        annot=True,
        fmt='.2f',
        cmap='RdYlBu_r',
        center=0
    )
    
    plt.title('Signal Strength Heatmap')
    plt.tight_layout()
    
    # Convert plot to base64 string
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    image_png = buffer.getvalue()
    buffer.close()
    plt.close()
    
    return base64.b64encode(image_png).decode()

def generate_html_report(analysis_results, evidence_data):
    """
    Generate HTML report with analysis results and visualizations
    """
    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Safety Signal Detection Report</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            h1, h2 { color: #333; }
            .section { margin: 20px 0; }
            .visualization { margin: 20px 0; }
            table { border-collapse: collapse; width: 100%; }
            th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
            th { background-color: #f5f5f5; }
        </style>
    </head>
    <body>
        <h1>Safety Signal Detection Report</h1>
        
        <div class="section">
            <h2>Analysis Summary</h2>
            <p>Product: {product_name}</p>
            <p>Analysis Period: {start_date} to {end_date}</p>
            <p>Total Reports: {total_reports}</p>
        </div>
        
        <div class="section">
            <h2>Trend Analysis</h2>
            <div class="visualization">
                <img src="data:image/png;base64,{trend_plot}" alt="Trend Analysis">
            </div>
        </div>
        
        <div class="section">
            <h2>Signal Detection Results</h2>
            <div class="visualization">
                <img src="data:image/png;base64,{signal_plot}" alt="Signal Analysis">
            </div>
            <div class="visualization">
                <img src="data:image/png;base64,{heatmap}" alt="Signal Heatmap">
            </div>
        </div>
        
        <div class="section">
            <h2>Evidence Assessment</h2>
            <h3>Literature Evidence</h3>
            {literature_summary}
            
            <h3>Label Information</h3>
            {label_summary}
            
            <h3>Causality Assessment</h3>
            {causality_summary}
        </div>
    </body>
    </html>
    """
    
    # Format literature summary
    literature = evidence_data.get('literature', [])
    literature_summary = "<ul>"
    for article in literature:
        literature_summary += f"""
            <li>
                <strong>{article['title']}</strong> ({article['year']})<br>
                PMID: {article['pmid']}<br>
                {article['abstract'][:300]}...
            </li>
        """
    literature_summary += "</ul>"
    
    # Format label summary
    label_info = evidence_data.get('label_info', {})
    label_summary = "<ul>"
    for category, items in label_info.items():
        if items:
            label_summary += f"<li><strong>{category.title()}:</strong><br>{items[0][:300]}...</li>"
    label_summary += "</ul>"
    
    # Format causality summary
    causality = evidence_data.get('causality_assessment', {})
    causality_summary = f"""
        <p><strong>Evidence Level:</strong> {causality.get('evidence_level', 'Unknown')}</p>
        <p><strong>Causality Score:</strong> {causality.get('causality_score', 0)}</p>
        <p><strong>Assessment Date:</strong> {causality.get('assessment_date', 'Unknown')}</p>
    """
    
    # Generate visualizations
    trend_plot = create_time_series_plot(analysis_results['trends'])
    signal_plot = create_signal_bar_chart(analysis_results['signals'])
    heatmap = create_signal_heatmap(analysis_results['signals'])
    
    # Fill template
    report_html = html_template.format(
        product_name=analysis_results['product_name'],
        start_date=analysis_results['analysis_period']['start'],
        end_date=analysis_results['analysis_period']['end'],
        total_reports=analysis_results['total_reports'],
        trend_plot=trend_plot,
        signal_plot=signal_plot,
        heatmap=heatmap,
        literature_summary=literature_summary,
        label_summary=label_summary,
        causality_summary=causality_summary
    )
    
    return report_html

def upload_to_s3(html_content, bucket_name, product_name):
    """
    Upload HTML report to S3
    """
    s3 = boto3.client('s3')
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    key = f"reports/{product_name}/signal_detection_{timestamp}.html"
    
    try:
        s3.put_object(
            Bucket=bucket_name,
            Key=key,
            Body=html_content,
            ContentType='text/html'
        )
        return f"s3://{bucket_name}/{key}"
    except Exception as e:
        logger.error(f"Error uploading to S3: {str(e)}")
        raise

def lambda_handler(event, context):
    """
    Lambda handler for report generation
    """
    try:
        logger.info(f"Received event: {json.dumps(event)}")
        
        # Parse input parameters
        body = json.loads(event.get('body', '{}'))
        analysis_results = body.get('analysis_results')
        evidence_data = body.get('evidence_data')
        include_graphs = body.get('include_graphs', True)
        
        if not analysis_results or not evidence_data:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Analysis results and evidence data are required'
                })
            }
        
        # Generate report
        report_html = generate_html_report(analysis_results, evidence_data)
        
        # Upload to S3
        bucket_name = os.environ.get('REPORT_BUCKET_NAME')
        if not bucket_name:
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'error': 'S3 bucket name not configured'
                })
            }
        
        report_url = upload_to_s3(
            report_html,
            bucket_name,
            analysis_results['product_name']
        )
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'report_url': report_url,
                'timestamp': datetime.now().isoformat()
            })
        }
        
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': f"Internal server error: {str(e)}"
            })
        }
