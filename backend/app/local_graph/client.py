"""
LocalGraphClient - Drop-in replacement for zep_cloud.client.Zep.
Provides the same nested namespace API: client.graph.create(), client.graph.node.get(), etc.
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional

from .database import Database
from .embeddings import EmbeddingService
from .extraction import EntityExtractor
from .models import Edge, Episode, EpisodeData, Node, SearchResult
from .worker import BackgroundWorker

logger = logging.getLogger(__name__)


class EpisodeNamespace:
    """client.graph.episode.*"""

    def __init__(self, db: Database):
        self._db = db

    def get(self, uuid_: str) -> Optional[Episode]:
        return self._db.get_episode(uuid_)


class NodeNamespace:
    """client.graph.node.*"""

    def __init__(self, db: Database):
        self._db = db

    def get(self, uuid_: str) -> Optional[Node]:
        return self._db.get_node(uuid_)

    def get_entity_edges(self, node_uuid: str) -> List[Edge]:
        return self._db.get_node_edges(node_uuid)

    def get_by_graph_id(self, graph_id: str, limit: int = 100, uuid_cursor: str = None) -> List[Node]:
        return self._db.get_nodes_by_graph(graph_id, limit=limit, cursor=uuid_cursor)


class EdgeNamespace:
    """client.graph.edge.*"""

    def __init__(self, db: Database):
        self._db = db

    def get_by_graph_id(self, graph_id: str, limit: int = 100, uuid_cursor: str = None) -> List[Edge]:
        return self._db.get_edges_by_graph(graph_id, limit=limit, cursor=uuid_cursor)


class GraphNamespace:
    """client.graph.* - Main graph operations."""

    def __init__(self, db: Database, embedder: EmbeddingService, extractor: EntityExtractor,
                 worker: BackgroundWorker):
        self._db = db
        self._embedder = embedder
        self._extractor = extractor
        self._worker = worker
        self.node = NodeNamespace(db)
        self.edge = EdgeNamespace(db)
        self.episode = EpisodeNamespace(db)

    def create(self, graph_id: str, name: str = "", description: str = ""):
        """Create a new graph."""
        self._db.create_graph(graph_id, name, description)
        self._worker.register_graph(graph_id)
        logger.info(f"Created local graph: {graph_id}")

    def set_ontology(self, graph_ids: List[str], entities: Dict = None, edges: Dict = None):
        """
        Store ontology schema. Accepts the same dynamic Pydantic classes that Zep expects.
        Introspects them to extract field metadata and stores as JSON.
        """
        entity_schema = self._introspect_entities(entities or {})
        edge_schema = self._introspect_edges(edges or {})

        for gid in graph_ids:
            self._db.set_ontology(gid, entity_schema, edge_schema)
        logger.info(f"Set ontology for graphs {graph_ids}: {len(entity_schema)} entity types, {len(edge_schema)} edge types")

    def add(self, graph_id: str, type: str = "text", data: str = ""):
        """Add a single text entry to the graph for processing."""
        self._worker.register_graph(graph_id)
        self._db.add_episode(graph_id, data, type)

    def add_batch(self, graph_id: str, episodes: List[EpisodeData] = None) -> List[Episode]:
        """Add a batch of text episodes. Returns Episode objects with UUIDs."""
        self._worker.register_graph(graph_id)
        results = []
        for ep in (episodes or []):
            data = ep.data if isinstance(ep, EpisodeData) else getattr(ep, 'data', str(ep))
            ep_type = ep.type if isinstance(ep, EpisodeData) else getattr(ep, 'type', 'text')
            ep_uuid = self._db.add_episode(graph_id, data, ep_type)
            results.append(Episode(uuid_=ep_uuid, processed=False, data=data, type=ep_type))
        return results

    def delete(self, graph_id: str):
        """Delete a graph and all its data."""
        self._worker.unregister_graph(graph_id)
        self._db.delete_graph(graph_id)
        logger.info(f"Deleted local graph: {graph_id}")

    def search(self, graph_id: str, query: str, limit: int = 10,
               scope: str = "edges", reranker: str = "cross_encoder") -> List[SearchResult]:
        """
        Semantic search across graph data using local embeddings.
        scope: "edges" or "nodes"
        reranker: accepted but ignored (cosine similarity used instead)
        """
        query_embedding = self._embedder.embed(query)
        if not query_embedding:
            return []

        if scope == "nodes":
            candidates = self._db.get_all_node_embeddings(graph_id)
            results = self._embedder.cosine_search(query_embedding, candidates, limit=limit)
            return [SearchResult(
                fact=f"{r['name']}: {r.get('summary', '')}",
                source_node_uuid=r["uuid"],
                target_node_uuid="",
                score=r["score"]
            ) for r in results]
        else:
            candidates = self._db.get_all_edge_embeddings(graph_id)
            results = self._embedder.cosine_search(query_embedding, candidates, limit=limit)
            return [SearchResult(
                fact=r["fact"],
                source_node_uuid=r["source_node_uuid"],
                target_node_uuid=r["target_node_uuid"],
                score=r["score"]
            ) for r in results]

    def _introspect_entities(self, entities: Dict) -> Dict:
        """Extract metadata from dynamic Pydantic entity classes."""
        schema = {}
        for name, cls in entities.items():
            info = {"description": getattr(cls, '__doc__', '') or name}
            # Try Pydantic v2 model_fields, then v1 __fields__
            fields = {}
            if hasattr(cls, 'model_fields'):
                for fname, finfo in cls.model_fields.items():
                    if fname not in ('name', 'uuid', 'group_id', 'created_at', 'summary', 'name_embedding'):
                        fields[fname] = {"name": fname, "description": getattr(finfo, 'description', '') or fname}
            elif hasattr(cls, '__fields__'):
                for fname, finfo in cls.__fields__.items():
                    if fname not in ('name', 'uuid', 'group_id', 'created_at', 'summary', 'name_embedding'):
                        desc = finfo.field_info.description if hasattr(finfo, 'field_info') else fname
                        fields[fname] = {"name": fname, "description": desc or fname}
            info["attributes"] = list(fields.values())
            schema[name] = info
        return schema

    def _introspect_edges(self, edges: Dict) -> Dict:
        """Extract metadata from dynamic Pydantic edge classes with source/target info."""
        schema = {}
        for name, value in edges.items():
            if isinstance(value, tuple) and len(value) == 2:
                cls, source_targets = value
            else:
                cls = value
                source_targets = []
            info = {
                "description": getattr(cls, '__doc__', '') or name,
                "source_targets": []
            }
            for st in source_targets:
                src = getattr(st, 'source', None) or (st.get('source') if isinstance(st, dict) else None)
                tgt = getattr(st, 'target', None) or (st.get('target') if isinstance(st, dict) else None)
                if src and tgt:
                    info["source_targets"].append({"source": src, "target": tgt})
            schema[name] = info
        return schema


class LocalGraphClient:
    """
    Drop-in replacement for zep_cloud.client.Zep.

    Usage:
        client = LocalGraphClient()
        client.graph.create(graph_id="my_graph", name="Test")
        client.graph.add(graph_id="my_graph", type="text", data="Some text...")
        results = client.graph.search(graph_id="my_graph", query="search term")
    """

    def __init__(self, db_path: str = None, lm_studio_url: str = None, llm_model: str = None):
        from ..config import Config

        if db_path is None:
            db_path = getattr(Config, 'LOCAL_GRAPH_DB_PATH',
                              os.path.join(os.path.dirname(__file__), '../../data/mirofish_graph.db'))
        if lm_studio_url is None:
            lm_studio_url = getattr(Config, 'LM_STUDIO_URL', Config.LLM_BASE_URL)
        if llm_model is None:
            llm_model = Config.LLM_MODEL_NAME

        # Ensure data directory exists
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)

        db = Database(db_path)
        embedder = EmbeddingService(lm_studio_url=lm_studio_url)
        extractor = EntityExtractor(lm_studio_url=lm_studio_url, model=llm_model)
        worker = BackgroundWorker(db=db, extractor=extractor, embedder=embedder)
        worker.start()

        self.graph = GraphNamespace(db=db, embedder=embedder, extractor=extractor, worker=worker)
        self._worker = worker

    def __del__(self):
        if hasattr(self, '_worker'):
            self._worker.stop()
