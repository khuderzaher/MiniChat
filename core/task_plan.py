# -*- coding: utf-8 -*-
"""
MiniChat v3 — Multi-Stage Task Plan

يمثل مهام متعددة الخطوات مع تبعيات وحدود صريحة.

التصميم:
    - TaskPlan القديم بقي كما هو (backward compatible).
    - ExecutionPlan طبقة اختيارية فوقه: قائمة خطوات مرتبة،
      كل خطوة لها نوع وأهداف اسمية وتبعيات.
    - الحدود: max_steps / max_tool_calls / time_budget_s.
    - deterministic: نفس الإدخال => نفس الخطة دائمًا.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from core.types import TaskPlan


STEP_TYPES = (
    "understanding",
    "memory_read",
    "retrieve",
    "reason",
    "tool",
    "generate",
    "verify",
    "memory_write",
)


@dataclass
class Step:
    step_id: str
    type: str
    target: str = ""                       # اسم المكوّن (provider/tool/...)
    depends_on: List[str] = field(default_factory=list)
    params: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id": self.step_id,
            "type": self.type,
            "target": self.target,
            "depends_on": list(self.depends_on),
            "params": dict(self.params),
        }


@dataclass
class ExecutionPlan:
    """خطة تنفيذ متعددة المراحل محدودة الخطوات."""

    task_plan: TaskPlan
    steps: List[Step] = field(default_factory=list)
    max_steps: int = 12
    max_tool_calls: int = 4
    time_budget_s: float = 120.0

    @property
    def mode(self) -> str:
        return self.task_plan.mode

    def tool_call_count(self) -> int:
        return sum(1 for s in self.steps if s.type == "tool")

    def ordered_steps(self) -> List[Step]:
        """ترتيب topological ثابت؛ الدورات تُقطع بحذف التبعية."""
        remaining = {s.step_id: set(s.depends_on) for s in self.steps}
        by_id = {s.step_id: s for s in self.steps}
        ordered: List[Step] = []
        placed: set = set()

        while remaining:
            ready = sorted(
                sid for sid, deps in remaining.items()
                if not (deps - placed)
            )
            if not ready:
                # دورة تبعية: نفكها بأخذ الأصغر id deterministically
                fallback = sorted(remaining)[0]
                ready = [fallback]
            for sid in ready:
                ordered.append(by_id[sid])
                placed.add(sid)
                del remaining[sid]

        return ordered[: self.max_steps]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mode": self.task_plan.mode,
            "steps": [s.to_dict() for s in self.steps],
            "limits": {
                "max_steps": self.max_steps,
                "max_tool_calls": self.max_tool_calls,
                "time_budget_s": self.time_budget_s,
            },
        }
