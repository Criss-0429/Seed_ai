"""Client LLM OpenAI-compatible: un solo client per OpenRouter / Vercel AI Gateway /
Ollama — cambia solo base_url+key+model nel config, mai il codice.

Tutto il testo in uscita DEVE essere gia' passato dal privacy gate:
questo modulo non redige, rifiuta di partire se il chiamante non lo dichiara.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

import requests

log = logging.getLogger("seed.llm")


@dataclass
class LLMResponse:
    text: str = ""
    tool_calls: list[dict] = field(default_factory=list)
    usage: dict = field(default_factory=dict)
    raw: dict = field(default_factory=dict)


def parse_json_object(text: str) -> dict[str, Any]:
    """Parse a JSON object, tolerating provider-added Markdown fences/prose."""
    if not isinstance(text, str) or not text.strip():
        raise json.JSONDecodeError("empty JSON response", "", 0)
    candidate = text.strip()
    if candidate.startswith("```"):
        lines = candidate.splitlines()
        if lines and lines[0].strip().lower() in {"```", "```json"}:
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        candidate = "\n".join(lines).strip()
    try:
        data = json.loads(candidate)
    except json.JSONDecodeError:
        start = candidate.find("{")
        if start < 0:
            raise
        data, _ = json.JSONDecoder().raw_decode(candidate[start:])
    if not isinstance(data, dict):
        raise json.JSONDecodeError("JSON response must be an object", candidate, 0)
    return data


class LLMClient:
    def __init__(self, base_url: str, api_key: str, default_model: str,
                 max_tokens: int = 2048, timeout: int = 120):
        if not base_url:
            raise ValueError("llm.base_url non configurato (config.json)")
        self.base_url = base_url.rstrip("/")
        self._api_key = api_key
        self.default_model = default_model
        self.max_tokens = max_tokens
        self.timeout = timeout

    @property
    def configured(self) -> bool:
        return bool(self._api_key and self.default_model)

    @property
    def has_key(self) -> bool:
        """Solo presenza credenziale, senza vincolo sul default_model.
        Usato dal ModelRouter (S10): il modello arriva dal ruolo, non dal default."""
        return bool(self._api_key)

    def chat(self, messages: list[dict], *, model: str | None = None,
             tools: list[dict] | None = None, redacted: bool = False,
             temperature: float = 0.7, response_json: bool = False) -> LLMResponse:
        """`redacted=True` e' la dichiarazione del chiamante che il contenuto
        e' passato dal privacy gate. Senza, il client rifiuta."""
        if not redacted:
            raise PermissionError("LLMClient: contenuto non dichiarato redatto — passare dal privacy gate")
        if not self.configured:
            raise RuntimeError("API key o modello mancanti: compila config.json")

        body: dict[str, Any] = {
            "model": model or self.default_model,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": temperature,
        }
        if tools:
            body["tools"] = tools
            body["tool_choice"] = "auto"
        if response_json:
            body["response_format"] = {"type": "json_object"}

        resp = requests.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self._api_key}",
                     "Content-Type": "application/json"},
            json=body, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()

        choice = (data.get("choices") or [{}])[0]
        msg = choice.get("message", {})
        out = LLMResponse(
            text=msg.get("content") or "",
            usage=data.get("usage", {}),
            raw=data,
        )
        for tc in msg.get("tool_calls") or []:
            fn = tc.get("function", {})
            try:
                args = json.loads(fn.get("arguments") or "{}")
            except json.JSONDecodeError:
                args = {}
            out.tool_calls.append({"id": tc.get("id"), "name": fn.get("name"), "arguments": args})
        return out
