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


def unify_with_fact(
    functor: str,
    args: list[str],
    negated: bool,
    fact: "Fact",
    bindings: Bindings,
) -> Optional[Bindings]:

    if len(args) != 1:
        return None

    if functor != fact.predicate:
        return None

    if negated != fact.negated:
        return None

    return unify_term(args[0], fact.subject, bindings)


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


def apply_bindings_to_predicate(
    functor: str,
    args: list[str],
    negated: bool,
    bindings: Bindings,
) -> Optional["Fact"]:

    from reasoning.model import Fact

    if len(args) != 1:
        return None

    value = args[0]

    if is_variable(value):
        if value not in bindings:
            return None
        subject = bindings[value]
    else:
        subject = value

    return Fact(
        subject=subject,
        predicate=functor,
        negated=negated,
    )
