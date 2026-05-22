"""
Referral System for SALAAR X SPENCER ULTRA BOT
Manages referral links, rewards, and leaderboards
"""

import random
import threading
from typing import Dict, List, Optional
from datetime import datetime

from database import DatabaseManager
from config import REFERRAL_REWARD
from logger import get_logger

logger = get_logger(__name__)


class ReferralSystem:
    """Complete referral management system"""

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
        logger.info("ReferralSystem initialized")

    def get_referral_link(self, user_id: int, bot_username: str) -> str:
        """Get referral link for user"""
        user = self.db.get_user(user_id)
        referral_code = user.get('referral_code', f"SXS{user_id}")

        return f"https://t.me/{bot_username}?start={referral_code}"

    def process_referral(self, referrer_id: int, referred_id: int) -> bool:
        """Process a referral when someone uses a referral link"""
        return self.db.add_referral(referrer_id, referred_id)

    def get_referral_count(self, user_id: int) -> int:
        """Get number of referrals for a user"""
        return self.db.get_referral_count(user_id)

    def get_referral_details(self, user_id: int) -> List[Dict]:
        """Get detailed referral information"""
        return self.db.get_referrals(user_id)

    def get_referral_leaderboard(self, limit: int = 10) -> List[Dict]:
        """Get top referrers"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT u.user_id, u.username, u.coins, COUNT(r.id) as referral_count
            FROM users u
            LEFT JOIN referrals r ON u.user_id = r.referrer_id
            WHERE u.is_banned = 0
            GROUP BY u.user_id
            ORDER BY referral_count DESC, u.coins DESC
            LIMIT ?
        """, (limit,))

        results = cursor.fetchall()
        conn.close()

        return [
            {
                'user_id': r[0],
                'username': r[1] or f"User_{r[0]}",
                'coins': r[2],
                'referral_count': r[3]
            }
            for r in results
        ]

    def get_referral_earnings(self, user_id: int) -> int:
        """Get total coins earned from referrals"""
        count = self.get_referral_count(user_id)
        return count * REFERRAL_REWARD

    def check_referral_eligibility(self, user_id: int) -> bool:
        """Check if user is eligible to refer others"""
        user = self.db.get_user(user_id)
        return not user.get('is_banned', False)

    def generate_referral_code(self, user_id: int) -> str:
        """Generate a unique referral code"""
        import random
        return f"SXS{user_id}{random.randint(1000, 9999)}"