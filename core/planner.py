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

from core.types import TaskPlan


class Planner:
    """
    مخطط التنفيذ المركزي.

    مسؤول عن اختيار المسارات المطلوبة،
    وليس تنفيذها.
    """

    name = "planner"

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
        # LLM
        # ----------------------------------------------------

        plan.needs_llm = True

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
