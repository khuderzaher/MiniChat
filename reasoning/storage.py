# -*- coding: utf-8 -*-
"""
reasoning/storage.py

مخزن المعرفة والاستدلال لـ MiniChat.

مبدأ التصميم:
- SQLite
- لا بيانات افتراضية
- لا تكرار
- كل نوع معرفة مستقل
- التخزين لا يحتوي على بيانات مشتقة يمكن إعادة توليدها
"""

from __future__ import annotations

import sqlite3
from pathlib import Path


class ReasoningStore:
    """مخزن مضغوط للحقائق والقواعد والعلاقات والقيود."""

    def __init__(self, path: str | Path = "reasoning/reasoning.db"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute("PRAGMA foreign_keys=ON")
        self._create_schema()

    def _create_schema(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS facts (
                id INTEGER PRIMARY KEY,
                subject TEXT NOT NULL,
                predicate TEXT NOT NULL,
                object TEXT NOT NULL,
                source TEXT,
                confidence REAL,
                UNIQUE(subject, predicate, object)
            );

            CREATE TABLE IF NOT EXISTS rules (
                id INTEGER PRIMARY KEY,
                premise TEXT NOT NULL,
                conclusion TEXT NOT NULL,
                source TEXT,
                confidence REAL,
                UNIQUE(premise, conclusion)
            );

            CREATE TABLE IF NOT EXISTS relations (
                id INTEGER PRIMARY KEY,
                subject TEXT NOT NULL,
                relation TEXT NOT NULL,
                object TEXT NOT NULL,
                source TEXT,
                confidence REAL,
                UNIQUE(subject, relation, object)
            );

            CREATE TABLE IF NOT EXISTS constraints (
                id INTEGER PRIMARY KEY,
                kind TEXT NOT NULL,
                left_value TEXT NOT NULL,
                right_value TEXT NOT NULL,
                source TEXT,
                confidence REAL,
                UNIQUE(kind, left_value, right_value)
            );

            CREATE INDEX IF NOT EXISTS idx_facts_subject
                ON facts(subject);

            CREATE INDEX IF NOT EXISTS idx_facts_predicate
                ON facts(predicate);

            CREATE INDEX IF NOT EXISTS idx_relations_subject
                ON relations(subject);

            CREATE INDEX IF NOT EXISTS idx_relations_relation
                ON relations(relation);

            CREATE INDEX IF NOT EXISTS idx_rules_premise
                ON rules(premise);

            CREATE INDEX IF NOT EXISTS idx_constraints_kind
                ON constraints(kind);
            """
        )
        self.connection.commit()

    def add_fact(
        self,
        subject: str,
        predicate: str,
        object_: str,
        source: str | None = None,
        confidence: float | None = None,
    ) -> bool:
        """إضافة حقيقة واحدة. يعيد True إذا أضيفت، وFalse إذا كانت موجودة."""
        if not subject or not predicate or not object_:
            raise ValueError("subject/predicate/object لا يمكن أن تكون فارغة")

        cursor = self.connection.execute(
            """
            INSERT OR IGNORE INTO facts
                (subject, predicate, object, source, confidence)
            VALUES (?, ?, ?, ?, ?)
            """,
            (subject.strip(), predicate.strip(), object_.strip(), source, confidence),
        )

        self.connection.commit()
        return cursor.rowcount == 1

    def add_rule(
        self,
        premise: str,
        conclusion: str,
        source: str | None = None,
        confidence: float | None = None,
    ) -> bool:
        """إضافة قاعدة واحدة. يعيد True إذا أضيفت، وFalse إذا كانت موجودة."""
        if not premise or not conclusion:
            raise ValueError("premise/conclusion لا يمكن أن تكون فارغة")

        cursor = self.connection.execute(
            """
            INSERT OR IGNORE INTO rules
                (premise, conclusion, source, confidence)
            VALUES (?, ?, ?, ?)
            """,
            (premise.strip(), conclusion.strip(), source, confidence),
        )

        self.connection.commit()
        return cursor.rowcount == 1

    def get_facts(self) -> list[str]:
        """قراءة الحقائق المخزنة بصيغة يفهمها محرك المنطق."""
        rows = self.connection.execute(
            """
            SELECT subject, predicate, object
            FROM facts
            ORDER BY id
            """
        ).fetchall()

        return [
            f"{subject} {predicate} {object_}"
            for subject, predicate, object_ in rows
        ]

    def get_rules(self) -> list[dict[str, str | None]]:
        """قراءة القواعد المخزنة."""
        rows = self.connection.execute(
            """
            SELECT premise, conclusion, source
            FROM rules
            ORDER BY id
            """
        ).fetchall()

        return [
            {
                "premise": premise,
                "conclusion": conclusion,
                "source": source,
            }
            for premise, conclusion, source in rows
        ]

    def close(self) -> None:
        self.connection.close()
