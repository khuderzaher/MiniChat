# -*- coding: utf-8 -*-
"""smart_summarizer.py — تلخيص ذكي واستخراج نقاط"""
import re
from collections import Counter
from arabic_utils import normalize_arabic, extract_core_tokens, ARABIC_STOPWORDS


class SmartSummarizer:
    """يلخص النصوص العربية ويستخرج النقاط المهمة."""

    @staticmethod
    def split_sentences(text):
        """يقسم النص إلى جمل."""
        # قسّم على . ! ؟ ؛
        t = text.strip()
        # ضع مسافة بعد علامات النهاية
        t = re.sub(r"([.!؟?؛])\s*", r"\1\n", t)
        parts = [s.strip() for s in t.split("\n") if s.strip()]
        return parts

    @staticmethod
    def score_sentence(sentence, word_freq, position, total):
        """يقيّم أهمية جملة."""
        tokens = extract_core_tokens(sentence, remove_stopwords=True)
        if not tokens:
            return 0.0
        # متوسط تكرار الكلمات
        score = sum(word_freq.get(t, 0) for t in tokens) / len(tokens)
        # طول الجملة (يفضل الطويلة قليلاً)
        length_bonus = min(len(tokens), 20) / 20.0
        # الجمل الأولى أكثر أهمية
        pos_bonus = 1.0 - (position / max(total, 1)) * 0.5
        return score * length_bonus * pos_bonus

    @staticmethod
    def summarize(text, max_sentences=3, max_chars=600):
        """يعيد ملخص بسيط."""
        if not text:
            return ""
        sents = SmartSummarizer.split_sentences(text)
        if len(sents) <= max_sentences:
            return text[:max_chars]

        # احسب تكرار الكلمات
        all_tokens = extract_core_tokens(text, remove_stopwords=True)
        word_freq = Counter(all_tokens)

        # رتّب الجمل
        scored = [(i, s, SmartSummarizer.score_sentence(s, word_freq, i, len(sents)))
                  for i, s in enumerate(sents)]
        top = sorted(scored, key=lambda x: -x[2])[:max_sentences]
        # رتّب حسب الترتيب الأصلي
        top.sort(key=lambda x: x[0])

        summary = " ".join(s for _, s, _ in top)
        return summary[:max_chars]

    @staticmethod
    def extract_keywords(text, top=5):
        """كلمات مفتاحية."""
        tokens = extract_core_tokens(text, remove_stopwords=True)
        # شيل القصيرة جدًا
        tokens = [t for t in tokens if len(t) > 2]
        freq = Counter(tokens)
        # فضّل الأطول قليلاً
        ranked = sorted(freq.items(),
                        key=lambda x: (-x[1], -len(x[0])))
        return [w for w, _ in ranked[:top]]

    @staticmethod
    def extract_numbers(text):
        """يستخرج الأرقام المهمة (تواريخ، سنوات، كميات)."""
        out = {}
        # سنوات
        years = re.findall(r"\b(1[0-9]{3}|20[0-9]{2})\b", text)
        if years:
            out["سنوات"] = years[:5]
        # أرقام عامة
        numbers = re.findall(r"\b\d+(?:\.\d+)?\b", text)
        if numbers:
            out["أرقام"] = list(dict.fromkeys(numbers))[:5]
        # نسب
        percents = re.findall(r"(\d+(?:\.\d+)?)\s*%", text)
        if percents:
            out["نسب"] = ["%s%%" % p for p in percents[:5]]
        return out

    @staticmethod
    def extract_proper_nouns(text):
        """أسماء أعلام بسيطة (كلمات بعد: هو، هي، قال، ابن، الملك، السيد)."""
        pattern = r"(?:هو|هي|قال|ابنه|ابن|الملك|السيد|الدكتور|الأستاذ|الرئيس|الشيخ)\s+([\u0600-\u06FF]{3,20})"
        matches = re.findall(pattern, text)
        return list(dict.fromkeys(matches))[:5]

    @staticmethod
    def key_points(text, max_points=4, max_chars=800):
        """يعيد نقاط مفتاحية بشكل قائمة."""
        if not text:
            return []
        sents = SmartSummarizer.split_sentences(text)
        if not sents:
            return []
        if len(sents) <= max_points:
            return [s[:180] for s in sents]

        all_tokens = extract_core_tokens(text, remove_stopwords=True)
        freq = Counter(all_tokens)
        scored = [(i, s, SmartSummarizer.score_sentence(s, freq, i, len(sents)))
                  for i, s in enumerate(sents)]
        top = sorted(scored, key=lambda x: -x[2])[:max_points]
        top.sort(key=lambda x: x[0])
        return [s[:180] for _, s, _ in top]

    @staticmethod
    def format_summary(text, title=None):
        """شكل نهائي جميل."""
        summary = SmartSummarizer.summarize(text, max_sentences=3)
        keywords = SmartSummarizer.extract_keywords(text, top=5)
        numbers = SmartSummarizer.extract_numbers(text)

        lines = []
        if title:
            lines.append("📝 %s" % title)
            lines.append("─" * min(40, len(title) + 5))
        lines.append(summary)
        lines.append("")
        if keywords:
            lines.append("🔑 كلمات: %s" % " • ".join(keywords))
        if numbers:
            for k, v in numbers.items():
                lines.append("🔢 %s: %s" % (k, " • ".join(v)))
        return "\n".join(lines)


if __name__ == "__main__":
    sample = (
        "القلب هو عضو عضلي عند البشر والحيوانات الأخرى. "
        "يضخ الدم عبر الأوعية الدموية في الدورة الدموية. "
        "يزود الدم الجسم بالأكسجين والمغذيات. "
        "يقع القلب بين الرئتين في الحجرة الوسطى للصدر. "
        "ينبض القلب حوالي 100 ألف نبضة يوميًا. "
        "يتكون القلب من أربع حجرات."
    )
    print(SmartSummarizer.format_summary(sample, "القلب"))
