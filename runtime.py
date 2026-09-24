# -*- coding: utf-8 -*-
"""
MiniChat v3 — Runtime / Composition Root

مسؤول عن تركيب مكونات النظام فقط.

لا يحتوي على منطق الإجابة.
لا يحتوي على قواعد معرفة.
لا يحتوي على منطق رياضيات.
"""

from __future__ import annotations

from typing import Optional, Dict, Any

from core.orchestrator import Orchestrator
from main import StructuredDB
from knowledge.providers.general import GeneralKnowledgeProvider
from tools.math import MathTool
from generation.llm import LocalQwenProvider
from reasoning.engine import FormalReasoner
from reasoning.storage import ReasoningStore
from core.verification import DefaultVerifier


class MiniChatRuntime:
    name = "minichat-v3-runtime"

    def __init__(self, db: Optional[StructuredDB] = None) -> None:
        self.db = db or StructuredDB()

        self.orchestrator = Orchestrator()

        # Tools
        self.orchestrator.pipeline.register(
            "math",
            MathTool(),
        )

        # Knowledge Providers
        self.orchestrator.pipeline.register(
            "general",
            GeneralKnowledgeProvider(self.db),
        )

        # LLM
        self.orchestrator.pipeline.register(
            "llm",
            LocalQwenProvider(),
        )

        # Reasoning
        self.orchestrator.pipeline.register(
            "reasoner",
            FormalReasoner(
                store=ReasoningStore(),
            ),
        )

        # Verification (deterministic; never an LLM)
        self.orchestrator.pipeline.register(
            "verifier",
            DefaultVerifier(),
        )

    def handle(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
    ):
        return self.orchestrator.handle(
            query,
            context=context,
        )
