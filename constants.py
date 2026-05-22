"""
Constants file for SALAAR X SPENCER ULTRA BOT
"""

from enum import Enum, auto

# ============================================================================
# ENUMS
# ============================================================================

class UserRole(Enum):
    USER = auto()
    VIP = auto()
    ADMIN = auto()
    SUPER_ADMIN = auto()
    MODERATOR = auto()
    BANNED = auto()

class ActionType(Enum):
    LIKE = auto()
    VISIT = auto()
    SPAM = auto()
    INFO = auto()
    DAILY = auto()
    REFER = auto()
    LEADERBOARD = auto()
    PROFILE = auto()

class Region(Enum):
    PK = "pk"
    IND = "ind"
    BR = "br"
    ID = "id"
    TH = "th"
    VN = "vn"

class SpeedLevel(Enum):
    NORMAL = 1
    FAST = 5
    ULTRA = 10
    PRO = 20
    MAX = 50
    ULTRA_PRO = 100
    ULTRA_PRO_MAX = 200
    ULTRA_PRO_MAX_PLUS = 500

class CommandCategory(Enum):
    GAME = auto()
    COIN = auto()
    ADMIN = auto()
    INFO = auto()
    OTHER = auto()

# ============================================================================
# MESSAGES
# ============================================================================

WELCOME_MESSAGE = """
╔══════════════════════════════════════════════════════════════════╗
║              🔥 SALAAR X SPENCER ULTRA BOT 🔥                     ║
║                 Version {version} | Speed: ULTRA                 ║
╚══════════════════════════════════════════════════════════════════╝

👋 *Welcome {name}!*

💎 *Your Stats:*
   ├─ 🪙 Coins: {coins}
   ├─ ❤️ Likes Sent: {likes}
   ├─ 👁️ Visitors Sent: {visitors}
   ├─ 💥 Spam Sent: {spam}
   └─ 👥 Referrals: {referrals}

⚡ *Commands:*
   ├─ /info <UID> - Get player stats
   ├─ /like <UID> - Send 100 likes
   ├─ /visit <UID> - Send 50 visitors
   ├─ /spam <UID> - Send 30 spam
   ├─ /daily - Claim daily reward
   └─ /balance - Check balance

💡 *Use /help for all commands!*
"""

HELP_MESSAGE = """
╔══════════════════════════════════════════════════════════════════╗
║                      📚 COMMANDS HELP 📚                          ║
╚══════════════════════════════════════════════════════════════════╝

⚡ *GAME COMMANDS*
─────────────────────────────────────────────────
/info <UID>              → Get player statistics
/like <UID> [region]     → Send 100 likes (5 coins)
/visit <UID> [region]    → Send 50 visitors (3 coins)
/spam <UID> [region]     → Send 30 spam (10 coins)
/bulk <UID> <count>      → Custom likes (0.5 coin/like)

💰 *COIN COMMANDS*
─────────────────────────────────────────────────
/daily                   → Claim daily reward (50-500 coins)
/balance                 → Check your balance
/refer                   → Get referral link (100 coins/referral)
/leaderboard             → Top coin earners
/profile                 → View your profile

👑 *ADMIN COMMANDS*
─────────────────────────────────────────────────
/stats                   → Bot statistics
/broadcast <msg>         → Send to all users
/addcoins <id> <amount>  → Add coins to user
/users                   → List all users
/ban <id>                → Ban user
/unban <id>              → Unban user

💡 *REGIONS*
─────────────────────────────────────────────────
PK - Pakistan (Fastest)
IND - India
BR - Brazil
ID - Indonesia
TH - Thailand
VN - Vietnam
"""

# ============================================================================
# ERROR MESSAGES
# ============================================================================

ERROR_INVALID_UID = "❌ *Invalid UID!*\n\nPlease enter a valid Free Fire UID (10-digit number)."
ERROR_INSUFFICIENT_COINS = "❌ *Insufficient Coins!*\n\n💰 Your balance: {coins} coins\n💎 Required: {required} coins\n\n💡 Use `/daily` to earn free coins!"
ERROR_DAILY_LIMIT = "❌ *Daily limit reached!*\n\n📅 Max {limit} likes per UID per day\n💡 Try again tomorrow!"
ERROR_PLAYER_NOT_FOUND = "❌ *Player not found!*\n\nPlease check the UID and try again."
ERROR_ADMIN_ONLY = "❌ *Admin only command!*"
ERROR_RATE_LIMIT = "⏰ *Please wait {seconds} seconds before using this command again.*"
ERROR_INVALID_REGION = "❌ *Invalid region!*\n\nSupported regions: {regions}"

# ============================================================================
# SUCCESS MESSAGES
# ============================================================================

SUCCESS_LIKES = """
✅ *LIKE SENT SUCCESSFULLY!*

📊 Result: {success}/{total} likes
⚡ Speed: {speed} likes/sec
⏱️ Duration: {duration}s
💰 Cost: {cost} coins
🎯 Target: `{target}`
📅 Daily remaining: {remaining}
"""

SUCCESS_VISITORS = """
✅ *VISITORS SENT!*

📊 Result: {success}/{total} visitors
⚡ Speed: {speed} visitors/sec
⏱️ Duration: {duration}s
💰 Cost: {cost} coins
🎯 Target: `{target}`
"""

SUCCESS_SPAM = """
✅ *SPAM SENT!*

📊 Result: {success}/{total} requests
⚡ Speed: {speed} req/sec
⏱️ Duration: {duration}s
💰 Cost: {cost} coins
🎯 Target: `{target}`
"""

SUCCESS_DAILY = """
🎁 *DAILY REWARD CLAIMED!*

✨ You received: {reward} coins
💰 New Balance: {balance} coins

💡 Come back tomorrow for more!
"""

# ============================================================================
# REGION API MAPPINGS
# ============================================================================

REGION_API_MAP = {
    "PK": {
        "like": "https://client.pk.freefiremobile.com/LikeProfile",
        "visit": "https://client.pk.freefiremobile.com/VisitProfile",
        "spam": "https://client.pk.freefiremobile.com/SendFriendRequest"
    },
    "IND": {
        "like": "https://client.ind.freefiremobile.com/LikeProfile",
        "visit": "https://client.ind.freefiremobile.com/VisitProfile",
        "spam": "https://client.ind.freefiremobile.com/SendFriendRequest"
    },
    "BR": {
        "like": "https://client.br.freefiremobile.com/LikeProfile",
        "visit": "https://client.br.freefiremobile.com/VisitProfile",
        "spam": "https://client.br.freefiremobile.com/SendFriendRequest"
    },
    "ID": {
        "like": "https://client.id.freefiremobile.com/LikeProfile",
        "visit": "https://client.id.freefiremobile.com/VisitProfile",
        "spam": "https://client.id.freefiremobile.com/SendFriendRequest"
    },
    "TH": {
        "like": "https://client.th.freefiremobile.com/LikeProfile",
        "visit": "https://client.th.freefiremobile.com/VisitProfile",
        "spam": "https://client.th.freefiremobile.com/SendFriendRequest"
    },
    "VN": {
        "like": "https://client.vn.freefiremobile.com/LikeProfile",
        "visit": "https://client.vn.freefiremobile.com/VisitProfile",
        "spam": "https://client.vn.freefiremobile.com/SendFriendRequest"
    }
}

# ============================================================================
# DATABASE QUERIES
# ============================================================================

DB_CREATE_USERS = """
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    coins INTEGER DEFAULT 500,
    total_likes_sent INTEGER DEFAULT 0,
    total_visitors_sent INTEGER DEFAULT 0,
    total_spam_sent INTEGER DEFAULT 0,
    total_commands_used INTEGER DEFAULT 0,
    join_date TEXT,
    last_active TEXT,
    last_claim TEXT,
    is_banned INTEGER DEFAULT 0,
    is_vip INTEGER DEFAULT 0,
    vip_expiry TEXT,
    referral_code TEXT UNIQUE,
    referred_by INTEGER DEFAULT NULL,
    daily_streak INTEGER DEFAULT 0
)
"""

DB_CREATE_GUESTS = """
CREATE TABLE IF NOT EXISTS guests_{region} (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uid TEXT UNIQUE,
    password TEXT,
    region TEXT DEFAULT '{region}',
    owner TEXT DEFAULT 'SALAAR X SPENCER',
    is_active INTEGER DEFAULT 1,
    added_date TEXT,
    last_used TEXT,
    total_likes_sent INTEGER DEFAULT 0,
    total_visitors_sent INTEGER DEFAULT 0,
    total_spam_sent INTEGER DEFAULT 0,
    success_rate REAL DEFAULT 0
)
"""

DB_CREATE_HISTORY = """
CREATE TABLE IF NOT EXISTS likes_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    target_uid TEXT,
    region TEXT,
    likes_sent INTEGER,
    likes_success INTEGER,
    timestamp TEXT,
    duration REAL,
    speed REAL
)
"""

# ============================================================================
# GUEST ACCOUNTS (Partial - More in database)
# ============================================================================

PK_GUESTS_BASE = [
    ("3301828218", "3A0E972E57E9EDC39DC4830E3D486DBFB5DA7C52A4E8B0B8F3F9DC4450899571"),
    ("3301828350", "8B7F2D1E5C9A4B3F6E8D1C2B5A9F7E3D8C1B4A6F9E2D5C8B1A4F7E9C2D5B8A1F4"),
    ("3301828456", "E5C8B1A4F7E9D2C5B8A1F4E7C9B2A5F8E1D4C7B0A3F6E9D2C5B8A1F4E7C9B2"),
]

IND_GUESTS_BASE = [
    ("4103677597", "BE281AB62B3F3A7FE98CE28881C0D55F6256151257D10DC068686FBF462CEF9C"),
    ("4104185061", "2318CCF2BF335700C06DFAC0E9598FA609D306B2665A4E6A2A231631BB389415"),
    ("4104163340", "AABD231C895C0B3D30E6E124C76040800316EE0CF1F1EDE405F26C7E914DD722"),
]

# ============================================================================
# ADMIN COMMANDS LIST
# ============================================================================

ADMIN_COMMANDS = [
    ("stats", "View bot statistics"),
    ("broadcast", "Send message to all users"),
    ("addcoins", "Add coins to user"),
    ("removecoins", "Remove coins from user"),
    ("users", "List all users"),
    ("ban", "Ban a user"),
    ("unban", "Unban a user"),
    ("addguest", "Add guest account"),
    ("guests", "List guest accounts"),
    ("speedtest", "Run speed test"),
    ("backup", "Backup database"),
    ("restore", "Restore from backup"),
    ("clearlogs", "Clear log files"),
    ("restart", "Restart the bot"),
]

# ============================================================================
# USER COMMANDS LIST
# ============================================================================

USER_COMMANDS = [
    ("start", "Start the bot"),
    ("help", "Show help message"),
    ("info", "Get player statistics"),
    ("like", "Send 100 likes"),
    ("visit", "Send 50 visitors"),
    ("spam", "Send 30 spam"),
    ("bulk", "Send custom likes"),
    ("daily", "Claim daily reward"),
    ("balance", "Check coin balance"),
    ("refer", "Get referral link"),
    ("leaderboard", "View top users"),
    ("profile", "View your profile"),
    ("about", "About the bot"),
    ("feedback", "Send feedback"),
]