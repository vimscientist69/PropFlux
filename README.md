# 🏠 Multi-Site Real Estate Scraper (MVP)

A production-style web scraping system built in Python for extracting, normalizing, and exporting structured real estate listing data from multiple websites.

This project demonstrates a reusable and scalable scraping architecture suitable for real-world data collection workflows.

---

## 🎯 Project Overview

This scraper is designed to collect property listing data from real estate websites and output clean, structured datasets ready for analysis or integration.

The system supports:

- Multi-site scraping (2 sites supported in MVP)
- Pagination and detail page extraction
- Data normalization and deduplication
- Structured export to CSV and JSON
- Logging and retry handling for reliability

The architecture is config-driven, making it easy to extend to additional websites with minimal code changes.

---

## ⚙️ Features

### ✔️ Scraping Capabilities
- Extracts listing data from multiple real estate websites
- Handles pagination automatically
- Visits individual listing pages for detailed data

### ✔️ Data Processing
- Normalizes fields (price, location, bedrooms, etc.)
- Removes duplicates based on listing ID or URL
- Validates required fields

### ✔️ Output
- CSV export
- JSON export
- Optional SQLite database support

### ✔️ Reliability
- Logging of successful and failed URLs
- Retry logic for failed requests
- Fault-tolerant execution (continues on errors)

### ✔️ Extensibility
- Config-driven selectors for each site
- Easily add new sites via YAML configuration
- Modular architecture for parsing and pipelines

---

## 📦 Example Output Fields

Each property listing includes:

- `title`
- `price`
- `location`
- `bedrooms`
- `bathrooms`
- `property_type`
- `listing_url`
- `description`

Optional fields (when available):

- `agent_name`
- `agent_phone`
- `listing_id`
- `date_posted`

---

## 🧱 Project Structure

```

scraper-platform/
│
├── scraper/
│   ├── spiders/
│   │   ├── site_a.py
│   │   ├── site_b.py
│
├── core/
│   ├── parser.py
│   ├── normalizer.py
│   ├── deduplicator.py
│   ├── exporter.py
│
├── config/
│   ├── sites.yaml
│
├── output/
│   ├── listings.csv
│   ├── listings.json
│
├── runner.py
├── requirements.txt
└── README.md

````

---

## 🚀 Getting Started

### 1. Install dependencies

```bash
pip install -r requirements.txt
````

### 2. Run the scraper

```bash
python runner.py --site site_a --url "https://example.com/property-for-sale"
```

You can replace `site_a` with any configured site in `config/sites.yaml`.

---

## 🔧 Configuration

Sites are defined in:

```
config/sites.yaml
```

Example:

```yaml
sites:
  site_a:
    start_urls:
      - "https://example.com/property-for-sale"
    selectors:
      listing_links: ".listing-card a::attr(href)"
      title: "h1::text"
      price: ".price::text"
      location: ".location::text"
```

To add a new site:

1. Add a new config entry
2. Create a corresponding spider file
3. Run via `runner.py`

---

## 🧪 Example Output (CSV)

| title                | price     | location  | bedrooms | bathrooms | listing_url |
| -------------------- | --------- | --------- | -------- | --------- | ----------- |
| Modern 2BR Apartment | 1,200,000 | Cape Town | 2        | 2         | https://... |

---

## 🔁 Logging & Reliability

The scraper logs:

* successful page fetches
* failed URLs
* retry attempts
* total listings scraped

This ensures the system can run reliably for large datasets.

---

## 🧠 Design Principles

* Simple, modular architecture
* Reusable scraping components
* Config-driven site support
* Clean, structured output
* Production-oriented reliability

---

## 📈 Future Enhancements

Planned extensions include:

* Additional website support
* Scheduling (cron / background jobs)
* Streamlit UI for non-technical users
* Docker containerization
* Cloud deployment (Fly.io / AWS)

---

## ⚖️ Compliance

This project only scrapes publicly accessible data and is designed to respect each website’s terms of service and rate limits.

No login, paywall, or restricted content is accessed.

---

## 💼 Use Cases

This system can be adapted for:

* Real estate listing aggregation
* Market research
* Lead generation
* Data analytics pipelines
* Business intelligence dashboards

---

## 👤 Author

William
Software Engineer – Web Scraping & Automation

Portfolio: [https://williamferns.org](https://williamferns.org)
GitHub: [https://github.com/vimscientist69](https://github.com/vimscientist69)

---

## 📌 License

MIT License
