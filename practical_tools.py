# -*- coding: utf-8 -*-
"""practical_tools.py — أدوات عملية (وحدات، تواريخ، حساب)"""
import re
import math
from datetime import datetime, timedelta, date


class PracticalTools:
    """أدوات يومية عملية."""

    # ═══════════════════════════════════════════════════════════
    # وحدات القياس
    # ═══════════════════════════════════════════════════════════
    UNITS = {
        # طول (بالأمتار)
        "كم": ("length", 1000.0), "كيلومتر": ("length", 1000.0),
        "م": ("length", 1.0), "متر": ("length", 1.0),
        "سم": ("length", 0.01), "سنتيمتر": ("length", 0.01),
        "مم": ("length", 0.001), "مليمتر": ("length", 0.001),
        "ميل": ("length", 1609.34),
        "قدم": ("length", 0.3048), "بوصة": ("length", 0.0254),
        "ياردة": ("length", 0.9144),
        # وزن (بالكيلوغرام)
        "كغ": ("mass", 1.0), "كيلو": ("mass", 1.0), "كيلوغرام": ("mass", 1.0),
        "غ": ("mass", 0.001), "غرام": ("mass", 0.001),
        "طن": ("mass", 1000.0),
        "رطل": ("mass", 0.4536),
        "أونصة": ("mass", 0.0283), "اونصة": ("mass", 0.0283),
        # حجم (باللتر)
        "ل": ("volume", 1.0), "لتر": ("volume", 1.0),
        "مل": ("volume", 0.001),
        "غالون": ("volume", 3.7854),
        # زمن (بالثواني)
        "ث": ("time", 1.0), "ثانية": ("time", 1.0),
        "د": ("time", 60.0), "دقيقة": ("time", 60.0),
        "س": ("time", 3600.0), "ساعة": ("time", 3600.0),
        "يوم": ("time", 86400.0),
        "أسبوع": ("time", 604800.0),
        "شهر": ("time", 2629800.0),  # متوسط
        "سنة": ("time", 31557600.0),
    }

    @staticmethod
    def convert_units(value, from_u, to_u):
        from_u = from_u.strip()
        to_u = to_u.strip()
        if from_u not in PracticalTools.UNITS or to_u not in PracticalTools.UNITS:
            return None
        fcat, fmult = PracticalTools.UNITS[from_u]
        tcat, tmult = PracticalTools.UNITS[to_u]
        if fcat != tcat:
            return None
        base = float(value) * fmult
        result = base / tmult
        if abs(result - round(result)) < 1e-6:
            result = int(round(result))
        else:
            result = round(result, 4)
        return result

    # ═══════════════════════════════════════════════════════════
    # الحرارة
    # ═══════════════════════════════════════════════════════════
    @staticmethod
    def temp_convert(value, from_u):
        try:
            v = float(value)
        except (ValueError, TypeError):
            return None
        f = from_u.upper().strip()
        if f in ("C", "°C", "مئوي", "سيلزيوس"):
            return {"F": v * 9 / 5 + 32, "K": v + 273.15, "C": v}
        if f in ("F", "°F", "فهرنهايت"):
            c = (v - 32) * 5 / 9
            return {"C": round(c, 2), "K": round(c + 273.15, 2), "F": v}
        if f in ("K", "كلفن"):
            c = v - 273.15
            return {"C": round(c, 2), "F": round(c * 9 / 5 + 32, 2), "K": v}
        return None

    # ═══════════════════════════════════════════════════════════
    # التواريخ
    # ═══════════════════════════════════════════════════════════
    AR_MONTHS = [
        "يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو",
        "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر",
    ]
    AR_WEEKDAYS = [
        "الاثنين", "الثلاثاء", "الأربعاء", "الخميس",
        "الجمعة", "السبت", "الأحد",
    ]

    @staticmethod
    def today():
        t = date.today()
        wd = PracticalTools.AR_WEEKDAYS[t.weekday()]
        return "%s، %d %s %d" % (wd, t.day, PracticalTools.AR_MONTHS[t.month - 1], t.year)

    @staticmethod
    def now():
        t = datetime.now()
        return t.strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def days_between(d1_str, d2_str):
        """يفرق بين تاريخين (YYYY-MM-DD)."""
        try:
            d1 = datetime.strptime(d1_str.strip(), "%Y-%m-%d").date()
            d2 = datetime.strptime(d2_str.strip(), "%Y-%m-%d").date()
            return abs((d2 - d1).days)
        except ValueError:
            return None

    @staticmethod
    def add_days(date_str, n):
        try:
            d = datetime.strptime(date_str.strip(), "%Y-%m-%d").date()
            r = d + timedelta(days=int(n))
            return r.strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            return None

    # ═══════════════════════════════════════════════════════════
    # النسب والحساب
    # ═══════════════════════════════════════════════════════════
    @staticmethod
    def percent_of(p, total):
        try:
            return round(float(p) * float(total) / 100.0, 4)
        except Exception:
            return None

    @staticmethod
    def percent_change(old, new):
        try:
            o = float(old); n = float(new)
            if o == 0:
                return None
            return round((n - o) / o * 100.0, 2)
        except Exception:
            return None

    @staticmethod
    def split_bill(amount, people, tip_pct=0):
        try:
            a = float(amount); p = int(people); t = float(tip_pct)
            total = a * (1 + t / 100.0)
            return {
                "total": round(total, 2),
                "per_person": round(total / p, 2),
                "tip": round(a * t / 100.0, 2),
            }
        except Exception:
            return None

    # ═══════════════════════════════════════════════════════════
    # استخراج تلقائي من النص
    # ═══════════════════════════════════════════════════════════
    @staticmethod
    def parse_conversion(text):
        """يحلل طلب تحويل وحدة. مثل: '5 كم إلى متر' أو '10 كغ كم غرام'"""
        # نمط: <رقم> <وحدة> (إلى|كم|=) <وحدة>
        patterns = [
            r"(\d+(?:\.\d+)?)\s*([\u0600-\u06FF]+)\s*(?:إلى|الى|لـ|كم|يساوي|=)\s*([\u0600-\u06FF]+)",
            r"(?:حول|حوّل)\s+(\d+(?:\.\d+)?)\s*([\u0600-\u06FF]+)\s+(?:إلى|الى|لـ)\s*([\u0600-\u06FF]+)",
        ]
        for p in patterns:
            m = re.search(p, text)
            if m:
                val, fu, tu = m.group(1), m.group(2), m.group(3)
                # جرّب تحويل الحرارة أولاً
                if fu in ("مئوي", "فهرنهايت", "كلفن") or tu in ("مئوي", "فهرنهايت", "كلفن"):
                    t = PracticalTools.temp_convert(val, fu)
                    if t and tu in ("مئوي", "C"):
                        return {"kind": "temp", "value": t["C"], "unit": "°C"}
                    if t and tu in ("فهرنهايت", "F"):
                        return {"kind": "temp", "value": round(t["F"], 2), "unit": "°F"}
                # تحويل وحدات عادي
                res = PracticalTools.convert_units(val, fu, tu)
                if res is not None:
                    return {"kind": "unit", "value": res, "from": fu, "to": tu}
        return None

    @staticmethod
    def parse_percent(text):
        """يحلل: '10% من 200' أو 'نسبة 50 من 200'"""
        patterns = [
            r"(\d+(?:\.\d+)?)\s*%\s*من\s*(\d+(?:\.\d+)?)",
            r"(\d+(?:\.\d+)?)\s*بالمئة\s*من\s*(\d+(?:\.\d+)?)",
        ]
        for p in patterns:
            m = re.search(p, text)
            if m:
                v = PracticalTools.percent_of(m.group(1), m.group(2))
                if v is not None:
                    return {"kind": "percent_of", "value": v}
        return None


if __name__ == "__main__":
    print("5 كم → متر:", PracticalTools.convert_units(5, "كم", "م"))
    print("10 كغ → غ:", PracticalTools.convert_units(10, "كغ", "غ"))
    print("100°C → F:", PracticalTools.temp_convert(100, "C"))
    print("اليوم:", PracticalTools.today())
    print("10% من 250:", PracticalTools.percent_of(10, 250))
    print("تحليل:", PracticalTools.parse_conversion("5 كم إلى متر"))
