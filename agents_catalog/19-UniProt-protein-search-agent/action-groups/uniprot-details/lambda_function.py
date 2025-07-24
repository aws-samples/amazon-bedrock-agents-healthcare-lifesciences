import json
import urllib.request
import urllib.parse
import logging
import re
from typing import Dict, List, Any

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for UniProt protein details retrieval.

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

        accession_id = param_dict.get("accession_id", "").strip().upper()
        include_sequence = param_dict.get("include_sequence", "false").lower() == "true"
        include_features = param_dict.get("include_features", "true").lower() == "true"

        if not accession_id:
            return create_response(event, "Error: Accession ID parameter is required.")

        # Validate accession ID format
        if not validate_accession_id(accession_id):
            return create_response(
                event,
                f"Error: Invalid UniProt accession ID format: {accession_id}. Expected format: 6-10 alphanumeric characters (e.g., P04637)",
            )

        logger.info(
            f"Retrieving protein details: accession_id='{accession_id}', include_sequence={include_sequence}, include_features={include_features}"
        )

        # Call UniProt API for details
        results = get_protein_details(accession_id, include_sequence, include_features)

        return create_response(event, results)

    except Exception as e:
        logger.error(f"Error retrieving protein details: {str(e)}", exc_info=True)
        return create_response(event, f"Error retrieving protein details: {str(e)}")


def validate_accession_id(accession_id: str) -> bool:
    """
    Validate UniProt accession ID format.

    Args:
        accession_id: Accession ID to validate

    Returns:
        True if valid format, False otherwise
    """
    # UniProt accession IDs are 6-10 alphanumeric characters
    pattern = r"^[A-Z0-9]{6,10}$"
    return re.match(pattern, accession_id) is not None


def get_protein_details(
    accession_id: str, include_sequence: bool, include_features: bool
) -> str:
    """
    Retrieve detailed protein information from UniProt.

    Args:
        accession_id: UniProt accession ID
        include_sequence: Whether to include amino acid sequence
        include_features: Whether to include protein features

    Returns:
        Formatted protein details as string
    """
    try:
        # UniProt REST API endpoint for entry retrieval
        base_url = f"https://rest.uniprot.org/uniprotkb/{accession_id}"

        # Fields to retrieve
        fields = [
            "accession",
            "id",
            "protein_name",
            "gene_names",
            "organism_name",
            "length",
            "cc_function",
            "cc_subcellular_location",
            "cc_disease",
            "ft_domain",
            "ft_region",
            "xref_pdb",
        ]

        if include_sequence:
            fields.append("sequence")

        # Construct URL parameters
        params = {"format": "json", "fields": ",".join(fields)}

        url = f"{base_url}?{urllib.parse.urlencode(params)}"
        logger.info(f"Calling UniProt API: {url}")

        # Make the API request
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "AWS-Lambda-UniProt-Agent/1.0")

        with urllib.request.urlopen(req, timeout=25) as response:
            if response.status == 404:
                return f"Protein with accession ID '{accession_id}' not found in UniProt database."
            elif response.status != 200:
                raise Exception(f"UniProt API returned status {response.status}")

            data = json.loads(response.read().decode("utf-8"))

        # Format the results
        return format_protein_details(
            data, accession_id, include_sequence, include_features
        )

    except urllib.error.URLError as e:
        logger.error(f"Network error calling UniProt API: {str(e)}")
        return f"Network error accessing UniProt database: {str(e)}"
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing UniProt API response: {str(e)}")
        return f"Error parsing UniProt response: {str(e)}"
    except Exception as e:
        logger.error(f"Unexpected error in UniProt details retrieval: {str(e)}")
        return f"Unexpected error retrieving protein details: {str(e)}"


def format_protein_details(
    data: Dict[str, Any],
    accession_id: str,
    include_sequence: bool,
    include_features: bool,
) -> str:
    """
    Format detailed protein information for display.

    Args:
        data: Raw UniProt API response
        accession_id: Protein accession ID
        include_sequence: Whether sequence was requested
        include_features: Whether features were requested

    Returns:
        Formatted protein details string
    """
    try:
        # Basic protein information
        protein_name = (
            data.get("proteinDescription", {})
            .get("recommendedName", {})
            .get("fullName", {})
            .get("value", "N/A")
        )
        gene_names = data.get("genes", [])
        primary_gene = (
            gene_names[0].get("geneName", {}).get("value", "N/A")
            if gene_names
            else "N/A"
        )
        organism = data.get("organism", {}).get("scientificName", "N/A")
        length = data.get("sequence", {}).get("length", "N/A")

        result = [f"Detailed Information for Protein {accession_id}"]
        result.append("=" * 50)
        result.append(f"Protein Name: {protein_name}")
        result.append(f"Primary Gene: {primary_gene}")
        result.append(f"Organism: {organism}")
        result.append(f"Length: {length} amino acids")
        result.append("")

        # Function information
        function_info = extract_function_info(data)
        if function_info:
            result.append("FUNCTION:")
            result.append(function_info)
            result.append("")

        # Subcellular localization
        location_info = extract_location_info(data)
        if location_info:
            result.append("SUBCELLULAR LOCALIZATION:")
            result.append(location_info)
            result.append("")

        # Disease associations
        disease_info = extract_disease_info(data)
        if disease_info:
            result.append("DISEASE ASSOCIATIONS:")
            result.append(disease_info)
            result.append("")

        # Protein features (if requested)
        if include_features:
            features_info = extract_features_info(data)
            if features_info:
                result.append("PROTEIN FEATURES:")
                result.append(features_info)
                result.append("")

        # PDB structures
        pdb_info = extract_pdb_info(data)
        if pdb_info:
            result.append("3D STRUCTURES (PDB):")
            result.append(pdb_info)
            result.append("")

        # Amino acid sequence (if requested)
        if include_sequence:
            sequence = data.get("sequence", {}).get("value", "")
            if sequence:
                result.append("AMINO ACID SEQUENCE:")
                result.append(format_sequence(sequence))
                result.append("")

        return "\n".join(result)

    except Exception as e:
        logger.error(f"Error formatting protein details: {str(e)}")
        return f"Error formatting protein details for {accession_id}: {str(e)}"


def extract_function_info(data: Dict[str, Any]) -> str:
    """Extract function information from protein data."""
    comments = data.get("comments", [])
    for comment in comments:
        if comment.get("commentType") == "FUNCTION":
            texts = comment.get("texts", [])
            if texts:
                return texts[0].get("value", "N/A")
    return ""


def extract_location_info(data: Dict[str, Any]) -> str:
    """Extract subcellular localization information."""
    comments = data.get("comments", [])
    for comment in comments:
        if comment.get("commentType") == "SUBCELLULAR_LOCATION":
            locations = comment.get("subcellularLocations", [])
            if locations:
                location_names = []
                for loc in locations:
                    location = loc.get("location", {})
                    if location:
                        location_names.append(location.get("value", ""))
                return ", ".join(filter(None, location_names))
    return ""


def extract_disease_info(data: Dict[str, Any]) -> str:
    """Extract disease association information."""
    comments = data.get("comments", [])
    diseases = []
    for comment in comments:
        if comment.get("commentType") == "DISEASE":
            disease = comment.get("disease", {})
            if disease:
                disease_name = disease.get("diseaseId", "")
                description = comment.get("texts", [])
                if description:
                    desc_text = (
                        description[0].get("value", "")[:200] + "..."
                        if len(description[0].get("value", "")) > 200
                        else description[0].get("value", "")
                    )
                    diseases.append(f"- {disease_name}: {desc_text}")
    return "\n".join(diseases) if diseases else ""


def extract_features_info(data: Dict[str, Any]) -> str:
    """Extract protein features information."""
    features = data.get("features", [])
    if not features:
        return ""

    feature_types = {}
    for feature in features[:10]:  # Limit to first 10 features
        feature_type = feature.get("type", "Unknown")
        description = feature.get("description", "")
        location = feature.get("location", {})
        start = location.get("start", {}).get("value", "")
        end = location.get("end", {}).get("value", "")

        if feature_type not in feature_types:
            feature_types[feature_type] = []

        location_str = f"{start}-{end}" if start and end else "Unknown"
        feature_types[feature_type].append(f"  {location_str}: {description}")

    result = []
    for ftype, flist in feature_types.items():
        result.append(f"- {ftype}:")
        result.extend(flist[:3])  # Limit to 3 per type

    return "\n".join(result)


def extract_pdb_info(data: Dict[str, Any]) -> str:
    """Extract PDB structure information."""
    xrefs = data.get("uniProtKBCrossReferences", [])
    pdb_ids = []
    for xref in xrefs:
        if xref.get("database") == "PDB":
            pdb_ids.append(xref.get("id", ""))

    if pdb_ids:
        return f"Available structures: {', '.join(pdb_ids[:5])}"  # Limit to first 5
    return ""


def format_sequence(sequence: str) -> str:
    """Format amino acid sequence for display."""
    # Break sequence into lines of 60 characters
    lines = []
    for i in range(0, len(sequence), 60):
        line_num = str(i + 1).rjust(6)
        seq_line = sequence[i : i + 60]
        lines.append(f"{line_num} {seq_line}")

    return "\n".join(lines)


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
