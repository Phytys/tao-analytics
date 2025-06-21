# TAO Analytics: Bittensor Subnet Intelligence Platform

## Project Overview

A comprehensive data collection, enrichment, and analytics platform for Bittensor subnets. This project fetches raw subnet data from the TAO API, scrapes additional context from websites and GitHub, uses OpenAI's GPT-4 to generate structured insights with full provenance tracking, and provides a Tesla-inspired web dashboard for exploration and analysis.

**Key Features:**
- **Provenance-aware enrichment**: Tracks whether data comes from scraped context or model knowledge
- **Smart caching**: Only re-enriches when context has changed (MD5 hash-based)
- **Batch processing**: Efficient processing of multiple subnets with cost control
- **Quality control**: Confidence scoring and context token tracking
- **Standardized categories**: Predefined taxonomy for consistent classification
- **Tesla-inspired Dashboard**: Modern web interface with filtering, charts, and expandable cards
- **Real-time data**: Live market cap and performance metrics from TAO.app API

---

## Project Structure

```
tao-analytics/
│
├── app.py                    # Flask application with Dash integration
├── config.py                 # Configuration and API keys
├── models.py                 # Database schema definitions
├── requirements.txt          # Python dependencies
├── Procfile                  # Heroku deployment configuration
├── tao.sqlite               # SQLite database (308KB, 124 subnets)
├── .gitignore               # Git ignore rules
├── README.md                # This file
│
├── static/                   # Static assets for landing page
│   └── css/
│       └── main.css         # Tesla-inspired landing page styles
│
├── templates/                # Flask templates
│   └── index.html           # Tesla-inspired landing page
│
├── dash_app/                 # Dash dashboard application
│   ├── __init__.py          # Dash app initialization
│   ├── pages/
│   │   └── explorer.py      # Subnet Explorer dashboard
│   └── assets/
│       ├── custom.css       # Dashboard styling
│       └── subnet_placeholder.svg
│
├── services/                 # Service layer
│   ├── db.py                # Database service with query helpers
│   └── favicons.py          # Favicon download service (stub)
│
├── scripts/                  # Data processing scripts
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
│
├── db_export/               # Exported CSV files
│   ├── subnet_meta.csv      # Enriched subnet data
│   ├── screener_raw.csv     # Raw screener data
│   └── parsed_subnets.csv   # Parsed subnet information
│
└── venv/                    # Python virtual environment
```

---

## 🚀 Quick Start

### Run the Subnet Explorer Dashboard

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set up environment (create .env file)
TAO_APP_API_KEY=your-tao-api-key
OPENAI_API_KEY=your-openai-api-key

# 3. Launch the application
python app.py          # → http://127.0.0.1:5000/
# or
export FLASK_APP=app.py
flask run              # → http://127.0.0.1:5000/dash/
```

**Dashboard Features:**
- **Tesla-inspired design** with modern UI/UX
- **Filterable subnet cards** with market cap, categories, and tags
- **Interactive charts** (pie chart for counts, bar chart for market cap by category)
- **Search functionality** across subnet names and tags
- **Real-time KPI metrics** including privacy-focused subnet percentage
- **Expandable cards** showing detailed descriptions and links
- **Category-colored borders** matching chart colors
- **Website & GitHub links** with proper URL formatting

---

## Data Pipeline

### 1. **Fetch Screener Data**
- `scripts/data-collection/fetch_screener.py`
- Downloads subnet data from the TAO.app API and stores it in the `screener_raw` table
- Updates the `subnet_meta` table with subnet names and resets LLM fields if names change
- **Current status**: 124 subnets loaded

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
- **Current status**: 94 subnets successfully enriched

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
Stores raw JSON data for each subnet from the TAO.app API, including:
- Market cap, volume, and performance metrics
- Website URLs and GitHub repositories
- Owner information and contact details

### **subnet_meta**
Stores subnet information and LLM-enriched fields:

| Field | Type | Description |
|-------|------|-------------|
| `netuid` | Integer | Primary key, subnet number |
| `subnet_name` | String | Subnet name from screener |
| `tagline` | String | LLM-generated concise description |
| `what_it_does` | Text | LLM-generated detailed purpose |
| `primary_category` | String | Standardized category (from predefined list) |
| `secondary_tags` | Text | Comma-separated relevant tags |
| `confidence` | Float | LLM confidence score (0-100) |
| `context_hash` | String | MD5 hash of context for change detection |
| `context_tokens` | Integer | Number of context tokens available |
| `provenance` | Text | JSON tracking data source for each field |
| `privacy_security_flag` | Boolean | Privacy/security focus flag |
| `last_enriched_at` | DateTime | When LLM fields were last updated |
| `updated_at` | DateTime | Last database update |

---

## Configuration

### **config.py Settings**

```python
# API Keys (set in .env file)
TAO_APP_API_KEY = "your-tao-api-key"
OPENAI_API_KEY = "your-openai-api-key"

# Granular primary categories for power-user analytics
PRIMARY_CATEGORIES = [
    "LLM-Inference",
    "LLM-Training / Fine-tune", 
    "Data-Feeds & Oracles",
    "Serverless-Compute",
    "Hashrate-Mining (BTC / PoW)",
    "Finance-Trading & Forecasting",
    "Security & Auditing",
    "Privacy / Anonymity",
    "Media-Vision / 3-D",
    "Science-Research (Non-financial)",
    "Consumer-AI & Games",
    "Dev-Tooling"
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
python scripts/data-collection/batch_enrich.py --range 1 124 --delay 2
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

### 8. **Run the Dashboard**

```bash
# Direct Python execution
python app.py          # → http://127.0.0.1:5000/

# Or using Flask CLI
export FLASK_APP=app.py
flask run              # → http://127.0.0.1:5000/dash/
```

---

## Dashboard Features

### **Tesla-Inspired Design**
- Modern, clean interface with smooth animations
- Responsive design that works on all devices
- Category-colored card borders matching chart colors
- Hover effects and transitions

### **Subnet Cards**
- **Subnet number + name** (e.g., "64 Chutes")
- **Category badges** with color coding
- **Market cap display** (formatted as K/M TAO)
- **Confidence scores** and privacy flags
- **Tag chips** for easy identification
- **Expandable descriptions** with "What it does" details
- **Website & GitHub links** with proper URL formatting

### **Interactive Features**
- **Category filtering** dropdown
- **Search functionality** across names and tags
- **Chart toggles** (subnet count vs. market cap by category)
- **Real-time KPI badges** (subnet count, categories, privacy %, confidence)
- **Responsive grid layout** (3 columns on desktop, 2 on tablet, 1 on mobile)

### **Data Sources**
- **TAO.app API**: Real-time market cap, volume, and performance data
- **OpenAI GPT-4**: AI-powered insights and categorization
- **Web scraping**: Website and GitHub README content for context

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
  "what_it_does": "context", 
  "primary_category": "model",
  "secondary_tags": "both"
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

- **Total subnets**: 124
- **Enriched subnets**: 94 (75.8%)
- **Success rate**: 100% for processed subnets
- **Database size**: 308KB
- **Categories**: 12 granular categories with good distribution
- **Quality**: Mix of high-confidence (context-rich) and lower-confidence (model-only) enrichments

### **Category Distribution**
- Science-Research (Non-financial): 17 subnets
- Finance-Trading & Forecasting: 16 subnets
- Serverless-Compute: 11 subnets
- Security & Auditing: 9 subnets
- LLM-Training / Fine-tune: 9 subnets
- Media-Vision / 3-D: 8 subnets
- LLM-Inference: 7 subnets
- Data-Feeds & Oracles: 6 subnets
- Consumer-AI & Games: 5 subnets
- Dev-Tooling: 3 subnets
- Hashrate-Mining (BTC / PoW): 2 subnets
- Privacy / Anonymity: 1 subnet

---

## Deployment

### **Heroku Deployment**
```bash
# Set environment variables
heroku config:set DATABASE_URL=$(heroku config:get DATABASE_URL)
heroku config:set OPENAI_API_KEY=your-openai-key
heroku config:set TAO_APP_API_KEY=your-tao-key

# Deploy
git push heroku main
```

### **Local Development**
```bash
# Development mode
export FLASK_ENV=development
python app.py

# Production mode
export FLASK_ENV=production
gunicorn app:create_app
```

---

## API Attribution

This project uses data and services from:
- **[TAO.app API](https://tao.app)**: Real-time subnet market data and metrics
- **[OpenAI GPT-4](https://openai.com)**: AI-powered content analysis and enrichment

---

## Notes

- The pipeline is designed to be Heroku-friendly (no browser scraping, lightweight dependencies)
- All context and enrichment steps are logged for transparency and debugging
- Hash-based caching prevents unnecessary API calls when context hasn't changed
- Provenance tracking enables quality control and transparency
- Batch processing includes cost control and progress tracking
- URL formatting ensures proper links (adds https:// to domains without protocols)
- Tesla-inspired design provides modern, professional user experience

---

## License

MIT 