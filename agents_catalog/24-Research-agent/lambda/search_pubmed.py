# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# Adapted from https://github.com/andybrandt/mcp-simple-pubmed
# SPDX-License-Identifier: MIT

import logging
import os
from typing import Any, Dict, List
from xml.etree.ElementTree import Element
import httpx
from defusedxml import ElementTree as ET

# Global configuration for commercial use filtering
COMMERCIAL_USE_ONLY = True


logger = logging.getLogger("strands")

# Type alias forbetter readibility
ArticleDict = Dict[str, Any]
ToolResult = Dict[str, Any]
ReferenceDict = Dict[str, str]

# Tool specification for Strands Agents framework
TOOL_SPEC = {
    "name": "search_pubmed",
    "description": "Search PubMed for articles matching the query with optional citation analysis and ranking capabilities.",
    "inputSchema": {
        "json": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query for PubMed using standard PubMed search syntax",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results to fetch from initial search",
                    "default": 100,
                    "minimum": 1,
                    "maximum": 1000,
                },
                "max_records": {
                    "type": "integer",
                    "description": "Maximum number of articles to return in final results",
                    "minimum": 1,
                    "maximum": 100,
                },
                "rerank": {
                    "type": "string",
                    "description": "Reranking method to apply",
                    "enum": ["referenced_by"],
                    "default": "referenced_by",
                },
            },
            "required": ["query"],
        }
    },
}


def search_pubmed(tool: Dict[str, Any], **kwargs: Any) -> ToolResult:
    """
    Search PubMed for articles matching the query with ToolResult format.

    This function performs a comprehensive search of PubMed literature with optional
    citation analysis and ranking capabilities. Results can be ranked by citation count
    within the result set to surface the most influential papers. The function follows
    the Strands Agents framework ToolResult format for consistent response handling.

    Args:
        tool: Dictionary containing toolUseId and input parameters
            - toolUseId: String identifier for the tool invocation
            - input: Dictionary with search parameters:
                - query (required): The search query for PubMed using standard PubMed search syntax
                - max_results (optional): Maximum number of results to fetch from initial search (default: 100, range: 1-1000)
                - max_records (optional): Maximum number of articles to return in final results (range: 1-100)
                - rerank (optional): Reranking method to apply (default: "referenced_by", options: ["referenced_by"])
        **kwargs: Additional keyword arguments (unused)

    Returns:
        ToolResult dictionary with the following structure:
        - toolUseId: String identifier from input tool parameter
        - status: "success" or "error"
        - content: List containing a single dictionary with "text" field:
            - For success: Formatted search results with article details, citation counts, and summary
            - For error: Descriptive error message explaining what went wrong

    ToolResult Success Response Format:
        {
            "toolUseId": "search_123",
            "status": "success",
            "content": [{"text": "Showing 5 of 50 articles found\\nResults ranked by citation count...\\n\\nArticle 1\\n..."}]
        }

    ToolResult Error Response Format:
        {
            "toolUseId": "search_123",
            "status": "error",
            "content": [{"text": "Error: query parameter is required"}]
        }

    Examples:
        # Basic search with citation ranking
        tool_input = {
            "toolUseId": "search_123",
            "input": {
                "query": "CRISPR gene editing",
                "max_results": 50,
                "max_records": 10
            }
        }
        result = search_pubmed(tool_input)

        # Advanced search with temporal filters
        tool_input = {
            "toolUseId": "search_456",
            "input": {
                "query": "mRNA vaccine COVID-19 AND \"last 2 years\"[dp]",
                "max_results": 200,
                "max_records": 20,
                "rerank": "referenced_by"
            }
        }
        result = search_pubmed(tool_input)

        # Handle success response
        if result["status"] == "success":
            formatted_articles = result["content"][0]["text"]
            print(formatted_articles)
        else:
            error_message = result["content"][0]["text"]
            print(f"Search failed: {error_message}")
    """
    # Extract toolUseId from tool parameter dictionary
    tool_use_id = tool.get("toolUseId", "")

    try:
        # Extract search parameters from tool["input"] dictionary
        input_params = tool.get("input", {})

        # Validate all parameters and return error ToolResult if validation fails
        validation_error = _validate_parameters(tool_use_id, input_params)
        if validation_error is not None:
            return validation_error

        # Extract validated parameters with defaults
        query = input_params.get("query")
        max_results = input_params.get("max_results", 100)
        max_records = input_params.get("max_records")
        rerank = input_params.get("rerank", "referenced_by")

        logger.info(f"Searching PubMed for: {query}")

        base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
        search_url = f"{base_url}/esearch.fcgi"

        # Build search query with filters
        try:
            filtered_query = _build_search_query(query)
        except Exception as query_error:
            logger.error(f"Error building search query: {query_error}")
            return {
                "toolUseId": tool_use_id,
                "status": "error",
                "content": [
                    {"text": f"Error building search query: {str(query_error)}"}
                ],
            }

        search_params = {
            "db": "pubmed",
            "term": filtered_query,
            "retmax": max_results,
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
            logger.error(f"HTTP error during PubMed search: {http_error}")
            return {
                "toolUseId": tool_use_id,
                "status": "error",
                "content": [
                    {
                        "text": f"HTTP error during PubMed search: {http_error.response.status_code} - {str(http_error)}"
                    }
                ],
            }
        except httpx.TimeoutException as timeout_error:
            logger.error(f"Timeout error during PubMed search: {timeout_error}")
            return {
                "toolUseId": tool_use_id,
                "status": "error",
                "content": [
                    {
                        "text": f"Request timeout during PubMed search: {str(timeout_error)}"
                    }
                ],
            }
        except httpx.NetworkError as network_error:
            logger.error(f"Network error during PubMed search: {network_error}")
            return {
                "toolUseId": tool_use_id,
                "status": "error",
                "content": [
                    {
                        "text": f"Network error during PubMed search: {str(network_error)}"
                    }
                ],
            }
        except httpx.RequestError as request_error:
            logger.error(f"Request error during PubMed search: {request_error}")
            return {
                "toolUseId": tool_use_id,
                "status": "error",
                "content": [
                    {
                        "text": f"Request error during PubMed search: {str(request_error)}"
                    }
                ],
            }

        try:
            search_data = search_response.json()
        except Exception as json_error:
            logger.error(f"JSON parsing error in search response: {json_error}")
            return {
                "toolUseId": tool_use_id,
                "status": "error",
                "content": [
                    {"text": f"Error parsing search response: {str(json_error)}"}
                ],
            }

        try:
            # Extract IDs
            id_list = search_data["esearchresult"]["idlist"]
            logger.info(f"Found {len(id_list)} article pmids")
        except KeyError as key_error:
            logger.error(f"Unexpected search response format: {key_error}")
            return {
                "toolUseId": tool_use_id,
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
                "toolUseId": tool_use_id,
                "status": "success",
                "content": [{"text": "No articles found for the given query."}],
            }

        # Fetch article details using the batch function
        try:
            articles = fetch_pubmed(id_list)
        except Exception as fetch_error:
            logger.error(f"Error fetching article details: {fetch_error}")
            return {
                "toolUseId": tool_use_id,
                "status": "error",
                "content": [
                    {"text": f"Error fetching article details: {str(fetch_error)}"}
                ],
            }

        # Apply reranking if requested
        if rerank == "referenced_by":
            try:
                logger.info("Calculating citation relationships and ranking articles")
                enhanced_articles = _calculate_referenced_by_counts(articles)
                ranked_articles = _rank_by_citations(enhanced_articles)
                logger.info("Citation ranking completed successfully")

                # Apply max_records limit to ranked results
                if max_records is not None:
                    final_results = ranked_articles[:max_records]
                    logger.info(
                        f"Applied max_records limit: returning {len(final_results)} of {len(ranked_articles)} articles"
                    )
                else:
                    final_results = ranked_articles

                _print_fetch_results(final_results, n=3)

                # Format search results using article formatting functions
                # Pass the total before max_records limit for proper summary
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
                        "toolUseId": tool_use_id,
                        "status": "error",
                        "content": [
                            {
                                "text": f"Error formatting search results: {str(format_error)}"
                            }
                        ],
                    }

                return {
                    "toolUseId": tool_use_id,
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

        # Return original results (either when rerank=None or as fallback)
        if max_records is not None:
            final_results = articles[:max_records]
            logger.info(
                f"Applied max_records limit: returning {len(final_results)} of {len(articles)} articles"
            )
        else:
            final_results = articles

        _print_fetch_results(final_results, n=10)

        # Format search results using article formatting functions
        # Pass the total before max_records limit for proper summary
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
                "toolUseId": tool_use_id,
                "status": "error",
                "content": [
                    {"text": f"Error formatting search results: {str(format_error)}"}
                ],
            }

        return {
            "toolUseId": tool_use_id,
            "status": "success",
            "content": [{"text": formatted_content}],
        }

    except Exception as unexpected_error:
        logger.error(f"Unexpected error in search_pubmed: {unexpected_error}")
        return {
            "toolUseId": tool_use_id,
            "status": "error",
            "content": [
                {
                    "text": f"Unexpected error during PubMed search: {str(unexpected_error)}"
                }
            ],
        }


def fetch_pubmed(pmids: List[str]) -> List[ArticleDict]:
    """
    Get detailed information about one or more PubMed articles.

    Args:
        pmids: List of PubMed IDs to fetch

    Returns:
        List of article dictionaries with detailed information including keywords and references.
        Empty articles are filtered out. Returns empty list if no articles found or on error.
    """
    if not pmids:
        return []

    logger.info(f"Fetching {len(pmids)} PubMed articles")

    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    fetch_url = f"{base_url}/efetch.fcgi"

    fetch_params = {"db": "pubmed", "id": ",".join(pmids), "retmode": "xml"}

    try:
        try:
            fetch_response = httpx.post(
                fetch_url, data=_get_api_key_params(fetch_params)
            )
            fetch_response.raise_for_status()
        except httpx.HTTPStatusError as http_error:
            logger.error(f"HTTP error during article fetch: {http_error}")
            raise Exception(
                f"HTTP error during article fetch: {http_error.response.status_code} - {str(http_error)}"
            )
        except httpx.TimeoutException as timeout_error:
            logger.error(f"Timeout error during article fetch: {timeout_error}")
            raise Exception(
                f"Request timeout during article fetch: {str(timeout_error)}"
            )
        except httpx.NetworkError as network_error:
            logger.error(f"Network error during article fetch: {network_error}")
            raise Exception(f"Network error during article fetch: {str(network_error)}")
        except httpx.RequestError as request_error:
            logger.error(f"Request error during article fetch: {request_error}")
            raise Exception(f"Request error during article fetch: {str(request_error)}")

        # Parse XML response
        try:
            root = ET.fromstring(fetch_response.text)
        except ET.ParseError as xml_error:
            logger.error(f"XML parsing error in fetch response: {xml_error}")
            raise Exception(f"Error parsing XML response from PubMed: {str(xml_error)}")
        except Exception as parse_error:
            logger.error(f"Unexpected parsing error in fetch response: {parse_error}")
            raise Exception(f"Error parsing response from PubMed: {str(parse_error)}")

        articles = []

        for article_element in root.findall(".//PubmedArticle"):
            try:
                article = _extract_article_data(article_element)
                if article:  # Only add non-empty articles
                    articles.append(article)
            except Exception as e:
                logger.error(f"Error parsing individual article: {e}")
                continue

        logger.info(f"Successfully fetched {len(articles)} articles")
        return articles

    except Exception as e:
        logger.error(f"Error fetching article details: {e}")
        # Re-raise the exception so search_pubmed can handle it properly
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


def _build_search_query(query: str) -> str:
    """Build the search query with appropriate filters."""
    if COMMERCIAL_USE_ONLY:
        license_filter = (
            " AND (pmc cc0 license [filter] OR pmc cc by license [filter] "
            "OR pmc cc by-sa license [filter] OR pmc cc by-nd license [filter])"
        )
    else:
        license_filter = " AND pubmed pmc open access[Filter]"

    return query + license_filter


def _extract_article_data(article_element: Element) -> ArticleDict:
    """Extract article data from XML element."""
    article = {}

    # Extract PMID
    pmid_element = article_element.find(".//PMID")
    if pmid_element is not None and pmid_element.text:
        article["id"] = pmid_element.text

    # Extract title
    title_element = article_element.find(".//ArticleTitle")
    if title_element is not None:
        # Use itertext() to get all text content including text within child elements
        title_text = "".join(title_element.itertext()).strip()
        if title_text:
            article["title"] = title_text

    # Extract abstract
    abstract_parts = article_element.findall(".//AbstractText")
    if abstract_parts:
        abstract_texts = []
        for part in abstract_parts:
            # Use itertext() to get all text content including text within child elements
            text_content = "".join(part.itertext()).strip()
            if text_content:
                abstract_texts.append(text_content)
        if abstract_texts:
            abstract_content = " ".join(abstract_texts)
            article["abstract"] = (
                abstract_content  # Keep existing field for backward compatibility
            )
            article["text"] = abstract_content  # Add new consistent field name

    # Extract authors
    author_elements = article_element.findall(".//Author")
    if author_elements:
        authors = []
        for author in author_elements:
            last_name_element = author.find("LastName")
            fore_name_element = author.find("ForeName")

            if last_name_element is not None and fore_name_element is not None:
                if last_name_element.text and fore_name_element.text:
                    authors.append(f"{fore_name_element.text} {last_name_element.text}")
            elif last_name_element is not None and last_name_element.text:
                authors.append(last_name_element.text)

        if authors:
            article["authors"] = ", ".join(authors)

    # Extract journal info
    journal_element = article_element.find(".//Journal/Title")
    if journal_element is not None and journal_element.text:
        article["journal"] = journal_element.text

    # Extract publication year
    pub_date_element = article_element.find(".//PubDate/Year")
    if pub_date_element is not None and pub_date_element.text:
        article["year"] = pub_date_element.text

    # Extract DOI and PMC from ArticleIdList (only from the main article, not references)
    # Look specifically in PubmedData/ArticleIdList to avoid picking up DOIs from references
    pubmed_data = article_element.find("PubmedData")
    if pubmed_data is not None:
        article_id_list = pubmed_data.find("ArticleIdList")
        if article_id_list is not None:
            article_id_elements = article_id_list.findall("ArticleId")
            for article_id in article_id_elements:
                id_type = article_id.get("IdType")
                if id_type == "doi" and article_id.text:
                    article["doi"] = article_id.text
                    # Create URI from DOI
                    doi_url = f"https://doi.org/{article_id.text}"
                    article["uri"] = (
                        doi_url  # Keep existing field for backward compatibility
                    )
                    article["source"] = doi_url  # Add new consistent field name
                elif id_type == "pmc" and article_id.text:
                    article["pmc"] = article_id.text

    # Extract references from ReferenceList
    reference_elements = article_element.findall(".//Reference")
    if reference_elements:
        references = []
        for ref in reference_elements:
            # Look for PubMed ID in the reference
            ref_pmid_element = ref.find(".//ArticleId[@IdType='pubmed']")
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

    # Build a citation graph: pmid -> set of pmids that reference it
    citation_graph = {}

    # Initialize citation counts for all articles
    for article in articles:
        article_id = article.get("id")
        if article_id:
            citation_graph[article_id] = set()

    # Build the citation relationships
    for article in articles:
        article_id = article.get("id")
        references = article.get("references", [])

        # Skip if article has no ID
        if not article_id:
            continue

        # Process each reference
        for ref_pmid in references:
            # Handle edge cases
            if not ref_pmid:  # Skip empty/None references
                continue
            if not ref_pmid.isdigit():  # Skip invalid PMIDs (non-numeric)
                continue
            if ref_pmid == article_id:  # Skip self-references
                continue

            # Add this article as a referencing article for the referenced PMID
            if ref_pmid in citation_graph:
                citation_graph[ref_pmid].add(article_id)

    # Calculate referenced_by_count for each article
    for article in articles:
        # Create a copy of the article dict
        enhanced_article = article.copy()

        article_id = article.get("id")
        if article_id and article_id in citation_graph:
            # Count how many articles reference this one
            enhanced_article["referenced_by_count"] = len(citation_graph[article_id])
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

    # Metadata (ID, DOI, PMC)
    article_id = article.get("id")
    if article_id:
        lines.append(f"PMID: {article_id}")

    doi = article.get("doi")
    if doi:
        lines.append(f"DOI: {doi}")

    pmc = article.get("pmc")
    if pmc:
        lines.append(f"PMC: {pmc}")

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
        total_found: Total number of articles found in search (before max_records limit)

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
        result_string += f"ID: {article.get('id', 'No ID')}\n"
        result_string += f"PMCID: {article.get('pmc', 'No PMCID')}\n"
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


def _validate_parameters(
    tool_use_id: str, input_params: Dict[str, Any]
) -> ToolResult | None:
    """
    Validate input parameters and return error ToolResult if validation fails.

    Args:
        tool_use_id: Tool use identifier for error responses
        input_params: Dictionary of input parameters to validate

    Returns:
        ToolResult with error if validation fails, None if validation passes
    """
    # Validate query parameter (required string)
    query = input_params.get("query")
    if query is None:
        return {
            "toolUseId": tool_use_id,
            "status": "error",
            "content": [{"text": "Error: query parameter is required"}],
        }

    if not isinstance(query, str):
        return {
            "toolUseId": tool_use_id,
            "status": "error",
            "content": [{"text": "Error: query parameter must be a string"}],
        }

    if not query.strip():
        return {
            "toolUseId": tool_use_id,
            "status": "error",
            "content": [{"text": "Error: query parameter cannot be empty"}],
        }

    # Validate max_results parameter (integer 1-1000, default 100)
    max_results = input_params.get("max_results", 100)
    if not isinstance(max_results, int):
        return {
            "toolUseId": tool_use_id,
            "status": "error",
            "content": [{"text": "Error: max_results parameter must be an integer"}],
        }

    if max_results < 1 or max_results > 1000:
        return {
            "toolUseId": tool_use_id,
            "status": "error",
            "content": [
                {"text": "Error: max_results parameter must be between 1 and 1000"}
            ],
        }

    # Validate max_records parameter (optional integer 1-100)
    max_records = input_params.get("max_records")
    if max_records is not None:
        if not isinstance(max_records, int):
            return {
                "toolUseId": tool_use_id,
                "status": "error",
                "content": [
                    {"text": "Error: max_records parameter must be an integer"}
                ],
            }

        if max_records < 1 or max_records > 100:
            return {
                "toolUseId": tool_use_id,
                "status": "error",
                "content": [
                    {"text": "Error: max_records parameter must be between 1 and 100"}
                ],
            }

    # Validate rerank parameter (enum ["referenced_by"], default "referenced_by")
    rerank = input_params.get("rerank", "referenced_by")
    if not isinstance(rerank, str):
        return {
            "toolUseId": tool_use_id,
            "status": "error",
            "content": [{"text": "Error: rerank parameter must be a string"}],
        }

    if rerank not in ["referenced_by"]:
        return {
            "toolUseId": tool_use_id,
            "status": "error",
            "content": [{"text": "Error: rerank parameter must be 'referenced_by'"}],
        }

    # All validations passed
    return None
