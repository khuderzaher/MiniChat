# -*- coding: utf-8 -*-
"""derivation_engine.py — ربط الجذور والاشتقاق العربي"""
import re
from collections import defaultdict
from arabic_utils import normalize_arabic, strip_definite, canonical


# حروف العلة
VOWELS = set("اويىآإأ")

# أوزان عربية معروفة
PATTERNS = [
    ("استفعل", "است", "request"),
    ("مستفعل", "مست", "passive"),
    ("مفاعل", "مفا", "instrument"),
    ("متفاعل", "متفا", "mutual"),
    ("مفتعل", "مفت", "passive"),
    ("انفعل", "ان", "reflexive"),
    ("افعل", "ا", "causative"),
    ("تفعل", "ت", "reflexive"),
    ("مفعل", "م", "place_or_tool"),
    ("فعال", None, "intensive"),
    ("فعّال", None, "intensive"),
    ("فعيل", None, "adjective"),
    ("فعول", None, "adjective"),
    ("فعلة", None, "single_action"),
    ("فعالة", None, "profession"),
    ("فعلان", None, "state"),
]


class RootExtractor:
    """يستخرج جذور الكلمات العربية."""
    PREFIXES = ["ال", "وال", "بال", "كال", "فال", "لل",
                "است", "مست", "مت", "ان", "الم", "وال"]
    SUFFIXES = ["ات", "ون", "ين", "ان", "ها", "هم", "هن",
                "كم", "كن", "نا", "ني", "ية", "ية", "ه", "ي", "ك"]

    @staticmethod
    def extract(word):
        w = normalize_arabic(word)
        w = strip_definite(w)

        # شيل السوابق
        changed = True
        while changed:
            changed = False
            for p in RootExtractor.PREFIXES:
                if w.startswith(p) and len(w) - len(p) >= 3:
                    w = w[len(p):]
                    changed = True
                    break

        # شيل اللواحق
        changed = True
        while changed:
            changed = False
            for s in RootExtractor.SUFFIXES:
                if w.endswith(s) and len(w) - len(s) >= 3:
                    w = w[:-len(s)]
                    changed = True
                    break

        # حالات خاصة (أفعال + أسماء)
        SPECIAL_MAP = {
            # النوم
            "نوم": "نوم", "منام": "نوم", "ننام": "نوم",
            "تنام": "نوم", "ينام": "نوم", "نام": "نوم",
            # المطر
            "مطر": "مطر", "مطرة": "مطر", "امطار": "مطر",
            "تمطر": "مطر", "يمطر": "مطر", "امطر": "مطر",
            # الشرب
            "شرب": "شرب", "نشرب": "شرب", "يشرب": "شرب",
            "أشرب": "شرب", "اشرب": "شرب",
            # الأكل
            "اكل": "اكل", "طعام": "اكل", "نأكل": "اكل",
            "يأكل": "اكل", "أكل": "اكل",
            # الكتابة
            "كتب": "كتب", "كتاب": "كتب", "نكتب": "كتب",
            "يكتب": "كتب",
            # الماء
            "ماء": "ماء", "مياه": "ماء", "مائية": "ماء",
            # الشمس
            "شمس": "شمس", "شمسي": "شمس",
            # القمر
            "قمر": "قمر", "قمري": "قمر",
            # الريح
            "ريح": "ريح", "رياح": "ريح", "تهب": "ريح",
        }
        if w in SPECIAL_MAP:
            return SPECIAL_MAP[w]
        # استخرج الحروف الصحيحة
        consonants = [c for c in w if c not in VOWELS]
        if len(consonants) >= 3:
            return "".join(consonants[:3])
        if len(consonants) == 2:
            # جذر معتل ثنائي
            return "".join(consonants)
        return w[:3] if len(w) >= 3 else w

    @staticmethod
    def identify_pattern(word):
        """يتعرف على الوزن."""
        w = normalize_arabic(word)
        w = strip_definite(w)
        n = len(w)
        if n < 3:
            return None
        for name, prefix, meaning in PATTERNS:
            if prefix and w.startswith(prefix):
                return {"name": name, "meaning": meaning}
        if n == 3:
            return {"name": "فعل", "meaning": "root_form"}
        if n == 4:
            if w[0] in "أم":
                return {"name": "أفعل/مفعل", "meaning": "causative_or_place"}
            return {"name": "فعلل", "meaning": "quadriliteral"}
        if n == 5:
            if w.endswith("ة"):
                return {"name": "فعلة", "meaning": "instance"}
            return {"name": "تفاعل", "meaning": "mutual"}
        return {"name": "unknown", "meaning": "complex"}


class RootIndex:
    """فهرس الكلمات حسب الجذور."""
    def __init__(self, db=None, words=None):
        self.root_to_words = defaultdict(set)
        self.word_to_root = {}
        self._built = False

        import os as _os, pickle as _pickle
        cache_path = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "root_index_cache.pkl")

        # 1) حاول التحميل من الكاش
        if db is not None and _os.path.exists(cache_path):
            try:
                with open(cache_path, 'rb') as _f:
                    d = _pickle.load(_f)
                self.root_to_words = defaultdict(set, {k: set(v) for k, v in d['root_to_words'].items()})
                self.word_to_root = d['word_to_root']
                self._built = True
                print("[DERIV] تم التحميل من الكاش: %d جذر، %d كلمة"
                      % (len(self.root_to_words), len(self.word_to_root)))
                return
            except Exception as _e:
                print("[DERIV] فشل تحميل الكاش: %s" % _e)

        # 2) بناء من الصفر
        if db is not None:
            self._build_from_db(db)
            try:
                with open(cache_path, 'wb') as _f:
                    _pickle.dump({
                        'root_to_words': {k: list(v) for k, v in self.root_to_words.items()},
                        'word_to_root': self.word_to_root,
                    }, _f)
                print("[DERIV] تم حفظ الكاش")
            except Exception as _e:
                print("[DERIV] فشل حفظ الكاش: %s" % _e)
        elif words:
            for w in words:
                self.add_word(w)

    def _build_from_db(self, db):
        """يبني الفهرس من قاعدة البيانات."""
        for item in db.faq_entries():
            if not isinstance(item, dict):
                continue
            text = item.get("q", "") + " " + item.get("a", "")[:200]
            tokens = re.findall(r"[\u0600-\u06FF]{3,}", normalize_arabic(text))
            for tok in tokens:
                self.add_word(tok)
        self._built = True
        print("[DERIV] الجذور: %d، الكلمات: %d"
              % (len(self.root_to_words), len(self.word_to_root)))

    def add_word(self, word):
        w = strip_definite(normalize_arabic(word))
        if len(w) < 3:
            return
        root = RootExtractor.extract(w)
        if not root or len(root) < 2:
            return
        self.word_to_root[w] = root
        self.root_to_words[root].add(w)

    def family(self, word, limit=15):
        """يعيد عائلة الكلمة (كل الكلمات بنفس الجذر)."""
        w = strip_definite(normalize_arabic(word))
        root = self.word_to_root.get(w) or RootExtractor.extract(w)
        if not root:
            return []
        family = sorted(self.root_to_words.get(root, []), key=len)
        # استبعد الكلمة نفسها
        return [x for x in family if x != w][:limit]

    def roots_of(self, text):
        """استخرج جذور نص."""
        tokens = re.findall(r"[\u0600-\u06FF]{3,}", normalize_arabic(text))
        return list({RootExtractor.extract(t) for t in tokens if len(t) >= 3})

    def words_with_root(self, root):
        """كل الكلمات بجذر معين."""
        return sorted(self.root_to_words.get(root, []))


if __name__ == "__main__":
    tests = ["القلب", "الكتاب", "استخدام", "المدرسة", "علماء", "يكتب"]
    for t in tests:
        r = RootExtractor.extract(t)
        p = RootExtractor.identify_pattern(t)
        print("%-12s → جذر: %-5s  وزن: %s" % (t, r, p["name"] if p else "?"))
