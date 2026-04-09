"""
SQLite database for local graph storage.
Thread-safe with WAL mode for concurrent reads during writes.
"""

import json
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .models import Edge, Episode, Node


class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._local = threading.local()
        self._init_schema()

    def _get_conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            conn.row_factory = sqlite3.Row
            self._local.conn = conn
        return self._local.conn

    def _init_schema(self):
        conn = self._get_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS graphs (
                graph_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS ontologies (
                graph_id TEXT PRIMARY KEY REFERENCES graphs(graph_id) ON DELETE CASCADE,
                entity_types_json TEXT NOT NULL DEFAULT '{}',
                edge_types_json TEXT NOT NULL DEFAULT '{}'
            );

            CREATE TABLE IF NOT EXISTS nodes (
                uuid TEXT PRIMARY KEY,
                graph_id TEXT NOT NULL REFERENCES graphs(graph_id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                labels_json TEXT DEFAULT '[]',
                summary TEXT DEFAULT '',
                attributes_json TEXT DEFAULT '{}',
                embedding BLOB,
                created_at TEXT DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS idx_nodes_graph ON nodes(graph_id);
            CREATE INDEX IF NOT EXISTS idx_nodes_name ON nodes(graph_id, name);

            CREATE TABLE IF NOT EXISTS edges (
                uuid TEXT PRIMARY KEY,
                graph_id TEXT NOT NULL REFERENCES graphs(graph_id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                fact TEXT DEFAULT '',
                source_node_uuid TEXT NOT NULL,
                target_node_uuid TEXT NOT NULL,
                attributes_json TEXT DEFAULT '{}',
                embedding BLOB,
                created_at TEXT DEFAULT (datetime('now')),
                valid_at TEXT,
                invalid_at TEXT,
                expired_at TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_edges_graph ON edges(graph_id);
            CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source_node_uuid);
            CREATE INDEX IF NOT EXISTS idx_edges_target ON edges(target_node_uuid);

            CREATE TABLE IF NOT EXISTS episodes (
                uuid TEXT PRIMARY KEY,
                graph_id TEXT NOT NULL REFERENCES graphs(graph_id) ON DELETE CASCADE,
                data TEXT NOT NULL,
                type TEXT DEFAULT 'text',
                processed INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS idx_episodes_graph ON episodes(graph_id);
            CREATE INDEX IF NOT EXISTS idx_episodes_pending ON episodes(processed) WHERE processed = 0;
        """)
        conn.commit()

    @staticmethod
    def _new_uuid() -> str:
        return uuid.uuid4().hex

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    # --- Graphs ---

    def create_graph(self, graph_id: str, name: str, description: str = ""):
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO graphs (graph_id, name, description, created_at) VALUES (?, ?, ?, ?)",
            (graph_id, name, description, self._now())
        )
        conn.commit()

    def delete_graph(self, graph_id: str):
        conn = self._get_conn()
        conn.execute("DELETE FROM graphs WHERE graph_id = ?", (graph_id,))
        conn.commit()

    def graph_exists(self, graph_id: str) -> bool:
        conn = self._get_conn()
        row = conn.execute("SELECT 1 FROM graphs WHERE graph_id = ?", (graph_id,)).fetchone()
        return row is not None

    # --- Ontology ---

    def set_ontology(self, graph_id: str, entity_types: Dict, edge_types: Dict):
        conn = self._get_conn()
        conn.execute(
            "INSERT OR REPLACE INTO ontologies (graph_id, entity_types_json, edge_types_json) VALUES (?, ?, ?)",
            (graph_id, json.dumps(entity_types, ensure_ascii=False), json.dumps(edge_types, ensure_ascii=False))
        )
        conn.commit()

    def get_ontology(self, graph_id: str) -> Optional[Dict]:
        conn = self._get_conn()
        row = conn.execute("SELECT entity_types_json, edge_types_json FROM ontologies WHERE graph_id = ?", (graph_id,)).fetchone()
        if not row:
            return None
        return {
            "entity_types": json.loads(row["entity_types_json"]),
            "edge_types": json.loads(row["edge_types_json"])
        }

    # --- Episodes ---

    def add_episode(self, graph_id: str, data: str, ep_type: str = "text") -> str:
        ep_uuid = self._new_uuid()
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO episodes (uuid, graph_id, data, type, processed, created_at) VALUES (?, ?, ?, ?, 0, ?)",
            (ep_uuid, graph_id, data, ep_type, self._now())
        )
        conn.commit()
        return ep_uuid

    def get_episode(self, ep_uuid: str) -> Optional[Episode]:
        conn = self._get_conn()
        row = conn.execute("SELECT uuid, data, type, processed FROM episodes WHERE uuid = ?", (ep_uuid,)).fetchone()
        if not row:
            return None
        return Episode(uuid_=row["uuid"], data=row["data"], type=row["type"], processed=bool(row["processed"]))

    def get_unprocessed_episodes(self, graph_id: str, limit: int = 10) -> List[Episode]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT uuid, data, type, processed FROM episodes WHERE graph_id = ? AND processed = 0 ORDER BY created_at LIMIT ?",
            (graph_id, limit)
        ).fetchall()
        return [Episode(uuid_=r["uuid"], data=r["data"], type=r["type"], processed=False) for r in rows]

    def mark_episode_processed(self, ep_uuid: str):
        conn = self._get_conn()
        conn.execute("UPDATE episodes SET processed = 1 WHERE uuid = ?", (ep_uuid,))
        conn.commit()

    # --- Nodes ---

    def upsert_node(self, graph_id: str, name: str, labels: List[str], summary: str = "",
                    attributes: Dict = None, embedding: bytes = None) -> str:
        conn = self._get_conn()
        # Check if node with same name exists in this graph
        row = conn.execute(
            "SELECT uuid, summary, attributes_json FROM nodes WHERE graph_id = ? AND LOWER(name) = LOWER(?)",
            (graph_id, name)
        ).fetchone()

        if row:
            # Merge: update summary and attributes
            existing_attrs = json.loads(row["attributes_json"])
            if attributes:
                existing_attrs.update(attributes)
            merged_summary = row["summary"]
            if summary and summary != merged_summary:
                merged_summary = f"{merged_summary} {summary}".strip() if merged_summary else summary

            conn.execute(
                "UPDATE nodes SET summary = ?, attributes_json = ?, labels_json = ?, embedding = ? WHERE uuid = ?",
                (merged_summary, json.dumps(existing_attrs, ensure_ascii=False),
                 json.dumps(labels, ensure_ascii=False), embedding, row["uuid"])
            )
            conn.commit()
            return row["uuid"]
        else:
            node_uuid = self._new_uuid()
            conn.execute(
                "INSERT INTO nodes (uuid, graph_id, name, labels_json, summary, attributes_json, embedding, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (node_uuid, graph_id, name, json.dumps(labels, ensure_ascii=False),
                 summary, json.dumps(attributes or {}, ensure_ascii=False), embedding, self._now())
            )
            conn.commit()
            return node_uuid

    def get_node(self, node_uuid: str) -> Optional[Node]:
        conn = self._get_conn()
        row = conn.execute(
            "SELECT uuid, name, labels_json, summary, attributes_json, created_at FROM nodes WHERE uuid = ?",
            (node_uuid,)
        ).fetchone()
        if not row:
            return None
        return Node(
            uuid_=row["uuid"], name=row["name"],
            labels=json.loads(row["labels_json"]),
            summary=row["summary"],
            attributes=json.loads(row["attributes_json"]),
            created_at=row["created_at"]
        )

    def get_nodes_by_graph(self, graph_id: str, limit: int = 100, cursor: str = None) -> List[Node]:
        conn = self._get_conn()
        if cursor:
            rows = conn.execute(
                "SELECT uuid, name, labels_json, summary, attributes_json, created_at FROM nodes "
                "WHERE graph_id = ? AND uuid > ? ORDER BY uuid LIMIT ?",
                (graph_id, cursor, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT uuid, name, labels_json, summary, attributes_json, created_at FROM nodes "
                "WHERE graph_id = ? ORDER BY uuid LIMIT ?",
                (graph_id, limit)
            ).fetchall()
        return [Node(
            uuid_=r["uuid"], name=r["name"],
            labels=json.loads(r["labels_json"]),
            summary=r["summary"],
            attributes=json.loads(r["attributes_json"]),
            created_at=r["created_at"]
        ) for r in rows]

    def count_nodes(self, graph_id: str) -> int:
        conn = self._get_conn()
        row = conn.execute("SELECT COUNT(*) as c FROM nodes WHERE graph_id = ?", (graph_id,)).fetchone()
        return row["c"]

    # --- Edges ---

    def add_edge(self, graph_id: str, name: str, fact: str, source_uuid: str, target_uuid: str,
                 attributes: Dict = None, embedding: bytes = None) -> str:
        edge_uuid = self._new_uuid()
        now = self._now()
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO edges (uuid, graph_id, name, fact, source_node_uuid, target_node_uuid, "
            "attributes_json, embedding, created_at, valid_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (edge_uuid, graph_id, name, fact, source_uuid, target_uuid,
             json.dumps(attributes or {}, ensure_ascii=False), embedding, now, now)
        )
        conn.commit()
        return edge_uuid

    def get_edges_by_graph(self, graph_id: str, limit: int = 100, cursor: str = None) -> List[Edge]:
        conn = self._get_conn()
        if cursor:
            rows = conn.execute(
                "SELECT uuid, name, fact, source_node_uuid, target_node_uuid, attributes_json, "
                "created_at, valid_at, invalid_at, expired_at FROM edges "
                "WHERE graph_id = ? AND uuid > ? ORDER BY uuid LIMIT ?",
                (graph_id, cursor, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT uuid, name, fact, source_node_uuid, target_node_uuid, attributes_json, "
                "created_at, valid_at, invalid_at, expired_at FROM edges "
                "WHERE graph_id = ? ORDER BY uuid LIMIT ?",
                (graph_id, limit)
            ).fetchall()
        return [self._row_to_edge(r) for r in rows]

    def get_node_edges(self, node_uuid: str) -> List[Edge]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT uuid, name, fact, source_node_uuid, target_node_uuid, attributes_json, "
            "created_at, valid_at, invalid_at, expired_at FROM edges "
            "WHERE source_node_uuid = ? OR target_node_uuid = ?",
            (node_uuid, node_uuid)
        ).fetchall()
        return [self._row_to_edge(r) for r in rows]

    def count_edges(self, graph_id: str) -> int:
        conn = self._get_conn()
        row = conn.execute("SELECT COUNT(*) as c FROM edges WHERE graph_id = ?", (graph_id,)).fetchone()
        return row["c"]

    # --- Search helpers ---

    def get_all_edge_embeddings(self, graph_id: str) -> List[Dict[str, Any]]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT uuid, fact, source_node_uuid, target_node_uuid, embedding FROM edges "
            "WHERE graph_id = ? AND embedding IS NOT NULL",
            (graph_id,)
        ).fetchall()
        return [{"uuid": r["uuid"], "fact": r["fact"], "source_node_uuid": r["source_node_uuid"],
                 "target_node_uuid": r["target_node_uuid"], "embedding": r["embedding"]} for r in rows]

    def get_all_node_embeddings(self, graph_id: str) -> List[Dict[str, Any]]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT uuid, name, summary, embedding FROM nodes "
            "WHERE graph_id = ? AND embedding IS NOT NULL",
            (graph_id,)
        ).fetchall()
        return [{"uuid": r["uuid"], "name": r["name"], "summary": r["summary"],
                 "embedding": r["embedding"]} for r in rows]

    def _row_to_edge(self, r) -> Edge:
        return Edge(
            uuid_=r["uuid"], name=r["name"], fact=r["fact"],
            source_node_uuid=r["source_node_uuid"],
            target_node_uuid=r["target_node_uuid"],
            attributes=json.loads(r["attributes_json"]),
            created_at=r["created_at"],
            valid_at=r["valid_at"],
            invalid_at=r["invalid_at"],
            expired_at=r["expired_at"]
        )
