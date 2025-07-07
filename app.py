from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from dash_app import create_dash
from services.tao_metrics import tao_metrics_service
from services.auth import require_admin, verify_admin_credentials, login_admin, logout_admin
import os
import logging
import socket
from datetime import datetime
from flask_talisman import Talisman
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_caching import Cache
import re

logger = logging.getLogger(__name__)

def check_port_availability(host, port):
    """Check if a port is available."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((host, port))
            return True
    except OSError:
        return False

def validate_input(text, max_length=100):
    """Basic input validation."""
    if not text or len(text) > max_length:
        return False
    # Allow alphanumeric, spaces, and common punctuation
    return bool(re.match(r'^[a-zA-Z0-9\s\-_.,!?@#$%&*()]+$', text))

def create_app():
    logger.info("Initializing Flask application")
    
    server = Flask(__name__)
    server.secret_key = os.getenv('SECRET_KEY', 'tao-analytics-secret-key-2024')
    server.config["JSONIFY_PRETTYPRINT_REGULAR"] = False
    
    # Configure Redis caching
    if os.getenv('REDIS_URL'):
        cache_config = {
            'CACHE_TYPE': 'RedisCache',
            'CACHE_REDIS_URL': os.getenv('REDIS_URL'),
            'CACHE_DEFAULT_TIMEOUT': 300,  # 5 minutes default
            'CACHE_KEY_PREFIX': 'tao_analytics_'
        }
    else:
        # Use simple in-process cache for local development without Redis
        cache_config = {
            'CACHE_TYPE': 'SimpleCache',
            'CACHE_DEFAULT_TIMEOUT': 300
        }
    
    # Initialize cache
    cache = Cache()
    cache.init_app(server, config=cache_config)
    
    # Make cache available globally
    server.cache = cache

    # Security headers
    Talisman(server, 
             content_security_policy={
                 'default-src': ["'self'"],
                 'script-src': ["'self'", "'unsafe-inline'", "https://cdn.plot.ly", "https://s3.tradingview.com"],
                 'style-src': ["'self'", "'unsafe-inline'", "https://cdn.jsdelivr.net", "https://fonts.googleapis.com", "https://cdnjs.cloudflare.com"],
                 'img-src': ["'self'", "data:", "https:"],
                 'font-src': ["'self'", "https://cdn.jsdelivr.net", "https://fonts.gstatic.com", "https://cdnjs.cloudflare.com"],
                 'frame-src': ["'self'", "https://s3.tradingview.com", "https://s.tradingview.com", "https://www.tradingview.com", "https://www.tradingview-widget.com", "https://tradingview-widget.com", "https://www.geckoterminal.com"],
                 'connect-src': ["'self'", "https://s3.tradingview.com", "https://www.tradingview.com", "https://www.geckoterminal.com"],
             },
             force_https=os.getenv('FORCE_HTTPS', 'false').lower() == 'true')

    # Rate limiting
    limiter = Limiter(
        get_remote_address,
        app=server,
        default_limits=["1000 per day", "200 per hour"],
        storage_uri="memory://"
    )

    # Tesla-inspired landing page
    @server.route("/")
    @limiter.limit("100 per hour")
    def index():
        """Landing page."""
        logger.info(f"Landing page accessed by {request.remote_addr}")
        
        # Get network overview for landing page
        try:
            network_data = tao_metrics_service.get_network_overview()
            data_available = True
            logger.debug("Successfully loaded network data for landing page")
        except Exception as e:
            logger.error(f"Error loading network data: {e}")
            network_data = None
            data_available = False
        
        # Get GPT analysis insights for landing page
        try:
            from services.correlation_analysis import correlation_service
            gpt_result = correlation_service.get_analysis()
            if gpt_result['success'] and gpt_result['status'] in ['Cached', 'Generated']:
                # Extract the JSON data from the analysis
                analysis_text = gpt_result['analysis']
                # Look for JSON in the analysis text - try multiple patterns
                import re
                import json
                
                # Try to find JSON with more flexible pattern
                # Look for complete JSON object at the end of the analysis
                json_patterns = [
                    # Look for JSON at the end of the text (most common case)
                    r'(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\})\s*$',
                    # Look for JSON with the specific keys we expect
                    r'(\{[^{}]*"undervalued"[^{}]*(?:\{[^{}]*\}[^{}]*)*"scam_flags"[^{}]*(?:\{[^{}]*\}[^{}]*)*"healthy"[^{}]*(?:\{[^{}]*\}[^{}]*)*\})',
                    # Fallback: look for any JSON object with our expected keys
                    r'(\{[^{}]*"undervalued"[^{}]*\})',
                ]
                
                gpt_insights = None
                for pattern in json_patterns:
                    json_match = re.search(pattern, analysis_text, re.DOTALL)
                    if json_match:
                        try:
                            # Use the first capture group if it exists, otherwise use the whole match
                            json_str = json_match.group(1) if json_match.groups() else json_match.group()
                            gpt_insights = json.loads(json_str)
                            logger.info(f"Successfully extracted GPT insights from analysis")
                            break
                        except json.JSONDecodeError as e:
                            logger.debug(f"JSON decode error with pattern {pattern}: {e}")
                            continue
                
                if not gpt_insights:
                    logger.warning("Could not extract JSON from GPT analysis text")
                    # For debugging, let's see what the analysis text looks like
                    logger.debug(f"Analysis text preview: {analysis_text[:500]}...")
                    
                    # No fallback data - show missing data instead
                    gpt_insights = None
            else:
                logger.warning(f"GPT analysis not available: {gpt_result.get('status', 'unknown')}")
                gpt_insights = None
        except Exception as e:
            logger.error(f"Error loading GPT analysis for landing page: {e}")
            gpt_insights = None
        
        return render_template("index.html", 
                             network_data=network_data, 
                             data_available=data_available,
                             gpt_insights=gpt_insights)

    @server.route("/about")
    @limiter.limit("100 per hour")
    def about():
        """About page."""
        logger.info(f"About page accessed by {request.remote_addr}")
        return render_template("about.html")

    @server.route('/admin/login', methods=['GET', 'POST'])
    @limiter.limit("5 per minute")
    def admin_login():
        """Admin login page."""
        if request.method == 'POST':
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')
            
            # Input validation
            if not validate_input(username, 50) or not password:
                logger.warning(f"Invalid input in admin login from {request.remote_addr}")
                flash('Invalid input', 'error')
                return render_template('admin_login.html', error='Invalid input')
            
            logger.info(f"Admin login attempt from {request.remote_addr} for user: {username}")
            
            if verify_admin_credentials(username, password):
                login_admin()
                logger.info(f"Successful admin login for user: {username}")
                return redirect(url_for('admin_system_info'))
            else:
                logger.warning(f"Failed admin login attempt for user: {username} from {request.remote_addr}")
                flash('Invalid credentials', 'error')
                return render_template('admin_login.html', error='Invalid username or password')
        
        logger.info(f"Admin login page accessed by {request.remote_addr}")
        return render_template('admin_login.html')

    @server.route('/admin/logout')
    @limiter.limit("10 per minute")
    def admin_logout():
        """Admin logout."""
        logger.info(f"Admin logout from {request.remote_addr}")
        session.pop('admin_authenticated', None)
        return redirect('/')

    @server.route('/admin/check-auth')
    @limiter.limit("30 per minute")
    def admin_check_auth():
        """Check if user is authenticated as admin."""
        is_authenticated = session.get('admin_authenticated', False)
        logger.debug(f"Auth check from {request.remote_addr}: {is_authenticated}")
        return jsonify({'authenticated': is_authenticated})

    @server.route('/api/search')
    @limiter.limit("100 per hour")
    def search_subnets_api():
        """Search subnets API endpoint (unified logic)."""
        query = request.args.get('q', '').strip()
        if not query:
            return jsonify({'results': []})
        try:
            from services.db import search_subnets
            results = search_subnets(query=query, return_type='dict', limit=5)
            return jsonify({'results': results})
        except Exception as e:
            logger.error(f"Search error: {e}")
            return jsonify({'results': [], 'error': 'Search failed'})

    @server.route('/admin/system-info')
    @require_admin
    @limiter.limit("30 per minute")
    def admin_system_info():
        """Admin system info page (redirects to Dash)."""
        logger.info(f"Admin system info accessed by {request.remote_addr}")
        return redirect('/dash/system-info')

    @server.before_request
    def check_system_info_access():
        """Check access to system info page."""
        if request.path == '/dash/system-info' and not session.get('admin_authenticated'):
            logger.warning(f"Unauthorized access attempt to system info from {request.remote_addr}")
            return redirect('/admin/login')

    @server.before_request
    def log_suspicious_activity():
        """Log potentially suspicious requests for security monitoring."""
        # Log requests with suspicious patterns
        suspicious_patterns = [
            '/admin', '/api', '/config', '/.env', '/wp-admin', '/phpmyadmin',
            'union', 'select', 'insert', 'update', 'delete', 'drop', 'exec'
        ]
        
        user_agent = request.headers.get('User-Agent', '').lower()
        path = request.path.lower()
        query = request.query_string.decode('utf-8').lower()
        
        # Skip Dash callback endpoints (they're legitimate)
        if path.startswith('/dash/_dash-'):
            return
        
        # Check for suspicious patterns
        for pattern in suspicious_patterns:
            if pattern in path or pattern in query or pattern in user_agent:
                logger.warning(f"Suspicious request detected from {request.remote_addr}: "
                             f"path={request.path}, query={query}, user_agent={user_agent[:100]}")
                break
        
        # Log admin access attempts
        if '/admin' in path:
            logger.info(f"Admin access attempt from {request.remote_addr}: {request.path}")

    @server.errorhandler(404)
    def not_found_error(error):
        logger.warning(f"404 error for {request.path} from {request.remote_addr}")
        return "Page not found", 404

    @server.errorhandler(500)
    def internal_error(error):
        logger.error(f"500 error for {request.path} from {request.remote_addr}: {error}")
        return "Internal server error", 500

    @server.errorhandler(429)
    def ratelimit_handler(error):
        logger.warning(f"Rate limit exceeded from {request.remote_addr}")
        return "Too many requests. Please try again later.", 429

    logger.info("Creating Dash application")
    create_dash(server)      # mounts at /dash/
    
    logger.info("Flask application initialization complete")
    return server

if __name__ == "__main__":
    # Configure logging only when running app.py directly
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/app.log'),
            logging.StreamHandler()
        ]
    )
    
    # Reduce terminal verbosity for development
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    logging.getLogger('dash').setLevel(logging.WARNING)
    
    # Ensure logs directory exists
    os.makedirs('logs', exist_ok=True)
    
    logger.info("Starting TAO Analytics Flask application")
    
    # Try multiple ports
    host = "0.0.0.0"
    ports_to_try = [5001, 5002, 5003, 5004, 5005]
    
    for port in ports_to_try:
        if check_port_availability(host, port):
            logger.info(f"Port {port} is available, starting server on {host}:{port}")
            try:
                app = create_app()
                logger.info("Flask app created successfully, starting server...")
                app.run(debug=True, host=host, port=port)
                break  # Successfully started, exit the loop
            except Exception as e:
                logger.error(f"Failed to start Flask application on port {port}: {e}")
                continue
        else:
            logger.warning(f"Port {port} is already in use, trying next port...")
    else:
        logger.error(f"All ports {ports_to_try} are in use. Please stop existing processes or use a different port range.")
        logger.info("You can find processes using these ports with: lsof -i :5001-5005")
        exit(1) 