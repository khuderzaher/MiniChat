# -*- coding: utf-8 -*-
"""scripts/wikipedia_loader.py — يجيب ملخصات من Wikipedia العربية."""
import json, os, shutil, time, urllib.request, urllib.parse
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "minichat_db.json")
UA = "MiniChat/2.3 (educational; contact@example.com)"

def load_db():
    with open(DB_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_db(db):
    bak = DB_PATH + ".bak_wiki_" + datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.copy2(DB_PATH, bak)
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)
    print("[WIKI] حفظ + نسخة: %s" % os.path.basename(bak))

def _fetch_one(title, lang="ar"):
    """محاولة واحدة لجلب مقالة."""
    url = "https://%s.wikipedia.org/api/rest_v1/page/summary/%s" % (lang, urllib.parse.quote(title))
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            d = json.load(r)
        if d.get("type") == "disambiguation":
            return None, None
        extract = d.get("extract", "").strip()
        if len(extract) < 40:
            return None, None
        return d.get("title", title), extract
    except Exception:
        return None, None

def _search_title(query, lang="ar"):
    """يبحث عن عنوان مقالة مطابقة."""
    api = "https://%s.wikipedia.org/w/api.php" % lang
    params = {"action": "query", "list": "search", "srsearch": query,
              "srlimit": "1", "format": "json"}
    url = api + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            d = json.load(r)
        hits = d.get("query", {}).get("search", [])
        if hits:
            return hits[0].get("title", "")
    except Exception:
        pass
    return None

def fetch_summary(title, lang="ar"):
    """يجيب ملخص المقالة من Wikipedia (مع محاولات احتياطية)."""
    # 1) مباشر
    t, e = _fetch_one(title, lang)
    if t:
        return t, e
    # 2) مع "ال"
    if not title.startswith("ال"):
        t, e = _fetch_one("ال" + title, lang)
        if t:
            return t, e
    # 3) بحث + محاولة على أول نتيجة
    found = _search_title(title, lang)
    if found and found != title:
        t, e = _fetch_one(found, lang)
        if t:
            return t, e
    return None, None

def main():
    # اقرأ من ملف JSON (أولوية)
    json_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wiki_topics.json")
    topics = []
    if os.path.exists(json_file):
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        # تجاهل التعليقات (المفاتيح التي تبدأ بـ _)
        for cat, items in data.items():
            if cat.startswith("_"):
                continue
            for t in items:
                topics.append((t, cat))
    else:
        # احتياطي: txt
        topics_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wiki_topics.txt")
        if os.path.exists(topics_file):
            with open(topics_file, "r", encoding="utf-8") as f:
                topics = [(ln.strip(), "general") for ln in f if ln.strip() and not ln.startswith("#")]
    print("[WIKI] عدد المواضيع: %d" % len(topics))

    db = load_db()
    faq = db.get("faq", [])
    existing = set()
    for it in faq:
        if isinstance(it, dict):
            existing.add(it.get("q", "").strip())

    added = 0
    skipped = 0
    failed = 0
    for i, entry in enumerate(topics, 1):
        topic, category = entry
        # تخطى إذا موجود
        q1 = "ما هو %s" % topic
        q2 = "ما هي %s" % topic
        if q1 in existing or q2 in existing:
            skipped += 1
            continue
        title, extract = fetch_summary(topic)
        if not title:
            failed += 1
            if i % 20 == 0:
                print("[WIKI] %d/%d (نجح %d، فشل %d)" % (i, len(topics), added, failed))
            time.sleep(0.3)
            continue
        # اختر صيغة السؤال
        q = q2 if (title.startswith("ال") or "ة" == title[-1:] or topic in ("شمس","أرض")) else q1
        # أحياناً الاثنين
        item1 = {"q": q1, "a": extract, "tags": ["wiki", category]}
        item2 = {"q": q2, "a": extract, "tags": ["wiki", category]}
        for it in (item1, item2):
            if it["q"] not in existing:
                faq.append(it)
                existing.add(it["q"])
                added += 1
        if i % 20 == 0:
            print("[WIKI] %d/%d (نجح %d، فشل %d)" % (i, len(topics), added, failed))
        time.sleep(0.3)

    db["faq"] = faq
    print("[WIKI] الإجمالي المضاف: %d" % added)
    print("[WIKI] مكرر: %d | فشل: %d" % (skipped, failed))
    print("[WIKI] إجمالي FAQ: %d" % len(faq))
    save_db(db)

if __name__ == "__main__":
    main()
