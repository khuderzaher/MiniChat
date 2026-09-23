import os, sys, shutil

p = 'scripts/grow_knowledge.py'
bak = p + '.before_ratelimit'
if os.path.exists(bak):
    print("NOTE: backup exists"); sys.exit(1)
shutil.copy(p, bak); print("backup:", bak)

src = open(p, encoding='utf-8').read()

# 1) نضيف دالة sparql_with_retry قبل CATEGORIES
old_anchor = "def sparql(query, timeout=90):"
new_block = '''def sparql_with_retry(query, retries=3, base_wait=70, timeout=90):
    """يستدعي SPARQL مع retry عند 429 (rate limit)."""
    last_err = None
    for attempt in range(retries):
        try:
            return sparql(query, timeout=timeout)
        except Exception as e:
            last_err = e
            msg = str(e)
            if "429" in msg or "rate" in msg.lower():
                wait = base_wait * (attempt + 1)
                print("[GROW] rate-limited، انتظار %ds..." % wait)
                time.sleep(wait)
                continue
            raise
    raise last_err


'''
assert src.count(old_anchor) == 1
src = src.replace(old_anchor, new_block + old_anchor, 1)

# 2) استبدل الاستدعاء المباشر بـ retry + sleep بين الفئات
old_call = '            data = sparql(query)'
new_call = '            data = sparql_with_retry(query)'
assert src.count(old_call) == 1
src = src.replace(old_call, new_call, 1)

# 3) sleep بين الفئات (قبل نهاية كل loop)
old_end = '''        print("[GROW] فئة %s: أضيف %d" % (cat_name, added_cat))
        prog["done_qids"] = sorted(done_qids)'''
new_end = '''        print("[GROW] فئة %s: أضيف %d" % (cat_name, added_cat))
        prog["done_qids"] = sorted(done_qids)'''
# no change here, instead add sleep before "for cat_name":

old_loop = '''    for cat_name, query_tpl, cat_limit in CATEGORIES:
        cat_limit = max(1, int(cat_limit * scale))'''
new_loop = '''    for cat_i, (cat_name, query_tpl, cat_limit) in enumerate(CATEGORIES):
        if cat_i > 0:
            print("[GROW] انتظار 75s بين الفئات (rate limit)…")
            time.sleep(75)
        cat_limit = max(1, int(cat_limit * scale))'''
assert src.count(old_loop) == 1
src = src.replace(old_loop, new_loop, 1)

open(p, 'w', encoding='utf-8').write(src)
print("OK: تم التعديل")
