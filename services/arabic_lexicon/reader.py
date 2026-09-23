# -*- coding: utf-8 -*-
"""
services/arabic_lexicon/reader.py — قارئ خالص لقاموس arramooz.

لا يحكم. لا يرجّح. لا يخمّن.
يعيد ما في القاعدة كما هو، والطبقة الأعلى تقرر.

التطبيع يستخدم نفس ما يستخدمه arramooz: pyarabic.araby.normalize_hamza
"""
import os
import sqlite3
from typing import Any, Dict, List, Optional

import arramooz
import pyarabic.araby as araby

DEFAULT_DB = os.path.join(
    os.path.dirname(arramooz.__file__),
    "data", "arabicdictionary.sqlite",
)


class Reader:
    def __init__(self, db_path: str = DEFAULT_DB):
        self.db_path = db_path
        self._con: Optional[sqlite3.Connection] = None

    def _connect(self) -> sqlite3.Connection:
        if self._con is None:
            self._con = sqlite3.connect(self.db_path)
            self._con.row_factory = sqlite3.Row
        return self._con

    @staticmethod
    def normalize(word: str) -> str:
        w = (word or "").strip()
        w = araby.strip_tashkeel(w)
        w = araby.normalize_hamza(w)
        return w

    # ---------- استعلامات أساسية ----------

    def entries(self, word: str) -> Dict[str, List[Dict[str, Any]]]:
        """كل صفوف الكلمة في verbs و nouns، بلا فلترة."""
        n = self.normalize(word)
        return {
            "verbs": [dict(r) for r in self._connect().execute(
                "SELECT * FROM verbs WHERE normalized = ?", (n,))],
            "nouns": [dict(r) for r in self._connect().execute(
                "SELECT * FROM nouns WHERE normalized = ?", (n,))],
        }

    def family(self, root: str) -> Dict[str, List[Dict[str, Any]]]:
        """كل الأفعال والأسماء بجذر معين."""
        r = self.normalize(root)
        return {
            "verbs": [dict(x) for x in self._connect().execute(
                "SELECT * FROM verbs WHERE root = ?", (r,))],
            "nouns": [dict(x) for x in self._connect().execute(
                "SELECT * FROM nouns WHERE root = ?", (r,))],
        }

    def by_category(self, root: str, category: str) -> List[Dict[str, Any]]:
        """أسماء الجذر في فئة معينة. قد تكون متعددة."""
        r = self.normalize(root)
        return [dict(x) for x in self._connect().execute(
            "SELECT * FROM nouns WHERE root = ? AND category = ?",
            (r, category))]

    def categories(self) -> List[str]:
        """كل الفئات المتوفرة في nouns."""
        return [row[0] for row in self._connect().execute(
            "SELECT DISTINCT category FROM nouns "
            "WHERE category <> '' ORDER BY category")]

    def root_of(self, word: str) -> List[str]:
        """كل الجذور المرتبطة بالكلمة (قد تكون أكثر من واحد)."""
        e = self.entries(word)
        roots = set()
        for row in e["verbs"]:
            if row.get("root"):
                roots.add(row["root"])
        for row in e["nouns"]:
            if row.get("root"):
                roots.add(row["root"])
        return sorted(roots)


if __name__ == "__main__":
    rd = Reader()
    print("=== entries: كتب ===")
    e = rd.entries("كتب")
    print("  verbs:", len(e["verbs"]), "| nouns:", len(e["nouns"]))
    for v in e["verbs"]:
        print("    V:", v["vocalized"], "root=", v["root"])
    print()
    print("=== family: شرب (أول 6 أسماء) ===")
    f = rd.family("شرب")
    print("  verbs:", len(f["verbs"]), "| nouns:", len(f["nouns"]))
    for n in f["nouns"][:6]:
        print("    N:", n["vocalized"], "| cat=", n["category"], "| orig=", n["original"])
    print()
    print("=== by_category(كتب, فاعل) ===")
    for r in rd.by_category("كتب", "فاعل"):
        print("  ", r["vocalized"], "| orig=", r["original"], "| number=", r["number"])
    print()
    print("=== root_of: قرأ ===")
    print("  ", rd.root_of("قرأ"))
    print("=== root_of: قرا ===")
    print("  ", rd.root_of("قرا"))
    print()
    print("=== categories (first 10) ===")
    for c in rd.categories()[:10]:
        print("  ", c)
