# TAO Analytics

**TAO Analytics** is a production-grade analytics and intelligence dashboard for the Bittensor decentralized AI network. It provides real-time subnet metrics, market cap analytics, and deep insights, with a modern, responsive UI built using Flask and Dash.

---

## Table of Contents

- [Project Structure](#project-structure)
- [Key Features](#key-features)
- [System Overview](#system-overview)
- [Setup & Installation](#setup--installation)
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
- [Development > SDK setup (macOS M-series)](#development--sdk-setup-macos-m-series)

---

## Project Structure

```
tao-analytics/
│
├── app.py
├── config.py
├── models.py
├── requirements.txt
├── Procfile
├── PLAN.md
├── README.md
├── =2.9
├── tao.sqlite
├── processed_netuids.json
├── admin_config.md
│
├── dash_app/
│   ├── __init__.py
│   ├── assets/
│   │   ├── custom.css
│   │   └── subnet_placeholder.svg
│   └── pages/
│       ├── explorer.py
│       └── system_info.py
│
├── db_export/
│   └── subnet_meta.csv
│
├── scripts/
│   ├── __init__.py
│   ├── fetch_favicons.py
│   ├── analyze_enrichment_stats.py
│   ├── auto_fallback_enrich.py
│   ├── explore_raw_data.py
│   ├── export_db_table.py
│   ├── inspect_raw_data.py
│   ├── reset_db.py
│   └── data-collection/
│       ├── __init__.py
│       ├── enrich_with_openai.py
│       ├── parameter_settings.py
│       ├── prepare_context.py
│       ├── batch_enrich.py
│       ├── fetch_screener.py
│       └── processed_netuids.json
│
├── services/
│   ├── db_utils.py
│   ├── metrics.py
│   ├── tao_metrics.py
│   ├── db.py
│   ├── favicons.py
│   ├── auth.py
│   └── cache.py
│
├── static/
│   ├── css/
│   │   └── main.css
│   └── favicons/
│       └── [many .ico files]
│
├── templates/
│   ├── index.html
│   └── admin_login.html
│
├── venv/
├── .git/
├── .gitignore
└── .cursor/
```

---

## Key Features

- **Modern Analytics Dashboard:** Real-time subnet and category analytics for Bittensor.
- **Responsive UI:** Optimized for desktop, with mobile support and a clear notice for best experience.
- **Admin System Info:** Secure admin login and system metrics dashboard.
- **Data Enrichment:** Automated scripts for AI-powered subnet enrichment and provenance tracking.
- **Caching & Performance:** LRU caching, favicon caching, and efficient data management.
- **Customizable:** Modular codebase for easy extension and maintenance.

---

## System Overview

- **Flask** serves as the main web server, handling routing, authentication, and static assets.
- **Dash** (by Plotly) powers the interactive analytics dashboard at `/dash/`.
- **SQLite** is used for persistent storage of subnet and enrichment data.
- **Scripts** automate data collection, enrichment, and export.
- **Services** provide modular business logic for metrics, caching, authentication, and more.

---

## Setup & Installation

1. **Clone the repository:**
   ```bash
   git clone <repo-url>
   cd tao-analytics
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set environment variables (optional):**
   - `SECRET_KEY` for Flask session security.
   - Admin credentials as needed (see `admin_config.md`).

---

## Configuration

- **config.py:** Central configuration for database, API keys, and environment settings.
- **admin_config.md:** Instructions and notes for admin setup.

---

## Running the App

- **Development:**
  ```bash
  python app.py
  ```
  The app will be available at `http://localhost:5001/`.

- **Production (Heroku or similar):**
  - Use the provided `Procfile` for deployment.
  - Ensure all environment variables are set.

---

## Dash App Pages

- **Explorer (`/dash/explorer`):**
  - Main analytics dashboard.
  - Features category filter, search, KPI badges, interactive charts, and subnet cards.
  - Filter/search controls are sticky for easy access.
  - Optimized for desktop; mobile users see a notice about best experience.

- **System Info (`/dash/system-info`):**
  - Admin-only dashboard for system metrics, cache stats, and enrichment progress.
  - Requires admin login.

---

## Database & Data Flow

- **tao.sqlite:** Main SQLite database for subnets, enrichment, and metrics.
- **db_export/subnet_meta.csv:** Exported subnet metadata for analysis or backup.
- **processed_netuids.json:** Tracks processed subnets for enrichment scripts.

---

## Scripts

- **scripts/**: Utility and automation scripts.
  - `analyze_enrichment_stats.py`: Analyze enrichment coverage and stats.
  - `auto_fallback_enrich.py`: Automated fallback enrichment.
  - `fetch_favicons.py`: Download and cache favicons for subnets.
  - `explore_raw_data.py`, `inspect_raw_data.py`: Data exploration utilities.
  - `export_db_table.py`: Export database tables to CSV.
  - `reset_db.py`: Reset or initialize the database.
  - **data-collection/**: Advanced enrichment and data prep scripts.
    - `enrich_with_openai.py`: AI-powered enrichment using OpenAI.
    - `prepare_context.py`: Prepare context for enrichment.
    - `batch_enrich.py`: Batch enrichment runner.
    - `fetch_screener.py`: Fetch subnet screener data.
    - `parameter_settings.py`: Parameter configs for enrichment.

---

## Services

- **services/**: Modular business logic.
  - `db.py`, `db_utils.py`: Database access and helpers.
  - `metrics.py`, `tao_metrics.py`: Metrics calculation and aggregation.
  - `favicons.py`: Favicon fetching and caching.
  - `auth.py`: Admin authentication and session management.
  - `cache.py`: LRU and in-memory caching utilities.

---

## Static Assets

- **static/css/main.css:** Main CSS for Flask-rendered pages.
- **dash_app/assets/custom.css:** Custom CSS for Dash app (explorer and system info).
- **static/favicons/**: Cached favicons for subnets.
- **dash_app/assets/subnet_placeholder.svg:** Placeholder SVG for missing favicons.

---

## Templates

- **templates/index.html:** Main landing page (Flask).
- **templates/admin_login.html:** Admin login page.

---

## Deployment

- **Procfile:** For Heroku or similar PaaS deployment.
- **requirements.txt:** All Python dependencies.
- **Environment Variables:** Set `SECRET_KEY` and admin credentials as needed.

---

## Development Notes

- **Mobile UX:** The app is optimized for desktop. Mobile users are shown a clear notice about best experience.
- **Sticky Filters:** The filter/search controls in the explorer are sticky for usability.
- **Extensibility:** The codebase is modular and can be extended with new metrics, pages, or enrichment logic.
- **Testing:** Scripts and services are designed for easy testing and debugging.

---

## License

This project is licensed under the MIT License. See `LICENSE` for details.

---

## Development > SDK setup (macOS M-series)

To reliably install the Bittensor SDK on Apple Silicon (macOS 14/15):

```
xcode-select --install               # ensure Command Line Tools
brew install openssl pkg-config      # headers for any native wheels
python3.10 -m venv bt_venv           # use 3.10 for maximum wheel coverage *
source bt_venv/bin/activate
python -m pip install -U pip wheel setuptools
pip install "grpcio>=1.73.0" "grpcio-tools>=1.73.0"
pip install "bittensor>=9.7.0"
```

* Python 3.10 still has the widest wheel support across the py-crypto stack. Python 3.11+ should also work today (grpc 1.73 ships wheels for 3.11 arm64), but 3.10 is a guaranteed "happy path".

To run the SDK smoke-test:

```
python scripts/data_sources/sdk_smoketest.py
```

Expected output:
```
{
  'network': 'finney',
  'chain_endpoint': 'wss://entrypoint-finney.opentensor.ai:443',
  'current_block': 1623456,
  'finalized_block': 1623452
}
```

---

**For further details, see inline code comments and the `PLAN.md` for roadmap and design notes.** 