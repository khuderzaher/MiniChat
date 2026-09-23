# -*- coding: utf-8 -*-
"""scripts/load_cidar.py — ينزّل CIDAR مع فلترة ذكية (نحو + صرف + معرفة)."""
import json, os, shutil, time, re, urllib.request, urllib.parse
from datetime import datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE, "minichat_db.json")
PROGRESS_FILE = os.path.join(BASE, "scripts", "cidar_progress.txt")
DATASET = "arbml/CIDAR"
API = "https://datasets-server.huggingface.co/rows"
UA = "MiniChat/2.3 (educational)"
BATCH = 100
TOTAL = 10000

# كلمات مفتاحية للمحتوى المفيد (نحو + صرف + معرفة)
USEFUL_PATTERNS = [
    r"صغ من الفعل",          # صرف
    r"صرّف|صرف",            # صرف
    r"أعرب|اعرب",           # إعراب
    r"استخرج",              # تحليل
    r"ما هو إعراب",         # إعراب
    r"ما هو نوع",           # تصنيف
    r"حدد نوع",             # تصنيف
    r"ما معنى",             # معنى
    r"ما هي|ما هو",         # تعريف
    r"اشرح|وضح",            # شرح
    r"اذكر",                # سرد
    r"أكمل",                # إكمال
    r"اجعل.*في جملة",       # تطبيق
    r"حول.*إلى",            # تحويل
]

# كلمات مفتاحية للمحتوى غير المفيد (نستبعد)
BAD_PATTERNS = [
    r"أنشئ قصيدة",          # شعر
    r"قصيدة",               # شعر
    r"أنشئ سرد",            # سرد
    r"اكتب.*قصة",           # قصة
    r"أنشئ قصة",            # قصة
    r"عنوان الأغنية",       # أغنية
    r"كلمات الأغنية",       # أغنية
    r"بالونات",             # غير مفيد
    r"خيال",                # خيال
]


def is_useful(instruction, output):
    """هل العنصر مفيد؟"""
    if not instruction or not output:
        return False
    if len(instruction) < 10 or len(output) < 20:
        return False
    ins = instruction.strip()
    out = output.strip()
    # استبعد السيئ
    for pat in BAD_PATTERNS:
        if re.search(pat, ins):
            return False
    # اقبل المفيد
    for pat in USEFUL_PATTERNS:
        if re.search(pat, ins):
            # تأكد إن الـ output ليس ضخماً (جداول طويلة مش مناسبة)
            if len(out) > 2000:
                return False
            return True
    return False


def fetch_batch(offset, length=BATCH):
    params = {
        "dataset": DATASET,
        "config": "default",
        "split": "train",
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
    bak = DB_PATH + ".bak_cidar_" + datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.copy2(DB_PATH, bak)
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)
    print("[CIDAR] حفظ + نسخة: %s" % os.path.basename(bak))


def main():
    start = 0
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, "r") as f:
                start = int(f.read().strip())
            print("[CIDAR] استئناف من offset=%d" % start)
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
    filtered = 0
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
                ins = (r.get("instruction") or "").strip()
                out = (r.get("output") or "").strip()
                # فلترة
                if not is_useful(ins, out):
                    filtered += 1
                    continue
                # نظف السؤال
                q = ins.rstrip("؟?.")
                q = q + "؟" if not q.endswith("؟") else q
                if q in existing:
                    skipped += 1
                    continue
                faq.append({"q": q, "a": out, "tags": ["cidar", "arabic", "grammar"]})
                existing.add(q)
                added += 1
            offset += len(rows)
            print("[CIDAR] %d/%d (نجح %d، مستبعد %d)" % (offset, TOTAL, added, filtered))
            try:
                with open(PROGRESS_FILE, "w") as f:
                    f.write(str(offset))
            except Exception:
                pass
            time.sleep(2)
        except Exception as e:
            err = str(e)
            print("[CIDAR] خطأ عند %d: %s" % (offset, err))
            if "429" in err:
                print("[CIDAR] rate limit، انتظار 60 ثانية...")
                time.sleep(60)
                continue
            failed += 1
            if failed > 5:
                break
            time.sleep(5)
            continue

    db["faq"] = faq
    print("[CIDAR] مضاف: %d | مستبعد: %d | مكرر: %d | إجمالي FAQ: %d" % (
        added, filtered, skipped, len(faq)))
    save_db(db)


if __name__ == "__main__":
    main()
