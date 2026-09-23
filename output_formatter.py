# -*- coding: utf-8 -*-
"""output_formatter.py — تنظيم المخرجات"""
import re


class Formatter:
    MAX_LINE = 70

    @staticmethod
    def clean(text):
        if not text:
            return ""
        # وحّد المسافات
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    @staticmethod
    def truncate(text, max_chars=500):
        if len(text) <= max_chars:
            return text
        cut = text[:max_chars]
        # اقطع عند آخر جملة
        m = max(cut.rfind("."), cut.rfind("،"), cut.rfind("!"), cut.rfind("?"))
        if m > max_chars * 0.6:
            return cut[:m+1].strip()
        return cut.rsplit(" ", 1)[0] + "..."

    @staticmethod
    def definition(title, body):
        """تعريف بسيط أنيق."""
        body = Formatter.clean(Formatter.truncate(body, 600))
        return "📖 %s\n\n%s" % (title, body)

    @staticmethod
    def comparison(title_a, body_a, title_b, body_b):
        a = Formatter.clean(Formatter.truncate(body_a, 400))
        b = Formatter.clean(Formatter.truncate(body_b, 400))
        return (
            "⚖️ مقارنة: %s ↔ %s\n"
            "─────────────────────\n"
            "◾ %s:\n%s\n\n"
            "◾ %s:\n%s"
        ) % (title_a, title_b, title_a, a, title_b, b)

    @staticmethod
    def bullet_list(items, header=None):
        lines = []
        if header:
            lines.append(header)
            lines.append("─" * min(30, len(header)))
        for i, item in enumerate(items, 1):
            lines.append("  %d. %s" % (i, item))
        return "\n".join(lines)

    @staticmethod
    def steps(steps_list, header="📋 الخطوات:"):
        lines = [header, ""]
        for i, s in enumerate(steps_list, 1):
            lines.append("  %d️⃣  %s" % (i, s))
        return "\n".join(lines)

    @staticmethod
    def summary_plus(main, details_list, header="📌"):
        lines = [header + " " + main, ""]
        for d in details_list:
            lines.append("  • " + d)
        return "\n".join(lines)

    @staticmethod
    def warning(text):
        return "⚠️ " + text

    @staticmethod
    def info(text):
        return "ℹ️ " + text

    @staticmethod
    def success(text):
        return "✅ " + text

    @staticmethod
    def number_stats(stats):
        lines = ["📊 إحصائيات:"]
        lines.append("  • العدد: %s" % stats.get("count", "?"))
        lines.append("  • المجموع: %s" % stats.get("sum", "?"))
        lines.append("  • المتوسط: %s" % stats.get("mean", "?"))
        lines.append("  • الوسيط: %s" % stats.get("median", "?"))
        lines.append("  • الأدنى: %s | الأعلى: %s" % (stats.get("min"), stats.get("max")))
        return "\n".join(lines)

    @staticmethod
    def card(title, lines):
        """بطاقة بسيطة."""
        w = max(len(title) + 4, 30)
        top = "╭" + "─" * w + "╮"
        mid = "│ " + title.ljust(w - 2) + " │"
        bot = "╰" + "─" * w + "╯"
        body = "\n".join("  • " + l for l in lines)
        return top + "\n" + mid + "\n" + bot + "\n" + body


if __name__ == "__main__":
    print(Formatter.definition("القلب", "عضو عضلي يضخ الدم"))
    print()
    print(Formatter.comparison("فيروس", "كائن صغير", "بكتيريا", "كائن وحيد الخلية"))
    print()
    print(Formatter.steps(["افتح الملف", "عدّل الكود", "احفظ"]))
    print()
    print(Formatter.number_stats({"count": 5, "sum": 15, "mean": 3, "median": 3, "min": 1, "max": 5}))
