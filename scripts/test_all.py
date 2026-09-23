# -*- coding: utf-8 -*-
"""scripts/test_all.py — اختبارات شاملة لـ MiniChat."""
import sys, os, json, time
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
os.chdir(BASE)

results = []

def test(name, condition, expected=None, got=None):
    ok = bool(condition)
    results.append((name, ok, expected, got))
    status = "PASS" if ok else "FAIL"
    print("[%s] %s" % (status, name))
    if not ok and (expected is not None or got is not None):
        print("      متوقع: %s" % str(expected)[:80])
        print("      حصلنا: %s" % str(got)[:80])


def main():
    print("=" * 60)
    print("اختبارات MiniChat الشاملة")
    print("=" * 60)

    print("\n[1] تحميل المكونات...")
    from main import DialogueManager, MemoryStore, Retriever, StructuredDB, simple_tokens
    from arabic_utils import normalize_arabic
    with open('minichat_db.json', 'r', encoding='utf-8') as f:
        raw = json.load(f)
    db = StructuredDB()
    mem = MemoryStore()
    dm = DialogueManager(db, mem, Retriever(db, mem))
    test("تهيئة DialogueManager", True)

    print("\n[2] اختبار التوكنايزر...")
    t = simple_tokens("ما هي فوائد فيتامين د")
    test("كلمة 'د' محفوظة", "د" in t, ["د"], t)
    test("'هاء' ≠ 'د'", "هاء" not in t)
    t2 = simple_tokens("ما هي سورة الكوثر")
    test("'كوثر' موجودة", "كوثر" in t2, ["كوثر"], t2)

    print("\n[3] اختبار extract_topic...")
    from understanding_engine import extract_topic
    test("فيتامين د كامل", "د" in extract_topic("ما هي فوائد فيتامين د"))
    test("سورة الكوثر كامل", "كوثر" in extract_topic("ما هي سورة الكوثر"))

    print("\n[4] اختبار قاعدة البيانات...")
    total = len(raw.get("faq", []))
    test("عدد FAQ >= 27,000", total >= 27000, ">=27000", total)
    has_nutrition = any(isinstance(i, dict) and "nutrition" in (i.get("tags") or []) for i in raw["faq"][:30000])
    test("بيانات تغذية موجودة", has_nutrition)
    has_health = any(isinstance(i, dict) and "health" in (i.get("tags") or []) for i in raw["faq"][:30000])
    test("بيانات صحة موجودة", has_health)

    print("\n[5] اختبار الأوامر (~)...")
    def shortcut(text):
        try:
            handled, reply = dm._shortcut(text)
            return reply if handled else None
        except Exception as e:
            return "ERROR: %s" % e

    r = shortcut("~مساعدة")
    test("~مساعدة ترجع نص", r and len(r) > 100)
    r = shortcut("~ذاكرة")
    test("~ذاكرة ترجع نص", r and "ذاكرة" in r)
    r = shortcut("~إحصاء")
    test("~إحصاء ترجع نص", r and ("إحصاء" in r or "عدد" in r))
    r = shortcut("~عائلة علم")
    test("~عائلة علم", r and "علم" in r)
    r = shortcut("~سبب مطر")
    test("~سبب مطر", r and ("مطر" in r or "تبخر" in r))
    r = shortcut("~يؤدي شمس")
    test("~يؤدي شمس", r and "شمس" in r)
    r = shortcut("~مسار مطر إلى حياه")
    test("~مسار مطر→حياه", r and "مسار" in r.lower())
    r = shortcut("~فجوات")
    test("~فجوات", r is not None and (isinstance(r, str) and len(r) > 5), "نص", str(r)[:60] if r else None)
    r = shortcut("~حالة")
    test("~حالة", r and ("النموذج" in r or "شغال" in r or "متوقف" in r))

    print("\n[6] اختبار الرياضيات...")
    r = dm.respond("3+5*2")
    test("3+5*2 = 13", "13" in r, "13", r[:50])
    r = dm.respond("10% من 250")
    test("10% من 250 = 25", "25" in r, "25", r[:50])

    print("\n[7] اختبار الفلتر (منع الردود الخاطئة)...")
    r = dm.respond("ما هي فوائد فيتامين د")
    # يجب ألا يحتوي على "هاء" أو "Vitamin E"
    test("فيتامين د لا يرجّع هاء", "هاء" not in r and "Vitamin E" not in r, "بدون هاء", r[:80])

    print("\n[8] اختبار التحقق...")
    # نتحقق من دالة _verify_match
    ok = dm._verify_match("ما هي سورة الكوثر", "سورة الكوثر سورة مكية من القرآن")
    test("_verify_match (نفس الموضوع)", ok)
    not_ok = dm._verify_match("ما هي سورة الكوثر", "سورة البلد سورة مكية طويلة")
    test("_verify_match (موضوع مختلف)", not not_ok, False, not_ok)

    print("\n[9] اختبار المزاج...")
    from mood_engine import detect_mood
    m, c, _ = detect_mood("أنا زعلان اليوم")
    test("كشف الحزن", m == "حزن", "حزن", m)
    m, c, _ = detect_mood("خلص! نجحت")
    test("كشف الفرح", m == "فرح", "فرح", m)

    print("\n[10] اختبار الشبكة المعرفية...")
    from knowledge_graph import get_knowledge_graph
    kg = get_knowledge_graph()
    stats = kg.stats()
    test("الشبكة فيها عقد", stats["nodes"] > 100, ">100", stats["nodes"])
    p = kg.path("مطر", "حياة")
    test("مسار مطر → حياة", p is not None)

    print("\n[11] اختبار فلتر التنقية...")
    from llm_bridge import clean_arabic, _dedup_ngrams
    t = clean_arabic("نص عربي уникай")
    test("يشيل الروسي", "уникай" not in t, "بدون روسي", t)
    t = _dedup_ngrams("كلمة " * 50, min_len=25)
    test("_dedup_ngrams يقلص", len(t) < 100, "<100", len(t))

    print("\n[12] اختبار تتبع السياق...")
    try:
        from context_tracker import ContextTracker
        ct = ContextTracker()
        ct.add_turn("ما هي سورة الكوثر", "سورة الكوثر سورة مكية...")
        r = ct.resolve_pronoun("كم آية فيها؟")
        test("كم آية فيها → كم عدد آيات سورة الكوثر",
             r and "سورة الكوثر" in r.get("new_question", "") and "كم عدد ايات" in r.get("new_question", ""),
             "rewrite", r.get("new_question") if r else None)

        ct.add_turn("ما هو القلب", "القلب عضو عضلي...")
        r = ct.resolve_pronoun("ما وظيفته؟")
        test("ما وظيفته → وظيفة القلب",
             r and "القلب" in r.get("new_question", ""),
             "rewrite", r.get("new_question") if r else None)

        r = ct.resolve_pronoun("أكمل")
        test("أكمل → continue",
             r and r.get("action") == "continue",
             "continue", r.get("action") if r else None)

        r = ct.resolve_pronoun("ما هو؟")
        test("ما هو؟ → rewrite",
             r and r.get("action") == "rewrite",
             "rewrite", r.get("action") if r else None)
    except Exception as e:
        test("تتبع السياق", False, "يعمل", str(e))

    print("\n" + "=" * 60)
    passed = sum(1 for _, ok, _, _ in results if ok)
    total_tests = len(results)
    print("النتيجة: %d / %d" % (passed, total_tests))
    if passed == total_tests:
        print("🎯 كل الاختبارات نجحت!")
    else:
        print("⚠️  في %d اختبار فشل" % (total_tests - passed))
        print("\nالفاشلة:")
        for name, ok, exp, got in results:
            if not ok:
                print("  - %s" % name)
    print("=" * 60)


if __name__ == "__main__":
    main()
