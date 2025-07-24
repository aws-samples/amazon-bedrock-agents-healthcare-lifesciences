"""
Tests for the SemanticSearch class
"""

import os
import unittest
from unittest.mock import patch, MagicMock, mock_open
import numpy as np

from bedrock_ez_search import SemanticSearch


class TestSemanticSearch(unittest.TestCase):
    """Test cases for the SemanticSearch class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_embedding = np.array([0.1, 0.2, 0.3, 0.4])
        
    @patch('boto3.Session')
    def test_initialization(self, mock_session):
        """Test initialization of SemanticSearch"""
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client
        
        search = SemanticSearch(
            model_id="test-model",
            region_name="us-west-2",
            profile_name="test-profile"
        )
        
        self.assertEqual(search.model_id, "test-model")
        mock_session.assert_called_once_with(
            region_name="us-west-2",
            profile_name="test-profile"
        )
        mock_session.return_value.client.assert_called_once_with("bedrock-runtime")
    
    @patch('boto3.Session')
    def test_get_embedding(self, mock_session):
        """Test getting embeddings from Bedrock"""
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client
        
        # Mock the response from bedrock-runtime
        mock_response = {
            "body": MagicMock()
        }
        mock_response["body"].read.return_value = '{"embedding": [0.1, 0.2, 0.3, 0.4]}'
        mock_client.invoke_model.return_value = mock_response
        
        search = SemanticSearch()
        embedding = search._get_embedding("test text")
        
        np.testing.assert_array_equal(embedding, np.array([0.1, 0.2, 0.3, 0.4]))
        mock_client.invoke_model.assert_called_once()
    
    @patch('boto3.Session')
    def test_index_with_cache(self, mock_session):
        """Test indexing with cache functionality"""
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client
        
        # Mock the embedding responses
        mock_response = {
            "body": MagicMock()
        }
        mock_response["body"].read.return_value = '{"embedding": [0.1, 0.2, 0.3, 0.4]}'
        mock_client.invoke_model.return_value = mock_response
        
        search = SemanticSearch()
        
        # Mock the _get_embedding method to return controlled values
        with patch.object(search, '_get_embedding') as mock_get_embedding:
            # For document embeddings
            mock_get_embedding.side_effect = [
                np.array([0.9, 0.1, 0.1, 0.1]),  # doc 1
                np.array([0.1, 0.9, 0.1, 0.1]),  # doc 2
            ]
            
            # Mock np.save to verify it's called with correct arguments
            with patch('numpy.save') as mock_save:
                # Index the documents with cache path
                search.index(
                    ["Document 1", "Document 2"],
                    cache_path="test_embeddings.npy"
                )
                
                # Verify np.save was called with the correct arguments
                mock_save.assert_called_once()
                args, _ = mock_save.call_args
                self.assertEqual(args[0], "test_embeddings.npy")
                np.testing.assert_array_equal(
                    args[1], 
                    np.vstack([
                        np.array([0.9, 0.1, 0.1, 0.1]),
                        np.array([0.1, 0.9, 0.1, 0.1])
                    ])
                )
    
    @patch('boto3.Session')
    def test_search(self, mock_session):
        """Test search functionality"""
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client
        
        # Mock the embedding responses
        mock_response = {
            "body": MagicMock()
        }
        mock_response["body"].read.return_value = '{"embedding": [0.1, 0.2, 0.3, 0.4]}'
        mock_client.invoke_model.return_value = mock_response
        
        search = SemanticSearch()
        
        # Mock the _get_embedding method to return controlled values
        with patch.object(search, '_get_embedding') as mock_get_embedding:
            # For document embeddings
            mock_get_embedding.side_effect = [
                np.array([0.9, 0.1, 0.1, 0.1]),  # doc 1 - less similar
                np.array([0.1, 0.9, 0.1, 0.1]),  # doc 2 - most similar
                np.array([0.5, 0.5, 0.1, 0.1]),  # doc 3 - medium similar
            ]
            
            # Index the documents
            search.index([
                "Document 1",
                "Document 2",
                "Document 3"
            ])
            
            # Reset the side_effect for the query embedding
            mock_get_embedding.side_effect = None
            mock_get_embedding.return_value = np.array([0.1, 0.9, 0.1, 0.1])  # Same as doc 2
            
            # Perform search
            results = search.search("test query", top_k=3)
            
            # Check results
            self.assertEqual(len(results), 3)
            self.assertEqual(results[0]["index"], 1)  # Doc 2 should be first
            self.assertEqual(results[0]["document"], "Document 2")
            self.assertGreater(results[0]["score"], results[1]["score"])  # First result should have higher score
    
    @patch('boto3.Session')
    def test_index_without_cache(self, mock_session):
        """Test indexing without cache functionality"""
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client
        
        # Mock the embedding responses
        mock_response = {
            "body": MagicMock()
        }
        mock_response["body"].read.return_value = '{"embedding": [0.1, 0.2, 0.3, 0.4]}'
        mock_client.invoke_model.return_value = mock_response
        
        search = SemanticSearch()
        
        # Mock the _get_embedding method to return controlled values
        with patch.object(search, '_get_embedding') as mock_get_embedding:
            # For document embeddings
            mock_get_embedding.side_effect = [
                np.array([0.9, 0.1, 0.1, 0.1]),  # doc 1
                np.array([0.1, 0.9, 0.1, 0.1]),  # doc 2
            ]
            
            # Mock np.save to verify it's not called when cache_path is None
            with patch('numpy.save') as mock_save:
                # Index the documents without cache path
                search.index(["Document 1", "Document 2"])
                
                # Verify np.save was not called
                mock_save.assert_not_called()
    
    @patch('boto3.Session')
    def test_index_with_embeddings_file(self, mock_session):
        """Test indexing with pre-computed embeddings from file"""
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client
        
        search = SemanticSearch()
        
        # Create mock embeddings data
        mock_embeddings = np.array([
            [0.1, 0.2, 0.3, 0.4],
            [0.5, 0.6, 0.7, 0.8]
        ])
        
        # Mock np.load to return our mock embeddings
        with patch('numpy.load', return_value=mock_embeddings) as mock_load:
            # Mock _get_batch_embeddings to verify it's not called
            with patch.object(search, '_get_batch_embeddings') as mock_get_batch:
                # Index the documents with embeddings_file
                search.index(
                    ["Document 1", "Document 2"],
                    embeddings_file="pre_computed_embeddings.npy"
                )
                
                # Verify np.load was called with the correct path
                mock_load.assert_called_once_with("pre_computed_embeddings.npy")
                
                # Verify _get_batch_embeddings was not called
                mock_get_batch.assert_not_called()
                
                # Verify the embeddings were properly set
                np.testing.assert_array_equal(search._embeddings, mock_embeddings)
                
                # Verify the documents were properly set
                self.assertEqual(search._documents, ["Document 1", "Document 2"])
    
    @patch('boto3.Session')
    def test_index_with_embeddings_file_and_cache(self, mock_session):
        """Test loading embeddings from file and saving to cache"""
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client
        
        search = SemanticSearch()
        
        # Create mock embeddings data
        mock_embeddings = np.array([
            [0.1, 0.2, 0.3, 0.4],
            [0.5, 0.6, 0.7, 0.8]
        ])
        
        # Mock np.load to return our mock embeddings
        with patch('numpy.load', return_value=mock_embeddings) as mock_load:
            # Mock np.save to verify it's called with correct arguments
            with patch('numpy.save') as mock_save:
                # Mock _get_batch_embeddings to verify it's not called
                with patch.object(search, '_get_batch_embeddings') as mock_get_batch:
                    # Index the documents with both embeddings_file and cache_path
                    search.index(
                        ["Document 1", "Document 2"],
                        cache_path="cached_embeddings.npy",
                        embeddings_file="pre_computed_embeddings.npy"
                    )
                    
                    # Verify np.load was called with the correct path
                    mock_load.assert_called_once_with("pre_computed_embeddings.npy")
                    
                    # Verify _get_batch_embeddings was not called
                    mock_get_batch.assert_not_called()
                    
                    # Verify np.save was called with the correct arguments
                    mock_save.assert_called_once()
                    args, _ = mock_save.call_args
                    self.assertEqual(args[0], "cached_embeddings.npy")
                    np.testing.assert_array_equal(args[1], mock_embeddings)


if __name__ == '__main__':
    unittest.main()
    @patch('boto3.Session')
    def test_index_with_mismatched_embeddings(self, mock_session):
        """Test indexing with embeddings file that doesn't match document count"""
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client
        
        search = SemanticSearch()
        
        # Create mock embeddings data with 3 embeddings
        mock_embeddings = np.array([
            [0.1, 0.2, 0.3, 0.4],
            [0.5, 0.6, 0.7, 0.8],
            [0.9, 0.8, 0.7, 0.6]
        ])
        
        # Mock np.load to return our mock embeddings
        with patch('numpy.load', return_value=mock_embeddings) as mock_load:
            # Try to index only 2 documents with embeddings for 3 documents
            with self.assertRaises(ValueError) as context:
                search.index(
                    ["Document 1", "Document 2"],
                    embeddings_file="mismatched_embeddings.npy"
                )
            
            # Verify the error message
            self.assertIn("Number of embeddings in file (3) doesn't match number of documents (2)", 
                         str(context.exception))
