# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import logging
import os
import re
from typing import Any, Dict, List, Literal

# Element only used for type check
# nosemgrep: use-defused-xml
from xml.etree.ElementTree import Element # nosec

import httpx
from defusedxml import ElementTree as ET
from strands import tool

# Global configuration for commercial use filtering
COMMERCIAL_USE_ONLY = os.getenv("COMMERCIAL_USE_ONLY", True)

# Configure logging
logging.basicConfig(
    format="%(levelname)s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler()],
)

logger = logging.getLogger("search_pmc")
logger.setLevel(logging.INFO)

# Type alias forbetter readibility
ArticleDict = Dict[str, Any]
ToolResult = Dict[str, Any]
ReferenceDict = Dict[str, str]


def search_pmc(
    query: str,
    max_search_result_count: int = 100,
    max_filtered_result_count: int = 10,
    rerank_by: Literal["references", None] = "references",
) -> dict:
    """
    Search PMC for articles matching the query with ToolResult format.

    This function performs a comprehensive search of PMC literature with optional
    citation analysis and ranking capabilities. Results can be ranked by citation count
    within the result set to surface the most influential papers. The function follows
    the Strands Agents framework ToolResult format for consistent response handling.

    Args:
        - query (required): The search query for PMC using standard PMC search syntax
        - max_search_result_count (optional): Maximum number of results to fetch from initial search (default: 100, range: 1-1000)
        - max_filtered_result_count (optional): Maximum number of articles to return in final, filtered results (range: 1-100)

    Returns:
        Dictionary with the following structure:
        - status: "success" or "error"
        - content: List containing a single dictionary with "text" field:
            - For success: Formatted search results with article details, citation counts, and summary
            - For error: Descriptive error message explaining what went wrong

    Success Response Format:
        {
            "status": "success",
            "content": [{"text": "Showing 5 of 50 articles found\\nResults ranked by citation count...\\n\\nArticle 1\\n..."}]
        }

    Error Response Format:
        {
            "status": "error",
            "content": [{"text": "Error: query parameter is required"}]
        }

    Note: To search by the relative date of publication, add one of the following date filters to the end of the search query INCLUDING THE DOUBLE QUOTES:

    - AND "last X days"[dp]
    - AND "last X months"[dp]
    - AND "last X years"[dp]

    where X is the number of days, months, or years immediately preceding today's date.

    For example

    Examples:
        # Basic search with citation ranking
        input = {
            "query": "CRISPR gene editing",
            "max_search_result_count": 50,
            "max_filtered_result_count": 10
        }
        result = search_pmc(input)

        # Advanced search with relative publication date
        input = {
            "query": 'mRNA vaccine COVID-19 AND "last 2 years"[dp]',
            "max_search_result_count": 200,
            "max_filtered_result_count": 20
        }
        result = search_pmc(tool_input)

        # Handle success response
        if result["status"] == "success":
            formatted_articles = result["content"][0]["text"]
            print(formatted_articles)
        else:
            error_message = result["content"][0]["text"]
            print(f"Search failed: {error_message}")
    """

    try:
        logger.info(f"Searching PMC for: {query}")

        base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
        search_url = f"{base_url}/esearch.fcgi"

        # Build search query with filters
        try:
            filtered_query = _build_search_query(query)
        except Exception as query_error:
            logger.error(f"Error building search query: {query_error}")
            return {
                "status": "error",
                "content": [
                    {"text": f"Error building search query: {str(query_error)}"}
                ],
            }

        search_params = {
            "db": "pmc",
            "term": filtered_query,
            "retmax": max_search_result_count,
            "retmode": "json",
            "sort": "relevance",
        }

        try:
            # Search for article IDs
            search_response = httpx.post(
                search_url, data=_get_api_key_params(search_params)
            )
            search_response.raise_for_status()
        except httpx.HTTPStatusError as http_error:
            logger.error(f"HTTP error during PMC search: {http_error}")
            return {
                "status": "error",
                "content": [
                    {
                        "text": f"HTTP error during PMC search: {http_error.response.status_code} - {str(http_error)}"
                    }
                ],
            }
        except httpx.TimeoutException as timeout_error:
            logger.error(f"Timeout error during PMC search: {timeout_error}")
            return {
                "status": "error",
                "content": [
                    {"text": f"Request timeout during PMC search: {str(timeout_error)}"}
                ],
            }
        except httpx.NetworkError as network_error:
            logger.error(f"Network error during PMC search: {network_error}")
            return {
                "status": "error",
                "content": [
                    {"text": f"Network error during PMC search: {str(network_error)}"}
                ],
            }
        except httpx.RequestError as request_error:
            logger.error(f"Request error during PMC search: {request_error}")
            return {
                "status": "error",
                "content": [
                    {"text": f"Request error during PMC search: {str(request_error)}"}
                ],
            }

        try:
            search_data = search_response.json()
        except Exception as json_error:
            logger.error(f"JSON parsing error in search response: {json_error}")
            return {
                "status": "error",
                "content": [
                    {"text": f"Error parsing search response: {str(json_error)}"}
                ],
            }

        try:
            # Extract IDs
            id_list = search_data["esearchresult"]["idlist"]
            logger.info(f"Found {len(id_list)} article pmcids")
        except KeyError as key_error:
            logger.error(f"Unexpected search response format: {key_error}")
            return {
                "status": "error",
                "content": [
                    {
                        "text": f"Unexpected search response format: missing {str(key_error)}"
                    }
                ],
            }

        if not id_list:
            logger.info("No articles found")
            return {
                # "toolUseId": tool_use_id,
                "status": "success",
                "content": [{"text": "No articles found for the given query."}],
            }

        # Fetch article details using the batch function
        try:
            articles = fetch_pmc(id_list)
        except Exception as fetch_error:
            logger.error(f"Error fetching article details: {fetch_error}")
            return {
                "status": "error",
                "content": [
                    {"text": f"Error fetching article details: {str(fetch_error)}"}
                ],
            }

        # Apply reranking if requested
        if rerank_by == "references":
            try:
                logger.info("Calculating citation relationships and ranking articles")
                enhanced_articles = _calculate_referenced_by_counts(articles)
                ranked_articles = _rank_by_citations(enhanced_articles)
                logger.info("Citation ranking completed successfully")

                # Apply max_filtered_result_count limit to ranked results
                if max_filtered_result_count is not None:
                    final_results = ranked_articles[:max_filtered_result_count]
                    logger.info(
                        f"Applied max_filtered_result_count limit: returning {len(final_results)} of {len(ranked_articles)} articles"
                    )
                else:
                    final_results = ranked_articles

                _print_fetch_results(final_results, n=3)

                # Format search results using article formatting functions
                # Pass the total before max_filtered_result_count limit for proper summary
                total_before_limit = len(ranked_articles)
                try:
                    formatted_content = _format_article_list(
                        final_results,
                        include_ranking=True,
                        total_found=total_before_limit,
                    )
                except Exception as format_error:
                    logger.error(f"Error formatting article results: {format_error}")
                    return {
                        "status": "error",
                        "content": [
                            {
                                "text": f"Error formatting search results: {str(format_error)}"
                            }
                        ],
                    }

                return {
                    "status": "success",
                    "content": [{"text": formatted_content}],
                }
            except Exception as ranking_error:
                logger.error(f"Citation ranking failed: {ranking_error}")
                logger.info("Falling back to original search results")
                # Fall through to return original results with warning
                warning_message = f"Warning: Citation analysis failed ({str(ranking_error)}). Returning results without ranking."
        else:
            logger.info("Skipping citation-based reranking")
            warning_message = None

        # Return original results (either when referenced_by=None or as fallback)
        if max_filtered_result_count is not None:
            final_results = articles[:max_filtered_result_count]
            logger.info(
                f"Applied max_filtered_result_count limit: returning {len(final_results)} of {len(articles)} articles"
            )
        else:
            final_results = articles

        _print_fetch_results(final_results, n=10)

        # Format search results using article formatting functions
        # Pass the total before max_filtered_result_count limit for proper summary
        total_before_limit = len(articles)
        try:
            formatted_content = _format_article_list(
                final_results, include_ranking=False, total_found=total_before_limit
            )

            # Add warning message if citation analysis failed
            if "warning_message" in locals() and warning_message:
                formatted_content = warning_message + "\n\n" + formatted_content

        except Exception as format_error:
            logger.error(f"Error formatting article results: {format_error}")
            return {
                "status": "error",
                "content": [
                    {"text": f"Error formatting search results: {str(format_error)}"}
                ],
            }

        return {
            "status": "success",
            "content": [{"text": formatted_content}],
        }

    except Exception as unexpected_error:
        logger.error(f"Unexpected error in search_pmc: {unexpected_error}")
        return {
            "status": "error",
            "content": [
                {"text": f"Unexpected error during PMC search: {str(unexpected_error)}"}
            ],
        }


def fetch_pmc(pmc_ids: List[str]) -> List[ArticleDict]:
    """
    Get detailed information about one or more PMC articles.

    Args:
        pmc_ids: List of PMC IDs to fetch

    Returns:
        List of article dictionaries with detailed information including keywords and references.
        Empty articles are filtered out. Returns empty list if no articles found or on error.
    """
    if not pmc_ids:
        return []

    logger.info(f"Fetching {len(pmc_ids)} PM articles")

    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    fetch_url = f"{base_url}/efetch.fcgi"

    fetch_params = {"db": "pmc", "id": ",".join(pmc_ids)}

    try:
        try:
            fetch_response = httpx.post(
                fetch_url, data=_get_api_key_params(fetch_params)
            )
            fetch_response.raise_for_status()
        except httpx.HTTPStatusError as http_error:
            logger.warning(f"HTTP error during article fetch: {http_error}")
            raise Exception(
                f"HTTP error during article fetch: {http_error.response.status_code} - {str(http_error)}"
            )
        except httpx.TimeoutException as timeout_error:
            logger.warning(f"Timeout error during article fetch: {timeout_error}")
            raise Exception(
                f"Request timeout during article fetch: {str(timeout_error)}"
            )
        except httpx.NetworkError as network_error:
            logger.warning(f"Network error during article fetch: {network_error}")
            raise Exception(f"Network error during article fetch: {str(network_error)}")
        except httpx.RequestError as request_error:
            logger.warning(f"Request error during article fetch: {request_error}")
            raise Exception(f"Request error during article fetch: {str(request_error)}")

        # Parse XML response
        try:
            root = ET.fromstring(fetch_response.text)
        except ET.ParseError as xml_error:
            logger.warning(f"XML parsing error in fetch response: {xml_error}")
            raise Exception(f"Error parsing XML response from PM: {str(xml_error)}")
        except Exception as parse_error:
            logger.warning(f"Unexpected parsing error in fetch response: {parse_error}")
            raise Exception(f"Error parsing response from PM: {str(parse_error)}")

        articles = []

        for article_element in root.findall(".//article"):
            try:
                article = _extract_article_data(article_element)
                if article:  # Only add non-empty articles
                    articles.append(article)
            except Exception as e:
                logger.warning(f"Error parsing individual article: {e}")
                continue

        logger.info(f"Successfully fetched {len(articles)} articles")
        return articles

    except Exception as e:
        logger.warning(f"Error fetching article details: {e}")
        # Re-raise the exception so search_pmc can handle it properly
        raise


def _get_api_key_params(base_params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Add NCBI API key to request parameters if available.

    Args:
        base_params: Base request parameters dictionary

    Returns:
        Parameters dictionary with API key added if available
    """
    api_key = os.getenv("NCBI_API_KEY")

    # If API key exists and is not empty, add it to parameters
    if api_key and api_key.strip():
        # Create a new dictionary to avoid modifying the original
        params_with_key = base_params.copy()
        params_with_key["api_key"] = api_key
        return params_with_key

    # Return original parameters if no API key or empty string
    return base_params


def _add_quotes_to_search_filter(query: str) -> str:
    """Search for any filter clauses in the search query and add any missing quotation marks."""

    return re.sub(r"AND ([a-zA-Z0-9 ]+?)(\[[a-z]+?\])", r'AND "\1"\2', query)


def _build_search_query(query: str) -> str:
    """Build the search query with appropriate filters."""

    # Add double-quotes around date filters
    query = _add_quotes_to_search_filter(query)

    if COMMERCIAL_USE_ONLY:
        license_filter = " AND (cc0 license[Filter] OR cc by license[Filter] OR cc by-sa license[Filter] OR cc by-nd license[Filter])"
    else:
        license_filter = " AND cc license[Filter]"

    return query + license_filter


def _extract_article_data(article_element: Element) -> ArticleDict:
    """Extract article data from XML element."""
    article = {}

    # Extract PMC ID and PMID (looking for pmcid and pmid type article-id)
    article_id_elements = article_element.findall(".//article-meta/article-id")
    for article_id in article_id_elements:
        id_type = article_id.get("pub-id-type")
        if id_type == "pmcid" and article_id.text:
            # Remove "PMC" prefix if present to get just the numeric ID
            pmc_id = article_id.text.replace("PMC", "")
            article["id"] = pmc_id
            article["pmc"] = article_id.text  # Keep full PMC ID with prefix
        elif id_type == "pmid" and article_id.text:
            article["pmid"] = article_id.text
        elif id_type == "doi" and article_id.text:
            article["doi"] = article_id.text
            # Create URI from DOI
            doi_url = f"https://doi.org/{article_id.text}"
            article["uri"] = doi_url
            article["source"] = doi_url

    # Extract title
    title_element = article_element.find(".//article-title")
    if title_element is not None:
        # Use itertext() to get all text content including text within child elements
        title_text = "".join(title_element.itertext()).strip()
        if title_text:
            article["title"] = title_text

    # Extract abstract
    abstract_element = article_element.find(".//abstract")
    if abstract_element is not None:
        # Get all paragraph text from abstract, excluding the "Abstract" title
        abstract_texts = []
        for p in abstract_element.findall(".//p"):
            text_content = "".join(p.itertext()).strip()
            if text_content:
                abstract_texts.append(text_content)

        if abstract_texts:
            abstract_content = " ".join(abstract_texts)
            article["abstract"] = abstract_content
            article["text"] = abstract_content

    # Extract authors
    author_elements = article_element.findall(
        ".//contrib-group/contrib[@contrib-type='author']"
    )
    if author_elements:
        authors = []
        for author in author_elements:
            name_element = author.find(".//name")
            if name_element is not None:
                surname_element = name_element.find("surname")
                given_names_element = name_element.find("given-names")

                if surname_element is not None and given_names_element is not None:
                    if surname_element.text and given_names_element.text:
                        authors.append(
                            f"{given_names_element.text} {surname_element.text}"
                        )
                elif surname_element is not None and surname_element.text:
                    authors.append(surname_element.text)

        if authors:
            article["authors"] = ", ".join(authors)

    # Extract journal title
    journal_element = article_element.find(".//journal-title")
    if journal_element is not None and journal_element.text:
        article["journal"] = journal_element.text

    # Extract publication year (try multiple pub-date types in order of preference)
    year = None
    # Try collection first (most common for PMC)
    pub_date_element = article_element.find(".//pub-date[@pub-type='collection']/year")
    if pub_date_element is not None and pub_date_element.text:
        year = pub_date_element.text
    # Fall back to epub (electronic publication)
    if not year:
        pub_date_element = article_element.find(".//pub-date[@pub-type='epub']/year")
        if pub_date_element is not None and pub_date_element.text:
            year = pub_date_element.text
    # Fall back to ppub (print publication)
    if not year:
        pub_date_element = article_element.find(".//pub-date[@pub-type='ppub']/year")
        if pub_date_element is not None and pub_date_element.text:
            year = pub_date_element.text
    # Last resort: any year element
    if not year:
        pub_date_element = article_element.find(".//pub-date/year")
        if pub_date_element is not None and pub_date_element.text:
            year = pub_date_element.text

    if year:
        article["year"] = year

    # Extract references from ReferenceList
    reference_elements = article_element.findall(".//ref")
    if reference_elements:
        references = []
        for ref in reference_elements:
            # Look for PubMed ID in the reference
            ref_pmid_element = ref.find(".//pub-id[@pub-id-type='pmid']")
            if ref_pmid_element is not None and ref_pmid_element.text:
                references.append(ref_pmid_element.text)

        if references:
            article["references"] = references

    return article


def _calculate_referenced_by_counts(articles: List[ArticleDict]) -> List[ArticleDict]:
    """
    Calculate how many times each article is referenced by others in the result set.

    Args:
        articles: List of articles with references

    Returns:
        Same list with referenced_by_count added to each article
    """
    # Create a copy of articles to avoid modifying the original list
    enhanced_articles = []

    # Build a mapping from PMID to PMC ID since references use PMIDs
    pmid_to_pmc = {}
    for article in articles:
        pmid = article.get("pmid")
        pmc_id = article.get("id")
        if pmid and pmc_id:
            pmid_to_pmc[pmid] = pmc_id

    # Build a citation graph: pmc_id -> set of pmc_ids that reference it
    citation_graph = {}

    # Initialize citation counts for all articles
    for article in articles:
        pmc_id = article.get("id")
        if pmc_id:
            citation_graph[pmc_id] = set()

    # Build the citation relationships
    for article in articles:
        pmc_id = article.get("id")
        references = article.get("references", [])  # These are PMIDs

        # Skip if article has no ID
        if not pmc_id:
            continue

        # Process each reference (PMID)
        for ref_pmid in references:
            # Handle edge cases
            if not ref_pmid:  # Skip empty/None references
                continue
            if not ref_pmid.isdigit():  # Skip invalid PMIDs (non-numeric)
                continue

            # Convert PMID to PMC ID using our mapping
            referenced_pmc_id = pmid_to_pmc.get(ref_pmid)

            if referenced_pmc_id:
                # Skip self-references
                if referenced_pmc_id == pmc_id:
                    continue

                # Add this article as a referencing article for the referenced PMC ID
                citation_graph[referenced_pmc_id].add(pmc_id)

    # Calculate referenced_by_count for each article
    for article in articles:
        # Create a copy of the article dict
        enhanced_article = article.copy()

        pmc_id = article.get("id")
        if pmc_id and pmc_id in citation_graph:
            # Count how many articles reference this one
            enhanced_article["referenced_by_count"] = len(citation_graph[pmc_id])
        else:
            # Articles without valid IDs get count of 0
            enhanced_article["referenced_by_count"] = 0

        enhanced_articles.append(enhanced_article)

    return enhanced_articles


def _rank_by_citations(articles: List[ArticleDict]) -> List[ArticleDict]:
    """
    Re-rank articles by referenced_by_count in descending order.

    Args:
        articles: List of articles with referenced_by_count

    Returns:
        Re-ordered list with highest cited articles first
    """
    # Sort articles by referenced_by_count (descending), then by PMID (descending) for tie-breaking
    ranked_articles = sorted(
        articles,
        key=lambda article: (
            article.get("referenced_by_count", 0),  # Primary sort: citation count
            (
                int(article.get("id", "0")) if article.get("id", "").isdigit() else 0
            ),  # Secondary sort: PMID
        ),
        reverse=True,  # Both sorts in descending order
    )

    return ranked_articles


def _format_individual_article(
    article: ArticleDict, index: int = None, include_ranking: bool = False
) -> str:
    """
    Format a single article as a readable text block.

    Args:
        include_ranking: Whether to include citation ranking information

    Returns:
        Formatted string representation of the article
    """
    lines = []

    # Add article number if provided
    if index is not None:
        lines.append(f"Article {index}")
        lines.append("-" * 20)

    # Title (required field)
    title = article.get("title", "No title available")
    lines.append(f"Title: {title}")

    # Authors
    authors = article.get("authors", "No authors listed")
    lines.append(f"Authors: {authors}")

    # Journal and year
    journal = article.get("journal", "Unknown journal")
    year = article.get("year", "Unknown year")
    lines.append(f"Journal: {journal} ({year})")

    # Metadata (PMID, PMC, DOI)
    pmid = article.get("pmid")
    if pmid:
        lines.append(f"PMID: {pmid}")

    pmc = article.get("pmc")
    if pmc:
        lines.append(f"PMC: {pmc}")

    doi = article.get("doi")
    if doi:
        lines.append(f"DOI: {doi}")

    # Abstract (truncated if very long)
    abstract = article.get("abstract", "No abstract available")
    if len(abstract) > 500:
        abstract = abstract[:497] + "..."
    lines.append(f"Abstract: {abstract}")

    # Citation information when ranking is applied
    if include_ranking:
        ref_count = len(article.get("references", []))
        referenced_by_count = article.get("referenced_by_count", 0)
        lines.append(f"References: {ref_count} articles")
        lines.append(f"Cited by: {referenced_by_count} articles in this result set")

    return "\n".join(lines)


def _format_article_list(
    articles: List[ArticleDict], include_ranking: bool = False, total_found: int = None
) -> str:
    """
    Format a list of articles with numbering and summary information.

    Args:
        articles: List of article dictionaries
        include_ranking: Whether to include citation ranking information
        total_found: Total number of articles found in search (before max_filtered_result_count limit)

    Returns:
        Formatted string representation of the article list
    """
    if not articles:
        return "No articles found for the given query."

    lines = []

    # Add summary information
    result_count = len(articles)
    if total_found is not None and total_found != result_count:
        lines.append(f"Showing {result_count} of {total_found} articles found")
    else:
        lines.append(f"Found {result_count} articles")

    if include_ranking:
        lines.append("Results ranked by citation count within this result set")

    lines.append("")  # Empty line for spacing

    # Format each article
    for i, article in enumerate(articles, 1):
        article_text = _format_individual_article(
            article, index=i, include_ranking=include_ranking
        )
        lines.append(article_text)

        # Add separator between articles (except after the last one)
        if i < len(articles):
            lines.append("")
            lines.append("=" * 50)
            lines.append("")

    return "\n".join(lines)


def _print_fetch_results(articles: list, n: int = 3) -> None:
    """Prints the fetch results in a formatted way."""

    result_string = f"Top {n} results:\n"
    result_string += "-" * 50 + "\n"
    for article in articles[:n]:
        result_string += f"Title: {article.get('title', 'No title')}\n"
        result_string += f"PMID: {article.get('pmid', 'No PMID')}\n"
        result_string += f"PMC: {article.get('pmc', 'No PMC')}\n"
        result_string += f"DOI: {article.get('doi', 'No DOI')}\n"
        result_string += f"Source: {article.get('source', 'No Source')}\n"
        result_string += f"Authors: {article.get('authors', 'No authors')}\n"
        result_string += f"Journal: {article.get('journal', 'No journal')}\n"
        result_string += f"Year: {article.get('year', 'No publication year')}\n"
        result_string += f"Abstract: {article.get('abstract', 'No abstract')}\n"
        result_string += f"Reference Count: {len(article.get('references', []))}\n"
        result_string += (
            f"Referenced By Count: {article.get('referenced_by_count', 0)}\n"
        )
        result_string += "-" * 50 + "\n"
    logger.info(result_string)
    return None


# Strands Agents Tool Wrapper
@tool
def search_pmc_tool(
    query: str,
    rerank_by: Literal["references", None] = "references",
) -> dict:
    """Search PubMed Central (PMC) for scientific articles with citation analysis and reranking.

    This tool performs comprehensive literature searches across PMC with optional citation
    analysis. Results can be ranked by how frequently they are cited within the result set,
    helping surface the most influential papers. Perfect for research, literature reviews,
    and finding authoritative sources on scientific topics.

    Args:
        query: Search query using PMC search syntax. Supports:
            - Field tags: [Title], [Author], [Journal], [Affiliation]
            - Boolean operators: AND, OR, NOT (must be uppercase)
            - Phrase search: Use quotes for exact phrases
            - Author search: Last name with initials, e.g., "Smith J[au]"
            - Journal search: Full title, abbreviation, or ISSN
            - Date filters (see examples below for date search syntax)
        rerank_by: Reranking method for search results. Options are:
            - (default) "references": Rerank results in decreasing order of incoming references. Use to identify the most influenctial articles.
            - None. Returns articles in the same order as the PMC search API. Use to identify newer articles or those tha capture a wider range of perspective.

    Date Search Syntax:
        - Single date: "2020/06/01[dp]" (month and day optional: "2020[dp]")
        - Date range: "2020/01/01:2023/12/31[dp]" (use colon between dates)
        - Relative dates: "last 2 years[dp]", "last 6 months[dp]", "last 30 days[dp]"
        - Publication date: [dp] or [pubdate]
        - Electronic pub date: [epdat]
        - Print pub date: [ppdat]
        - PMC live date: [pmcrdat]

    Returns:
        Dictionary with status and content:
        - status: "success" or "error"
        - content: List with single dict containing "text" field with formatted results
            including article titles, authors, abstracts, DOIs, and citation counts

    Examples:
        Basic search:
            search_pmc_tool("machine learning in healthcare")

        Search with recent date filter:
            search_pmc_tool("mRNA vaccine COVID-19 AND last 2 years[dp]", rerank_by=None)

        Search with specific date range:
            search_pmc_tool("CRISPR gene editing AND 2020:2023[dp]")

        Search by author and date:
            search_pmc_tool("Smith J[au] AND cancer AND 2022/01/01:2024/12/31[dp]")

        Search by journal and recent articles:
            search_pmc_tool("Nature[journal] AND last 6 months[dp]", rerank_by=None)

    """
    return search_pmc(query=query, rerank_by=rerank_by)
