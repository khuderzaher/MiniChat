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



# ============================================================
# Canonical Arabic *query* compiler
# ------------------------------------------------------------
# This is a semantic-interpretation layer, not a bag of ad-hoc
# regexes: every supported surface pattern maps onto the same
# canonical typed representation used by the logic engine
# (Fact / VariablePredicate / VariableRule).  Anything that does
# not map cleanly is reported as unsupported — never guessed.
# ============================================================

_TANWEEN = {
    "\u064b": "",   # fathatan
    "\u064c": "",   # dammatan
    "\u064d": "",   # kasratan
}


def _canonicalize(text: str) -> str:
    """Deterministic light normalization for pattern matching."""

    text = (text or "").strip()
    text = re.sub(r"[؟?!.،,؛:]+$", "", text)

    for mark, replacement in _TANWEEN.items():
        text = text.replace(mark, replacement)

    text = text.replace("\u0623\u0644", "\u0627\u0644")  # common hamza-definite merge
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def _strip_leading_if(text: str) -> str:
    for prefix in ("إذا كان ", "إذا كانت ", "إذا "):
        if text.startswith(prefix):
            return text[len(prefix):].strip()
    return text


_CLAUSE_SPLIT = re.compile(r"\s*(?:و|،|,)\s*(?=.)")

_UNIVERSAL_GENERIC = re.compile(
    r"^كل\s+(.+?)\s+(?:هو|هي|يكون|تكون)?\s*(.+)$"
)

_COPULA_FACT = re.compile(r"^(.+?)\s+(?:هو|هي)\s+(.+)$")

_COMPARATIVE = re.compile(
    r"^(.+?)\s+(أطول|أكبر|أصغر|أقدم|أحدث|أسرع|أبطأ|أثقل|أخف|أعلى|أدنى|أغلى|أرخص|أفضل|أسوأ|أكثر|أقل)\s+من\s+(.+)$"
)

_YESNO_GOAL = re.compile(
    r"^هل\s+(.+?)\s+(?:هو|هي)?\s+(.+?)\s*$"
)

_WHO_REL_GOAL = re.compile(
    r"^(?:فـ)?مَن\s+(?:الـ)?(.+?)\s+بين\s+(.+?)\s+و\s+(.+?)\s*[؟?]?$"
)

_WHICH_REL_GOAL = re.compile(
    r"^(?:فـ)?أيّ?\s+(.+?)\s+بين\s+(.+?)\s+و\s+(.+?)\s*[؟?]?$"
)

_SUPERLATIVE_WORDS = {
    "الأطول": "أطول",
    "الاطول": "أطول",
    "الأكبر": "أكبر",
    "الاكبر": "أكبر",
    "الأصغر": "أصغر",
    "الاصغر": "أصغر",
    "الأقدم": "أقدم",
    "الاقدم": "أقدم",
    "الأسرع": "أسرع",
    "الاسرع": "أسرع",
    "الأفضل": "أفضل",
    "الافضل": "أفضل",
}


@dataclass
class CompiledQuery:
    """Canonical logical form of an Arabic question."""

    supported: bool
    facts: List[Any] = field(default_factory=list)
    variable_rules: List[Any] = field(default_factory=list)
    goal: Any = None
    reason: str = ""
    raw: str = ""


class ArabicQueryCompiler:
    """
    Conservative compiler from Arabic surface text to canonical
    logical forms consumed by LogicReasoner / FormalReasoner.

    Supported surface families (by *structure*, not vocabulary):

      1. Conditional fact chains ending with a yes/no goal:
         "إذا كان <clause> و <clause> ... فهل <X> <P>؟"
         clauses are compiled individually (fact | universal rule |
         comparative relation), and the final clause becomes the
         goal.

      2. Relational choice questions:
         "<premises...> فمن/فأيّ الـ<sadj> بين <A> و <B>؟"
         compiles to a binary pattern goal أطول(?X, @B) style.

      3. Plain yes/no over class membership:
         "هل <X> <P>؟"  -> goal Fact(X, P)

    Anything else returns supported=False with an explicit reason.
    No meaning is ever invented.
    """

    name = "arabic-query-compiler"

    # --------------------------------------------------------
    # single-clause compilation
    # --------------------------------------------------------

    def compile_clause(self, text: str):
        """
        Returns one of:
          ("fact", Fact)
          ("negated_fact", Fact)
          ("rule", VariableRule)
          ("relation", Fact)           # binary ground fact
          (None, reason)
        """

        from reasoning.model import (
            Fact,
            VariablePredicate,
            VariableRule,
        )

        clean = _canonicalize(_strip_leading_if(text))

        if not clean:
            return None, "empty_clause"

        # negation first (before copula rules eat it)
        statement = ArabicStatementParser().parse(clean)

        comparative = _COMPARATIVE.match(clean)
        if comparative:
            subject = _canonicalize(comparative.group(1))
            rel = comparative.group(2)
            target = _canonicalize(comparative.group(3))
            if subject and target:
                return "relation", Fact(
                    subject=subject,
                    predicate=f"{rel} @{target}",
                )
            return None, "comparative_missing_term"

        if statement.kind == "rule":
            var = "?X"
            try:
                rule = VariableRule(
                    premises=(
                        VariablePredicate(
                            functor=_canonicalize(statement.subject),
                            args=(var,),
                        ),
                    ),
                    conclusion=VariablePredicate(
                        functor=_canonicalize(statement.predicate),
                        args=(var,),
                    ),
                    source="arabic_query_compiler",
                )
            except ValueError:
                return None, "rule_variables_invalid"
            return "rule", rule

        if statement.kind == "fact":
            return "fact", Fact(
                subject=_canonicalize(statement.subject),
                predicate=_canonicalize(statement.predicate),
            )

        if statement.kind == "negated_fact":
            return "negated_fact", Fact(
                subject=_canonicalize(statement.subject),
                predicate=_canonicalize(statement.predicate),
                negated=True,
            )

        # nominal sentence without copula: "سقراط إنسان"
        parts = clean.split(" ")
        if len(parts) == 2 and parts[0] and parts[1]:
            return "fact", Fact(
                subject=parts[0],
                predicate=parts[1],
            )

        return None, "no_supported_clause_pattern"

    # --------------------------------------------------------
    # goal extraction
    # --------------------------------------------------------

    def compile_goal(self, text: str):
        """
        Returns:
          ("goal_fact", Fact)
          ("goal_pattern", VariablePredicate)
          (None, reason)
        """

        from reasoning.model import VariablePredicate

        clean = _canonicalize(re.sub(r"^(فـ)?", "", _canonicalize(text)))
        clean = _canonicalize(text)
        clean = re.sub(r"^[ف]", "", clean) if clean.startswith("ف") else clean
        clean = _canonicalize(clean)

        who = _WHO_REL_GOAL.match(clean) or _WHICH_REL_GOAL.match(clean)
        if who:
            adjective = _canonicalize(who.group(1))
            left = _canonicalize(who.group(2))
            right = _canonicalize(who.group(3))
            core = _SUPERLATIVE_WORDS.get(adjective)
            if core is None and adjective.startswith("ال"):
                core = adjective[2:]
            if core and left and right:
                return "goal_pattern", VariablePredicate(
                    functor=core,
                    args=("?X", "@" + right),
                )
            return None, "relational_goal_unresolved"

        yesno = _YESNO_GOAL.match(clean.rstrip("؟?"))
        if yesno:
            subject = _canonicalize(yesno.group(1))
            predicate = _canonicalize(yesno.group(2))
            if subject and predicate:
                from reasoning.model import Fact
                return "goal_fact", Fact(
                    subject=subject,
                    predicate=predicate,
                )

        return None, "no_supported_goal_pattern"

    # --------------------------------------------------------
    # full query compilation
    # --------------------------------------------------------

    def compile(self, text: str) -> CompiledQuery:
        if not isinstance(text, str) or not text.strip():
            return CompiledQuery(supported=False, reason="empty_text")

        original = text.strip()
        cleaned = _canonicalize(original)

        conditional = re.match(
            r"^إذا\s+كان(?:ت)?\s+(.+?)(?:\s+f?(?:فهل|فمن|فأي))(.+)$",
            cleaned,
        )
        # Arabic-aware split on the concluding فـ marker.
        goal_part = None
        premise_part = cleaned

        for marker in ("فهل ", "فمن ", "فأيّ ", "فأي "):
            index = cleaned.find(marker)
            if index != -1:
                premise_part = cleaned[:index]
                goal_part = cleaned[index:]
                break

        if premise_part.startswith("إذا"):
            premise_part = _strip_leading_if(premise_part)
        elif premise_part == cleaned and not goal_part:
            # Not a conditional chain at all: maybe a plain yes/no.
            kind, value = self.compile_goal(cleaned)
            if kind is None:
                return CompiledQuery(
                    supported=False,
                    reason="no_supported_query_structure",
                    raw=original,
                )
            return CompiledQuery(
                supported=True,
                goal=value,
                raw=original,
            )

        if goal_part is None:
            return CompiledQuery(
                supported=False,
                reason="missing_conclusion_clause",
                raw=original,
            )

        goal_kind, goal_value = self.compile_goal(goal_part)

        if goal_kind is None:
            return CompiledQuery(
                supported=False,
                reason=goal_value,
                raw=original,
            )

        query = CompiledQuery(supported=True, goal=goal_value, raw=original)

        clauses = [
            clause
            for clause in _CLAUSE_SPLIT.split(premise_part)
            if clause.strip()
        ]

        if not clauses:
            query.supported = False
            query.reason = "no_premises"
            query.goal = None
            return query

        for clause in clauses:
            kind, value = self.compile_clause(clause)

            if kind == "fact" or kind == "negated_fact":
                query.facts.append(value)
            elif kind == "relation":
                query.facts.append(value)
            elif kind == "rule":
                query.variable_rules.append(value)
            else:
                # A single uncompilable clause makes the whole
                # interpretation unreliable: fail explicitly.
                return CompiledQuery(
                    supported=False,
                    reason=f"premise_unsupported:{value}",
                    raw=original,
                )

        return query
