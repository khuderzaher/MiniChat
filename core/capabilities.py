# -*- coding: utf-8 -*-
"""
MiniChat v3 — Capability Analysis Layer

فصل صريح بين:
    intent detection   (أي قدرة *مرشَّحة*؟)
    argument extraction (استخراج الوسائط الحتمية)
    solver probing     (هل تستطيع القدرة الحل *فعليًا*؟)

القاعدة الحاكمة:
    LLM هو آخر خيار، ويُستخدم فقط عندما لا توجد قدرة
    deterministic قادرة على حل السؤال.

الـPlanner لا يعرف تفاصيل FormalReasoner الداخلية:
كل ما يملكه قائمة capabilities قابلة للتوسعة، وكل
capability تجيب عن can_solve() بنفسها.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from core.types import CapabilityDecision


class Capability:
    """عقد عام لقدرة حل واحدة."""

    name: str = "capability"

    def probe(self, query: str, analysis: Dict[str, Any]) -> CapabilityDecision:
        raise NotImplementedError


# ------------------------------------------------------------
# Math
# ------------------------------------------------------------

class MathCapability(Capability):
    """
    يكشف الأسئلة التي يستطيع MathTool حلها حتميًا:
      - تعبيرات حسابية (25 × 4)
      - predicates رياضية ذات وسيط صحيح واحد
        (هل 17 عدد أولي؟ / هل 49 مربع كامل؟)

    الفصل المطلوب:
      intent detection هنا،
      argument extraction هنا أيضًا لكن بصيغة مهيكلَة،
      solver الحقيقي في MathTool،
      verification في طبقة التحقق.
    """

    name = "math"

    _INTEGER_WORD_PATTERNS = {
        "prime": (
            "أولي",
            "اولي",
            "أولية",
            "اولية",
            "أوليا",
        ),
        "perfect_square": (
            "مربع كامل",
        ),
        "even": ("زوجي", "شفعي"),
        "odd": ("فردي", "وتري"),
    }

    _NUMBER = re.compile(r"(\d+)")

    def extract(self, query: str) -> Optional[Dict[str, Any]]:
        text = query.strip()

        if not text:
            return None

        # 1) arithmetic expression?
        from tools.math import MathTool

        expression = MathTool._extract_expression(text)

        if expression is not None:
            return {"kind": "expression", "expression": expression}

        # 2) numeric predicate question?
        numbers = self._NUMBER.findall(text)

        if len(numbers) != 1:
            return None

        number = int(numbers[0])

        for predicate, words in self._INTEGER_WORD_PATTERNS.items():
            for word in words:
                if word in text:
                    return {
                        "kind": "predicate",
                        "predicate": predicate,
                        "number": number,
                    }

        return None

    def probe(self, query: str, analysis: Dict[str, Any]) -> CapabilityDecision:
        extracted = self.extract(query)

        if extracted is None:
            return CapabilityDecision(
                capability=self.name,
                can_solve=False,
                reason="no_math_structure",
            )

        # Deterministic executability check without invoking the
        # full solver pipeline: predicate math is always solvable,
        # expressions are solvable iff MathEngine evaluates them.
        if extracted["kind"] == "predicate":
            from math_engine import MathEngine

            number = extracted["number"]
            predicate = extracted["predicate"]

            try:
                answer = MathEngine.integer_predicate(predicate, number)
            except ValueError:
                return CapabilityDecision(
                    capability=self.name,
                    can_solve=False,
                    reason=f"unknown_math_predicate:{predicate}",
                )

            return CapabilityDecision(
                capability=self.name,
                can_solve=True,
                reason="deterministic_integer_predicate",
                payload={**extracted, "answer": bool(answer)},
            )

        return CapabilityDecision(
            capability=self.name,
            can_solve=True,
            reason="deterministic_arithmetic_expression",
            payload=extracted,
        )


# ------------------------------------------------------------
# Reasoning
# ------------------------------------------------------------

class ReasoningCapability(Capability):
    """
    يسأل ArabicQueryCompiler فعليًا: هل يمكن ترجمة السؤال إلى
    نموذج منطقي canonical مدعوم؟

    لا يعرف شيئًا عن خوارزمية الاستدلال الداخلية؛ يفحص فقط
    أن الترجمة مدعومة وأن goal موجود.
    """

    name = "reasoning"

    def probe(self, query: str, analysis: Dict[str, Any]) -> CapabilityDecision:

        from reasoning.language import ArabicQueryCompiler

        compiled = ArabicQueryCompiler().compile(query)

        if not compiled.supported:
            return CapabilityDecision(
                capability=self.name,
                can_solve=False,
                reason=compiled.reason or "unsupported_logical_form",
            )

        if compiled.goal is None:
            return CapabilityDecision(
                capability=self.name,
                can_solve=False,
                reason="missing_goal",
            )

        if not compiled.facts and not compiled.variable_rules:
            return CapabilityDecision(
                capability=self.name,
                can_solve=False,
                reason="no_premises",
            )

        return CapabilityDecision(
            capability=self.name,
            can_solve=True,
            reason="supported_canonical_logical_form",
            payload={
                "facts": [str(fact) for fact in compiled.facts],
                "variable_rules": list(compiled.variable_rules),
                "goal": compiled.goal,
            },
        )


# ------------------------------------------------------------
# Knowledge
# ------------------------------------------------------------

class KnowledgeCapability(Capability):
    """
    مرشح استعلامي بحت: لا يبحث في قواعد البيانات ولا يستدعي
    الـproviders (هذا حق الـPipeline)، لكنه يمنع توجيه أسئلة
    الرياضيات/المنطق الصريحة إلى المعرفة.
    """

    name = "knowledge"

    _KNOWLEDGE_TYPES = {
        "define",
        "who",
        "where",
        "when",
        "what",
        "list",
        "classify",
        "relation",
        "general",
    }

    def probe(self, query: str, analysis: Dict[str, Any]) -> CapabilityDecision:

        question_type = str(analysis.get("question_type") or "general")
        contexts = set(analysis.get("contexts") or [])

        # سؤال رياضي أو منطقي صريح ليس سؤال معرفة.
        if contexts.intersection({"math"}) or question_type == "how_many":
            return CapabilityDecision(
                capability=self.name,
                can_solve=False,
                reason="not_a_knowledge_question",
            )

        if question_type in self._KNOWLEDGE_TYPES or contexts:
            return CapabilityDecision(
                capability=self.name,
                can_solve=True,
                reason="knowledge_eligible",
                payload={"attempt_providers": True},
            )

        return CapabilityDecision(
            capability=self.name,
            can_solve=False,
            reason="no_knowledge_signal",
        )


# ------------------------------------------------------------
# LLM (last resort only)
# ------------------------------------------------------------

class LLMCapability(Capability):
    """LLM متاح دائمًا كـfallback لكنه لا يتصدر أي قرار."""

    name = "llm"

    def probe(self, query: str, analysis: Dict[str, Any]) -> CapabilityDecision:
        return CapabilityDecision(
            capability=self.name,
            can_solve=True,
            reason="fallback_only",
        )


class CapabilityAnalyzer:
    """
    مجموعة capabilities قابلة للتوسعة بترتيب تفضيل ثابت:
    قدرات deterministic أولًا، ثم knowledge، وLLM أخيرًا.
    """

    DEFAULT_ORDER = (
        MathCapability(),
        ReasoningCapability(),
        KnowledgeCapability(),
        LLMCapability(),
    )

    def __init__(self, capabilities: Optional[List[Capability]] = None):
        self.capabilities = list(
            capabilities if capabilities is not None
            else self.DEFAULT_ORDER
        )

    def analyze(
        self,
        query: str,
        analysis: Dict[str, Any],
    ) -> List[CapabilityDecision]:

        decisions: List[CapabilityDecision] = []

        for capability in self.capabilities:
            decisions.append(capability.probe(query, analysis))

        return decisions

    def primary(
        self,
        query: str,
        analysis: Dict[str, Any],
    ) -> Optional[CapabilityDecision]:
        """أول قدرة قادرة فعليًا على الحل (LLM مستثنى)."""

        for decision in self.analyze(query, analysis):
            if decision.can_solve and decision.capability != "llm":
                return decision

        return None
