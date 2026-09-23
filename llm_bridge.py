# -*- coding: utf-8 -*-
"""llm_bridge.py — جسر للتواصل مع llama-server (Qwen3-4B)."""
import json
import urllib.request
import urllib.error

SERVER_URL = "http://127.0.0.1:8080/v1/chat/completions"
DEFAULT_TIMEOUT = 180  # 3 دقائق
DEFAULT_MAX_TOKENS = 300


def is_server_up(timeout=3):
    """يتحقق إن السيرفر شغال."""
    try:
        url = "http://127.0.0.1:8080/health"
        req = urllib.request.Request(url, headers={"User-Agent": "MiniChat/2.3"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status == 200
    except Exception:
        return False


import re as _re

# نمط: نطاقات Unicode غير العربية (السيريلية، الصينية، اليابانية، إلخ)
_FOREIGN_PATTERN = _re.compile(
    r"[\u0400-\u04FF"   # Cyrillic
    r"\u4E00-\u9FFF"    # CJK
    r"\u3040-\u30FF"    # Japanese
    r"\uAC00-\uD7AF"    # Korean
    r"\u0600-\u06FF"    # Arabic (نحتفظ بها)
    r"]+"
)


def clean_arabic(text):
    """يشيل أي حروف أجنبية (سيريلية، صينية، إلخ) من النص."""
    if not text:
        return text
    # احتفظ فقط بالعربي + اللاتيني (للأسماء التقنية) + الأرقام + الترقيم
    # نشيل كل حرف خارج: عربي، لاتيني، أرقام، مسافات، ترقيم
    allowed = _re.compile(
        r"[^\u0600-\u06FF"      # Arabic
        r"\u0750-\u077F"       # Arabic Supplement
        r"\uFB50-\uFDFF"       # Arabic Presentation Forms-A
        r"\uFE70-\uFEFF"       # Arabic Presentation Forms-B
        r"a-zA-Z0-9"
        r"\s"
        r".,،؛;:؟?!\-—–()\[\]{}\"\'«»%$#@&*+=/\\|<>&"
        r"]+"
    )
    cleaned = allowed.sub(" ", text)
    # شيل المسافات الزائدة
    cleaned = _re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _dedup_repetition(text):
    """يشيل حلقات التكرار (على ، و . و ؟)."""
    if not text or len(text) < 60:
        return text
    import re as _re2
    # اقسم على كل علامات الترقيم العربية والإنجليزية
    parts = _re2.split(r'[،.؛!؟]+', text)
    parts = [p.strip() for p in parts if p.strip()]
    if len(parts) < 3:
        return text

    # اكتشف التكرار بعتبة: إذا ظهر نفس المقطع (50 حرف أولى) 2+ مرات، احتفظ بالأول فقط
    seen = {}
    out = []
    for p in parts:
        key = p[:50]
        if key in seen:
            seen[key] += 1
            if seen[key] >= 2:
                continue
        else:
            seen[key] = 1
        out.append(p)

    result = "، ".join(out)
    return result


def _dedup_ngrams(text, min_len=25):
    """يقطع النص عند أول تكرار لنافذة من min_len حرف (خطوة 1)."""
    if not text or len(text) < min_len * 2:
        return text
    n = len(text)
    for i in range(0, n - min_len):
        sub = text[i:i+min_len]
        if not sub.strip():
            continue
        j = text.find(sub, i + min_len)
        if j != -1:
            cut = text[:j].rstrip()
            # حاول تمديد القطع لنهاية آخر فاصل
            for sep in ["،", ".", "؛", "!", "؟", ":", "\n"]:
                p = cut.rfind(sep)
                if p != -1 and len(cut) - p < 100:
                    return cut[:p+1].strip()
            return cut.strip()
    return text


def ask(system, user, max_tokens=DEFAULT_MAX_TOKENS, temperature=0.6, timeout=DEFAULT_TIMEOUT):
    """يرسل سؤال للنموذج ويعيد الجواب النصي."""
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": user})

    payload = {
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        SERVER_URL,
        data=data,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "MiniChat/2.3",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read().decode("utf-8")
        d = json.loads(raw)
        choices = d.get("choices", [])
        if not choices:
            return None
        raw = choices[0].get("message", {}).get("content", "").strip()
        if not raw:
            return None
        raw = clean_arabic(raw)
        raw = _dedup_repetition(raw)
        raw = _dedup_ngrams(raw, min_len=25)
        return raw
    except urllib.error.URLError as e:
        return None
    except Exception as e:
        return None


def stream_ask(system, user, max_tokens=DEFAULT_MAX_TOKENS, temperature=0.6, timeout=DEFAULT_TIMEOUT):
    """يرسل سؤال ويعيد الجواب (بدون stream حالياً — للاستخدام المستقبلي)."""
    return ask(system, user, max_tokens=max_tokens, temperature=temperature, timeout=timeout)


if __name__ == "__main__":
    print("فحص السيرفر...")
    if not is_server_up():
        print("❌ السيرفر مش شغال")
        exit(1)
    print("✅ السيرفر شغال")
    print()
    print("السؤال: ما هو القلب؟")
    print("---")
    reply = ask(
        system="أنت مساعد عربي فصيح. أجب بإيجاز ووضوح.",
        user="ما هو القلب؟",
        max_tokens=100,
    )
    print(reply or "(لا رد)")
