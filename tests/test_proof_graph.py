# -*- coding: utf-8 -*-
"""Proof graph hardening."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from reasoning.model import Fact
from reasoning.proof import ProofGraph


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


socrates = Fact("سقراط", "إنسان")
alive = Fact("سقراط", "حي")
breathes = Fact("سقراط", "يتنفس")


graph = ProofGraph()

human_node = graph.add_fact(socrates)

check(
    "base fact node created",
    human_node.kind == "fact",
)

check(
    "base fact deterministic id",
    human_node.node_id == "fact:سقراط::إنسان",
)


alive_node = graph.add_inference(
    alive,
    rule_id="human-alive",
    bindings={"?x": "سقراط"},
    parents=[socrates],
)

check(
    "inference node created",
    alive_node.kind == "inference",
)

check(
    "inference records rule",
    alive_node.rule_id == "human-alive",
)

check(
    "inference records binding",
    alive_node.bindings == (("?x", "سقراط"),),
)

check(
    "inference points to parent",
    alive_node.parents == ("fact:سقراط::إنسان",),
)


breathes_node = graph.add_inference(
    breathes,
    rule_id="alive-breathes",
    bindings={"?x": "سقراط"},
    parents=[alive],
)

check(
    "multi-hop proof node",
    breathes_node.kind == "inference",
)

ancestors = graph.ancestors(
    breathes_node.node_id
)

check(
    "ancestor traversal",
    ancestors == {
        breathes_node.node_id,
        alive_node.node_id,
        human_node.node_id,
    },
    repr(ancestors),
)


same = graph.add_inference(
    breathes,
    rule_id="alive-breathes",
    bindings={"?x": "سقراط"},
    parents=[alive],
)

check(
    "duplicate inference is deterministic",
    same.node_id == breathes_node.node_id
    and len(graph.nodes) == 3,
)


fact_nodes = graph.get_fact_nodes(alive)

check(
    "fact lookup finds inference",
    len(fact_nodes) == 1
    and fact_nodes[0].node_id == alive_node.node_id,
)


serialized = graph.serialize()

check(
    "serialization has nodes",
    len(serialized["nodes"]) == 3,
)

check(
    "serialization is deterministic",
    serialized == graph.serialize(),
)


# Contradiction marker.

not_alive = Fact(
    "سقراط",
    "حي",
    negated=True,
)

contradiction = graph.add_fact(
    not_alive,
    kind="contradiction",
)

check(
    "contradiction node supported",
    contradiction.kind == "contradiction",
)


print("=" * 65)
print(
    f"PROOF GRAPH HARDENING: "
    f"{PASS} PASS / {FAIL} FAIL"
)
print("=" * 65)

raise SystemExit(1 if FAIL else 0)
