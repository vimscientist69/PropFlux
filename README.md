# 🏠 Multi-Site Real Estate Scraper

A production-ready, scalable web scraping system for extracting structured real estate listings from multiple websites. Built with Scrapy and designed for easy extension to new sites.

## 🎯 Features

- **Multi-site support**: Currently supports Property24 and Private Property (easily extensible)
- **Robust scraping**: Automatic pagination, retry logic, and error handling
- **Data normalization**: Standardizes prices, locations, and property details
- **Deduplication**: Removes duplicate listings based on ID or URL
- **Multiple export formats**: CSV, JSON, and SQLite database
- **Configurable**: YAML-based configuration for easy site addition
- **Production-ready**: Comprehensive logging, caching, and rate limiting

## 📋 Requirements

- Python 3.11+
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
# Scrape Property24
python runner.py --site property24

# Scrape Private Property
python runner.py --site privateproperty

# Use custom URL (search results or single listing)
python runner.py --site property24 --url "https://www.property24.com/for-sale/cape-town/western-cape/432"

# Scrape a single listing directly
python runner.py --site property24 --url "https://www.property24.com/for-sale/diep-river/cape-town/western-cape/10195/116918754"

# Limit pages
python runner.py --site property24 --max-pages 5

# Verbose logging
python runner.py --site property24 --verbose
```

## 📞 Phone Number Retrieval (NopeCHA CAPTCHA Solver)

Some sites (e.g. Property24) hide agent phone numbers behind a CAPTCHA. This project uses the [NopeCHA](https://nopecha.com) browser extension with a **persistent Chrome profile** to auto-solve CAPTCHAs via Selenium.

> **The `chrome-profiles/` directory is gitignored** — your API key and session data are never committed.

### One-Time Setup (per developer)

**Prerequisites**
- A NopeCHA API key — sign up at [nopecha.com](https://nopecha.com)
- Set it in your `.env` file: `NOPECHA_API_KEY=your_key_here`

**Run the setup command:**

```bash
python runner.py --setup-chrome-profile
```

This opens a Chrome window with a dedicated profile and prints these instructions:

```
============================================================
 NopeCHA Chrome Profile Setup
============================================================

A Chrome window is opening with a dedicated profile.
Please follow these steps in the browser:

  STEP 1 — Install the NopeCHA extension:
    https://chromewebstore.google.com/detail/nopecha-captcha-solver/...

  STEP 2 — Authenticate with your API key:
    https://nopecha.com/setup#YOUR_API_KEY_HERE

  STEP 3 — Once done, close the browser window.
============================================================
```

After setup, the profile is saved to `chrome-profiles/nopecha-profile/`. All future scraper runs reuse this profile — **no re-authentication needed**.

### How It Works

| Step | What happens |
|------|--------------|
| `--setup-chrome-profile` | Opens Chrome, developer installs extension + enters API key once |
| Normal scrape run | Selenium reuses the saved profile; NopeCHA is already active |
| CAPTCHA encountered | NopeCHA auto-solves it in the background; phone number is revealed |

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
│   ├── normalizer.py           # Data normalization
│   ├── deduplicator.py         # Duplicate removal
│   ├── exporter.py             # Export to CSV/JSON/SQLite
│   └── phone_service.py        # Selenium + NopeCHA phone retrieval
├── config/
│   └── sites.yaml              # Site configurations
├── chrome-profiles/            # Persistent Chrome profile (gitignored)
├── output/                     # Generated files (CSV, JSON, DB)
├── logs/                       # Log files
├── runner.py                   # Main entry point
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

## ⚙️ Configuration

Site-specific configurations are stored in `config/sites.yaml`. Each site has:

- **Selectors**: CSS selectors for extracting data
- **Pagination**: Settings for navigating pages
- **Rate limiting**: Delays between requests

### Adding a New Site

1. Add configuration to `config/sites.yaml`:

```yaml
sites:
  newsite:
    name: "New Site"
    base_url: "https://www.newsite.com"
    start_urls:
      - "https://www.newsite.com/listings"
    selectors:
      listing_links: ".listing a::attr(href)"
      title: "h1.title::text"
      price: ".price::text"
      # ... more selectors
```

2. Create spider in `scraper/spiders/newsite.py`:

```python
from .base_spider import BaseRealEstateSpider

class NewSiteSpider(BaseRealEstateSpider):
    name = 'newsite'
    site_key = 'newsite'
```

3. Update `runner.py` to include the new spider in `SPIDER_MAP`

## 📊 Output

The scraper generates three output formats:

### CSV
```
output/property24_20260216_143000.csv
```

### JSON
```
output/property24_20260216_143000.json
```

### SQLite
```
output/listings.db
```

## 📝 Extracted Data

Each listing includes:

**Required fields:**
- `title` - Property title
- `price` - Numeric price
- `location` - Standardized location
- `bedrooms` - Number of bedrooms
- `bathrooms` - Number of bathrooms
- `property_type` - Type (House, Apartment, etc.)
- `listing_url` - URL to listing
- `description` - Property description

**Optional fields:**
- `agent_name` - Agent name
- `agent_phone` - Contact number
- `listing_id` - Unique listing ID
- `date_posted` - Posting date

**Metadata:**
- `source_site` - Which site it was scraped from
- `scraped_at` - Timestamp of scraping

## 🔧 Advanced Usage

### Custom Settings

Override Scrapy settings in spider classes:

```python
class MySpider(BaseRealEstateSpider):
    custom_settings = {
        'DOWNLOAD_DELAY': 2,
        'CONCURRENT_REQUESTS': 4,
    }
```

### Logging

Logs are saved to `logs/scraper_YYYY-MM-DD.log` with 7-day retention.

## 🛡️ Best Practices

- **Respect robots.txt**: Enabled by default
- **Rate limiting**: 1-second delay between requests
- **Caching**: HTTP cache enabled to reduce server load
- **Retries**: Automatic retry on failures (3 attempts)
- **User agent**: Identifies as a legitimate browser

## 🧪 Testing

Before scraping large datasets:

1. Test with `--max-pages 1` to verify selectors
2. Check output files for data quality
3. Review logs for errors

## 📈 Performance

- **Concurrent requests**: 8 global, 4 per domain
- **Auto-throttle**: Adjusts speed based on server response
- **HTTP caching**: Reduces redundant requests
- **Efficient deduplication**: In-memory tracking

## 🐛 Troubleshooting

### No data extracted
- Check CSS selectors in `config/sites.yaml`
- Verify site structure hasn't changed
- Use `--verbose` flag for detailed logs

### Rate limiting errors (429)
- Increase `DOWNLOAD_DELAY` in settings
- Reduce `CONCURRENT_REQUESTS`

### Missing dependencies
```bash
pip install -r requirements.txt --upgrade
```

## 📚 Dependencies

- **Scrapy**: Web scraping framework
- **Pandas**: Data processing and export
- **PyYAML**: Configuration management
- **Loguru**: Advanced logging
- **Playwright**: JavaScript rendering (optional)

## 🎯 Use Cases

This scraper is ideal for:

- Real estate data aggregation
- Market research and analysis
- Lead generation
- Price monitoring
- Property comparison tools

## 💼 Portfolio Quality

This project demonstrates:

- **Scalable architecture**: Easy to add new sites
- **Production practices**: Logging, error handling, retries
- **Clean code**: Modular design with separation of concerns
- **Reliability**: Robust against failures and edge cases
- **Documentation**: Comprehensive README and code comments

## 📄 License

This project is for educational and portfolio purposes. Always respect website terms of service and robots.txt when scraping.

## 🤝 Contributing

To add a new site:
1. Update `config/sites.yaml`
2. Create spider class
3. Test thoroughly
4. Update documentation

## 📞 Support

For issues or questions, please check:
- Log files in `logs/`
- Scrapy documentation: https://docs.scrapy.org/
- Project structure and comments

---

**Built with ❤️ for reliable, scalable web scraping**
