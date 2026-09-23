# -*- coding: utf-8 -*-
import json, urllib.request, urllib.parse, time
from pathlib import Path

DB = Path("minichat_db.json")
API = "https://ar.wikipedia.org/w/api.php"

def api(params):
    params["format"] = "json"
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "MiniChat/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))

def search_articles(keyword, limit=200):
    """يبحث عن مقالات بكلمة مفتاحية."""
    out = []
    offset = 0
    while len(out) < limit:
        p = {
            "action": "query",
            "list": "search",
            "srsearch": keyword,
            "srlimit": "50",
            "sroffset": str(offset),
            "srnamespace": "0",
        }
        try:
            d = api(p)
        except Exception:
            break
        results = d.get("query", {}).get("search", [])
        if not results:
            break
        for r in results:
            t = r.get("title", "")
            if t:
                out.append(t)
        offset += 50
        if offset > 500:
            break
        time.sleep(0.1)
    return out[:limit]

def get_extracts(titles):
    """يجلب ملخصات (20 في الطلب)."""
    out = {}
    for i in range(0, len(titles), 20):
        batch = titles[i:i+20]
        p = {
            "action": "query",
            "prop": "extracts",
            "exintro": "1",
            "explaintext": "1",
            "exchars": "600",
            "titles": "|".join(batch),
        }
        try:
            d = api(p)
            pages = d.get("query", {}).get("pages", {})
            for pid, page in pages.items():
                t = page.get("title", "")
                e = page.get("extract", "").strip()
                if t and e and len(e) > 40 and not t.startswith(("قائمة", "تصنيف")):
                    out[t] = e
        except Exception:
            pass
        time.sleep(0.05)
    return out

# كلمات البحث الشاملة
KEYWORDS = [
    # أحياء وطب
    "علم الأحياء", "علم الوراثة", "خلية", "دم", "عضلة", "عظم",
    "جهاز عصبي", "جهاز هضمي", "جهاز دوران", "جهاز مناعي",
    "طب", "أمراض", "أعراض طبية", "تشريح", "فسيولوجيا",
    "علم الأدوية", "جراحة", "تغذية", "فيتامين", "هرمون",
    "دماغ", "قلب", "كبد", "رئة", "كلية", "معدة",
    # رياضيات
    "رياضيات", "جبر", "هندسة رياضية", "تحليل رياضي",
    "نظرية الأعداد", "إحصاء", "احتمال", "حساب تفاضلي",
    # تقنية
    "حاسوب", "برمجة", "ذكاء اصطناعي", "شبكة حاسوبية",
    "إنترنت", "قاعدة بيانات", "أمن الحاسوب", "خوارزمية",
    "لغة برمجة", "نظام تشغيل", "تطبيق ويب",
    # علوم أرض
    "جيولوجيا", "علم الأرصاد الجوية", "علم البيئة",
    "محيط", "نهر", "جبل", "بركان", "زلزال",
    # فضاء
    "مجموعة شمسية", "نجم", "مجرة", "كوكب", "قمر",
    "مذنب", "ثقب أسود", "مستعر", "نيزك",
    # فيزياء
    "طاقة", "ضوء", "صوت", "حرارة", "كهرباء", "مغناطيسية",
    "ذرة", "جزيء", "إلكترون", "بروتون", "نيوترون",
    # كيمياء
    "عنصر كيميائي", "مركب كيميائي", "تفاعل كيميائي",
    "حمض", "قاعدة", "ملح", "بوليمر",
    # فلسفة ومنطق
    "فلسفة", "منطق", "أخلاق", "ميتافيزيقا", "معرفة",
]

all_items = []
seen = set()

for kw in KEYWORDS:
    print("Search: " + kw)
    try:
        titles = search_articles(kw, limit=150)
        if not titles:
            print("   0")
            continue
        extracts = get_extracts(titles)
        added_here = 0
        for title, extract in extracts.items():
            q = "ما هو " + title + "؟"
            if q[:80] in seen:
                continue
            seen.add(q[:80])
            all_items.append({
                "q": q,
                "a": extract,
                "tags": ["wiki_search", kw, "science"]
            })
            added_here += 1
        print("   +" + str(added_here) + " (total " + str(len(all_items)) + ")")
    except Exception as e:
        print("   ERR: " + str(e))

print("")
print("Total collected: " + str(len(all_items)))

if all_items:
    with open(DB, "r", encoding="utf-8") as f:
        db = json.load(f)
    existing = {x.get("q","")[:80] for x in db.get("faq", [])}
    added = 0
    for it in all_items:
        if it["q"][:80] not in existing:
            db["faq"].append(it)
            existing.add(it["q"][:80])
            added += 1
    with open(DB, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)
    print("Added: " + str(added))
    print("Total DB: " + str(len(db["faq"])))
print("DONE")
