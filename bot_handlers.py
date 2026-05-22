"""
Bot Handlers for SALAAR X SPENCER ULTRA BOT
Main bot message router and dispatcher
"""

import telebot
import time
import threading
from typing import Dict, Any

from config import BOT_TOKEN, ADMIN_IDS
from user_commands import UserCommands
from admin_panel import AdminPanel
from logger import get_logger

logger = get_logger(__name__)


class BotHandlers:
    """Main bot message handlers and router"""

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

        self.bot = telebot.TeleBot(BOT_TOKEN)
        self.user_commands = UserCommands()
        self.admin_panel = AdminPanel()

        self.is_running = False
        self.start_time = time.time()

        self._register_handlers()

        logger.info("BotHandlers initialized")

    def _register_handlers(self):
        """Register all command handlers"""
        self.user_commands.register_handlers(self.bot)

        # Admin command handler
        @self.bot.message_handler(commands=['admin'])
        def admin_handler(message):
            if message.from_user.id in ADMIN_IDS:
                response = self.admin_panel.execute_command(
                    message.from_user.id,
                    message.text,
                    message.text.split()[1:] if len(message.text.split()) > 1 else []
                )
                if response:
                    self.bot.reply_to(message, response, parse_mode='Markdown')
            else:
                self.bot.reply_to(message, "❌ *Access Denied!*", parse_mode='Markdown')

        @self.bot.message_handler(commands=['stats', 'broadcast', 'addcoins', 'users',
                                            'ban', 'unban', 'addguest', 'guests',
                                            'speedtest', 'restart', 'backup'])
        def admin_commands_handler(message):
            if message.from_user.id not in ADMIN_IDS:
                self.bot.reply_to(message, "❌ *Admin only command!*", parse_mode='Markdown')
                return

            cmd = message.text.split()[0].replace('/', '')
            args = message.text.split()[1:] if len(message.text.split()) > 1 else []
            response = self.admin_panel.execute_command(message.from_user.id, cmd, args)

            if response:
                self.bot.reply_to(message, response, parse_mode='Markdown')

        @self.bot.message_handler(content_types=['text'])
        def text_handler(message):
            if not message.text.startswith('/'):
                self.bot.reply_to(message, """
❓ *Unknown Command!*

Use `/help` to see all available commands.

💡 *Quick Start:*
• `/info 5351564274` - Get player stats
• `/like 5351564274` - Send 100 likes
• `/daily` - Claim free coins
• `/balance` - Check your balance
                """, parse_mode='Markdown')

        # Error handler
        @self.bot.message_handler(func=lambda m: True)
        def echo_all(message):
            pass

        logger.info("Bot handlers registered")

    def start(self):
        """Start the bot"""
        self.is_running = True
        logger.info("Bot started")
        self._run_polling()

    def _run_polling(self):
        """Run bot polling with auto-reconnect"""
        while self.is_running:
            try:
                self.bot.infinity_polling(timeout=30, long_polling_timeout=30)
            except Exception as e:
                logger.error(f"Bot polling error: {e}")
                time.sleep(5)

    def stop(self):
        """Stop the bot"""
        self.is_running = False
        self.bot.stop_polling()
        logger.info("Bot stopped")

    def get_uptime(self) -> float:
        """Get bot uptime in seconds"""
        return time.time() - self.start_time