# -*- coding: utf-8 -*-
"""
MiniChat v3 — Verification Layer Tests

تغطي:
- إعادة فحص نتائج الأدوات (math re-check) بما فيها عدم التطابق
- سلامة بنية البرهان (proof graph well-formedness)
- تغطية الأدلة وكشف ادعاءات المصادر غير المدعومة
- تكامل Pipeline: فشل التحقق لا يتحول لنجاح صامت
- تكامل الاستدلال: proof_verified + proof_node_count في metadata
- اختبارات عشوائية deterministic (seeded)
"""

from __future__ import annotations

import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.pipeline import Pipeline
from core.planner import Planner
from core.types import Evidence, Status, TaskPlan, ToolResult
from core.verification import DefaultVerifier
from reasoning.model import Fact
from reasoning.proof import ProofGraph

PASS = 0
FAIL = 0


def check(name: str, condition: bool):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"PASS : {name}")
    else:
        FAIL += 1
        print(f"FAIL : {name}")


V = DefaultVerifier()

# ------------------------------------------------------------
# 1) math re-check
# ------------------------------------------------------------

r = V.verify_math_result("احسب 25*4", 100)
check("math_recheck_correct", r.verified and r.metadata["expected"] == 100)

r = V.verify_math_result("احسب 25*4", 101)
check(
    "math_recheck_mismatch_flagged",
    not r.verified and "tool_result_mismatch" in r.issues,
)
check("math_recheck_correction", r.corrections == ["100"])

r = V.verify_math_result("ما عاصمة سوريا؟", None)
check(
    "math_recheck_no_expression",
    not r.verified
    and "no_math_expression_found_for_recheck" in r.issues,
)

r = V.verify_math_result("2+2", "not-a-number")
check(
    "math_recheck_non_numeric_result",
    not r.verified and "tool_result_not_numeric" in r.issues,
)

r = V.verify_math_result("7 × 6", 42)
check("math_recheck_unicode_multiply", r.verified)

# ------------------------------------------------------------
# 2) proof structure
# ------------------------------------------------------------

g = ProofGraph()
h = Fact("سقراط", "إنسان")
alive = Fact("سقراط", "حي")
g.add_fact(h)
g.add_inference(alive, rule_id="semantic:0:rule", bindings={}, parents=[h])

r = V.verify_proof_structure(g.serialize())
# fact node + inference node (add_fact on the premise may dedupe;
# assert exact count against serialized graph instead)
check(
    "proof_structure_valid",
    r.verified
    and r.metadata["node_count"] == len(g.serialize()["nodes"]),
)

bad = {"nodes": {"n1": {"kind": "inference", "parents": ["missing"]}}}
r = V.verify_proof_structure(bad)
check(
    "proof_structure_dangling_parent",
    not r.verified and any("dangling_parent" in i for i in r.issues),
)

bad2 = {"nodes": {"n1": {"kind": "banana", "parents": []}}}
r = V.verify_proof_structure(bad2)
check(
    "proof_structure_bad_kind",
    not r.verified and any("bad_kind" in i for i in r.issues),
)

r = V.verify_proof_structure("not json {{{")
check("proof_structure_invalid_json", not r.verified)

r = V.verify_proof_structure(None)
check("proof_structure_missing", not r.verified)

# ------------------------------------------------------------
# 3) evidence coverage / fabricated sources
# ------------------------------------------------------------

ev = [
    Evidence(
        content="دمشق عاصمة سوريا",
        source="general",
        source_type="faq",
    )
]

r = V.verify_generated_answer("عاصمة سوريا هي دمشق.", evidence=ev)
check("evidence_coverage_ok", r.verified)

r = V.verify_generated_answer(
    "The capital city is located near the river valley plateau region.",
    evidence=ev,
)
check(
    "evidence_low_coverage_flagged",
    not r.verified
    and any("low_evidence_coverage" in i for i in r.issues),
)

r = V.verify_generated_answer(
    "وفقًا لمصدر موثوق فإن الأمر كذلك",
    evidence=None,
)
check(
    "unsupported_source_claim_flagged",
    not r.verified and "unsupported_source_claim" in r.issues,
)

r = V.verify_generated_answer("", evidence=None)
check("empty_answer_flagged", not r.verified and "empty_answer" in r.issues)

# ------------------------------------------------------------
# 4) generic verify() contract
# ------------------------------------------------------------

res = V.verify("answer", evidence=None, context={"stage": "llm"})
check("verify_llm_stage_runs", res.status in (Status.SUCCESS, Status.ERROR))

res = V.verify("", context={})
check("verify_nothing_returns_empty", res.status == Status.EMPTY)

res = V.verify(
    "",
    context={"stage": "tool", "tool": "math", "query": "3*3", "value": 9},
)
check(
    "verify_tool_math_pass",
    res.status == Status.SUCCESS and res.metadata["verified"],
)

res = V.verify(
    "",
    context={"stage": "tool", "tool": "math", "query": "3*3", "value": 10},
)
check(
    "verify_tool_math_fail_is_error",
    res.status == Status.ERROR and not res.metadata["verified"],
)

res = V.verify(
    "",
    context={"stage": "reasoning", "proof_graph": g.serialize()},
)
check("verify_reasoning_proof_pass", res.status == Status.SUCCESS)

# ------------------------------------------------------------
# 5) pipeline integration (no silent success on failed verification)
# ------------------------------------------------------------


class _WrongMathTool:
    name = "math"

    def run(self, query, context=None):
        # Deliberately WRONG numeric result -> must fail verification.
        return ToolResult(success=True, tool="math", value=999, formatted="999")


plan = TaskPlan(mode="tool", needs_math=True, tools=["math"], needs_verification=True)

p = Pipeline()
p.register("math", _WrongMathTool())
p.register("verifier", DefaultVerifier())

out = p.execute("احسب 25*4", plan)
meta = out.metadata.get("verification", {})
check("pipeline_tool_verification_attached", "verified" in meta)
check(
    "pipeline_wrong_math_not_silent_success",
    out.status == Status.ERROR and meta.get("verified") is False,
)

from tools.math import MathTool

p2 = Pipeline()
p2.register("math", MathTool())
p2.register("verifier", DefaultVerifier())

out2 = p2.execute("احسب 25*4", plan)
check(
    "pipeline_correct_math_verified",
    out2.metadata.get("verification", {}).get("verified") is True
    and out2.status == Status.SUCCESS,
)

# No verifier registered -> legacy behavior preserved (backward compat)
p3 = Pipeline()
p3.register("math", MathTool())
out3 = p3.execute("احسب 25*4", plan)
check(
    "pipeline_without_verifier_unchanged",
    out3.status == Status.SUCCESS and "verification" not in out3.metadata,
)

# Reasoning stage carries proof graph + verification flag
from reasoning.engine import FormalReasoner

p4 = Pipeline()
p4.register("reasoner", FormalReasoner(store=None))
p4.register("verifier", DefaultVerifier())

rplan = TaskPlan(mode="reasoning", needs_reasoning=True, needs_verification=True)
out4 = p4.execute("هل سقراط حي؟", rplan)
md = out4.metadata
check(
    "pipeline_reasoning_stage",
    md.get("stage") == "reasoning",
)
check(
    "pipeline_reasoning_proof_metadata",
    "proof_node_count" in md and "proof_verified" in md,
)

# ------------------------------------------------------------
# 6) planner routing sanity (existing contracts preserved)
# ------------------------------------------------------------

pl = Planner()
u = pl.plan("احسب 25×4", {}) if False else None

from understanding.service import UnderstandingService

us = UnderstandingService()
plan_math = pl.plan("احسب 25*4", us.analyze("احسب 25*4"))
check("planner_math_routes_tool", plan_math.needs_math and "math" in plan_math.tools)
check("planner_math_requests_verification", plan_math.needs_verification)

# ------------------------------------------------------------
# 7) deterministic randomized property tests
# ------------------------------------------------------------

rng = random.Random(42)
ok = True
for _ in range(200):
    a = rng.randint(-999, 999)
    b = rng.randint(0, 999)
    expr = f"{a}*{b}"
    res = V.verify_math_result(expr, a * b)
    if not res.verified:
        ok = False
        break
    wrong = a * b + rng.choice([1, -1, 7])
    res2 = V.verify_math_result(expr, wrong)
    if res2.verified:
        ok = False
        break
check("random_math_property_200", ok)

rng2 = random.Random(7)
ok2 = True
for i in range(50):
    n = rng2.randint(1, 6)
    gg = ProofGraph()
    base = Fact(f"k{i}", "prop")
    gg.add_fact(base)
    prev = base
    for j in range(n):
        nxt = Fact(f"k{i}", f"derived{j}")
        gg.add_inference(nxt, rule_id=f"r{j}", bindings={}, parents=[prev])
        prev = nxt
    rr = V.verify_proof_structure(gg.serialize())
    if not rr.verified or rr.metadata["node_count"] != n + 1:
        ok2 = False
        break
check("random_proof_chains_50", ok2)

print("=" * 65)
print(f"VERIFICATION HARDENING: {PASS} PASS / {FAIL} FAIL")
print("=" * 65)

sys.exit(1 if FAIL else 0)
