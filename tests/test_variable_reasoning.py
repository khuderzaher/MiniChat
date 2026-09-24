# -*- coding: utf-8 -*-
"""MiniChat variable/unification hardening."""

from __future__ import annotations

import random
import sys
from pathlib import Path

# Allow direct execution:
# python3 tests/test_variable_reasoning.py
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from reasoning.engine import FormalReasoner
from reasoning.logic import LogicReasoner
from reasoning.model import (
    Fact,
    SemanticRule,
    VariablePredicate,
    VariableRule,
)
from reasoning.unification import (
    find_all_bindings,
    unify_term,
    unify_with_fact,
)


PASS = 0
FAIL = 0


def check(name, condition, detail=""):
    global PASS, FAIL

    if condition:
        PASS += 1
        print(f"✅ PASS | {name}")
    else:
        FAIL += 1
        print(f"❌ FAIL | {name} | {detail}")


def fact(subject, predicate, negated=False):
    return Fact(
        subject,
        predicate,
        negated=negated,
    )


def vp(functor, arg, negated=False):
    return VariablePredicate(
        functor,
        (arg,),
        negated,
    )


# ------------------------------------------------------------
# Unification
# ------------------------------------------------------------

check(
    "variable detection",
    unify_term(
        "?x",
        "سقراط",
        {},
    ) == {"?x": "سقراط"},
)

check(
    "bound variable consistency",
    unify_term(
        "?x",
        "سقراط",
        {"?x": "سقراط"},
    ) == {"?x": "سقراط"},
)

check(
    "bound variable conflict",
    unify_term(
        "?x",
        "أفلاطون",
        {"?x": "سقراط"},
    ) is None,
)

check(
    "constant equality",
    unify_term(
        "سقراط",
        "سقراط",
        {},
    ) == {},
)

check(
    "constant mismatch",
    unify_term(
        "سقراط",
        "أفلاطون",
        {},
    ) is None,
)

check(
    "predicate + variable match",
    unify_with_fact(
        "إنسان",
        ["?x"],
        False,
        fact(
            "سقراط",
            "إنسان",
        ),
        {},
    ) == {"?x": "سقراط"},
)


# ------------------------------------------------------------
# Same-variable conjunction
# ------------------------------------------------------------

premises = [
    ("إنسان", ["?x"], False),
    ("طالب", ["?x"], False),
]

same_entity = find_all_bindings(
    premises,
    [
        fact("سقراط", "إنسان"),
        fact("سقراط", "طالب"),
    ],
)

check(
    "same variable binds same entity",
    same_entity == [
        {"?x": "سقراط"}
    ],
    repr(same_entity),
)

cross_entity = find_all_bindings(
    premises,
    [
        fact("سقراط", "إنسان"),
        fact("أفلاطون", "طالب"),
    ],
)

check(
    "different entities do not cross-bind",
    cross_entity == [],
    repr(cross_entity),
)


# ------------------------------------------------------------
# Forward chaining
# ------------------------------------------------------------

engine = LogicReasoner(
    max_depth=10
)

engine.add_fact(
    fact("سقراط", "إنسان")
)

engine.add_variable_rule(
    VariableRule(
        premises=(
            vp("إنسان", "?x"),
        ),
        conclusion=vp("حي", "?x"),
        rule_id="human-alive",
    )
)

result = engine.infer(
    fact("سقراط", "حي")
)

check(
    "general rule proves concrete goal",
    result.valid
    and result.status == "proven"
    and result.conclusion == "سقراط هو حي",
    repr(result),
)

check(
    "general rule proof provenance",
    result.premises == [
        "سقراط هو إنسان"
    ],
    repr(result.premises),
)


# ------------------------------------------------------------
# Multi-hop variable chain
# ------------------------------------------------------------

engine = LogicReasoner(
    max_depth=10
)

engine.add_fact(
    fact("سقراط", "إنسان")
)

engine.add_variable_rule(
    VariableRule(
        premises=(
            vp("إنسان", "?x"),
        ),
        conclusion=vp("حي", "?x"),
        rule_id="r1",
    )
)

engine.add_variable_rule(
    VariableRule(
        premises=(
            vp("حي", "?x"),
        ),
        conclusion=vp("يتنفس", "?x"),
        rule_id="r2",
    )
)

engine.add_variable_rule(
    VariableRule(
        premises=(
            vp("يتنفس", "?x"),
        ),
        conclusion=vp("يحتاج_غذاء", "?x"),
        rule_id="r3",
    )
)

result = engine.infer(
    fact(
        "سقراط",
        "يحتاج_غذاء",
    )
)

check(
    "multi-hop variable reasoning",
    result.valid
    and result.status == "proven",
    repr(result),
)

check(
    "multi-hop provenance reaches base fact",
    result.premises == [
        "سقراط هو إنسان"
    ],
    repr(result.premises),
)


# ------------------------------------------------------------
# Entity isolation
# ------------------------------------------------------------

engine = LogicReasoner()

engine.add_facts(
    [
        fact("سقراط", "إنسان"),
        fact("أفلاطون", "إنسان"),
        fact("أرسطو", "شاعر"),
    ]
)

engine.add_variable_rule(
    VariableRule(
        premises=(
            vp("إنسان", "?x"),
        ),
        conclusion=vp("حي", "?x"),
    )
)

derived = engine.derive_with_variables()

derived_pairs = {
    (
        item.fact.subject,
        item.fact.predicate,
    )
    for item in derived
}

check(
    "variable isolation by entity",
    derived_pairs == {
        ("سقراط", "حي"),
        ("أفلاطون", "حي"),
    },
    repr(derived_pairs),
)


# ------------------------------------------------------------
# Negation
# ------------------------------------------------------------

negated = find_all_bindings(
    [
        ("إنسان", ["?x"], True)
    ],
    [
        fact(
            "سقراط",
            "إنسان",
            negated=True,
        )
    ],
)

check(
    "negated premise matches negated fact",
    negated == [
        {"?x": "سقراط"}
    ],
)

check(
    "negated premise rejects positive fact",
    find_all_bindings(
        [
            ("إنسان", ["?x"], True)
        ],
        [
            fact(
                "سقراط",
                "إنسان",
            )
        ],
    ) == [],
)


# ------------------------------------------------------------
# Noise immunity
# ------------------------------------------------------------

engine = LogicReasoner()

engine.add_facts(
    [
        fact("سقراط", "إنسان"),
        *[
            fact(
                f"noise_{i}",
                "غريب",
            )
            for i in range(50)
        ],
    ]
)

engine.add_variable_rule(
    VariableRule(
        premises=(
            vp("إنسان", "?x"),
        ),
        conclusion=vp("حي", "?x"),
    )
)

result = engine.infer(
    fact("سقراط", "حي")
)

check(
    "unrelated noise does not affect proof",
    result.valid
    and result.premises == [
        "سقراط هو إنسان"
    ],
    repr(result),
)


# ------------------------------------------------------------
# Unbound conclusion variable
# ------------------------------------------------------------

try:
    VariableRule(
        premises=(
            vp("إنسان", "?x"),
        ),
        conclusion=vp("حي", "?y"),
    )

    unbound_ok = False

except ValueError:
    unbound_ok = True

check(
    "unbound conclusion variable rejected",
    unbound_ok,
)


# ------------------------------------------------------------
# Multiple paths
# ------------------------------------------------------------

engine = LogicReasoner()

engine.add_facts(
    [
        fact("سقراط", "إنسان"),
        fact("سقراط", "كائن_حي"),
    ]
)

engine.add_variable_rule(
    VariableRule(
        premises=(
            vp("إنسان", "?x"),
        ),
        conclusion=vp("حي", "?x"),
        rule_id="path-a",
    )
)

engine.add_variable_rule(
    VariableRule(
        premises=(
            vp("كائن_حي", "?x"),
        ),
        conclusion=vp("حي", "?x"),
        rule_id="path-b",
    )
)

first = engine.infer(
    fact("سقراط", "حي")
)

second = engine.infer(
    fact("سقراط", "حي")
)

check(
    "multiple paths remain deterministic",
    first.steps == second.steps
    and first.premises == second.premises,
    f"first={first!r} second={second!r}",
)


# ------------------------------------------------------------
# Legacy compatibility
# ------------------------------------------------------------

legacy = LogicReasoner()

legacy.add_fact("A")
legacy.add_rule(
    "A",
    "B",
)

legacy_result = legacy.infer("B")

check(
    "legacy atomic reasoning preserved",
    legacy_result.valid
    and legacy_result.conclusion == "B",
    repr(legacy_result),
)


legacy_typed = LogicReasoner()

legacy_typed.add_fact(
    Fact(
        "ليلى",
        "طالبة",
    )
)

legacy_typed.add_rule(
    SemanticRule(
        Fact(
            "ليلى",
            "طالبة",
        ),
        Fact(
            "ليلى",
            "ناجحة",
        ),
    )
)

legacy_typed_result = legacy_typed.infer(
    Fact(
        "ليلى",
        "ناجحة",
    )
)

check(
    "legacy semantic rule preserved",
    legacy_typed_result.valid
    and legacy_typed_result.conclusion == "ليلى هو ناجحة",
    repr(legacy_typed_result),
)


# ------------------------------------------------------------
# Hybrid legacy + variable
# ------------------------------------------------------------

hybrid = LogicReasoner()

hybrid.add_fact(
    Fact(
        "سقراط",
        "إنسان",
    )
)

hybrid.add_variable_rule(
    VariableRule(
        premises=(
            vp("إنسان", "?x"),
        ),
        conclusion=vp("حي", "?x"),
    )
)

hybrid.add_rule(
    Fact(
        "سقراط",
        "حي",
    ),
    Fact(
        "سقراط",
        "يتنفس",
    ),
)

hybrid_result = hybrid.infer(
    Fact(
        "سقراط",
        "يتنفس",
    )
)

check(
    "variable-to-legacy hybrid chain",
    hybrid_result.valid
    and hybrid_result.conclusion == "سقراط هو يتنفس",
    repr(hybrid_result),
)


# ------------------------------------------------------------
# FormalReasoner integration
# ------------------------------------------------------------

formal = FormalReasoner(
    store=None
)

formal_result = formal.reason(
    "هل سقراط حي؟",
    context={
        "facts": [
            Fact(
                "سقراط",
                "إنسان",
            ),
        ],
        "variable_rules": [
            {
                "premises": [
                    {
                        "functor": "إنسان",
                        "args": ["?x"],
                    }
                ],
                "conclusion": {
                    "functor": "حي",
                    "args": ["?x"],
                },
                "rule_id": "formal-variable",
            }
        ],
        "goal": "سقراط هو حي",
    },
)

check(
    "FormalReasoner variable-rule integration",
    formal_result.valid
    and formal_result.status == "proven"
    and formal_result.conclusion == "سقراط هو حي",
    repr(formal_result),
)


# ------------------------------------------------------------
# Deterministic randomized intersection
# ------------------------------------------------------------

rng = random.Random(42)

names = [
    f"شخص_{i}"
    for i in range(40)
]

humans = set(
    rng.sample(
        names,
        25,
    )
)

students = set(
    rng.sample(
        names,
        20,
    )
)

expected = humans & students

facts = [
    *(
        fact(
            name,
            "إنسان",
        )
        for name in humans
    ),
    *(
        fact(
            name,
            "طالب",
        )
        for name in students
    ),
]

bindings = find_all_bindings(
    [
        ("إنسان", ["?x"], False),
        ("طالب", ["?x"], False),
    ],
    facts,
)

actual = {
    item["?x"]
    for item in bindings
}

check(
    "randomized variable intersection",
    actual == expected,
    f"expected={expected} actual={actual}",
)


print("=" * 65)
print(
    f"VARIABLE HARDENING: "
    f"{PASS} PASS / {FAIL} FAIL"
)
print("=" * 65)

raise SystemExit(
    1 if FAIL else 0
)
