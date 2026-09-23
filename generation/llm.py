from __future__ import annotations

import time
from typing import Optional

from core.protocols import LLMProvider
from core.types import LLMResult, Status
from llm_bridge import ask, is_server_up


class LocalQwenProvider(LLMProvider):
    """واجهة v3 للنموذج المحلي عبر llama-server."""

    name = "local-qwen"

    def __init__(
        self,
        default_max_tokens: int = 300,
        default_temperature: float = 0.6,
        default_timeout: int = 180,
    ):
        self.default_max_tokens = default_max_tokens
        self.default_temperature = default_temperature
        self.default_timeout = default_timeout

    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        context: Optional[dict] = None,
    ) -> LLMResult:
        if not isinstance(prompt, str) or not prompt.strip():
            return LLMResult(
                status=Status.INVALID_INPUT,
                text=None,
                model=self.name,
                metadata={"reason": "empty_prompt"},
            )

        started = time.perf_counter()

        try:
            if not is_server_up(timeout=3):
                return LLMResult(
                    status=Status.UNAVAILABLE,
                    text=None,
                    model=self.name,
                    metadata={"reason": "llama_server_unavailable"},
                )

            text = ask(
                system=system or "",
                user=prompt,
                max_tokens=self.default_max_tokens,
                temperature=self.default_temperature,
                timeout=self.default_timeout,
            )

            latency_ms = (time.perf_counter() - started) * 1000

            if not text:
                return LLMResult(
                    status=Status.EMPTY,
                    text=None,
                    model=self.name,
                    latency_ms=latency_ms,
                    metadata={"reason": "empty_model_response"},
                )

            return LLMResult(
                status=Status.SUCCESS,
                text=text,
                model=self.name,
                latency_ms=latency_ms,
                metadata={
                    "provider": self.name,
                    "backend": "llama-server",
                },
            )

        except Exception as exc:
            latency_ms = (time.perf_counter() - started) * 1000

            return LLMResult(
                status=Status.ERROR,
                text=None,
                model=self.name,
                latency_ms=latency_ms,
                metadata={
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                },
            )
