"""
FAQ Retrieval Service
Uses Sentence-Transformers and ChromaDB for semantic FAQ retrieval.
Persistent vector store — survives server restarts.
"""

import os
import logging
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# Lazy imports
_model = None
_chroma_client = None

# Persistent storage path
CHROMA_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "chroma_db")


def _get_embedding_model():
    """Lazy load the sentence transformer model."""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer('all-MiniLM-L6-v2')
        logger.info("Loaded embedding model: all-MiniLM-L6-v2")
    return _model


def _get_chroma_client():
    """Lazy load ChromaDB persistent client."""
    global _chroma_client
    if _chroma_client is None:
        import chromadb
        os.makedirs(CHROMA_DB_PATH, exist_ok=True)
        _chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
        logger.info(f"ChromaDB initialized at: {CHROMA_DB_PATH}")
    return _chroma_client


class SentenceTransformerEmbedder:
    """Wraps SentenceTransformer for ChromaDB's embedding function interface."""
    
    def __call__(self, input: List[str]) -> List[List[float]]:
        model = _get_embedding_model()
        embeddings = model.encode(input, normalize_embeddings=True)
        return embeddings.tolist()


class FAQRetrievalService:
    """FAQ retrieval service using ChromaDB + semantic similarity."""
    
    def __init__(self):
        """Initialize the FAQ retrieval service."""
        self._loaded_campaigns: set = set()
        self._embedder = SentenceTransformerEmbedder()
    
    def _get_collection(self, campaign_id: int):
        """Get or create a ChromaDB collection for a campaign."""
        client = _get_chroma_client()
        collection_name = f"campaign_{campaign_id}"
        return client.get_or_create_collection(
            name=collection_name,
            embedding_function=self._embedder,
            metadata={"hnsw:space": "cosine"}  # cosine similarity
        )
    
    def load_faqs(self, campaign_id: int, faqs: List[Dict]) -> bool:
        """
        Load and index FAQs for a campaign into ChromaDB.
        
        Args:
            campaign_id: Campaign ID
            faqs: List of FAQ dictionaries with 'question' and 'answer' keys
            
        Returns:
            True if successful, False otherwise
        """
        if not faqs:
            logger.warning(f"No FAQs provided for campaign {campaign_id}")
            return False
        
        try:
            collection = self._get_collection(campaign_id)
            
            # Clear existing data for this campaign (fresh load)
            existing = collection.count()
            if existing > 0:
                # Get all IDs and delete them
                all_ids = collection.get()["ids"]
                if all_ids:
                    collection.delete(ids=all_ids)
                logger.info(f"Cleared {existing} existing FAQs for campaign {campaign_id}")
            
            # Prepare documents for ChromaDB
            documents = []
            metadatas = []
            ids = []
            
            for i, faq in enumerate(faqs):
                question = faq.get("question", "")
                answer = faq.get("answer", "")
                keywords = faq.get("keywords", [])
                
                # Document = question + keywords (for embedding)
                doc_text = question
                if keywords:
                    doc_text += " " + " ".join(keywords)
                
                documents.append(doc_text)
                metadatas.append({
                    "question": question,
                    "answer": answer,
                    "keywords": " ".join(keywords) if keywords else "",
                    "faq_index": i
                })
                ids.append(f"faq_{campaign_id}_{i}")
            
            # Add to ChromaDB (handles embedding automatically)
            collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            
            self._loaded_campaigns.add(campaign_id)
            logger.info(f"Loaded {len(faqs)} FAQs for campaign {campaign_id} into ChromaDB")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load FAQs for campaign {campaign_id}: {str(e)}")
            return False
    
    def retrieve(
        self,
        campaign_id: int,
        query: str,
        top_k: int = 3,
        threshold: float = 0.5
    ) -> List[Tuple[Dict, float]]:
        """
        Retrieve relevant FAQs for a query using ChromaDB.
        
        Args:
            campaign_id: Campaign ID to search in
            query: User's query
            top_k: Maximum number of results
            threshold: Minimum similarity score (0-1)
            
        Returns:
            List of (FAQ dict, similarity score) tuples
        """
        if campaign_id not in self._loaded_campaigns:
            logger.warning(f"No FAQs loaded for campaign {campaign_id}")
            return []
        
        try:
            collection = self._get_collection(campaign_id)
            
            # Query ChromaDB
            results = collection.query(
                query_texts=[query],
                n_results=min(top_k, collection.count()),
                include=["metadatas", "distances"]
            )
            
            # ChromaDB returns distances (lower = more similar for cosine)
            # Convert to similarity: similarity = 1 - distance
            matched = []
            if results["metadatas"] and results["distances"]:
                for metadata, distance in zip(results["metadatas"][0], results["distances"][0]):
                    similarity = 1.0 - distance  # cosine distance → similarity
                    if similarity >= threshold:
                        faq = {
                            "question": metadata.get("question", ""),
                            "answer": metadata.get("answer", ""),
                            "keywords": metadata.get("keywords", "").split() if metadata.get("keywords") else []
                        }
                        matched.append((faq, float(similarity)))
            
            logger.info(f"ChromaDB retrieved {len(matched)} FAQs for query: '{query[:50]}...'")
            return matched
            
        except Exception as e:
            logger.error(f"FAQ retrieval failed: {str(e)}")
            return []
    
    def format_faq_context(self, faqs: List[Tuple[Dict, float]]) -> str:
        """
        Format retrieved FAQs as context for the LLM.
        
        Args:
            faqs: List of (FAQ dict, score) tuples
            
        Returns:
            Formatted context string
        """
        if not faqs:
            return ""
        
        context_parts = ["Here are some relevant FAQ answers that may help:"]
        
        for i, (faq, score) in enumerate(faqs, 1):
            question = faq.get("question", "")
            answer = faq.get("answer", "")
            context_parts.append(f"\nQ{i}: {question}\nA{i}: {answer}")
        
        return "\n".join(context_parts)
    
    def remove_campaign(self, campaign_id: int):
        """Remove indexed FAQs for a campaign."""
        try:
            client = _get_chroma_client()
            collection_name = f"campaign_{campaign_id}"
            client.delete_collection(collection_name)
            self._loaded_campaigns.discard(campaign_id)
            logger.info(f"Removed ChromaDB collection for campaign {campaign_id}")
        except Exception as e:
            logger.warning(f"Could not remove collection for campaign {campaign_id}: {e}")
    
    def is_campaign_loaded(self, campaign_id: int) -> bool:
        """Check if a campaign's FAQs are loaded."""
        return campaign_id in self._loaded_campaigns


# Singleton instance
faq_service = FAQRetrievalService()
