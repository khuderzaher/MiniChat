# -*- coding: utf-8 -*-
"""
MiniChat v3 — Understanding Service

طبقة موحّدة لفهم السؤال.
تستخدم المحرك القديم حاليًا كتنفيذ خلفي مؤقت،
من دون أن تجعل بقية النظام يعتمد عليه مباشرة.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from understanding_engine import get_understanding_engine


class UnderstandingService:
    """
    واجهة v3 لفهم اللغة والسؤال.

    لاحقًا يمكن استبدال التنفيذ الداخلي بالكامل
    دون تغيير الـOrchestrator.
    """

    name = "understanding"

    def __init__(self) -> None:
        self.engine = get_understanding_engine()

    def analyze(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if not isinstance(text, str):
            raise TypeError("text must be a string")

        text = text.strip()

        if not text:
            return {
                "original": "",
                "question_type": "general",
                "topic": "",
                "contexts": [],
                "tokens": [],
            }

        result = self.engine.analyze(text)

        # ننسخ النتيجة بدل تمرير مرجع داخلي للمحرك القديم.
        return dict(result)

    def disambiguate(
        self,
        word: str,
        contexts: Optional[list[str]] = None,
    ) -> Dict[str, Any]:
        if not isinstance(word, str):
            raise TypeError("word must be a string")

        return self.engine.disambiguate(
            word,
            contexts or [],
        )
