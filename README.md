# TAO Analytics

**TAO Analytics** is a production-grade analytics and intelligence dashboard for the Bittensor decentralized AI network. It provides real-time subnet metrics, market cap analytics, and deep insights, with a modern, responsive UI built using Flask and Dash.

---

## Table of Contents

- [Project Structure](#project-structure)
- [Key Features](#key-features)
- [System Overview](#system-overview)
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
│       └── system_info.py          # Admin system info
│
├── db_export/                      # Data exports
│   └── subnet_meta.csv
│
├── scripts/                        # Utility and automation scripts
│   ├── __init__.py
│   ├── dev/                        # Development tools
│   │   └── setup_bt_sdk.sh         # Bittensor SDK installation script
│   ├── bittensor/                  # Bittensor SDK scripts
│   │   ├── __init__.py
│   │   ├── bt_endpoints.py         # Network endpoint constants
│   │   ├── sdk_smoketest.py        # SDK connectivity test
│   │   └── subnet_check.py         # Subnet validation script
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
│   └── cache.py                    # Caching utilities
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
python scripts/bittensor/sdk_smoketest.py
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
- Bittensor SDK 9.7.* installed and tested
- Python 3.11 environment configured
- Live connectivity to Bittensor MAIN-NET and TEST-NET verified
- Ready to implement on-chain data collection scripts
- Network clarification: `finney` = MAIN-NET (production), `test` = TEST-NET (development)

---

## Configuration

- **config.py:** Central configuration for database, API keys, and environment settings
- **admin_config.md:** Instructions and notes for admin setup
- **runtime.txt:** Python version specification for deployment

---

## Running the App

- **Development:**
  ```bash
  python app.py
  ```
  The app will be available at `http://localhost:5001/`

- **Production (Heroku or similar):**
  - Use the provided `Procfile` for deployment
  - Ensure all environment variables are set

---

## Dash App Pages

- **Explorer (`/dash/explorer`):**
  - Main analytics dashboard
  - Features category filter, search, KPI badges, interactive charts, and subnet cards
  - Filter/search controls are sticky for easy access
  - Optimized for desktop; mobile users see a notice about best experience

- **System Info (`/dash/system-info`):**
  - Admin-only dashboard for system metrics, cache stats, and enrichment progress
  - Requires admin login

---

## Database & Data Flow

- **tao.sqlite:** Main SQLite database for subnets, enrichment, and metrics
- **db_export/subnet_meta.csv:** Exported subnet metadata for analysis or backup
- **processed_netuids.json:** Tracks processed subnets for enrichment scripts

---

## Scripts

- **scripts/**: Utility and automation scripts
  - **bittensor/**: Bittensor SDK scripts
    - `bt_endpoints.py`: Network endpoint constants
    - `sdk_smoketest.py`: Bittensor SDK connectivity test
    - `subnet_check.py`: Subnet validation and health checks
  - **data-collection/**: Advanced enrichment and data prep scripts
    - `enrich_with_openai.py`: AI-powered enrichment using OpenAI
    - `prepare_context.py`: Prepare context for enrichment
    - `batch_enrich.py`: Batch enrichment runner
    - `fetch_screener.py`: Fetch subnet screener data
    - `fetch_coingecko_data.py`: Fetch market data from CoinGecko API
    - `parameter_settings.py`: Parameter configs for enrichment
    - `processed_netuids.json`: Local tracking of processed subnets
  - **dev/**: Development tools
    - `setup_bt_sdk.sh`: Bittensor SDK installation script
  - `analyze_enrichment_stats.py`: Analyze enrichment coverage and stats
  - `auto_fallback_enrich.py`: Automated fallback enrichment
  - `fetch_favicons.py`: Download and cache favicons for subnets
  - `explore_raw_data.py`, `inspect_raw_data.py`: Data exploration utilities
  - `export_db_table.py`: Export database tables to CSV
  - `reset_db.py`: Reset or initialize the database

---

## Services

- **services/**: Modular business logic
  - `db.py`, `db_utils.py`: Database access and helpers
  - `metrics.py`, `tao_metrics.py`: Metrics calculation and aggregation
  - `favicons.py`: Favicon fetching and caching
  - `auth.py`: Admin authentication and session management
  - `cache.py`: LRU and in-memory caching utilities

---

## Static Assets

- **static/css/main.css:** Main CSS for Flask-rendered pages
- **dash_app/assets/custom.css:** Custom CSS for Dash app (explorer and system info)
- **static/favicons/**: Cached favicons for subnets
- **static/favicon.ico, static/favicon.png, static/favicon.svg:** Main application favicons
- **dash_app/assets/subnet_placeholder.svg:** Placeholder SVG for missing favicons
- **dash_app/assets/favicon.ico:** Dash app favicon

---

## Templates

- **templates/index.html:** Main landing page (Flask)
- **templates/about_placeholder.html:** About page template
- **templates/admin_login.html:** Admin login page

---

## Deployment

- **Procfile:** For Heroku or similar PaaS deployment
- **requirements.txt:** All Python dependencies (including Bittensor SDK)
- **runtime.txt:** Python version specification
- **Environment Variables:** Set `SECRET_KEY` and admin credentials as needed

---

## Development Notes

- **Bittensor Integration:** SDK is ready for on-chain data collection with proper network endpoints
- **Network Setup:** MAIN-NET (`finney`) and TEST-NET (`test`) both accessible
- **Next Steps:** Implement live subnet data fetching and real-time metrics updates from main-net
- **Mobile UX:** The app is optimized for desktop. Mobile users are shown a clear notice about best experience
- **Sticky Filters:** The filter/search controls in the explorer are sticky for usability
- **Extensibility:** The codebase is modular and can be extended with new metrics, pages, or enrichment logic
- **Testing:** Scripts and services are designed for easy testing and debugging

---

## License

This project is licensed under the MIT License. See `LICENSE` for details. 