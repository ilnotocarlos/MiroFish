"""
Local graph engine - drop-in replacement for Zep Cloud.
Uses SQLite + local LLM for entity extraction + local embeddings for search.
"""

from .client import LocalGraphClient
from .models import EpisodeData, EntityEdgeSourceTarget, InternalServerError

__all__ = ['LocalGraphClient', 'EpisodeData', 'EntityEdgeSourceTarget', 'InternalServerError']
