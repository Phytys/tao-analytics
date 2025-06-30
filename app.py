from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from dash_app import create_dash
from services.tao_metrics import tao_metrics_service
from services.auth import require_admin, verify_admin_credentials, login_admin, logout_admin
import os
import logging
import socket
from datetime import datetime

logger = logging.getLogger(__name__)

def check_port_availability(host, port):
    """Check if a port is available."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((host, port))
            return True
    except OSError:
        return False

def create_app():
    logger.info("Initializing Flask application")
    
    server = Flask(__name__)
    server.secret_key = os.getenv('SECRET_KEY', 'tao-analytics-secret-key-2024')
    server.config["JSONIFY_PRETTYPRINT_REGULAR"] = False

    # Tesla-inspired landing page
    @server.route("/")
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
        
        return render_template("index.html", network_data=network_data, data_available=data_available)

    @server.route("/about")
    def about():
        """About page - placeholder for Sprint 1.5."""
        logger.info(f"About page accessed by {request.remote_addr}")
        return render_template("about_placeholder.html")

    @server.route('/admin/login', methods=['GET', 'POST'])
    def admin_login():
        """Admin login page."""
        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')
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
    def admin_logout():
        """Admin logout."""
        logger.info(f"Admin logout from {request.remote_addr}")
        session.pop('admin_authenticated', None)
        return redirect('/')

    @server.route('/admin/check-auth')
    def admin_check_auth():
        """Check if user is authenticated as admin."""
        is_authenticated = session.get('admin_authenticated', False)
        logger.debug(f"Auth check from {request.remote_addr}: {is_authenticated}")
        return jsonify({'authenticated': is_authenticated})

    @server.route('/admin/system-info')
    @require_admin
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

    @server.errorhandler(404)
    def not_found_error(error):
        logger.warning(f"404 error for {request.path} from {request.remote_addr}")
        return "Page not found", 404

    @server.errorhandler(500)
    def internal_error(error):
        logger.error(f"500 error for {request.path} from {request.remote_addr}: {error}")
        return "Internal server error", 500

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