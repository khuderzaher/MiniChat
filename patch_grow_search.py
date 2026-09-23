import os, sys, shutil

p = 'scripts/grow_knowledge.py'
bak = p + '.before_search_fallback'
if os.path.exists(bak):
    print("NOTE: backup exists"); sys.exit(1)
shutil.copy(p, bak); print("backup:", bak)

src = open(p, encoding='utf-8').read()

anchor = 'def wiki_summary(title, timeout=15):'
new_funcs = '''def wiki_search_title(query, lang="ar", timeout=15):
    """بحث عن أقرب عنوان في ويكيبيديا العربية."""
    api = "https://%s.wikipedia.org/w/api.php" % lang
    params = {"action": "query", "list": "search", "srsearch": query,
              "srlimit": "1", "format": "json"}
    url = api + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            d = json.load(r)
        hits = d.get("query", {}).get("search", [])
        if hits:
            return hits[0].get("title", "")
    except Exception:
        pass
    return None


def fetch_with_search(title):
    """يجيب ملخص المقالة، مع fallback إلى البحث."""
    r = wiki_summary(title)
    if r:
        return r
    if not title.startswith("ال"):
        r = wiki_summary("ال" + title)
        if r:
            return r
    found = wiki_search_title(title)
    if found and found != title:
        r = wiki_summary(found)
        if r:
            return r
    return None


'''
assert src.count(anchor) == 1, "anchor: %d" % src.count(anchor)
src = src.replace(anchor, new_funcs + anchor, 1)

old_call = '            res = wiki_summary(title)'
new_call = '            res = fetch_with_search(title)'
assert src.count(old_call) == 1, "call: %d" % src.count(old_call)
src = src.replace(old_call, new_call, 1)

old_fail = '''            if not res:
                total_failed += 1
                done_qids.add(qid)'''
new_fail = '''            if not res:
                total_failed += 1
                try:
                    failed_list.append({"qid": qid, "title": title, "cat": cat_name})
                except Exception:
                    pass
                done_qids.add(qid)'''
assert src.count(old_fail) == 1, "fail: %d" % src.count(old_fail)
src = src.replace(old_fail, new_fail, 1)

old_pre = '    total_added = 0\n    total_failed = 0'
new_pre = '    total_added = 0\n    total_failed = 0\n    failed_list = []'
assert src.count(old_pre) == 1, "pre: %d" % src.count(old_pre)
src = src.replace(old_pre, new_pre, 1)

old_end = '    print("[GROW] (القاعدة محفوظة بعد كل فئة)")'
new_end = '''    print("[GROW] (القاعدة محفوظة بعد كل فئة)")
    try:
        import json as _json
        with open("grow_failed.json", "w", encoding="utf-8") as _f:
            _json.dump(failed_list, _f, ensure_ascii=False, indent=2)
        print("[GROW] سجل الفاشلين: grow_failed.json (%d)" % len(failed_list))
    except Exception as _e:
        print("[GROW] فشل حفظ سجل الفشل:", _e)'''
assert src.count(old_end) == 1, "end: %d" % src.count(old_end)
src = src.replace(old_end, new_end, 1)

open(p, 'w', encoding='utf-8').write(src)
print("OK")
