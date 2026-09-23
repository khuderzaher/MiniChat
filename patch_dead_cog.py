import os, sys, shutil

mp = 'main.py'
bak = 'main.py.before_dead_cognition_removal'

if os.path.exists(bak):
    print("NOTE: backup exists:", bak)
else:
    shutil.copy(mp, bak)
    print("backup:", bak)

with open(mp, encoding='utf-8') as f:
    lines = f.read().split('\n')

start_i = end_i = None
for i, ln in enumerate(lines):
    s = ln.strip()
    if s.startswith('# 6.b)') and start_i is None:
        start_i = i
    if s.startswith('# 6.b3)') and start_i is not None and end_i is None:
        end_i = i
        break

if start_i is None:
    print("ABORT: 6.b marker not found"); sys.exit(1)
if end_i is None:
    print("ABORT: 6.b3 marker not found"); sys.exit(1)
if end_i <= start_i:
    print("ABORT: order wrong"); sys.exit(1)

print("start line %d: %r" % (start_i, lines[start_i][:50]))
print("end   line %d: %r" % (end_i, lines[end_i][:50]))
print("deleting %d lines" % (end_i - start_i))

# preuve: الكتلة تحتوي السطر الذي يسبب الخطأ
block = '\n'.join(lines[start_i:end_i])
if 'understand(text)' not in block:
    print("ABORT: block does not contain understand() call"); sys.exit(1)
if 'placeholder' not in block:
    print("ABORT: block does not contain placeholder"); sys.exit(1)

new_lines = lines[:start_i] + lines[end_i:]
open(mp, 'w', encoding='utf-8').write('\n'.join(new_lines))
print("OK: تم الحذف")
