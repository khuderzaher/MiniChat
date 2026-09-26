# -*- coding: utf-8 -*-
"""
MiniChat v3 — Knowledge Base (shared lexical index)

قاعدة معرفة عامة قابلة للتوسعة مع:
    - inverted index (token -> entry ids) بدل O(N) scan كامل
    - تطبيع عربي موحد (همزات/تاء مربوطة/تشكيل)
    - dedup على مستوى (question, answer)
    - provenal metadata لكل مصدر

لا تعتمد على StructuredDB مباشرة؛ تُغذّى من providers عبر add().
"""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Optional, Set


def normalize_arabic(text: str) -> str:
    """تطبيع عربي مضبوط ومستقر."""
    text = text.lower()
    for a, b in (
        ("أ", "ا"), ("إ", "ا"), ("آ", "ا"), ("ٱ", "ا"),
        ("ى", "ي"), ("ة", "ه"), ("ؤ", "و"), ("ئ", "ي"),
    ):
        text = text.replace(a, b)
    text = re.sub(r"[\u064B-\u065F\u0670]", "", text)      # تشكيل
    text = re.sub(r"[^\w\s\u0600-\u06FF]", " ", text)      # ترقيم
    return re.sub(r"\s+", " ", text).strip()


STOP_WORDS: Set[str] = {
    "ما", "ماذا", "متى", "من", "اين", "ايه", "كيف", "هل", "هو", "هي",
    "هم", "هن", "كم", "لماذا", "ماهو", "ماهي", "عرف", "عرفني", "اشرح",
    "لي", "عن", "ال", "و", "او", "في", "علي", "الي", "ده", "بدي",
}


def tokenize(text: str, drop_stop: bool = True) -> List[str]:
    normalized = normalize_arabic(text)
    if not normalized:
        return []
    tokens = normalized.split()
    if drop_stop:
        content = [t for t in tokens if t not in STOP_WORDS]
        # لا نعاقب سؤالًا كله أدوات استفهام.
        return content or tokens
    return tokens


class KnowledgeBase:
    """
    فهرس معرفة صغير ومحدد الذاكرة.

    entry schema:
        {id, q, a, source, source_type, reliability, tags}
    """

    def __init__(self) -> None:
        self._entries: List[Dict[str, Any]] = []
        self._index: Dict[str, Set[int]] = {}
        self._seen: Set[tuple] = set()

    def __len__(self) -> int:
        return len(self._entries)

    def add(
        self,
        question: str,
        answer: str,
        source: str,
        source_type: str = "curated",
        reliability: float = 0.8,
        tags: Optional[List[str]] = None,
    ) -> Optional[int]:
        if not isinstance(question, str) or not isinstance(answer, str):
            return None
        if not question.strip() or not answer.strip():
            return None

        fingerprint = (normalize_arabic(question), normalize_arabic(answer))
        if fingerprint in self._seen:
            return None                      # dedup صامت مدروس: نسخة واحدة فقط

        self._seen.add(fingerprint)

        entry_id = len(self._entries)
        entry = {
            "id": entry_id,
            "q": question.strip(),
            "a": answer.strip(),
            "source": source,
            "source_type": source_type,
            "reliability": float(reliability),
            "tags": list(tags or []),
        }
        self._entries.append(entry)

        for token in set(tokenize(question) + tokenize(answer)):
            self._index.setdefault(token, set()).add(entry_id)

        return entry_id

    def add_many(self, items: Iterable[Dict[str, Any]]) -> int:
        added = 0
        for item in items:
            if not isinstance(item, dict):
                continue
            if self.add(
                question=str(item.get("q") or item.get("question") or ""),
                answer=str(item.get("a") or item.get("answer") or ""),
                source=str(item.get("source") or "unknown"),
                source_type=str(item.get("source_type") or "curated"),
                reliability=float(item.get("reliability", 0.8)),
                tags=item.get("tags"),
            ) is not None:
                added += 1
        return added

    def candidates(self, query: str) -> List[int]:
        """مرشحون عبر inverted index — لا مسح كامل للمدخلات."""
        found: Set[int] = set()
        for token in tokenize(query):
            ids = self._index.get(token)
            if ids:
                found |= ids
        return sorted(found)

    def entry(self, entry_id: int) -> Optional[Dict[str, Any]]:
        if 0 <= entry_id < len(self._entries):
            return self._entries[entry_id]
        return None

    @staticmethod
    def score(query: str, question: str, answer: str = "") -> float:
        q_tokens: Set[str] = set(tokenize(query))
        d_tokens: Set[str] = set(tokenize(question))

        if not q_tokens or not d_tokens:
            return 0.0

        intersection = q_tokens & d_tokens
        if not intersection:
            return 0.0

        coverage = len(intersection) / len(q_tokens)
        jaccard = len(intersection) / len(q_tokens | d_tokens)
        score = 0.75 * coverage + 0.25 * jaccard

        if normalize_arabic(query) == normalize_arabic(question):
            score += 0.20

        if q_tokens.issubset(d_tokens):
            score += 0.10

        # مكافأة صغيرة إذا كانت كلمات السؤال تظهر في الجواب نفسه
        # (مؤشر على أن المدخل يدور حول الموضوع فعليًا).
        if answer:
            a_tokens = set(tokenize(answer))
            extra = len(q_tokens & a_tokens) / len(q_tokens)
            score += 0.05 * extra

        return round(min(score, 1.0), 6)
