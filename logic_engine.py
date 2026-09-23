# -*- coding: utf-8 -*-
import re
from collections import defaultdict
from arabic_utils import normalize_arabic, canonical


class LogicEngine:
    def __init__(self):
        self.rules = []
        self.facts = defaultdict(set)
        self.max_facts = 50000
        self.total = 0

    def learn_from_sentence(self, text):
        if self.total > self.max_facts:
            return
        t = normalize_arabic(text)
        m = re.match(r'كل\s+(.+?)\s+(?:هو|هي)\s+(.+)', t)
        if m:
            g = canonical(m.group(1).strip()); p = canonical(m.group(2).strip())
            if g and p and len(g) < 40:
                self.rules.append((g, p))
                self.total += 1
                return
        m = re.match(r'إذا\s+(.+?)\s+(?:فإن|فـ|اذا)\s+(.+)', t)
        if m:
            c = canonical(m.group(1).strip()); q = canonical(m.group(2).strip())
            if c and q and len(c) < 60:
                self.rules.append((c, q))
                self.total += 1
                return
        m = re.match(r'(.{2,40}?)\s+(?:هو|هي)\s+(.+)', t)
        if m:
            s = canonical(m.group(1).strip()); p = canonical(m.group(2).strip())
            if s and p and len(s) < 30 and len(p) < 200:
                self.facts[s].add(p)
                self.total += 1

    def deduce(self, subject, max_depth=3):
        s = canonical(subject)
        result = set(self.facts.get(s, []))
        for _ in range(max_depth):
            added = False
            for cond, concl in self.rules:
                if cond in result or cond in s:
                    if concl not in result:
                        result.add(concl)
                        added = True
            if not added:
                break
        return result

    def stats(self):
        return {"rules": len(self.rules), "facts": sum(len(v) for v in self.facts.values())}
