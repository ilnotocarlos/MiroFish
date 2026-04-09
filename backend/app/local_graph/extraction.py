"""
Entity/relationship extraction using local LLM (Ministral via LM Studio).
Processes text episodes against an ontology schema to extract structured graph data.
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

import requests

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = """You are an entity/relationship extraction system. Given text and an ontology schema, extract entities and relationships.

## Ontology Schema

### Entity Types:
{entity_types}

### Relationship Types:
{edge_types}

## Text to Analyze:
{text}

## Instructions
1. Extract all entities mentioned in the text. For each entity, assign the most specific matching entity type from the schema as the label. If no specific type matches, use "Entity".
2. Extract all relationships between entities. Use the relationship type names from the schema.
3. For each entity, provide a brief summary and any relevant attributes from the schema.
4. For each relationship, describe the factual connection as a complete sentence.

Output ONLY valid JSON with no additional text:
{{
  "entities": [
    {{"name": "Entity Name", "type": "EntityType", "summary": "Brief description", "attributes": {{}}}}
  ],
  "relationships": [
    {{"name": "RELATIONSHIP_TYPE", "fact": "Entity A has relationship with Entity B because...", "source": "Source Entity Name", "target": "Target Entity Name", "attributes": {{}}}}
  ]
}}"""


class EntityExtractor:
    def __init__(self, lm_studio_url: str = "http://localhost:1234/v1",
                 model: str = None):
        self.url = f"{lm_studio_url}/chat/completions"
        self.model = model  # Will be resolved from config if None

    def extract(self, text: str, ontology: Dict) -> Tuple[List[Dict], List[Dict]]:
        """
        Extract entities and relationships from text using ontology schema.

        Returns: (entities, relationships) where each is a list of dicts.
        """
        if not text or not text.strip():
            return [], []

        entity_types_desc = self._format_entity_types(ontology.get("entity_types", {}))
        edge_types_desc = self._format_edge_types(ontology.get("edge_types", {}))

        prompt = EXTRACTION_PROMPT.format(
            entity_types=entity_types_desc,
            edge_types=edge_types_desc,
            text=text[:6000]  # Truncate to fit context
        )

        try:
            resp = requests.post(self.url, json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "You are a precise entity/relationship extraction system. Output only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.1,
                "max_tokens": 4096
            }, timeout=120)
            resp.raise_for_status()

            content = resp.json()["choices"][0]["message"].get("content", "")
            # Strip thinking tags from reasoning models
            content = re.sub(r'<think>[\s\S]*?</think>', '', content).strip()

            return self._parse_extraction(content)

        except Exception as e:
            logger.error(f"Entity extraction failed: {e}")
            return [], []

    def _parse_extraction(self, content: str) -> Tuple[List[Dict], List[Dict]]:
        """Parse LLM output into entities and relationships."""
        # Clean markdown code blocks
        cleaned = content.strip()
        cleaned = re.sub(r'^```(?:json)?\s*\n?', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\n?```\s*$', '', cleaned)
        cleaned = cleaned.strip()

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            # Try to find JSON in the content
            match = re.search(r'\{[\s\S]*\}', cleaned)
            if match:
                try:
                    data = json.loads(match.group())
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse extraction JSON: {cleaned[:200]}")
                    return [], []
            else:
                logger.error(f"No JSON found in extraction output: {cleaned[:200]}")
                return [], []

        entities = data.get("entities", [])
        relationships = data.get("relationships", [])

        # Validate and clean entities
        valid_entities = []
        for e in entities:
            if isinstance(e, dict) and e.get("name"):
                valid_entities.append({
                    "name": str(e["name"]).strip(),
                    "type": str(e.get("type", "Entity")).strip(),
                    "summary": str(e.get("summary", "")).strip(),
                    "attributes": e.get("attributes", {}) if isinstance(e.get("attributes"), dict) else {}
                })

        # Validate and clean relationships
        valid_rels = []
        for r in relationships:
            if isinstance(r, dict) and r.get("source") and r.get("target"):
                valid_rels.append({
                    "name": str(r.get("name", "RELATED_TO")).strip(),
                    "fact": str(r.get("fact", "")).strip(),
                    "source": str(r["source"]).strip(),
                    "target": str(r["target"]).strip(),
                    "attributes": r.get("attributes", {}) if isinstance(r.get("attributes"), dict) else {}
                })

        return valid_entities, valid_rels

    def _format_entity_types(self, entity_types: Dict) -> str:
        """Format entity types for the prompt."""
        if not entity_types:
            return "No specific entity types defined. Use generic 'Entity' type."
        lines = []
        for name, info in entity_types.items():
            desc = info.get("description", "")
            attrs = info.get("attributes", [])
            attrs_str = ", ".join(a.get("name", "") for a in attrs) if attrs else "none"
            lines.append(f"- {name}: {desc} (attributes: {attrs_str})")
        return "\n".join(lines)

    def _format_edge_types(self, edge_types: Dict) -> str:
        """Format edge types for the prompt."""
        if not edge_types:
            return "No specific relationship types defined. Use generic 'RELATED_TO' type."
        lines = []
        for name, info in edge_types.items():
            desc = info.get("description", "")
            sources = info.get("source_targets", [])
            st_str = ", ".join(f"{s.get('source','?')}→{s.get('target','?')}" for s in sources) if sources else "any→any"
            lines.append(f"- {name}: {desc} ({st_str})")
        return "\n".join(lines)
