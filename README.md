# TAO Analytics

**Production-grade analytics and intelligence dashboard for the Bittensor decentralized AI network**

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-2.0+-green.svg)](https://flask.palletsprojects.com)
[![Dash](https://img.shields.io/badge/Dash-2.0+-orange.svg)](https://dash.plotly.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 🚀 Live Demo

**🌐 Website**: [www.taoanalytics.app](https://www.taoanalytics.app)

**📊 Features**:
- Real-time subnet analytics with 30+ metrics
- AI-powered subnet insights using GPT-4o
- Statistical correlation analysis with p-value filtering
- Interactive dashboards with live data
- Comprehensive search and filtering

---

## 📋 Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [Data Sources](#data-sources)
- [Pages & Features](#pages--features)
- [Development](#development)
- [Deployment](#deployment)
- [API Documentation](#api-documentation)

---

## Overview

TAO Analytics provides comprehensive insights into the Bittensor network through:

- **Real-time Data**: Live on-chain metrics from 120+ subnets
- **AI Intelligence**: GPT-4o powered subnet analysis and insights
- **Statistical Analysis**: Correlation analysis with statistical rigor
- **Market Analytics**: Price tracking, volume analysis, and market cap metrics
- **Interactive Dashboards**: Responsive visualizations with Plotly/Dash
- **Advanced Search**: Unified search across all subnet data

### Tech Stack

- **Backend**: Flask + Dash + SQLite/PostgreSQL
- **Frontend**: HTML5 + CSS3 + JavaScript + Plotly
- **AI**: OpenAI GPT-4o for subnet insights and analysis
- **Data**: TAO.app API + CoinGecko + Bittensor SDK
- **Caching**: Redis + Multi-layer fallback system

---

## Key Features

### 🤖 AI-Powered Intelligence
- **GPT-4o Subnet Insights**: AI-powered analysis and recommendations for individual subnets
- **Smart Classification**: 14 granular subnet categories with confidence scoring
- **Context-Aware Enrichment**: Website scraping and GitHub README analysis
- **Real-time Insights**: Live buy signals and investment recommendations

### 📊 Statistical Analytics
- **Correlation Analysis**: Statistical correlation matrices with p-value filtering
- **Outlier Detection**: Z-score analysis and statistical significance testing
- **Network-wide Analysis**: Cross-subnet metric comparisons
- **Time Series Analysis**: Historical correlation tracking

### 📈 Comprehensive Analytics
- **30+ Metrics**: Stake quality, market cap, volume, validator utilization
- **Real-time Updates**: 5-minute refresh cycles with live data
- **Interactive Charts**: Scatter plots, heatmaps, and trend analysis
- **Category Analysis**: Performance comparison across 14 subnet categories

### ⚡ Performance & Reliability
- **Multi-layer Caching**: Redis with graceful fallback to SimpleCache
- **Rate Limiting**: Intelligent API quota management
- **Error Handling**: Comprehensive logging and graceful degradation
- **Mobile Responsive**: Optimized for all device sizes

### 🔍 Advanced Search & Discovery
- **Unified Search**: Consistent search across all pages
- **International Support**: Greek character and special character handling
- **Real-time Results**: Instant search with debounced API calls
- **Smart Filtering**: Category-aware search with subnet details

---

## Quick Start

### Prerequisites
- Python 3.10+ (recommended: 3.11)
- API keys for [TAO.app](https://tao.app), [CoinGecko](https://coingecko.com), and [OpenAI](https://openai.com)

### Installation

```bash
# 1. Clone repository
git clone <repository-url>
cd tao-analytics

# 2. Create virtual environment
python -m venv venv311
source venv311/bin/activate  # Windows: venv311\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env with your API keys
```

### Environment Configuration

Create a `.env` file:
```bash
# Required API Keys
TAO_APP_API_KEY=your_tao_app_api_key
COINGECKO_API_KEY=your_coingecko_api_key
OPENAI_API_KEY=your_openai_api_key

# Flask Configuration
SECRET_KEY=your_secret_key_here
FLASK_ENV=development

# Optional: Redis for production caching
REDIS_URL=redis://localhost:6379

# Admin credentials
ADMIN_USERNAME=admin
ADMIN_PASSWORD=secure_password
```

### Run the Application

```bash
# Start the application
python app.py

# Access points:
# Main app: http://localhost:5001/
# Dashboard: http://localhost:5001/dash/
# Admin: http://localhost:5001/admin/login
```

### Initial Data Setup

```bash
# Collect initial data
python scripts/cron_fetch.py --once nightly

# Run AI enrichment
python scripts/data_collection/batch_enrich.py --range 1 128
```

---

## Architecture

### System Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   External      │    │   Data          │    │   Web           │
│   APIs          │    │   Processing    │    │   Interface     │
├─────────────────┤    ├─────────────────┤    ├─────────────────┤
│ • TAO.app API   │───▶│ • Flask Server  │───▶│ • Landing Page  │
│ • CoinGecko     │    │ • Dash App      │    │ • Explorer      │
│ • Bittensor SDK │    │ • AI Services   │    │ • Screener      │
│ • OpenAI APIs   │    │ • Cache Layer   │    │ • Insights      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │   Database      │
                       ├─────────────────┤
                       │ • SQLite/PostgreSQL │
                       │ • Redis Cache   │
                       │ • Migrations    │
                       └─────────────────┘
```

### Core Components

| Component | Purpose | Technology |
|-----------|---------|------------|
| **Flask Server** | Main web server, routing, auth | Flask + Talisman |
| **Dash App** | Interactive analytics dashboard | Dash + Plotly |
| **Data Collection** | Automated API data gathering | Python + Async |
| **AI Services** | GPT-powered subnet analysis | OpenAI APIs |
| **Statistical Analysis** | Correlation and statistical analysis | SciPy + Pandas |
| **Database** | Data storage and caching | SQLite/PostgreSQL + Redis |
| **Search** | Unified search functionality | SQL + JavaScript |

---

## Data Sources

### Primary APIs

| API | Purpose | Frequency | Data |
|-----|---------|-----------|------|
| **TAO.app** | Subnet screener data | Hourly | Price, volume, market cap |
| **CoinGecko** | TAO price & market cap | Hourly | USD conversion rates |
| **Bittensor SDK** | Live on-chain metrics | 5 min | Stake quality, emissions |
| **OpenAI** | AI subnet analysis & insights | On-demand | Classification, insights |

### Data Flow

```
External APIs → Raw Storage → AI Enrichment → Analysis → Dashboard
     ↓              ↓              ↓              ↓           ↓
TAO.app API    screener_raw   OpenAI APIs    metrics_snap   Dash App
CoinGecko      coingecko      classification  gpt_insights   Real-time
Bittensor SDK  real-time      insights        correlation    Updates
```

### Database Schema

| Table | Purpose | Key Fields |
|-------|---------|------------|
| `screener_raw` | Raw API data | JSON field with price/volume |
| `subnet_meta` | Enriched data | AI classifications, categories |
| `coingecko` | Price history | TAO/USD rates |
| `metrics_snap` | Calculated metrics | TAO scores, stake quality |
| `gpt_insights_new` | AI insights | Buy signals, subnet analysis |

---

## Pages & Features

### 🏠 Landing Page (`/`)
- **Network Overview**: Live statistics and key metrics
- **GPT Insights**: AI-powered network analysis
- **TradingView Chart**: Live TAO price chart
- **Quick Navigation**: Direct access to all features

### 🔍 Explorer (`/dash/explorer`)
- **Subnet Discovery**: Browse all 120+ subnets
- **Category Filtering**: Filter by 14 subnet categories
- **Interactive Charts**: Market cap and performance visualizations
- **Search & Sort**: Advanced filtering and sorting options

### 📊 Screener (`/dash/screener`)
- **Buy Signal Analysis**: AI-powered investment insights
- **Interactive Scatter Plots**: Click-to-save buy signals
- **Momentum Analysis**: 1d, 7d, 30d price changes
- **Real-time Updates**: Live data with timestamp tracking

### 🧠 Insights (`/dash/insights`)
- **Network Trends**: Time series analytics
- **Performance Tracking**: Subnet improvement monitoring
- **Category Analysis**: Cross-category performance comparison
- **Custom Metrics**: Flexible trend analysis

### 📈 Correlation (`/dash/correlation`)
- **Statistical Analysis**: Comprehensive correlation matrices
- **P-value Filtering**: Statistical significance testing
- **Outlier Detection**: Z-score analysis
- **Network-wide Analysis**: Cross-subnet metric correlations
- **Time Series**: Historical correlation tracking

### 🔧 Subnet Detail (`/dash/subnet-detail`)
- **Comprehensive Metrics**: All subnet data in one view
- **Historical Performance**: Price and metric history
- **Validator Information**: Network health metrics
- **AI Insights**: GPT-generated subnet analysis

### ⚙️ System Info (`/dash/system-info`)
- **Admin Dashboard**: System performance monitoring
- **Database Statistics**: Data quality and completeness
- **API Usage**: Quota tracking and management
- **Cache Performance**: Redis and fallback metrics

---

## Development

### Project Structure

```
tao-analytics/
├── 📁 Core Application
│   ├── app.py                    # Main Flask application
│   ├── config.py                 # Configuration settings
│   ├── models.py                 # Database models
│   └── requirements.txt          # Python dependencies
│
├── 📁 Dash Dashboard
│   ├── dash_app/
│   │   ├── __init__.py           # Dash app initialization
│   │   ├── pages/                # Dashboard pages
│   │   └── assets/               # CSS and static files
│
├── 📁 Data Collection
│   ├── scripts/
│   │   ├── cron_fetch.py         # Automated data collection
│   │   └── data_collection/      # AI enrichment scripts
│
├── 📁 Services
│   ├── services/
│   │   ├── db.py                 # Database operations
│   │   ├── gpt_insight.py        # AI insights service
│   │   ├── correlation_analysis.py # Statistical analysis
│   │   └── bittensor/            # SDK integration
│
├── 📁 Templates & Static
│   ├── templates/                # Flask templates
│   └── static/                   # CSS, images, favicons
│
└── 📁 Testing & Docs
    ├── tests/                    # Test suite
    └── docs/                     # Documentation
```

### Key Scripts

| Script | Purpose | Usage |
|--------|---------|-------|
| `cron_fetch.py` | Data collection | `python scripts/cron_fetch.py --once nightly` |
| `batch_enrich.py` | AI enrichment | `python scripts/data_collection/batch_enrich.py --range 1 128` |
| `analyze_enrichment_stats.py` | Quality analysis | `python scripts/analyze_enrichment_stats.py` |
| `export_db_table.py` | Data export | `python scripts/export_db_table.py subnet_meta` |

### Development Workflow

```bash
# 1. Set up development environment
python -m venv venv311
source venv311/bin/activate
pip install -r requirements.txt

# 2. Configure environment variables
cp .env.example .env
# Edit .env with your API keys

# 3. Initialize database
python scripts/reset_db.py

# 4. Collect initial data
python scripts/cron_fetch.py --once nightly

# 5. Run AI enrichment
python scripts/data_collection/batch_enrich.py --range 1 128

# 6. Start development server
python app.py
```

### Testing

```bash
# Run all tests
python -m pytest tests/

# Run specific test categories
python -m pytest tests/test_calculations.py
python -m pytest tests/test_subnet_metrics.py

# View test documentation
cat tests/README.md
```

---

## Deployment

### Heroku Deployment

The app is configured for Heroku with automatic database switching.

#### Environment Variables

Set in Heroku dashboard:
```bash
# Required API Keys
TAO_APP_API_KEY=your_tao_app_api_key
COINGECKO_API_KEY=your_coingecko_api_key
OPENAI_API_KEY=your_openai_api_key

# Production Settings
SECRET_KEY=your_production_secret_key
FLASK_ENV=production

# Optional: Redis for caching
REDIS_URL=redis://...  # Auto-provided by Heroku Redis addon
```

#### Database Configuration

- **Development**: SQLite (`tao.sqlite`)
- **Production**: PostgreSQL (auto-provided by Heroku Postgres)
- **Automatic Switching**: Detects `DATABASE_URL` environment variable

#### Data Collection Strategy

**Recommended**: Run data collection locally targeting Heroku database

```bash
# Add to .env
HEROKU_DB_URL_FOR_SCRIPT="postgresql://username:password@host:port/database"

# Run collection targeting Heroku
python scripts/run_heroku_cron.py --once nightly
```

**Alternative**: Use Heroku Scheduler for lightweight updates

```bash
# Configure in Heroku Scheduler addon
python scripts/cron_fetch.py --once daily
```

### Production Considerations

- **Connection Limits**: Heroku Postgres has connection limits by plan
- **Timeout Limits**: Heroku has 30-minute timeout for long-running scripts
- **Cost Optimization**: Run heavy data collection locally, lightweight updates on Heroku
- **Caching**: Use Redis for production caching with graceful fallback

---

## API Documentation

### Internal APIs

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/search` | GET | Subnet search API |
| `/sitemap.xml` | GET | SEO sitemap |
| `/robots.txt` | GET | SEO robots file |

### External API Integration

| Service | Rate Limits | Usage |
|---------|-------------|-------|
| **TAO.app** | 1000 calls/month | Subnet screener data |
| **CoinGecko** | 10,000 calls/month | Price and market cap |
| **OpenAI** | Pay-per-use | AI subnet analysis and insights |
| **Bittensor SDK** | No limits | Live on-chain metrics |

### Caching Strategy

| Layer | TTL | Purpose |
|-------|-----|---------|
| **Redis** | 5 minutes | Production caching |
| **API Cache** | 1 hour | External API responses |
| **Database Cache** | 30 minutes | Query results |
| **Analysis Cache** | 24 hours | GPT insights and correlation analysis |

---

## Support & Resources

### Documentation
- **Test Suite**: `tests/README.md`
- **Calculations**: `tests/CALCULATIONS_DOCUMENTATION.md`
- **Development Plan**: `PLAN.md`

### Monitoring
- **Application Logs**: `logs/` directory
- **System Health**: `/dash/system-info` (admin only)
- **Database Stats**: Available in admin dashboard

### Community
- **LinkedIn**: [Glenn Landgren](https://www.linkedin.com/in/glenn-landgren/?originalSubdomain=se)
- **X (Twitter)**: [@_landgren_](https://x.com/_landgren_)

---

## License

This project is licensed under the MIT License - see the LICENSE file for details.

---

**TAO Analytics** - Production-grade analytics for the Bittensor network 🚀

*Built with ❤️ for the decentralized AI community* 