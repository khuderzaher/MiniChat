# -*- coding: utf-8 -*-
"""linguistic_engine.py — إدراك لغوي عربي عميق"""
import re
from arabic_utils import normalize_arabic, strip_definite


# أوزان عربية شائعة
PATTERNS = {
    "فاعل": "doer", "مفعول": "object", "فعّال": "intensive",
    "فعيل": "adj", "مفعل": "place", "استفعل": "request",
    "افتعل": "reflexive", "تفاعل": "mutual", "مفاعل": "instrument",
    "مفتعل": "passive", "فعالة": "profession", "فعولة": "abstract",
}


class ArabicMorphology:
    PRONOUN_SUFFIX = {
        "ه": "3ms", "ها": "3fs", "هم": "3mp", "هن": "3fp",
        "ك": "2ms", "كم": "2mp", "كن": "2fp",
        "ي": "1s", "ني": "1s_obj", "نا": "1p",
    }
    PRONOUN_PREFIX = {
        "أ": "1s", "ن": "1p", "ي": "3ms", "ت": "2"
    }

    @staticmethod
    def strip_all_affixes(w):
        w = normalize_arabic(w)
        w = strip_definite(w)
        # sufix
        for suf in sorted(ArabicMorphology.PRONOUN_SUFFIX, key=len, reverse=True):
            if w.endswith(suf) and len(w) - len(suf) >= 3:
                w = w[:-len(suf)]
                break
        # plural
        for suf in ("ات", "ون", "ين", "ان"):
            if w.endswith(suf) and len(w) - len(suf) >= 3:
                w = w[:-len(suf)]
                break
        # prefix
        for pref in ("است", "مست", "مت", "ان"):
            if w.startswith(pref) and len(w) - len(pref) >= 3:
                w = w[len(pref):]
                break
        for pref in ("ي", "ت", "ن", "أ", "م"):
            if w.startswith(pref) and len(w) > 4:
                w = w[1:]
                break
        return w

    @staticmethod
    def extract_root(word):
        w = ArabicMorphology.strip_all_affixes(word)
        # احتفظ بالحروف الأصلية
        letters = [c for c in w if c in "ابتثجحخدذرزسشصضطظعغفقكلمنهوي"]
        # احذف حروف العلة من الوسط
        consonants = [c for c in letters if c not in "اوي"]
        if len(consonants) >= 3:
            return "".join(consonants[:3])
        if len(letters) >= 3:
            return "".join(letters[:3])
        return w

    @staticmethod
    def identify_pattern(word):
        w = normalize_arabic(word)
        w = strip_definite(w)
        n = len(w)
        # تحقق من الأوزان
        if w.startswith("است") and n >= 6:
            return "استفعل"
        if w.startswith("مست") and n >= 6:
            return "مستفعل"
        if w.startswith("م") and n == 4:
            return "مفعل"
        if w.startswith("م") and n == 5:
            return "مفعلة"
        if w.startswith("ت") and n == 5:
            return "تفاعل"
        if w.startswith("ا") and n == 5:
            return "افتعل"
        if w.endswith("ة") and n == 5:
            return "فعالة"
        return "unknown"


class SentenceAnalyzer:
    QUESTION_WORDS = {"ما","ماذا","من","متى","أين","كيف","لماذا","هل","كم","أي"}
    CONDITIONAL = {"إذا","إن","لو","لولا","كلما","متى"}
    NEGATION = {"لا","ما","لم","لن","ليس","غير","بدون","دون"}
    EMPHASIS = {"إن","أن","لقد","قد","بالتأكيد","فعلا","حقا"}
    PREPOSITIONS = {"في","من","إلى","على","عن","مع","حتى","بين","حول"}

    @staticmethod
    def analyze(text):
        t = normalize_arabic(text)
        tokens = re.findall(r"[\u0600-\u06FF]+", t)
        result = {
            "type": "declarative",
            "subject": None,
            "object": None,
            "verb": None,
            "negated": False,
            "conditional": False,
            "question_word": None,
            "emphasis": [],
            "prepositions": [],
            "roots": [],
            "tokens": tokens,
        }

        # نوع الجملة
        if tokens and tokens[0] in SentenceAnalyzer.QUESTION_WORDS:
            result["type"] = "question"
            result["question_word"] = tokens[0]
        if any(w in t for w in SentenceAnalyzer.CONDITIONAL):
            result["conditional"] = True
            result["type"] = "conditional"

        # نفي
        result["negated"] = any(w in tokens for w in SentenceAnalyzer.NEGATION)

        # توكيد
        result["emphasis"] = [w for w in tokens if w in SentenceAnalyzer.EMPHASIS]

        # حروف جر
        result["prepositions"] = [w for w in tokens if w in SentenceAnalyzer.PREPOSITIONS]

        # جذور
        result["roots"] = [ArabicMorphology.extract_root(w) for w in tokens if len(w) > 3]

        # فاعل/مفعول مبسط
        for i, tok in enumerate(tokens):
            if tok in SentenceAnalyzer.PREPOSITIONS and i + 1 < len(tokens):
                result["object"] = result["object"] or tokens[i + 1]

        return result

    @staticmethod
    def summarize(analysis):
        """وصف لغوي مختصر."""
        parts = []
        types = {
            "question": "سؤال",
            "conditional": "جملة شرطية",
            "declarative": "جملة خبرية",
        }
        parts.append(types.get(analysis["type"], "جملة"))
        if analysis["negated"]:
            parts.append("منفية")
        if analysis["emphasis"]:
            parts.append("مؤكدة")
        if analysis["question_word"]:
            parts.append("أداة: " + analysis["question_word"])
        return " • ".join(parts)


if __name__ == "__main__":
    tests = ["ما هو القلب", "لماذا السماء زرقاء", "إذا درست نجحت", "لا أريد", "استخدام الحاسوب"]
    for t in tests:
        a = SentenceAnalyzer.analyze(t)
        print("%-25s → %s" % (t, SentenceAnalyzer.summarize(a)))
        print("   الجذور: %s" % a["roots"][:5])
