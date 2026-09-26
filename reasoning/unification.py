# -*- coding: utf-8 -*-
"""Pure deterministic variable unification for MiniChat."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from reasoning.model import Fact

Bindings = dict[str, str]
Predicate = tuple[str, list[str], bool]


def is_variable(token: str) -> bool:
    return isinstance(token, str) and token.startswith("?")


def unify_term(
    pattern: str,
    value: str,
    bindings: Bindings,
) -> Optional[Bindings]:

    if is_variable(pattern):
        if pattern in bindings:
            if bindings[pattern] != value:
                return None
            return dict(bindings)

        result = dict(bindings)
        result[pattern] = value
        return result

    return dict(bindings) if pattern == value else None


def _fact_terms(fact: "Fact") -> list[str]:
    """
    Canonical term view of a Fact.

    unary fact  -> [subject]
    binary fact -> [subject, "@object"]

    The "@" prefix marks the relation-target position explicitly so
    it can never collide with a variable token.
    """

    if fact.predicate.startswith("@"):
        return [fact.subject, fact.predicate]

    return [fact.subject]


def unify_with_fact(
    functor: str,
    args: list[str],
    negated: bool,
    fact: "Fact",
    bindings: Bindings,
) -> Optional[Bindings]:

    terms = _fact_terms(fact)

    if len(args) != len(terms):
        return None

    if functor != fact.predicate.lstrip("@"):
        return None

    if negated != fact.negated:
        return None

    current = bindings

    for pattern, value in zip(args, terms):
        extended = unify_term(pattern, value, current)

        if extended is None:
            return None

        current = extended

    return current


def find_all_bindings(
    premises: list[Predicate],
    facts: list["Fact"],
    bindings: Optional[Bindings] = None,
) -> list[Bindings]:

    current = dict(bindings or {})

    ordered_facts = sorted(
        list(facts),
        key=lambda fact: getattr(fact, "key", str(fact)),
    )

    if not premises:
        return [current]

    functor, args, negated = premises[0]
    rest = premises[1:]

    solutions: list[Bindings] = []

    for fact in ordered_facts:
        extended = unify_with_fact(
            functor,
            args,
            negated,
            fact,
            current,
        )

        if extended is None:
            continue

        solutions.extend(
            find_all_bindings(
                rest,
                ordered_facts,
                extended,
            )
        )

    return solutions


def _resolve_term(token: str, bindings: Bindings) -> Optional[str]:
    if is_variable(token):
        return bindings.get(token)
    return token


def apply_bindings_to_predicate(
    functor: str,
    args: list[str],
    negated: bool,
    bindings: Bindings,
) -> Optional["Fact"]:

    from reasoning.model import Fact

    if len(args) == 1:
        subject = _resolve_term(args[0], bindings)

        if subject is None:
            return None

        return Fact(
            subject=subject,
            predicate=functor,
            negated=negated,
        )

    if len(args) == 2:
        subject = _resolve_term(args[0], bindings)
        target = _resolve_term(args[1], bindings)

        if subject is None or target is None:
            return None

        if not target.startswith("@"):
            target = "@" + target

        return Fact(
            subject=subject,
            predicate=f"{functor} {target}",
            negated=negated,
        )

    return None
