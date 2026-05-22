"""
Webhook Handler for SALAAR X SPENCER ULTRA BOT
Sends notifications for important events
"""

import threading
import requests
import json
from typing import Dict, List, Optional
from datetime import datetime

from logger import get_logger

logger = get_logger(__name__)


class WebhookHandler:
    """Handles webhook notifications for events"""

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

        self.webhooks = {}
        self.event_handlers = {}
        self._load_webhooks()

        logger.info("WebhookHandler initialized")

    def _load_webhooks(self):
        """Load webhooks from database"""
        import sqlite3
        from config import DATABASE_FILE

        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        cursor.execute("SELECT user_id, url, event_type FROM webhooks WHERE is_active = 1")
        for row in cursor.fetchall():
            user_id, url, event_type = row
            if user_id not in self.webhooks:
                self.webhooks[user_id] = []
            self.webhooks[user_id].append({'url': url, 'event_type': event_type})

        conn.close()
        logger.info(f"Loaded {sum(len(v) for v in self.webhooks.values())} webhooks")

    def register_webhook(self, user_id: int, url: str, event_type: str) -> bool:
        """Register a webhook for a user"""
        import sqlite3
        from config import DATABASE_FILE

        try:
            conn = sqlite3.connect(DATABASE_FILE)
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO webhooks (user_id, url, event_type, created_at, is_active)
                VALUES (?, ?, ?, ?, 1)
            """, (user_id, url, event_type, datetime.now().isoformat()))

            conn.commit()
            conn.close()

            if user_id not in self.webhooks:
                self.webhooks[user_id] = []
            self.webhooks[user_id].append({'url': url, 'event_type': event_type})

            logger.info(f"Webhook registered for user {user_id}: {url}")
            return True

        except Exception as e:
            logger.error(f"Webhook registration failed: {e}")
            return False

    def unregister_webhook(self, user_id: int, url: str = None) -> bool:
        """Unregister webhook for a user"""
        import sqlite3
        from config import DATABASE_FILE

        try:
            conn = sqlite3.connect(DATABASE_FILE)
            cursor = conn.cursor()

            if url:
                cursor.execute("DELETE FROM webhooks WHERE user_id = ? AND url = ?", (user_id, url))
            else:
                cursor.execute("DELETE FROM webhooks WHERE user_id = ?", (user_id,))

            conn.commit()
            conn.close()

            if user_id in self.webhooks:
                if url:
                    self.webhooks[user_id] = [w for w in self.webhooks[user_id] if w['url'] != url]
                else:
                    del self.webhooks[user_id]

            logger.info(f"Webhook unregistered for user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Webhook unregistration failed: {e}")
            return False

    def send_event(self, user_id: int, event_type: str, data: Dict):
        """Send event to webhooks"""
        if user_id not in self.webhooks:
            return

        payload = {
            'event': event_type,
            'user_id': user_id,
            'timestamp': datetime.now().isoformat(),
            'data': data
        }

        for webhook in self.webhooks[user_id]:
            if webhook['event_type'] != event_type and webhook['event_type'] != '*':
                continue

            try:
                response = requests.post(
                    webhook['url'],
                    json=payload,
                    timeout=5,
                    headers={'Content-Type': 'application/json'}
                )
                if response.status_code != 200:
                    logger.warning(f"Webhook {webhook['url']} returned {response.status_code}")
            except Exception as e:
                logger.error(f"Webhook send failed: {e}")

    def send_like_event(self, user_id: int, target_uid: str, success_count: int, total_count: int):
        """Send like completion event"""
        self.send_event(user_id, 'like_completed', {
            'target_uid': target_uid,
            'success_count': success_count,
            'total_count': total_count,
            'success_rate': round(success_count / max(total_count, 1) * 100, 2)
        })

    def send_daily_event(self, user_id: int, reward: int, streak: int):
        """Send daily claim event"""
        self.send_event(user_id, 'daily_claimed', {
            'reward': reward,
            'streak': streak,
            'balance': self._get_user_balance(user_id)
        })

    def _get_user_balance(self, user_id: int) -> int:
        """Get user's coin balance"""
        from database import DatabaseManager
        db = DatabaseManager()
        user = db.get_user(user_id)
        return user['coins']