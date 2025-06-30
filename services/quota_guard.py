"""
Quota Guard Service for TAO Analytics.
Tracks API calls to stay under monthly limits and provides reporting.
"""

import sqlite3
import argparse
from datetime import datetime, date
from typing import Dict, Optional
from pathlib import Path
import sys

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from models import engine, Base
from sqlalchemy import Column, Integer, String, DateTime, func, text
from sqlalchemy.orm import declarative_base
from sqlalchemy.exc import SQLAlchemyError

# Create a separate base for quota tracking
QuotaBase = declarative_base()

class ApiQuota(QuotaBase):
    """Track API calls per endpoint per month."""
    __tablename__ = "api_quota"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    endpoint = Column(String(100), nullable=False)  # e.g., '/subnet_screener', '/analytics/macro/aggregated'
    month = Column(String(7), nullable=False)  # YYYY-MM format
    count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Create the quota table
QuotaBase.metadata.create_all(engine)

class QuotaExceededError(Exception):
    """Raised when API quota is exceeded."""
    pass

class QuotaGuard:
    """Manages API call quotas and tracking."""
    
    def __init__(self):
        """Initialize quota guard."""
        self.engine = engine
    
    def _get_current_month(self) -> str:
        """Get current month in YYYY-MM format."""
        return datetime.now().strftime("%Y-%m")
    
    def _get_month_key(self, endpoint: str, month: str) -> tuple:
        """Get unique key for endpoint/month combination."""
        return (endpoint, month)
    
    def get_call_count(self, endpoint: str, month: Optional[str] = None) -> int:
        """
        Get current call count for an endpoint in a given month.
        
        Args:
            endpoint: API endpoint (e.g., '/subnet_screener')
            month: Month in YYYY-MM format (defaults to current month)
            
        Returns:
            Number of calls made this month
        """
        if month is None:
            month = self._get_current_month()
        
        try:
            with self.engine.connect() as conn:
                result = conn.execute(
                    text("SELECT count FROM api_quota WHERE endpoint = :endpoint AND month = :month"),
                    {"endpoint": endpoint, "month": month}
                ).fetchone()
                
                return result[0] if result else 0
        except SQLAlchemyError as e:
            print(f"Error getting call count: {e}")
            return 0
    
    def increment_call_count(self, endpoint: str, month: Optional[str] = None) -> int:
        """
        Increment call count for an endpoint in a given month.
        
        Args:
            endpoint: API endpoint
            month: Month in YYYY-MM format (defaults to current month)
            
        Returns:
            New call count after increment
        """
        if month is None:
            month = self._get_current_month()
        
        try:
            with self.engine.connect() as conn:
                # Try to update existing record
                result = conn.execute(
                    text("""
                        UPDATE api_quota 
                        SET count = count + 1, updated_at = :updated_at
                        WHERE endpoint = :endpoint AND month = :month
                    """),
                    {
                        "endpoint": endpoint, 
                        "month": month, 
                        "updated_at": datetime.utcnow()
                    }
                )
                
                if result.rowcount == 0:
                    # No existing record, create new one
                    conn.execute(
                        text("""
                            INSERT INTO api_quota (endpoint, month, count, created_at, updated_at)
                            VALUES (:endpoint, :month, 1, :created_at, :updated_at)
                        """),
                        {
                            "endpoint": endpoint,
                            "month": month,
                            "created_at": datetime.utcnow(),
                            "updated_at": datetime.utcnow()
                        }
                    )
                
                conn.commit()
                
                # Return new count
                return self.get_call_count(endpoint, month)
                
        except SQLAlchemyError as e:
            print(f"Error incrementing call count: {e}")
            return 0
    
    def check_quota(self, endpoint: str, limit: int = 1000, month: Optional[str] = None) -> bool:
        """
        Check if endpoint is within quota limit.
        
        Args:
            endpoint: API endpoint
            limit: Monthly call limit (default 1000 for TAO.app)
            month: Month to check (defaults to current month)
            
        Returns:
            True if within quota, False if exceeded
        """
        current_count = self.get_call_count(endpoint, month)
        return current_count < limit
    
    def enforce_quota(self, endpoint: str, limit: int = 1000, month: Optional[str] = None) -> int:
        """
        Check quota and increment count if within limit.
        
        Args:
            endpoint: API endpoint
            limit: Monthly call limit
            month: Month to check (defaults to current month)
            
        Returns:
            New call count after increment
            
        Raises:
            QuotaExceededError: If quota would be exceeded
        """
        if not self.check_quota(endpoint, limit, month):
            raise QuotaExceededError(
                f"Quota exceeded for {endpoint} in {month or self._get_current_month()}. "
                f"Limit: {limit}, Current: {self.get_call_count(endpoint, month)}"
            )
        
        return self.increment_call_count(endpoint, month)
    
    def get_monthly_report(self, month: Optional[str] = None) -> Dict[str, int]:
        """
        Get monthly report of all endpoint calls.
        
        Args:
            month: Month to report (defaults to current month)
            
        Returns:
            Dictionary of endpoint -> call count
        """
        if month is None:
            month = self._get_current_month()
        
        try:
            with self.engine.connect() as conn:
                result = conn.execute(
                    text("SELECT endpoint, count FROM api_quota WHERE month = :month ORDER BY count DESC"),
                    {"month": month}
                ).fetchall()
                
                return {row[0]: row[1] for row in result}
        except SQLAlchemyError as e:
            print(f"Error getting monthly report: {e}")
            return {}
    
    def get_all_time_report(self) -> Dict[str, Dict[str, int]]:
        """
        Get all-time report of endpoint calls by month.
        
        Returns:
            Dictionary of month -> {endpoint -> count}
        """
        try:
            with self.engine.connect() as conn:
                result = conn.execute(
                    text("SELECT month, endpoint, count FROM api_quota ORDER BY month DESC, count DESC")
                ).fetchall()
                
                report = {}
                for row in result:
                    month, endpoint, count = row
                    if month not in report:
                        report[month] = {}
                    report[month][endpoint] = count
                
                return report
        except SQLAlchemyError as e:
            print(f"Error getting all-time report: {e}")
            return {}

def main():
    """CLI interface for quota guard."""
    parser = argparse.ArgumentParser(description="TAO Analytics Quota Guard")
    parser.add_argument("--report", action="store_true", help="Show monthly quota report")
    parser.add_argument("--all-time", action="store_true", help="Show all-time quota report")
    parser.add_argument("--month", type=str, help="Month to report (YYYY-MM format)")
    parser.add_argument("--endpoint", type=str, help="Check specific endpoint")
    parser.add_argument("--limit", type=int, default=1000, help="Quota limit (default: 1000)")
    
    args = parser.parse_args()
    
    guard = QuotaGuard()
    
    if args.report:
        month = args.month or guard._get_current_month()
        report = guard.get_monthly_report(month)
        
        print(f"\n📊 Quota Report for {month}")
        print("=" * 50)
        
        if not report:
            print("No API calls recorded for this month.")
        else:
            total_calls = sum(report.values())
            print(f"Total calls: {total_calls}")
            print(f"Remaining quota: {args.limit - total_calls}")
            print()
            
            for endpoint, count in report.items():
                remaining = args.limit - count
                status = "✅" if count < args.limit else "❌"
                print(f"{status} {endpoint}: {count}/{args.limit} ({remaining} remaining)")
    
    elif args.all_time:
        report = guard.get_all_time_report()
        
        print("\n📊 All-Time Quota Report")
        print("=" * 50)
        
        if not report:
            print("No API calls recorded.")
        else:
            for month in sorted(report.keys(), reverse=True):
                print(f"\n{month}:")
                month_data = report[month]
                total = sum(month_data.values())
                print(f"  Total: {total} calls")
                
                for endpoint, count in month_data.items():
                    print(f"    {endpoint}: {count}")
    
    elif args.endpoint:
        month = args.month or guard._get_current_month()
        count = guard.get_call_count(args.endpoint, month)
        remaining = args.limit - count
        status = "✅" if count < args.limit else "❌"
        
        print(f"\n🔍 Endpoint: {args.endpoint}")
        print(f"📅 Month: {month}")
        print(f"📊 Calls: {count}/{args.limit} {status}")
        print(f"📈 Remaining: {remaining}")
    
    else:
        # Default: show current month report
        month = guard._get_current_month()
        report = guard.get_monthly_report(month)
        
        print(f"\n📊 Current Month Quota Report ({month})")
        print("=" * 50)
        
        if not report:
            print("No API calls recorded for this month.")
        else:
            total_calls = sum(report.values())
            print(f"Total calls: {total_calls}")
            print(f"Remaining quota: {args.limit - total_calls}")
            print()
            
            for endpoint, count in report.items():
                remaining = args.limit - count
                status = "✅" if count < args.limit else "❌"
                print(f"{status} {endpoint}: {count}/{args.limit} ({remaining} remaining)")

if __name__ == "__main__":
    main() 