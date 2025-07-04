from pathlib import Path
import os
import re
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env")

# Environment variable validation
def validate_env_vars():
    """Validate required environment variables."""
    required_vars = {
        'SECRET_KEY': 'Flask secret key for session security',
        'TAO_APP_API_KEY': 'TAO.app API key for data fetching',
        'OPENAI_API_KEY': 'OpenAI API key for enrichment'
    }
    
    missing_vars = []
    for var, description in required_vars.items():
        if not os.getenv(var):
            missing_vars.append(f"{var} ({description})")
    
    if missing_vars:
        print("WARNING: Missing environment variables:")
        for var in missing_vars:
            print(f"  - {var}")
        print("Some features may not work correctly.")
    
    return len(missing_vars) == 0

# Validate environment on import
validate_env_vars()

TAO_KEY = os.getenv("TAO_APP_API_KEY")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
COINGECKO_API_KEY = os.getenv('COINGECKO_API_KEY')

# Security: Ensure secret key is strong
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY or len(SECRET_KEY) < 32:
    print("WARNING: SECRET_KEY should be at least 32 characters long for security")

TAO_ENDPOINT = "https://api.tao.app/api/beta/subnet_screener"
TAO_APP_BASE_URL = "https://api.tao.app/api/beta"  # Base URL for TAO.app API endpoints

DB_PATH = BASE_DIR / "tao.sqlite"
DB_URL = f"sqlite:///{DB_PATH}"
OPENAI_MODEL = "gpt-4o"  # Optimal balance of quality and cost for enrichment

# Granular primary categories for power-user analytics
PRIMARY_CATEGORIES = [
    "LLM-Inference",
    "LLM-Training / Fine-tune", 
    "Data-Feeds & Oracles",
    "Serverless-Compute",  # deploy & run models, GPU grids
    "AI-Verification & Trust",  # zero-knowledge proofs, model authenticity
    "Confidential-Compute",  # secure, private AI execution
    "Hashrate-Mining (BTC / PoW)",
    "Finance-Trading & Forecasting",
    "Security & Auditing",
    "Privacy / Anonymity",
    "Media-Vision / 3-D",
    "Science-Research (Non-financial)",
    "Consumer-AI & Games",
    "Dev-Tooling"  # SDKs, dashboards, validators' tools
]

def normalize_tags(tags_list):
    """Normalize tags: lower-case, kebab-case, max 6 tags, no duplicates."""
    if not tags_list:
        return []
    
    normalized = []
    for tag in tags_list:
        # Convert to lowercase and replace spaces/special chars with hyphens
        clean_tag = re.sub(r'[^a-zA-Z0-9\s-]', '', tag.lower())
        clean_tag = re.sub(r'[\s-]+', '-', clean_tag).strip('-')
        
        if clean_tag and clean_tag not in normalized:
            normalized.append(clean_tag)
    
    # Remove duplicates and limit to 6 tags
    unique_tags = list(dict.fromkeys(normalized))
    return unique_tags[:6]

# Legacy category choices (for backward compatibility)
CATEGORY_CHOICES = PRIMARY_CATEGORIES

# Enrichment policy
ALLOW_MODEL_KNOWLEDGE = True  # Whether to let model use prior knowledge
MODEL_ONLY_MAX_CONF = 50      # Max confidence when using model knowledge only
