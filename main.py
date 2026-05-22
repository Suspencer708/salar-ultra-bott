"""
╔════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╗
║                                                                                         🔥 SALAAR X SPENCER ULTRA PRO MAX BOT 🔥                                                                                          ║
║                                                                                         Version: 8.0.0 | Total Lines: 50,000+ | Speed: ULTRA PRO MAX                                                                     ║
║                                                                                         Features: 6 Regions | 1000+ Guests | 500 Concurrent | Full Admin Panel                                                           ║
╚════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╝
"""

import os
import sys
import time
import signal
import threading
import logging
from datetime import datetime

# Import all modules
from config import BOT_TOKEN, ADMIN_IDS, VERSION, BOT_NAME, AUTHOR
from database import DatabaseManager, init_database
from api_client import APIClient
from guest_manager import GuestManager
from like_sender import LikeSender
from visitor_sender import VisitorSender
from spam_sender import SpamSender
from info_fetcher import InfoFetcher
from coin_system import CoinSystem
from referral_system import ReferralSystem
from admin_panel import AdminPanel
from user_commands import UserCommands
from cache_system import CacheSystem
from logger import setup_logger
from web_dashboard import WebDashboard
from analytics import Analytics
from backup_manager import BackupManager
from rate_limiter import RateLimiter
from thread_pool import ThreadPool
from queue_system import QueueSystem
from webhook_handler import WebhookHandler
from api_endpoints import APIEndpoints
from bot_handlers import BotHandlers
from utils import Utils
from constants import *

# ============================================================================
# MAIN BOT CLASS
# ============================================================================

class SalarUltraBot:
    """Main bot class - orchestrates all components"""
    
    def __init__(self):
        self.start_time = datetime.now()
        self.is_running = True
        self.components = {}
        
        # Initialize logger
        self.logger = setup_logger()
        
        # Initialize all components
        self.init_components()
        
        # Start background threads
        self.start_background_threads()
        
        self.logger.info(f"{BOT_NAME} v{VERSION} initialized successfully")
    
    def init_components(self):
        """Initialize all bot components"""
        self.logger.info("Initializing components...")
        
        # Core components
        self.components['database'] = DatabaseManager()
        self.components['cache'] = CacheSystem()
        self.components['rate_limiter'] = RateLimiter()
        self.components['thread_pool'] = ThreadPool()
        self.components['queue_system'] = QueueSystem()
        
        # Business components
        self.components['guest_manager'] = GuestManager()
        self.components['api_client'] = APIClient()
        self.components['like_sender'] = LikeSender()
        self.components['visitor_sender'] = VisitorSender()
        self.components['spam_sender'] = SpamSender()
        self.components['info_fetcher'] = InfoFetcher()
        self.components['coin_system'] = CoinSystem()
        self.components['referral_system'] = ReferralSystem()
        
        # Management components
        self.components['admin_panel'] = AdminPanel()
        self.components['user_commands'] = UserCommands()
        self.components['analytics'] = Analytics()
        self.components['backup_manager'] = BackupManager()
        self.components['web_dashboard'] = WebDashboard()
        self.components['webhook_handler'] = WebhookHandler()
        self.components['api_endpoints'] = APIEndpoints()
        self.components['bot_handlers'] = BotHandlers()
        
        self.logger.info(f"All {len(self.components)} components initialized")
    
    def start_background_threads(self):
        """Start all background threads"""
        self.logger.info("Starting background threads...")
        
        # Analytics thread
        analytics_thread = threading.Thread(target=self._analytics_loop, daemon=True)
        analytics_thread.start()
        
        # Cache cleanup thread
        cache_thread = threading.Thread(target=self._cache_cleanup_loop, daemon=True)
        cache_thread.start()
        
        # Backup thread
        backup_thread = threading.Thread(target=self._backup_loop, daemon=True)
        backup_thread.start()
        
        # Web dashboard thread
        web_thread = threading.Thread(target=self._web_dashboard_loop, daemon=True)
        web_thread.start()
        
        self.logger.info("Background threads started")
    
    def _analytics_loop(self):
        """Background analytics collection"""
        while self.is_running:
            try:
                self.components['analytics'].collect_stats()
                time.sleep(3600)  # Every hour
            except Exception as e:
                self.logger.error(f"Analytics error: {e}")
                time.sleep(60)
    
    def _cache_cleanup_loop(self):
        """Background cache cleanup"""
        while self.is_running:
            try:
                self.components['cache'].cleanup_expired()
                time.sleep(300)  # Every 5 minutes
            except Exception as e:
                self.logger.error(f"Cache cleanup error: {e}")
                time.sleep(60)
    
    def _backup_loop(self):
        """Background backup"""
        while self.is_running:
            try:
                self.components['backup_manager'].auto_backup()
                time.sleep(86400)  # Every 24 hours
            except Exception as e:
                self.logger.error(f"Backup error: {e}")
                time.sleep(3600)
    
    def _web_dashboard_loop(self):
        """Background web dashboard"""
        while self.is_running:
            try:
                self.components['web_dashboard'].run()
                time.sleep(1)
            except Exception as e:
                self.logger.error(f"Web dashboard error: {e}")
                time.sleep(5)
    
    def run(self):
        """Start the bot"""
        self.logger.info("Starting bot...")
        
        # Start web dashboard
        self.components['web_dashboard'].start()
        
        # Start bot polling
        self.components['bot_handlers'].start()
        
        while self.is_running:
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                self.shutdown()
                break
    
    def shutdown(self):
        """Graceful shutdown"""
        self.logger.info("Shutting down...")
        self.is_running = False
        
        # Stop all components
        for name, component in self.components.items():
            try:
                if hasattr(component, 'shutdown'):
                    component.shutdown()
                self.logger.info(f"Stopped {name}")
            except Exception as e:
                self.logger.error(f"Error stopping {name}: {e}")
        
        self.logger.info("Shutdown complete")
        sys.exit(0)

# ============================================================================
# ENTRY POINT
# ============================================================================

def signal_handler(sig, frame):
    print("\n⚠️ Received shutdown signal")
    sys.exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Print banner
    print("=" * 120)
    print(f"🔥 {BOT_NAME} v{VERSION} 🔥")
    print("=" * 120)
    print(f"👑 Author: {AUTHOR}")
    print(f"⚡ Features: 6 Regions | 1000+ Guests | 500+ Concurrent")
    print(f"💾 Database: SQLite with Connection Pool")
    print("=" * 120)
    
    # Start bot
    bot = SalarUltraBot()
    bot.run()