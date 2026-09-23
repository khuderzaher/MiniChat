# -*- coding: utf-8 -*-
"""
MiniChat v3 — Core Protocols

العقود المعمارية بين مكونات النظام.

هذا الملف يعرّف "كيف تتحدث المكونات مع بعضها"
ولا يحتوي على تنفيذ فعلي للذكاء.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from core.types import (
    Evidence,
    KnowledgeResult,
    LLMResult,
    MemoryResult,
    ReasoningResult,
    Result,
    ToolResult,
)


# ============================================================
# TOOL
# ============================================================

class Tool(ABC):
    """
    أداة deterministic أو متخصصة.

    أمثلة:
        MathTool
        UnitTool
        PracticalTool
    """

    name = "tool"

    @abstractmethod
    def run(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> ToolResult:
        raise NotImplementedError


# ============================================================
# KNOWLEDGE PROVIDER
# ============================================================

class KnowledgeProvider(ABC):
    """
    مزود معرفة.

    مهم:
        المزود لا يصيغ جوابًا للمستخدم.
        يعيد Evidence يمكن للـOrchestrator استخدامها.
    """

    name = "knowledge"

    @abstractmethod
    def search(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        limit: int = 5,
    ) -> KnowledgeResult:
        raise NotImplementedError


# ============================================================
# MEMORY PROVIDER
# ============================================================

class MemoryProvider(ABC):
    """
    مزود ذاكرة المستخدم/الجلسة.

    الذاكرة ليست قاعدة معرفة للعالم.
    """

    name = "memory"

    @abstractmethod
    def search(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        limit: int = 5,
    ) -> MemoryResult:
        raise NotImplementedError

    @abstractmethod
    def store(
        self,
        item: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> Result:
        raise NotImplementedError


# ============================================================
# REASONER
# ============================================================

class Reasoner(ABC):
    """
    محرك استدلال.

    يجب أن يوضح المقدمات والنتيجة والخطوات،
    بدل إعادة نص غامض فقط.
    """

    name = "reasoner"

    @abstractmethod
    def reason(
        self,
        query: str,
        evidence: Optional[list[Evidence]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> ReasoningResult:
        raise NotImplementedError


# ============================================================
# LLM PROVIDER
# ============================================================

class LLMProvider(ABC):
    """
    واجهة النموذج اللغوي.

    Qwen هو تنفيذ محتمل لهذه الواجهة،
    وليس هو المعمارية كلها.
    """

    name = "llm"

    @abstractmethod
    def generate(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> LLMResult:
        raise NotImplementedError


# ============================================================
# VERIFIER
# ============================================================

class Verifier(ABC):
    """
    واجهة التحقق من النتائج.

    يمكن أن تتحقق من:
        - الحساب
        - الأدلة
        - الاتساق
        - التناقضات
        - الافتراضات
    """

    name = "verifier"

    @abstractmethod
    def verify(
        self,
        answer: str,
        evidence: Optional[list[Evidence]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Result:
        raise NotImplementedError
