import sys
from pathlib import Path
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import uuid
import sqlite3
import pandas as pd
import multiprocessing

# Add project root to path so we can import runner and core
sys.path.insert(0, str(Path(__file__).parent.parent))

from runner import run_spider
from core.exporter import Exporter

app = FastAPI(title="PropFlux API", description="Backend API for PropFlux Real Estate Scraper")

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = Path("output/listings.db")

class JobRequest(BaseModel):
    site: str
    url: Optional[str] = None
    limit: Optional[int] = None
    max_pages: Optional[int] = None
    skip_dynamic_fields: bool = False
    settings_overrides: Optional[Dict[str, Any]] = None

@app.get("/")
async def health_check():
    return {"status": "ok", "service": "PropFlux API"}

@app.post("/jobs/run")
async def start_scrape_job(request: JobRequest, background_tasks: BackgroundTasks):
    """
    Triggers a scrape job in the background.
    """
    job_id = f"job_{uuid.uuid4().hex[:8]}"
    
    # Run spider in a separate process to avoid Signal/Thread issues with Scrapy
    proc = multiprocessing.Process(
        target=run_spider,
        kwargs={
            "site_key": request.site,
            "url": request.url,
            "limit": request.limit,
            "max_pages": request.max_pages,
            "skip_dynamic_fields": request.skip_dynamic_fields,
            "job_id": job_id,
            "settings_overrides": request.settings_overrides
        }
    )
    proc.start()
    
    return {
        "job_id": job_id,
        "site": request.site,
        "status": "starting"
    }

@app.get("/jobs")
async def get_jobs_history():
    """
    Returns the history of all scrape jobs from the database.
    """
    if not DB_PATH.exists():
        return []
    
    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query("SELECT * FROM scrape_jobs ORDER BY started_at DESC", conn)
        conn.close()
        
        # Explicit conversion of NaN to None for robust JSON serialization
        records = df.to_dict(orient="records")
        return [
            {k: (None if pd.isna(v) else v) for k, v in record.items()}
            for record in records
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

@app.get("/listings")
async def get_listings(limit: int = 100, site: Optional[str] = None, job_id: Optional[str] = None):
    """
    Returns current scraped listings from the database.
    """
    if not DB_PATH.exists():
        return []
        
    try:
        conn = sqlite3.connect(DB_PATH)
        query = "SELECT * FROM listings"
        params = []
        conditions = []
        
        if site:
            conditions.append("source_site = ?")
            params.append(site)
        if job_id:
            conditions.append("job_id = ?")
            params.append(job_id)
            
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += " ORDER BY scraped_at DESC LIMIT ?"
        params.append(limit)
        
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        
        # Explicit conversion of NaN to None for robust JSON serialization
        records = df.to_dict(orient="records")
        return [
            {k: (None if pd.isna(v) else v) for k, v in record.items()}
            for record in records
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
