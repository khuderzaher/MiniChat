# -*- coding: utf-8 -*-
"""data/syria/db_init.py — يهيئ syria.db بـ schema موحد + FTS5."""
import sqlite3, os, sys

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "db", "syria.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS facts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fact TEXT NOT NULL,
    source TEXT NOT NULL,
    date TEXT,
    confidence REAL DEFAULT 0.9,
    tags TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_facts_date ON facts(date);
CREATE INDEX IF NOT EXISTS idx_facts_conf ON facts(confidence);

CREATE VIRTUAL TABLE IF NOT EXISTS facts_fts USING fts5(
    fact,
    tags,
    content='facts',
    content_rowid='id',
    tokenize='unicode61 remove_diacritics 2'
);

CREATE TRIGGER IF NOT EXISTS facts_ai AFTER INSERT ON facts BEGIN
    INSERT INTO facts_fts(rowid, fact, tags) VALUES (new.id, new.fact, new.tags);
END;
CREATE TRIGGER IF NOT EXISTS facts_ad AFTER DELETE ON facts BEGIN
    INSERT INTO facts_fts(facts_fts, rowid, fact, tags) VALUES('delete', old.id, old.fact, old.tags);
END;
CREATE TRIGGER IF NOT EXISTS facts_au AFTER UPDATE ON facts BEGIN
    INSERT INTO facts_fts(facts_fts, rowid, fact, tags) VALUES('delete', old.id, old.fact, old.tags);
    INSERT INTO facts_fts(rowid, fact, tags) VALUES (new.id, new.fact, new.tags);
END;
"""

SAMPLE = [
    ("دمشق هي عاصمة سوريا وأقدم مدينة مأهولة في العالم.", "كتاب الجغرافيا السورية", "2024-01-01", 0.95, "geography,capital"),
    ("حلب أكبر مدينة سورية من حيث عدد السكان وأشهر مدنها الصناعية.", "الموسوعة العربية", "2024-01-01", 0.92, "geography,cities"),
    ("نهر بردى يمر بمدينة دمشق ويروي غوطتها الشرقية والغربية.", "مصادر وزارة الموارد المائية", "2023-06-01", 0.90, "geography,rivers"),
]


def main():
    print("[SYRIA] DB path:", DB)
    con = sqlite3.connect(DB)
    con.executescript(SCHEMA)
    con.commit()

    # فحص FTS5
    try:
        con.execute("SELECT * FROM facts_fts LIMIT 0").fetchall()
        print("[SYRIA] FTS5: متاح ✓")
    except Exception as e:
        print("[SYRIA] FTS5 فشل:", repr(e))
        sys.exit(1)

    # أدخل عيّنات (تجنب التكرار)
    for f in SAMPLE:
        cur = con.execute("SELECT COUNT(*) FROM facts WHERE fact = ?", (f[0],))
        if cur.fetchone()[0] == 0:
            con.execute(
                "INSERT INTO facts (fact, source, date, confidence, tags) VALUES (?, ?, ?, ?, ?)",
                f)
    con.commit()

    # اقرأ
    rows = con.execute("SELECT id, fact, source, confidence, tags FROM facts").fetchall()
    print("[SYRIA] عدد الحقائق:", len(rows))
    for r in rows:
        print("  #%d [%s] %s" % (r[0], r[4], r[1][:50]))

    # اختبار بحث
    print()
    print("[SYRIA] اختبار بحث FTS5 عن 'دمشق':")
    for r in con.execute(
            "SELECT f.id, f.fact FROM facts_fts JOIN facts f ON f.id = facts_fts.rowid "
            "WHERE facts_fts MATCH ? ORDER BY f.confidence DESC LIMIT 3",
            ('دمشق',)):
        print("  →", r[1][:60])

    con.close()
    print("[SYRIA] ✓ جاهز")


if __name__ == "__main__":
    main()
