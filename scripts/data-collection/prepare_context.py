#!/usr/bin/env python
"""
Prepare context for subnet analysis.

This script collects and prepares context for subnet analysis by:
1. Fetching basic info from the screener database
2. Scraping website content (if available)
3. Fetching GitHub README (if available)
4. Cleaning and formatting the content
5. Saving the prepared context to a JSON file

Usage:
    python prepare_context.py [--netuid <netuid>] [--output <output_file>]

Options:
    --netuid <netuid>    : NetUID of the subnet to analyze (if not provided, processes all subnets)
    --output <file>      : Output file to save context (default: contexts/<netuid>.json)
    --no-save           : Don't save context to file (just print it)
"""

import sys
from pathlib import Path
import requests
import httpx
from bs4 import BeautifulSoup
import re
import json
import time
from typing import Optional, Dict, List
from dataclasses import dataclass, asdict
from datetime import datetime
from fake_useragent import UserAgent
import hashlib

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from models import ScreenerRaw
from config import DB_URL
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

# Constants for content limits
MAX_WEBSITE_CHARS = 1000  # Maximum characters to fetch from website
MAX_README_CHARS = 2000   # Maximum characters to fetch from README

@dataclass
class SubnetContext:
    """Structured context for a subnet.
    
    Attributes:
        netuid: The subnet's NetUID
        subnet_name: Name of the subnet
        website_url: URL of the subnet's website
        github_repo: URL of the subnet's GitHub repository
        website_content: Scraped content from the website
        readme_content: Content from the GitHub README
        token_count: Estimated token count for the content
        prepared_at: Timestamp when the context was prepared
    """
    netuid: int
    subnet_name: str
    website_url: Optional[str]
    github_repo: Optional[str]
    website_content: Optional[str]
    readme_content: Optional[str]
    token_count: int
    prepared_at: str

def clean_text(text: str) -> str:
    """Clean text by removing HTML, extra whitespace, etc."""
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Remove multiple spaces
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def get_headers() -> Dict[str, str]:
    """Get randomized headers for requests."""
    ua = UserAgent()
    return {
        'User-Agent': ua.random,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Cache-Control': 'max-age=0',
    }

def fetch_website_content(url: str, max_retries: int = 3) -> Optional[str]:
    """Fetch and clean content from a website using httpx with proper headers."""
    headers = get_headers()
    
    for attempt in range(max_retries):
        try:
            print(f"Attempt {attempt + 1}/{max_retries} to fetch {url}")
            
            # Use httpx for better async support and modern HTTP features
            with httpx.Client(timeout=30.0, follow_redirects=True) as client:
                response = client.get(url, headers=headers)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Remove unwanted elements
                    for element in soup(['script', 'style', 'nav', 'header', 'footer', 'iframe', 'noscript']):
                        element.decompose()
                    
                    # Get text and clean it
                    text = soup.get_text(separator=' ', strip=True)
                    text = clean_text(text)
                    
                    if text:
                        if len(text) > MAX_WEBSITE_CHARS:
                            text = text[:MAX_WEBSITE_CHARS] + "..."
                        return text
                    else:
                        print("No text content found in the page")
                else:
                    print(f"HTTP {response.status_code} error")
                    
        except httpx.TimeoutException:
            print("Request timed out")
        except httpx.RequestError as e:
            print(f"Request failed: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")
        
        if attempt < max_retries - 1:
            print("Waiting before retry...")
            time.sleep(2)
    
    return None

def fetch_github_readme(repo_url: str) -> Optional[str]:
    """Fetch and clean README content from GitHub."""
    try:
        if "github.com" in repo_url:
            parts = repo_url.rstrip("/").split("/")
            if len(parts) >= 5:  # github.com/owner/repo
                owner, repo = parts[-2], parts[-1]
                print(f"Fetching README for {owner}/{repo}")
                
                # Try raw content URLs
                branches = ['main', 'master']
                for branch in branches:
                    raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/README.md"
                    response = requests.get(raw_url, timeout=10)
                    if response.status_code == 200:
                        content = response.text
                        print(f"Successfully fetched README from {branch} branch")
                        if content:
                            content = clean_text(content)
                            if len(content) > MAX_README_CHARS:
                                content = content[:MAX_README_CHARS] + "..."
                            return content
    except Exception as e:
        print(f"Error fetching README: {e}")
    return None

def count_tokens(text: str) -> int:
    """Simple token count estimation (rough approximation)."""
    # Rough estimate: 1 token ≈ 4 characters
    return len(text) // 4

def get_all_netuids() -> List[int]:
    """Get list of all netuids from the database."""
    engine = create_engine(DB_URL)
    with Session(engine) as session:
        return [row.netuid for row in session.query(ScreenerRaw).all()]

def prepare_context(netuid: int) -> Optional[SubnetContext]:
    """Prepare context for a subnet."""
    engine = create_engine(DB_URL)
    with Session(engine) as session:
        # Get raw data from screener
        raw = session.get(ScreenerRaw, netuid)
        if not raw:
            print(f"No data found for subnet {netuid}")
            return None
        
        data = raw.raw_json
        
        # Extract basic info
        subnet_name = data.get('subnet_name', '')
        
        # Try all possible URL fields
        website_url = None
        for url_field in ['subnet_website', 'subnet_url']:
            url = data.get(url_field)
            if url:
                website_url = url
                break
        
        # Format website URL if needed
        if website_url:
            if not website_url.startswith(('http://', 'https://')):
                website_url = f'https://{website_url}'
            print(f"Found website URL: {website_url}")
        
        github_repo = data.get('github_repo')
        if github_repo:
            print(f"Found GitHub repo: {github_repo}")
        
        # Fetch content
        website_content = None
        if website_url:
            print(f"Fetching website content from {website_url}")
            website_content = fetch_website_content(website_url)
            if website_content:
                print(f"Successfully fetched {len(website_content)} characters from website")
            else:
                print("Failed to fetch website content")
        
        readme_content = None
        if github_repo:
            readme_content = fetch_github_readme(github_repo)
            if readme_content:
                print(f"Successfully fetched {len(readme_content)} characters from README")
            else:
                print("Failed to fetch README content")
        
        # Create context
        context = SubnetContext(
            netuid=netuid,
            subnet_name=subnet_name,
            website_url=website_url,
            github_repo=github_repo,
            website_content=website_content,
            readme_content=readme_content,
            token_count=0,  # Will be calculated below
            prepared_at=datetime.now().isoformat()
        )
        
        # Calculate total tokens
        total_tokens = 0
        if website_content:
            total_tokens += count_tokens(website_content)
        if readme_content:
            total_tokens += count_tokens(readme_content)
        context.token_count = total_tokens
        
        return context

def format_context(context: SubnetContext) -> str:
    """Format context for LLM consumption."""
    parts = [
        f"Subnet {context.netuid}: {context.subnet_name}",
    ]
    
    if context.website_url:
        parts.append(f"\nWebsite: {context.website_url}")
    if context.github_repo:
        parts.append(f"\nGitHub: {context.github_repo}")
    
    if context.website_content:
        parts.append("\nWebsite Content:")
        parts.append(context.website_content)
    
    if context.readme_content:
        parts.append("\nGitHub README:")
        parts.append(context.readme_content)
    
    return "\n".join(parts)

def compute_context_hash(context: SubnetContext) -> str:
    """Compute MD5 hash of the context JSON."""
    # Convert context to dict and sort keys for consistent hashing
    context_dict = asdict(context)
    # Remove timestamp-dependent fields
    context_dict.pop('prepared_at', None)
    # Convert to JSON string with sorted keys
    context_json = json.dumps(context_dict, sort_keys=True)
    # Compute MD5 hash
    return hashlib.md5(context_json.encode()).hexdigest()

def save_context(context: SubnetContext, output_file: Optional[str] = None) -> None:
    """Save context to a JSON file."""
    if output_file is None:
        output_file = f"contexts/{context.netuid}.json"
    
    # Compute hash before saving
    context_hash = compute_context_hash(context)
    
    # Add hash to the context
    context_dict = asdict(context)
    context_dict['context_hash'] = context_hash
    
    # Save to file
    with open(output_file, 'w') as f:
        json.dump(context_dict, f, indent=2)
    
    print(f"Context saved to {output_file}")
    print(f"Context hash: {context_hash}")
    
    # Update hash in database
    engine = create_engine(DB_URL)
    with Session(engine) as session:
        meta = session.get(SubnetMeta, context.netuid)
        if meta:
            meta.context_hash = context_hash
            session.commit()
            print(f"Updated context hash in database for subnet {context.netuid}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Prepare context for subnet analysis")
    parser.add_argument("--netuid", type=int, help="NetUID of the subnet to analyze (if not provided, processes all subnets)")
    parser.add_argument("--output", type=str, help="Output file to save context")
    parser.add_argument("--no-save", action="store_true", help="Don't save context to file")
    args = parser.parse_args()
    
    # Get list of netuids to process
    if args.netuid is not None:
        netuids = [args.netuid]
    else:
        netuids = get_all_netuids()
        print(f"Processing {len(netuids)} subnets...")
    
    # Process each netuid
    for netuid in netuids:
        print(f"\nProcessing subnet {netuid}...")
        context = prepare_context(netuid)
        if context:
            print(f"Prepared context ({context.token_count} estimated tokens):")
            print("\n" + "="*80)
            print(format_context(context))
            print("="*80)
            
            if not args.no_save:
                save_context(context, args.output) 