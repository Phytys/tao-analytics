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
            primary_use_case,
            key_technical_features,
            primary_category,
            secondary_tags,
            confidence,
            context_tokens,
            privacy_security_flag,
            provenance,
            last_enriched_at,
            category_suggestion
        FROM subnet_meta 
        WHERE primary_category IS NOT NULL
        ORDER BY netuid
    """)
    
    result = session.execute(query)
    rows = result.fetchall()
    session.close()
    
    return pd.DataFrame(rows, columns=[
        'netuid', 'subnet_name', 'tagline', 'what_it_does', 
        'primary_use_case', 'key_technical_features',
        'primary_category', 'secondary_tags', 'confidence', 
        'context_tokens', 'privacy_security_flag', 'provenance', 'last_enriched_at',
        'category_suggestion'
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

def analyze_context_quality(df):
    """Analyze context quality and distribution."""
    print("\n" + "="*60)
    print("📚 CONTEXT QUALITY ANALYSIS")
    print("="*60)
    
    total_subnets = len(df)
    
    # Context token distribution
    no_context = len(df[df['context_tokens'] == 0])
    low_context = len(df[df['context_tokens'].between(1, 500)])
    medium_context = len(df[df['context_tokens'].between(501, 1000)])
    high_context = len(df[df['context_tokens'] > 1000])
    
    print(f"Context token distribution:")
    print(f"  No context (0 tokens):     {no_context:>3} ({no_context/total_subnets*100:>5.1f}%)")
    print(f"  Low context (1-500):       {low_context:>3} ({low_context/total_subnets*100:>5.1f}%)")
    print(f"  Medium context (501-1000): {medium_context:>3} ({medium_context/total_subnets*100:>5.1f}%)")
    print(f"  High context (>1000):      {high_context:>3} ({high_context/total_subnets*100:>5.1f}%)")
    
    # Context quality by category
    print(f"\nContext quality by category (avg tokens):")
    context_by_category = df.groupby('primary_category')['context_tokens'].agg(['mean', 'count']).round(0)
    context_by_category = context_by_category.sort_values('mean', ascending=False)
    
    for category, row in context_by_category.iterrows():
        print(f"  {category:<30} {row['mean']:>6.0f} tokens ({row['count']:>2} subnets)")
    
    # Top 10 subnets by context tokens
    print(f"\nTop 10 subnets by context tokens:")
    top_context = df.nlargest(10, 'context_tokens')[['netuid', 'subnet_name', 'context_tokens', 'primary_category']]
    for _, row in top_context.iterrows():
        print(f"  Subnet {row['netuid']:>3}: {row['subnet_name']:<20} {row['context_tokens']:>4} tokens ({row['primary_category']})")

def analyze_category_suggestions(df):
    """Analyze category suggestions from LLM."""
    print("\n" + "="*60)
    print("💡 CATEGORY SUGGESTIONS ANALYSIS")
    print("="*60)
    
    # Get subnets with category suggestions
    suggestions = df[df['category_suggestion'].notna() & (df['category_suggestion'] != '')]
    
    if len(suggestions) == 0:
        print("No category suggestions found.")
        return
    
    print(f"Subnets with category suggestions: {len(suggestions)} ({len(suggestions)/len(df)*100:.1f}%)")
    
    print(f"\nCategory suggestions:")
    for _, row in suggestions.iterrows():
        print(f"  Subnet {row['netuid']:>3}: {row['subnet_name']:<20} → {row['category_suggestion']}")
    
    # Analyze suggestion patterns
    suggestion_counts = suggestions['category_suggestion'].value_counts()
    print(f"\nMost common suggestions:")
    for suggestion, count in suggestion_counts.head(5).items():
        print(f"  {suggestion}: {count} subnets")

def analyze_enrichment_success_metrics(df):
    """Analyze overall enrichment success metrics."""
    print("\n" + "="*60)
    print("🎯 ENRICHMENT SUCCESS METRICS")
    print("="*60)
    
    total_subnets = len(df)
    
    # Completeness metrics
    complete_profiles = df[
        df['tagline'].notna() & 
        df['what_it_does'].notna() & 
        df['primary_use_case'].notna() & 
        df['key_technical_features'].notna() & 
        df['primary_category'].notna()
    ]
    
    print(f"Profile completeness:")
    print(f"  Complete profiles: {len(complete_profiles)} ({len(complete_profiles)/total_subnets*100:.1f}%)")
    print(f"  Partial profiles:  {total_subnets - len(complete_profiles)} ({(total_subnets - len(complete_profiles))/total_subnets*100:.1f}%)")
    
    # Field completion rates
    fields = ['tagline', 'what_it_does', 'primary_use_case', 'key_technical_features', 'primary_category', 'secondary_tags']
    print(f"\nField completion rates:")
    for field in fields:
        completion_rate = (df[field].notna().sum() / total_subnets) * 100
        print(f"  {field:<20}: {completion_rate:>5.1f}%")
    
    # Quality metrics
    high_confidence = len(df[df['confidence'] >= 90])
    context_based = len(df[df['context_tokens'] > 100])
    
    print(f"\nQuality metrics:")
    print(f"  High confidence (≥90): {high_confidence} ({high_confidence/total_subnets*100:.1f}%)")
    print(f"  Context-based:         {context_based} ({context_based/total_subnets*100:.1f}%)")
    print(f"  Average confidence:    {df['confidence'].mean():.1f}%")
    print(f"  Average context tokens: {df['context_tokens'].mean():.0f}")

def analyze_word_count_distribution(df):
    """Analyze word count distribution for text fields."""
    print("\n" + "="*60)
    print("📝 WORD COUNT ANALYSIS")
    print("="*60)
    
    def count_words(text):
        if pd.isna(text):
            return 0
        return len(str(text).split())
    
    # Analyze word counts for key text fields
    fields = ['tagline', 'what_it_does', 'primary_use_case', 'key_technical_features']
    
    for field in fields:
        word_counts = df[field].apply(count_words)
        print(f"\n{field.replace('_', ' ').title()}:")
        print(f"  Mean: {word_counts.mean():.1f} words")
        print(f"  Median: {word_counts.median():.1f} words")
        print(f"  Min: {word_counts.min()} words")
        print(f"  Max: {word_counts.max()} words")
        
        # Show examples of longest descriptions
        longest_idx = word_counts.idxmax()
        if not pd.isna(longest_idx):
            longest_text = df.loc[longest_idx, field]
            print(f"  Longest (Subnet {df.loc[longest_idx, 'netuid']}): {longest_text[:100]}...")

def analyze_enrichment_timeline(df):
    """Analyze enrichment timeline and patterns."""
    print("\n" + "="*60)
    print("⏰ ENRICHMENT TIMELINE ANALYSIS")
    print("="*60)
    
    if 'last_enriched_at' not in df.columns or df['last_enriched_at'].isna().all():
        print("No enrichment timestamps available.")
        return
    
    # Convert to datetime
    df['enrichment_date'] = pd.to_datetime(df['last_enriched_at'])
    
    # Timeline analysis
    earliest = df['enrichment_date'].min()
    latest = df['enrichment_date'].max()
    duration = latest - earliest
    
    print(f"Enrichment timeline:")
    print(f"  Earliest: {earliest}")
    print(f"  Latest:   {latest}")
    print(f"  Duration: {duration}")
    
    # Enrichments per day
    daily_counts = df.groupby(df['enrichment_date'].dt.date).size()
    print(f"\nEnrichments per day:")
    print(f"  Average: {daily_counts.mean():.1f} per day")
    print(f"  Max:     {daily_counts.max()} per day")
    print(f"  Min:     {daily_counts.min()} per day")
    
    # Show daily breakdown
    print(f"\nDaily breakdown:")
    for date, count in daily_counts.items():
        print(f"  {date}: {count} enrichments")

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
    analyze_context_quality(df)
    analyze_category_suggestions(df)
    analyze_enrichment_success_metrics(df)
    analyze_word_count_distribution(df)
    analyze_enrichment_timeline(df)
    
    print("\n" + "="*60)
    print("🎉 ANALYSIS COMPLETE")
    print("="*60)

if __name__ == "__main__":
    main() 