# -*- coding: utf-8 -*-
"""
reasoning/logic.py
نواة استدلال منطقي حتمية لـ MiniChat v3.

المسؤوليات:
- تخزين الحقائق والقواعد.
- تطبيق Modus Ponens.
- تنفيذ استدلال متسلسل محدود العمق.
- كشف التناقض بين القضية ونفيها.
- إنتاج ReasoningResult قابل للتتبع.

هذه الطبقة لا تفسر اللغة الطبيعية ولا تستخدم LLM.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

from core.types import ReasoningResult


@dataclass(frozen=True)
class Rule:
    """قاعدة منطقية بالشكل: premise -> conclusion."""
    premise: str
    conclusion: str
    source: Optional[str] = None


class LogicReasoner:
    """
    محرك استدلال منطقي حتمي.

    مثال:
        fact: "المطر"
        rule: "المطر" -> "الأرض رطبة"
    """

    def __init__(self, max_depth: int = 10):
        if max_depth < 1:
            raise ValueError("max_depth يجب أن يكون >= 1")

        self.max_depth = max_depth
        self.facts: set[str] = set()
        self.rules: list[Rule] = []

    # ---------------------------------------------------------
    # Facts
    # ---------------------------------------------------------

    def add_fact(self, fact: str) -> None:
        fact = self._clean(fact)
        if fact:
            self.facts.add(fact)

    def add_facts(self, facts: Iterable[str]) -> None:
        for fact in facts:
            self.add_fact(fact)

    # ---------------------------------------------------------
    # Rules
    # ---------------------------------------------------------

    def add_rule(
        self,
        premise: str,
        conclusion: str,
        source: Optional[str] = None,
    ) -> None:
        premise = self._clean(premise)
        conclusion = self._clean(conclusion)

        if not premise or not conclusion:
            raise ValueError("المقدمة والنتيجة يجب ألا تكونا فارغتين")

        self.rules.append(
            Rule(
                premise=premise,
                conclusion=conclusion,
                source=source,
            )
        )

    # ---------------------------------------------------------
    # Negation
    # ---------------------------------------------------------

    @staticmethod
    def negate(value: str) -> str:
        """
        يعكس النفي الصريح:

            B  -> ¬B
            ¬B -> B
        """
        value = " ".join(value.strip().split())

        if value.startswith("¬"):
            return value[1:].strip()

        return f"¬{value}"

    # ---------------------------------------------------------
    # Inference
    # ---------------------------------------------------------

    def infer(
        self,
        goal: Optional[str] = None,
    ) -> ReasoningResult:

        known = set(self.facts)
        premises = sorted(self.facts)
        steps: list[str] = []

        # -----------------------------------------------------
        # 1. Build full reachable closure.
        # -----------------------------------------------------

        for depth in range(1, self.max_depth + 1):
            added = False

            for rule in self.rules:
                if rule.premise not in known:
                    continue

                if rule.conclusion in known:
                    continue

                known.add(rule.conclusion)
                added = True

                source = (
                    f" ({rule.source})"
                    if rule.source
                    else ""
                )

                steps.append(
                    f"الخطوة {len(steps) + 1}: "
                    f"{rule.premise} → {rule.conclusion}{source}"
                )

            if not added:
                break

        # -----------------------------------------------------
        # 2. No goal: return derived closure.
        # -----------------------------------------------------

        if goal is None:
            return ReasoningResult(
                valid=True,
                conclusion=None,
                premises=premises,
                steps=steps,
                confidence=1.0 if steps or premises else None,
                metadata={
                    "engine": "logic",
                    "method": "modus_ponens",
                    "derived_facts": sorted(known - self.facts),
                },
            )

        clean_goal = self._clean(goal)
        opposite = self.negate(clean_goal)

        goal_known = clean_goal in known
        opposite_known = opposite in known

        # -----------------------------------------------------
        # 3. Contradiction.
        # -----------------------------------------------------

        if goal_known and opposite_known:
            return ReasoningResult(
                valid=False,
                conclusion=None,
                premises=premises,
                steps=steps,
                confidence=0.0,
                metadata={
                    "engine": "logic",
                    "method": "modus_ponens",
                    "status": "contradiction",
                    "goal": clean_goal,
                    "negation": opposite,
                },
            )

        # -----------------------------------------------------
        # 4. Goal proven.
        # -----------------------------------------------------

        if goal_known:
            return ReasoningResult(
                valid=True,
                conclusion=clean_goal,
                premises=premises,
                steps=steps,
                confidence=1.0,
                metadata={
                    "engine": "logic",
                    "method": "modus_ponens",
                    "status": "proven",
                    "goal": clean_goal,
                    "negation": opposite,
                },
            )

        # -----------------------------------------------------
        # 5. Goal disproven.
        # -----------------------------------------------------

        if opposite_known:
            return ReasoningResult(
                valid=False,
                conclusion=opposite,
                premises=premises,
                steps=steps,
                confidence=1.0,
                metadata={
                    "engine": "logic",
                    "method": "modus_ponens",
                    "status": "disproven",
                    "goal": clean_goal,
                    "negation": opposite,
                },
            )

        # -----------------------------------------------------
        # 6. Undetermined.
        # -----------------------------------------------------

        return ReasoningResult(
            valid=False,
            conclusion=None,
            premises=premises,
            steps=steps,
            confidence=0.0,
            metadata={
                "engine": "logic",
                "method": "modus_ponens",
                "status": "undetermined",
                "goal": clean_goal,
                "negation": opposite,
            },
        )

    # ---------------------------------------------------------
    # Utility
    # ---------------------------------------------------------

    @staticmethod
    def _clean(value: object) -> str:
        if not isinstance(value, str):
            return ""

        return " ".join(value.strip().split())
