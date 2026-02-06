"""
FAQ Retrieval Service
Uses Sentence-Transformers and FAISS for semantic FAQ retrieval.
"""

import logging
from typing import List, Dict, Optional, Tuple
import numpy as np

logger = logging.getLogger(__name__)

# Lazy imports for heavy dependencies
_model = None
_faiss = None


def _get_embedding_model():
    """Lazy load the sentence transformer model."""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer('all-MiniLM-L6-v2')
        logger.info("Loaded embedding model: all-MiniLM-L6-v2")
    return _model


def _get_faiss():
    """Lazy load FAISS."""
    global _faiss
    if _faiss is None:
        import faiss
        _faiss = faiss
    return _faiss


class FAQRetrievalService:
    """FAQ retrieval service using semantic similarity."""
    
    def __init__(self):
        """Initialize the FAQ retrieval service."""
        self._indexes: Dict[int, any] = {}  # campaign_id -> FAISS index
        self._faq_data: Dict[int, List[Dict]] = {}  # campaign_id -> FAQ list
        self._embeddings: Dict[int, np.ndarray] = {}  # campaign_id -> embeddings
    
    def load_faqs(self, campaign_id: int, faqs: List[Dict]) -> bool:
        """
        Load and index FAQs for a campaign.
        
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
            model = _get_embedding_model()
            faiss = _get_faiss()
            
            # Extract questions for embedding
            questions = [faq.get("question", "") for faq in faqs]
            
            # Also include keywords if present
            for i, faq in enumerate(faqs):
                keywords = faq.get("keywords", [])
                if keywords:
                    questions[i] = questions[i] + " " + " ".join(keywords)
            
            # Generate embeddings
            embeddings = model.encode(questions, normalize_embeddings=True)
            embeddings = np.array(embeddings).astype('float32')
            
            # Create FAISS index
            dimension = embeddings.shape[1]
            index = faiss.IndexFlatIP(dimension)  # Inner product for cosine similarity
            index.add(embeddings)
            
            # Store data
            self._indexes[campaign_id] = index
            self._faq_data[campaign_id] = faqs
            self._embeddings[campaign_id] = embeddings
            
            logger.info(f"Loaded {len(faqs)} FAQs for campaign {campaign_id}")
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
        Retrieve relevant FAQs for a query.
        
        Args:
            campaign_id: Campaign ID to search in
            query: User's query
            top_k: Maximum number of results
            threshold: Minimum similarity score (0-1)
            
        Returns:
            List of (FAQ dict, similarity score) tuples
        """
        if campaign_id not in self._indexes:
            logger.warning(f"No FAQs indexed for campaign {campaign_id}")
            return []
        
        try:
            model = _get_embedding_model()
            
            # Embed query
            query_embedding = model.encode([query], normalize_embeddings=True)
            query_embedding = np.array(query_embedding).astype('float32')
            
            # Search
            index = self._indexes[campaign_id]
            scores, indices = index.search(query_embedding, min(top_k, len(self._faq_data[campaign_id])))
            
            # Filter by threshold and return
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if score >= threshold and idx >= 0:
                    faq = self._faq_data[campaign_id][idx]
                    results.append((faq, float(score)))
            
            logger.info(f"Retrieved {len(results)} FAQs for query: '{query[:50]}...'")
            return results
            
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
        self._indexes.pop(campaign_id, None)
        self._faq_data.pop(campaign_id, None)
        self._embeddings.pop(campaign_id, None)
        logger.info(f"Removed FAQ index for campaign {campaign_id}")
    
    def is_campaign_loaded(self, campaign_id: int) -> bool:
        """Check if a campaign's FAQs are loaded."""
        return campaign_id in self._indexes


# Singleton instance
faq_service = FAQRetrievalService()
