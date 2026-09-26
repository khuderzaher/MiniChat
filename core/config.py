# -*- coding: utf-8 -*-
"""
MiniChat v3 — Configuration Layer

طبقة إعدادات واحدة لكل النظام:
    - لا hard-coded paths/timeouts/limits داخل منطق الوحدات.
    - كل قيمة يمكن تجاوزها عبر environment (MINICHAT_*).
    - بيئات: development / testing / production بسلوك افتراضي آمن.

القاعدة:
    الإعدادات بيانات، لا منطق. لا شيء هنا يقرر ذكاءً؛
    هو فقط يحدد الحدود والمسارات والأعلام.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field, fields
from typing import Any, Dict, Optional

ENV_PREFIX = "MINICHAT_"

VALID_ENVIRONMENTS = ("development", "testing", "production")


def _env(name: str) -> Optional[str]:
    value = os.environ.get(ENV_PREFIX + name)
    if value is None or not value.strip():
        return None
    return value.strip()


def _env_bool(name: str, default: bool) -> bool:
    raw = _env(name)
    if raw is None:
        return default
    return raw.lower() in ("1", "true", "yes", "on")


def _env_int(name: str, default: int) -> int:
    raw = _env(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    raw = _env(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


@dataclass
class LLMConfig:
    host: str = "127.0.0.1"
    port: int = 8080
    model: str = "qwen"
    timeout_s: float = 60.0
    max_context_chars: int = 6000
    enabled: bool = True

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}/v1"


@dataclass
class ReasoningConfig:
    max_depth: int = 10
    max_iterations: int = 24
    max_proof_nodes: int = 5000
    time_budget_ms: int = 5000
    persistent_store: bool = False
    store_path: str = "reasoning/reasoning.db"


@dataclass
class MemoryConfig:
    session_max_items: int = 200
    profile_max_items: int = 100
    episodic_max_items: int = 500
    feedback_max_items: int = 200
    session_ttl_s: int = 60 * 60 * 24          # 24h
    profile_ttl_s: int = 0                     # 0 = no expiry
    episodic_ttl_s: int = 60 * 60 * 24 * 90    # 90 days
    feedback_ttl_s: int = 0
    persist_path: str = ""                     # "" = memory-only
    max_value_chars: int = 2000


@dataclass
class KnowledgeConfig:
    min_score: float = 0.55
    retrieval_limit: int = 5
    syria_data_path: str = "data/knowledge/syria.json"
    arabic_data_path: str = "data/knowledge/arabic.json"


@dataclass
class LoggingConfig:
    level: str = "INFO"                        # DEBUG/INFO/WARNING/ERROR
    file: str = ""                             # "" = stderr only
    max_bytes: int = 1_000_000
    backup_count: int = 2
    redact_query: bool = True                  # do not log full user text


@dataclass
class LimitsConfig:
    max_query_chars: int = 4000
    pipeline_time_budget_s: float = 120.0
    max_tool_calls: int = 4


@dataclass
class AppConfig:
    environment: str = "development"
    llm: LLMConfig = field(default_factory=LLMConfig)
    reasoning: ReasoningConfig = field(default_factory=ReasoningConfig)
    memory: MemoryConfig = field(default_factory=MemoryConfig)
    knowledge: KnowledgeConfig = field(default_factory=KnowledgeConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    limits: LimitsConfig = field(default_factory=LimitsConfig)

    # ----------------------------------------------------
    # Construction
    # ----------------------------------------------------

    @classmethod
    def load(
        cls,
        path: Optional[str] = None,
        environment: Optional[str] = None,
    ) -> "AppConfig":
        """
        البناء من (بالأولوية التصاعدية):
            defaults -> JSON file -> env overrides
        """
        cfg = cls()

        cfg.environment = (
            environment
            or _env("ENV")
            or "development"
        )

        if cfg.environment not in VALID_ENVIRONMENTS:
            cfg.environment = "development"

        # production defaults tighten automatically before overrides
        if cfg.environment == "production":
            cfg.logging.level = "WARNING"
            cfg.llm.enabled = True
            cfg.memory.persist_path = "data/memory.json"
        elif cfg.environment == "testing":
            cfg.llm.enabled = False
            cfg.logging.level = "ERROR"

        file_path = path or _env("CONFIG")

        if file_path and os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            cfg._apply_dict(data)

        cfg._apply_env()
        cfg.validate()
        return cfg

    def _apply_dict(self, data: Dict[str, Any]) -> None:
        sections = {
            "llm": self.llm,
            "reasoning": self.reasoning,
            "memory": self.memory,
            "knowledge": self.knowledge,
            "logging": self.logging,
            "limits": self.limits,
        }

        for key, value in data.items():
            if key == "environment" and isinstance(value, str):
                self.environment = value
                continue
            target = sections.get(key)
            if target is None or not isinstance(value, dict):
                continue
            valid_names = {f.name for f in fields(target)}
            for fname, fvalue in value.items():
                if fname in valid_names:
                    setattr(target, fname, fvalue)

    def _apply_env(self) -> None:
        self.llm.host = _env("LLM_HOST") or self.llm.host
        self.llm.port = _env_int("LLM_PORT", self.llm.port)
        self.llm.model = _env("LLM_MODEL") or self.llm.model
        self.llm.timeout_s = _env_float("LLM_TIMEOUT", self.llm.timeout_s)
        self.llm.enabled = _env_bool("LLM_ENABLED", self.llm.enabled)

        self.reasoning.max_depth = _env_int(
            "REASONING_MAX_DEPTH", self.reasoning.max_depth
        )
        self.reasoning.persistent_store = _env_bool(
            "REASONING_PERSIST", self.reasoning.persistent_store
        )

        self.logging.level = _env("LOG_LEVEL") or self.logging.level
        self.logging.file = _env("LOG_FILE") or self.logging.file

        self.memory.persist_path = (
            _env("MEMORY_PATH") or self.memory.persist_path
        )

    # ----------------------------------------------------
    # Validation
    # ----------------------------------------------------

    def validate(self) -> None:
        errors = []

        if self.environment not in VALID_ENVIRONMENTS:
            errors.append(f"invalid environment: {self.environment}")

        if not (1 <= self.reasoning.max_depth <= 64):
            errors.append("reasoning.max_depth must be within 1..64")

        if not (1 <= self.reasoning.max_iterations <= 1000):
            errors.append("reasoning.max_iterations must be within 1..1000")

        if not (1 <= self.reasoning.max_proof_nodes <= 200000):
            errors.append("reasoning.max_proof_nodes must be within 1..200000")

        if self.llm.port < 1 or self.llm.port > 65535:
            errors.append("llm.port out of range")

        if self.llm.timeout_s <= 0:
            errors.append("llm.timeout_s must be > 0")

        if not (0.0 <= self.knowledge.min_score <= 1.0):
            errors.append("knowledge.min_score must be within 0..1")

        if self.limits.max_query_chars < 1:
            errors.append("limits.max_query_chars must be >= 1")

        for item in (
            self.memory.session_max_items,
            self.memory.profile_max_items,
            self.memory.episodic_max_items,
            self.memory.feedback_max_items,
        ):
            if item < 1:
                errors.append("memory *_max_items must be >= 1")

        if errors:
            raise ValueError(
                "invalid configuration: " + "; ".join(errors)
            )

    # ----------------------------------------------------
    # Serialization
    # ----------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def write_json(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(self.to_dict(), fh, ensure_ascii=False, indent=2)


_shared: Optional[AppConfig] = None


def get_config() -> AppConfig:
    """إعدادات مشتركة محمّلة مرة واحدة (lazy)."""
    global _shared
    if _shared is None:
        _shared = AppConfig.load()
    return _shared


def set_config(cfg: AppConfig) -> None:
    global _shared
    cfg.validate()
    _shared = cfg
