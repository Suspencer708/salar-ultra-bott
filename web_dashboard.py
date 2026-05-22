"""
Web Dashboard for SALAAR X SPENCER ULTRA BOT
Flask-based dashboard for monitoring and management
"""

import threading
import json
from datetime import datetime
from flask import Flask, render_template, jsonify, request

from database import DatabaseManager
from analytics import Analytics
from config import WEB_DASHBOARD_PORT, WEB_DASHBOARD_HOST, WEB_DASHBOARD_ENABLED
from logger import get_logger

logger = get_logger(__name__)

app = Flask(__name__)


class WebDashboard:
    """Flask web dashboard for bot monitoring"""

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
        self.analytics = Analytics()
        self.server_thread = None
        self.is_running = False

        self._register_routes()

        logger.info("WebDashboard initialized")

    def _register_routes(self):
        """Register Flask routes"""

        @app.route('/')
        def index():
            return self._render_dashboard()

        @app.route('/api/stats')
        def api_stats():
            return jsonify(self.db.get_bot_stats())

        @app.route('/api/users')
        def api_users():
            limit = request.args.get('limit', 50, type=int)
            users = self.db.get_all_users(limit)
            return jsonify(users)

        @app.route('/api/analytics/daily')
        def api_daily_analytics():
            days = request.args.get('days', 7, type=int)
            analytics = self.analytics.get_daily_analytics(days)
            return jsonify(analytics)

        @app.route('/api/analytics/hourly')
        def api_hourly_analytics():
            hours = request.args.get('hours', 24, type=int)
            analytics = self.analytics.get_hourly_analytics(hours)
            return jsonify(analytics)

        @app.route('/api/guests')
        def api_guests():
            from guest_manager import GuestManager
            guest_manager = GuestManager()
            stats = guest_manager.get_region_stats()
            return jsonify(stats)

        @app.route('/api/commands')
        def api_commands():
            from user_commands import UserCommands
            user_commands = UserCommands()
            return jsonify(user_commands.get_command_stats())

    def _render_dashboard(self):
        """Render main dashboard HTML"""
        stats = self.db.get_bot_stats()

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>SALAAR X SPENCER BOT - Dashboard</title>
            <style>
                * {{ margin: 0; padding: 0; box-sizing: border-box; }}
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    background: linear-gradient(135deg, #1a1a2e, #16213e);
                    color: #fff;
                    padding: 20px;
                }}
                .container {{
                    max-width: 1400px;
                    margin: 0 auto;
                }}
                h1 {{
                    text-align: center;
                    margin-bottom: 30px;
                    color: #00ff88;
                    text-shadow: 0 0 10px rgba(0,255,136,0.5);
                }}
                .stats-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                    gap: 20px;
                    margin-bottom: 30px;
                }}
                .stat-card {{
                    background: rgba(255,255,255,0.1);
                    border-radius: 15px;
                    padding: 20px;
                    text-align: center;
                    backdrop-filter: blur(10px);
                    transition: transform 0.3s;
                }}
                .stat-card:hover {{
                    transform: translateY(-5px);
                }}
                .stat-value {{
                    font-size: 36px;
                    font-weight: bold;
                    color: #00ff88;
                }}
                .stat-label {{
                    font-size: 14px;
                    color: #ccc;
                    margin-top: 10px;
                }}
                .chart-container {{
                    background: rgba(255,255,255,0.1);
                    border-radius: 15px;
                    padding: 20px;
                    margin-bottom: 30px;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                }}
                th, td {{
                    padding: 12px;
                    text-align: left;
                    border-bottom: 1px solid rgba(255,255,255,0.1);
                }}
                th {{
                    background: rgba(0,255,136,0.2);
                    color: #00ff88;
                }}
                .status-online {{
                    color: #00ff88;
                }}
                .footer {{
                    text-align: center;
                    margin-top: 30px;
                    padding: 20px;
                    color: #666;
                }}
                @keyframes pulse {{
                    0% {{ opacity: 0.6; }}
                    100% {{ opacity: 1; }}
                }}
                .online-badge {{
                    display: inline-block;
                    width: 10px;
                    height: 10px;
                    border-radius: 50%;
                    background-color: #00ff88;
                    animation: pulse 1s infinite;
                    margin-right: 5px;
                }}
            </style>
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        </head>
        <body>
            <div class="container">
                <h1>🔥 SALAAR X SPENCER BOT DASHBOARD 🔥</h1>
                
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-value">{stats['total_users']:,}</div>
                        <div class="stat-label">Total Users</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">{stats['total_likes']:,}</div>
                        <div class="stat-label">Total Likes</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">{stats['total_visitors']:,}</div>
                        <div class="stat-label">Total Visitors</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">{stats['total_spam']:,}</div>
                        <div class="stat-label">Total Spam</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">{stats['total_coins']:,}</div>
                        <div class="stat-label">Total Coins</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">{stats['active_today']}</div>
                        <div class="stat-label">Active Today</div>
                    </div>
                </div>

                <div class="chart-container">
                    <canvas id="dailyChart"></canvas>
                </div>

                <div class="chart-container">
                    <canvas id="regionChart"></canvas>
                </div>

                <div class="stat-card">
                    <h3>System Status</h3>
                    <p><span class="online-badge"></span> <span class="status-online">Bot Online</span></p>
                    <p>Version: 8.0.0</p>
                    <p>Uptime: 24/7</p>
                </div>
            </div>

            <script>
                fetch('/api/analytics/daily?days=7')
                    .then(res => res.json())
                    .then(data => {{
                        const ctx = document.getElementById('dailyChart').getContext('2d');
                        new Chart(ctx, {{
                            type: 'line',
                            data: {{
                                labels: data.map(d => d.date),
                                datasets: [
                                    {{
                                        label: 'Likes',
                                        data: data.map(d => d.total_likes),
                                        borderColor: '#00ff88',
                                        fill: false
                                    }},
                                    {{
                                        label: 'Active Users',
                                        data: data.map(d => d.active_users),
                                        borderColor: '#ffaa00',
                                        fill: false
                                    }}
                                ]
                            }},
                            options: {{
                                responsive: true,
                                title: {{
                                    display: true,
                                    text: '7-Day Activity'
                                }}
                            }}
                        }});
                    }});

                fetch('/api/guests')
                    .then(res => res.json())
                    .then(data => {{
                        const ctx = document.getElementById('regionChart').getContext('2d');
                        new Chart(ctx, {{
                            type: 'bar',
                            data: {{
                                labels: Object.keys(data),
                                datasets: [{{
                                    label: 'Guest Accounts',
                                    data: Object.values(data),
                                    backgroundColor: '#00ff88'
                                }}]
                            }},
                            options: {{
                                responsive: true,
                                title: {{
                                    display: true,
                                    text: 'Guest Accounts by Region'
                                }}
                            }}
                        }});
                    }});
            </script>
        </body>
        </html>
        """
        return html

    def start(self):
        """Start web dashboard server"""
        if not WEB_DASHBOARD_ENABLED:
            logger.info("Web dashboard disabled")
            return

        def run_server():
            self.is_running = True
            try:
                app.run(host=WEB_DASHBOARD_HOST, port=WEB_DASHBOARD_PORT, debug=False, use_reloader=False)
            except Exception as e:
                logger.error(f"Web dashboard error: {e}")
            finally:
                self.is_running = False

        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()
        logger.info(f"Web dashboard started at http://{WEB_DASHBOARD_HOST}:{WEB_DASHBOARD_PORT}")

    def stop(self):
        """Stop web dashboard"""
        self.is_running = False
        logger.info("Web dashboard stopped")