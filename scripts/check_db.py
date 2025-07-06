#!/usr/bin/env python3
"""
Check current database configuration.
Usage: python scripts/check_db.py
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load .env file
load_dotenv(project_root / ".env")

def main():
    """Check and display current database configuration."""
    print("🔍 Database Configuration Check")
    print("=" * 50)
    
    # Check environment variables
    database_url = os.getenv('DATABASE_URL')
    heroku_db_url = os.getenv('HEROKU_DB_URL_FOR_SCRIPT')
    
    print(f"📋 Environment Variables:")
    print(f"   DATABASE_URL: {'✅ Set' if database_url else '❌ Not set'}")
    print(f"   HEROKU_DB_URL_FOR_SCRIPT: {'✅ Set' if heroku_db_url else '❌ Not set'}")
    
    # Check .env file
    env_file = project_root / ".env"
    print(f"\n📁 .env file: {'✅ Exists' if env_file.exists() else '❌ Not found'}")
    
    # Determine which database will be used
    print(f"\n🎯 Database Target:")
    if database_url:
        if 'postgresql' in database_url or 'postgres://' in database_url:
            print(f"   ☁️  Heroku PostgreSQL (from DATABASE_URL)")
        else:
            print(f"   📁 Local SQLite (from DATABASE_URL)")
    elif heroku_db_url:
        print(f"   ⚠️  HEROKU_DB_URL_FOR_SCRIPT is set but not used by cron_fetch.py")
        print(f"   📁 Local SQLite (default)")
    else:
        print(f"   📁 Local SQLite (default)")
    
    # Show what cron_fetch.py will use
    print(f"\n🚀 cron_fetch.py will use:")
    if database_url and ('postgresql' in database_url or 'postgres://' in database_url):
        print(f"   ☁️  Heroku PostgreSQL")
        print(f"   URL: {database_url[:50]}...")
    else:
        print(f"   📁 Local SQLite")
        print(f"   File: {project_root / 'tao.sqlite'}")
    
    # Show what run_heroku_cron.py will use
    print(f"\n🚀 run_heroku_cron.py will use:")
    if heroku_db_url:
        print(f"   ☁️  Heroku PostgreSQL")
        print(f"   URL: {heroku_db_url[:50]}...")
    else:
        print(f"   ❌ Error: HEROKU_DB_URL_FOR_SCRIPT not set in .env")
    
    print(f"\n💡 Commands:")
    print(f"   Local SQLite: python scripts/cron_fetch.py --once nightly")
    print(f"   Heroku DB:    python scripts/run_heroku_cron.py --once nightly")

if __name__ == "__main__":
    import sys
    main() 