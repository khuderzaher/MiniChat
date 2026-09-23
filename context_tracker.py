# -*- coding: utf-8 -*-
"""context_tracker.py — تتبع السياق وربط الردود."""
import re
from arabic_utils import normalize_arabic, strip_definite


# ═══════════════════════════════════════════════════════════════
# الضمائر والإشارات
# ═══════════════════════════════════════════════════════════════
PRONOUNS = {
    # ضمائر مفرد مذكر
    "هو": "m", "له": "m", "عليه": "m", "منه": "m", "فيه": "m",
    "عنه": "m", "إليه": "m", "لديه": "m", "به": "m", "معو": "m",
    # ضمائر مفرد مؤنث
    "هي": "f", "لها": "f", "عليها": "f", "منها": "f", "فيها": "f",
    "عنها": "f", "إليها": "f", "لديها": "f", "بها": "f", "معها": "f",
    # أسماء إشارة
    "هذا": "m", "ذلك": "m", "هذه": "f", "تلك": "f",
    "هذول": "p", "هؤلاء": "p", "أولئك": "p", "هذيك": "f",
    # للإشارة للرد السابق
    "السابق": "*", "السابقة": "*", "المذكور": "*", "المذكورة": "*",
    "أكمل": "*", "كمل": "*", "تابع": "*",
}


# كلمات سؤال تبدأ بـ "ما" + ضمير
QUESTION_PATTERNS = [
    (r"ما (هو|هي)", "what"),
    (r"ما (وظيفت[هو]|دور[هو]|فائدت[هو]|أهميت[هو])", "function"),
    (r"كم (عدد|عمر|طول|وزن|سعر)", "how_many"),
    (r"(متى|في أي سنة|في أي عام)", "when"),
    (r"(أين|وين|في أي مكان)", "where"),
    (r"(من هو|من هي|من هم)", "who"),
    (r"(لماذا|ليش|ليش هيك)", "why"),
    (r"(كيف|شلون)", "how"),
    (r"(هل|هل هو|هل هي)", "yes_no"),
    (r"(أكمل|تابع|كمّل|زدني|المزيد|والمزيد)", "continue"),
]


# كلمات مهمة تنتهي بضمير متصل — نستبعدها (مش ضمائر)
KNOWN_WORDS_END_H = {"الله", "وجه", "شبه", "سنه", "سنة", "امه", "أمه",
                     "ابيه", "أبيه", "اخيه", "أخيه", "يده", "قلبه",
                     "مائه", "ماءه", "دمه", "عينه", "رأسه", "راسه",
                     "منه", "عنه", "فيه", "له", "به", "عليه", "إليه"}


def detect_attached_pronoun(word):
    """يكتشف الضمير المتصل في نهاية كلمة.

    مثال:
      "وظيفته" → base="وظيفة", suffix="ه"
      "فائدتها" → base="فائدة", suffix="ها"
      "آياتها" → base="آيات", suffix="ها"
      "دورهم" → base="دور", suffix="هم"
    """
    if not word or len(word) < 3:
        return None
    # الضمائر المتصلة: ه، ها، هم، هن، ك، كم، كن
    suffixes = [
        ("ها", "f"),   # مؤنث مفرد (فائدتها)
        ("هم", "p"),   # جمع مذكر (دورهم)
        ("هن", "p"),   # جمع مؤنث
        ("كم", "p"),   # جمع مخاطب
        ("كن", "p"),   # جمع مخاطبة
        ("ه", "m"),    # مذكر مفرد (وظيفته، دوره)
    ]
    # استبعاد الكلمات المعروفة
    w = word.strip("؟?.,،!:؛")
    if w in KNOWN_WORDS_END_H:
        return None
    for suffix, gender in suffixes:
        if w.endswith(suffix) and len(w) > len(suffix) + 1:
            base = w[:-len(suffix)]
            # استبعاد كلمات وقف
            if base in ("ما", "هو", "هي", "من", "في", "على", "عن", "إلى"):
                return None
            # إصلاح: إذا كانت الكلمة تنتهي بـ "ت" قبل الضمير،
            # الأرجح أنها "ة" أصلية (وظيفته → وظيفة، فائدته → فائدة)
            if base.endswith("ت") and suffix == "ه":
                base = base[:-1] + "ة"
            return {"base": base, "suffix": suffix, "gender": gender}
    return None


def detect_pronoun_ref(text):
    """يكتشف إذا الجملة فيها ضمير يعود على موضوع سابق."""
    t = normalize_arabic(text).strip()
    words = t.split()
    if not words:
        return None

    # 1) كلمات "أكمل" و "المزيد"
    for w in words:
        if w in ("اكمل", "كمل", "تابع", "زدني", "المزيد", "والمزيد"):
            return {"kind": "continue", "pronoun": w}

    # 2) ضمائر منفصلة (هو، هي، له، فيها، عليه، إلخ)
    for w in words:
        w_clean = w.strip("؟?.,،!")
        if w_clean in PRONOUNS:
            gender = PRONOUNS[w_clean]
            return {"kind": "pronoun", "pronoun": w_clean, "gender": gender}

    # 3) ضمائر متصلة في نهاية الكلمات (وظيفته، فائدتها، دوره)
    for w in words:
        attached = detect_attached_pronoun(w)
        if attached:
            return {"kind": "attached", "word": w,
                    "base": attached["base"],
                    "suffix": attached["suffix"],
                    "gender": attached["gender"]}

    # 4) أسماء إشارة (هذا، ذلك، هذه، تلك)
    for w in words:
        w_clean = w.strip("؟?.,،!")
        if w_clean in ("هذا", "ذلك", "هذه", "تلك", "هذيك"):
            return {"kind": "demonstrative", "pronoun": w_clean,
                    "gender": PRONOUNS.get(w_clean, "m")}

    return None


def detect_question_kind(text):
    """يكتشف نوع السؤال."""
    t = normalize_arabic(text)
    for pattern, kind in QUESTION_PATTERNS:
        if re.search(pattern, t):
            return kind
    return None


def extract_topic_from_question(q):
    """يستخرج الموضوع من سؤال سابق."""
    if not q:
        return None
    t = q.strip().rstrip("؟?.")
    # أزل كلمات السؤال
    prefixes = [
        "ما هو ", "ما هي ", "ما معنى ", "ما وظيفة ", "ما دور ",
        "ما فائدة ", "ما أهمية ", "من هو ", "من هي ",
        "أخبرني عن ", "أعطني معلومات عن ", "حدثني عن ",
        "اشرح ", "وضح ", "عرّف ", "عرف ",
        "متى ", "أين ", "وين ", "كيف ", "لماذا ", "ليش ",
    ]
    for p in prefixes:
        if t.startswith(p):
            return t[len(p):].strip()
    return None


class ContextTracker:
    """يتتبع السياق في المحادثة."""

    def __init__(self, max_history=5):
        self.history = []  # [(user_q, bot_reply, topic, kind)]
        self.max_history = max_history

    def add_turn(self, user_q, bot_reply):
        """يضيف دور جديد."""
        topic = extract_topic_from_question(user_q)
        kind = detect_question_kind(user_q)
        if topic:
            self.history.append({
                "user_q": user_q,
                "bot_reply": bot_reply,
                "topic": topic,
                "kind": kind,
            })
            if len(self.history) > self.max_history:
                self.history = self.history[-self.max_history:]

    def get_last_topic(self):
        """آخر موضوع."""
        if not self.history:
            return None
        return self.history[-1].get("topic")

    def resolve_pronoun(self, text):
        """يحاول حل الضمير → سؤال كامل.

        مثال:
          السابق: "ما هو القلب"
          الجديد: "ما وظيفته؟"
          النتيجة: "ما وظيفة القلب؟"
        """
        # 1) هل الجملة فيها ضمير؟
        ref = detect_pronoun_ref(text)
        kind = detect_question_kind(text)

        # 2) "أكمل" → أرجع إشارة خاصة
        if ref and ref["kind"] == "continue":
            last = self.history[-1] if self.history else None
            if last:
                return {
                    "action": "continue",
                    "topic": last["topic"],
                    "original": text,
                }
            return None

        # 3) ضمير أو إشارة → نحتاج موضوع سابق
        if not ref or not self.history:
            return None

        last = self.history[-1]
        topic = last.get("topic")
        if not topic:
            return None

        # 4) ابنِ السؤال الكامل
        # مثال: "ما وظيفته؟" + topic="القلب" → "ما وظيفة القلب؟"
        resolved = self._rebuild_question(text, topic)
        if resolved and resolved != text:
            return {
                "action": "rewrite",
                "new_question": resolved,
                "topic": topic,
                "original": text,
            }
        # 5) جرّب الصيغة العامة ("ما هو؟" → "ما هي سورة الكوثر؟")
        generic = self._build_generic(text, topic)
        if generic:
            return {
                "action": "rewrite",
                "new_question": generic,
                "topic": topic,
                "original": text,
            }
        return None

    # صيغ تحويل خاصة: بعد التطبيع (ة→ه، آ→ا)
    REWRITE_PATTERNS = [
        # كم آية / كم عدد الآيات (بعد التطبيع: "ايه")
        (r"كم\s+اي", "كم عدد ايات "),
        (r"كم\s+عدد\s+الاي", "كم عدد ايات "),
        (r"كم\s+عدد\s+اي", "كم عدد ايات "),
        # كم سورة
        (r"كم\s+سور", "كم عدد سور "),
        # عدد السكان
        (r"كم\s+سكان", "كم عدد سكان "),
        (r"كم\s+عدد\s+سكان", "كم عدد سكان "),
        # متى ولد / توفي
        (r"متى\s+ولد", "متى ولد "),
        (r"متى\s+توفي", "متى توفي "),
    ]

    def _apply_rewrite_pattern(self, text, topic):
        """يطبّق صيغ التحويل الخاصة."""
        t = normalize_arabic(text).strip(" ؟?.,!")
        for pattern, replacement in self.REWRITE_PATTERNS:
            if re.search(pattern, t):
                # نستبدل الجزء المطابق + نضيف topic
                # "كم آية" → "كم عدد آيات سورة الكوثر"
                return replacement + topic + "؟"
        return None

    def _rebuild_question(self, text, topic):
        """يعيد بناء السؤال بعد استبدال الضمير."""
        t = text.strip()

        # -1) طبّق صيغ التحويل الخاصة أولاً
        special = self._apply_rewrite_pattern(t, topic)
        if special:
            return special

        # 0) إذا السؤال "ما هو؟" / "ما هي؟" → نستخدم الصيغة العامة
        t_check = normalize_arabic(t).strip(" ؟?.,!")
        if t_check in ("ما هو", "ما هي", "شو هو", "شو هي", "وشو", "شو"):
            return self._build_generic(t, topic)

        # 1) هل فيه ضمير متصل؟ (وظيفته → وظيفة القلب)
        words = t.split()
        for i, w in enumerate(words):
            attached = detect_attached_pronoun(w)
            if attached:
                # استبدل الكلمة: "وظيفته" → "وظيفة القلب"
                base = attached["base"]
                # أعد علامة الترقيم
                punct = ""
                for ch in ("؟", "?", ".", "،", "!", "؛"):
                    if w.endswith(ch):
                        punct = ch
                        break
                words[i] = base + " " + topic + punct
                result = " ".join(words)
                result = re.sub(r"\s+", " ", result).strip()
                return result

        # 2) ضمائر منفصلة وأسماء إشارة
        replacements = [
            (r"\bهو\b", topic), (r"\bله\b", "ل" + topic),
            (r"\bعليه\b", "على " + topic), (r"\bمنه\b", "من " + topic),
            (r"\bفيه\b", "في " + topic), (r"\bبه\b", topic),
            (r"\bهي\b", topic), (r"\bلها\b", "ل" + topic),
            (r"\bعليها\b", "على " + topic), (r"\bمنها\b", "من " + topic),
            (r"\bفيها\b", "في " + topic),
            (r"\bهذا\b", topic), (r"\bهذه\b", topic),
            (r"\bذلك\b", topic), (r"\bتلك\b", topic),
        ]
        result = t
        for pattern, replacement in replacements:
            new_result = re.sub(pattern, replacement, result)
            if new_result != result:
                result = new_result
                break

        result = re.sub(r"\s+", " ", result).strip()
        if result != t:
            return result
        return None

    def _build_generic(self, text, topic):
        """يبني سؤال عام من "ما هو؟" + topic."""
        t = normalize_arabic(text).strip(" ؟?.")
        # إذا السؤال قصير جداً وفيه "ما هو" أو "ما هي"
        if t in ("ما هو", "ما هي", "شو هو", "شو هي", "وشو", "شو"):
            # نحدد جنس الـ topic
            feminine = topic.endswith("ة") or topic.endswith("ات") or \
                       topic.startswith("سورة ") or topic.startswith("ال") and \
                       topic.endswith(("ة", "ات", "اء"))
            # جرّب الاستنتاج من كلمات معروفة
            fem_words = ("سورة", "آية", "مدينة", "دولة", "جامعة", "مدرسة",
                         "قلب", "رئة", "كلية", "معدة", "خلية")
            if any(fw in topic for fw in ("سورة", "آية", "مدينة", "دولة")):
                feminine = True
            verb = "ما هي" if feminine else "ما هو"
            return "%s %s؟" % (verb, topic)
        return None


_TRACKER = None

def get_tracker():
    global _TRACKER
    if _TRACKER is None:
        _TRACKER = ContextTracker()
    return _TRACKER


if __name__ == "__main__":
    t = ContextTracker()
    t.add_turn("ما هو القلب", "القلب عضو عضلي...")
    t.add_turn("ما هي سورة الكوثر", "سورة الكوثر سورة مكية...")
    print("الموضوع الأخير:", t.get_last_topic())
    print()
    for q in ["ما وظيفته؟", "كم آية فيها؟", "أكمل", "ما هو؟"]:
        print("%s → %s" % (q, t.resolve_pronoun(q)))
