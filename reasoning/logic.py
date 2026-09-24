# -*- coding: utf-8 -*-
"""Deterministic typed logic engine with variables and legacy compatibility."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

from core.types import ReasoningResult
from reasoning.model import (
    DerivedFact,
    Fact,
    SemanticRule,
    VariableRule,
    clean_text,
)
from reasoning.unification import (
    apply_bindings_to_predicate,
    find_all_bindings,
)


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
        self.variable_rules: list[VariableRule] = []

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

        self.rules.append(
            SemanticRule(p, c, source)
        )

    def add_variable_rule(self, rule: VariableRule) -> None:
        if not isinstance(rule, VariableRule):
            raise TypeError(
                "add_variable_rule requires VariableRule"
            )

        self.variable_rules.append(rule)

    @staticmethod
    def negate(value: str | Fact) -> str:
        return str(_parse_fact(value).negate())

    @staticmethod
    def _support_for(
        support_facts: Iterable[Fact],
        provenance: dict[Fact, set[Fact]],
    ) -> set[Fact]:

        result: set[Fact] = set()

        for fact in support_facts:
            result.update(
                provenance.get(
                    fact,
                    {fact},
                )
            )

        return result

    def _collect_variable_support(
        self,
        rule: VariableRule,
        bindings: dict[str, str],
        facts: list[Fact],
    ) -> list[Fact]:

        support: list[Fact] = []
        seen: set[Fact] = set()

        for premise in rule.premises:

            grounded = apply_bindings_to_predicate(
                premise.functor,
                list(premise.args),
                premise.negated,
                bindings,
            )

            if grounded is None:
                continue

            for fact in facts:

                if (
                    fact.subject == grounded.subject
                    and fact.predicate == grounded.predicate
                    and fact.negated == grounded.negated
                    and fact not in seen
                ):
                    support.append(fact)
                    seen.add(fact)
                    break

        return support

    def _derive_variable_once(
        self,
        known: set[Fact],
        provenance: dict[Fact, set[Fact]],
    ) -> list[DerivedFact]:

        if not self.variable_rules:
            return []

        snapshot = sorted(
            known,
            key=lambda fact: fact.key,
        )

        derived: list[DerivedFact] = []

        for rule in self.variable_rules:

            premise_specs = [
                premise.as_tuple()
                for premise in rule.premises
            ]

            bindings_list = find_all_bindings(
                premise_specs,
                snapshot,
            )

            for bindings in bindings_list:

                conclusion = rule.conclusion

                fact = apply_bindings_to_predicate(
                    conclusion.functor,
                    list(conclusion.args),
                    conclusion.negated,
                    bindings,
                )

                if fact is None or fact in known:
                    continue

                support = self._collect_variable_support(
                    rule,
                    bindings,
                    snapshot,
                )

                base_support = self._support_for(
                    support,
                    provenance,
                )

                known.add(fact)

                provenance[fact] = (
                    base_support
                    if base_support
                    else set(support)
                )

                derived.append(
                    DerivedFact(
                        fact=fact,
                        rule=rule,
                        bindings=dict(bindings),
                        support_facts=list(support),
                        base_support_facts=sorted(
                            provenance[fact],
                            key=lambda item: item.key,
                        ),
                    )
                )

        return derived

    def derive_with_variables(
        self,
        base_facts: Optional[Iterable[str | Fact]] = None,
        max_depth: Optional[int] = None,
    ) -> list[DerivedFact]:

        known: set[Fact] = (
            {
                _parse_fact(fact)
                for fact in base_facts
                if _parse_fact(fact).subject
            }
            if base_facts is not None
            else set(self.facts)
        )

        provenance = {
            fact: {fact}
            for fact in known
        }

        depth_limit = (
            max_depth
            if max_depth is not None
            else self.max_depth
        )

        results: list[DerivedFact] = []

        for _ in range(depth_limit):

            before = len(known)

            batch = self._derive_variable_once(
                known,
                provenance,
            )

            results.extend(batch)

            if len(known) == before:
                break

        return results

    def infer(
        self,
        goal: Optional[str | Fact] = None,
    ) -> ReasoningResult:

        known = set(self.facts)

        provenance: dict[Fact, set[Fact]] = {
            fact: {fact}
            for fact in known
        }

        steps: list[str] = []

        for _depth in range(
            1,
            self.max_depth + 1,
        ):

            added = False

            # Legacy / typed direct rules.
            for rule in self.rules:

                if rule.premise not in known:
                    continue

                if rule.conclusion in known:
                    continue

                known.add(rule.conclusion)

                provenance[rule.conclusion] = set(
                    provenance.get(
                        rule.premise,
                        {rule.premise},
                    )
                )

                source = (
                    f" ({rule.source})"
                    if rule.source
                    else ""
                )

                steps.append(
                    f"الخطوة {len(steps) + 1}: "
                    f"{rule.premise} → "
                    f"{rule.conclusion}"
                    f"{source}"
                )

                added = True

            # General variable rules.
            variable_derived = self._derive_variable_once(
                known,
                provenance,
            )

            if variable_derived:

                for derived in variable_derived:

                    bindings_text = ", ".join(
                        f"{key}={value}"
                        for key, value in sorted(
                            derived.bindings.items()
                        )
                    )

                    source = (
                        f" ({derived.rule.source})"
                        if derived.rule.source
                        else ""
                    )

                    steps.append(
                        f"الخطوة {len(steps) + 1}: "
                        f"{derived.rule.conclusion} "
                        f"← {derived.rule.premises} "
                        f"[{bindings_text}]"
                        f"{source}"
                    )

                added = True

            if not added:
                break

        if goal is None:
            return ReasoningResult(
                valid=True,
                conclusion=None,
                premises=sorted(
                    str(fact)
                    for fact in self.facts
                ),
                steps=steps,
                confidence=(
                    1.0
                    if steps or self.facts
                    else None
                ),
                metadata={
                    "engine": "logic",
                    "method": (
                        "typed_modus_ponens"
                        if not self.variable_rules
                        else "hybrid_modus_ponens_unification"
                    ),
                    "derived_facts": sorted(
                        str(fact)
                        for fact in known - self.facts
                    ),
                    "proof_provenance": {
                        str(key): sorted(
                            str(value)
                            for value in values
                        )
                        for key, values in provenance.items()
                    },
                    "variable_rules": len(
                        self.variable_rules
                    ),
                },
            )

        clean_goal = _parse_fact(goal)
        opposite = clean_goal.negate()

        goal_known = clean_goal in known
        opposite_known = opposite in known

        if goal_known and opposite_known:

            goal_support = provenance.get(
                clean_goal,
                {clean_goal},
            )

            opposite_support = provenance.get(
                opposite,
                {opposite},
            )

            premises = sorted(
                {
                    str(fact)
                    for fact in (
                        goal_support
                        | opposite_support
                    )
                }
            )

            return ReasoningResult(
                valid=False,
                conclusion=None,
                premises=premises,
                steps=steps,
                confidence=0.0,
                metadata={
                    "engine": "logic",
                    "method": "hybrid_modus_ponens_unification",
                    "status": "contradiction",
                    "goal": str(clean_goal),
                    "negation": str(opposite),
                    "proof_provenance": {
                        "goal": sorted(
                            str(fact)
                            for fact in goal_support
                        ),
                        "negation": sorted(
                            str(fact)
                            for fact in opposite_support
                        ),
                    },
                    "variable_rules": len(
                        self.variable_rules
                    ),
                },
            )

        if goal_known:

            premises = sorted(
                str(fact)
                for fact in provenance.get(
                    clean_goal,
                    {clean_goal},
                )
            )

            return ReasoningResult(
                valid=True,
                conclusion=str(clean_goal),
                premises=premises,
                steps=steps,
                confidence=1.0,
                metadata={
                    "engine": "logic",
                    "method": (
                        "typed_modus_ponens"
                        if not self.variable_rules
                        else "hybrid_modus_ponens_unification"
                    ),
                    "status": "proven",
                    "goal": str(clean_goal),
                    "negation": str(opposite),
                    "proof_provenance": premises,
                    "variable_rules": len(
                        self.variable_rules
                    ),
                },
            )

        if opposite_known:

            premises = sorted(
                str(fact)
                for fact in provenance.get(
                    opposite,
                    {opposite},
                )
            )

            return ReasoningResult(
                valid=False,
                conclusion=str(opposite),
                premises=premises,
                steps=steps,
                confidence=1.0,
                metadata={
                    "engine": "logic",
                    "method": (
                        "typed_modus_ponens"
                        if not self.variable_rules
                        else "hybrid_modus_ponens_unification"
                    ),
                    "status": "disproven",
                    "goal": str(clean_goal),
                    "negation": str(opposite),
                    "proof_provenance": premises,
                    "variable_rules": len(
                        self.variable_rules
                    ),
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
                "method": (
                    "typed_modus_ponens"
                    if not self.variable_rules
                    else "hybrid_modus_ponens_unification"
                ),
                "status": "undetermined",
                "goal": str(clean_goal),
                "negation": str(opposite),
                "proof_provenance": [],
                "variable_rules": len(
                    self.variable_rules
                ),
            },
        )
