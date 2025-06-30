from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from dash_app import create_dash
from services.tao_metrics import tao_metrics_service
from services.auth import require_admin, verify_admin_credentials, login_admin, logout_admin
import os

def create_app():
    server = Flask(__name__)
    server.secret_key = os.getenv('SECRET_KEY', 'tao-analytics-secret-key-2024')
    server.config["JSONIFY_PRETTYPRINT_REGULAR"] = False

    # Tesla-inspired landing page
    @server.route("/")
    def index():
        """Landing page."""
        # Get network overview for landing page
        try:
            network_data = tao_metrics_service.get_network_overview()
            data_available = True
        except Exception as e:
            print(f"Error loading network data: {e}")
            network_data = None
            data_available = False
        
        return render_template("index.html", network_data=network_data, data_available=data_available)

    @server.route("/about")
    def about():
        """About page - placeholder for Sprint 1.5."""
        return render_template("about_placeholder.html")

    @server.route('/admin/login', methods=['GET', 'POST'])
    def admin_login():
        """Admin login page."""
        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')
            
            if verify_admin_credentials(username, password):
                login_admin()
                return redirect(url_for('admin_system_info'))
            else:
                flash('Invalid credentials', 'error')
                return render_template('admin_login.html', error='Invalid username or password')
        
        return render_template('admin_login.html')

    @server.route('/admin/logout')
    def admin_logout():
        """Admin logout."""
        session.pop('admin_authenticated', None)
        return redirect('/')

    @server.route('/admin/check-auth')
    def admin_check_auth():
        """Check if user is authenticated as admin."""
        return jsonify({'authenticated': session.get('admin_authenticated', False)})

    @server.route('/admin/system-info')
    @require_admin
    def admin_system_info():
        """Admin system info page (redirects to Dash)."""
        return redirect('/dash/system-info')

    @server.before_request
    def check_system_info_access():
        """Check access to system info page."""
        if request.path == '/dash/system-info' and not session.get('admin_authenticated'):
            return redirect('/admin/login')

    create_dash(server)      # mounts at /dash/
    return server

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, host="0.0.0.0", port=5001) 