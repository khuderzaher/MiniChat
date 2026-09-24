# -*- coding: utf-8 -*-
"""
MiniChat v3 — Arabic Logic Parser (bounded, deterministic)

مهمة هذه الطبقة: تحويل نص عربي طبيعي محدود إلى facts/rules قابلة
للاستدلال الشكلي، أو الإعلان عن العجز بوضوح.

النماذج المدعومة (عمدًا قليلة وصارمة):
    1. "كل X هو Y" / "كل X يـY"          => قاعدة متغيرة (X→Y)
       مثال: كل إنسان فانٍ  +  سقراط إنسان => سقراط فانٍ
    2. "X هو Y" / "X هي Y"               => fact بسيط
    3. "ليس X هو Y" / "X ليس Y"          => fact منفي
    4. نفي القاعدة لا يُشتق تلقائيًا — لا inverse افتراضي.

لا LLM هنا إطلاقًا. كل شيء regex/قواعد ثابتة.
أي نص خارج النماذج => parsed=False مع سبب، ولا اختلاق.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


def _normalize(text: str) -> str:
    text = text.strip()
    text = re.sub(r"[؟?.!,؛:]+$", "", text)
    return text


_SUBJECT_COPULA = re.compile(
    r"^(.+?)\s+(?:هو|هي)\s+(.+)$"
)

_NEGATED_COPULA = re.compile(
    r"^(?:ليس|ليست)\s+(.+?)\s+(?:هو|هي)?\s*(.+)$"
)

_NEGATED_POSTFIX = re.compile(
    r"^(.+?)\s+(?:ليس|ليست)\s+(.+)$"
)

_UNIVERSAL_RULE = re.compile(
    r"^كل\s+(.+?)\s+(?:هو|هي|يكون|تكون)?\s*(.+)$"
)

_PARTICULAR = re.compile(r"^(بعض|هناك)\s+")


@dataclass
class ParsedStatement:
    kind: str                       # "fact" | "negated_fact" | "rule" | "unsupported"
    subject: str = ""
    predicate: str = ""
    raw: str = ""
    reason: str = ""

    def as_fact(self) -> Optional[str]:
        if self.kind == "fact":
            return f"{self.subject} هو {self.predicate}"
        if self.kind == "negated_fact":
            return f"¬{self.subject} هو {self.predicate}"
        return None

    def as_rule(self) -> Optional[Dict[str, Any]]:
        """قاعدة متغيرة: premise(X)=subject => conclusion(X)=predicate."""
        if self.kind != "rule":
            return None
        var = "?X"
        return {
            "premise": {"predicate": self.subject, "args": [var]},
            "conclusion": {"predicate": self.predicate, "args": [var]},
            "source": "arabic_statement_parser",
        }


class _VariableRuleAdapter:
    """
    محوّل statement -> VariableRule دون استيراد reasoning.model
    في مستوى الاستيراد العلوي (يتفادى أي دورة استيراد).
    """

    @staticmethod
    def to_variable_rule(statement: ParsedStatement):
        from reasoning.model import VariablePredicate, VariableRule

        var = "?X"
        return VariableRule(
            premises=(
                VariablePredicate(functor=statement.subject, args=(var,)),
            ),
            conclusion=VariablePredicate(
                functor=statement.predicate, args=(var,)
            ),
            source="arabic_statement_parser",
        )


class ArabicStatementParser:
    """
    parser محافظ: لا يشتق إلا ما يطابق نموذجًا صريحًا تمامًا.
    """

    name = "arabic-statement-parser"

    def parse(self, text: str) -> ParsedStatement:
        if not isinstance(text, str):
            return ParsedStatement(kind="unsupported", reason="not_a_string")

        clean = _normalize(text)

        if not clean:
            return ParsedStatement(kind="unsupported", reason="empty_text")

        # "بعض ..." — وجودي لا يمكن اشتقاقه بشكل آمن كقاعدة كلية.
        if _PARTICULAR.match(clean):
            return ParsedStatement(
                kind="unsupported",
                raw=text,
                reason="particular_quantifier_not_supported",
            )

        universal = _UNIVERSAL_RULE.match(clean)
        if universal:
            subject = _normalize(universal.group(1))
            predicate = _normalize(universal.group(2))
            if subject and predicate and " " not in predicate.split():
                return ParsedStatement(
                    kind="rule",
                    subject=subject,
                    predicate=predicate,
                    raw=text,
                )
            if subject and predicate:
                # قواعد متعددة الكلمات مسموحة إذا كانت مختصرة ومحدودة.
                if len(subject) <= 60 and len(predicate) <= 60:
                    return ParsedStatement(
                        kind="rule",
                        subject=subject,
                        predicate=predicate,
                        raw=text,
                    )
            return ParsedStatement(
                kind="unsupported",
                raw=text,
                reason="universal_rule_too_complex",
            )

        neg_prefix = _NEGATED_COPULA.match(clean)
        if neg_prefix:
            subject = _normalize(neg_prefix.group(1))
            predicate = _normalize(neg_prefix.group(2))
            if subject and predicate:
                return ParsedStatement(
                    kind="negated_fact",
                    subject=subject,
                    predicate=predicate,
                    raw=text,
                )

        neg_postfix = _NEGATED_POSTFIX.match(clean)
        if neg_postfix:
            subject = _normalize(neg_postfix.group(1))
            predicate = _normalize(neg_postfix.group(2))
            if subject and predicate:
                return ParsedStatement(
                    kind="negated_fact",
                    subject=subject,
                    predicate=predicate,
                    raw=text,
                )

        copula = _SUBJECT_COPULA.match(clean)
        if copula:
            subject = _normalize(copula.group(1))
            predicate = _normalize(copula.group(2))
            if subject and predicate:
                return ParsedStatement(
                    kind="fact",
                    subject=subject,
                    predicate=predicate,
                    raw=text,
                )

        return ParsedStatement(
            kind="unsupported",
            raw=text,
            reason="no_supported_pattern",
        )

    def parse_many(self, texts: List[str]) -> Dict[str, List[ParsedStatement]]:
        buckets: Dict[str, List[ParsedStatement]] = {
            "facts": [],
            "rules": [],
            "unsupported": [],
        }
        for text in texts:
            statement = self.parse(text)
            if statement.kind in ("fact", "negated_fact"):
                buckets["facts"].append(statement)
            elif statement.kind == "rule":
                buckets["rules"].append(statement)
            else:
                buckets["unsupported"].append(statement)
        return buckets
