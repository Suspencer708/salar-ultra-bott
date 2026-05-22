"""
User Commands for SALAAR X SPENCER ULTRA BOT
All user-facing commands with formatting and error handling
"""

import time
import threading
from datetime import datetime
from typing import Dict, List, Optional, Any
from collections import defaultdict

from telebot import TeleBot
from database import DatabaseManager
from guest_manager import GuestManager
from like_sender import LikeSender
from visitor_sender import VisitorSender
from spam_sender import SpamSender
from info_fetcher import InfoFetcher
from coin_system import CoinSystem
from referral_system import ReferralSystem
from config import (
    BOT_NAME, VERSION, SUPPORTED_REGIONS, DEFAULT_REGION,
    MAX_LIKES_PER_DAY_PER_UID, MAX_VISITORS_PER_DAY_PER_UID,
    MAX_SPAM_PER_DAY_PER_UID, LIKE_COST, VISITOR_COST, SPAM_COST
)
from constants import WELCOME_MESSAGE, HELP_MESSAGE, ERROR_MESSAGES, SUCCESS_MESSAGES
from logger import get_logger

logger = get_logger(__name__)


class UserCommands:
    """All user-facing commands handler"""

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
        self.guest_manager = GuestManager()
        self.like_sender = LikeSender()
        self.visitor_sender = VisitorSender()
        self.spam_sender = SpamSender()
        self.info_fetcher = InfoFetcher()
        self.coin_system = CoinSystem()
        self.referral_system = ReferralSystem()

        self.user_cooldown = defaultdict(float)
        self.command_stats = defaultdict(int)

        logger.info("UserCommands initialized")

    def register_handlers(self, bot: TeleBot):
        """Register all command handlers with the bot"""
        
        @bot.message_handler(commands=['start'])
        def start_handler(message):
            self._handle_start(message, bot)

        @bot.message_handler(commands=['help'])
        def help_handler(message):
            self._handle_help(message, bot)

        @bot.message_handler(commands=['info'])
        def info_handler(message):
            self._handle_info(message, bot)

        @bot.message_handler(commands=['like'])
        def like_handler(message):
            self._handle_like(message, bot)

        @bot.message_handler(commands=['visit'])
        def visit_handler(message):
            self._handle_visit(message, bot)

        @bot.message_handler(commands=['spam'])
        def spam_handler(message):
            self._handle_spam(message, bot)

        @bot.message_handler(commands=['bulk'])
        def bulk_handler(message):
            self._handle_bulk(message, bot)

        @bot.message_handler(commands=['bulkvisit'])
        def bulkvisit_handler(message):
            self._handle_bulkvisit(message, bot)

        @bot.message_handler(commands=['bulkspam'])
        def bulkspam_handler(message):
            self._handle_bulkspam(message, bot)

        @bot.message_handler(commands=['daily'])
        def daily_handler(message):
            self._handle_daily(message, bot)

        @bot.message_handler(commands=['balance'])
        def balance_handler(message):
            self._handle_balance(message, bot)

        @bot.message_handler(commands=['refer'])
        def refer_handler(message):
            self._handle_refer(message, bot)

        @bot.message_handler(commands=['leaderboard'])
        def leaderboard_handler(message):
            self._handle_leaderboard(message, bot)

        @bot.message_handler(commands=['profile'])
        def profile_handler(message):
            self._handle_profile(message, bot)

        @bot.message_handler(commands=['about'])
        def about_handler(message):
            self._handle_about(message, bot)

        @bot.message_handler(commands=['feedback'])
        def feedback_handler(message):
            self._handle_feedback(message, bot)

        @bot.message_handler(func=lambda m: True)
        def unknown_handler(message):
            self._handle_unknown(message, bot)

        logger.info("User command handlers registered")

    def _check_rate_limit(self, user_id: int, cooldown: float = 1.0) -> bool:
        """Check if user is rate limited"""
        now = time.time()
        if now - self.user_cooldown[user_id] < cooldown:
            return False
        self.user_cooldown[user_id] = now
        return True

    def _log_command(self, user_id: int, command: str):
        """Log command usage"""
        self.command_stats[command] += 1
        self.db.log_command(user_id, command)

    def _validate_uid(self, uid: str) -> bool:
        """Validate Free Fire UID"""
        return uid and uid.isdigit() and 5 <= len(uid) <= 15

    # ========================================================================
    # CORE COMMAND HANDLERS
    # ========================================================================

    def _handle_start(self, message, bot):
        """Handle /start command"""
        user_id = message.from_user.id
        username = message.from_user.username or ""
        first_name = message.from_user.first_name or "User"

        user = self.db.get_user(user_id)
        self.db.update_user(user_id, username=username, first_name=first_name)

        # Check for referral
        if len(message.text.split()) > 1:
            ref_code = message.text.split()[1]
            if ref_code.startswith('SXS'):
                # Find referrer by referral code
                import sqlite3
                conn = sqlite3.connect('salar_ultra.db')
                cursor = conn.cursor()
                cursor.execute("SELECT user_id FROM users WHERE referral_code = ?", (ref_code,))
                result = cursor.fetchone()
                conn.close()

                if result and result[0] != user_id:
                    self.referral_system.process_referral(result[0], user_id)
                    bot.send_message(result[0], f"🎉 You got {REFERRAL_REWARD} coins for referring @{username or user_id}!")

        welcome_text = WELCOME_MESSAGE.format(
            version=VERSION,
            name=first_name,
            coins=user['coins'],
            likes=user.get('total_likes_sent', 0),
            visitors=user.get('total_visitors_sent', 0),
            spam=user.get('total_spam_sent', 0),
            referrals=self.db.get_referral_count(user_id)
        )

        bot.reply_to(message, welcome_text, parse_mode='Markdown')
        self._log_command(user_id, 'start')

    def _handle_help(self, message, bot):
        """Handle /help command"""
        user_id = message.from_user.id
        help_text = HELP_MESSAGE.format(
            max_likes=MAX_LIKES_PER_DAY_PER_UID,
            max_visitors=MAX_VISITORS_PER_DAY_PER_UID,
            max_spam=MAX_SPAM_PER_DAY_PER_UID,
            like_cost=LIKE_COST,
            visitor_cost=VISITOR_COST,
            spam_cost=SPAM_COST
        )
        bot.reply_to(message, help_text, parse_mode='Markdown')
        self._log_command(user_id, 'help')

    def _handle_info(self, message, bot):
        """Handle /info command"""
        user_id = message.from_user.id
        args = message.text.split()

        if len(args) < 2:
            bot.reply_to(message, "❌ *Usage:* `/info 5351564274`\n\n*Example:* `/info 5351564274`", parse_mode='Markdown')
            return

        uid = args[1].strip()
        if not self._validate_uid(uid):
            bot.reply_to(message, "❌ *Invalid UID!*\n\nPlease enter a valid Free Fire UID (10-digit number).", parse_mode='Markdown')
            return

        status_msg = bot.reply_to(message, "⚡ *Fetching player statistics...*", parse_mode='Markdown')
        info = self.info_fetcher.get_formatted_info(uid)

        if info:
            bot.edit_message_text(info, message.chat.id, status_msg.message_id, parse_mode='Markdown')
        else:
            bot.edit_message_text("❌ *Player Not Found!*\n\nPlease check the UID and try again.", message.chat.id, status_msg.message_id, parse_mode='Markdown')

        self._log_command(user_id, 'info')

    def _handle_like(self, message, bot):
        """Handle /like command"""
        user_id = message.from_user.id
        args = message.text.split()

        if len(args) < 2:
            bot.reply_to(message, "❌ *Usage:* `/like 5351564274 PK`\n\n*Supported regions:* PK, IND, BR, ID, TH, VN", parse_mode='Markdown')
            return

        target_uid = args[1].strip()
        region = args[2].strip().upper() if len(args) > 2 else DEFAULT_REGION

        if not self._validate_uid(target_uid):
            bot.reply_to(message, ERROR_MESSAGES['invalid_uid'], parse_mode='Markdown')
            return

        if region not in SUPPORTED_REGIONS:
            bot.reply_to(message, ERROR_MESSAGES['invalid_region'].format(regions=', '.join(SUPPORTED_REGIONS)), parse_mode='Markdown')
            return

        if not self._check_rate_limit(user_id, 2):
            bot.reply_to(message, "⏰ *Please wait a few seconds before using this command again.*", parse_mode='Markdown')
            return

        user = self.db.get_user(user_id)
        is_vip = user.get('is_vip', False)
        cost = self.coin_system.get_action_cost('like', is_vip)

        if user['coins'] < cost:
            bot.reply_to(message, ERROR_MESSAGES['insufficient_coins'].format(coins=user['coins'], required=cost), parse_mode='Markdown')
            return

        status_msg = bot.reply_to(message, f"⚡ *ULTRA SPEED: Sending 100 likes to `{target_uid}` ({region})...*\n⏱️ Using 300 concurrent threads!", parse_mode='Markdown')

        result = self.like_sender.send_likes(target_uid, 100, region, user_id)

        if result['success'] > 0:
            self.coin_system.deduct_coins(user_id, cost, 'like')
            response = SUCCESS_MESSAGES['likes'].format(
                success=result['success'],
                total=result['total'],
                speed=result.get('speed', 0),
                duration=result['duration'],
                cost=cost,
                target=target_uid,
                remaining=result.get('remaining', 0)
            )
            bot.edit_message_text(response, message.chat.id, status_msg.message_id, parse_mode='Markdown')
        else:
            bot.edit_message_text(f"❌ *Failed to send likes!*\n\n{result.get('message', 'Unknown error')}\n\n💡 Try a different region or UID.", message.chat.id, status_msg.message_id, parse_mode='Markdown')

        self._log_command(user_id, 'like')

    def _handle_visit(self, message, bot):
        """Handle /visit command"""
        user_id = message.from_user.id
        args = message.text.split()

        if len(args) < 2:
            bot.reply_to(message, "❌ *Usage:* `/visit 5351564274 PK`", parse_mode='Markdown')
            return

        target_uid = args[1].strip()
        region = args[2].strip().upper() if len(args) > 2 else DEFAULT_REGION

        if not self._validate_uid(target_uid):
            bot.reply_to(message, "❌ *Invalid UID!*", parse_mode='Markdown')
            return

        if not self._check_rate_limit(user_id, 2):
            bot.reply_to(message, "⏰ *Please wait a few seconds.*", parse_mode='Markdown')
            return

        user = self.db.get_user(user_id)
        is_vip = user.get('is_vip', False)
        cost = self.coin_system.get_action_cost('visit', is_vip)

        if user['coins'] < cost:
            bot.reply_to(message, f"❌ *Need {cost} coins!* Balance: {user['coins']}", parse_mode='Markdown')
            return

        status_msg = bot.reply_to(message, f"👁️ *Sending 50 visitors to `{target_uid}` ({region})...*", parse_mode='Markdown')

        result = self.visitor_sender.send_visitors(target_uid, 50, region, user_id)

        if result['success'] > 0:
            self.coin_system.deduct_coins(user_id, cost, 'visit')
            response = SUCCESS_MESSAGES['visitors'].format(
                success=result['success'],
                total=result['total'],
                speed=result.get('speed', 0),
                duration=result['duration'],
                cost=cost,
                target=target_uid
            )
            bot.edit_message_text(response, message.chat.id, status_msg.message_id, parse_mode='Markdown')
        else:
            bot.edit_message_text(f"❌ *Failed!* {result.get('message', 'Unknown error')}", message.chat.id, status_msg.message_id, parse_mode='Markdown')

        self._log_command(user_id, 'visit')

    def _handle_spam(self, message, bot):
        """Handle /spam command"""
        user_id = message.from_user.id
        args = message.text.split()

        if len(args) < 2:
            bot.reply_to(message, "❌ *Usage:* `/spam 5351564274 PK`", parse_mode='Markdown')
            return

        target_uid = args[1].strip()
        region = args[2].strip().upper() if len(args) > 2 else DEFAULT_REGION

        if not self._validate_uid(target_uid):
            bot.reply_to(message, "❌ *Invalid UID!*", parse_mode='Markdown')
            return

        if not self._check_rate_limit(user_id, 2):
            bot.reply_to(message, "⏰ *Please wait a few seconds.*", parse_mode='Markdown')
            return

        user = self.db.get_user(user_id)
        is_vip = user.get('is_vip', False)
        cost = self.coin_system.get_action_cost('spam', is_vip)

        if user['coins'] < cost:
            bot.reply_to(message, f"❌ *Need {cost} coins!* Balance: {user['coins']}", parse_mode='Markdown')
            return

        status_msg = bot.reply_to(message, f"💥 *Sending 30 spam requests to `{target_uid}` ({region})...*", parse_mode='Markdown')

        result = self.spam_sender.send_spam(target_uid, 30, region, user_id)

        if result['success'] > 0:
            self.coin_system.deduct_coins(user_id, cost, 'spam')
            response = SUCCESS_MESSAGES['spam'].format(
                success=result['success'],
                total=result['total'],
                speed=result.get('speed', 0),
                duration=result['duration'],
                cost=cost,
                target=target_uid
            )
            bot.edit_message_text(response, message.chat.id, status_msg.message_id, parse_mode='Markdown')
        else:
            bot.edit_message_text(f"❌ *Failed!* {result.get('message', 'Unknown error')}", message.chat.id, status_msg.message_id, parse_mode='Markdown')

        self._log_command(user_id, 'spam')

    def _handle_bulk(self, message, bot):
        """Handle /bulk command - custom likes"""
        user_id = message.from_user.id
        args = message.text.split()

        if len(args) < 3:
            bot.reply_to(message, "❌ *Usage:* `/bulk 5351564274 200 PK`\n\n*Max:* 500 likes per request", parse_mode='Markdown')
            return

        target_uid = args[1].strip()
        try:
            count = max(1, min(int(args[2]), 500))
        except ValueError:
            bot.reply_to(message, "❌ *Invalid count!* Please enter a number between 1 and 500.", parse_mode='Markdown')
            return

        region = args[3].strip().upper() if len(args) > 3 else DEFAULT_REGION

        if not self._validate_uid(target_uid):
            bot.reply_to(message, "❌ *Invalid UID!*", parse_mode='Markdown')
            return

        if not self._check_rate_limit(user_id, 3):
            bot.reply_to(message, "⏰ *Please wait a few seconds.*", parse_mode='Markdown')
            return

        user = self.db.get_user(user_id)
        is_vip = user.get('is_vip', False)
        cost_per_like = 1 if not is_vip else 0.5
        cost = int(count * cost_per_like)

        if user['coins'] < cost:
            bot.reply_to(message, f"❌ *Need {cost} coins!* Balance: {user['coins']}", parse_mode='Markdown')
            return

        status_msg = bot.reply_to(message, f"⚡ *Sending {count} likes to `{target_uid}` ({region})...*", parse_mode='Markdown')

        result = self.like_sender.send_likes(target_uid, count, region, user_id)

        if result['success'] > 0:
            self.coin_system.deduct_coins(user_id, cost, 'bulk_like')
            response = f"""
✅ *BULK LIKE COMPLETED!*

📊 *Sent:* {result['success']}/{result['total']} likes
⚡ *Speed:* {result.get('speed', 0)} likes/sec
⏱️ *Duration:* {result['duration']}s
💰 *Cost:* {cost} coins
🎯 *Target:* `{target_uid}`
            """
            bot.edit_message_text(response, message.chat.id, status_msg.message_id, parse_mode='Markdown')
        else:
            bot.edit_message_text(f"❌ *Failed!* {result.get('message', 'Unknown error')}", message.chat.id, status_msg.message_id, parse_mode='Markdown')

        self._log_command(user_id, 'bulk')

    def _handle_bulkvisit(self, message, bot):
        """Handle /bulkvisit command"""
        user_id = message.from_user.id
        args = message.text.split()

        if len(args) < 3:
            bot.reply_to(message, "❌ *Usage:* `/bulkvisit 5351564274 100 PK`", parse_mode='Markdown')
            return

        target_uid = args[1].strip()
        try:
            count = max(1, min(int(args[2]), 300))
        except ValueError:
            bot.reply_to(message, "❌ *Invalid count!*", parse_mode='Markdown')
            return

        region = args[3].strip().upper() if len(args) > 3 else DEFAULT_REGION

        if not self._validate_uid(target_uid):
            bot.reply_to(message, "❌ *Invalid UID!*", parse_mode='Markdown')
            return

        user = self.db.get_user(user_id)
        is_vip = user.get('is_vip', False)
        cost_per_visit = 1 if not is_vip else 0.5
        cost = int(count * cost_per_visit)

        if user['coins'] < cost:
            bot.reply_to(message, f"❌ *Need {cost} coins!*", parse_mode='Markdown')
            return

        status_msg = bot.reply_to(message, f"👁️ *Sending {count} visitors to `{target_uid}`...*", parse_mode='Markdown')

        result = self.visitor_sender.send_visitors(target_uid, count, region, user_id)

        if result['success'] > 0:
            self.coin_system.deduct_coins(user_id, cost, 'bulk_visit')
            response = f"✅ *BULK VISITORS: {result['success']}/{result['total']} in {result['duration']}s at {result.get('speed', 0)}/sec*"
            bot.edit_message_text(response, message.chat.id, status_msg.message_id, parse_mode='Markdown')
        else:
            bot.edit_message_text("❌ *Failed!*", message.chat.id, status_msg.message_id)

        self._log_command(user_id, 'bulkvisit')

    def _handle_bulkspam(self, message, bot):
        """Handle /bulkspam command"""
        user_id = message.from_user.id
        args = message.text.split()

        if len(args) < 3:
            bot.reply_to(message, "❌ *Usage:* `/bulkspam 5351564274 50 PK`", parse_mode='Markdown')
            return

        target_uid = args[1].strip()
        try:
            count = max(1, min(int(args[2]), 200))
        except ValueError:
            bot.reply_to(message, "❌ *Invalid count!*", parse_mode='Markdown')
            return

        region = args[3].strip().upper() if len(args) > 3 else DEFAULT_REGION

        if not self._validate_uid(target_uid):
            bot.reply_to(message, "❌ *Invalid UID!*", parse_mode='Markdown')
            return

        user = self.db.get_user(user_id)
        is_vip = user.get('is_vip', False)
        cost_per_spam = 1 if not is_vip else 0.5
        cost = int(count * cost_per_spam)

        if user['coins'] < cost:
            bot.reply_to(message, f"❌ *Need {cost} coins!*", parse_mode='Markdown')
            return

        status_msg = bot.reply_to(message, f"💥 *Sending {count} spam requests to `{target_uid}`...*", parse_mode='Markdown')

        result = self.spam_sender.send_spam(target_uid, count, region, user_id)

        if result['success'] > 0:
            self.coin_system.deduct_coins(user_id, cost, 'bulk_spam')
            response = f"✅ *BULK SPAM: {result['success']}/{result['total']} in {result['duration']}s at {result.get('speed', 0)}/sec*"
            bot.edit_message_text(response, message.chat.id, status_msg.message_id, parse_mode='Markdown')
        else:
            bot.edit_message_text("❌ *Failed!*", message.chat.id, status_msg.message_id)

        self._log_command(user_id, 'bulkspam')

    # ========================================================================
    # COIN & REWARD COMMANDS
    # ========================================================================

    def _handle_daily(self, message, bot):
        """Handle /daily command"""
        user_id = message.from_user.id
        user = self.db.get_user(user_id)
        is_vip = user.get('is_vip', False)

        status = self.coin_system.get_daily_claim_status(user_id)

        if not status['can_claim']:
            bot.reply_to(message, f"⏰ *Already Claimed Today!*\n\n⏳ Next claim in: {status.get('hours_remaining', 0)}h {status.get('minutes_remaining', 0)}m\n🔥 Current streak: {status['streak']} days", parse_mode='Markdown')
            return

        reward, streak, bonus = self.coin_system.claim_daily_reward(user_id, is_vip)
        new_balance = self.coin_system.get_balance(user_id)

        response = f"""
🎁 *DAILY REWARD CLAIMED!*

✨ Base Reward: +{reward - bonus} coins
🔥 Streak Bonus (x{streak}): +{bonus} coins
{f'👑 VIP Bonus: +{(reward - bonus)} coins' if is_vip else ''}
💰 *Total Reward: {reward} coins* 🪙

📊 *Your Stats:*
├─ New Balance: *{new_balance}* coins
├─ Current Streak: *{streak}* days
└─ Next Bonus: +{min((streak + 1) * 5, 100)} coins tomorrow

💡 Come back tomorrow for more rewards!
        """
        bot.reply_to(message, response, parse_mode='Markdown')
        self._log_command(user_id, 'daily')

    def _handle_balance(self, message, bot):
        """Handle /balance command"""
        user_id = message.from_user.id
        stats = self.coin_system.get_user_stats(user_id)

        response = f"""
💰 *YOUR BALANCE & STATS*

🪙 *Current Coins:* {stats['balance']}
📈 *Total Earned:* {stats['total_earned']:,} coins
📉 *Total Spent:* {stats['total_spent']:,} coins

❤️ *Likes Sent:* {stats['likes_sent']:,}
👁️ *Visitors Sent:* {stats['visitors_sent']:,}
💥 *Spam Sent:* {stats['spam_sent']:,}
👥 *Referrals:* {stats['referrals']}
🔥 *Daily Streak:* {stats['daily_streak']} days

⚡ *ULTRA PRICES:*
├─ 100 Likes: {LIKE_COST} coins
├─ 50 Visitors: {VISITOR_COST} coins
└─ 30 Spam: {SPAM_COST} coins

💡 Use `/daily` to earn free coins!
        """
        bot.reply_to(message, response, parse_mode='Markdown')
        self._log_command(user_id, 'balance')

    def _handle_refer(self, message, bot):
        """Handle /refer command"""
        user_id = message.from_user.id
        bot_username = bot.get_me().username

        link = self.referral_system.get_referral_link(user_id, bot_username)
        count = self.referral_system.get_referral_count(user_id)
        earnings = self.referral_system.get_referral_earnings(user_id)

        response = f"""
👥 *REFERRAL PROGRAM*

🔗 *Your Referral Link:*
`{link}`

📊 *Your Stats:*
├─ Total Referrals: *{count}*
├─ Coins Earned: *{earnings}*
└─ Next Reward: *100* coins per referral

💡 *How it works:*
1️⃣ Share your link with friends
2️⃣ They click and start the bot
3️⃣ You automatically get 100 coins!

📢 *Share on social media for more referrals!*
        """
        bot.reply_to(message, response, parse_mode='Markdown')
        self._log_command(user_id, 'refer')

    def _handle_leaderboard(self, message, bot):
        """Handle /leaderboard command"""
        user_id = message.from_user.id
        top_users = self.coin_system.get_top_users(10)

        if not top_users:
            bot.reply_to(message, "📊 *No users on leaderboard yet!*", parse_mode='Markdown')
            return

        leaderboard_text = "🏆 *TOP 10 COIN LEADERBOARD* 🏆\n\n"
        medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]

        for i, user in enumerate(top_users):
            username = user.get('username', f"User_{user['user_id']}")
            leaderboard_text += f"{medals[i]} *{username}*\n"
            leaderboard_text += f"   ├─ 💰 {user['coins']} coins\n"
            leaderboard_text += f"   └─ ❤️ {user.get('likes', 0)} likes\n\n"

        # Get user's rank
        import sqlite3
        conn = sqlite3.connect('salar_ultra.db')
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) + 1 FROM users WHERE coins > (SELECT coins FROM users WHERE user_id = ? AND is_banned = 0)", (user_id,))
        rank = cursor.fetchone()[0]
        conn.close()

        leaderboard_text += f"\n📊 *Your Rank:* #{rank}\n💡 Use `/daily` to earn coins!"

        bot.reply_to(message, leaderboard_text, parse_mode='Markdown')
        self._log_command(user_id, 'leaderboard')

    def _handle_profile(self, message, bot):
        """Handle /profile command"""
        user_id = message.from_user.id
        stats = self.coin_system.get_user_stats(user_id)

        # Get rank
        import sqlite3
        conn = sqlite3.connect('salar_ultra.db')
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) + 1 FROM users WHERE coins > (SELECT coins FROM users WHERE user_id = ? AND is_banned = 0)", (user_id,))
        rank = cursor.fetchone()[0]
        conn.close()

        # Calculate activity level
        total_actions = stats['likes_sent'] + stats['visitors_sent'] + stats['spam_sent']
        if total_actions > 10000:
            badge = "👑 LEGEND"
        elif total_actions > 5000:
            badge = "⚡ MASTER"
        elif total_actions > 1000:
            badge = "🔥 WARRIOR"
        elif total_actions > 100:
            badge = "🌟 ROOKIE"
        else:
            badge = "🌱 BEGINNER"

        response = f"""
👤 *USER PROFILE*

📱 *Basic Info:*
├─ 🆔 User ID: `{user_id}`
├─ 👤 Username: @{message.from_user.username or 'Not set'}
├─ 🏆 Rank: #{rank}
└─ 🎖️ Badge: {badge}

💰 *Economy:*
├─ 🪙 Coins: {stats['balance']}
├─ 📈 Earned: {stats['total_earned']:,}
├─ 📉 Spent: {stats['total_spent']:,}
├─ 👥 Referrals: {stats['referrals']}
└─ 🔥 Streak: {stats['daily_streak']} days

🎮 *Activity:*
├─ ❤️ Likes: {stats['likes_sent']:,}
├─ 👁️ Visitors: {stats['visitors_sent']:,}
├─ 💥 Spam: {stats['spam_sent']:,}
└─ 🎯 Total Actions: {total_actions:,}

💎 *VIP Status:* {'✅ ACTIVE' if stats['is_vip'] else '❌ INACTIVE'}

💡 Use `/daily` to claim rewards!
        """
        bot.reply_to(message, response, parse_mode='Markdown')
        self._log_command(user_id, 'profile')

    def _handle_about(self, message, bot):
        """Handle /about command"""
        response = f"""
╔══════════════════════════════════════════════════════════════╗
║                    🔥 SALAAR X SPENCER ULTRA BOT 🔥           ║
║                         Version {VERSION}                       ║
╚══════════════════════════════════════════════════════════════╝

🤖 *Bot Information:*
├─ Name: {BOT_NAME}
├─ Version: {VERSION}
├─ Developer: SALAAR X SPENCER
└─ Release Date: 2026

✨ *ULTRA FEATURES:*
├─ ✅ 300+ concurrent actions/sec
├─ ✅ 6 region support (PK, IND, BR, ID, TH, VN)
├─ ✅ 1000+ guest accounts
├─ ✅ Auto guest generation
├─ ✅ Coin & referral system
├─ ✅ Daily rewards with streak bonus
├─ ✅ VIP membership system
└─ ✅ 24/7 uptime

💡 *Use `/help` for all commands!*
        """
        bot.reply_to(message, response, parse_mode='Markdown')
        self._log_command(user_id, 'about')

    def _handle_feedback(self, message, bot):
        """Handle /feedback command"""
        user_id = message.from_user.id
        args = message.text.split(maxsplit=1)

        if len(args) < 2:
            bot.reply_to(message, "❌ *Usage:* `/feedback Your message here`", parse_mode='Markdown')
            return

        feedback_text = args[1]

        # Save feedback
        import sqlite3
        conn = sqlite3.connect('salar_ultra.db')
        cursor = conn.cursor()
        cursor.execute('INSERT INTO feedback (user_id, message, timestamp) VALUES (?, ?, ?)',
                       (user_id, feedback_text, datetime.now().isoformat()))
        conn.commit()
        conn.close()

        # Notify admins
        from config import ADMIN_IDS
        for admin_id in ADMIN_IDS:
            try:
                bot.send_message(admin_id, f"📝 *New Feedback*\n\n👤 User: `{user_id}`\n💬 Message: {feedback_text}", parse_mode='Markdown')
            except:
                pass

        bot.reply_to(message, "✅ *Thank you for your feedback!*\n\nYour message has been sent to the developer.", parse_mode='Markdown')
        self._log_command(user_id, 'feedback')

    def _handle_unknown(self, message, bot):
        """Handle unknown commands"""
        user_id = message.from_user.id
        bot.reply_to(message, """
❓ *Unknown Command!*

Use `/help` to see all available commands.

💡 *Quick Start:*
• `/info 5351564274` - Get player stats
• `/like 5351564274` - Send 100 likes
• `/daily` - Claim free coins
• `/balance` - Check your balance
        """, parse_mode='Markdown')
        self._log_command(user_id, 'unknown')

    def get_command_stats(self) -> Dict:
        """Get command usage statistics"""
        return dict(self.command_stats)