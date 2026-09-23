# -*- coding: utf-8 -*-
"""
MiniChat v3 — Orchestrator

المنسق المركزي للنسخة v3.

مسؤوليته الحالية:
    Query
      ↓
    Understanding
      ↓
    Planning
      ↓
    Pipeline

لا يحتوي على:
- منطق معرفة
- منطق رياضيات
- منطق استدلال
- استدعاء Qwen
- تخزين ذاكرة

هذه مسؤوليات مكونات أخرى.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from core.pipeline import Pipeline
from core.planner import Planner
from core.types import Result, Status
from understanding.service import UnderstandingService


class Orchestrator:
    """
    المنسق المركزي.

    يجمع المكونات الموجودة دون أن يمتلك منطقها الداخلي.
    """

    name = "orchestrator"

    def __init__(
        self,
        understanding: Optional[UnderstandingService] = None,
        planner: Optional[Planner] = None,
        pipeline: Optional[Pipeline] = None,
    ) -> None:

        self.understanding = understanding or UnderstandingService()
        self.planner = planner or Planner()
        self.pipeline = pipeline or Pipeline()

    def handle(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Result:

        if not isinstance(query, str) or not query.strip():
            return Result(
                status=Status.INVALID_INPUT,
                message="query must be a non-empty string",
            )

        text = query.strip()

        # -----------------------------------------------
        # 1) Understanding
        # -----------------------------------------------

        try:
            analysis = self.understanding.analyze(
                text,
                context=context,
            )
        except Exception as exc:
            return Result(
                status=Status.ERROR,
                message=str(exc),
                source="understanding",
                metadata={
                    "orchestrator": "v3",
                    "stage": "understanding",
                    "exception": type(exc).__name__,
                },
            )

        # -----------------------------------------------
        # 2) Planning
        # -----------------------------------------------

        try:
            plan = self.planner.plan(
                text,
                analysis,
                context=context,
            )
        except Exception as exc:
            return Result(
                status=Status.ERROR,
                message=str(exc),
                source="planner",
                metadata={
                    "orchestrator": "v3",
                    "stage": "planning",
                    "exception": type(exc).__name__,
                },
            )

        # -----------------------------------------------
        # 3) Execution
        # -----------------------------------------------

        result = self.pipeline.execute(
            text,
            plan,
            context=context,
        )

        # -----------------------------------------------
        # 4) Attach orchestration metadata
        # -----------------------------------------------

        result.metadata.setdefault("orchestrator", "v3")
        result.metadata["analysis"] = analysis
        result.metadata["plan"] = plan

        return result
