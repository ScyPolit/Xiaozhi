from __future__ import annotations

import json
import logging
from typing import Any, AsyncIterator

import httpx

from .config import Config

LOGGER = logging.getLogger(__name__)


class OpenClawClient:
    def __init__(self, config: Config):
        self._config = config
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=4.0), trust_env=False)

    async def close(self) -> None:
        await self._client.aclose()

    async def chat(self, user_text: str, history: list[dict[str, str]] | None = None) -> AsyncIterator[str]:
        url = f"{self._config.openclaw_base_url}/chat/completions"
        headers = {"Authorization": f"Bearer {self._config.openclaw_api_key}", "Content-Type": "application/json"}
        messages: list[dict[str, Any]] = [{"role": "system", "content": self._config.system_prompt}]
        messages.extend((history or [])[-8:])
        messages.append({"role": "user", "content": user_text})
        payload = {
            "model": self._config.openclaw_model,
            "messages": messages,
            "stream": True,
            "max_tokens": self._config.max_output_tokens,
            "reasoning_effort": self._config.reasoning_effort,
            "temperature": 0.35,
        }
        emitted = 0
        try:
            async with self._client.stream("POST", url, headers=headers, json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    text = self._parse_stream_line(line)
                    if not text:
                        continue
                    remaining = self._config.max_reply_chars - emitted
                    if remaining <= 0:
                        break
                    text = text[:remaining]
                    emitted += len(text)
                    yield text
                return
        except Exception as exc:
            if emitted:
                LOGGER.warning("stream ended after partial response: %s", exc)
                return
            LOGGER.warning("streaming request failed, retrying once: %s", exc)
        payload["stream"] = False
        response = await self._client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        content = response.json().get("choices", [{}])[0].get("message", {}).get("content", "")
        if content:
            yield content[: self._config.max_reply_chars]

    @staticmethod
    def _parse_stream_line(line: str) -> str:
        line = line.strip()
        if not line or line == "data: [DONE]":
            return ""
        if line.startswith("data:"):
            line = line[5:].strip()
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            return ""
        choices = data.get("choices") or []
        if not choices:
            return ""
        delta = choices[0].get("delta") or {}
        return delta.get("content") or choices[0].get("text") or ""
