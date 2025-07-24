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
    search_query = (
        f'(patient.drug.medicinalproduct:"{product_name}" OR '
        f'patient.drug.openfda.generic_name:"{product_name}" OR '
        f'patient.drug.openfda.brand_name:"{product_name}") '
        f'AND receivedate:[{start_date} TO {end_date}]'
    )
    all_results = []
    batch_size = 100
    max_results = 1000
    total_available = 0
    
    try:
        for skip in range(0, max_results, batch_size):
            params = {
                'search': search_query,
                'limit': min(batch_size, max_results - skip),
                'skip': skip
            }
            
            url = f"{base_url}?{urllib.parse.urlencode(params)}"
            logger.info(f"OpenFDA API URL (batch {skip//batch_size + 1}): {url}")
            
            req = urllib.request.Request(url, headers={'Accept': 'application/json'})
            with urllib.request.urlopen(req, timeout=30) as response:
                data = json.loads(response.read().decode())
                
                if skip == 0:  # First batch
                    total_available = data.get('meta', {}).get('results', {}).get('total', 0)
                    if total_available > max_results:
                        logger.info(f"Note: Only retrieving {max_results} out of {total_available} total reports")
                
                results = data.get('results', [])
                if not results:
                    break
                
                all_results.extend(results)
                logger.info(f"Batch {skip//batch_size + 1}: Retrieved {len(results)} reports (total so far: {len(all_results)})")
                
                if len(results) < batch_size:
                    break
            
        return {'results': all_results, 'total_available': total_available}
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
    daily_counts = defaultdict(lambda: {"total": 0, "serious": 0})
    monthly_counts = defaultdict(lambda: {"total": 0, "serious": 0})
    
    for report in data['results']:
        date_str = report.get('receivedate', '')
        if date_str:
            try:
                date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
                month = f"{date_str[:4]}-{date_str[4:6]}"
                
                is_serious = report.get('serious') == '1'
                daily_counts[date]["total"] += 1
                monthly_counts[month]["total"] += 1
                if is_serious:
                    daily_counts[date]["serious"] += 1
                    monthly_counts[month]["serious"] += 1
            except IndexError:
                continue
    
    dates = sorted(daily_counts.keys())
    moving_average = defaultdict(dict)
    
    for i, date in enumerate(dates):
        if i >= 3 and i < len(dates) - 3:
            total_window_sum = sum(daily_counts[dates[j]]["total"] for j in range(i-3, i+4))
            serious_window_sum = sum(daily_counts[dates[j]]["serious"] for j in range(i-3, i+4))
            moving_average[date]["total"] = round(total_window_sum / 7, 2)
            moving_average[date]["serious"] = round(serious_window_sum / 7, 2)
    
    return {
        'daily_counts': {k: dict(v) for k, v in daily_counts.items()},
        'monthly_counts': {k: dict(v) for k, v in monthly_counts.items()},
        'moving_average': dict(moving_average)
    }

def detect_signals(data, threshold=2.0):
    """
    Detect safety signals using PRR calculation
    """
    signals = []
    total_drug_reports = len(data['results'])
    
    if total_drug_reports == 0:
        return []
    
    events = {}
    for report in data['results']:
        reactions = report.get('patient', {}).get('reaction', [])
        is_serious = report.get('serious') == '1'
        
        for event in reactions:
            event_term = event.get('reactionmeddrapt', '')
            if event_term:
                if event_term not in events:
                    events[event_term] = {
                        'count': 0,
                        'serious_count': 0
                    }
                events[event_term]['count'] += 1
                if is_serious:
                    events[event_term]['serious_count'] += 1
    
    for event, event_data in events.items():
        count = event_data['count']
        background_rate = 0.01
        total_background = 1000000
        
        prr = calculate_prr(
            count,
            total_drug_reports,
            background_rate * total_background,
            total_background
        )
        
        if prr and prr >= threshold:
            signals.append({
                'event': event,
                'count': count,
                'serious_count': event_data['serious_count'],
                'serious_percentage': round(event_data['serious_count'] / count * 100, 2),
                'prr': round(prr, 2),
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
    Format the response for Bedrock
    """
    response_lines = []
    
    response_lines.append(f"Analysis Results for {data['product_name']}")
    response_lines.append(f"Analysis Period: {data['analysis_period']['start']} to {data['analysis_period']['end']}")
    if 'total_available' in data and data['total_available'] > data['total_reports']:
        response_lines.append(f"Total Reports: {data['total_reports']} (showing top {data['total_reports']} out of {data['total_available']} available reports)")
    else:
        response_lines.append(f"Total Reports: {data['total_reports']}")
    
    if data['signals']:
        response_lines.append("\nTop Safety Signals:")
        for signal in data['signals'][:5]:  # Show top 5 signals
            ci = signal['confidence_interval']
            ci_text = f" (95% CI: {ci['lower']}-{ci['upper']})" if ci else ""
            response_lines.extend([
                f"- {signal['event']}:",
                f"  * PRR: {signal['prr']}",
                f"  * Reports: {signal['count']} ({signal['serious_percentage']}% serious){ci_text}"
            ])
    else:
        response_lines.append("\nNo significant safety signals detected.")
    
    if data['trends']['daily_counts']:
        dates = sorted(data['trends']['daily_counts'].keys())
        response_lines.extend([
            "\nTrend Analysis:",
            f"Report dates: {dates[0]} to {dates[-1]}",
            f"Peak daily reports: {max(v['total'] for v in data['trends']['daily_counts'].values())}"
        ])
    
    return "\n".join(response_lines)

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
    Create a properly formatted response for Bedrock
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
        
        # Use 2025-04-28 as end date (latest available data in OpenFDA)
        end_date = datetime(2025, 4, 28)
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
            'total_available': data.get('total_available'),
            'trends': trends,
            'signals': signals[:10]
        }
        
        return create_response(event, format_response(response_data))
        
    except urllib.error.HTTPError as e:
        return create_response(event, f"OpenFDA API error: {e.reason}")
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}", exc_info=True)
        return create_response(event, f"An error occurred while analyzing adverse events: {str(e)}")
