import os, sys, json, shutil

# ================= 1) JSON =================
categories = [
    {"name": "دول", "limit": 250, "sparql": """SELECT ?item ?labelAr WHERE {
      ?item wdt:P31 wd:Q6256 .
      ?item rdfs:label ?labelAr FILTER(LANG(?labelAr)="ar") .
    } LIMIT %d"""},
    {"name": "عواصم", "limit": 250, "sparql": """SELECT DISTINCT ?item ?labelAr WHERE {
      ?item wdt:P31/wdt:P279* wd:Q515 ;
            wdt:P1376 ?country .
      ?country wdt:P31 wd:Q6256 .
      ?item rdfs:label ?labelAr FILTER(LANG(?labelAr)="ar") .
    } LIMIT %d"""},
    {"name": "أنهار", "limit": 120, "sparql": """SELECT ?item ?labelAr WHERE {
      ?item wdt:P31/wdt:P279* wd:Q4022 .
      ?item rdfs:label ?labelAr FILTER(LANG(?labelAr)="ar") .
    } LIMIT %d"""},
    {"name": "جبال", "limit": 120, "sparql": """SELECT ?item ?labelAr WHERE {
      ?item wdt:P31/wdt:P279* wd:Q8502 .
      ?item rdfs:label ?labelAr FILTER(LANG(?labelAr)="ar") .
    } LIMIT %d"""},
    {"name": "بحار", "limit": 60, "sparql": """SELECT ?item ?labelAr WHERE {
      ?item wdt:P31/wdt:P279* wd:Q165 .
      ?item rdfs:label ?labelAr FILTER(LANG(?labelAr)="ar") .
    } LIMIT %d"""},
    {"name": "لغات", "limit": 120, "sparql": """SELECT ?item ?labelAr WHERE {
      ?item wdt:P31/wdt:P279* wd:Q34770 .
      ?item rdfs:label ?labelAr FILTER(LANG(?labelAr)="ar") .
    } LIMIT %d"""},
    {"name": "مدن", "limit": 400, "sparql": """SELECT DISTINCT ?item ?labelAr WHERE {
      ?item wdt:P31/wdt:P279* wd:Q515 .
      ?item rdfs:label ?labelAr FILTER(LANG(?labelAr)="ar") .
    } LIMIT %d"""},
    {"name": "جامعات", "limit": 150, "sparql": """SELECT ?item ?labelAr WHERE {
      ?item wdt:P31/wdt:P279* wd:Q3918 .
      ?item rdfs:label ?labelAr FILTER(LANG(?labelAr)="ar") .
    } LIMIT %d"""},
    {"name": "علماء", "limit": 200, "sparql": """SELECT ?item ?labelAr WHERE {
      ?item wdt:P106 wd:Q901 .
      ?item rdfs:label ?labelAr FILTER(LANG(?labelAr)="ar") .
    } LIMIT %d"""},
    {"name": "أدباء", "limit": 200, "sparql": """SELECT ?item ?labelAr WHERE {
      ?item wdt:P106 wd:Q36180 .
      ?item rdfs:label ?labelAr FILTER(LANG(?labelAr)="ar") .
    } LIMIT %d"""},
    {"name": "فلاسفة", "limit": 150, "sparql": """SELECT ?item ?labelAr WHERE {
      ?item wdt:P106 wd:Q4964182 .
      ?item rdfs:label ?labelAr FILTER(LANG(?labelAr)="ar") .
    } LIMIT %d"""},
    {"name": "مخترعون", "limit": 120, "sparql": """SELECT ?item ?labelAr WHERE {
      ?item wdt:P106 wd:Q205375 .
      ?item rdfs:label ?labelAr FILTER(LANG(?labelAr)="ar") .
    } LIMIT %d"""},
    {"name": "شركات تقنية", "limit": 120, "sparql": """SELECT ?item ?labelAr WHERE {
      ?item wdt:P31/wdt:P279* wd:Q4830453 ;
            wdt:P452/wdt:P279* wd:Q11661 .
      ?item rdfs:label ?labelAr FILTER(LANG(?labelAr)="ar") .
    } LIMIT %d"""},
    {"name": "لغات برمجة", "limit": 100, "sparql": """SELECT ?item ?labelAr WHERE {
      ?item wdt:P31/wdt:P279* wd:Q9143 .
      ?item rdfs:label ?labelAr FILTER(LANG(?labelAr)="ar") .
    } LIMIT %d"""},
    {"name": "عناصر كيميائية", "limit": 118, "sparql": """SELECT ?item ?labelAr WHERE {
      ?item wdt:P31 wd:Q11344 .
      ?item rdfs:label ?labelAr FILTER(LANG(?labelAr)="ar") .
    } LIMIT %d"""},
    {"name": "معادن", "limit": 100, "sparql": """SELECT ?item ?labelAr WHERE {
      ?item wdt:P31/wdt:P279* wd:Q7946 .
      ?item rdfs:label ?labelAr FILTER(LANG(?labelAr)="ar") .
    } LIMIT %d"""},
    {"name": "كواكب", "limit": 50, "sparql": """SELECT ?item ?labelAr WHERE {
      ?item wdt:P31/wdt:P279* wd:Q634 .
      ?item rdfs:label ?labelAr FILTER(LANG(?labelAr)="ar") .
    } LIMIT %d"""},
    {"name": "صحارى", "limit": 50, "sparql": """SELECT ?item ?labelAr WHERE {
      ?item wdt:P31/wdt:P279* wd:Q8514 .
      ?item rdfs:label ?labelAr FILTER(LANG(?labelAr)="ar") .
    } LIMIT %d"""},
    {"name": "براكين", "limit": 100, "sparql": """SELECT ?item ?labelAr WHERE {
      ?item wdt:P31/wdt:P279* wd:Q8072 .
      ?item rdfs:label ?labelAr FILTER(LANG(?labelAr)="ar") .
    } LIMIT %d"""},
    {"name": "مساجد", "limit": 100, "sparql": """SELECT ?item ?labelAr WHERE {
      ?item wdt:P31/wdt:P279* wd:Q32815 .
      ?item rdfs:label ?labelAr FILTER(LANG(?labelAr)="ar") .
    } LIMIT %d"""},
    {"name": "رياضات", "limit": 100, "sparql": """SELECT ?item ?labelAr WHERE {
      ?item wdt:P31/wdt:P279* wd:Q349 .
      ?item rdfs:label ?labelAr FILTER(LANG(?labelAr)="ar") .
    } LIMIT %d"""},
]

with open('scripts/grow_categories.json', 'w', encoding='utf-8') as f:
    json.dump(categories, f, ensure_ascii=False, indent=2)
print("OK JSON: %d فئة" % len(categories))

# ================= 2) Patch =================
p = 'scripts/grow_knowledge.py'
src = open(p, encoding='utf-8').read()

if '_load_categories' in src:
    print("already patched, skipping"); sys.exit(0)

bak = p + '.before_json_cats'
if os.path.exists(bak):
    print("NOTE: backup exists:", bak)
else:
    shutil.copy(p, bak); print("backup:", bak)

# 2a) استبدل CATEGORIES = [ ... ]
start = src.find('CATEGORIES = [')
if start == -1:
    print("ABORT: CATEGORIES not found"); sys.exit(1)
i = src.find('[', start)
depth, end = 0, -1
for j in range(i, len(src)):
    if src[j] == '[': depth += 1
    elif src[j] == ']':
        depth -= 1
        if depth == 0: end = j + 1; break
if end == -1:
    print("ABORT: closing ] not found"); sys.exit(1)

new_block = '''def _load_categories():
    import json as _json
    from pathlib import Path as _P
    p = _P(__file__).resolve().parent / "grow_categories.json"
    with open(p, encoding="utf-8") as f:
        data = _json.load(f)
    return [(c["name"], c["sparql"], c["limit"]) for c in data]


CATEGORIES = _load_categories()'''
src = src[:start] + new_block + src[end:]

# 2b) أضف filter في main()
old_hdr = '''def main():
    scale = 1.0
    if len(sys.argv) > 1:
        try:
            scale = float(sys.argv[1])
        except Exception:
            pass
    print("[GROW] scale =", scale)'''

new_hdr = '''def main():
    scale = 1.0
    if len(sys.argv) > 1:
        try:
            scale = float(sys.argv[1])
        except Exception:
            pass

    filter_names = None
    if len(sys.argv) > 2:
        filter_names = set(x.strip() for x in sys.argv[2].split(",") if x.strip())

    cats = CATEGORIES
    if filter_names:
        cats = [c for c in CATEGORIES if c[0] in filter_names]
        print("[GROW] فئات مختارة:", [c[0] for c in cats])

    print("[GROW] scale =", scale)'''

if src.count(old_hdr) != 1:
    print("ABORT: main header not found uniquely"); sys.exit(1)
src = src.replace(old_hdr, new_hdr, 1)

# 2c) استخدم cats بدل CATEGORIES في الحلقة
src = src.replace(
    'for cat_i, (cat_name, query_tpl, cat_limit) in enumerate(CATEGORIES):',
    'for cat_i, (cat_name, query_tpl, cat_limit) in enumerate(cats):', 1)

open(p, 'w', encoding='utf-8').write(src)
print("OK: تم تعديل grow_knowledge.py")
