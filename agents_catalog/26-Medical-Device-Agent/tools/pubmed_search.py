import html
from urllib.parse import quote
import requests
from strands import tool

@tool
def search_pubmed(query: str, max_results: int = 5) -> str:
    """
    Search PubMed for medical literature.

    Args:
        query (str): Search query for medical literature.
        max_results (int): Maximum number of results to return (default: 5).

    Returns:
        str: Search results from PubMed.
    """
    try:
        # Search PubMed using eSearch
        search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        # Sanitize query to prevent XSS
        sanitized_query = html.escape(query.strip())
        search_params = {
            "db": "pubmed",
            "term": sanitized_query,
            "retmax": max_results,
            "retmode": "json"
        }
        
        search_response = requests.get(search_url, params=search_params)
        search_data = search_response.json()
        
        if "esearchresult" not in search_data or not search_data["esearchresult"]["idlist"]:
            return f"No results found for query: {query}"
        
        pmids = search_data["esearchresult"]["idlist"]
        
        # Fetch article details using eSummary
        summary_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
        summary_params = {
            "db": "pubmed",
            "id": ",".join(pmids),
            "retmode": "json"
        }
        
        summary_response = requests.get(summary_url, params=summary_params)
        summary_data = summary_response.json()
        
        results = []
        for pmid in pmids:
            if pmid in summary_data["result"]:
                article = summary_data["result"][pmid]
                title = article.get("title", "No title")
                authors = ", ".join([author["name"] for author in article.get("authors", [])[:3]])
                journal = article.get("source", "Unknown journal")
                pub_date = article.get("pubdate", "Unknown date")
                
                results.append(f"PMID: {pmid}\nTitle: {title}\nAuthors: {authors}\nJournal: {journal}\nDate: {pub_date}\nURL: https://pubmed.ncbi.nlm.nih.gov/{pmid}/\n")
        
        return "\n".join(results)
        
    except Exception as e:
        return f"Error searching PubMed: {str(e)}"