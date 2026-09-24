# -*- coding: utf-8 -*-
"""Deterministic typed logic engine with legacy compatibility."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

from core.types import ReasoningResult
from reasoning.model import Fact, SemanticRule, clean_text


@dataclass(frozen=True)
class Rule:
    premise: str
    conclusion: str
    source: Optional[str] = None


def _parse_fact(value: str | Fact) -> Fact:
    if isinstance(value, Fact):
        return value

    text = clean_text(value)
    if not text:
        return Fact("")

    negated = text.startswith("¬")
    body = text[1:].strip() if negated else text

    # Preserve arbitrary legacy atomic facts such as A, B, C.
    for marker in (" هو ", " هي "):
        if marker in body:
            subject, predicate = body.split(marker, 1)
            return Fact(
                subject=subject,
                predicate=predicate,
                negated=negated,
                source_text=text,
            )

    return Fact(
        subject=body,
        predicate="",
        negated=negated,
        source_text=text,
    )


class LogicReasoner:
    def __init__(self, max_depth: int = 10):
        if max_depth < 1:
            raise ValueError("max_depth يجب أن يكون >= 1")

        self.max_depth = max_depth
        self.facts: set[Fact] = set()
        self.rules: list[SemanticRule] = []

    def add_fact(self, fact: str | Fact) -> None:
        parsed = _parse_fact(fact)
        if parsed.subject:
            self.facts.add(parsed)

    def add_facts(self, facts: Iterable[str | Fact]) -> None:
        for fact in facts:
            self.add_fact(fact)

    def add_rule(
        self,
        premise: str | Fact | SemanticRule,
        conclusion: str | Fact | None = None,
        source: Optional[str] = None,
    ) -> None:
        """
        Add a rule through either supported API:

            add_rule("A", "B")
            add_rule(Fact(...), Fact(...))
            add_rule(SemanticRule(...))
        """

        if isinstance(premise, SemanticRule):
            if conclusion is not None:
                raise TypeError(
                    "عند تمرير SemanticRule لا يجوز تمرير conclusion"
                )

            rule = premise

            if source is not None:
                rule = SemanticRule(
                    rule.premise,
                    rule.conclusion,
                    source,
                )

            if not rule.premise.subject or not rule.conclusion.subject:
                raise ValueError(
                    "المقدمة والنتيجة يجب ألا تكونا فارغتين"
                )

            self.rules.append(rule)
            return

        if conclusion is None:
            raise TypeError(
                "add_rule يتطلب conclusion عند استخدام "
                "صيغة premise/conclusion"
            )

        p = _parse_fact(premise)
        c = _parse_fact(conclusion)

        if not p.subject or not c.subject:
            raise ValueError(
                "المقدمة والنتيجة يجب ألا تكونا فارغتين"
            )

        self.rules.append(SemanticRule(p, c, source))

    @staticmethod
    def negate(value: str) -> str:
        return str(_parse_fact(value).negate())

    def infer(self, goal: Optional[str] = None) -> ReasoningResult:
        known = set(self.facts)

        provenance: dict[Fact, set[Fact]] = {
            fact: {fact}
            for fact in known
        }

        steps: list[str] = []

        for _depth in range(1, self.max_depth + 1):
            added = False

            for rule in self.rules:
                if rule.premise not in known:
                    continue

                if rule.conclusion in known:
                    continue

                known.add(rule.conclusion)
                provenance[rule.conclusion] = set(
                    provenance.get(rule.premise, {rule.premise})
                )

                source = f" ({rule.source})" if rule.source else ""

                steps.append(
                    f"الخطوة {len(steps) + 1}: "
                    f"{rule.premise} → {rule.conclusion}{source}"
                )

                added = True

            if not added:
                break

        if goal is None:
            return ReasoningResult(
                valid=True,
                conclusion=None,
                premises=sorted(str(f) for f in self.facts),
                steps=steps,
                confidence=1.0 if steps or self.facts else None,
                metadata={
                    "engine": "logic",
                    "method": "typed_modus_ponens",
                    "derived_facts": sorted(
                        str(f) for f in known - self.facts
                    ),
                    "proof_provenance": {
                        str(k): sorted(str(v) for v in values)
                        for k, values in provenance.items()
                    },
                },
            )

        clean_goal = _parse_fact(goal)
        opposite = clean_goal.negate()

        goal_known = clean_goal in known
        opposite_known = opposite in known

        if goal_known and opposite_known:
            premises = sorted(
                str(f)
                for f in (
                    provenance.get(clean_goal, set())
                    | provenance.get(opposite, set())
                )
            )

            return ReasoningResult(
                valid=False,
                conclusion=None,
                premises=premises,
                steps=steps,
                confidence=0.0,
                metadata={
                    "engine": "logic",
                    "method": "typed_modus_ponens",
                    "status": "contradiction",
                    "goal": str(clean_goal),
                    "negation": str(opposite),
                    "proof_provenance": {
                        "goal": sorted(
                            str(f)
                            for f in provenance.get(clean_goal, set())
                        ),
                        "negation": sorted(
                            str(f)
                            for f in provenance.get(opposite, set())
                        ),
                    },
                },
            )

        if goal_known:
            premises = sorted(
                str(f)
                for f in provenance.get(clean_goal, set())
            )

            return ReasoningResult(
                valid=True,
                conclusion=str(clean_goal),
                premises=premises,
                steps=steps,
                confidence=1.0,
                metadata={
                    "engine": "logic",
                    "method": "typed_modus_ponens",
                    "status": "proven",
                    "goal": str(clean_goal),
                    "negation": str(opposite),
                    "proof_provenance": premises,
                },
            )

        if opposite_known:
            premises = sorted(
                str(f)
                for f in provenance.get(opposite, set())
            )

            return ReasoningResult(
                valid=False,
                conclusion=str(opposite),
                premises=premises,
                steps=steps,
                confidence=1.0,
                metadata={
                    "engine": "logic",
                    "method": "typed_modus_ponens",
                    "status": "disproven",
                    "goal": str(clean_goal),
                    "negation": str(opposite),
                    "proof_provenance": premises,
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
                "method": "typed_modus_ponens",
                "status": "undetermined",
                "goal": str(clean_goal),
                "negation": str(opposite),
                "proof_provenance": [],
            },
        )
