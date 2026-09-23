# -*- coding: utf-8 -*-
"""deep_reasoner.py — استدلال متقدم"""
from collections import defaultdict
from arabic_utils import canonical


class DeepReasoner:
    def __init__(self, db, knowledge_index):
        self.db = db
        self.ki = knowledge_index
        self.categories = defaultdict(set)
        self._learn_categories()

    def _learn_categories(self):
        """يستنتج تصنيفات من tags."""
        for item in self.db.faq_entries():
            if not isinstance(item, dict):
                continue
            subj = item.get("q", "")
            for tag in item.get("tags", []):
                if tag and isinstance(tag, str):
                    self.categories[tag].add(subj[:60])

    def classify(self, subject):
        """يصنف كيان (إلى أي فئة ينتمي)."""
        c = canonical(subject)
        tags = []
        for tag, members in self.categories.items():
            if len(members) < 2:
                continue
            for m in members:
                if c in canonical(m):
                    tags.append(tag)
                    break
        return tags[:5]

    def compare(self, a, b):
        """مقارنة منظمة."""
        item_a = self.ki.find(a)
        item_b = self.ki.find(b)
        return {
            "a": {"title": a, "text": item_a["a"][:500] if item_a else None},
            "b": {"title": b, "text": item_b["a"][:500] if item_b else None},
            "same_category": bool(set(self.classify(a)) & set(self.classify(b))),
        }

    def why_chain(self, subject, depth=3):
        """سلسلة 'لماذا'."""
        chain = [subject]
        current = subject
        for _ in range(depth):
            item = self.ki.find(current)
            if not item:
                break
            # استخرج سبب من النص
            txt = item["a"]
            m = None
            import re
            for pat in [r"بسبب\s+([^\.،]+)", r"لأن\s+([^\.،]+)", r"نتيجة\s+([^\.،]+)"]:
                m = re.search(pat, txt)
                if m:
                    break
            if m:
                current = m.group(1).strip()[:50]
                chain.append(current)
            else:
                break
        return chain

    def multi_hop(self, start, target, max_depth=3):
        """بحث متعدد الخطوات بين كيانين."""
        # BFS بسيط عبر التصنيفات المشتركة
        s = canonical(start); t = canonical(target)
        visited = {s}
        queue = [(s, [start])]
        while queue:
            cur, path = queue.pop(0)
            if len(path) > max_depth:
                continue
            item = self.ki.find(cur)
            if not item:
                continue
            for tag in item.get("tags", [])[:3]:
                for member in list(self.categories.get(tag, []))[:20]:
                    mc = canonical(member)
                    if mc in visited:
                        continue
                    visited.add(mc)
                    new_path = path + [member]
                    if t in mc:
                        return new_path
                    queue.append((mc, new_path))
        return None


if __name__ == "__main__":
    print("Deep Reasoner ready")
