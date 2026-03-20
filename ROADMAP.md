# 🗺️ PropFlux Dashboard Roadmap

This roadmap outlines the multi-phase implementation of the PropFlux Admin & Monitoring System.

## Phase 1: API Foundation & Scraper Integration (Current)
*Focus: Enabling programmatic control and state tracking.*
- [x] **Scraper Engine Refactor:** 
  - Abstract `runner.py` into a reusable `run_spider` function.
  - Implement dynamic setting overrides (injected from API).
- [x] **FastAPI Backend Structure:**
  - Set up basic FastAPI boilerplate.
  - Create `POST /jobs/run` endpoint to trigger background scraper tasks.
  - Create `GET /listings` endpoint to query the SQLite database.
- [x] **Job State Tracking:**
  - Create `scrape_jobs` table in SQLite.
  - Implement job lifecycle hooks (Pending -> Running -> Completed/Failed).

## Phase 2: Dashboard Control Center (UI Foundation)
*Focus: A functional web interface to replace CLI commands.*
- [x] **React/Vite Setup:** Initialize the frontend project with Tailwind CSS.
- [x] **shadcn/ui Integration:** Set up the core design system and components.
- [x] **Main Control Panel:**
  - Site selector, URL input, and Limit sliders.
  - "Run Job" and "Terminte" controls.
- [x] **API Client Implementation:** Build the services to communicate with FastAPI.

## Phase 3: Real-Time Monitoring & Telemetry
*Focus: Live feedback during active scrapes.*
- [x] **WebSockets/Polling Implementation:** Stream status updates from backend to frontend.
- [x] **Live Console:** Stream Scrapy logs to a terminal component in the UI.
- [x] **Progress Monitoring:** Visual indicators for items scraped vs. limits.

## Phase 4: Data Visualization & Analytics
*Focus: Turning scraped data into actionable insights.*
- [x] **Analytics Dashboard:**
  - Price distribution charts (Price vs. Suburb).
  - Property type breakdown (Pie charts).
  - Geographic heatmaps.
- [x] **Data Explorer:** A searchable, paginated grid of all scraped listings.

## Phase 5: Infrastructure & Fine-Tuning
*Focus: History, Exports, and Production Readiness.*
- [ ] **Job History:** View and filter past runs.
- [ ] **Export Management:** Download JSON/CSV directly from the dashboard.
- [ ] **Performance Polishing:** Optimize API queries and frontend transitions.
