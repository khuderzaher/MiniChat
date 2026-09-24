# -*- coding: utf-8 -*-
"""Typed semantic structures with legacy-compatible rendering."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


def clean_text(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return " ".join(value.strip().split())


@dataclass(frozen=True)
class Fact:
    subject: str
    predicate: str
    negated: bool = False
    source_text: Optional[str] = field(
        default=None,
        compare=False,
        hash=False,
        repr=False,
    )

    def __post_init__(self):
        object.__setattr__(self, "subject", clean_text(self.subject))
        object.__setattr__(self, "predicate", clean_text(self.predicate))

    @property
    def key(self) -> str:
        prefix = "¬" if self.negated else ""
        return f"{prefix}{self.subject}::{self.predicate}"

    def negate(self) -> "Fact":
        return Fact(
            self.subject,
            self.predicate,
            not self.negated,
            self.source_text,
        )

    def __str__(self) -> str:
        if self.source_text:
            return clean_text(self.source_text)

        prefix = "¬" if self.negated else ""

        if not self.predicate:
            return f"{prefix}{self.subject}"

        return f"{prefix}{self.subject} هو {self.predicate}"


@dataclass(frozen=True)
class SemanticRule:
    premise: Fact
    conclusion: Fact
    source: Optional[str] = None

    @property
    def key(self) -> str:
        return f"{self.premise.key} → {self.conclusion.key}"


@dataclass(frozen=True)
class VariablePredicate:
    """Unary predicate pattern."""

    functor: str
    args: tuple[str, ...]
    negated: bool = False

    def __post_init__(self):
        object.__setattr__(self, "functor", clean_text(self.functor))
        object.__setattr__(
            self,
            "args",
            tuple(clean_text(arg) for arg in self.args),
        )

        if not self.functor:
            raise ValueError("functor must not be empty")

        if len(self.args) != 1:
            raise ValueError(
                "MiniChat variable predicates currently support exactly one argument"
            )

    def is_ground(self) -> bool:
        return not any(arg.startswith("?") for arg in self.args)

    def as_tuple(self):
        return self.functor, list(self.args), self.negated

    def variables(self) -> set[str]:
        return {
            arg for arg in self.args
            if isinstance(arg, str) and arg.startswith("?")
        }

    def __str__(self) -> str:
        prefix = "¬" if self.negated else ""
        return f"{prefix}{self.functor}({', '.join(self.args)})"


@dataclass(frozen=True)
class VariableRule:
    """Universally quantified rule."""

    premises: tuple[VariablePredicate, ...]
    conclusion: VariablePredicate
    source: str = ""
    rule_id: str = ""

    def __post_init__(self):
        premises = tuple(self.premises)

        if not premises:
            raise ValueError("VariableRule requires at least one premise")

        object.__setattr__(self, "premises", premises)

        premise_variables = set()
        for premise in premises:
            premise_variables.update(premise.variables())

        unbound = self.conclusion.variables() - premise_variables

        if unbound:
            raise ValueError(
                "Conclusion contains unbound variables: "
                + ", ".join(sorted(unbound))
            )

        if not self.rule_id:
            prem_text = " ∧ ".join(str(p) for p in premises)
            generated_id = f"({prem_text}) → {self.conclusion}"
            object.__setattr__(self, "rule_id", generated_id)


@dataclass
class DerivedFact:
    """One deterministic selected proof path."""

    fact: Fact
    rule: VariableRule
    bindings: dict[str, str]
    support_facts: list[Fact] = field(default_factory=list)
    base_support_facts: list[Fact] = field(default_factory=list)

    @property
    def proof_text(self) -> str:
        bindings_text = ", ".join(
            f"{key}={value}"
            for key, value in sorted(self.bindings.items())
        )

        support_text = " + ".join(
            str(fact)
            for fact in self.support_facts
        )

        return (
            f"{self.rule.rule_id} | "
            f"bindings={bindings_text} | "
            f"support={support_text}"
        )
