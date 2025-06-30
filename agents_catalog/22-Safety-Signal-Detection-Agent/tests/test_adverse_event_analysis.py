import os
import sys
import json
import pytest
from unittest.mock import patch, MagicMock

# Add Lambda function directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../action-groups/adverse-event-analysis'))

from lambda_function import (
    lambda_handler,
    calculate_prr,
    query_openfda,
    analyze_trends,
    detect_signals
)

# Test data
SAMPLE_ADVERSE_EVENT_RESPONSE = {
    "meta": {
        "disclaimer": "Sample disclaimer",
        "terms": "Sample terms",
        "license": "Sample license",
        "last_updated": "2025-06-30",
        "results": {
            "skip": 0,
            "limit": 100,
            "total": 1000
        }
    },
    "results": [
        {
            "receiptdate": "20250101",
            "patient": {
                "reaction": [
                    {
                        "reactionmeddrapt": "Headache",
                        "reactionoutcome": "1"
                    }
                ],
                "drug": [
                    {
                        "medicinalproduct": "SAMPLE_DRUG",
                        "drugcharacterization": "1"
                    }
                ]
            }
        }
    ]
}

def test_calculate_prr():
    """Test PRR calculation"""
    # Test normal case
    assert calculate_prr(10, 100, 20, 1000) == pytest.approx(5.0)
    
    # Test edge cases
    assert calculate_prr(0, 100, 20, 1000) == None  # Zero numerator
    assert calculate_prr(10, 0, 20, 1000) == None   # Division by zero
    assert calculate_prr(10, 100, 0, 1000) == None  # Zero denominator

@patch('urllib.request.urlopen')
def test_query_openfda(mock_urlopen):
    """Test OpenFDA API query"""
    # Mock response
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps(SAMPLE_ADVERSE_EVENT_RESPONSE).encode()
    mock_urlopen.return_value.__enter__.return_value = mock_response
    
    # Test query
    result = query_openfda("SAMPLE_DRUG", "20250101", "20250630")
    
    assert result == SAMPLE_ADVERSE_EVENT_RESPONSE
    assert len(result['results']) == 1
    assert result['results'][0]['patient']['drug'][0]['medicinalproduct'] == "SAMPLE_DRUG"

def test_analyze_trends():
    """Test trend analysis"""
    result = analyze_trends(SAMPLE_ADVERSE_EVENT_RESPONSE)
    
    assert 'daily_counts' in result
    assert 'moving_average' in result
    assert isinstance(result['daily_counts'], dict)
    assert isinstance(result['moving_average'], dict)

def test_detect_signals():
    """Test signal detection"""
    signals = detect_signals(SAMPLE_ADVERSE_EVENT_RESPONSE, threshold=1.5)
    
    assert isinstance(signals, list)
    for signal in signals:
        assert 'event' in signal
        assert 'count' in signal
        assert 'prr' in signal
        assert 'confidence_interval' in signal

def test_lambda_handler():
    """Test Lambda handler"""
    # Test with valid input
    event = {
        'body': json.dumps({
            'product_name': 'SAMPLE_DRUG',
            'time_period': 6,
            'signal_threshold': 2.0
        })
    }
    
    with patch('lambda_function.query_openfda') as mock_query:
        mock_query.return_value = SAMPLE_ADVERSE_EVENT_RESPONSE
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert 'product_name' in body
        assert 'analysis_period' in body
        assert 'total_reports' in body
        assert 'trends' in body
        assert 'signals' in body

    # Test with invalid input
    event = {
        'body': json.dumps({})
    }
    response = lambda_handler(event, None)
    assert response['statusCode'] == 400
    assert 'error' in json.loads(response['body'])

if __name__ == '__main__':
    pytest.main([__file__])
