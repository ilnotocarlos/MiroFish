"""
Local embedding service using LM Studio's nomic-embed-text model.
Generates embeddings and performs cosine similarity search.
"""

import logging
import struct
from typing import Any, Dict, List, Optional

import numpy as np
import requests

logger = logging.getLogger(__name__)

# Default embedding model in LM Studio
DEFAULT_EMBEDDING_MODEL = "text-embedding-nomic-embed-text-v1.5"


class EmbeddingService:
    def __init__(self, lm_studio_url: str = "http://localhost:1234/v1",
                 model: str = DEFAULT_EMBEDDING_MODEL):
        self.url = f"{lm_studio_url}/embeddings"
        self.model = model
        self._dimension = None

    def embed(self, text: str) -> Optional[bytes]:
        """Generate embedding for a single text. Returns raw bytes (float32 array)."""
        if not text or not text.strip():
            return None
        try:
            resp = requests.post(self.url, json={
                "model": self.model,
                "input": text[:8000]  # Truncate to avoid token limits
            }, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            vector = data["data"][0]["embedding"]
            self._dimension = len(vector)
            return np.array(vector, dtype=np.float32).tobytes()
        except Exception as e:
            logger.warning(f"Embedding generation failed: {e}")
            return None

    def embed_batch(self, texts: List[str]) -> List[Optional[bytes]]:
        """Generate embeddings for multiple texts."""
        results = []
        for text in texts:
            results.append(self.embed(text))
        return results

    @staticmethod
    def bytes_to_vector(raw: bytes) -> np.ndarray:
        """Convert raw bytes back to numpy float32 array."""
        return np.frombuffer(raw, dtype=np.float32)

    def cosine_search(self, query_embedding: bytes, candidates: List[Dict[str, Any]],
                      limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search candidates by cosine similarity to query.

        Each candidate dict must have an 'embedding' key with raw bytes.
        Returns top-k candidates sorted by score, with 'score' added to each dict.
        """
        if not query_embedding or not candidates:
            return []

        query_vec = self.bytes_to_vector(query_embedding)
        query_norm = np.linalg.norm(query_vec)
        if query_norm == 0:
            return []

        scored = []
        for candidate in candidates:
            emb = candidate.get("embedding")
            if not emb:
                continue
            cand_vec = self.bytes_to_vector(emb)
            cand_norm = np.linalg.norm(cand_vec)
            if cand_norm == 0:
                continue
            score = float(np.dot(query_vec, cand_vec) / (query_norm * cand_norm))
            scored.append({**candidate, "score": score})

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:limit]
