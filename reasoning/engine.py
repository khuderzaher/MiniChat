# -*- coding: utf-8 -*-
"""
reasoning/engine.py

واجهة MiniChat الرسمية لمحرك الاستدلال المنطقي.

المسؤوليات:
- تطبيق عقد Reasoner.
- تحميل المعرفة المخزنة من ReasoningStore.
- دمج حقائق وقواعد الطلب الحالي.
- تشغيل LogicReasoner مستقل لكل طلب.
- إعادة ReasoningResult قابل للتتبع.

هذه الطبقة لا تصوغ الإجابة للمستخدم.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from core.protocols import Reasoner
from core.types import Evidence, ReasoningResult
from reasoning.logic import LogicReasoner
from reasoning.storage import ReasoningStore


class FormalReasoner(Reasoner):
    """واجهة الاستدلال المنطقي الرسمي."""

    name = "formal-reasoner"

    def __init__(
        self,
        max_depth: int = 10,
        store: Optional[ReasoningStore] = None,
    ):
        if max_depth < 1:
            raise ValueError("max_depth يجب أن يكون >= 1")

        self.max_depth = max_depth
        self.store = store

        # يحتفظ به للتوافق مع الاستخدامات القديمة.
        # الاستدلال الفعلي يستخدم محركًا جديدًا لكل طلب.
        self.logic = LogicReasoner(max_depth=max_depth)

    def parse_and_add_fact(self, text: str) -> Optional[str]:
        """تحليل حقيقة عربية وإضافتها إلى التخزين أو الذاكرة."""
        from reasoning.parser import ArabicLogicParser

        parsed = ArabicLogicParser().parse_fact(text)

        if parsed is None:
            return None

        if self.store is not None:
            self.store.add_fact(
                parsed.subject,
                "هو",
                parsed.predicate,
            )
        else:
            self.logic.add_fact(parsed.fact)

        return parsed.fact

    def reason(
        self,
        query: str,
        evidence: Optional[list[Evidence]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> ReasoningResult:
        context = context or {}

        facts = context.get("facts", [])
        rules = context.get("rules", [])
        goal = context.get("goal")

        # محرك مستقل لكل طلب لمنع تسرب حالة طلب سابق.
        engine = LogicReasoner(max_depth=self.max_depth)

        # ---------------------------------------------
        # المعرفة الدائمة
        # ---------------------------------------------
        if self.store is not None:
            engine.add_facts(self.store.get_facts())

            for stored_rule in self.store.get_rules():
                engine.add_rule(
                    premise=stored_rule["premise"],
                    conclusion=stored_rule["conclusion"],
                    source=stored_rule["source"],
                )

        # ---------------------------------------------
        # حقائق الطلب الحالي
        # ---------------------------------------------
        if isinstance(facts, (list, tuple, set)):
            engine.add_facts(
                fact
                for fact in facts
                if isinstance(fact, str)
            )

        # ---------------------------------------------
        # قواعد الطلب الحالي
        # ---------------------------------------------
        if isinstance(rules, (list, tuple)):
            for rule in rules:
                if not isinstance(rule, dict):
                    continue

                premise = rule.get("premise")
                conclusion = rule.get("conclusion")
                source = rule.get("source")

                if not isinstance(premise, str):
                    continue

                if not isinstance(conclusion, str):
                    continue

                engine.add_rule(
                    premise=premise,
                    conclusion=conclusion,
                    source=source if isinstance(source, str) else None,
                )

        # ---------------------------------------------
        # الهدف
        # ---------------------------------------------
        if not isinstance(goal, str) or not goal.strip():
            goal = None

        result = engine.infer(goal=goal)

        if evidence:
            result.evidence = list(evidence)

        result.metadata.update(
            {
                "reasoner": self.name,
                "query": query,
                "formal": True,
                "persistent_store": self.store is not None,
            }
        )

        return result
