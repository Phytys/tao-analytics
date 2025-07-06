# TAO Analytics

**TAO Analytics** is a production-grade analytics and intelligence dashboard for the Bittensor decentralized AI network. It provides real-time subnet metrics, market cap analytics, AI-powered subnet classification, and deep insights with a modern, responsive UI built using Flask and Dash.

---

## Table of Contents

- [Project Structure](#project-structure)
- [Key Features](#key-features)
- [System Overview](#system-overview)
- [Data Pipeline](#data-pipeline)
- [Setup & Installation](#setup--installation)
- [Configuration](#configuration)
- [Running the App](#running-the-app)
- [Dash App Pages](#dash-app-pages)
- [Database & Data Flow](#database--data-flow)
- [Scripts & Automation](#scripts--automation)
- [Data Collection & Database Storage](#data-collection--database-storage)
- [Services](#services)
- [Deployment](#deployment)
- [Development Notes](#development-notes)
- [License](#license)

---

## Project Structure

```
tao-analytics/
│
├── 📁 Core Application Files
│   ├── app.py                          # Main Flask application (152 lines)
│   ├── config.py                       # Configuration settings (62 lines)
│   ├── models.py                       # Database models (276 lines)
│   ├── requirements.txt                # Python dependencies (24 packages)
│   ├── runtime.txt                     # Python version specification (3.10.14)
│   ├── Procfile                        # Heroku deployment config
│   ├── PLAN.md                         # Development roadmap (135 lines)
│   ├── README.md                       # This documentation file
│   ├── admin_config.md                 # Admin setup instructions (23 lines)
│   ├── tao.sqlite                      # Main SQLite database (1.6MB)
│   └── processed_netuids.json          # Enrichment progress tracking
│
├── 📁 Dash Analytics Dashboard
│   ├── dash_app/
│   │   ├── __init__.py                 # Dash app initialization (225 lines)
│   │   ├── assets/
│   │   │   ├── custom.css              # Dash app styling
│   │   │   ├── favicon.ico             # Dash app favicon
│   │   │   └── subnet_placeholder.svg  # Placeholder image
│   │   └── pages/
│   │       ├── explorer.py             # Main analytics page (779 lines)
│   │       ├── screener.py             # Subnet screener with AI insights (865 lines)
│   │       ├── subnet_detail.py        # Subnet detail page (936 lines)
│   │       ├── system_info.py          # Admin system info (602 lines)
│   │       └── sdk_poc.py              # Bittensor SDK proof of concept (127 lines)
│
├── 📁 Data Collection & Automation
│   ├── scripts/
│   │   ├── __init__.py
│   │   ├── cron_fetch.py               # Automated data collection (1015 lines)
│   │   ├── data_migration.py           # Database migration utilities (469 lines)
│   │   ├── fetch_favicons.py           # Favicon collection (141 lines)
│   │   ├── analyze_enrichment_stats.py # Enrichment analysis (399 lines)
│   │   ├── auto_fallback_enrich.py     # Automated enrichment (196 lines)
│   │   ├── explore_raw_data.py         # Data exploration (52 lines)
│   │   ├── export_db_table.py          # Database exports (59 lines)
│   │   ├── inspect_raw_data.py         # Data inspection (73 lines)
│   │   └── reset_db.py                 # Database reset (23 lines)
│   │
│   └── scripts/data_collection/        # Advanced AI-powered enrichment
│       ├── __init__.py
│       ├── enrich_with_openai.py       # AI-powered enrichment (345 lines)
│       ├── parameter_settings.py       # Enrichment parameters (149 lines)
│       ├── prepare_context.py          # Context preparation (538 lines)
│       ├── batch_enrich.py             # Batch enrichment (210 lines)
│       ├── fetch_screener.py           # Screener data collection (67 lines)
│       └── fetch_coingecko_data.py     # CoinGecko data fetching (65 lines)
│
├── 📁 Business Logic & Services
│   ├── services/
│   │   ├── db.py                       # Database operations (138 lines)
│   │   ├── db_utils.py                 # Database utilities (78 lines)
│   │   ├── metrics.py                  # Metrics calculation (326 lines)
│   │   ├── calc_metrics.py             # Advanced calculations (613 lines)
│   │   ├── tao_metrics.py              # TAO-specific metrics (197 lines)
│   │   ├── taoapp_cache.py             # TAO.app API caching (346 lines)
│   │   ├── quota_guard.py              # API quota management (310 lines)
│   │   ├── gpt_insight.py              # GPT insights service (695 lines)
│   │   ├── favicons.py                 # Favicon management (217 lines)
│   │   ├── auth.py                     # Authentication (45 lines)
│   │   └── cache.py                    # Caching utilities (158 lines)
│   │
│   └── services/bittensor/             # Bittensor SDK integration
│       ├── __init__.py
│       ├── metrics.py                  # Live subnet metrics (365 lines)
│       ├── async_metrics.py            # Async metrics collection (385 lines)
│       ├── async_utils.py              # Async utilities (8 lines)
│       ├── endpoints.py                # Network endpoints (30 lines)
│       ├── cache.py                    # SDK caching (171 lines)
│       ├── probe.py                    # Connectivity testing (222 lines)
│       ├── debug_emissions.py          # Debug utilities (52 lines)
│       └── test_spike.py               # SDK testing (59 lines)
│
├── 📁 Database & Migrations
│   ├── migrations/
│   │   ├── add_buy_signal_column.py    # Buy signal migration (30 lines)
│   │   ├── add_active_stake_ratio.py   # Stake ratio migration (57 lines)
│   │   ├── add_tao_score_column.py     # TAO score migration (38 lines)
│   │   ├── add_rank_percentages.py     # Rank percentages migration (46 lines)
│   │   └── add_investor_metrics.py     # Investor metrics migration (116 lines)
│   │
│   └── db_export/                      # Data exports
│       └── subnet_meta.csv
│
├── 📁 Testing & Documentation
│   ├── tests/
│   │   ├── README.md                   # Test documentation (95 lines)
│   │   ├── test_calculations.py        # Calculation tests (199 lines)
│   │   ├── test_subnet_detail.py       # Subnet detail tests (310 lines)
│   │   ├── test_subnet_metrics.py      # Metrics tests (127 lines)
│   │   ├── test_tao_score_v1_1.py      # TAO score tests (248 lines)
│   │   ├── test_tao_score_v1_1_simple.py # Simple TAO score tests (185 lines)
│   │   ├── CALCULATION_SUMMARY.md      # Calculation summary (188 lines)
│   │   ├── CALCULATIONS_DOCUMENTATION.md # Detailed calculations (414 lines)
│   │   └── fixtures/                   # Test data
│   │
│   └── docs/                           # Documentation
│
├── 📁 Static Assets & Templates
│   ├── static/
│   │   ├── css/
│   │   │   └── main.css                # Main CSS
│   │   ├── favicon.ico                 # Main favicon
│   │   ├── favicon.png                 # PNG favicon
│   │   ├── favicon.svg                 # SVG favicon
│   │   └── favicons/                   # Cached favicons
│   │
│   └── templates/                      # Flask templates
│       ├── index.html                  # Landing page
│       ├── about.html                  # About page
│       └── admin_login.html            # Admin login
│
├── 📁 Environment & Configuration
│   ├── venv311/                        # Python 3.11 virtual environment (active)
│   ├── venv/                           # Legacy virtual environment
│   ├── logs/                           # Application logs
│   ├── .git/                           # Git repository
│   ├── .gitignore                      # Git ignore rules
│   └── .cursor/                        # Cursor IDE config
│
└── 📁 Runtime Files
    ├── __pycache__/                    # Python cache
    └── tao.sqlite                      # Main database (1.6MB)
```

---

## Key Features

### 🎯 **Core Analytics**
- **Real-time Subnet Metrics**: Live on-chain data from Bittensor network
- **Market Cap Analytics**: TAO price and market cap tracking
- **Category Analytics**: 14 granular subnet categories with performance metrics
- **Interactive Dashboards**: Responsive Dash/Plotly visualizations
- **Buy Signal Analysis**: AI-powered investment insights with GPT integration

### 🤖 **AI-Powered Enrichment**
- **GPT-4 Classification**: Automated subnet categorization and description
- **Smart Context Detection**: Website scraping, GitHub README analysis
- **Confidence Scoring**: Provenance tracking with confidence metrics
- **Batch Processing**: Efficient bulk enrichment with progress tracking
- **Context Hash Caching**: Intelligent caching to avoid redundant processing
- **Automated Category Sync**: Automatic synchronization between enrichment and GPT insights

### 🔧 **Advanced Features**
- **Admin System**: Secure admin login with system metrics dashboard
- **API Quota Management**: Intelligent rate limiting and quota tracking
- **Caching System**: Multi-layer caching (API, database, SDK, favicons)
- **Data Migration**: Automated database schema updates
- **Export Tools**: CSV exports and data analysis utilities

### 📊 **Data Sources**
- **TAO.app API**: Subnet screener data with market metrics
- **CoinGecko API**: TAO price and market cap data
- **Bittensor SDK**: Live on-chain metrics and emissions
- **OpenAI GPT-4**: AI-powered content analysis and classification

---

## System Overview

### **Architecture**
- **Flask**: Main web server handling routing, authentication, and static assets
- **Dash**: Interactive analytics dashboard with Plotly visualizations
- **SQLite**: Lightweight database for persistent storage
- **Bittensor SDK**: Real-time blockchain data access
- **OpenAI API**: AI-powered content analysis and classification

### **Key Components**
- **Data Collection**: Automated scripts with quota management
- **AI Enrichment**: GPT-4 powered subnet classification
- **Caching**: Multi-layer caching for performance optimization
- **Authentication**: Secure admin access control
- **Monitoring**: Comprehensive logging and error handling

---

## Data Pipeline

### **Primary Data Sources**

1. **TAO.app API** (`https://api.tao.app/api/beta/subnet_screener`)
   - **Purpose**: Raw subnet data (market cap, volume, URLs, metadata)
   - **Authentication**: API key required (`TAO_APP_API_KEY`)
   - **Frequency**: Automated collection via `cron_fetch.py`
   - **Storage**: `screener_raw` table with JSON field

2. **CoinGecko API** (`https://api.coingecko.com/api/v3/`)
   - **Purpose**: TAO price and market cap data
   - **Authentication**: API key required (`COINGECKO_API_KEY`)
   - **Frequency**: Regular updates via automated collection
   - **Storage**: `coingecko` table

3. **Bittensor SDK** (Live on-chain data)
   - **Purpose**: Real-time subnet metrics, emissions, validator data
   - **Endpoints**: Multiple RPC endpoints with fallbacks
   - **Frequency**: Real-time with 5-minute caching
   - **Storage**: In-memory cache + real-time calculations

4. **OpenAI GPT-4** (`https://api.openai.com/v1/chat/completions`)
   - **Purpose**: AI-powered subnet classification and description
   - **Model**: GPT-4o (optimal balance of quality and cost)
   - **Features**: 
     - 14 granular category classification
     - Confidence scoring with provenance tracking
     - Context-aware enrichment from websites/GitHub
     - Tag normalization and deduplication
     - Real-time insights with comprehensive price momentum data (1d, 7d, 30d)
   - **Storage**: `subnet_meta` table with enriched fields

### **Database Schema**

#### **Core Tables**
- **`screener_raw`**: Raw API data with JSON field for flexibility
- **`subnet_meta`**: Enriched data with AI-generated classifications
- **`coingecko`**: TAO price and market cap history
- **`metrics_snap`**: Calculated metrics and performance data
- **`gpt_insights_new`**: AI-generated insights and buy signals

#### **Key Fields in `subnet_meta`**
- `primary_category`: 14 granular categories (LLM-Inference, Serverless-Compute, etc.)
- `confidence`: AI confidence score (0-100) with provenance tracking
- `privacy_security_flag`: Boolean for privacy/security focus
- `context_hash`: MD5 hash for change detection
- `provenance`: JSON tracking of data sources (context vs model knowledge)

#### **GPT Insights Integration**
- **Real-time Analysis**: Live insights with current market data
- **Price Momentum**: Comprehensive 1-day, 7-day, and 30-day price changes
- **Category Synchronization**: Automatic sync between enrichment and insights
- **Intelligent Caching**: Context-aware caching with automatic invalidation

### **Caching Strategy**
- **API Cache**: 1-hour TTL for external API responses
- **Database Cache**: 30-minute TTL for database queries
- **SDK Cache**: 5-minute TTL for Bittensor SDK data
- **Favicon Cache**: Persistent storage with URL mapping

---

## Setup & Installation

### **Prerequisites**
- Python 3.10+ (recommended: 3.11)
- Git
- API keys for TAO.app, CoinGecko, and OpenAI

### **1. Clone Repository**
```bash
git clone <repository-url>
cd tao-analytics
```

### **2. Create Virtual Environment**
```bash
python -m venv venv311
source venv311/bin/activate  # On Windows: venv311\Scripts\activate
```

### **3. Install Dependencies**
```bash
pip install -r requirements.txt
```

### **4. Environment Configuration**
Create a `.env` file in the root directory:
```bash
# API Keys
TAO_APP_API_KEY=your_tao_app_api_key
COINGECKO_API_KEY=your_coingecko_api_key
OPENAI_API_KEY=your_openai_api_key

# Flask Configuration
SECRET_KEY=your_secret_key_here
FLASK_ENV=development

# Admin Credentials (for admin_config.md)
ADMIN_USERNAME=admin
ADMIN_PASSWORD=secure_password
```

### **5. Initialize Database**
```bash
# The database will be created automatically on first run
# Or manually initialize:
python scripts/reset_db.py
```

### **6. Run Initial Data Collection**
```bash
# Collect initial data
python scripts/cron_fetch.py --once nightly

# Run AI enrichment (includes automatic category sync)
python scripts/data_collection/batch_enrich.py --range 1 128
```

---

## Configuration

### **Main Configuration (`config.py`)**
- **API Endpoints**: TAO.app, CoinGecko, OpenAI
- **Database**: SQLite configuration
- **Categories**: 14 granular subnet categories
- **Enrichment**: AI model settings and parameters

### **Parameter Settings (`scripts/data_collection/parameter_settings.py`)**
- **Content Limits**: Website (3000 chars), README (2000 chars)
- **API Settings**: Timeouts, retries, delays
- **Quality Thresholds**: Min context tokens (100)
- **LLM Settings**: Response limits, confidence penalties

### **Admin Configuration (`admin_config.md`)**
- **Admin Credentials**: Username and password setup
- **Security**: Session management and access control

---

## Running the App

### **Development Mode**
```bash
# Activate virtual environment
source venv311/bin/activate

# Run the application
python app.py
```

The app will automatically find an available port (5001-5005) and start the server.

### **Production Mode**
```bash
# Using gunicorn (recommended)
gunicorn -w 4 -b 0.0.0.0:5001 app:create_app()

# Using Heroku
# The Procfile is configured for Heroku deployment
```

### **Access Points**
- **Main App**: `http://localhost:5001/`
- **Dash Dashboard**: `http://localhost:5001/dash/`
- **Admin Login**: `http://localhost:5001/admin/login`
- **System Info**: `http://localhost:5001/admin/system-info` (admin only)

---

## Dash App Pages

### **1. Explorer (`/dash/explorer`)**
- **Purpose**: Main analytics dashboard
- **Features**: 
  - Real-time subnet metrics
  - Category performance analysis
  - Market cap trends
  - Interactive charts and filters

### **2. Screener (`/dash/screener`)**
- **Purpose**: Subnet screening with AI insights
- **Features**:
  - Buy Signal Analysis with GPT insights
  - Interactive scatter plots with click-to-save buy signals
  - Real-time data updates with comprehensive price momentum (1d, 7d, 30d)
  - AI-powered investment recommendations with category-aware analysis

### **3. Subnet Detail (`/dash/subnet-detail`)**
- **Purpose**: Detailed subnet analysis
- **Features**:
  - Comprehensive subnet metrics with real-time updates
  - Historical performance data with price momentum analysis
  - Validator information and network health metrics
  - AI-generated insights with category-synchronized analysis

### **4. System Info (`/dash/system-info`)**
- **Purpose**: Admin system monitoring
- **Features**:
  - Database statistics
  - API quota usage
  - Cache performance
  - System health metrics

### **5. SDK POC (`/dash/sdk-poc`)**
- **Purpose**: Bittensor SDK testing
- **Features**:
  - Live SDK connectivity testing
  - Network endpoint validation
  - Real-time data verification

---

## Database & Data Flow

### **Data Flow Overview**
```
External APIs → Raw Storage → Context Enrichment → AI Analysis → Quality Validation → Category Sync → Production Database
     ↓              ↓              ↓              ↓              ↓              ↓              ↓
TAO.app API    screener_raw   prepare_context  OpenAI GPT-4   confidence     auto-sync      subnet_meta
CoinGecko API  coingecko      web scraping     classification  validation     categories     metrics_snap
Bittensor SDK  real-time      GitHub README    confidence      provenance     GPT insights   gpt_insights
```

### **Key Database Operations**
- **Data Collection**: Automated via `cron_fetch.py`
- **Enrichment**: AI-powered via `batch_enrich.py` with automatic category sync
- **Migration**: Schema updates via migration scripts
- **Export**: Data export via `export_db_table.py`
- **Category Sync**: Automatic synchronization between enrichment and GPT insights

---

## Scripts & Automation

### **Data Collection Scripts**

#### **`cron_fetch.py`** (1015 lines)
- **Purpose**: Automated data collection with quota management
- **Features**:
  - Scheduled collection (hourly/daily)
  - Quota enforcement and tracking
  - Error handling and logging
  - Multiple data sources integration

#### **`run_heroku_cron.py`** (Convenience Script)
- **Purpose**: Run cron_fetch.py locally while targeting Heroku database
- **Usage**: `python scripts/run_heroku_cron.py --once nightly`
- **Requires**: `HEROKU_DB_URL_FOR_SCRIPT` in `.env` file
- **Scenario**: Local development → Heroku database
- **Benefits**: 
  - No manual environment variable setting
  - Clear separation between local and production targets
  - Automatic database URL loading from `.env`

#### **`scripts/data_collection/`**
- **`fetch_screener.py`**: TAO.app API data collection
- **`fetch_coingecko_data.py`**: CoinGecko price data
- **`prepare_context.py`**: Website and GitHub content scraping
- **`enrich_with_openai.py`**: AI-powered subnet classification with automatic category sync
- **`batch_enrich.py`**: Bulk enrichment with smart caching and category synchronization

### **Utility Scripts**

#### **Analysis & Monitoring**
- **`analyze_enrichment_stats.py`**: Enrichment quality analysis
- **`auto_fallback_enrich.py`**: Low-confidence subnet re-enrichment
- **`data_migration.py`**: Database migration and validation

#### **Data Management**
- **`export_db_table.py`**: Database table exports
- **`explore_raw_data.py`**: Raw data exploration
- **`inspect_raw_data.py`**: Data inspection utilities
- **`reset_db.py`**: Database reset and initialization

#### **Asset Management**
- **`fetch_favicons.py`**: Website favicon collection and caching

### **Automation Workflows**

#### **Daily Collection**
```bash
# Automated nightly collection
python scripts/cron_fetch.py --once nightly

# Followed by enrichment (includes automatic category sync)
python scripts/data_collection/batch_enrich.py --range 1 128
```

#### **Quality Assurance**
```bash
# Analyze enrichment quality
python scripts/analyze_enrichment_stats.py

# Re-enrich low-confidence subnets
python scripts/auto_fallback_enrich.py --max-subnets 10
```

---

## Data Collection & Database Storage

### **📊 Data Collection Overview**

TAO Analytics uses a modular data collection system with three main components that can be run independently or together:

| Component | Data Source | Duration | Purpose | Database Table |
|-----------|-------------|----------|---------|----------------|
| **Subnet Screener** | TAO.app API | ~30 seconds | Price, volume, market data | `screener_raw` |
| **CoinGecko** | CoinGecko API | ~5 seconds | TAO/USD price & market cap | `coingecko` |
| **SDK Snapshot** | Bittensor SDK | ~7 minutes | Network metrics, stake quality | `metrics_snap` |

### **🚀 Running Data Collection**

#### **Complete Daily Collection (Recommended)**
```bash
# Run all components together
python scripts/cron_fetch.py --once nightly
```

#### **Individual Components**
```bash
# Update only subnet screener data (price/volume)
python scripts/cron_fetch.py --once subnet

# Update only TAO/USD price
python scripts/cron_fetch.py --once coingecko

# Update only network metrics (stake quality, consensus, etc.)
python scripts/cron_fetch.py --once sdk_snapshot
```

#### **Testing & Development**
```bash
# Test with limited subnets
python scripts/cron_fetch.py --once sdk_snapshot --limit 10

# Test without quota enforcement
python scripts/cron_fetch.py --test
```

### **💾 Database Storage Architecture**

#### **Data Tables & Storage Pattern**

| Table | Component | Storage Pattern | Data Type | Example |
|-------|-----------|----------------|-----------|---------|
| `screener_raw` | Subnet Screener | **Upsert** (update existing) | Raw JSON from TAO.app | Price, volume, market cap |
| `coingecko` | CoinGecko | **New row** each time | TAO price & market cap | $324.68 USD, $2.9B market cap |
| `metrics_snap` | SDK Snapshot | **New row** each time | Calculated metrics | Stake quality, TAO score |

#### **Time Series Data Behavior**

**✅ NEW RECORDS ARE CREATED EACH TIME YOU RUN THE SCRIPT**

- **Each run creates a new timestamp** for all components
- **No data overwriting** - each run adds fresh records
- **True time series data** - track changes throughout the day
- **Database growth**: ~122 records per run (one per subnet)

#### **Example Timeline**
```bash
# Run 1: 09:00 AM
python scripts/cron_fetch.py --once nightly
# Result: 122 new metrics_snap records + 1 coingecko record + 128 screener_raw updates

# Run 2: 02:00 PM  
python scripts/cron_fetch.py --once nightly
# Result: 122 new metrics_snap records + 1 coingecko record + 128 screener_raw updates
# Total: 244 metrics_snap records for the day
```

### **🔗 Data Dependencies & Usage**

#### **How Dash Pages Use Data**

The dashboards use a **JOIN** between multiple tables:

```python
# From services/db.py - load_screener_frame()
query = select(
    # From ScreenerRaw (price/volume data)
    func.coalesce(json_field(ScreenerRaw.raw_json, 'price_tao'), 0).label('price_tao'),
    func.coalesce(json_field(ScreenerRaw.raw_json, 'market_cap_tao'), 0).label('market_cap_tao'),
    
    # From MetricsSnap (calculated metrics)
    MetricsSnap.stake_quality,
    MetricsSnap.tao_score,
    MetricsSnap.validator_util_pct,
    
    # From CoinGecko (USD conversion rate)
    # Used to convert TAO values to USD in dashboards
)
```

#### **Data Completeness by Component**

| Component | Price Data | Network Metrics | USD Conversion | Dash Impact |
|-----------|------------|-----------------|----------------|-------------|
| `subnet` only | ✅ Fresh | ❌ Stale | ❌ Stale | Partial updates |
| `coingecko` only | ❌ Stale | ❌ Stale | ✅ Fresh | USD updates only |
| `sdk_snapshot` only | ❌ Stale | ✅ Fresh | ❌ Stale | Metrics updates only |
| `nightly` | ✅ Fresh | ✅ Fresh | ✅ Fresh | Complete updates |

### **🌐 Heroku Database Integration**

#### **Local Scripts → Heroku Database**

For production deployment, run scripts locally while targeting the Heroku PostgreSQL database:

```bash
# Set Heroku database URL
export HEROKU_DATABASE_URL="postgresql://username:password@host:port/database"

# Run collection targeting Heroku database
python scripts/cron_fetch.py --once nightly
```

#### **Database Logging**

The cron script includes database logging to show which database is being targeted:

```bash
🚀 Starting cron_fetch.py - Database target: POSTGRESQL
☁️  Heroku PostgreSQL database: postgresql://...
🏁 Nightly Collection complete - ✅ SUCCESS - Database: POSTGRESQL - 3/3 successful
```

### **📈 Recommended Workflows**

#### **Daily Production Workflow**
```bash
# 1. Complete daily collection (recommended)
python scripts/cron_fetch.py --once nightly

# 2. Verify data collection
python scripts/analyze_enrichment_stats.py
```

#### **Development & Testing**
```bash
# Test individual components
python scripts/cron_fetch.py --once subnet
python scripts/cron_fetch.py --once coingecko
python scripts/cron_fetch.py --once sdk_snapshot --limit 5

# Check database stats
python -c "from services.db import get_db; from models import MetricsSnap; session = get_db(); print(f'Total records: {session.query(MetricsSnap).count()}')"
```

#### **Troubleshooting**
```bash
# Check database connection
python -c "from services.db import get_db; session = get_db(); print('Database connected successfully')"

# View recent data
python -c "from services.db import get_db; from models import MetricsSnap; session = get_db(); latest = session.query(MetricsSnap).order_by(MetricsSnap.timestamp.desc()).first(); print(f'Latest: {latest.timestamp}')"
```

### **🔧 Advanced Configuration**

#### **Environment Variables**
```bash
# Required for data collection
export TAO_APP_API_KEY="your_tao_app_api_key"
export COINGECKO_API_KEY="your_coingecko_api_key"
export OPENAI_API_KEY="your_openai_api_key"

# Database configuration
export HEROKU_DATABASE_URL="postgresql://..."  # For Heroku targeting
export DATABASE_URL="sqlite:///tao.sqlite"     # For local development
```

#### **Quota Management**
- **TAO.app API**: 1000 calls/month (tracked automatically)
- **CoinGecko API**: 10,000 calls/month (tracked automatically)
- **OpenAI API**: Pay-per-use (tracked in database)

#### **Performance Optimization**
- **Connection Pooling**: Scripts reuse database connections
- **Async Processing**: SDK metrics use async collection for speed
- **Caching**: Multi-layer caching reduces API calls
- **Batch Processing**: Efficient bulk operations

---

## Services

### **Core Services**

#### **Database Services**
- **`db.py`**: Database connection and session management
- **`db_utils.py`**: Database utility functions
- **`cache.py`**: Multi-layer caching system

#### **Metrics Services**
- **`metrics.py`**: General metrics calculations
- **`calc_metrics.py`**: Advanced financial and performance metrics
- **`tao_metrics.py`**: TAO-specific metrics and calculations

#### **API Services**
- **`taoapp_cache.py`**: TAO.app API caching and management
- **`quota_guard.py`**: API quota tracking and enforcement
- **`gpt_insight.py`**: OpenAI GPT integration for insights with comprehensive price momentum analysis

#### **Utility Services**
- **`auth.py`**: Authentication and authorization
- **`favicons.py`**: Favicon management and caching

### **Bittensor Services**

#### **`services/bittensor/`**
- **`metrics.py`**: Live subnet metrics collection
- **`async_metrics.py`**: Asynchronous metrics processing
- **`endpoints.py`**: Network endpoint management
- **`cache.py`**: SDK data caching
- **`probe.py`**: Network connectivity testing

---

## Deployment

### **Heroku Deployment**

The app is configured for Heroku deployment with automatic database switching between SQLite (development) and PostgreSQL (production).

#### **Deployment Configuration**
- **Procfile**: Gunicorn configuration for production server
- **runtime.txt**: Python version specification (3.10.14)
- **requirements.txt**: Production dependencies
- **config.py**: Automatic database URL detection

#### **Environment Variables**
Set the following environment variables in Heroku:
```bash
# Required API Keys
TAO_APP_API_KEY=your_tao_app_api_key
COINGECKO_API_KEY=your_coingecko_api_key
OPENAI_API_KEY=your_openai_api_key

# Production Settings
SECRET_KEY=your_production_secret_key
FLASK_ENV=production

# Database (automatically set by Heroku)
DATABASE_URL=postgresql://...  # Auto-provided by Heroku Postgres addon
```

#### **Database Architecture**
- **Development**: SQLite database (`tao.sqlite`) for local development
- **Production**: PostgreSQL database (auto-provided by Heroku Postgres addon)
- **Automatic Switching**: The app automatically detects `DATABASE_URL` environment variable and switches between SQLite and PostgreSQL

### **Data Collection & Automation on Heroku**

#### **Key Insight: Local Scripts → Heroku Database**
For optimal performance and cost management, run data collection scripts locally while targeting the Heroku database:

#### **Option 1: Convenience Script (Local → Heroku)**
For running scripts locally while targeting the Heroku database:

Add your Heroku database URL to `.env`:
```bash
# In your .env file
HEROKU_DB_URL_FOR_SCRIPT="postgresql://username:password@host:port/database"
```

Then use the convenience script:
```bash
# Normal development (uses local SQLite)
python scripts/cron_fetch.py --once nightly

# Local → Heroku database (uses PostgreSQL)
python scripts/run_heroku_cron.py --once nightly
```

#### **Option 2: Manual Environment Override (Local → Heroku)**
Alternative way to run scripts locally while targeting the Heroku database:

```bash
# Set Heroku database URL locally for data collection
export HEROKU_DATABASE_URL="postgresql://username:password@host:port/database"

# Run cron job locally targeting Heroku database
DATABASE_URL=$HEROKU_DATABASE_URL python scripts/cron_fetch.py --once nightly

# Run enrichment locally targeting Heroku database  
DATABASE_URL=$HEROKU_DATABASE_URL python scripts/data_collection/batch_enrich.py --range 1 128
```

#### **Option 3: Heroku Platform (Heroku → Heroku)**
For running scripts directly on Heroku (via Heroku Scheduler):

```bash
# On Heroku platform - uses DATABASE_URL automatically provided by Heroku
python scripts/cron_fetch.py --once nightly
```

#### **Why This Approach?**
- **Cost Effective**: Avoids Heroku dyno costs for heavy data collection
- **Performance**: Local execution is faster than Heroku's limited resources
- **Reliability**: Avoids Heroku's 30-minute timeout limits for long-running scripts
- **Connection Limits**: Bypasses Heroku Postgres connection limits (20 on basic plan)

#### **Heroku Scheduler Setup**
For lightweight, automated tasks on Heroku:

1. **Add Heroku Scheduler Addon**:
   ```bash
   heroku addons:create scheduler:standard
   ```

2. **Configure Scheduled Jobs**:
   ```bash
   # Open scheduler dashboard
   heroku addons:open scheduler
   ```

3. **Recommended Schedule**:
   - **Daily**: `python scripts/cron_fetch.py --once daily` (lightweight collection)
   - **Hourly**: `python scripts/cron_fetch.py --once hourly` (market data updates)

#### **Database Connection Management**
- **Connection Pooling**: Scripts are optimized to reuse database connections
- **Connection Limits**: Heroku Postgres has connection limits by plan tier:
  - Basic: 20 connections
  - Standard: 120 connections  
  - Premium: 500+ connections
- **Best Practice**: Use single engine/session per script to avoid connection exhaustion

#### **Production Data Workflow**
```bash
# 1. Heavy Data Collection (Local → Heroku)
python scripts/run_heroku_cron.py --once nightly

# 2. AI Enrichment (Local → Heroku)  
DATABASE_URL=$HEROKU_DATABASE_URL python scripts/data_collection/batch_enrich.py --range 1 128

# 3. Lightweight Updates (Heroku → Heroku)
# Configured via Heroku Scheduler addon for hourly/daily updates
# Uses: python scripts/cron_fetch.py --once nightly
```

### **Database Management**
- **Development**: SQLite database (`tao.sqlite`)
- **Production**: PostgreSQL database (Heroku Postgres addon)
- **Backups**: Regular database exports via `export_db_table.py`
- **Migrations**: Automated schema updates via migration scripts

---

## Development Notes

### **Code Quality**
- **Type Hints**: Used throughout the codebase
- **Error Handling**: Comprehensive exception handling
- **Logging**: Structured logging with file and console output
- **Documentation**: Inline documentation and docstrings

### **Performance Optimizations**
- **Caching**: Multi-layer caching for API responses and database queries
- **Async Processing**: Asynchronous operations for Bittensor SDK
- **Batch Processing**: Efficient bulk operations for enrichment
- **Connection Pooling**: Database connection optimization

### **Testing**
- **Test Suite**: Comprehensive test coverage in `tests/`
- **Calculation Tests**: Financial and metrics calculation validation
- **Integration Tests**: End-to-end functionality testing
- **Documentation**: Detailed calculation documentation

### **Monitoring**
- **Logging**: Application logs in `logs/` directory
- **Metrics**: System performance monitoring
- **Error Tracking**: Comprehensive error handling and reporting
- **Health Checks**: System health monitoring endpoints

---

## License

This project is licensed under the MIT License - see the LICENSE file for details.

---

## Support

For support and questions:
- Check the documentation in `docs/`
- Review the test suite in `tests/`
- Examine the calculation documentation in `tests/CALCULATIONS_DOCUMENTATION.md`
- Contact the development team

---

**TAO Analytics** - Production-grade analytics for the Bittensor network 🚀 