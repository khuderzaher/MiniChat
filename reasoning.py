# -*- coding: utf-8 -*-
"""
reasoning.py — محرك بحث عربي ذكي v3
"""
import re
from arabic_utils import (
    normalize_arabic, strip_definite, stem_plural,
    canonical, similarity_score, extract_core_tokens,
    expand_with_synonyms, ARABIC_STOPWORDS,
)


SUBJECT_PATTERNS = [
    r"^ما هو\s+(.+?)[\؟\?]?$",
    r"^ما هي\s+(.+?)[\؟\?]?$",
    r"^من هو\s+(.+?)[\؟\?]?$",
    r"^من هي\s+(.+?)[\؟\?]?$",
    r"^ما معنى\s+(.+?)[\؟\?]?$",
    r"^أخبرني عن\s+(.+?)[\؟\?]?$",
    r"^اخبرني عن\s+(.+?)[\؟\?]?$",
    r"^حديث\s+(?:رقم\s+)?(.+?)[\؟\?]?$",
    r"^آية\s+(.+?)[\؟\?]?$",
    r"^تعريف\s+(.+?)[\؟\?]?$",
]


def strip_parens(s):
    return re.sub(r"\s*\([^)]*\)\s*", " ", s).strip()


def extract_subject_raw(query):
    """يعيد الموضوع كما هو (مع الأقواس)."""
    q = normalize_arabic(query).strip()
    for p in SUBJECT_PATTERNS:
        m = re.match(p, q)
        if m:
            return m.group(1).strip(" ؟?،.")
    return None


def extract_keywords(query):
    s = normalize_arabic(query)
    for kw in ["ما هو", "ما هي", "من هو", "من هي", "أخبرني عن",
               "اخبرني عن", "ما معنى", "ما", "هو", "هي", "عن"]:
        s = s.replace(kw, " ")
    s = re.sub(r"[^\u0600-\u06FFa-zA-Z0-9\s]", " ", s)
    words = [w.strip() for w in s.split() if len(w.strip()) > 2]
    words = [w for w in words if w not in ARABIC_STOPWORDS]
    words.sort(key=lambda x: -len(x))
    return words[:5]


class KnowledgeIndex:
    def __init__(self, db):
        self.db = db
        self.by_canon = {}
        self.items = []
        self._build()

    def _priority(self, subj_raw):
        if "توضيح" in subj_raw:
            return -1000
        core = strip_parens(subj_raw)
        has_paren = "(" in subj_raw
        if has_paren:
            return 1000 - len(core)
        return 500 - len(core)

    def _build(self):
        for item in self.db.faq_entries():
            if not isinstance(item, dict):
                continue
            q = item.get("q", "").strip()
            a = item.get("a", "").strip()
            if not q or not a:
                continue
            subj_raw = extract_subject_raw(q)
            if not subj_raw:
                continue
            # تجاهل "توضيح" — من العنوان الخام قبل شيل الأقواس
            if "توضيح" in subj_raw:
                continue
            core = strip_parens(subj_raw)
            c = canonical(core)
            if not c:
                continue
            pr = self._priority(subj_raw)
            self.items.append((c, subj_raw, item, pr))
            if c not in self.by_canon:
                self.by_canon[c] = (item, pr)
            else:
                _, old_pr = self.by_canon[c]
                if pr > old_pr:
                    self.by_canon[c] = (item, pr)
        print("[INDEX] تم فهرسة %d عنصر" % len(self.items))

    def find(self, subject):
        if not subject:
            return None
        c = canonical(subject)
        if not c:
            return None

        # 1) تطابق تام
        if c in self.by_canon:
            return self.by_canon[c][0]

        # 1.b) جرب بـ canonical_stem
        try:
            from arabic_utils import canonical_stem
            cs = canonical_stem(subject)
            if cs and cs != c and cs in self.by_canon:
                return self.by_canon[cs][0]
        except Exception:
            pass

        # 2) subj == أول N كلمة في cc (بدون كلمات إضافية في البداية)
        c_words = c.split()
        n = len(c_words)
        starts_with = []
        for cc, _, item, pr in self.items:
            cc_words = cc.split()
            if len(cc_words) >= n and cc_words[:n] == c_words:
                extra = len(cc_words) - n
                starts_with.append((extra, len(cc), -pr, item))
        if starts_with:
            starts_with.sort()
            return starts_with[0][3]

        # 3) subj ⊆ cc (set)
        c_set = set(c_words)
        candidates = []
        for cc, _, item, pr in self.items:
            if c_set.issubset(set(cc.split())):
                candidates.append((len(cc), -pr, item))
        if candidates:
            candidates.sort()
            return candidates[0][2]

        # 3) مرادفات
        for syn in expand_with_synonyms(c):
            sc = canonical(syn)
            if sc in self.by_canon:
                return self.by_canon[sc][0]

        # 4) تشابه
        best_item = None
        best_score = 0.65
        for cc, _, item, _ in self.items:
            score = similarity_score(c, cc)
            if score > best_score:
                best_score = score
                best_item = item
        return best_item


class ReasoningEngine:
    def __init__(self, db, mem, retriever):
        self.db = db
        self.mem = mem
        self.retriever = retriever
        self.index = KnowledgeIndex(db)
        self.context = []

    def think(self, query):
        trace = []
        subj_raw = extract_subject_raw(query)
        if subj_raw:
            subj = strip_parens(subj_raw)
            trace.append("موضوع: " + subj)
        else:
            subj = query

        item = self.index.find(subj)
        if item:
            trace.append("وجدت في الفهرس")
            self._remember(subj)
            return item["a"], "index", 0.95, trace

        for kw in extract_keywords(query):
            item = self.index.find(kw)
            if item:
                trace.append("وجدت بكلمة: " + kw)
                self._remember(kw)
                return item["a"], "keyword", 0.85, trace

        try:
            best = self.retriever.best(query)
            if best:
                score, src, q, a = best
                if score >= 0.4:
                    return a, "retriever", score, trace
        except Exception:
            pass

        return None, "none", 0.0, trace

    def _remember(self, subj):
        self.context.append(subj)
        self.context = self.context[-5:]


_ENGINE = None

def get_engine(db, mem, retriever):
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = ReasoningEngine(db, mem, retriever)
    return _ENGINE
