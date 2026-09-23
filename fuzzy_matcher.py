# -*- coding: utf-8 -*-
"""fuzzy_matcher.py — تصحيح أخطاء إملائية وتقريب"""
from arabic_utils import normalize_arabic, canonical


# قواعد أخطاء إملائية شائعة عربي
TYPO_MAP = {
    "أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا",
    "ئ": "ي", "ى": "ي",
    "ة": "ه",
    "ذ": "ز",
    "ظ": "ز",
    "ث": "س",
    "ص": "س",
    "ط": "ت",
    "ض": "د",
    "غ": "ق",
}

# حروف متشابهة على الكيبورد


# ═══════════════════════════════════════════════════════════════
# قاموس تصحيحات مخصص (أخطاء شائعة معروفة)
# ═══════════════════════════════════════════════════════════════
KNOWN_TYPOS = {
    "بايون": "بايثون",
    "البايون": "بايثون",
    "بايثن": "بايثون",
    "البايثن": "بايثون",
    "جافاسكرابت": "جافاسكريبت",
    "الاندرويد": "أندرويد",
    "الاندريود": "أندرويد",
    "انتلجنس": "الذكاء الاصطناعي",
    "القلبب": "القلب",
    "ادرويد": "أندرويد",
    "الادرويد": "أندرويد",
    "الفيروسات": "فيروس",
    "البكتريا": "بكتيريا",
    "المغرب": "المغرب",
    "برمجه": "برمجة",
    "البرمجه": "برمجة",
    "كمبيوتر": "حاسوب",
    "الكمبيوتر": "حاسوب",
    "موبايل": "هاتف",
    "الموبايل": "هاتف",
    "تليفون": "هاتف",
    "التليفون": "هاتف",
    "انترنت": "إنترنت",
    "الانترنت": "إنترنت",
    "نت": "إنترنت",
}

KEYBOARD_NEIGHBORS = {
    "ا": "لا", "ب": "نا", "ت": "بث", "ث": "ت", "ج": "حخ",
    "ح": "جخ", "خ": "حج", "د": "ذر", "ذ": "د", "ر": "دز",
    "ز": "ر", "س": "ش", "ش": "س", "ص": "ض", "ض": "ص",
    "ط": "ظ", "ظ": "ط", "ع": "غ", "غ": "ع", "ف": "ق",
    "ق": "ف", "ك": "ل", "ل": "ك", "م": "ن", "ن": "م",
    "ه": "ةو", "و": "هي", "ي": "وى",
}


def levenshtein(a, b, max_dist=3):
    """مسافة ليفنشتاين — عدد التعديلات بين سلسلتين."""
    if a == b:
        return 0
    if abs(len(a) - len(b)) > max_dist:
        return max_dist + 1
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cost = 0 if ca == cb else 1
            cur.append(min(cur[-1] + 1, prev[j] + 1, prev[j-1] + cost))
        prev = cur
    return prev[-1]


def damerau_levenshtein(a, b, max_dist=3):
    """مع دعم تبديل الحروف (نقل مقلوب)."""
    if a == b:
        return 0
    la, lb = len(a), len(b)
    if abs(la - lb) > max_dist:
        return max_dist + 1
    d = {}
    for i in range(-1, la + 1):
        d[(i, -1)] = i + 1
    for j in range(-1, lb + 1):
        d[(-1, j)] = j + 1
    for i in range(la):
        for j in range(lb):
            cost = 0 if a[i] == b[j] else 1
            d[(i, j)] = min(
                d.get((i-1, j), 0) + 1,
                d.get((i, j-1), 0) + 1,
                d.get((i-1, j-1), 0) + cost,
            )
            if i > 0 and j > 0 and a[i] == b[j-1] and a[i-1] == b[j]:
                d[(i, j)] = min(d[(i, j)], d.get((i-2, j-2), 0) + 1)
    return d.get((la-1, lb-1), max_dist + 1)


def arabic_typo_normalize(word):
    """يطبق خريطة الأخطاء الشائعة."""
    w = normalize_arabic(word)
    out = []
    for c in w:
        out.append(TYPO_MAP.get(c, c))
    return "".join(out)


def correct_word(word, vocabulary, max_dist=2):
    """يجد أقرب كلمة في القاموس."""
    if not word or len(word) < 3:
        return word
    w = arabic_typo_normalize(word)
    w_canon = canonical(w)
    if not w_canon:
        return word

    # 0) تصحيحات مخصصة معروفة (أولوية عليا)
    if w in KNOWN_TYPOS:
        return KNOWN_TYPOS[w]
    # جرّب بدون "ال"
    w_nolef = w[2:] if w.startswith("ال") else w
    if w_nolef in KNOWN_TYPOS:
        return KNOWN_TYPOS[w_nolef]
    if ("ال" + w_nolef) in KNOWN_TYPOS:
        return KNOWN_TYPOS["ال" + w_nolef]

    # 1) تام
    if w_canon in vocabulary:
        return w_canon

    # 2) ابحث عن الأفضل
    best = None
    best_d = max_dist + 1
    best_sim = 0.0
    for cand in vocabulary:
        c_canon = canonical(cand)
        if not c_canon:
            continue
        if abs(len(c_canon) - len(w_canon)) > 2:
            continue
        d = levenshtein(w_canon, c_canon, max_dist)
        if d > max_dist:
            continue
        # التشابه النسبي (جاكار على الأحرف)
        mlen = max(len(w_canon), len(c_canon))
        sim = 1.0 - (d / mlen) if mlen else 0.0
        # نقبل لو sim > 0.6
        if sim < 0.6:
            continue
        # bonus للـ prefix match (قمر يفوز على قدم لـ "قم")
        prefix_bonus = 0
        if c_canon.startswith(w_canon) or w_canon.startswith(c_canon):
            prefix_bonus = -1  # يقلل المفتاح = أولوية أعلى
        # فضّل: prefix أولاً، ثم d الأقل، ثم sim الأعلى، ثم الطول الأقرب
        len_diff = abs(len(c_canon) - len(w_canon))
        key = (prefix_bonus, d, -sim, len_diff)
        if best is None:
            best = c_canon
            best_d = d
            best_sim = sim
        else:
            old_prefix = 0
            if best.startswith(w_canon) or w_canon.startswith(best):
                old_prefix = -1
            old_key = (old_prefix, best_d, -best_sim, abs(len(best) - len(w_canon)))
            if key < old_key:
                best = c_canon
                best_d = d
                best_sim = sim

    if best:
        return best
    return word
    w = arabic_typo_normalize(word)
    w_canon = canonical(w)

    # 1) تام
    if w_canon in vocabulary:
        return w_canon

    # 2) ابحث في القاموس
    best = None
    best_d = max_dist + 1
    for cand in vocabulary:
        c_canon = canonical(cand)
        if not c_canon:
            continue
        # اختصار: فقط لو نفس الطول ± 2
        if abs(len(c_canon) - len(w_canon)) > 2:
            continue
        d = levenshtein(w_canon, c_canon, max_dist)
        if d < best_d:
            best_d = d
            best = c_canon
            if d == 1:
                break

    if best and best_d <= max_dist:
        # فقط لو التشابه 70%+ (تجنب "بايون"→"أيون")
        sim = 1.0 - (best_d / max(len(w_canon), len(best), 1))
        if sim >= 0.75:
            return best
    return word


def correct_sentence(text, vocabulary, max_dist=2):
    """يصلح كلمات الجملة."""
    from arabic_utils import extract_core_tokens
    tokens = text.split()
    out = []
    for tok in tokens:
        # احتفظ بعلامات الترقيم
        if len(tok) < 3 or not any('\u0600' <= c <= '\u06ff' for c in tok):
            out.append(tok)
            continue
        corrected = correct_word(tok, vocabulary, max_dist)
        out.append(corrected)
    return " ".join(out)


if __name__ == "__main__":
    tests = ["القلبب", "البايون", "الفيروسات", "المخ"]
    vocab = {"قلب", "بايثون", "فيروس", "دماغ", "المخ", "الفيروس"}
    for t in tests:
        c = correct_word(t, vocab)
        print("%-12s → %s" % (t, c))
