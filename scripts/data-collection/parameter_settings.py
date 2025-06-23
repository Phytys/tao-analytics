"""
Parameter Settings for TAO Analytics Data Collection and Enrichment

This file centralizes all configurable parameters for the data collection pipeline.
Modify these values to adjust the behavior of the enrichment process.
"""

# =============================================================================
# CONTENT LIMITS
# =============================================================================

# Maximum characters to fetch from website content
MAX_WEBSITE_CHARS = 3000

# Maximum characters to fetch from GitHub README
MAX_README_CHARS = 2000

# =============================================================================
# LLM RESPONSE LIMITS
# =============================================================================

# Maximum words for tagline (concise description)
TAGLINE_MAX_WORDS = 8

# Maximum words for what_it_does (detailed description)
WHAT_IT_DOES_MAX_WORDS = 100

# Maximum words for primary use case
PRIMARY_USE_CASE_MAX_WORDS = 20

# Maximum words for key technical features
KEY_TECHNICAL_FEATURES_MAX_WORDS = 30

# Maximum number of secondary tags
MAX_SECONDARY_TAGS = 6

# =============================================================================
# API CONFIGURATION
# =============================================================================

# Maximum tokens for OpenAI API response
OPENAI_MAX_TOKENS = 1500

# OpenAI API timeout in seconds
OPENAI_TIMEOUT = 90

# Temperature for OpenAI API calls (0.0 = deterministic, 1.0 = creative)
OPENAI_TEMPERATURE = 0.1

# =============================================================================
# CONTEXT THRESHOLDS
# =============================================================================

# Minimum context tokens required for enrichment (below this = model-only mode)
MIN_CONTEXT_TOKENS = 100

# Maximum confidence when using model knowledge only
MODEL_ONLY_MAX_CONFIDENCE = 50

# =============================================================================
# QUALITY CONTROL PENALTIES
# =============================================================================

# Confidence penalty for model-derived categories despite good context
PROVENANCE_PENALTY = 5

# Additional penalty for thin context with model provenance
THIN_CONTEXT_PENALTY = 15

# Threshold for thin context (tokens below this get additional penalty)
THIN_CONTEXT_THRESHOLD = 100

# Threshold for thin context in auto fallback enrichment
AUTO_FALLBACK_THIN_CONTEXT_THRESHOLD = 100

# Low confidence threshold for manual review flag
LOW_CONFIDENCE_THRESHOLD = 70

# =============================================================================
# WEB SCRAPING SETTINGS
# =============================================================================

# Maximum retries for website scraping
MAX_SCRAPING_RETRIES = 3

# Timeout for website requests in seconds
WEBSITE_TIMEOUT = 30.0

# Timeout for GitHub API requests in seconds
GITHUB_TIMEOUT = 10

# Timeout for Wayback Machine requests in seconds
WAYBACK_TIMEOUT = 15

# Maximum GitHub issues to fetch as fallback context
MAX_GITHUB_ISSUES = 5

# Minimum content length for meaningful fallback content
MIN_FALLBACK_CONTENT_LENGTH = 100

# =============================================================================
# BATCH PROCESSING
# =============================================================================

# Default delay between API calls in seconds
DEFAULT_API_DELAY = 1.0

# Progress save frequency (save every N subnets)
PROGRESS_SAVE_FREQUENCY = 10

# =============================================================================
# TEXT PROCESSING
# =============================================================================

# Token estimation ratio (characters per token)
TOKEN_ESTIMATION_RATIO = 4

# =============================================================================
# FALLBACK TAGS
# =============================================================================

# Generic fallback tags when context is insufficient
FALLBACK_TAGS = [
    "bittensor",
    "decentralized", 
    "ai",
    "blockchain",
    "subnet"
]

# =============================================================================
# CACHE SETTINGS
# =============================================================================

# Whether to allow model knowledge when context is insufficient
ALLOW_MODEL_KNOWLEDGE = True

# =============================================================================
# VALIDATION SETTINGS
# =============================================================================

# Default category when validation fails (must NOT be in PRIMARY_CATEGORIES)
DEFAULT_CATEGORY = "Uncategorized"

# Whether to re-ask for category when model chooses default despite good context
ENABLE_CATEGORY_REASK = True

# Max tokens for category re-ask calls
CATEGORY_REASK_MAX_TOKENS = 50 