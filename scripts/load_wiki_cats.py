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

def get_category_members(cat, limit=500):
    """يجلب أعضاء تصنيف."""
    out = []
    cont = None
    while len(out) < limit:
        p = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": "تصنيف:" + cat,
            "cmlimit": "500",
            "cmtype": "page",
        }
        if cont:
            p["cmcontinue"] = cont
        try:
            d = api(p)
        except Exception:
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

def get_extracts(titles):
    """يجلب ملخصات المقالات (50 في الطلب)."""
    out = {}
    for i in range(0, len(titles), 20):
        batch = titles[i:i+20]
        p = {
            "action": "query",
            "prop": "extracts",
            "exintro": "1",
            "explaintext": "1",
            "exchars": "500",
            "titles": "|".join(batch),
        }
        try:
            d = api(p)
            pages = d.get("query", {}).get("pages", {})
            for pid, page in pages.items():
                t = page.get("title", "")
                e = page.get("extract", "").strip()
                if t and e and len(e) > 40:
                    out[t] = e
        except Exception:
            pass
        time.sleep(0.05)
    return out

# التصنيفات العلمية الموسعة
CATEGORIES = [
    # فيزياء
    "فيزياء", "ميكانيكا الكم", "النسبية", "الكهرومغناطيسية",
    "فيزياء الجسيمات", "علم الفلك", "الفيزياء الفلكية",
    # كيمياء
    "كيمياء", "كيمياء عضوية", "كيمياء غير عضوية", "كيمياء حيوية",
    "عناصر كيميائية", "مركبات كيميائية", "تفاعلات كيميائية",
    # أحياء
    "علم الأحياء", "علم النبات", "علم الحيوان", "علم الوراثة",
    "الجهاز العصبي", "الجهاز الهضمي", "جهاز الدوران",
    "خلية", "عضلة", "عظم", "دم",
    # طب
    "طب", "أمراض", "أعراض طبية", "علم الأدوية",
    "تشريح", "فسيولوجيا", "علم المناعة",
    # رياضيات
    "رياضيات", "جبر", "هندسة رياضية", "تحليل رياضي",
    "نظرية الأعداد", "إحصاء", "احتمال",
    # تقنية
    "حاسوب", "برمجة", "ذكاء اصطناعي", "شبكات حاسوبية",
    "إنترنت", "قواعد بيانات", "أمن الحاسوب",
    # علوم أرض
    "جيولوجيا", "أرصاد جوية", "علم البيئة", "بحار ومحيطات",
    # فضاء
    "مجموعة الشمسية", "نجوم", "مجرات", "كواكب",
]

all_items = []
seen = set()

for cat in CATEGORIES:
    print("Category: " + cat)
    try:
        members = get_category_members(cat, limit=200)
        print("   Members: " + str(len(members)))
        if not members:
            continue
        extracts = get_extracts(members)
        added_here = 0
        for title, extract in extracts.items():
            q = "ما هو " + title + "؟"
            if q[:80] in seen:
                continue
            seen.add(q[:80])
            all_items.append({
                "q": q,
                "a": extract,
                "tags": ["wiki_cat", cat, "science"]
            })
            added_here += 1
        print("   Extracts: " + str(added_here))
        print("   Total so far: " + str(len(all_items)))
    except Exception as e:
        print("   ERR: " + str(e))

print("")
print("Collected total: " + str(len(all_items)))

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
