# -*- coding: utf-8 -*-
try:
    from semantic_engine import SemanticEngine
except Exception:
    SemanticEngine = None
from language_analyzer import ArabicLanguageAnalyzer
from logic_engine import LogicEngine
from scripts.data_analyzer import DataAnalyzer


class Cognition:
    def __init__(self, db):
        print("[COG] تهيئة محرك الإدراك...")
        self.db = db
        self.semantic = None
        # SemanticEngine معطّل: كان يستهلك 28 MB RAM بلا مستخدم بعد إزالة 6.b
        # (يُعاد تفعيله عند الحاجة)
        self.language = ArabicLanguageAnalyzer()
        self.logic = LogicEngine()
        self.data = DataAnalyzer()
        self._learn_from_db()
        print("[COG] القواعد: %s" % self.logic.stats())

    def _learn_from_db(self):
        faqs = self.db.faq_entries()
        for item in faqs[:3000]:
            if isinstance(item, dict):
                a = item.get('a', '')
                if a:
                    self.logic.learn_from_sentence(a[:300])

    def understand(self, query):
        return {
            'original': query,
            'lang': self.language.analyze(query),
            'data': self.data.extract(query),
            'compare': self.data.compare(query),
            'expanded': (self.semantic.expand_query(query) if self.semantic else []),
        }

    def related(self, word, top=5):
        if self.semantic is None:
            return []
        return self.semantic.related_words(word, top)

    def deduce(self, subject):
        return self.logic.deduce(subject)


_COG = None

def get_cognition(db):
    global _COG
    if _COG is None:
        _COG = Cognition(db)
    return _COG
