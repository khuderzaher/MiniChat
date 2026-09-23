# -*- coding: utf-8 -*-
"""learning_engine.py — تعلّم ذاتي من الأخطاء"""
import json
import time
import pickle
from pathlib import Path
from collections import Counter, defaultdict


class LearningEngine:
    """يتعلم من الأخطاء والتصحيحات تلقائيًا."""

    def __init__(self, path="minichat_learning.pkl"):
        self.path = Path(path)
        self.data = {
            "version": "1.0",
            "wrong_answers": {},   # سؤال → {جواب_خاطئ: عدد}
            "right_answers": {},   # سؤال → {جواب_صحيح: عدد}
            "intent_stats": {},    # نوع النية → عدد
            "user_corrections": [],  # آخر التصحيحات
            "topic_confidence": {},  # موضوع → ثقة
            "total_turns": 0,
            "success_rate": {},
        }
        self._load()

    def _load(self):
        if self.path.exists():
            try:
                with open(self.path, "rb") as f:
                    loaded = pickle.load(f)
                self.data.update(loaded)
                print("[LEARN] ذاكرة التعلم: %d تصحيح"
                      % len(self.data["user_corrections"]))
            except Exception:
                pass

    def save(self):
        try:
            with open(self.path, "wb") as f:
                pickle.dump(self.data, f)
        except Exception as e:
            print("[LEARN] فشل الحفظ: %s" % e)

    # ═══════════════════════════════════════════════════════════
    # تعلّم من الأخطاء
    # ═══════════════════════════════════════════════════════════
    def record_wrong(self, question, wrong_answer, correct_answer=None):
        """يسجّل جوابًا خاطئًا."""
        q = self._norm(question)
        w = self._norm(wrong_answer)
        if q not in self.data["wrong_answers"]:
            self.data["wrong_answers"][q] = {}
        if w not in self.data["wrong_answers"][q]:
            self.data["wrong_answers"][q][w] = 0
        self.data["wrong_answers"][q][w] += 1

        if correct_answer:
            self.data["user_corrections"].append({
                "q": q,
                "wrong": w,
                "correct": self._norm(correct_answer),
                "ts": time.time(),
            })
            # احتفظ بآخر 200 تصحيح
            if len(self.data["user_corrections"]) > 200:
                self.data["user_corrections"] = \
                    self.data["user_corrections"][-200:]

        self.save()

    def record_right(self, question, answer):
        """يسجّل جوابًا صحيحًا."""
        q = self._norm(question)
        a = self._norm(answer)
        if q not in self.data["right_answers"]:
            self.data["right_answers"][q] = {}
        if a not in self.data["right_answers"][q]:
            self.data["right_answers"][q][a] = 0
        self.data["right_answers"][q][a] += 1
        self.save()

    def record_intent(self, intent_type):
        """يسجّل نوع نية."""
        self.data["intent_stats"][intent_type] = \
            self.data["intent_stats"].get(intent_type, 0) + 1
        self.data["total_turns"] += 1
        self.save()

    # ═══════════════════════════════════════════════════════════
    # تجنب الأخطاء
    # ═══════════════════════════════════════════════════════════
    def is_bad_answer(self, question, answer):
        """هل هذا الجواب كان خاطئًا في السابق؟"""
        q = self._norm(question)
        a = self._norm(answer)
        return a in self.data["wrong_answers"].get(q, {})

    def get_correct_answer(self, question):
        """يعيد الجواب الصحيح إذا كان مسجّلًا."""
        q = self._norm(question)
        # ابحث في التصحيحات
        corrections = [c for c in self.data["user_corrections"]
                       if c["q"] == q]
        if corrections:
            return corrections[-1]["correct"]
        # أو في right_answers (الأكثر تكرارًا)
        ra = self.data["right_answers"].get(q, {})
        if ra:
            return max(ra.items(), key=lambda x: -x[1])[0]
        return None

    def suggest_better(self, question, current_answer):
        """يقترح جوابًا أفضل."""
        correct = self.get_correct_answer(question)
        if correct and correct != self._norm(current_answer):
            return correct
        return None

    # ═══════════════════════════════════════════════════════════
    # ثقة الموضوع
    # ═══════════════════════════════════════════════════════════
    def update_topic_confidence(self, topic, was_correct):
        """يحدّث ثقة الموضوع."""
        if topic not in self.data["topic_confidence"]:
            self.data["topic_confidence"][topic] = {"right": 0, "wrong": 0}
        if was_correct:
            self.data["topic_confidence"][topic]["right"] += 1
        else:
            self.data["topic_confidence"][topic]["wrong"] += 1
        self.save()

    def get_topic_confidence(self, topic):
        """يرجع نسبة الثقة بالموضوع (0-1)."""
        stats = self.data["topic_confidence"].get(topic, {})
        r = stats.get("right", 0)
        w = stats.get("wrong", 0)
        total = r + w
        if total == 0:
            return 0.5  # غير معروف
        return r / total

    # ═══════════════════════════════════════════════════════════
    # إحصاءات
    # ═══════════════════════════════════════════════════════════
    def stats(self):
        """إحصاءات التعلم."""
        return {
            "total_turns": self.data["total_turns"],
            "wrong_qs": len(self.data["wrong_answers"]),
            "right_qs": len(self.data["right_answers"]),
            "corrections": len(self.data["user_corrections"]),
            "top_intents": Counter(self.data["intent_stats"]).most_common(5),
        }

    def _norm(self, text):
        if not text:
            return ""
        return str(text).strip().lower()


_LEARN = None

def get_learning_engine(path="minichat_learning.pkl"):
    global _LEARN
    if _LEARN is None:
        _LEARN = LearningEngine(path)
    return _LEARN


if __name__ == "__main__":
    le = LearningEngine("test_learning.pkl")
    le.record_wrong("ما هي عاصمة فرنسا", "لندن", "باريس")
    print(le.get_correct_answer("ما هي عاصمة فرنسا"))
    print(le.stats())
