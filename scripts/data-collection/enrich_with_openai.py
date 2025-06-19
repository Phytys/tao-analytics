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
from config import DB_URL, OPENAI_KEY, OPENAI_MODEL, CATEGORY_CHOICES, ALLOW_MODEL_KNOWLEDGE, MIN_CONTEXT_TOKENS, MODEL_ONLY_MAX_CONF, PRIMARY_CATEGORIES, normalize_tags
from prepare_context import prepare_context, format_context, SubnetContext, get_all_netuids, compute_context_hash

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
  \"tagline\":                  \"... ≤12 words ...\",
  \"what_it_does\":             \"... ≤40 words ...\",
  \"primary_category\":         \"<exact name from list above>\",
  \"secondary_tags\":           [\"max 6 kebab-case tags\"],
  \"confidence\":               0-100,
  \"privacy_security_flag\":    true|false,   // true if focus is privacy, security, or auditing
  \"provenance\":               {{          // track where each field came from
       \"tagline\": \"context|model|both|unknown\",
       \"what_it_does\": \"...\",
       \"primary_category\": \"...\",
       \"secondary_tags\": \"...\",
       \"privacy_security_flag\": \"...\"
  }}
}}

Generate secondary_tags beginning with the most unique features 
(e.g. serverless-ai, zk-proof, deepfake-detection, solidity-audit).

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
            max_tokens=50
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

def enrich_with_openai(context: SubnetContext) -> Optional[Dict[str, Any]]:
    """Call OpenAI API to analyze the subnet."""
    
    # Pre-flight guard: skip if context is too thin
    if context.token_count < MIN_CONTEXT_TOKENS:
        print(f"⚠️  WARNING: Subnet {context.netuid} has insufficient context ({context.token_count} tokens < {MIN_CONTEXT_TOKENS})")
        print("Skipping LLM call to avoid wasting money on poor results")
        return None
    
    try:
        # Determine mode based on context availability
        mode = "model-only" if context.token_count < MIN_CONTEXT_TOKENS else "mixed"
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
            temperature=0.1,  # Low temperature for more consistent results
            max_tokens=1000,
            timeout=90  # Add timeout to prevent hanging
        )
        
        # Get the content and clean it
        content = response.choices[0].message.content
        print("\n--- RAW LLM RESPONSE ---")
        print(content)
        print("--- END RAW LLM RESPONSE ---\n")
        
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
        
        # Parse response
        try:
            result = json.loads(json_str)
        except Exception as e:
            print("[ERROR] Failed to parse LLM response as JSON!")
            print(f"Raw content was:\n{content}")
            print(f"Extracted JSON string was:\n{json_str}")
            print(f"Exception: {e}")
            return None
        
        # Validate and normalize primary category
        raw_category = result.get("primary_category", "").strip()
        # Case-insensitive match to our canonical list
        canonical_category = next(
            (c for c in PRIMARY_CATEGORIES if c.lower() == raw_category.lower()), 
            "Dev-Tooling"  # Default fallback
        )
        result["primary_category"] = canonical_category
        print(f"Primary category normalized: '{raw_category}' -> '{canonical_category}'")
        
        # Category re-ask fallback if model chose category despite good context
        provenance = result.get("provenance", {})
        if (provenance.get("primary_category") == "model" and 
            context.token_count >= MIN_CONTEXT_TOKENS and
            canonical_category == "Dev-Tooling"):  # Common fallback
            
            print("⚠️  WARNING: Category from model despite good context (tokens: {context.token_count})")
            print("Re-asking for category due to model choice with good context...")
            better_category = re_ask_category(context, canonical_category)
            if better_category != canonical_category:
                result["primary_category"] = better_category
                provenance["primary_category"] = "context"
                result["provenance"] = provenance
        
        # Normalize secondary tags
        raw_tags = result.get("secondary_tags", [])
        normalized_tags = normalize_tags(raw_tags)
        
        # Pad tags to ensure exactly 6 tags
        while len(normalized_tags) < 6:
            # Add auto-generated tags from context n-grams
            if context.relevant_ngrams and len(context.relevant_ngrams) > 0:
                for ngram in context.relevant_ngrams:
                    if ngram not in normalized_tags and len(normalized_tags) < 6:
                        normalized_tags.append(ngram)
                        break
            else:
                # Fallback generic tags
                fallback_tags = ["bittensor", "decentralized", "ai", "blockchain", "subnet"]
                for tag in fallback_tags:
                    if tag not in normalized_tags and len(normalized_tags) < 6:
                        normalized_tags.append(tag)
                        break
        
        result["secondary_tags"] = normalized_tags
        print(f"Secondary tags normalized: {raw_tags} -> {normalized_tags}")
        
        # Process privacy/security flag
        result["privacy_security_flag"] = bool(result.get("privacy_security_flag", False))
        print(f"Privacy/security flag: {result['privacy_security_flag']}")
        
        # Apply confidence penalties for model-only mode
        if mode == "model-only":
            result["confidence"] = min(result.get("confidence", 0), MODEL_ONLY_MAX_CONF)
            print(f"Model-only mode: confidence clamped to {result['confidence']}")
        
        # Apply provenance penalty for model-derived categories
        if provenance.get("primary_category") == "model" and context.token_count >= MIN_CONTEXT_TOKENS:
            current_confidence = result.get("confidence", 0)
            result["confidence"] = max(current_confidence - 5, 0)
            print(f"⚠️  Provenance penalty: confidence reduced by 5 (model-derived category)")
        
        # Add context token count
        result["context_tokens"] = context.token_count
        
        return result
    except Exception as e:
        print(f"\nError calling OpenAI API:")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        if hasattr(e, 'response'):
            print(f"Response status: {e.response.status_code if hasattr(e.response, 'status_code') else 'N/A'}")
            print(f"Response body: {e.response.text if hasattr(e.response, 'text') else 'N/A'}")
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
        enriched.primary_category = enrichment.get('primary_category')
        enriched.secondary_tags = ','.join(enrichment.get('secondary_tags', []))
        enriched.confidence = enrichment.get('confidence')
        enriched.privacy_security_flag = enrichment.get('privacy_security_flag')
        enriched.last_enriched_at = datetime.now()
        
        # Save context hash
        enriched.context_hash = compute_context_hash(context)
        
        # Save new fields
        enriched.context_tokens = enrichment.get('context_tokens', 0)
        enriched.provenance = json.dumps(enrichment.get('provenance', {}))
        
        session.commit()
        print(f"Enrichment saved to database for subnet {netuid}")
        print(f"Context tokens: {enriched.context_tokens}")
        print(f"Provenance: {enriched.provenance}")

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
            context = prepare_context(netuid)
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