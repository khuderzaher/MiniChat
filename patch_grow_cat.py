import os, sys, shutil, json

p = 'scripts/grow_from_categories.py'
bak = p + '.before_quality'
if os.path.exists(bak):
    print("NOTE: backup exists"); sys.exit(1)
shutil.copy(p, bak); print("backup:", bak)

src = open(p, encoding='utf-8').read()

# 1) قائمة التصنيفات من JSON
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

new_block = '''def _load_cats():
    p = Path(__file__).resolve().parent.parent / "grow_cat_categories.json"
    with open(p, encoding="utf-8") as f:
        return json.load(f)


CATEGORIES = _load_cats()'''
src = src[:start] + new_block + src[end:]

# 2) wiki_summary: عتبة 400 + استبعاد أقواس
old_summary = '''def wiki_summary(title, timeout=15):
    url = REST + urllib.parse.quote(title)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            d = json.load(r)
        if d.get("type") == "disambiguation":
            return None
        ext = (d.get("extract") or "").strip()
        if len(ext) < 60:
            return None
        return d.get("title") or title, ext
    except Exception:
        return None'''

new_summary = '''MIN_EXTRACT = 400


def wiki_summary(title, timeout=15, retries=1):
    # استبعد عناوين بأقواس — غالبًا توضيحات/هوامش
    if " (" in title or "（" in title:
        return None
    url = REST + urllib.parse.quote(title)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                d = json.load(r)
            if d.get("type") == "disambiguation":
                return None
            ext = (d.get("extract") or "").strip()
            if len(ext) < MIN_EXTRACT:
                return None
            return d.get("title") or title, ext
        except Exception:
            if attempt < retries:
                time.sleep(1.0)
                continue
            return None'''
if src.count(old_summary) != 1:
    print("ABORT: wiki_summary block not unique"); sys.exit(1)
src = src.replace(old_summary, new_summary, 1)

open(p, 'w', encoding='utf-8').write(src)
print("OK")
