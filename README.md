# TAO Analytics: Subnet Data Collection & Enrichment Pipeline

## Project Overview

This project provides a robust pipeline for collecting, enriching, and analyzing data about Bittensor subnets. It fetches raw subnet data, scrapes additional context from websites and GitHub, and uses OpenAI's GPT-4 to generate structured insights with full provenance tracking, storing everything in a local SQLite database.

**Key Features:**
- **Provenance-aware enrichment**: Tracks whether data comes from scraped context or model knowledge
- **Smart caching**: Only re-enriches when context has changed (MD5 hash-based)
- **Batch processing**: Efficient processing of multiple subnets with cost control
- **Quality control**: Confidence scoring and context token tracking
- **Standardized categories**: Predefined taxonomy for consistent classification

---

## Project Structure

```
tao-analytics/
│
├── config.py                 # Configuration and API keys
├── models.py                 # Database schema definitions
├── requirements.txt          # Python dependencies
├── tao.sqlite               # SQLite database (308KB, 154 lines)
├── .gitignore               # Git ignore rules
├── README.md                # This file
├── db_export/               # Exported CSV files
│   ├── subnet_meta.csv      # Enriched subnet data
│   ├── screener_raw.csv     # Raw screener data
│   └── parsed_subnets.csv   # Parsed subnet information
├── scripts/
│   ├── __init__.py
│   ├── data-collection/
│   │   ├── __init__.py
│   │   ├── fetch_screener.py        # Download subnet data from TAO API
│   │   ├── prepare_context.py       # Scrape websites and GitHub READMEs
│   │   ├── enrich_with_openai.py    # LLM enrichment with provenance tracking
│   │   ├── batch_enrich.py          # Batch processing with cost control
│   │   └── contexts/                # Cached context JSON files
│   │       ├── 1.json
│   │       ├── 19.json
│   │       └── 64.json
│   ├── inspect_raw_data.py          # Inspect raw screener data
│   ├── explore_raw_data.py          # Explore and parse raw data
│   ├── export_db_table.py           # Export tables to CSV
│   └── reset_db.py                  # Reset database schema
└── venv/                    # Python virtual environment
```

---

## Data Pipeline

### 1. **Fetch Screener Data**
- `scripts/data-collection/fetch_screener.py`
- Downloads subnet data from the TAO API and stores it in the `screener_raw` table
- Updates the `subnet_meta` table with subnet names and resets LLM fields if names change
- **Current status**: 123 subnets loaded

### 2. **Prepare Context**
- `scripts/data-collection/prepare_context.py`
- For each subnet, gathers:
  - Subnet number and name
  - Website URL and GitHub repo (from screener)
  - Scraped website content (if available, with retry logic)
  - Scraped GitHub README (if available)
- Cleans and truncates content, estimates token count, and saves context as JSON
- **Smart features**: Retry logic for failed requests, content truncation, token estimation

### 3. **Enrich with OpenAI** (Provenance-Aware)
- `scripts/data-collection/enrich_with_openai.py`
- **Provenance tracking**: Distinguishes between "context", "model", "both", or "unknown" sources
- **Smart caching**: MD5 hash-based change detection to avoid unnecessary API calls
- **Quality control**: Confidence scoring and context token tracking
- **Category standardization**: Uses predefined taxonomy from `config.py`
- Updates the `subnet_meta` table with enriched fields and provenance information

### 4. **Batch Processing**
- `scripts/data-collection/batch_enrich.py`
- **Cost control**: Configurable delays between API calls
- **Progress tracking**: Real-time status updates and success/failure reporting
- **Flexible input**: Process specific subnets, ranges, or all subnets
- **Current status**: All 123 subnets successfully enriched

### 5. **Explore and Export Data**
- `scripts/inspect_raw_data.py`, `scripts/explore_raw_data.py`, `scripts/export_db_table.py`
- Tools for inspecting, parsing, and exporting data from the database to CSV
- **Current exports**: Full enriched dataset available in `db_export/`

### 6. **Database Reset**
- `scripts/reset_db.py`
- Drops and recreates all tables in `tao.sqlite` using the latest schema

---

## Database Schema

### **screener_raw**
Stores raw JSON data for each subnet from the TAO API.

### **subnet_meta**
Stores subnet information and LLM-enriched fields:

| Field | Type | Description |
|-------|------|-------------|
| `netuid` | Integer | Primary key, subnet number |
| `subnet_name` | String | Subnet name from screener |
| `tagline` | String | LLM-generated concise description |
| `what_it_does` | Text | LLM-generated detailed purpose |
| `category` | String | Standardized category (from predefined list) |
| `tags` | String | Comma-separated relevant tags |
| `confidence` | Float | LLM confidence score (0-100) |
| `context_hash` | String | MD5 hash of context for change detection |
| `context_tokens` | Integer | Number of context tokens available |
| `provenance` | Text | JSON tracking data source for each field |
| `last_enriched_at` | DateTime | When LLM fields were last updated |
| `updated_at` | DateTime | Last database update |

---

## Configuration

### **config.py Settings**

```python
# API Keys (set in .env file)
TAO_APP_API_KEY = "your-tao-api-key"
OPENAI_API_KEY = "your-openai-api-key"

# Predefined subnet categories
CATEGORY_CHOICES = [
    "LLM-Inference", "LLM-Training", "Data", "GPU-Compute",
    "BTC-Hash", "Trading", "Tooling", "Research", 
    "Infrastructure", "Other"
]

# Enrichment policy
ALLOW_MODEL_KNOWLEDGE = True      # Use model prior knowledge
MIN_CONTEXT_TOKENS = 50           # Below this → model-only mode
MODEL_ONLY_MAX_CONF = 50          # Max confidence for model-only
```

---

## Setup & Usage

### 1. **Install Dependencies**

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. **Configure Environment**

Create a `.env` file in the project root:

```bash
TAO_APP_API_KEY=your-tao-api-key
OPENAI_API_KEY=your-openai-api-key
```

### 3. **Initialize Database**

```bash
python scripts/reset_db.py
```

### 4. **Fetch Subnet Data**

```bash
python scripts/data-collection/fetch_screener.py
```

### 5. **Prepare Context**

For a single subnet:
```bash
python scripts/data-collection/prepare_context.py --netuid 1
```

For all subnets:
```bash
python scripts/data-collection/prepare_context.py
```

### 6. **Enrich with OpenAI**

For a single subnet:
```bash
python scripts/data-collection/enrich_with_openai.py --netuid 1
```

For all subnets (batch processing):
```bash
python scripts/data-collection/batch_enrich.py --range 1 123 --delay 2
```

### 7. **Export Data**

List available tables:
```bash
python scripts/export_db_table.py --list
```

Export enriched data:
```bash
python scripts/export_db_table.py --table subnet_meta
```

---

## Provenance Tracking

The enrichment system tracks the source of each field:

- **"context"**: Data came from scraped website/README content
- **"model"**: Data came from LLM's prior knowledge
- **"both"**: Data was found in both context and model knowledge
- **"unknown"**: LLM couldn't determine the source

**Example provenance:**
```json
{
  "tagline": "context",
  "project_purpose": "context", 
  "category": "model",
  "tags": "both"
}
```

---

## Quality Control

### **Confidence Scoring**
- **95-100**: High confidence, rich context available
- **50-94**: Moderate confidence, some context available
- **10-49**: Low confidence, minimal or no context
- **Model-only mode**: Automatically clamped to max 50

### **Context Token Tracking**
- **750+ tokens**: Rich context (website + README)
- **250-749 tokens**: Moderate context (partial data)
- **50-249 tokens**: Minimal context
- **0-49 tokens**: No context (model-only mode)

---

## Current Status

- **Total subnets processed**: 123
- **Success rate**: 100%
- **Database size**: 308KB
- **Enrichment complete**: All subnets enriched with provenance tracking
- **Categories distributed**: Across all 10 predefined categories
- **Quality**: Mix of high-confidence (context-rich) and lower-confidence (model-only) enrichments

---

## Example Context JSON

See `scripts/data-collection/contexts/1.json` for an example of the context sent to OpenAI.

---

## Notes

- The pipeline is designed to be Heroku-friendly (no browser scraping, lightweight dependencies)
- All context and enrichment steps are logged for transparency and debugging
- Hash-based caching prevents unnecessary API calls when context hasn't changed
- Provenance tracking enables quality control and transparency
- Batch processing includes cost control and progress tracking

---

## License

MIT 