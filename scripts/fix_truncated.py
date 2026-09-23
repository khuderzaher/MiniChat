# -*- coding: utf-8 -*-
"""scripts/fix_truncated.py — يعيد تنزيل المقالات المقطوعة عند 400 حرف."""
import json, os, shutil, time, urllib.request, urllib.parse
from datetime import datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE, "minichat_db.json")
UA = "MiniChat/2.3 (educational)"
TRUNCATED_LEN = 400


def fetch_summary(title, lang="ar"):
    url = "https://%s.wikipedia.org/api/rest_v1/page/summary/%s" % (lang, urllib.parse.quote(title))
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            d = json.load(r)
        if d.get("type") == "disambiguation":
            return None
        extract = d.get("extract", "").strip()
        if len(extract) < 100:
            return None
        return extract
    except Exception:
        return None


def extract_title_from_q(q):
    """يستخرج عنوان المقالة من صيغة السؤال."""
    q = q.strip().rstrip("؟?.")
    for prefix in ("ما هو ", "ما هي ", "أخبرني عن ", "ما معنى ", "من هو ", "من هي "):
        if q.startswith(prefix):
            return q[len(prefix):].strip()
    return q


def main():
    print("[FIX] تحميل قاعدة البيانات...")
    with open(DB_PATH, "r", encoding="utf-8") as f:
        db = json.load(f)
    faq = db.get("faq", [])
    print("[FIX] عدد العناصر: %d" % len(faq))

    # اجمع كل العناوين الفريدة اللي جاوبها 400 حرف بالضبط
    titles_to_fix = set()
    for item in faq:
        if not isinstance(item, dict):
            continue
        a = item.get("a", "")
        if len(a) == TRUNCATED_LEN:
            t = extract_title_from_q(item.get("q", ""))
            if t:
                titles_to_fix.add(t)

    print("[FIX] عدد العناوين المقطوعة: %d" % len(titles_to_fix))
    if not titles_to_fix:
        print("[FIX] لا يوجد شيء لإصلاحه.")
        return

    # أنشئ خريطة جديدة للعناوين
    new_content = {}
    fixed_count = 0
    failed_count = 0
    for i, t in enumerate(sorted(titles_to_fix), 1):
        extract = fetch_summary(t)
        if extract and len(extract) > TRUNCATED_LEN:
            new_content[t] = extract
            fixed_count += 1
            print("[FIX] %d/%d ✅ %s (%d حرف)" % (i, len(titles_to_fix), t, len(extract)))
        else:
            failed_count += 1
            if i % 10 == 0:
                print("[FIX] %d/%d (نجح %d، فشل %d)" % (i, len(titles_to_fix), fixed_count, failed_count))
        time.sleep(0.4)

    # حدّث قاعدة البيانات
    print("[FIX] تحديث القاعدة...")
    updated = 0
    for item in faq:
        if not isinstance(item, dict):
            continue
        a = item.get("a", "")
        if len(a) != TRUNCATED_LEN:
            continue
        t = extract_title_from_q(item.get("q", ""))
        if t in new_content:
            item["a"] = new_content[t]
            updated += 1

    db["faq"] = faq
    bak = DB_PATH + ".bak_fixtrunc_" + datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.copy2(DB_PATH, bak)
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)
    print("[FIX] ✅ حدّثنا %d عنصر" % updated)
    print("[FIX] نسخة احتياطية: %s" % os.path.basename(bak))


if __name__ == "__main__":
    main()
