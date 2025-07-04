"""
Security configuration for TAO Analytics.
Centralized security settings and constants.
"""

import os
from datetime import timedelta

# Rate limiting configuration
RATE_LIMITS = {
    'default': ["1000 per day", "200 per hour"],  # Increased for Dash dashboards
    'landing_page': "100 per hour",
    'admin_login': "5 per minute",
    'admin_endpoints': "30 per minute",
    'api_endpoints': "100 per hour",
    # Dash page rate limits (now use default limits)
    'dash_system_info': "30 per minute",      # Admin only - stricter
    'dash_explorer': "200 per hour",          # Main explorer page (increased)
    'dash_screener': "200 per hour",          # Screener page (increased)
    'dash_subnet_detail': "200 per hour",     # Individual subnet pages
    'dash_default': "200 per hour"            # Other Dash pages (increased)
}

# Security headers configuration
SECURITY_HEADERS = {
    'content_security_policy': {
        'default-src': ["'self'"],
        'script-src': ["'self'", "'unsafe-inline'", "https://cdn.plot.ly"],
        'style-src': ["'self'", "'unsafe-inline'", "https://cdn.jsdelivr.net"],
        'img-src': ["'self'", "data:", "https:"],
        'font-src': ["'self'", "https://cdn.jsdelivr.net"],
    },
    'force_https': os.getenv('FORCE_HTTPS', 'false').lower() == 'true'
}

# Input validation patterns
INPUT_PATTERNS = {
    'username': r'^[a-zA-Z0-9\s\-_.,!?@#$%&*()]+$',
    'search': r'^[a-zA-Z0-9\s\-_.,!?@#$%&*()]+$',
    'category': r'^[a-zA-Z0-9\s\-_.,!?@#$%&*()]+$'
}

# Input length limits
INPUT_LIMITS = {
    'username': 50,
    'search': 100,
    'category': 50,
    'password': 128
}

# Suspicious activity patterns
SUSPICIOUS_PATTERNS = [
    '/admin', '/api', '/config', '/.env', '/wp-admin', '/phpmyadmin',
    'union', 'select', 'insert', 'update', 'delete', 'drop', 'exec',
    'script', 'javascript', 'vbscript', 'onload', 'onerror'
]

# Session security
SESSION_CONFIG = {
    'permanent': False,
    'max_age': timedelta(hours=8),  # 8 hour session timeout
    'secure': os.getenv('SESSION_SECURE', 'false').lower() == 'true',
    'httponly': True,
    'samesite': 'Lax'
}

# Environment validation
REQUIRED_ENV_VARS = {
    'SECRET_KEY': 'Flask secret key for session security',
    'TAO_APP_API_KEY': 'TAO.app API key for data fetching',
    'OPENAI_API_KEY': 'OpenAI API key for enrichment'
}

# Security warnings
SECURITY_WARNINGS = {
    'weak_secret_key': 32,  # Minimum length for secret key
    'missing_env_vars': REQUIRED_ENV_VARS
}

# Logging configuration for security
SECURITY_LOGGING = {
    'suspicious_requests': True,
    'admin_access': True,
    'rate_limit_violations': True,
    'authentication_failures': True
} 