import logging
from typing import List, Optional, Dict, Any
import os
from dotenv import load_dotenv
import chromadb
from sentence_transformers import SentenceTransformer

load_dotenv()

class EmbeddingService:
    """Service for managing document embeddings"""
    
    def __init__(
        self, 
        embedding_model: Optional[str] = None, 
        vector_db_path: Optional[str] = None
    ):
        """
        Initialize embedding service
        
        Args:
            embedding_model (str): Sentence Transformer model name
            vector_db_path (str): Path to persistent vector storage
        """
        self.embedding_model = embedding_model or os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
        self.vector_db_path = vector_db_path or os.getenv("VECTOR_DB_PATH", "./vectordb")
        
        self.logger = logging.getLogger(__name__)
        try:
            self.model = SentenceTransformer(self.embedding_model)
            self.chroma_client = chromadb.PersistentClient(path=self.vector_db_path)
            self.collection = self.chroma_client.get_or_create_collection(
                name="document_embeddings",
                metadata={"hnsw:space": "cosine"}
            )
            self.logger.info(f"Initialized embedding service with model: {self.embedding_model}")
        except Exception as e:
            self.logger.error(f"Initialization failed: {e}")
            raise

    def create_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for text chunks
        
        Args:
            texts (List[str]): List of text chunks to embed
        
        Returns:
            List[List[float]]: List of embedding vectors
        
        Raises:
            RuntimeError: If embedding generation fails
        """
        try:
            return self.model.encode(texts).tolist()
        except Exception as e:
            self.logger.error(f"Embedding generation failed: {e}")
            raise RuntimeError("Embedding creation failed") from e

    def store_embeddings(
        self, 
        texts: List[str], 
        embeddings: Optional[List[List[float]]] = None,
        metadatas: Optional[List[Dict]] = None, 
        unique_id: Optional[str] = None
    ):
        """
        Store text embeddings in ChromaDB
        
        Args:
            texts (List[str]): Text chunks to store
            embeddings (Optional[List[List[float]]]): Precomputed embeddings
            metadatas (Optional[List[Dict]]): Metadata for each chunk
            unique_id (Optional[str]): Unique document identifier
        
        Raises:
            RuntimeError: If storage operation fails
        """
        try:
            embeddings = embeddings or self.create_embeddings(texts)
            metadatas = metadatas or [{} for _ in texts]
            ids = [f"{unique_id}_chunk_{i}" for i in range(len(texts))] if unique_id else [f"chunk_{i}" for i in range(len(texts))]
            
            self.collection.add(
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas,
                ids=ids
            )
            self.logger.info(f"Stored {len(texts)} chunks from {unique_id or 'unknown'}")
        except Exception as e:
            self.logger.error(f"Storage failed: {e}")
            raise RuntimeError("Embedding storage failed") from e

    def search_embeddings(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Perform semantic search on stored embeddings
        
        Args:
            query (str): Search query text
            top_k (int): Number of results to return
        
        Returns:
            List[Dict[str, Any]]: Search results with metadata
        
        Raises:
            RuntimeError: If search operation fails
        """
        try:
            query_embedding = self.create_embeddings([query])[0]
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k
            )
            return [{
                "text": doc,
                "distance": dist,
                "metadata": meta
            } for doc, dist, meta in zip(results['documents'][0], results['distances'][0], results['metadatas'][0])]
        except Exception as e:
            self.logger.error(f"Search failed: {e}")
            raise RuntimeError("Embedding search failed") from e