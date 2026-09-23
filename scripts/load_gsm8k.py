# -*- coding: utf-8 -*-
"""scripts/load_gsm8k.py — ينزّل Arabic-GSM8K-v2 من HuggingFace."""
import json, os, shutil, time, re, urllib.request, urllib.parse
from datetime import datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE, "minichat_db.json")
PROGRESS_FILE = os.path.join(BASE, "scripts", "gsm8k_progress.txt")
DATASET = "Omartificial-Intelligence-Space/Arabic-gsm8k-v2"
SPLIT = "main_train"
API = "https://datasets-server.huggingface.co/rows"
UA = "MiniChat/2.3 (educational)"
BATCH = 100
TOTAL = 7473


def fetch_batch(offset, length=BATCH):
    params = {
        "dataset": DATASET,
        "config": "default",
        "split": SPLIT,
        "offset": str(offset),
        "length": str(length),
    }
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def clean_answer(text):
    """يشيل رموز الحساب الوسيطة <<...>> ويحول #### لنص واضح."""
    if not text:
        return text
    # احذف <<...>>
    text = re.sub(r"<<[^>]*>>", "", text)
    # استبدل #### بـ "الجواب:"
    text = re.sub(r"####\s*", "الجواب النهائي: ", text)
    # شيل المسافات الزائدة
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r" {2,}", " ", text)
    return text.strip()


def load_db():
    with open(DB_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_db(db):
    bak = DB_PATH + ".bak_gsm8k_" + datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.copy2(DB_PATH, bak)
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)
    print("[GSM] حفظ + نسخة: %s" % os.path.basename(bak))


def main():
    # استئناف
    start = 0
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, "r") as f:
                start = int(f.read().strip())
            print("[GSM] استئناف من offset=%d" % start)
        except Exception:
            pass

    db = load_db()
    faq = db.get("faq", [])
    existing = set()
    for it in faq:
        if isinstance(it, dict):
            existing.add(it.get("q", "").strip())

    added = 0
    skipped = 0
    failed = 0
    offset = start
    while offset < TOTAL:
        try:
            data = fetch_batch(offset)
            rows = data.get("rows", [])
            if not rows:
                break
            for row in rows:
                r = row.get("row", {})
                q = (r.get("question") or "").strip()
                a = (r.get("answer") or "").strip()
                if not q or not a or len(a) < 15:
                    continue
                if q in existing:
                    skipped += 1
                    continue
                a_clean = clean_answer(a)
                faq.append({"q": q, "a": a_clean, "tags": ["math", "stem", "gsm8k"]})
                existing.add(q)
                added += 1
            offset += len(rows)
            print("[GSM] %d/%d (نجح %d، مكرر %d)" % (offset, TOTAL, added, skipped))
            try:
                with open(PROGRESS_FILE, "w") as f:
                    f.write(str(offset))
            except Exception:
                pass
            time.sleep(2)
        except Exception as e:
            err = str(e)
            print("[GSM] خطأ عند %d: %s" % (offset, err))
            if "429" in err:
                print("[GSM] rate limit، انتظار 60 ثانية...")
                time.sleep(60)
                continue
            failed += 1
            if failed > 5:
                break
            time.sleep(5)
            continue

    db["faq"] = faq
    print("[GSM] مضاف: %d | مكرر: %d | إجمالي FAQ: %d" % (added, skipped, len(faq)))
    save_db(db)


if __name__ == "__main__":
    main()
