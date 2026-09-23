# -*- coding: utf-8 -*-
"""
services/syria_knowledge/service.py
خدمة معرفة سورية — تقرأ من data/syria/db/syria.db (SQLite + FTS5).

البروتوكول: handle(query, context) -> Result | None
- لا تخترع. لا تجيب إلا إذا وجدت حقيقة مطابقة بثقة كافية.
"""
import os
import re
import sqlite3
from typing import Optional

from ..protocol import Result, Service

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, "..", "..", "data", "syria", "db", "syria.db")

# كلمات استفهام/حشو تُحذف قبل البحث
STOP = {
    "ما", "هي", "هو", "من", "في", "على", "عن", "إلى", "إلى",
    "أخبرني", "حدثني", "قل", "لي", "هل", "ماذا", "كيف", "لماذا",
    "ال", "و", "أو", "ثم", "ثم", "the", "is", "of",
}

# كلمات تحدد أن السؤال "سوري" — بوابة قبل الاستعلام
SYRIA_HINTS = {
    "سوريا", "سورية", "دمشق", "حلب", "حمص", "حماة", "اللاذقية",
    "طرطوس", "إدلب", "درعا", "السويداء", "القامشلي", "الحسكة",
    "دير الزور", "الرقة", "رقة", "غوطة", "بردى", "العاصي", "الفرات",
    "تدمر", "بصرى", "صلنفة", "مصياف", "الساحل السوري", "الجولان",
}


def _tokenize(text: str):
    """يستخرج كلمات عربية/لاتينية بطول ≥2، بلا كلمات حشو."""
    text = (text or "").strip()
    tokens = re.findall(r"[\u0600-\u06FF\w]+", text)
    out = []
    for t in tokens:
        t = t.strip()
        if len(t) < 2:
            continue
        if t in STOP:
            continue
        out.append(t)
    return out


def _has_syria_hint(query: str) -> bool:
    q = (query or "").strip()
    for h in SYRIA_HINTS:
        if h in q:
            return True
    return False


class SyriaKnowledgeService(Service):
    name = "syria_knowledge"

    def __init__(self, db_path: str = DB):
        self.db_path = db_path
        self._con: Optional[sqlite3.Connection] = None

    def _connect(self) -> sqlite3.Connection:
        if self._con is None:
            self._con = sqlite3.connect(self.db_path)
            self._con.row_factory = sqlite3.Row
        return self._con

    def _fts_search(self, terms, limit=5):
        """FTS5 MATCH بعبارة OR. يعيد list of (rank, row)."""
        if not terms:
            return []
        # FTS5 OR: "term1" OR "term2" ...
        match_q = " OR ".join('"%s"' % t.replace('"', "") for t in terms)
        sql = (
            "SELECT f.id, f.fact, f.source, f.confidence, f.tags, "
            "       bm25(facts_fts) AS rank "
            "FROM facts_fts JOIN facts f ON f.id = facts_fts.rowid "
            "WHERE facts_fts MATCH ? "
            "ORDER BY rank ASC LIMIT ?"
        )
        try:
            return self._connect().execute(sql, (match_q, limit)).fetchall()
        except Exception as e:
            # لا نبتلع الخطأ — نطبعه ليظهر بوضوح
            print("[SYRIA][ERR] _fts_search:", repr(e))
            return []

    def _score(self, row, terms):
        """درجة ثقة مبنية على bm25 + عدد الكلمات المطابقة."""
        if not row:
            return 0.0
        fact = (row["fact"] or "").lower()
        hits = sum(1 for t in terms if t in fact)
        if hits == 0:
            return 0.0
        base = row["confidence"] or 0.8
        # كل مطابقة تزيد الثقة
        coverage = hits / float(len(terms))
        return min(0.99, base * (0.6 + 0.4 * coverage))

    def handle(self, query, context=None):
        if not query:
            return None

        # 1) بوابة: هل السؤال عن سوريا؟
        if not _has_syria_hint(query):
            return None

        terms = _tokenize(query)
        if not terms:
            return None

        rows = self._fts_search(terms, limit=5)
        if not rows:
            return Result(
                handled=True,
                answer=None,
                source="syria_knowledge:no_match",
                confidence=0.0,
                metadata={"terms": terms},
            )

        scored = []
        for r in rows:
            s = self._score(r, terms)
            if s > 0:
                scored.append((s, r))
        if not scored:
            return None

        scored.sort(key=lambda x: -x[0])
        best_score, best = scored[0]

        # عتبة دنيا
        if best_score < 0.5:
            return None

        return Result(
            handled=True,
            answer=best["fact"],
            source="syria_knowledge:" + (best["tags"] or "").split(",")[0],
            confidence=best_score,
            metadata={
                "id": best["id"],
                "source_ref": best["source"],
                "tags": best["tags"],
                "alternatives": [
                    {"fact": r["fact"], "score": round(s, 3)}
                    for s, r in scored[1:4]
                ],
            },
        )


if __name__ == "__main__":
    svc = SyriaKnowledgeService()
    tests = [
        "ما هي عاصمة سوريا؟",
        "ما هو نهر بردى؟",
        "أخبرني عن حلب",
        "ما هي عاصمة مصر؟",         # لا سوريا
        "من هو صلاح الدين؟",         # سوري hint مفقود → None
        "كيف حالك؟",                # ليس سؤالًا
        "ما هي أكبر مدينة سورية؟",
    ]
    for q in tests:
        r = svc.handle(q)
        if r is None:
            print("[%s] → None (لا سوريا hint)" % q)
        elif not r.answer:
            print("[%s] → handled لكن بلا إجابة (%s)" % (q, r.source))
        else:
            print("[%s]" % q)
            print("   → %s" % r.answer)
            print("     conf=%.2f source=%s" % (r.confidence, r.source))
