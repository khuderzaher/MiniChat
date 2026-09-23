# -*- coding: utf-8 -*-
"""cognition_v2.py — المنسق النهائي للإدراك والاستدلال"""
from understanding_engine import get_understanding_engine
from reasoning_chain import ReasoningChain
from learning_engine import get_learning_engine
from arabic_utils import normalize_arabic, canonical


class CognitionV2:
    """المحرك المنسق: يجمع الفهم + الاستدلال + التعلم."""

    def __init__(self, db=None):
        print("[COG2] تهيئة المحرك المنسق...")
        self.understanding = get_understanding_engine()
        self.reasoning = ReasoningChain()
        self.learning = get_learning_engine()
        print("[COG2] ✅ جاهز")

    # ═══════════════════════════════════════════════════════════
    # 1) تحليل كامل للسؤال
    # ═══════════════════════════════════════════════════════════
    def analyze(self, text):
        """تحليل عميق للسؤال."""
        analysis = self.understanding.analyze(text)
        # استدلال إضافي
        analysis["reasoning"] = {
            "why": self.reasoning.why_chain(text),
            "causal_chain": self.reasoning.causal_chain(text),
            "multi_hop": self.reasoning.multi_hop(text),
            "what_if": self.reasoning.what_if(text),
        }
        return analysis

    # ═══════════════════════════════════════════════════════════
    # 2) إجابة على "لماذا"
    # ═══════════════════════════════════════════════════════════
    def answer_why(self, text):
        """جواب منظم لسؤال 'لماذا'."""
        chain = self.reasoning.causal_chain(text)
        why = self.reasoning.why_chain(text)

        if not chain and not why:
            return None

        lines = []

        if why:
            lines.append("🤔 السبب:")
            lines.append("  %s → %s (%d%% ثقة)"
                         % (why["cause"], why["effect"],
                            int(why["confidence"] * 100)))
            lines.append("")

        if chain and len(chain) > 1:
            lines.append("🔗 سلسلة السبب-النتيجة:")
            for i, (c, e, conf) in enumerate(chain, 1):
                lines.append("  %d. %s → %s (%d%%)"
                             % (i, c, e, int(conf * 100)))

        return "\n".join(lines) if lines else None

    # ═══════════════════════════════════════════════════════════
    # 3) تصحيح الإجابة بناءً على التعلّم
    # ═══════════════════════════════════════════════════════════
    def check_answer(self, question, proposed_answer):
        """يتحقق إن كانت الإجابة خاطئة سابقًا."""
        if self.learning.is_bad_answer(question, proposed_answer):
            correct = self.learning.get_correct_answer(question)
            if correct:
                return {
                    "was_wrong": True,
                    "correct_answer": correct,
                    "note": "(صححتها بناءً على تعلم سابق)",
                }
        return None

    # ═══════════════════════════════════════════════════════════
    # 4) تسجيل نتيجة
    # ═══════════════════════════════════════════════════════════
    def record(self, question, answer, positive=True, correct=None):
        """يسجّل نتيجة سؤال."""
        if positive:
            self.learning.record_right(question, answer)
        else:
            self.learning.record_wrong(question, answer, correct)

    # ═══════════════════════════════════════════════════════════
    # 5) تصحيح الكلمات المتشابهة (استخدم السياق)
    # ═══════════════════════════════════════════════════════════
    def disambiguate(self, text):
        """
        يحدد الكلمات الغامضة ويقترح السياق.
        """
        analysis = self.understanding.analyze(text)
        contexts = analysis["contexts"]
        topic = analysis["topic"]

        # اختبر كل كلمة في الموضوع
        ambiguous = []
        for word in topic.split():
            disamb = self.understanding.disambiguate(word, contexts)
            if disamb["candidates"]:
                ambiguous.append(disamb)

        return {
            "contexts": contexts,
            "ambiguous_words": ambiguous,
        }

    # ═══════════════════════════════════════════════════════════
    # 6) اقتراح استدلال للبحث
    # ═══════════════════════════════════════════════════════════
    def enrich_query(self, text):
        """
        يوسّع الاستعلام بكلمات من الاستدلال.
        مثال: "السماء زرقاء" → يضيف "ضوء" + "تشتت"
        """
        analysis = self.understanding.analyze(text)
        enrichment = []

        # من سلاسل السبب
        chain = self.reasoning.causal_chain(text)
        for cause, effect, _ in chain[:2]:
            enrichment.append(cause)
            enrichment.append(effect)

        # من السياق
        CONTEXT_EXPANSIONS = {
            "health": ["مرض", "علاج", "أعراض"],
            "animal": ["حيوان", "كائن"],
            "tech": ["تقنية", "حاسوب"],
            "science": ["علم", "طبيعة"],
            "geo": ["جغرافيا", "مكان"],
            "history": ["تاريخ", "حدث"],
            "religion": ["دين", "إسلام"],
        }
        for ctx in analysis["contexts"]:
            enrichment.extend(CONTEXT_EXPANSIONS.get(ctx, []))

        # إزالة المكرر
        return list(dict.fromkeys(enrichment))

    # ═══════════════════════════════════════════════════════════
    # 7) إحصاءات شاملة
    # ═══════════════════════════════════════════════════════════
    def stats(self):
        """إحصاءات محرك الإدراك."""
        return {
            "learning": self.learning.stats(),
            "reasoning_rules": len(self.reasoning.causal),
            "context_types": len(self.understanding.__class__.__dict__),
        }


_COG2 = None

def get_cognition_v2(db=None):
    global _COG2
    if _COG2 is None:
        _COG2 = CognitionV2(db)
    return _COG2


if __name__ == "__main__":
    cog = get_cognition_v2()
    for q in ["لماذا تمطر السماء؟", "ما علاقة الشمس بالنبات"]:
        print("=" * 50)
        print("سؤال:", q)
        print("نوع:", cog.understanding.analyze(q)["question_type"])
        print("موضوع:", cog.understanding.analyze(q)["topic"])
        print("سياق:", cog.understanding.analyze(q)["contexts"])
        ans = cog.answer_why(q)
        if ans:
            print(ans)
