"""Competitive Intelligence Agent combining web search, SEC 10-K, and USPTO capabilities."""

import datetime
import json
import logging
import os
import urllib.parse
import urllib.request

import boto3
from strands import Agent, tool
from strands.models import BedrockModel

logger = logging.getLogger(__name__)

MODEL_ID = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"

SYSTEM_PROMPT = """You are an expert Corporate Competitive Intelligence Analyst. Your purpose is to create comprehensive competitive intelligence reports on major US corporations by analyzing recent activities, market positioning, and financial trends.

Your Capabilities:
You have three specialized tools:
- web_search: Retrieve recent news, press releases, analyst reports, and media coverage
- sec_company_financials: Extract financial data from SEC 10-K filings (revenue, margins, cash flow, etc.)
- uspto_search: Search patent applications from the USPTO

Report Structure:
1. Executive Summary (Key findings and strategic implications in 2-3 paragraphs)
2. Company Overview (Brief description, sector, market cap, core business lines)
3. Recent Developments (Key news, product launches, leadership changes, strategic shifts)
4. Financial Performance Analysis
   - Revenue trends and growth rates
   - Profitability metrics (margins, ROI, etc.)
   - Balance sheet health
   - Cash flow patterns
5. Strategic Initiatives (Recent or ongoing)
6. Competitive Position (Market share, positioning relative to key competitors)
7. Risk Factors (Regulatory, market, operational challenges)
8. Future Outlook (Analyst projections, guidance, growth vectors)

Working Process:
1. Understand the specific company the user wants analyzed
2. Use web_search to find recent news (last 3-6 months)
3. Use sec_company_financials to retrieve financial data from 10-K filings
4. Use uspto_search to find patent applications from the past 365 days
5. Synthesize information from all sources into a cohesive narrative
6. Present findings objectively with relevant quantitative data

Guidelines:
- Maintain objectivity and avoid speculation
- Support claims with specific data points and citations
- Focus on material developments that impact company valuation or strategic position
- Provide proper attribution for all information sources
- Note any significant data limitations or areas requiring further research

When a user requests a competitive intelligence report, ask clarifying questions if needed."""


# --- Web Search Tool ---


@tool
def web_search(
    search_query: str,
    target_website: str = "",
    topic: str = "general",
    days: int = 90,
) -> str:
    """Execute an internet search query using Tavily Search for news, press releases, and analyst reports.

    Args:
        search_query: The search query to execute. Example: 'Eli Lilly recent acquisitions 2024'
        target_website: Optional specific website domain to search.
        topic: The topic type: 'news' or 'general'. Use 'news' for recent events.
        days: Number of days of history to search. Default 90 for competitive intel.
    """
    api_key = os.environ.get("TAVILY_API_KEY", "")
    if not api_key:
        return "Error: TAVILY_API_KEY environment variable is not set."

    payload = {
        "api_key": api_key,
        "query": search_query,
        "search_depth": "advanced",
        "include_images": False,
        "include_answer": False,
        "include_raw_content": False,
        "max_results": 5,
        "topic": topic,
        "days": days,
        "include_domains": [target_website] if target_website else [],
        "exclude_domains": [],
    }

    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        "https://api.tavily.com/search",
        data=data,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )

    try:
        response = urllib.request.urlopen(request, timeout=25)  # nosec: B310
        return response.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return f"Error: Tavily search failed with HTTP {e.code}"
    except Exception as e:
        return f"Error: Tavily search failed: {e}"


# --- SEC 10-K Tool ---


def _get_cik(company_name: str) -> dict | None:
    """Look up SEC CIK for a company name via SEC EDGAR company search."""
    url = f"https://efts.sec.gov/LATEST/search-index?q=%22{urllib.parse.quote(company_name)}%22&dateRange=custom&startdt=2020-01-01&forms=10-K"
    headers = {"User-Agent": "AWS HCLS Agents research@example.com"}
    request = urllib.request.Request(url, headers=headers)

    # Use the SEC full-text search tickers file instead
    tickers_url = "https://www.sec.gov/files/company_tickers.json"
    request = urllib.request.Request(tickers_url, headers=headers)
    try:
        response = urllib.request.urlopen(request, timeout=15)  # nosec: B310
        tickers = json.loads(response.read().decode("utf-8"))

        # Fuzzy match by checking if company_name is contained in title
        company_lower = company_name.lower()
        for entry in tickers.values():
            if company_lower in entry.get("title", "").lower():
                return entry
        # Try partial match
        for entry in tickers.values():
            title = entry.get("title", "").lower()
            if any(word in title for word in company_lower.split() if len(word) > 3):
                return entry
    except Exception as e:
        logger.error(f"CIK lookup failed: {e}")
    return None


@tool
def sec_company_financials(company_name: str, financial_metric: str) -> str:
    """Retrieve financial data from SEC 10-K filings for a company using the EDGAR API.

    Use this to get specific quantitative financial information such as revenue, profit margins,
    earnings, balance sheet metrics, cash flow, and debt levels.

    Args:
        company_name: The company name to look up. Example: 'Amazon', 'Eli Lilly'
        financial_metric: The US-GAAP taxonomy tag for the metric. Common tags:
            - Revenues, RevenueFromContractWithCustomerExcludingAssessedTax
            - NetIncomeLoss
            - GrossProfit
            - OperatingIncomeLoss
            - EarningsPerShareBasic
            - Assets, Liabilities
            - CashAndCashEquivalentsAtCarryingValue
            - LongTermDebt
            - ResearchAndDevelopmentExpense
            - AccountsPayableCurrent
    """
    cik_info = _get_cik(company_name)
    if not cik_info:
        return json.dumps({"error": f"Could not find SEC CIK for: {company_name}"})

    cik = str(cik_info["cik_str"]).zfill(10)
    tag = financial_metric

    url = f"https://data.sec.gov/api/xbrl/companyconcept/CIK{cik}/us-gaap/{tag}.json"
    headers = {"User-Agent": "AWS HCLS Agents research@example.com"}
    request = urllib.request.Request(url, headers=headers)

    try:
        response = urllib.request.urlopen(request, timeout=15)  # nosec: B310
        data = json.loads(response.read().decode("utf-8"))

        # Extract 10-K annual data
        units = data.get("units", {})
        unit_key, entries = next(iter(units.items()), ("", []))
        annual_data = [
            {"date": e.get("end", ""), "value": e.get("val", 0), "form": e.get("form", "")}
            for e in entries
            if e.get("form") == "10-K" and "frame" in e
        ]

        result = {
            "entity_name": data.get("entityName", ""),
            "label": data.get("label", ""),
            "description": data.get("description", ""),
            "unit": unit_key,
            "annual_10k_data": annual_data[-10:],  # Last 10 years
        }
        return json.dumps(result, separators=(",", ":"))
    except urllib.error.HTTPError as e:
        return json.dumps({"error": f"SEC EDGAR API returned HTTP {e.code} for tag '{tag}'. Try a different tag."})
    except Exception as e:
        return json.dumps({"error": f"SEC lookup failed: {e}"})


# --- USPTO Search Tool ---


def _get_uspto_api_key() -> str:
    """Retrieve USPTO API key from environment or AWS Secrets Manager."""
    key_name = os.environ.get("USPTO_API_KEY_NAME", "USPTO_API_KEY")
    if key_name in os.environ:
        return os.environ[key_name].strip()
    client = boto3.client("secretsmanager")
    return client.get_secret_value(SecretId=key_name)["SecretString"]


@tool
def uspto_search(search_query: str, days: str = None) -> str:
    """Search the USPTO patent database for patent applications.

    Use this to find recent patent filings, research activity, and innovation trends for a company or topic.

    Args:
        search_query: The search query for USPTO. Example: 'tirzepatide', 'Eli Lilly antibody'
        days: Optional number of days of history to search. Example: '365' for past year.
    """
    api_key = _get_uspto_api_key()

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-API-KEY": api_key,
    }

    payload = {
        "q": search_query,
        "sort": [{"field": "applicationMetaData.effectiveFilingDate", "order": "desc"}],
        "fields": [
            "applicationNumberText",
            "applicationMetaData.firstInventorName",
            "applicationMetaData.effectiveFilingDate",
            "applicationMetaData.applicationTypeLabelName",
            "applicationMetaData.firstApplicantName",
            "applicationMetaData.inventionTitle",
        ],
        "pagination": {"offset": 0, "limit": 25},
    }

    if days:
        end_date = datetime.date.today()
        start_date = end_date - datetime.timedelta(days=int(days))
        payload["rangeFilters"] = [
            {
                "field": "applicationMetaData.effectiveFilingDate",
                "valueFrom": str(start_date),
                "valueTo": str(end_date),
            }
        ]

    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        "https://api.uspto.gov/api/v1/patent/applications/search",
        data=data,
        headers=headers,
    )

    try:
        response = urllib.request.urlopen(request)  # nosec: B310
        response_data = response.read().decode("utf-8")
        results = json.loads(response_data)
        return json.dumps(results, separators=(",", ":"))
    except urllib.error.HTTPError as e:
        return json.dumps({"error": f"USPTO API returned HTTP {e.code}"})
    except Exception as e:
        return json.dumps({"error": f"USPTO search failed: {e}"})


# --- Agent Factory ---


def create_agent() -> Agent:
    """Create and return the Competitive Intelligence Agent."""
    model = BedrockModel(model_id=MODEL_ID, streaming=True)
    return Agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        tools=[web_search, sec_company_financials, uspto_search],
    )
