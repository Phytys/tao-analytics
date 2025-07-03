#!/usr/bin/env python3
"""
Enrich subnet data using OpenAI GPT-4 with improved classification system.
Features: TF-IDF n-gram hints, granular categories, provenance tracking, and confidence scoring.

USAGE EXAMPLES:
    # Enrich a single subnet
    python enrich_with_openai.py --netuid 64
    
    # Force re-enrichment even if context hasn't changed
    python enrich_with_openai.py --netuid 64 --force
    
    # Use existing context file instead of fetching fresh data
    python enrich_with_openai.py --netuid 64 --context-file contexts/64.json
    
    # Process without saving to database (for testing)
    python enrich_with_openai.py --netuid 64 --no-save
    
    # Process all subnets in database
    python enrich_with_openai.py

OPTIONS:
    --netuid NETUID              Specific NetUID to process
    --context-file FILE          Use existing context file instead of fetching
    --force                      Force enrichment even if context hasn't changed
    --no-save                    Don't save results to database (for testing)

FEATURES:
    - Granular primary categories (Serverless-Compute, Security & Auditing, etc.)
    - TF-IDF n-gram hints for better LLM understanding
    - Provenance tracking (context vs model knowledge)
    - Confidence scoring with context token correlation
    - Tag normalization and deduplication
    - Category re-ask fallback for better accuracy
"""

import sys
from pathlib import Path
import json
from datetime import datetime
from typing import Optional, Dict, Any, List
from openai import OpenAI
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
import re

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from models import ScreenerRaw, SubnetMeta
from config import DB_URL, OPENAI_KEY, OPENAI_MODEL, CATEGORY_CHOICES, ALLOW_MODEL_KNOWLEDGE, MODEL_ONLY_MAX_CONF, PRIMARY_CATEGORIES, normalize_tags
from prepare_context import prepare_context_with_fallback, format_context, SubnetContext, get_all_netuids, compute_context_hash
from parameter_settings import (
    TAGLINE_MAX_WORDS, WHAT_IT_DOES_MAX_WORDS, PRIMARY_USE_CASE_MAX_WORDS, KEY_TECHNICAL_FEATURES_MAX_WORDS,
    MAX_SECONDARY_TAGS, OPENAI_MAX_TOKENS, OPENAI_TIMEOUT, OPENAI_TEMPERATURE,
    PROVENANCE_PENALTY, THIN_CONTEXT_PENALTY, THIN_CONTEXT_THRESHOLD, LOW_CONFIDENCE_THRESHOLD,
    FALLBACK_TAGS, DEFAULT_CATEGORY, ENABLE_CATEGORY_REASK, CATEGORY_REASK_MAX_TOKENS,
    MIN_CONTEXT_TOKENS
)

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_KEY)

def build_prompt(context: SubnetContext, mode: str) -> str:
    """Build the prompt based on context availability and mode."""
    
    # Dynamically generate the category list for the prompt
    category_list_str = "\n".join([f"  {i+1}) {cat}" for i, cat in enumerate(PRIMARY_CATEGORIES)])
    
    if mode == "model-only":
        mode_instruction = """
IMPORTANT: You have minimal context about this subnet. Only fill fields if you are 80%+ confident 
from your training data. Otherwise leave them empty and set confidence low.
"""
    else:
        mode_instruction = """
Use the provided context as your primary source. You may supplement with your knowledge 
if you're confident, but always prefer context over prior knowledge.
"""
    
    system_prompt = f"""
You are a researcher creating a structured JSON profile for Bittensor subnets.
Respond with *only* valid JSON following the schema given below.

If a value is not in the supplied context but you *know it confidently* from
your own pre-training, you MAY use it, but set `\"provenance\":\"model\"` and
lower `\"confidence\"` accordingly. If unsure, leave the field empty and
set confidence to a low number.

Choose ONE \"primary_category\" from:
{category_list_str}

Prioritize a category that reflects *what utility end-users buy* 
(e.g. \"Serverless-Compute\" for platforms that deploy/run models).

Schema (all strings unless noted):
{{
  "tagline":                  "... ≤{TAGLINE_MAX_WORDS} words ...",
  "what_it_does":             "... ≤{WHAT_IT_DOES_MAX_WORDS} words ...",
  "primary_use_case":         "... ≤{PRIMARY_USE_CASE_MAX_WORDS} words ...",
  "key_technical_features":   "... ≤{KEY_TECHNICAL_FEATURES_MAX_WORDS} words ...",
  "primary_category":         "<exact name from list above>",
  "category_suggestion":      "<suggest new category name if existing ones don't fit well, otherwise leave empty>",
  "secondary_tags":           ["max {MAX_SECONDARY_TAGS} kebab-case tags"],
  "confidence":               0-100,
  "privacy_security_flag":    true|false,   // true if focus is privacy, security, or auditing
  "provenance":               {{          // track where each field came from
       "tagline": "context|model|both|unknown",
       "what_it_does": "...",
       "primary_use_case": "...",
       "key_technical_features": "...",
       "primary_category": "...",
       "category_suggestion": "...",
       "secondary_tags": "...",
       "privacy_security_flag": "..."
  }}
}}

Field Guidelines:
- tagline: Concise, memorable description (e.g., "Decentralized AI inference network")
- what_it_does: Comprehensive, investor-friendly explanation in simple terms. Explain what the subnet does, why it matters, how it works, and what value it provides to users. Use clear language that non-technical people can understand. Include business context and real-world applications.
- primary_use_case: Specific use case or application (e.g., "AI model deployment and inference")
- key_technical_features: Technical capabilities and innovations (e.g., "Distributed training, ZK proofs, consensus mechanisms")
- primary_category: Choose the best match from the list above. If none fit well, suggest a new category name in category_suggestion.
- category_suggestion: If the existing categories don't capture this subnet's focus well, suggest a new category name (e.g., "AI-Governance", "Cross-Chain-Bridges"). Leave empty if existing categories work.
- secondary_tags: Start with most unique features (e.g., serverless-ai, zk-proof, deepfake-detection)

{mode_instruction}
"""
    
    formatted_context = format_context(context)
    return f"{system_prompt}\n\nCONTEXT START\n{formatted_context}\nCONTEXT END"

def load_context(context_file: str) -> Optional[SubnetContext]:
    """Load context from a JSON file."""
    try:
        with open(context_file, 'r') as f:
            data = json.load(f)
            return SubnetContext(**data)
    except Exception as e:
        print(f"Error loading context file: {e}")
        return None

def re_ask_category(context: SubnetContext, initial_category: str) -> Optional[str]:
    """Re-ask for category if model chose one despite having good context."""
    if context.token_count < MIN_CONTEXT_TOKENS:
        return initial_category  # Don't re-ask if context is poor
    
    category_prompt = f"""You previously categorized this subnet as "{initial_category}".

Given ONLY the context below, choose the most appropriate primary category from:
{chr(10).join(f"{i+1}) {cat}" for i, cat in enumerate(PRIMARY_CATEGORIES))}

Return ONLY the exact category name from the list above.

CONTEXT:
{format_context(context)}"""

    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that categorizes Bittensor subnets."},
                {"role": "user", "content": category_prompt}
            ],
            temperature=0.1,
            max_tokens=CATEGORY_REASK_MAX_TOKENS
        )
        
        content = response.choices[0].message.content.strip()
        
        # Find exact match in our categories
        for category in PRIMARY_CATEGORIES:
            if category.lower() == content.lower():
                print(f"Category re-ask: '{initial_category}' -> '{category}'")
                return category
        
        print(f"Category re-ask failed, keeping: '{initial_category}'")
        return initial_category
        
    except Exception as e:
        print(f"Category re-ask error: {e}")
        return initial_category

def enrich_with_openai(context: SubnetContext, force_model_only: bool = False) -> Optional[Dict[str, Any]]:
    """Call OpenAI API to analyze the subnet."""
    
    # Pre-flight guard: skip if context is too thin, unless forced
    if not force_model_only and context.token_count < MIN_CONTEXT_TOKENS:
        print(f"⚠️  WARNING: Subnet {context.netuid} has insufficient context ({context.token_count} tokens < {MIN_CONTEXT_TOKENS})")
        print("Skipping LLM call to avoid wasting money on poor results")
        return None
    
    try:
        # Determine mode based on context availability or forced model-only
        mode = "model-only" if force_model_only or context.token_count < MIN_CONTEXT_TOKENS else "mixed"
        print(f"Enrichment mode: {mode} (context tokens: {context.token_count})")
        
        # Build prompt based on mode
        prompt = build_prompt(context, mode)
        
        print("\nAttempting OpenAI API call...")
        print(f"Using model: {OPENAI_MODEL}")
        print(f"API Key present: {'Yes' if OPENAI_KEY else 'No'}")
        
        # Call OpenAI API with timeout
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that analyzes Bittensor subnet projects."},
                {"role": "user", "content": prompt}
            ],
            temperature=OPENAI_TEMPERATURE,
            max_tokens=OPENAI_MAX_TOKENS,
            timeout=OPENAI_TIMEOUT
        )
        
        content = response.choices[0].message.content.strip()
        
        # Parse JSON response
        try:
            # Try to extract JSON block if present
            json_str = content
            # Remove code block markers if present
            if '```' in json_str:
                json_str = re.sub(r'```[a-zA-Z]*', '', json_str)
                json_str = json_str.replace('```', '')
            json_str = json_str.strip()
            # Try to find the first { ... } block
            match = re.search(r'\{[\s\S]*\}', json_str)
            if match:
                json_str = match.group(0)
            
            enrichment = json.loads(json_str)
        except Exception as e:
            print(f"Error parsing LLM response as JSON: {e}")
            print(f"Raw response: {content}")
            return None
        
        return enrichment
        
    except Exception as e:
        print(f"OpenAI API error: {e}")
        return None

def save_enrichment(netuid: int, enrichment: Dict[str, Any], context: SubnetContext) -> None:
    """Save enrichment results to database."""
    engine = create_engine(DB_URL)
    with Session(engine) as session:
        # Get or create enriched record
        enriched = session.get(SubnetMeta, netuid)
        if not enriched:
            enriched = SubnetMeta(netuid=netuid)
            session.add(enriched)
        
        # Update fields
        enriched.tagline = enrichment.get('tagline')
        enriched.what_it_does = enrichment.get('what_it_does')
        enriched.primary_use_case = enrichment.get('primary_use_case')
        enriched.key_technical_features = enrichment.get('key_technical_features')
        enriched.primary_category = enrichment.get('primary_category')
        enriched.category_suggestion = enrichment.get('category_suggestion')
        enriched.secondary_tags = ','.join(enrichment.get('secondary_tags', []))
        enriched.confidence = enrichment.get('confidence')
        enriched.privacy_security_flag = enrichment.get('privacy_security_flag')
        enriched.last_enriched_at = datetime.now()
        
        # Save context hash
        enriched.context_hash = compute_context_hash(context)
        
        # Save new fields
        enriched.context_tokens = context.token_count  # Use actual context token count
        enriched.provenance = json.dumps(enrichment.get('provenance', {}))
        
        session.commit()
        print(f"Enrichment saved to database for subnet {netuid}")
        print(f"Context tokens: {enriched.context_tokens}")
        print(f"Provenance: {enriched.provenance}")
        
        # Sync category to MetricsSnap table for GPT insights
        try:
            from models import MetricsSnap
            from sqlalchemy import func
            
            # Get the latest metrics snapshot for this subnet
            latest_metrics = session.query(MetricsSnap).filter_by(netuid=netuid)\
                .order_by(MetricsSnap.timestamp.desc()).first()
            
            if latest_metrics and enriched.primary_category:
                if latest_metrics.category != enriched.primary_category:
                    print(f"Syncing category: '{latest_metrics.category}' -> '{enriched.primary_category}'")
                    latest_metrics.category = enriched.primary_category
                    session.commit()
                    print(f"✅ Category synced to MetricsSnap for subnet {netuid}")
                else:
                    print(f"Category already in sync for subnet {netuid}")
            else:
                print(f"No metrics data found for subnet {netuid}, category sync skipped")
                
        except Exception as e:
            print(f"⚠️  Error syncing category for subnet {netuid}: {e}")
            print("GPT insights may use outdated category data")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Enrich subnet data using OpenAI")
    parser.add_argument("--netuid", type=int, help="NetUID of the subnet to analyze (if not provided, processes all subnets)")
    parser.add_argument("--context-file", type=str, help="Use existing context file")
    parser.add_argument("--no-save", action="store_true", help="Don't save results to database")
    parser.add_argument("--force", action="store_true", help="Force enrichment even if context hasn't changed")
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
        
        # Get context
        if args.context_file:
            context = load_context(args.context_file)
            if not context:
                print(f"Failed to load context from {args.context_file}")
                continue
        else:
            context = prepare_context_with_fallback(netuid)
            if not context:
                print(f"Failed to prepare context for subnet {netuid}")
                continue
        
        # Check if context has changed
        engine = create_engine(DB_URL)
        with Session(engine) as session:
            meta = session.get(SubnetMeta, netuid)
            current_hash = compute_context_hash(context)
            print(f"Computed context hash: {current_hash}")
            if meta and meta.context_hash:
                print(f"Stored context hash:   {meta.context_hash}")
                if current_hash == meta.context_hash and not args.force:
                    print(f"Context unchanged for subnet {netuid}, skipping enrichment")
                    continue
                print(f"Context changed for subnet {netuid}, proceeding with enrichment")
            else:
                print(f"No stored hash for subnet {netuid}, proceeding with enrichment")
        
        # Print only the formatted context (exactly what is sent to OpenAI)
        formatted_context = format_context(context)
        print("\n--- CONTEXT SENT TO OPENAI ---")
        print(formatted_context)
        print("--- END CONTEXT ---\n")
        
        # Enrich with OpenAI
        enrichment = enrich_with_openai(context)
        if enrichment:
            print("\nEnrichment Results:")
            print(json.dumps(enrichment, indent=2))
            
            if not args.no_save:
                save_enrichment(netuid, enrichment, context)

if __name__ == "__main__":
    main() 