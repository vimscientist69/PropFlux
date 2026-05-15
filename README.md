# 🏠 PropFlux

<img width="1920" height="1080" alt="propflux-dashboard" src="https://github.com/user-attachments/assets/0273cdc9-cdf9-4245-ae72-1684326a72d4" />

PropFlux is a scalable real estate data extraction engine designed for resilient, multi-site scraping. Built with Scrapy, with Selenium + NopeCHA support for dynamic fields, and an admin dashboard that makes long-running jobs observable and controllable.

### Why clients pick this (quick pitch)
- You get a repeatable scraping pipeline: run jobs, monitor progress, and export clean results.
- Anti-bot resilience is built in: proxies, retry-aware crawling, and browser stealth/CAPTCHA solving.
- The project is operator-friendly: live logs, telemetry, termination controls, and search/exploration of results.

## 🎯 Features

- **Multi-site support**: Architecture ready for scale, with high-fidelity support for Property24 and Private Property.
- **Robust scraping**: Automatic pagination, retry logic, and error handling.
- **Data normalization**: Standardizes prices, locations, and property details.
- **Deduplication**: Removes duplicate listings based on ID or URL.
- **Multiple export formats**: CSV, SQLite, and finalized JSON arrays.
- **Memory-Efficient**: Periodic flushing to disk for large-scale scraping.
- **Stealth Infrastructure**: Full proxy rotation and anti-bot bypassing (NopeCHA integration).
- **Dynamic Content Support**: Selenium-based extraction for JavaScript-heavy elements (agent details, phone numbers).
- **Admin dashboard (monitoring + job control)**: React + FastAPI UI for telemetry, live logs, job termination, analytics, and data exploration.

## 📊 Current State
PropFlux is running as a complete scraping + data pipeline system with: incremental exports (CSV/JSON/SQLite), optional Selenium/NopeCHA dynamic extraction, and a FastAPI + React dashboard for monitoring, job lifecycle control, and analytics. Ongoing work focuses on adding new targets and improving dashboard coverage as more fields are standardized.

## Dashboard Screenshots

<img width="1859" height="992" alt="propflux-2" src="https://github.com/user-attachments/assets/e61020b1-78e3-417d-9969-040b08882828" />

<img width="1867" height="1007" alt="propflux-3" src="https://github.com/user-attachments/assets/e4cbdcf6-05ad-4980-a894-eac46bb7fe35" />

<img width="1856" height="989" alt="propflux-4" src="https://github.com/user-attachments/assets/f1ab9e11-14ab-4f06-87e3-1223793bccf0" />

<img width="1869" height="985" alt="propflux-5" src="https://github.com/user-attachments/assets/bb49e18d-2ed6-4e68-9c75-12207d1d348c" />

## 📋 Requirements

- Python 3.11+
- Chrome Browser (for Selenium-based extraction)
- See `requirements.txt` for dependencies

## 🚀 Quick Start

### 1. Setup

```bash
# Clone or navigate to project directory
cd multi-site-real-estate-scraper

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Run the Scraper

```bash
# Scrape Property24 (default settings)
python runner.py --site property24

# Scrape Private Property
python runner.py --site privateproperty

# Hard limit total listings (useful for testing)
python runner.py --site property24 --limit 10

# Skip expensive Selenium dynamic extraction (for rapid testing of Scrapy logic)
python runner.py --site privateproperty --limit 5 --skip-dynamic-fields

# Use custom URL (search results or single listing)
python runner.py --site property24 --url "https://www.property24.com/for-sale/cape-town/western-cape/432"

# Verbose logging
python runner.py --site property24 --verbose
```


## 📞 Dynamic Data Extraction (Selenium + NopeCHA)

Some sites hide agent details (names, phone numbers) behind JavaScript or CAPTCHAs. This project uses the `BrowserService` with a **persistent Chrome profile** to auto-solve CAPTCHAs via the [NopeCHA](https://nopecha.com) extension.

> **The `chrome-profiles/` directory is gitignored** — your API key and session data are never committed.

### One-Time Setup (per developer)

**Prerequisites**
- A NopeCHA API key — sign up at [nopecha.com](https://nopecha.com)
- Set it in your `.env` file: `NOPECHA_API_KEY=your_key_here`

**Run the setup command:**

```bash
python runner.py --setup-chrome-profile
```

Follow the on-screen instructions to install the extension and authenticate. After setup, all future runs will reuse this profile automatically.
## Output (where results go)
- CSV: `output/<spider>_<timestamp>.csv`
- Finalized JSON: `output/<spider>_<timestamp>.json`
- SQLite: `output/listings.db`
- Job progress snapshots: `output/job_stats/<job_id>.json`
- Logs: `logs/<site>_<job_id>.log`

## Key listing fields
- Required: `title`, `price`, `location`, `bedrooms`, `bathrooms`, `property_type`, `listing_url`, `description`
- Metadata/flags: `source_site`, `job_id`, `scraped_at`, plus `is_studio`, `is_auction`, `is_private_seller` (when detectable)
- Optional (depends on site selectors): `agent_name`, `agent_phone`, `agency_name`, `listing_id`, `date_posted`, `erf_size`, `floor_size`

## Client-Facing Walkthrough (how this delivers results)
PropFlux is the kind of scraper I build when the goal is not just “get data once”, but to create a repeatable pipeline you can operate: run jobs, monitor progress, stop bad runs, and export clean outputs for analysis or downstream systems.

### How it works
1. `runner.py` starts the scrape (Scrapy spider) and records a job in the SQLite-backed `scrape_jobs` table.
2. Spiders parse listing pages and emit raw items.
3. Pipelines normalize + deduplicate + export in batches (controlled by `EXPORT_BATCH_SIZE`).
4. For dynamic fields, `BrowserService` performs Selenium extraction using a persistent Chrome profile and NopeCHA (under `MAX_CONCURRENT_BROWSERS`, with `RETRY_TIMES`).
5. Scrapy updates lightweight progress snapshots in `output/job_stats/<job_id>.json`.
6. `api/main.py` exposes telemetry, logs, listings search, and job exports.
7. The dashboard provides an operator-friendly UI for starting/terminating jobs and exploring results.

## How I would use this on your project
If you’re hiring me for web scraping + data pipelines + browser automation, I typically apply this same structure:
- Start with site discovery and selector mapping (Scrapy + dynamic selectors).
- Implement or extend a spider and pipelines so your output schema is consistent and validated.
- Add resilience controls: retries, throttling, proxy strategy, and (when needed) Selenium extraction under a browser concurrency limit.
- Ship monitoring: job lifecycle, telemetry, and log tailing, so you can safely run long scrapes without guessing.
- Provide exports in the formats you need (CSV/JSON/SQLite) and optionally wire them to your downstream system.

## Dashboard Documentation (what to click + what to expect)
The dashboard lives in `dashboard/` and talks to the FastAPI backend.

### Start the backend
```bash
python -m uvicorn api.main:app --reload --port 8000
```

### Start the dashboard UI
```bash
cd dashboard
npm install
npm run dev
```

If your backend is not on `localhost:8000`, set:
`VITE_API_BASE_URL=http://<host>:<port>`.

### Main Control Panel
- **Target site**: choose `property24` or `privateproperty`
- **Start URL / Search query**: optional override (falls back to site defaults)
- **Skip dynamic fields**: when enabled, the scraper avoids Selenium dynamic extraction (faster; less complete)
- **Use engine settings** (default OFF): controls whether `settings_overrides` are sent to the API when starting a job.
  - When OFF: the job runs using the current defaults in `scraper/settings.py` and `config/settings.py`
  - When ON: engine sliders apply to the next job you run
- **Run job**: starts a background scrape and selects the new job in the UI
- **Terminate**: stops an active job and updates job status/termination timestamps in the database
- **Live Console**: streams the latest log lines for the selected job
- **Recent Jobs**: quick selector + job status snapshots (`job_id`, timestamps, item counts)

### Engine Settings tab (applies only when the main toggle is ON)
- Concurrency / domain (`CONCURRENT_REQUESTS_PER_DOMAIN`)
- Download delay (`DOWNLOAD_DELAY`)
- Headless mode (`HEADLESS`)
- Export batch size (`EXPORT_BATCH_SIZE`)
- Max concurrent browsers (`MAX_CONCURRENT_BROWSERS`)
- Retry times (`RETRY_TIMES`)

### Analytics + Data Explorer
- **Analytics**: charts for distribution and missing-field heatmaps (based on stored listings)
- **Data Explorer**: searchable, paginated listing grid powered by `/listings/query`

### Job History
- Filter + pagination over `/jobs/query`
- Per-job exports (CSV or prettified JSON) via `/jobs/{job_id}/export`

## API endpoints (used by the dashboard)
- `GET /` health check
- `POST /jobs/run` start a job
- `POST /jobs/{job_id}/terminate` stop a running job
- `GET /jobs/{job_id}/telemetry` progress + runtime status
- `GET /jobs/{job_id}/logs?tail=<N>` live log tail
- `GET /listings/query?limit=&offset=&site=&job_id=&q=` search + paginate listings
- `GET /jobs/{job_id}/export?format=csv|json` download results

## Extending PropFlux to new websites
To add a new target site:
1. Add site configuration in `config/sites.yaml` (selectors, pagination strategy, dynamic selectors).
2. Create a spider in `scraper/spiders/` that extends the base spider.
3. Register the spider in `runner.py` (`SPIDER_MAP`).

---
Built with ❤️ for reliable, scalable web scraping
