import os, sys, shutil

p = 'scripts/grow_knowledge.py'
bak = p + '.before_save_each_cat'
if os.path.exists(bak):
    print("NOTE: backup exists"); sys.exit(1)
shutil.copy(p, bak); print("backup:", bak)

src = open(p, encoding='utf-8').read()

old = '''        print("[GROW] فئة %s: أضيف %d" % (cat_name, added_cat))
        prog["done_qids"] = sorted(done_qids)
        prog["done_titles"] = sorted(done_titles)
        save_prog(prog)'''

new = '''        print("[GROW] فئة %s: أضيف %d" % (cat_name, added_cat))
        # احفظ القاعدة أولًا ثم التقدم
        # (ترتيب مهم: لو انقطع بينهما، الحد الأقصى = تكرار بلا فقدان)
        db["faq"] = faq
        save_db(db)
        prog["done_qids"] = sorted(done_qids)
        prog["done_titles"] = sorted(done_titles)
        save_prog(prog)'''

assert src.count(old) == 1, "found %d" % src.count(old)
src = src.replace(old, new, 1)

# أزل save_db النهائي لتجنب نسخة احتياطية مكررة
old_end = '''    db["faq"] = faq
    print()
    print("[GROW] إجمالي المضاف:", total_added)
    print("[GROW] إجمالي فشل:", total_failed)
    print("[GROW] إجمالي FAQ بعد:", len(faq))
    save_db(db)'''
new_end = '''    print()
    print("[GROW] إجمالي المضاف:", total_added)
    print("[GROW] إجمالي فشل:", total_failed)
    print("[GROW] إجمالي FAQ بعد:", len(faq))
    print("[GROW] (القاعدة محفوظة بعد كل فئة)")'''
assert src.count(old_end) == 1
src = src.replace(old_end, new_end, 1)

open(p, 'w', encoding='utf-8').write(src)
print("OK")
