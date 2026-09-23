# -*- coding: utf-8 -*-
import re
from arabic_utils import normalize_arabic, canonical, strip_definite


class ArabicLanguageAnalyzer:
    PREPOSITIONS = {'في','من','إلى','على','عن','مع','حتى','بين','حول','ضد','نحو','عند','لدى'}
    VERBS = {'كان','يكون','صار','أصبح','ظل','بات','ليس'}

    @staticmethod
    def detect_kind(word):
        if not word or len(word) < 2:
            return "unknown"
        w = strip_definite(canonical(word))
        if w in ArabicLanguageAnalyzer.PREPOSITIONS:
            return "preposition"
        if w in ArabicLanguageAnalyzer.VERBS:
            return "verb"
        for p in ['ي', 'ت', 'أ', 'ن']:
            if w.startswith(p) and len(w) > 3:
                return "verb"
        if w.endswith('ي') and len(w) > 3:
            return "adjective"
        if w.endswith('ة') and len(w) > 3:
            return "adjective_or_noun"
        return "noun"

    @staticmethod
    def extract_root(word):
        w = strip_definite(canonical(word))
        for p in ['است', 'مست', 'ان', 'مت']:
            if w.startswith(p) and len(w) > len(p) + 2:
                w = w[len(p):]
                break
        for p in ['ي', 'ت', 'ن', 'أ', 'م']:
            if w.startswith(p) and len(w) > 4:
                w = w[1:]
                break
        for s in ['ات', 'ون', 'ين', 'ان', 'ها', 'هم', 'كم', 'نا']:
            if w.endswith(s) and len(w) > len(s) + 2:
                w = w[:-len(s)]
                break
        cons = [c for c in w if c not in 'اوياء']
        if len(cons) >= 3:
            return ''.join(cons[:3])
        return w

    @staticmethod
    def analyze(text):
        tokens = re.findall(r'[\u0600-\u06FF]+', normalize_arabic(text))
        kinds = [ArabicLanguageAnalyzer.detect_kind(t) for t in tokens]
        roots = [ArabicLanguageAnalyzer.extract_root(t) for t in tokens]
        return {
            'tokens': tokens,
            'kinds': kinds,
            'roots': roots,
            'nouns': [t for t, k in zip(tokens, kinds) if k in ('noun', 'adjective', 'adjective_or_noun')],
            'verbs': [t for t, k in zip(tokens, kinds) if k == 'verb'],
        }
