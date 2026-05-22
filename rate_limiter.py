"""
Rate Limiter for SALAAR X SPENCER ULTRA BOT
Prevents abuse with per-user and per-action rate limiting
"""

import time
import threading
from collections import defaultdict
from typing import Dict, Optional
from datetime import datetime, timedelta

from logger import get_logger

logger = get_logger(__name__)


class RateLimiter:
    """Thread-safe rate limiter with sliding window"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self.limits = {}
        self.user_requests = defaultdict(list)
        self.lock = threading.RLock()

        # Default limits (requests per time window in seconds)
        self.default_limits = {
            'command': (30, 60),      # 30 commands per minute
            'like': (10, 60),         # 10 likes per minute
            'visit': (10, 60),        # 10 visitors per minute
            'spam': (5, 60),          # 5 spam per minute
            'daily': (1, 86400),      # 1 daily claim per day
            'refer': (5, 3600),       # 5 referrals per hour
        }

        logger.info("RateLimiter initialized")

    def set_limit(self, action: str, max_requests: int, window_seconds: int):
        """Set rate limit for an action"""
        with self.lock:
            self.limits[action] = (max_requests, window_seconds)
            logger.info(f"Rate limit set for {action}: {max_requests}/{window_seconds}s")

    def check(self, user_id: int, action: str = 'command', 
              max_requests: int = None, window_seconds: int = None) -> bool:
        """Check if request is within rate limit"""
        with self.lock:
            now = time.time()
            key = f"{user_id}:{action}"

            # Get limit
            if max_requests is None:
                max_requests, window_seconds = self.limits.get(
                    action, self.default_limits.get(action, (10, 60))
                )

            # Clean old requests
            cutoff = now - window_seconds
            self.user_requests[key] = [
                ts for ts in self.user_requests[key] if ts > cutoff
            ]

            # Check limit
            if len(self.user_requests[key]) < max_requests:
                self.user_requests[key].append(now)
                return True

            logger.warning(f"Rate limit exceeded for user {user_id} on {action}")
            return False

    def get_remaining(self, user_id: int, action: str = 'command') -> int:
        """Get remaining requests allowed"""
        with self.lock:
            now = time.time()
            key = f"{user_id}:{action}"

            max_requests, window_seconds = self.limits.get(
                action, self.default_limits.get(action, (10, 60))
            )

            cutoff = now - window_seconds
            self.user_requests[key] = [
                ts for ts in self.user_requests[key] if ts > cutoff
            ]

            return max(0, max_requests - len(self.user_requests[key]))

    def get_reset_time(self, user_id: int, action: str = 'command') -> int:
        """Get seconds until rate limit resets"""
        with self.lock:
            now = time.time()
            key = f"{user_id}:{action}"

            _, window_seconds = self.limits.get(
                action, self.default_limits.get(action, (10, 60))
            )

            if not self.user_requests[key]:
                return 0

            oldest = min(self.user_requests[key])
            reset_time = oldest + window_seconds

            return max(0, int(reset_time - now))

    def reset(self, user_id: int, action: str = None):
        """Reset rate limit for a user"""
        with self.lock:
            if action:
                key = f"{user_id}:{action}"
                if key in self.user_requests:
                    self.user_requests[key] = []
            else:
                # Reset all for user
                keys_to_delete = [k for k in self.user_requests if k.startswith(f"{user_id}:")]
                for key in keys_to_delete:
                    self.user_requests[key] = []

    def get_stats(self) -> Dict:
        """Get rate limiter statistics"""
        with self.lock:
            total_keys = len(self.user_requests)
            total_requests = sum(len(requests) for requests in self.user_requests.values())

            return {
                'total_keys': total_keys,
                'total_requests': total_requests,
                'limits': self.limits,
                'default_limits': self.default_limits
            }