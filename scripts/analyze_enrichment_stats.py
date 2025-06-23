#!/usr/bin/env python3
"""
Analyze enrichment statistics for the TAO Analytics database.
Enhanced with new primary categories, secondary tags, and privacy/security analytics.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from config import DB_URL, PRIMARY_CATEGORIES
import json
from collections import Counter

def get_enrichment_stats():
    """Get comprehensive enrichment statistics."""
    engine = create_engine(DB_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Get all subnet metadata
    query = text("""
        SELECT 
            netuid,
            subnet_name,
            tagline,
            what_it_does,
            primary_category,
            secondary_tags,
            confidence,
            context_tokens,
            privacy_security_flag,
            provenance,
            last_enriched_at
        FROM subnet_meta 
        WHERE primary_category IS NOT NULL
        ORDER BY netuid
    """)
    
    result = session.execute(query)
    rows = result.fetchall()
    session.close()
    
    return pd.DataFrame(rows, columns=[
        'netuid', 'subnet_name', 'tagline', 'what_it_does', 
        'primary_category', 'secondary_tags', 'confidence', 
        'context_tokens', 'privacy_security_flag', 'provenance', 'last_enriched_at'
    ])

def analyze_primary_categories(df):
    """Analyze distribution of primary categories."""
    print("\n" + "="*60)
    print("📊 PRIMARY CATEGORY DISTRIBUTION")
    print("="*60)
    
    category_counts = df['primary_category'].value_counts()
    total_subnets = len(df)
    
    print(f"Total subnets analyzed: {total_subnets}")
    print("\nCategory breakdown:")
    print("-" * 40)
    
    for category in PRIMARY_CATEGORIES:
        count = category_counts.get(category, 0)
        percentage = (count / total_subnets) * 100
        print(f"{category:<30} {count:>3} ({percentage:>5.1f}%)")
    
    # Show any categories not in our canonical list
    unexpected_categories = set(category_counts.index) - set(PRIMARY_CATEGORIES)
    if unexpected_categories:
        print(f"\n⚠️  Unexpected categories found: {unexpected_categories}")
    
    # Special analysis for uncategorized subnets
    uncategorized = df[df['primary_category'] == 'Uncategorized']
    if len(uncategorized) > 0:
        print(f"\n🔴 UNCategorized subnets: {len(uncategorized)} ({len(uncategorized)/total_subnets*100:.1f}%)")
        print("These subnets failed category validation and need manual review:")
        for _, row in uncategorized.iterrows():
            print(f"  - Subnet {row['netuid']}: {row['subnet_name']} (confidence: {row['confidence']}%)")

def analyze_secondary_tags(df):
    """Analyze secondary tags usage."""
    print("\n" + "="*60)
    print("🏷️  SECONDARY TAGS ANALYSIS")
    print("="*60)
    
    all_tags = []
    for tags_str in df['secondary_tags'].dropna():
        if tags_str:
            tags = [tag.strip() for tag in tags_str.split(',') if tag.strip()]
            all_tags.extend(tags)
    
    if not all_tags:
        print("No secondary tags found.")
        return
    
    tag_counts = Counter(all_tags)
    total_subnets = len(df)
    
    print(f"Total tags used: {len(all_tags)}")
    print(f"Unique tags: {len(tag_counts)}")
    print(f"Average tags per subnet: {len(all_tags)/total_subnets:.1f}")
    
    print("\nTop 20 most common tags:")
    print("-" * 40)
    for tag, count in tag_counts.most_common(20):
        percentage = (count / total_subnets) * 100
        print(f"{tag:<25} {count:>3} ({percentage:>5.1f}%)")

def analyze_privacy_security(df):
    """Analyze privacy and security focused subnets."""
    print("\n" + "="*60)
    print("🔒 PRIVACY & SECURITY ANALYSIS")
    print("="*60)
    
    privacy_subnets = df[df['privacy_security_flag'] == True]
    total_subnets = len(df)
    
    print(f"Privacy/security focused subnets: {len(privacy_subnets)} ({len(privacy_subnets)/total_subnets*100:.1f}%)")
    
    if len(privacy_subnets) > 0:
        print("\nPrivacy/security subnets by category:")
        print("-" * 40)
        privacy_by_category = privacy_subnets['primary_category'].value_counts()
        for category, count in privacy_by_category.items():
            print(f"{category:<30} {count:>3}")
        
        print(f"\nPrivacy/security subnets (NetUIDs): {sorted(privacy_subnets['netuid'].tolist())}")

def analyze_confidence_by_category(df):
    """Analyze confidence scores by primary category."""
    print("\n" + "="*60)
    print("📈 CONFIDENCE SCORES BY CATEGORY")
    print("="*60)
    
    confidence_stats = df.groupby('primary_category')['confidence'].agg([
        'count', 'mean', 'std', 'min', 'max'
    ]).round(1)
    
    print(confidence_stats)
    
    # High confidence subnets (≥90)
    high_conf = df[df['confidence'] >= 90]
    print(f"\nHigh confidence subnets (≥90): {len(high_conf)} ({len(high_conf)/len(df)*100:.1f}%)")
    
    # Low confidence subnets (≤50)
    low_conf = df[df['confidence'] <= 50]
    print(f"Low confidence subnets (≤50): {len(low_conf)} ({len(low_conf)/len(df)*100:.1f}%)")

def analyze_context_correlation(df):
    """Analyze correlation between context tokens and confidence."""
    print("\n" + "="*60)
    print("🔗 CONTEXT TOKENS vs CONFIDENCE CORRELATION")
    print("="*60)
    
    # Remove rows with missing data
    clean_df = df.dropna(subset=['context_tokens', 'confidence'])
    
    if len(clean_df) == 0:
        print("No data available for correlation analysis.")
        return
    
    correlation = clean_df['context_tokens'].corr(clean_df['confidence'])
    print(f"Correlation coefficient: {correlation:.3f}")
    
    # Context token statistics
    print(f"\nContext token statistics:")
    print(f"  Mean: {clean_df['context_tokens'].mean():.0f}")
    print(f"  Median: {clean_df['context_tokens'].median():.0f}")
    print(f"  Std: {clean_df['context_tokens'].std():.0f}")
    print(f"  Min: {clean_df['context_tokens'].min()}")
    print(f"  Max: {clean_df['context_tokens'].max()}")
    
    # Subnets with no context
    no_context = clean_df[clean_df['context_tokens'] == 0]
    print(f"\nSubnets with no context: {len(no_context)} ({len(no_context)/len(clean_df)*100:.1f}%)")

def analyze_provenance(df):
    """Analyze provenance patterns."""
    print("\n" + "="*60)
    print("📋 PROVENANCE ANALYSIS")
    print("="*60)
    
    provenance_counts = {'context': 0, 'model': 0, 'both': 0, 'unknown': 0}
    
    for provenance_str in df['provenance'].dropna():
        try:
            provenance = json.loads(provenance_str)
            for field, source in provenance.items():
                if source in provenance_counts:
                    provenance_counts[source] += 1
        except:
            provenance_counts['unknown'] += 1
    
    total_fields = sum(provenance_counts.values())
    if total_fields > 0:
        print("Provenance breakdown:")
        for source, count in provenance_counts.items():
            percentage = (count / total_fields) * 100
            print(f"  {source.capitalize()}: {count} ({percentage:.1f}%)")

def main():
    print("🔍 Loading enrichment data...")
    df = get_enrichment_stats()
    
    if df.empty:
        print("❌ No enrichment data found!")
        return
    
    print(f"✅ Loaded {len(df)} enriched subnets")
    
    # Run all analyses
    analyze_primary_categories(df)
    analyze_secondary_tags(df)
    analyze_privacy_security(df)
    analyze_confidence_by_category(df)
    analyze_context_correlation(df)
    analyze_provenance(df)
    
    print("\n" + "="*60)
    print("🎉 ANALYSIS COMPLETE")
    print("="*60)

if __name__ == "__main__":
    main() 