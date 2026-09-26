# -*- coding: utf-8 -*-
"""
MiniChat v3 — Pipeline

خط تنفيذ مركزي.

يدعم حاليًا:
- Tools
- Knowledge Providers

ولا يزال:
- Understanding خارج الـPipeline
- Planning خارج الـPipeline
- Reasoning غير مدمج
- LLM غير مدمج
- Verification غير مدمج
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from core.types import (
    Decision,
    KnowledgeResult,
    Result,
    Status,
    TaskPlan,
    ToolResult,
)
from core.policies import EvidencePolicy
from generation.rag import EvidenceContextBuilder


class Pipeline:
    """
    خط تنفيذ موحد.

    المكونات تسجل بأسماء مستقرة، مثل:
        math
        general
        memory
        llm
    """

    def __init__(self) -> None:
        self._components: Dict[str, Any] = {}
        self.evidence_policy = EvidencePolicy()
        self.rag = EvidenceContextBuilder()
        self.register("rag", self.rag)

    def register(self, name: str, component: Any) -> None:
        if not name:
            raise ValueError("component name cannot be empty")

        if component is None:
            raise ValueError(f"component '{name}' cannot be None")

        self._components[name] = component

    def get(self, name: str) -> Optional[Any]:
        return self._components.get(name)

    def execute(
        self,
        query: str,
        plan: TaskPlan,
        context: Optional[Dict[str, Any]] = None,
    ) -> Result:

        if not isinstance(query, str) or not query.strip():
            return Result(
                status=Status.INVALID_INPUT,
                message="query must be a non-empty string",
            )

        if not isinstance(plan, TaskPlan):
            return Result(
                status=Status.INVALID_INPUT,
                message="plan must be a TaskPlan",
            )

        # ----------------------------------------------------
        # Tool execution
        # ----------------------------------------------------

        if plan.tools:
            tool_results = []

            for tool_name in plan.tools:
                tool = self.get(tool_name)

                if tool is None:
                    return Result(
                        status=Status.UNAVAILABLE,
                        message=f"tool '{tool_name}' is not registered",
                        source=tool_name,
                        metadata={
                            "pipeline": "v3",
                            "stage": "tool",
                        },
                    )

                run = getattr(tool, "run", None)

                if not callable(run):
                    return Result(
                        status=Status.ERROR,
                        message=f"component '{tool_name}' has no callable run()",
                        source=tool_name,
                        metadata={
                            "pipeline": "v3",
                            "stage": "tool",
                        },
                    )

                tool_context = dict(context or {})

                if (
                    tool_name == "math"
                    and isinstance(
                        getattr(plan, "metadata", None), dict
                    )
                    and "math_payload" in plan.metadata
                ):
                    payload = plan.metadata["math_payload"]

                    if payload.get("kind") == "predicate":
                        tool_context["math_predicate"] = {
                            "predicate": payload.get("predicate"),
                            "number": payload.get("number"),
                        }

                try:
                    tool_result = run(query, context=tool_context)
                except Exception as exc:
                    return Result(
                        status=Status.ERROR,
                        message=str(exc),
                        source=tool_name,
                        metadata={
                            "pipeline": "v3",
                            "stage": "tool",
                            "exception": type(exc).__name__,
                        },
                    )

                if not isinstance(tool_result, ToolResult):
                    return Result(
                        status=Status.ERROR,
                        message=(
                            f"tool '{tool_name}' returned "
                            f"{type(tool_result).__name__}, "
                            "expected ToolResult"
                        ),
                        source=tool_name,
                        metadata={
                            "pipeline": "v3",
                            "stage": "tool",
                        },
                    )

                tool_results.append(tool_result)

                if not tool_result.success:
                    return Result(
                        status=Status.EMPTY,
                        value=tool_result,
                        message=tool_result.error,
                        source=tool_name,
                        metadata={
                            "pipeline": "v3",
                            "stage": "tool",
                            "tool_success": False,
                        },
                    )

            # في المرحلة الحالية نستخدم أول نتيجة ناجحة.
            selected = tool_results[0]

            tool_result_payload = Result(
                status=Status.SUCCESS,
                value=selected,
                source=selected.tool,
                confidence=1.0,
                metadata={
                    "pipeline": "v3",
                    "stage": "tool",
                    "tool_success": True,
                },
            )

            # Verification hook: deterministic re-check whenever a
            # verifier is registered.  This is NOT gated on
            # plan.needs_verification anymore: verification is
            # fail-closed — if a verifier exists and refuses to
            # certify the result, SUCCESS is impossible.
            verifier = self.get("verifier")

            if verifier is not None:
                verifier = self.get("verifier")

                verify = getattr(verifier, "verify", None)

                if callable(verify):
                    try:
                        check = verify(
                            str(selected.formatted or ""),
                            evidence=None,
                            context={
                                "stage": "tool",
                                "tool": selected.tool,
                                "query": query,
                                "value": selected.value,
                                "metadata": dict(
                                    getattr(selected, "metadata", {}) or {}
                                ),
                            },
                        )
                    except Exception as exc:
                        check = None
                        tool_result_payload.metadata[
                            "verification_error"
                        ] = f"{type(exc).__name__}: {exc}"

                    if check is None:
                        verified_flag = False
                        issues = ["verifier_returned_nothing"]
                    else:
                        check_meta = getattr(check, "metadata", {}) or {}
                        verified_flag = bool(
                            check_meta.get("verified", False)
                        )
                        issues = list(check_meta.get("issues", []))

                    tool_result_payload.metadata["verification"] = {
                        "verified": verified_flag,
                        "issues": issues,
                    }

                    if not verified_flag:
                        # لا نتجاهل فشل التحقق بصمت.
                        tool_result_payload.status = Status.ERROR
                        tool_result_payload.message = (
                            "tool result failed verification"
                        )
            else:
                # A tool result without any available verification
                # cannot be certified; report it as unverified but
                # keep the raw value for inspection.
                tool_result_payload.metadata["verification"] = {
                    "verified": False,
                    "issues": ["no_verifier_registered"],
                }
                tool_result_payload.status = Status.EMPTY
                tool_result_payload.message = "unverified_tool_result"

            return tool_result_payload

        # ----------------------------------------------------
        # Reasoning execution
        # ----------------------------------------------------

        if plan.needs_reasoning:
            reasoner = self.get("reasoner")

            if reasoner is None:
                return Result(
                    status=Status.UNAVAILABLE,
                    message="component 'reasoner' is not registered",
                    source="reasoner",
                    metadata={
                        "pipeline": "v3",
                        "stage": "reasoning",
                    },
                )

            reason = getattr(reasoner, "reason", None)

            if not callable(reason):
                return Result(
                    status=Status.ERROR,
                    message="component 'reasoner' has no callable reason()",
                    source="reasoner",
                    metadata={
                        "pipeline": "v3",
                        "stage": "reasoning",
                    },
                )

            reasoning_context = dict(context or {})

            payload = getattr(plan, "metadata", {}).get(
                "reasoning_payload"
            )

            if isinstance(payload, dict):
                # The planner forwards the compiled canonical form
                # verbatim; the pipeline never interprets it.
                reasoning_context.setdefault(
                    "facts", list(payload.get("facts", []))
                )
                reasoning_context.setdefault(
                    "variable_rules",
                    list(payload.get("variable_rules", [])),
                )
                reasoning_context.setdefault(
                    "goal", payload.get("goal")
                )

            try:
                reasoning_result = reason(
                    query,
                    context=reasoning_context,
                )
            except Exception as exc:
                return Result(
                    status=Status.ERROR,
                    message=str(exc),
                    source="reasoner",
                    metadata={
                        "pipeline": "v3",
                        "stage": "reasoning",
                        "exception": type(exc).__name__,
                    },
                )

            reasoning_metadata = {
                "pipeline": "v3",
                "stage": "reasoning",
                "reasoning_valid": reasoning_result.valid,
                "reasoning_status": reasoning_result.metadata.get("status"),
            }

            for forwarded in ("method", "goal_bindings"):
                if forwarded in reasoning_result.metadata:
                    reasoning_metadata[forwarded] = (
                        reasoning_result.metadata[forwarded]
                    )

            proof_graph = reasoning_result.metadata.get("proof_graph")

            # ------------------------------------------------------------
            # Fail-closed contract:
            #   SUCCESS requires ALL of:
            #     * engine validity with an explicit conclusion
            #     * a present, non-empty proof graph whose root
            #       matches that conclusion
            #     * verifier certification (well-formedness,
            #       acyclicity, provenance coverage)
            #   Anything else — missing/empty/cyclic/unverified
            #   proof — must NOT become SUCCESS.
            # ------------------------------------------------------------

            conclusion = reasoning_result.conclusion

            verification_issues: List[str] = []

            if not reasoning_result.valid:
                verification_issues.append("engine_reported_invalid")

            if conclusion is None or not str(conclusion).strip():
                verification_issues.append("missing_conclusion")

            if proof_graph is None:
                verification_issues.append("missing_proof_graph")
            else:
                nodes = proof_graph.get("nodes", {})

                if not nodes:
                    verification_issues.append("empty_proof_graph")

                roots = [
                    node
                    for node in nodes.values()
                    if node.get("kind") == "inference"
                ]

                if conclusion is not None and roots:
                    if not any(
                        node.get("fact") == str(conclusion)
                        for node in roots
                    ):
                        verification_issues.append(
                            "conclusion_not_root_of_proof"
                        )

            verifier = self.get("verifier")

            verified = False

            if verifier is None:
                verification_issues.append("no_verifier_registered")
            else:
                verify = getattr(verifier, "verify", None)

                if not callable(verify):
                    verification_issues.append("verifier_lacks_verify")
                else:
                    try:
                        check = verify(
                            str(conclusion or ""),
                            evidence=None,
                            context={
                                "stage": "reasoning",
                                "query": query,
                                "proof_graph": proof_graph,
                                "conclusion": (
                                    str(conclusion)
                                    if conclusion is not None
                                    else ""
                                ),
                                "premises": list(
                                    reasoning_result.premises
                                ),
                                "provenance": (
                                    reasoning_result.metadata.get(
                                        "proof_provenance"
                                    )
                                ),
                            },
                        )
                        check_meta = (
                            getattr(check, "metadata", {}) or {}
                        )
                        verified = bool(check_meta.get("verified", False))
                        verification_issues.extend(
                            check_meta.get("issues", [])
                        )
                    except Exception as exc:
                        verified = False
                        verification_issues.append(
                            f"verification_error:{type(exc).__name__}"
                        )

            if not verified:
                verification_issues.append("not_certified_by_verifier")

            reasoning_metadata["proof_verified"] = bool(
                verified
                and reasoning_result.valid
                and conclusion is not None
                and proof_graph is not None
                and proof_graph.get("nodes", {})
                and not verification_issues
            )
            reasoning_metadata["verification_issues"] = sorted(
                set(verification_issues)
            )

            if reasoning_metadata["proof_verified"]:
                return Result(
                    status=Status.SUCCESS,
                    value=conclusion,
                    source="reasoner",
                    confidence=(
                        reasoning_result.confidence
                        if reasoning_result.confidence is not None
                        else 1.0
                    ),
                    metadata=reasoning_metadata,
                )

            if proof_graph is not None:
                reasoning_metadata["proof_node_count"] = len(
                    proof_graph.get("nodes", {})
                )

            # Unproven goal vs failed verification: distinguish so
            # callers can see WHY there is no success.
            unproven_only = set(verification_issues) <= {
                "missing_conclusion",
                "engine_reported_invalid",
            }

            return Result(
                status=Status.EMPTY if unproven_only else Status.ERROR,
                value=(
                    conclusion
                    if conclusion is not None
                    else reasoning_result
                ),
                source="reasoner",
                message=(
                    "not_proven"
                    if unproven_only
                    else "reasoning_failed_verification"
                ),
                confidence=reasoning_result.confidence,
                metadata=reasoning_metadata,
            )

        # ----------------------------------------------------
        # Knowledge Provider execution
        # ----------------------------------------------------

        if plan.providers:
            provider_results = []

            for provider_name in plan.providers:
                provider = self.get(provider_name)

                if provider is None:
                    return Result(
                        status=Status.UNAVAILABLE,
                        message=f"provider '{provider_name}' is not registered",
                        source=provider_name,
                        metadata={
                            "pipeline": "v3",
                            "stage": "knowledge",
                        },
                    )

                search = getattr(provider, "search", None)

                if not callable(search):
                    return Result(
                        status=Status.ERROR,
                        message=(
                            f"component '{provider_name}' has no "
                            "callable search()"
                        ),
                        source=provider_name,
                        metadata={
                            "pipeline": "v3",
                            "stage": "knowledge",
                        },
                    )

                try:
                    knowledge_result = search(
                        query,
                        context=context,
                        limit=5,
                    )
                except Exception as exc:
                    return Result(
                        status=Status.ERROR,
                        message=str(exc),
                        source=provider_name,
                        metadata={
                            "pipeline": "v3",
                            "stage": "knowledge",
                            "exception": type(exc).__name__,
                        },
                    )

                if not isinstance(knowledge_result, KnowledgeResult):
                    return Result(
                        status=Status.ERROR,
                        message=(
                            f"provider '{provider_name}' returned "
                            f"{type(knowledge_result).__name__}, "
                            "expected KnowledgeResult"
                        ),
                        source=provider_name,
                        metadata={
                            "pipeline": "v3",
                            "stage": "knowledge",
                        },
                    )

                provider_results.append(
                    (provider_name, knowledge_result)
                )

            # نستخدم أول Provider حاليًا.
            provider_name, selected = provider_results[0]

            if not selected.found:
                # Knowledge غير موجودة؛ لا نتوقف إذا كانت الخطة
                # تطلب LLM. ننتقل إلى مسار التوليد كـfallback.
                if plan.needs_llm:
                    llm = self.get("llm")

                    if llm is None:
                        return Result(
                            status=Status.UNAVAILABLE,
                            value=selected,
                            source="llm",
                            metadata={
                                "pipeline": "v3",
                                "stage": "llm",
                                "knowledge_found": False,
                                "reason": "llm_not_registered",
                            },
                        )

                    generate = getattr(llm, "generate", None)

                    if not callable(generate):
                        return Result(
                            status=Status.ERROR,
                            value=selected,
                            source="llm",
                            metadata={
                                "pipeline": "v3",
                                "stage": "llm",
                                "knowledge_found": False,
                                "reason": "llm_has_no_generate",
                            },
                        )

                    rag = self.get("rag")

                    # لا توجد أدلة؛ لذلك لا نرسل Prompt RAG فارغًا.
                    prompt = query
                    rag_used = False

                    try:
                        llm_result = generate(
                            prompt=prompt,
                            system=(
                                "أنت مساعد عربي دقيق وواضح. "
                                "أجب عن السؤال مباشرة وباختصار. "
                                "لا تختلق معلومات ولا تضف تفاصيل غير لازمة."
                            ),
                            context=context,
                        )
                    except Exception as exc:
                        return Result(
                            status=Status.ERROR,
                            value=selected,
                            source="llm",
                            message=str(exc),
                            metadata={
                                "pipeline": "v3",
                                "stage": "llm",
                                "knowledge_found": False,
                                "rag_used": rag_used,
                                "exception": type(exc).__name__,
                            },
                        )

                    if llm_result.status != Status.SUCCESS:
                        return Result(
                            status=llm_result.status,
                            value=llm_result,
                            source="llm",
                            message=llm_result.metadata.get("reason"),
                            metadata={
                                "pipeline": "v3",
                                "stage": "llm",
                                "knowledge_found": False,
                                "rag_used": rag_used,
                                "llm_success": False,
                                "decision": Decision.LLM,
                            },
                        )

                    return Result(
                        status=Status.SUCCESS,
                        value=llm_result.text,
                        source="llm",
                        metadata={
                            "pipeline": "v3",
                            "stage": "llm",
                            "knowledge_found": False,
                            "evidence_count": 0,
                            "rag_used": rag_used,
                            "llm_success": True,
                            "model": llm_result.model,
                            "latency_ms": llm_result.latency_ms,
                        },
                    )

                return Result(
                    status=Status.EMPTY,
                    value=selected,
                    source=provider_name,
                    metadata={
                        "pipeline": "v3",
                        "stage": "knowledge",
                        "knowledge_found": False,
                    },
                )

            top_score = None

            if selected.evidence:
                top_score = selected.evidence[0].score

            direct_answer = self.evidence_policy.direct_answer(
                selected.evidence
            )

            # إذا كان لدينا دليل واحد قوي، فهو جواب نهائي.
            # لا حاجة لاستدعاء LLM أو أي طبقة توليد.
            if direct_answer:
                return Result(
                    status=Status.SUCCESS,
                    value=selected.evidence[0].content.strip(),
                    source=provider_name,
                    confidence=(
                        selected.evidence[0].score
                        if selected.evidence[0].score is not None
                        else selected.evidence[0].reliability
                    ),
                    metadata={
                        "pipeline": "v3",
                        "stage": "knowledge",
                        "knowledge_found": True,
                        "evidence_count": len(selected.evidence),
                        "top_score": top_score,
                        "direct_answer": True,
                        "terminal": True,
                        "decision": Decision.DIRECT,
                    },
                )

            # الدليل موجود لكنه غير قوي بما يكفي للإجابة المباشرة.
            # نكمل إلى مسار LLM/RAG بدل إيقاف الـPipeline.
            if plan.needs_llm:
                pass
            else:
                return Result(
                    status=Status.SUCCESS,
                    value=selected,
                    source=provider_name,
                    metadata={
                        "pipeline": "v3",
                        "stage": "knowledge",
                        "knowledge_found": True,
                        "evidence_count": len(selected.evidence),
                        "top_score": top_score,
                        "direct_answer": False,
                        "terminal": False,
                    },
                )

        # ----------------------------------------------------
        # LLM / RAG execution
        # ----------------------------------------------------

        if plan.needs_llm:
            llm = self.get("llm")

            if llm is None:
                return Result(
                    status=Status.UNAVAILABLE,
                    message="component 'llm' is not registered",
                    source="llm",
                    metadata={
                        "pipeline": "v3",
                        "stage": "llm",
                    },
                )

            rag = self.get("rag")

            evidence = []

            # إذا كان لدينا Knowledge Provider، نعيد استخدامه
            # لبناء أدلة مقيدة للـLLM.
            if plan.providers:
                provider_name = plan.providers[0]
                provider = self.get(provider_name)

                if provider is not None:
                    search = getattr(provider, "search", None)

                    if callable(search):
                        try:
                            knowledge_result = search(
                                query,
                                context=context,
                                limit=5,
                            )

                            if isinstance(
                                knowledge_result,
                                KnowledgeResult,
                            ):
                                evidence = knowledge_result.evidence

                        except Exception:
                            evidence = []

            # تحديد مسار التنفيذ قبل استدعاء الـLLM.
            decision = (
                Decision.RAG
                if evidence and rag is not None
                else Decision.LLM
            )

            # بناء Prompt مقيد بالأدلة إذا كان RAG متاحًا.
            if rag is not None and evidence:
                build_prompt = getattr(rag, "build_prompt", None)

                if callable(build_prompt):
                    prompt = build_prompt(
                        query,
                        evidence,
                    )
                else:
                    prompt = query
            else:
                prompt = query

            generate = getattr(llm, "generate", None)

            if not callable(generate):
                return Result(
                    status=Status.ERROR,
                    message="component 'llm' has no callable generate()",
                    source="llm",
                    metadata={
                        "pipeline": "v3",
                        "stage": "llm",
                    },
                )

            try:
                llm_result = generate(
                    prompt=prompt,
                    system=(
                        "أنت مولد إجابات عربي دقيق. "
                        "إذا وُجدت أدلة في الطلب، "
                        "استخدم الأدلة فقط ولا تضف معلومات خارجها. "
                        "إذا لم تكفِ الأدلة، قل بوضوح إن المعلومات "
                        "المتاحة لا تكفي للإجابة."
                    ),
                    context=context,
                )
            except Exception as exc:
                return Result(
                    status=Status.ERROR,
                    message=str(exc),
                    source="llm",
                    metadata={
                        "pipeline": "v3",
                        "stage": "llm",
                        "exception": type(exc).__name__,
                    },
                )

            if llm_result.status != Status.SUCCESS:
                return Result(
                    status=llm_result.status,
                    value=llm_result,
                    message=llm_result.metadata.get("reason"),
                    source="llm",
                    metadata={
                        "pipeline": "v3",
                        "stage": "llm",
                        "llm_success": False,
                        "decision": decision,
                    },
                )

            return Result(
                status=Status.SUCCESS,
                value=llm_result.text,
                source="llm",
                metadata={
                    "pipeline": "v3",
                    "stage": "llm",
                    "llm_success": True,
                    "knowledge_found": bool(evidence),
                    "evidence_count": len(evidence),
                    "rag_used": bool(evidence and rag is not None),
                    "decision": decision,
                    "model": llm_result.model,
                    "latency_ms": llm_result.latency_ms,
                },
            )

        # ----------------------------------------------------
        # No executable component yet
        # ----------------------------------------------------

        return Result(
            status=Status.EMPTY,
            value=None,
            metadata={
                "pipeline": "v3",
                "executed": False,
                "reason": "no_executable_stage",
            },
        )
