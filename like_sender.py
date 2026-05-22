"""
Like Sender Engine for SALAAR X SPENCER ULTRA BOT
Ultra-fast concurrent like sending with 300+ threads
"""

import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
from datetime import datetime, timedelta

from database import DatabaseManager
from guest_manager import GuestManager
from api_client import APIClient
from cache_system import CacheSystem
from rate_limiter import RateLimiter
from config import (
    MAX_CONCURRENT_LIKES, MAX_LIKES_PER_DAY_PER_UID, RATE_LIMIT_SECONDS,
    REQUEST_TIMEOUT, MAX_RETRIES, RETRY_DELAY
)
from logger import get_logger

logger = get_logger(__name__)

# ============================================================================
# LIKE SENDER CLASS
# ============================================================================

class LikeSender:
    """Ultra-fast concurrent like sender"""
    
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
        
        # Statistics
        self.total_likes_sent = 0
        self.total_likes_failed = 0
        self.stats_lock = threading.Lock()
        
        # Active queues
        self.active_sessions = {}
        
        logger.info("LikeSender initialized with {} concurrent capacity".format(MAX_CONCURRENT_LIKES))
    
    def send_likes(self, target_uid: str, count: int, region: str = 'PK', 
                   user_id: int = None) -> Dict:
        """Send likes to a target UID"""
        start_time = time.time()
        
        # Validate target UID
        if not self._validate_uid(target_uid):
            return {
                'success': 0,
                'total': 0,
                'message': 'Invalid UID format',
                'duration': 0
            }
        
        # Check daily limit
        daily_stats = self.db.get_daily_stats(target_uid, region)
        remaining = MAX_LIKES_PER_DAY_PER_UID - daily_stats['likes']
        
        if remaining <= 0:
            return {
                'success': 0,
                'total': 0,
                'remaining': 0,
                'message': f'Daily limit reached. Max {MAX_LIKES_PER_DAY_PER_UID} likes per day',
                'duration': 0
            }
        
        # Adjust count to daily limit
        count = min(count, remaining)
        
        # Get guest accounts
        guests = self.guest_manager.get_guests(region, count)
        
        if not guests:
            # Auto-generate new guests if needed
            if GUEST_AUTO_GENERATE:
                new_guest = self.guest_manager.generate_guest(region)
                guests = [new_guest]
            else:
                return {
                    'success': 0,
                    'total': 0,
                    'message': 'No active guest accounts available',
                    'duration': 0
                }
        
        # Send likes concurrently
        success_count = 0
        session_id = f"{target_uid}_{region}_{int(time.time())}"
        self.active_sessions[session_id] = {'active': True, 'progress': 0}
        
        try:
            with ThreadPoolExecutor(max_workers=min(MAX_CONCURRENT_LIKES, count)) as executor:
                futures = []
                for i, guest in enumerate(guests[:count]):
                    future = executor.submit(self._send_single_like, guest, target_uid, region)
                    futures.append(future)
                
                # Process results as they complete
                for future in as_completed(futures):
                    try:
                        result = future.result(timeout=REQUEST_TIMEOUT + 5)
                        if result:
                            success_count += 1
                            self._update_stats(True)
                        else:
                            self._update_stats(False)
                        
                        # Update session progress
                        self.active_sessions[session_id]['progress'] = success_count
                        
                    except TimeoutError:
                        logger.warning(f"Like request timeout for {target_uid}")
                        self._update_stats(False)
                    except Exception as e:
                        logger.error(f"Like request error: {e}")
                        self._update_stats(False)
        
        finally:
            del self.active_sessions[session_id]
        
        duration = time.time() - start_time
        
        # Update database
        self.db.update_daily_stats(target_uid, region, likes=success_count)
        
        if user_id:
            self.db.log_likes(user_id, target_uid, region, count, success_count, duration)
        
        return {
            'success': success_count,
            'total': count,
            'remaining': remaining - success_count,
            'duration': round(duration, 2),
            'speed': round(success_count / max(duration, 0.1), 1),
            'session_id': session_id,
            'message': f'Sent {success_count}/{count} likes in {duration:.2f}s'
        }
    
    def _send_single_like(self, guest: Dict, target_uid: str, region: str) -> bool:
        """Send a single like using a guest account"""
        # Get access token
        token = self.api.get_access_token(guest['uid'], guest['password'], region)
        
        if not token:
            self.guest_manager.mark_used(guest, False)
            return False
        
        # Rate limit check
        if not self.rate_limiter.check(f"like_{guest['uid']}", 5, 10):
            return False
        
        # Send like
        success, status = self.api.send_like(token, target_uid, region)
        
        # Update guest stats
        self.guest_manager.mark_used(guest, success)
        
        # Small delay to avoid rate limiting
        time.sleep(RATE_LIMIT_SECONDS)
        
        return success
    
    def send_bulk_likes(self, target_uid: str, count: int, region: str = 'PK',
                        user_id: int = None, concurrency: int = 50) -> Dict:
        """Send bulk likes with custom concurrency"""
        start_time = time.time()
        
        # Split into batches
        batch_size = concurrency
        total_success = 0
        
        for batch_start in range(0, count, batch_size):
            batch_count = min(batch_size, count - batch_start)
            result = self.send_likes(target_uid, batch_count, region, user_id)
            total_success += result['success']
            
            # Small delay between batches
            time.sleep(1)
        
        duration = time.time() - start_time
        
        return {
            'success': total_success,
            'total': count,
            'duration': round(duration, 2),
            'speed': round(total_success / max(duration, 0.1), 1),
            'message': f'Sent {total_success}/{count} likes in {duration:.2f}s'
        }
    
    def _validate_uid(self, uid: str) -> bool:
        """Validate Free Fire UID format"""
        if not uid:
            return False
        if not uid.isdigit():
            return False
        if len(uid) < 5 or len(uid) > 15:
            return False
        return True
    
    def _update_stats(self, success: bool):
        """Update like statistics"""
        with self.stats_lock:
            if success:
                self.total_likes_sent += 1
            else:
                self.total_likes_failed += 1
    
    def get_stats(self) -> Dict:
        """Get like sender statistics"""
        with self.stats_lock:
            return {
                'total_sent': self.total_likes_sent,
                'total_failed': self.total_likes_failed,
                'success_rate': round(
                    self.total_likes_sent / max(self.total_likes_sent + self.total_likes_failed, 1) * 100, 2
                ),
                'active_sessions': len(self.active_sessions)
            }
    
    def get_session_progress(self, session_id: str) -> Optional[Dict]:
        """Get progress of an active session"""
        if session_id in self.active_sessions:
            return dict(self.active_sessions[session_id])
        return None
    
    def cancel_session(self, session_id: str) -> bool:
        """Cancel an active session"""
        if session_id in self.active_sessions:
            self.active_sessions[session_id]['active'] = False
            return True
        return False
    
    def shutdown(self):
        """Shutdown like sender"""
        logger.info(f"LikeSender shutdown. Final stats: {self.get_stats()}")