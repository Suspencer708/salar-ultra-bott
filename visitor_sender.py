"""
Visitor Sender Engine for SALAAR X SPENCER ULTRA BOT
Ultra-fast concurrent visitor sending with 200+ threads
"""

import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
from datetime import datetime

from database import DatabaseManager
from guest_manager import GuestManager
from api_client import APIClient
from cache_system import CacheSystem
from rate_limiter import RateLimiter
from config import (
    MAX_CONCURRENT_VISITORS, MAX_VISITORS_PER_DAY_PER_UID, RATE_LIMIT_SECONDS,
    REQUEST_TIMEOUT, GUEST_AUTO_GENERATE
)
from logger import get_logger

logger = get_logger(__name__)


class VisitorSender:
    """Ultra-fast concurrent visitor sender"""

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

        self.db = DatabaseManager()
        self.guest_manager = GuestManager()
        self.api = APIClient()
        self.cache = CacheSystem()
        self.rate_limiter = RateLimiter()

        self.total_visitors_sent = 0
        self.total_visitors_failed = 0
        self.stats_lock = threading.Lock()
        self.active_sessions = {}

        logger.info(f"VisitorSender initialized with {MAX_CONCURRENT_VISITORS} concurrent capacity")

    def send_visitors(self, target_uid: str, count: int, region: str = 'PK',
                      user_id: int = None) -> Dict:
        """Send visitors to a target UID"""
        start_time = time.time()

        if not self._validate_uid(target_uid):
            return {'success': 0, 'total': 0, 'message': 'Invalid UID format', 'duration': 0}

        daily_stats = self.db.get_daily_stats(target_uid, region)
        remaining = MAX_VISITORS_PER_DAY_PER_UID - daily_stats['visitors']

        if remaining <= 0:
            return {
                'success': 0, 'total': 0, 'remaining': 0,
                'message': f'Daily limit reached. Max {MAX_VISITORS_PER_DAY_PER_UID} visitors per day',
                'duration': 0
            }

        count = min(count, remaining)
        guests = self.guest_manager.get_guests(region, count)

        if not guests:
            if GUEST_AUTO_GENERATE:
                new_guest = self.guest_manager.generate_guest(region)
                guests = [new_guest]
            else:
                return {'success': 0, 'total': 0, 'message': 'No active guest accounts', 'duration': 0}

        success_count = 0
        session_id = f"visit_{target_uid}_{region}_{int(time.time())}"
        self.active_sessions[session_id] = {'active': True, 'progress': 0}

        try:
            with ThreadPoolExecutor(max_workers=min(MAX_CONCURRENT_VISITORS, count)) as executor:
                futures = []
                for i, guest in enumerate(guests[:count]):
                    future = executor.submit(self._send_single_visitor, guest, target_uid, region)
                    futures.append(future)

                for future in as_completed(futures):
                    try:
                        if future.result(timeout=REQUEST_TIMEOUT + 5):
                            success_count += 1
                            self._update_stats(True)
                        else:
                            self._update_stats(False)
                        self.active_sessions[session_id]['progress'] = success_count
                    except TimeoutError:
                        logger.warning(f"Visitor request timeout for {target_uid}")
                        self._update_stats(False)
                    except Exception as e:
                        logger.error(f"Visitor request error: {e}")
                        self._update_stats(False)
        finally:
            del self.active_sessions[session_id]

        duration = time.time() - start_time
        self.db.update_daily_stats(target_uid, region, visitors=success_count)

        if user_id:
            self.db.log_visitors(user_id, target_uid, region, count, success_count, duration)

        return {
            'success': success_count,
            'total': count,
            'remaining': remaining - success_count,
            'duration': round(duration, 2),
            'speed': round(success_count / max(duration, 0.1), 1),
            'message': f'Sent {success_count}/{count} visitors in {duration:.2f}s'
        }

    def _send_single_visitor(self, guest: Dict, target_uid: str, region: str) -> bool:
        """Send a single visitor using a guest account"""
        token = self.api.get_access_token(guest['uid'], guest['password'], region)
        if not token:
            self.guest_manager.mark_used(guest, False)
            return False

        if not self.rate_limiter.check(f"visit_{guest['uid']}", 5, 10):
            return False

        success, status = self.api.send_visitor(token, target_uid, region)
        self.guest_manager.mark_used(guest, success)
        time.sleep(RATE_LIMIT_SECONDS)
        return success

    def _validate_uid(self, uid: str) -> bool:
        return uid and uid.isdigit() and 5 <= len(uid) <= 15

    def _update_stats(self, success: bool):
        with self.stats_lock:
            if success:
                self.total_visitors_sent += 1
            else:
                self.total_visitors_failed += 1

    def get_stats(self) -> Dict:
        with self.stats_lock:
            return {
                'total_sent': self.total_visitors_sent,
                'total_failed': self.total_visitors_failed,
                'success_rate': round(
                    self.total_visitors_sent / max(self.total_visitors_sent + self.total_visitors_failed, 1) * 100, 2
                ),
                'active_sessions': len(self.active_sessions)
            }

    def shutdown(self):
        logger.info(f"VisitorSender shutdown. Final stats: {self.get_stats()}")