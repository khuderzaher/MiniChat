# -*- coding: utf-8 -*-
"""
arabic_utils.py — أدوات معالجة اللغة العربية
"""
import re
import unicodedata


# ═══════════════════════════════════════════════════════════════
# 1) التطبيع العربي الشامل
# ═══════════════════════════════════════════════════════════════
_TASHKEEL = re.compile(r"[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED]")

def normalize_arabic(text):
    """تطبيع عربي كامل."""
    if not text:
        return ""
    t = str(text)
    
    # إزالة التشكيل
    t = _TASHKEEL.sub("", t)
    
    # إزالة الرموز المخفية
    t = t.replace("\u200b", "").replace("\u200c", "").replace("\u200d", "")
    t = t.replace("\ufeff", "").replace("\u00a0", " ")
    
    # توحيد الألف بكل أنواعها
    t = t.replace("\u0671", "\u0627")  # ٱ
    t = t.replace("\u0672", "\u0627")  # ٲ
    t = t.replace("\u0673", "\u0627")  # ٳ
    t = t.replace("\u0675", "\u0627")  # ٵ
    t = re.sub(r"[إأآا]", "ا", t)
    
    # توحيد الياء
    t = t.replace("\u0649", "\u064a")  # ى → ي
    t = t.replace("\u0626", "\u064a")  # ئ → ي
    t = t.replace("\u06cc", "\u064a")  # ی
    
    # توحيد الواو
    t = t.replace("\u0624", "\u0648")  # ؤ → و
    
    # توحيد التاء المربوطة
    t = t.replace("\u0629", "\u0647")  # ة → ه
    
    # توحيد الكاف الفارسية
    t = t.replace("\u06a9", "\u0643")
    
    # توحيد علامات الترقيم
    t = t.replace("\u060c", ",")   # ،
    t = t.replace("\u061b", ";")
    t = t.replace("\u061f", "?")   # ؟
    
    # تنظيف المسافات
    t = re.sub(r"\s+", " ", t).strip()
    
    return t


def strip_definite(word):
    """يزيل 'ال' التعريف من بداية الكلمة."""
    if len(word) > 3 and word.startswith("ال"):
        return word[2:]
    return word


def strip_attached_pronouns(word):
    """يزيل ضمائر ملتصقة شائعة."""
    if len(word) < 4:
        return word
    # ضمائر النهاية
    for suf in ("ها", "هم", "هن", "كم", "كن", "نا", "ني", "ه", "ي", "ك"):
        if word.endswith(suf) and len(word) - len(suf) >= 3:
            return word[:-len(suf)]
    return word


def extract_core_tokens(text, remove_stopwords=True):
    """يستخرج الكلمات الجوهرية من نص."""
    if not text:
        return []
    t = normalize_arabic(text)
    # إزالة علامات الترقيم
    t = re.sub(r"[^\u0600-\u06FFa-zA-Z0-9\s]", " ", t)
    words = [w.strip() for w in t.split() if len(w.strip()) >= 2]
    
    if remove_stopwords:
        words = [w for w in words if w not in ARABIC_STOPWORDS]
    
    out = []
    for w in words:
        core = strip_definite(w)
        if core and core not in out:
            out.append(core)
        if w != core and w not in out:
            out.append(w)
    return out


# ═══════════════════════════════════════════════════════════════
# 2) كلمات الوقف العربية
# ═══════════════════════════════════════════════════════════════
ARABIC_STOPWORDS = {
    "ما", "هو", "هي", "من", "في", "على", "عن", "إلى", "الى",
    "و", "أو", "او", "ثم", "لكن", "بل", "لا", "لم", "لن",
    "هذا", "هذه", "ذلك", "تلك", "التي", "الذي", "الذين",
    "كان", "كانت", "يكون", "تكون", "هل", "قد", "كل", "بعض",
    "أي", "اي", "كيف", "متى", "أين", "اين", "لماذا", "ليش",
    "أخبرني", "اخبرني", "أعطني", "اعطني", "قل", "لي",
    "عرفني", "علمني", "اشرح", "وضح", "وضّح",
    "شيء", "شي", "بس", "قط", "حتى", "حتي", "أيضا", "أيضًا",
    "فقط", "جدا", "جدًا", "كثيرا", "كثيرًا",
}


# ═══════════════════════════════════════════════════════════════
# 3) قياس التشابه الذكي
# ═══════════════════════════════════════════════════════════════
def stem_plural(word):
    """يزيل علامات الجمع والتأنيث."""
    if not word or len(word) < 4:
        return word
    # جمع مؤنث سالم
    if word.endswith("ات") and len(word) > 4:
        return word[:-2]
    # جمع مؤنث بألف
    if word.endswith("ين") and len(word) > 4:
        return word[:-2]
    # جمع مذكر سالم
    if word.endswith("ون") and len(word) > 4:
        return word[:-2]
    # تاء مربوطة
    if word.endswith("ه") and len(word) > 3:
        return word[:-1]
    return word


def canonical(word):
    """التطبيع — بدون إزالة الجمع (للحفاظ على التطابق)."""
    w = normalize_arabic(word).lower()
    w = strip_definite(w)
    return w


def canonical_stem(word):
    """التطبيع + إزالة الجمع (للمرونة)."""
    w = canonical(word)
    return stem_plural(w)


def similarity_score(a, b):
    """
    يحسب تشابه بين سلسلتين — بين 0 و 1.
    أفضل من jaccard لأنه:
    - يعطي وزناً أكبر للكلمات الطويلة
    - يفضّل التطابق الكامل
    """
    if not a or not b:
        return 0.0
    
    na = canonical(a)
    nb = canonical(b)
    ca = canonical(a)
    cb = canonical(b)
    
    # تطابق تام = 1.0
    if na == nb:
        return 1.0
    
    # تطابق بعد إزالة "ال" = 0.95
    if strip_definite(na) == strip_definite(nb):
        return 0.95
    
    # تطابق جزئي (واحد يحتوي الآخر) = 0.85
    if na.startswith(nb + " ") or na.endswith(" " + nb):
        return 0.85
    if nb.startswith(na + " ") or nb.endswith(" " + na):
        return 0.85
    
    # تشابه Jaccard
    ta = set(extract_core_tokens(a, remove_stopwords=True))
    tb = set(extract_core_tokens(b, remove_stopwords=True))
    
    if not ta or not tb:
        return 0.0
    
    inter = ta & tb
    union = ta | tb
    
    # وزن حسب طول الكلمات المتقاطعة
    score = 0.0
    for w in inter:
        score += min(len(w), 8) / 8.0
    
    base = len(inter) / float(len(union))
    weighted = score / float(len(ta) + len(tb))
    
    return 0.6 * base + 0.4 * weighted


# ═══════════════════════════════════════════════════════════════
# 4) مرادفات عربية شائعة
# ═══════════════════════════════════════════════════════════════
SYNONYMS_AR = {
    "دكتور":  ["طبيب", "حكيم"],
    "طبيب":   ["دكتور"],
    "سيارة":  ["عربة", "مركبة"],
    "بيت":    ["منزل", "دار"],
    "منزل":   ["بيت", "دار"],
    "جميل":   ["حسن", "بديع", "رائع"],
    "كبير":   ["ضخم", "عظيم", "جسيم"],
    "صغير":   ["ضئيل", "ضغير"],
    "سريع":   ["عاجل", "مسرع"],
    "قلب":    ["فؤاد", "قلوب"],
    "دماغ":   ["مخ", "عقل"],
    "عقل":    ["دماغ", "فكر"],
    "طفل":    ["ولد", "صبي", "غلام"],
    "ولد":    ["طفل", "صبي"],
    "بنت":    ["فتاة", "صبية"],
    "فتاة":   ["بنت", "صبية"],
    "حاسوب":  ["كمبيوتر", "حاسب"],
    "كمبيوتر": ["حاسوب", "حاسب"],
    "هاتف":   ["جوال", "موبايل", "تلفون"],
    "جوال":   ["هاتف", "موبايل"],
    "موبايل": ["هاتف", "جوال"],
    "انترنت": ["إنترنت", "شبكة"],
    "نت":     ["إنترنت", "انترنت"],
    "برمجة":  ["تكويد", "برمجيات"],
    "برنامج": ["تطبيق", "ابليكيشن"],
    "تطبيق":  ["برنامج", "ابليكيشن"],
    "لعبة":   ["لعب", "العاب"],
    "كتاب":   ["مؤلف", "مصنف"],
    "مدرسة":  ["ثانوية", "معهد"],
    "جامعة":  ["كلية", "معهد"],
    "طالب":   ["تلميذ", "دارس"],
    "استاذ":  ["مدرس", "معلم"],
    "معلم":   ["استاذ", "مدرس"],
    "مدرس":   ["است??ذ", "معلم"],
    "مريض":   ["عليل", "سقيم"],
    "دواء":   ["علاج", "عقار"],
    "مرض":    ["سقم", "داء", "علة"],
    "الم":    ["وجع", "ألم"],
    "الم":    ["وجع", "ألم"],
}


def expand_with_synonyms(word):
    """يوسّع كلمة بمرادفاتها."""
    if not word:
        return []
    w = normalize_arabic(word).lower()
    out = [w]
    
    # مباشر
    if w in SYNONYMS_AR:
        out.extend(SYNONYMS_AR[w])
    
    # بعد إزالة "ال"
    core = strip_definite(w)
    if core in SYNONYMS_AR:
        out.extend(SYNONYMS_AR[core])
    
    # إزالة التكرار
    return list(set(out))


# ═══════════════════════════════════════════════════════════════
# 5) اختبار سريع
# ═══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    tests = [
        ("أندرويد", "أندرويد (نظام تشغيل)"),
        ("بايثون", "بايثون (لغة برمجة)"),
        ("القلب", "قلب"),
        ("فيتامين", "فيتامينات"),
    ]
    for a, b in tests:
        s = similarity_score(a, b)
        print("%s vs %s = %.2f" % (a, b, s))
