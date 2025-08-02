import os
import chromadb
from chromadb.config import Settings
from chromadb.utils.embedding_functions import EmbeddingFunction
from chromadb.utils.embedding_functions.openai_embedding_function import OpenAIEmbeddingFunction
from typing import List, Dict, Any, Optional, Sequence, Mapping, Union
from dotenv import load_dotenv
from typing import cast

# Load environment variables
load_dotenv()

def create_collection(
    collection_name: str = "default_collection",
    persist_directory: str = "chroma_db"
) -> str:
    """
    Creates a new Chroma collection with OpenAI embeddings.
    
    Args:
        collection_name: Name for the collection
        persist_directory: Directory to store the database
        
    Returns:
        str: Success message with collection details
    """
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        raise ValueError("OPENAI_API_KEY environment variable is not set!")
        
    client = chromadb.Client(Settings(
        persist_directory=persist_directory
    ))
    
    embedding_function = cast(
        EmbeddingFunction,
        OpenAIEmbeddingFunction(
            model_name="text-embedding-ada-002",
            api_key=openai_api_key
        )
    )
    
    collection = client.get_or_create_collection(
        name=collection_name,
        embedding_function=embedding_function
    )
    
    return f"Created collection '{collection_name}' in {persist_directory}"

def add_documents(
    collection_name: str,
    documents: List[Dict[str, str]],
    persist_directory: str = "chroma_db"
) -> str:
    """
    Adds documents to a Chroma collection.
    
    Args:
        collection_name: Name of the collection to add documents to
        documents: List of documents, each with "content" and "url" keys
        persist_directory: Directory where the database is stored
        
    Returns:
        str: Success message with number of documents added
    """
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        raise ValueError("OPENAI_API_KEY environment variable is not set!")
        
    client = chromadb.Client(Settings(
        persist_directory=persist_directory
    ))
    
    embedding_function = cast(
        EmbeddingFunction,
        OpenAIEmbeddingFunction(
            model_name="text-embedding-ada-002",
            api_key=openai_api_key
        )
    )
    
    collection = client.get_collection(
        name=collection_name,
        embedding_function=embedding_function
    )
    
    docs: List[str] = []
    metadatas: List[Mapping[str, Union[str, int, float, bool]]] = []
    ids: List[str] = []
    
    for i, doc in enumerate(documents):
        docs.append(doc.get("content", ""))
        metadatas.append({"url": doc.get("url", "")})
        ids.append(f"doc_{i}")
    
    collection.add(
        documents=docs,
        metadatas=metadatas,
        ids=ids
    )
    
    return f"Added {len(documents)} documents to collection '{collection_name}'"

def query_collection(
    collection_name: str,
    query_text: str,
    n_results: int = 3,
    persist_directory: str = "chroma_db"
) -> str:
    """
    Query a Chroma collection using natural language.
    
    Args:
        collection_name: Name of the collection to query
        query_text: The search query
        n_results: Number of results to return
        persist_directory: Directory where the database is stored
        
    Returns:
        str: Query results including document content and metadata
    """
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        raise ValueError("OPENAI_API_KEY environment variable is not set!")
        
    client = chromadb.Client(Settings(
        persist_directory=persist_directory
    ))
    
    embedding_function = cast(
        EmbeddingFunction,
        OpenAIEmbeddingFunction(
            model_name="text-embedding-ada-002",
            api_key=openai_api_key
        )
    )
    
    collection = client.get_collection(
        name=collection_name,
        embedding_function=embedding_function
    )
    
    results = collection.query(
        query_texts=[query_text],
        n_results=n_results
    )
    
    # Format results nicely
    formatted_results = []
    for i, (doc, metadata, distance) in enumerate(zip(
        results['documents'][0],  # type: ignore
        results['metadatas'][0],  # type: ignore
        results['distances'][0]   # type: ignore
    )):
        formatted_results.append(
            f"Result {i+1}:\n"
            f"Content: {doc}\n"
            f"URL: {metadata['url']}\n"
            f"Relevance Score: {1 - float(distance):.2f}\n"
        )
    
    return "\n".join(formatted_results)
