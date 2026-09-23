import os, sys, shutil

mp = 'main.py'
bak = mp + '.before_disable_cognition'
if os.path.exists(bak):
    print("NOTE: backup exists"); sys.exit(1)
shutil.copy(mp, bak); print("backup:", bak)

src = open(mp, encoding='utf-8').read()

# 1) حارس المقارنة: استبدل db.cognition بـ engine
old_gate = '''        # 6.a) محرك المقارنة (قبل كل شيء)
        if self.db.cognition is not None:'''
new_gate = '''        # 6.a) محرك المقارنة (قبل كل شيء)
        # ملاحظة: db.cognition لم يكن يُستخدم هنا إلا كحارس.
        # نستخدم self.engine لتفادي بناء Cognition بلا داعٍ.
        if self.engine is not None:'''
assert src.count(old_gate) == 1, "gate: %d" % src.count(old_gate)
src = src.replace(old_gate, new_gate, 1)

# 2) لا تبنِ Cognition في __init__
old_init = '''        # محرك الإدراك
        self.cognition = None
        if get_cognition is not None:
            try:
                self.cognition = get_cognition(self)
                print("[COG] ✅ محرك الإدراك جاهز")
            except Exception as e:
                print("[COG] ❌ فشل: %s" % e)
                traceback.print_exc()'''
new_init = '''        # محرك الإدراك معطّل: لم يعد له استخدام فعلي بعد إزالة 6.b
        # (يوفّر ~28 MB RAM + وقت إقلاع). يُعاد تفعيله عند الحاجة.
        self.cognition = None'''
assert src.count(old_init) == 1, "init: %d" % src.count(old_init)
src = src.replace(old_init, new_init, 1)

open(mp, 'w', encoding='utf-8').write(src)
print("OK")
