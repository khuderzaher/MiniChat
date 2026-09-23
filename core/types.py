# -*- coding: utf-8 -*-
"""
MiniChat v3 — Core Types
العقود المشتركة بين مكونات النظام.

هذا الملف لا ينفذ ذكاءً بحد ذاته.
وظيفته توحيد شكل البيانات بين الطبقات.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


# ============================================================
# STATUS
# ============================================================

class Status(str, Enum):
    SUCCESS = "success"
    EMPTY = "empty"
    UNAVAILABLE = "unavailable"
    INVALID_INPUT = "invalid_input"
    TIMEOUT = "timeout"
    ERROR = "error"


class Decision(str, Enum):
    """
    القرار التنفيذي النهائي لمسار الـPipeline.

    لا يحدد صحة الجواب؛ يحدد فقط المسار الذي اتُّخذ.
    """

    DIRECT = "direct"
    RAG = "rag"
    LLM = "llm"
    EMPTY = "empty"
    UNAVAILABLE = "unavailable"


# ============================================================
# GENERIC RESULT
# ============================================================

@dataclass
class Result:
    """
    النتيجة العامة لأي خدمة.

    لا نستخدم None لتمييز كل أنواع الفشل.
    يجب أن يكون سبب النتيجة واضحًا.
    """

    status: Status
    value: Any = None
    message: Optional[str] = None
    source: Optional[str] = None
    confidence: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.status == Status.SUCCESS


# ============================================================
# EVIDENCE
# ============================================================

@dataclass
class Evidence:
    """
    قطعة معلومة استُخدمت كدليل.

    content:
        النص/المعلومة نفسها.

    source:
        المصدر الداخلي الذي جاءت منه.

    source_type:
        نوع المصدر مثل:
        faq / syria / arabic_lexicon / user_memory / tool

    reliability:
        موثوقية المصدر، وليست درجة تشابه البحث.

    score:
        درجة ملاءمة هذه القطعة للسؤال الحالي.

    metadata:
        معلومات إضافية مثل id أو version أو timestamp.
    """

    content: str
    source: str
    source_type: str

    reliability: Optional[float] = None
    score: Optional[float] = None

    metadata: Dict[str, Any] = field(default_factory=dict)


# ============================================================
# TASK PLAN
# ============================================================

@dataclass
class TaskPlan:
    """
    خطة تنفيذ السؤال.

    الـOrchestrator هو الذي ينشئها.
    """

    mode: str = "direct"

    domain: Optional[str] = None
    intent: Optional[str] = None

    needs_knowledge: bool = False
    needs_reasoning: bool = False
    needs_math: bool = False
    needs_memory: bool = False
    needs_llm: bool = True
    needs_verification: bool = False

    providers: List[str] = field(default_factory=list)
    tools: List[str] = field(default_factory=list)

    metadata: Dict[str, Any] = field(default_factory=dict)


# ============================================================
# REASONING RESULT
# ============================================================

@dataclass
class ReasoningResult:
    """
    نتيجة الاستدلال.

    valid:
        هل الاستدلال نفسه صالح؟

    conclusion:
        النتيجة التي تم الوصول إليها.

    premises:
        المقدمات التي بُني عليها الاستنتاج.

    evidence:
        الأدلة المستخدمة.

    steps:
        خطوات الاستدلال المختصرة.
    """

    valid: bool

    conclusion: Optional[str] = None

    premises: List[str] = field(default_factory=list)
    evidence: List[Evidence] = field(default_factory=list)
    steps: List[str] = field(default_factory=list)

    confidence: Optional[float] = None

    metadata: Dict[str, Any] = field(default_factory=dict)


# ============================================================
# VERIFICATION RESULT
# ============================================================

@dataclass
class VerificationResult:
    """
    نتيجة التحقق من جواب أو نتيجة.

    verified:
        هل تم التحقق بنجاح؟

    checks:
        قائمة بالفحوصات التي أُجريت.

    issues:
        المشاكل التي اكتُشفت.

    corrections:
        التصحيحات المقترحة.
    """

    verified: bool

    checks: List[str] = field(default_factory=list)
    issues: List[str] = field(default_factory=list)
    corrections: List[str] = field(default_factory=list)

    confidence: Optional[float] = None

    metadata: Dict[str, Any] = field(default_factory=dict)


# ============================================================
# LLM RESULT
# ============================================================

@dataclass
class LLMResult:
    """
    نتيجة الاتصال بالنموذج اللغوي.

    لا نعيد نصًا فقط.
    نريد معرفة حالة الطلب ومعلومات التنفيذ.
    """

    status: Status

    text: Optional[str] = None

    model: Optional[str] = None

    latency_ms: Optional[float] = None

    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None

    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.status == Status.SUCCESS


# ============================================================
# MEMORY RESULT
# ============================================================

@dataclass
class MemoryResult:
    """
    نتيجة استرجاع الذاكرة.
    """

    found: bool

    items: List[Dict[str, Any]] = field(default_factory=list)

    memory_type: Optional[str] = None

    confidence: Optional[float] = None

    metadata: Dict[str, Any] = field(default_factory=dict)


# ============================================================
# KNOWLEDGE RESULT
# ============================================================

@dataclass
class KnowledgeResult:
    """
    نتيجة البحث في قاعدة/مزود معرفة.

    لا يعيد جوابًا مصاغًا.
    يعيد Evidence.
    """

    found: bool

    evidence: List[Evidence] = field(default_factory=list)

    query: Optional[str] = None

    metadata: Dict[str, Any] = field(default_factory=dict)


# ============================================================
# TOOL RESULT
# ============================================================

@dataclass
class ToolResult:
    """
    نتيجة أداة deterministic أو خارجية.
    """

    success: bool

    tool: str

    value: Any = None

    formatted: Optional[str] = None

    error: Optional[str] = None

    metadata: Dict[str, Any] = field(default_factory=dict)
