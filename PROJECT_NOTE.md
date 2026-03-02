# 🏠 PropFlux (MVP)

## 🎯 Goal

Build a reusable, production-style web scraping system that extracts structured real estate listings from **2 websites initially**, with a design that allows easily adding more sites later.

This project will serve as a **portfolio-quality reference** for Upwork web scraping jobs.

---

# 🧩 MVP Scope

## Supported Sites (initial)

1. Site A (e.g. Property24 or similar listing site)
2. Site B (another real estate listing site with similar structure)

> Note: Both sites should have:
- listing pages (pagination or infinite scroll)
- individual listing detail pages

---

# 📥 Input

The scraper should accept:

- a **start URL** (search page or category page)
- optional filters embedded in URL (location, price range, etc.)

Example:

```
python runner.py --site property24 --url "https://example.com/property-for-sale"
```

---

# 📤 Output

The system must output **structured data** in:

- CSV file
- JSON file (optional)
- SQLite database (optional but recommended)

### Fields to Extract

Each listing should include:

- `title`
- `price`
- `location`
- `bedrooms`
- `bathrooms`
- `property_type`
- `listing_url`
- `description`

Optional (if available):

- `agent_name`
- `agent_phone`
- `listing_id`
- `date_posted`

---

# 🧠 Core Features

## 1. Pagination Handling
- Automatically navigate listing pages
- Support next-page links or infinite scroll (if needed)

## 2. Detail Page Extraction
- Visit each listing page
- Extract full structured data

## 3. Data Normalization
Ensure consistent format:

- Price → numeric format
- Location → standardized text
- Bedrooms/bathrooms → integers
- Remove whitespace and noise

## 4. Deduplication
- Remove duplicate listings based on:
  - listing_id (preferred)
  - or URL fallback

## 5. Logging
Track:

- successful pages
- failed URLs
- retry attempts
- total listings scraped

## 6. Retry & Error Handling
- Retry failed requests (e.g. 2–3 times)
- Skip broken pages safely
- Continue scraping without crashing

---

# ⚙️ Architecture

```
/scraper
    spiders/
        site_a.py
        site_b.py

/core
    parser.py
    normalizer.py
    deduplicator.py
    exporter.py

/config
    sites.yaml

/output
    listings.csv
    listings.json

runner.py
requirements.txt
README.md
```

---

# 🛠 Tech Stack

- Python 3.11+
- Scrapy (main scraping engine)
- Requests (optional lightweight fetching)
- Playwright (only if required for JS-heavy pages)
- pandas (data cleaning/export)
- SQLite (optional storage)
- Docker (optional for deployment)

---

# 🔧 Config System

Create a config file:

```
/config/sites.yaml
```

Example:

```yaml
sites:
  property24:
    start_urls:
      - "https://example.com/property-for-sale"
    selectors:
      listing_links: ".listing-card a::attr(href)"
      title: "h1::text"
      price: ".price::text"
      location: ".location::text"
```

This allows adding new sites easily without rewriting core logic.

---

# 🚀 Runner Script

Main entry point:

```
python runner.py --site property24 --url "<start_url>"
```

Responsibilities:

- load config
- run correct spider
- store output
- trigger normalization + export

---

# 📦 Deliverables (for portfolio)

The final project must include:

- working scraping system
- clean structured output (CSV/JSON)
- sample dataset
- README with usage instructions
- config system for new sites
- logs demonstrating reliability

---

# 🧪 Example Output (CSV)

| title | price | location | bedrooms | bathrooms | url |
|------|------|----------|----------|-----------|-----|
| Modern 2BR Apartment | 1,200,000 | Cape Town | 2 | 2 | https://... |

---

# 🧱 Development Plan (3–4 weeks, 10h/week)

## Week 1
- project setup
- build scraper for Site A
- basic CSV export

## Week 2
- add detail page extraction
- normalization layer
- deduplication

## Week 3
- build scraper for Site B
- config system
- logging + retries

## Week 4 (optional polish)
- CLI runner improvements
- JSON + SQLite export
- README + docs
- screenshots for portfolio

---

# 🧠 Future Enhancements (Optional)

- simple UI (Streamlit)
- scheduling (cron / Airflow)
- Docker containerization
- proxy support (compliant usage only)
- cloud deployment (Fly.io / AWS)
- any real estate website support using AI

---

# 💼 How This Will Be Used

This project will be referenced in job proposals as:

> “A reusable multi-site real estate scraping platform that handles pagination, normalization, deduplication, and structured export.”

This demonstrates:

- real-world scraping capability
- scalable architecture
- clean engineering practices
- reliability for client work

---

# ✅ Definition of Done (MVP)

The MVP is complete when:

- 2 sites are fully supported
- data is extracted correctly
- output is clean and structured
- system runs end-to-end without manual fixes
- code is clean and documented

---

# 🧭 Guiding Principles

- Keep it simple
- Focus on reliability over complexity
- Build reusable components
- Design for extension (new sites later)

---

# 🎯 End Result

A **production-style scraping system** you can confidently show to clients to win jobs in:

- real estate scraping
- listing aggregation
- lead generation
- structured data extraction
