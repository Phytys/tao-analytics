#!/usr/bin/env python
"""
Enrich subnet data using OpenAI's GPT-4.

This script analyzes subnet data using OpenAI's GPT-4 model to extract:
- Tagline: A concise description of the project
- Project Purpose: Detailed explanation of what the project does
- Category: Main category of the project (e.g., AI, DeFi, Infrastructure)
- Tags: Relevant tags for the project
- Confidence: Confidence level in the analysis (0-100)

The script can either:
1. Load existing context from a JSON file
2. Generate new context using prepare_context.py

Usage:
    python enrich_with_openai.py [--netuid <netuid>] [--context-file <file>]

Options:
    --netuid <netuid>     : NetUID of the subnet to analyze (if not provided, processes all subnets)
    --context-file <file> : Use existing context file instead of generating new one
    --no-save            : Don't save results to database (just print them)
    --force            : Force enrichment even if context hasn't changed
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
from config import DB_URL, OPENAI_KEY, OPENAI_MODEL, CATEGORY_CHOICES, ALLOW_MODEL_KNOWLEDGE, MIN_CONTEXT_TOKENS, MODEL_ONLY_MAX_CONF
from prepare_context import prepare_context, format_context, SubnetContext, get_all_netuids, compute_context_hash

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_KEY)

SYSTEM_PREFIX = """\
You are a researcher creating a structured JSON profile for Bittensor subnets.
Respond with *only* valid JSON following the schema given below.

If a value is not in the supplied context but you *know it confidently* from
your own pre-training, you MAY use it, but set `"provenance":"model"` and
lower `"confidence"` accordingly. If unsure, leave the field empty and
set confidence to a low number.

Schema (all strings unless noted):
{{
  "tagline":               "",
  "project_purpose":       "",
  "category":              "",        // one of: {category_list}
  "tags":                  [""],      // comma-separated keywords
  "confidence":            0-100,     // int
  "provenance":            {{          // track where each field came from
       "tagline": "context|model|both|unknown",
       "project_purpose": "...",
       "category": "...",
       "tags": "..."
  }}
}}

{mode_instruction}
"""

def build_prompt(context: SubnetContext, mode: str) -> str:
    """Build the prompt based on context availability and mode."""
    category_list = ", ".join(CATEGORY_CHOICES)
    
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
    
    system_prompt = SYSTEM_PREFIX.format(
        category_list=category_list,
        mode_instruction=mode_instruction
    )
    
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

def enrich_with_openai(context: SubnetContext) -> Optional[Dict[str, Any]]:
    """Call OpenAI API to analyze the subnet."""
    mode = "model-only" if context.token_count < MIN_CONTEXT_TOKENS else "mixed"
    print(f"Enrichment mode: {mode} (context tokens: {context.token_count})")
    
    # Build prompt based on mode
    prompt = build_prompt(context, mode)
    
    print("\nAttempting OpenAI API call...")
    print(f"Using model: {OPENAI_MODEL}")
    print(f"API Key present: {'Yes' if OPENAI_KEY else 'No'}")
    try:
        # Call OpenAI API
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that analyzes Bittensor subnet projects."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,  # Low temperature for more consistent results
            max_tokens=1000
        )
        # Print the raw LLM response immediately
        content = response.choices[0].message.content
        print("\n--- RAW LLM RESPONSE ---")
        print(content)
        print("--- END RAW LLM RESPONSE ---\n")
    except Exception as e:
        print("[ERROR] Exception during OpenAI API call!")
        print(f"Exception: {e}")
        return None
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
        # Parse response
        result = json.loads(json_str)
    except Exception as e:
        print("[ERROR] Failed to parse LLM response as JSON!")
        print(f"Raw content was:\n{content}")
        print(f"Extracted JSON string was:\n{json_str}")
        print(f"Exception: {e}")
        return None
    # Validate and normalize category
    raw_cat = result.get("category", "").strip()
    # Case-insensitive match to our canonical list
    canonical_cat = next(
        (c for c in CATEGORY_CHOICES if c.lower() == raw_cat.lower()), 
        "Other"
    )
    result["category"] = canonical_cat
    print(f"Category normalized: '{raw_cat}' -> '{canonical_cat}'")
    # Apply confidence penalties for model-only mode
    if mode == "model-only":
        result["confidence"] = min(result.get("confidence", 0), MODEL_ONLY_MAX_CONF)
        print(f"Model-only mode: confidence clamped to {result['confidence']}")
    # Add context token count
    result["context_tokens"] = context.token_count
    return result

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
        enriched.what_it_does = enrichment.get('project_purpose')
        enriched.category = enrichment.get('category')
        enriched.tags = ','.join(enrichment.get('tags', []))
        enriched.confidence = enrichment.get('confidence')
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