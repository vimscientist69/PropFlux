# 📊 PropFlux Admin & Monitoring System

## 🎯 Overview
The PropFlux Admin System is a full-stack, comprehensive web application built to completely manage, monitor, and configure the real-estate scraper environment. Designed with a **React frontend** and a **FastAPI backend**, it proves top-tier engineering capabilities for a portfolio piece by moving beyond simple scripting into enterprise-level operations and infrastructure management.

---

## 🏗️ Architecture

### 1. The Core Scraper (Python/Scrapy)
- Works standalone via CLI (e.g. `python runner.py`) or programmatically.
- Decoupled from the API, maintaining clean separation of concerns.

### 2. The Backend API (FastAPI)
- Exposes RESTful endpoints to trigger scraper jobs, update configurations, and fetch data.
- Handles state management (knowing if a scraper is "Idle", "Running", "Failed", or "Completed").
- Reads the underlying SQLite database (`listings.db`) and Scrapy log/stats files to stream data to the frontend.

### 3. The Frontend (React/Vite)
- A modern, dynamic single-page application (SPA).
- Uses WebSockets or polling to update the scraper state and live data in real-time.
- Features beautiful data visualizations and an interactive control panel.

---

## 🎨 UI/UX Design Guidelines (The "Portfolio" Look)

To guarantee this project stands out to potential clients, the frontend must move away from generic bootstrap designs and adopt a **modern, clean, and highly professional aesthetic**. 

### Recommended UI Libraries
*   **Core Components:** **shadcn/ui** (Built on Tailwind CSS and Radix UI). It provides beautifully designed, accessible components (dropdowns, sliders, data tables) that look custom-built rather than "off-the-shelf" like older Material UI implementations.
*   **Styling Engine:** **Tailwind CSS**. Allows for rapid, consistent styling with a focus on a "glassmorphism" or sleek dark-mode aesthetic.
*   **Data Visualization:** **Tremor (tremor.so)** or **Recharts**. Tremor is specifically designed for building stunning, modern admin dashboards and integrates perfectly with Tailwind and React.

### Aesthetic Principles
1.  **Minimalistic Hierarchy:** Let the data breathe. Use generous padding, subtle borders (or borderless cards with soft drop-shadows), and a restricted color palette.
2.  **Dark Mode First (Optional but Recommended):** A sleek, slate/zinc dark mode (ex: `bg-zinc-950` with `border-zinc-800` borders) immediately signals a modern "developer-tool" or "command-center" vibe.
3.  **Accent Colors:** Use a single, vibrant accent color (like a neon indigo or emerald green) exclusively for active states, running progress bars, or "Run Job" primary buttons.
4.  **Micro-Interactions:** Buttons should have subtle hover states; logs should scroll smoothly; status indicators should softly pulse when a job is `[LIVE]`.

---

## ⚙️ The Admin Control Panel (Capabilities)

The dashboard is not just for viewing; it's the control center. The frontend will allow users to dynamically configure the following parameters before launching a scrape job:

### Target & Scope
*   **Target Site:** Dropdown selector (`Property24`, `PrivateProperty`, etc.).
*   **Start URL / Search Query:** A text input accepting direct category/search links.
*   **Max Pages Limit:** Override the default pagination depth.
*   **Hard Item Limit:** Cease scraping after X number of successfully saved listings.

### Infrastructure Control
*   **Concurrency & Speed:** Sliders to adjust `CONCURRENT_REQUESTS_PER_DOMAIN` and `DOWNLOAD_DELAY` based on current proxy health.
*   **Anti-Bot Toggling:** Toggle headless browser mode (to visually debug Selenium), or toggle CAPTCHA solving modules entirely.

### Job Management
*   **Run & Terminate:** Buttons to asynchronously launch a job or safely send a kill signal to an active Scrapy thread.
*   **Job History:** A table of past runs showing timestamp, target site, total items retrieved, success rate, and export links (Download CSV/JSON).

---

## 📈 Monitoring & Data Visualization Panels

### 1. Live Job Telemetry
While a job is running, the dashboard switches to a live tracking view:
*   **Progress Bar:** Calculated by `(Pages Scraped / Configured Max Pages) * 100`.
*   **Speedometer:** Items scraped per minute.
*   **Health Indicators (Green/Yellow/Red):**
    *   Proxy Success Rate (403/Forbidden tracking).
    *   CAPTCHA Solver Efficiency (Solved vs. Failed).
*   **Live Console Log:** A terminal-like window tailing the Scrapy logs directly in the browser.

### 2. Listing Analytics (Data Visualization)
Once scraped, the actual real-estate data is visualized to prove its value:
*   **Scatter Plot - Price vs. Bedroom/Bathroom Density:** Instantly identify market clusters and outliers across different suburbs.
*   **Bar Chart - Listings by Suburb/City:** Shows geographical distribution of the extracted data.
*   **Pie Chart - Property Types:** Distribution of Houses vs. Apartments vs. Commercial.
*   **Missing Fields Heatmap:** A grid showing data quality (e.g., what percentage of listings in Sea Point are missing Erf Size?).
*   **Live Data Table:** A searchable, filterable grid of the listings themselves exactly as they appear in the SQLite database.

---

## 🔌 Necessary Changes to the Scraper Engine

To seamlessly integrate this full-stack architecture while maintaining CLI capabilities, the following architectural shifts must occur in the existing Python codebase:

### 1. Job State Management (The Database Layer)
The scraper itself currently only saves *listings*. We need to track *jobs*.
*   **Action:** Add a `scrape_jobs` table to SQLite tracking: `job_id`, `site`, `status` (Running, Completed, Failed), `started_at`, `ended_at`, `items_scraped`.
*   **Action:** The `runner.py` must be updated so that when launched, it registers a row in `scrape_jobs`, and when gracefully shutting down or crashing, it updates that rows `status`.

### 2. Programmatic Execution (`runner.py` refactor)
Currently, `runner.py` is highly CLI-focused with `argparse`.
*   **Action:** Abstract the core execution logic inside `runner.py` into a reusable function (e.g., `run_spider(site_key, config_overrides)`). 
*   This allows the CLI to call `run_spider(args...)`, but also allows FastAPI to import and execute `run_spider(...)` in a background thread or asynchronous task (like Celery/RQ) with JSON payload settings from the React frontend.

### 3. Dynamic Configuration Passing
Currently, configuration lives statically in `config/sites.yaml`.
*   **Action:** Modify `scraper/spiders/base_spider.py` so it can accept a `config_overrides` dictionary injected during initialization.
*   If the frontend slides the "Download Delay" to `3.0`, FastAPI passes `{'DOWNLOAD_DELAY': 3.0}` into the Scrapy `CrawlerProcess`, overriding `sites.yaml` safely without modifying the filesystem.

### 4. Live Stats Extraction
FastAPI needs to know how fast the scraper is working *right now* to feed the React frontend.
*   **Action:** Hook into Scrapy's built-in Stats collection via a lightweight Custom Extension or Pipeline. Every 10 seconds, this extension should write a tiny `current_job_stats.json` file (or update a Redis/DB row) containing `pages_scraped`, `items_saved`, and `error_count`, which FastAPI simply reads and sends over WebSockets.