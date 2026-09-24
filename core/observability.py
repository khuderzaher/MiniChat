# -*- coding: utf-8 -*-
"""
MiniChat v3 — Structured Logging / Observability

Logging منظم (JSON lines) مع trace لكل طلب:
    - request_id لكل استعلام
    - event/stage/latency/status لكل خطوة
    - لا تسجّل أسرارًا أو نصوص مستخدم حساسة كاملة
      (تُختصر إلى query_len + مقتطف آمن عند الحاجة)

لا يعتمد على أي مكتبة خارجية.
"""

from __future__ import annotations

import contextlib
import json
import logging
import threading
import time
import uuid
from typing import Any, Dict, Iterator, Optional


# ============================================================
# SAFE REDACTION
# ============================================================

_SENSITIVE_KEYS = {
    "password", "token", "secret", "api_key", "apikey",
    "authorization", "credential", "cookies",
}


def _safe(value: Any, max_len: int = 200) -> Any:
    """اختصار القيم الطويلة ومنع تسريب النصوص الحساسة كاملة."""
    if isinstance(value, str):
        if len(value) > max_len:
            return value[:max_len] + f"...(len={len(value)})"
        return value
    if isinstance(value, dict):
        return {
            k: ("***" if str(k).lower() in _SENSITIVE_KEYS else _safe(v, max_len))
            for k, v in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_safe(v, max_len) for v in value[:20]]
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return _safe(str(value), max_len)


def new_request_id() -> str:
    return uuid.uuid4().hex[:16]


# ============================================================
# LOGGER
# ============================================================

class StructuredLogger:
    """غلافة صغيرة فوق logging تعيد سطور JSON واحدة لكل حدث."""

    name = "structured-logger"

    def __init__(
        self,
        level: str = "INFO",
        file_path: str = "",
        logger_name: str = "minichat",
    ) -> None:
        self._logger = logging.getLogger(logger_name)
        self._logger.setLevel(getattr(logging, level.upper(), logging.INFO))
        self._logger.propagate = False

        if not self._logger.handlers:
            formatter = logging.Formatter("%(message)s")

            if file_path:
                handler: logging.Handler = logging.FileHandler(
                    file_path, encoding="utf-8"
                )
            else:
                handler = logging.StreamHandler()

            handler.setFormatter(formatter)
            self._logger.addHandler(handler)

    def log(self, event: str, **fields: Any) -> None:
        record: Dict[str, Any] = {"event": event}
        record.update({k: _safe(v) for k, v in fields.items()})
        try:
            line = json.dumps(record, ensure_ascii=False, default=str)
        except Exception:
            line = json.dumps({"event": event, "log_error": "unserializable"})
        self._logger.info(line)

    def warning(self, event: str, **fields: Any) -> None:
        self.log(event, level="warning", **fields)

    def error(self, event: str, **fields: Any) -> None:
        self.log(event, level="error", **fields)


_default: Optional[StructuredLogger] = None
_default_lock = threading.Lock()


def get_logger() -> StructuredLogger:
    global _default
    if _default is None:
        with _default_lock:
            if _default is None:
                from core.config import get_config

                cfg = get_config().logging
                _default = StructuredLogger(level=cfg.level, file_path=cfg.file)
    return _default


def set_logger(logger: Optional[StructuredLogger]) -> None:
    """يستخدم في الاختبارات لإعادة التهيئة."""
    global _default
    _default = logger


# ============================================================
# REQUEST TRACE
# ============================================================

class RequestTrace:
    """
    تتبع طلب واحد: id + مراحل + أزمنة + حالات.

    الاستخدام:
        trace = RequestTrace(query)
        with trace.stage("reasoning"):
            ...
        trace.finish(status="success")
    """

    def __init__(self, query: str, logger: Optional[StructuredLogger] = None):
        self.request_id = new_request_id()
        self.query_len = len(query or "")
        self.started = time.perf_counter()
        self.logger = logger or get_logger()
        self.stages: list[Dict[str, Any]] = []
        self._seq = 0

        self.logger.log(
            "request.start",
            request_id=self.request_id,
            query_len=self.query_len,
        )

    @contextlib.contextmanager
    def stage(self, name: str, **extra: Any) -> Iterator[Dict[str, Any]]:
        self._seq += 1
        started = time.perf_counter()
        info: Dict[str, Any] = {"stage": name, "ok": True, "error": None}
        info.update(extra)
        try:
            yield info
        except Exception as exc:
            info["ok"] = False
            info["error"] = type(exc).__name__
            raise
        finally:
            duration_ms = round((time.perf_counter() - started) * 1000, 3)
            entry = {
                "request_id": self.request_id,
                "seq": self._seq,
                "stage": name,
                "duration_ms": duration_ms,
                "ok": info["ok"],
            }
            for key in ("status", "source", "tool", "provider",
                        "decision", "error", "evidence_count",
                        "proof_node_count", "verification"):
                if key in info and info[key] is not None:
                    entry[key] = info[key]
            self.stages.append(entry)
            self.logger.log("stage", **entry)

    def finish(self, status: str, **extra: Any) -> Dict[str, Any]:
        total_ms = round((time.perf_counter() - self.started) * 1000, 3)
        payload = {
            "request_id": self.request_id,
            "status": status,
            "total_ms": total_ms,
            "stages": [s["stage"] for s in self.stages],
        }
        payload.update({k: _safe(v) for k, v in extra.items()})
        self.logger.log("request.end", **payload)
        return payload

    def summary(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "total_ms": round((time.perf_counter() - self.started) * 1000, 3),
            "stages": list(self.stages),
        }
