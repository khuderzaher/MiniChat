# -*- coding: utf-8 -*-
"""
MiniChat v3 — General Knowledge Provider

واجهة v3 فوق StructuredDB القديم.

المصدر:
    StructuredDB.faq_entries()

البحث هنا lexical محافظ.
لا توجد إجابة مولدة ولا Qwen.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from core.protocols import KnowledgeProvider
from core.types import Evidence, KnowledgeResult


class GeneralKnowledgeProvider(KnowledgeProvider):
    name = "general"

    # كلمات سؤال عامة لا تحمل عادةً المعلومة الأساسية.
    STOP_WORDS = {
        "ما",
        "ماذا",
        "متى",
        "من",
        "اين",
        "أين",
        "كيف",
        "هل",
        "هو",
        "هي",
        "هم",
        "هن",
        "كم",
        "لماذا",
        "ماهو",
        "ماهي",
        "ماهو",
        "عرف",
        "عرفني",
        "اشرح",
        "لي",
        "عن",
        "هو",
        "هي",
    }

    def __init__(self, db: Any) -> None:
        if db is None:
            raise ValueError("db cannot be None")

        self.db = db
        self._entries = self._load_entries()

    def _load_entries(self) -> List[Dict[str, Any]]:
        entries = self.db.faq_entries()

        if not isinstance(entries, list):
            raise TypeError(
                "StructuredDB.faq_entries() must return a list"
            )

        valid = []

        for entry in entries:
            if not isinstance(entry, dict):
                continue

            question = entry.get("q")
            answer = entry.get("a")

            if not isinstance(question, str):
                continue

            if not isinstance(answer, str):
                continue

            if not question.strip() or not answer.strip():
                continue

            valid.append(entry)

        return valid

    @staticmethod
    def _normalize(text: str) -> str:
        text = text.lower()

        # توحيد بعض أشكال العربية.
        text = text.replace("أ", "ا")
        text = text.replace("إ", "ا")
        text = text.replace("آ", "ا")
        text = text.replace("ى", "ي")
        text = text.replace("ة", "ه")

        # إزالة التشكيل.
        text = re.sub(r"[\u064B-\u065F\u0670]", "", text)

        # إزالة علامات الترقيم.
        # لا نعتمد على نطاق Unicode العربي هنا لأن بعض
        # علامات الترقيم العربية مثل ؟ قد تقع ضمنه.
        text = re.sub(
            r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\w]",
            lambda m: m.group(0) if (
                m.group(0).isalnum() or m.group(0) == "_"
            ) else " ",
            text,
        )

        text = re.sub(r"\s+", " ", text)

        return text.strip()

    @classmethod
    def _tokens(cls, text: str) -> List[str]:
        normalized = cls._normalize(text)

        if not normalized:
            return []

        return normalized.split()

    @classmethod
    def _content_tokens(cls, text: str) -> List[str]:
        """
        كلمات تحمل محتوى السؤال أكثر من أدوات الاستفهام.
        """
        return [
            token
            for token in cls._tokens(text)
            if token not in cls.STOP_WORDS
        ]

    @classmethod
    def _score(cls, query: str, question: str) -> float:
        q_tokens = cls._content_tokens(query)
        d_tokens = cls._content_tokens(question)

        if not q_tokens or not d_tokens:
            return 0.0

        q_set = set(q_tokens)
        d_set = set(d_tokens)

        intersection = q_set & d_set

        if not intersection:
            return 0.0

        # مدى تغطية الكلمات المهمة في السؤال.
        query_coverage = len(intersection) / len(q_set)

        # تشابه مجموعتي الكلمات.
        union = q_set | d_set
        jaccard = len(intersection) / len(union)

        score = (
            0.75 * query_coverage
            + 0.25 * jaccard
        )

        # مكافأة المطابقة الدقيقة بعد التطبيع.
        normalized_query = cls._normalize(query)
        normalized_question = cls._normalize(question)

        if normalized_query == normalized_question:
            score += 0.20

        # إذا كانت كلمات السؤال المهمة كلها موجودة
        # في المرشح، نعطيه مكافأة إضافية صغيرة.
        if q_set.issubset(d_set):
            score += 0.10

        return round(min(score, 1.0), 6)

    def search(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        limit: int = 5,
    ) -> KnowledgeResult:

        if not isinstance(query, str) or not query.strip():
            return KnowledgeResult(
                found=False,
                query=query,
                metadata={
                    "provider": self.name,
                    "reason": "empty_query",
                },
            )

        if limit < 1:
            limit = 1

        scored = []

        for entry in self._entries:
            question = entry["q"]
            score = self._score(query, question)

            if score <= 0:
                continue

            scored.append((score, entry))

        scored.sort(
            key=lambda item: item[0],
            reverse=True,
        )

        # حد قبول محافظ.
        MIN_SCORE = 0.55

        accepted = [
            (score, entry)
            for score, entry in scored
            if score >= MIN_SCORE
        ]

        evidence: List[Evidence] = []

        for score, entry in accepted[:limit]:
            evidence.append(
                Evidence(
                    content=entry["a"],
                    source="structured_db.faq",
                    source_type="faq",
                    reliability=0.75,
                    score=score,
                    metadata={
                        "question": entry["q"],
                        "tags": entry.get("tags", []),
                    },
                )
            )

        return KnowledgeResult(
            found=bool(evidence),
            evidence=evidence,
            query=query,
            metadata={
                "provider": self.name,
                "entries_scanned": len(self._entries),
                "candidates": len(scored),
                "accepted": len(evidence),
                "method": "lexical",
                "min_score": MIN_SCORE,
            },
        )
