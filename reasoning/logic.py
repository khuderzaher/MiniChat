# -*- coding: utf-8 -*-
"""
MiniChat v3 — Deterministic Logic Engine

- Modus Ponens
- bounded closure
- contradiction detection
- proof provenance
- proof-specific premises
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

from core.types import ReasoningResult


@dataclass(frozen=True)
class Rule:
    premise: str
    conclusion: str
    source: Optional[str] = None


class LogicReasoner:
    def __init__(self, max_depth: int = 10):
        if max_depth < 1:
            raise ValueError("max_depth يجب أن يكون >= 1")

        self.max_depth = max_depth
        self.facts: set[str] = set()
        self.rules: list[Rule] = []

    def add_fact(self, fact: str) -> None:
        fact = self._clean(fact)
        if fact:
            self.facts.add(fact)

    def add_facts(self, facts: Iterable[str]) -> None:
        for fact in facts:
            self.add_fact(fact)

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

        self.rules.append(Rule(premise, conclusion, source))

    @staticmethod
    def negate(value: str) -> str:
        value = " ".join(value.strip().split())

        if value.startswith("¬"):
            return value[1:].strip()

        return f"¬{value}"

    def infer(self, goal: Optional[str] = None) -> ReasoningResult:
        known = set(self.facts)

        # لكل حقيقة: مجموعة الحقائق الأصلية التي تعتمد عليها.
        provenance: dict[str, set[str]] = {
            fact: {fact}
            for fact in self.facts
        }

        steps: list[str] = []
        derived_by: dict[str, Rule] = {}

        for _depth in range(1, self.max_depth + 1):
            added = False

            for rule in self.rules:
                if rule.premise not in known:
                    continue

                if rule.conclusion in known:
                    continue

                known.add(rule.conclusion)
                added = True

                provenance[rule.conclusion] = set(
                    provenance.get(rule.premise, {rule.premise})
                )
                derived_by[rule.conclusion] = rule

                source = f" ({rule.source})" if rule.source else ""

                steps.append(
                    f"الخطوة {len(steps) + 1}: "
                    f"{rule.premise} → {rule.conclusion}{source}"
                )

            if not added:
                break

        if goal is None:
            return ReasoningResult(
                valid=True,
                conclusion=None,
                premises=sorted(self.facts),
                steps=steps,
                confidence=1.0 if steps or self.facts else None,
                metadata={
                    "engine": "logic",
                    "method": "modus_ponens",
                    "derived_facts": sorted(known - self.facts),
                    "proof_provenance": {
                        key: sorted(value)
                        for key, value in provenance.items()
                    },
                },
            )

        clean_goal = self._clean(goal)
        opposite = self.negate(clean_goal)

        goal_known = clean_goal in known
        opposite_known = opposite in known

        if goal_known and opposite_known:
            premises = sorted(
                provenance.get(clean_goal, set())
                | provenance.get(opposite, set())
            )
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
                    "proof_provenance": {
                        "goal": sorted(provenance.get(clean_goal, set())),
                        "negation": sorted(provenance.get(opposite, set())),
                    },
                },
            )

        if goal_known:
            premises = sorted(provenance.get(clean_goal, set()))
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
                    "proof_provenance": sorted(premises),
                },
            )

        if opposite_known:
            premises = sorted(provenance.get(opposite, set()))
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
                    "proof_provenance": sorted(premises),
                },
            )

        return ReasoningResult(
            valid=False,
            conclusion=None,
            premises=[],
            steps=steps,
            confidence=0.0,
            metadata={
                "engine": "logic",
                "method": "modus_ponens",
                "status": "undetermined",
                "goal": clean_goal,
                "negation": opposite,
                "proof_provenance": [],
            },
        )

    @staticmethod
    def _clean(value: object) -> str:
        if not isinstance(value, str):
            return ""

        return " ".join(value.strip().split())
