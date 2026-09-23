# -*- coding: utf-8 -*-
"""scripts/load_nutrition_qa.py — ينزّل Arabic-Nutrition-QA من HuggingFace API."""
import json, os, shutil, time, urllib.request, urllib.parse
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "minichat_db.json")
DATASET = "moazeldegwy/Arabic-Nutrition-QA"
API = "https://datasets-server.huggingface.co/rows"
UA = "MiniChat/2.3 (educational)"
BATCH = 100


def fetch_batch(offset, length=BATCH, split="train"):
    params = {
        "dataset": DATASET,
        "config": "default",
        "split": split,
        "offset": str(offset),
        "length": str(length),
    }
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def load_db():
    with open(DB_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_db(db):
    bak = DB_PATH + ".bak_nutrition_" + datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.copy2(DB_PATH, bak)
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)
    print("[NUT] حفظ + نسخة: %s" % os.path.basename(bak))


def main():
    # 1) جرّب أول دفعة لمعرفة العدد
    print("[NUT] جرّب أول دفعة...")
    try:
        test = fetch_batch(0, length=1)
        total = test.get("num_rows_total", 0)
        print("[NUT] عدد الصفوف: %d" % total)
    except Exception as e:
        print("[NUT] فشل: %s" % e)
        return

    db = load_db()
    faq = db.get("faq", [])
    existing = set()
    for it in faq:
        if isinstance(it, dict):
            existing.add(it.get("q", "").strip())

    added = 0
    skipped = 0
    failed = 0
    # ابدأ من آخر نقطة (نحسب من عدد الموجود)
    import os as _os
    start_offset = 0
    resume_file = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "nutrition_progress.txt")
    if _os.path.exists(resume_file):
        try:
            with open(resume_file, "r") as _f:
                start_offset = int(_f.read().strip())
            print("[NUT] استئناف من offset=%d" % start_offset)
        except Exception:
            pass
    offset = start_offset
    while offset < total:
        try:
            data = fetch_batch(offset)
            rows = data.get("rows", [])
            if not rows:
                break
            for row in rows:
                r = row.get("row", {})
                q = (r.get("Question") or "").strip()
                a = (r.get("Answer") or "").strip()
                if not q or not a or len(a) < 20:
                    continue
                if q in existing:
                    skipped += 1
                    continue
                faq.append({"q": q, "a": a, "tags": ["nutrition", "health"]})
                existing.add(q)
                added += 1
            offset += len(rows)
            print("[NUT] %d/%d (نجح %d، مكرر %d)" % (offset, total, added, skipped))
            # احفظ التقدم
            try:
                with open(resume_file, "w") as _f:
                    _f.write(str(offset))
            except Exception:
                pass
            time.sleep(2)
        except Exception as e:
            err = str(e)
            print("[NUT] خطأ عند offset=%d: %s" % (offset, err))
            if "429" in err:
                # rate limit: انتظر 60 ثانية
                print("[NUT] rate limit، انتظار 60 ثانية...")
                time.sleep(60)
                continue
            failed += 1
            if failed > 5:
                print("[NUT] توقف بعد 5 أخطاء")
                break
            time.sleep(5)
            continue

    db["faq"] = faq
    print("[NUT] مضاف: %d | مكرر: %d | إجمالي FAQ: %d" % (added, skipped, len(faq)))
    save_db(db)


if __name__ == "__main__":
    main()
