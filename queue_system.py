"""
Queue System for SALAAR X SPENCER ULTRA BOT
Manages action queues with priority and rate limiting
"""

import time
import threading
import queue
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime

from logger import get_logger

logger = get_logger(__name__)


class QueuePriority(Enum):
    LOW = 3
    NORMAL = 2
    HIGH = 1
    VIP = 0


@dataclass
class QueueItem:
    """Queue item with metadata"""
    user_id: int
    action: str
    target: str
    region: str
    count: int
    priority: QueuePriority = QueuePriority.NORMAL
    created_at: datetime = field(default_factory=datetime.now)
    status: str = 'pending'
    result: Dict = field(default_factory=dict)


class ActionQueue:
    """Priority queue for actions"""

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

        self.queues = {
            QueuePriority.VIP: queue.Queue(),
            QueuePriority.HIGH: queue.Queue(),
            QueuePriority.NORMAL: queue.Queue(),
            QueuePriority.LOW: queue.Queue()
        }

        self.active_items = {}
        self.completed_items = []
        self.processing = True
        self.lock = threading.RLock()

        self._start_processor()

        logger.info("ActionQueue initialized")

    def _start_processor(self):
        """Start queue processor thread"""
        def process_loop():
            while self.processing:
                try:
                    item = self._get_next_item()
                    if item:
                        self._process_item(item)
                except Exception as e:
                    logger.error(f"Queue processor error: {e}")
                time.sleep(0.01)

        thread = threading.Thread(target=process_loop, daemon=True)
        thread.start()
        logger.info("Queue processor started")

    def _get_next_item(self) -> Optional[QueueItem]:
        """Get next item by priority"""
        for priority in [QueuePriority.VIP, QueuePriority.HIGH,
                         QueuePriority.NORMAL, QueuePriority.LOW]:
            try:
                return self.queues[priority].get_nowait()
            except queue.Empty:
                continue
        return None

    def _process_item(self, item: QueueItem):
        """Process a queue item"""
        with self.lock:
            self.active_items[item.user_id] = item
            item.status = 'processing'

        try:
            # This will be handled by the actual sender
            from like_sender import LikeSender
            from visitor_sender import VisitorSender
            from spam_sender import SpamSender

            if item.action == 'like':
                sender = LikeSender()
                result = sender.send_likes(item.target, item.count, item.region, item.user_id)
            elif item.action == 'visit':
                sender = VisitorSender()
                result = sender.send_visitors(item.target, item.count, item.region, item.user_id)
            elif item.action == 'spam':
                sender = SpamSender()
                result = sender.send_spam(item.target, item.count, item.region, item.user_id)
            else:
                result = {'error': 'Unknown action'}

            item.result = result
            item.status = 'completed'

        except Exception as e:
            item.status = 'failed'
            item.result = {'error': str(e)}
            logger.error(f"Queue item processing failed: {e}")

        finally:
            with self.lock:
                if item.user_id in self.active_items:
                    del self.active_items[item.user_id]
                self.completed_items.append(item)

    def enqueue(self, user_id: int, action: str, target: str, region: str,
                count: int, priority: QueuePriority = QueuePriority.NORMAL) -> str:
        """Add item to queue"""
        item = QueueItem(
            user_id=user_id,
            action=action,
            target=target,
            region=region,
            count=count,
            priority=priority
        )

        self.queues[priority].put(item)
        logger.info(f"Enqueued {action} for user {user_id} with priority {priority.name}")

        return f"{user_id}_{action}_{int(time.time())}"

    def get_status(self, user_id: int) -> Dict:
        """Get queue status for a user"""
        with self.lock:
            if user_id in self.active_items:
                return {
                    'status': 'processing',
                    'item': self.active_items[user_id]
                }

            # Check if in queue
            for priority, q in self.queues.items():
                for item in list(q.queue):
                    if item.user_id == user_id:
                        return {
                            'status': 'queued',
                            'priority': priority.name,
                            'position': list(q.queue).index(item) + 1
                        }

            return {'status': 'idle'}

    def get_queue_length(self) -> Dict:
        """Get queue lengths by priority"""
        return {
            'vip': self.queues[QueuePriority.VIP].qsize(),
            'high': self.queues[QueuePriority.HIGH].qsize(),
            'normal': self.queues[QueuePriority.NORMAL].qsize(),
            'low': self.queues[QueuePriority.LOW].qsize(),
            'total': sum(q.qsize() for q in self.queues.values()),
            'active': len(self.active_items)
        }

    def clear(self):
        """Clear all queues"""
        with self.lock:
            for q in self.queues.values():
                while not q.empty():
                    try:
                        q.get_nowait()
                    except queue.Empty:
                        break
            self.active_items.clear()
            logger.info("All queues cleared")

    def shutdown(self):
        """Shutdown queue system"""
        self.processing = False
        logger.info("ActionQueue shutdown")