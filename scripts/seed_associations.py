# -*- coding: utf-8 -*-
"""scripts/seed_associations.py — يغذّي الترابطات من قاعدة البيانات."""
import json, pickle, os, sys, time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from arabic_utils import normalize_arabic

MEM_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "minichat_memory.pkl")
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "minichat_db.json")


def simple_tokens(text):
    """كلمات بسيطة (بدون تكرار الكلمة نفسها في الجملة)."""
    t = normalize_arabic(text)
    import re
    words = re.findall(r"[\u0600-\u06FF]{3,}", t)
    # شيل التكرار المتتالي
    out = []
    for w in words:
        if not out or out[-1] != w:
            out.append(w)
    return out


def load_memory():
    if os.path.exists(MEM_PATH):
        with open(MEM_PATH, "rb") as f:
            return pickle.load(f)
    return {}


def save_memory(d):
    with open(MEM_PATH, "wb") as f:
        pickle.dump(d, f)


def update_assoc(assoc, tokens, max_per_word=30):
    """نفس منطق update_associations لكن سريع."""
    n = len(tokens)
    for i, w in enumerate(tokens):
        bucket = assoc.setdefault(w, {})
        for j in range(max(0, i - 5), min(n, i + 6)):
            if j == i:
                continue
            v = tokens[j]
            weight = 5 - abs(j - i)
            bucket[v] = int(bucket.get(v, 0)) + weight
        # شذّب
        if len(bucket) > max_per_word * 2:
            top = sorted(bucket.items(), key=lambda x: -x[1])[:max_per_word]
            assoc[w] = dict(top)


def main():
    print("[SEED] تحميل قاعدة البيانات...")
    with open(DB_PATH, "r", encoding="utf-8") as f:
        db = json.load(f)
    faq = db.get("faq", [])
    print("[SEED] عدد العناصر: %d" % len(faq))

    print("[SEED] تحميل الذاكرة...")
    mem = load_memory()
    # نبدأ من الصفر
    old_assoc = mem.get("associations", {})
    print("[SEED] ترابطات قديمة: %d (سيتم استبدالها)" % len(old_assoc))
    assoc = {}

    t0 = time.time()
    processed = 0
    for item in faq:
        if not isinstance(item, dict):
            continue
        # نستخدم السؤال + الجواب (أول 200 حرف من الجواب)
        q = item.get("q", "")
        a = item.get("a", "")[:200]
        text = q + " " + a
        tokens = simple_tokens(text)
        if len(tokens) < 3:
            continue
        update_assoc(assoc, tokens)
        processed += 1
        if processed % 2000 == 0:
            print("[SEED] %d/%d ..." % (processed, len(faq)))

    # استبعد الكلمات العامة (تظهر في كثير من العناصر)
    print("[SEED] استبعاد الكلمات العامة...")
    doc_freq = {}
    for item in faq:
        if not isinstance(item, dict):
            continue
        text = (item.get("q", "") + " " + item.get("a", "")[:200])
        toks = set(simple_tokens(text))
        for t in toks:
            doc_freq[t] = doc_freq.get(t, 0) + 1
    # الكلمات اللي تظهر في >300 عنصر = عامة جداً
    common = {w for w, c in doc_freq.items() if c > 300}
    print("[SEED] عدد الكلمات العامة المستبعدة: %d" % len(common))
    # احذف العام من الترابطات
    for w in list(assoc.keys()):
        if w in common:
            del assoc[w]
            continue
        filtered = {k: v for k, v in assoc[w].items() if k not in common}
        if filtered:
            assoc[w] = filtered
        else:
            del assoc[w]

    # شذّب نهائي: top-10 فقط + حد أدنى
    print("[SEED] شذّب نهائي (top-10)...")
    for w in list(assoc.keys()):
        bucket = {k: v for k, v in assoc[w].items() if v >= 4}
        if bucket:
            top = sorted(bucket.items(), key=lambda x: -x[1])[:10]
            assoc[w] = dict(top)
        else:
            del assoc[w]

    mem["associations"] = assoc
    save_memory(mem)

    print("[SEED] ✅ انتهى في %.1f ثانية" % (time.time() - t0))
    print("[SEED] عدد الكلمات: %d" % len(assoc))
    print("[SEED] إجمالي الترابطات: %d" % sum(len(v) for v in assoc.values()))


if __name__ == "__main__":
    main()
