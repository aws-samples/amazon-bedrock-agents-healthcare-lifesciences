import json
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
import sys
import os

# Add the action-groups directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'action-groups', 'adverse-event-analysis'))

import lambda_function

class TestAdverseEventAnalysis(unittest.TestCase):
    def setUp(self):
        self.mock_openfda_response = {
            'results': [
                {
                    'receiptdate': '20250101',
                    'patient': {
                        'reaction': [
                            {'reactionmeddrapt': 'Headache'},
                            {'reactionmeddrapt': 'Nausea'}
                        ]
                    }
                },
                {
                    'receiptdate': '20250102',
                    'patient': {
                        'reaction': [
                            {'reactionmeddrapt': 'Headache'},
                            {'reactionmeddrapt': 'Dizziness'}
                        ]
                    }
                }
            ]
        }

        self.mock_bedrock_event = {
            'messageVersion': '1.0',
            'function': 'analyze_adverse_events',
            'parameters': [
                {
                    'name': 'product_name',
                    'type': 'string',
                    'value': 'test_product'
                },
                {
                    'name': 'time_period',
                    'type': 'integer',
                    'value': '6'
                },
                {
                    'name': 'signal_threshold',
                    'type': 'number',
                    'value': '2.0'
                }
            ]
        }

    def test_calculate_prr(self):
        # Test normal case
        self.assertAlmostEqual(
            lambda_function.calculate_prr(10, 100, 20, 1000),
            5.0
        )

        # Test zero cases
        self.assertIsNone(lambda_function.calculate_prr(0, 100, 20, 1000))
        self.assertIsNone(lambda_function.calculate_prr(10, 0, 20, 1000))
        self.assertIsNone(lambda_function.calculate_prr(10, 100, 0, 1000))
        self.assertIsNone(lambda_function.calculate_prr(10, 100, 20, 0))

    def test_analyze_trends(self):
        trends = lambda_function.analyze_trends(self.mock_openfda_response)
        
        self.assertIn('daily_counts', trends)
        self.assertIn('moving_average', trends)
        self.assertEqual(len(trends['daily_counts']), 2)
        self.assertEqual(trends['daily_counts']['20250101'], 1)
        self.assertEqual(trends['daily_counts']['20250102'], 1)

    def test_detect_signals(self):
        signals = lambda_function.detect_signals(self.mock_openfda_response, threshold=1.0)
        
        self.assertTrue(isinstance(signals, list))
        self.assertTrue(all(isinstance(s, dict) for s in signals))
        
        # Check signal structure
        for signal in signals:
            self.assertIn('event', signal)
            self.assertIn('count', signal)
            self.assertIn('prr', signal)
            self.assertIn('confidence_interval', signal)

    def test_calculate_confidence_interval(self):
        ci = lambda_function.calculate_confidence_interval(10, 100)
        
        self.assertIsNotNone(ci)
        self.assertIn('lower', ci)
        self.assertIn('upper', ci)
        self.assertTrue(0 <= ci['lower'] <= ci['upper'] <= 1)

    @patch('urllib.request.urlopen')
    def test_query_openfda(self, mock_urlopen):
        # Mock the API response
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(self.mock_openfda_response).encode()
        mock_urlopen.return_value.__enter__.return_value = mock_response

        # Test the function
        result = lambda_function.query_openfda(
            'test_product',
            '20250101',
            '20250102'
        )

        self.assertEqual(result, self.mock_openfda_response)

    def test_format_response(self):
        data = {
            'product_name': 'Test Product',
            'analysis_period': {
                'start': '2025-01-01T00:00:00',
                'end': '2025-06-30T00:00:00'
            },
            'total_reports': 2,
            'trends': {
                'daily_counts': {'20250101': 1, '20250102': 1},
                'moving_average': {}
            },
            'signals': [
                {
                    'event': 'Headache',
                    'count': 2,
                    'prr': 2.5,
                    'confidence_interval': {'lower': 0.1, 'upper': 0.3}
                }
            ]
        }

        response = lambda_function.format_response(data)
        
        self.assertIsInstance(response, str)
        self.assertIn('Test Product', response)
        self.assertIn('Headache', response)
        self.assertIn('PRR=2.5', response)

    def test_parse_parameters(self):
        # Test with valid parameters
        product_name, time_period, signal_threshold = lambda_function.parse_parameters(self.mock_bedrock_event)
        self.assertEqual(product_name, 'test_product')
        self.assertEqual(time_period, 6)
        self.assertEqual(signal_threshold, 2.0)

        # Test with missing product name
        event_without_product = {
            'messageVersion': '1.0',
            'function': 'analyze_adverse_events',
            'parameters': [
                {
                    'name': 'time_period',
                    'type': 'integer',
                    'value': '6'
                }
            ]
        }
        with self.assertRaises(ValueError):
            lambda_function.parse_parameters(event_without_product)

        # Test with invalid time period
        event_invalid_time = {
            'messageVersion': '1.0',
            'function': 'analyze_adverse_events',
            'parameters': [
                {
                    'name': 'product_name',
                    'type': 'string',
                    'value': 'test_product'
                },
                {
                    'name': 'time_period',
                    'type': 'integer',
                    'value': 'invalid'
                }
            ]
        }
        product_name, time_period, signal_threshold = lambda_function.parse_parameters(event_invalid_time)
        self.assertEqual(time_period, 6)  # Should use default value

    def test_lambda_handler(self):
        # Mock the OpenFDA API call
        with patch('lambda_function.query_openfda') as mock_query:
            mock_query.return_value = self.mock_openfda_response

            # Test with valid input
            response = lambda_function.lambda_handler(self.mock_bedrock_event, None)
            
            self.assertEqual(response['messageVersion'], '1.0')
            self.assertIn('response', response)
            self.assertIsInstance(response['response'], str)

            # Test with missing product name
            event_without_product = {
                'messageVersion': '1.0',
                'function': 'analyze_adverse_events',
                'parameters': [
                    {
                        'name': 'time_period',
                        'type': 'integer',
                        'value': '6'
                    }
                ]
            }
            response = lambda_function.lambda_handler(event_without_product, None)
            
            self.assertEqual(response['messageVersion'], '1.0')
            self.assertIn('response', response)
            self.assertIn('Product name is required', response['response'])

if __name__ == '__main__':
    unittest.main()
