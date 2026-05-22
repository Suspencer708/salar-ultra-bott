"""
Database Manager for SALAAR X SPENCER ULTRA BOT
Complete database operations with connection pooling, migrations, and backup
"""

import sqlite3
import json
import time
import threading
import queue
import os
import shutil
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any, Union
from contextlib import contextmanager

from config import DATABASE_FILE, DATABASE_POOL_SIZE
from constants import (
    DB_CREATE_USERS, DB_CREATE_GUESTS, DB_CREATE_HISTORY,
    DB_CREATE_LIKES_HISTORY, DB_CREATE_VISITORS_HISTORY,
    DB_CREATE_SPAM_HISTORY, DB_CREATE_DAILY_LIMITS,
    DB_CREATE_COMMANDS_USAGE, DB_CREATE_REFERRALS,
    DB_CREATE_VIP_BENEFITS, DB_CREATE_FEEDBACK,
    DB_CREATE_ANNOUNCEMENTS, DB_CREATE_BLACKLIST,
    DB_CREATE_SETTINGS, DB_CREATE_ANALYTICS,
    DB_CREATE_API_KEYS, DB_CREATE_WEBHOOKS,
    DB_CREATE_RATE_LIMITS, DB_CREATE_SESSIONS,
    DB_CREATE_QUEUE, DB_CREATE_LOGS
)
from logger import get_logger

logger = get_logger(__name__)

# ============================================================================
# DATABASE MANAGER CLASS
# ============================================================================

class DatabaseManager:
    """Complete database manager with connection pooling, migrations, and backup"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Singleton pattern"""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        
        self.db_file = DATABASE_FILE
        self.pool_size = DATABASE_POOL_SIZE
        self.connection_pool = queue.Queue(maxsize=self.pool_size)
        self._init_connection_pool()
        self._init_database()
        self._init_migrations()
        
        logger.info(f"DatabaseManager initialized with pool size {self.pool_size}")
    
    def _init_connection_pool(self):
        """Initialize connection pool"""
        for i in range(self.pool_size):
            conn = self._create_connection()
            self.connection_pool.put(conn)
        logger.debug(f"Created {self.pool_size} database connections")
    
    def _create_connection(self) -> sqlite3.Connection:
        """Create a new database connection"""
        conn = sqlite3.connect(self.db_file, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA cache_size=10000")
        conn.execute("PRAGMA temp_store=MEMORY")
        return conn
    
    @contextmanager
    def get_connection(self):
        """Get a connection from the pool"""
        conn = None
        try:
            conn = self.connection_pool.get(timeout=5)
            yield conn
        except queue.Empty:
            logger.warning("Connection pool empty, creating temporary connection")
            conn = self._create_connection()
            yield conn
        finally:
            if conn:
                try:
                    self.connection_pool.put_nowait(conn)
                except queue.Full:
                    conn.close()
    
    def _init_database(self):
        """Initialize all database tables"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Create all tables
            cursor.execute(DB_CREATE_USERS)
            cursor.execute(DB_CREATE_LIKES_HISTORY)
            cursor.execute(DB_CREATE_VISITORS_HISTORY)
            cursor.execute(DB_CREATE_SPAM_HISTORY)
            cursor.execute(DB_CREATE_DAILY_LIMITS)
            cursor.execute(DB_CREATE_COMMANDS_USAGE)
            cursor.execute(DB_CREATE_REFERRALS)
            cursor.execute(DB_CREATE_VIP_BENEFITS)
            cursor.execute(DB_CREATE_FEEDBACK)
            cursor.execute(DB_CREATE_ANNOUNCEMENTS)
            cursor.execute(DB_CREATE_BLACKLIST)
            cursor.execute(DB_CREATE_SETTINGS)
            cursor.execute(DB_CREATE_ANALYTICS)
            cursor.execute(DB_CREATE_API_KEYS)
            cursor.execute(DB_CREATE_WEBHOOKS)
            cursor.execute(DB_CREATE_RATE_LIMITS)
            cursor.execute(DB_CREATE_SESSIONS)
            cursor.execute(DB_CREATE_QUEUE)
            cursor.execute(DB_CREATE_LOGS)
            
            # Create guest tables for each region
            for region in ['PK', 'IND', 'BR', 'ID', 'TH', 'VN']:
                cursor.execute(DB_CREATE_GUESTS.format(region=region))
            
            # Insert default settings
            self._insert_default_settings(cursor)
            
            conn.commit()
        
        logger.info("Database initialized with all tables")
    
    def _insert_default_settings(self, cursor):
        """Insert default settings into database"""
        default_settings = [
            ('bot_version', '8.0.0'),
            ('bot_name', 'SALAAR X SPENCER ULTRA BOT'),
            ('maintenance_mode', 'false'),
            ('daily_reward_min', '50'),
            ('daily_reward_max', '500'),
            ('referral_reward', '100'),
            ('like_cost', '5'),
            ('visitor_cost', '3'),
            ('spam_cost', '10'),
            ('max_likes_per_day', '1000'),
            ('max_visitors_per_day', '1000'),
            ('max_spam_per_day', '500'),
            ('max_concurrent', '500'),
            ('last_maintenance', datetime.now().isoformat()),
            ('total_users', '0'),
            ('total_likes', '0'),
            ('total_visitors', '0'),
            ('total_spam', '0'),
            ('total_coins', '0')
        ]
        
        for key, value in default_settings:
            cursor.execute("""
                INSERT OR REPLACE INTO settings (key, value, updated_at)
                VALUES (?, ?, ?)
            """, (key, value, datetime.now().isoformat()))
    
    def _init_migrations(self):
        """Run database migrations if needed"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if migrations table exists
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='migrations'
            """)
            
            if not cursor.fetchone():
                cursor.execute("""
                    CREATE TABLE migrations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        version INTEGER,
                        applied_at TEXT
                    )
                """)
                conn.commit()
            
            # Run migrations
            self._run_migrations(cursor)
            conn.commit()
    
    def _run_migrations(self, cursor):
        """Run pending migrations"""
        cursor.execute("SELECT MAX(version) FROM migrations")
        result = cursor.fetchone()
        current_version = result[0] if result[0] else 0
        
        migrations = [
            (1, "ALTER TABLE users ADD COLUMN daily_streak INTEGER DEFAULT 0"),
            (2, "ALTER TABLE users ADD COLUMN total_earned_coins INTEGER DEFAULT 0"),
            (3, "ALTER TABLE users ADD COLUMN total_spent_coins INTEGER DEFAULT 0"),
            (4, "CREATE INDEX idx_likes_target ON likes_history(target_uid)"),
            (5, "CREATE INDEX idx_likes_date ON likes_history(timestamp)"),
            (6, "CREATE INDEX idx_users_coins ON users(coins)"),
        ]
        
        for version, sql in migrations:
            if version > current_version:
                try:
                    cursor.execute(sql)
                    cursor.execute(
                        "INSERT INTO migrations (version, applied_at) VALUES (?, ?)",
                        (version, datetime.now().isoformat())
                    )
                    logger.info(f"Applied migration version {version}")
                except Exception as e:
                    logger.error(f"Migration {version} failed: {e}")
    
    # ========================================================================
    # USER MANAGEMENT
    # ========================================================================
    
    def get_user(self, user_id: int) -> Dict[str, Any]:
        """Get or create user"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            user = cursor.fetchone()
            
            if not user:
                # Generate unique referral code
                import random
                referral_code = f"SXS{user_id}{random.randint(1000, 9999)}"
                
                cursor.execute("""
                    INSERT INTO users (user_id, join_date, last_active, referral_code, coins)
                    VALUES (?, ?, ?, ?, 500)
                """, (user_id, datetime.now().isoformat(), datetime.now().isoformat(), referral_code))
                conn.commit()
                
                cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
                user = cursor.fetchone()
                
                # Update total users count in settings
                cursor.execute("SELECT value FROM settings WHERE key = 'total_users'")
                total_users = int(cursor.fetchone()[0]) + 1
                cursor.execute(
                    "UPDATE settings SET value = ? WHERE key = 'total_users'",
                    (str(total_users),)
                )
                conn.commit()
            
            return dict(user)
    
    def update_user(self, user_id: int, **kwargs) -> bool:
        """Update user fields"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            set_clause = ", ".join([f"{key} = ?" for key in kwargs.keys()])
            values = list(kwargs.values()) + [user_id]
            
            cursor.execute(f"UPDATE users SET {set_clause} WHERE user_id = ?", values)
            conn.commit()
            
            return cursor.rowcount > 0
    
    def get_all_users(self, limit: int = None, offset: int = 0) -> List[Dict]:
        """Get all users with pagination"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            query = "SELECT * FROM users WHERE is_banned = 0 ORDER BY coins DESC"
            if limit:
                query += f" LIMIT {limit} OFFSET {offset}"
            
            cursor.execute(query)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_user_count(self) -> int:
        """Get total number of users"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM users WHERE is_banned = 0")
            return cursor.fetchone()[0]
    
    def get_banned_users(self) -> List[Dict]:
        """Get all banned users"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE is_banned = 1")
            return [dict(row) for row in cursor.fetchall()]
    
    def ban_user(self, user_id: int, reason: str = None) -> bool:
        """Ban a user"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET is_banned = 1 WHERE user_id = ?",
                (user_id,)
            )
            conn.commit()
            return cursor.rowcount > 0
    
    def unban_user(self, user_id: int) -> bool:
        """Unban a user"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET is_banned = 0 WHERE user_id = ?",
                (user_id,)
            )
            conn.commit()
            return cursor.rowcount > 0
    
    # ========================================================================
    # COIN MANAGEMENT
    # ========================================================================
    
    def add_coins(self, user_id: int, amount: int) -> int:
        """Add coins to user and return new balance"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET coins = coins + ?, total_earned_coins = total_earned_coins + ? WHERE user_id = ?",
                (amount, amount, user_id)
            )
            cursor.execute("SELECT coins FROM users WHERE user_id = ?", (user_id,))
            new_balance = cursor.fetchone()[0]
            conn.commit()
            
            # Update total coins in settings
            cursor.execute("SELECT value FROM settings WHERE key = 'total_coins'")
            total_coins = int(cursor.fetchone()[0]) + amount
            cursor.execute(
                "UPDATE settings SET value = ? WHERE key = 'total_coins'",
                (str(total_coins),)
            )
            conn.commit()
            
            return new_balance
    
    def deduct_coins(self, user_id: int, amount: int) -> bool:
        """Deduct coins from user if sufficient balance"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT coins FROM users WHERE user_id = ?", (user_id,))
            coins = cursor.fetchone()[0]
            
            if coins >= amount:
                cursor.execute(
                    "UPDATE users SET coins = coins - ?, total_spent_coins = total_spent_coins + ? WHERE user_id = ?",
                    (amount, amount, user_id)
                )
                conn.commit()
                return True
            return False
    
    def get_balance(self, user_id: int) -> int:
        """Get user's coin balance"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT coins FROM users WHERE user_id = ?", (user_id,))
            result = cursor.fetchone()
            return result[0] if result else 500
    
    def get_leaderboard(self, limit: int = 10) -> List[Dict]:
        """Get top coin earners"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT user_id, username, coins, total_likes_sent, 
                       total_visitors_sent, total_spam_sent, total_referrals
                FROM users 
                WHERE is_banned = 0 
                ORDER BY coins DESC 
                LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]
    
    # ========================================================================
    # REFERRAL SYSTEM
    # ========================================================================
    
    def add_referral(self, referrer_id: int, referred_id: int) -> bool:
        """Add a referral and give reward"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if already referred
            cursor.execute(
                "SELECT * FROM referrals WHERE referred_id = ?",
                (referred_id,)
            )
            if cursor.fetchone():
                return False
            
            # Add referral record
            cursor.execute("""
                INSERT INTO referrals (referrer_id, referred_id, timestamp, reward_amount)
                VALUES (?, ?, ?, ?)
            """, (referrer_id, referred_id, datetime.now().isoformat(), 100))
            
            # Give reward to referrer
            cursor.execute(
                "UPDATE users SET coins = coins + 100, total_referrals = total_referrals + 1 WHERE user_id = ?",
                (referrer_id,)
            )
            
            # Update referred user
            cursor.execute(
                "UPDATE users SET referred_by = ? WHERE user_id = ?",
                (referrer_id, referred_id)
            )
            
            conn.commit()
            return True
    
    def get_referral_count(self, user_id: int) -> int:
        """Get number of referrals for a user"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM referrals WHERE referrer_id = ?",
                (user_id,)
            )
            return cursor.fetchone()[0]
    
    def get_referrals(self, user_id: int) -> List[Dict]:
        """Get list of referrals for a user"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT r.*, u.username, u.first_name
                FROM referrals r
                JOIN users u ON r.referred_id = u.user_id
                WHERE r.referrer_id = ?
                ORDER BY r.timestamp DESC
            """, (user_id,))
            return [dict(row) for row in cursor.fetchall()]
    
    # ========================================================================
    # GUEST ACCOUNT MANAGEMENT
    # ========================================================================
    
    def add_guest(self, uid: str, password: str, region: str = 'PK') -> bool:
        """Add a guest account"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            table = f"guests_{region.upper()}"
            
            try:
                cursor.execute(f"""
                    INSERT INTO {table} (uid, password, region, added_date, owner)
                    VALUES (?, ?, ?, ?, 'SALAAR X SPENCER')
                """, (uid, password, region.upper(), datetime.now().isoformat()))
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False
    
    def get_guests(self, region: str = 'PK', limit: int = 500, active_only: bool = True) -> List[Dict]:
        """Get guest accounts for a region"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            table = f"guests_{region.upper()}"
            
            query = f"SELECT uid, password, region FROM {table}"
            if active_only:
                query += " WHERE is_active = 1"
            query += " ORDER BY total_likes_sent ASC LIMIT ?"
            
            cursor.execute(query, (limit,))
            return [dict(row) for row in cursor.fetchall()]
    
    def update_guest_usage(self, uid: str, region: str, success: bool):
        """Update guest usage statistics"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            table = f"guests_{region.upper()}"
            
            cursor.execute(f"""
                UPDATE {table} 
                SET last_used = ?, total_likes_sent = total_likes_sent + 1
                WHERE uid = ?
            """, (datetime.now().isoformat(), uid))
            conn.commit()
    
    def deactivate_guest(self, uid: str, region: str) -> bool:
        """Deactivate a guest account"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            table = f"guests_{region.upper()}"
            
            cursor.execute(f"UPDATE {table} SET is_active = 0 WHERE uid = ?", (uid,))
            conn.commit()
            return cursor.rowcount > 0
    
    def get_guest_count(self, region: str = None) -> int:
        """Get total number of guest accounts"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if region:
                table = f"guests_{region.upper()}"
                cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE is_active = 1")
            else:
                total = 0
                for r in ['PK', 'IND', 'BR', 'ID', 'TH', 'VN']:
                    cursor.execute(f"SELECT COUNT(*) FROM guests_{r} WHERE is_active = 1")
                    total += cursor.fetchone()[0]
                return total
            
            return cursor.fetchone()[0]
    
    # ========================================================================
    # HISTORY AND LOGGING
    # ========================================================================
    
    def log_likes(self, user_id: int, target_uid: str, region: str, 
                  likes_sent: int, likes_success: int, duration: float) -> bool:
        """Log likes history"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            speed = likes_success / duration if duration > 0 else 0
            
            cursor.execute("""
                INSERT INTO likes_history 
                (user_id, target_uid, region, likes_sent, likes_success, timestamp, duration, speed)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (user_id, target_uid, region, likes_sent, likes_success, 
                  datetime.now().isoformat(), duration, speed))
            
            cursor.execute(
                "UPDATE users SET total_likes_sent = total_likes_sent + ? WHERE user_id = ?",
                (likes_success, user_id)
            )
            
            # Update total likes in settings
            cursor.execute("SELECT value FROM settings WHERE key = 'total_likes'")
            total_likes = int(cursor.fetchone()[0]) + likes_success
            cursor.execute(
                "UPDATE settings SET value = ? WHERE key = 'total_likes'",
                (str(total_likes),)
            )
            
            conn.commit()
            return True
    
    def log_visitors(self, user_id: int, target_uid: str, region: str,
                     visitors_sent: int, visitors_success: int, duration: float) -> bool:
        """Log visitors history"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            speed = visitors_success / duration if duration > 0 else 0
            
            cursor.execute("""
                INSERT INTO visitors_history 
                (user_id, target_uid, region, visitors_sent, visitors_success, timestamp, duration, speed)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (user_id, target_uid, region, visitors_sent, visitors_success,
                  datetime.now().isoformat(), duration, speed))
            
            cursor.execute(
                "UPDATE users SET total_visitors_sent = total_visitors_sent + ? WHERE user_id = ?",
                (visitors_success, user_id)
            )
            
            # Update total visitors in settings
            cursor.execute("SELECT value FROM settings WHERE key = 'total_visitors'")
            total_visitors = int(cursor.fetchone()[0]) + visitors_success
            cursor.execute(
                "UPDATE settings SET value = ? WHERE key = 'total_visitors'",
                (str(total_visitors),)
            )
            
            conn.commit()
            return True
    
    def log_spam(self, user_id: int, target_uid: str, region: str,
                 spam_sent: int, spam_success: int, duration: float) -> bool:
        """Log spam history"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            speed = spam_success / duration if duration > 0 else 0
            
            cursor.execute("""
                INSERT INTO spam_history 
                (user_id, target_uid, region, spam_sent, spam_success, timestamp, duration, speed)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (user_id, target_uid, region, spam_sent, spam_success,
                  datetime.now().isoformat(), duration, speed))
            
            cursor.execute(
                "UPDATE users SET total_spam_sent = total_spam_sent + ? WHERE user_id = ?",
                (spam_success, user_id)
            )
            
            # Update total spam in settings
            cursor.execute("SELECT value FROM settings WHERE key = 'total_spam'")
            total_spam = int(cursor.fetchone()[0]) + spam_success
            cursor.execute(
                "UPDATE settings SET value = ? WHERE key = 'total_spam'",
                (str(total_spam),)
            )
            
            conn.commit()
            return True
    
    def log_command(self, user_id: int, command: str, duration: float = 0, success: bool = True) -> bool:
        """Log command usage"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO commands_usage (command, user_id, timestamp, duration, success)
                VALUES (?, ?, ?, ?, ?)
            """, (command, user_id, datetime.now().isoformat(), duration, 1 if success else 0))
            
            cursor.execute(
                "UPDATE users SET total_commands_used = total_commands_used + 1, last_active = ? WHERE user_id = ?",
                (datetime.now().isoformat(), user_id)
            )
            conn.commit()
            return True
    
    # ========================================================================
    # DAILY LIMITS
    # ========================================================================
    
    def get_daily_stats(self, target_uid: str, region: str = 'PK') -> Dict[str, int]:
        """Get daily stats for a target UID"""
        today = datetime.now().date().isoformat()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT likes_sent, visitors_sent, spam_sent 
                FROM daily_limits 
                WHERE target_uid = ? AND region = ? AND date = ?
            """, (target_uid, region, today))
            
            result = cursor.fetchone()
            if result:
                return {
                    'likes': result[0],
                    'visitors': result[1],
                    'spam': result[2]
                }
            return {'likes': 0, 'visitors': 0, 'spam': 0}
    
    def update_daily_stats(self, target_uid: str, region: str, 
                          likes: int = 0, visitors: int = 0, spam: int = 0) -> bool:
        """Update daily stats for a target UID"""
        today = datetime.now().date().isoformat()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO daily_limits (target_uid, region, date, likes_sent, visitors_sent, spam_sent)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(target_uid, region, date) DO UPDATE SET
                likes_sent = likes_sent + ?,
                visitors_sent = visitors_sent + ?,
                spam_sent = spam_sent + ?
            """, (target_uid, region, today, likes, visitors, spam, likes, visitors, spam))
            conn.commit()
            return True
    
    # ========================================================================
    # VIP MANAGEMENT
    # ========================================================================
    
    def set_vip(self, user_id: int, days: int) -> bool:
        """Set VIP status for a user"""
        expiry = (datetime.now() + timedelta(days=days)).isoformat()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users SET is_vip = 1, vip_expiry = ? WHERE user_id = ?
            """, (expiry, user_id))
            conn.commit()
            return cursor.rowcount > 0
    
    def remove_vip(self, user_id: int) -> bool:
        """Remove VIP status from a user"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users SET is_vip = 0, vip_expiry = NULL WHERE user_id = ?
            """, (user_id,))
            conn.commit()
            return cursor.rowcount > 0
    
    def check_vip_expiry(self):
        """Check and expire VIP statuses"""
        now = datetime.now().isoformat()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users SET is_vip = 0, vip_expiry = NULL
                WHERE is_vip = 1 AND vip_expiry < ?
            """, (now,))
            conn.commit()
            return cursor.rowcount
    
    def get_vip_users(self) -> List[Dict]:
        """Get all VIP users"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT user_id, username, coins, vip_expiry
                FROM users WHERE is_vip = 1
                ORDER BY vip_expiry ASC
            """)
            return [dict(row) for row in cursor.fetchall()]
    
    # ========================================================================
    # FEEDBACK MANAGEMENT
    # ========================================================================
    
    def add_feedback(self, user_id: int, message: str, rating: int = 5) -> int:
        """Add user feedback"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO feedback (user_id, message, rating, timestamp)
                VALUES (?, ?, ?, ?)
            """, (user_id, message, rating, datetime.now().isoformat()))
            conn.commit()
            return cursor.lastrowid
    
    def get_feedback(self, limit: int = 50, resolved: bool = None) -> List[Dict]:
        """Get user feedback"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM feedback"
            params = []
            
            if resolved is not None:
                query += " WHERE is_resolved = ?"
                params.append(1 if resolved else 0)
            
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def resolve_feedback(self, feedback_id: int, resolved_by: int) -> bool:
        """Mark feedback as resolved"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE feedback 
                SET is_resolved = 1, resolved_by = ?, resolved_at = ?
                WHERE id = ?
            """, (resolved_by, datetime.now().isoformat(), feedback_id))
            conn.commit()
            return cursor.rowcount > 0
    
    # ========================================================================
    # ANNOUNCEMENTS
    # ========================================================================
    
    def add_announcement(self, message: str, sent_by: int, sent_to_count: int) -> int:
        """Add an announcement record"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO announcements (message, sent_by, sent_to_count, timestamp)
                VALUES (?, ?, ?, ?)
            """, (message, sent_by, sent_to_count, datetime.now().isoformat()))
            conn.commit()
            return cursor.lastrowid
    
    def get_announcements(self, limit: int = 20) -> List[Dict]:
        """Get recent announcements"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM announcements 
                ORDER BY timestamp DESC 
                LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]
    
    # ========================================================================
    # BLACKLIST MANAGEMENT
    # ========================================================================
    
    def add_to_blacklist(self, uid: str, region: str, reason: str, added_by: int) -> bool:
        """Add UID to blacklist"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO blacklist (uid, region, reason, added_by, added_date)
                VALUES (?, ?, ?, ?, ?)
            """, (uid, region, reason, added_by, datetime.now().isoformat()))
            conn.commit()
            return True
    
    def remove_from_blacklist(self, uid: str, region: str) -> bool:
        """Remove UID from blacklist"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM blacklist WHERE uid = ? AND region = ?
            """, (uid, region))
            conn.commit()
            return cursor.rowcount > 0
    
    def is_blacklisted(self, uid: str, region: str) -> bool:
        """Check if UID is blacklisted"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 1 FROM blacklist WHERE uid = ? AND region = ?
            """, (uid, region))
            return cursor.fetchone() is not None
    
    def get_blacklist(self) -> List[Dict]:
        """Get all blacklisted UIDs"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM blacklist ORDER BY added_date DESC")
            return [dict(row) for row in cursor.fetchall()]
    
    # ========================================================================
    # SETTINGS MANAGEMENT
    # ========================================================================
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a setting value"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
            result = cursor.fetchone()
            
            if result:
                # Try to parse JSON
                try:
                    return json.loads(result[0])
                except:
                    return result[0]
            return default
    
    def set_setting(self, key: str, value: Any, updated_by: int = None) -> bool:
        """Set a setting value"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Convert to JSON if needed
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            else:
                value = str(value)
            
            cursor.execute("""
                INSERT OR REPLACE INTO settings (key, value, updated_at, updated_by)
                VALUES (?, ?, ?, ?)
            """, (key, value, datetime.now().isoformat(), updated_by))
            conn.commit()
            return True
    
    def get_all_settings(self) -> Dict[str, Any]:
        """Get all settings"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT key, value FROM settings")
            result = {}
            for row in cursor.fetchall():
                try:
                    result[row[0]] = json.loads(row[1])
                except:
                    result[row[0]] = row[1]
            return result
    
    # ========================================================================
    # ANALYTICS
    # ========================================================================
    
    def get_daily_analytics(self, date: str = None) -> Dict[str, Any]:
        """Get analytics for a specific date"""
        if not date:
            date = datetime.now().date().isoformat()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get daily stats
            cursor.execute("""
                SELECT 
                    COUNT(DISTINCT user_id) as active_users,
                    SUM(likes_sent) as total_likes,
                    SUM(visitors_sent) as total_visitors,
                    SUM(spam_sent) as total_spam
                FROM likes_history 
                WHERE date(timestamp) = ?
            """, (date,))
            result = cursor.fetchone()
            
            # Get new users
            cursor.execute("""
                SELECT COUNT(*) FROM users WHERE date(join_date) = ?
            """, (date,))
            new_users = cursor.fetchone()[0]
            
            return {
                'date': date,
                'active_users': result[0] or 0,
                'total_likes': result[1] or 0,
                'total_visitors': result[2] or 0,
                'total_spam': result[3] or 0,
                'new_users': new_users
            }
    
    def get_weekly_analytics(self) -> List[Dict]:
        """Get weekly analytics"""
        results = []
        for i in range(7):
            date = (datetime.now() - timedelta(days=i)).date().isoformat()
            results.append(self.get_daily_analytics(date))
        return results
    
    def get_monthly_analytics(self) -> List[Dict]:
        """Get monthly analytics"""
        results = []
        for i in range(30):
            date = (datetime.now() - timedelta(days=i)).date().isoformat()
            results.append(self.get_daily_analytics(date))
        return results
    
    # ========================================================================
    # BACKUP AND RESTORE
    # ========================================================================
    
    def backup(self, backup_path: str = None) -> str:
        """Create database backup"""
        if not backup_path:
            backup_path = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        
        with self.get_connection() as conn:
            # Backup using SQLite backup API
            backup_conn = sqlite3.connect(backup_path)
            conn.backup(backup_conn)
            backup_conn.close()
        
        logger.info(f"Database backed up to {backup_path}")
        return backup_path
    
    def restore(self, backup_path: str) -> bool:
        """Restore database from backup"""
        if not os.path.exists(backup_path):
            logger.error(f"Backup file {backup_path} not found")
            return False
        
        try:
            # Close all connections
            while not self.connection_pool.empty():
                conn = self.connection_pool.get()
                conn.close()
            
            # Restore backup
            shutil.copy2(backup_path, self.db_file)
            
            # Reinitialize connection pool
            self._init_connection_pool()
            
            logger.info(f"Database restored from {backup_path}")
            return True
        except Exception as e:
            logger.error(f"Restore failed: {e}")
            return False
    
    # ========================================================================
    # STATISTICS
    # ========================================================================
    
    def get_bot_stats(self) -> Dict[str, Any]:
        """Get complete bot statistics"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # User stats
            cursor.execute("SELECT COUNT(*) FROM users")
            total_users = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM users WHERE is_vip = 1")
            vip_users = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM users WHERE is_banned = 1")
            banned_users = cursor.fetchone()[0]
            
            # Action stats
            cursor.execute("SELECT SUM(coins) FROM users")
            total_coins = cursor.fetchone()[0] or 0
            
            cursor.execute("SELECT SUM(total_likes_sent) FROM users")
            total_likes = cursor.fetchone()[0] or 0
            
            cursor.execute("SELECT SUM(total_visitors_sent) FROM users")
            total_visitors = cursor.fetchone()[0] or 0
            
            cursor.execute("SELECT SUM(total_spam_sent) FROM users")
            total_spam = cursor.fetchone()[0] or 0
            
            cursor.execute("SELECT SUM(total_commands_used) FROM users")
            total_commands = cursor.fetchone()[0] or 0
            
            cursor.execute("SELECT COUNT(*) FROM referrals")
            total_referrals = cursor.fetchone()[0]
            
            # Daily stats
            today = datetime.now().date().isoformat()
            cursor.execute("""
                SELECT COUNT(DISTINCT user_id) FROM commands_usage 
                WHERE date(timestamp) = ?
            """, (today,))
            active_today = cursor.fetchone()[0] or 0
            
            # Guest stats
            total_guests = 0
            for region in ['PK', 'IND', 'BR', 'ID', 'TH', 'VN']:
                cursor.execute(f"SELECT COUNT(*) FROM guests_{region} WHERE is_active = 1")
                total_guests += cursor.fetchone()[0]
            
            return {
                'total_users': total_users,
                'vip_users': vip_users,
                'banned_users': banned_users,
                'total_coins': total_coins,
                'total_likes': total_likes,
                'total_visitors': total_visitors,
                'total_spam': total_spam,
                'total_commands': total_commands,
                'total_referrals': total_referrals,
                'active_today': active_today,
                'total_guests': total_guests
            }
    
    # ========================================================================
    # CLEANUP
    # ========================================================================
    
    def cleanup_old_records(self, days: int = 30):
        """Delete old records from history tables"""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            tables = ['likes_history', 'visitors_history', 'spam_history', 'commands_usage']
            for table in tables:
                cursor.execute(f"DELETE FROM {table} WHERE timestamp < ?", (cutoff,))
            
            conn.commit()
            logger.info(f"Cleaned up records older than {days} days")
    
    def shutdown(self):
        """Shutdown database manager"""
        logger.info("Shutting down database manager...")
        
        # Close all connections
        while not self.connection_pool.empty():
            try:
                conn = self.connection_pool.get_nowait()
                conn.close()
            except queue.Empty:
                break
        
        logger.info("Database manager shutdown complete")