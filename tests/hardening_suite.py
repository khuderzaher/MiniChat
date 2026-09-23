# -*- coding: utf-8 -*-
"""
MiniChat — Development Hardening / Regression Suite

الهدف:
- كشف الانكسارات قبل إضافة ميزات جديدة.
- اختبار عدم تسرب الحالة.
- اختبار parser / reasoning / storage / planner / pipeline.
- كشف hanging داخل Runtime بمهلة زمنية.
- عدم تشغيل LLM الحقيقي ضمن اختبارات الوحدات.
"""

from __future__ import annotations

import importlib
import inspect
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

PASS = 0
FAIL = 0
WARN = 0


def ok(name: str, detail: str = ""):
    global PASS
    PASS += 1
    print(f"✅ PASS | {name}" + (f" | {detail}" if detail else ""))


def fail(name: str, detail: str = ""):
    global FAIL
    FAIL += 1
    print(f"❌ FAIL | {name}" + (f" | {detail}" if detail else ""))


def warn(name: str, detail: str = ""):
    global WARN
    WARN += 1
    print(f"⚠️ WARN | {name}" + (f" | {detail}" if detail else ""))


def section(title: str):
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


# ------------------------------------------------------------
# 1. Python syntax integrity
# ------------------------------------------------------------

section("1) PYTHON SYNTAX INTEGRITY")

bad = []

for path in ROOT.rglob("*.py"):
    if any(part in {".venv", "venv", "__pycache__", ".git"} for part in path.parts):
        continue

    try:
        compile(
            path.read_text(encoding="utf-8"),
            str(path),
            "exec",
        )
    except Exception as exc:
        bad.append((path, exc))

if not bad:
    ok("all Python files compile")
else:
    for path, exc in bad:
        fail(str(path), f"{type(exc).__name__}: {exc}")


# ------------------------------------------------------------
# 2. Critical imports
# ------------------------------------------------------------

section("2) CRITICAL IMPORTS")

critical_modules = [
    "core.types",
    "core.protocols",
    "core.policies",
    "core.pipeline",
    "core.orchestrator",
    "core.planner",
    "understanding_engine",
    "reasoning.logic",
    "reasoning.parser",
    "reasoning.storage",
    "reasoning.engine",
    "tools.math",
    "generation.llm",
    "runtime",
]

for module_name in critical_modules:
    try:
        importlib.import_module(module_name)
        ok(f"import {module_name}")
    except Exception as exc:
        fail(f"import {module_name}", f"{type(exc).__name__}: {exc}")


# ------------------------------------------------------------
# 3. Understanding routing
# ------------------------------------------------------------

section("3) UNDERSTANDING / QUESTION CLASSIFICATION")

from understanding_engine import classify_question

classification_cases = {
    "هل سقراط هو إنسان؟": "logic",
    "إذا كان سقراط إنسانًا فهل هو حي؟": "logic",
    "هل يمكن أن يكون الشيء موجودًا وغير موجود في الوقت نفسه؟": "logic",
    "لماذا السماء زرقاء؟": "why",
    "قارن بين الضوء والصوت": "compare",
    "ما هي عاصمة سوريا؟": "define",
    "ما هو تعريف الموجة؟": "define",
}

for query, expected in classification_cases.items():
    actual = classify_question(query)
    if actual == expected:
        ok(f"classify: {query}", actual)
    else:
        fail(
            f"classify: {query}",
            f"expected={expected!r}, actual={actual!r}",
        )


# ------------------------------------------------------------
# 4. Arabic logic parser
# ------------------------------------------------------------

section("4) ARABIC LOGIC PARSER")

from reasoning.parser import ArabicLogicParser

parser = ArabicLogicParser()

parser_cases = [
    ("الماء هو سائل", "الماء", "سايل"),
    ("السماء هي زرقاء", "السماء", "زرقاء"),
    ("مرحبا كيف حالك؟", None, None),
    ("", None, None),
]

for text, expected_subject, expected_predicate in parser_cases:
    result = parser.parse_fact(text)

    if expected_subject is None:
        if result is None:
            ok(f"parser rejects: {text!r}")
        else:
            fail(
                f"parser rejects: {text!r}",
                f"unexpected={result!r}",
            )
        continue

    if (
        result is not None
        and result.subject == expected_subject
        and result.predicate == expected_predicate
    ):
        ok(f"parser: {text}")
    else:
        fail(f"parser: {text}", f"result={result!r}")


# ------------------------------------------------------------
# 5. Deterministic logic engine
# ------------------------------------------------------------

section("5) LOGIC ENGINE")

from reasoning.logic import LogicReasoner

# Direct fact
engine = LogicReasoner()
engine.add_fact("A")
result = engine.infer(goal="A")

if result.valid and result.conclusion == "A":
    ok("direct fact")
else:
    fail("direct fact", repr(result))


# Multi-hop
engine = LogicReasoner(max_depth=20)
engine.add_fact("A")
engine.add_rule("A", "B", source="r1")
engine.add_rule("B", "C", source="r2")
engine.add_rule("C", "D", source="r3")

result = engine.infer(goal="D")

if (
    result.valid
    and result.conclusion == "D"
    and len(result.steps) == 3
):
    ok("multi-hop chain", f"{len(result.steps)} steps")
else:
    fail("multi-hop chain", repr(result))


# Undetermined
engine = LogicReasoner()
engine.add_fact("A")
result = engine.infer(goal="B")

if not result.valid and result.metadata.get("status") == "undetermined":
    ok("undetermined goal")
else:
    fail("undetermined goal", repr(result))


# Contradiction
engine = LogicReasoner()
engine.add_fact("A")
engine.add_rule("A", "B", source="positive")
engine.add_rule("A", "¬B", source="negative")

result = engine.infer(goal="B")

if not result.valid and result.metadata.get("status") == "contradiction":
    ok("contradiction detection")
else:
    fail("contradiction detection", repr(result))


# State isolation
engine = LogicReasoner()
engine.add_fact("A")
result1 = engine.infer(goal="A")

engine2 = LogicReasoner()
result2 = engine2.infer(goal="A")

if result1.valid and not result2.valid:
    ok("engine state isolation")
else:
    fail("engine state isolation", f"r1={result1!r}, r2={result2!r}")


# ------------------------------------------------------------
# 6. Reasoning storage
# ------------------------------------------------------------

section("6) REASONING STORAGE")

from reasoning.storage import ReasoningStore

with tempfile.TemporaryDirectory() as tmp:
    db_path = Path(tmp) / "reasoning.db"
    store = ReasoningStore(db_path)

    first = store.add_fact(
        "سقراط",
        "هو",
        "إنسان",
        source="test",
    )

    second = store.add_fact(
        "سقراط",
        "هو",
        "إنسان",
        source="test",
    )

    if first and not second:
        ok("fact deduplication")
    else:
        fail(
            "fact deduplication",
            f"first={first}, second={second}",
        )

    store.add_rule(
        "سقراط هو إنسان",
        "سقراط هو حي",
        source="test",
    )

    facts = store.get_facts()
    rules = store.get_rules()

    if len(facts) == 1 and len(rules) == 1:
        ok("storage round-trip")
    else:
        fail(
            "storage round-trip",
            f"facts={facts}, rules={rules}",
        )

    store.close()


# ------------------------------------------------------------
# 7. FormalReasoner contract
# ------------------------------------------------------------

section("7) FORMAL REASONER")

from reasoning.engine import FormalReasoner

reasoner = FormalReasoner(
    store=ReasoningStore(":memory:")
)

formal_result = reasoner.reason(
    "test",
    context={
        "facts": ["سقراط هو إنسان"],
        "rules": [
            {
                "premise": "سقراط هو إنسان",
                "conclusion": "سقراط هو حي",
                "source": "hardening",
            }
        ],
        "goal": "سقراط هو حي",
    },
)

if (
    formal_result.valid
    and formal_result.conclusion == "سقراط هو حي"
    and formal_result.metadata.get("reasoner") == "formal-reasoner"
):
    ok("FormalReasoner contract")
else:
    fail("FormalReasoner contract", repr(formal_result))


# ------------------------------------------------------------
# 8. Planner routing
# ------------------------------------------------------------

section("8) PLANNER ROUTING")

from runtime import MiniChatRuntime

runtime = MiniChatRuntime()

routing_cases = [
    ("هل سقراط هو إنسان؟", True, False, False),
    ("لماذا السماء زرقاء؟", True, True, False),
    ("قارن بين الضوء والصوت", True, True, False),
    ("ما هي عاصمة سوريا؟", False, True, False),
    ("احسب 25 × 4", False, False, True),
]

for query, expected_reasoning, expected_knowledge, expected_math in routing_cases:
    analysis = runtime.orchestrator.understanding.analyze(query)
    plan = runtime.orchestrator.planner.plan(query, analysis)

    if (
        plan.needs_reasoning == expected_reasoning
        and plan.needs_knowledge == expected_knowledge
        and plan.needs_math == expected_math
    ):
        ok(f"planner: {query}")
    else:
        fail(
            f"planner: {query}",
            (
                f"got reasoning={plan.needs_reasoning}, "
                f"knowledge={plan.needs_knowledge}, "
                f"math={plan.needs_math}"
            ),
        )


# ------------------------------------------------------------
# 9. Pipeline reasoning without LLM
# ------------------------------------------------------------

section("9) PIPELINE — FORMAL REASONING PATH")

from core.pipeline import Pipeline
from core.types import TaskPlan

pipeline = Pipeline()
pipeline.register("reasoner", reasoner)

analysis = runtime.orchestrator.understanding.analyze(
    "هل سقراط هو حي؟"
)

plan = runtime.orchestrator.planner.plan(
    "هل سقراط هو حي؟",
    analysis,
)

try:
    pipeline_result = pipeline.execute(
        "هل سقراط هو حي؟",
        plan,
        context={
            "facts": ["سقراط هو إنسان"],
            "rules": [
                {
                    "premise": "سقراط هو إنسان",
                    "conclusion": "سقراط هو حي",
                    "source": "pipeline-hardening",
                }
            ],
            "goal": "سقراط هو حي",
        },
    )

    if (
        getattr(pipeline_result, "source", None) == "reasoner"
        and getattr(getattr(pipeline_result, "value", None), "valid", False)
    ):
        ok("pipeline → reasoner")
    else:
        fail(
            "pipeline → reasoner",
            repr(pipeline_result),
        )

except Exception as exc:
    fail(
        "pipeline → reasoner",
        f"{type(exc).__name__}: {exc}",
    )


# ------------------------------------------------------------
# 10. Real Runtime watchdog
# ------------------------------------------------------------

section("10) REAL RUNTIME HANG DETECTION")

child_code = r'''
from runtime import MiniChatRuntime

runtime = MiniChatRuntime()

result = runtime.handle(
    "هل سقراط هو حي؟",
    context={
        "facts": ["سقراط هو إنسان"],
        "rules": [
            {
                "premise": "سقراط هو إنسان",
                "conclusion": "سقراط هو حي",
                "source": "runtime-watchdog",
            }
        ],
        "goal": "سقراط هو حي",
    },
)

print("RETURNED")
print("STATUS:", getattr(result, "status", None))
print("SOURCE:", getattr(result, "source", None))
print("VALUE:", type(getattr(result, "value", None)).__name__)
'''

try:
    proc = subprocess.run(
        [sys.executable, "-c", child_code],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=20,
    )

    if proc.returncode == 0:
        ok(
            "runtime.handle returns within 20s",
            proc.stdout.strip().replace("\n", " | "),
        )
    else:
        fail(
            "runtime.handle crashed",
            (
                proc.stdout.strip()
                + " || STDERR: "
                + proc.stderr.strip()
            ).strip()
        )

except subprocess.TimeoutExpired:
    fail(
        "runtime.handle HANG",
        "child process exceeded 20 seconds",
    )


# ------------------------------------------------------------
# 11. Reasoning isolation + proof provenance
# ------------------------------------------------------------

section("11) REASONING ISOLATION + PROOF PROVENANCE")

from reasoning.engine import FormalReasoner
from reasoning.storage import ReasoningStore


# Persistent knowledge must NOT leak by default.
store = ReasoningStore(":memory:")
store.add_fact("ليلى", "هي", "غائبة")
store.add_rule(
    "ليلى هي غائبة",
    "ليلى هي فاشلة",
    source="persistent-old",
)

isolated_reasoner = FormalReasoner(store=store)

isolated = isolated_reasoner.reason(
    "هل ليلى هي ناجحة؟",
    context={
        "facts": ["ليلى هي طالبة"],
        "rules": [
            {
                "premise": "ليلى هي طالبة",
                "conclusion": "ليلى هي مجتهدة",
                "source": "current",
            },
            {
                "premise": "ليلى هي مجتهدة",
                "conclusion": "ليلى هي ناجحة",
                "source": "current",
            },
        ],
        "goal": "ليلى هي ناجحة",
    },
)

if (
    isolated.valid
    and isolated.conclusion == "ليلى هي ناجحة"
    and isolated.premises == ["ليلى هي طالبة"]
    and all("persistent-old" not in step for step in isolated.steps)
):
    ok("persistent knowledge isolation")
else:
    fail("persistent knowledge isolation", repr(isolated))


# Persistent knowledge may be explicitly enabled.
persistent = isolated_reasoner.reason(
    "هل ليلى هي فاشلة؟",
    context={
        "use_persistent": True,
        "goal": "ليلى هي فاشلة",
    },
)

if (
    persistent.valid
    and persistent.conclusion == "ليلى هي فاشلة"
    and persistent.premises == ["ليلى هي غائبة"]
):
    ok("explicit persistent knowledge")
else:
    fail("explicit persistent knowledge", repr(persistent))


# Proof premises must exclude unrelated current facts.
proof = isolated_reasoner.reason(
    "هل ليلى هي ناجحة؟",
    context={
        "facts": [
            "ليلى هي طالبة",
            "أحمد هو غني",
            "سارة هي سعيدة",
        ],
        "rules": [
            {
                "premise": "ليلى هي طالبة",
                "conclusion": "ليلى هي ناجحة",
                "source": "proof-test",
            }
        ],
        "goal": "ليلى هي ناجحة",
    },
)

if proof.premises == ["ليلى هي طالبة"]:
    ok("proof-specific premises")
else:
    fail("proof-specific premises", repr(proof))


# Contradiction provenance.
contradiction = isolated_reasoner.reason(
    "هل ليلى هي ناجحة؟",
    context={
        "facts": ["ليلى هي طالبة"],
        "rules": [
            {
                "premise": "ليلى هي طالبة",
                "conclusion": "ليلى هي ناجحة",
                "source": "positive",
            },
            {
                "premise": "ليلى هي طالبة",
                "conclusion": "¬ليلى هي ناجحة",
                "source": "negative",
            },
        ],
        "goal": "ليلى هي ناجحة",
    },
)

if (
    contradiction.metadata.get("status") == "contradiction"
    and contradiction.premises == ["ليلى هي طالبة"]
):
    ok("contradiction provenance")
else:
    fail("contradiction provenance", repr(contradiction))


# ------------------------------------------------------------
# 12. Deterministic randomized reasoning
# ------------------------------------------------------------

section("12) DETERMINISTIC RANDOMIZED REASONING")

import random

rng = random.Random(20260923)

random_failures = []

for case_id in range(100):
    subject = f"كيان{case_id}"

    chain_length = rng.randint(1, 8)
    predicates = [
        f"صفة_{case_id}_{i}"
        for i in range(chain_length + 1)
    ]

    facts = [f"{subject} هو {predicates[0]}"]

    rules = []
    for i in range(chain_length):
        rules.append(
            {
                "premise": f"{subject} هو {predicates[i]}",
                "conclusion": f"{subject} هو {predicates[i + 1]}",
                "source": f"random-{case_id}",
            }
        )

    # Add unrelated noise.
    for noise in range(rng.randint(1, 5)):
        facts.append(f"ضوضاء{case_id}_{noise} هو غير_مرتبط")

    expected_goal = f"{subject} هو {predicates[-1]}"

    rr = isolated_reasoner.reason(
        f"هل {expected_goal}؟",
        context={
            "facts": facts,
            "rules": rules,
            "goal": expected_goal,
        },
    )

    if not (
        rr.valid
        and rr.conclusion == expected_goal
        and rr.premises == [facts[0]]
        and len(rr.steps) == chain_length
    ):
        random_failures.append(
            {
                "case": case_id,
                "chain_length": chain_length,
                "result": repr(rr),
            }
        )

if not random_failures:
    ok("100 randomized reasoning scenarios")
else:
    fail(
        "100 randomized reasoning scenarios",
        repr(random_failures[:3]),
    )


# ------------------------------------------------------------
# 13. Randomized negative / missing-link tests
# ------------------------------------------------------------

section("13) RANDOMIZED NEGATIVE REASONING")

negative_failures = []

for case_id in range(100):
    subject = f"سلبية{case_id}"

    facts = [f"{subject} هو البداية"]

    rules = [
        {
            "premise": f"{subject} هو البداية",
            "conclusion": f"{subject} هو وسط",
            "source": "negative-random",
        }
    ]

    # Goal deliberately requires a missing second rule.
    goal = f"{subject} هو نهاية"

    rr = isolated_reasoner.reason(
        f"هل {goal}؟",
        context={
            "facts": facts,
            "rules": rules,
            "goal": goal,
        },
    )

    if rr.metadata.get("status") != "undetermined":
        negative_failures.append((case_id, repr(rr)))

if not negative_failures:
    ok("100 randomized missing-link scenarios")
else:
    fail(
        "100 randomized missing-link scenarios",
        repr(negative_failures[:3]),
    )


store.close()


# ------------------------------------------------------------
# 14. Formal reasoner repeatability
# ------------------------------------------------------------

section("14) REASONING REPEATABILITY")

repeat_context = {
    "facts": ["سليم هو طالب"],
    "rules": [
        {
            "premise": "سليم هو طالب",
            "conclusion": "سليم هو مجتهد",
            "source": "repeat",
        },
        {
            "premise": "سليم هو مجتهد",
            "conclusion": "سليم هو ناجح",
            "source": "repeat",
        },
    ],
    "goal": "سليم هو ناجح",
}

r1 = isolated_reasoner.reason("هل سليم هو ناجح؟", context=repeat_context)
r2 = isolated_reasoner.reason("هل سليم هو ناجح؟", context=repeat_context)

if (
    r1.valid == r2.valid
    and r1.conclusion == r2.conclusion
    and r1.premises == r2.premises
    and r1.steps == r2.steps
    and r1.metadata.get("status") == r2.metadata.get("status")
):
    ok("deterministic repeatability")
else:
    fail("deterministic repeatability", f"r1={r1!r} r2={r2!r}")

# ------------------------------------------------------------
# Final report
# ------------------------------------------------------------

section("FINAL HARDENING REPORT")

total = PASS + FAIL + WARN

print(f"PASS : {PASS}")
print(f"FAIL : {FAIL}")
print(f"WARN : {WARN}")
print(f"TOTAL: {total}")

if FAIL == 0:
    print("\n🟢 HARDENING STATUS: CLEAN")
    sys.exit(0)

print("\n🔴 HARDENING STATUS: FAILURES DETECTED")
sys.exit(1)
