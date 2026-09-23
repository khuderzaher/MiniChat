import os, sys, shutil

p = 'cognition.py'
bak = p + '.before_nosem'
if os.path.exists(bak):
    print("NOTE: backup exists"); sys.exit(1)
shutil.copy(p, bak); print("backup:", bak)

src = open(p, encoding='utf-8').read()

# 1) اجعل استيراد SemanticEngine اختياريًا
old_imp = 'from semantic_engine import SemanticEngine'
new_imp = '''try:
    from semantic_engine import SemanticEngine
except Exception:
    SemanticEngine = None'''
assert src.count(old_imp) == 1, "import: %d" % src.count(old_imp)
src = src.replace(old_imp, new_imp, 1)

# 2) لا تبنِه
old_init = '        self.semantic = SemanticEngine(db)'
new_init = '''        self.semantic = None
        # SemanticEngine معطّل: كان يستهلك 28 MB RAM بلا مستخدم بعد إزالة 6.b
        # (يُعاد تفعيله عند الحاجة)'''
assert src.count(old_init) == 1, "init: %d" % src.count(old_init)
src = src.replace(old_init, new_init, 1)

# 3) اجعل expand_query آمنًا
old_expand = "            'expanded': self.semantic.expand_query(query),"
new_expand = "            'expanded': (self.semantic.expand_query(query) if self.semantic else []),"
assert src.count(old_expand) == 1, "expand: %d" % src.count(old_expand)
src = src.replace(old_expand, new_expand, 1)

# 4) related_words آمن
old_rel = '''    def related(self, word, top=5):
        return self.semantic.related_words(word, top)'''
new_rel = '''    def related(self, word, top=5):
        if self.semantic is None:
            return []
        return self.semantic.related_words(word, top)'''
assert src.count(old_rel) == 1, "related: %d" % src.count(old_rel)
src = src.replace(old_rel, new_rel, 1)

open(p, 'w', encoding='utf-8').write(src)
print("OK")
