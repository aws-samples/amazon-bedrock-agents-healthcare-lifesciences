from typing import TypedDict, Annotated, Sequence, Literal
from langgraph.graph import StateGraph, START, END, add_messages
import operator
from langchain_core.messages import AnyMessage, SystemMessage, HumanMessage, ToolMessage, AIMessage
import logging
from file_data_extraction_agent import extract as file_extract
from xml_extraction_agent import extract as xml_extract
from csv_extraction_agent import extract as csv_extract
from llm_enrichment_and_extraction_agent import enrich_and_extract
import os
import mimetypes
import json
from refine_matching_targets_agent import match
import csv
from save_mapping_report import generate_html_with_xml_and_mappings
import pandas as pd
import io

from ontology.OMOP_ontology import OMOPOntology

# Configure logging
logger = logging.getLogger(__name__)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s')
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)


ontology = OMOPOntology(graph_id="g-x5qxts1926")

class GraphConfig(TypedDict):
    model_name: Literal["anthropic-claude-3.5-sonnet"]

class WorkflowState(TypedDict):
   messages: Annotated[list[AnyMessage], operator.add]
   document : str
   extracted_entities : str
   mapping : str
   error : str
   filepath : str

def file_extraction_agent(state: WorkflowState):
    logger.info("Executing file-based extraction")
    try:
        doc_location = state['document']
        extracted_entities = file_extract(doc_location)  
        return {
            "messages": state['messages'] + [AIMessage(content=f"Extracted from file: {doc_location}")],
            "extracted_entities": extracted_entities
        }
    except Exception as e:
        logger.error(f"File extraction error: {str(e)}", exc_info=True)
        return {"error": str(e)}

def xml_extraction_agent(state: WorkflowState):
    logger.info("Executing XML-based extraction")
    try:
        doc = state['document']
        extracted_entities = xml_extract(doc) 
        return {
            "messages": state['messages'] + [AIMessage(content=f"Extracted from XML: {doc}")],
            "extracted_entities": extracted_entities
        }
    except Exception as e:
        logger.error(f"XML extraction error: {str(e)}", exc_info=True)
        return {"error": str(e)}
    
def csv_extraction_agent(state: WorkflowState):
    logger.info("Executing CSV-based extraction")
    try:
        doc = state['document']
        extracted_entities = csv_extract(doc)
        return {
            "messages": state['messages'] + [AIMessage(content=f"Extracted from CSV: {doc}")],
            "extracted_entities": extracted_entities
        }
    except Exception as e:
        logger.error(f"CSV extraction error: {str(e)}", exc_info=True)
        return {"error": str(e)}
    

def inline_source_data_extraction(state: WorkflowState):
    logger.info("Executing LLM-based extraction")
    try:
        doc = state['document']
        import io
        import pandas as pd
        
        # Use StringIO to handle the CSV string
        csv_buffer = io.StringIO(doc)
        
        # Read CSV into a pandas DataFrame
        df = pd.read_csv(csv_buffer)
        
        # Initialize the entities list
        entities_map = {}
        
        # Iterate through each row and create entity structure
        for index, row in df.iterrows():
            entity = {
                "description": f"{row['Label']} is part of {row['Table Description']}",
                "values": {}  # Empty dictionary for values
            }
            entities_map[row['Variable Name']] = entity
        
        return {
            "messages": state['messages'] + [AIMessage(content=f"Extracted from file: {doc}")],
            "extracted_entities": entities_map
        }
    except Exception as e:
        logger.error(f"LLM extraction error: {str(e)}", exc_info=True)
        return {"error": str(e)}


# def text_extraction_agent(state: WorkflowState):
#     logger.info("Executing text-based extraction")
#     try:
#         doc_location = state['document']
#         extracted_entities = text_extraction(doc_location)  # Text extraction function
#         return {
#             "messages": state['messages'] + [AIMessage(content=f"Extracted from text: {doc_location}")],
#             "extracted_entities": extracted_entities
#         }
#     except Exception as e:
#         logger.error(f"Text extraction error: {str(e)}", exc_info=True)
#         return {"error": str(e)}

def document_router(state: WorkflowState):
    logger.info("Routing document to appropriate extraction agent")
    doc = state['document']
    extractor = None
    # if os.path.exists(doc): 
    #     mime_type, _ = mimetypes.guess_type(doc)
    #     extractor = "File-Extraction"
    # elif doc.startswith('<?xml') or doc.startswith('<'):
    #     extractor = "XML-Extraction"
    # else:
    #     extractor = "CSV-Extraction"

    if os.path.exists(doc): 
        mime_type, _ = mimetypes.guess_type(doc)
        extractor = "File-Extraction"
    else :
        extractor = "LLM-Extraction"
    
    return { "extractor" : extractor }


# def meta_data_extraction(state: WorkflowState):
#     logger.info("Starting metadata extraction")
#     try:
#         doc_location = state['document']
#         extracted_entities = extraction()
#         logger.info("Metadata extraction completed successfully")

#         new_message = AIMessage(content=f"Extracted Entities from the dcoument : {doc_location}")
        
#         # Update the state with the output data source object (JSON object here)
#         return {
#             "messages": state['messages'] + [new_message],
#             "extracted_entities": extracted_entities
#         }
#     except Exception as e:
#         logger.error(f"Error in metadata extraction: {str(e)}", exc_info=True)
#         return {
#             "error" : e
#         }

def target_ontology_retrieval(state: WorkflowState):
    logger.info("Starting target ontology retrieval")
    try:
        ontology_summary = ontology.connect()
        
        logger.info(f"Target ontology {ontology_summary}")

        result = {
            "messages": state['messages'] + [AIMessage(content=f"Target Ontology is : {ontology_summary}")]
        }

        return result
    except Exception as e:
        logger.error(f"Error in target ontology retrieval: {str(e)}", exc_info=True)
        raise e

def retrive_similar_nodes(state: WorkflowState):
    logger.info("Starting target ontology retrieval")
    
    results = []
    for entity_key in state["extracted_entities"].keys():
        entity_description = state["extracted_entities"][entity_key]["description"]
        #entity_value = state["extracted_entities"][entity_key]["values"]

        similar_nodes = ontology.find_similar_fields(f"{entity_key}:{entity_description}")
        results.append({
            "source_field": entity_key,
            "source_field_description": entity_description,
            "possible_targets": similar_nodes
        })
    
    logger.info(results)
    return {
        "messages": state["messages"],
        "extracted_entities": results
    }

def refine_targets(state: WorkflowState):
    logger.info("Starting target ontology retrieval")
    try:
        possible_targets = json.dumps(state["extracted_entities"])
        
        logger.info(possible_targets)
        
        entities, reasoning = match(possible_targets)

        result = {
            "messages": [HumanMessage(content=reasoning)],
            "mapping": entities
        }
        
        return result
    except Exception as e:
        logger.error(f"Error in target ontology retrieval: {str(e)}", exc_info=True)
        raise e

def save_mapping(state: WorkflowState):
    
    try:
        entities = state["mapping"]
        headers = entities[0].keys()

        logger.info(f"Entities to save: {entities}")
        logger.info(f"Saving mapping with headers: {headers}")

        file_name = f"./results/{state["filepath"]}"
        
        csv_file = f"{os.path.abspath(file_name)}.csv"
        report_file = f"{os.path.abspath(file_name)}.html"

        logger.info("Saving to CSV")
        with open(csv_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=headers)
            writer.writeheader()
            writer.writerows(entities)
        
        logger.info("Generating Mapping Report.")
        generate_html_with_xml_and_mappings(state["document"], entities, report_file)
        
        result = {
            "messages": [
                AIMessage(content=f"CSV Mapping file saved at: {csv_file}"),
                AIMessage(content=f"Mapping report generated and saved at: {report_file}")
            ]
        }

        return result
    except Exception as e:
        logger.error(f"Error in saving to CSV: {str(e)}", exc_info=True)
        raise e

# Log graph building process
logger.info("Initializing workflow graph")
graph_builder = StateGraph(WorkflowState, config_schema=GraphConfig)

logger.info("Adding nodes to the graph")

#graph_builder.add_node("Document-Router", document_router)
#graph_builder.add_node("File-Extraction", file_extraction_agent)
#graph_builder.add_node("CSV-Extraction", csv_extraction_agent)
#graph_builder.add_node("XML-Extraction", xml_extraction_agent)
#graph_builder.add_node("LLM-Extraction", llm_extraction_agent)
graph_builder.add_node("Source-Data-Extraction", inline_source_data_extraction)
graph_builder.add_node("Target-DS-Retrieval", target_ontology_retrieval)
graph_builder.add_node("Identify-Mappings", retrive_similar_nodes)
graph_builder.add_node("Refine-targets", refine_targets)
graph_builder.add_node("Save-Mapping", save_mapping)

logger.info("Adding edges to the graph")

graph_builder.add_edge(START, "Source-Data-Extraction")

graph_builder.add_edge("Source-Data-Extraction", "Target-DS-Retrieval")
graph_builder.add_edge("Target-DS-Retrieval", "Identify-Mappings")
graph_builder.add_edge("Identify-Mappings", "Refine-targets")
graph_builder.add_edge("Refine-targets", "Save-Mapping")
graph_builder.add_edge("Save-Mapping", END)

logger.info("Compiling the graph")
graph = graph_builder.compile(interrupt_after=[])
logger.info("Graph compilation completed")
