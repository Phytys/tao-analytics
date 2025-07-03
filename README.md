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

# Run AI enrichment (optional)
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
  - Interactive scatter plots
  - Real-time data updates
  - AI-powered investment recommendations

### **3. Subnet Detail (`/dash/subnet-detail`)**
- **Purpose**: Detailed subnet analysis
- **Features**:
  - Comprehensive subnet metrics
  - Historical performance data
  - Validator information
  - AI-generated insights

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
External APIs → Raw Storage → Context Enrichment → AI Analysis → Quality Validation → Production Database
     ↓              ↓              ↓              ↓              ↓              ↓
TAO.app API    screener_raw   prepare_context  OpenAI GPT-4   confidence     subnet_meta
CoinGecko API  coingecko      web scraping     classification  validation     metrics_snap
Bittensor SDK  real-time      GitHub README    confidence      provenance     gpt_insights
```

### **Key Database Operations**
- **Data Collection**: Automated via `cron_fetch.py`
- **Enrichment**: AI-powered via `batch_enrich.py`
- **Migration**: Schema updates via migration scripts
- **Export**: Data export via `export_db_table.py`

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

#### **`scripts/data_collection/`**
- **`fetch_screener.py`**: TAO.app API data collection
- **`fetch_coingecko_data.py`**: CoinGecko price data
- **`prepare_context.py`**: Website and GitHub content scraping
- **`enrich_with_openai.py`**: AI-powered subnet classification
- **`batch_enrich.py`**: Bulk enrichment with smart caching

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

# Followed by enrichment (if needed)
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
- **`gpt_insight.py`**: OpenAI GPT integration for insights

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
The app is configured for Heroku deployment with:
- **Procfile**: Gunicorn configuration
- **runtime.txt**: Python version specification
- **requirements.txt**: Dependencies

### **Environment Variables**
Set the following environment variables in production:
```bash
TAO_APP_API_KEY=your_tao_app_api_key
COINGECKO_API_KEY=your_coingecko_api_key
OPENAI_API_KEY=your_openai_api_key
SECRET_KEY=your_production_secret_key
FLASK_ENV=production
```

### **Database Management**
- **Development**: SQLite database (`tao.sqlite`)
- **Production**: Consider PostgreSQL for scalability
- **Backups**: Regular database exports via `export_db_table.py`

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