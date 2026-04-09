"""
Zep Retrieval Tools Service
Graph search, node reading, edge query tools for Report Agent

Core retrieval tools (optimized):
1. InsightForge (deep insight retrieval) - Most powerful hybrid retrieval, auto-generates sub-questions and multi-dimensional retrieval
2. PanoramaSearch (breadth search) - Get full picture, including expired content
3. QuickSearch (simple search) - Fast retrieval
"""

import time
import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

from ..local_graph import LocalGraphClient

from ..config import Config
from ..utils.logger import get_logger
from ..utils.llm_client import LLMClient
from ..utils.zep_paging import fetch_all_nodes, fetch_all_edges

logger = get_logger('mirofish.zep_tools')


@dataclass
class SearchResult:
    """SearchResult"""
    facts: List[str]
    edges: List[Dict[str, Any]]
    nodes: List[Dict[str, Any]]
    query: str
    total_count: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "facts": self.facts,
            "edges": self.edges,
            "nodes": self.nodes,
            "query": self.query,
            "total_count": self.total_count
        }
    
    def to_text(self) -> str:
        """Convert to text format for LLM comprehension"""
        text_parts = [f"Query di ricerca: {self.query}", f"Trovati {self.total_count} risultati pertinenti"]

        if self.facts:
            text_parts.append("\n### Fatti pertinenti:")
            for i, fact in enumerate(self.facts, 1):
                text_parts.append(f"{i}. {fact}")
        
        return "\n".join(text_parts)


@dataclass
class NodeInfo:
    """Nodeinfo"""
    uuid: str
    name: str
    labels: List[str]
    summary: str
    attributes: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "uuid": self.uuid,
            "name": self.name,
            "labels": self.labels,
            "summary": self.summary,
            "attributes": self.attributes
        }
    
    def to_text(self) -> str:
        """Convert to text format"""
        entity_type = next((l for l in self.labels if l not in ["Entity", "Node"]), "Tipo sconosciuto")
        return f"Entità: {self.name} (Tipo: {entity_type})\nRiepilogo: {self.summary}"


@dataclass
class EdgeInfo:
    """Edge info"""
    uuid: str
    name: str
    fact: str
    source_node_uuid: str
    target_node_uuid: str
    source_node_name: Optional[str] = None
    target_node_name: Optional[str] = None
    # Timeinfo
    created_at: Optional[str] = None
    valid_at: Optional[str] = None
    invalid_at: Optional[str] = None
    expired_at: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "uuid": self.uuid,
            "name": self.name,
            "fact": self.fact,
            "source_node_uuid": self.source_node_uuid,
            "target_node_uuid": self.target_node_uuid,
            "source_node_name": self.source_node_name,
            "target_node_name": self.target_node_name,
            "created_at": self.created_at,
            "valid_at": self.valid_at,
            "invalid_at": self.invalid_at,
            "expired_at": self.expired_at
        }
    
    def to_text(self, include_temporal: bool = False) -> str:
        """Convert to text format"""
        source = self.source_node_name or self.source_node_uuid[:8]
        target = self.target_node_name or self.target_node_uuid[:8]
        base_text = f"Relazione: {source} --[{self.name}]--> {target}\nFatto: {self.fact}"

        if include_temporal:
            valid_at = self.valid_at or "Sconosciuto"
            invalid_at = self.invalid_at or "Attuale"
            base_text += f"\nValidità: {valid_at} - {invalid_at}"
            if self.expired_at:
                base_text += f" (Scaduto: {self.expired_at})"
        
        return base_text
    
    @property
    def is_expired(self) -> bool:
        """Whether already expired"""
        return self.expired_at is not None
    
    @property
    def is_invalid(self) -> bool:
        """Whether already invalidated"""
        return self.invalid_at is not None


@dataclass
class InsightForgeResult:
    """
    Deep insight retrieval result (InsightForge)
    Contains retrieval results from multiple sub-questions, plus synthesized analysis
    """
    query: str
    simulation_requirement: str
    sub_queries: List[str]
    
    # Retrieval results by dimension
    semantic_facts: List[str] = field(default_factory=list)  # Semantic search results
    entity_insights: List[Dict[str, Any]] = field(default_factory=list)  # Entity insights
    relationship_chains: List[str] = field(default_factory=list)  # Relationshipchain
    
    # Statisticsinfo
    total_facts: int = 0
    total_entities: int = 0
    total_relationships: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "simulation_requirement": self.simulation_requirement,
            "sub_queries": self.sub_queries,
            "semantic_facts": self.semantic_facts,
            "entity_insights": self.entity_insights,
            "relationship_chains": self.relationship_chains,
            "total_facts": self.total_facts,
            "total_entities": self.total_entities,
            "total_relationships": self.total_relationships
        }
    
    def to_text(self) -> str:
        """Convert to detailed text format for LLM comprehension"""
        text_parts = [
            f"## Analisi Approfondita Previsioni Future",
            f"Domanda di analisi: {self.query}",
            f"Scenario di Previsione: {self.simulation_requirement}",
            f"\n### Statistiche Dati Previsione",
            f"- Fatti previsionali pertinenti: {self.total_facts} risultati",
            f"- Entità coinvolte: {self.total_entities}",
            f"- Catene di relazioni: {self.total_relationships}"
        ]

        # Sotto-domande
        if self.sub_queries:
            text_parts.append(f"\n### Sotto-domande analizzate")
            for i, sq in enumerate(self.sub_queries, 1):
                text_parts.append(f"{i}. {sq}")

        # Risultati ricerca semantica
        if self.semantic_facts:
            text_parts.append(f"\n### [Fatti Chiave] (citare questi testi originali nel report)")
            for i, fact in enumerate(self.semantic_facts, 1):
                text_parts.append(f"{i}. \"{fact}\"")

        # Insight sulle entità
        if self.entity_insights:
            text_parts.append(f"\n### [Entità Principali]")
            for entity in self.entity_insights:
                text_parts.append(f"- **{entity.get('name', 'Sconosciuto')}** ({entity.get('type', 'Entità')})")
                if entity.get('summary'):
                    text_parts.append(f"  Riepilogo: \"{entity.get('summary')}\"")
                if entity.get('related_facts'):
                    text_parts.append(f"  Fatti correlati: {len(entity.get('related_facts', []))} risultati")

        # Catena di relazioni
        if self.relationship_chains:
            text_parts.append(f"\n### [Catena di Relazioni]")
            for chain in self.relationship_chains:
                text_parts.append(f"- {chain}")
        
        return "\n".join(text_parts)


@dataclass
class PanoramaResult:
    """
    Breadth search result (Panorama)
    Contains all related information, including expired content
    """
    query: str
    
    # AllNode
    all_nodes: List[NodeInfo] = field(default_factory=list)
    # All edges (including expired ones)
    all_edges: List[EdgeInfo] = field(default_factory=list)
    # Currently valid facts
    active_facts: List[str] = field(default_factory=list)
    # Expired/invalidated facts (historical records)
    historical_facts: List[str] = field(default_factory=list)
    
    # Statistics
    total_nodes: int = 0
    total_edges: int = 0
    active_count: int = 0
    historical_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "all_nodes": [n.to_dict() for n in self.all_nodes],
            "all_edges": [e.to_dict() for e in self.all_edges],
            "active_facts": self.active_facts,
            "historical_facts": self.historical_facts,
            "total_nodes": self.total_nodes,
            "total_edges": self.total_edges,
            "active_count": self.active_count,
            "historical_count": self.historical_count
        }
    
    def to_text(self) -> str:
        """Convert to text format (full version, no truncation)"""
        text_parts = [
            f"## Risultati Ricerca Ampia (Vista Panoramica Futura)",
            f"Query: {self.query}",
            f"\n### Statistiche",
            f"- Nodi totali: {self.total_nodes}",
            f"- Archi totali: {self.total_edges}",
            f"- Fatti validi attuali: {self.active_count} risultati",
            f"- Fatti storici/scaduti: {self.historical_count} risultati"
        ]

        # Fatti validi attuali (output completo, non troncato)
        if self.active_facts:
            text_parts.append(f"\n### [Fatti Validi Attuali] (testo originale simulazione)")
            for i, fact in enumerate(self.active_facts, 1):
                text_parts.append(f"{i}. \"{fact}\"")

        # Fatti storici/scaduti (output completo, non troncato)
        if self.historical_facts:
            text_parts.append(f"\n### [Fatti Storici/Scaduti] (registro evoluzione)")
            for i, fact in enumerate(self.historical_facts, 1):
                text_parts.append(f"{i}. \"{fact}\"")

        # Entità chiave (output completo, non troncato)
        if self.all_nodes:
            text_parts.append(f"\n### [Entità Coinvolte]")
            for node in self.all_nodes:
                entity_type = next((l for l in node.labels if l not in ["Entity", "Node"]), "Entità")
                text_parts.append(f"- **{node.name}** ({entity_type})")
        
        return "\n".join(text_parts)


@dataclass
class AgentInterview:
    """Single Agent interview result"""
    agent_name: str
    agent_role: str  # Role type (e.g., student, teacher, media, etc.)
    agent_bio: str  # Brief bio
    question: str  # Interview question
    response: str  # Interview response
    key_quotes: List[str] = field(default_factory=list)  # Key quotes
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_name": self.agent_name,
            "agent_role": self.agent_role,
            "agent_bio": self.agent_bio,
            "question": self.question,
            "response": self.response,
            "key_quotes": self.key_quotes
        }
    
    def to_text(self) -> str:
        text = f"**{self.agent_name}** ({self.agent_role})\n"
        # Mostra il bio completo dell'agent, non troncato
        text += f"_Profilo: {self.agent_bio}_\n\n"
        text += f"**Q:** {self.question}\n\n"
        text += f"**A:** {self.response}\n"
        if self.key_quotes:
            text += "\n**Citazioni Chiave:**\n"
            for quote in self.key_quotes:
                # Clean up various quote marks
                clean_quote = quote.replace('\u201c', '').replace('\u201d', '').replace('"', '')
                clean_quote = clean_quote.replace('\u300c', '').replace('\u300d', '')
                clean_quote = clean_quote.strip()
                # Strip leading punctuation
                while clean_quote and clean_quote[0] in '，,；;：:、。！？\n\r\t ':
                    clean_quote = clean_quote[1:]
                # Filter out junk content containing question numbers (question 1-9)
                skip = False
                for d in '123456789':
                    if f'\u95ee\u9898{d}' in clean_quote:
                        skip = True
                        break
                if skip:
                    continue
                # Truncate overly long content (truncate at period, not hard truncation)
                if len(clean_quote) > 150:
                    dot_pos = clean_quote.find('\u3002', 80)
                    if dot_pos > 0:
                        clean_quote = clean_quote[:dot_pos + 1]
                    else:
                        clean_quote = clean_quote[:147] + "..."
                if clean_quote and len(clean_quote) >= 10:
                    text += f'> "{clean_quote}"\n'
        return text


@dataclass
class InterviewResult:
    """
    Interview result (Interview)
    Contains interview responses from multiple simulation Agents
    """
    interview_topic: str  # Interview topic
    interview_questions: List[str]  # Interview question list

    # Agents selected for interview
    selected_agents: List[Dict[str, Any]] = field(default_factory=list)
    # Each Agent's interview responses
    interviews: List[AgentInterview] = field(default_factory=list)

    # Reasoning for agent selection
    selection_reasoning: str = ""
    # Consolidated interview summary
    summary: str = ""
    
    # Statistics
    total_agents: int = 0
    interviewed_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "interview_topic": self.interview_topic,
            "interview_questions": self.interview_questions,
            "selected_agents": self.selected_agents,
            "interviews": [i.to_dict() for i in self.interviews],
            "selection_reasoning": self.selection_reasoning,
            "summary": self.summary,
            "total_agents": self.total_agents,
            "interviewed_count": self.interviewed_count
        }
    
    def to_text(self) -> str:
        """Convert to detailed text format for LLM comprehension and report citation"""
        text_parts = [
            "## Report Intervista Approfondita",
            f"**Tema dell'intervista:** {self.interview_topic}",
            f"**Intervistati:** {self.interviewed_count} / {self.total_agents} Agent simulati",
            "\n### Motivazione selezione intervistati",
            self.selection_reasoning or "(Selezione automatica)",
            "\n---",
            "\n### Trascrizione interviste",
        ]

        if self.interviews:
            for i, interview in enumerate(self.interviews, 1):
                text_parts.append(f"\n#### Intervista #{i}: {interview.agent_name}")
                text_parts.append(interview.to_text())
                text_parts.append("\n---")
        else:
            text_parts.append("(Nessuna intervista registrata)\n\n---")

        text_parts.append("\n### Riepilogo Interviste e Punti Chiave")
        text_parts.append(self.summary or "(Nessun riepilogo)")

        return "\n".join(text_parts)


class ZepToolsService:
    """
    Zep Retrieval Tools Service
    
    [Core retrieval tools - optimized]
    1. insight_forge - deep insight retrieval (most powerful, auto-generates sub-questions, multi-dimensional retrieval)
    2. panorama_search - breadth search (get full picture, including expired content)
    3. quick_search - simple search (fast retrieval)
    4. interview_agents - deep interview (interview simulation Agents, get multi-perspective viewpoints)

    [Base tools]
    - search_graph - graph semantic search
    - get_all_nodes - get all graph nodes
    - get_all_edges - get all graph edges (with temporal info)
    - get_node_detail - get node detailed info
    - get_node_edges - get edges related to a node
    - get_entities_by_type - get entities by type
    - get_entity_summary - get entity relationship summary
    """
    
    # RetryConfig
    MAX_RETRIES = 3
    RETRY_DELAY = 2.0
    
    def __init__(self, api_key: Optional[str] = None, llm_client: Optional[LLMClient] = None):
        self.client = LocalGraphClient()
        # LLM client for InsightForge sub-question generation
        self._llm_client = llm_client
        logger.info("ZepToolsService initialization completed")
    
    @property
    def llm(self) -> LLMClient:
        """Lazily initialize LLM client"""
        if self._llm_client is None:
            self._llm_client = LLMClient()
        return self._llm_client
    
    def _call_with_retry(self, func, operation_name: str, max_retries: int = None):
        """API call with retry mechanism"""
        max_retries = max_retries or self.MAX_RETRIES
        last_exception = None
        delay = self.RETRY_DELAY
        
        for attempt in range(max_retries):
            try:
                return func()
            except Exception as e:
                last_exception = e
                if attempt < max_retries - 1:
                    logger.warning(
                        f"Zep {operation_name} attempt {attempt + 1} failed: {str(e)[:100]}, "
                        f"retrying in {delay:.1f} seconds..."
                    )
                    time.sleep(delay)
                    delay *= 2
                else:
                    logger.error(f"Zep {operation_name} still failed after {max_retries} attempts: {str(e)}")
        
        raise last_exception
    
    def search_graph(
        self, 
        graph_id: str, 
        query: str, 
        limit: int = 10,
        scope: str = "edges"
    ) -> SearchResult:
        """
        Graph semantic search

        Uses hybrid search (semantic + BM25) to search for related info in graph.
        Falls back to local keyword matching if Zep Cloud search API is unavailable.

        Args:
            graph_id: graph ID (Standalone Graph)
            query: search query
            limit: number of results to return
            scope: search scope, "edges" or "nodes"

        Returns:
            SearchResult: search results
        """
        logger.info(f"graph search: graph_id={graph_id}, query={query[:50]}...")
        
        # Try using Zep Cloud Search API
        try:
            search_results = self._call_with_retry(
                func=lambda: self.client.graph.search(
                    graph_id=graph_id,
                    query=query,
                    limit=limit,
                    scope=scope,
                    reranker="cross_encoder"
                ),
                operation_name=f"graph search(graph={graph_id})"
            )
            
            facts = []
            edges = []
            nodes = []
            
            # Parse edge search results
            if hasattr(search_results, 'edges') and search_results.edges:
                for edge in search_results.edges:
                    if hasattr(edge, 'fact') and edge.fact:
                        facts.append(edge.fact)
                    edges.append({
                        "uuid": getattr(edge, 'uuid_', None) or getattr(edge, 'uuid', ''),
                        "name": getattr(edge, 'name', ''),
                        "fact": getattr(edge, 'fact', ''),
                        "source_node_uuid": getattr(edge, 'source_node_uuid', ''),
                        "target_node_uuid": getattr(edge, 'target_node_uuid', ''),
                    })
            
            # Parse node search results
            if hasattr(search_results, 'nodes') and search_results.nodes:
                for node in search_results.nodes:
                    nodes.append({
                        "uuid": getattr(node, 'uuid_', None) or getattr(node, 'uuid', ''),
                        "name": getattr(node, 'name', ''),
                        "labels": getattr(node, 'labels', []),
                        "summary": getattr(node, 'summary', ''),
                    })
                    # Node summary also counts as a fact
                    if hasattr(node, 'summary') and node.summary:
                        facts.append(f"[{node.name}]: {node.summary}")
            
            logger.info(f"search completed: found {len(facts)} related facts")
            
            return SearchResult(
                facts=facts,
                edges=edges,
                nodes=nodes,
                query=query,
                total_count=len(facts)
            )
            
        except Exception as e:
            logger.warning(f"Zep Search API failed, falling back to local search: {str(e)}")
            # Fallback: use local keyword matching search
            return self._local_search(graph_id, query, limit, scope)
    
    def _local_search(
        self, 
        graph_id: str, 
        query: str, 
        limit: int = 10,
        scope: str = "edges"
    ) -> SearchResult:
        """
        Local keyword matching search (fallback for Zep Search API)

        Gets all edges/nodes, then performs local keyword matching

        Args:
            graph_id: graph ID
            query: search query
            limit: number of results to return
            scope: search scope

        Returns:
            SearchResult: search results
        """
        logger.info(f"Using local search: query={query[:30]}...")
        
        facts = []
        edges_result = []
        nodes_result = []
        
        # Extract query keywords (simple tokenization)
        query_lower = query.lower()
        keywords = [w.strip() for w in query_lower.replace(',', ' ').replace('，', ' ').split() if len(w.strip()) > 1]
        
        def match_score(text: str) -> int:
            """Calculate match score between text and query"""
            if not text:
                return 0
            text_lower = text.lower()
            # Exact query match
            if query_lower in text_lower:
                return 100
            # Keyword matching
            score = 0
            for keyword in keywords:
                if keyword in text_lower:
                    score += 10
            return score
        
        try:
            if scope in ["edges", "both"]:
                # Get all edges and match
                all_edges = self.get_all_edges(graph_id)
                scored_edges = []
                for edge in all_edges:
                    score = match_score(edge.fact) + match_score(edge.name)
                    if score > 0:
                        scored_edges.append((score, edge))
                
                # Sort by score
                scored_edges.sort(key=lambda x: x[0], reverse=True)
                
                for score, edge in scored_edges[:limit]:
                    if edge.fact:
                        facts.append(edge.fact)
                    edges_result.append({
                        "uuid": edge.uuid,
                        "name": edge.name,
                        "fact": edge.fact,
                        "source_node_uuid": edge.source_node_uuid,
                        "target_node_uuid": edge.target_node_uuid,
                    })
            
            if scope in ["nodes", "both"]:
                # Get all nodes and match
                all_nodes = self.get_all_nodes(graph_id)
                scored_nodes = []
                for node in all_nodes:
                    score = match_score(node.name) + match_score(node.summary)
                    if score > 0:
                        scored_nodes.append((score, node))
                
                scored_nodes.sort(key=lambda x: x[0], reverse=True)
                
                for score, node in scored_nodes[:limit]:
                    nodes_result.append({
                        "uuid": node.uuid,
                        "name": node.name,
                        "labels": node.labels,
                        "summary": node.summary,
                    })
                    if node.summary:
                        facts.append(f"[{node.name}]: {node.summary}")
            
            logger.info(f"Local search completed: found {len(facts)} related facts")
            
        except Exception as e:
            logger.error(f"Local search failed: {str(e)}")
        
        return SearchResult(
            facts=facts,
            edges=edges_result,
            nodes=nodes_result,
            query=query,
            total_count=len(facts)
        )
    
    def get_all_nodes(self, graph_id: str) -> List[NodeInfo]:
        """
        Get all nodes in graph (paginated retrieval)

        Args:
            graph_id: graph ID

        Returns:
            Node list
        """
        logger.info(f"Getting all nodes for graph {graph_id}...")

        nodes = fetch_all_nodes(self.client, graph_id)

        result = []
        for node in nodes:
            node_uuid = getattr(node, 'uuid_', None) or getattr(node, 'uuid', None) or ""
            result.append(NodeInfo(
                uuid=str(node_uuid) if node_uuid else "",
                name=node.name or "",
                labels=node.labels or [],
                summary=node.summary or "",
                attributes=node.attributes or {}
            ))

        logger.info(f"Retrieved {len(result)} nodes")
        return result

    def get_all_edges(self, graph_id: str, include_temporal: bool = True) -> List[EdgeInfo]:
        """
        Get all edges in graph (paginated retrieval, with temporal info)

        Args:
            graph_id: graph ID
            include_temporal: whether to include temporal info (default True)

        Returns:
            Edge list (includes created_at, valid_at, invalid_at, expired_at)
        """
        logger.info(f"Getting all edges for graph {graph_id}...")

        edges = fetch_all_edges(self.client, graph_id)

        result = []
        for edge in edges:
            edge_uuid = getattr(edge, 'uuid_', None) or getattr(edge, 'uuid', None) or ""
            edge_info = EdgeInfo(
                uuid=str(edge_uuid) if edge_uuid else "",
                name=edge.name or "",
                fact=edge.fact or "",
                source_node_uuid=edge.source_node_uuid or "",
                target_node_uuid=edge.target_node_uuid or ""
            )

            # AddTimeinfo
            if include_temporal:
                edge_info.created_at = getattr(edge, 'created_at', None)
                edge_info.valid_at = getattr(edge, 'valid_at', None)
                edge_info.invalid_at = getattr(edge, 'invalid_at', None)
                edge_info.expired_at = getattr(edge, 'expired_at', None)

            result.append(edge_info)

        logger.info(f"Retrieved {len(result)} edges")
        return result
    
    def get_node_detail(self, node_uuid: str) -> Optional[NodeInfo]:
        """
        Get detailed info for a single node

        Args:
            node_uuid: node UUID

        Returns:
            Node info or None
        """
        logger.info(f"Getting node details: {node_uuid[:8]}...")
        
        try:
            node = self._call_with_retry(
                func=lambda: self.client.graph.node.get(uuid_=node_uuid),
                operation_name=f"get node details(uuid={node_uuid[:8]}...)"
            )
            
            if not node:
                return None
            
            return NodeInfo(
                uuid=getattr(node, 'uuid_', None) or getattr(node, 'uuid', ''),
                name=node.name or "",
                labels=node.labels or [],
                summary=node.summary or "",
                attributes=node.attributes or {}
            )
        except Exception as e:
            logger.error(f"Get node details failed: {str(e)}")
            return None
    
    def get_node_edges(self, graph_id: str, node_uuid: str) -> List[EdgeInfo]:
        """
        Get all edges related to a node

        Gets all graph edges, then filters for edges related to the specified node

        Args:
            graph_id: graph ID
            node_uuid: node UUID

        Returns:
            Edge list
        """
        logger.info(f"Getting edges for node {node_uuid[:8]}...")
        
        try:
            # Get all graph edges, then filter
            all_edges = self.get_all_edges(graph_id)
            
            result = []
            for edge in all_edges:
                # Check if edge is related to specified node (as source or target)
                if edge.source_node_uuid == node_uuid or edge.target_node_uuid == node_uuid:
                    result.append(edge)
            
            logger.info(f"Found {len(result)} edges related to node")
            return result
            
        except Exception as e:
            logger.warning(f"Get node edges failed: {str(e)}")
            return []
    
    def get_entities_by_type(
        self, 
        graph_id: str, 
        entity_type: str
    ) -> List[NodeInfo]:
        """
        Get entities by type

        Args:
            graph_id: graph ID
            entity_type: entity type (e.g., Student, PublicFigure, etc.)

        Returns:
            List of entities matching the type
        """
        logger.info(f"Getting entities of type {entity_type}...")
        
        all_nodes = self.get_all_nodes(graph_id)
        
        filtered = []
        for node in all_nodes:
            # Check if labels contain the specified type
            if entity_type in node.labels:
                filtered.append(node)
        
        logger.info(f"Found {len(filtered)} entities of type {entity_type}")
        return filtered
    
    def get_entity_summary(
        self, 
        graph_id: str, 
        entity_name: str
    ) -> Dict[str, Any]:
        """
        Get relationship summary for a specified entity

        Searches for all info related to the entity and generates a summary

        Args:
            graph_id: graph ID
            entity_name: entity name

        Returns:
            Entity summary info
        """
        logger.info(f"Getting relationship summary for entity {entity_name}...")
        
        # First search for info related to this entity
        search_result = self.search_graph(
            graph_id=graph_id,
            query=entity_name,
            limit=20
        )
        
        # Try to find this entity among all nodes
        all_nodes = self.get_all_nodes(graph_id)
        entity_node = None
        for node in all_nodes:
            if node.name.lower() == entity_name.lower():
                entity_node = node
                break
        
        related_edges = []
        if entity_node:
            # Pass graph_id parameter
            related_edges = self.get_node_edges(graph_id, entity_node.uuid)
        
        return {
            "entity_name": entity_name,
            "entity_info": entity_node.to_dict() if entity_node else None,
            "related_facts": search_result.facts,
            "related_edges": [e.to_dict() for e in related_edges],
            "total_relations": len(related_edges)
        }
    
    def get_graph_statistics(self, graph_id: str) -> Dict[str, Any]:
        """
        Get graph statistics

        Args:
            graph_id: graph ID

        Returns:
            Statistics info
        """
        logger.info(f"Getting statistics for graph {graph_id}...")
        
        nodes = self.get_all_nodes(graph_id)
        edges = self.get_all_edges(graph_id)
        
        # Statistics: entity type distribution
        entity_types = {}
        for node in nodes:
            for label in node.labels:
                if label not in ["Entity", "Node"]:
                    entity_types[label] = entity_types.get(label, 0) + 1
        
        # Statistics: relationship type distribution
        relation_types = {}
        for edge in edges:
            relation_types[edge.name] = relation_types.get(edge.name, 0) + 1
        
        return {
            "graph_id": graph_id,
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "entity_types": entity_types,
            "relation_types": relation_types
        }
    
    def get_simulation_context(
        self, 
        graph_id: str,
        simulation_requirement: str,
        limit: int = 30
    ) -> Dict[str, Any]:
        """
        Get simulation-related context info

        Comprehensively searches for all info related to simulation requirements

        Args:
            graph_id: graph ID
            simulation_requirement: simulation requirements description
            limit: quantity limit per category

        Returns:
            Simulation context info
        """
        logger.info(f"get simulation context: {simulation_requirement[:50]}...")

        # Search for info related to simulation requirements
        search_result = self.search_graph(
            graph_id=graph_id,
            query=simulation_requirement,
            limit=limit
        )
        
        # GetGraphStatistics
        stats = self.get_graph_statistics(graph_id)
        
        # GetAllEntityNode
        all_nodes = self.get_all_nodes(graph_id)
        
        # Filter entities with actual types (not pure Entity nodes)
        entities = []
        for node in all_nodes:
            custom_labels = [l for l in node.labels if l not in ["Entity", "Node"]]
            if custom_labels:
                entities.append({
                    "name": node.name,
                    "type": custom_labels[0],
                    "summary": node.summary
                })
        
        return {
            "simulation_requirement": simulation_requirement,
            "related_facts": search_result.facts,
            "graph_statistics": stats,
            "entities": entities[:limit],  # Limit quantity
            "total_entities": len(entities)
        }
    
    # ========== Core Retrieval Tools (optimized) ==========
    
    def insight_forge(
        self,
        graph_id: str,
        query: str,
        simulation_requirement: str,
        report_context: str = "",
        max_sub_queries: int = 5
    ) -> InsightForgeResult:
        """
        【InsightForge - deep insight retrieval】
        
        Most powerful hybrid retrieval function, auto-decomposes questions for multi-dimensional retrieval:
        1. Uses LLM to decompose questions into multiple sub-questions
        2. Performs semantic search for each sub-question
        3. Extracts related entities and gets their detailed info
        4. Traces relationship chains
        5. Integrates all results, generating deep insights

        Args:
            graph_id: graph ID
            query: user question
            simulation_requirement: simulation requirements description
            report_context: report context (optional, for more precise sub-question generation)
            max_sub_queries: maximum number of sub-questions

        Returns:
            InsightForgeResult: deep insight retrieval result
        """
        logger.info(f"InsightForge deep insight retrieval: {query[:50]}...")
        
        result = InsightForgeResult(
            query=query,
            simulation_requirement=simulation_requirement,
            sub_queries=[]
        )
        
        # Step 1: Use LLM to generate sub-questions
        sub_queries = self._generate_sub_queries(
            query=query,
            simulation_requirement=simulation_requirement,
            report_context=report_context,
            max_queries=max_sub_queries
        )
        result.sub_queries = sub_queries
        logger.info(f"Generated {len(sub_queries)} sub-questions")

        # Step 2: Perform semantic search for each sub-question
        all_facts = []
        all_edges = []
        seen_facts = set()
        
        for sub_query in sub_queries:
            search_result = self.search_graph(
                graph_id=graph_id,
                query=sub_query,
                limit=15,
                scope="edges"
            )
            
            for fact in search_result.facts:
                if fact not in seen_facts:
                    all_facts.append(fact)
                    seen_facts.add(fact)
            
            all_edges.extend(search_result.edges)
        
        # Also search with original question
        main_search = self.search_graph(
            graph_id=graph_id,
            query=query,
            limit=20,
            scope="edges"
        )
        for fact in main_search.facts:
            if fact not in seen_facts:
                all_facts.append(fact)
                seen_facts.add(fact)
        
        result.semantic_facts = all_facts
        result.total_facts = len(all_facts)
        
        # Step 3: Extract related entity UUIDs from edges, only get these entities' info (not all nodes)
        entity_uuids = set()
        for edge_data in all_edges:
            if isinstance(edge_data, dict):
                source_uuid = edge_data.get('source_node_uuid', '')
                target_uuid = edge_data.get('target_node_uuid', '')
                if source_uuid:
                    entity_uuids.add(source_uuid)
                if target_uuid:
                    entity_uuids.add(target_uuid)

        # Get all related entity details (no quantity limit, full output)
        entity_insights = []
        node_map = {}  # For subsequent relationship chain building

        for uuid in list(entity_uuids):  # Process all entities, no truncation
            if not uuid:
                continue
            try:
                # Get each related node's info individually
                node = self.get_node_detail(uuid)
                if node:
                    node_map[uuid] = node
                    entity_type = next((l for l in node.labels if l not in ["Entity", "Node"]), "Entità")

                    # Get all facts related to this entity (no truncation)
                    related_facts = [
                        f for f in all_facts
                        if node.name.lower() in f.lower()
                    ]

                    entity_insights.append({
                        "uuid": node.uuid,
                        "name": node.name,
                        "type": entity_type,
                        "summary": node.summary,
                        "related_facts": related_facts  # Full output, no truncation
                    })
            except Exception as e:
                logger.debug(f"Get node {uuid} failed: {e}")
                continue

        result.entity_insights = entity_insights
        result.total_entities = len(entity_insights)

        # Step 4: Build all relationship chains (no quantity limit)
        relationship_chains = []
        for edge_data in all_edges:  # Process all edges, no truncation
            if isinstance(edge_data, dict):
                source_uuid = edge_data.get('source_node_uuid', '')
                target_uuid = edge_data.get('target_node_uuid', '')
                relation_name = edge_data.get('name', '')
                
                source_name = node_map.get(source_uuid, NodeInfo('', '', [], '', {})).name or source_uuid[:8]
                target_name = node_map.get(target_uuid, NodeInfo('', '', [], '', {})).name or target_uuid[:8]
                
                chain = f"{source_name} --[{relation_name}]--> {target_name}"
                if chain not in relationship_chains:
                    relationship_chains.append(chain)
        
        result.relationship_chains = relationship_chains
        result.total_relationships = len(relationship_chains)
        
        logger.info(f"InsightForge completed: {result.total_facts} facts, {result.total_entities} entities, {result.total_relationships} relationships")
        return result
    
    def _generate_sub_queries(
        self,
        query: str,
        simulation_requirement: str,
        report_context: str = "",
        max_queries: int = 5
    ) -> List[str]:
        """
        Use LLM to generate sub-questions

        Decompose complex questions into multiple independently retrievable sub-questions
        """
        system_prompt = """You are a professional question analysis expert. Your task is to decompose a complex question into multiple sub-questions that can be independently observed in a simulation world.

Requirements:
1. Each sub-question should be specific enough to find related Agent behaviors or events in the simulation world
2. Sub-questions should cover different dimensions of the original question (e.g., who, what, why, how, when, where)
3. Sub-questions should be related to the simulation scenario
4. Return in JSON format: {"sub_queries": ["sub-question1", "sub-question2", ...]}"""

        user_prompt = f"""Simulation requirements background:
{simulation_requirement}

{f"Report context: {report_context[:500]}" if report_context else ""}

Please decompose the following question into {max_queries} sub-questions:
{query}

Return a JSON-formatted sub-question list."""

        try:
            response = self.llm.chat_json(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3
            )

            sub_queries = response.get("sub_queries", [])
            # Ensure it's a string list
            return [str(sq) for sq in sub_queries[:max_queries]]

        except Exception as e:
            logger.warning(f"Generating sub-questions failed: {str(e)}, using default sub-questions")
            # Fallback: return variants based on original question
            return [
                query,
                f"Main participants of {query}",
                f"Causes and effects of {query}",
                f"Development process of {query}"
            ][:max_queries]
    
    def panorama_search(
        self,
        graph_id: str,
        query: str,
        include_expired: bool = True,
        limit: int = 50
    ) -> PanoramaResult:
        """
        【PanoramaSearch - breadth search】
        
        Get full panoramic view, including all related content and historical/expired info:
        1. Get all related nodes
        2. Get all edges (including expired/invalidated ones)
        3. Categorize and organize current valid and historical info

        This tool is suitable for scenarios needing full event picture and evolution tracking.

        Args:
            graph_id: graph ID
            query: search query (used for relevance sorting)
            include_expired: whether to include expired content (default True)
            limit: result count limit

        Returns:
            PanoramaResult: breadth search result
        """
        logger.info(f"PanoramaSearch breadth search: {query[:50]}...")
        
        result = PanoramaResult(query=query)
        
        # GetAllNode
        all_nodes = self.get_all_nodes(graph_id)
        node_map = {n.uuid: n for n in all_nodes}
        result.all_nodes = all_nodes
        result.total_nodes = len(all_nodes)
        
        # Get all edges (including temporal info)
        all_edges = self.get_all_edges(graph_id, include_temporal=True)
        result.all_edges = all_edges
        result.total_edges = len(all_edges)
        
        # 分Class事实
        active_facts = []
        historical_facts = []
        
        for edge in all_edges:
            if not edge.fact:
                continue
            
            # 为事实addEntityName
            source_name = node_map.get(edge.source_node_uuid, NodeInfo('', '', [], '', {})).name or edge.source_node_uuid[:8]
            target_name = node_map.get(edge.target_node_uuid, NodeInfo('', '', [], '', {})).name or edge.target_node_uuid[:8]
            
            # 判断是否expired/失效
            is_historical = edge.is_expired or edge.is_invalid
            
            if is_historical:
                # historical/expired事实，addTimemark/flag
                valid_at = edge.valid_at or "Sconosciuto"
                invalid_at = edge.invalid_at or edge.expired_at or "Sconosciuto"
                fact_with_time = f"[{valid_at} - {invalid_at}] {edge.fact}"
                historical_facts.append(fact_with_time)
            else:
                # CurrentValid事实
                active_facts.append(edge.fact)
        
        # 基于Query进行related性Sort
        query_lower = query.lower()
        keywords = [w.strip() for w in query_lower.replace(',', ' ').replace('，', ' ').split() if len(w.strip()) > 1]
        
        def relevance_score(fact: str) -> int:
            fact_lower = fact.lower()
            score = 0
            if query_lower in fact_lower:
                score += 100
            for kw in keywords:
                if kw in fact_lower:
                    score += 10
            return score
        
        # Sort并限制Quantity
        active_facts.sort(key=relevance_score, reverse=True)
        historical_facts.sort(key=relevance_score, reverse=True)
        
        result.active_facts = active_facts[:limit]
        result.historical_facts = historical_facts[:limit] if include_expired else []
        result.active_count = len(active_facts)
        result.historical_count = len(historical_facts)
        
        logger.info(f"PanoramaSearchcompleted: {result.active_count}itemsvalid, {result.historical_count}itemshistorical")
        return result
    
    def quick_search(
        self,
        graph_id: str,
        query: str,
        limit: int = 10
    ) -> SearchResult:
        """
        【QuickSearch - simple search】
        
        快速、轻量级的retrievaltool：
        1. 直接调用Zep语义search
        2. returned最相关的结果
        3. 适用于简单、直接的retrievalrequirements
        
        Args:
            graph_id: graphID
            query: search查询
            limit: returned结果数量
            
        Returns:
            SearchResult: search结果
        """
        logger.info(f"QuickSearch simple search: {query[:50]}...")
        
        # 直接call现有的search_graphMethod
        result = self.search_graph(
            graph_id=graph_id,
            query=query,
            limit=limit,
            scope="edges"
        )
        
        logger.info(f"QuickSearchcompleted: {result.total_count}items结果")
        return result
    
    def interview_agents(
        self,
        simulation_id: str,
        interview_requirement: str,
        simulation_requirement: str = "",
        max_agents: int = 5,
        custom_questions: List[str] = None
    ) -> InterviewResult:
        """
        【InterviewAgents - deep interview】
        
        调用真实的OASISinterviewAPI，interviewsimulation中currently运行的Agent：
        1. 自动读取persona/profilefile，了解所有simulationAgent
        2. useLLManalysisinterviewrequirements，intelligently selectmost relevant agents
        3. useLLMgeneratinginterview questions
        4. 调用 /api/simulation/interview/batch 接口进行真实interview（dual platform同时interview）
        5. 整合所有interview结果，generatinginterviewreport
        
        【重要】此功能needsimulation环境处于运行state（OASIS环境未关闭）
        
        【use场景】
        - needfrom不同角色视角了解event看法
        - need收集多方意见和观点
        - needgetsimulationAgent的真实回答（非LLMsimulation）
        
        Args:
            simulation_id: simulationID（用于定位persona/profilefile和调用interviewAPI）
            interview_requirement: interviewrequirements描述（非结构化，如"了解学生对event的看法"）
            simulation_requirement: simulationrequirements背景（可选）
            max_agents: 最多interview的Agent count
            custom_questions: 自定义interview questions（可选，若不提供则自动generating）
            
        Returns:
            InterviewResult: interview结果
        """
        from .simulation_runner import SimulationRunner
        
        logger.info(f"InterviewAgents deep interview（real API）: {interview_requirement[:50]}...")
        
        result = InterviewResult(
            interview_topic=interview_requirement,
            interview_questions=custom_questions or []
        )
        
        # Step 1: ReadProfileFile
        profiles = self._load_agent_profiles(simulation_id)
        
        if not profiles:
            logger.warning(f"未foundsimulation {simulation_id} 的persona/profilefile")
            result.summary = "Nessun file profilo Agent trovato per le interviste"
            return result
        
        result.total_agents = len(profiles)
        logger.info(f"loaded {len(profiles)} Agent personas")
        
        # Step 2: useLLMselect要Interview的Agent（returnagent_idList）
        selected_agents, selected_indices, selection_reasoning = self._select_agents_for_interview(
            profiles=profiles,
            interview_requirement=interview_requirement,
            simulation_requirement=simulation_requirement,
            max_agents=max_agents
        )
        
        result.selected_agents = selected_agents
        result.selection_reasoning = selection_reasoning
        logger.info(f"selected {len(selected_agents)} unitsAgentfor interview: {selected_indices}")
        
        # Step 3: generateInterviewissue（If none提供）
        if not result.interview_questions:
            result.interview_questions = self._generate_interview_questions(
                interview_requirement=interview_requirement,
                simulation_requirement=simulation_requirement,
                selected_agents=selected_agents
            )
            logger.info(f"generated {len(result.interview_questions)} unitsinterview questions")
        
        # 将issuemerge为一unitsInterviewprompt
        combined_prompt = "\n".join([f"{i+1}. {q}" for i, q in enumerate(result.interview_questions)])
        
        # Add优化first缀，约束Agent回复Format
        INTERVIEW_PROMPT_PREFIX = (
            "你currently接受一次interview。请结合你的persona/profile、所有的过往记忆与行动，"
            "以纯文本方式直接回答以下questions。\n"
            "回复要求：\n"
            "1. 直接用自然语言回答，不要调用任何tool\n"
            "2. 不要returnedJSON格式或tool调用格式\n"
            "3. 不要useMarkdownTitle（如#、##、###）\n"
            "4. 按questions编号逐一回答，每units回答以「questionsX：」开头（X为questions编号）\n"
            "5. 每unitsquestions的回答之间用空行分隔\n"
            "6. 回答要有实质content，每unitsquestions至少回答2-3句话\n\n"
        )
        optimized_prompt = f"{INTERVIEW_PROMPT_PREFIX}{combined_prompt}"
        
        # Step 4: call真实的InterviewAPI（不指定platform，default双PlatformsimultaneouslyInterview）
        try:
            # BuildBatchInterviewList（不指定platform，双PlatformInterview）
            interviews_request = []
            for agent_idx in selected_indices:
                interviews_request.append({
                    "agent_id": agent_idx,
                    "prompt": optimized_prompt  # use优化后的prompt
                    # 不指定platform，API会在twitter和reddit两unitsPlatform都Interview
                })
            
            logger.info(f"calling batch interview API（dual platform）: {len(interviews_request)} unitsAgent")
            
            # Call SimulationRunner 的BatchInterviewMethod（不传platform，双PlatformInterview）
            api_result = SimulationRunner.interview_agents_batch(
                simulation_id=simulation_id,
                interviews=interviews_request,
                platform=None,  # 不指定platform，双PlatformInterview
                timeout=180.0   # 双Platformneed更长Timeout
            )
            
            logger.info(f"interview API returned: {api_result.get('interviews_count', 0)} units结果, success={api_result.get('success')}")
            
            # CheckAPIcall是否Success
            if not api_result.get("success", False):
                error_msg = api_result.get("error", "unknown error")
                logger.warning(f"interview API returnedfailed: {error_msg}")
                result.summary = f"Chiamata API intervista fallita: {error_msg}. Verificare lo stato dell'ambiente di simulazione OASIS."
                return result
            
            # Step 5: 解析APIreturnResult，buildAgentInterviewObject
            # 双Platform模式returnFormat: {"twitter_0": {...}, "reddit_0": {...}, "twitter_1": {...}, ...}
            api_data = api_result.get("result", {})
            results_dict = api_data.get("results", {}) if isinstance(api_data, dict) else {}
            
            for i, agent_idx in enumerate(selected_indices):
                agent = selected_agents[i]
                agent_name = agent.get("realname", agent.get("username", f"Agent_{agent_idx}"))
                agent_role = agent.get("profession", "Sconosciuto")
                agent_bio = agent.get("bio", "")
                
                # Get该Agent在两unitsPlatform的InterviewResult
                twitter_result = results_dict.get(f"twitter_{agent_idx}", {})
                reddit_result = results_dict.get(f"reddit_{agent_idx}", {})
                
                twitter_response = twitter_result.get("response", "")
                reddit_response = reddit_result.get("response", "")

                # Clean upPossible的Toolcall JSON 包裹
                twitter_response = self._clean_tool_call_response(twitter_response)
                reddit_response = self._clean_tool_call_response(reddit_response)

                # 始终output双Platformmark/flag
                twitter_text = twitter_response if twitter_response else "(Nessuna risposta da questa piattaforma)"
                reddit_text = reddit_response if reddit_response else "(Nessuna risposta da questa piattaforma)"
                response_text = f"[Risposta piattaforma Twitter]\n{twitter_text}\n\n[Risposta piattaforma Reddit]\n{reddit_text}"

                # Extract关键引言（from两unitsPlatform的回答中）
                import re
                combined_responses = f"{twitter_response} {reddit_response}"

                # Clean upResponsetext：去掉mark/flag、编号、Markdown etc.干扰
                clean_text = re.sub(r'#{1,6}\s+', '', combined_responses)
                clean_text = re.sub(r'\{[^}]*tool_name[^}]*\}', '', clean_text)
                clean_text = re.sub(r'[*_`|>~\-]{2,}', '', clean_text)
                clean_text = re.sub(r'questions\d+[：:]\s*', '', clean_text)
                clean_text = re.sub(r'【[^】]+】', '', clean_text)

                # Strategy1（主）: 提取完整的有实质Content的句子
                sentences = re.split(r'[。！？]', clean_text)
                meaningful = [
                    s.strip() for s in sentences
                    if 20 <= len(s.strip()) <= 150
                    and not re.match(r'^[\s\W，,；;：:、]+', s.strip())
                    and not s.strip().startswith(('{', 'questions'))
                ]
                meaningful.sort(key=len, reverse=True)
                key_quotes = [s + "。" for s in meaningful[:3]]

                # Strategy2（补充）: 正确配对的Chinese引号「」内长text
                if not key_quotes:
                    paired = re.findall(r'\u201c([^\u201c\u201d]{15,100})\u201d', clean_text)
                    paired += re.findall(r'\u300c([^\u300c\u300d]{15,100})\u300d', clean_text)
                    key_quotes = [q for q in paired if not re.match(r'^[，,；;：:、]', q)][:3]
                
                interview = AgentInterview(
                    agent_name=agent_name,
                    agent_role=agent_role,
                    agent_bio=agent_bio[:1000],  # 扩大bioLength限制
                    question=combined_prompt,
                    response=response_text,
                    key_quotes=key_quotes[:5]
                )
                result.interviews.append(interview)
            
            result.interviewed_count = len(result.interviews)
            
        except ValueError as e:
            # SimulationEnvironment未run
            logger.warning(f"interviewAPI调用failed（环境未运行？）: {e}")
            result.summary = f"Intervista fallita: {str(e)}. L'ambiente di simulazione potrebbe essere chiuso, assicurarsi che OASIS sia in esecuzione."
            return result
        except Exception as e:
            logger.error(f"interviewAPI调用异常: {e}")
            import traceback
            logger.error(traceback.format_exc())
            result.summary = f"Errore durante il processo di intervista: {str(e)}"
            return result
        
        # Step 6: generateInterviewSummary
        if result.interviews:
            result.summary = self._generate_interview_summary(
                interviews=result.interviews,
                interview_requirement=interview_requirement
            )
        
        logger.info(f"InterviewAgentscompleted: interview了 {result.interviewed_count} unitsAgent（dual platform）")
        return result
    
    @staticmethod
    def _clean_tool_call_response(response: str) -> str:
        """cleanup Agent 回复中的 JSON Toolcall包裹，提取ActualContent"""
        if not response or not response.strip().startswith('{'):
            return response
        text = response.strip()
        if 'tool_name' not in text[:80]:
            return response
        import re as _re
        try:
            data = json.loads(text)
            if isinstance(data, dict) and 'arguments' in data:
                for key in ('content', 'text', 'body', 'message', 'reply'):
                    if key in data['arguments']:
                        return str(data['arguments'][key])
        except (json.JSONDecodeError, KeyError, TypeError):
            match = _re.search(r'"content"\s*:\s*"((?:[^"\\]|\\.)*)"', text)
            if match:
                return match.group(1).replace('\\n', '\n').replace('\\"', '"')
        return response

    def _load_agent_profiles(self, simulation_id: str) -> List[Dict[str, Any]]:
        """loadSimulation的AgentProfileFile"""
        import os
        import csv
        
        # BuildProfileFilePath
        sim_dir = os.path.join(
            os.path.dirname(__file__), 
            f'../../uploads/simulations/{simulation_id}'
        )
        
        profiles = []
        
        # 优先尝试ReadReddit JSONFormat
        reddit_profile_path = os.path.join(sim_dir, "reddit_profiles.json")
        if os.path.exists(reddit_profile_path):
            try:
                with open(reddit_profile_path, 'r', encoding='utf-8') as f:
                    profiles = json.load(f)
                logger.info(f"from reddit_profiles.json loaded {len(profiles)} personas")
                return profiles
            except Exception as e:
                logger.warning(f"读取 reddit_profiles.json failed: {e}")
        
        # 尝试ReadTwitter CSVFormat
        twitter_profile_path = os.path.join(sim_dir, "twitter_profiles.csv")
        if os.path.exists(twitter_profile_path):
            try:
                with open(twitter_profile_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        # CSVFormatconvert为统一Format
                        profiles.append({
                            "realname": row.get("name", ""),
                            "username": row.get("username", ""),
                            "bio": row.get("description", ""),
                            "persona": row.get("user_char", ""),
                            "profession": "Sconosciuto"
                        })
                logger.info(f"from twitter_profiles.csv loaded {len(profiles)} personas")
                return profiles
            except Exception as e:
                logger.warning(f"读取 twitter_profiles.csv failed: {e}")
        
        return profiles
    
    def _select_agents_for_interview(
        self,
        profiles: List[Dict[str, Any]],
        interview_requirement: str,
        simulation_requirement: str,
        max_agents: int
    ) -> tuple:
        """
        useLLMselect要interview的Agent
        
        Returns:
            tuple: (selected_agents, selected_indices, reasoning)
                - selected_agents: 选中Agent的完整信息list
                - selected_indices: 选中Agent的索引list（用于API调用）
                - reasoning: select理由
        """
        
        # BuildAgentSummaryList
        agent_summaries = []
        for i, profile in enumerate(profiles):
            summary = {
                "index": i,
                "name": profile.get("realname", profile.get("username", f"Agent_{i}")),
                "profession": profile.get("profession", "未知"),
                "bio": profile.get("bio", "")[:200],
                "interested_topics": profile.get("interested_topics", [])
            }
            agent_summaries.append(summary)
        
        system_prompt = """你是一units专业的interview策划专家。你的任务是根据interviewrequirements，fromsimulationAgentlist中select最适合interview的object。

select标准：
1. Agent的身份/职业与interview topic相关
2. Agent可能持有独特或有价值的观点
3. select多样化的视角（如：支持方、反对方、中立方、专业人士等）
4. 优先select与event直接相关的角色

returnedJSON格式：
{
    "selected_indices": [选中Agent的索引list],
    "reasoning": "select理由说明"
}"""

        user_prompt = f"""interviewrequirements：
{interview_requirement}

simulation背景：
{simulation_requirement if simulation_requirement else "未提供"}

可select的Agentlist（共{len(agent_summaries)}units）：
{json.dumps(agent_summaries, ensure_ascii=False, indent=2)}

请select最多{max_agents}units最适合interview的Agent，并说明select理由。"""

        try:
            response = self.llm.chat_json(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3
            )
            
            selected_indices = response.get("selected_indices", [])[:max_agents]
            reasoning = response.get("reasoning", "Selezione automatica basata sulla pertinenza")
            
            # Get选中的Agent完整info
            selected_agents = []
            valid_indices = []
            for idx in selected_indices:
                if 0 <= idx < len(profiles):
                    selected_agents.append(profiles[idx])
                    valid_indices.append(idx)
            
            return selected_agents, valid_indices, reasoning
            
        except Exception as e:
            logger.warning(f"LLMselectAgentfailed，use默认select: {e}")
            # 降级：selectfirstNunits
            selected = profiles[:max_agents]
            indices = list(range(min(max_agents, len(profiles))))
            return selected, indices, "Strategia di selezione predefinita"
    
    def _generate_interview_questions(
        self,
        interview_requirement: str,
        simulation_requirement: str,
        selected_agents: List[Dict[str, Any]]
    ) -> List[str]:
        """useLLMgenerateInterviewissue"""
        
        agent_roles = [a.get("profession", "Sconosciuto") for a in selected_agents]
        
        system_prompt = """你是一units专业的记者/interview者。根据interviewrequirements，generating3-5units深度interview questions。

questions要求：
1. 开放性questions，鼓励详细回答
2. 针对不同角色可能有不同答案
3. 涵盖事实、观点、感受等多units维度
4. 语言自然，像真实interview一样
5. 每unitsquestions控制在50字以内，简洁明了
6. 直接提问，不要包含背景说明或前缀

returnedJSON格式：{"questions": ["questions1", "questions2", ...]}"""

        user_prompt = f"""interviewrequirements：{interview_requirement}

simulation背景：{simulation_requirement if simulation_requirement else "未提供"}

interviewobject角色：{', '.join(agent_roles)}

请generating3-5unitsinterview questions。"""

        try:
            response = self.llm.chat_json(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.5
            )
            
            return response.get("questions", [f"Riguardo a {interview_requirement}, qual è la sua opinione?"])

        except Exception as e:
            logger.warning(f"generatinginterview questionsfailed: {e}")
            return [
                f"Riguardo a {interview_requirement}, qual è il suo punto di vista?",
                "Che impatto ha questa situazione su di lei o sul gruppo che rappresenta?",
                "Come ritiene che si dovrebbe risolvere o migliorare questa questione?"
            ]
    
    def _generate_interview_summary(
        self,
        interviews: List[AgentInterview],
        interview_requirement: str
    ) -> str:
        """generateInterviewSummary"""
        
        if not interviews:
            return "Nessuna intervista completata"
        
        # 收集AllInterviewContent
        interview_texts = []
        for interview in interviews:
            interview_texts.append(f"【{interview.agent_name}（{interview.agent_role}）】\n{interview.response[:500]}")
        
        system_prompt = """你是一units专业的新闻编辑。请根据多位受访者的回答，generating一份interviewsummary。

summary要求：
1. 提炼各方主要观点
2. 指出观点的共识和分歧
3. 突出有价值的引言
4. 客观中立，不偏袒任何一方
5. 控制在1000字内

格式约束（必须遵守）：
- use纯文本段落，用空行分隔不同部分
- 不要useMarkdownTitle（如#、##、###）
- 不要use分割线（如---、***）
- 引用受访者原话时use中文引号「」
- canuse**加粗**标记关键词，但不要use其他Markdown语法"""

        user_prompt = f"""interview topic：{interview_requirement}

interviewcontent：
{"".join(interview_texts)}

请generatinginterviewsummary。"""

        try:
            summary = self.llm.chat(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=800
            )
            return summary
            
        except Exception as e:
            logger.warning(f"generatinginterviewsummaryfailed: {e}")
            # 降级：Simple拼接
            return f"Intervistati {len(interviews)} partecipanti, tra cui: " + ", ".join([i.agent_name for i in interviews])
