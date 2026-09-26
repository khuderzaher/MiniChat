# -*- coding: utf-8 -*-
"""MiniChat v3 — Formal Reasoner."""

from __future__ import annotations

from typing import Any, Dict, Optional

from core.protocols import Reasoner
from core.types import Evidence, ReasoningResult
from reasoning.logic import LogicReasoner
from reasoning.model import (
    Fact,
    SemanticRule,
    VariablePredicate,
    VariableRule,
)
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

    def parse_and_add_fact(
        self,
        text: str,
    ) -> Optional[str]:

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

        return parsed.fact

    @staticmethod
    def _coerce_variable_predicate(
        value: Any,
    ) -> VariablePredicate:

        if isinstance(value, VariablePredicate):
            return value

        if not isinstance(value, dict):
            raise TypeError(
                "variable predicate must be dict or VariablePredicate"
            )

        functor = value.get("functor")
        args = value.get("args")
        negated = value.get(
            "negated",
            False,
        )

        if not isinstance(functor, str):
            raise TypeError(
                "variable predicate functor must be str"
            )

        if not isinstance(args, (list, tuple)):
            raise TypeError(
                "variable predicate args must be list/tuple"
            )

        return VariablePredicate(
            functor=functor,
            args=tuple(
                str(arg)
                for arg in args
            ),
            negated=bool(negated),
        )

    @classmethod
    def _coerce_variable_rule(
        cls,
        value: Any,
    ) -> VariableRule:

        if isinstance(value, VariableRule):
            return value

        if not isinstance(value, dict):
            raise TypeError(
                "variable rule must be dict or VariableRule"
            )

        premises = value.get("premises")
        conclusion = value.get("conclusion")

        if not isinstance(
            premises,
            (list, tuple),
        ):
            raise TypeError(
                "variable rule premises must be list/tuple"
            )

        return VariableRule(
            premises=tuple(
                cls._coerce_variable_predicate(
                    premise
                )
                for premise in premises
            ),
            conclusion=cls._coerce_variable_predicate(
                conclusion
            ),
            source=(
                value.get("source")
                if isinstance(
                    value.get("source"),
                    str,
                )
                else ""
            ),
            rule_id=(
                value.get("rule_id")
                if isinstance(
                    value.get("rule_id"),
                    str,
                )
                else ""
            ),
        )

    def reason(
        self,
        query: str,
        evidence: Optional[list[Evidence]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> ReasoningResult:

        context = context or {}

        facts = context.get(
            "facts",
            [],
        )

        rules = context.get(
            "rules",
            [],
        )

        variable_rules = context.get(
            "variable_rules",
            [],
        )

        goal = context.get(
            "goal"
        )

        # A goal may also be a *pattern* (VariablePredicate), e.g. a
        # relational query like أطول(?X, @كريم).  We ground it once
        # the closure is computed via derive_with_variables below;
        # for now LogicReasoner.infer only accepts Fact/str, so we
        # keep pattern goals aside.
        goal_pattern = None

        from reasoning.model import VariablePredicate as _VP

        if isinstance(goal, _VP):
            goal_pattern = goal
            goal = None

        engine = LogicReasoner(
            max_depth=self.max_depth
        )

        use_persistent = (
            context.get("use_persistent")
            is True
        )

        if (
            use_persistent
            and self.store is not None
        ):
            engine.add_facts(
                self.store.get_facts()
            )

            for stored_rule in self.store.get_rules():
                engine.add_rule(
                    premise=stored_rule["premise"],
                    conclusion=stored_rule["conclusion"],
                    source=stored_rule["source"],
                )

        if isinstance(
            facts,
            (list, tuple, set),
        ):
            for fact in facts:
                if isinstance(
                    fact,
                    (str, Fact),
                ):
                    engine.add_fact(fact)

        if isinstance(
            rules,
            (list, tuple),
        ):
            for rule in rules:

                try:

                    if isinstance(
                        rule,
                        SemanticRule,
                    ):
                        engine.add_rule(rule)
                        continue

                    if not isinstance(
                        rule,
                        dict,
                    ):
                        continue

                    premise = rule.get(
                        "premise"
                    )

                    conclusion = rule.get(
                        "conclusion"
                    )

                    if not isinstance(
                        premise,
                        (str, Fact),
                    ):
                        continue

                    if not isinstance(
                        conclusion,
                        (str, Fact),
                    ):
                        continue

                    source = (
                        rule.get("source")
                        if isinstance(
                            rule.get("source"),
                            str,
                        )
                        else None
                    )

                    engine.add_rule(
                        premise=premise,
                        conclusion=conclusion,
                        source=source,
                    )

                except (
                    TypeError,
                    ValueError,
                ):
                    continue

        if isinstance(
            variable_rules,
            (list, tuple),
        ):
            for rule in variable_rules:

                try:
                    engine.add_variable_rule(
                        self._coerce_variable_rule(
                            rule
                        )
                    )

                except (
                    TypeError,
                    ValueError,
                ):
                    continue

        if not isinstance(
            goal,
            (str, Fact),
        ) or (
            isinstance(goal, str)
            and not goal.strip()
        ):
            goal = None

        result = engine.infer(
            goal=goal
        )

        if goal_pattern is not None:
            # Backward-chaining over the derived closure: try every
            # binding of the pattern against all known/derived facts.
            from reasoning.unification import find_all_bindings
            from reasoning.model import Fact as _F

            closure_facts = sorted(
                {
                    _F.from_text(text)
                    for text in result.metadata.get("derived_facts", [])
                }
                | set(engine.facts),
                key=lambda fact: fact.key,
            )

            matches = find_all_bindings(
                [goal_pattern.as_tuple()],
                closure_facts,
            )

            if matches:
                bindings = matches[0]
                grounded = goal_pattern.grounded_predicate(bindings)
                subject = grounded.args[0]
                target = grounded.args[1].lstrip("@")
                predicate_core = grounded.functor

                conclusion_text = f"{subject} هو {predicate_core} @{target}"

                premises = sorted(
                    str(fact)
                    for fact in closure_facts
                    if fact.subject == subject or fact.subject == target
                )

                result.valid = True
                result.conclusion = conclusion_text
                result.premises = premises
                result.confidence = 1.0
                result.metadata.update(
                    {
                        "status": "proven",
                        "method": "backward_pattern_match",
                        "goal_bindings": dict(bindings),
                    }
                )
            else:
                result.valid = False
                result.conclusion = None
                result.confidence = 0.0
                result.metadata["status"] = "not_proven"

        if evidence:
            result.evidence = list(evidence)

        result.metadata.update(
            {
                "reasoner": self.name,
                "query": query,
                "formal": True,
                "persistent_store": (
                    self.store is not None
                ),
                "persistent_used": (
                    use_persistent
                    and self.store is not None
                ),
            }
        )

        return result
