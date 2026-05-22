"""
Info Fetcher for SALAAR X SPENCER ULTRA BOT
Fetches player statistics from multiple API sources with caching
"""

import time
import threading
from typing import Dict, Optional, List
from datetime import datetime, timedelta

from api_client import APIClient
from cache_system import CacheSystem
from config import REQUEST_TIMEOUT
from logger import get_logger

logger = get_logger(__name__)


class InfoFetcher:
    """Fetches player statistics from multiple sources"""

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

        self.api = APIClient()
        self.cache = CacheSystem()
        self.stats_cache = {}
        self.cache_lock = threading.Lock()

        logger.info("InfoFetcher initialized")

    def get_player_info(self, uid: str, force_refresh: bool = False) -> Optional[Dict]:
        """Get player information"""
        if not self._validate_uid(uid):
            return None

        # Check cache
        if not force_refresh:
            cached = self._get_cached(uid)
            if cached:
                return cached

        # Fetch from API
        info = self.api.get_player_info(uid)

        if info:
            self._cache_info(uid, info)
            return info

        return None

    def get_player_batch_info(self, uids: List[str]) -> Dict[str, Optional[Dict]]:
        """Get information for multiple players in batch"""
        results = {}
        for uid in uids:
            results[uid] = self.get_player_info(uid)
        return results

    def _validate_uid(self, uid: str) -> bool:
        return uid and uid.isdigit() and 5 <= len(uid) <= 15

    def _get_cached(self, uid: str) -> Optional[Dict]:
        """Get cached player info"""
        with self.cache_lock:
            if uid in self.stats_cache:
                info, expiry = self.stats_cache[uid]
                if time.time() < expiry:
                    return info
                del self.stats_cache[uid]
        return None

    def _cache_info(self, uid: str, info: Dict, ttl: int = 300):
        """Cache player info"""
        with self.cache_lock:
            self.stats_cache[uid] = (info, time.time() + ttl)

    def clear_cache(self):
        """Clear all cached info"""
        with self.cache_lock:
            self.stats_cache.clear()
        logger.info("Info cache cleared")

    def get_formatted_info(self, uid: str) -> Optional[str]:
        """Get formatted player info for display"""
        info = self.get_player_info(uid)
        if not info:
            return None

        return f"""
╔══════════════════════════════════════════════════════════════╗
║                    🎮 PLAYER STATISTICS 🎮                    ║
╚══════════════════════════════════════════════════════════════╝

👤 *Name:* {info.get('name', 'Unknown')}
🆔 *UID:* `{uid}`
🏆 *Level:* {info.get('level', 'N/A')}
🎯 *K/D Ratio:* {info.get('kd', 0)}

📊 *COMBAT STATS*
├─ 💀 Total Kills: {info.get('kills', 0):,}
├─ 🏅 Total Wins: {info.get('wins', 0):,}
├─ 📊 Matches: {info.get('matches', 0):,}
├─ ❤️ Likes Received: {info.get('likes', 0):,}
└─ 🎯 Headshots: {info.get('headshots', 0):,}

📅 *Last Updated:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """