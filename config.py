from pathlib import Path
import os
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env")

TAO_KEY = os.getenv("TAO_APP_API_KEY")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

TAO_ENDPOINT = "https://api.tao.app/api/beta/subnet_screener"

DB_PATH = BASE_DIR / "tao.sqlite"
DB_URL = f"sqlite:///{DB_PATH}"
OPENAI_MODEL = "gpt-4-turbo-preview"  # Using the latest model

# Updateable list of *coarse* subnet categories users care about.
# ⚠️  Order matters only for UI; feel free to reorder later.
CATEGORY_CHOICES: list[str] = [
    "LLM-Inference",
    "LLM-Training", 
    "Data",
    "GPU-Compute",
    "BTC-Hash",
    "Trading",
    "Tooling",
    "Research",
    "Infrastructure",
    "Other",          # ←  fallback bucket
]

# Enrichment policy
ALLOW_MODEL_KNOWLEDGE = True  # Whether to let model use prior knowledge
MIN_CONTEXT_TOKENS = 50       # Below this → model-only mode
MODEL_ONLY_MAX_CONF = 50      # Max confidence when using model knowledge only
