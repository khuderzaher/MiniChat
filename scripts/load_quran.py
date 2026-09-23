# -*- coding: utf-8 -*-
import json, urllib.request
from pathlib import Path

DB = Path(__file__).parent / "minichat_db.json"

print("Downloading Quran...")
url = "https://api.alquran.cloud/v1/quran/quran-uthmani"
req = urllib.request.Request(url, headers={"User-Agent": "MiniChat/1.0"})
with urllib.request.urlopen(req, timeout=120) as resp:
    data = json.loads(resp.read().decode("utf-8"))

items = []
for s in data["data"]["surahs"]:
    sname = s["name"]
    for a in s["ayahs"]:
        text = a["text"].strip()
        if len(text) < 10:
            continue
        items.append({
            "q": "آية " + str(a["numberInSurah"]) + " من " + sname,
            "a": text,
            "tags": ["quran", sname]
        })

print("Verses extracted: " + str(len(items)))

with open(DB, "r", encoding="utf-8") as f:
    db = json.load(f)

backup = DB.parent / "minichat_db.backup_before_quran.json"
with open(backup, "w", encoding="utf-8") as f:
    json.dump(db, f, ensure_ascii=False, indent=2)
print("Backup: " + backup.name)

existing = {x.get("q","")[:80] for x in db.get("faq", [])}
added = 0
for it in items:
    if it["q"][:80] not in existing:
        db["faq"].append(it)
        added += 1

print("Added: " + str(added))
print("Total: " + str(len(db["faq"])))

with open(DB, "w", encoding="utf-8") as f:
    json.dump(db, f, ensure_ascii=False, indent=2)
print("DONE")
