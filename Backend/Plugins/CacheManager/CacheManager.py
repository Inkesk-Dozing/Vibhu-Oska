"""
Vibhu-Oska AI-OS — Cache Manager Plugin
Provides high-performance, thread-safe cache operations (LRU + TTL) with optional Redis integration.
"""

from __future__ import annotations

import time
from collections import OrderedDict
from threading import Lock
from typing import Any

from Backend.Plugins.ConfigLoader.ConfigLoader import ConfigLoader
from Backend.Plugins.ToolRegistry.BaseService import BaseService
from Shared.Models import PluginInfo, CoreStatus, ExecutionTarget


class CacheManager(BaseService):
    """
    Cache Manager Service.
    Supports in-memory OrderedDict-based LRU cache with TTL expiration.
    Has hooks to route through Redis if configured.
    """

    def __init__(self, max_size: int = 1000, default_ttl: int = 3600) -> None:
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._lock = Lock()
        self._cache: OrderedDict[str, tuple[Any, float]] = OrderedDict()
        self._initialized = False
        self._redis_client: Any = None
        self._use_redis = False

    def info(self) -> PluginInfo:
        backend_desc = "Redis" if self._use_redis else "In-Memory"
        return PluginInfo(
            name="cache_manager",
            version="0.1.0",
            description=f"Provides key-value cache access (Backend: {backend_desc}) with LRU & TTL.",
            capabilities=["cache", "lru", "ttl"],
            status=CoreStatus.HEALTHY if self._initialized else CoreStatus.UNKNOWN,
            preferred_target=ExecutionTarget.CPU,
        )

    async def initialize(self) -> None:
        """Lifecycle hook: check config to see if Redis is configured and try to connect."""
        if self._initialized:
            return

        config = ConfigLoader.load()
        engine = config.get("memory.cache.engine", "memory")
        ttl = config.get("memory.cache.ttl_seconds", 3600)
        self._default_ttl = ttl

        if engine == "redis":
            redis_url = config.get("memory.cache.redis_url", "redis://localhost:6379/0")
            try:
                import redis
                self._redis_client = redis.from_url(redis_url, decode_responses=True)
                # Test connection
                self._redis_client.ping()
                self._use_redis = True
            except Exception:
                # Fall back to in-memory silently
                self._use_redis = False

        self._initialized = True

    async def shutdown(self) -> None:
        """Lifecycle hook: close Redis connection if active."""
        if self._use_redis and self._redis_client:
            try:
                self._redis_client.close()
            except Exception:
                pass
            self._redis_client = None
            self._use_redis = False
        self._initialized = False

    def health_check(self) -> bool:
        """Verify Cache is operational."""
        if self._use_redis:
            try:
                self._redis_client.ping()
                return True
            except Exception:
                return False
        return True

    async def execute(self, action: str, **kwargs: Any) -> Any:
        """
        Execute Cache commands.

        Actions:
            - "get": Retrieve cached value by key.
              Args: key (str) -> returns Value or None
            - "set": Set value with key and optional TTL.
              Args: key (str), value (Any), ttl (int, optional)
            - "delete": Remove key from cache.
              Args: key (str)
            - "clear": Evict all keys.
        """
        if not self._initialized:
            await self.initialize()

        key = kwargs.get("key")

        if action == "get":
            if not key:
                raise ValueError("Argument 'key' is required for action 'get'.")
            return self._get(key)

        elif action == "set":
            value = kwargs.get("value")
            ttl = kwargs.get("ttl", self._default_ttl)
            if not key:
                raise ValueError("Argument 'key' is required for action 'set'.")
            self._set(key, value, ttl)
            return True

        elif action == "delete":
            if not key:
                raise ValueError("Argument 'key' is required for action 'delete'.")
            self._delete(key)
            return True

        elif action == "clear":
            self._clear()
            return True

        else:
            raise ValueError(f"Action '{action}' is not supported by CacheManager.")

    # ══════════════════════════════════════════════════════════════════════
    # Core Operations
    # ══════════════════════════════════════════════════════════════════════

    def _get(self, key: str) -> Any | None:
        if self._use_redis:
            try:
                # Redis serialization fallback: use simple string representations or JSON
                import json
                val = self._redis_client.get(key)
                if val is not None:
                    try:
                        return json.loads(val)
                    except json.JSONDecodeError:
                        return val
                return None
            except Exception:
                pass

        with self._lock:
            if key not in self._cache:
                return None

            value, expires_at = self._cache[key]
            if time.time() > expires_at:
                # Expired
                del self._cache[key]
                return None

            # Move key to the end to maintain LRU order
            self._cache.move_to_end(key)
            return value

    def _set(self, key: str, value: Any, ttl: int) -> None:
        expires_at = time.time() + ttl

        if self._use_redis:
            try:
                import json
                try:
                    val_str = json.dumps(value)
                except Exception:
                    val_str = str(value)
                self._redis_client.setex(key, ttl, val_str)
                return
            except Exception:
                pass

        with self._lock:
            if key in self._cache:
                del self._cache[key]

            # Enforce size limit
            if len(self._cache) >= self._max_size:
                # Evict oldest (first item in OrderedDict)
                self._cache.popitem(last=False)

            self._cache[key] = (value, expires_at)

    def _delete(self, key: str) -> None:
        if self._use_redis:
            try:
                self._redis_client.delete(key)
                return
            except Exception:
                pass

        with self._lock:
            self._cache.pop(key, None)

    def _clear(self) -> None:
        if self._use_redis:
            try:
                self._redis_client.flushdb()
                return
            except Exception:
                pass

        with self._lock:
            self._cache.clear()
