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
from multiprocessing.process import BaseProcess
import json

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
JOB_STATS_DIR = Path("output/job_stats")

# In-memory registry of active scraper processes keyed by job_id.
# This lives inside the FastAPI process and is sufficient for single-instance deployments.
JOB_PROCESSES: Dict[str, BaseProcess] = {}

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

    # Track the child process so we can terminate it later if requested.
    JOB_PROCESSES[job_id] = proc
    
    return {
        "job_id": job_id,
        "site": request.site,
        "status": "starting"
    }


@app.post("/jobs/{job_id}/terminate")
async def terminate_scrape_job(job_id: str):
    """
    Attempts to terminate a running scrape job.
    """
    proc = JOB_PROCESSES.get(job_id)

    # If we have no record of the process, report a 404 – either it never existed
    # for this API instance or it has already finished and been garbage-collected.
    if proc is None:
        raise HTTPException(
            status_code=404,
            detail=f"No active process found for job_id={job_id}",
        )

    # If the process has already exited, clean up and report a benign response.
    if not proc.is_alive():
        JOB_PROCESSES.pop(job_id, None)
        return {"job_id": job_id, "status": "already-finished"}

    # Before terminating, compute the current number of items scraped for this job
    # so we can persist an accurate snapshot in scrape_jobs.
    items_scraped: Optional[int] = None
    if DB_PATH.exists():
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM listings WHERE job_id = ?",
                (job_id,),
            )
            row = cursor.fetchone()
            items_scraped = int(row[0]) if row and row[0] is not None else 0
            conn.close()
        except Exception as count_err:  # pragma: no cover - defensive
            print(f"Warning: failed to count listings for job {job_id}: {count_err}")

    try:
        proc.terminate()
        proc.join(timeout=10)
        JOB_PROCESSES.pop(job_id, None)

        # Best-effort status update in the scrape_jobs table.
        try:
            exporter = Exporter()
            exporter.update_job_status(
                job_id,
                "TERMINATED",
                items_scraped=items_scraped,
                ended_at=True,
                terminated_at=True,
            )
        except Exception as db_err:  # pragma: no cover - defensive
            # We don't want DB issues to mask a successful termination.
            print(f"Warning: failed to update terminated status for {job_id}: {db_err}")

        return {"job_id": job_id, "status": "terminated"}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to terminate job {job_id}: {e}",
        )

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


@app.get("/jobs/{job_id}/telemetry")
async def get_job_telemetry(job_id: str):
    """
    Returns near-real-time telemetry for a job:
    - job row from scrape_jobs
    - scraped count (from job row)
    - pages scraped, items requested, etc (from output/job_stats/<job_id>.json)
    - computed progress (best-effort)
    """
    job_row: Dict[str, Any] | None = None
    if DB_PATH.exists():
        try:
            conn = sqlite3.connect(DB_PATH)
            df = pd.read_sql_query(
                "SELECT * FROM scrape_jobs WHERE job_id = ? LIMIT 1",
                conn,
                params=(job_id,),
            )
            conn.close()
            if not df.empty:
                record = df.to_dict(orient="records")[0]
                job_row = {k: (None if pd.isna(v) else v) for k, v in record.items()}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Database error: {e}")

    if job_row is None:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    # Read job_stats file (written by the Scrapy process)
    stats: Dict[str, Any] = {}
    stats_path = JOB_STATS_DIR / f"{job_id}.json"
    if stats_path.exists():
        try:
            stats = json.loads(stats_path.read_text(encoding="utf-8"))
        except Exception:
            stats = {}

    # Best-effort progress computation
    items_scraped = job_row.get("items_scraped") or 0
    limit = stats.get("limit")
    max_pages = stats.get("max_pages")
    pages_scraped = stats.get("pages_scraped")
    
    items_discovered = stats.get("items_discovered")
    items_processed = stats.get("items_processed")

    progress_mode = "unknown"
    progress = None
    
    if isinstance(limit, int) and limit > 0:
        progress_mode = "items"
        progress = min(1.0, items_scraped / float(limit))
    elif isinstance(items_discovered, int) and items_discovered > 0 and isinstance(items_processed, int):
        # Dynamic progress based on discovery vs processing
        progress_mode = "dynamic"
        progress = min(1.0, items_processed / float(items_discovered))

    is_alive = False
    proc = JOB_PROCESSES.get(job_id)
    if proc is not None:
        try:
            is_alive = proc.is_alive()
        except Exception:
            is_alive = False

    return {
        "job": job_row,
        "stats": stats,
        "runtime": {
            "is_alive": is_alive,
            "progress": progress,
            "progress_mode": progress_mode,
        },
    }


@app.get("/jobs/{job_id}/logs")
async def get_job_logs(job_id: str, tail: int = 200):
    """
    Returns the last N lines of the job's log file.
    """
    if tail < 1:
        tail = 1
    if tail > 2000:
        tail = 2000

    log_path: Optional[str] = None
    if DB_PATH.exists():
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT log_path, config FROM scrape_jobs WHERE job_id = ? LIMIT 1", (job_id,))
            row = cursor.fetchone()
            conn.close()
            if row:
                # Prefer explicit log_path column; fall back to config.log_path if needed
                log_path = row[0]
                if not log_path and row[1]:
                    try:
                        cfg = json.loads(row[1])
                        log_path = cfg.get("log_path")
                    except Exception:
                        pass
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Database error: {e}")

    if not log_path:
        # Fallback: attempt to find a matching log file
        candidates = sorted(Path("logs").glob(f"*{job_id}*.log"))
        if candidates:
            log_path = str(candidates[-1])

    if not log_path or not Path(log_path).exists():
        return {"job_id": job_id, "log_path": log_path, "lines": []}

    from collections import deque

    dq: deque[str] = deque(maxlen=tail)
    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                dq.append(line.rstrip("\n"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read log file: {e}")

    return {"job_id": job_id, "log_path": log_path, "lines": list(dq)}

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


@app.get("/listings/query")
async def query_listings(
    limit: int = 50,
    offset: int = 0,
    site: Optional[str] = None,
    job_id: Optional[str] = None,
    q: Optional[str] = None,
):
    """
    Paginated/searchable listings endpoint for the Phase 4 Data Explorer.
    """
    if not DB_PATH.exists():
        return {"total": 0, "items": []}

    # Basic guardrails
    limit = max(1, min(limit, 500))
    offset = max(0, offset)

    try:
        conn = sqlite3.connect(DB_PATH)

        conditions = []
        params: List[Any] = []

        if site:
            conditions.append("source_site = ?")
            params.append(site)
        if job_id:
            conditions.append("job_id = ?")
            params.append(job_id)
        if q:
            like = f"%{q}%"
            # Keep it simple: text search over a handful of columns.
            conditions.append("(title LIKE ? OR location LIKE ? OR property_type LIKE ?)")
            params.extend([like, like, like])

        where_clause = (" WHERE " + " AND ".join(conditions)) if conditions else ""

        total_query = "SELECT COUNT(*) FROM listings" + where_clause
        total = conn.execute(total_query, params).fetchone()
        total_count = int(total[0]) if total and total[0] is not None else 0

        items_query = (
            "SELECT * FROM listings"
            + where_clause
            + " ORDER BY scraped_at DESC LIMIT ? OFFSET ?"
        )
        items_params = params + [limit, offset]

        df = pd.read_sql_query(items_query, conn, params=items_params)
        conn.close()

        records = df.to_dict(orient="records")
        items = [
            {k: (None if pd.isna(v) else v) for k, v in record.items()}
            for record in records
        ]

        return {"total": total_count, "items": items}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
