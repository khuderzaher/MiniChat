#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys, shutil

HOME = os.path.expanduser("~")
PATH = os.path.join(HOME, "MiniChat", "main.py")
BACKUP = PATH + ".v34_before_refactor"

if not os.path.exists(PATH):
    print("ما لقيت main.py"); sys.exit(1)

shutil.copy(PATH, BACKUP)
print("نسخة احتياطية: " + BACKUP)

with open(PATH, "r", encoding="utf-8") as f:
    src = f.read()

START = "        # 1) اكشف السياق"
END = "        # اكشف المزاج"

i = src.find(START)
if i == -1:
    print("ما لقيت بداية بلوك السياق"); sys.exit(1)
start_eol = src.find("\n", i)
j = src.find(END, start_eol)
if j == -1:
    print("ما لقيت نهاية بلوك السياق"); sys.exit(1)

block = src[start_eol+1:j].rstrip()
src = src[:i] + src[j:]

method = (
    "    def _route_context(self, text, lang):\n"
    "        _original_text = text\n"
    + block
    + "\n        return None\n\n"
)

ANCHOR = '        lang = "ar" if is_arabic(text) else "en"\n'
if ANCHOR not in src:
    print("ما لقيت سطر lang")
    print("رجّع: cp " + BACKUP + " " + PATH)
    sys.exit(1)

CALL = ANCHOR + (
    "\n        # [0] سياق\n"
    "        _ctx = self._route_context(text, lang)\n"
    "        if _ctx is not None:\n"
    "            return _ctx\n"
)
src = src.replace(ANCHOR, CALL, 1)

RD = "    def respond(self, text, allow_shortcut=True):"
if RD not in src:
    print("ما لقيت def respond"); sys.exit(1)
src = src.replace(RD, method + RD, 1)

with open(PATH, "w", encoding="utf-8") as f:
    f.write(src)

print("تم.")
print("اختبر:")
print("  cd ~/MiniChat && python3 main.py --chat")
print("  اسأل: ما هي سورة الكوثر")
print("  بعدين: كم آية فيها؟")
print("للاسترجاع: cp " + BACKUP + " " + PATH)
