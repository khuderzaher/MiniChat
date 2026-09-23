# -*- coding: utf-8 -*-
"""
MiniChat v3 — Formal Reasoner

Persistent knowledge is NOT injected into every request.

Default:
    current request context only.

Optional:
    context["use_persistent"] = True

This keeps persistent knowledge an explicit source instead of
an implicit global working memory.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from core.protocols import Reasoner
from core.types import Evidence, ReasoningResult
from reasoning.logic import LogicReasoner
from reasoning.storage import ReasoningStore


class FormalReasoner(Reasoner):
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
        self.logic = LogicReasoner(max_depth=max_depth)

    def parse_and_add_fact(self, text: str) -> Optional[str]:
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

        engine = LogicReasoner(max_depth=self.max_depth)

        # Persistent knowledge is opt-in.
        use_persistent = context.get("use_persistent") is True

        if use_persistent and self.store is not None:
            engine.add_facts(self.store.get_facts())

            for stored_rule in self.store.get_rules():
                engine.add_rule(
                    premise=stored_rule["premise"],
                    conclusion=stored_rule["conclusion"],
                    source=stored_rule["source"],
                )

        if isinstance(facts, (list, tuple, set)):
            engine.add_facts(
                fact
                for fact in facts
                if isinstance(fact, str)
            )

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
                "persistent_used": use_persistent and self.store is not None,
            }
        )

        return result
