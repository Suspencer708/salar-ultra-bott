"""
Thread Pool for SALAAR X SPENCER ULTRA BOT
Manages concurrent task execution with priority queue
"""

import threading
import queue
import time
from typing import Callable, Any, List, Dict, Optional
from enum import Enum

from logger import get_logger

logger = get_logger(__name__)


class Priority(Enum):
    LOW = 3
    NORMAL = 2
    HIGH = 1
    CRITICAL = 0


class Task:
    """Task wrapper with priority"""

    def __init__(self, func: Callable, args: tuple = None, kwargs: dict = None,
                 priority: Priority = Priority.NORMAL, task_id: str = None):
        self.func = func
        self.args = args or ()
        self.kwargs = kwargs or {}
        self.priority = priority.value
        self.task_id = task_id or str(time.time())
        self.created_at = time.time()
        self.result = None
        self.error = None
        self.completed = False

    def __lt__(self, other):
        return self.priority < other.priority


class ThreadPool:
    """Thread pool with priority queue"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
        return cls._instance

    def __init__(self, max_workers: int = 500):
        if self._initialized:
            return
        self._initialized = True

        self.max_workers = max_workers
        self.task_queue = queue.PriorityQueue()
        self.workers = []
        self.is_running = True
        self.active_tasks = 0
        self.completed_tasks = 0
        self.failed_tasks = 0
        self.lock = threading.RLock()

        self._start_workers()
        logger.info(f"ThreadPool initialized with {max_workers} workers")

    def _start_workers(self):
        """Start worker threads"""
        for i in range(self.max_workers):
            worker = threading.Thread(target=self._worker_loop, name=f"Worker-{i}", daemon=True)
            worker.start()
            self.workers.append(worker)

        logger.info(f"Started {self.max_workers} worker threads")

    def _worker_loop(self):
        """Worker thread loop"""
        while self.is_running:
            try:
                task = self.task_queue.get(timeout=1)
                if task is None:
                    continue

                with self.lock:
                    self.active_tasks += 1

                try:
                    result = task.func(*task.args, **task.kwargs)
                    task.result = result
                    with self.lock:
                        self.completed_tasks += 1
                except Exception as e:
                    task.error = str(e)
                    with self.lock:
                        self.failed_tasks += 1
                    logger.error(f"Task {task.task_id} failed: {e}")
                finally:
                    task.completed = True
                    with self.lock:
                        self.active_tasks -= 1
                    self.task_queue.task_done()

            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Worker error: {e}")

    def submit(self, func: Callable, *args, priority: Priority = Priority.NORMAL,
               task_id: str = None, **kwargs) -> str:
        """Submit a task to the pool"""
        task = Task(func, args, kwargs, priority, task_id)
        self.task_queue.put(task)
        return task.task_id

    def submit_and_wait(self, func: Callable, *args, timeout: float = None,
                        priority: Priority = Priority.NORMAL, **kwargs) -> Any:
        """Submit a task and wait for result"""
        task_id = self.submit(func, *args, priority=priority, **kwargs)

        start_time = time.time()
        while True:
            if timeout and time.time() - start_time > timeout:
                raise TimeoutError(f"Task {task_id} timed out")

            # Find task in queue (simplified - in production, track tasks in dict)
            time.sleep(0.01)

    def map(self, func: Callable, items: List, priority: Priority = Priority.NORMAL) -> List:
        """Map a function over a list with concurrency"""
        futures = []
        for item in items:
            task_id = self.submit(func, item, priority=priority)
            futures.append(task_id)

        # Wait for all (simplified)
        return futures

    def get_stats(self) -> Dict:
        """Get thread pool statistics"""
        with self.lock:
            return {
                'max_workers': self.max_workers,
                'active_workers': len([w for w in self.workers if w.is_alive()]),
                'queue_size': self.task_queue.qsize(),
                'active_tasks': self.active_tasks,
                'completed_tasks': self.completed_tasks,
                'failed_tasks': self.failed_tasks,
                'total_tasks': self.completed_tasks + self.failed_tasks
            }

    def shutdown(self, wait: bool = True):
        """Shutdown thread pool"""
        self.is_running = False

        if wait:
            self.task_queue.join()

        for worker in self.workers:
            worker.join(timeout=5)

        logger.info("ThreadPool shutdown complete")