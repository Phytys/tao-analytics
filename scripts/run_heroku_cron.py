#!/usr/bin/env python3
"""
Convenience script to run cron_fetch.py targeting Heroku database.
Usage: python scripts/run_heroku_cron.py --once nightly
"""

import os
import sys
import subprocess
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load .env file
load_dotenv(project_root / ".env")

# Get Heroku database URL from environment
HEROKU_DB_URL = os.getenv("HEROKU_DB_URL_FOR_SCRIPT")
if not HEROKU_DB_URL:
    print("❌ Error: HEROKU_DB_URL_FOR_SCRIPT not found in .env file")
    print("Please add HEROKU_DB_URL_FOR_SCRIPT=your_heroku_db_url to your .env file")
    sys.exit(1)

def main():
    """Run cron_fetch.py with Heroku database targeting."""
    # Set environment variable
    env = os.environ.copy()
    env['DATABASE_URL'] = HEROKU_DB_URL  # type: ignore - we already check it's not None above
    
    # Build command
    cmd = [sys.executable, 'scripts/cron_fetch.py'] + sys.argv[1:]
    
    print(f"🚀 Running cron_fetch.py targeting Heroku database...")
    print(f"Command: {' '.join(cmd)}")
    print(f"Database: {HEROKU_DB_URL[:50] if HEROKU_DB_URL else 'Unknown'}...")
    print("-" * 50)
    
    # Run the command
    result = subprocess.run(cmd, env=env, cwd=project_root)
    
    if result.returncode == 0:
        print("✅ Cron job completed successfully!")
    else:
        print(f"❌ Cron job failed with exit code {result.returncode}")
        sys.exit(result.returncode)

if __name__ == "__main__":
    main() 