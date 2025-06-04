"""
Core semantic search functionality using Amazon Bedrock embeddings
"""

import json
from typing import Dict, List, Tuple, Union, Optional, Any

import boto3
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity


class SemanticSearch:
    """
    A simple semantic search engine using Amazon Bedrock embeddings.
    
    This class allows you to index a list of strings and perform semantic
    searches against them using Amazon Bedrock embedding models.
    """
    
    def __init__(
        self, 
        model_id: str = "amazon.titan-embed-text-v1",
        region_name: Optional[str] = None,
        profile_name: Optional[str] = None,
    ):
        """
        Initialize the semantic search engine.
        
        Args:
            model_id: The Amazon Bedrock model ID to use for embeddings
            region_name: AWS region name (uses boto3 default if None)
            profile_name: AWS profile name (uses boto3 default if None)
        """
        session_kwargs = {}
        if region_name:
            session_kwargs["region_name"] = region_name
        if profile_name:
            session_kwargs["profile_name"] = profile_name
            
        session = boto3.Session(**session_kwargs)
        self.bedrock_runtime = session.client("bedrock-runtime")
        self.model_id = model_id
        
        self._documents = []
        self._embeddings = None
        
    def _get_embedding(self, text: str) -> np.ndarray:
        """
        Get embedding for a single text using Amazon Bedrock.
        
        Args:
            text: The text to embed
            
        Returns:
            A numpy array containing the embedding vector
        """
        request_body = {
            "inputText": text
        }
        
        response = self.bedrock_runtime.invoke_model(
            modelId=self.model_id,
            body=json.dumps(request_body)
        )
        
        response_body = json.loads(response.get("body").read())
        embedding = np.array(response_body.get("embedding"))
        
        return embedding
    
    def _get_batch_embeddings(self, texts: List[str]) -> np.ndarray:
        """
        Get embeddings for a batch of texts.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            A numpy array containing the embedding vectors
        """
        # For simplicity, we'll process one at a time
        # In a production system, you might want to batch these calls
        embeddings = []
        for text in texts:
            embedding = self._get_embedding(text)
            embeddings.append(embedding)
        
        return np.vstack(embeddings)
    
    def index(self, documents: List[str], cache_path: Optional[str] = None, embeddings_file: Optional[str] = None) -> None:
        """
        Index a list of documents for semantic search.
        
        Args:
            documents: List of text documents to index
            cache_path: Optional path to save embeddings as a .npy file
                        If provided, the embeddings will be saved to this location
            embeddings_file: Optional path to load pre-computed embeddings from a .npy file
                            If provided, embeddings will be loaded from this file instead
                            of computing them via the Bedrock API
                            
        Raises:
            ValueError: If the number of embeddings loaded from file doesn't match
                       the number of documents
        """
        self._documents = documents
        
        # Load embeddings from file if embeddings_file is provided
        if embeddings_file is not None:
            loaded_embeddings = np.load(embeddings_file)
            
            # Validate that the number of embeddings matches the number of documents
            if len(loaded_embeddings) != len(documents):
                raise ValueError(
                    f"Number of embeddings in file ({len(loaded_embeddings)}) "
                    f"doesn't match number of documents ({len(documents)})"
                )
                
            self._embeddings = loaded_embeddings
        else:
            # Otherwise compute embeddings via the Bedrock API
            self._embeddings = self._get_batch_embeddings(documents)
        
        # Save embeddings to file if cache_path is provided
        if cache_path is not None:
            np.save(cache_path, self._embeddings)
    
    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Search the indexed documents for semantic matches to the query.
        
        Args:
            query: The search query
            top_k: Number of top results to return
            
        Returns:
            List of dictionaries containing document text and similarity score
        """
        if self._embeddings is None or len(self._documents) == 0:
            raise ValueError("No documents have been indexed. Call index() first.")
        
        # Get query embedding
        query_embedding = self._get_embedding(query)
        
        # Calculate cosine similarities
        similarities = cosine_similarity(
            query_embedding.reshape(1, -1), 
            self._embeddings
        )[0]
        
        # Get top-k indices
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        # Prepare results
        results = []
        for idx in top_indices:
            results.append({
                "document": self._documents[idx],
                "score": float(similarities[idx]),
                "index": int(idx)
            })
        
        return results
