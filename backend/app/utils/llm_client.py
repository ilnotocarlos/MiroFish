"""
LLM Client Wrapper
Supports LM Studio (OpenAI format) and Anthropic Claude API
"""

import json
import re
from typing import Optional, Dict, Any, List
from openai import OpenAI

try:
    from anthropic import Anthropic
except ImportError:
    Anthropic = None

from ..config import Config


class LLMClient:
    """LLM Client"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None
    ):
        self.provider = Config.LLM_PROVIDER

        if self.provider == 'anthropic':
            if Anthropic is None:
                raise ImportError(
                    "Il pacchetto 'anthropic' non e installato. "
                    "Esegui: pip install anthropic"
                )
            self.anthropic_client = Anthropic(
                api_key=api_key or Config.ANTHROPIC_API_KEY
            )
            self.model = model or Config.ANTHROPIC_MODEL
        else:
            # LM Studio / OpenAI format
            self.api_key = api_key or Config.LLM_API_KEY
            self.base_url = base_url or Config.LLM_BASE_URL
            self.model = model or Config.LLM_MODEL_NAME

            if not self.api_key:
                raise ValueError("LLM_API_KEY not configured")

            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 16384,
        response_format: Optional[Dict] = None
    ) -> str:
        """
        Send a chat request

        Args:
            messages: Message list
            temperature: Temperature parameter
            max_tokens: Maximum token count
            response_format: Response format (e.g., JSON mode)

        Returns:
            Model response text
        """
        if self.provider == 'anthropic':
            # Anthropic: il messaggio system va separato dai messaggi utente
            system_msg = ""
            user_msgs = []
            for m in messages:
                if m["role"] == "system":
                    system_msg = m["content"]
                else:
                    user_msgs.append(m)

            response = self.anthropic_client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_msg,
                messages=user_msgs
            )
            content = response.content[0].text
        else:
            # LM Studio / OpenAI format
            kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }

            # Per LM Studio locale, response_format non è supportato con molti modelli.
            # Tentiamo prima con response_format, se fallisce riprova senza.
            if response_format:
                kwargs["response_format"] = response_format
                try:
                    response = self.client.chat.completions.create(**kwargs)
                except Exception:
                    kwargs.pop("response_format", None)
                    response = self.client.chat.completions.create(**kwargs)
            else:
                response = self.client.chat.completions.create(**kwargs)

            content = response.choices[0].message.content or ""
            # Modelli reasoning (es. Ministral) possono avere content vuoto con reasoning_content
            if not content and hasattr(response.choices[0].message, 'reasoning_content'):
                content = ""

        # Rimuovi tag <think> (modelli come MiniMax M2.5, Qwen thinking)
        content = re.sub(r'<think>[\s\S]*?</think>', '', content).strip()
        return content

    def chat_json(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 8192
    ) -> Dict[str, Any]:
        """
        Send a chat request and return JSON

        Args:
            messages: Message list
            temperature: Temperature parameter
            max_tokens: Maximum token count

        Returns:
            Parsed JSON object
        """
        # Per modelli reasoning: aggiungere istruzione di essere concisi
        optimized_messages = list(messages)
        if optimized_messages and optimized_messages[0]["role"] == "system":
            optimized_messages[0] = {
                "role": "system",
                "content": optimized_messages[0]["content"] + "\n\nIMPORTANT: Be concise. Do not overthink. Output ONLY the requested JSON, nothing else."
            }
        response = self.chat(
            messages=optimized_messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"}
        )
        # Clean up markdown code block markers
        cleaned_response = response.strip()
        cleaned_response = re.sub(r'^```(?:json)?\s*\n?', '', cleaned_response, flags=re.IGNORECASE)
        cleaned_response = re.sub(r'\n?```\s*$', '', cleaned_response)
        cleaned_response = cleaned_response.strip()

        try:
            return json.loads(cleaned_response)
        except json.JSONDecodeError:
            # Tentativo di riparazione JSON troncato (modelli reasoning possono esaurire i token)
            repaired = self._try_repair_json(cleaned_response)
            if repaired is not None:
                return repaired
            raise ValueError(f"Invalid JSON format returned by LLM: {cleaned_response[:500]}...")

    @staticmethod
    def _try_repair_json(text: str):
        """Tenta di riparare un JSON troncato chiudendo parentesi/stringhe mancanti."""
        if not text.strip().startswith('{'):
            return None
        # Tronca all'ultimo valore completo
        # Trova l'ultima chiusura di parentesi quadra o graffa valida
        for end_char in ['}', ']']:
            last_idx = text.rfind(end_char)
            if last_idx > 0:
                candidate = text[:last_idx + 1]
                # Chiudi le parentesi mancanti
                open_braces = candidate.count('{') - candidate.count('}')
                open_brackets = candidate.count('[') - candidate.count(']')
                candidate += ']' * max(0, open_brackets) + '}' * max(0, open_braces)
                try:
                    return json.loads(candidate)
                except json.JSONDecodeError:
                    continue
        # Ultimo tentativo: tronca stringhe aperte e chiudi tutto
        truncated = re.sub(r',\s*"[^"]*$', '', text)  # Rimuovi ultimo campo incompleto
        open_braces = truncated.count('{') - truncated.count('}')
        open_brackets = truncated.count('[') - truncated.count(']')
        truncated += ']' * max(0, open_brackets) + '}' * max(0, open_braces)
        try:
            return json.loads(truncated)
        except json.JSONDecodeError:
            return None
