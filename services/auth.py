"""
Authentication service for TAO Analytics.
Provides simple admin authentication for system info access.
"""

import os
from functools import wraps
from flask import request, session, redirect, url_for, flash
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Admin credentials (in production, use proper user management)
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

# Ensure admin password is set
if not ADMIN_PASSWORD:
    raise ValueError("ADMIN_PASSWORD environment variable must be set. Please add it to your .env file.")

def require_admin(f):
    """Decorator to require admin authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_authenticated'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_login_required():
    """Check if admin login is required."""
    return not session.get('admin_authenticated')

def verify_admin_credentials(username, password):
    """Verify admin credentials."""
    return username == ADMIN_USERNAME and password == ADMIN_PASSWORD

def login_admin():
    """Log in admin user."""
    session['admin_authenticated'] = True

def logout_admin():
    """Log out admin user."""
    session.pop('admin_authenticated', None) 