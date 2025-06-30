# TAO Analytics

**TAO Analytics** is a production-grade analytics and intelligence dashboard for the Bittensor decentralized AI network. It provides real-time subnet metrics, market cap analytics, and deep insights, with a modern, responsive UI built using Flask and Dash.

---

## Table of Contents

- [Project Structure](#project-structure)
- [Key Features](#key-features)
- [System Overview](#system-overview)
- [Data Pipeline & Storage](#data-pipeline--storage)
- [APIs & External Services](#apis--external-services)
- [Setup & Installation](#setup--installation)
- [Bittensor SDK Setup](#bittensor-sdk-setup)
- [Configuration](#configuration)
- [Running the App](#running-the-app)
- [Dash App Pages](#dash-app-pages)
- [Database & Data Flow](#database--data-flow)
- [Scripts](#scripts)
- [Services](#services)
- [Static Assets](#static-assets)
- [Templates](#templates)
- [Deployment](#deployment)
- [Development Notes](#development-notes)
- [License](#license)

---

## Project Structure

```
tao-analytics/
│
├── app.py                          # Main Flask application
├── config.py                       # Configuration settings
├── models.py                       # Database models
├── requirements.txt                # Python dependencies (includes Bittensor SDK)
├── runtime.txt                     # Python version specification (3.10.14)
├── Procfile                        # Heroku deployment config
├── PLAN.md                         # Development roadmap
├── README.md                       # This file
├── =2.9                           # Version file
├── tao.sqlite                      # Main SQLite database
├── processed_netuids.json          # Enrichment tracking
├── admin_config.md                 # Admin setup instructions
│
├── dash_app/                       # Dash analytics dashboard
│   ├── __init__.py
│   ├── assets/
│   │   ├── custom.css              # Dash app styling
│   │   ├── favicon.ico             # Dash app favicon
│   │   └── subnet_placeholder.svg  # Placeholder image
│   └── pages/
│       ├── explorer.py             # Main analytics page
│       ├── subnet_detail.py        # Subnet detail page
│       ├── sdk_poc.py              # Bittensor SDK proof-of-concept
│       └── system_info.py          # Admin system info
│
├── db_export/                      # Data exports
│   └── subnet_meta.csv
│
├── scripts/                        # Utility and automation scripts
│   ├── __init__.py
│   ├── data-collection/            # Advanced data collection
│   │   ├── __init__.py
│   │   ├── enrich_with_openai.py   # AI-powered enrichment
│   │   ├── parameter_settings.py   # Enrichment parameters
│   │   ├── prepare_context.py      # Context preparation
│   │   ├── batch_enrich.py         # Batch enrichment
│   │   ├── fetch_screener.py       # Screener data collection
│   │   ├── fetch_coingecko_data.py # CoinGecko data fetching
│   │   └── processed_netuids.json  # Local enrichment tracking
│   ├── fetch_favicons.py           # Favicon collection
│   ├── analyze_enrichment_stats.py # Enrichment analysis
│   ├── auto_fallback_enrich.py     # Automated enrichment
│   ├── explore_raw_data.py         # Data exploration
│   ├── export_db_table.py          # Database exports
│   ├── inspect_raw_data.py         # Data inspection
│   └── reset_db.py                 # Database reset
│
├── services/                       # Business logic modules
│   ├── db_utils.py                 # Database utilities
│   ├── metrics.py                  # Metrics calculation
│   ├── tao_metrics.py              # TAO-specific metrics
│   ├── db.py                       # Database operations
│   ├── favicons.py                 # Favicon management
│   ├── auth.py                     # Authentication
│   ├── cache.py                    # Caching utilities
│   └── bittensor/                  # Bittensor SDK integration
│       ├── __init__.py
│       ├── metrics.py              # Live subnet metrics
│       ├── endpoints.py            # Network endpoints
│       ├── cache.py                # SDK caching
│       ├── probe.py                # Network connectivity
│       ├── debug_emissions.py      # Emission debugging
│       ├── debug_hyperparams.py    # Hyperparameter debugging
│       ├── debug_metagraph.py      # Metagraph debugging
│       └── test_spike.py           # SDK testing
│
├── static/                         # Static assets
│   ├── css/
│   │   └── main.css                # Main CSS
│   ├── favicon.ico                 # Main favicon
│   ├── favicon.png                 # PNG favicon
│   ├── favicon.svg                 # SVG favicon
│   └── favicons/                   # Cached favicons
│
├── templates/                      # Flask templates
│   ├── index.html                  # Landing page
│   ├── about_placeholder.html      # About page template
│   └── admin_login.html            # Admin login
│
├── tests/                          # Test suite
├── venv311/                        # Python 3.11 virtual environment (active)
├── venv/                           # Legacy virtual environment
├── .git/                           # Git repository
├── .gitignore                      # Git ignore rules
└── .cursor/                        # Cursor IDE config
```

---

## Key Features

- **Modern Analytics Dashboard:** Real-time subnet and category analytics for Bittensor
- **Bittensor SDK Integration:** Live on-chain data collection and analysis
- **AI-Powered Enrichment:** Automated subnet classification and description using GPT-4
- **Responsive UI:** Optimized for desktop with mobile support
- **Admin System Info:** Secure admin login and system metrics dashboard
- **Data Enrichment:** Automated scripts for AI-powered subnet enrichment
- **Caching & Performance:** LRU caching, favicon caching, and efficient data management
- **Customizable:** Modular codebase for easy extension and maintenance

---

## System Overview

- **Flask** serves as the main web server, handling routing, authentication, and static assets
- **Dash** (by Plotly) powers the interactive analytics dashboard at `/dash/`
- **Bittensor SDK** provides live on-chain data access and network metrics
- **SQLite** is used for persistent storage of subnet and enrichment data
- **Scripts** automate data collection, enrichment, and export
- **Services** provide modular business logic for metrics, caching, authentication, and more

---

## Data Pipeline & Storage

### Database Schema

The application uses SQLite with three main tables:

#### `screener_raw` - Raw API Data
- `netuid` (Primary Key): Subnet identifier
- `raw_json` (JSON): Complete raw data from tao.app API
- `fetched_at` (DateTime): When data was last fetched
- `updated_at` (DateTime): Last update timestamp

#### `subnet_meta` - Enriched Subnet Data
- `netuid` (Primary Key): Subnet identifier
- `subnet_name` (String): Human-readable subnet name
- `tagline` (String): Concise description (≤15 words)
- `what_it_does` (Text): Comprehensive explanation (≤100 words)
- `primary_use_case` (Text): Specific use case (≤50 words)
- `key_technical_features` (Text): Technical capabilities (≤75 words)
- `primary_category` (String): Granular category classification
- `category_suggestion` (Text): LLM suggestions for new categories
- `secondary_tags` (Text): CSV string of normalized tags
- `confidence` (Float): AI confidence score (0-100)
- `context_hash` (String): MD5 hash of context for change detection
- `context_tokens` (Integer): Available context token count
- `provenance` (Text): JSON tracking data sources
- `privacy_security_flag` (Boolean): Privacy/security focus indicator
- `favicon_url` (String): Cached favicon URL
- `last_enriched_at` (DateTime): Last AI enrichment timestamp
- `updated_at` (DateTime): Last update timestamp

#### `coingecko` - TAO Price Data
- `id` (Primary Key): Auto-incrementing ID
- `price_usd` (Float): TAO price in USD
- `market_cap_usd` (Float): Total TAO market cap
- `fetched_at` (DateTime): When data was fetched

### Data Flow

1. **Data Collection** (`scripts/data-collection/`)
   - `fetch_screener.py`: Fetches raw subnet data from tao.app API
   - `fetch_coingecko_data.py`: Fetches TAO price/market cap from CoinGecko
   - `fetch_favicons.py`: Collects and caches subnet favicons

2. **AI Enrichment** (`scripts/data-collection/`)
   - `enrich_with_openai.py`: Uses GPT-4 to classify and describe subnets
   - `prepare_context.py`: Prepares context from websites/GitHub for LLM
   - `batch_enrich.py`: Batch processing for multiple subnets

3. **Data Processing** (`services/`)
   - `db.py`: Database operations and query building
   - `tao_metrics.py`: Network overview and performance metrics
   - `cache.py`: LRU caching for API responses and database queries

4. **Live SDK Data** (`services/bittensor/`)
   - `metrics.py`: Real-time subnet metrics from Bittensor SDK
   - `probe.py`: Network connectivity testing
   - `cache.py`: SDK data caching

### Caching Strategy

- **API Cache**: 1-hour TTL for external API responses
- **Database Cache**: 30-minute TTL for database queries
- **SDK Cache**: 5-minute TTL for Bittensor SDK data
- **Favicon Cache**: Persistent storage with URL mapping

---

## APIs & External Services

### Primary Data Sources

1. **tao.app API** (`https://api.tao.app/api/beta/subnet_screener`)
   - **Purpose**: Raw subnet data (market cap, volume, URLs)
   - **Authentication**: API key required (`TAO_APP_API_KEY`)
   - **Frequency**: Manual/automated collection
   - **Data**: Market metrics, GitHub repos, websites

2. **CoinGecko API** (`https://api.coingecko.com/api/v3/`)
   - **Purpose**: TAO price and market cap data
   - **Authentication**: API key required (`COINGECKO_API_KEY`)
   - **Frequency**: Regular updates
   - **Data**: Current TAO price, total market cap

3. **Bittensor SDK** (Live on-chain data)
   - **Purpose**: Real-time subnet metrics and emissions
   - **Endpoints**: Multiple RPC endpoints with fallbacks
   - **Frequency**: Real-time (with caching)
   - **Data**: Stake distribution, emissions, consensus, trust scores

### Enrichment Services

4. **OpenAI GPT-4** (`https://api.openai.com/v1/chat/completions`)
   - **Purpose**: AI-powered subnet classification and description
   - **Authentication**: API key required (`OPENAI_API_KEY`)
   - **Model**: GPT-4o (optimal balance of quality and cost)
   - **Features**: 
     - Granular category classification
     - Confidence scoring with provenance tracking
     - Context-aware enrichment
     - Tag normalization and deduplication

### Web Scraping

5. **Subnet Websites & GitHub**
   - **Purpose**: Context collection for AI enrichment
   - **Tools**: BeautifulSoup4, httpx, fake-useragent
   - **Data**: README files, website content, project descriptions
   - **Processing**: TF-IDF analysis, token counting, context preparation

---

## Setup & Installation

1. **Clone the repository:**
```bash
   git clone <repo-url>
   cd tao-analytics
```

2. **Create and activate a virtual environment:**
```bash
   python3.11 -m venv venv311
   source venv311/bin/activate
   ```

3. **Install dependencies:**
```bash
   pip install -r requirements.txt
   ```

4. **Set environment variables:**
   - `TAO_APP_API_KEY` - tao.app API key for subnet data
   - `OPENAI_API_KEY` - OpenAI API key for AI enrichment
   - `COINGECKO_API_KEY` - CoinGecko API key for price data
   - `SECRET_KEY` - Flask session security (optional)

---

## Bittensor SDK Setup

The project includes the Bittensor SDK for live on-chain data collection. The SDK is already configured in `requirements.txt` with the proper dependency order to avoid compilation issues.

### Quick Setup
```bash
# Use the provided setup script
bash scripts/dev/setup_bt_sdk.sh

# Or manually install
source venv311/bin/activate
pip install "grpcio>=1.73.0" "grpcio-tools>=1.73.0"
pip install "bittensor>=9.7.0" rich
```

### Test SDK Installation
```bash
source venv311/bin/activate
python services/bittensor/test_spike.py
```

Expected output:
```
✅ MAIN-NET (Production) connectivity successful!
🌐 Endpoint: wss://entrypoint-finney.opentensor.ai:443
📦 Current Block: 5,852,786
🧠 Root Subnet Neurons: 64

✅ TEST-NET (Development) connectivity successful!
🌐 Endpoint: wss://test.finney.opentensor.ai:443
📦 Current Block: 4,827,443
🧠 Root Subnet Neurons: 128
```

**Note**: `finney` is the MAIN-NET (production), not a test network!

### Status: ✅ Ready for On-Chain Data Collection

---

## Configuration

### Primary Categories

The system uses 14 granular categories for subnet classification:

1. **LLM-Inference** - AI text generation and language model services
2. **LLM-Training / Fine-tune** - Training and fine-tuning large language models
3. **Data-Feeds & Oracles** - Real-time data feeds and blockchain oracles
4. **Serverless-Compute** - GPU computing power and model deployment
5. **AI-Verification & Trust** - AI verification, zero-knowledge proofs, and trust systems
6. **Confidential-Compute** - Secure and private AI execution
7. **Hashrate-Mining (BTC / PoW)** - Bitcoin mining and proof-of-work services
8. **Finance-Trading & Forecasting** - Financial trading and prediction services
9. **Security & Auditing** - Security analysis and auditing services
10. **Privacy / Anonymity** - Privacy-focused AI and anonymity services
11. **Media-Vision / 3-D** - Computer vision, 3D modeling, and media AI
12. **Science-Research (Non-financial)** - Scientific research and non-financial AI
13. **Consumer-AI & Games** - Consumer AI applications and gaming
14. **Dev-Tooling** - Developer tools, SDKs, and validator utilities

### Enrichment Settings

- **Model**: GPT-4o (optimal balance of quality and cost)
- **Max Tokens**: Configurable per field type
- **Confidence Thresholds**: Automatic confidence scoring
- **Provenance Tracking**: Context vs model knowledge tracking
- **Category Re-ask**: Fallback for better classification accuracy

---

## Running the App

### Development Mode
```bash
python app.py
```
Access at: `http://localhost:5001`

### Production Mode
```bash
gunicorn app:create_app
```

### Data Collection Scripts

```bash
# Fetch latest subnet data
python scripts/data-collection/fetch_screener.py

# Fetch TAO price data
python scripts/data-collection/fetch_coingecko_data.py

# Enrich a specific subnet
python scripts/data-collection/enrich_with_openai.py --netuid 64

# Enrich all subnets
python scripts/data-collection/enrich_with_openai.py

# Collect favicons
python scripts/fetch_favicons.py
```

---

## Dash App Pages

### `/dash/explorer` - Main Analytics Dashboard
- **Purpose**: Browse and compare subnets
- **Features**: 
  - Category filtering and search
  - Market cap and flow metrics
  - AI confidence indicators
  - Quick start guide
  - Interactive charts
  - Subnet cards with detailed information

### `/dash/subnet-detail` - Subnet Detail Page
- **Purpose**: Deep dive into individual subnets
- **Features**:
  - Comprehensive subnet information
  - Links to website and GitHub
  - Future: Detailed metrics, validator performance, historical data

### `/dash/sdk-poc` - Bittensor SDK Proof of Concept
- **Purpose**: Test live on-chain data integration
- **Features**:
  - Real-time subnet metrics
  - Stake distribution analysis
  - Emission split visualization
  - Rolling window calculations
  - Interactive charts and gauges

### `/dash/system-info` - Admin System Info
- **Purpose**: Development and monitoring tools
- **Access**: Admin authentication required
- **Features**: System metrics, cache statistics, database info

---

## Database & Data Flow

### Query Architecture

The application uses SQLAlchemy ORM with database-agnostic JSON extraction:

```python
# Base query with JSON field extraction
query = select(
    SubnetMeta,
    func.coalesce(json_field(ScreenerRaw.raw_json, 'market_cap_tao'), 0).label('mcap_tao'),
    func.coalesce(json_field(ScreenerRaw.raw_json, 'net_volume_tao_24h'), 0).label('flow_24h'),
    json_field(ScreenerRaw.raw_json, 'github_repo').label('github_url'),
    json_field(ScreenerRaw.raw_json, 'subnet_url').label('website_url')
).select_from(
    SubnetMeta.__table__.outerjoin(ScreenerRaw.__table__, SubnetMeta.netuid == ScreenerRaw.netuid)
)
```

### Data Processing Pipeline

1. **Raw Data Ingestion**: tao.app API → `screener_raw` table
2. **AI Enrichment**: Website/GitHub scraping → GPT-4 analysis → `subnet_meta` table
3. **Price Data**: CoinGecko API → `coingecko` table
4. **Live Metrics**: Bittensor SDK → Real-time calculations
5. **Caching**: LRU cache for performance optimization
6. **Display**: Dash dashboard with interactive visualizations

---

## Scripts

### Data Collection
- `fetch_screener.py` - Fetch raw subnet data from tao.app
- `fetch_coingecko_data.py` - Fetch TAO price and market cap
- `fetch_favicons.py` - Collect and cache subnet favicons

### AI Enrichment
- `enrich_with_openai.py` - AI-powered subnet classification
- `prepare_context.py` - Context preparation for LLM
- `batch_enrich.py` - Batch processing for multiple subnets
- `auto_fallback_enrich.py` - Automated enrichment with fallbacks

### Analysis & Utilities
- `analyze_enrichment_stats.py` - Enrichment quality analysis
- `explore_raw_data.py` - Data exploration and debugging
- `export_db_table.py` - Database export utilities
- `inspect_raw_data.py` - Raw data inspection
- `reset_db.py` - Database reset utilities

---

## Services

### Core Services
- `tao_metrics.py` - Network overview and performance metrics
- `db.py` - Database operations and query building
- `cache.py` - LRU caching for API responses and database queries
- `auth.py` - Admin authentication and session management
- `favicons.py` - Favicon collection and caching

### Bittensor Services
- `bittensor/metrics.py` - Live subnet metrics from SDK
- `bittensor/endpoints.py` - Network endpoint management
- `bittensor/cache.py` - SDK data caching
- `bittensor/probe.py` - Network connectivity testing
- `bittensor/debug_*.py` - Various debugging utilities

### Utility Services
- `db_utils.py` - Database-agnostic utilities
- `metrics.py` - General metrics calculation

---

## Static Assets

### CSS Architecture
- `main.css` - Tesla-inspired design system
- Responsive grid layouts
- Error handling UI components
- Interactive hover states
- Mobile-first responsive design

### Favicon System
- Automatic favicon collection from subnet websites
- Caching system for performance
- Fallback to placeholder images
- Multiple format support (ICO, PNG, SVG)

---

## Templates

### Flask Templates
- `index.html` - Landing page with network overview
- `about_placeholder.html` - About page template
- `admin_login.html` - Admin authentication

### Error Handling
- Graceful data loading failures
- User-friendly error messages
- Retry mechanisms
- Fallback content display

---

## Deployment

### Heroku Deployment
- **Buildpack**: Python 3.10.14
- **Process**: Gunicorn web server
- **Database**: SQLite (can be upgraded to PostgreSQL)
- **Environment**: Production-ready with proper logging

### Environment Variables
```bash
TAO_APP_API_KEY=your_tao_app_key
OPENAI_API_KEY=your_openai_key
COINGECKO_API_KEY=your_coingecko_key
SECRET_KEY=your_flask_secret_key
```

### Performance Optimization
- LRU caching for API responses and database queries
- Favicon caching for faster page loads
- Database query optimization with proper indexing
- Static asset compression and caching

---

## Development Notes

### Current Development Status

**Sprint 3 - SDK Exploration Spike** (In Progress)
- ✅ Bittensor SDK integration with live metrics
- ✅ SDK PoC dashboard page
- ✅ Network endpoint management with fallbacks
- ✅ Real-time subnet metrics calculation
- ✅ Emission split analysis and visualization
- 🔄 SDK connectivity testing and validation
- 🔄 Performance optimization for live data

### Recent Improvements

1. **Error Handling Enhancement**
   - Graceful handling of network data failures
   - User-friendly error messages with retry options
   - Conditional rendering based on data availability

2. **SDK Integration**
   - Comprehensive Bittensor SDK integration
   - Live subnet metrics and emissions analysis
   - Rolling window calculations for stability
   - Multiple RPC endpoint support with fallbacks

3. **Code Organization**
   - Moved Bittensor utilities from scripts to services
   - Improved modular architecture
   - Better separation of concerns

4. **UI Improvements**
   - Enhanced error states and responsive design
   - Improved subnet card styling
   - Better visual hierarchy and user experience

### Next Steps

1. **Sprint 4 - Subnet Detail Page Enhancement**
   - Integrate live SDK data into detail pages
   - Add historical metrics and charts
   - Implement validator performance tracking

2. **Sprint 5 - Conditional SDK Integration**
   - Evaluate SDK performance and reliability
   - Implement fallback to API data when needed
   - Optimize caching strategies

3. **Sprint 6 - TVI / Validator Hub**
   - Build validator intelligence scoring
   - Create validator ranking system
   - Implement staking recommendations

---

## License

This project is licensed under the MIT License - see the LICENSE file for details. 