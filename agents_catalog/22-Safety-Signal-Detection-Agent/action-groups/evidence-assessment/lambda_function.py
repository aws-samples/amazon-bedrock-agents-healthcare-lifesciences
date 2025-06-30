import json
import logging
import os
import urllib.request
import urllib.parse
from datetime import datetime
import xml.etree.ElementTree as ET

# Configure logging
logger = logging.getLogger()
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))

def search_pubmed(product_name, adverse_event):
    """
    Search PubMed for literature about the drug and adverse event
    """
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    
    # Construct search query
    search_term = f'"{product_name}"[Title/Abstract] AND "{adverse_event}"[Title/Abstract] AND "adverse effects"[Subheading]'
    
    # First get the list of PMIDs
    search_url = f"{base_url}/esearch.fcgi"
    params = {
        'db': 'pubmed',
        'term': search_term,
        'retmax': 10,
        'sort': 'relevance'
    }
    
    try:
        # Get PMIDs
        url = f"{search_url}?{urllib.parse.urlencode(params)}"
        with urllib.request.urlopen(url) as response:
            search_data = response.read()
            root = ET.fromstring(search_data)
            pmids = [id_elem.text for id_elem in root.findall('.//Id')]
            
        if not pmids:
            return []
            
        # Get article summaries
        fetch_url = f"{base_url}/efetch.fcgi"
        fetch_params = {
            'db': 'pubmed',
            'id': ','.join(pmids),
            'rettype': 'abstract',
            'retmode': 'xml'
        }
        
        url = f"{fetch_url}?{urllib.parse.urlencode(fetch_params)}"
        with urllib.request.urlopen(url) as response:
            fetch_data = response.read()
            root = ET.fromstring(fetch_data)
            
        articles = []
        for article in root.findall('.//PubmedArticle'):
            try:
                title = article.find('.//ArticleTitle').text
                abstract = article.find('.//Abstract/AbstractText')
                abstract_text = abstract.text if abstract is not None else "No abstract available"
                year = article.find('.//DateCompleted/Year')
                if year is None:
                    year = article.find('.//PubDate/Year')
                year_text = year.text if year is not None else "Year not available"
                
                articles.append({
                    'title': title,
                    'abstract': abstract_text,
                    'year': year_text,
                    'pmid': article.find('.//PMID').text
                })
            except Exception as e:
                logger.warning(f"Error parsing article: {str(e)}")
                continue
                
        return articles
        
    except Exception as e:
        logger.error(f"Error searching PubMed: {str(e)}")
        raise

def query_fda_label(product_name):
    """
    Query FDA Label API for product labeling information
    """
    base_url = "https://api.fda.gov/drug/label.json"
    
    params = {
        'search': f'openfda.brand_name:"{product_name}" OR openfda.generic_name:"{product_name}"',
        'limit': 1
    }
    
    try:
        url = f"{base_url}?{urllib.parse.urlencode(params)}"
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read().decode())
            
        if data['results']:
            label = data['results'][0]
            return {
                'warnings': label.get('warnings', []),
                'adverse_reactions': label.get('adverse_reactions', []),
                'boxed_warnings': label.get('boxed_warning', []),
                'contraindications': label.get('contraindications', [])
            }
        return None
        
    except Exception as e:
        logger.error(f"Error querying FDA Label API: {str(e)}")
        raise

def assess_causality(literature, label_info):
    """
    Perform basic causality assessment based on available evidence
    """
    evidence_level = "Insufficient"
    causality_score = 0
    
    # Check label information and literature evidence
    if label_info:
        if 'boxed_warnings' in label_info and label_info['boxed_warnings']:
            causality_score += 3
            evidence_level = "Strong"
        elif 'warnings' in label_info and label_info['warnings']:
            causality_score += 2
            evidence_level = "Moderate"
        elif 'adverse_reactions' in label_info and label_info['adverse_reactions']:
            causality_score += 1
            evidence_level = "Possible"
    
    # Check literature evidence and update evidence level
    if literature:
        num_articles = len(literature)
        if num_articles >= 5:
            causality_score += 2
            if evidence_level != "Strong":
                evidence_level = "Moderate"
        elif num_articles >= 2:
            causality_score += 1
            if evidence_level == "Insufficient":
                evidence_level = "Moderate"
    
    return {
        'evidence_level': evidence_level,
        'causality_score': causality_score,
        'assessment_date': datetime.now().isoformat()
    }

def lambda_handler(event, context):
    """
    Lambda handler for evidence assessment
    """
    try:
        logger.info(f"Received event: {json.dumps(event)}")
        
        # Parse input parameters
        body = json.loads(event.get('body', '{}'))
        product_name = body.get('product_name')
        adverse_event = body.get('adverse_event')
        include_pubmed = body.get('include_pubmed', True)
        include_label = body.get('include_label', True)
        
        if not product_name or not adverse_event:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Product name and adverse event are required'
                })
            }
        
        evidence = {
            'product_name': product_name,
            'adverse_event': adverse_event
        }
        
        # Get literature evidence
        if include_pubmed:
            evidence['literature'] = search_pubmed(product_name, adverse_event)
        
        # Get label information
        if include_label:
            evidence['label_info'] = query_fda_label(product_name)
        
        # Assess causality
        evidence['causality_assessment'] = assess_causality(
            evidence.get('literature', []),
            evidence.get('label_info', None)
        )
        
        return {
            'statusCode': 200,
            'body': json.dumps(evidence)
        }
        
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': f"Internal server error: {str(e)}"
            })
        }
