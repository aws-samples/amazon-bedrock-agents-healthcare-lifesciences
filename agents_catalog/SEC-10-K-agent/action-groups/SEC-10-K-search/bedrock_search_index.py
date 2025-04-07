import boto3
import botocore
from json import dumps, loads
import logging
from numpy import ndarray
from os import environ
from pathlib import Path
import pickle
from sentence_transformers import util
from torch import tensor, Tensor, load, save, stack
from tqdm import tqdm
from typing import List, Dict
import time

valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
log_level = environ.get("LOG_LEVEL", "INFO").strip().upper()
if log_level not in valid_log_levels:
    log_level = "INFO"
logging.basicConfig(
    format="[%(asctime)s] p%(process)s {%(filename)s:%(lineno)d} %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)
logger.setLevel(log_level)


class BedrockSearchIndex:
    def __init__(
        self,
        index: List[str] = None,
        index_path: Path = None,
        model_id: str = "amazon.titan-embed-text-v2:0",
        boto_session: boto3.session = boto3.Session(),
    ):
        self.model_id: str = model_id
        self.boto_session: boto3.session = boto_session
        self.bedrock_runtime_client: boto3.client = self.boto_session.client(
            service_name="bedrock-runtime"
        )
        self.index: List = index
        self.index_path: Path = index_path
        self._embeddings: ndarray | None = None

    @property
    def embeddings(self):
        if self._embeddings is None:
            logger.debug("Processing index")
            try:
                if self.index_path is not None:
                    logger.info("Loading index from disk")
                    with open(self.index_path, "rb") as f:
                        self.index, self._embeddings = pickle.load(f)
                elif self.index is not None:
                    self._embeddings = self._list_to_embeddings(self.index)
                    index_cache = (self.index, self._embeddings)
                    # save(self._embeddings, "index.pt")
                    with open("index.pkl", "wb") as f:
                        pickle.dump(index_cache, f)
                else:
                    raise ValueError("No index provided")
            except Exception as e:
                logger.error(f"Error calculating embeddings: {str(e)}")
                raise
            logger.info(f"Index embedding shape is {tuple(self._embeddings.size())}")
        return self._embeddings

    def search(
        self,
        query: str,
        k: int = 5,
    ) -> List[Dict[str, str]]:
        """
        Search a list of strings for the k most similar strings to a query
        """
        logger.info("Searching")
        if not hasattr(self, "_query_cache"):
            self._query_cache: Dict[
                str, Tensor
            ] = {}  # Add a cache for query embeddings
        if query not in self._query_cache:
            self._query_cache[query] = self._get_bedrock_embedding(query)
        query_embedding = self._query_cache[query]
        try:
            search_results = util.semantic_search(query_embedding, self.embeddings)
            if not search_results or not search_results[0]:
                logger.warning("No search results found")
                return []
            return [
                {
                    "index_id": result["corpus_id"],
                    "score": round(result["score"], 3),
                    "text": self.index[result["corpus_id"]],
                }
                for result in search_results[0][:k]
            ]
        except Exception as e:
            logger.error(f"Error during semantic search: {str(e)}")
            return []

    def _get_bedrock_embedding(
        self,
        text: str,
        max_retries: int = 3,
        delay: float = 1.0,
    ) -> Tensor:
        """
        Use Amazon Bedrock to generate embeddings for a test string
        """
        body = dumps({"inputText": text})
        for attempt in range(max_retries):
            try:
                response = self.bedrock_runtime_client.invoke_model(
                    body=body, modelId=self.model_id
                )
                response_body = loads(response.get("body").read())
                embedding = response_body.get("embedding")
                if embedding is None:
                    raise ValueError("Embedding not found in the response")
                return tensor(embedding)
            except botocore.exceptions.ClientError as e:
                if attempt < max_retries - 1:
                    logger.warning(
                        f"Retrying after {delay} seconds due to AWS SDK error: {str(e)}"
                    )
                    time.sleep(delay)
                else:
                    logger.error(
                        f"AWS SDK error when getting Bedrock embedding: {str(e)}"
                    )
                    raise
            except Exception as e:
                logger.error(
                    f"Unexpected error when getting Bedrock embedding: {str(e)}"
                )
                raise

    def _list_to_embeddings(
        self,
        docs: List,
    ) -> Tensor:
        """
        Use Amazon Bedrock to generate embeddings for a list of strings
        """
        output = []
        for doc in tqdm(docs, desc="Generating embedding"):
            try:
                embedding = self._get_bedrock_embedding(doc)
                output.append(embedding)
            except Exception as e:
                logger.error(f"Error generating embedding for document: {str(e)}")
        return stack(output)


if __name__ == "__main__":
    session = boto3.Session(region_name="us-west-2")
    my_dict = {
        "apple": "A sweet, edible fruit with red, green, or yellow skin.",
        "banana": "A tropical fruit with a yellow peel and soft, sweet flesh.",
        "car": "A four-wheeled vehicle used for transportation.",
        "bus": "A large vehicle that carries many passengers.",
        "orange": "A citrus fruit with a tough reddish-orange peel and juicy pulp.",
    }

    print("Index:")
    for i in my_dict.items():
        print(i)
    query = "transport vehicle"
    print(f"\nQuery:\n{query}")
    k = 5

    # Test list search
    print("\nTesting list search")
    index = BedrockSearchIndex(index=list(my_dict.values()), boto_session=session)

    results = index.search(query, k)
    assert len(results) == k

    print("\nResults:")
    for result in results:
        print(result)

    # Test load index from disk
    print("\nTesting load index from disk")
    index = BedrockSearchIndex(index_path="index.pkl", boto_session=session)

    results = index.search(query, k)
    assert len(results) == k

    print("\nResults:")
    for result in results:
        print(result)
