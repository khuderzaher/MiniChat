# -*- coding: utf-8 -*-
import pickle, math
from collections import defaultdict, Counter
from pathlib import Path
from arabic_utils import normalize_arabic, canonical, extract_core_tokens


class SemanticEngine:
    def __init__(self, db, cache_path="semantic_cache.pkl"):
        self.db = db
        self.cache_path = Path(cache_path)
        self.word_docs = {}
        self.word_freq = Counter()
        self.doc_count = 0
        self.idf = {}
        self.cooccur = defaultdict(Counter)
        self._load_or_build()

    def _load_or_build(self):
        if self.cache_path.exists():
            try:
                with open(self.cache_path, 'rb') as f:
                    d = pickle.load(f)
                self.word_docs = d['word_docs']
                self.word_freq = d['word_freq']
                self.doc_count = d['doc_count']
                self.idf = d['idf']
                self.cooccur = defaultdict(Counter, d['cooccur'])
                print("[SEM] تم تحميل الشبكة (%d كلمة)" % len(self.word_freq))
                return
            except Exception:
                pass
        self._build()
        self._save()

    def _build(self):
        print("[SEM] جاري البناء...")
        faqs = self.db.faq_entries()
        self.doc_count = len(faqs)
        for doc_id, item in enumerate(faqs):
            if not isinstance(item, dict):
                continue
            text = (item.get('q','') + ' ' + item.get('a','')).lower()
            tokens = extract_core_tokens(text, remove_stopwords=True)
            if len(tokens) < 2:
                continue
            unique = list(set(tokens))
            for w in tokens:
                if w not in self.word_docs:
                    self.word_docs[w] = Counter()
                self.word_docs[w][doc_id] += 1
                self.word_freq[w] += 1
            for i, w1 in enumerate(unique):
                for w2 in unique[i+1:]:
                    self.cooccur[w1][w2] += 1
                    self.cooccur[w2][w1] += 1
        for w, docs in self.word_docs.items():
            self.idf[w] = math.log(self.doc_count / max(len(docs), 1))
        print("[SEM] %d كلمة، %d علاقة" % (len(self.word_freq), sum(len(v) for v in self.cooccur.values())))

    def _save(self):
        # شذّب العلاقات: احتفظ بأهم 30 لكل كلمة، وتجاهل اللي تكرر مرة بس
        pruned = {}
        for w, counter in self.cooccur.items():
            items = [(k, v) for k, v in counter.items() if v >= 2]
            items.sort(key=lambda x: -x[1])
            if items:
                pruned[w] = dict(items[:30])
        try:
            with open(self.cache_path, 'wb') as f:
                pickle.dump({
                    'word_docs': dict(self.word_docs),
                    'word_freq': self.word_freq,
                    'doc_count': self.doc_count,
                    'idf': self.idf,
                    'cooccur': pruned,
                }, f)
            print("[SEM] تم الحفظ (cooccur: %d كلمة)" % len(pruned))
        except Exception:
            pass

    def related_words(self, word, top=10):
        w = canonical(word)
        if w in self.cooccur:
            return self.cooccur[w].most_common(top)
        return []

    def expand_query(self, query, top=3):
        tokens = extract_core_tokens(query, remove_stopwords=True)
        expanded = list(tokens)
        for t in tokens:
            for w, _ in self.related_words(t, top=2):
                if w not in expanded:
                    expanded.append(w)
        return expanded

    def similarity(self, w1, w2):
        a = canonical(w1); b = canonical(w2)
        if a == b:
            return 1.0
        c1 = self.cooccur.get(a, Counter())
        c2 = self.cooccur.get(b, Counter())
        if not c1 or not c2:
            return 0.0
        common = set(c1) & set(c2)
        if not common:
            return 0.0
        num = sum(c1[k] * c2[k] for k in common)
        d1 = math.sqrt(sum(v*v for v in c1.values()))
        d2 = math.sqrt(sum(v*v for v in c2.values()))
        return num / (d1 * d2 + 1e-9)
