# Setup Instructions

## Quick Setup

Run these commands to get started:

```bash
# Navigate to project directory
cd /Users/williamferns/dev/personal-projects/multi-site-real-estate-scraper

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# OPTIONAL: Setup Chrome Profile for CAPTCHA solving (NopeCHA)
# Only needed if you want to extract agent details/phone numbers
python runner.py --setup-chrome-profile

# Verification Run (Scrape 1 page with verbose logging)
python runner.py --site property24 --limit 5 --verbose
```

## Anti-Bot & Selenium Setup

PropFlux uses a generalized `BrowserService` to handle dynamically rendered content on sites like Private Property and Property24.

1. **Proxy Configuration**: Set your `STICKY_PROXY_URL` in `.env` (refer to `.env.example`).
2. **NopeCHA**: Ensure you have an active NopeCHA API key entered during `--setup-chrome-profile`.
3. **Headless Mode**: By default, Selenium runs in headless mode. Use `--verbose` or check `logs/` if you encounter timeouts.

## Monitoring the Scraper

1. **Logs**: Real-time logs are saved to `logs/{site}_{timestamp}.log`.
2. **Output**: Successfully scraped items are flushed to `output/` in batches.
3. **Deduplication**: If a URL has already been scraped, it will be skipped automatically based on the `listings.db` history.

---

✅ All core components created
✅ Configuration files ready for Property24 & Private Property
✅ BrowserService for dynamic extraction implemented
✅ Virtual environment initialized
