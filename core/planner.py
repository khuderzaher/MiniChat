# -*- coding: utf-8 -*-
"""
MiniChat v3 — Planner

يحوّل تحليل السؤال إلى خطة تنفيذ.

الـPlanner لا يجيب على السؤال.
ولا يستدعي Qwen.
ولا يبحث في قواعد البيانات.

وظيفته الوحيدة:
    تحديد ما الذي يحتاجه السؤال.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional

from core.types import CapabilityDecision, TaskPlan
from core.capabilities import CapabilityAnalyzer


class Planner:
    """
    مخطط التنفيذ المركزي.

    مسؤول عن اختيار المسارات المطلوبة،
    وليس تنفيذها.
    """

    name = "planner"

    def __init__(self, analyzer: Optional[CapabilityAnalyzer] = None):
        # The planner only *decides which capabilities are needed*.
        # Whether a capability can actually solve the question is
        # answered by the capability itself (can_solve), and final
        # executability is re-checked at execution time.
        self.analyzer = analyzer or CapabilityAnalyzer()

    @staticmethod
    def _looks_like_math(query: str) -> bool:
        """
        كشف محافظ عن وجود عملية رياضية صريحة.

        لا يحاول فهم اللغة العربية كاملة.
        فقط يبحث عن بنية رياضية واضحة.
        """

        text = query.strip()

        if not text:
            return False

        # معادلة تحتوي على = ومتغير رياضي.
        if "=" in text and re.search(r"\d\s*[a-zA-Z]\b|\b[a-zA-Z]\s*[\+\-\*/]", text):
            return True

        # رموز العمليات الرياضية مع أرقام على الجانبين.
        if re.search(
            r"\d\s*(?:[+\-*/×÷%^])\s*-?\d",
            text,
        ):
            return True

        # عمليات عربية صريحة + أرقام.
        arithmetic_words = (
            "احسب",
            "ناتج",
            "يساوي",
            "أوجد",
            "اوجد",
            "احسبلي",
            "احسب لي",
        )

        if any(word in text for word in arithmetic_words):
            if re.search(r"\d", text):
                return True

        # معادلات لفظية واضحة.
        if re.search(r"(حل|حلّ)\s+(?:المعادلة|المعادله)", text):
            if re.search(r"\d", text):
                return True

        # النسب المئوية.
        if "نسبة" in text and re.search(r"\d", text):
            return True

        return False

    def plan(
        self,
        query: str,
        understanding: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> TaskPlan:

        if not isinstance(query, str) or not query.strip():
            raise ValueError("query must be a non-empty string")

        if not isinstance(understanding, dict):
            raise TypeError("understanding must be a dictionary")

        question_type = understanding.get("question_type", "general")
        contexts = set(understanding.get("contexts") or [])
        topic = understanding.get("topic") or ""

        plan = TaskPlan(
            mode="direct",
            intent=question_type,
            metadata={
                "planner": "v3",
                "topic": topic,
            },
        )

        # ----------------------------------------------------
        # Mathematics
        # ----------------------------------------------------

        is_math = self._looks_like_math(query)

        math_types = {
            "how_many",
        }

        math_contexts = {
            "math",
        }

        if (
            is_math
            or question_type in math_types
            or contexts.intersection(math_contexts)
        ):
            plan.mode = "tool"
            plan.needs_math = True
            plan.needs_llm = True
            plan.tools.append("math")

        # ----------------------------------------------------
        # Knowledge
        # ----------------------------------------------------

        knowledge_types = {
            "define",
            "who",
            "where",
            "when",
            "list",
            "classify",
            "relation",
        }

        if question_type in knowledge_types:
            plan.needs_knowledge = True
            plan.providers.append("general")

        # ----------------------------------------------------
        # Reasoning
        # ----------------------------------------------------

        reasoning_types = {
            "why",
            "how",
            "reason_chain",
        }

        if question_type in reasoning_types:
            plan.needs_reasoning = True
            plan.needs_knowledge = True
            plan.providers.append("general")

        # المنطق الصريح لا يحتاج إلى قاعدة المعرفة العامة
        # إلا إذا أثبتت مرحلة لاحقة أن السؤال يحتاج معرفة خارجية.
        if question_type == "logic":
            plan.needs_reasoning = True

        # ----------------------------------------------------
        # Comparison
        # ----------------------------------------------------

        if question_type == "compare":
            plan.needs_knowledge = True
            plan.needs_reasoning = True
            plan.providers.append("general")

        # ----------------------------------------------------
        # Arabic domain
        # ----------------------------------------------------

        if "religion" in contexts:
            plan.domain = "religion"

        elif "science" in contexts:
            plan.domain = "science"

        elif "tech" in contexts:
            plan.domain = "technology"

        elif "history" in contexts:
            plan.domain = "history"

        elif "geo" in contexts:
            plan.domain = "geography"

        # ----------------------------------------------------
        # Capability analysis (composable; replaces hard rules)
        # ----------------------------------------------------

        decisions = self.analyzer.analyze(query, understanding)

        by_name = {
            decision.capability: decision
            for decision in decisions
        }

        plan.metadata["capability_decisions"] = [
            {
                "capability": decision.capability,
                "can_solve": decision.can_solve,
                "reason": decision.reason,
            }
            for decision in decisions
        ]

        math_decision = by_name.get("math")
        reasoning_decision = by_name.get("reasoning")
        knowledge_decision = by_name.get("knowledge")

        # The planner records *needs* from its own routing policy
        # (question_type/contexts above); the analyzer records what
        # each solver can actually deliver.  Execution consumes the
        # solver verdicts, never the needs flags alone.

        deterministic_claimed = False

        if math_decision is not None and math_decision.can_solve:
            deterministic_claimed = True
            plan.mode = "tool"
            plan.tools.append("math")
            plan.metadata["math_payload"] = dict(math_decision.payload)

        if (
            reasoning_decision is not None
            and reasoning_decision.can_solve
        ):
            deterministic_claimed = True
            plan.needs_reasoning = True
            plan.metadata["reasoning_payload"] = {
                "facts": list(reasoning_decision.payload.get("facts", [])),
                "variable_rules": list(
                    reasoning_decision.payload.get("variable_rules", [])
                ),
                "goal": reasoning_decision.payload.get("goal"),
            }

        if (
            knowledge_decision is not None
            and knowledge_decision.can_solve
            and not deterministic_claimed
        ):
            plan.needs_knowledge = True
            plan.providers.append("general")

        # ----------------------------------------------------
        # LLM — fallback ONLY when no deterministic capability
        # claimed the question.  If a capability was selected but
        # turns out unable at execution time, the pipeline reports
        # that explicitly instead of silently escalating to LLM.
        # ----------------------------------------------------

        plan.needs_llm = not deterministic_claimed

        # ----------------------------------------------------
        # Verification
        # ----------------------------------------------------

        if (
            plan.needs_math
            or plan.needs_reasoning
            or plan.needs_knowledge
        ):
            plan.needs_verification = True

        # إزالة التكرار مع الحفاظ على الترتيب.
        plan.providers = list(dict.fromkeys(plan.providers))
        plan.tools = list(dict.fromkeys(plan.tools))

        return plan
