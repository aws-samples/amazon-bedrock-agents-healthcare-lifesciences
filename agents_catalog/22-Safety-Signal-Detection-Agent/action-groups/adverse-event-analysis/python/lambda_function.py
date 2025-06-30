import json
import logging
import os
import urllib.request
import urllib.parse
from datetime import datetime, timedelta
from collections import defaultdict

# Configure logging
logger = logging.getLogger()
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))

def calculate_prr(a, b, c, d):
    """
    Calculate Proportional Reporting Ratio (PRR)
    a: Number of reports with the drug and adverse event
    b: Number of reports with the drug
    c: Number of reports with the adverse event
    d: Total number of reports
    """
    if a == 0:
        return None
    try:
        prr = (a/b)/(c/d)
        return prr
    except ZeroDivisionError:
        return None

def query_openfda(product_name, start_date, end_date):
    """
    Query OpenFDA API for adverse event reports
    """
    base_url = "https://api.fda.gov/drug/event.json"
    
    # Construct search query
    search_query = f'patient.drug.medicinalproduct:"{product_name}" AND receiptdate:[{start_date} TO {end_date}]'
    
    params = {
        'search': search_query,
        'limit': 100  # Adjust based on needs
    }
    
    url = f"{base_url}?{urllib.parse.urlencode(params)}"
    
    try:
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read().decode())
            return data
    except Exception as e:
        logger.error(f"Error querying OpenFDA API: {str(e)}")
        raise

def analyze_trends(data):
    """
    Analyze trends in adverse event reports
    """
    daily_counts = defaultdict(int)
    
    # Count reports by date
    for report in data['results']:
        date = report.get('receiptdate', '').split('T')[0]  # Get date part only
        if date:
            daily_counts[date] += 1
    
    # Sort dates
    dates = sorted(daily_counts.keys())
    
    # Calculate 7-day moving average
    moving_average = {}
    for i, date in enumerate(dates):
        if i >= 3 and i < len(dates) - 3:  # Need 3 days before and after
            window_sum = sum(daily_counts[dates[j]] for j in range(i-3, i+4))
            moving_average[date] = window_sum / 7
    
    return {
        'daily_counts': dict(daily_counts),
        'moving_average': moving_average
    }

def detect_signals(data, threshold=2.0):
    """
    Detect safety signals using PRR calculation
    """
    signals = []
    
    # Calculate total reports for the drug
    total_drug_reports = len(data['results'])
    
    # Group adverse events
    events = defaultdict(int)
    for report in data['results']:
        for event in report.get('patient', {}).get('reaction', []):
            event_term = event.get('reactionmeddrapt', '')
            if event_term:
                events[event_term] += 1
    
    # Calculate PRR for each event
    for event, count in events.items():
        # Query background rates (simplified - should use actual background rates)
        background_rate = 0.01  # Example background rate
        total_background = 1000000  # Example total reports
        
        prr = calculate_prr(
            count,  # a: reports with drug and event
            total_drug_reports,  # b: total reports with drug
            background_rate * total_background,  # c: total reports with event
            total_background  # d: total reports
        )
        
        if prr and prr >= threshold:
            signals.append({
                'event': event,
                'count': count,
                'prr': prr,
                'confidence_interval': calculate_confidence_interval(count, total_drug_reports)
            })
    
    return sorted(signals, key=lambda x: x['prr'], reverse=True)

def calculate_confidence_interval(count, total):
    """
    Calculate 95% confidence interval for proportion
    """
    if total == 0:
        return None
    
    proportion = count / total
    z = 1.96  # 95% confidence level
    
    try:
        # Using simplified formula for standard error
        standard_error = ((proportion * (1 - proportion)) / total) ** 0.5
        ci_lower = max(0, proportion - z * standard_error)
        ci_upper = min(1, proportion + z * standard_error)
        
        return {
            'lower': ci_lower,
            'upper': ci_upper
        }
    except:
        return None

def lambda_handler(event, context):
    """
    Lambda handler for adverse event analysis
    """
    try:
        logger.info(f"Received event: {json.dumps(event)}")
        
        # Parse input parameters
        body = json.loads(event.get('body', '{}'))
        product_name = body.get('product_name')
        time_period = int(body.get('time_period', 6))  # Default 6 months
        signal_threshold = float(body.get('signal_threshold', 2.0))
        
        if not product_name:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Product name is required'
                })
            }
        
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30*time_period)
        
        # Query OpenFDA API
        data = query_openfda(
            product_name,
            start_date.strftime('%Y%m%d'),
            end_date.strftime('%Y%m%d')
        )
        
        # Analyze trends
        trends = analyze_trends(data)
        
        # Detect signals
        signals = detect_signals(data, signal_threshold)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'product_name': product_name,
                'analysis_period': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat()
                },
                'total_reports': len(data['results']),
                'trends': trends,
                'signals': signals[:10]  # Top 10 signals
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
