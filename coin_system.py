"""
Coin System for SALAAR X SPENCER ULTRA BOT
Manages coins, daily rewards, streak bonuses, and VIP benefits
"""

import random
import threading
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from collections import defaultdict

from database import DatabaseManager
from config import (
    DAILY_REWARD_MIN, DAILY_REWARD_MAX, REFERRAL_REWARD,
    LIKE_COST, VISITOR_COST, SPAM_COST,
    VIP_DISCOUNT, VIP_DAILY_MULTIPLIER
)
from logger import get_logger

logger = get_logger(__name__)


class CoinSystem:
    """Complete coin management system"""

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
        self.daily_claims = defaultdict(lambda: {'last_claim': None, 'streak': 0})
        self.claims_lock = threading.Lock()

        logger.info("CoinSystem initialized")

    def get_balance(self, user_id: int) -> int:
        """Get user's coin balance"""
        user = self.db.get_user(user_id)
        return user['coins']

    def add_coins(self, user_id: int, amount: int, source: str = 'admin') -> int:
        """Add coins to user"""
        new_balance = self.db.add_coins(user_id, amount)
        logger.info(f"Added {amount} coins to {user_id} from {source}. New balance: {new_balance}")
        return new_balance

    def deduct_coins(self, user_id: int, amount: int, reason: str = 'action') -> bool:
        """Deduct coins from user"""
        success = self.db.deduct_coins(user_id, amount)
        if success:
            logger.info(f"Deducted {amount} coins from {user_id} for {reason}")
        else:
            logger.warning(f"Insufficient coins for {user_id}. Required: {amount}")
        return success

    def get_action_cost(self, action: str, is_vip: bool = False) -> int:
        """Get cost for an action with VIP discount"""
        costs = {
            'like': LIKE_COST,
            'visit': VISITOR_COST,
            'spam': SPAM_COST,
            'bulk_like': 1  # per like
        }

        base_cost = costs.get(action, 0)

        if is_vip:
            return int(base_cost * (1 - VIP_DISCOUNT))
        return base_cost

    def claim_daily_reward(self, user_id: int, is_vip: bool = False) -> Tuple[int, int, int]:
        """Claim daily reward with streak bonus"""
        with self.claims_lock:
            user = self.db.get_user(user_id)
            last_claim = user.get('last_claim')
            current_streak = user.get('daily_streak', 0)

            # Check if already claimed today
            if last_claim:
                last_date = datetime.fromisoformat(last_claim).date()
                if datetime.now().date() == last_date:
                    return 0, current_streak, 0

                # Check if yesterday was claimed
                if (datetime.now().date() - last_date).days == 1:
                    current_streak += 1
                else:
                    current_streak = 1
            else:
                current_streak = 1

            # Calculate reward
            base_reward = random.randint(DAILY_REWARD_MIN, DAILY_REWARD_MAX)
            streak_bonus = min(current_streak * 5, 100)

            if is_vip:
                base_reward *= VIP_DAILY_MULTIPLIER
                streak_bonus *= VIP_DAILY_MULTIPLIER

            total_reward = base_reward + streak_bonus

            # Update user
            self.db.add_coins(user_id, total_reward)
            self.db.update_user(user_id, last_claim=datetime.now().isoformat(), daily_streak=current_streak)

            logger.info(f"User {user_id} claimed daily reward: {total_reward} coins (streak: {current_streak})")
            return total_reward, current_streak, streak_bonus

    def get_daily_claim_status(self, user_id: int) -> Dict:
        """Get daily claim status"""
        user = self.db.get_user(user_id)
        last_claim = user.get('last_claim')

        if not last_claim:
            return {'can_claim': True, 'streak': 0, 'next_claim': None}

        last_date = datetime.fromisoformat(last_claim)
        today = datetime.now()

        if last_date.date() < today.date():
            return {'can_claim': True, 'streak': user.get('daily_streak', 0), 'next_claim': None}
        else:
            next_claim = last_date + timedelta(days=1)
            return {
                'can_claim': False,
                'streak': user.get('daily_streak', 0),
                'next_claim': next_claim.isoformat(),
                'hours_remaining': (next_claim - today).seconds // 3600,
                'minutes_remaining': ((next_claim - today).seconds % 3600) // 60
            }

    def process_referral(self, referrer_id: int, referred_id: int) -> bool:
        """Process referral and give reward"""
        return self.db.add_referral(referrer_id, referred_id)

    def get_top_users(self, limit: int = 10) -> List[Dict]:
        """Get top coin earners"""
        return self.db.get_leaderboard(limit)

    def get_user_stats(self, user_id: int) -> Dict:
        """Get user's coin statistics"""
        user = self.db.get_user(user_id)

        return {
            'balance': user['coins'],
            'total_earned': user.get('total_earned_coins', 0),
            'total_spent': user.get('total_spent_coins', 0),
            'likes_sent': user.get('total_likes_sent', 0),
            'visitors_sent': user.get('total_visitors_sent', 0),
            'spam_sent': user.get('total_spam_sent', 0),
            'referrals': self.db.get_referral_count(user_id),
            'daily_streak': user.get('daily_streak', 0),
            'is_vip': user.get('is_vip', False)
        }

    def transfer_coins(self, from_user_id: int, to_user_id: int, amount: int) -> bool:
        """Transfer coins between users"""
        if amount <= 0:
            return False

        if not self.deduct_coins(from_user_id, amount, 'transfer'):
            return False

        self.add_coins(to_user_id, amount, 'transfer')
        logger.info(f"Transferred {amount} coins from {from_user_id} to {to_user_id}")
        return True