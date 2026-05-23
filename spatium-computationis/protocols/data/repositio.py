"""
Protocol: Repositio  💾
Meaning: Caching and memoization.

Handles:
- In-memory caching
- TTL-based expiration
- Cache invalidation
- Cache statistics
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from collections import OrderedDict
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, TypeVar

from pydantic import BaseModel, Field


T = TypeVar("T")


class CacheStrategy(str, Enum):
    """Cache eviction strategies."""
    LRU = "lru"       # Least Recently Used
    LFU = "lfu"       # Least Frequently Used
    FIFO = "fifo"     # First In First Out
    TTL = "ttl"       # Time To Live only


class CacheConfig(BaseModel):
    """Configuration for caching."""
    max_size: int = 1000          # Max cache entries
    ttl_seconds: float = 3600.0   # Default TTL (1 hour)
    strategy: CacheStrategy = CacheStrategy.LRU
    persist: bool = False         # Persist to database


class CacheEntry(BaseModel):
    """A single cache entry."""
    key: str
    value: Any
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime | None = None
    access_count: int = 0
    last_accessed: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CacheStats(BaseModel):
    """Cache statistics."""
    total_entries: int = 0
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    hit_rate: float = 0.0
    memory_bytes: int = 0


# ---------------------------------------------------------------------------
# Database (for persistent cache)
# ---------------------------------------------------------------------------

DB_PATH = Path(__file__).parent.parent.parent / "field" / "cache.db"


def _init_cache_db() -> None:
    """Initialize the cache database."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cache_entries (
                cache_key       TEXT PRIMARY KEY,
                cache_value     TEXT NOT NULL,
                created_at      TEXT NOT NULL,
                expires_at      TEXT,
                access_count    INTEGER DEFAULT 0,
                last_accessed   TEXT NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ce_expires ON cache_entries(expires_at)")
        conn.commit()


_init_cache_db()


@contextmanager
def _db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# In-Memory Cache
# ---------------------------------------------------------------------------

class InMemoryCache:
    """LRU cache implementation."""
    
    def __init__(self, config: CacheConfig):
        self.config = config
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._hits = 0
        self._misses = 0
        self._evictions = 0
    
    def get(self, key: str) -> Any | None:
        """Get a value from the cache."""
        if key not in self._cache:
            self._misses += 1
            return None
        
        entry = self._cache[key]
        
        # Check expiration
        if entry.expires_at and entry.expires_at < datetime.now(timezone.utc):
            del self._cache[key]
            self._misses += 1
            return None
        
        # Update access info
        entry.access_count += 1
        entry.last_accessed = datetime.now(timezone.utc)
        
        # Move to end for LRU
        if self.config.strategy == CacheStrategy.LRU:
            self._cache.move_to_end(key)
        
        self._hits += 1
        return entry.value
    
    def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: float | None = None,
    ) -> None:
        """Set a value in the cache."""
        now = datetime.now(timezone.utc)
        ttl = ttl_seconds if ttl_seconds is not None else self.config.ttl_seconds
        expires_at = now + timedelta(seconds=ttl) if ttl > 0 else None
        
        # Evict if at capacity
        while len(self._cache) >= self.config.max_size:
            self._evict_one()
        
        self._cache[key] = CacheEntry(
            key=key,
            value=value,
            created_at=now,
            expires_at=expires_at,
            last_accessed=now,
        )
    
    def delete(self, key: str) -> bool:
        """Delete a key from the cache."""
        if key in self._cache:
            del self._cache[key]
            return True
        return False
    
    def clear(self) -> int:
        """Clear all entries from the cache."""
        count = len(self._cache)
        self._cache.clear()
        return count
    
    def _evict_one(self) -> None:
        """Evict one entry based on strategy."""
        if not self._cache:
            return
        
        if self.config.strategy == CacheStrategy.LRU:
            # Remove least recently used (first item)
            self._cache.popitem(last=False)
        elif self.config.strategy == CacheStrategy.LFU:
            # Remove least frequently used
            min_key = min(self._cache.keys(), key=lambda k: self._cache[k].access_count)
            del self._cache[min_key]
        elif self.config.strategy == CacheStrategy.FIFO:
            # Remove oldest (first item)
            self._cache.popitem(last=False)
        else:
            # Default: remove first
            self._cache.popitem(last=False)
        
        self._evictions += 1
    
    def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        total = self._hits + self._misses
        return CacheStats(
            total_entries=len(self._cache),
            hits=self._hits,
            misses=self._misses,
            evictions=self._evictions,
            hit_rate=self._hits / total if total > 0 else 0.0,
        )


# ---------------------------------------------------------------------------
# Global Cache
# ---------------------------------------------------------------------------

_default_config = CacheConfig()
_cache = InMemoryCache(_default_config)


def configure_cache(config: CacheConfig) -> None:
    """Configure the global cache."""
    global _default_config, _cache
    _default_config = config
    _cache = InMemoryCache(config)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def cache_get(
    key: str,
    namespace: str = "default",
) -> Any | None:
    """
    Protocol Repositio: get a value from the cache.
    """
    full_key = f"{namespace}:{key}"
    
    # Try in-memory cache first
    value = _cache.get(full_key)
    if value is not None:
        return value
    
    # Try persistent cache if enabled
    if _default_config.persist:
        value = _get_from_db(full_key)
        if value is not None:
            # Populate in-memory cache
            _cache.set(full_key, value)
        return value
    
    return None


async def cache_set(
    key: str,
    value: Any,
    namespace: str = "default",
    ttl_seconds: float | None = None,
) -> None:
    """
    Protocol Repositio: set a value in the cache.
    """
    full_key = f"{namespace}:{key}"
    
    # Set in in-memory cache
    _cache.set(full_key, value, ttl_seconds)
    
    # Persist if enabled
    if _default_config.persist:
        _set_in_db(full_key, value, ttl_seconds)


async def cache_delete(
    key: str,
    namespace: str = "default",
) -> bool:
    """
    Protocol Repositio: delete a value from the cache.
    """
    full_key = f"{namespace}:{key}"
    
    result = _cache.delete(full_key)
    
    if _default_config.persist:
        _delete_from_db(full_key)
    
    return result


async def cache_clear(namespace: str | None = None) -> int:
    """
    Protocol Repositio: clear cache entries.
    """
    if namespace:
        # Clear specific namespace
        count = 0
        keys_to_delete = [k for k in _cache._cache.keys() if k.startswith(f"{namespace}:")]
        for key in keys_to_delete:
            _cache.delete(key)
            count += 1
        return count
    else:
        return _cache.clear()


def get_cache_stats() -> CacheStats:
    """Get cache statistics."""
    return _cache.get_stats()


# ---------------------------------------------------------------------------
# Database Operations
# ---------------------------------------------------------------------------

def _get_from_db(key: str) -> Any | None:
    """Get a value from the persistent cache."""
    now = datetime.now(timezone.utc)
    
    with _db() as conn:
        row = conn.execute(
            "SELECT * FROM cache_entries WHERE cache_key = ?",
            (key,)
        ).fetchone()
        
        if not row:
            return None
        
        # Check expiration
        if row["expires_at"]:
            expires_at = datetime.fromisoformat(row["expires_at"])
            if expires_at < now:
                conn.execute("DELETE FROM cache_entries WHERE cache_key = ?", (key,))
                conn.commit()
                return None
        
        # Update access info
        conn.execute(
            "UPDATE cache_entries SET access_count = access_count + 1, last_accessed = ? WHERE cache_key = ?",
            (now.isoformat(), key)
        )
        conn.commit()
        
        return json.loads(row["cache_value"])


def _set_in_db(key: str, value: Any, ttl_seconds: float | None) -> None:
    """Set a value in the persistent cache."""
    now = datetime.now(timezone.utc)
    ttl = ttl_seconds if ttl_seconds is not None else _default_config.ttl_seconds
    expires_at = (now + timedelta(seconds=ttl)).isoformat() if ttl > 0 else None
    
    with _db() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO cache_entries 
            (cache_key, cache_value, created_at, expires_at, access_count, last_accessed)
            VALUES (?, ?, ?, ?, 0, ?)
            """,
            (key, json.dumps(value), now.isoformat(), expires_at, now.isoformat())
        )
        conn.commit()


def _delete_from_db(key: str) -> None:
    """Delete a value from the persistent cache."""
    with _db() as conn:
        conn.execute("DELETE FROM cache_entries WHERE cache_key = ?", (key,))
        conn.commit()


# ---------------------------------------------------------------------------
# Caching Decorator
# ---------------------------------------------------------------------------

def cached(
    ttl_seconds: float | None = None,
    namespace: str = "default",
    key_fn: Callable[..., str] | None = None,
):
    """Decorator to cache function results."""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        import asyncio
        
        def generate_key(*args, **kwargs) -> str:
            if key_fn:
                return key_fn(*args, **kwargs)
            # Generate key from function name and arguments
            key_data = f"{func.__name__}:{args}:{sorted(kwargs.items())}"
            return hashlib.md5(key_data.encode()).hexdigest()
        
        if asyncio.iscoroutinefunction(func):
            async def async_wrapper(*args, **kwargs):
                key = generate_key(*args, **kwargs)
                cached_value = await cache_get(key, namespace)
                if cached_value is not None:
                    return cached_value
                
                result = await func(*args, **kwargs)
                await cache_set(key, result, namespace, ttl_seconds)
                return result
            return async_wrapper
        else:
            def sync_wrapper(*args, **kwargs):
                key = generate_key(*args, **kwargs)
                cached_value = _cache.get(f"{namespace}:{key}")
                if cached_value is not None:
                    return cached_value
                
                result = func(*args, **kwargs)
                _cache.set(f"{namespace}:{key}", result, ttl_seconds)
                return result
            return sync_wrapper
    
    return decorator
