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
    Search PubMed for literature evidence
    """
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    search_term = f'"{product_name}"[Title/Abstract] AND "{adverse_event}"[Title/Abstract] AND "adverse effects"[Subheading]'
    search_url = f"{base_url}/esearch.fcgi"
    params = {
        'db': 'pubmed',
        'term': search_term,
        'retmax': 10,
        'sort': 'relevance'
    }

    try:
        url = f"{search_url}?{urllib.parse.urlencode(params)}"
        with urllib.request.urlopen(url) as response:
            search_data = response.read()
            root = ET.fromstring(search_data)
            pmids = [id_elem.text for id_elem in root.findall('.//Id')]

        if not pmids:
            return []

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
    Query FDA Label API for product information
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
    Assess causality based on available evidence
    """
    evidence_level = "Insufficient"
    causality_score = 0

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

def format_response(evidence):
    """
    Format the response for Bedrock
    """
    response_lines = []
    
    response_lines.append(f"Evidence Assessment for {evidence['product_name']} - {evidence['adverse_event']}")
    
    if evidence.get('literature'):
        response_lines.append("\nLiterature Evidence:")
        for article in evidence['literature']:
            response_lines.append(f"- {article['title']} ({article['year']}, PMID: {article['pmid']})")
            response_lines.append(f"  Abstract: {article['abstract'][:200]}...")
    else:
        response_lines.append("\nNo relevant literature evidence found.")
    
    if evidence.get('label_info'):
        response_lines.append("\nFDA Label Information:")
        label_info = evidence['label_info']
        if label_info.get('boxed_warnings'):
            response_lines.append("Boxed Warnings:")
            response_lines.append(label_info['boxed_warnings'][0][:200] + "...")
        if label_info.get('warnings'):
            response_lines.append("Warnings:")
            response_lines.append(label_info['warnings'][0][:200] + "...")
        if label_info.get('adverse_reactions'):
            response_lines.append("Adverse Reactions:")
            response_lines.append(label_info['adverse_reactions'][0][:200] + "...")
    else:
        response_lines.append("\nNo FDA label information found.")
    
    if evidence.get('causality_assessment'):
        assessment = evidence['causality_assessment']
        response_lines.extend([
            "\nCausality Assessment:",
            f"Evidence Level: {assessment['evidence_level']}",
            f"Causality Score: {assessment['causality_score']}"
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
    adverse_event = parameters.get('adverse_event')
    
    if not product_name or not adverse_event:
        raise ValueError("Product name and adverse event are required")
    
    include_pubmed = parameters.get('include_pubmed', 'true').lower() == 'true'
    include_label = parameters.get('include_label', 'true').lower() == 'true'
    
    return product_name, adverse_event, include_pubmed, include_label

def lambda_handler(event, context):
    """
    Lambda handler for evidence assessment
    """
    try:
        logger.info(f"Received event: {json.dumps(event)}")
        
        try:
            product_name, adverse_event, include_pubmed, include_label = parse_parameters(event)
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
        
        evidence = {
            'product_name': product_name,
            'adverse_event': adverse_event
        }
        
        if include_pubmed:
            evidence['literature'] = search_pubmed(product_name, adverse_event)
        
        if include_label:
            evidence['label_info'] = query_fda_label(product_name)
        
        evidence['causality_assessment'] = assess_causality(
            evidence.get('literature', []),
            evidence.get('label_info', None)
        )
        
        return {
            "response": {
                "actionGroup": event["actionGroup"],
                "function": event["function"],
                "functionResponse": {
                    "responseBody": {
                        "TEXT": {
                            "body": format_response(evidence)
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
                            "body": f"An error occurred while assessing evidence: {str(e)}"
                        }
                    }
                }
            }
        }
