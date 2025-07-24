import json
import urllib.request
import urllib.parse
import logging
from typing import Dict, List, Any

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for UniProt protein search functionality.

    Args:
        event: Lambda event containing parameters from Bedrock
        context: Lambda context object

    Returns:
        Formatted response for Bedrock
    """
    try:
        logger.info(f"Received event: {json.dumps(event)}")

        # Extract parameters from the event
        parameters = event.get("parameters", [])
        param_dict = {param["name"]: param["value"] for param in parameters}

        query = param_dict.get("query", "").strip()
        organism = param_dict.get("organism", "human").strip()
        limit = min(int(param_dict.get("limit", 10)), 50)  # Cap at 50

        if not query:
            return create_response(
                event, "Error: Query parameter is required for protein search."
            )

        logger.info(
            f"Searching for proteins: query='{query}', organism='{organism}', limit={limit}"
        )

        # Construct UniProt search query
        search_query = construct_search_query(query, organism)
        logger.info(f"Constructed UniProt query: {search_query}")

        # Call UniProt API
        results = search_uniprot_proteins(search_query, limit)

        return create_response(event, results)

    except Exception as e:
        logger.error(f"Error in protein search: {str(e)}", exc_info=True)
        return create_response(event, f"Error searching proteins: {str(e)}")


def construct_search_query(query: str, organism: str) -> str:
    """
    Construct a UniProt search query from user input.

    Args:
        query: User search query
        organism: Target organism

    Returns:
        Formatted UniProt search query
    """
    # Handle organism filtering
    organism_lower = organism.lower()
    if organism_lower in ["human", "homo sapiens"]:
        organism_filter = 'organism_name:"Homo sapiens"'
    elif organism_lower in ["mouse", "mus musculus"]:
        organism_filter = 'organism_name:"Mus musculus"'
    elif organism_lower in ["rat", "rattus norvegicus"]:
        organism_filter = 'organism_name:"Rattus norvegicus"'
    else:
        # Use the organism as provided
        organism_filter = f'organism_name:"{organism}"'

    # Handle multi-word queries by creating flexible search terms
    query_terms = query.strip().split()

    if len(query_terms) == 1:
        # Single word - search in multiple fields
        single_term = query_terms[0]
        search_terms = f'(protein_name:"{single_term}" OR gene:"{single_term}" OR cc_function:"{single_term}" OR cc_disease:"{single_term}" OR keyword:"{single_term}")'
    else:
        # Multiple words - create flexible combinations
        full_phrase = " ".join(query_terms)

        # Create search combinations:
        # 1. Full phrase in quotes for exact matches
        # 2. All terms without quotes for broader matching
        # 3. Individual terms for maximum flexibility
        search_parts = []

        # Full phrase search (exact match)
        search_parts.append(f'protein_name:"{full_phrase}"')
        search_parts.append(f'cc_function:"{full_phrase}"')
        search_parts.append(f'cc_disease:"{full_phrase}"')

        # All terms together (broader match)
        all_terms = " AND ".join(query_terms)
        search_parts.append(f"({all_terms})")

        # Individual terms for maximum coverage
        for term in query_terms:
            search_parts.append(f'protein_name:"{term}"')
            search_parts.append(f'gene:"{term}"')
            search_parts.append(f'keyword:"{term}"')

        search_terms = f"({' OR '.join(search_parts)})"

    return f"{search_terms} AND {organism_filter}"


def search_uniprot_proteins(query: str, limit: int) -> str:
    """
    Search UniProt database for proteins matching the query.

    Args:
        query: UniProt formatted search query
        limit: Maximum number of results to return

    Returns:
        Formatted search results as string
    """
    try:
        # UniProt REST API endpoint for search
        base_url = "https://rest.uniprot.org/uniprotkb/search"

        # Fields to retrieve
        fields = "accession,id,protein_name,gene_names,organism_name,length,cc_function"

        # Construct URL parameters
        params = {
            "query": query,
            "format": "json",
            "size": str(limit),
            "fields": fields,
        }

        url = f"{base_url}?{urllib.parse.urlencode(params)}"
        logger.info(f"Calling UniProt API: {url}")

        # Make the API request
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "AWS-Lambda-UniProt-Agent/1.0")

        with urllib.request.urlopen(req, timeout=25) as response:
            if response.status != 200:
                raise Exception(f"UniProt API returned status {response.status}")

            data = json.loads(response.read().decode("utf-8"))

        # Format the results
        return format_search_results(data, query)

    except urllib.error.URLError as e:
        logger.error(f"Network error calling UniProt API: {str(e)}")
        return f"Network error accessing UniProt database: {str(e)}"
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing UniProt API response: {str(e)}")
        return f"Error parsing UniProt response: {str(e)}"
    except Exception as e:
        logger.error(f"Unexpected error in UniProt search: {str(e)}")
        return f"Unexpected error searching UniProt: {str(e)}"


def format_search_results(data: Dict[str, Any], query: str) -> str:
    """
    Format UniProt search results for display.

    Args:
        data: Raw UniProt API response
        query: Original search query

    Returns:
        Formatted results string
    """
    results = data.get("results", [])

    if not results:
        return f"No proteins found matching query: {query}"

    formatted_results = [f"Found {len(results)} protein(s) matching your search:\n"]

    for i, protein in enumerate(results, 1):
        accession = protein.get("primaryAccession", "N/A")
        protein_name = (
            protein.get("proteinDescription", {})
            .get("recommendedName", {})
            .get("fullName", {})
            .get("value", "N/A")
        )
        gene_names = protein.get("genes", [])
        gene_name = (
            gene_names[0].get("geneName", {}).get("value", "N/A")
            if gene_names
            else "N/A"
        )
        organism = protein.get("organism", {}).get("scientificName", "N/A")
        length = protein.get("sequence", {}).get("length", "N/A")

        # Get function description (first sentence)
        function_comments = protein.get("comments", [])
        function_desc = "N/A"
        for comment in function_comments:
            if comment.get("commentType") == "FUNCTION":
                texts = comment.get("texts", [])
                if texts:
                    function_desc = (
                        texts[0].get("value", "N/A")[:200] + "..."
                        if len(texts[0].get("value", "")) > 200
                        else texts[0].get("value", "N/A")
                    )
                break

        formatted_results.append(f"""
{i}. {protein_name}
   - Accession ID: {accession}
   - Gene: {gene_name}
   - Organism: {organism}
   - Length: {length} amino acids
   - Function: {function_desc}
""")

    formatted_results.append(
        "\nTo get detailed information about any protein, use the accession ID with the get_protein_details function."
    )

    return "\n".join(formatted_results)


def create_response(event: Dict[str, Any], result: str) -> Dict[str, Any]:
    """
    Create a properly formatted response for Bedrock.

    Args:
        event: Original event from Bedrock
        result: Result string to return

    Returns:
        Formatted response dictionary
    """
    return {
        "response": {
            "actionGroup": event["actionGroup"],
            "function": event["function"],
            "functionResponse": {"responseBody": {"TEXT": {"body": result}}},
        }
    }
