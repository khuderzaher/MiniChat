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
