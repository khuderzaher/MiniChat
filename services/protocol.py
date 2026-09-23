# -*- coding: utf-8 -*-
"""
MiniChat v3 — Service Compatibility Protocol

المرجع الأساسي للنتائج أصبح:
    core.types.Result

هذا الملف موجود مؤقتًا للحفاظ على توافق الخدمات القديمة
أثناء عملية الانتقال إلى معمارية v3.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from core.types import Result, Status


class Service:
    """
    الواجهة الأساسية للخدمات.

    الخدمات الجديدة يُفضّل أن تستخدم core.types.Result مباشرة.
    """

    name = "service"

    def handle(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Result:
        raise NotImplementedError


def legacy_result(
    handled: bool = False,
    answer: Optional[str] = None,
    source: str = "",
    confidence: float = 0.0,
    metadata: Optional[Dict[str, Any]] = None,
) -> Result:
    """
    محوّل مؤقت من صيغة Result القديمة إلى الصيغة الجديدة.

    لن نستخدمه في المكونات الجديدة.
    """

    if handled:
        status = Status.SUCCESS
    else:
        status = Status.EMPTY

    return Result(
        status=status,
        value=answer,
        source=source or None,
        confidence=confidence,
        metadata=metadata or {},
    )
