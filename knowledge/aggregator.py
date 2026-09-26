# -*- coding: utf-8 -*-
"""
MiniChat v3 — Knowledge Aggregator

استرجاع متعدد المزودين مع ranking موحد وتعارضات صريحة:

    1. نفّذ كل providers المطلوبة في الخطة.
    2. اجمع الأدلة ووحّد الـscore النهائي:
           final = score * reliability_bonus * domain_bonus
       حيث domain_bonus يكافئ provider المتخصص عندما يكون
       السؤال داخل نطاقه (حتى لا يغطيه مزود عام).
    3. dedup حسب محتوى الدليل (أبقِ الأعلى).
    4. كشف التعارض: أدلة عالية النتيجة بمحتويات مختلفة
       لنفس السؤال => conflict metadata، ولا direct answer.
    5. لا نتيجة؟ found=False مع سبب واضح (insufficient_evidence).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from core.protocols import KnowledgeProvider
from core.types import Evidence, KnowledgeResult


class KnowledgeAggregator:
    name = "knowledge-aggregator"

    def __init__(self) -> None:
        self._providers: Dict[str, KnowledgeProvider] = {}

    def register(self, provider: KnowledgeProvider) -> None:
        if not getattr(provider, "name", ""):
            raise ValueError("provider must have a non-empty name")
        self._providers[provider.name] = provider

    @property
    def provider_names(self) -> List[str]:
        return sorted(self._providers)

    def search(
        self,
        query: str,
        provider_names: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None,
        limit: int = 5,
    ) -> KnowledgeResult:
        names = provider_names or self.provider_names
        merged: List[Evidence] = []
        per_provider: Dict[str, Any] = {}
        failures: Dict[str, str] = {}

        for name in names:
            provider = self._providers.get(name)
            if provider is None:
                failures[name] = "not_registered"
                continue
            try:
                result = provider.search(query, context=context, limit=limit)
            except Exception as exc:
                # فشل مزود واحد لا يُسقط الباقي، لكنه ليس silent.
                failures[name] = f"{type(exc).__name__}: {exc}"
                continue

            if not isinstance(result, KnowledgeResult):
                failures[name] = "invalid_result_type"
                continue

            per_provider[name] = {
                "found": result.found,
                "count": len(result.evidence),
                "top_score": (
                    result.evidence[0].score if result.evidence else None
                ),
            }

            domain_bonus = 1.0
            relevant = getattr(provider, "relevant", None)
            if callable(relevant):
                try:
                    if relevant(query):
                        domain_bonus = 1.15   # متخصص داخل نطاقه يتقدّم
                except Exception:
                    pass

            for item in result.evidence:
                score = item.score or 0.0
                reliability = item.reliability if item.reliability is not None else 0.5
                final = round(min(score * (0.7 + 0.3 * reliability) * domain_bonus, 1.0), 6)
                enriched = Evidence(
                    content=item.content,
                    source=item.source,
                    source_type=item.source_type,
                    reliability=item.reliability,
                    score=final,
                    metadata={**item.metadata, "raw_score": score, "provider": name},
                )
                merged.append(enriched)

        # dedup حسب المحتوى — أبقِ الأعلى نهائيًا، tie-break stable.
        merged.sort(key=lambda e: (-e.score, e.source_type, e.content))
        deduped: List[Evidence] = []
        seen: set = set()
        for item in merged:
            fingerprint = item.content.strip().lower()
            if fingerprint in seen:
                continue
            seen.add(fingerprint)
            deduped.append(item)

        top = deduped[: max(1, int(limit))]

        # conflict detection: دليلان قويان مختلفا المحتوى لنفس السؤال
        conflicts: List[str] = []
        strong = [e for e in top if (e.score or 0) >= 0.75]
        contents = {e.content.strip().lower() for e in strong}
        if len(contents) > 1:
            conflicts = sorted({e.content for e in strong})[:4]

        return KnowledgeResult(
            found=bool(top),
            evidence=top,
            query=query,
            metadata={
                "aggregator": "v3",
                "providers_queried": names,
                "per_provider": per_provider,
                "failures": failures,
                "conflicts": conflicts,
                "reason": None if top else "insufficient_evidence",
            },
        )
