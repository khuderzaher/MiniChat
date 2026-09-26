# -*- coding: utf-8 -*-
"""Deterministic proof graph for MiniChat."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class ProofNode:
    """
    One node in a proof graph.

    kind:
        fact       -> base/known fact
        inference  -> fact derived from premises
        assumption -> explicitly supplied assumption
        contradiction -> conflicting derivation marker
    """

    node_id: str
    fact: str
    kind: str = "fact"
    rule_id: Optional[str] = None
    source: Optional[str] = None
    bindings: tuple[tuple[str, str], ...] = ()
    parents: tuple[str, ...] = ()

    def __post_init__(self):
        if not self.node_id:
            raise ValueError("node_id must not be empty")

        if not self.fact:
            raise ValueError("fact must not be empty")

        allowed = {
            "fact",
            "inference",
            "assumption",
            "contradiction",
        }

        if self.kind not in allowed:
            raise ValueError(
                f"unsupported proof node kind: {self.kind}"
            )

    @property
    def key(self) -> str:
        return self.node_id


@dataclass
class ProofGraph:
    """
    Deterministic directed acyclic proof graph.

    The graph deliberately stores nodes by ID and keeps insertion
    independent from Python set ordering.
    """

    nodes: dict[str, ProofNode] = field(default_factory=dict)
    roots: list[str] = field(default_factory=list)

    @staticmethod
    def fact_id(fact: object) -> str:
        key = getattr(fact, "key", None)

        if isinstance(key, str) and key:
            return f"fact:{key}"

        return f"fact:{str(fact)}"

    @staticmethod
    def inference_id(
        fact: object,
        rule_id: str,
        bindings: dict[str, str],
        parents: list[str],
    ) -> str:
        fact_key = getattr(fact, "key", str(fact))

        binding_text = ",".join(
            f"{key}={value}"
            for key, value in sorted(bindings.items())
        )

        parent_text = ",".join(sorted(parents))

        return (
            f"inference:{fact_key}"
            f"|rule={rule_id}"
            f"|bindings={binding_text}"
            f"|parents={parent_text}"
        )

    def add_fact(
        self,
        fact: object,
        *,
        kind: str = "fact",
        source: Optional[str] = None,
    ) -> ProofNode:
        node_id = self.fact_id(fact)

        existing = self.nodes.get(node_id)

        if existing is not None:
            return existing

        node = ProofNode(
            node_id=node_id,
            fact=str(fact),
            kind=kind,
            source=source,
        )

        self.nodes[node_id] = node

        if node_id not in self.roots:
            self.roots.append(node_id)

        return node

    def _resolve_parent_node(self, parent: object) -> ProofNode:
        """
        Resolve a parent Fact to an existing proof node.

        If the fact was itself derived, use the deterministic
        inference node instead of creating a duplicate base-fact node.

        If no proof node exists yet, create a genuine base-fact node.
        """

        fact_text = str(parent)

        candidates = sorted(
            (
                node
                for node in self.nodes.values()
                if node.fact == fact_text
            ),
            key=lambda node: (
                0 if node.kind == "inference" else 1,
                node.node_id,
            ),
        )

        if candidates:
            return candidates[0]

        return self.add_fact(parent)

    def add_inference(
        self,
        fact: object,
        *,
        rule_id: str,
        bindings: dict[str, str],
        parents: list[object],
        source: Optional[str] = None,
    ) -> ProofNode:
        parent_nodes = [
            self._resolve_parent_node(parent)
            for parent in parents
        ]

        parent_ids = [
            node.node_id
            for node in parent_nodes
        ]

        node_id = self.inference_id(
            fact,
            rule_id,
            bindings,
            parent_ids,
        )

        existing = self.nodes.get(node_id)

        if existing is not None:
            return existing

        node = ProofNode(
            node_id=node_id,
            fact=str(fact),
            kind="inference",
            rule_id=rule_id,
            source=source,
            bindings=tuple(
                sorted(bindings.items())
            ),
            parents=tuple(sorted(parent_ids)),
        )

        self.nodes[node_id] = node

        return node

    def get_fact_nodes(self, fact: object) -> list[ProofNode]:
        target = str(fact)

        return sorted(
            (
                node
                for node in self.nodes.values()
                if node.fact == target
            ),
            key=lambda node: node.node_id,
        )

    def ancestors(self, node_id: str) -> set[str]:
        visited: set[str] = set()

        def visit(current: str):
            if current in visited:
                return

            visited.add(current)

            node = self.nodes.get(current)

            if node is None:
                return

            for parent in sorted(node.parents):
                visit(parent)

        visit(node_id)
        return visited

    def serialize(self) -> dict:
        return {
            "roots": sorted(self.roots),
            "nodes": {
                node_id: {
                    "fact": node.fact,
                    "kind": node.kind,
                    "rule_id": node.rule_id,
                    "source": node.source,
                    "bindings": dict(node.bindings),
                    "parents": list(node.parents),
                }
                for node_id, node in sorted(
                    self.nodes.items()
                )
            },
        }


def proof_tree(graph: "ProofGraph", node_id: str, _seen=None) -> dict:
    """
    Render a deterministic nested proof tree for one node.

    Each level exposes:
        goal fact -> rule -> bindings -> premises (recursively)

    Cycle safety: nodes already on the current traversal path are
    rendered once with ``"cyclic": true`` instead of recursing.
    """

    if _seen is None:
        _seen = set()

    node = graph.nodes.get(node_id)

    if node is None:
        return {"node_id": node_id, "missing": True}

    if node_id in _seen:
        return {
            "node_id": node_id,
            "fact": node.fact,
            "kind": node.kind,
            "cyclic": True,
        }

    path = _seen | {node_id}

    children = [
        proof_tree(graph, parent, path)
        for parent in sorted(node.parents)
    ]

    tree = {
        "node_id": node.node_id,
        "fact": node.fact,
        "kind": node.kind,
    }

    if node.rule_id is not None:
        tree["rule_id"] = node.rule_id

    if node.bindings:
        tree["bindings"] = dict(node.bindings)

    if node.source is not None:
        tree["source"] = node.source

    if children:
        tree["premises"] = children

    return tree


def explain_proof(graph: "ProofGraph", node_id: str) -> list[str]:
    """
    Flatten a proof tree into ordered human-readable explanation
    lines (deterministic).
    """

    lines: list[str] = []

    def visit(current: str, depth: int, seen: set):
        node = graph.nodes.get(current)

        if node is None:
            return

        if current in seen:
            return

        path = seen | {current}
        prefix = "  " * depth

        if node.kind == "inference":
            rule = node.rule_id or "?"
            bindings = ", ".join(
                f"{k}={v}" for k, v in sorted(node.bindings)
            )
            suffix = f" [{bindings}]" if bindings else ""
            lines.append(
                f"{prefix}⊢ {node.fact}   ({rule}){suffix}"
            )
        else:
            label = {
                "fact": "given",
                "assumption": "assumption",
                "contradiction": "contradiction",
            }.get(node.kind, node.kind)
            lines.append(f"{prefix}• {node.fact}   ({label})")

        for parent in sorted(node.parents):
            visit(parent, depth + 1, path)

    visit(node_id, 0, set())
    return lines
