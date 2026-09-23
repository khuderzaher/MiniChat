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

def search(kw, limit=150):
    out = []
    offset = 0
    while len(out) < limit:
        try:
            d = api({"action": "query", "list": "search",
                     "srsearch": kw, "srlimit": "50",
                     "sroffset": str(offset), "srnamespace": "0"})
            results = d.get("query", {}).get("search", [])
        except Exception:
            break
        if not results:
            break
        for r in results:
            t = r.get("title", "")
            if t and not t.startswith(("قائمة", "تصنيف")):
                out.append(t)
        offset += 50
        if offset > 400:
            break
        time.sleep(0.1)
    return out[:limit]

def extracts(titles):
    out = {}
    for i in range(0, len(titles), 20):
        batch = titles[i:i+20]
        try:
            d = api({"action": "query", "prop": "extracts",
                     "exintro": "1", "explaintext": "1",
                     "exchars": "700", "titles": "|".join(batch)})
            pages = d.get("query", {}).get("pages", {})
            for pid, page in pages.items():
                t = page.get("title", "")
                e = page.get("extract", "").strip()
                if t and e and len(e) > 50 and not t.startswith(("قائمة", "تصنيف")):
                    out[t] = e
        except Exception:
            pass
        time.sleep(0.05)
    return out

KEYWORDS = [
    # تقنية
    "ذكاء اصطناعي", "تعلم الآلة", "شبكة عصبية", "تعلم عميق",
    "شبكة حاسوبية", "إنترنت", "بروتوكول", "خادم",
    "هاتف ذكي", "روبوت", "طائرة بدون طيار", "طابعة ثلاثية",
    "نظام تشغيل", "لينكس", "ويندوز", "أندرويد",
    "قاعدة بيانات", "حوسبة سحابية", "بيانات ضخمة",
    "أمن معلوماتي", "اختراق", "تشفير", "كلمة مرور",
    "لغة برمجة", "بايثون", "جافا", "جافاسكريبت", "سي بلس بلس",
    # طب
    "قلب", "دماغ", "كبد", "رئة", "كلية", "معدة", "أمعاء",
    "جهاز عصبي", "جهاز مناعي", "جهاز هضمي", "جهاز تنفسي",
    "سرطان", "سكري", "ضغط دم", "التهاب", "فيروس", "بكتيريا",
    "لقاح", "مضاد حيوي", "فيتامين", "هرمون", "إنزيم",
    "تشريح", "فسيولوجيا", "جراحة", "تخدير",
    # هندسة
    "هندسة مدنية", "هندسة معمارية", "هندسة كهربائية",
    "هندسة ميكانيكية", "هندسة كيميائية", "هندسة برمجيات",
    "جسر", "سد", "نفق", "برج", "مطار", "سكة حديد",
    # فيزياء تطبيقية
    "كهرباء", "مغناطيسية", "إلكترونيات", "نصف ناقل",
    "طاقة شمسية", "طاقة نووية", "طاقة رياح",
    "ليزر", "رادار", "أشعة إكس", "موجات راديوية",
    # كيمياء تطبيقية
    "بترول", "بلاستيك", "مبيد", "سماد", "منظف",
    "سبيكة", "بوليمر", "نانو تكنولوجي",
]

all_items = []
seen = set()

for kw in KEYWORDS:
    print("Search: " + kw)
    try:
        titles = search(kw, limit=150)
        if not titles:
            print("   0")
            continue
        exts = extracts(titles)
        added = 0
        for t, e in exts.items():
            q = "ما هو " + t + "؟"
            if q[:80] in seen:
                continue
            seen.add(q[:80])
            all_items.append({"q": q, "a": e,
                              "tags": ["wiki_search", kw, "tech_med"]})
            added += 1
        print("   +" + str(added) + " (total " + str(len(all_items)) + ")")
    except Exception as e:
        print("   ERR: " + str(e))

print("")
print("Total: " + str(len(all_items)))

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
