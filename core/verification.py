# -*- coding: utf-8 -*-
"""
MiniChat v3 — Verification Layer

طبقة تحقق deterministic تعمل بعد الأدوات والاستدلال والمعرفة.

المسؤوليات:
1. إعادة تنفيذ نتائج الأدوات (math re-check) والتأكد من التطابق.
2. التحقق من سلامة بنية البرهان (proof graph well-formedness).
3. كشف المطالبات غير المدعومة في نص LLM عند توفر أدلة (evidence coverage).
4. عدم تحويل أي فشل إلى نجاح صامت: كل فحص يعيد سببًا صريحًا.

لا تستخدم هذه الطبقة LLM إطلاقًا.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, Iterable, List, Optional

from core.protocols import Verifier
from core.types import Evidence, Result, Status, VerificationResult


class DefaultVerifier(Verifier):
    """Deterministic verifier for tool/reasoning/knowledge outputs."""

    name = "default-verifier"

    # ------------------------------------------------------------
    # math re-check
    # ------------------------------------------------------------

    _MATH_EXPR = re.compile(
        r"[-+]?\d+(?:\.\d+)?"
        r"(?:\s*[+\-*/×÷^%]\s*[-+]?\d+(?:\.\d+)?)+"
    )

    def verify_math_result(
        self,
        query: str,
        value: Any,
    ) -> VerificationResult:
        """
        Re-evaluate the arithmetic expression found in the query and
        compare it with the tool result.  A mismatch is an ERROR, not
        a silent pass.
        """

        from math_engine import MathEngine

        match = self._MATH_EXPR.search(query or "")

        if match is None:
            return VerificationResult(
                verified=False,
                checks=["math_recheck"],
                issues=["no_math_expression_found_for_recheck"],
            )

        expression = (
            match.group(0)
            .replace("×", "*")
            .replace("÷", "/")
        )

        try:
            expected = MathEngine.evaluate(expression)
        except Exception as exc:  # pragma: no cover - defensive
            return VerificationResult(
                verified=False,
                checks=["math_recheck"],
                issues=[f"recheck_error:{type(exc).__name__}"],
            )

        if expected is None:
            return VerificationResult(
                verified=False,
                checks=["math_recheck"],
                issues=["recheck_unsupported_expression"],
            )

        try:
            actual = float(value)
        except (TypeError, ValueError):
            return VerificationResult(
                verified=False,
                checks=["math_recheck"],
                issues=["tool_result_not_numeric"],
            )

        if abs(actual - float(expected)) < 1e-9:
            return VerificationResult(
                verified=True,
                checks=["math_recheck"],
                confidence=1.0,
                metadata={
                    "expression": expression,
                    "expected": expected,
                    "actual": actual,
                },
            )

        return VerificationResult(
            verified=False,
            checks=["math_recheck"],
            issues=["tool_result_mismatch"],
            corrections=[str(expected)],
            metadata={
                "expression": expression,
                "expected": expected,
                "actual": actual,
            },
        )

    # ------------------------------------------------------------
    # proof structure check
    # ------------------------------------------------------------

    @staticmethod
    def verify_proof_structure(
        proof_graph: Any,
    ) -> VerificationResult:

        if isinstance(proof_graph, str):
            try:
                proof_graph = json.loads(proof_graph)
            except json.JSONDecodeError as exc:
                return VerificationResult(
                    verified=False,
                    checks=["proof_structure"],
                    issues=[f"proof_graph_invalid_json:{exc}"],
                )

        if not isinstance(proof_graph, dict):
            return VerificationResult(
                verified=False,
                checks=["proof_structure"],
                issues=["proof_graph_missing_or_wrong_type"],
            )

        nodes = proof_graph.get("nodes")

        if not isinstance(nodes, dict):
            return VerificationResult(
                verified=False,
                checks=["proof_structure"],
                issues=["proof_graph_nodes_missing"],
            )

        issues: List[str] = []

        for node_id, node in nodes.items():
            if not isinstance(node, dict):
                issues.append(f"node_not_dict:{node_id}")
                continue

            if node.get("kind") not in {
                "fact",
                "inference",
                "assumption",
                "contradiction",
            }:
                issues.append(f"bad_kind:{node_id}")

            for parent in node.get("parents", []) or []:
                if parent not in nodes:
                    issues.append(
                        f"dangling_parent:{node_id}->{parent}"
                    )

        if issues:
            return VerificationResult(
                verified=False,
                checks=["proof_structure"],
                issues=sorted(issues),
            )

        return VerificationResult(
            verified=True,
            checks=["proof_structure"],
            confidence=1.0,
            metadata={"node_count": len(nodes)},
        )

    # ------------------------------------------------------------
    # evidence coverage for generated text
    # ------------------------------------------------------------

    # Note: Arabic tanween/hamza writing variants (وفقًا / وفقاً / وفقا)
    # are normalized before matching so all common forms are caught.
    _SOURCE_CLAIM = re.compile(
        r"(وفق\s*[ا]?(?:\s*[للي]|)|بحسب\s+|من\s+مصدر|"
        r"حسب\s+مصدر|استناد(?:ا)?\s+إلى|"
        r"source[:：]|according\s+to)",
        re.IGNORECASE,
    )

    @staticmethod
    def _normalize_claims(text: str) -> str:
        text = text or ""
        # strip harakat (fathatan/damma/kasra/fatha/damma/kasra/sukun/shadda)
        for mark in ("\u064b", "\u064c", "\u064d", "\u064e", "\u064f", "\u0650", "\u0652", "\u0651"):
            text = text.replace(mark, "")
        return text.replace("\u0649", "\u064a")

    def verify_generated_answer(
        self,
        answer: str,
        evidence: Optional[Iterable[Evidence]] = None,
    ) -> VerificationResult:

        checks: List[str] = ["non_empty_answer"]
        issues: List[str] = []

        if not isinstance(answer, str) or not answer.strip():
            return VerificationResult(
                verified=False,
                checks=checks,
                issues=["empty_answer"],
            )

        items = [
            item
            for item in (evidence or [])
            if isinstance(item, Evidence)
        ]

        checks.append("evidence_coverage")

        if items:
            evidence_words = set()

            for item in items:
                evidence_words.update(
                    re.findall(r"\w+", item.content.lower())
                )

            answer_words = {
                word
                for word in re.findall(r"\w+", answer.lower())
                if len(word) > 3
            }

            if answer_words:
                coverage = len(
                    answer_words & {
                        word for word in evidence_words if len(word) > 3
                    }
                ) / len(answer_words)

                if coverage < 0.15:
                    issues.append(
                        f"low_evidence_coverage:{round(coverage, 3)}"
                    )
        else:
            # No evidence supplied: any explicit source claim inside
            # the generated text is unverifiable and must be flagged.
            if self._SOURCE_CLAIM.search(self._normalize_claims(answer)):
                issues.append("unsupported_source_claim")

        return VerificationResult(
            verified=not issues,
            checks=checks,
            issues=issues,
            metadata={"evidence_count": len(items)},
        )

    # ------------------------------------------------------------
    # generic Verifier contract
    # ------------------------------------------------------------

    def verify(
        self,
        answer: str,
        evidence: Optional[list[Evidence]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Result:

        context = context or {}
        stage = str(context.get("stage", ""))
        results: List[VerificationResult] = []

        if stage == "tool" and context.get("tool") == "math":
            results.append(
                self.verify_math_result(
                    str(context.get("query", "")),
                    context.get("value"),
                )
            )

        proof_graph = context.get("proof_graph")

        if proof_graph is not None:
            results.append(self.verify_proof_structure(proof_graph))

        if stage == "llm" or (not results and answer):
            results.append(
                self.verify_generated_answer(answer, evidence)
            )

        if not results:
            # An answer with no evidence and no structured context is
            # NOT verified.  Returning SUCCESS here would be a silent
            # pass, which this layer explicitly forbids.
            return Result(
                status=Status.EMPTY,
                message="nothing_to_verify",
                source=self.name,
                metadata={"verified": False},
            )

        verified = all(item.verified for item in results)

        combined = VerificationResult(
            verified=verified,
            checks=[
                check
                for item in results
                for check in item.checks
            ],
            issues=[
                issue
                for item in results
                for issue in item.issues
            ],
            corrections=[
                correction
                for item in results
                for correction in item.corrections
            ],
            metadata={
                "verifications": [
                    {
                        "verified": item.verified,
                        "checks": item.checks,
                        "issues": item.issues,
                    }
                    for item in results
                ]
            },
        )

        return Result(
            status=Status.SUCCESS if verified else Status.ERROR,
            value=combined,
            source=self.name,
            confidence=1.0 if verified else 0.0,
            metadata={
                "verified": verified,
                "issues": combined.issues,
            },
        )
