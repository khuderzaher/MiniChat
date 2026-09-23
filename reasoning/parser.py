# -*- coding: utf-8 -*-
"""Arabic logical fact parser."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from arabic_utils import normalize_arabic
from reasoning.model import Fact


@dataclass(frozen=True)
class ParsedFact:
    subject: str
    predicate: str
    source_text: str
    negated: bool = False

    @property
    def fact(self) -> str:
        prefix = "¬" if self.negated else ""
        return f"{prefix}{self.subject} هو {self.predicate}"

    def to_fact(self) -> Fact:
        return Fact(
            subject=self.subject,
            predicate=self.predicate,
            negated=self.negated,
            source_text=self.source_text,
        )


class ArabicLogicParser:
    """Parse explicit Arabic facts into typed semantic facts."""

    FACT_PATTERN = re.compile(
        r"^\s*(.+?)\s+(?:هو|هي)\s+(.+?)\s*[.،؟?]?\s*$"
    )

    NEGATION_PREFIXES = (
        "ليس ",
        "ليست ",
        "غير ",
    )

    def parse_fact(self, text: str) -> Optional[ParsedFact]:
        if not isinstance(text, str):
            return None

        original = text.strip()
        if not original:
            return None

        normalized = normalize_arabic(original).strip()
        match = self.FACT_PATTERN.match(normalized)

        if not match:
            return None

        subject = self._clean(match.group(1))
        predicate = self._clean(match.group(2))

        if not subject or not predicate:
            return None

        negated = False
        for prefix in self.NEGATION_PREFIXES:
            if predicate.startswith(prefix):
                predicate = self._clean(predicate[len(prefix):])
                negated = True
                break

        if not predicate:
            return None

        return ParsedFact(
            subject=subject,
            predicate=predicate,
            source_text=original,
            negated=negated,
        )

    def parse_typed(self, text: str) -> Optional[Fact]:
        parsed = self.parse_fact(text)
        return parsed.to_fact() if parsed else None

    @staticmethod
    def _clean(value: str) -> str:
        value = re.sub(r"\s+", " ", value)
        return value.strip(" ،.؟?")


def parse_fact(text: str) -> Optional[Fact]:
    return ArabicLogicParser().parse_typed(text)
