# -*- coding: utf-8 -*-
import json, urllib.request, urllib.parse, time
from pathlib import Path

DB = Path("minichat_db.json")
ENDPOINT = "https://query.wikidata.org/sparql"

def run_sparql(query, timeout=60):
    url = ENDPOINT + "?" + urllib.parse.urlencode({
        "query": query, "format": "json"
    })
    req = urllib.request.Request(url, headers={
        "User-Agent": "MiniChat/1.0 (educational)",
        "Accept": "application/sparql-results+json"
    })
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))

def qa(q, a, tag):
    return {"q": q, "a": a, "tags": [tag, "wikidata"]}

items = []

# 1) العناصر الكيميائية
print("1/6 Chemical elements...")
q = """
SELECT ?el ?elLabel ?sym ?num ?mass WHERE {
  ?el wdt:P31 wd:Q11344 ;
      wdt:P246 ?sym ;
      wdt:P1086 ?num .
  OPTIONAL { ?el wdt:P2067 ?mass . }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "ar,en". }
}
LIMIT 200
"""
try:
    r = run_sparql(q)
    for b in r["results"]["bindings"]:
        name = b["elLabel"]["value"]
        sym = b["sym"]["value"]
        num = b["num"]["value"]
        items.append(qa("ما هو الرمز الكيميائي لـ " + name + "؟", sym, "chem"))
        items.append(qa("ما هو العدد الذري لـ " + name + "؟", num, "chem"))
        if "mass" in b:
            items.append(qa("ما هي الكتلة الذرية لـ " + name + "؟", b["mass"]["value"], "chem"))
    print("   OK: " + str(len(items)))
except Exception as e:
    print("   ERR: " + str(e))

# 2) الكواكب
print("2/6 Planets...")
q = """
SELECT ?p ?pLabel ?mass ?radius WHERE {
  ?p wdt:P31 wd:Q634 .
  OPTIONAL { ?p wdt:P2067 ?mass . }
  OPTIONAL { ?p wdt:P2120 ?radius . }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "ar,en". }
}
LIMIT 50
"""
try:
    r = run_sparql(q)
    for b in r["results"]["bindings"]:
        name = b["pLabel"]["value"]
        if "mass" in b:
            items.append(qa("ما هي كتلة " + name + "؟", b["mass"]["value"] + " كغ", "astro"))
        if "radius" in b:
            items.append(qa("ما هو نصف قطر " + name + "؟", b["radius"]["value"] + " كم", "astro"))
    print("   OK: " + str(len(items)))
except Exception as e:
    print("   ERR: " + str(e))

# 3) النجوم
print("3/6 Stars...")
q = """
SELECT ?s ?sLabel ?const WHERE {
  ?s wdt:P31 wd:Q523 .
  OPTIONAL { ?s wdt:P59 ?const . }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "ar,en". }
}
LIMIT 300
"""
try:
    r = run_sparql(q)
    for b in r["results"]["bindings"]:
        name = b["sLabel"]["value"]
        if "const" in b:
            items.append(qa("في أي كوكبة يقع نجم " + name + "؟", b["const"]["value"].split("/")[-1], "astro"))
    print("   OK: " + str(len(items)))
except Exception as e:
    print("   ERR: " + str(e))

# 4) الأمراض
print("4/6 Diseases...")
q = """
SELECT ?d ?dLabel ?symptom ?symptomLabel WHERE {
  ?d wdt:P31 wd:Q12136 .
  OPTIONAL { ?d wdt:P780 ?symptom . }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "ar,en". }
}
LIMIT 500
"""
try:
    r = run_sparql(q)
    for b in r["results"]["bindings"]:
        name = b["dLabel"]["value"]
        if "symptomLabel" in b:
            items.append(qa("ما هي أعراض " + name + "؟", b["symptomLabel"]["value"], "med"))
    print("   OK: " + str(len(items)))
except Exception as e:
    print("   ERR: " + str(e))

# 5) الحيوانات
print("5/6 Animals...")
q = """
SELECT ?a ?aLabel ?sci WHERE {
  ?a wdt:P31 wd:Q729 .
  OPTIONAL { ?a wdt:P225 ?sci . }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "ar,en". }
}
LIMIT 500
"""
try:
    r = run_sparql(q)
    for b in r["results"]["bindings"]:
        name = b["aLabel"]["value"]
        if "sci" in b:
            items.append(qa("ما هو الاسم العلمي لـ " + name + "؟", b["sci"]["value"], "bio"))
    print("   OK: " + str(len(items)))
except Exception as e:
    print("   ERR: " + str(e))

# 6) الفيتامينات
print("6/6 Vitamins...")
q = """
SELECT ?v ?vLabel ?formula WHERE {
  ?v wdt:P31 wd:Q34956 .
  OPTIONAL { ?v wdt:P274 ?formula . }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "ar,en". }
}
LIMIT 100
"""
try:
    r = run_sparql(q)
    for b in r["results"]["bindings"]:
        name = b["vLabel"]["value"]
        if "formula" in b:
            items.append(qa("ما هي الصيغة الكيميائية لـ " + name + "؟", b["formula"]["value"], "bio"))
    print("   OK: " + str(len(items)))
except Exception as e:
    print("   ERR: " + str(e))

print("")
print("Total collected: " + str(len(items)))

# الدمج
if not items:
    print("No items collected.")
else:
    with open(DB, "r", encoding="utf-8") as f:
        db = json.load(f)
    existing = {x.get("q","")[:80] for x in db.get("faq", [])}
    added = 0
    for it in items:
        if it["q"][:80] not in existing:
            db["faq"].append(it)
            existing.add(it["q"][:80])
            added += 1
    with open(DB, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)
    print("Added: " + str(added))
    print("Total now: " + str(len(db["faq"])))
print("DONE")
