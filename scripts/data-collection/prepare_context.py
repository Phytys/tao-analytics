#!/usr/bin/env python3
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
from collections import Counter

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from models import ScreenerRaw
from config import DB_URL
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from parameter_settings import (
    MAX_WEBSITE_CHARS, MAX_README_CHARS, MAX_SCRAPING_RETRIES, 
    WEBSITE_TIMEOUT, GITHUB_TIMEOUT, WAYBACK_TIMEOUT, MAX_GITHUB_ISSUES,
    TOKEN_ESTIMATION_RATIO, MIN_FALLBACK_CONTENT_LENGTH, MIN_CONTEXT_TOKENS
)

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
        relevant_ngrams: Top keywords from content (simplified)
    """
    netuid: int
    subnet_name: str
    website_url: Optional[str]
    github_repo: Optional[str]
    website_content: Optional[str]
    readme_content: Optional[str]
    token_count: int
    prepared_at: str
    relevant_ngrams: List[str]

def extract_simple_keywords(text: str, max_keywords: int = 5) -> List[str]:
    """Extract simple keywords from text content without NLTK."""
    if not text:
        return []
    
    # Simple word frequency analysis
    words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
    
    # Remove common words
    common_words = {'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had', 'her', 'was', 'one', 'our', 'out', 'day', 'get', 'has', 'him', 'his', 'how', 'man', 'new', 'now', 'old', 'see', 'two', 'way', 'who', 'boy', 'did', 'its', 'let', 'put', 'say', 'she', 'too', 'use', 'with', 'this', 'that', 'have', 'will', 'your', 'from', 'they', 'know', 'want', 'been', 'good', 'much', 'some', 'time', 'very', 'when', 'come', 'here', 'just', 'like', 'long', 'make', 'many', 'over', 'such', 'take', 'than', 'them', 'well', 'were', 'what', 'work', 'year', 'back', 'call', 'come', 'down', 'even', 'find', 'give', 'here', 'last', 'left', 'life', 'make', 'most', 'much', 'name', 'next', 'part', 'same', 'seem', 'take', 'tell', 'than', 'that', 'them', 'they', 'this', 'time', 'very', 'well', 'what', 'when', 'work', 'year'}
    
    words = [word for word in words if word not in common_words]
    
    # Count frequencies
    word_freq = Counter(words)
    
    # Get top words
    top_words = [word for word, freq in word_freq.most_common(max_keywords)]
    
    return top_words

def clean_text(text: str) -> str:
    """Clean text by removing HTML, extra whitespace, etc."""
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Remove multiple spaces
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def get_headers() -> Dict[str, str]:
    """Get headers for requests with proper User-Agent."""
    return {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Cache-Control': 'max-age=0',
    }

def fetch_website_content(url: str, max_retries: int = MAX_SCRAPING_RETRIES) -> Optional[str]:
    """Fetch and clean content from a website using httpx with proper headers and exponential backoff."""
    headers = get_headers()
    
    for attempt in range(max_retries):
        try:
            print(f"Attempt {attempt + 1}/{max_retries} to fetch {url}")
            
            # Use httpx for better async support and modern HTTP features
            with httpx.Client(timeout=WEBSITE_TIMEOUT, follow_redirects=True) as client:
                response = client.get(url, headers=headers)
                
                # Handle successful responses
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Remove unwanted elements
                    for element in soup(['script', 'style', 'nav', 'header', 'footer', 'iframe', 'noscript']):
                        element.decompose()
                    
                    # Enhanced content extraction with priority for headers and important sections
                    text = extract_prioritized_content(soup)
                    text = clean_text(text)
                    
                    if text:
                        if len(text) > MAX_WEBSITE_CHARS:
                            text = text[:MAX_WEBSITE_CHARS] + "..."
                        return text
                    else:
                        print("No text content found in the page")
                        return None
                
                # Handle rate limiting and access denied
                elif response.status_code in [429, 403]:
                    print(f"HTTP {response.status_code} error")
                    if attempt < max_retries - 1:
                        # Exponential backoff: 2, 4, 8 seconds
                        wait_time = 2 ** (attempt + 1)
                        print(f"Waiting {wait_time} seconds before retry...")
                        time.sleep(wait_time)
                    continue
                
                # Handle other HTTP errors
                elif response.status_code >= 400:
                    print(f"HTTP {response.status_code} error")
                    if attempt < max_retries - 1:
                        print("Waiting before retry...")
                        time.sleep(2)
                    continue
                    
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

def extract_prioritized_content(soup: BeautifulSoup) -> str:
    """
    Extract content with priority for headers and important sections.
    
    Priority order:
    1. H1 and H2 headers
    2. Main content sections
    3. Remaining content
    """
    content_parts = []
    
    # 1. Extract H1 and H2 headers first
    headers = soup.find_all(['h1', 'h2'])
    for header in headers:
        header_text = header.get_text(strip=True)
        if header_text:
            content_parts.append(f"HEADER: {header_text}")
            # Also include the next paragraph or section after each header
            next_sibling = header.find_next_sibling(['p', 'div', 'section'])
            if next_sibling:
                sibling_text = next_sibling.get_text(strip=True)
                if sibling_text and len(sibling_text) > 20:  # Only include substantial content
                    content_parts.append(sibling_text)
    
    # 2. Look for main content sections (main, article, section with specific classes)
    main_selectors = [
        'main',
        'article', 
        '[class*="content"]',
        '[class*="main"]',
        '[id*="content"]',
        '[id*="main"]'
    ]
    
    for selector in main_selectors:
        elements = soup.select(selector)
        for element in elements:
            text = element.get_text(strip=True)
            if text and len(text) > 50:  # Only include substantial sections
                content_parts.append(text)
    
    # 3. If we don't have enough content, add remaining text
    if len(' '.join(content_parts)) < MAX_WEBSITE_CHARS // 2:
        remaining_text = soup.get_text(separator=' ', strip=True)
        content_parts.append(remaining_text)
    
    # Combine all parts
    combined_text = ' '.join(content_parts)
    
    # Clean up excessive whitespace
    combined_text = re.sub(r'\s+', ' ', combined_text).strip()
    
    return combined_text

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
                    response = requests.get(raw_url, timeout=GITHUB_TIMEOUT)
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
    return len(text) // TOKEN_ESTIMATION_RATIO

def get_all_netuids() -> List[int]:
    """Get list of all netuids from the database."""
    engine = create_engine(DB_URL)
    with Session(engine) as session:
        return [row.netuid for row in session.query(ScreenerRaw).all()]

def fetch_github_issues(owner: str, repo: str, max_issues: int = MAX_GITHUB_ISSUES) -> Optional[str]:
    """Fetch recent GitHub issues as fallback context."""
    try:
        # Use GitHub API to get recent issues
        api_url = f"https://api.github.com/repos/{owner}/{repo}/issues?state=open&per_page={max_issues}"
        response = requests.get(api_url, timeout=GITHUB_TIMEOUT)
        
        if response.status_code == 200:
            issues = response.json()
            if issues:
                # Extract titles and bodies from issues
                issue_texts = []
                for issue in issues:
                    title = issue.get('title', '')
                    body = issue.get('body', '')
                    if title or body:
                        issue_texts.append(f"ISSUE: {title}\n{body}")
                
                if issue_texts:
                    combined_text = "\n\n".join(issue_texts)
                    return clean_text(combined_text[:MAX_README_CHARS])
    except Exception as e:
        print(f"Error fetching GitHub issues: {e}")
    return None

def fetch_wayback_snapshot(url: str) -> Optional[str]:
    """Try to fetch content from Wayback Machine as fallback."""
    try:
        # Try to get the latest snapshot from Wayback Machine
        wayback_url = f"https://web.archive.org/web/{url}"
        response = requests.get(wayback_url, timeout=WAYBACK_TIMEOUT, headers=get_headers())
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove unwanted elements
            for element in soup(['script', 'style', 'nav', 'header', 'footer', 'iframe', 'noscript']):
                element.decompose()
            
            text = soup.get_text(separator=' ', strip=True)
            text = clean_text(text)
            
            if text and len(text) > MIN_FALLBACK_CONTENT_LENGTH:  # Only return if we got meaningful content
                return text[:MAX_WEBSITE_CHARS]
    except Exception as e:
        print(f"Error fetching Wayback snapshot: {e}")
    return None

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
            prepared_at=datetime.now().isoformat(),
            relevant_ngrams=[]
        )
        
        # Calculate total tokens
        total_tokens = 0
        if website_content:
            total_tokens += count_tokens(website_content)
        if readme_content:
            total_tokens += count_tokens(readme_content)
        context.token_count = total_tokens
        
        # Extract relevant n-grams
        if readme_content:
            context.relevant_ngrams = extract_simple_keywords(readme_content)
        
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
    
    # Add relevant n-grams hint
    if context.relevant_ngrams:
        parts.append(f"\nMOST_RELEVANT_NGRAMS: {', '.join(context.relevant_ngrams)}")
    
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

def prepare_context_with_fallback(netuid: int) -> Optional[SubnetContext]:
    """Prepare context with fallback strategies for zero-token cases."""
    context = prepare_context(netuid)
    
    # If we got good context, return it
    if context and context.token_count >= MIN_CONTEXT_TOKENS:
        return context
    
    # If we have zero or very low context, try fallbacks
    if context and context.token_count < MIN_CONTEXT_TOKENS:
        print(f"⚠️  Low context for subnet {netuid} ({context.token_count} tokens), trying fallbacks...")
        
        # Try GitHub issues if we have a repo
        if context.github_repo and "github.com" in context.github_repo:
            parts = context.github_repo.rstrip("/").split("/")
            if len(parts) >= 5:
                owner, repo = parts[-2], parts[-1]
                issues_content = fetch_github_issues(owner, repo)
                if issues_content:
                    print(f"✅ Found {len(issues_content)} characters from GitHub issues")
                    context.readme_content = issues_content
                    context.token_count = count_tokens(issues_content)
                    context.relevant_ngrams = extract_simple_keywords(issues_content)
                    return context
        
        # Try Wayback Machine if we have a website
        if context.website_url:
            wayback_content = fetch_wayback_snapshot(context.website_url)
            if wayback_content:
                print(f"✅ Found {len(wayback_content)} characters from Wayback Machine")
                context.website_content = wayback_content
                context.token_count = count_tokens(wayback_content)
                context.relevant_ngrams = extract_simple_keywords(wayback_content)
                return context
    
    # If all fallbacks failed, return None (will be skipped)
    if context and context.token_count < MIN_CONTEXT_TOKENS:
        print(f"❌ All fallbacks failed for subnet {netuid}, skipping enrichment")
        return None
    
    return context

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
        context = prepare_context_with_fallback(netuid)
        if context:
            print(f"Prepared context ({context.token_count} estimated tokens):")
            print("\n" + "="*80)
            print(format_context(context))
            print("="*80)
            
            if not args.no_save:
                save_context(context, args.output) 