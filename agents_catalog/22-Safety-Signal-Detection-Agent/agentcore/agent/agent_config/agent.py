import json
import logging
import os
import urllib.request
import urllib.parse
import urllib.error
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime, timedelta

import boto3
from strands import Agent, tool
from strands.models import BedrockModel

logger = logging.getLogger(__name__)

MODEL_ID = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"

SYSTEM_PROMPT = """You are an expert pharmacovigilance professional specializing in safety signal detection and evaluation. Help users analyze adverse event data and detect potential safety signals using OpenFDA data and supporting evidence from literature.

You have access to the following tools:

- analyze_adverse_events: Analyze adverse events from OpenFDA data, perform trend analysis, and detect safety signals using PRR calculation.
- assess_evidence: Gather and assess evidence for detected signals using PubMed literature and FDA label information.
- generate_report: Create comprehensive reports with visualizations of the analysis results.

Analysis Process

1. Begin by understanding what safety analysis the user is seeking.
2. Use analyze_adverse_events to retrieve and analyze adverse event data for the specified product.
3. Present initial findings and highlight any detected safety signals.
4. Use assess_evidence to gather supporting evidence for significant signals.
5. Use generate_report to create a comprehensive report with visualizations.
6. Present findings with appropriate pharmacovigilance context.

Response Guidelines

- Provide scientifically accurate analysis based on available data
- Explain pharmacovigilance concepts in accessible language while maintaining precision
- Include relevant visualizations and statistical analysis
- Highlight the strength of evidence for detected signals
- Make appropriate interpretations considering data limitations
- Suggest follow-up actions when warranted
- Always include evidence sources and data coverage:
  * Total number of available reports and number of reports analyzed
  * Time period covered by the analysis
  * Literature evidence with article titles, authors, and publication years
  * FDA label information with specific sections referenced
  * Strength of evidence assessment with clear rationale
- Clearly state any data limitations or gaps
- Support conclusions with specific data points:
  * PRR values with confidence intervals
  * Number of cases for each adverse event
  * Percentage of serious cases
  * Temporal trends in reporting
"""


def _calculate_prr(a, b, c, d):
    """Calculate Proportional Reporting Ratio (PRR)."""
    if a == 0 or b == 0:
        return None
    try:
        return (a / b) / (c / d)
    except ZeroDivisionError:
        return None


def _calculate_confidence_interval(count, total):
    """Calculate 95% confidence interval for proportion."""
    if total == 0:
        return None
    proportion = count / total
    z = 1.96
    try:
        se = ((proportion * (1 - proportion)) / total) ** 0.5
        return {
            "lower": round(max(0, proportion - z * se), 3),
            "upper": round(min(1, proportion + z * se), 3),
        }
    except Exception:
        return None


def _query_openfda(product_name, start_date, end_date):
    """Query OpenFDA API for adverse event reports."""
    base_url = "https://api.fda.gov/drug/event.json"
    search_query = (
        f'(patient.drug.medicinalproduct:"{product_name}" OR '
        f'patient.drug.openfda.generic_name:"{product_name}" OR '
        f'patient.drug.openfda.brand_name:"{product_name}") '
        f"AND receivedate:[{start_date} TO {end_date}]"
    )
    all_results = []
    batch_size = 100
    max_results = 1000
    total_available = 0

    try:
        for skip in range(0, max_results, batch_size):
            params = {
                "search": search_query,
                "limit": min(batch_size, max_results - skip),
                "skip": skip,
            }
            url = f"{base_url}?{urllib.parse.urlencode(params)}"
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=30) as response:
                data = json.loads(response.read().decode())
                if skip == 0:
                    total_available = data.get("meta", {}).get("results", {}).get("total", 0)
                results = data.get("results", [])
                if not results:
                    break
                all_results.extend(results)
                if len(results) < batch_size:
                    break
        return {"results": all_results, "total_available": total_available}
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return {"results": [], "total_available": 0}
        raise
    except Exception as e:
        logger.error(f"Error querying OpenFDA: {e}")
        raise


def _analyze_trends(data):
    """Analyze trends in adverse event reports."""
    daily_counts = defaultdict(lambda: {"total": 0, "serious": 0})
    monthly_counts = defaultdict(lambda: {"total": 0, "serious": 0})

    for report in data["results"]:
        date_str = report.get("receivedate", "")
        if date_str and len(date_str) >= 8:
            date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
            month = f"{date_str[:4]}-{date_str[4:6]}"
            is_serious = report.get("serious") == "1"
            daily_counts[date]["total"] += 1
            monthly_counts[month]["total"] += 1
            if is_serious:
                daily_counts[date]["serious"] += 1
                monthly_counts[month]["serious"] += 1

    return {
        "daily_counts": dict(daily_counts),
        "monthly_counts": dict(monthly_counts),
    }


def _detect_signals(data, threshold=2.0):
    """Detect safety signals using PRR calculation."""
    total_drug_reports = len(data["results"])
    if total_drug_reports == 0:
        return []

    events = {}
    for report in data["results"]:
        reactions = report.get("patient", {}).get("reaction", [])
        is_serious = report.get("serious") == "1"
        for event in reactions:
            term = event.get("reactionmeddrapt", "")
            if term:
                if term not in events:
                    events[term] = {"count": 0, "serious_count": 0}
                events[term]["count"] += 1
                if is_serious:
                    events[term]["serious_count"] += 1

    signals = []
    background_rate = 0.01
    total_background = 1000000

    for event_term, event_data in events.items():
        count = event_data["count"]
        prr = _calculate_prr(count, total_drug_reports, background_rate * total_background, total_background)
        if prr and prr >= threshold:
            signals.append({
                "event": event_term,
                "count": count,
                "serious_count": event_data["serious_count"],
                "serious_percentage": round(event_data["serious_count"] / count * 100, 2),
                "prr": round(prr, 2),
                "confidence_interval": _calculate_confidence_interval(count, total_drug_reports),
            })

    return sorted(signals, key=lambda x: x["prr"], reverse=True)


@tool
def analyze_adverse_events(
    product_name: str,
    time_period: int = 6,
    signal_threshold: float = 2.0,
) -> str:
    """Analyze adverse events and detect safety signals using OpenFDA data.

    Args:
        product_name: Name of the product to analyze.
        time_period: Analysis period in months (default: 6).
        signal_threshold: PRR threshold for signal detection (default: 2.0).
    """
    end_date = datetime(2025, 4, 28)
    start_date = end_date - timedelta(days=30 * time_period)

    data = _query_openfda(product_name, start_date.strftime("%Y%m%d"), end_date.strftime("%Y%m%d"))

    if not data["results"]:
        return f"No adverse event reports found for {product_name} in the specified time period."

    trends = _analyze_trends(data)
    signals = _detect_signals(data, signal_threshold)

    response_lines = [
        f"Analysis Results for {product_name}",
        f"Analysis Period: {start_date.date()} to {end_date.date()}",
        f"Total Reports: {len(data['results'])}",
    ]
    if data["total_available"] > len(data["results"]):
        response_lines.append(f"(showing {len(data['results'])} out of {data['total_available']} available)")

    if signals:
        response_lines.append("\nTop Safety Signals:")
        for sig in signals[:5]:
            ci = sig["confidence_interval"]
            ci_text = f" (95% CI: {ci['lower']}-{ci['upper']})" if ci else ""
            response_lines.append(f"- {sig['event']}: PRR={sig['prr']}, Reports={sig['count']} ({sig['serious_percentage']}% serious){ci_text}")
    else:
        response_lines.append("\nNo significant safety signals detected.")

    if trends["daily_counts"]:
        dates = sorted(trends["daily_counts"].keys())
        response_lines.append(f"\nTrend: {dates[0]} to {dates[-1]}, Peak daily reports: {max(v['total'] for v in trends['daily_counts'].values())}")

    return "\n".join(response_lines)


@tool
def assess_evidence(
    product_name: str,
    adverse_event: str,
    include_pubmed: bool = True,
    include_label: bool = True,
) -> str:
    """Gather and assess evidence for safety signals using PubMed and FDA label data.

    Args:
        product_name: Product name.
        adverse_event: Adverse event term to assess.
        include_pubmed: Include PubMed literature search.
        include_label: Include FDA label information.
    """
    evidence = {"product_name": product_name, "adverse_event": adverse_event}

    if include_pubmed:
        evidence["literature"] = _search_pubmed(product_name, adverse_event)

    if include_label:
        evidence["label_info"] = _query_fda_label(product_name)

    evidence["causality_assessment"] = _assess_causality(
        evidence.get("literature", []), evidence.get("label_info")
    )

    response_lines = [f"Evidence Assessment for {product_name} - {adverse_event}"]

    literature = evidence.get("literature", [])
    if literature:
        response_lines.append("\nLiterature Evidence:")
        for article in literature:
            response_lines.append(f"- {article['title']} ({article['year']}, PMID: {article['pmid']})")
    else:
        response_lines.append("\nNo relevant literature evidence found.")

    label_info = evidence.get("label_info")
    if label_info:
        response_lines.append("\nFDA Label Information:")
        if label_info.get("boxed_warnings"):
            response_lines.append(f"Boxed Warnings: {label_info['boxed_warnings'][0][:200]}...")
        if label_info.get("warnings"):
            response_lines.append(f"Warnings: {label_info['warnings'][0][:200]}...")
        if label_info.get("adverse_reactions"):
            response_lines.append(f"Adverse Reactions: {label_info['adverse_reactions'][0][:200]}...")
    else:
        response_lines.append("\nNo FDA label information found.")

    assessment = evidence["causality_assessment"]
    response_lines.append(f"\nCausality Assessment: Evidence Level={assessment['evidence_level']}, Score={assessment['causality_score']}")

    return "\n".join(response_lines)


@tool
def generate_report(
    analysis_results: str,
    evidence_data: str,
    include_graphs: bool = False,
) -> str:
    """Generate safety signal detection report.

    Args:
        analysis_results: JSON string of results from adverse event analysis.
        evidence_data: JSON string of evidence assessment data.
        include_graphs: Include data visualizations (not supported in text mode).
    """
    try:
        analysis = json.loads(analysis_results)
    except (json.JSONDecodeError, TypeError):
        analysis = {"product_name": "Unknown", "analysis_period": {"start": "N/A", "end": "N/A"}, "total_reports": 0, "signals": [], "trends": {"daily_counts": {}}}

    try:
        evidence = json.loads(evidence_data)
    except (json.JSONDecodeError, TypeError):
        evidence = {}

    report_lines = [
        "Safety Signal Detection Report",
        "===========================\n",
        f"Product: {analysis.get('product_name', 'Unknown')}",
        f"Analysis Period: {analysis.get('analysis_period', {}).get('start', 'N/A')} to {analysis.get('analysis_period', {}).get('end', 'N/A')}",
        f"Total Reports: {analysis.get('total_reports', 0)}\n",
        "Signal Detection Results",
        "----------------------",
    ]

    for sig in analysis.get("signals", []):
        ci = sig.get("confidence_interval")
        ci_text = f" (95% CI: {ci['lower']}-{ci['upper']})" if ci else ""
        report_lines.append(f"- {sig['event']}: PRR={sig['prr']}, Reports={sig['count']}{ci_text}")

    literature = evidence.get("literature", [])
    if literature:
        report_lines.append("\nLiterature Evidence:")
        for article in literature:
            report_lines.append(f"- {article['title']} ({article['year']}, PMID: {article['pmid']})")

    causality = evidence.get("causality_assessment", {})
    if causality:
        report_lines.append(f"\nCausality: Evidence Level={causality.get('evidence_level', 'Unknown')}, Score={causality.get('causality_score', 0)}")

    bucket_name = os.environ.get("REPORT_BUCKET_NAME")
    if bucket_name:
        try:
            report_text = "\n".join(report_lines)
            s3 = boto3.client("s3")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            key = f"reports/{analysis.get('product_name', 'unknown')}/signal_detection_{timestamp}.txt"
            s3.put_object(Bucket=bucket_name, Key=key, Body=report_text, ContentType="text/plain")
            report_lines.append(f"\nReport uploaded to s3://{bucket_name}/{key}")
        except Exception as e:
            report_lines.append(f"\nFailed to upload report to S3: {e}")

    return "\n".join(report_lines)


def _search_pubmed(product_name, adverse_event):
    """Search PubMed for literature evidence."""
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    search_term = f'"{product_name}"[Title/Abstract] AND "{adverse_event}"[Title/Abstract] AND "adverse effects"[Subheading]'
    params = {"db": "pubmed", "term": search_term, "retmax": 10, "sort": "relevance"}

    try:
        url = f"{base_url}/esearch.fcgi?{urllib.parse.urlencode(params)}"
        with urllib.request.urlopen(url, timeout=30) as response:
            root = ET.fromstring(response.read())
            pmids = [id_elem.text for id_elem in root.findall(".//Id")]

        if not pmids:
            return []

        fetch_params = {"db": "pubmed", "id": ",".join(pmids), "rettype": "abstract", "retmode": "xml"}
        url = f"{base_url}/efetch.fcgi?{urllib.parse.urlencode(fetch_params)}"
        with urllib.request.urlopen(url, timeout=30) as response:
            root = ET.fromstring(response.read())

        articles = []
        for article in root.findall(".//PubmedArticle"):
            try:
                title = article.find(".//ArticleTitle").text or ""
                abstract = article.find(".//Abstract/AbstractText")
                year = article.find(".//DateCompleted/Year") or article.find(".//PubDate/Year")
                articles.append({
                    "title": title,
                    "abstract": abstract.text[:300] if abstract is not None and abstract.text else "",
                    "year": year.text if year is not None else "N/A",
                    "pmid": article.find(".//PMID").text,
                })
            except Exception:
                continue
        return articles
    except Exception as e:
        logger.error(f"Error searching PubMed: {e}")
        return []


def _query_fda_label(product_name):
    """Query FDA Label API for product information."""
    base_url = "https://api.fda.gov/drug/label.json"
    params = {"search": f'openfda.brand_name:"{product_name}" OR openfda.generic_name:"{product_name}"', "limit": 1}

    try:
        url = f"{base_url}?{urllib.parse.urlencode(params)}"
        with urllib.request.urlopen(url, timeout=30) as response:
            data = json.loads(response.read().decode())
        if data.get("results"):
            label = data["results"][0]
            return {
                "warnings": label.get("warnings", []),
                "adverse_reactions": label.get("adverse_reactions", []),
                "boxed_warnings": label.get("boxed_warning", []),
                "contraindications": label.get("contraindications", []),
            }
        return None
    except Exception as e:
        logger.error(f"Error querying FDA Label: {e}")
        return None


def _assess_causality(literature, label_info):
    """Assess causality based on available evidence."""
    evidence_level = "Insufficient"
    causality_score = 0

    if label_info:
        if label_info.get("boxed_warnings"):
            causality_score += 3
            evidence_level = "Strong"
        elif label_info.get("warnings"):
            causality_score += 2
            evidence_level = "Moderate"
        elif label_info.get("adverse_reactions"):
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
        "evidence_level": evidence_level,
        "causality_score": causality_score,
        "assessment_date": datetime.now().isoformat(),
    }


def create_agent() -> Agent:
    """Create and return the Safety Signal Detection agent."""
    model = BedrockModel(model_id=MODEL_ID, streaming=True)
    return Agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        tools=[analyze_adverse_events, assess_evidence, generate_report],
    )
