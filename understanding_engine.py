# -*- coding: utf-8 -*-
"""understanding_engine.py — فهم عميق للنية والسياق"""
import re
from arabic_utils import normalize_arabic, canonical


# ═══════════════════════════════════════════════════════════════
# 1) تصنيف نوع السؤال
# ═══════════════════════════════════════════════════════════════
QUESTION_TYPES = {
    "define": ["ما هو", "ما هي", "ما معنى", "عرف", "تعريف", "اشرح"],
    "who": ["من هو", "من هي", "من هم", "من الذي", "من التي"],
    "where": ["اين", "أين", "وين", "في أي مكان", "بأي بلد"],
    "when": ["متى", "متي", "في أي سنة", "في أي عام", "في أي قرن"],
    "why": ["لماذا", "ليش", "ما سبب", "ما السبب", "بسبب ماذا"],
    "how": ["كيف", "شلون", "كيفاش", "بأي طريقة"],
    "how_many": ["كم", "كم عدد", "كم يبلغ", "كم يساوي"],
    "compare": ["الفرق", "قارن", "أيهما", "الافضل", "ما الفرق"],
    "list": ["اذكر", "عدد", "ما هي أنواع", "ما هي أشهر"],
    "classify": ["ما تصنيف", "ما نوع", "من أي فئة", "اي فصيلة"],
    "relation": ["ما علاقة", "ما هي علاقة", "كيف يرتبط", "ما الرابط"],
    "reason_chain": ["لماذا يحدث", "ما يؤدي", "ما يسبب", "ما نتيجة"],
}


def classify_question(text):
    """يحدد نوع السؤال."""
    t = normalize_arabic(text).strip()

    # ---------------------------------------------
    # أسئلة الاستدلال والمنطق
    # ---------------------------------------------
    # لا نعتبر كل "هل" سؤالًا منطقيًا.
    # نبحث عن بنية تحقق/استنتاج واضحة.
    logic_patterns = (
        r"^اذا كان .+ فهل .+",
        r"^اذا كانت .+ فهل .+",
        r"^هل .+ هو .+",
        r"^هل .+ هي .+",
        r"^هل يمكن ان يكون .+ و.+ في الوقت نفسه",
        r"^هل يمكن ان يكون .+ وغير .+",
    )

    for pattern in logic_patterns:
        if re.search(pattern, t):
            return "logic"

    # رتّب حسب الأولوية (الأطول أولاً)
    for qtype, patterns in QUESTION_TYPES.items():
        for p in patterns:
            if p in t:
                return qtype

    return "general"


# ═══════════════════════════════════════════════════════════════
# 2) استخراج الموضوع الحقيقي (بعد كلمة الاستفهام)
# ═══════════════════════════════════════════════════════════════
STOP_WORDS = {"ما", "هو", "هي", "من", "في", "على", "عن", "إلى",
              "التي", "الذي", "اي", "أي", "و", "أو", "ثم"}


def extract_topic(text):
    """استخراج الموضوع الأساسي (يحتفظ بالحروف المهمة)."""
    t = normalize_arabic(text).strip(" ؟?،.")
    for patterns in QUESTION_TYPES.values():
        for p in patterns:
            t = t.replace(p, " ")
    t = re.sub(r"[؟?،.()\[\]{}]", " ", t)
    words = [w.strip() for w in t.split() if w.strip()]
    TRIGGERS = ("فيتامين", "سوره", "ايه", "نوع", "فصيله", "درجه",
                "مرحله", "شكل", "حرف", "بند", "فقره", "ماده", "رقم")
    KEEP_SINGLE = {"د", "س", "ب", "ج", "ك", "أ", "إ", "آ", "ي", "ط",
                   "ص", "ع", "م", "ن", "ف", "ق", "ر", "ت", "ز", "ح",
                   "خ", "ذ", "ش", "ض", "ظ", "غ", "ث", "ه"}
    out = []
    prev = ""
    for w in words:
        if len(w) >= 2:
            if w not in STOP_WORDS:
                out.append(w)
            prev = w
            continue
        if w in KEEP_SINGLE and any(tr in prev for tr in TRIGGERS):
            out.append(w)
        prev = w
    return " ".join(out).strip()

# ═══════════════════════════════════════════════════════════════
# 3) سياق الجملة (مفاهيم مهمة)
# ═══════════════════════════════════════════════════════════════
CONTEXT_HINTS = {
    "health": ["مرض", "علاج", "صحه", "دواء", "اعراض", "علاج",
               "سرطان", "سكري", "وجع"],
    "animal": ["حيوان", "طائر", "سمك", "زاحف", "حشرة", "كلب",
               "قط", "اسد", "فيل"],
    "tech": ["حاسوب", "برمجه", "تطبيق", "موقع", "شبكه", "انترنت",
             "ذكاء", "بيانات"],
    "science": ["ذره", "جزيء", "كيمياء", "فيزياء", "طبيعه", "طاقه"],
    "geo": ["مدينه", "دوله", "عاصمه", "نهر", "جبل", "بحر", "قاره"],
    "history": ["تاريخ", "حرب", "معركه", "امبراطوريه", "قديم"],
    "religion": ["اسلام", "قران", "حديث", "صلاه", "زكاه", "رسول",
                 "نبي", "صحابه"],
    "people": ["ملك", "رئيس", "شاعر", "كاتب", "عالم", "قائد", "طبيب"],
}


def detect_contexts(text):
    """يكتشف سياقات الجملة باستخدام مطابقة كلمات كاملة."""
    t = normalize_arabic(text)
    tokens = set(t.split())
    contexts = []

    for ctx, kws in CONTEXT_HINTS.items():
        for kw in kws:
            if kw in tokens:
                contexts.append(ctx)
                break

    return contexts


# ═══════════════════════════════════════════════════════════════
# 4) فهم السؤال كاملًا
# ═══════════════════════════════════════════════════════════════
class Understanding:
    def __init__(self):
        self.last_topic = None
        self.last_question_type = None
        self.last_contexts = []

    def analyze(self, text):
        """تحليل كامل."""
        result = {
            "original": text,
            "question_type": classify_question(text),
            "topic": extract_topic(text),
            "contexts": detect_contexts(text),
            "tokens": normalize_arabic(text).split(),
        }
        self.last_topic = result["topic"]
        self.last_question_type = result["question_type"]
        self.last_contexts = result["contexts"]
        return result

    def disambiguate(self, word, contexts):
        """
        يفك الالتباس: إذا كلمة لها أكثر من معنى،
        يفضّل المعنى المناسب للسياق.
        """
        # كلمات متعددة المعاني
        AMBIGUOUS = {
            "سرطان": ["animal", "health"],
            "عين": ["body", "geo", "language"],
            "بحر": ["geo", "language"],
            "حرب": ["history", "language"],
            "شمس": ["science", "geo"],
            "قمر": ["science", "geo"],
            "برج": ["geo", "history", "zodiac"],
            "فيل": ["animal", "chess"],
            "ملك": ["people", "chess"],
        }
        if word in AMBIGUOUS:
            allowed = AMBIGUOUS[word]
            # 1) ابحث عن تطابق مع السياق
            for ctx in contexts:
                if ctx in allowed:
                    return {"word": word, "preferred_context": ctx,
                            "candidates": allowed}
            # 2) لا سياق — اختر الأنسب افتراضيًا
            DEFAULT_PREF = {
                "سرطان": "health",
                "عين": "body",
                "بحر": "geo",
                "شمس": "science",
                "قمر": "science",
                "فيل": "animal",
                "ملك": "people",
            }
            if word in DEFAULT_PREF:
                return {"word": word, "preferred_context": DEFAULT_PREF[word],
                        "candidates": allowed}
        return {"word": word, "preferred_context": None,
                "candidates": []}


def get_understanding_engine():
    return Understanding()
