# TAO Analytics

**TAO Analytics** is a production-grade analytics and intelligence dashboard for the Bittensor decentralized AI network. It provides real-time subnet metrics, market cap analytics, and deep insights, with a modern, responsive UI built using Flask and Dash.

---

## Table of Contents

- [Project Structure](#project-structure)
- [Key Features](#key-features)
- [System Overview](#system-overview)
- [Data Pipeline](#data-pipeline)
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
│       ├── system_info.py          # Admin system info
│       ├── subnet_detail.py        # Subnet detail page
│       └── sdk_poc.py              # Bittensor SDK proof of concept
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
│       ├── probe.py                # Connectivity testing
│       ├── debug_*.py              # Debug utilities
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
- **AI-Powered Enrichment:** GPT-4 powered subnet classification and description
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

## Data Pipeline

### Primary Data Sources

1. **tao.app API** (`https://api.tao.app/api/beta/subnet_screener`)
   - **Purpose**: Raw subnet data (market cap, volume, URLs)
   - **Authentication**: API key required (`TAO_APP_API_KEY`)
   - **Frequency**: Manual/automated collection via `fetch_screener.py`
   - **Storage**: `screener_raw` table with JSON field

2. **CoinGecko API** (`https://api.coingecko.com/api/v3/`)
   - **Purpose**: TAO price and market cap data
   - **Authentication**: API key required (`COINGECKO_API_KEY`)
   - **Frequency**: Regular updates via `fetch_coingecko_data.py`
   - **Storage**: `coingecko` table

3. **Bittensor SDK** (Live on-chain data)
   - **Purpose**: Real-time subnet metrics and emissions
   - **Endpoints**: Multiple RPC endpoints with fallbacks
   - **Frequency**: Real-time (with 5-minute caching)
   - **Storage**: In-memory cache + real-time calculations

4. **OpenAI GPT-4** (`https://api.openai.com/v1/chat/completions`)
   - **Purpose**: AI-powered subnet classification and description
   - **Model**: GPT-4o (optimal balance of quality and cost)
   - **Features**: 
     - Granular category classification (14 categories)
     - Confidence scoring with provenance tracking
     - Context-aware enrichment from websites/GitHub
     - Tag normalization and deduplication
   - **Storage**: `subnet_meta` table with enriched fields

### Database Schema

#### Core Tables
- **`screener_raw`**: Raw API data with JSON field for flexibility
- **`subnet_meta`**: Enriched data with AI-generated classifications
- **`coingecko`**: TAO price and market cap history

#### Key Fields in `subnet_meta`
- `primary_category`: 14 granular categories (LLM-Inference, Serverless-Compute, etc.)
- `confidence`: AI confidence score (0-100) with provenance tracking
- `privacy_security_flag`: Boolean for privacy/security focus
- `context_hash`: MD5 hash for change detection
- `provenance`: JSON tracking of data sources (context vs model knowledge)

### Caching Strategy
- **API Cache**: 1-hour TTL for external API responses
- **Database Cache**: 30-minute TTL for database queries
- **SDK Cache**: 5-minute TTL for Bittensor SDK data
- **Favicon Cache**: Persistent storage with URL mapping

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

4. **Set environment variables (optional):**
   - `SECRET_KEY` for Flask session security
   - `TAO_APP_API_KEY` for tao.app API access
   - `OPENAI_API_KEY` for AI enrichment
   - `COINGECKO_API_KEY` for price data
   - Admin credentials as needed (see `admin_config.md`)

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

### Environment Variables
```bash
# Required for full functionality
TAO_APP_API_KEY=your_tao_app_key
OPENAI_API_KEY=your_openai_key
COINGECKO_API_KEY=your_coingecko_key

# Optional
SECRET_KEY=your_flask_secret_key
```

### Primary Categories
The system defines 14 granular categories for subnet classification, with 13 currently active in the database:
- LLM-Inference
- LLM-Training / Fine-tune
- Data-Feeds & Oracles
- Serverless-Compute
- AI-Verification & Trust
- Confidential-Compute *(defined but not yet used)*
- Hashrate-Mining (BTC / PoW)
- Finance-Trading & Forecasting
- Security & Auditing
- Privacy / Anonymity
- Media-Vision / 3-D
- Science-Research (Non-financial)
- Consumer-AI & Games
- Dev-Tooling

*Note: The dropdown and charts dynamically show only categories that have subnets classified with them. Currently 13 categories are active.*

---

## Running the App

### Development Mode
```bash
source venv311/bin/activate
python app.py
```

The app will be available at `http://localhost:5001`

### Production Mode
```bash
# For Heroku deployment
gunicorn app:create_app()
```

---

## Dash App Pages

### `/dash/explorer` - Main Analytics Page
- Browse and filter subnets by category
- Search functionality with multiple field matching
- Interactive charts and visualizations
- Quick Start guide for new users
- Confidence scores and tooltips

### `/dash/subnet-detail` - Subnet Detail Page
- Deep dive into individual subnet data
- Links to website and GitHub
- Basic metrics and descriptions
- Future: Historical data and validator performance

### `/dash/sdk-poc` - SDK Proof of Concept
- Live on-chain data from Bittensor SDK
- Real-time subnet metrics (stake, emissions, consensus)
- Interactive charts and visualizations
- Performance testing and validation

### `/dash/system-info` - Admin System Info
- Secure admin access required
- System metrics and performance data
- Cache statistics and database info
- Development tools and debugging

---

## Database & Data Flow

### Data Collection Process
1. **Raw Data Collection**: `fetch_screener.py` collects data from tao.app API
2. **Price Data**: `fetch_coingecko_data.py` updates TAO price and market cap
3. **AI Enrichment**: `enrich_with_openai.py` processes subnets with GPT-4
4. **Live Metrics**: Bittensor SDK provides real-time on-chain data
5. **Caching**: Multi-layer caching optimizes performance

### Data Enrichment Pipeline
1. **Context Preparation**: Gather website and GitHub data
2. **LLM Processing**: GPT-4 classification and description
3. **Quality Scoring**: Confidence and provenance tracking
4. **Storage**: Save enriched data to `subnet_meta` table

### Performance Optimization
- **LRU Caching**: Reduces API calls and database queries
- **JSON Field Extraction**: Database-agnostic JSON handling
- **Connection Pooling**: Efficient database connections
- **Static Asset Caching**: Favicon and CSS optimization

---

## Scripts

### Data Collection Scripts
- `fetch_screener.py`: Collect raw subnet data from tao.app
- `fetch_coingecko_data.py`: Update TAO price and market cap
- `fetch_favicons.py`: Collect and cache subnet favicons

### Enrichment Scripts
- `enrich_with_openai.py`: AI-powered subnet enrichment
- `batch_enrich.py`: Process multiple subnets
- `auto_fallback_enrich.py`: Automated enrichment with fallbacks
- `analyze_enrichment_stats.py`: Analyze enrichment quality

### Utility Scripts
- `export_db_table.py`: Export data to CSV
- `explore_raw_data.py`: Data exploration and analysis
- `inspect_raw_data.py`: Raw data inspection
- `reset_db.py`: Database reset utility

---

## Services

### Core Services
- **`tao_metrics.py`**: Network overview and subnet performance metrics
- **`db.py`**: Database operations and query optimization
- **`cache.py`**: LRU caching with TTL support
- **`auth.py`**: Admin authentication and session management
- **`favicons.py`**: Favicon management and caching

### Bittensor SDK Services
- **`bittensor/metrics.py`**: Live subnet metrics calculation
- **`bittensor/endpoints.py`**: Network endpoint management
- **`bittensor/cache.py`**: SDK-specific caching
- **`bittensor/probe.py`**: Connectivity testing and validation

### Utility Services
- **`db_utils.py`**: Database-agnostic utilities
- **`metrics.py`**: General metrics calculation

---

## Static Assets

### CSS Styling
- **`main.css`**: Tesla-inspired design with modern aesthetics
- **`custom.css`**: Dash app specific styling
- Responsive design for mobile and desktop

### Favicons
- Automated favicon collection and caching
- Fallback to placeholder images
- Optimized for performance

---

## Templates

### Flask Templates
- **`index.html`**: Landing page with network overview
- **`about_placeholder.html`**: About page template
- **`admin_login.html`**: Admin authentication page

### Error Handling
- Graceful handling of data loading failures
- User-friendly error messages
- Retry functionality for failed requests

---

## Deployment

### Heroku Deployment
```bash
# Procfile configuration
web: gunicorn app:create_app()

# Runtime specification
python-3.10.14
```

### Environment Setup
- Python 3.10.14 for Heroku compatibility
- Pre-built `grpcio` wheels to avoid compilation issues
- Environment variables for API keys and secrets

### Performance Considerations
- Database query optimization
- Static asset compression
- Cache warming strategies
- Connection pooling

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

### Technical Architecture

#### Data Pipeline
- Multi-source data collection with redundancy
- AI-powered enrichment with quality scoring
- Real-time on-chain data integration
- Comprehensive caching strategy

#### Performance Optimization
- Database query optimization with JSON fields
- Multi-layer caching (API, DB, SDK, static assets)
- Connection pooling and resource management
- Static asset compression and caching

#### Scalability Considerations
- SQLite to PostgreSQL migration path
- API rate limiting and respect
- SDK connection pooling
- Cache memory usage optimization

---

## License

This project is licensed under the MIT License - see the LICENSE file for details. 