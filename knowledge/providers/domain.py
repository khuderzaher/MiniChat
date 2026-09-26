# -*- coding: utf-8 -*-
"""
MiniChat v3 — Domain Knowledge Providers

مزودان متخصصان فوق نفس الواجهة (KnowledgeProvider):

    ArabicKnowledgeProvider  : لغة/أدب/ثقافة عربية
    SyriaKnowledgeProvider   : سوريا تحديدًا (جغرافيا/تاريخ/حياة)

القاعدة المعمارية:
    - كل provider يعلن domain خاصًا به و reliability أعلى داخله.
    - provider متخصص لا يغطيه provider عام عند تعارض النتيجة:
      الـAggregator يرتب بالـ(specialty match, score, reliability).
    - البيانات JSON صغيرة ومحدودة، تُحمّل lazy مرة واحدة.
    - مصدر الحقيقة هنا ملفات curated داخل المستودع، مع provenance كامل.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

from core.protocols import KnowledgeProvider
from core.types import Evidence, KnowledgeResult
from knowledge.base import KnowledgeBase


class JsonFileKnowledgeProvider(KnowledgeProvider):
    """
    أساس مشترك: ملف JSON واحد بصيغة:
        [ {"q": "...", "a": "...", "tags": [...], "source": "..."}, ... ]
    """

    name = "json-knowledge"
    source_type = "curated"
    default_reliability = 0.8

    def __init__(self, data_path: str) -> None:
        self.data_path = data_path
        self._base: Optional[KnowledgeBase] = None

    # lazy loading — لا قراءة ملفات عند الاستيراد.
    @property
    def base(self) -> KnowledgeBase:
        if self._base is None:
            kb = KnowledgeBase()
            for item in self._load_raw():
                kb.add(
                    question=str(item.get("q") or ""),
                    answer=str(item.get("a") or ""),
                    source=str(item.get("source") or f"file:{os.path.basename(self.data_path)}"),
                    source_type=self.source_type,
                    reliability=float(item.get("reliability", self.default_reliability)),
                    tags=item.get("tags"),
                )
            self._base = kb
        return self._base

    def _load_raw(self) -> List[Dict[str, Any]]:
        try:
            if not os.path.exists(self.data_path):
                return []
            with open(self.data_path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            if isinstance(data, list):
                return [d for d in data if isinstance(d, dict)]
            if isinstance(data, dict) and isinstance(data.get("entries"), list):
                return [d for d in data["entries"] if isinstance(d, dict)]
            return []
        except (ValueError, OSError):
            return []

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
                metadata={"provider": self.name, "reason": "empty_query"},
            )

        from core.config import get_config

        threshold = (
            float((context or {}).get("knowledge_min_score"))
            if (context or {}).get("knowledge_min_score") is not None
            else get_config().knowledge.min_score
        )

        scored: List[tuple] = []
        for entry_id in self.base.candidates(query):
            entry = self.base.entry(entry_id)
            if entry is None:
                continue
            s = KnowledgeBase.score(query, entry["q"], entry["a"])
            if s >= threshold and s > 0:
                scored.append((s, entry))

        # deterministic ranking: score ثم reliability ثم id
        scored.sort(key=lambda p: (-p[0], -p[1]["reliability"], p[1]["id"]))

        evidence: List[Evidence] = []
        seen_contents: set = set()
        for s, entry in scored[: max(1, int(limit))]:
            content = entry["a"].strip()
            if content in seen_contents:
                continue                      # dedup أدلة مكررة
            seen_contents.add(content)
            evidence.append(
                Evidence(
                    content=content,
                    source=entry["source"],
                    source_type=entry["source_type"],
                    reliability=entry["reliability"],
                    score=s,
                    metadata={
                        "question": entry["q"],
                        "tags": entry["tags"],
                        "provider": self.name,
                    },
                )
            )

        return KnowledgeResult(
            found=bool(evidence),
            evidence=evidence,
            query=query,
            metadata={
                "provider": self.name,
                "entries": len(self.base),
                "candidates": len(scored),
                "accepted": len(evidence),
                "method": "lexical-index",
                "min_score": threshold,
            },
        )


class ArabicKnowledgeProvider(JsonFileKnowledgeProvider):
    """معرفة عربية متخصصة (لغة، أدب، ثقافة، لهجات)."""

    name = "arabic"
    source_type = "arabic_curated"
    default_reliability = 0.85

    def __init__(self, data_path: Optional[str] = None) -> None:
        if data_path is None:
            from core.config import get_config

            data_path = get_config().knowledge.arabic_data_path
        super().__init__(data_path)


class SyriaKnowledgeProvider(JsonFileKnowledgeProvider):
    """معرفة سورية متخصصة — الأولوية داخل نطاقها لهذا المزود."""

    name = "syria"
    source_type = "syria_curated"
    default_reliability = 0.9

    SYRIA_HINTS = (
        "سوريا", "السوري", "دمشق", "حلب", "حمص", "اللاذقية", "ادلب",
        "إدلب", "دير الزور", "الحسكة", "درعا", "السويداء", "طرطوس",
        "الفرات", "سورية", "الشام",
    )

    def __init__(self, data_path: Optional[str] = None) -> None:
        if data_path is None:
            from core.config import get_config

            data_path = get_config().knowledge.syria_data_path
        super().__init__(data_path)

    def relevant(self, query: str) -> bool:
        from knowledge.base import normalize_arabic

        normalized = normalize_arabic(query)
        return any(h in normalized for h in map(normalize_arabic, self.SYRIA_HINTS))

    def search(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        limit: int = 5,
    ) -> KnowledgeResult:
        result = super().search(query, context=context, limit=limit)
        # خارج النطاق السوري لا ندّعي خبرة: نخفض الثقة بدل المنع الكامل.
        if not self.relevant(query):
            for item in result.evidence:
                item.score = round((item.score or 0.0) * 0.6, 6)
                item.metadata["out_of_domain"] = True
        return result
