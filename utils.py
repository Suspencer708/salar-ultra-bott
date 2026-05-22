"""
Utility Functions for SALAAR X SPENCER ULTRA BOT
Common helper functions and tools
"""

import re
import hashlib
import random
import string
import time
from datetime import datetime
from typing import Dict, List, Optional, Any

from logger import get_logger

logger = get_logger(__name__)


class Utils:
    """Collection of utility functions"""

    @staticmethod
    def validate_uid(uid: str) -> bool:
        """Validate Free Fire UID"""
        if not uid:
            return False
        if not uid.isdigit():
            return False
        if len(uid) < 5 or len(uid) > 15:
            return False
        return True

    @staticmethod
    def format_number(num: int) -> str:
        """Format number with commas"""
        return f"{num:,}"

    @staticmethod
    def format_duration(seconds: float) -> str:
        """Format duration in human readable form"""
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{minutes}m {secs}s"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"{hours}h {minutes}m"

    @staticmethod
    def generate_id(prefix: str = "") -> str:
        """Generate unique ID"""
        timestamp = int(time.time() * 1000)
        random_part = random.randint(1000, 9999)
        return f"{prefix}{timestamp}{random_part}"

    @staticmethod
    def generate_token(length: int = 32) -> str:
        """Generate random token"""
        chars = string.ascii_letters + string.digits
        return ''.join(random.choice(chars) for _ in range(length))

    @staticmethod
    def hash_string(text: str) -> str:
        """Hash string using SHA256"""
        return hashlib.sha256(text.encode()).hexdigest()

    @staticmethod
    def truncate(text: str, max_length: int = 100) -> str:
        """Truncate text to max length"""
        if len(text) <= max_length:
            return text
        return text[:max_length - 3] + "..."

    @staticmethod
    def extract_uid(text: str) -> Optional[str]:
        """Extract UID from text"""
        match = re.search(r'\b\d{5,15}\b', text)
        return match.group(0) if match else None

    @staticmethod
    def extract_region(text: str) -> str:
        """Extract region from text"""
        regions = ['PK', 'IND', 'BR', 'ID', 'TH', 'VN']
        for region in regions:
            if region in text.upper():
                return region
        return 'PK'

    @staticmethod
    def parse_command(text: str) -> Dict:
        """Parse command and arguments"""
        parts = text.strip().split()
        if not parts:
            return {'command': None, 'args': []}

        command = parts[0].lower().replace('/', '') if parts[0].startswith('/') else parts[0].lower()
        args = parts[1:]

        return {'command': command, 'args': args}

    @staticmethod
    def format_telegram_message(text: str, escape: bool = True) -> str:
        """Format message for Telegram"""
        if escape:
            escape_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
            for char in escape_chars:
                text = text.replace(char, f'\\{char}')
        return text

    @staticmethod
    def chunk_list(lst: List, chunk_size: int) -> List[List]:
        """Split list into chunks"""
        return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]

    @staticmethod
    def retry_on_failure(func, max_retries: int = 3, delay: float = 1.0):
        """Retry function on failure"""
        for attempt in range(max_retries):
            try:
                return func()
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
                time.sleep(delay * (attempt + 1))

    @staticmethod
    def get_timestamp() -> str:
        """Get current timestamp"""
        return datetime.now().isoformat()

    @staticmethod
    def get_date() -> str:
        """Get current date"""
        return datetime.now().date().isoformat()

    @staticmethod
    def is_valid_email(email: str) -> bool:
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None

    @staticmethod
    def mask_string(text: str, show_first: int = 4, show_last: int = 4) -> str:
        """Mask string with asterisks"""
        if len(text) <= show_first + show_last:
            return '*' * len(text)
        return text[:show_first] + '*' * (len(text) - show_first - show_last) + text[-show_last:]

    @staticmethod
    def calculate_percentage(part: float, total: float) -> float:
        """Calculate percentage"""
        if total == 0:
            return 0
        return round(part / total * 100, 2)

    @staticmethod
    def get_ordinal_suffix(num: int) -> str:
        """Get ordinal suffix for number (1st, 2nd, 3rd, etc.)"""
        if 10 <= num % 100 <= 20:
            suffix = 'th'
        else:
            suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(num % 10, 'th')
        return f"{num}{suffix}"
