# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
import json
import logging
import os
from pathlib import Path
from rapidfuzz import process, fuzz, utils
from sec_edgar_api import EdgarClient
from typing import Dict, Optional, List
from typing import List, Dict
from pathlib import Path
import json

from txtai.embeddings import Embeddings
import warnings

warnings.filterwarnings("ignore", category=FutureWarning)

# Note: From https://www.sec.gov/submit-filings/filer-support-resources/edgar-glossary

# CIK (Central Index Key):
# A unique number that the SEC assigns to each EDGAR filer and that is associated
# with the filer’s EDGAR filing account.


# Taxonomy:
# Electronic dictionary of business reporting elements used to report business data.
# A taxonomy is composed of an element names file (.xsd) and relationships files directly
# referenced by that schema. Together the set of related schemas and relationships files
# constitute a taxonomy. Information on the current taxonomies supported for the SEC’s
# interactive data programs is available from the Office of Structured Disclosure in the
# Division of Economic and Risk Analysis.
# e.g. dei, us-gaap, srt

# Tag:
# An identifier that highlights specific information to EDGAR that is in the format required by the EDGAR Filer Manual. e.g. EntityCommonStockSharesOutstanding, AcceleratedShareRepurchasesFinalPricePaidPerShare

# Company Concept:
# A combination of a taxonomy and tag with a separate array of facts for each units on measure that the company has chosen to disclose (e.g. net profits reported in U.S. dollars and in Canadian dollars).

valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
log_level = os.environ.get("LOG_LEVEL", "INFO").strip().upper()
if log_level not in valid_log_levels:
    log_level = "INFO"
logging.basicConfig(
    format="[%(asctime)s] p%(process)s {%(filename)s:%(lineno)d} %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)
logger.setLevel(log_level)

FUNCTION_NAMES = ["get_company_concept", "list_available_facts", "get_company_facts"]
DEFAULT_SCORE_CUTOFF = (
    80  # Define constant for default score cutoff for cik fuzzy matching
)

# amazonq-ignore-next-line
edgar = EdgarClient(
    user_agent=os.environ.get("USER_AGENT", "AWS HCLS AGENTS").strip().upper()
)

##############################################################################
# Get CIK for company name
##############################################################################


def get_cik(
    query: str, data_file: Path, score_cutoff: int = DEFAULT_SCORE_CUTOFF
) -> Optional[Dict]:
    """
    Look up the SEC Central Index Key (CIK) for a given company name using fuzzy matching.

    Args:
        query (str): The company name to search for
        data_file (Path): Path to the JSON file containing company data
        score_cutoff (int): Minimum similarity score threshold

    Returns:
        Optional[Dict]: Company information dictionary if found, None if no match or error

    Raises:
        FileNotFoundError: If the data_file doesn't exist
        json.JSONDecodeError: If the data_file contains invalid JSON
    """
    with open(data_file, "r", encoding="utf-8") as f:
        company_tickers = json.load(f)

    if not company_tickers:
        return None

    choices = [company.get("title", "") for company in company_tickers.values()]

    match = process.extractOne(
        query,
        choices,
        scorer=fuzz.WRatio,
        processor=utils.default_process,
        score_cutoff=score_cutoff,
    )
    return list(company_tickers.values())[match[2]] if match else None


class TagSearchEngine:
    def __init__(self, data_file: Path):
        """
        Initialize txtai embeddings and index the tag data

        Args:
            data_file (Path): Path to the JSON file containing fact tags
        """
        # Load tag data
        with open(data_file, "r", encoding="utf-8") as f:
            self.tag_reference = json.load(f)

        # Initialize txtai embeddings
        self.embeddings = Embeddings({"path": "sentence-transformers/all-MiniLM-L6-v2"})

        # Create index data
        self.index_data = [
            (tag_name, description, None)
            for tag_name, description in self.tag_reference.items()
        ]

        # Build the similarity index
        self.embeddings.index(self.index_data)

def get_fact_tags(query: str, data_file: Path, n: int = 5) -> List[Dict]:
    """
    Find the n most relevant fact tags for a given query based on a similarity search with the description

    Args:
        query (str): The query string to search for
        data_file (Path): Path to the JSON file containing fact tags name:description pairs
        n (int): The number of relevant tags to return

    Returns:
        List: A list of dictionaries containing the most relevant fact tags and their scores
    """
    # Initialize search engine if not already created
    if not hasattr(get_fact_tags, "search_engine"):
        get_fact_tags.search_engine = TagSearchEngine(data_file)

    # Perform similarity search
    results = get_fact_tags.search_engine.embeddings.search(query, n)

    # Create results list
    facts = []
    for tag_name, score in results:
        facts.append(
            {
                "tag": tag_name,
                "description": get_fact_tags.search_engine.tag_reference[tag_name],
                "score": score,
            }
        )

    return facts
