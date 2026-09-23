# -*- coding: utf-8 -*-
import json
import time
import urllib.request
import urllib.parse
from pathlib import Path

HERE = Path(__file__).parent
DB_FILE = HERE / "minichat_db.json"
BACKUP_FILE = HERE / "minichat_db.backup_before_wiki.json"


def download_from_wiki(total=600):
    print("Downloading articles from Arabic Wikipedia...")
    seeds = [
        "دمشق", "بغداد", "القاهرة", "بيروت", "الرياض", "دبي", "القدس",
        "إسطنبول", "طهران", "الدوحة", "أبوظبي", "المنامة", "الخرطوم",
        "طرابلس", "تونس", "الجزائر", "الرباط", "نواكشوط", "صنعاء",
        "مسقط", "الكويت", "حلب", "حمص", "حماة", "اللاذقية",
        "ابن خلدون", "محمد بن موسى الخوارزمي", "ابن سينا",
        "أبو الطيب المتنبي", "نجيب محفوظ", "طه حسين", "أحمد شوقي",
        "جبران خليل جبران", "نزار قباني", "محمود درويش",
        "غسان كنفاني", "توفيق الحكيم", "يوسف إدريس",
        "عباس محمود العقاد",
        "ذكاء اصطناعي", "تعلم الآلة", "شبكة عصبية", "تعلم عميق",
        "خوارزمية", "بيانات", "حوسبة سحابية", "أمن سيبراني",
        "برمجة", "لغة برمجة", "بايثون", "جافا",
        "قلب", "دماغ", "كبد", "رئة", "كلية", "معدة",
        "جهاز عصبي", "جهاز مناعي", "دورة دموية", "دم",
        "عظم", "عضلة", "جلد", "عين", "أذن",
        "شمس", "قمر", "مريخ", "مشتري", "زهرة", "زحل", "عطارد",
        "ماء", "هواء", "ذهب", "فضة", "حديد", "نحاس",
        "إسلام", "قرآن", "محمد", "رمضان", "حج", "صلاة", "زكاة",
        "حاسوب", "إنترنت", "هاتف ذكي", "روبوت", "طائرة", "سيارة",
        "كرة القدم", "كرة السلة", "تنس", "شطرنج",
        "موسيقى", "رسم", "شعر", "رواية", "مسرح", "سينما",
        "شاي", "قهوة", "حليب", "عسل", "تمر", "زيتون",
        "قط", "كلب", "حصان", "أسد", "فيل", "دلفين", "نحلة",
    ]
    rows = []
    successful = 0
    failed = 0
    for title in seeds:
        if len(rows) >= total:
            break
        try:
            url = "https://ar.wikipedia.org/api/rest_v1/page/summary/" + urllib.parse.quote(title)
            req = urllib.request.Request(url, headers={"User-Agent": "MiniChat/1.0 (educational)"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            extract = data.get("extract", "").strip()
            page_title = data.get("title", title)
            if extract and len(extract) > 30:
                rows.append({"row": {"question": "ما هو " + page_title + "؟", "answers": {"text": [extract]}}})
                rows.append({"row": {"question": "أخبرني عن " + page_title, "answers": {"text": [extract]}}})
                rows.append({"row": {"question": page_title, "answers": {"text": [extract]}}})
                successful += 1
                print("OK: " + page_title)
            time.sleep(0.15)
        except Exception:
            failed += 1
            continue
    print("Successful: " + str(successful))
    print("Failed: " + str(failed))
    print("Total rows: " + str(len(rows)))
    return rows[:total]


def extract_pairs(rows):
    faq = []
    seen = set()
    for row in rows:
        r = row.get("row", row)
        q = (r.get("question") or "").strip()
        answers = r.get("answers") or {}
        if isinstance(answers, dict):
            a_list = answers.get("text", [])
            a = a_list[0].strip() if a_list else ""
        else:
            a = str(answers).strip()
        if not q or not a:
            continue
        key = q[:80]
        if key in seen:
            continue
        seen.add(key)
        faq.append({"q": q, "a": a, "tags": ["qa_arabic", "wikipedia_ar"]})
    return faq


def merge_into_db(new_faq):
    if not DB_FILE.exists():
        print("ERROR: minichat_db.json not found")
        return False
    print("Reading database...")
    with open(DB_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    current = data.get("faq", [])
    print("Current: " + str(len(current)))
    try:
        with open(BACKUP_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print("Backup saved")
    except Exception as e:
        print("Backup failed: " + str(e))
    existing = {item.get("q", "")[:80] for item in current}
    added = 0
    for item in new_faq:
        key = item["q"][:80]
        if key not in existing:
            current.append(item)
            existing.add(key)
            added += 1
    data["faq"] = current
    print("Saving...")
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("Added: " + str(added))
    print("Total now: " + str(len(current)))
    return True


def main():
    print("=" * 60)
    print("  Wikipedia Arabic Knowledge Loader")
    print("=" * 60)
    rows = download_from_wiki(total=600)
    if not rows:
        print("No rows downloaded.")
        return
    print("Extracting Q&A...")
    faq = extract_pairs(rows)
    print("Extracted: " + str(len(faq)))
    if not faq:
        return
    merge_into_db(faq)
    print("DONE!")


if __name__ == "__main__":
    main()