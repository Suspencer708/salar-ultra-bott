"""
API Endpoints for SALAAR X SPENCER ULTRA BOT
REST API for external access with authentication
"""

import json
import threading
from flask import Flask, request, jsonify
from functools import wraps

from database import DatabaseManager
from like_sender import LikeSender
from visitor_sender import VisitorSender
from spam_sender import SpamSender
from coin_system import CoinSystem
from config import API_PORT, API_HOST, API_ENABLED
from logger import get_logger

logger = get_logger(__name__)

app = Flask(__name__)


class APIEndpoints:
    """REST API for bot"""

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
        self.like_sender = LikeSender()
        self.visitor_sender = VisitorSender()
        self.spam_sender = SpamSender()
        self.coin_system = CoinSystem()

        self.api_keys = {}
        self._load_api_keys()
        self._register_routes()

        logger.info("APIEndpoints initialized")

    def _load_api_keys(self):
        """Load API keys from database"""
        import sqlite3
        from config import DATABASE_FILE

        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        cursor.execute("SELECT key, user_id, permissions FROM api_keys WHERE is_active = 1")
        for row in cursor.fetchall():
            self.api_keys[row[0]] = {
                'user_id': row[1],
                'permissions': row[2].split(',') if row[2] else []
            }

        conn.close()
        logger.info(f"Loaded {len(self.api_keys)} API keys")

    def _require_auth(self, permission: str = None):
        """Authentication decorator"""
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                api_key = request.headers.get('X-API-Key')
                if not api_key or api_key not in self.api_keys:
                    return jsonify({'error': 'Invalid or missing API key'}), 401

                if permission and permission not in self.api_keys[api_key]['permissions']:
                    return jsonify({'error': f'Missing required permission: {permission}'}), 403

                request.user_id = self.api_keys[api_key]['user_id']
                return f(*args, **kwargs)
            return decorated_function
        return decorator

    def _register_routes(self):
        """Register API routes"""

        @app.route('/api/health', methods=['GET'])
        def health():
            return jsonify({'status': 'online', 'version': '8.0.0'})

        @app.route('/api/like', methods=['POST'])
        @self._require_auth('like')
        def api_like():
            data = request.get_json()
            target = data.get('target')
            count = data.get('count', 100)
            region = data.get('region', 'PK')

            if not target:
                return jsonify({'error': 'Target UID required'}), 400

            result = self.like_sender.send_likes(target, count, region, request.user_id)
            return jsonify(result)

        @app.route('/api/visit', methods=['POST'])
        @self._require_auth('visit')
        def api_visit():
            data = request.get_json()
            target = data.get('target')
            count = data.get('count', 50)
            region = data.get('region', 'PK')

            if not target:
                return jsonify({'error': 'Target UID required'}), 400

            result = self.visitor_sender.send_visitors(target, count, region, request.user_id)
            return jsonify(result)

        @app.route('/api/spam', methods=['POST'])
        @self._require_auth('spam')
        def api_spam():
            data = request.get_json()
            target = data.get('target')
            count = data.get('count', 30)
            region = data.get('region', 'PK')

            if not target:
                return jsonify({'error': 'Target UID required'}), 400

            result = self.spam_sender.send_spam(target, count, region, request.user_id)
            return jsonify(result)

        @app.route('/api/balance', methods=['GET'])
        @self._require_auth()
        def api_balance():
            user_id = request.user_id
            balance = self.coin_system.get_balance(user_id)
            return jsonify({'user_id': user_id, 'balance': balance})

        @app.route('/api/stats', methods=['GET'])
        def api_stats():
            stats = self.db.get_bot_stats()
            return jsonify(stats)

        @app.route('/api/users', methods=['GET'])
        @self._require_auth('admin')
        def api_users():
            limit = request.args.get('limit', 50, type=int)
            users = self.db.get_all_users(limit)
            return jsonify(users)

    def start(self):
        """Start API server"""
        if not API_ENABLED:
            logger.info("API disabled")
            return

        def run_server():
            try:
                app.run(host=API_HOST, port=API_PORT, debug=False, use_reloader=False)
            except Exception as e:
                logger.error(f"API server error: {e}")

        thread = threading.Thread(target=run_server, daemon=True)
        thread.start()
        logger.info(f"API server started at http://{API_HOST}:{API_PORT}")