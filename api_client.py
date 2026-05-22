"""
API Client for SALAAR X SPENCER ULTRA BOT
Handles all external API calls with retry, caching, and rate limiting
"""

import requests
import time
import json
import hashlib
from typing import Dict, List, Tuple, Optional, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from config import (
    FF_INFO_API, FF_INFO_API_BACKUP, FF_INFO_API_BACKUP2,
    FF_LIKE_API_PK, FF_LIKE_API_IND, FF_VISITOR_API_PK,
    FF_VISITOR_API_IND, FF_SPAM_API_PK, FF_SPAM_API_IND,
    FF_TOKEN_API, REQUEST_TIMEOUT, MAX_RETRIES, RETRY_DELAY
)
from constants import REGION_API_MAP
from cache_system import CacheSystem
from rate_limiter import RateLimiter
from logger import get_logger

logger = get_logger(__name__)

# ============================================================================
# API CLIENT CLASS
# ============================================================================

class APIClient:
    """Complete API client with retry, caching, and rate limiting"""
    
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
        
        self.cache = CacheSystem()
        self.rate_limiter = RateLimiter()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Dalvik/2.1.0 (Linux; U; Android 13; CPH2095 Build/RKQ1.211119.001)',
            'Accept-Encoding': 'gzip',
            'Connection': 'keep-alive'
        })
        
        # Token cache
        self.token_cache = {}
        self.token_cache_lock = threading.Lock()
        
        logger.info("APIClient initialized")
    
    def _get_cache_key(self, *args, **kwargs) -> str:
        """Generate cache key from arguments"""
        key_string = str(args) + str(sorted(kwargs.items()))
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _make_request(self, method: str, url: str, **kwargs) -> Optional[requests.Response]:
        """Make HTTP request with retry logic"""
        for attempt in range(MAX_RETRIES):
            try:
                response = self.session.request(
                    method=method,
                    url=url,
                    timeout=REQUEST_TIMEOUT,
                    **kwargs
                )
                
                if response.status_code == 200:
                    return response
                elif response.status_code == 429:
                    # Rate limited - wait longer
                    wait_time = RETRY_DELAY * (attempt + 1) * 2
                    logger.warning(f"Rate limited on {url}, waiting {wait_time}s")
                    time.sleep(wait_time)
                else:
                    logger.warning(f"Request failed: {response.status_code} on attempt {attempt + 1}")
                    
            except requests.exceptions.Timeout:
                logger.warning(f"Timeout on {url}, attempt {attempt + 1}")
            except requests.exceptions.ConnectionError:
                logger.warning(f"Connection error on {url}, attempt {attempt + 1}")
            except Exception as e:
                logger.error(f"Request error on {url}: {e}")
            
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))
        
        return None
    
    # ========================================================================
    # TOKEN MANAGEMENT
    # ========================================================================
    
    def get_access_token(self, uid: str, password: str, region: str = 'PK') -> Optional[str]:
        """Get access token for a guest account"""
        cache_key = f"token_{region}_{uid}"
        
        # Check cache
        with self.token_cache_lock:
            if cache_key in self.token_cache:
                token, expiry = self.token_cache[cache_key]
                if time.time() < expiry:
                    return token
        
        # Rate limit check
        if not self.rate_limiter.check(f"token_{uid}", 10, 60):
            logger.warning(f"Token rate limit exceeded for {uid}")
            return None
        
        # Make request
        payload = {
            'uid': uid,
            'password': password,
            'response_type': 'token',
            'client_type': '2',
            'client_secret': '2ee44819e9b4598845141067b281621874d0d5d7af9d8f7e00c1e54715b7d1e3',
            'client_id': '100067'
        }
        
        response = self._make_request('POST', FF_TOKEN_API, data=payload)
        
        if response and response.status_code == 200:
            data = response.json()
            token = data.get('access_token')
            
            if token:
                with self.token_cache_lock:
                    self.token_cache[cache_key] = (token, time.time() + 3600)
                return token
        
        return None
    
    def clear_token_cache(self):
        """Clear token cache"""
        with self.token_cache_lock:
            self.token_cache.clear()
        logger.info("Token cache cleared")
    
    # ========================================================================
    # LIKE API
    # ========================================================================
    
    def send_like(self, token: str, target_uid: str, region: str = 'PK') -> Tuple[bool, int]:
        """Send a single like"""
        api_url = REGION_API_MAP.get(region, REGION_API_MAP['PK'])['like']
        
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        response = self._make_request('POST', api_url, data=f'uid={target_uid}', headers=headers)
        
        if response:
            return response.status_code == 200, response.status_code
        return False, 0
    
    def send_bulk_likes(self, token: str, target_uid: str, count: int, region: str = 'PK') -> Dict[str, Any]:
        """Send multiple likes using same token (not recommended, use different guests)"""
        api_url = REGION_API_MAP.get(region, REGION_API_MAP['PK'])['like']
        headers = {'Authorization': f'Bearer {token}'}
        
        success_count = 0
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            for _ in range(min(count, 100)):
                future = executor.submit(
                    self._make_request, 'POST', api_url,
                    data=f'uid={target_uid}', headers=headers
                )
                futures.append(future)
            
            for future in as_completed(futures):
                response = future.result()
                if response and response.status_code == 200:
                    success_count += 1
        
        duration = time.time() - start_time
        
        return {
            'success': success_count,
            'total': min(count, 100),
            'duration': round(duration, 2),
            'speed': round(success_count / max(duration, 0.1), 1)
        }
    
    # ========================================================================
    # VISITOR API
    # ========================================================================
    
    def send_visitor(self, token: str, target_uid: str, region: str = 'PK') -> Tuple[bool, int]:
        """Send a single visitor"""
        api_url = REGION_API_MAP.get(region, REGION_API_MAP['PK'])['visit']
        
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        response = self._make_request('POST', api_url, data=f'uid={target_uid}', headers=headers)
        
        if response:
            return response.status_code == 200, response.status_code
        return False, 0
    
    # ========================================================================
    # SPAM API
    # ========================================================================
    
    def send_spam(self, token: str, target_uid: str, region: str = 'PK') -> Tuple[bool, int]:
        """Send a single spam request"""
        api_url = REGION_API_MAP.get(region, REGION_API_MAP['PK'])['spam']
        
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        response = self._make_request('POST', api_url, data=f'uid={target_uid}', headers=headers)
        
        if response:
            return response.status_code == 200, response.status_code
        return False, 0
    
    # ========================================================================
    # INFO API
    # ========================================================================
    
    def get_player_info(self, uid: str) -> Optional[Dict[str, Any]]:
        """Get player information from multiple APIs"""
        cache_key = self._get_cache_key('player_info', uid)
        
        # Check cache
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        # Try multiple API endpoints
        endpoints = [
            f"{FF_INFO_API}?id={uid}",
            f"{FF_INFO_API_BACKUP}?keyword={uid}",
            f"{FF_INFO_API_BACKUP2}?uid={uid}"
        ]
        
        for url in endpoints:
            response = self._make_request('GET', url)
            
            if response and response.status_code == 200:
                data = response.json()
                
                # Normalize response format
                info = self._normalize_player_info(data)
                if info:
                    self.cache.set(cache_key, info, ttl=300)  # Cache for 5 minutes
                    return info
        
        return None
    
    def _normalize_player_info(self, data: Dict) -> Optional[Dict]:
        """Normalize player info from different API formats"""
        try:
            return {
                'name': data.get('name') or data.get('nickname') or data.get('player_name') or 'Unknown',
                'level': data.get('level') or data.get('player_level') or 0,
                'kills': data.get('kills') or data.get('total_kills') or 0,
                'wins': data.get('wins') or data.get('total_wins') or 0,
                'matches': data.get('matches') or data.get('total_matches') or 0,
                'likes': data.get('likes') or data.get('total_likes') or 0,
                'headshots': data.get('headshots') or data.get('total_headshots') or 0,
                'kd': round(
                    (data.get('kills') or 0) / max((data.get('deaths') or 1), 1), 2
                )
            }
        except Exception as e:
            logger.error(f"Error normalizing player info: {e}")
            return None
    
    # ========================================================================
    # BULK OPERATIONS
    # ========================================================================
    
    def send_bulk_actions_with_guests(self, guests: List[Dict], target_uid: str, 
                                      action: str, region: str = 'PK') -> Dict[str, Any]:
        """Send bulk actions using multiple guest accounts"""
        start_time = time.time()
        success_count = 0
        
        # Get tokens for all guests
        tokens = []
        for guest in guests[:100]:  # Limit to 100 concurrent
            token = self.get_access_token(guest['uid'], guest['password'], region)
            if token:
                tokens.append(token)
        
        if not tokens:
            return {'success': 0, 'total': 0, 'message': 'No valid tokens'}
        
        # Send actions
        with ThreadPoolExecutor(max_workers=len(tokens)) as executor:
            futures = []
            
            for token in tokens:
                if action == 'like':
                    future = executor.submit(self.send_like, token, target_uid, region)
                elif action == 'visit':
                    future = executor.submit(self.send_visitor, token, target_uid, region)
                elif action == 'spam':
                    future = executor.submit(self.send_spam, token, target_uid, region)
                else:
                    continue
                futures.append(future)
            
            for future in as_completed(futures):
                success, _ = future.result()
                if success:
                    success_count += 1
        
        duration = time.time() - start_time
        
        return {
            'success': success_count,
            'total': len(tokens),
            'duration': round(duration, 2),
            'speed': round(success_count / max(duration, 0.1), 1),
            'message': f"Sent {success_count}/{len(tokens)} {action}s"
        }
    
    # ========================================================================
    # HEALTH CHECK
    # ========================================================================
    
    def health_check(self) -> Dict[str, Any]:
        """Check API health"""
        results = {
            'token_api': False,
            'info_api': False,
            'like_api': False
        }
        
        # Check token API
        response = self._make_request('GET', FF_TOKEN_API)
        results['token_api'] = response is not None
        
        # Check info API
        response = self._make_request('GET', f"{FF_INFO_API}?id=5351564274")
        results['info_api'] = response is not None and response.status_code == 200
        
        # Check like API (without auth)
        response = self._make_request('GET', FF_LIKE_API_PK)
        results['like_api'] = response is not None
        
        return results
    
    def shutdown(self):
        """Shutdown API client"""
        self.session.close()
        logger.info("APIClient shutdown complete")