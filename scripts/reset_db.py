#!/usr/bin/env python
import sys
from pathlib import Path

# Add the parent directory to Python path
sys.path.append(str(Path(__file__).parent.parent))
from models import Base, engine

def reset_db():
    print("Dropping all tables...")
    Base.metadata.drop_all(engine)
    
    print("Creating tables with latest schema...")
    Base.metadata.create_all(engine)
    
    print("Database reset complete!")

if __name__ == "__main__":
    try:
        reset_db()
    except Exception as e:
        print("ERROR:", e)
        sys.exit(1) 