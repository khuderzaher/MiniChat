# -*- coding: utf-8 -*-
"""
MiniChat v3 — Scoped Memory System

أربعة مستويات مفصولة بصراحة:

    session   : ذاكرة الجلسة الحالية (short-term، TTL قصير)
    profile   : خصائص المستخدم المعلنة صراحة (long-term)
    episodic  : أحداث/إجابات مهمة سُجّلت بقرار صريح
    feedback  : تقييمات المستخدم (جيد/سيئ/تصحيح)

السياسة (MemoryPolicy):
    - لا شيء يُخزن تلقائيًا من نص حر إلا عبر remember() الصريح
      أو store() بنوع مسموح.
    - profile يقبل مفاتيح معلنة فقط (name, location, language, ...)
      ويطرد أي قيمة تبدو كسرّ (رمز/بريد/هاتف مطوّل).
    - كل قراءة/كتابة scoped: session معزولة لكل session_id،
      profile/episodic/feedback معزولة لكل user_id.
    - لا تسريب بين الجلسات ولا بين المستخدمين إطلاقًا.
    - deterministic: ترتيب الاسترجاع ثابت (score ثم ts ثم key).
    - حدود حجم صارمة + dedup بالـkey داخل نفس scope.

التنفيذ: in-memory مع persistence JSON اختياري (path من config).
لا SQLite جديد، لا background threads، ذاكرة محدودة.
"""

from __future__ import annotations

import json
import os
import re
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from core.protocols import MemoryProvider
from core.types import MemoryResult, Result, Status


SCOPES = ("session", "profile", "episodic", "feedback")

# مفاتيح profile المسموح بها صراحةً — whitelist لا blacklist.
ALLOWED_PROFILE_KEYS = {
    "name",
    "preferred_name",
    "language",
    "dialect",
    "location",
    "country",
    "city",
    "age_group",
    "occupation",
    "interests",
    "topic_preference",
    "answer_style",
}

# أنماط يجب ألا تُخزن أبدًا في الذاكرة (أسرار/معرفات حساسة).
_REJECTED_VALUE_PATTERNS = [
    re.compile(r"\b\d{12,}\b"),                      # أرقام طويلة (بطاقات/hashes)
    re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"),         # بريد إلكتروني
    re.compile(r"(?i)\b(password|token|secret|api[_-]?key)\b"),
    re.compile(r"^\s*[\d\-+ ]{8,}$"),                # أرقام هواتف محتملة
]

_KEY_RE = re.compile(r"^[a-zA-Z0-9_\u0600-\u06FF][a-zA-Z0-9_\-.\u0600-\u06FF]{0,63}$")


def _now() -> float:
    return time.time()


@dataclass
class MemoryItem:
    key: str
    value: str
    scope: str
    session_id: str = ""
    user_id: str = ""
    ts: float = field(default_factory=_now)
    ttl_s: int = 0            # 0 = no expiry
    hits: int = 0

    def expired(self, now: Optional[float] = None) -> bool:
        if self.ttl_s <= 0:
            return False
        now = now if now is not None else _now()
        return (now - self.ts) > self.ttl_s

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "value": self.value,
            "scope": self.scope,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "ts": self.ts,
            "ttl_s": self.ttl_s,
        }


# ============================================================
# POLICY
# ============================================================

class MemoryPolicy:
    """
    سياسة صريحة: ما الذي يجوز حفظه وأين.

    تعيد Result(status=INVALID_INPUT/...) بدل الرمي الصامت.
    """

    name = "memory-policy"

    def validate_store(
        self,
        scope: str,
        key: Any,
        value: Any,
    ) -> Result:
        if scope not in SCOPES:
            return Result(
                status=Status.INVALID_INPUT,
                message=f"unknown memory scope: {scope!r}",
            )

        if not isinstance(key, str) or not _KEY_RE.match(key):
            return Result(
                status=Status.INVALID_INPUT,
                message="memory key must be a safe identifier (1-64 chars)",
            )

        if not isinstance(value, (str, int, float)) and not isinstance(
            value, (list, dict)
        ):
            return Result(
                status=Status.INVALID_INPUT,
                message="memory value must be text or JSON-serializable",
            )

        text = value if isinstance(value, str) else json.dumps(
            value, ensure_ascii=False
        )

        if not text.strip():
            return Result(
                status=Status.INVALID_INPUT,
                message="memory value cannot be empty",
            )

        for pattern in _REJECTED_VALUE_PATTERNS:
            if pattern.search(text):
                return Result(
                    status=Status.INVALID_INPUT,
                    message="value rejected by privacy policy",
                    metadata={"rule": pattern.pattern},
                )

        if scope == "profile" and key not in ALLOWED_PROFILE_KEYS:
            return Result(
                status=Status.INVALID_INPUT,
                message=f"profile key not allowed: {key!r}",
            )

        return Result(status=Status.SUCCESS, value=text)


# ============================================================
# MEMORY SERVICE
# ============================================================

class ScopedMemory(MemoryProvider):
    """
    تنفيذ scoped للذاكرة مع عزل كامل للجلسات والمستخدمين.

    متوافق مع MemoryProvider protocol القديم:
        search(query, context, limit) -> MemoryResult
        store(item, context)          -> Result
    وإضافات صريحة: remember()/recall()/forget()/clear_session().
    """

    name = "memory"

    def __init__(self, config: Any = None, policy: Optional[MemoryPolicy] = None) -> None:
        if config is None:
            from core.config import get_config

            config = get_config().memory

        self.config = config
        self.policy = policy or MemoryPolicy()
        self._lock = threading.Lock()
        # scope -> list[MemoryItem]
        self._items: Dict[str, List[MemoryItem]] = {s: [] for s in SCOPES}
        self._dirty = False

        persist_path = getattr(config, "persist_path", "") or ""
        if persist_path:
            self._load(persist_path)

    # ----------------------------------------------------
    # persistence
    # ----------------------------------------------------

    def _load(self, path: str) -> None:
        try:
            if not os.path.exists(path):
                return
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            if not isinstance(data, dict):
                return
            for scope in SCOPES:
                raw_items = data.get(scope)
                if not isinstance(raw_items, list):
                    continue
                for raw in raw_items:
                    item = self._item_from_dict(raw)
                    if item is not None:
                        self._items[scope].append(item)
        except (ValueError, OSError, TypeError):
            # ملف تالف: نتجاهله بأمان بدل تفجير الإقلاع.
            pass

    @staticmethod
    def _item_from_dict(raw: Any) -> Optional[MemoryItem]:
        if not isinstance(raw, dict):
            return None
        key = raw.get("key")
        value = raw.get("value")
        scope = raw.get("scope")
        if not isinstance(key, str) or not isinstance(value, str):
            return None
        if scope not in SCOPES:
            return None
        try:
            return MemoryItem(
                key=key,
                value=value,
                scope=scope,
                session_id=str(raw.get("session_id", "") or ""),
                user_id=str(raw.get("user_id", "") or ""),
                ts=float(raw.get("ts", _now())),
                ttl_s=int(raw.get("ttl_s", 0) or 0),
            )
        except (TypeError, ValueError):
            return None

    def save(self, path: Optional[str] = None) -> Result:
        target = path or getattr(self.config, "persist_path", "") or ""
        if not target:
            return Result(
                status=Status.INVALID_INPUT,
                message="no persistence path configured",
            )
        with self._lock:
            payload = {
                scope: [i.to_dict() for i in items if not i.expired()]
                for scope, items in self._items.items()
            }
        tmp = target + ".tmp"
        directory = os.path.dirname(target)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False)
        os.replace(tmp, target)
        self._dirty = False
        return Result(status=Status.SUCCESS, value=target)

    # ----------------------------------------------------
    # helpers
    # ----------------------------------------------------

    def _ttl_for(self, scope: str) -> int:
        return int(getattr(self.config, f"{scope}_ttl_s", 0) or 0)

    def _max_for(self, scope: str) -> int:
        return int(getattr(self.config, f"{scope}_max_items", 100) or 100)

    def _trim_and_expire(self, scope: str, now: float) -> None:
        items = self._items[scope]
        items[:] = [i for i in items if not i.expired(now)]
        max_items = self._max_for(scope)
        if len(items) > max_items:
            # نحذف الأقدم أولًا (FIFO حسب ts ثم الترتيب الداخلي)
            items.sort(key=lambda i: (i.ts, i.key))
            del items[: len(items) - max_items]

    # ----------------------------------------------------
    # write API
    # ----------------------------------------------------

    def remember(
        self,
        key: str,
        value: str,
        scope: str = "session",
        session_id: str = "",
        user_id: str = "",
    ) -> Result:
        """تخزين صريح بنوع scope واضح."""
        check = self.policy.validate_store(scope, key, value)
        if not check.ok:
            return check

        text = str(check.value)
        max_chars = int(getattr(self.config, "max_value_chars", 2000))
        if len(text) > max_chars:
            return Result(
                status=Status.INVALID_INPUT,
                message=f"value exceeds max_value_chars={max_chars}",
            )

        now = _now()
        with self._lock:
            items = self._items[scope]

            # dedup/update: نفس scope+owner+key يستبدل القيمة.
            for existing in items:
                if (
                    existing.key == key
                    and existing.session_id == (session_id or "")
                    and existing.user_id == (user_id or "")
                ):
                    existing.value = text
                    existing.ts = now
                    self._dirty = True
                    return Result(
                        status=Status.SUCCESS,
                        value=existing.to_dict(),
                        source=self.name,
                        metadata={"updated": True, "scope": scope},
                    )

            items.append(
                MemoryItem(
                    key=key,
                    value=text,
                    scope=scope,
                    session_id=session_id or "",
                    user_id=user_id or "",
                    ts=now,
                    ttl_s=self._ttl_for(scope),
                )
            )
            self._trim_and_expire(scope, now)
            self._dirty = True

        return Result(
            status=Status.SUCCESS,
            metadata={"created": True, "scope": scope},
            source=self.name,
        )

    def store(
        self,
        item: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> Result:
        """متوافق مع MemoryProvider protocol."""
        if not isinstance(item, dict):
            return Result(
                status=Status.INVALID_INPUT,
                message="memory item must be a dict",
            )

        ctx = context or {}
        scope = str(item.get("scope") or ctx.get("scope") or "session")
        key = str(item.get("key") or "").strip()
        value = item.get("value")

        return self.remember(
            key=key,
            value="" if value is None else str(value),
            scope=scope,
            session_id=str(ctx.get("session_id", "") or ""),
            user_id=str(ctx.get("user_id", "") or ""),
        )

    # ----------------------------------------------------
    # read API
    # ----------------------------------------------------

    def recall(
        self,
        query_tokens: Optional[List[str]] = None,
        scopes: Optional[List[str]] = None,
        session_id: str = "",
        user_id: str = "",
        limit: int = 5,
    ) -> MemoryResult:
        wanted = [s for s in (scopes or list(SCOPES)) if s in SCOPES]
        tokens = [t for t in (query_tokens or []) if t]
        now = _now()
        scored: List[tuple] = []

        with self._lock:
            for scope in wanted:
                for item in self._items[scope]:
                    if item.expired(now):
                        continue
                    # عزل صارم: جلسة لا ترى إلا جلستها،
                    # وبيانات مستخدم لا ترى إلا مستخدمها.
                    if scope == "session":
                        if not session_id or item.session_id != session_id:
                            continue
                    else:
                        if not user_id or item.user_id != user_id:
                            continue

                    score = 0.0
                    if tokens:
                        hay = f"{item.key} {item.value}".lower()
                        matches = sum(1 for t in tokens if t.lower() in hay)
                        if matches == 0:
                            continue
                        score = matches / len(tokens)
                    else:
                        score = 1.0

                    item.hits += 1
                    scored.append((score, item))

            # deterministic ordering: score ↓ ثم ts ↓ ثم key ↑
            scored.sort(key=lambda p: (-p[0], -p[1].ts, p[1].key))
            selected = scored[: max(1, int(limit))]
            items_out = [
                {**i.to_dict(), "score": round(s, 6)}
                for s, i in selected
            ]

        return MemoryResult(
            found=bool(items_out),
            items=items_out,
            memory_type=",".join(wanted),
            confidence=round(selected[0][0], 4) if selected else None,
            metadata={
                "provider": self.name,
                "scopes": wanted,
                "candidates": len(scored),
            },
        )

    def search(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        limit: int = 5,
    ) -> MemoryResult:
        """متوافق مع MemoryProvider protocol — بحث lexical مضبوط."""
        if not isinstance(query, str):
            return MemoryResult(found=False, metadata={"reason": "invalid_query"})

        ctx = context or {}
        tokens = [t for t in re.split(r"\s+", query.strip().lower()) if t]

        return self.recall(
            query_tokens=tokens,
            scopes=ctx.get("scopes"),
            session_id=str(ctx.get("session_id", "") or ""),
            user_id=str(ctx.get("user_id", "") or ""),
            limit=limit,
        )

    # ----------------------------------------------------
    # lifecycle
    # ----------------------------------------------------

    def forget(
        self,
        key: str,
        scope: str = "session",
        session_id: str = "",
        user_id: str = "",
    ) -> Result:
        if scope not in SCOPES:
            return Result(
                status=Status.INVALID_INPUT,
                message=f"unknown memory scope: {scope!r}",
            )
        removed = 0
        with self._lock:
            items = self._items[scope]
            keep = []
            for item in items:
                owner_match = (
                    (scope == "session" and item.session_id == session_id)
                    or (scope != "session" and item.user_id == user_id)
                )
                if item.key == key and owner_match:
                    removed += 1
                else:
                    keep.append(item)
            self._items[scope] = keep
            if removed:
                self._dirty = True
        return Result(
            status=Status.SUCCESS if removed else Status.EMPTY,
            metadata={"removed": removed, "scope": scope},
        )

    def clear_session(self, session_id: str) -> Result:
        if not session_id:
            return Result(
                status=Status.INVALID_INPUT,
                message="session_id required",
            )
        with self._lock:
            before = len(self._items["session"])
            self._items["session"] = [
                i for i in self._items["session"] if i.session_id != session_id
            ]
            removed = before - len(self._items["session"])
            if removed:
                self._dirty = True
        return Result(status=Status.SUCCESS, metadata={"removed": removed})

    def clear_user(self, user_id: str) -> Result:
        """حق النسيان: حذف كل ما يخص مستخدمًا (privacy deletion)."""
        if not user_id:
            return Result(
                status=Status.INVALID_INPUT,
                message="user_id required",
            )
        with self._lock:
            removed = 0
            for scope in ("profile", "episodic", "feedback"):
                before = len(self._items[scope])
                self._items[scope] = [
                    i for i in self._items[scope] if i.user_id != user_id
                ]
                removed += before - len(self._items[scope])
            self._dirty = True
        return Result(status=Status.SUCCESS, metadata={"removed": removed})

    def stats(self) -> Dict[str, Any]:
        now = _now()
        with self._lock:
            return {
                scope: sum(1 for i in items if not i.expired(now))
                for scope, items in self._items.items()
            }
