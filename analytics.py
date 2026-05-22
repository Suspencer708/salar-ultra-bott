"""
Analytics Engine for SALAAR X SPENCER ULTRA BOT
Collects and analyzes bot usage statistics
"""

import time
import threading
import sqlite3
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, List, Optional, Any

from database import DatabaseManager
from config import DATABASE_FILE
from logger import get_logger

logger = get_logger(__name__)


class Analytics:
    """Complete analytics engine for bot statistics"""

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
        self.collection_thread = None
        self.is_collecting = False

        self._init_analytics_tables()
        self._start_collection_thread()

        logger.info("Analytics engine initialized")

    def _init_analytics_tables(self):
        """Initialize analytics tables"""
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS analytics_daily (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT UNIQUE,
                total_users INTEGER DEFAULT 0,
                active_users INTEGER DEFAULT 0,
                new_users INTEGER DEFAULT 0,
                total_likes INTEGER DEFAULT 0,
                total_visitors INTEGER DEFAULT 0,
                total_spam INTEGER DEFAULT 0,
                total_commands INTEGER DEFAULT 0,
                total_coins_earned INTEGER DEFAULT 0,
                total_coins_spent INTEGER DEFAULT 0,
                avg_response_time REAL DEFAULT 0,
                peak_concurrent INTEGER DEFAULT 0
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS analytics_hourly (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hour TEXT UNIQUE,
                commands_count INTEGER DEFAULT 0,
                likes_count INTEGER DEFAULT 0,
                visitors_count INTEGER DEFAULT 0,
                spam_count INTEGER DEFAULT 0,
                unique_users INTEGER DEFAULT 0
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS analytics_regions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                region TEXT,
                date TEXT,
                likes_sent INTEGER DEFAULT 0,
                visitors_sent INTEGER DEFAULT 0,
                spam_sent INTEGER DEFAULT 0,
                UNIQUE(region, date)
            )
        """)

        conn.commit()
        conn.close()
        logger.info("Analytics tables initialized")

    def _start_collection_thread(self):
        """Start background analytics collection"""
        def collect_loop():
            self.is_collecting = True
            while self.is_collecting:
                try:
                    self.collect_daily_stats()
                    time.sleep(3600)  # Collect every hour
                except Exception as e:
                    logger.error(f"Analytics collection error: {e}")
                    time.sleep(60)

        self.collection_thread = threading.Thread(target=collect_loop, daemon=True)
        self.collection_thread.start()
        logger.info("Analytics collection thread started")

    def collect_daily_stats(self):
        """Collect daily statistics"""
        today = datetime.now().date().isoformat()
        yesterday = (datetime.now() - timedelta(days=1)).date().isoformat()

        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        # Get today's stats
        cursor.execute("SELECT COUNT(*) FROM users WHERE date(join_date) = ?", (today,))
        new_users = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(DISTINCT user_id) FROM commands_usage WHERE date(timestamp) = ?", (today,))
        active_users = cursor.fetchone()[0]

        cursor.execute("SELECT SUM(likes_sent) FROM likes_history WHERE date(timestamp) = ?", (today,))
        total_likes = cursor.fetchone()[0] or 0

        cursor.execute("SELECT SUM(visitors_sent) FROM visitors_history WHERE date(timestamp) = ?", (today,))
        total_visitors = cursor.fetchone()[0] or 0

        cursor.execute("SELECT SUM(spam_sent) FROM spam_history WHERE date(timestamp) = ?", (today,))
        total_spam = cursor.fetchone()[0] or 0

        cursor.execute("SELECT COUNT(*) FROM commands_usage WHERE date(timestamp) = ?", (today,))
        total_commands = cursor.fetchone()[0] or 0

        # Get coin stats
        cursor.execute("SELECT SUM(total_earned_coins) FROM users WHERE date(join_date) = ?", (today,))
        coins_earned = cursor.fetchone()[0] or 0

        cursor.execute("SELECT SUM(total_spent_coins) FROM users WHERE date(join_date) = ?", (today,))
        coins_spent = cursor.fetchone()[0] or 0

        # Get total users
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]

        # Insert or update
        cursor.execute("""
            INSERT OR REPLACE INTO analytics_daily 
            (date, total_users, active_users, new_users, total_likes, total_visitors, 
             total_spam, total_commands, total_coins_earned, total_coins_spent)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (today, total_users, active_users, new_users, total_likes, total_visitors,
              total_spam, total_commands, coins_earned, coins_spent))

        conn.commit()
        conn.close()

        logger.info(f"Daily analytics collected for {today}")

    def collect_hourly_stats(self, commands: List[Dict]):
        """Collect hourly statistics"""
        current_hour = datetime.now().strftime('%Y-%m-%d %H:00:00')

        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        likes_count = sum(1 for c in commands if c.get('command') == 'like')
        visitors_count = sum(1 for c in commands if c.get('command') == 'visit')
        spam_count = sum(1 for c in commands if c.get('command') == 'spam')
        unique_users = len(set(c.get('user_id') for c in commands))

        cursor.execute("""
            INSERT OR REPLACE INTO analytics_hourly 
            (hour, commands_count, likes_count, visitors_count, spam_count, unique_users)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (current_hour, len(commands), likes_count, visitors_count, spam_count, unique_users))

        conn.commit()
        conn.close()

    def collect_region_stats(self, region: str, action: str, count: int):
        """Collect region-specific statistics"""
        today = datetime.now().date().isoformat()

        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        if action == 'like':
            cursor.execute("""
                INSERT INTO analytics_regions (region, date, likes_sent)
                VALUES (?, ?, ?)
                ON CONFLICT(region, date) DO UPDATE SET likes_sent = likes_sent + ?
            """, (region, today, count, count))
        elif action == 'visit':
            cursor.execute("""
                INSERT INTO analytics_regions (region, date, visitors_sent)
                VALUES (?, ?, ?)
                ON CONFLICT(region, date) DO UPDATE SET visitors_sent = visitors_sent + ?
            """, (region, today, count, count))
        elif action == 'spam':
            cursor.execute("""
                INSERT INTO analytics_regions (region, date, spam_sent)
                VALUES (?, ?, ?)
                ON CONFLICT(region, date) DO UPDATE SET spam_sent = spam_sent + ?
            """, (region, today, count, count))

        conn.commit()
        conn.close()

    def get_daily_analytics(self, days: int = 7) -> List[Dict]:
        """Get daily analytics for last N days"""
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM analytics_daily 
            ORDER BY date DESC 
            LIMIT ?
        """, (days,))

        results = cursor.fetchall()
        conn.close()

        return [
            {
                'date': r[1],
                'total_users': r[2],
                'active_users': r[3],
                'new_users': r[4],
                'total_likes': r[5],
                'total_visitors': r[6],
                'total_spam': r[7],
                'total_commands': r[8],
                'total_coins_earned': r[9],
                'total_coins_spent': r[10]
            }
            for r in results
        ]

    def get_hourly_analytics(self, hours: int = 24) -> List[Dict]:
        """Get hourly analytics for last N hours"""
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM analytics_hourly 
            ORDER BY hour DESC 
            LIMIT ?
        """, (hours,))

        results = cursor.fetchall()
        conn.close()

        return [
            {
                'hour': r[1],
                'commands_count': r[2],
                'likes_count': r[3],
                'visitors_count': r[4],
                'spam_count': r[5],
                'unique_users': r[6]
            }
            for r in results
        ]

    def get_region_analytics(self, days: int = 7) -> Dict:
        """Get region-wise analytics"""
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT region, SUM(likes_sent) as likes, SUM(visitors_sent) as visitors, SUM(spam_sent) as spam
            FROM analytics_regions 
            WHERE date >= date('now', ?)
            GROUP BY region
        """, (f'-{days} days',))

        results = cursor.fetchall()
        conn.close()

        return {
            r[0]: {'likes': r[1] or 0, 'visitors': r[2] or 0, 'spam': r[3] or 0}
            for r in results
        }

    def get_growth_metrics(self) -> Dict:
        """Get user growth metrics"""
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        # Last 7 days growth
        cursor.execute("""
            SELECT 
                SUM(new_users) as total_new,
                AVG(new_users) as avg_new,
                MAX(new_users) as peak_new
            FROM analytics_daily 
            WHERE date >= date('now', '-7 days')
        """)
        result = cursor.fetchone()

        # User retention
        cursor.execute("""
            SELECT COUNT(DISTINCT user_id) FROM commands_usage 
            WHERE date(timestamp) >= date('now', '-7 days')
        """)
        active_last_7 = cursor.fetchone()[0] or 0

        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0] or 0

        conn.close()

        return {
            'total_users': total_users,
            'new_last_7_days': result[0] or 0,
            'avg_daily_new': round(result[1] or 0, 2),
            'peak_daily_new': result[2] or 0,
            'active_last_7_days': active_last_7,
            'retention_rate_7d': round(active_last_7 / max(total_users, 1) * 100, 2)
        }

    def get_performance_metrics(self) -> Dict:
        """Get performance metrics"""
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        # Average response time
        cursor.execute("SELECT AVG(duration) FROM commands_usage WHERE duration IS NOT NULL")
        avg_response = cursor.fetchone()[0] or 0

        # Success rate
        cursor.execute("""
            SELECT 
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as success,
                COUNT(*) as total
            FROM commands_usage
        """)
        result = cursor.fetchone()
        success_rate = round(result[0] / max(result[1], 1) * 100, 2) if result[1] > 0 else 0

        # Most used commands
        cursor.execute("""
            SELECT command, COUNT(*) as count
            FROM commands_usage
            GROUP BY command
            ORDER BY count DESC
            LIMIT 5
        """)
        top_commands = {r[0]: r[1] for r in cursor.fetchall()}

        conn.close()

        return {
            'avg_response_time_ms': round(avg_response * 1000, 2),
            'success_rate': success_rate,
            'top_commands': top_commands
        }

    def get_economy_metrics(self) -> Dict:
        """Get economy metrics"""
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT 
                SUM(total_coins_earned) as total_earned,
                SUM(total_coins_spent) as total_spent,
                AVG(total_coins_earned) as avg_daily_earned
            FROM analytics_daily
        """)
        result = cursor.fetchone()

        cursor.execute("SELECT AVG(coins) FROM users")
        avg_coins_per_user = cursor.fetchone()[0] or 0

        conn.close()

        return {
            'total_coins_earned_all_time': result[0] or 0,
            'total_coins_spent_all_time': result[1] or 0,
            'avg_daily_coins_earned': round(result[2] or 0, 2),
            'avg_coins_per_user': round(avg_coins_per_user, 2)
        }

    def shutdown(self):
        """Shutdown analytics engine"""
        self.is_collecting = False
        logger.info("Analytics engine shutdown")