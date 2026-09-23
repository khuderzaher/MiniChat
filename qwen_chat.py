import json
import urllib.request

URL = "http://127.0.0.1:8080/v1/chat/completions"

messages = [
    {
        "role": "system",
        "content": "أنت مساعد عربي ذكي. أجب بدقة ووضوح."
    }
]

print("🧠 QWEN DIRECT CHAT")
print("اكتب خروج لإنهاء المحادثة.\n")

while True:
    try:
        user = input("أنت: ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\nانتهت الجلسة.")
        break

    if user in ("خروج", "exit", "quit"):
        print("انتهت الجلسة.")
        break

    if not user:
        continue

    messages.append({"role": "user", "content": user})

    payload = json.dumps({
        "messages": messages,
        "temperature": 0.6,
        "max_tokens": 500,
        "stream": False
    }).encode("utf-8")

    request = urllib.request.Request(
        URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            data = json.loads(response.read().decode("utf-8"))

        answer = data["choices"][0]["message"]["content"]

        print("\nQwen:", answer, "\n")

        messages.append({
            "role": "assistant",
            "content": answer
        })

    except Exception as e:
        print("\n[ERROR]", e, "\n")
