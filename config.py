"""
Configuration file for SALAAR X SPENCER ULTRA BOT
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ============================================================================
# BOT CONFIGURATION
# ============================================================================

BOT_TOKEN = os.getenv("BOT_TOKEN", "8842107581:AAF9Uq0U93irdJ-TYTyzSltsXkXDWS14Kwk")
ADMIN_IDS = [7433302366, 8842107581, 7433302366]
VERSION = "8.0.0"
BOT_NAME = "SALAAR X SPENCER ULTRA BOT"
AUTHOR = "SALAAR X SPENCER"

# ============================================================================
# DATABASE CONFIGURATION
# ============================================================================

DATABASE_FILE = "salar_ultra.db"
DATABASE_POOL_SIZE = 10
DATABASE_BACKUP_INTERVAL = 86400  # 24 hours

# ============================================================================
# SPEED CONFIGURATION
# ============================================================================

MAX_CONCURRENT_ACTIONS = 500
MAX_CONCURRENT_LIKES = 300
MAX_CONCURRENT_VISITORS = 200
MAX_CONCURRENT_SPAM = 150

# Rate limits
RATE_LIMIT_LIKES = 1000  # per day per UID
RATE_LIMIT_VISITORS = 1000
RATE_LIMIT_SPAM = 500
RATE_LIMIT_USER = 0.3  # seconds between commands

# ============================================================================
# COIN SYSTEM
# ============================================================================

DAILY_REWARD_MIN = 50
DAILY_REWARD_MAX = 500
REFERRAL_REWARD = 100
LIKE_COST = 5
VISITOR_COST = 3
SPAM_COST = 10

# VIP discounts
VIP_DISCOUNT = 0.5  # 50% off
VIP_DAILY_MULTIPLIER = 2

# ============================================================================
# API ENDPOINTS
# ============================================================================

# Free Fire APIs
FF_INFO_API = "https://api.dictech.dev/ff/stats"
FF_INFO_API_BACKUP = "https://ff.garena.com/api/antispam/search"
FF_LIKE_API_PK = "https://client.pk.freefiremobile.com/LikeProfile"
FF_LIKE_API_IND = "https://client.ind.freefiremobile.com/LikeProfile"
FF_VISITOR_API_PK = "https://client.pk.freefiremobile.com/VisitProfile"
FF_VISITOR_API_IND = "https://client.ind.freefiremobile.com/VisitProfile"
FF_SPAM_API_PK = "https://client.pk.freefiremobile.com/SendFriendRequest"
FF_SPAM_API_IND = "https://client.ind.freefiremobile.com/SendFriendRequest"
FF_TOKEN_API = "https://ffmconnect.live.gop.garenanow.com/oauth/guest/token/grant"

# ============================================================================
# CACHE CONFIGURATION
# ============================================================================

CACHE_SIZE = 10000
CACHE_TTL = 300  # 5 minutes
CACHE_CLEANUP_INTERVAL = 60

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

LOG_LEVEL = "INFO"
LOG_FILE = "salar_ultra.log"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_MAX_SIZE = 10485760  # 10 MB
LOG_BACKUP_COUNT = 5

# ============================================================================
# WEB DASHBOARD
# ============================================================================

WEB_DASHBOARD_ENABLED = True
WEB_DASHBOARD_PORT = 8080
WEB_DASHBOARD_HOST = "0.0.0.0"

# ============================================================================
# BACKUP CONFIGURATION
# ============================================================================

BACKUP_ENABLED = True
BACKUP_INTERVAL = 86400  # 24 hours
BACKUP_RETENTION_DAYS = 30
BACKUP_PATH = "backups/"

# ============================================================================
# REGION CONFIGURATION
# ============================================================================

SUPPORTED_REGIONS = ["PK", "IND", "BR", "ID", "TH", "VN"]
DEFAULT_REGION = "PK"

REGION_NAMES = {
    "PK": "Pakistan",
    "IND": "India",
    "BR": "Brazil",
    "ID": "Indonesia",
    "TH": "Thailand",
    "VN": "Vietnam"
}

# ============================================================================
# GUEST ACCOUNT CONFIGURATION
# ============================================================================

MAX_GUESTS_PER_REGION = 500
GUEST_AUTO_GENERATE = True
GUEST_VALIDATION_INTERVAL = 3600  # 1 hour

# ============================================================================
# PERFORMANCE CONFIGURATION
# ============================================================================

THREAD_POOL_SIZE = 500
QUEUE_SIZE = 100000
BATCH_SIZE = 1000
REQUEST_TIMEOUT = 10
MAX_RETRIES = 3
RETRY_DELAY = 1

# ============================================================================
# SECURITY CONFIGURATION
# ============================================================================

MAX_LOGIN_ATTEMPTS = 5
SESSION_TIMEOUT = 3600  # 1 hour
TOKEN_EXPIRY = 86400  # 24 hours

# ============================================================================
# WEBHOOK CONFIGURATION
# ============================================================================

WEBHOOK_ENABLED = False
WEBHOOK_URL = ""
WEBHOOK_SECRET = ""

# ============================================================================
# API CONFIGURATION
# ============================================================================

API_ENABLED = True
API_PORT = 5000
API_HOST = "0.0.0.0"
API_RATE_LIMIT = 100  # requests per minute

# ============================================================================
# FEATURE FLAGS
# ============================================================================

FEATURE_LIKES = True
FEATURE_VISITORS = True
FEATURE_SPAM = True
FEATURE_REFERRALS = True
FEATURE_VIP = True
FEATURE_WEBHOOKS = False
FEATURE_API = True
FEATURE_WEB_DASHBOARD = True