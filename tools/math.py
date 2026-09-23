# -*- coding: utf-8 -*-
"""
MiniChat v3 — Math Tool

واجهة v3 لمحرك الرياضيات القديم.

مسؤولية هذه الطبقة:
1. فهم الغلاف اللغوي البسيط حول العملية الرياضية.
2. استخراج التعبير الرياضي.
3. تمرير التعبير النظيف إلى MathEngine.
4. إعادة ToolResult موحّد.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional

from core.protocols import Tool
from core.types import ToolResult
from math_engine import MathEngine


class MathTool(Tool):
    name = "math"

    @staticmethod
    def _extract_expression(text: str) -> Optional[str]:
        """
        استخراج تعبير رياضي من سؤال عربي بسيط.

        أمثلة:
            احسب 25 × 4
            ما ناتج 25 × 4؟
            أوجد ناتج 15 + 7
            25 × 4

        لا نحاول هنا بناء محلل لغوي عام.
        """

        text = text.strip()

        # ------------------------------------------------
        # 1) معادلة: نأخذ الجزء الرياضي الذي يحتوي على =
        # ------------------------------------------------

        if "=" in text:
            match = re.search(
                r"([+-]?\d+(?:\.\d+)?(?:\s*[a-zA-Z]\s*)?"
                r"(?:\s*[+\-*/×÷^%]\s*[+-]?\d+(?:\.\d+)?"
                r"(?:\s*[a-zA-Z]\s*)?)*)"
                r"\s*=\s*"
                r"([+-]?\d+(?:\.\d+)?)",
                text,
            )

            if match:
                return f"{match.group(1).strip()} = {match.group(2).strip()}"

        # ------------------------------------------------
        # 2) تعبير حسابي صريح
        # ------------------------------------------------

        match = re.search(
            r"[-+]?\d+(?:\.\d+)?"
            r"(?:\s*[+\-*/×÷^%]\s*[-+]?\d+(?:\.\d+)?)+",
            text,
        )

        if match:
            return match.group(0).strip()

        return None

    def run(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> ToolResult:

        if not isinstance(query, str) or not query.strip():
            return ToolResult(
                success=False,
                tool=self.name,
                error="empty_query",
            )

        text = query.strip()

        # ------------------------------------------------
        # 1) استخراج التعبير الرياضي
        # ------------------------------------------------

        expression = self._extract_expression(text)

        if expression is None:
            return ToolResult(
                success=False,
                tool=self.name,
                error="no_math_expression_found",
            )

        # ------------------------------------------------
        # 2) معادلة خطية
        # ------------------------------------------------

        if "=" in expression:
            result = MathEngine.solve_linear(expression)

            if result is not None:
                return ToolResult(
                    success=True,
                    tool=self.name,
                    value=result,
                    formatted=f"{result['var']} = {result['value']}",
                    metadata={
                        "operation": "solve_linear",
                        "expression": expression,
                    },
                )

        # ------------------------------------------------
        # 3) تعبير رياضي
        # ------------------------------------------------

        expr = expression.replace("×", "*").replace("÷", "/")

        result = MathEngine.evaluate(expr)

        if result is not None:
            return ToolResult(
                success=True,
                tool=self.name,
                value=result,
                formatted=str(result),
                metadata={
                    "operation": "evaluate",
                    "expression": expression,
                },
            )

        return ToolResult(
            success=False,
            tool=self.name,
            error="unsupported_or_unresolved_expression",
            metadata={
                "expression": expression,
            },
        )
