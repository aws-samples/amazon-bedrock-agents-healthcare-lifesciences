import os
import sys
import json
import pytest
from unittest.mock import patch, MagicMock
import xml.etree.ElementTree as ET

# Add Lambda function directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../action-groups/evidence-assessment'))

from lambda_function import (
    lambda_handler,
    search_pubmed,
    query_fda_label,
    assess_causality
)

# Test data
SAMPLE_PUBMED_SEARCH_RESPONSE = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE eSearchResult PUBLIC "-//NLM//DTD esearch 20060628//EN" "https://eutils.ncbi.nlm.nih.gov/eutils/dtd/20060628/esearch.dtd">
<eSearchResult>
    <Count>10</Count>
    <RetMax>10</RetMax>
    <RetStart>0</RetStart>
    <IdList>
        <Id>12345678</Id>
    </IdList>
</eSearchResult>"""

SAMPLE_PUBMED_FETCH_RESPONSE = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE PubmedArticleSet PUBLIC "-//NLM//DTD PubMedArticle, 1st January 2024//EN" "https://dtd.nlm.nih.gov/ncbi/pubmed/out/pubmed_190101.dtd">
<PubmedArticleSet>
    <PubmedArticle>
        <MedlineCitation Status="MEDLINE">
            <PMID Version="1">12345678</PMID>
            <Article>
                <ArticleTitle>Sample Article Title</ArticleTitle>
                <Abstract>
                    <AbstractText>Sample abstract text.</AbstractText>
                </Abstract>
            </Article>
            <DateCompleted>
                <Year>2025</Year>
            </DateCompleted>
        </MedlineCitation>
    </PubmedArticle>
</PubmedArticleSet>"""

SAMPLE_FDA_LABEL_RESPONSE = {
    "meta": {
        "disclaimer": "Sample disclaimer",
        "terms": "Sample terms",
        "license": "Sample license",
        "last_updated": "2025-06-30",
        "results": {
            "skip": 0,
            "limit": 1,
            "total": 1
        }
    },
    "results": [
        {
            "warnings": ["Sample warning"],
            "adverse_reactions": ["Sample adverse reaction"],
            "boxed_warning": ["Sample boxed warning"],
            "contraindications": ["Sample contraindication"]
        }
    ]
}

@patch('urllib.request.urlopen')
def test_search_pubmed(mock_urlopen):
    """Test PubMed search"""
    # Mock responses for search and fetch
    mock_search_response = MagicMock()
    mock_search_response.read.return_value = SAMPLE_PUBMED_SEARCH_RESPONSE.encode()
    
    mock_fetch_response = MagicMock()
    mock_fetch_response.read.return_value = SAMPLE_PUBMED_FETCH_RESPONSE.encode()
    
    mock_urlopen.return_value.__enter__.side_effect = [
        mock_search_response,
        mock_fetch_response
    ]
    
    # Test search
    articles = search_pubmed("SAMPLE_DRUG", "Headache")
    
    assert isinstance(articles, list)
    assert len(articles) == 1
    assert articles[0]['pmid'] == "12345678"
    assert articles[0]['title'] == "Sample Article Title"
    assert articles[0]['abstract'] == "Sample abstract text."
    assert articles[0]['year'] == "2025"

@patch('urllib.request.urlopen')
def test_query_fda_label(mock_urlopen):
    """Test FDA Label API query"""
    # Mock response
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps(SAMPLE_FDA_LABEL_RESPONSE).encode()
    mock_urlopen.return_value.__enter__.return_value = mock_response
    
    # Test query
    result = query_fda_label("SAMPLE_DRUG")
    
    assert isinstance(result, dict)
    assert 'warnings' in result
    assert 'adverse_reactions' in result
    assert 'boxed_warnings' in result
    assert 'contraindications' in result

def test_assess_causality():
    """Test causality assessment"""
    # Test with strong evidence
    literature = [{'title': 'Article 1'}, {'title': 'Article 2'}, 
                 {'title': 'Article 3'}, {'title': 'Article 4'},
                 {'title': 'Article 5'}]
    label_info = {'boxed_warnings': ['Warning 1']}
    
    assessment = assess_causality(literature, label_info)
    assert assessment['evidence_level'] == "Strong"
    assert assessment['causality_score'] > 0
    assert 'assessment_date' in assessment
    
    # Test with moderate evidence
    literature = [{'title': 'Article 1'}, {'title': 'Article 2'}]
    label_info = {'warnings': ['Warning 1']}
    
    assessment = assess_causality(literature, label_info)
    assert assessment['evidence_level'] == "Moderate"
    assert assessment['causality_score'] > 0
    
    # Test with insufficient evidence
    literature = []
    label_info = {}
    
    assessment = assess_causality(literature, label_info)
    assert assessment['evidence_level'] == "Insufficient"
    assert assessment['causality_score'] == 0

def test_lambda_handler():
    """Test Lambda handler"""
    # Test with valid input
    event = {
        'body': json.dumps({
            'product_name': 'SAMPLE_DRUG',
            'adverse_event': 'Headache',
            'include_pubmed': True,
            'include_label': True
        })
    }
    
    with patch('lambda_function.search_pubmed') as mock_search, \
         patch('lambda_function.query_fda_label') as mock_label:
        
        mock_search.return_value = [
            {
                'title': 'Sample Article',
                'abstract': 'Sample abstract',
                'year': '2025',
                'pmid': '12345678'
            }
        ]
        mock_label.return_value = {
            'warnings': ['Sample warning'],
            'adverse_reactions': ['Sample reaction']
        }
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert 'product_name' in body
        assert 'adverse_event' in body
        assert 'literature' in body
        assert 'label_info' in body
        assert 'causality_assessment' in body

    # Test with invalid input
    event = {
        'body': json.dumps({})
    }
    response = lambda_handler(event, None)
    assert response['statusCode'] == 400
    assert 'error' in json.loads(response['body'])

if __name__ == '__main__':
    pytest.main([__file__])
