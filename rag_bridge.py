# -*- coding: utf-8 -*-
"""rag_bridge.py — RAG: يسترجع من قاعدة البيانات + يصيغ عبر Qwen."""
from llm_bridge import ask, is_server_up


SYSTEM_PROMPT = """أنت مساعد عربي ذكي وفصيح.
مهمتك: صياغة إجابة عربية راقية من المعلومات المعطاة.

قواعد صارمة:
1. استخدم فقط المعلومات المعطاة — لا تضف من معرفتك.
2. لا تغيّر الحقائق أو الأرقام أو الأسماء.
3. اكتب بأسلوب عربي فصيح وواضح.
4. اجعل الرد موجزاً (2-5 أسطر عادة).
5. بدون إيموجيات.
6. إذا كانت المعلومات المعطاة لا تجيب على السؤال، قل فقط: "لا تتوفر لدي معلومات كافية عن هذا الموضوع."
"""


def format_context(items):
    """يحوّل قائمة معلومات إلى نص مرتّب."""
    if not items:
        return ""
    lines = []
    for i, item in enumerate(items, 1):
        q = item.get("q", "").strip()
        a = item.get("a", "").strip()
        if a:
            lines.append("[%d] %s" % (i, a))
    return "\n\n".join(lines)


def rag_answer(question, context_items, max_tokens=250, temperature=0.4):
    """يصيغ جواباً بالاعتماد على المعلومات المسترجعة."""
    if not is_server_up():
        return None
    context = format_context(context_items)
    if not context:
        return None
    user_prompt = """المعلومات المتوفرة:
%s

السؤال: %s

اكتب إجابة عربية فصيحة وموجزة بالاعتماد على المعلومات أعلاه فقط.""" % (context, question)
    return ask(SYSTEM_PROMPT, user_prompt, max_tokens=max_tokens, temperature=temperature)


def polish_answer(question, raw_answer, max_tokens=200, temperature=0.5):
    """يصيغ إجابة موجودة (من DB) بأسلوب أجمل."""
    if not is_server_up():
        return None
    user_prompt = """السؤال: %s

المعلومة الخام:
%s

أعد صياغة هذه المعلومة بالعربية الفصحى بأسلوب واضح وموجز. لا تضف معلومات جديدة.""" % (question, raw_answer)
    return ask(SYSTEM_PROMPT, user_prompt, max_tokens=max_tokens, temperature=temperature)


if __name__ == "__main__":
    print("اختبار RAG")
    print("---")
    items = [
        {"q": "ما هو القلب", "a": "القلب عضو عضلي عند البشر والحيوانات الأخرى، يضخّ الدم عبر الأوعية الدموية في الدورة الدموية. يزود الدم الجسم بالأكسجين والمغذيات، كما يساعد في إزالة مخلفات عمليات الاستقلاب. يقع القلب عند البشر بين الرئتين، في الحجرة الوسطى للصدر، خلف القفص الصدري."},
    ]
    print("السؤال: ما هو القلب؟")
    print("---")
    reply = rag_answer("ما هو القلب؟", items)
    print(reply or "(لا رد)")
