"""
Background worker thread for processing episodes.
Picks up unprocessed episodes, runs LLM extraction, stores results.
"""

import logging
import threading
import time
from typing import Optional

from .database import Database
from .embeddings import EmbeddingService
from .extraction import EntityExtractor

logger = logging.getLogger(__name__)


class BackgroundWorker:
    def __init__(self, db: Database, extractor: EntityExtractor, embedder: EmbeddingService):
        self.db = db
        self.extractor = extractor
        self.embedder = embedder
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._graph_ids: set = set()  # Active graph IDs to process

    def start(self):
        """Start the background worker thread."""
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name="local-graph-worker")
        self._thread.start()
        logger.info("Local graph background worker started")

    def stop(self):
        """Stop the background worker thread."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=10)
            self._thread = None
        logger.info("Local graph background worker stopped")

    def register_graph(self, graph_id: str):
        """Register a graph ID for processing."""
        self._graph_ids.add(graph_id)

    def unregister_graph(self, graph_id: str):
        """Unregister a graph ID."""
        self._graph_ids.discard(graph_id)

    def _run(self):
        """Main worker loop."""
        while not self._stop_event.is_set():
            processed_any = False
            for graph_id in list(self._graph_ids):
                try:
                    episodes = self.db.get_unprocessed_episodes(graph_id, limit=3)
                    for episode in episodes:
                        if self._stop_event.is_set():
                            return
                        self._process_episode(graph_id, episode)
                        processed_any = True
                except Exception as e:
                    logger.error(f"Worker error for graph {graph_id}: {e}")

            # If nothing was processed, sleep before next check
            if not processed_any:
                self._stop_event.wait(timeout=2.0)

    def _process_episode(self, graph_id: str, episode):
        """Process a single episode: extract entities/relationships, store, embed."""
        try:
            ontology = self.db.get_ontology(graph_id)
            if not ontology:
                ontology = {"entity_types": {}, "edge_types": {}}

            # Extract entities and relationships via LLM
            entities, relationships = self.extractor.extract(episode.data, ontology)

            # Store entities (with dedup)
            entity_name_to_uuid = {}
            for entity in entities:
                labels = ["Entity", entity["type"]] if entity["type"] != "Entity" else ["Entity"]
                embed_text = f"{entity['name']}. {entity['summary']}"
                embedding = self.embedder.embed(embed_text)

                node_uuid = self.db.upsert_node(
                    graph_id=graph_id,
                    name=entity["name"],
                    labels=labels,
                    summary=entity["summary"],
                    attributes=entity["attributes"],
                    embedding=embedding
                )
                entity_name_to_uuid[entity["name"].lower()] = node_uuid

            # Store relationships
            for rel in relationships:
                source_uuid = entity_name_to_uuid.get(rel["source"].lower())
                target_uuid = entity_name_to_uuid.get(rel["target"].lower())

                # If source/target not in this batch, look up in DB
                if not source_uuid:
                    source_uuid = self._find_node_uuid(graph_id, rel["source"])
                if not target_uuid:
                    target_uuid = self._find_node_uuid(graph_id, rel["target"])

                if source_uuid and target_uuid:
                    embedding = self.embedder.embed(rel["fact"]) if rel["fact"] else None
                    self.db.add_edge(
                        graph_id=graph_id,
                        name=rel["name"],
                        fact=rel["fact"],
                        source_uuid=source_uuid,
                        target_uuid=target_uuid,
                        attributes=rel["attributes"],
                        embedding=embedding
                    )
                else:
                    logger.warning(
                        f"Skipping relationship '{rel['name']}': "
                        f"source='{rel['source']}' ({source_uuid}), "
                        f"target='{rel['target']}' ({target_uuid})"
                    )

            # Mark as processed
            self.db.mark_episode_processed(episode.uuid_)
            logger.debug(f"Processed episode {episode.uuid_}: {len(entities)} entities, {len(relationships)} relationships")

        except Exception as e:
            logger.error(f"Failed to process episode {episode.uuid_}: {e}")
            # Mark as processed anyway to avoid infinite loop
            self.db.mark_episode_processed(episode.uuid_)

    def _find_node_uuid(self, graph_id: str, name: str) -> Optional[str]:
        """Look up a node UUID by name in the database."""
        conn = self.db._get_conn()
        row = conn.execute(
            "SELECT uuid FROM nodes WHERE graph_id = ? AND LOWER(name) = LOWER(?)",
            (graph_id, name)
        ).fetchone()
        return row["uuid"] if row else None
