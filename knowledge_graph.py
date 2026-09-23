# -*- coding: utf-8 -*-
"""knowledge_graph.py — شبكة معرفية للاستدلال العميق"""
from collections import defaultdict, deque
from arabic_utils import normalize_arabic

try:
    from reasoning_chain import CAUSAL_RULES, SEQUENCE_RULES
except Exception:
    CAUSAL_RULES = []
    SEQUENCE_RULES = []


class KnowledgeGraph:
    """شبكة موجهة من المفاهيم والعلاقات السببية."""

    def __init__(self, causal_rules=None, sequences=None):
        self.edges = defaultdict(dict)
        self.reverse = defaultdict(dict)
        self.nodes = set()
        causal = causal_rules if causal_rules is not None else CAUSAL_RULES
        seqs = sequences if sequences is not None else SEQUENCE_RULES
        for rule in causal:
            if len(rule) >= 3:
                self.add_edge(rule[0], rule[1], rule[2])
        for seq in seqs:
            for i in range(len(seq) - 1):
                self.add_edge(seq[i], seq[i + 1], 0.85)

    def add_edge(self, src, dst, conf=1.0):
        s = normalize_arabic(src)
        d = normalize_arabic(dst)
        if not s or not d:
            return
        prev = self.edges[s].get(d, 0)
        if conf > prev:
            self.edges[s][d] = conf
        prev_r = self.reverse[d].get(s, 0)
        if conf > prev_r:
            self.reverse[d][s] = conf
        self.nodes.add(s)
        self.nodes.add(d)

    def neighbors(self, node):
        n = normalize_arabic(node)
        return dict(self.edges.get(n, {}))

    def parents(self, node):
        n = normalize_arabic(node)
        return dict(self.reverse.get(n, {}))

    def find_node(self, word):
        """يبحث عن أقرب عقدة مطابقة."""
        w = normalize_arabic(word)
        if not w:
            return None
        if w in self.nodes:
            return w
        for n in self.nodes:
            if w in n or n in w:
                return n
        return None

    def path(self, start, target, max_depth=6):
        """BFS: أقصر مسار موجه بين مفهومين."""
        s = self.find_node(start)
        t = self.find_node(target)
        if not s or not t:
            return None
        if s == t:
            return [(s, 1.0)]
        queue = deque([(s, [(s, 1.0)])])
        visited = {s}
        while queue:
            node, path_so_far = queue.popleft()
            if len(path_so_far) > max_depth:
                continue
            for nxt, conf in self.edges.get(node, {}).items():
                if nxt == t:
                    return path_so_far + [(nxt, conf)]
                if nxt not in visited:
                    visited.add(nxt)
                    queue.append((nxt, path_so_far + [(nxt, conf)]))
        return None

    def infer(self, start, max_depth=4, min_conf=0.5):
        """يستنتج سلاسل من نقطة بداية."""
        s = self.find_node(start)
        if not s:
            return []
        results = []
        visited = {s}

        def dfs(node, chain, depth):
            if depth >= max_depth:
                return
            for nxt, conf in self.edges.get(node, {}).items():
                if nxt in visited or conf < min_conf:
                    continue
                visited.add(nxt)
                chain.append((nxt, conf))
                results.append(list(chain))
                dfs(nxt, chain, depth + 1)
                chain.pop()
        dfs(s, [], 0)
        return results

    def stats(self):
        return {
            "nodes": len(self.nodes),
            "edges": sum(len(v) for v in self.edges.values()),
        }


_GRAPH = None

def get_knowledge_graph():
    global _GRAPH
    if _GRAPH is None:
        _GRAPH = KnowledgeGraph()
    return _GRAPH


if __name__ == "__main__":
    g = KnowledgeGraph()
    print("stats:", g.stats())
    p = g.path("مطر", "حياة")
    print("مسار مطر → حياة:", p)
    print("ما يؤدي من شمس:", g.infer("شمس")[:5])
