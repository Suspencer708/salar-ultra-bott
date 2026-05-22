"""
Backup Manager for SALAAR X SPENCER ULTRA BOT
Automatic database backup with compression and rotation
"""

import os
import shutil
import gzip
import threading
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional

from config import DATABASE_FILE, BACKUP_PATH, BACKUP_INTERVAL, BACKUP_RETENTION_DAYS
from logger import get_logger

logger = get_logger(__name__)


class BackupManager:
    """Complete backup management system"""

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

        self.backup_path = BACKUP_PATH
        self.db_file = DATABASE_FILE
        self.is_backing_up = False

        self._ensure_backup_dir()
        self._start_backup_thread()

        logger.info("BackupManager initialized")

    def _ensure_backup_dir(self):
        """Ensure backup directory exists"""
        if not os.path.exists(self.backup_path):
            os.makedirs(self.backup_path)
            logger.info(f"Created backup directory: {self.backup_path}")

    def _start_backup_thread(self):
        """Start automatic backup thread"""
        def backup_loop():
            while True:
                try:
                    time.sleep(BACKUP_INTERVAL)
                    self.create_backup(auto=True)
                    self.cleanup_old_backups()
                except Exception as e:
                    logger.error(f"Auto backup error: {e}")

        thread = threading.Thread(target=backup_loop, daemon=True)
        thread.start()
        logger.info("Auto backup thread started")

    def create_backup(self, auto: bool = False) -> Optional[str]:
        """Create a database backup"""
        if self.is_backing_up:
            logger.warning("Backup already in progress")
            return None

        self.is_backing_up = True

        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_name = f"backup_{timestamp}.db.gz"
            backup_file = os.path.join(self.backup_path, backup_name)

            # Create compressed backup
            with open(self.db_file, 'rb') as f_in:
                with gzip.open(backup_file, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)

            file_size = os.path.getsize(backup_file) / 1024  # KB
            logger.info(f"Backup created: {backup_name} ({file_size:.2f} KB)")

            return backup_file

        except Exception as e:
            logger.error(f"Backup creation failed: {e}")
            return None

        finally:
            self.is_backing_up = False

    def restore_backup(self, backup_file: str) -> bool:
        """Restore database from backup"""
        backup_path = os.path.join(self.backup_path, backup_file)

        if not os.path.exists(backup_path):
            logger.error(f"Backup file not found: {backup_file}")
            return False

        try:
            # Close database connections first
            # (This will be handled by the main bot)

            # Restore from backup
            with gzip.open(backup_path, 'rb') as f_in:
                with open(self.db_file, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)

            logger.info(f"Database restored from: {backup_file}")
            return True

        except Exception as e:
            logger.error(f"Restore failed: {e}")
            return False

    def list_backups(self) -> List[Dict]:
        """List all available backups"""
        backups = []

        if not os.path.exists(self.backup_path):
            return backups

        for file in os.listdir(self.backup_path):
            if file.endswith('.db.gz'):
                file_path = os.path.join(self.backup_path, file)
                stat = os.stat(file_path)

                backups.append({
                    'name': file,
                    'size_kb': round(stat.st_size / 1024, 2),
                    'created_at': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    'path': file_path
                })

        # Sort by creation date (newest first)
        backups.sort(key=lambda x: x['created_at'], reverse=True)

        return backups

    def cleanup_old_backups(self, days: int = BACKUP_RETENTION_DAYS):
        """Delete backups older than specified days"""
        cutoff = datetime.now() - timedelta(days=days)
        deleted_count = 0

        if not os.path.exists(self.backup_path):
            return

        for file in os.listdir(self.backup_path):
            if file.endswith('.db.gz'):
                file_path = os.path.join(self.backup_path, file)
                mtime = datetime.fromtimestamp(os.path.getmtime(file_path))

                if mtime < cutoff:
                    os.remove(file_path)
                    deleted_count += 1
                    logger.info(f"Deleted old backup: {file}")

        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} old backups")

    def get_backup_stats(self) -> Dict:
        """Get backup statistics"""
        backups = self.list_backups()

        total_size = sum(b['size_kb'] for b in backups)
        latest_backup = backups[0] if backups else None

        return {
            'total_backups': len(backups),
            'total_size_mb': round(total_size / 1024, 2),
            'latest_backup': latest_backup,
            'backup_path': self.backup_path,
            'retention_days': BACKUP_RETENTION_DAYS
        }