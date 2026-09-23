# -*- coding: utf-8 -*-
"""
mega_load.py — تحميل ضخم من 6 مصادر
يحفظ التقدم تلقائيًا (resume)
"""
import json, urllib.request, urllib.parse, time
from pathlib import Path

DB = Path("minichat_db.json")
PROGRESS = Path("mega_progress.json")
API = "https://ar.wikipedia.org/w/api.php"


# ================= أدوات =================
def api_call(params, retries=3):
    params["format"] = "json"
    url = API + "?" + urllib.parse.urlencode(params)
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "MiniChat/1.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception:
            time.sleep(0.5)
    return None

def load_progress():
    if PROGRESS.exists():
        try:
            return json.loads(PROGRESS.read_text())
        except Exception:
            pass
    return {"done_sources": [], "total_added": 0}

def save_progress(p):
    PROGRESS.write_text(json.dumps(p, ensure_ascii=False, indent=2))

def add_to_db(items, tag):
    """يضيف عناصر لقاعدة البيانات ويعيد عدد المضاف."""
    if not items:
        return 0
    with open(DB, "r", encoding="utf-8") as f:
        db = json.load(f)
    existing = {x.get("q","")[:80] for x in db.get("faq", [])}
    added = 0
    for it in items:
        k = it["q"][:80]
        if k not in existing:
            db["faq"].append(it)
            existing.add(k)
            added += 1
    with open(DB, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)
    return added


# ================= المصدر 1: الأحاديث النبوية =================
def load_hadith():
    print("\n[1/6] الأحاديث النبوية (9 كتب)...")
    books = [
        ("bukhari", "صحيح البخاري"),
        ("muslim", "صحيح مسلم"),
        ("abudawud", "سنن أبي داود"),
        ("tirmidhi", "سنن الترمذي"),
        ("nasai", "سنن النسائي"),
        ("ibnmajah", "سنن ابن ماجه"),
        ("malik", "موطأ مالك"),
        ("ahmed", "مسند أحمد"),
        ("darimi", "سنن الدارمي"),
    ]
    items = []
    for slug, name in books:
        count_for_book = 0
        for i in range(1, 400):
            try:
                url = "https://api.hadith.gading.dev/books/%s/%d" % (slug, i)
                req = urllib.request.Request(url, headers={"User-Agent": "MiniChat/1.0"})
                with urllib.request.urlopen(req, timeout=8) as resp:
                    d = json.loads(resp.read().decode("utf-8"))
                hadiths = d.get("data", {}).get("hadiths", [])
                for h in hadiths:
                    txt = h.get("arab", "").strip()
                    num = h.get("number", i)
                    if txt and len(txt) > 30:
                        items.append({
                            "q": "حديث رقم %s من %s" % (str(num), name),
                            "a": txt,
                            "tags": ["hadith", slug, name]
                        })
                        count_for_book += 1
            except Exception:
                pass
        print("   %s: +%d" % (name, count_for_book))
    return items


# ================= المصدر 2: تصنيفات ويكيبيديا (تاريخ+جغرافيا) =================
def wiki_extracts(titles):
    out = {}
    for i in range(0, len(titles), 20):
        batch = titles[i:i+20]
        d = api_call({
            "action": "query", "prop": "extracts",
            "exintro": "1", "explaintext": "1", "exchars": "600",
            "titles": "|".join(batch),
        })
        if d:
            pages = d.get("query", {}).get("pages", {})
            for pid, page in pages.items():
                t = page.get("title", "")
                e = page.get("extract", "").strip()
                if t and e and len(e) > 40 and not t.startswith(("قائمة", "تصنيف")):
                    out[t] = e
        time.sleep(0.05)
    return out

def wiki_category(cat, limit=300):
    out = []
    cont = None
    while len(out) < limit:
        p = {"action": "query", "list": "categorymembers",
             "cmtitle": "تصنيف:" + cat, "cmlimit": "500",
             "cmtype": "page"}
        if cont:
            p["cmcontinue"] = cont
        d = api_call(p)
        if not d:
            break
        members = d.get("query", {}).get("categorymembers", [])
        if not members:
            break
        out.extend([m["title"] for m in members])
        cont = d.get("continue", {}).get("cmcontinue")
        if not cont:
            break
        time.sleep(0.1)
    return out[:limit]

def load_history_geo():
    print("\n[2/6] التاريخ والجغرافيا...")
    cats = [
        "تاريخ", "تاريخ إسلامي", "الدولة العباسية", "الدولة الأموية",
        "الدولة العثمانية", "الحضارة الإسلامية", "التاريخ الإسلامي",
        "معارك", "حروب", "ثورات", "امبراطوريات قديمة",
        "جغرافيا", "دول", "عواصم", "مدن", "أنهار", "جبال",
        "بحار", "محيطات", "جزر", "صحاري", "قارات",
        "الوطن العربي", "الشرق الأوسط", "أفريقيا", "آسيا", "أوروبا",
    ]
    items = []
    for cat in cats:
        print("   %s..." % cat)
        members = wiki_category(cat, limit=200)
        extracts = wiki_extracts(members)
        for t, e in extracts.items():
            items.append({"q": "ما هو " + t + "؟", "a": e,
                          "tags": ["wiki_cat", cat, "history_geo"]})
        print("      +%d (total %d)" % (len(extracts), len(items)))
    return items


# ================= المصدر 3: الأدب واللغة =================
def load_literature():
    print("\n[3/6] الأدب واللغة العربية...")
    cats = [
        "أدب عربي", "شعر عربي", "شعراء عرب", "كتاب عرب",
        "روائيون عرب", "روايات عربية", "أدباء عرب",
        "علم النحو", "علم البلاغة", "قواعد اللغة العربية",
        "معاجم عربية", "أمثال عربية", "حكم عربية",
        "أدب إسلامي", "لغة عربية",
    ]
    items = []
    for cat in cats:
        print("   %s..." % cat)
        members = wiki_category(cat, limit=200)
        extracts = wiki_extracts(members)
        for t, e in extracts.items():
            items.append({"q": "ما هو " + t + "؟", "a": e,
                          "tags": ["wiki_cat", cat, "literature"]})
        print("      +%d (total %d)" % (len(extracts), len(items)))
    return items


# ================= المصدر 4: الدين والفقه =================
def load_religion():
    print("\n[4/6] الدين والفقه...")
    cats = [
        "إسلام", "القرآن", "التفسير", "علوم القرآن",
        "الفقه الإسلامي", "أصول الفقه", "الحديث النبوي",
        "علوم الحديث", "السيرة النبوية", "الصحابة",
        "الفقه الحنفي", "الفقه الشافعي", "الفقه المالكي", "الفقه الحنبلي",
        "التوحيد", "العقيدة الإسلامية", "التصوف",
        "رمضان", "الحج", "الصلاة", "الزكاة", "الصوم",
    ]
    items = []
    for cat in cats:
        print("   %s..." % cat)
        members = wiki_category(cat, limit=200)
        extracts = wiki_extracts(members)
        for t, e in extracts.items():
            items.append({"q": "ما هو " + t + "؟", "a": e,
                          "tags": ["wiki_cat", cat, "religion"]})
        print("      +%d (total %d)" % (len(extracts), len(items)))
    return items


# ================= المصدر 5: الفلسفة والمنطق =================
def load_philosophy():
    print("\n[5/6] الفلسفة والمنطق...")
    cats = [
        "فلسفة", "منطق", "أخلاق", "ميتافيزيقا", "نظرية المعرفة",
        "فلسفة إسلامية", "الفلسفة اليونانية", "الفلسفة الحديثة",
        "فلاسفة مسلمون", "فلاسفة غربيون",
        "علم النفس", "علم الاجتماع", "الاقتصاد",
    ]
    items = []
    for cat in cats:
        print("   %s..." % cat)
        members = wiki_category(cat, limit=200)
        extracts = wiki_extracts(members)
        for t, e in extracts.items():
            items.append({"q": "ما هو " + t + "؟", "a": e,
                          "tags": ["wiki_cat", cat, "philosophy"]})
        print("      +%d (total %d)" % (len(extracts), len(items)))
    return items


# ================= المصدر 6: التقنية والطب =================
def load_tech_med():
    print("\n[6/6] التقنية والطب...")
    cats = [
        "تقنية", "حوسبة", "برمجة", "ذكاء اصطناعي",
        "شبكات", "إنترنت", "هواتف ذكية", "روبوتات",
        "طب", "أمراض", "تشريح", "فسيولوجيا",
        "علم الأدوية", "جراحة", "طب الأسنان", "صحة عامة",
        "هندسة", "فيزياء تطبيقية", "كيمياء تطبيقية",
    ]
    items = []
    for cat in cats:
        print("   %s..." % cat)
        members = wiki_category(cat, limit=150)
        extracts = wiki_extracts(members)
        for t, e in extracts.items():
            items.append({"q": "ما هو " + t + "؟", "a": e,
                          "tags": ["wiki_cat", cat, "tech_med"]})
        print("      +%d (total %d)" % (len(extracts), len(items)))
    return items


# ================= التشغيل الرئيسي =================
def main():
    progress = load_progress()
    print("=" * 60)
    print("  التحميل الشامل — 6 مصادر")
    print("  المنجز سابقًا: %s" % (progress["done_sources"] or "لا شيء"))
    print("=" * 60)

    sources = [
        ("hadith",       load_hadith),
        ("history_geo",  load_history_geo),
        ("literature",   load_literature),
        ("religion",     load_religion),
        ("philosophy",   load_philosophy),
        ("tech_med",     load_tech_med),
    ]

    for key, loader in sources:
        if key in progress["done_sources"]:
            print("\n[SKIP] %s — مكتمل" % key)
            continue
        try:
            items = loader()
            n = add_to_db(items, key)
            progress["done_sources"].append(key)
            progress["total_added"] += n
            save_progress(progress)
            print("   ✅ %s: +%d (إجمالي: %d)" % (key, n, progress["total_added"]))
        except KeyboardInterrupt:
            print("\n⚠️ توقف بيد المستخدم — Progress محفوظ")
            raise
        except Exception as e:
            print("   ❌ %s: %s" % (key, e))

    # النتيجة النهائية
    with open(DB, "r", encoding="utf-8") as f:
        db = json.load(f)
    print("")
    print("=" * 60)
    print("  ✅ اكتمل التحميل الشامل")
    print("  إجمالي المضاف: %d" % progress["total_added"])
    print("  إجمالي قاعدة البيانات: %d" % len(db["faq"]))
    print("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nتم الإيقاف — أعد التشغيل للاستكمال.")
