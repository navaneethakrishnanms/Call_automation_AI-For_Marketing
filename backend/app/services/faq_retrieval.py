"""
Campaign Knowledge Base Service
================================
Embeds campaign name, description, and FAQs into a unified ChromaDB vector store.
Uses Sentence-Transformers for semantic retrieval.
Persistent vector store — survives server restarts.
"""

import os
import re
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
    
    def name(self) -> str:
        return "all-MiniLM-L6-v2"
    
    def __call__(self, input: List[str]) -> List[List[float]]:
        model = _get_embedding_model()
        embeddings = model.encode(input, normalize_embeddings=True)
        return embeddings.tolist()


def _split_description(description: str) -> List[str]:
    """
    Split a campaign description into meaningful chunks for embedding.
    Splits on paragraph breaks first, then on sentences if chunks are too long.
    Each chunk should be self-contained enough to be useful in retrieval.
    """
    if not description or not description.strip():
        return []
    
    description = description.strip()
    
    # First split on double newlines (paragraphs)
    paragraphs = re.split(r'\n\s*\n', description)
    
    chunks = []
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        
        # If paragraph is short enough (<500 chars), keep it as one chunk
        if len(para) < 500:
            chunks.append(para)
        else:
            # Split long paragraphs into sentences
            sentences = re.split(r'(?<=[.!?])\s+', para)
            current_chunk = ""
            for sentence in sentences:
                if len(current_chunk) + len(sentence) < 400:
                    current_chunk += (" " if current_chunk else "") + sentence
                else:
                    if current_chunk:
                        chunks.append(current_chunk)
                    current_chunk = sentence
            if current_chunk:
                chunks.append(current_chunk)
    
    # If no chunks were created (e.g., single-line description), use the whole thing
    if not chunks:
        chunks = [description]
    
    return chunks


class FAQRetrievalService:
    """Campaign knowledge base using ChromaDB + semantic similarity.
    Embeds campaign name, description, and FAQs."""
    
    def __init__(self):
        """Initialize the knowledge base service."""
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
    
    def load_campaign_knowledge(
        self,
        campaign_id: int,
        name: str,
        description: Optional[str] = None,
        faqs: Optional[List[Dict]] = None
    ) -> bool:
        """
        Build a unified knowledge base for a campaign.
        Embeds: campaign name, description chunks, and FAQ questions.
        
        Args:
            campaign_id: Campaign ID
            name: Campaign name
            description: Campaign description (product/college marketing details)
            faqs: List of FAQ dictionaries with 'question' and 'answer' keys
            
        Returns:
            True if successful, False otherwise
        """
        try:
            collection = self._get_collection(campaign_id)
            
            # Clear existing data for this campaign (fresh rebuild)
            existing = collection.count()
            if existing > 0:
                all_ids = collection.get()["ids"]
                if all_ids:
                    collection.delete(ids=all_ids)
                logger.info(f"Cleared {existing} existing items for campaign {campaign_id}")
            
            documents = []
            metadatas = []
            ids = []
            
            # === 1. Embed campaign name ===
            if name:
                documents.append(name)
                metadatas.append({
                    "type": "campaign_info",
                    "question": f"What is {name}?",
                    "answer": name,
                    "source": "campaign_name"
                })
                ids.append(f"name_{campaign_id}")
            
            # === 2. Embed description chunks ===
            if description:
                desc_chunks = _split_description(description)
                for i, chunk in enumerate(desc_chunks):
                    documents.append(chunk)
                    metadatas.append({
                        "type": "campaign_description",
                        "question": chunk[:200],  # Summary for display
                        "answer": chunk,
                        "source": "description",
                        "chunk_index": i
                    })
                    ids.append(f"desc_{campaign_id}_{i}")
                
                logger.info(f"Split description into {len(desc_chunks)} chunks for campaign {campaign_id}")
            
            # === 3. Embed FAQs ===
            if faqs:
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
                        "type": "faq",
                        "question": question,
                        "answer": answer,
                        "keywords": " ".join(keywords) if keywords else "",
                        "faq_index": i
                    })
                    ids.append(f"faq_{campaign_id}_{i}")
            
            if not documents:
                logger.warning(f"No knowledge items for campaign {campaign_id}")
                return False
            
            # Add all to ChromaDB (handles embedding automatically)
            collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            
            self._loaded_campaigns.add(campaign_id)
            
            faq_count = len(faqs) if faqs else 0
            desc_count = len(_split_description(description)) if description else 0
            total = len(documents)
            logger.info(
                f"Loaded {total} knowledge items for campaign {campaign_id} "
                f"(name: 1, description: {desc_count}, FAQs: {faq_count})"
            )
            return True
            
        except Exception as e:
            logger.error(f"Failed to load knowledge base for campaign {campaign_id}: {str(e)}")
            return False
    
    def load_faqs(self, campaign_id: int, faqs: List[Dict]) -> bool:
        """
        Legacy method — loads only FAQs (backward compatibility).
        Prefer load_campaign_knowledge() for full knowledge base.
        """
        return self.load_campaign_knowledge(
            campaign_id=campaign_id,
            name="",
            description=None,
            faqs=faqs
        )
    
    def retrieve(
        self,
        campaign_id: int,
        query: str,
        top_k: int = 5,
        threshold: float = 0.3
    ) -> List[Tuple[Dict, float]]:
        """
        Retrieve relevant knowledge items for a query using ChromaDB.
        Returns matches from FAQs, description, and campaign name.
        
        Args:
            campaign_id: Campaign ID to search in
            query: User's query
            top_k: Maximum number of results (increased to 5 for richer context)
            threshold: Minimum similarity score (0-1)
            
        Returns:
            List of (item dict, similarity score) tuples
        """
        if campaign_id not in self._loaded_campaigns:
            logger.warning(f"No knowledge loaded for campaign {campaign_id}")
            return []
        
        try:
            collection = self._get_collection(campaign_id)
            
            # Query ChromaDB
            count = collection.count()
            if count == 0:
                return []
            
            results = collection.query(
                query_texts=[query],
                n_results=min(top_k, count),
                include=["metadatas", "distances"]
            )
            
            # ChromaDB returns distances (lower = more similar for cosine)
            # Convert to similarity: similarity = 1 - distance
            matched = []
            if results["metadatas"] and results["distances"]:
                for metadata, distance in zip(results["metadatas"][0], results["distances"][0]):
                    similarity = 1.0 - distance  # cosine distance → similarity
                    if similarity >= threshold:
                        item = {
                            "type": metadata.get("type", "faq"),
                            "question": metadata.get("question", ""),
                            "answer": metadata.get("answer", ""),
                            "keywords": metadata.get("keywords", "").split() if metadata.get("keywords") else []
                        }
                        matched.append((item, float(similarity)))
            
            logger.info(f"ChromaDB retrieved {len(matched)} items for query: '{query[:50]}...'")
            return matched
            
        except Exception as e:
            logger.error(f"Knowledge retrieval failed: {str(e)}")
            return []
    
    def format_knowledge_context(self, items: List[Tuple[Dict, float]]) -> str:
        """
        Format retrieved knowledge items as context for the LLM.
        Handles FAQ, description, and campaign_info types differently.
        
        Args:
            items: List of (item dict, score) tuples
            
        Returns:
            Formatted context string
        """
        if not items:
            return ""
        
        faq_parts = []
        desc_parts = []
        faq_num = 0
        
        for item, score in items:
            item_type = item.get("type", "faq")
            
            if item_type == "faq":
                faq_num += 1
                question = item.get("question", "")
                answer = item.get("answer", "")
                faq_parts.append(f"Q{faq_num}: {question}\nA{faq_num}: {answer}")
            
            elif item_type in ("campaign_description", "campaign_info"):
                answer = item.get("answer", "")
                if answer:
                    desc_parts.append(answer)
        
        context_sections = []
        
        if desc_parts:
            context_sections.append(
                "About this campaign/product:\n" + "\n".join(desc_parts)
            )
        
        if faq_parts:
            context_sections.append(
                "Relevant FAQ answers:\n" + "\n\n".join(faq_parts)
            )
        
        return "\n\n".join(context_sections)
    
    def format_faq_context(self, faqs: List[Tuple[Dict, float]]) -> str:
        """Legacy alias for format_knowledge_context."""
        return self.format_knowledge_context(faqs)
    
    def remove_campaign(self, campaign_id: int):
        """Remove knowledge base for a campaign."""
        try:
            client = _get_chroma_client()
            collection_name = f"campaign_{campaign_id}"
            client.delete_collection(collection_name)
            self._loaded_campaigns.discard(campaign_id)
            logger.info(f"Removed ChromaDB collection for campaign {campaign_id}")
        except Exception as e:
            logger.warning(f"Could not remove collection for campaign {campaign_id}: {e}")
    
    def is_campaign_loaded(self, campaign_id: int) -> bool:
        """Check if a campaign's knowledge base is loaded."""
        return campaign_id in self._loaded_campaigns


# Singleton instance
faq_service = FAQRetrievalService()
