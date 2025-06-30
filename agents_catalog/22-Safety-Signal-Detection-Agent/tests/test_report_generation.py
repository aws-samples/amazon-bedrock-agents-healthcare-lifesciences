import os
import sys
import json
import pytest
from unittest.mock import patch, MagicMock
import matplotlib
matplotlib.use('Agg')  # Set non-interactive backend for testing
import matplotlib.pyplot as plt
import base64

# Add Lambda function directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../action-groups/report-generation'))

from lambda_function import (
    lambda_handler,
    create_time_series_plot,
    create_signal_bar_chart,
    create_signal_heatmap,
    generate_html_report,
    upload_to_s3
)

# Test data
SAMPLE_TRENDS = {
    'daily_counts': {
        '2025-01-01': 10,
        '2025-01-02': 15,
        '2025-01-03': 12
    },
    'moving_average': {
        '2025-01-01': 10,
        '2025-01-02': 12.5,
        '2025-01-03': 12.3
    }
}

SAMPLE_SIGNALS = [
    {
        'event': 'Headache',
        'count': 100,
        'prr': 2.5,
        'confidence_interval': {'lower': 1.8, 'upper': 3.2}
    },
    {
        'event': 'Dizziness',
        'count': 50,
        'prr': 1.8,
        'confidence_interval': {'lower': 1.2, 'upper': 2.4}
    }
]

SAMPLE_ANALYSIS_RESULTS = {
    'product_name': 'SAMPLE_DRUG',
    'analysis_period': {
        'start': '2025-01-01',
        'end': '2025-06-30'
    },
    'total_reports': 1000,
    'trends': SAMPLE_TRENDS,
    'signals': SAMPLE_SIGNALS
}

SAMPLE_EVIDENCE_DATA = {
    'literature': [
        {
            'title': 'Sample Article',
            'abstract': 'Sample abstract text',
            'year': '2025',
            'pmid': '12345678'
        }
    ],
    'label_info': {
        'warnings': ['Sample warning'],
        'adverse_reactions': ['Sample reaction']
    },
    'causality_assessment': {
        'evidence_level': 'Moderate',
        'causality_score': 3,
        'assessment_date': '2025-06-30T00:00:00'
    }
}

def test_create_time_series_plot():
    """Test time series plot creation"""
    plot = create_time_series_plot(SAMPLE_TRENDS)
    
    assert isinstance(plot, str)
    # Verify it's a valid base64 string
    try:
        base64.b64decode(plot)
        is_valid_base64 = True
    except:
        is_valid_base64 = False
    assert is_valid_base64

def test_create_signal_bar_chart():
    """Test signal bar chart creation"""
    plot = create_signal_bar_chart(SAMPLE_SIGNALS)
    
    assert isinstance(plot, str)
    # Verify it's a valid base64 string
    try:
        base64.b64decode(plot)
        is_valid_base64 = True
    except:
        is_valid_base64 = False
    assert is_valid_base64

def test_create_signal_heatmap():
    """Test signal heatmap creation"""
    plot = create_signal_heatmap(SAMPLE_SIGNALS)
    
    assert isinstance(plot, str)
    # Verify it's a valid base64 string
    try:
        base64.b64decode(plot)
        is_valid_base64 = True
    except:
        is_valid_base64 = False
    assert is_valid_base64

def test_generate_html_report():
    """Test HTML report generation"""
    report = generate_html_report(SAMPLE_ANALYSIS_RESULTS, SAMPLE_EVIDENCE_DATA)
    
    assert isinstance(report, str)
    assert 'Safety Signal Detection Report' in report
    assert 'SAMPLE_DRUG' in report
    assert 'Trend Analysis' in report
    assert 'Signal Detection Results' in report
    assert 'Evidence Assessment' in report
    assert 'data:image/png;base64' in report  # Check for embedded images

@patch('boto3.client')
def test_upload_to_s3(mock_boto3_client):
    """Test S3 upload"""
    mock_s3 = MagicMock()
    mock_boto3_client.return_value = mock_s3
    
    result = upload_to_s3(
        'Sample HTML content',
        'test-bucket',
        'SAMPLE_DRUG'
    )
    
    assert isinstance(result, str)
    assert result.startswith('s3://')
    mock_s3.put_object.assert_called_once()

def test_lambda_handler():
    """Test Lambda handler"""
    # Test with valid input
    event = {
        'body': json.dumps({
            'analysis_results': SAMPLE_ANALYSIS_RESULTS,
            'evidence_data': SAMPLE_EVIDENCE_DATA,
            'include_graphs': True
        })
    }
    
    with patch('lambda_function.upload_to_s3') as mock_upload, \
         patch.dict(os.environ, {'REPORT_BUCKET_NAME': 'test-bucket'}):
        mock_upload.return_value = 's3://test-bucket/reports/test.html'

        response = lambda_handler(event, None)
    
    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert 'report_url' in body
    assert 'timestamp' in body

    # Test with invalid input
    event = {
        'body': json.dumps({})
    }
    response = lambda_handler(event, None)
    assert response['statusCode'] == 400
    assert 'error' in json.loads(response['body'])

    # Test with missing S3 bucket configuration
    event = {
        'body': json.dumps({
            'analysis_results': SAMPLE_ANALYSIS_RESULTS,
            'evidence_data': SAMPLE_EVIDENCE_DATA
        })
    }
    with patch.dict(os.environ, {}, clear=True):  # Remove all env vars
        response = lambda_handler(event, None)
        assert response['statusCode'] == 500
        assert 'error' in json.loads(response['body'])

if __name__ == '__main__':
    pytest.main([__file__])
