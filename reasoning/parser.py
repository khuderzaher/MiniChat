# -*- coding: utf-8 -*-
"""
reasoning/parser.py

محلل بسيط للجمل المنطقية العربية.

المرحلة الأولى:
- استخراج الحقائق الصريحة من النمط:
    X هو Y
    X هي Y

لا يقوم هذا الملف بالاستدلال.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from arabic_utils import normalize_arabic


@dataclass(frozen=True)
class ParsedFact:
    subject: str
    predicate: str
    source_text: str

    @property
    def fact(self) -> str:
        return f"{self.subject} هو {self.predicate}"


class ArabicLogicParser:
    """محلل حقائق عربية صريحة."""

    FACT_PATTERN = re.compile(
        r"^\s*(.+?)\s+(?:هو|هي)\s+(.+?)\s*[.،؟?]?\s*$"
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

        return ParsedFact(
            subject=subject,
            predicate=predicate,
            source_text=original,
        )

    @staticmethod
    def _clean(value: str) -> str:
        value = re.sub(r"\s+", " ", value)
        return value.strip(" ،.؟?")

