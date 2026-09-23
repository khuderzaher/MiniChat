from __future__ import annotations

from typing import Iterable

from core.types import Evidence


class EvidencePolicy:
    """يحدد متى يمكن استخدام الدليل مباشرة دون توليد إضافي."""

    name = "evidence-policy"

    def __init__(
        self,
        min_score: float = 0.90,
        min_reliability: float = 0.70,
    ):
        self.min_score = min_score
        self.min_reliability = min_reliability

    def direct_answer(self, evidence: Iterable[Evidence]) -> bool:
        items = [
            item
            for item in evidence
            if isinstance(item, Evidence)
        ]

        if len(items) != 1:
            return False

        item = items[0]

        if not item.content.strip():
            return False

        if item.score is None or item.score < self.min_score:
            return False

        if (
            item.reliability is not None
            and item.reliability < self.min_reliability
        ):
            return False

        return True
