# 🏠 PropFlux

PropFlux is a scalable real estate data extraction engine designed for resilient, multi-site scraping. Built with Scrapy and designed for easy extension to new sites.

## 🎯 Features

- **Multi-site support**: Architecture ready for scale, with high-fidelity support for Property24 and Private Property.
- **Robust scraping**: Automatic pagination, retry logic, and error handling.
- **Data normalization**: Standardizes prices, locations, and property details.
- **Deduplication**: Removes duplicate listings based on ID or URL.
- **Multiple export formats**: CSV, SQLite, and finalized JSON arrays.
- **Memory-Efficient**: Periodic flushing to disk for large-scale scraping.
- **Stealth Infrastructure**: Full proxy rotation and anti-bot bypassing (NopeCHA integration).
- **Dynamic Content Support**: Selenium-based extraction for JavaScript-heavy elements (agent details, phone numbers).

## 📊 Current Project Status (85% Complete)

PropFlux is currently in advanced development, with the core engine and most complex features fully operational.

### ✅ Completed & Production-Ready
- **Advanced Anti-Bot Bypassing**: Integrated `selenium-stealth` and NopeCHA for seamless CAPTCHA solving and browser fingerprint masking.
- **Memory-Optimized Pipeline**: Custom incremental saving system that flushes data to disk in batches, ensuring stability for 100k+ listings.
- **Intelligent Normalization**: Automated parsing of complex pricing (e.g., "POA", "Negotiable", "Auction") and unit conversion (M/K suffixes).
- **Studio Detection**: Automatically detects and flags studio apartments from descriptions and decimal bedroom counts (0.5 -> 0 Studio).
- **Stealth Proxy Logic**: Support for sessionized residential proxies with sticky session management to prevent IP blocking.
- **Streaming Export Engine**: Real-time export to JSONL with final conversion to standard JSON, CSV, and SQLite.

### 🚀 Roadmap (Remaining 15%)
- **Admin Dashboard**: Developing a React + FastAPI monitoring dashboard for real-time success tracking and job management.

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

# Skip expensive Selenium extraction (for rapid testing of Scrapy logic)
python runner.py --site privateproperty --limit 5 --skip-phone

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

## 📁 Project Structure

```
multi-site-real-estate-scraper/
├── scraper/
│   ├── spiders/
│   │   ├── base_spider.py      # Base spider with common logic
│   │   ├── property24.py       # Property24 spider
│   │   └── privateproperty.py  # Private Property spider
│   ├── settings.py             # Scrapy settings
│   └── pipelines.py            # Data processing pipelines
├── core/
│   ├── parser.py               # HTML parsing logic
│   ├── normalizer.py           # Data normalization & Studio detection
│   ├── deduplicator.py         # Duplicate removal
│   ├── exporter.py             # Export to CSV/JSON/SQLite
│   └── browser_service.py      # Selenium dynamic data extraction
├── config/
│   └── sites.yaml              # Site configurations & CSS selectors
├── chrome-profiles/            # Persistent Chrome profile (gitignored)
├── output/                     # Generated files (CSV, JSON, DB)
├── logs/                       # Log files
├── runner.py                   # Main entry point
└── requirements.txt            # Python dependencies
```

## ⚙️ Configuration

Site-specific configurations are stored in `config/sites.yaml`. Each site has:

- **Selectors**: Static CSS selectors for Scrapy
- **Dynamic Selectors**: Fields requiring browser-based extraction
- **Pagination**: URL templates and page limits
- **Rate limiting**: RPM settings and delays

## 📊 Output

The scraper generates three output formats:
- **CSV**: `output/property24_YYYYMMDD_HHMMSS.csv`
- **JSON**: `output/property24_YYYYMMDD_HHMMSS.json` (Finalized array)
- **SQLite**: `output/listings.db`

## 📝 Extracted Data

Each listing includes:

**Required fields:**
- `title`, `price`, `location`, `bedrooms`, `bathrooms`, `property_type`, `listing_url`, `description`

**Flags & Metadata:**
- `is_studio` - Boolean (Auto-detected)
- `is_auction` - Boolean (Auto-detected)
- `is_private_seller` - Boolean (Auto-detected)
- `source_site` - Origin (e.g. `property24`)
- `scraped_at` - Timestamp of extraction

**Optional fields:**
- `agent_name`, `agent_phone`, `agency_name`, `listing_id`, `date_posted`, `erf_size`, `floor_size`


---

**Built with ❤️ for reliable, scalable web scraping**
