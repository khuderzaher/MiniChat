#!/data/data/com.termux/files/usr/bin/bash
# sync_to_pydroid.sh — نسخ المشروع من Termux إلى /sdcard/MiniChat/
SRC="$HOME/MiniChat"
DST="/sdcard/MiniChat"

if [ ! -d "$DST" ]; then
    echo "❌ المجلد الهدف غير موجود: $DST"
    exit 1
fi

echo "🔄 مزامنة $SRC → $DST"

# نسخ الملفات الأساسية
cp -v "$SRC"/*.py "$DST"/ 2>/dev/null
cp -v "$SRC"/*.json "$DST"/ 2>/dev/null
cp -v "$SRC"/*.pkl "$DST"/ 2>/dev/null
cp -v "$SRC"/*.sh "$DST"/ 2>/dev/null

# نسخ المجلدات
if [ -d "$SRC/templates" ]; then
    mkdir -p "$DST/templates"
    cp -v "$SRC/templates"/* "$DST/templates"/ 2>/dev/null
fi
if [ -d "$SRC/scripts" ]; then
    mkdir -p "$DST/scripts"
    cp -v "$SRC/scripts"/*.py "$DST/scripts"/ 2>/dev/null
    cp -v "$SRC/scripts"/*.json "$DST/scripts"/ 2>/dev/null
    cp -v "$SRC/scripts"/*.txt "$DST/scripts"/ 2>/dev/null
fi

echo ""
echo "✅ تمت المزامنة"
ls -lh "$DST"/*.json "$DST"/*.pkl 2>/dev/null | tail -8
