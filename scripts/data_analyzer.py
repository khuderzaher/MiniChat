# -*- coding: utf-8 -*-
import re


class DataAnalyzer:
    NUMBER_RE = re.compile(r'\d+(?:[.,]\d+)?')
    PERCENT_RE = re.compile(r'(\d+(?:[.,]\d+)?)\s*%')
    YEAR_RE = re.compile(r'\b(1[0-9]{3}|20[0-9]{2})\b')
    MONEY_RE = re.compile(r'(\d+(?:[.,]\d+)?)\s*(دولار|يورو|ريال|ليرة|جنيه|درهم|دينار)')

    @staticmethod
    def extract(text):
        nums = []
        for x in DataAnalyzer.NUMBER_RE.findall(text):
            try:
                nums.append(float(x.replace(',', '.')))
            except ValueError:
                pass
        return {
            'numbers': nums,
            'percentages': [float(x.replace(',', '.')) for x in DataAnalyzer.PERCENT_RE.findall(text)],
            'years': [int(y) for y in DataAnalyzer.YEAR_RE.findall(text)],
            'money': DataAnalyzer.MONEY_RE.findall(text),
        }

    @staticmethod
    def compare(text):
        ops = []
        for pat, op in [('أكثر من','>'),('أكبر من','>'),('أقل من','<'),('أصغر من','<'),
                        ('يساوي','='),('ضعف','x2'),('نصف','/2')]:
            if pat in text:
                ops.append(op)
        return ops

    @staticmethod
    def stats(items):
        if not items:
            return {}
        s = sorted(items); n = len(s)
        return {
            'count': n, 'min': s[0], 'max': s[-1],
            'mean': sum(s) / n,
            'median': s[n//2] if n % 2 else (s[n//2-1] + s[n//2]) / 2,
        }
