# -*- coding: utf-8 -*-

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from reasoning.engine import FormalReasoner
from reasoning.proof import ProofGraph
from reasoning.logic import LogicReasoner
from reasoning.model import Fact, VariablePredicate, VariableRule


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


def vp(functor, arg):
    return VariablePredicate(
        functor,
        (arg,),
    )


# ------------------------------------------------------------
# 1. Logic result remains unchanged
# ------------------------------------------------------------

engine = LogicReasoner()

engine.add_fact(
    Fact("سقراط", "إنسان")
)

engine.add_variable_rule(
    VariableRule(
        premises=(vp("إنسان", "?x"),),
        conclusion=vp("حي", "?x"),
        rule_id="human-alive",
    )
)

result = engine.infer(
    Fact("سقراط", "حي")
)

check(
    "logic result preserved",
    result.valid
    and result.status == "proven"
    and result.conclusion == "سقراط هو حي",
    repr(result),
)


# ------------------------------------------------------------
# 2. Proof graph can represent the same derivation
# ------------------------------------------------------------

graph = ProofGraph()

base = graph.add_fact(
    Fact("سقراط", "إنسان")
)

inference = graph.add_inference(
    Fact("سقراط", "حي"),
    rule_id="human-alive",
    bindings={"?x": "سقراط"},
    parents=[Fact("سقراط", "إنسان")],
)

check(
    "integration base node",
    base.fact == "سقراط هو إنسان",
)

check(
    "integration inference node",
    inference.fact == "سقراط هو حي"
    and inference.rule_id == "human-alive",
)

check(
    "integration inference parent",
    inference.parents == (base.node_id,),
    repr(inference),
)


# ------------------------------------------------------------
# 3. Multi-hop proof
# ------------------------------------------------------------

graph = ProofGraph()

human = Fact("سقراط", "إنسان")
alive = Fact("سقراط", "حي")
breathes = Fact("سقراط", "يتنفس")

graph.add_fact(human)

alive_node = graph.add_inference(
    alive,
    rule_id="human-alive",
    bindings={"?x": "سقراط"},
    parents=[human],
)

breath_node = graph.add_inference(
    breathes,
    rule_id="alive-breathes",
    bindings={"?x": "سقراط"},
    parents=[alive],
)

ancestors = graph.ancestors(breath_node.node_id)

check(
    "multi-hop proof reaches base",
    ancestors == {
        graph.fact_id(human),
        alive_node.node_id,
        breath_node.node_id,
    },
    repr(ancestors),
)


# ------------------------------------------------------------
# 4. Duplicate derivation remains deterministic
# ------------------------------------------------------------

first = graph.add_inference(
    breathes,
    rule_id="alive-breathes",
    bindings={"?x": "سقراط"},
    parents=[alive],
)

second = graph.add_inference(
    breathes,
    rule_id="alive-breathes",
    bindings={"?x": "سقراط"},
    parents=[alive],
)

check(
    "duplicate proof node deterministic",
    first.node_id == second.node_id
    and first == second,
)


# ------------------------------------------------------------
# 5. Graph lookup
# ------------------------------------------------------------

found = graph.get_fact_nodes(
    "سقراط هو يتنفس"
)

check(
    "derived fact lookup",
    any(
        node.kind == "inference"
        for node in found
    ),
    repr(found),
)


# ------------------------------------------------------------
# 6. FormalReasoner remains compatible
# ------------------------------------------------------------

formal = FormalReasoner()

formal_result = formal.reason(
    "هل سقراط حي؟",
    context={
        "facts": [
            Fact("سقراط", "إنسان")
        ],
        "variable_rules": [
            VariableRule(
                premises=(vp("إنسان", "?x"),),
                conclusion=vp("حي", "?x"),
                rule_id="human-alive",
            )
        ],
        "goal": Fact("سقراط", "حي"),
    },
)

check(
    "FormalReasoner compatibility",
    formal_result.valid
    and formal_result.status == "proven",
    repr(formal_result),
)


print("=" * 65)
print(
    f"PROOF INTEGRATION: "
    f"{PASS} PASS / {FAIL} FAIL"
)
print("=" * 65)

raise SystemExit(1 if FAIL else 0)
