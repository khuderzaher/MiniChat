# -*- coding: utf-8 -*-
"""math_engine.py — محرك رياضيات متقدم"""
import re
import math
from datetime import datetime


class MathEngine:
    SAFE_CHARS = set("0123456789+-*/.()%^ ")

    @staticmethod
    def is_safe(expr):
        return all(c in MathEngine.SAFE_CHARS for c in expr)

    @staticmethod
    def evaluate(expr):
        """يقيّم تعبير رياضي بأمان."""
        e = expr.strip()
        # استبدل الرموز العربية
        e = e.replace("×", "*").replace("÷", "/").replace("^", "**")
        e = e.replace("٪", "/100")
        if not MathEngine.is_safe(e.replace("**", "^")):
            return None
        try:
            result = eval(e, {"__builtins__": {}}, {"sqrt": math.sqrt, "pi": math.pi, "e": math.e})
            if isinstance(result, (int, float)):
                if abs(result - round(result)) < 1e-9:
                    return int(round(result))
                return round(result, 6)
        except Exception:
            return None
        return None

    @staticmethod
    def percent(what, of):
        try:
            return (float(what) / float(of)) * 100.0
        except Exception:
            return None

    @staticmethod
    def percent_of(percent, total):
        try:
            return (float(percent) * float(total)) / 100.0
        except Exception:
            return None

    @staticmethod
    def solve_linear(eq):
        """يحل معادلة خطية مثل: 2x + 5 = 15"""
        e = eq.replace(" ", "").replace("−", "-")
        if "=" not in e:
            return None
        left, right = e.split("=", 1)
        # نمط: ax + b = c
        m = re.match(r"^(-?\d*)([a-z])?([+-]\d+)?$", left)
        if not m:
            return None
        a_str, var, b_str = m.groups()
        if not var:
            return None
        a = int(a_str) if a_str and a_str not in ("", "-") else (1 if not a_str else -1)
        b = int(b_str) if b_str else 0
        try:
            c = int(right)
        except ValueError:
            return None
        # ax + b = c → x = (c - b) / a
        x = (c - b) / a
        if abs(x - round(x)) < 1e-9:
            x = int(round(x))
        return {"var": var, "value": x}

    @staticmethod
    def stats(numbers):
        if not numbers:
            return None
        s = sorted(numbers)
        n = len(s)
        mean = sum(s) / n
        # median
        if n % 2:
            median = s[n // 2]
        else:
            median = (s[n // 2 - 1] + s[n // 2]) / 2
        # mode
        from collections import Counter
        cnt = Counter(s)
        mode = cnt.most_common(1)[0][0]
        # std
        var = sum((x - mean) ** 2 for x in s) / n
        std = math.sqrt(var)
        return {
            "count": n, "min": s[0], "max": s[-1],
            "mean": round(mean, 4), "median": median,
            "mode": mode, "std": round(std, 4),
            "sum": sum(s),
        }

    UNITS = {
        "كم": 1000.0, "م": 1.0, "سم": 0.01, "مم": 0.001,
        "ميل": 1609.34, "ياردة": 0.9144, "قدم": 0.3048, "بوصة": 0.0254,
        "كغ": 1.0, "غ": 0.001, "طن": 1000.0, "رطل": 0.4536,
        "ل": 1.0, "مل": 0.001,
    }

    @staticmethod
    def convert(value, from_u, to_u):
        try:
            if from_u not in MathEngine.UNITS or to_u not in MathEngine.UNITS:
                return None
            base = float(value) * MathEngine.UNITS[from_u]
            return round(base / MathEngine.UNITS[to_u], 6)
        except Exception:
            return None

    @staticmethod
    def parse_arabic_numbers(text):
        """يستخرج كل الأرقام من نص."""
        return [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?", text)]


if __name__ == "__main__":
    print(MathEngine.evaluate("3 + 5 * 2"))
    print(MathEngine.solve_linear("2x + 5 = 15"))
    print(MathEngine.stats([1,2,3,4,5]))
    print(MathEngine.convert(5, "كم", "م"))
