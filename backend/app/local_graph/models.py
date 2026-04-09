"""
Data models that replicate Zep Cloud's return types.
These must match the attribute names that existing MiroFish code accesses.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Node:
    uuid_: str
    name: str
    labels: List[str] = field(default_factory=list)
    summary: str = ""
    attributes: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[str] = None

    # Alias for compatibility (some code uses .uuid instead of .uuid_)
    @property
    def uuid(self):
        return self.uuid_


@dataclass
class Edge:
    uuid_: str
    name: str
    fact: str = ""
    source_node_uuid: str = ""
    target_node_uuid: str = ""
    attributes: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[str] = None
    valid_at: Optional[str] = None
    invalid_at: Optional[str] = None
    expired_at: Optional[str] = None
    episodes: Optional[List[str]] = None

    @property
    def uuid(self):
        return self.uuid_


@dataclass
class Episode:
    uuid_: str
    processed: bool = False
    data: str = ""
    type: str = "text"

    @property
    def uuid(self):
        return self.uuid_


@dataclass
class EpisodeData:
    """Input data for add_batch(), compatible with zep_cloud.EpisodeData."""
    data: str
    type: str = "text"


@dataclass
class EntityEdgeSourceTarget:
    """Compatible with zep_cloud.EntityEdgeSourceTarget."""
    source: str
    target: str


@dataclass
class SearchResult:
    """A single search result with edge/node data."""
    fact: str = ""
    source_node_uuid: str = ""
    target_node_uuid: str = ""
    score: float = 0.0


class InternalServerError(Exception):
    """Compatible with zep_cloud.InternalServerError."""
    pass
