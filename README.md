# TAO Analytics: Subnet Data Collection & Enrichment Pipeline

## Project Overview

This project provides a robust pipeline for collecting, enriching, and analyzing data about Bittensor subnets. It fetches raw subnet data, scrapes additional context from websites and GitHub, and uses OpenAI's GPT-4 to generate structured insights, storing everything in a local SQLite database.

---

## Project Structure

```
tao-analytics/
│
├── config.py
├── models.py
├── requirements.txt
├── tao.sqlite
├── db_export/
│   ├── subnet_meta.csv
│   ├── screener_raw.csv
│   └── parsed_subnets.csv
├── scripts/
│   ├── __init__.py
│   ├── data-collection/
│   │   ├── __init__.py
│   │   ├── fetch_screener.py
│   │   ├── prepare_context.py
│   │   ├── enrich_with_openai.py
│   │   └── contexts/
│   │       ├── 1.json
│   │       ├── 19.json
│   │       └── 64.json
│   ├── inspect_raw_data.py
│   ├── explore_raw_data.py
│   ├── export_db_table.py
│   └── reset_db.py
└── venv/
```

---

## Data Pipeline

1. **Fetch Screener Data**
   - `scripts/data-collection/fetch_screener.py`
   - Downloads subnet data from the TAO API and stores it in the `screener_raw` table in `tao.sqlite`.
   - Updates the `subnet_meta` table with subnet names and resets LLM fields if names change.

2. **Prepare Context**
   - `scripts/data-collection/prepare_context.py`
   - For each subnet, gathers:
     - Subnet number and name
     - Website URL and GitHub repo (from screener)
     - Scraped website content (if available)
     - Scraped GitHub README (if available)
   - Cleans and truncates content, estimates token count, and saves context as JSON in `scripts/data-collection/contexts/`.

3. **Enrich with OpenAI**
   - `scripts/data-collection/enrich_with_openai.py`
   - Loads context (from JSON or directly from DB), sends it to OpenAI's GPT-4, and parses the structured response.
   - Updates the `subnet_meta` table with LLM-generated fields: tagline, what_it_does, category, tags, confidence, and timestamp.

4. **Explore and Export Data**
   - `scripts/inspect_raw_data.py`, `scripts/explore_raw_data.py`, `scripts/export_db_table.py`
   - Tools for inspecting, parsing, and exporting data from the database to CSV for further analysis.

5. **Database Reset**
   - `scripts/reset_db.py`
   - Drops and recreates all tables in `tao.sqlite` using the latest schema.

---

## Database Schema

- **screener_raw**: Stores raw JSON data for each subnet.
- **subnet_meta**: Stores subnet name and LLM-enriched fields (tagline, what_it_does, category, tags, confidence, last_enriched_at).

See `models.py` for full schema details.

---

## Setup & Usage

### 1. Install Dependencies

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment

Create a `.env` file in the project root with your API keys:

```
TAO_APP_API_KEY=your-tao-api-key
OPENAI_API_KEY=your-openai-api-key
```

### 3. Initialize Database

```bash
python scripts/reset_db.py
```

### 4. Fetch Subnet Data

```bash
python scripts/data-collection/fetch_screener.py
```

### 5. Prepare Context

For a single subnet:
```bash
python scripts/data-collection/prepare_context.py --netuid 1
```
For all subnets:
```bash
python scripts/data-collection/prepare_context.py
```

### 6. Enrich with OpenAI

For a single subnet:
```bash
python scripts/data-collection/enrich_with_openai.py --netuid 1
```
For all subnets:
```bash
python scripts/data-collection/enrich_with_openai.py
```

### 7. Export Data

List tables:
```bash
python scripts/export_db_table.py --list
```
Export a table:
```bash
python scripts/export_db_table.py --table subnet_meta
```

---

## Example Context JSON

See `scripts/data-collection/contexts/1.json` for an example of the context sent to OpenAI.

---

## Notes

- The pipeline is designed to be Heroku-friendly (no browser scraping, lightweight dependencies).
- All context and enrichment steps are logged for transparency and debugging.
- You can inspect and explore the raw and enriched data using the provided scripts.

---

## License

MIT 