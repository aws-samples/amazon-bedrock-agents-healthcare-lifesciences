import json
import logging
import os
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timedelta
from collections import defaultdict

# Configure logging
logger = logging.getLogger()
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))

def calculate_prr(a, b, c, d):
    """
    Calculate Proportional Reporting Ratio (PRR)
    """
    if a == 0:
        return None
    try:
        prr = (a/b)/(c/d)
        logger.debug(f"PRR calculation: a={a}, b={b}, c={c}, d={d}, prr={prr}")
        return prr
    except ZeroDivisionError:
        logger.warning("Division by zero in PRR calculation")
        return None

def query_openfda(product_name, start_date, end_date):
    """
    Query OpenFDA API for adverse event reports
    """
    base_url = "https://api.fda.gov/drug/event.json"
    search_query = f'patient.drug.medicinalproduct:"{product_name}" AND receiptdate:[{start_date} TO {end_date}]'
    params = {
        'search': search_query,
        'limit': 100
    }
    
    url = f"{base_url}?{urllib.parse.urlencode(params)}"
    logger.info(f"OpenFDA API URL: {url}")
    
    try:
        req = urllib.request.Request(url, headers={'Accept': 'application/json'})
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            logger.info(f"OpenFDA API response: {len(data.get('results', []))} results found")
            return data
    except urllib.error.HTTPError as e:
        logger.error(f"OpenFDA API HTTP error: {e.code} - {e.reason}")
        if e.code == 404:
            return {'results': []}
        raise
    except Exception as e:
        logger.error(f"Error querying OpenFDA API: {str(e)}")
        raise

def analyze_trends(data):
    """
    Analyze trends in adverse event reports
    """
    daily_counts = defaultdict(int)
    
    for report in data['results']:
        date = report.get('receiptdate', '').split('T')[0]
        if date:
            daily_counts[date] += 1
    
    dates = sorted(daily_counts.keys())
    
    moving_average = {}
    for i, date in enumerate(dates):
        if i >= 3 and i < len(dates) - 3:
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
    total_drug_reports = len(data['results'])
    
    events = defaultdict(int)
    for report in data['results']:
        for event in report.get('patient', {}).get('reaction', []):
            event_term = event.get('reactionmeddrapt', '')
            if event_term:
                events[event_term] += 1
    
    for event, count in events.items():
        background_rate = 0.01
        total_background = 1000000
        
        prr = calculate_prr(
            count,
            total_drug_reports,
            background_rate * total_background,
            total_background
        )
        
        if prr and prr >= threshold:
            signal = {
                'event': event,
                'count': count,
                'prr': round(prr, 2),
                'confidence_interval': calculate_confidence_interval(count, total_drug_reports)
            }
            signals.append(signal)
    
    return sorted(signals, key=lambda x: x['prr'], reverse=True)

def calculate_confidence_interval(count, total):
    """
    Calculate 95% confidence interval for proportion
    """
    if total == 0:
        return None
    
    proportion = count / total
    z = 1.96
    
    try:
        standard_error = ((proportion * (1 - proportion)) / total) ** 0.5
        ci_lower = max(0, proportion - z * standard_error)
        ci_upper = min(1, proportion + z * standard_error)
        
        return {
            'lower': round(ci_lower, 3),
            'upper': round(ci_upper, 3)
        }
    except:
        return None

def format_response(data):
    """
    Format the response for Bedrock Agent
    """
    if not data['signals']:
        return "No safety signals were detected for the specified criteria."
    
    response_lines = []
    
    response_lines.append(f"Analysis Results for {data['product_name']}")
    response_lines.append(f"Analysis Period: {data['analysis_period']['start']} to {data['analysis_period']['end']}")
    response_lines.append(f"Total Reports: {data['total_reports']}")
    
    response_lines.append("\nTop Safety Signals:")
    for signal in data['signals']:
        ci = signal['confidence_interval']
        ci_text = f" (95% CI: {ci['lower']}-{ci['upper']})" if ci else ""
        response_lines.append(
            f"- {signal['event']}: PRR={signal['prr']}, Reports={signal['count']}{ci_text}"
        )
    
    if data['trends']['daily_counts']:
        dates = sorted(data['trends']['daily_counts'].keys())
        response_lines.extend([
            "\nTrend Analysis:",
            f"Report dates: {dates[0]} to {dates[-1]}",
            f"Peak daily reports: {max(data['trends']['daily_counts'].values())}"
        ])
    
    return "\n".join(response_lines)

def parse_parameters(event):
    """
    Parse parameters from Bedrock Agent event
    """
    logger.info(f"Parsing parameters from event: {json.dumps(event)}")
    
    parameters = {}
    if 'parameters' in event:
        for param in event['parameters']:
            name = param.get('name')
            value = param.get('value')
            if name and value is not None:
                parameters[name] = value
    
    product_name = parameters.get('product_name')
    if not product_name:
        raise ValueError("Product name is required")
    
    try:
        time_period = int(parameters.get('time_period', 6))
    except (TypeError, ValueError):
        time_period = 6
    
    try:
        signal_threshold = float(parameters.get('signal_threshold', 2.0))
    except (TypeError, ValueError):
        signal_threshold = 2.0
    
    return product_name, time_period, signal_threshold

def create_response(event, result):
    """
    Create a properly formatted response for Bedrock Agent
    """
    return {
        "response": {
            "actionGroup": event["actionGroup"],
            "function": event["function"],
            "functionResponse": {
                "responseBody": {
                    "TEXT": {
                        "body": result
                    }
                }
            }
        }
    }

def lambda_handler(event, context):
    """
    Lambda handler for adverse event analysis
    """
    try:
        logger.info(f"Received event: {json.dumps(event)}")
        
        try:
            product_name, time_period, signal_threshold = parse_parameters(event)
        except ValueError as e:
            return create_response(event, str(e))
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30*time_period)
        
        data = query_openfda(
            product_name,
            start_date.strftime('%Y%m%d'),
            end_date.strftime('%Y%m%d')
        )
        
        if not data['results']:
            return create_response(
                event,
                f"No adverse event reports found for {product_name} in the specified time period."
            )
        
        trends = analyze_trends(data)
        signals = detect_signals(data, signal_threshold)
        
        response_data = {
            'product_name': product_name,
            'analysis_period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            },
            'total_reports': len(data['results']),
            'trends': trends,
            'signals': signals[:10]
        }
        
        return create_response(event, format_response(response_data))
        
    except urllib.error.HTTPError as e:
        return create_response(event, f"OpenFDA API error: {e.reason}")
    except Exception as e:
        return create_response(event, f"An error occurred while analyzing adverse events: {str(e)}")
