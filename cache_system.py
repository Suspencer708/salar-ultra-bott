"""
Cache System for SALAAR X SPENCER ULTRA BOT
LRU cache with TTL and thread-safe operations
"""

import time
import threading
from collections import OrderedDict
from typing import Dict, Any, Optional, List
from datetime import datetime

from config import CACHE_SIZE, CACHE_TTL, CACHE_CLEANUP_INTERVAL
from logger import get_logger

logger = get_logger(__name__)


class CacheSystem:
    """Thread-safe LRU cache with TTL"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
        return cls._instance

    def __init__(self, max_size: int = CACHE_SIZE, ttl: int = CACHE_TTL):
        if self._initialized:
            return
        self._initialized = True

        self.max_size = max_size
        self.ttl = ttl
        self.cache = OrderedDict()
        self.lock = threading.RLock()

        self.hits = 0
        self.misses = 0

        self._start_cleanup_thread()

        logger.info(f"CacheSystem initialized with max_size={max_size}, ttl={ttl}")

    def _start_cleanup_thread(self):
        """Start background cleanup thread"""
        def cleanup_loop():
            while True:
                time.sleep(CACHE_CLEANUP_INTERVAL)
                self.cleanup_expired()

        thread = threading.Thread(target=cleanup_loop, daemon=True)
        thread.start()
        logger.info("Cache cleanup thread started")

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        with self.lock:
            if key in self.cache:
                value, expiry = self.cache[key]
                if time.time() < expiry:
                    self.cache.move_to_end(key)
                    self.hits += 1
                    return value
                else:
                    del self.cache[key]
            self.misses += 1
            return None

    def set(self, key: str, value: Any, ttl: int = None):
        """Set value in cache with TTL"""
        with self.lock:
            if key in self.cache:
                del self.cache[key]
            elif len(self.cache) >= self.max_size:
                self.cache.popitem(last=False)

            ttl = ttl or self.ttl
            self.cache[key] = (value, time.time() + ttl)

    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        with self.lock:
            if key in self.cache:
                del self.cache[key]
                return True
            return False

    def exists(self, key: str) -> bool:
        """Check if key exists in cache and not expired"""
        with self.lock:
            if key in self.cache:
                value, expiry = self.cache[key]
                if time.time() < expiry:
                    return True
                del self.cache[key]
            return False

    def cleanup_expired(self):
        """Remove expired entries"""
        with self.lock:
            now = time.time()
            expired = [k for k, (_, exp) in self.cache.items() if exp < now]
            for k in expired:
                del self.cache[k]

            if expired:
                logger.debug(f"Cleaned up {len(expired)} expired cache entries")

    def clear(self):
        """Clear entire cache"""
        with self.lock:
            self.cache.clear()
            self.hits = 0
            self.misses = 0
            logger.info("Cache cleared")

    def get_stats(self) -> Dict:
        """Get cache statistics"""
        with self.lock:
            total = self.hits + self.misses
            hit_rate = (self.hits / total * 100) if total > 0 else 0

            return {
                'size': len(self.cache),
                'max_size': self.max_size,
                'hits': self.hits,
                'misses': self.misses,
                'hit_rate': round(hit_rate, 2),
                'ttl': self.ttl,
                'memory_estimate': self._estimate_memory()
            }

    def _estimate_memory(self) -> int:
        """Estimate memory usage in bytes"""
        # Rough estimation
        return len(self.cache) * 1024  # Assume ~1KB per entry

    def get_keys(self) -> List[str]:
        """Get all cache keys"""
        with self.lock:
            return list(self.cache.keys())

    def get_ttl(self, key: str) -> Optional[int]:
        """Get remaining TTL for a key in seconds"""
        with self.lock:
            if key in self.cache:
                value, expiry = self.cache[key]
                remaining = max(0, expiry - time.time())
                return int(remaining)
            return None

    def touch(self, key: str, ttl: int = None) -> bool:
        """Refresh TTL for a key"""
        with self.lock:
            if key in self.cache:
                value, _ = self.cache[key]
                ttl = ttl or self.ttl
                self.cache[key] = (value, time.time() + ttl)
                return True
            return False

    def get_or_set(self, key: str, factory, ttl: int = None) -> Any:
        """Get from cache or set using factory function"""
        value = self.get(key)
        if value is not None:
            return value

        value = factory()
        if value is not None:
            self.set(key, value, ttl)
        return value

    def mget(self, keys: List[str]) -> Dict[str, Any]:
        """Get multiple keys at once"""
        return {key: self.get(key) for key in keys}

    def mset(self, items: Dict[str, Any], ttl: int = None):
        """Set multiple key-value pairs"""
        for key, value in items.items():
            self.set(key, value, ttl)

    def incr(self, key: str, delta: int = 1, ttl: int = None) -> int:
        """Increment a counter in cache"""
        with self.lock:
            value = self.get(key)
            if value is None:
                value = 0
            new_value = value + delta
            self.set(key, new_value, ttl)
            return new_value

    def decr(self, key: str, delta: int = 1, ttl: int = None) -> int:
        """Decrement a counter in cache"""
        return self.incr(key, -delta, ttl)