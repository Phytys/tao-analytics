# TAO Analytics: Bittensor Subnet Intelligence Platform

## Project Overview

A comprehensive data collection, enrichment, and analytics platform for Bittensor subnets. This project fetches raw subnet data from the TAO API, scrapes additional context from websites and GitHub, uses OpenAI's GPT-4 to generate structured insights with full provenance tracking, and provides a modern web dashboard for exploration and analysis.

**Key Features:**
- **Provenance-aware enrichment**: Tracks whether data comes from scraped context or model knowledge
- **Smart caching**: Only re-enriches when context has changed (MD5 hash-based)
- **Batch processing**: Efficient processing of multiple subnets with cost control
- **Quality control**: Confidence scoring and context token tracking
- **Standardized categories**: Predefined taxonomy for consistent classification
- **Modern Dashboard**: Web interface with filtering, charts, and expandable cards
- **Admin System**: Protected system information dashboard for administrators
- **Real-time data**: Live market cap and performance metrics from TAO.app API

---

## Project Structure

```
tao-analytics/
│
├── app.py                    # Main Flask application with Dash integration
├── config.py                 # Configuration, API keys, and category definitions
├── models.py                 # Database schema definitions
├── requirements.txt          # Python dependencies
├── Procfile                  # Heroku deployment configuration
├── tao.sqlite               # SQLite database (308KB, 124 subnets)
├── .gitignore               # Git ignore rules
├── README.md                # This file
├── PLAN.md                  # Project roadmap and development plan
├── admin_config.md          # Admin authentication configuration
├── processed_netuids.json   # Cache of processed subnet IDs
│
├── static/                   # Static assets for landing page
│   ├── css/
│   │   └── main.css         # Landing page styles
│   └── favicons/            # Favicon assets
│
├── templates/                # Flask templates
│   ├── index.html           # Tesla-inspired landing page
│   └── admin_login.html     # Admin authentication page
│
├── dash_app/                 # Dash dashboard application
│   ├── __init__.py          # Dash app initialization and routing
│   ├── pages/
│   │   ├── explorer.py      # Subnet Explorer dashboard (public)
│   │   └── system_info.py   # System Information dashboard (admin only)
│   └── assets/
│       ├── custom.css       # Dashboard styling
│       └── subnet_placeholder.svg
│
├── services/                 # Service layer
│   ├── auth.py              # Admin authentication service
│   ├── cache.py             # Caching service with statistics
│   ├── db.py                # Database service with query helpers
│   ├── db_utils.py          # Database utility functions
│   ├── favicons.py          # Favicon download service
│   └── metrics.py           # Metrics and analytics service
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
│   ├── analyze_enrichment_stats.py  # Analyze enrichment quality and statistics
│   ├── auto_fallback_enrich.py      # Automatic fallback enrichment for failed subnets
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

## File Descriptions

### **Core Application Files**
- **`app.py`**: Main Flask application that serves the landing page, admin authentication, and mounts the Dash dashboard
- **`config.py`**: Configuration settings, API keys, category definitions, and enrichment policies
- **`models.py`**: SQLAlchemy database models and schema definitions
- **`requirements.txt`**: Python package dependencies
- **`Procfile`**: Heroku deployment configuration

### **Dashboard Files**
- **`dash_app/__init__.py`**: Dash app initialization, routing, and navigation setup
- **`dash_app/pages/explorer.py`**: Public subnet explorer with filtering, search, and interactive charts
- **`dash_app/pages/system_info.py`**: Admin-only system information dashboard with performance metrics

### **Service Layer**
- **`services/auth.py`**: Admin authentication with session management and decorators
- **`services/cache.py`**: Caching service with statistics and cleanup utilities
- **`services/db.py`**: Database service with query helpers and connection management
- **`services/db_utils.py`**: Database utility functions for common operations
- **`services/favicons.py`**: Favicon download and management service
- **`services/metrics.py`**: Metrics service for dashboard KPIs and analytics

### **Data Collection Scripts**
- **`scripts/data-collection/fetch_screener.py`**: Downloads subnet data from TAO API
- **`scripts/data-collection/prepare_context.py`**: Scrapes websites and GitHub READMEs for context
- **`scripts/data-collection/enrich_with_openai.py`**: LLM enrichment with provenance tracking
- **`scripts/data-collection/batch_enrich.py`**: Batch processing with cost control and progress tracking
- **`scripts/analyze_enrichment_stats.py`**: Analyzes enrichment quality and generates statistics
- **`scripts/auto_fallback_enrich.py`**: Automatic retry and fallback enrichment for failed subnets

### **Utility Scripts**
- **`scripts/inspect_raw_data.py`**: Inspect and analyze raw screener data
- **`scripts/explore_raw_data.py`**: Explore and parse raw data structures
- **`scripts/export_db_table.py`**: Export database tables to CSV format
- **`scripts/reset_db.py`**: Reset database schema and tables

### **Templates and Static Files**
- **`templates/index.html`**: Tesla-inspired landing page with navigation
- **`templates/admin_login.html`**: Admin authentication page
- **`static/css/main.css`**: Landing page styling
- **`dash_app/assets/custom.css`**: Dashboard styling and custom components

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- TAO API key
- OpenAI API key

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
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your-secure-password
SECRET_KEY=your-secret-key-for-sessions
```

### 3. **Launch the Application**

```bash
python app.py          # → http://127.0.0.1:5000/
```

**Available Pages:**
- **Homepage**: `http://127.0.0.1:5000/` - Landing page with navigation
- **Subnet Explorer**: `http://127.0.0.1:5000/dash/explorer` - Public subnet dashboard
- **Admin Login**: `http://127.0.0.1:5000/admin/login` - Admin authentication
- **System Info**: `http://127.0.0.1:5000/dash/system-info` - Admin-only system dashboard

---

## Dashboard Features

### **Public Subnet Explorer**
- **Modern design** with responsive layout
- **Filterable subnet cards** with market cap, categories, and tags
- **Interactive charts** (category distribution, confidence scores)
- **Search functionality** across subnet names and tags
- **Real-time KPI metrics** including enrichment statistics
- **Expandable cards** showing detailed descriptions and links
- **Category-colored borders** matching chart colors
- **Website & GitHub links** with proper URL formatting

### **Admin System Information Dashboard**
- **Protected access** requiring admin authentication
- **System performance metrics** and cache statistics
- **Enrichment quality analytics** with confidence distributions
- **Database statistics** and table information
- **Cache management** with clear and cleanup functions
- **Top subnets** by market cap and performance
- **Real-time data refresh** every 30 seconds

### **Authentication System**
- **Admin login/logout** with session management
- **Protected routes** for system information
- **Environment-based credentials** (no hardcoded passwords)
- **Automatic redirects** for unauthenticated access

---

## Data Pipeline

### 1. **Fetch Screener Data**
```bash
python scripts/data-collection/fetch_screener.py
```
- Downloads subnet data from the TAO.app API
- Stores raw JSON data in `screener_raw` table
- Updates `subnet_meta` table with subnet names

### 2. **Prepare Context**
```bash
python scripts/data-collection/prepare_context.py
```
- Scrapes website content and GitHub READMEs
- Cleans and truncates content
- Estimates token count and saves as JSON
- **Smart features**: Retry logic, content truncation, token estimation

### 3. **Enrich with OpenAI**
```bash
python scripts/data-collection/enrich_with_openai.py --netuid 1
```
- **Provenance tracking**: Distinguishes between context, model, both, or unknown sources
- **Smart caching**: MD5 hash-based change detection
- **Quality control**: Confidence scoring and context token tracking
- **Category standardization**: Uses predefined taxonomy

### 4. **Batch Processing**
```bash
python scripts/data-collection/batch_enrich.py --range 1 124 --delay 2
```
- **Cost control**: Configurable delays between API calls
- **Progress tracking**: Real-time status updates
- **Flexible input**: Process specific subnets, ranges, or all subnets

### 5. **Analyze and Export**
```bash
python scripts/analyze_enrichment_stats.py
python scripts/export_db_table.py --table subnet_meta
```

---

## Database Schema

### **screener_raw**
Raw JSON data from TAO.app API:
- Market cap, volume, and performance metrics
- Website URLs and GitHub repositories
- Owner information and contact details

### **subnet_meta**
Enriched subnet information:

| Field | Type | Description |
|-------|------|-------------|
| `netuid` | Integer | Primary key, subnet number |
| `subnet_name` | String | Subnet name from screener |
| `tagline` | String | LLM-generated concise description |
| `what_it_does` | Text | LLM-generated detailed purpose |
| `primary_category` | String | Standardized category |
| `secondary_tags` | Text | Comma-separated relevant tags |
| `confidence` | Float | LLM confidence score (0-100) |
| `context_hash` | String | MD5 hash for change detection |
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

# Granular primary categories
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

## Deployment

### **Heroku Deployment**
```bash
# Set environment variables
heroku config:set DATABASE_URL=$(heroku config:get DATABASE_URL)
heroku config:set OPENAI_API_KEY=your-openai-key
heroku config:set TAO_APP_API_KEY=your-tao-key
heroku config:set ADMIN_USERNAME=admin
heroku config:set ADMIN_PASSWORD=your-secure-password
heroku config:set SECRET_KEY=your-secret-key

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

## Security Features

- **Environment-based credentials**: No hardcoded passwords
- **Session management**: Secure admin authentication
- **Protected routes**: Admin-only access to system information
- **Input validation**: Proper sanitization of user inputs
- **Error handling**: Graceful error handling without information leakage

---

## Notes

- The pipeline is designed to be Heroku-friendly (no browser scraping, lightweight dependencies)
- All context and enrichment steps are logged for transparency and debugging
- Hash-based caching prevents unnecessary API calls when context hasn't changed
- Provenance tracking enables quality control and transparency
- Batch processing includes cost control and progress tracking
- URL formatting ensures proper links (adds https:// to domains without protocols)
- Modern design provides professional user experience
- Admin system provides secure access to system information and management functions

---

## License

MIT 