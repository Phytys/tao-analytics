"""
Favicon service for TAO Analytics.
Fetches and caches favicons from websites with fallback options.
"""

import os
import requests
import hashlib
from pathlib import Path
from urllib.parse import urljoin, urlparse
from typing import Optional, Dict, Any
from bs4 import BeautifulSoup
import time

from .cache import cached, api_cache


class FaviconService:
    """Service for fetching and managing favicons."""
    
    def __init__(self, cache_dir: str = "static/favicons"):
        """
        Initialize favicon service.
        
        Args:
            cache_dir: Directory to store favicon files
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Common favicon paths to try
        self.favicon_paths = [
            '/favicon.ico',
            '/favicon.png',
            '/favicon.jpg',
            '/favicon.jpeg',
            '/apple-touch-icon.png',
            '/apple-touch-icon-precomposed.png',
            '/icon.png',
            '/logo.png'
        ]
    
    def _get_domain(self, url: str) -> str:
        """Extract domain from URL."""
        parsed = urlparse(url)
        return parsed.netloc.lower()
    
    def _get_favicon_filename(self, domain: str, url: str) -> str:
        """Generate filename for favicon based on domain and URL."""
        # Create hash of the URL to avoid filename conflicts
        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
        return f"{domain}_{url_hash}.ico"
    
    @cached(api_cache)
    def _fetch_url_content(self, url: str, timeout: int = 10) -> Optional[str]:
        """Fetch URL content with caching."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            return response.text
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return None
    
    def _extract_favicon_from_html(self, html_content: str, base_url: str) -> Optional[str]:
        """Extract favicon URL from HTML content."""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Look for favicon links
            favicon_links = soup.find_all('link', rel=lambda x: x and 'icon' in x.lower())
            
            for link in favicon_links:
                href = link.get('href')
                if href:
                    # Handle relative URLs
                    if href.startswith('//'):
                        href = 'https:' + href
                    elif href.startswith('/'):
                        href = urljoin(base_url, href)
                    elif not href.startswith('http'):
                        href = urljoin(base_url, href)
                    
                    return href
            
            return None
        except Exception as e:
            print(f"Error parsing HTML for favicon: {e}")
            return None
    
    def _download_favicon(self, favicon_url: str, filename: str) -> bool:
        """Download favicon and save to cache directory."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(favicon_url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # Check if it's actually an image
            content_type = response.headers.get('content-type', '')
            if not content_type.startswith('image/'):
                return False
            
            # Save to cache
            filepath = self.cache_dir / filename
            with open(filepath, 'wb') as f:
                f.write(response.content)
            
            return True
        except Exception as e:
            print(f"Error downloading favicon from {favicon_url}: {e}")
            return False
    
    def get_favicon(self, website_url: str) -> Optional[str]:
        """
        Get favicon for a website.
        
        Args:
            website_url: Website URL to get favicon for
            
        Returns:
            Path to favicon file or None if not found
        """
        if not website_url:
            return None
        
        domain = self._get_domain(website_url)
        
        # Try to find favicon URL
        favicon_url = None
        
        # Method 1: Try common favicon paths
        for path in self.favicon_paths:
            test_url = urljoin(website_url, path)
            try:
                response = requests.head(test_url, timeout=5)
                if response.status_code == 200:
                    favicon_url = test_url
                    break
            except:
                continue
        
        # Method 2: Extract from HTML if not found
        if not favicon_url:
            html_content = self._fetch_url_content(website_url)
            if html_content:
                favicon_url = self._extract_favicon_from_html(html_content, website_url)
        
        # Method 3: Try Google's favicon service as fallback
        if not favicon_url:
            favicon_url = f"https://www.google.com/s2/favicons?domain={domain}&sz=32"
        
        # Download and cache favicon
        if favicon_url:
            filename = self._get_favicon_filename(domain, favicon_url)
            filepath = self.cache_dir / filename
            
            # Check if already cached
            if filepath.exists():
                return str(filepath)
            
            # Download if not cached
            if self._download_favicon(favicon_url, filename):
                return str(filepath)
        
        return None
    
    def get_favicon_url(self, website_url: str) -> Optional[str]:
        """
        Get favicon URL for use in templates.
        
        Args:
            website_url: Website URL
            
        Returns:
            URL path to favicon or None
        """
        favicon_path = self.get_favicon(website_url)
        if favicon_path:
            # Convert to URL path
            return f"/static/favicons/{Path(favicon_path).name}"
        return None
    
    def cleanup_old_favicons(self, max_age_days: int = 30) -> int:
        """
        Clean up old favicon files.
        
        Args:
            max_age_days: Maximum age in days before deletion
            
        Returns:
            Number of files deleted
        """
        if not self.cache_dir.exists():
            return 0
        
        current_time = time.time()
        max_age_seconds = max_age_days * 24 * 3600
        deleted_count = 0
        
        for filepath in self.cache_dir.glob("*.ico"):
            if current_time - filepath.stat().st_mtime > max_age_seconds:
                try:
                    filepath.unlink()
                    deleted_count += 1
                except Exception as e:
                    print(f"Error deleting {filepath}: {e}")
        
        return deleted_count


# Global instance
favicon_service = FaviconService() 